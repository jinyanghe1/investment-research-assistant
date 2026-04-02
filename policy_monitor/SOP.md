# 政策监控SOP - 分层获取策略

> 版本: v1.0  
> 更新日期: 2026-04-02  
> 适用范围: 国内外政策数据获取

---

## 一、获取策略总览

采用**三层分层获取策略**，优先级递减：

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: MCP Tools / API (结构化数据)                        │
│ ├─ Wind/同花顺API                                           │
│ ├─ 政府开放平台API                                           │
│ ├─ 北大法宝API                                              │
│ └─ RSS订阅                                                  │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: 定向爬虫 (半结构化数据)                             │
│ ├─ 维护网站清单 (直接爬取, 不使用websearch)                  │
│ ├─ 国务院/各部委官网                                         │
│ ├─ 央行/证监会网站                                           │
│ └─ 美联储/SEC网站                                           │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: Web Search (Fallback/补充)                         │
│ ├─ 仅当Layer 1&2无法获取时使用                               │
│ ├─ 用于补充解读/背景信息                                     │
│ └─ 验证信息准确性                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、Layer 1: MCP Tools / API

### 2.1 优先级P0 (实时监控)

| 数据源 | 获取方式 | 更新频率 | 监控内容 |
|--------|----------|----------|----------|
| **央行货币政策** | yfinance + 官网RSS | 实时 | 利率、准备金率、MLF、LPR |
| **证监会监管动态** | RSS订阅 | 5分钟 | 发行监管、上市审核、处罚决定 |
| **国务院文件** | gov.cn RSS | 实时 | 国发、国办发、国函 |
| **美联储FOMC** | fredapi / RSS | 实时 | 利率决议、会议纪要 |

### 2.2 优先级P1 (每日监控)

| 数据源 | 获取方式 | 更新频率 | 监控内容 |
|--------|----------|----------|----------|
| **发改委产业政策** | 官网爬虫 | 每日 | 产业规划、项目审批、价格政策 |
| **财政部财税政策** | RSS + 爬虫 | 每日 | 预算、税收、国债、转移支付 |
| **地方政策** | 数据开放平台API | 每日 | 省级政府重大政策 |

### 2.3 Layer 1 工具清单

```yaml
# tools/policy_layer1.py 维护的工具

mcp_tools:
  - name: fetch_policy_rss
    description: 获取RSS订阅源
    sources:
      - gov_cn_zhengce
      - pbc_monetary
      - csrc_news
      
  - name: fetch_open_data_api
    description: 政府开放平台API
    sources:
      - shanghai_data_platform
      - beijing_data_platform
      
  - name: fetch_fred_data
    description: 美联储经济数据
    indicators:
      - FEDFUNDS (联邦基金利率)
      - DFF (日度有效利率)
```

---

## 三、Layer 2: 定向爬虫 (网站清单)

### 3.1 核心网站清单 (维护在 `config/websites.yaml`)

```yaml
# 国内政策网站清单
domestic:
  central:
    - name: "国务院"
      url: "http://www.gov.cn/zhengce/zhengceku/"
      xpath: "//div[@class='news_list']/ul/li"
      check_interval: 300
      priority: 0
      
    - name: "央行货币政策司"
      url: "http://www.pbc.gov.cn/zhengcehuobisi/11111/index.html"
      xpath: "//table[@class='table']//tr"
      check_interval: 300
      priority: 0
      
    - name: "证监会"
      url: "http://www.csrc.gov.cn/csrc/c100028/zfxxgk_zdgk.shtml"
      xpath: "//div[@class='row']//li"
      check_interval: 300
      priority: 0
      
    - name: "发改委"
      url: "https://www.ndrc.gov.cn/xxgk/zcfb/"
      xpath: "//div[@class='tzgg-list']//li"
      check_interval: 1800
      priority: 1
      
    - name: "财政部"
      url: "http://www.mof.gov.cn/zhengwuxinxi/zhengcefabu/"
      xpath: "//div[@class='list_cont']//li"
      check_interval: 1800
      priority: 1
      
    - name: "工信部"
      url: "https://www.miit.gov.cn/zwgk/zcwj/wjfb/tzgg/"
      xpath: "//div[@class='list']//li"
      check_interval: 3600
      priority: 1
      
    - name: "税务总局"
      url: "https://www.chinatax.gov.cn/chinatax/n810341/n810825/index.html"
      xpath: "//div[@class='list']//li"
      check_interval: 3600
      priority: 1

  local:
    - name: "上海市政府"
      url: "https://www.shanghai.gov.cn/nw12344/"
      api: "https://data.sh.gov.cn/api/v1/datasets"
      check_interval: 3600
      
    - name: "北京市政府"
      url: "https://www.beijing.gov.cn/zhengce/zhengcefagui/"
      api: "https://data.beijing.gov.cn/api/datasets"
      check_interval: 3600

# 国际政策网站清单
international:
  us:
    - name: "Federal Reserve"
      url: "https://www.federalreserve.gov/monetarypolicy/policy.htm"
      rss: "https://www.federalreserve.gov/feeds/press_all.xml"
      check_interval: 300
      priority: 0
      
    - name: "SEC"
      url: "https://www.sec.gov/news/press-releases"
      rss: "https://www.sec.gov/cgi/browse-edgar?action=getcurrent"
      check_interval: 600
      priority: 1
      
    - name: "White House"
      url: "https://www.whitehouse.gov/briefing-room/"
      rss: "https://www.whitehouse.gov/feed/"
      check_interval: 600
      priority: 1
      
    - name: "Treasury"
      url: "https://home.treasury.gov/news/press-releases"
      rss: "https://home.treasury.gov/news/press-releases/rss.xml"
      check_interval: 600
      priority: 1
      
    - name: "USTR"
      url: "https://ustr.gov/about-us/policy-offices/press-office/press-releases"
      check_interval: 3600
      priority: 2

  eu:
    - name: "ECB"
      url: "https://www.ecb.europa.eu/press/pr/date/html/index.en.html"
      rss: "https://www.ecb.europa.eu/rss/press.html"
      check_interval: 600
      priority: 1
      
    - name: "EU Commission"
      url: "https://ec.europa.eu/commission/presscorner/api/en/announcements"
      check_interval: 3600
      priority: 2

  international_org:
    - name: "IMF"
      url: "https://www.imf.org/en/news"
      rss: "https://www.imf.org/en/rss-feeds"
      check_interval: 3600
      priority: 2
      
    - name: "World Bank"
      url: "https://www.worldbank.org/en/news"
      rss: "https://www.worldbank.org/en/rss"
      check_interval: 3600
      priority: 2
```

### 3.2 Layer 2 爬虫规范

```python
# scripts/policy_scraper.py

class PolicyScraper:
    """
    Layer 2: 定向爬虫
    直接从维护的网站清单获取, 不使用websearch
    """
    
    def __init__(self, website_config: str):
        self.websites = self._load_websites(website_config)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PolicyMonitor/1.0 (Research Purpose)'
        })
    
    def crawl(self, source_name: str) -> List[PolicyItem]:
        """
        爬取指定源
        优先使用RSS, 其次是API, 最后是XPath爬虫
        """
        website = self.websites.get(source_name)
        if not website:
            raise ValueError(f"Unknown source: {source_name}")
        
        # 1. 尝试RSS
        if website.get('rss'):
            return self._parse_rss(website['rss'])
        
        # 2. 尝试API
        if website.get('api'):
            return self._call_api(website['api'], website.get('params', {}))
        
        # 3. 使用XPath爬虫
        return self._xpath_scrape(website['url'], website['xpath'])
    
    def _parse_rss(self, rss_url: str) -> List[PolicyItem]:
        """解析RSS订阅"""
        import feedparser
        feed = feedparser.parse(rss_url)
        return [
            PolicyItem(
                title=entry.title,
                link=entry.link,
                publish_date=entry.published,
                source=feed.title
            )
            for entry in feed.entries
        ]
    
    def _xpath_scrape(self, url: str, xpath: str) -> List[PolicyItem]:
        """XPath定向爬取"""
        from lxml import html
        
        response = self.session.get(url, timeout=30)
        tree = html.fromstring(response.content)
        elements = tree.xpath(xpath)
        
        return [
            PolicyItem(
                title=elem.text_content().strip(),
                link=elem.get('href'),
                source=url
            )
            for elem in elements
        ]
```

---

## 四、Layer 3: Web Search (Fallback)

### 4.1 使用条件

仅当以下情况使用Web Search：
- Layer 1 & 2 都无法获取目标信息
- 需要补充政策解读/背景信息
- 验证已获取信息的准确性

### 4.2 Web Search 查询模板

```yaml
# config/search_templates.yaml

templates:
  - name: "政策全文搜索"
    query: '{policy_title} site:gov.cn filetype:pdf OR filetype:doc'
    use_case: "获取官方政策文件全文"
    
  - name: "政策解读搜索"
    query: '{policy_title} 解读 分析 影响'
    sources: ["新华网", "人民网", "财新", "第一财经"]
    use_case: "获取权威媒体解读"
    
  - name: "国际政策搜索"
    query: '{policy_keyword} site:whitehouse.gov OR site:federalreserve.gov'
    use_case: "获取美国政策原文"
    
  - name: "行业影响搜索"
    query: '{industry} {policy_keyword} 影响 利好 利空'
    use_case: "分析政策对行业影响"
```

---

## 五、整合与输出

### 5.1 数据处理流程

```
获取原始数据
    ↓
[数据清洗] → 去重、格式化、标准化
    ↓
[关键词匹配] → 提取关键信息
    ↓
[优先级分级] → P0/P1/P2
    ↓
[影响分析] → 行业/市场影响
    ↓
[报告生成] → Markdown/HTML
    ↓
[告警通知] → 钉钉/微信/邮件
```

### 5.2 输出报告模板

```markdown
# 政策监控日报 - {{date}}

## 🔴 P0级政策 (立即关注)

### 1. {{政策标题}}
- **来源**: {{source}}
- **发布时间**: {{publish_time}}
- **关键词**: {{keywords}}
- **核心内容**: {{summary}}
- **影响分析**: 
  - 行业: {{affected_industries}}
  - 市场: {{market_impact}}
  - 预期: {{expectation}}
- **原文链接**: {{link}}

## 🟡 P1级政策 (今日关注)
...

## 📊 统计数据
- 今日新增政策: {{total_count}}
- P0级: {{p0_count}}
- P1级: {{p1_count}}
- P2级: {{p2_count}}
```

---

## 六、执行工作流

### 6.1 手动执行

```bash
# 执行Layer 1获取
python policy_monitor.py --layer 1 --source all

# 执行Layer 2爬取
python policy_monitor.py --layer 2 --source gov_cn,pbc,csrc

# 执行Layer 3补充搜索 (仅用于特定查询)
python policy_monitor.py --layer 3 --query "LPR下调影响"

# 生成完整报告
python policy_monitor.py --report daily
```

### 6.2 自动调度 (crontab)

```bash
# /etc/crontab

# Layer 1: 每5分钟监控核心源
*/5 * * * * cd /path/to/policy_monitor && python policy_monitor.py --layer 1 --critical >> logs/layer1.log 2>&1

# Layer 2: 每小时监控次要源
0 * * * * cd /path/to/policy_monitor && python policy_monitor.py --layer 2 >> logs/layer2.log 2>&1

# 日报生成: 每日18:00
0 18 * * * cd /path/to/policy_monitor && python policy_monitor.py --report daily >> logs/report.log 2>&1
```

---

## 七、维护 checklist

### 每周维护
- [ ] 检查Layer 1 RSS/API是否正常
- [ ] 验证Layer 2网站清单可访问性
- [ ] 更新失效的xpath选择器
- [ ] 清理重复数据

### 每月维护
- [ ] 更新网站清单 (新增/删除/修改)
- [ ] 优化关键词列表
- [ ] 调整告警规则
- [ ] 生成数据质量报告

---

## 八、附录

### A. 快速参考命令

```bash
# 测试单个源
python policy_monitor.py --test-source gov_cn

# 查看监控状态
python policy_monitor.py --status

# 导出近期数据
python policy_monitor.py --export --days 7 --format csv

# 清理缓存
python policy_monitor.py --cleanup --days 30
```

### B. 联系方式

- 技术支持: {{tech_contact}}
- 政策解读: {{policy_contact}}
- 紧急告警: {{alert_contact}}

---

**执行原则**: 
1. 优先使用MCP Tools和API
2. 网站清单直接爬取, 减少websearch依赖
3. Web Search仅作为fallback和信息验证
