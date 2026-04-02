#!/usr/bin/env python3
"""
数据管道调度器 - 定时任务管理

功能：
    - 定时数据更新
    - 任务依赖管理
    - 失败重试
    - 执行日志记录

Usage:
    python scheduler.py --run-daily       # 运行日常更新
    python scheduler.py --run-hourly      # 运行小时更新
    python scheduler.py --add-job         # 添加定时任务
    python scheduler.py --list-jobs       # 列出所有任务
    python scheduler.py --cron-setup      # 生成crontab配置

Crontab Setup:
    # 每小时更新股价数据
    0 * * * * cd /path/to/project && python scripts/data-pipeline/scheduler.py --run-hourly
    
    # 每日更新完整数据
    0 18 * * * cd /path/to/project && python scripts/data-pipeline/scheduler.py --run-daily

Author: 投研AI中枢
Date: 2026-04-02
"""

import argparse
import json
import logging
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DataScheduler')


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class ScheduledJob:
    """定时任务定义"""
    job_id: str
    name: str
    command: str
    schedule: str  # 'hourly', 'daily', 'weekly', 'custom'
    custom_cron: Optional[str] = None
    enabled: bool = True
    last_run: Optional[str] = None
    last_status: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    depends_on: List[str] = None
    
    def __post_init__(self):
        if self.depends_on is None:
            self.depends_on = []


class SchedulerDB:
    """调度器数据库"""
    
    def __init__(self, db_path: str = "data/scheduler.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            # 任务表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    name TEXT,
                    command TEXT,
                    schedule TEXT,
                    custom_cron TEXT,
                    enabled INTEGER DEFAULT 1,
                    last_run TEXT,
                    last_status TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    depends_on TEXT
                )
            """)
            
            # 执行日志表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS job_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    status TEXT,
                    output TEXT,
                    error TEXT,
                    retry_number INTEGER DEFAULT 0
                )
            """)
            
            # 数据更新记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_updates (
                    update_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_type TEXT,
                    identifier TEXT,
                    update_time TEXT,
                    records_count INTEGER,
                    status TEXT,
                    next_update TEXT
                )
            """)
            
            conn.commit()
    
    def add_job(self, job: ScheduledJob):
        """添加任务"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO jobs 
                   (job_id, name, command, schedule, custom_cron, enabled,
                    last_run, last_status, retry_count, max_retries, depends_on)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (job.job_id, job.name, job.command, job.schedule, 
                 job.custom_cron, int(job.enabled), job.last_run,
                 job.last_status, job.retry_count, job.max_retries,
                 json.dumps(job.depends_on))
            )
            conn.commit()
    
    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """获取任务"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?",
                (job_id,)
            )
            row = cursor.fetchone()
            
            if row is None:
                return None
            
            return ScheduledJob(
                job_id=row[0],
                name=row[1],
                command=row[2],
                schedule=row[3],
                custom_cron=row[4],
                enabled=bool(row[5]),
                last_run=row[6],
                last_status=row[7],
                retry_count=row[8],
                max_retries=row[9],
                depends_on=json.loads(row[10]) if row[10] else []
            )
    
    def list_jobs(self) -> List[ScheduledJob]:
        """列出所有任务"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT * FROM jobs")
            rows = cursor.fetchall()
            
            jobs = []
            for row in rows:
                jobs.append(ScheduledJob(
                    job_id=row[0],
                    name=row[1],
                    command=row[2],
                    schedule=row[3],
                    custom_cron=row[4],
                    enabled=bool(row[5]),
                    last_run=row[6],
                    last_status=row[7],
                    retry_count=row[8],
                    max_retries=row[9],
                    depends_on=json.loads(row[10]) if row[10] else []
                ))
            return jobs
    
    def update_job_status(self, job_id: str, status: str, last_run: str = None):
        """更新任务状态"""
        with sqlite3.connect(self.db_path) as conn:
            if last_run:
                conn.execute(
                    "UPDATE jobs SET last_status = ?, last_run = ? WHERE job_id = ?",
                    (status, last_run, job_id)
                )
            else:
                conn.execute(
                    "UPDATE jobs SET last_status = ? WHERE job_id = ?",
                    (status, job_id)
                )
            conn.commit()
    
    def log_execution(self, job_id: str, start_time: str, end_time: str,
                      status: str, output: str = "", error: str = "",
                      retry_number: int = 0):
        """记录执行日志"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO job_logs 
                   (job_id, start_time, end_time, status, output, error, retry_number)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (job_id, start_time, end_time, status, output, error, retry_number)
            )
            conn.commit()
    
    def log_data_update(self, data_type: str, identifier: str, 
                        records_count: int, status: str):
        """记录数据更新"""
        next_update = (datetime.now() + timedelta(hours=1)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO data_updates 
                   (data_type, identifier, update_time, records_count, status, next_update)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (data_type, identifier, datetime.now().isoformat(),
                 records_count, status, next_update)
            )
            conn.commit()
    
    def get_recent_logs(self, job_id: str = None, limit: int = 10) -> List[Dict]:
        """获取最近日志"""
        with sqlite3.connect(self.db_path) as conn:
            if job_id:
                cursor = conn.execute(
                    """SELECT * FROM job_logs WHERE job_id = ? 
                       ORDER BY start_time DESC LIMIT ?""",
                    (job_id, limit)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM job_logs ORDER BY start_time DESC LIMIT ?",
                    (limit,)
                )
            
            rows = cursor.fetchall()
            logs = []
            for row in rows:
                logs.append({
                    'log_id': row[0],
                    'job_id': row[1],
                    'start_time': row[2],
                    'end_time': row[3],
                    'status': row[4],
                    'output': row[5][:200] if row[5] else "",
                    'error': row[6][:200] if row[6] else "",
                    'retry_number': row[7]
                })
            return logs


class DataScheduler:
    """数据调度器"""
    
    def __init__(self):
        self.db = SchedulerDB()
        self._init_default_jobs()
    
    def _init_default_jobs(self):
        """初始化默认任务"""
        default_jobs = [
            ScheduledJob(
                job_id='update_indices',
                name='更新指数数据',
                command='python tools/fetch_index_data.py --index hs300,cy,sz',
                schedule='hourly',
                max_retries=3
            ),
            ScheduledJob(
                job_id='update_stock_000988',
                name='更新华工科技数据',
                command='python tools/fetch_stock_data.py --ts-code 000988.SZ --verify',
                schedule='hourly',
                max_retries=3
            ),
            ScheduledJob(
                job_id='cleanup_cache',
                name='清理过期缓存',
                command='python scripts/data-pipeline/data_manager.py --cleanup-cache --max-age 7',
                schedule='daily',
                max_retries=1
            ),
            ScheduledJob(
                job_id='daily_report',
                name='生成日报',
                command='python tools/technical_analysis_enhanced.py --ts-code 000988.SZ --margin --money-flow',
                schedule='daily',
                depends_on=['update_stock_000988'],
                max_retries=2
            ),
        ]
        
        for job in default_jobs:
            existing = self.db.get_job(job.job_id)
            if existing is None:
                self.db.add_job(job)
                logger.info(f"添加默认任务: {job.name}")
    
    def run_job(self, job_id: str, force: bool = False) -> bool:
        """运行任务"""
        job = self.db.get_job(job_id)
        if not job:
            logger.error(f"任务不存在: {job_id}")
            return False
        
        if not job.enabled and not force:
            logger.info(f"任务已禁用: {job.name}")
            return False
        
        # 检查依赖
        for dep_id in job.depends_on:
            dep_job = self.db.get_job(dep_id)
            if dep_job and dep_job.last_status != 'success':
                logger.warning(f"依赖任务 {dep_id} 未成功，跳过 {job_id}")
                return False
        
        logger.info(f"运行任务: {job.name}")
        start_time = datetime.now().isoformat()
        
        try:
            # 更新状态
            self.db.update_job_status(job_id, JobStatus.RUNNING.value, start_time)
            
            # 执行命令
            result = subprocess.run(
                job.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            end_time = datetime.now().isoformat()
            
            if result.returncode == 0:
                self.db.update_job_status(job_id, JobStatus.SUCCESS.value, end_time)
                self.db.log_execution(
                    job_id, start_time, end_time, 
                    JobStatus.SUCCESS.value,
                    output=result.stdout
                )
                logger.info(f"任务成功: {job.name}")
                return True
            else:
                raise Exception(result.stderr)
                
        except Exception as e:
            end_time = datetime.now().isoformat()
            
            # 重试逻辑
            if job.retry_count < job.max_retries:
                job.retry_count += 1
                self.db.update_job_status(job_id, JobStatus.RETRYING.value)
                logger.warning(f"任务失败，准备重试 ({job.retry_count}/{job.max_retries}): {e}")
                time.sleep(2 ** job.retry_count)  # 指数退避
                return self.run_job(job_id, force=True)
            else:
                self.db.update_job_status(job_id, JobStatus.FAILED.value, end_time)
                self.db.log_execution(
                    job_id, start_time, end_time,
                    JobStatus.FAILED.value,
                    error=str(e)
                )
                logger.error(f"任务失败: {job.name}, 错误: {e}")
                return False
    
    def run_hourly(self):
        """运行小时任务"""
        logger.info("运行小时更新任务")
        
        jobs = self.db.list_jobs()
        hourly_jobs = [j for j in jobs if j.schedule == 'hourly' and j.enabled]
        
        for job in hourly_jobs:
            self.run_job(job.job_id)
    
    def run_daily(self):
        """运行日任务"""
        logger.info("运行日更新任务")
        
        jobs = self.db.list_jobs()
        daily_jobs = [j for j in jobs if j.schedule == 'daily' and j.enabled]
        
        for job in daily_jobs:
            self.run_job(job.job_id)
    
    def add_job(self, name: str, command: str, schedule: str, 
                custom_cron: str = None, depends_on: List[str] = None):
        """添加任务"""
        job_id = f"job_{int(time.time())}_{name}"
        
        job = ScheduledJob(
            job_id=job_id,
            name=name,
            command=command,
            schedule=schedule,
            custom_cron=custom_cron,
            depends_on=depends_on or []
        )
        
        self.db.add_job(job)
        logger.info(f"添加任务: {name}")
        return job_id
    
    def list_jobs(self):
        """列出任务"""
        jobs = self.db.list_jobs()
        
        print(f"\n{'任务ID':<20} {'名称':<20} {'调度':<10} {'状态':<10} {'上次运行':<20}")
        print("-" * 80)
        
        for job in jobs:
            status = "启用" if job.enabled else "禁用"
            last_run = job.last_run or "从未"
            if len(last_run) > 19:
                last_run = last_run[:19]
            print(f"{job.job_id:<20} {job.name:<20} {job.schedule:<10} {status:<10} {last_run:<20}")
    
    def get_crontab_config(self) -> str:
        """生成crontab配置"""
        config = """# 投研助手数据管道定时任务
# 生成时间: {}

# 每小时更新股价数据
0 * * * * cd {} && python scripts/data-pipeline/scheduler.py --run-hourly >> logs/scheduler_hourly.log 2>&1

# 每日18:00更新完整数据
0 18 * * * cd {} && python scripts/data-pipeline/scheduler.py --run-daily >> logs/scheduler_daily.log 2>&1

# 每周日凌晨清理缓存
0 0 * * 0 cd {} && python scripts/data-pipeline/data_manager.py --cleanup-cache --max-age 30 >> logs/cleanup.log 2>&1
""".format(
            datetime.now().isoformat(),
            Path.cwd(),
            Path.cwd(),
            Path.cwd()
        )
        return config


def main():
    parser = argparse.ArgumentParser(description='数据管道调度器')
    parser.add_argument('--run-hourly', action='store_true', help='运行小时任务')
    parser.add_argument('--run-daily', action='store_true', help='运行日任务')
    parser.add_argument('--run-job', help='运行指定任务')
    parser.add_argument('--add-job', help='添加任务名称')
    parser.add_argument('--command', help='任务命令')
    parser.add_argument('--schedule', choices=['hourly', 'daily', 'weekly'], 
                        help='调度周期')
    parser.add_argument('--list-jobs', action='store_true', help='列出任务')
    parser.add_argument('--cron-setup', action='store_true', help='生成crontab配置')
    parser.add_argument('--logs', help='查看任务日志')
    parser.add_argument('--limit', type=int, default=10, help='日志条数')
    
    args = parser.parse_args()
    
    scheduler = DataScheduler()
    
    if args.run_hourly:
        scheduler.run_hourly()
    
    elif args.run_daily:
        scheduler.run_daily()
    
    elif args.run_job:
        success = scheduler.run_job(args.run_job)
        sys.exit(0 if success else 1)
    
    elif args.add_job:
        if not args.command or not args.schedule:
            print("错误: --add-job 需要 --command 和 --schedule 参数")
            return 1
        job_id = scheduler.add_job(args.add_job, args.command, args.schedule)
        print(f"添加任务成功: {job_id}")
    
    elif args.list_jobs:
        scheduler.list_jobs()
    
    elif args.cron_setup:
        print(scheduler.get_crontab_config())
    
    elif args.logs:
        logs = scheduler.db.get_recent_logs(args.logs, args.limit)
        for log in logs:
            print(f"\n[{log['start_time']}] {log['status']}")
            if log['output']:
                print(f"输出: {log['output'][:100]}")
            if log['error']:
                print(f"错误: {log['error'][:100]}")
    
    else:
        parser.print_help()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
