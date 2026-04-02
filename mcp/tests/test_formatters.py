"""格式化函数单元测试"""
from utils.formatters import (
    format_number, format_currency, format_change, format_date,
    safe_round, date_to_str, df_to_markdown_table,
)


class TestFormatNumber:
    def test_positive(self):
        assert format_number(1234.56) == "1,234.56"

    def test_negative(self):
        assert format_number(-5678.9) == "-5,678.90"

    def test_zero(self):
        assert format_number(0) == "0.00"

    def test_large_wan(self):
        """>=1万 自动缩放为 万"""
        result = format_number(1234567.89)
        assert "万" in result
        assert "123.46" in result

    def test_large_yi(self):
        """>=1亿 自动缩放为 亿"""
        result = format_number(1_500_000_000)
        assert "亿" in result

    def test_large_wanyi(self):
        """>=1万亿 自动缩放"""
        result = format_number(2_000_000_000_000)
        assert "万亿" in result

    def test_small_decimal(self):
        result = format_number(0.5, 4)
        assert result == "0.5000"

    def test_none(self):
        assert format_number(None) == "N/A"

    def test_invalid_string(self):
        assert format_number("not_a_number") == "N/A"

    def test_custom_decimals(self):
        result = format_number(3.14159, 3)
        assert result == "3.142"


class TestFormatCurrency:
    def test_cny(self):
        result = format_currency(1234.56, "CNY")
        assert result.startswith("¥")
        assert "1,234.56" in result

    def test_usd(self):
        result = format_currency(99.99, "USD")
        assert result.startswith("$")

    def test_large_yi(self):
        result = format_currency(500_000_000, "CNY")
        assert "¥" in result
        assert "亿" in result

    def test_none(self):
        result = format_currency(None, "CNY")
        assert "N/A" in result

    def test_hkd(self):
        result = format_currency(100, "HKD")
        assert "HK$" in result

    def test_unknown_currency(self):
        result = format_currency(100, "BTC")
        assert "BTC" in result


class TestFormatChange:
    def test_positive(self):
        assert format_change(2.35) == "+2.35%"

    def test_negative(self):
        assert format_change(-1.20) == "-1.20%"

    def test_zero(self):
        assert format_change(0) == "0.00%"

    def test_none(self):
        assert format_change(None) == "N/A"

    def test_html_positive(self):
        result = format_change(3.5, as_html=True)
        assert "<span" in result
        assert "+3.50%" in result
        assert "#ef4444" in result  # 红色上涨

    def test_html_negative(self):
        result = format_change(-2.0, as_html=True)
        assert "#22c55e" in result  # 绿色下跌

    def test_html_zero(self):
        result = format_change(0, as_html=True)
        assert "#9ca3af" in result  # 灰色


class TestFormatDate:
    def test_standard(self):
        assert format_date("2025-06-15") == "2025-06-15"

    def test_slash_format(self):
        assert format_date("2025/06/15") == "2025-06-15"

    def test_compact_format(self):
        assert format_date("20250615") == "2025-06-15"

    def test_chinese_format(self):
        assert format_date("2025年06月15日") == "2025-06-15"

    def test_datetime_format(self):
        assert format_date("2025-06-15 14:30:00") == "2025-06-15"

    def test_iso_format(self):
        assert format_date("2025-06-15T14:30:00Z") == "2025-06-15"

    def test_empty_returns_today(self):
        from datetime import datetime
        result = format_date("")
        today = datetime.now().strftime("%Y-%m-%d")
        assert result == today

    def test_unrecognized_passthrough(self):
        """无法解析的格式原样返回"""
        assert format_date("unknown-date") == "unknown-date"


class TestSafeRound:
    def test_normal(self):
        assert safe_round(3.14159, 2) == 3.14

    def test_invalid(self):
        assert safe_round("abc") == "abc"

    def test_none(self):
        assert safe_round(None) is None


class TestDateToStr:
    def test_none(self):
        assert date_to_str(None) is None

    def test_string(self):
        assert date_to_str("2025-01-15 14:00:00") == "2025-01-15"

    def test_datetime(self):
        from datetime import datetime
        dt = datetime(2025, 6, 15, 12, 0, 0)
        assert date_to_str(dt) == "2025-06-15"


class TestDfToMarkdownTable:
    def test_basic(self):
        import pandas as pd
        df = pd.DataFrame({"指标": ["GDP", "CPI"], "数值": [5.0, 2.1]})
        result = df_to_markdown_table(df)
        assert "指标" in result
        assert "GDP" in result
        assert "|" in result

    def test_empty(self):
        import pandas as pd
        result = df_to_markdown_table(pd.DataFrame())
        assert "无数据" in result

    def test_none(self):
        result = df_to_markdown_table(None)
        assert "无数据" in result
