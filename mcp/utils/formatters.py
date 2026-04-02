"""
数据格式化工具 - 提供金融数据的格式化辅助函数

支持数字、货币、涨跌幅、DataFrame 转 Markdown/HTML 表格等。
"""

from datetime import datetime
from typing import Optional, Union

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


def format_number(num: Optional[Union[int, float]], decimals: int = 2) -> str:
    """
    格式化数字（自动缩放单位 + 千分位分隔）

    Args:
        num: 数字
        decimals: 小数位数

    Returns:
        格式化后的字符串，如 "1,234,567.89" 或 "1.23亿"

    Examples:
        >>> format_number(1234567.891)
        '123.47万'
        >>> format_number(0.5, 4)
        '0.5000'
    """
    if num is None:
        return "N/A"
    try:
        num = float(num)
    except (ValueError, TypeError):
        return "N/A"

    if abs(num) >= 1e12:
        return f"{num / 1e12:,.{decimals}f}万亿"
    elif abs(num) >= 1e8:
        return f"{num / 1e8:,.{decimals}f}亿"
    elif abs(num) >= 1e4:
        return f"{num / 1e4:,.{decimals}f}万"
    else:
        return f"{num:,.{decimals}f}"


def format_currency(num: Optional[Union[int, float]], currency: str = "CNY") -> str:
    """
    格式化货币金额

    Args:
        num: 金额
        currency: 货币代码（CNY/USD/HKD/EUR/JPY/GBP）

    Returns:
        格式化后的货币字符串，如 "¥1,234.56" 或 "¥1.23亿"
    """
    symbols = {
        "CNY": "¥",
        "USD": "$",
        "HKD": "HK$",
        "EUR": "€",
        "JPY": "¥",
        "GBP": "£",
    }
    symbol = symbols.get(currency.upper(), currency + " ")

    if num is None:
        return f"{symbol}N/A"
    try:
        num = float(num)
    except (ValueError, TypeError):
        return f"{symbol}N/A"

    if abs(num) >= 1e12:
        return f"{symbol}{num / 1e12:,.2f}万亿"
    elif abs(num) >= 1e8:
        return f"{symbol}{num / 1e8:,.2f}亿"
    elif abs(num) >= 1e4:
        return f"{symbol}{num / 1e4:,.2f}万"
    else:
        return f"{symbol}{num:,.2f}"


def format_change(num: Optional[Union[int, float]], as_html: bool = False) -> str:
    """
    格式化涨跌幅（A股风格：上涨红色、下跌绿色）

    Args:
        num: 涨跌幅数值（如 2.35 表示 +2.35%）
        as_html: 是否输出带颜色的HTML标签

    Returns:
        格式化后的涨跌幅字符串

    Examples:
        >>> format_change(2.35)
        '+2.35%'
        >>> format_change(-1.20)
        '-1.20%'
    """
    if num is None:
        return "N/A"
    try:
        num = float(num)
    except (ValueError, TypeError):
        return "N/A"

    if num > 0:
        text = f"+{num:.2f}%"
        color = "#ef4444"  # 红色（A股上涨为红）
    elif num < 0:
        text = f"{num:.2f}%"
        color = "#22c55e"  # 绿色（A股下跌为绿）
    else:
        text = "0.00%"
        color = "#9ca3af"  # 灰色

    if as_html:
        return f'<span style="color:{color};font-weight:600">{text}</span>'
    return text


def df_to_markdown_table(df, max_rows: int = 50) -> str:
    """
    将 DataFrame 转换为 Markdown 表格

    Args:
        df: pandas DataFrame
        max_rows: 最大显示行数

    Returns:
        Markdown格式的表格字符串
    """
    if not HAS_PANDAS:
        return "[错误] 需要安装 pandas 库"

    if df is None or df.empty:
        return "*（无数据）*"

    total_rows = len(df)
    truncated = total_rows > max_rows
    if truncated:
        df = df.head(max_rows)

    # 构建表头
    headers = list(df.columns)
    header_line = "| " + " | ".join(str(h) for h in headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"

    # 构建数据行
    rows = []
    for _, row in df.iterrows():
        cells = []
        for val in row:
            cell = str(val) if val is not None else ""
            cell = cell.replace("|", "\\|")
            cells.append(cell)
        rows.append("| " + " | ".join(cells) + " |")

    result = "\n".join([header_line, separator] + rows)
    if truncated:
        result += f"\n\n*（仅显示前 {max_rows} 行，共 {total_rows} 行）*"

    return result


def df_to_html_table(df, title: str = "", max_rows: int = 100) -> str:
    """
    将 DataFrame 转换为深色金融风格的 HTML 表格

    Args:
        df: pandas DataFrame
        title: 表格标题
        max_rows: 最大显示行数

    Returns:
        HTML格式的表格字符串（含内联样式）
    """
    if not HAS_PANDAS:
        return "<p>[错误] 需要安装 pandas 库</p>"

    if df is None or df.empty:
        return "<p><em>（无数据）</em></p>"

    total_rows = len(df)
    truncated = total_rows > max_rows
    if truncated:
        df = df.head(max_rows)

    html_parts = []
    html_parts.append('<div class="data-table-wrapper">')
    if title:
        html_parts.append(f'  <h4 class="table-title">{title}</h4>')

    html_parts.append('  <div style="overflow-x:auto">')
    html_parts.append('  <table class="data-table">')

    # 表头
    html_parts.append("    <thead><tr>")
    for col in df.columns:
        html_parts.append(f"      <th>{col}</th>")
    html_parts.append("    </tr></thead>")

    # 表体
    html_parts.append("    <tbody>")
    for idx, (_, row) in enumerate(df.iterrows()):
        row_class = "even" if idx % 2 == 0 else "odd"
        html_parts.append(f'    <tr class="{row_class}">')
        for val in row:
            cell = str(val) if val is not None else ""
            try:
                float(val)
                html_parts.append(f'      <td style="text-align:right">{cell}</td>')
            except (ValueError, TypeError):
                html_parts.append(f"      <td>{cell}</td>")
        html_parts.append("    </tr>")
    html_parts.append("    </tbody>")

    html_parts.append("  </table>")
    html_parts.append("  </div>")

    if truncated:
        html_parts.append(
            f'  <p class="table-note">仅显示前 {max_rows} 行，共 {total_rows} 行</p>'
        )

    html_parts.append("</div>")
    return "\n".join(html_parts)


def format_date(date_str: Optional[str], output_fmt: str = "%Y-%m-%d") -> str:
    """
    日期格式标准化 - 支持多种输入格式，统一输出

    Args:
        date_str: 日期字符串
        output_fmt: 输出格式，默认 YYYY-MM-DD

    Returns:
        标准化后的日期字符串
    """
    if not date_str:
        return datetime.now().strftime(output_fmt)

    date_str = str(date_str).strip()

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y%m%d",
        "%Y年%m月%d日",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime(output_fmt)
        except ValueError:
            continue

    return date_str
