#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投研助手 MCP Server - 全链路投研工具集

提供行情数据、宏观分析、公司研究、研报生成、知识库管理等工具。
基于 FastMCP 3.x 构建，支持 stdio / SSE 传输。

启动方式:
    python server.py                   # stdio 模式（Claude Desktop 用）
    fastmcp run server.py              # 开发调试
    python -m server                   # 作为模块运行
"""

import sys
from pathlib import Path

from fastmcp import FastMCP

# ── 创建 MCP Server 实例 ──────────────────────────────────────────
mcp = FastMCP(
    "投研助手",
)

# ── 导入并注册所有工具模块 ──────────────────────────────────────────
# 支持两种 import 路径：
#   1. 从 research_mcp/ 目录直接运行（python server.py）
#   2. 从上级目录运行（python -m research_mcp.server）

def _register_all_tools():
    """导入各工具模块并注册到 mcp 实例"""
    tool_modules = [
        "market_data",
        "macro_data",
        "company_analysis",
        "fundamental_analysis",
        "report_generator",
        "knowledge_base",
        "technical_analysis",
        "futures_data",
    ]

    for module_name in tool_modules:
        try:
            # 方式1: 从上级目录运行（使用 research_mcp.tools 前缀）
            mod = __import__(f"research_mcp.tools.{module_name}", fromlist=["register_tools"])
        except ImportError:
            try:
                # 方式2: 从 research_mcp/ 目录内运行
                mod = __import__(f"tools.{module_name}", fromlist=["register_tools"])
            except ImportError:
                print(f"[投研助手] 跳过未实现的工具模块: {module_name}", file=sys.stderr)
                continue

        if hasattr(mod, "register_tools"):
            mod.register_tools(mcp)
            print(f"[投研助手] 已注册工具模块: {module_name}", file=sys.stderr)
        else:
            print(f"[投研助手] 模块 {module_name} 缺少 register_tools 函数", file=sys.stderr)


_register_all_tools()


# ── 内置健康检查工具 ──────────────────────────────────────────────
@mcp.tool()
def ping() -> str:
    """健康检查：返回服务器状态和已注册工具列表"""
    return "🟢 投研助手 MCP Server 运行中 | 版本 1.0.0"


@mcp.tool()
def list_available_tools() -> str:
    """列出所有可用的投研工具及其说明"""
    tool_categories = {
        "📈 行情数据": ["get_stock_quote", "get_index_data", "get_futures_quote"],
        "🏛️ 宏观分析": ["get_macro_indicator", "get_policy_summary", "get_economic_calendar"],
        "🏢 公司研究": ["get_company_financials", "get_company_profile", "get_industry_chain"],
        "📝 研报生成": ["generate_report", "init_report_project"],
        "📚 知识库": ["search_reports", "update_index", "get_report_meta"],
        "🔧 系统": ["ping", "list_available_tools"],
    }
    lines = ["# 投研助手 - 可用工具清单\n"]
    for category, tools in tool_categories.items():
        lines.append(f"\n## {category}")
        for t in tools:
            lines.append(f"  - `{t}`")
    return "\n".join(lines)


# ── 入口 ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")
