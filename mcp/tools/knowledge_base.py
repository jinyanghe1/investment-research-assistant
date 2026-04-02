#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识库管理工具集

提供研报列表查询与关键词搜索两大工具，
供 FastMCP Server 通过 register_tools(mcp) 挂载。
"""

import json
import os

# ── 路径约定 ─────────────────────────────────────────────
_MCP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WORKSPACE_ROOT = os.path.dirname(_MCP_ROOT)
_INDEX_JSON = os.path.join(_WORKSPACE_ROOT, "index.json")


def _read_index() -> list[dict]:
    """读取 index.json，不存在或解析失败则返回空列表。"""
    if not os.path.exists(_INDEX_JSON):
        return []
    try:
        with open(_INDEX_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("reports", [])
        return []
    except (json.JSONDecodeError, OSError):
        return []


def _slim_record(r: dict) -> dict:
    """精简单条研报记录，仅保留列表展示所需字段。"""
    return {
        "id": r.get("id", ""),
        "title": r.get("title", ""),
        "date": r.get("date", ""),
        "category": r.get("category", ""),
        "tags": r.get("tags", []),
        "summary": r.get("summary", ""),
        "path": r.get("filePath", r.get("path", "")),
    }


def register_tools(mcp):
    """将知识库管理工具集注册到 FastMCP 实例。"""

    # ─────────────────────────────────────────────────────
    # 工具 4: list_reports
    # ─────────────────────────────────────────────────────
    @mcp.tool
    def list_reports(
        category: str = "",
        limit: int = 50,
        sort_by: str = "date",
    ) -> dict:
        """列出知识库中的所有研报，支持分类筛选与排序。

        从 index.json 读取研报索引，可按分类过滤、按日期/标题/
        分类排序，并限制返回条数。

        Args:
            category: 按分类筛选（空则返回全部）
            limit: 返回最大条数（默认 50）
            sort_by: 排序方式 - date（日期倒序）、title、category

        Returns:
            包含 total 和 reports 列表的字典
        """
        try:
            reports = _read_index()

            # 分类过滤
            if category:
                category_lower = category.lower()
                reports = [
                    r for r in reports
                    if category_lower in r.get("category", "").lower()
                ]

            # 排序
            if sort_by == "date":
                reports.sort(key=lambda r: r.get("date", ""), reverse=True)
            elif sort_by == "title":
                reports.sort(key=lambda r: r.get("title", ""))
            elif sort_by == "category":
                reports.sort(key=lambda r: r.get("category", ""))

            total = len(reports)
            reports = reports[:limit]

            return {
                "total": total,
                "reports": [_slim_record(r) for r in reports],
            }

        except Exception as e:
            return {"status": "error", "message": str(e), "total": 0, "reports": []}

    # ─────────────────────────────────────────────────────
    # 工具 5: search_reports
    # ─────────────────────────────────────────────────────
    @mcp.tool
    def search_reports(
        query: str,
        search_fields: str = "title,tags,summary",
        limit: int = 20,
    ) -> dict:
        """关键词搜索研报，支持多字段匹配与相关性排序。

        对查询字符串按空格分词，在指定字段中进行不区分大小写的
        模糊匹配，并按匹配度（命中字段数 × 命中词数）降序排列。

        Args:
            query: 搜索关键词（支持空格分隔多词）
            search_fields: 搜索范围（逗号分隔，可选 title/tags/summary/category/author）
            limit: 返回最大条数（默认 20）

        Returns:
            包含 query, total, results 的字典
        """
        try:
            reports = _read_index()

            if not query or not query.strip():
                return {"query": query, "total": 0, "results": []}

            # 分词
            keywords = [kw.lower() for kw in query.strip().split() if kw.strip()]
            if not keywords:
                return {"query": query, "total": 0, "results": []}

            fields = [f.strip().lower() for f in search_fields.split(",") if f.strip()]

            scored_results: list[tuple[int, dict]] = []

            for r in reports:
                score = 0
                for field in fields:
                    field_value = _get_field_text(r, field)
                    if not field_value:
                        continue
                    field_lower = field_value.lower()
                    for kw in keywords:
                        if kw in field_lower:
                            score += 1

                if score > 0:
                    scored_results.append((score, r))

            # 按匹配度降序排列
            scored_results.sort(key=lambda x: x[0], reverse=True)
            scored_results = scored_results[:limit]

            return {
                "query": query,
                "total": len(scored_results),
                "results": [_slim_record(r) for _, r in scored_results],
            }

        except Exception as e:
            return {"status": "error", "message": str(e), "query": query, "total": 0, "results": []}


def _get_field_text(record: dict, field: str) -> str:
    """从研报记录中提取指定字段的文本值。"""
    if field == "tags":
        tags = record.get("tags", [])
        if isinstance(tags, list):
            return " ".join(str(t) for t in tags)
        return str(tags)
    if field == "path":
        return record.get("filePath", record.get("path", ""))
    value = record.get(field, "")
    return str(value) if value else ""
