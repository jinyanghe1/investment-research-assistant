#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
研报生成工具集

提供 Markdown→HTML 研报生成、数据表格构建、知识库注册三大核心工具，
供 FastMCP Server 通过 register_tools(mcp) 挂载。
"""

import json
import os
import sys
import re
import fcntl
import hashlib
from datetime import datetime, timezone

_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _base not in sys.path:
    sys.path.insert(0, _base)

from config import config
from utils.errors import handle_errors, MCPToolError, ErrorCode

# ── 路径约定 ─────────────────────────────────────────────
_TEMPLATE_DIR = os.path.join(config.mcp_root, "templates")

# ── 内置 Fallback 模板 ──────────────────────────────────
DEFAULT_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{TITLE}} - 投研助手</title>
<style>
  /* ── Reset & Base ─────────────────────────────────── */
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html { font-size: 15px; scroll-behavior: smooth; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                 "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    background: #0b1120; color: #c9d1d9; line-height: 1.75;
    display: flex; flex-direction: column; min-height: 100vh;
  }

  /* ── Top Bar ──────────────────────────────────────── */
  .topbar {
    background: linear-gradient(135deg, #0d1b3e 0%, #162447 100%);
    border-bottom: 1px solid #1f3461;
    padding: 12px 32px; display: flex; align-items: center;
    justify-content: space-between; position: sticky; top: 0; z-index: 100;
  }
  .topbar a.home {
    color: #58a6ff; text-decoration: none; font-size: 0.9rem;
    display: flex; align-items: center; gap: 6px;
  }
  .topbar a.home:hover { text-decoration: underline; }
  .topbar .meta-inline {
    font-size: 0.8rem; color: #8b949e;
    display: flex; gap: 16px; flex-wrap: wrap;
  }

  /* ── Layout ───────────────────────────────────────── */
  .page-wrapper {
    display: flex; flex: 1; max-width: 1400px;
    width: 100%; margin: 0 auto;
  }

  /* ── TOC Sidebar ──────────────────────────────────── */
  .toc-sidebar {
    width: 240px; min-width: 200px; padding: 28px 16px;
    border-right: 1px solid #1f3461; position: sticky;
    top: 52px; height: calc(100vh - 52px); overflow-y: auto;
    background: #0d1424;
  }
  .toc-sidebar h4 {
    color: #79c0ff; font-size: 0.85rem; margin-bottom: 12px;
    text-transform: uppercase; letter-spacing: 1px;
    font-weight: 600;
  }
  .toc-sidebar ul { list-style: none; }
  .toc-sidebar li { margin-bottom: 6px; }
  .toc-sidebar a {
    color: #c9d1d9; text-decoration: none; font-size: 0.82rem;
    display: block; padding: 3px 8px; border-radius: 4px;
    transition: all 0.2s;
  }
  .toc-sidebar a:hover { color: #79c0ff; background: rgba(88,166,255,0.1); }
  .toc-sidebar .toc-h3 { padding-left: 20px; font-size: 0.78rem; }

  /* ── Main Content ─────────────────────────────────── */
  .content-area {
    flex: 1; padding: 36px 48px; max-width: 900px;
  }

  /* ── Header Block ─────────────────────────────────── */
  .report-header {
    margin-bottom: 36px; padding-bottom: 24px;
    border-bottom: 2px solid #1f3461;
  }
  .report-header h1 {
    font-size: 1.85rem; color: #e6edf3; font-weight: 700;
    margin-bottom: 12px; line-height: 1.35;
  }
  .report-header .meta {
    display: flex; gap: 20px; flex-wrap: wrap;
    font-size: 0.82rem; color: #8b949e;
  }
  .report-header .meta span { display: flex; align-items: center; gap: 4px; }
  .report-header .tags { margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap; }
  .report-header .tag {
    background: rgba(88,166,255,0.12); color: #58a6ff;
    padding: 2px 10px; border-radius: 12px; font-size: 0.75rem;
  }

  /* ── Typography ───────────────────────────────────── */
  .report-body h2 {
    font-size: 1.4rem; color: #58a6ff; margin: 32px 0 14px;
    padding-bottom: 8px; border-bottom: 1px solid #1f3461;
  }
  .report-body h3 {
    font-size: 1.15rem; color: #79c0ff; margin: 24px 0 10px;
  }
  .report-body h4 { font-size: 1rem; color: #a5d6ff; margin: 18px 0 8px; }
  .report-body p { margin: 10px 0; text-align: justify; }
  .report-body strong { color: #e6edf3; }
  .report-body em { color: #d2a8ff; font-style: italic; }
  .report-body a { color: #58a6ff; text-decoration: none; }
  .report-body a:hover { text-decoration: underline; }

  /* ── Lists ────────────────────────────────────────── */
  .report-body ul, .report-body ol {
    margin: 10px 0 10px 24px;
  }
  .report-body li { margin-bottom: 4px; }

  /* ── Blockquote ───────────────────────────────────── */
  .report-body blockquote {
    border-left: 3px solid #58a6ff; margin: 16px 0;
    padding: 10px 18px; background: rgba(88,166,255,0.06);
    color: #a0b4cc; border-radius: 0 6px 6px 0;
  }

  /* ── Table ────────────────────────────────────────── */
  .report-body table {
    width: 100%; border-collapse: collapse; margin: 18px 0;
    font-size: 0.9rem; border: 1px solid #1f3461;
    border-radius: 8px; overflow: hidden;
  }
  .report-body thead th {
    background: linear-gradient(180deg, #1a2744 0%, #0d1b3e 100%);
    color: #79c0ff; font-weight: 600;
    padding: 10px 14px; text-align: left;
    border-bottom: 2px solid #1f3461;
  }
  .report-body tbody td {
    padding: 8px 14px; border-bottom: 1px solid #21262d;
    color: #c9d1d9;
  }
  .report-body tbody tr:nth-child(even) { background: rgba(88, 166, 255, 0.03); }
  .report-body tbody tr:hover { background: rgba(88, 166, 255, 0.08); }

  /* ── Code Block ───────────────────────────────────── */
  .report-body pre {
    background: #161b22; border: 1px solid #30363d;
    border-radius: 6px; padding: 16px; overflow-x: auto;
    margin: 14px 0; font-size: 0.85rem;
  }
  .report-body code {
    font-family: "SF Mono", "Fira Code", Consolas, monospace;
    color: #79c0ff;
  }
  .report-body p code, .report-body li code {
    background: #161b22; padding: 2px 6px; border-radius: 4px;
    font-size: 0.88em;
  }

  /* ── Horizontal Rule ──────────────────────────────── */
  .report-body hr {
    border: none; border-top: 1px solid #21262d; margin: 28px 0;
  }

  /* ── Footer ───────────────────────────────────────── */
  .footer-disclaimer {
    background: #0d1117; border-top: 1px solid #1f3461;
    padding: 24px 48px; font-size: 0.75rem; color: #484f58;
    text-align: center; line-height: 1.6;
  }

  /* ── Chart Placeholder ───────────────────────────── */
  .chart-placeholder {
    background: linear-gradient(135deg, #0d1b3e 0%, #162447 100%);
    border: 2px dashed #1f3461;
    border-radius: 8px;
    padding: 40px 20px;
    margin: 20px 0;
    text-align: center;
    color: #58a6ff;
    font-size: 0.9rem;
  }
  .chart-placeholder .icon {
    font-size: 2.5rem;
    margin-bottom: 12px;
    opacity: 0.7;
  }
  .chart-placeholder .hint {
    color: #8b949e;
    font-size: 0.8rem;
    margin-top: 8px;
  }

  /* ── Risk Section ─────────────────────────────────── */
  .risk-section {
    background: rgba(239, 68, 68, 0.05);
    border: 1px solid rgba(239, 68, 68, 0.2);
    border-radius: 8px;
    padding: 20px;
    margin: 24px 0;
  }
  .risk-section h3 {
    color: #ef4444;
    margin-top: 0;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .risk-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 12px 0;
    border-bottom: 1px solid rgba(239, 68, 68, 0.1);
  }
  .risk-item:last-child { border-bottom: none; }
  .risk-item .level {
    flex-shrink: 0;
    padding: 2px 10px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
  }
  .risk-item .level.high { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
  .risk-item .level.medium { background: rgba(245, 158, 11, 0.2); color: #f59e0b; }
  .risk-item .level.low { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
  .risk-item .desc { flex: 1; color: #c9d1d9; font-size: 0.9rem; }

  /* ── Peer Comparison Table ────────────────────────── */
  .peer-comparison-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    margin: 18px 0;
    font-size: 0.88rem;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #1f3461;
  }
  .peer-comparison-table thead th {
    background: linear-gradient(180deg, #1a2744 0%, #0d1b3e 100%);
    color: #58a6ff;
    font-weight: 600;
    padding: 12px 14px;
    text-align: center;
    border-bottom: 2px solid #1f3461;
  }
  .peer-comparison-table thead th:first-child {
    text-align: left;
    background: linear-gradient(180deg, #162447 0%, #0d1b3e 100%);
  }
  .peer-comparison-table tbody td {
    padding: 10px 14px;
    border-bottom: 1px solid #21262d;
    text-align: center;
  }
  .peer-comparison-table tbody td:first-child {
    text-align: left;
    font-weight: 500;
    color: #e6edf3;
    background: rgba(13, 27, 62, 0.3);
  }
  .peer-comparison-table tbody tr:nth-child(even) { background: rgba(88, 166, 255, 0.03); }
  .peer-comparison-table tbody tr:hover { background: rgba(88, 166, 255, 0.08); }
  .peer-comparison-table .highlight { color: #58a6ff; font-weight: 600; }
  .peer-comparison-table .positive { color: #22c55e; }
  .peer-comparison-table .negative { color: #ef4444; }

  /* ── Analyst Info Bar ─────────────────────────────── */
  .analyst-bar {
    background: rgba(88, 166, 255, 0.05);
    border: 1px solid rgba(88, 166, 255, 0.15);
    border-radius: 8px;
    padding: 16px 20px;
    margin: 20px 0;
    display: flex;
    align-items: center;
    gap: 20px;
    flex-wrap: wrap;
  }
  .analyst-bar .avatar {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: linear-gradient(135deg, #58a6ff 0%, #3b82f6 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    flex-shrink: 0;
  }
  .analyst-bar .info { flex: 1; min-width: 200px; }
  .analyst-bar .name {
    color: #e6edf3;
    font-weight: 600;
    font-size: 1rem;
  }
  .analyst-bar .title {
    color: #8b949e;
    font-size: 0.8rem;
    margin-top: 2px;
  }
  .analyst-bar .credentials {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }
  .analyst-bar .credential {
    background: rgba(88, 166, 255, 0.1);
    color: #58a6ff;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 0.75rem;
  }

  /* ── Enhanced Footer Disclaimer ───────────────────── */
  .footer-enhanced {
    background: linear-gradient(180deg, #0d1117 0%, #0b1120 100%);
    border-top: 2px solid #1f3461;
    padding: 32px 48px;
    margin-top: 40px;
  }
  .footer-enhanced .disclaimer-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 20px;
    max-width: 1200px;
    margin: 0 auto;
  }
  .footer-enhanced .disclaimer-box {
    background: rgba(13, 17, 23, 0.8);
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 16px;
  }
  .footer-enhanced .disclaimer-box h4 {
    color: #f59e0b;
    font-size: 0.8rem;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .footer-enhanced .disclaimer-box p {
    color: #484f58;
    font-size: 0.75rem;
    line-height: 1.7;
  }
  .footer-enhanced .copyright {
    text-align: center;
    margin-top: 24px;
    padding-top: 20px;
    border-top: 1px solid #21262d;
    color: #484f58;
    font-size: 0.75rem;
  }

  /* ── Responsive ───────────────────────────────────── */
  @media (max-width: 900px) {
    .toc-sidebar { display: none; }
    .content-area { padding: 24px 18px; }
    .footer-disclaimer { padding: 18px; }
  }
  @media (max-width: 600px) {
    .report-header h1 { font-size: 1.3rem; }
    .topbar { padding: 10px 16px; }
  }
</style>
</head>
<body>

<!-- Top Bar -->
<div class="topbar">
  <a class="home" href="../index.html">← 返回知识库首页</a>
  <div class="meta-inline">
    <span>{{AUTHOR}}</span>
    <span>{{DATE}}</span>
    <span>{{CATEGORY}}</span>
  </div>
</div>

<!-- Page Layout -->
<div class="page-wrapper">

  <!-- TOC Sidebar -->
  <nav class="toc-sidebar">
    <h4>目录导航</h4>
    {{TOC}}
  </nav>

  <!-- Main Content -->
  <main class="content-area">
    <header class="report-header">
      <h1>{{TITLE}}</h1>
      <div class="meta">
        <span>📝 {{AUTHOR}}</span>
        <span>📅 {{DATE}}</span>
        <span>📂 {{CATEGORY}}</span>
      </div>
      <div class="tags">{{TAGS_HTML}}</div>
    </header>

    <article class="report-body">
      {{CONTENT}}
    </article>
  </main>
</div>

<!-- Enhanced Footer with Disclaimer -->
<footer class="footer-enhanced">
  <div class="disclaimer-grid">
    <div class="disclaimer-box">
      <h4>⚠️ 风险提示</h4>
      <p>本研报由投研AI助手自动生成，仅供内部参考，不构成任何投资建议。市场有风险，投资需谨慎。</p>
    </div>
    <div class="disclaimer-box">
      <h4>📋 数据声明</h4>
      <p>报告中的数据、观点和结论可能存在偏差或延迟，使用者应自行核实数据源并独立判断。</p>
    </div>
    <div class="disclaimer-box">
      <h4>⚖️ 责任限制</h4>
      <p>据此操作所产生的风险由使用者自行承担。作者及平台不对因使用本报告而产生的任何损失负责。</p>
    </div>
  </div>
  <div class="copyright">
    <p>© {{YEAR}} 投研助手 · AI投研中枢 · 内部研究资料 · 禁止外传</p>
  </div>
</footer>

</body>
</html>"""


# ═══════════════════════════════════════════════════════════
# Markdown → HTML 转换器（手动实现，零外部依赖）
# ═══════════════════════════════════════════════════════════

def _md_to_html(md: str) -> str:
    """将 Markdown 文本转换为 HTML 片段。"""
    lines = md.split("\n")
    html_parts: list[str] = []
    i = 0
    n = len(lines)

    def _inline(text: str) -> str:
        """处理行内元素：粗体、斜体、行内代码、链接。"""
        # 行内代码（优先处理，避免内部被其他规则破坏）
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        # 链接
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
        # 粗体
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        # 斜体
        text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
        return text

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # ── 空行 → 跳过 ──
        if not stripped:
            i += 1
            continue

        # ── 代码块 ``` ──
        if stripped.startswith("```"):
            lang = stripped[3:].strip()
            code_lines: list[str] = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            code_text = "\n".join(code_lines)
            code_text = code_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            cls = f' class="language-{lang}"' if lang else ""
            html_parts.append(f"<pre><code{cls}>{code_text}</code></pre>")
            continue

        # ── 标题 # ──
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            text = _inline(heading_match.group(2))
            slug = re.sub(r"<[^>]+>", "", text)
            slug = re.sub(r"[^\w\u4e00-\u9fff]+", "-", slug).strip("-").lower()
            html_parts.append(f'<h{level} id="{slug}">{text}</h{level}>')
            i += 1
            continue

        # ── 水平线 ──
        if re.match(r"^[-*_]{3,}$", stripped):
            html_parts.append("<hr>")
            i += 1
            continue

        # ── 引用块 > ──
        if stripped.startswith(">"):
            bq_lines: list[str] = []
            while i < n and lines[i].strip().startswith(">"):
                bq_lines.append(_inline(lines[i].strip().lstrip(">").strip()))
                i += 1
            html_parts.append("<blockquote>" + "<br>".join(bq_lines) + "</blockquote>")
            continue

        # ── 表格 ──
        if "|" in stripped and i + 1 < n and re.match(r"^\s*\|?\s*[-:]+", lines[i + 1].strip()):
            table_lines: list[str] = []
            while i < n and "|" in lines[i]:
                table_lines.append(lines[i].strip())
                i += 1
            html_parts.append(_parse_table(table_lines))
            continue

        # ── 无序列表 ──
        if re.match(r"^[-*+]\s+", stripped):
            items: list[str] = []
            while i < n and re.match(r"^\s*[-*+]\s+", lines[i]):
                items.append(_inline(re.sub(r"^\s*[-*+]\s+", "", lines[i])))
                i += 1
            html_parts.append("<ul>" + "".join(f"<li>{it}</li>" for it in items) + "</ul>")
            continue

        # ── 有序列表 ──
        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while i < n and re.match(r"^\s*\d+\.\s+", lines[i]):
                items.append(_inline(re.sub(r"^\s*\d+\.\s+", "", lines[i])))
                i += 1
            html_parts.append("<ol>" + "".join(f"<li>{it}</li>" for it in items) + "</ol>")
            continue

        # ── 普通段落 ──
        para_lines: list[str] = []
        while i < n and lines[i].strip() and not _is_block_start(lines[i]):
            para_lines.append(lines[i].strip())
            i += 1
        if para_lines:
            html_parts.append("<p>" + _inline(" ".join(para_lines)) + "</p>")

    return "\n".join(html_parts)


def _is_block_start(line: str) -> bool:
    """判断某行是否为块级元素起始。"""
    s = line.strip()
    if not s:
        return True
    if s.startswith("#"):
        return True
    if s.startswith("```"):
        return True
    if s.startswith(">"):
        return True
    if re.match(r"^[-*_]{3,}$", s):
        return True
    if re.match(r"^[-*+]\s+", s):
        return True
    if re.match(r"^\d+\.\s+", s):
        return True
    if "|" in s and s.startswith("|"):
        return True
    return False


def _parse_table(table_lines: list[str]) -> str:
    """将 Markdown 表格行转为 HTML <table>。"""
    def split_row(line: str) -> list[str]:
        line = line.strip().strip("|")
        return [c.strip() for c in line.split("|")]

    if len(table_lines) < 2:
        return ""

    headers = split_row(table_lines[0])

    # 解析对齐信息
    aligns: list[str] = []
    for cell in split_row(table_lines[1]):
        cell = cell.strip()
        if cell.startswith(":") and cell.endswith(":"):
            aligns.append("center")
        elif cell.endswith(":"):
            aligns.append("right")
        else:
            aligns.append("left")

    html = '<table class="report-table">\n<thead><tr>'
    for idx, h in enumerate(headers):
        align = aligns[idx] if idx < len(aligns) else "left"
        html += f'<th style="text-align:{align}">{h}</th>'
    html += '</tr></thead>\n<tbody>'

    for row_line in table_lines[2:]:
        cells = split_row(row_line)
        html += "<tr>"
        for idx, c in enumerate(cells):
            align = aligns[idx] if idx < len(aligns) else "left"
            html += f'<td style="text-align:{align}">{c}</td>'
        html += "</tr>"

    html += "</tbody>\n</table>"
    return html


def _extract_toc(html_content: str) -> str:
    """从转换后的 HTML 中提取 h2/h3 标题生成目录。"""
    headings = re.findall(r'<h([23])\s+id="([^"]*)">(.*?)</h\1>', html_content)
    if not headings:
        return "<ul><li>暂无目录</li></ul>"

    toc = "<ul>"
    for level, slug, text in headings:
        clean = re.sub(r"<[^>]+>", "", text)
        cls = ' class="toc-h3"' if level == "3" else ""
        toc += f'<li{cls}><a href="#{slug}">{clean}</a></li>'
    toc += "</ul>"
    return toc


def _make_slug(title: str) -> str:
    """基于标题生成合法文件名 slug。"""
    slug = re.sub(r"[^\w\u4e00-\u9fff]+", "_", title).strip("_")
    return slug[:80] if slug else "report"


def _generate_id(title: str) -> str:
    """基于标题和时间生成唯一 ID。"""
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    digest = hashlib.md5(title.encode("utf-8")).hexdigest()[:6]
    return f"RPT-{now}-{digest}"


# ═══════════════════════════════════════════════════════════
# index.json 读写（带文件锁）
# ═══════════════════════════════════════════════════════════

def _read_index() -> list[dict]:
    """读取 index.json，不存在则返回空列表。"""
    idx_path = config.index_json_path
    if not os.path.exists(idx_path):
        return []
    try:
        with open(idx_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("reports", [])
        return []
    except (json.JSONDecodeError, OSError):
        return []


def _write_index(reports: list[dict]) -> None:
    """将研报列表写回 index.json（带文件锁）。"""
    idx_path = config.index_json_path
    os.makedirs(os.path.dirname(idx_path), exist_ok=True)
    with open(idx_path, "w", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            json.dump(reports, f, ensure_ascii=False, indent=2)
            f.write("\n")
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


# ═══════════════════════════════════════════════════════════
# 独立业务函数（可被 pytest 直接测试）
# ═══════════════════════════════════════════════════════════

@handle_errors
def build_report(title: str, content: str, author: str = "投研AI团队",
                 category: str = "宏观研究", tags: str = "",
                 filename: str = "") -> dict:
    """将 Markdown 内容生成为专业 HTML 研报文件的核心逻辑。"""
    reports_dir = config.abs_reports_dir
    os.makedirs(reports_dir, exist_ok=True)

    # 读取外部模板或使用内置模板
    template_path = os.path.join(_TEMPLATE_DIR, "report_base.html")
    if os.path.isfile(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()
    else:
        template = DEFAULT_TEMPLATE

    body_html = _md_to_html(content)
    toc_html = _extract_toc(body_html)

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    tags_html = "".join(f'<span class="tag">{t}</span>' for t in tag_list)

    today = datetime.now().strftime("%Y-%m-%d")
    year = datetime.now().strftime("%Y")

    html = template
    for placeholder, value in [
        ("{{TITLE}}", title), ("{{AUTHOR}}", author), ("{{DATE}}", today),
        ("{{CATEGORY}}", category), ("{{TOC}}", toc_html),
        ("{{TAGS_HTML}}", tags_html), ("{{CONTENT}}", body_html),
        ("{{YEAR}}", year),
    ]:
        html = html.replace(placeholder, value)

    if not filename:
        filename = _make_slug(title)
    if not filename.endswith(".html"):
        filename += ".html"
    out_path = os.path.join(reports_dir, filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    rel_path = f"reports/{filename}"
    _auto_register(title=title, author=author, category=category,
                   tags=tag_list, path=rel_path, date=today)

    return {"status": "success", "path": rel_path, "title": title, "url": rel_path}


@handle_errors
def build_data_table(headers: str, rows: str, title: str = "",
                     highlight_cols: str = "") -> dict:
    """生成可嵌入研报的 HTML 数据表格核心逻辑。"""
    header_list = [h.strip() for h in headers.split(",")]
    row_list = []
    for row_str in rows.split(";"):
        row_str = row_str.strip()
        if row_str:
            row_list.append([c.strip() for c in row_str.split(",")])

    hl_set: set[int] = set()
    if highlight_cols.strip():
        for c in highlight_cols.split(","):
            c = c.strip()
            if c.isdigit():
                hl_set.add(int(c))

    def _is_numeric(v: str) -> bool:
        return bool(re.match(r"^[-+]?\d[\d,.%]*%?$", v.strip()))

    # HTML 表格
    table_style = (
        'style="width:100%;border-collapse:collapse;font-size:0.9rem;'
        'margin:18px 0;"'
    )
    html = ""
    if title:
        html += (
            f'<div style="color:#58a6ff;font-weight:600;'
            f'margin-bottom:6px;font-size:0.95rem;">{title}</div>\n'
        )
    html += f"<table {table_style}>\n<thead><tr>"
    for idx, h in enumerate(header_list):
        bg = "#1a2744" if idx in hl_set else "#161b22"
        html += (
            f'<th style="background:{bg};color:#e6edf3;font-weight:600;'
            f'padding:10px 14px;text-align:left;'
            f'border-bottom:2px solid #30363d;">{h}</th>'
        )
    html += "</tr></thead>\n<tbody>"

    for r_idx, row in enumerate(row_list):
        row_bg = "rgba(255,255,255,0.02)" if r_idx % 2 == 0 else "transparent"
        html += f'<tr style="background:{row_bg};">'
        for c_idx, cell in enumerate(row):
            align = "right" if _is_numeric(cell) and c_idx > 0 else "left"
            hl_bg = "background:rgba(88,166,255,0.08);" if c_idx in hl_set else ""
            html += (
                f'<td style="padding:8px 14px;{hl_bg}'
                f'border-bottom:1px solid #21262d;text-align:{align};">'
                f"{cell}</td>"
            )
        html += "</tr>"
    html += "</tbody>\n</table>"

    # Markdown 表格
    md = "| " + " | ".join(header_list) + " |\n"
    md += "| " + " | ".join(["---"] * len(header_list)) + " |\n"
    for row in row_list:
        padded = row + [""] * (len(header_list) - len(row))
        md += "| " + " | ".join(padded[: len(header_list)]) + " |\n"

    return {"html": html, "markdown": md.strip()}


@handle_errors
def do_register_report(title: str, category: str, tags: str, summary: str,
                       path: str, author: str = "投研AI团队",
                       date: str = "") -> dict:
    """将研报元数据注册到 index.json 知识库索引的核心逻辑。"""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    report_id = _generate_id(title)

    reports = _read_index()
    record = {
        "id": report_id, "title": title, "author": author, "date": date,
        "tags": tag_list, "category": category, "summary": summary,
        "filePath": path, "lastUpdated": datetime.now(timezone.utc).isoformat(),
    }
    reports.append(record)
    _write_index(reports)

    return {"status": "success", "id": report_id, "total_reports": len(reports)}


# ═══════════════════════════════════════════════════════════
# 注册入口
# ═══════════════════════════════════════════════════════════

def register_tools(mcp):
    """将研报生成工具集注册到 FastMCP 实例。"""

    @mcp.tool
    def generate_report(
        title: str,
        content: str,
        author: str = "投研AI团队",
        category: str = "宏观研究",
        tags: str = "",
        filename: str = "",
    ) -> dict:
        """将 Markdown 内容生成为专业 HTML 研报文件。

        接收 Markdown 格式的研报正文，自动转换为带有深色金融风格的
        专业 HTML 页面，包含目录导航、元数据、免责声明等，同时
        自动注册到知识库 index.json。

        Args:
            title: 研报标题
            content: Markdown 格式的研报正文
            author: 作者（默认"投研AI团队"）
            category: 分类（宏观研究/产业研究/公司研究/策略研究）
            tags: 标签，逗号分隔
            filename: 输出文件名（不含路径和后缀），空则自动生成

        Returns:
            包含 status, path, title, url 的字典
        """
        return build_report(title, content, author, category, tags, filename)

    @mcp.tool
    def create_data_table(
        headers: str,
        rows: str,
        title: str = "",
        highlight_cols: str = "",
    ) -> dict:
        """生成可嵌入研报的 HTML 数据表格。

        接收逗号分隔的表头和分号/逗号分隔的数据行，生成带有深色
        金融风格的 HTML 表格以及对应的 Markdown 表格文本。

        Args:
            headers: 表头（逗号分隔，如 "指标,2024Q4,2025Q1"）
            rows: 数据行（分号分隔行，逗号分隔列）
            title: 表格标题（可选）
            highlight_cols: 需要高亮的列号（逗号分隔，从 0 开始）

        Returns:
            包含 html 和 markdown 两个键的字典
        """
        return build_data_table(headers, rows, title, highlight_cols)

    @mcp.tool
    def register_report(
        title: str,
        category: str,
        tags: str,
        summary: str,
        path: str,
        author: str = "投研AI团队",
        date: str = "",
    ) -> dict:
        """将研报元数据注册到 index.json 知识库索引。

        读取现有 index.json（不存在则新建），追加新研报记录，
        生成唯一 ID 并更新 lastUpdated 时间戳后写回文件。

        Args:
            title: 研报标题
            category: 分类（宏观研究/产业研究/公司研究/策略研究）
            tags: 标签（逗号分隔）
            summary: 研报摘要（200 字以内）
            path: 文件路径（相对于投研助手根目录）
            author: 作者
            date: 日期（空则取当天）

        Returns:
            包含 status, id, total_reports 的字典
        """
        return do_register_report(title, category, tags, summary, path,
                                  author, date)


# ── 内部辅助：generate_report 自动注册 ──

def _auto_register(
    title: str,
    author: str,
    category: str,
    tags: list[str],
    path: str,
    date: str,
) -> None:
    """generate_report 内部调用，自动将新研报追加到 index.json。"""
    report_id = _generate_id(title)
    reports = _read_index()
    record = {
        "id": report_id,
        "title": title,
        "author": author,
        "date": date,
        "tags": tags,
        "category": category,
        "filePath": path,
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
    }
    reports.append(record)
    _write_index(reports)
