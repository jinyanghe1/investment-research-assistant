# MCP 配置与工具链说明

本目录包含将投研助手工具链封装为 MCP（Model Context Protocol）Server 的配置与文档。

## 可用 Tools

| Tool 名称 | 描述 | 对应脚本 |
|-----------|------|----------|
| `fetch_index_data` | 抓取A股主要指数日线数据（沪深300、创业板指、上证指数） | `tools/fetch_index_data.py` |
| `init_report` | 初始化新研报项目，生成基于模板的HTML文件夹 | `tools/init_report.py` |
| `update_index_json` | 将新研报元数据注册到 `index.json` | `tools/update_index_json.py` |

## 本地使用方式

### 方式一：直接运行 Python 脚本

```bash
# 抓取指数数据
python3 tools/fetch_index_data.py --index hs300,cy --output data/ --days 180

# 初始化研报
python3 tools/init_report.py --title "铜产业链2026Q2展望" --author "投研AI中枢"

# 注册到知识库
python3 tools/update_index_json.py \
  --id "RPT-2026-002" \
  --title "铜产业链2026Q2展望" \
  --category "微观" \
  --tags "铜,大宗商品,供给侧" \
  --filepath "reports/20260402_铜产业链2026Q2展望/index.html"
```

### 方式二：通过 MCP Server 调用

将 `.mcp.json` 中的配置集成到你的 Claude Code 插件环境中，即可在对话中直接调用上述工具。

## `.mcp.json` 结构

根目录下的 `.mcp.json` 定义了本地 stdio MCP Server 的入口。所有工具脚本通过统一的 Python wrapper `mcp/server.py` 暴露为 MCP 工具。

```json
{
  "mcpServers": {
    "investment-research": {
      "command": "python3",
      "args": ["mcp/server.py"],
      "env": {}
    }
  }
}
```

## 扩展 Tools

如需新增工具：
1. 在 `tools/` 下编写独立脚本（带命令行参数）。
2. 在 `mcp/server.py` 中注册对应的 tool schema 和 handler。
3. 更新本 `README.md` 的可用 Tools 表格。
