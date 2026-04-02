# 投研助手 MCP Server

> AI驱动的全链路投研工具集 — 行情数据 · 宏观分析 · 公司研究 · 研报生成 · 知识库管理

基于 [FastMCP 3.x](https://github.com/jlowin/fastmcp) 构建的 Model Context Protocol (MCP) Server，为 Claude Desktop 及其他 MCP 客户端提供专业金融投研能力。

## 快速开始

### 1. 安装依赖

```bash
cd mcp/
pip install -r requirements.txt
```

### 2. 启动方式

```bash
# 方式一：直接运行（stdio 模式，适配 Claude Desktop）
python server.py

# 方式二：使用 FastMCP CLI（开发调试）
fastmcp run server.py

# 方式三：作为 Python 模块（从上级目录）
cd .. && python -m mcp.server
```

### 3. Claude Desktop 配置

在 Claude Desktop 的 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "投研助手": {
      "command": "python3",
      "args": ["/Users/hejinyang/投研助手/mcp/server.py"],
      "env": {}
    }
  }
}
```

或在 Claude Code 项目根目录 `.mcp.json` 中配置：

```json
{
  "mcpServers": {
    "投研助手": {
      "command": "python3",
      "args": ["mcp/server.py"],
      "cwd": "."
    }
  }
}
```

## 工具清单

### 📈 行情数据 (market_data)

| 工具名称 | 说明 | 主要参数 |
|---------|------|---------|
| `get_stock_quote` | 获取个股实时/历史行情 | `symbol`, `period` |
| `get_index_data` | 获取A股主要指数数据 | `index_code`, `days` |
| `get_futures_quote` | 获取期货品种行情 | `symbol`, `exchange` |

### 🏛️ 宏观分析 (macro_data)

| 工具名称 | 说明 | 主要参数 |
|---------|------|---------|
| `get_macro_indicator` | 获取宏观经济指标 (GDP/CPI/PMI等) | `indicator`, `period` |
| `get_policy_summary` | 获取重要政策/会议纪要摘要 | `topic`, `date_range` |
| `get_economic_calendar` | 获取经济数据日历 | `days_ahead` |

### 🏢 公司研究 (company_analysis)

| 工具名称 | 说明 | 主要参数 |
|---------|------|---------|
| `get_company_financials` | 获取上市公司财务数据 | `symbol`, `report_type` |
| `get_company_profile` | 获取公司基本面画像 | `symbol` |
| `get_industry_chain` | 获取产业链上下游分析 | `industry`, `depth` |

### 📝 研报生成 (report_generator)

| 工具名称 | 说明 | 主要参数 |
|---------|------|---------|
| `generate_report` | 生成专业HTML研报 | `title`, `content`, `category` |
| `init_report_project` | 初始化研报项目目录 | `title`, `author` |

### 📚 知识库管理 (knowledge_base)

| 工具名称 | 说明 | 主要参数 |
|---------|------|---------|
| `search_reports` | 全文检索已有研报 | `query`, `category` |
| `update_index` | 更新研报索引 (index.json) | `report_meta` |
| `get_report_meta` | 获取研报元数据 | `report_id` |

### 🔧 系统工具

| 工具名称 | 说明 |
|---------|------|
| `ping` | 健康检查 |
| `list_available_tools` | 列出所有可用工具 |

## 示例对话

以下展示用户如何通过自然语言触发 MCP 工具：

```
用户: 帮我查一下沪深300最近30天的走势
→ 触发 get_index_data(index_code="hs300", days=30)

用户: 看看最新的CPI和PPI数据
→ 触发 get_macro_indicator(indicator="CPI") + get_macro_indicator(indicator="PPI")

用户: 分析一下宁德时代的财务状况
→ 触发 get_company_financials(symbol="300750") + get_company_profile(symbol="300750")

用户: 帮我写一篇关于铜产业链的研报
→ 触发 init_report_project(title="铜产业链分析") → 触发 generate_report(...)

用户: 搜索之前写过的关于新能源的报告
→ 触发 search_reports(query="新能源")
```

## 项目结构

```
mcp/
├── server.py              # MCP Server 主入口
├── requirements.txt       # Python 依赖
├── .mcp.json              # MCP 配置元数据
├── README.md              # 本文档
├── tools/                 # 工具模块
│   ├── __init__.py
│   ├── market_data.py     # 行情数据工具
│   ├── macro_data.py      # 宏观分析工具
│   ├── company_analysis.py# 公司研究工具
│   ├── report_generator.py# 研报生成工具
│   └── knowledge_base.py  # 知识库管理工具
├── utils/                 # 辅助模块
│   ├── __init__.py
│   ├── cache.py           # 数据缓存系统
│   └── formatters.py      # 格式化工具
├── templates/             # HTML 模板
│   └── report_base.html   # 研报基础模板
└── data/                  # 数据与缓存目录
    └── cache/             # 缓存文件（自动生成）
```

## 开发指南

### 新增工具模块

每个工具模块遵循统一的注册模式：

```python
# tools/my_new_tool.py
"""我的新工具模块"""

def register_tools(mcp):
    """注册工具到 MCP Server"""

    @mcp.tool()
    def my_tool(param1: str, param2: int = 10) -> str:
        """工具说明 - 会展示给AI作为工具描述"""
        # 实现逻辑
        return "结果"
```

### 使用缓存

```python
from utils.cache import get_cache, TTL_MARKET, TTL_MACRO

cache = get_cache()

# 写入缓存
cache.set("stock:600519", {"price": 1888.88})

# 读取缓存（5分钟过期）
data = cache.get("stock:600519", ttl_seconds=TTL_MARKET)
```

### 使用格式化工具

```python
from utils.formatters import format_number, format_change, df_to_markdown_table

format_number(123456789)     # "1.23亿"
format_change(2.35)          # "+2.35%"
format_change(-1.20)         # "-1.20%"
df_to_markdown_table(df)     # Markdown 表格字符串
```

## 技术栈

- **MCP 框架**: FastMCP 3.x
- **数据源**: akshare（A股数据）、yfinance（全球市场）
- **数据处理**: pandas
- **运行环境**: Python 3.10+

## 许可

内部工具，仅供研究使用。
