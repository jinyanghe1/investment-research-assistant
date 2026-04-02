# 政策数据获取标准作业程序 (SOP)

> 版本：v1.0
> 创建日期：2026-04-02
> 适用范围：国内外政策文件、数据获取任务

---

## 一、目的

本SOP旨在规范政策数据获取流程，确保数据的**权威性**、**时效性**和**完整性**。

### 获取优先级原则

```
Layer 1: MCP Tools (首选)
    ↓ 不可用/不完整时
Layer 2: 直接官方来源网页抓取
    ↓ 仍不足时
Layer 3: WebSearch + 商业平台补充
```

---

## 二、数据源层级

### Layer 1: MCP Tools (首选)

| 工具 | 用途 | 调用方式 |
|------|------|----------|
| **Notion MCP** | 企业/机构政策文档库 | `mcp__notion__API-*` |
| **WebSearch MCP** | 实时政策搜索 | `WebFetch` |
| **AKShare MCP** | 宏观政策数据 | `ak.macro_china_*` |
| **FRED API** | 国际货币政策数据 | `fredapi` |

### Layer 2: 直接官方来源 (Fallback)

> 详见 `SOP/sources/` 子目录

### Layer 3: 商业平台 (补充)

| 平台 | 用途 | 费用 |
|------|------|------|
| 东方财富 | 政策资讯聚合 | 免费 |
| 华尔街见闻 | 实时政策解读 | 免费 |
| Tushare | 结构化政策数据 | 部分免费 |
| Bloomberg | 专业政策数据 | 付费 |

---

## 三、国内政策数据源

### 3.1 核心官方来源

| 来源 | URL | 数据类型 | 更新频率 |
|------|-----|----------|----------|
| **国务院政策文件库** | https://www.gov.cn/zhengce/ | 国务院文件、常务会议 | 实时 |
| **国务院常务会议** | https://www.gov.cn/zxft/ | 重要决策部署 | 每周 |
| **发改委政策发布** | https://www.ndrc.gov.cn/xinwen/ | 项目审批、规划 | 实时 |
| **证监会公告** | http://www.csrc.gov.cn/csrc/c100028/index.shtml | 监管政策、披露 | 实时 |
| **央行货币政策司** | http://www.pbc.gov.cn/rmyh/ | 利率、汇率政策 | 实时 |
| **财政部政策** | http://www.mof.gov.cn/zhengwuxinxi/ | 财政数据、政策 | 实时 |
| **商务部发布** | http://www.mofcom.gov.cn/article/ | 贸易、对外开放 | 实时 |
| **国家统计局** | http://www.stats.gov.cn/ | 宏观数据 | 月度 |
| **银保监会公告** | http://www.cbirc.gov.cn/ | 银行保险监管 | 实时 |

### 3.2 政策文件类型

| 类型 | 来源 | 权威性 |
|------|------|--------|
| **行政法规** | 国务院 | 最高 |
| **部门规章** | 各部委 | 高 |
| **规范性文件** | 各部委 | 高 |
| **政策解读** | 各部委 | 中 |
| **新闻稿** | 各部委 | 中 |

---

## 四、国际政策数据源

### 4.1 美国政策

| 来源 | URL | 数据类型 | 更新频率 |
|------|-----|----------|----------|
| **白宫新闻** | https://www.whitehouse.gov/briefings-statements/ | 行政命令、政策 | 实时 |
| **美联储** | https://www.federalreserve.gov/pressrels.htm | FOMC声明、褐皮书 | 重要会议后 |
| **SEC新闻** | https://www.sec.gov/news/pressreleases | 监管政策 | 实时 |
| **USTR公告** | https://ustr.gov/about-us/policy-offices/press-office | 贸易政策 | 实时 |

### 4.2 欧洲政策

| 来源 | URL | 数据类型 |
|------|-----|----------|
| **欧央行** | https://www.ecb.europa.eu/press/prhtml | 货币政策声明 |
| **欧盟委员会** | https://ec.europa.eu/commission/presscorner/ | 政策发布 |
| **英国央行** | https://www.bankofengland.co.uk/news | 货币政策 |

### 4.3 国际组织

| 来源 | URL | 数据类型 |
|------|-----|----------|
| **IMF** | https://www.imf.org/en/News | 宏观经济评估 |
| **世界银行** | https://www.worldbank.org/en/news | 发展政策 |
| **WTO** | https://www.wto.org/english/news_e/ | 贸易政策 |
| **G20** | https://g20.org/ | 全球协调政策 |

---

## 五、获取流程

### 5.1 标准流程图

```
开始
  │
  ▼
确定政策需求 (国内/国际/金融/财政/贸易/产业)
  │
  ▼
Layer 1: 尝试MCP Tools
  │  ├─ 成功 + 数据完整 → 保存
  │  └─ 失败/不完整 → Layer 2
  │
  ▼
Layer 2: 直接官方来源抓取
  │  ├─ 成功 + 数据完整 → 保存
  │  └─ 失败/不完整 → Layer 3
  │
  ▼
Layer 3: WebSearch + 商业平台
  │
  ▼
整合数据 + 记录来源 + 时间戳
  │
  ▼
输出政策报告/摘要
  │
  ▼
结束
```

### 5.2 关键词策略

```python
# 国内政策关键词
CN_POLICY_KEYWORDS = {
    "金融监管": ["证监会", "银保监", "央行", "监管", "合规"],
    "财政政策": ["财政部", "预算", "赤字", "专项债", "退税"],
    "货币政策": ["央行", "利率", "准备金率", "LPR", "流动性"],
    "贸易政策": ["商务部", "关税", "贸易战", "制裁", "出口管制"],
    "产业政策": ["发改委", "十四五", "规划", "新能源", "半导体", "芯片"],
    "房地产政策": ["住建部", "房地产", "限购", "房贷", "房产税"],
}

# 国际政策关键词
INTL_POLICY_KEYWORDS = {
    "美联储": ["FOMC", "Federal Reserve", "interest rate", "monetary policy"],
    "贸易": ["USTR", "tariff", "trade war", "sanctions", "WTO"],
    "科技政策": ["export control", "semiconductor", "AI regulation"],
}
```

---

## 六、代码模板

### 6.1 基础获取模板

```python
#!/usr/bin/env python3
"""
fetch_policy_data.py - 政策数据获取脚本

Usage:
    python fetch_policy_data.py --source gov --keyword "新能源"
    python fetch_policy_data.py --source cbirc --days 7
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 官方来源URL配置
POLICY_SOURCES = {
    "gov": {
        "name": "国务院政策文件库",
        "url": "https://www.gov.cn/zhengce/",
        "selector": "div.list ul li",
    },
    "cbirc": {
        "name": "银保监会公告",
        "url": "http://www.cbirc.gov.cn/cn/list/list.do",
        "selector": "div.newslist",
    },
}

def fetch_from_official_source(source_code: str, days: int = 30) -> list:
    """
    从官方来源直接抓取政策数据

    Args:
        source_code: 来源代码
        days: 抓取最近N天数据

    Returns:
        政策数据列表
    """
    import requests

    source = POLICY_SOURCES.get(source_code)
    if not source:
        return []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

    try:
        response = requests.get(source['url'], headers=headers, timeout=10)
        response.raise_for_status()

        # 解析HTML (需要配合 BeautifulSoup)
        # results = parse_policy_list(response.text, source['selector'])

        return [{
            'source': source['name'],
            'url': source['url'],
            'fetch_time': datetime.now().isoformat(),
            'data_source': 'official_direct'
        }]
    except Exception as e:
        print(f"[ERROR] 获取{source['name']}失败: {e}")
        return []


def fetch_policy_data(keywords: list, region: str = "CN", days: int = 30) -> dict:
    """
    综合政策数据获取 (三层策略)

    Args:
        keywords: 关键词列表
        region: 区域 CN/INTL
        days: 抓取天数

    Returns:
        包含政策数据的字典
    """
    results = {
        'keywords': keywords,
        'region': region,
        'policies': [],
        'sources_used': [],
        'fetch_time': datetime.now().isoformat(),
    }

    # Layer 1: 尝试MCP Tools
    # if MCP tools available:
    #     mcp_results = fetch_via_mcp(keywords)
    #     if mcp_results:
    #         results['policies'].extend(mcp_results)
    #         results['sources_used'].append('mcp')

    # Layer 2: 直接官方来源
    for source_code in POLICY_SOURCES.keys():
        official_data = fetch_from_official_source(source_code, days)
        if official_data:
            results['policies'].extend(official_data)
            results['sources_used'].append(f'official_{source_code}')

    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='政策数据获取')
    parser.add_argument('--keyword', '-k', nargs='+', help='政策关键词')
    parser.add_argument('--source', '-s', choices=['gov', 'ndrc', 'cbirc', 'all'], default='all')
    parser.add_argument('--days', '-d', type=int, default=30)
    args = parser.parse_args()

    data = fetch_policy_data(args.keyword or [], days=args.days)
    print(json.dumps(data, ensure_ascii=False, indent=2))
```

### 6.2 WebSearch 策略模板

```python
def search_policies_via_websearch(keywords: list, region: str = "CN") -> list:
    """
    通过WebSearch MCP获取政策数据

    Args:
        keywords: 关键词列表
        region: CN 或 INTL

    Returns:
        搜索结果列表
    """
    # 构造搜索查询
    if region == "CN":
        query = " OR ".join([f'"{k}"' for k in keywords])
        query += " site:gov.cn"
    else:
        query = " OR ".join([f'"{k}"' for k in keywords])

    # 使用WebSearch MCP
    # results = websearch(query)

    return results
```

---

## 七、输出格式

### 7.1 标准输出结构

```json
{
  "policies": [
    {
      "title": "政策标题",
      "source": "发布机构",
      "url": "原文链接",
      "publish_date": "2026-04-02",
      "fetch_time": "2026-04-02T10:30:00",
      "keywords": ["关键词1", "关键词2"],
      "summary": "政策摘要...",
      "data_source": "official_direct | websearch | mcp",
      "relevance_score": 0.95
    }
  ],
  "search_metadata": {
    "keywords": ["政策关键词"],
    "region": "CN",
    "days": 30,
    "total_results": 10,
    "sources_used": ["official_gov", "websearch"]
  }
}
```

### 7.2 Markdown 输出模板

```markdown
# 政策追踪报告

**生成时间**: {datetime}
**追踪关键词**: {keywords}
**时间范围**: 近{days}天

---

## 政策清单

### 1. [政策标题](链接)
- **来源**: {发布机构}
- **发布日期**: {日期}
- **摘要**: {摘要}

---

## 数据来源

| 来源 | 获取方式 | 数据条数 |
|------|----------|----------|
| 国务院 | 直接抓取 | 3 |
| 发改委 | WebSearch | 5 |
| 证监会 | MCP | 2 |
```

---

## 八、来源清单文件

详细的数据源URL和维护清单位于：

```
SOP/
├── 政策获取SOP.md              # 本文件
└── sources/
    ├── 国内政策来源清单.md       # 国内官方来源详细清单
    └── 国际政策来源清单.md       # 国际官方来源详细清单
```

> **注意**: 官方来源URL可能随时间变化，请定期检查并更新 `sources/` 目录下的清单文件。

---

## 九、测试要求

### 9.1 基础测试

```bash
# 测试直接来源抓取
python fetch_policy_data.py --source gov --days 7

# 测试关键词搜索
python fetch_policy_data.py --keyword "新能源" "半导体" --days 30

# 验证数据完整性
python -c "
from fetch_policy_data import POLICY_SOURCES
print(f'可用来源数: {len(POLICY_SOURCES)}')
for code, info in POLICY_SOURCES.items():
    print(f'  {code}: {info[\"name\"]}')"
```

### 9.2 验证清单

- [ ] 各官方来源可访问
- [ ] 页面结构解析正常
- [ ] 数据字段完整
- [ ] 时间戳准确

---

## 十、常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 官方来源无法访问 | 网站维护/防火墙 | 切换到WebSearch |
| 数据解析失败 | 页面结构变化 | 更新CSS选择器 |
| 结果为空 | 关键词不匹配 | 扩大关键词范围 |
| 时效性差 | 缓存延迟 | 直接来源+WebSearch组合 |

---

**注意**: 本SOP遵循获取优先级原则，优先使用MCP工具，官方来源作为Fallback，WebSearch作为最后补充。
