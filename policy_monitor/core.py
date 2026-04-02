#!/usr/bin/env python3
"""
Policy Monitor Core - 政策监控核心引擎

采用三层分层获取策略:
Layer 1: MCP Tools / API (结构化数据)
Layer 2: 定向爬虫 (网站清单)
Layer 3: Web Search (Fallback)
"""

import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib
import feedparser
import requests
from lxml import html

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('PolicyMonitor')


@dataclass
class PolicyItem:
    """政策条目"""
    title: str
    source: str
    publish_date: str
    link: str
    content: str = ""
    summary: str = ""
    keywords: List[str] = None
    priority: str = "P2"  # P0/P1/P2
    impact_analysis: Dict = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.impact_analysis is None:
            self.impact_analysis = {}
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def get_id(self) -> str:
        """生成唯一ID"""
        content = f"{self.title}:{self.source}:{self.publish_date}"
        return hashlib.md5(content.encode()).hexdigest()


class BaseFetcher(ABC):
    """获取器基类"""
    
    @abstractmethod
    def fetch(self) -> List[PolicyItem]:
        pass


class RSSFetcher(BaseFetcher):
    """RSS获取器 (Layer 1)"""
    
    def __init__(self, name: str, url: str, category: str = "general"):
        self.name = name
        self.url = url
        self.category = category
    
    def fetch(self) -> List[PolicyItem]:
        logger.info(f"[Layer 1] Fetching RSS: {self.name}")
        
        try:
            feed = feedparser.parse(self.url)
            items = []
            
            for entry in feed.entries[:20]:  # 最近20条
                item = PolicyItem(
                    title=entry.get('title', ''),
                    source=self.name,
                    publish_date=entry.get('published', datetime.now().isoformat()),
                    link=entry.get('link', ''),
                    content=entry.get('summary', '')
                )
                items.append(item)
            
            logger.info(f"[Layer 1] {self.name}: Got {len(items)} items")
            return items
            
        except Exception as e:
            logger.error(f"[Layer 1] RSS {self.name} failed: {e}")
            return []


class APIDataFetcher(BaseFetcher):
    """API数据获取器 (Layer 1)"""
    
    def __init__(self, name: str, api_url: str, params: Dict = None):
        self.name = name
        self.api_url = api_url
        self.params = params or {}
    
    def fetch(self) -> List[PolicyItem]:
        logger.info(f"[Layer 1] Fetching API: {self.name}")
        
        try:
            response = requests.get(self.api_url, params=self.params, timeout=30)
            data = response.json()
            
            # 解析API返回 (根据具体API调整)
            items = self._parse_api_response(data)
            
            logger.info(f"[Layer 1] {self.name}: Got {len(items)} items")
            return items
            
        except Exception as e:
            logger.error(f"[Layer 1] API {self.name} failed: {e}")
            return []
    
    def _parse_api_response(self, data: Dict) -> List[PolicyItem]:
        """解析API响应 - 子类可覆盖"""
        return []


class WebsiteScraper(BaseFetcher):
    """网站爬虫 (Layer 2)"""
    
    def __init__(self, name: str, url: str, xpath: str, 
                 link_prefix: str = "", encoding: str = "utf-8"):
        self.name = name
        self.url = url
        self.xpath = xpath
        self.link_prefix = link_prefix
        self.encoding = encoding
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PolicyMonitor/1.0 (Research Purpose)'
        })
    
    def fetch(self) -> List[PolicyItem]:
        logger.info(f"[Layer 2] Scraping: {self.name}")
        
        try:
            response = self.session.get(self.url, timeout=30)
            response.encoding = self.encoding
            
            tree = html.fromstring(response.content)
            elements = tree.xpath(self.xpath)
            
            items = []
            for elem in elements[:30]:  # 最近30条
                title = self._extract_text(elem)
                link = self._extract_link(elem)
                
                if title and link:
                    item = PolicyItem(
                        title=title,
                        source=self.name,
                        publish_date=datetime.now().isoformat(),
                        link=link
                    )
                    items.append(item)
            
            logger.info(f"[Layer 2] {self.name}: Got {len(items)} items")
            return items
            
        except Exception as e:
            logger.error(f"[Layer 2] Scrape {self.name} failed: {e}")
            return []
    
    def _extract_text(self, elem) -> str:
        """提取文本"""
        if hasattr(elem, 'text_content'):
            return elem.text_content().strip()
        return str(elem).strip()
    
    def _extract_link(self, elem) -> str:
        """提取链接"""
        link = elem.get('href', '')
        if link and not link.startswith('http'):
            link = self.link_prefix + link
        return link


class PolicyDatabase:
    """政策数据库"""
    
    def __init__(self, db_path: str = "policy_monitor.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS policies (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    source TEXT,
                    publish_date TEXT,
                    link TEXT,
                    content TEXT,
                    summary TEXT,
                    keywords TEXT,
                    priority TEXT,
                    impact_analysis TEXT,
                    fetched_at TEXT,
                    notified INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_policies_date 
                ON policies(publish_date DESC)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_policies_source 
                ON policies(source)
            """)
            
            conn.commit()
    
    def save(self, item: PolicyItem) -> bool:
        """保存政策条目"""
        item_id = item.get_id()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id FROM policies WHERE id = ?",
                (item_id,)
            )
            if cursor.fetchone():
                return False  # 已存在
            
            conn.execute(
                """INSERT INTO policies 
                   (id, title, source, publish_date, link, content, 
                    summary, keywords, priority, impact_analysis, fetched_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    item_id,
                    item.title,
                    item.source,
                    item.publish_date,
                    item.link,
                    item.content,
                    item.summary,
                    json.dumps(item.keywords),
                    item.priority,
                    json.dumps(item.impact_analysis),
                    datetime.now().isoformat()
                )
            )
            conn.commit()
            return True
    
    def get_recent(self, days: int = 7, priority: str = None) -> List[PolicyItem]:
        """获取近期政策"""
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            if priority:
                cursor = conn.execute(
                    """SELECT * FROM policies 
                       WHERE publish_date > ? AND priority = ?
                       ORDER BY publish_date DESC""",
                    (since, priority)
                )
            else:
                cursor = conn.execute(
                    """SELECT * FROM policies 
                       WHERE publish_date > ?
                       ORDER BY publish_date DESC""",
                    (since,)
                )
            
            rows = cursor.fetchall()
            return [self._row_to_item(row) for row in rows]
    
    def _row_to_item(self, row) -> PolicyItem:
        """数据库行转对象"""
        return PolicyItem(
            title=row[1],
            source=row[2],
            publish_date=row[3],
            link=row[4],
            content=row[5],
            summary=row[6],
            keywords=json.loads(row[7]) if row[7] else [],
            priority=row[8],
            impact_analysis=json.loads(row[9]) if row[9] else {}
        )
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM policies")
            total = cursor.fetchone()[0]
            
            cursor = conn.execute(
                "SELECT COUNT(*) FROM policies WHERE fetched_at > ?",
                ((datetime.now() - timedelta(days=1)).isoformat(),)
            )
            today = cursor.fetchone()[0]
            
            cursor = conn.execute(
                "SELECT source, COUNT(*) FROM policies GROUP BY source"
            )
            by_source = dict(cursor.fetchall())
            
            return {
                'total': total,
                'today': today,
                'by_source': by_source
            }


class KeywordMatcher:
    """关键词匹配器"""
    
    KEYWORDS = {
        'macro': ['货币政策', '财政政策', '降准', '降息', 'LPR', '专项债'],
        'industry': ['新能源汽车', '半导体', '芯片', '人工智能', '数字经济'],
        'capital_market': ['IPO', '注册制', '退市', '并购重组', '科创板'],
        'real_estate': ['房地产', '限购', '房贷利率', '保交楼'],
    }
    
    @classmethod
    def match(cls, text: str) -> List[str]:
        """匹配关键词"""
        matched = []
        text = text.lower()
        
        for category, keywords in cls.KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    matched.append(kw)
        
        return matched
    
    @classmethod
    def get_priority(cls, keywords: List[str]) -> str:
        """根据关键词确定优先级"""
        macro_kws = set(cls.KEYWORDS['macro'])
        
        if any(kw in macro_kws for kw in keywords):
            return "P0"
        
        if len(keywords) >= 2:
            return "P1"
        
        return "P2"


class PolicyMonitor:
    """政策监控主引擎"""
    
    def __init__(self, db_path: str = "policy_monitor.db"):
        self.db = PolicyDatabase(db_path)
        self.fetchers: List[BaseFetcher] = []
        self._init_fetchers()
    
    def _init_fetchers(self):
        """初始化获取器"""
        # Layer 1: RSS
        self.fetchers.extend([
            RSSFetcher("gov_cn", "http://www.gov.cn/zhengce/zhengceku/rss.htm"),
            RSSFetcher("pbc_monetary", "http://www.pbc.gov.cn/zhengcehuobisi/rss.xml"),
        ])
        
        # Layer 2: 网站爬虫
        self.fetchers.extend([
            WebsiteScraper(
                "ndrc",
                "https://www.ndrc.gov.cn/xxgk/zcfb/",
                "//div[@class='tzgg-list']//li/a",
                "https://www.ndrc.gov.cn"
            ),
        ])
    
    def run(self) -> List[PolicyItem]:
        """执行监控"""
        logger.info("=" * 50)
        logger.info("Policy Monitor Started")
        logger.info("=" * 50)
        
        all_items = []
        new_items = []
        
        # 执行所有获取器
        for fetcher in self.fetchers:
            items = fetcher.fetch()
            all_items.extend(items)
        
        # 处理并保存
        for item in all_items:
            # 关键词匹配
            text = f"{item.title} {item.content}"
            item.keywords = KeywordMatcher.match(text)
            item.priority = KeywordMatcher.get_priority(item.keywords)
            
            # 生成摘要
            if len(item.content) > 200:
                item.summary = item.content[:200] + "..."
            else:
                item.summary = item.content
            
            # 保存到数据库
            is_new = self.db.save(item)
            if is_new:
                new_items.append(item)
                logger.info(f"[NEW] {item.priority} | {item.source} | {item.title[:50]}")
        
        logger.info(f"Total: {len(all_items)}, New: {len(new_items)}")
        return new_items
    
    def generate_report(self, days: int = 1) -> str:
        """生成监控报告"""
        p0_items = self.db.get_recent(days, priority="P0")
        p1_items = self.db.get_recent(days, priority="P1")
        p2_items = self.db.get_recent(days, priority="P2")
        
        report = f"""# 政策监控报告 - {datetime.now().strftime('%Y-%m-%d')}

## 📊 统计概览

| 级别 | 数量 |
|------|------|
| P0 (紧急) | {len(p0_items)} |
| P1 (重要) | {len(p1_items)} |
| P2 (一般) | {len(p2_items)} |
| **总计** | **{len(p0_items) + len(p1_items) + len(p2_items)}** |

"""
        
        if p0_items:
            report += "## 🔴 P0级政策 (立即关注)\n\n"
            for item in p0_items:
                report += f"### {item.title}\n"
                report += f"- **来源**: {item.source}\n"
                report += f"- **关键词**: {', '.join(item.keywords)}\n"
                report += f"- **链接**: {item.link}\n\n"
        
        if p1_items:
            report += "## 🟡 P1级政策 (今日关注)\n\n"
            for item in p1_items[:5]:  # 只显示前5条
                report += f"- **{item.title}** ({item.source})\n"
        
        return report
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.db.get_stats()


if __name__ == '__main__':
    # 测试运行
    monitor = PolicyMonitor()
    
    # 执行监控
    new_items = monitor.run()
    
    # 生成报告
    report = monitor.generate_report(days=1)
    print(report)
    
    # 显示统计
    stats = monitor.get_stats()
    print(f"\nDatabase Stats: {stats}")
