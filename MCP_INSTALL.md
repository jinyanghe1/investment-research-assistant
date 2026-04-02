# MCP 安装与配置指南

> 版本：v1.0
> 更新日期：2026-04-02
> 支持平台：Claude Code · Claude Desktop · Kimi · Copilot

---

## 一、概述

投研助手 MCP Server 基于 FastMCP 3.x 构建，提供：

- 📈 **行情数据**：股票、指数、期货实时/历史数据
- 🏛️ **宏观分析**：GDP、CPI、PMI、政策追踪
- 🏢 **公司研究**：财务报表、估值分析、产业链
- 📝 **研报生成**：专业HTML研报自动生成
- 📚 **知识库**：研报索引管理与全文检索
- 🔧 **技术分析**：K线形态、均线系统、技术指标

---

## 二、通用安装步骤

### 2.1 安装依赖

```bash
cd /Users/hejinyang/投研助手/mcp
pip install -r requirements.txt
```

主要依赖：
- `fastmcp>=3.0.0` - MCP Server框架
- `akshare>=1.13.0` - 金融数据（宏观、期货）
- `yfinance>=0.2.40` - 行情数据（A股首选）
- `pandas>=2.0.0` - 数据处理
- `requests>=2.31.0` - HTTP请求

### 2.2 验证安装

```bash
cd /Users/hejinyang/投研助手
python3 -m mcp.server --test
# 或
python3 mcp/server.py --help
```

---

## 三、Claude Code 配置

### 3.1 项目级配置（推荐）

项目根目录 `.mcp.json` 已配置好，直接使用：

```json
{
  "mcpServers": {
    "投研助手": {
      "command": "python3",
      "args": ["-m", "mcp.server"],
      "cwd": "/Users/hejinyang/投研助手",
      "env": {
        "PYTHONPATH": "/Users/hejinyang/投研助手"
      }
    }
  }
}
```

Claude Code 会自动读取项目根目录的 `.mcp.json` 并加载 MCP Server。

### 3.2 全局配置（Claude Desktop）

编辑 `~/.claude/settings/claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "投研助手": {
      "command": "python3",
      "args": ["/Users/hejinyang/投研助手/mcp/server.py"],
      "env": {
        "PYTHONPATH": "/Users/hejinyang/投研助手"
      }
    }
  }
}
```

### 3.3 验证 Claude Code MCP

```bash
# 在项目目录中启动 Claude Code
cd /Users/hejinyang/投研助手
claude

# 测试 MCP 连接
claude -p "列出可用的MCP工具"
```

---

## 四、Kimi MCP 配置

### 4.1 Kimi MCP 简介

Kimi 支持通过标准 MCP 协议连接外部工具服务器。

### 4.2 安装步骤

1. **确认 Kimi MCP 支持**
   - Kimi桌面应用 → 设置 → MCP Server
   - 或通过 Kimi API 配置

2. **配置 Kimi MCP**
   在 Kimi 的 MCP 设置中添加：

   ```json
   {
     "mcpServers": {
       "投研助手": {
         "command": "python3",
         "args": [
           "-m",
           "mcp.server"
         ],
         "cwd": "/Users/hejinyang/投研助手",
         "env": {
           "PYTHONPATH": "/Users/hejinyang/投研助手"
         }
       }
     }
   }
   ```

3. **使用 SSE 模式（如果 Kimi 需要）**

   ```bash
   # 启动 SSE 模式
   python3 -m mcp.server --sse --port 8765
   ```

   然后在 Kimi 中配置 SSE 端点：`http://localhost:8765/sse`

### 4.3 验证

```bash
# 测试 Server 是否运行
curl http://localhost:8765/health
```

---

## 五、Copilot MCP 配置

### 5.1 Copilot MCP 支持

GitHub Copilot 和 Copilot Studio 支持 MCP 协议扩展。

### 5.2 VS Code 配置

1. **安装 Copilot MCP 扩展**
   - 搜索 "MCP" 扩展
   - 安装 "Model Context Protocol" 相关扩展

2. **配置 `settings.json`**
   ```json
   {
     "mcp": {
       "servers": {
         "投研助手": {
           "command": "python3",
           "args": ["-m", "mcp.server"],
           "cwd": "/Users/hejinyang/投研助手",
           "env": {
             "PYTHONPATH": "/Users/hejinyang/投研助手"
           }
         }
       }
     }
   }
   ```

### 5.3 Copilot CLI 配置

```bash
# 安装 Copilot MCP CLI (如果可用)
# 然后配置
copilot mcp add 投研助手 -c python3 -a "-m mcp.server"
```

### 5.4 GitHub Copilot Labs (旧版)

如果使用 GitHub Copilot Labs：

1. 打开 Copilot Labs
2. 选择 "Custom Tools" 或 "MCP Servers"
3. 添加服务器地址：`http://localhost:8765`

---

## 六、动态更新机制

### 6.1 自动更新脚本

项目提供了 `scripts/update-mcp.sh` 用于动态更新 MCP 配置：

```bash
cd /Users/hejinyang/投研助手
./scripts/update-mcp.sh
```

### 6.2 手动更新工具列表

当新增工具模块时，需要更新：

1. **`.mcp.json`** - 添加工具模块到 `metadata.tools`

2. **`mcp/server.py`** - 在 `_register_all_tools()` 中添加新模块

3. **`MCP_INSTALL.md`** - 在工具清单中记录

### 6.3 更新后验证

```bash
# 重启 MCP Server 后验证
cd /Users/hejinyang/投研助手
python3 -m mcp.server &
sleep 2
curl -X POST http://localhost:8765/tools -H "Content-Type: application/json"
```

---

## 七、启动模式

### 7.1 stdio 模式（默认）

```bash
# 直接运行
python3 -m mcp.server

# 或
python3 mcp/server.py
```

### 7.2 SSE 模式（HTTP）

```bash
# 启动 SSE 服务器
python3 -m mcp.server --sse --port 8765

# 或使用 FastMCP CLI
fastmcp run server.py --transport sse --port 8765
```

### 7.3 开发调试模式

```bash
# 使用 FastMCP 开发服务器
cd /Users/hejinyang/投研助手/mcp
fastmcp dev server.py
```

---

## 八、故障排除

### 8.1 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `Module not found: tools.xxx` | PYTHONPATH 未设置 | 设置 `PYTHONPATH=/Users/hejinyang/投研助手` |
| `fastmcp: command not found` | 未安装 fastmcp | `pip install fastmcp` |
| 连接超时 | 端口被占用 | 检查8765端口或更换端口 |
| 工具列表为空 | 模块导入失败 | 检查依赖是否完整安装 |

### 8.2 日志查看

```bash
# 查看 MCP Server 日志
tail -f /tmp/mcp-server.log

# 或使用 stderr 重定向
python3 -m mcp.server 2>&1 | tee /tmp/mcp-server.log
```

### 8.3 依赖检查

```bash
cd /Users/hejinyang/投研助手/mcp
python3 -c "
import fastmcp
import akshare
import yfinance
import pandas
print('All dependencies OK')
print(f'FastMCP: {fastmcp.__version__}')
"
```

---

## 九、快速参考

### 9.1 文件位置

| 文件 | 说明 |
|------|------|
| `.mcp.json` | Claude Code 项目级配置 |
| `mcp/server.py` | MCP Server 主入口 |
| `mcp/tools/*.py` | 各工具模块 |
| `mcp/README.md` | MCP 工具文档 |
| `scripts/update-mcp.sh` | 动态更新脚本 |

### 9.2 可用工具

| 类别 | 工具数 | 主要工具 |
|------|--------|----------|
| 行情数据 | 3 | get_stock_quote, get_index_data, get_futures_quote |
| 宏观分析 | 3 | get_macro_indicator, get_policy_summary, get_economic_calendar |
| 公司研究 | 3 | get_company_financials, get_company_profile, get_industry_chain |
| 研报生成 | 2 | generate_report, init_report_project |
| 知识库 | 3 | search_reports, update_index, get_report_meta |
| 系统 | 2 | ping, list_available_tools |

### 9.3 命令速查

```bash
# 启动 stdio 模式
python3 -m mcp.server

# 启动 SSE 模式
python3 -m mcp.server --sse --port 8765

# 开发调试
fastmcp dev mcp/server.py

# 测试安装
python3 -c "from mcp.server import mcp; print('OK')"
```

---

**维护说明**：
- 随着项目开发，工具模块可能增加
- 更新后请运行 `scripts/update-mcp.sh` 同步配置
- 详细工具文档见 `mcp/README.md`
