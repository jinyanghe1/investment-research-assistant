#!/usr/bin/env python3
"""
数据管道管理器 - 统一的数据获取、缓存和管理系统

功能：
    - 增量数据更新
    - SQLite缓存层
    - 数据血缘追踪
    - 错误重试机制
    - 统一的API接口

Usage:
    from data_manager import DataManager
    
    manager = DataManager()
    data = manager.get_stock_data('000988.SZ', days=60)
    
    # 或命令行
    python data_manager.py --update-stock 000988.SZ
    python data_manager.py --update-all-indices
    python data_manager.py --cleanup-cache --days 30

Author: 投研AI中枢
Date: 2026-04-02
"""

import argparse
import json
import logging
import sqlite3
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable
from functools import wraps
import hashlib
import pickle

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('DataManager')


@dataclass
class DataSource:
    """数据源配置"""
    name: str
    source_type: str  # 'yfinance', 'akshare', 'tushare', 'file'
    priority: int  # 优先级，数字越小优先级越高
    enabled: bool = True
    config: Dict = None
    
    def __post_init__(self):
        if self.config is None:
            self.config = {}


@dataclass
class DataLineage:
    """数据血缘记录"""
    data_id: str
    source: str
    fetch_time: str
    data_hash: str
    raw_size: int
    processed_size: int
    transform_steps: List[str]
    quality_score: float
    expires_at: Optional[str] = None


class RetryPolicy:
    """重试策略"""
    def __init__(self, max_retries: int = 3, backoff_factor: float = 2.0, 
                 max_delay: float = 60.0):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
    
    def execute(self, func: Callable, *args, **kwargs):
        """执行带重试的函数"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                wait_time = min(
                    self.backoff_factor ** attempt,
                    self.max_delay
                )
                logger.warning(
                    f"尝试 {attempt + 1}/{self.max_retries} 失败: {e}. "
                    f"{wait_time:.1f}秒后重试..."
                )
                time.sleep(wait_time)
        
        raise last_exception


def with_retry(max_retries: int = 3, backoff_factor: float = 2.0):
    """重试装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            policy = RetryPolicy(max_retries, backoff_factor)
            return policy.execute(func, *args, **kwargs)
        return wrapper
    return decorator


class CacheManager:
    """SQLite缓存管理器"""
    
    def __init__(self, db_path: str = "data/cache.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    data BLOB,
                    timestamp TEXT,
                    expires_at TEXT,
                    data_hash TEXT,
                    size INTEGER
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lineage (
                    data_id TEXT PRIMARY KEY,
                    source TEXT,
                    fetch_time TEXT,
                    data_hash TEXT,
                    raw_size INTEGER,
                    processed_size INTEGER,
                    transform_steps TEXT,
                    quality_score REAL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_expires 
                ON cache(expires_at)
            """)
            
            conn.commit()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT data, expires_at FROM cache WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            
            if row is None:
                return None
            
            data, expires_at = row
            
            # 检查是否过期
            if expires_at:
                expires = datetime.fromisoformat(expires_at)
                if datetime.now() > expires:
                    logger.debug(f"缓存已过期: {key}")
                    return None
            
            return pickle.loads(data)
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """设置缓存数据"""
        expires_at = (datetime.now() + timedelta(seconds=ttl)).isoformat()
        data = pickle.dumps(value)
        data_hash = hashlib.md5(data).hexdigest()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO cache 
                   (key, data, timestamp, expires_at, data_hash, size)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (key, data, datetime.now().isoformat(), expires_at, data_hash, len(data))
            )
            conn.commit()
    
    def record_lineage(self, lineage: DataLineage):
        """记录数据血缘"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO lineage 
                   (data_id, source, fetch_time, data_hash, raw_size, 
                    processed_size, transform_steps, quality_score)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (lineage.data_id, lineage.source, lineage.fetch_time,
                 lineage.data_hash, lineage.raw_size, lineage.processed_size,
                 json.dumps(lineage.transform_steps), lineage.quality_score)
            )
            conn.commit()
    
    def get_lineage(self, data_id: str) -> Optional[DataLineage]:
        """获取数据血缘"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM lineage WHERE data_id = ?",
                (data_id,)
            )
            row = cursor.fetchone()
            
            if row is None:
                return None
            
            return DataLineage(
                data_id=row[0],
                source=row[1],
                fetch_time=row[2],
                data_hash=row[3],
                raw_size=row[4],
                processed_size=row[5],
                transform_steps=json.loads(row[6]),
                quality_score=row[7]
            )
    
    def cleanup(self, max_age_days: int = 30):
        """清理过期缓存"""
        cutoff = (datetime.now() - timedelta(days=max_age_days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # 删除过期数据
            cursor = conn.execute(
                "DELETE FROM cache WHERE expires_at < ?",
                (datetime.now().isoformat(),)
            )
            expired_count = cursor.rowcount
            
            # 删除旧数据
            cursor = conn.execute(
                "DELETE FROM cache WHERE timestamp < ?",
                (cutoff,)
            )
            old_count = cursor.rowcount
            
            conn.commit()
        
        logger.info(f"清理完成: {expired_count} 条过期, {old_count} 条旧数据")
        return expired_count + old_count
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*), SUM(size) FROM cache")
            total_count, total_size = cursor.fetchone()
            
            cursor = conn.execute(
                "SELECT COUNT(*) FROM cache WHERE expires_at < ?",
                (datetime.now().isoformat(),)
            )
            expired_count = cursor.fetchone()[0]
            
            return {
                'total_entries': total_count or 0,
                'total_size_mb': (total_size or 0) / (1024 * 1024),
                'expired_entries': expired_count,
                'db_path': str(self.db_path)
            }


class DataFetcher(ABC):
    """数据获取器基类"""
    
    def __init__(self, source: DataSource):
        self.source = source
        self.cache = CacheManager()
    
    @abstractmethod
    def fetch(self, identifier: str, **kwargs) -> Any:
        """获取数据"""
        pass
    
    def get_cache_key(self, identifier: str, **kwargs) -> str:
        """生成缓存key"""
        params = json.dumps(kwargs, sort_keys=True)
        return f"{self.source.name}:{identifier}:{hashlib.md5(params.encode()).hexdigest()}"


class YFinanceFetcher(DataFetcher):
    """yfinance数据获取器"""
    
    @with_retry(max_retries=3)
    def fetch(self, identifier: str, **kwargs) -> Dict:
        """获取股票数据"""
        import yfinance as yf
        
        days = kwargs.get('days', 120)
        
        ticker = yf.Ticker(identifier)
        hist = ticker.history(period=f'{days}d')
        info = ticker.info
        
        if hist.empty:
            raise ValueError(f"无法获取 {identifier} 的数据")
        
        # 转换为字典
        data = {
            'prices': hist.reset_index().to_dict('records'),
            'info': {
                'name': info.get('longName'),
                'sector': info.get('sector'),
                'market_cap': info.get('marketCap'),
                'pe': info.get('trailingPE'),
                'pb': info.get('priceToBook'),
            },
            'last_update': datetime.now().isoformat()
        }
        
        return data


class AKShareFetcher(DataFetcher):
    """AKShare数据获取器"""
    
    @with_retry(max_retries=3)
    def fetch(self, identifier: str, **kwargs) -> Dict:
        """获取数据"""
        try:
            import akshare as ak
        except ImportError:
            raise ImportError("请先安装 akshare: pip install akshare")
        
        data_type = kwargs.get('type', 'stock')
        
        if data_type == 'margin':
            # 融资融券数据
            code = identifier.replace('.SZ', '').replace('.SH', '')
            df = ak.stock_margin_detail_szse(symbol=code)
            return {'data': df.to_dict('records'), 'type': 'margin'}
        
        elif data_type == 'money_flow':
            # 资金流向
            code = identifier.replace('.SZ', '').replace('.SH', '')
            prefix = 'sz' if identifier.endswith('.SZ') else 'sh'
            df = ak.stock_individual_fund_flow(symbol=code, market=prefix)
            return {'data': df.to_dict('records'), 'type': 'money_flow'}
        
        else:
            raise ValueError(f"不支持的数据类型: {data_type}")


class DataManager:
    """数据管理器 - 统一入口"""
    
    # 缓存TTL配置（秒）
    TTL_CONFIG = {
        'stock_price': 300,      # 股价 5分钟
        'stock_kline': 3600,     # K线 1小时
        'margin': 1800,          # 融资融券 30分钟
        'money_flow': 900,       # 资金流向 15分钟
        'macro': 86400,          # 宏观数据 1天
        'index': 1800,           # 指数 30分钟
    }
    
    def __init__(self, cache_db: str = "data/cache.db"):
        self.cache = CacheManager(cache_db)
        self.fetchers = {}
        self._init_fetchers()
    
    def _init_fetchers(self):
        """初始化数据获取器"""
        # yfinance - 股票数据
        self.fetchers['yfinance'] = YFinanceFetcher(
            DataSource('yfinance', 'yfinance', 1)
        )
        
        # AKShare - 融资融券、资金流向
        try:
            self.fetchers['akshare'] = AKShareFetcher(
                DataSource('akshare', 'akshare', 2)
            )
        except Exception as e:
            logger.warning(f"AKShare初始化失败: {e}")
    
    def get_stock_data(self, ts_code: str, days: int = 120, 
                       use_cache: bool = True) -> Dict:
        """获取股票数据"""
        cache_key = f"stock:{ts_code}:{days}"
        
        # 尝试缓存
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                logger.debug(f"[CACHE] 命中 {ts_code}")
                return cached
        
        # 获取数据
        fetcher = self.fetchers.get('yfinance')
        if not fetcher:
            raise RuntimeError("yfinance获取器未初始化")
        
        data = fetcher.fetch(ts_code, days=days)
        
        # 写入缓存
        ttl = self.TTL_CONFIG['stock_kline']
        self.cache.set(cache_key, data, ttl)
        
        # 记录血缘
        lineage = DataLineage(
            data_id=cache_key,
            source='yfinance',
            fetch_time=datetime.now().isoformat(),
            data_hash=hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest(),
            raw_size=len(json.dumps(data)),
            processed_size=len(json.dumps(data)),
            transform_steps=['fetch', 'convert'],
            quality_score=1.0
        )
        self.cache.record_lineage(lineage)
        
        return data
    
    def get_margin_data(self, ts_code: str, use_cache: bool = True) -> Dict:
        """获取融资融券数据"""
        cache_key = f"margin:{ts_code}"
        
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        
        fetcher = self.fetchers.get('akshare')
        if not fetcher:
            raise RuntimeError("AKShare获取器未初始化")
        
        data = fetcher.fetch(ts_code, type='margin')
        
        ttl = self.TTL_CONFIG['margin']
        self.cache.set(cache_key, data, ttl)
        
        return data
    
    def get_money_flow(self, ts_code: str, use_cache: bool = True) -> Dict:
        """获取资金流向数据"""
        cache_key = f"money_flow:{ts_code}"
        
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        
        fetcher = self.fetchers.get('akshare')
        if not fetcher:
            raise RuntimeError("AKShare获取器未初始化")
        
        data = fetcher.fetch(ts_code, type='money_flow')
        
        ttl = self.TTL_CONFIG['money_flow']
        self.cache.set(cache_key, data, ttl)
        
        return data
    
    def get_incremental_update(self, ts_code: str, last_date: str) -> Dict:
        """
        获取增量更新数据
        
        Args:
            ts_code: 股票代码
            last_date: 上次更新日期 (YYYY-MM-DD)
            
        Returns:
            新增数据
        """
        # 获取完整数据
        full_data = self.get_stock_data(ts_code, days=365)
        
        # 过滤新增数据
        prices = full_data.get('prices', [])
        new_prices = [
            p for p in prices 
            if p.get('Date', '') > last_date
        ]
        
        logger.info(f"{ts_code}: 找到 {len(new_prices)} 条新数据")
        
        return {
            'prices': new_prices,
            'last_update': datetime.now().isoformat(),
            'incremental': True
        }
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计"""
        return self.cache.get_stats()
    
    def cleanup_cache(self, max_age_days: int = 30):
        """清理缓存"""
        return self.cache.cleanup(max_age_days)


def main():
    parser = argparse.ArgumentParser(description='数据管道管理器')
    parser.add_argument('--update-stock', help='更新股票数据')
    parser.add_argument('--days', type=int, default=120, help='数据天数')
    parser.add_argument('--update-margin', help='更新融资融券数据')
    parser.add_argument('--update-money-flow', help='更新资金流向数据')
    parser.add_argument('--incremental', help='增量更新 (股票代码)')
    parser.add_argument('--last-date', help='上次更新日期 (YYYY-MM-DD)')
    parser.add_argument('--cache-stats', action='store_true', help='缓存统计')
    parser.add_argument('--cleanup-cache', action='store_true', help='清理缓存')
    parser.add_argument('--max-age', type=int, default=30, help='最大缓存天数')
    parser.add_argument('--output', '-o', help='输出文件')
    
    args = parser.parse_args()
    
    manager = DataManager()
    
    if args.update_stock:
        data = manager.get_stock_data(args.update_stock, days=args.days)
        print(f"成功获取 {args.update_stock} 数据")
        print(f"数据条数: {len(data.get('prices', []))}")
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"数据已保存: {args.output}")
    
    elif args.update_margin:
        data = manager.get_margin_data(args.update_margin)
        print(f"成功获取 {args.update_margin} 融资融券数据")
        print(json.dumps(data, indent=2, default=str)[:500])
    
    elif args.update_money_flow:
        data = manager.get_money_flow(args.update_money_flow)
        print(f"成功获取 {args.update_money_flow} 资金流向数据")
        print(json.dumps(data, indent=2, default=str)[:500])
    
    elif args.incremental:
        if not args.last_date:
            print("错误: 增量更新需要 --last-date 参数")
            return 1
        data = manager.get_incremental_update(args.incremental, args.last_date)
        print(f"增量更新完成: {len(data.get('prices', []))} 条新数据")
    
    elif args.cache_stats:
        stats = manager.get_cache_stats()
        print("缓存统计:")
        print(f"  总条目: {stats['total_entries']}")
        print(f"  总大小: {stats['total_size_mb']:.2f} MB")
        print(f"  过期条目: {stats['expired_entries']}")
        print(f"  数据库: {stats['db_path']}")
    
    elif args.cleanup_cache:
        count = manager.cleanup_cache(args.max_age)
        print(f"清理完成: {count} 条缓存被删除")
    
    else:
        parser.print_help()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
