"""基本面分析工具测试（全部 mock，无网络调用）"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock, PropertyMock


# ---------------------------------------------------------------------------
# Fixtures — mock akshare DataFrames
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_financial_indicator():
    """Mock akshare stock_financial_analysis_indicator — latest 2 periods."""
    return pd.DataFrame({
        "日期": ["2024-12-31", "2024-06-30"],
        "净资产收益率(%)": [25.3, 22.1],
        "销售毛利率(%)": [91.5, 90.8],
        "销售净利率(%)": [53.2, 51.9],
        "总资产报酬率(%)": [20.1, 19.5],
        "资产负债率(%)": [25.0, 26.3],
        "流动比率": [3.5, 3.2],
        "速动比率": [3.1, 2.9],
        "存货周转天数(天)": [1200, 1150],
        "应收账款周转天数(天)": [15, 14],
        "总资产周转率(次)": [0.35, 0.33],
        "主营业务收入增长率(%)": [18.5, 16.2],
        "净利润增长率(%)": [20.1, 18.0],
    })


@pytest.fixture
def mock_financial_indicator_poor():
    """Mock poor-quality company: low ROE, low margin, high debt."""
    return pd.DataFrame({
        "日期": ["2024-12-31", "2024-06-30"],
        "净资产收益率(%)": [3.2, 2.8],
        "销售毛利率(%)": [12.5, 11.8],
        "销售净利率(%)": [-2.1, -3.5],
        "总资产报酬率(%)": [1.5, 1.2],
        "资产负债率(%)": [78.0, 79.3],
        "流动比率": [0.8, 0.7],
        "速动比率": [0.5, 0.4],
        "存货周转天数(天)": [200, 210],
        "应收账款周转天数(天)": [95, 100],
        "总资产周转率(次)": [0.15, 0.14],
        "主营业务收入增长率(%)": [-5.0, -8.0],
        "净利润增长率(%)": [-15.0, -20.0],
    })


@pytest.fixture
def mock_stock_info():
    """Mock akshare stock_individual_info_em."""
    return pd.DataFrame({
        "item": ["股票简称", "行业", "总市值"],
        "value": ["贵州茅台", "白酒", "2000000000000"],
    })


@pytest.fixture
def mock_spot_em():
    """Mock akshare stock_zh_a_spot_em for a few stocks."""
    return pd.DataFrame({
        "代码": ["600519", "000858", "000568"],
        "名称": ["贵州茅台", "五粮液", "泸州老窖"],
        "最新价": [1800.0, 150.0, 200.0],
        "市盈率-动态": [30.5, 25.0, 28.0],
        "市净率": [10.2, 6.5, 8.0],
        "总市值": [2.26e12, 5.5e11, 2.9e11],
        "涨跌幅": [1.2, -0.5, 0.8],
    })


@pytest.fixture
def mock_cash_flow():
    """Mock akshare stock_financial_cash_ths."""
    return pd.DataFrame({
        "报告期": ["2024-12-31"],
        "经营活动产生的现金流量净额": [7_000_000_000.0],
        "购建固定资产、无形资产和其他长期资产支付的现金": [500_000_000.0],
    })


@pytest.fixture
def mock_profit_sheet():
    """Mock akshare stock_profit_sheet_by_report_em."""
    return pd.DataFrame({
        "净利润": [5_000_000_000.0],
        "营业总收入": [12_000_000_000.0],
    })


@pytest.fixture
def mock_board_cons():
    """Mock akshare stock_board_industry_cons_em (industry constituents)."""
    return pd.DataFrame({
        "代码": ["600519", "000858", "000568", "002304", "603589"],
        "名称": ["贵州茅台", "五粮液", "泸州老窖", "洋河股份", "口子窖"],
    })


@pytest.fixture
def mock_holder_detail():
    """Mock akshare stock_gdfx_free_holding_detail_em."""
    return pd.DataFrame({
        "日期": ["2024-12-31"] * 5,
        "股东名称": ["中国贵州茅台酒厂", "香港中央结算", "证金公司", "社保基金", "张三"],
        "持股数量": [8e8, 3e7, 2e7, 1.5e7, 1e7],
        "持股比例(%)": [61.99, 2.32, 1.55, 1.16, 0.77],
        "股东类型": ["国有", "境外", "国有", "社保", "个人"],
    })


@pytest.fixture
def mock_holder_stats():
    """Mock akshare stock_zh_a_gdhs_detail_em."""
    return pd.DataFrame({
        "股东户数": [80000, 85000],
        "人均持股": [15600, 14700],
    })


def _build_ak_mock(
    financial_indicator=None,
    stock_info=None,
    spot_em=None,
    cash_flow=None,
    profit_sheet=None,
    board_cons=None,
    holder_detail=None,
    holder_stats=None,
):
    """Build a mock akshare module that returns controlled DataFrames."""
    mock_ak = MagicMock()

    def _return_or_empty(df):
        return df if df is not None else pd.DataFrame()

    mock_ak.stock_financial_analysis_indicator.return_value = _return_or_empty(financial_indicator)
    mock_ak.stock_financial_abstract_ths.return_value = pd.DataFrame()

    # stock_individual_info_em
    if stock_info is not None:
        mock_ak.stock_individual_info_em.return_value = stock_info
    else:
        mock_ak.stock_individual_info_em.return_value = pd.DataFrame({
            "item": ["股票简称", "行业"],
            "value": ["测试股票", "未知"],
        })

    mock_ak.stock_zh_a_spot_em.return_value = _return_or_empty(spot_em)
    mock_ak.stock_financial_cash_ths.return_value = _return_or_empty(cash_flow)
    mock_ak.stock_profit_sheet_by_report_em.return_value = _return_or_empty(profit_sheet)
    mock_ak.stock_board_industry_cons_em.return_value = _return_or_empty(board_cons)
    mock_ak.stock_board_industry_name_em.return_value = pd.DataFrame()

    # Shareholder APIs
    mock_ak.stock_gdfx_free_holding_detail_em.return_value = _return_or_empty(holder_detail)
    mock_ak.stock_gdfx_holding_detail_em.return_value = pd.DataFrame()
    mock_ak.stock_zh_a_gdhs_detail_em.return_value = _return_or_empty(holder_stats)
    mock_ak.stock_zh_a_gdhs.return_value = pd.DataFrame()
    mock_ak.stock_report_fund_hold_detail.return_value = pd.DataFrame()
    mock_ak.stock_institute_hold_detail.return_value = pd.DataFrame()

    return mock_ak


# ---------------------------------------------------------------------------
# Profile Tests
# ---------------------------------------------------------------------------

class TestFundamentalProfile:
    """Test fetch_fundamental_profile."""

    def test_profile_structure(
        self, mock_financial_indicator, mock_stock_info,
        mock_spot_em, mock_cash_flow, mock_profit_sheet,
    ):
        """Verify all expected sections are present in the profile."""
        mock_ak = _build_ak_mock(
            financial_indicator=mock_financial_indicator,
            stock_info=mock_stock_info,
            spot_em=mock_spot_em,
            cash_flow=mock_cash_flow,
            profit_sheet=mock_profit_sheet,
        )
        with patch("tools.fundamental_analysis.ak", mock_ak):
            from tools.fundamental_analysis import fetch_fundamental_profile
            result = fetch_fundamental_profile("600519", market="A")

        assert isinstance(result, dict)
        assert result.get("error") is not True
        for section in (
            "profitability", "growth", "efficiency",
            "solvency", "cash_flow", "valuation", "quality_score",
        ):
            assert section in result, f"Missing section: {section}"

        # quality_score sub-fields
        qs = result["quality_score"]
        assert "score" in qs
        assert "grade" in qs
        assert isinstance(qs["score"], (int, float))

    def test_quality_score_high(
        self, mock_financial_indicator, mock_stock_info,
        mock_spot_em, mock_cash_flow, mock_profit_sheet,
    ):
        """High-quality metrics (ROE>20, margin>50) → score≥80, grade A."""
        mock_ak = _build_ak_mock(
            financial_indicator=mock_financial_indicator,
            stock_info=mock_stock_info,
            spot_em=mock_spot_em,
            cash_flow=mock_cash_flow,
            profit_sheet=mock_profit_sheet,
        )
        with patch("tools.fundamental_analysis.ak", mock_ak):
            from tools.fundamental_analysis import fetch_fundamental_profile
            result = fetch_fundamental_profile("600519", market="A")

        qs = result["quality_score"]
        assert qs["score"] >= 80, f"Expected score≥80, got {qs['score']}"
        assert qs["grade"] == "A"

    def test_quality_score_low(
        self, mock_financial_indicator_poor, mock_stock_info,
        mock_spot_em,
    ):
        """Poor metrics → low score, grade D or F."""
        mock_ak = _build_ak_mock(
            financial_indicator=mock_financial_indicator_poor,
            stock_info=mock_stock_info,
            spot_em=mock_spot_em,
        )
        with patch("tools.fundamental_analysis.ak", mock_ak):
            from tools.fundamental_analysis import fetch_fundamental_profile
            result = fetch_fundamental_profile("600519", market="A")

        qs = result["quality_score"]
        assert qs["score"] < 40, f"Expected score<40, got {qs['score']}"
        assert qs["grade"] in ("D", "F")

    def test_profile_partial_data(self, mock_stock_info, mock_spot_em):
        """When some akshare APIs fail, profile still returns partial result."""
        mock_ak = _build_ak_mock(stock_info=mock_stock_info, spot_em=mock_spot_em)
        # Make financial_indicator raise an exception
        mock_ak.stock_financial_analysis_indicator.side_effect = Exception("API down")
        mock_ak.stock_financial_abstract_ths.side_effect = Exception("API down")
        mock_ak.stock_financial_cash_ths.side_effect = Exception("Cash flow API down")
        mock_ak.stock_profit_sheet_by_report_em.side_effect = Exception("Profit API down")

        with patch("tools.fundamental_analysis.ak", mock_ak):
            from tools.fundamental_analysis import fetch_fundamental_profile
            result = fetch_fundamental_profile("600519", market="A")

        # Should still return a dict (not crash)
        assert isinstance(result, dict)
        assert result.get("error") is not True
        assert result["symbol"] == "600519"
        # quality_score should still be present (with 0 or low values)
        assert "quality_score" in result


# ---------------------------------------------------------------------------
# Peer Comparison Tests
# ---------------------------------------------------------------------------

class TestPeerComparison:
    """Test fetch_peer_comparison."""

    def test_peer_comparison_structure(
        self, mock_stock_info, mock_spot_em, mock_board_cons,
        mock_financial_indicator,
    ):
        """Verify keys: target, peers, rankings, summary."""
        mock_ak = _build_ak_mock(
            stock_info=mock_stock_info,
            spot_em=mock_spot_em,
            board_cons=mock_board_cons,
            financial_indicator=mock_financial_indicator,
        )
        with patch("tools.fundamental_analysis.ak", mock_ak):
            from tools.fundamental_analysis import fetch_peer_comparison
            result = fetch_peer_comparison("600519")

        assert isinstance(result, dict)
        assert result.get("error") is not True
        for key in ("target", "peers", "rankings", "summary"):
            assert key in result, f"Missing key: {key}"
        assert result["target"]["symbol"] == "600519"
        assert isinstance(result["peers"], list)

    def test_peer_ranking(
        self, mock_stock_info, mock_spot_em, mock_board_cons,
        mock_financial_indicator,
    ):
        """Verify rank/percentile calculations are present and sane."""
        mock_ak = _build_ak_mock(
            stock_info=mock_stock_info,
            spot_em=mock_spot_em,
            board_cons=mock_board_cons,
            financial_indicator=mock_financial_indicator,
        )
        with patch("tools.fundamental_analysis.ak", mock_ak):
            from tools.fundamental_analysis import fetch_peer_comparison
            result = fetch_peer_comparison("600519", metrics=["pe", "roe"])

        rankings = result.get("rankings", {})
        for metric in rankings:
            r = rankings[metric]
            assert "rank" in r
            assert "total" in r
            assert "percentile" in r
            assert 1 <= r["rank"] <= r["total"]
            assert 0 <= r["percentile"] <= 100

    def test_peer_metrics_filter(
        self, mock_stock_info, mock_spot_em, mock_board_cons,
        mock_financial_indicator,
    ):
        """Custom metrics list filters which rankings are computed."""
        mock_ak = _build_ak_mock(
            stock_info=mock_stock_info,
            spot_em=mock_spot_em,
            board_cons=mock_board_cons,
            financial_indicator=mock_financial_indicator,
        )
        with patch("tools.fundamental_analysis.ak", mock_ak):
            from tools.fundamental_analysis import fetch_peer_comparison
            result = fetch_peer_comparison("600519", metrics=["pb"])

        # Rankings should only contain metrics requested (or subset that has data)
        rankings = result.get("rankings", {})
        for key in rankings:
            assert key in ("pb",)


# ---------------------------------------------------------------------------
# Shareholder Tests
# ---------------------------------------------------------------------------

class TestShareholderAnalysis:
    """Test fetch_shareholder_analysis."""

    def test_shareholder_structure(
        self, mock_stock_info, mock_holder_detail, mock_holder_stats,
    ):
        """Verify keys: top_shareholders, holder_stats, institutional."""
        mock_ak = _build_ak_mock(
            stock_info=mock_stock_info,
            holder_detail=mock_holder_detail,
            holder_stats=mock_holder_stats,
        )
        with patch("tools.fundamental_analysis.ak", mock_ak):
            from tools.fundamental_analysis import fetch_shareholder_analysis
            result = fetch_shareholder_analysis("600519")

        assert isinstance(result, dict)
        assert result.get("error") is not True
        for key in ("top_shareholders", "holder_stats", "institutional"):
            assert key in result, f"Missing key: {key}"
        assert isinstance(result["top_shareholders"], list)
        assert isinstance(result["holder_stats"], dict)
        assert isinstance(result["institutional"], dict)

    def test_shareholder_concentration(self, mock_stock_info):
        """Verify concentration classification: high/medium/low."""
        # Holders dropping significantly → high concentration
        mock_stats_high = pd.DataFrame({
            "股东户数": [60000, 70000],
            "人均持股": [20000, 17000],
        })
        mock_ak = _build_ak_mock(
            stock_info=mock_stock_info,
            holder_stats=mock_stats_high,
        )
        with patch("tools.fundamental_analysis.ak", mock_ak):
            from tools.fundamental_analysis import fetch_shareholder_analysis
            result = fetch_shareholder_analysis("600519")

        stats = result.get("holder_stats", {})
        concentration = stats.get("concentration", "unknown")
        # 60000 vs 70000: change = -14.3% → should be "high"
        assert concentration in ("high", "medium", "low"), f"Unexpected: {concentration}"
        if stats.get("holders_change") is not None and stats["holders_change"] < -5:
            assert concentration == "high"


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

class TestFundamentalEdgeCases:
    """Edge-case and error-path tests."""

    def test_invalid_symbol(self, mock_stock_info):
        """Invalid symbol with all APIs returning empty → graceful result."""
        mock_ak = _build_ak_mock(stock_info=mock_stock_info)
        with patch("tools.fundamental_analysis.ak", mock_ak):
            from tools.fundamental_analysis import fetch_fundamental_profile
            result = fetch_fundamental_profile("999999", market="A")

        # Should not crash, returns a result dict
        assert isinstance(result, dict)

    def test_us_market_fallback(self):
        """market='US' uses yfinance fallback."""
        mock_yf = MagicMock()
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "shortName": "Apple Inc.",
            "grossMargins": 0.46,
            "profitMargins": 0.26,
            "returnOnEquity": 1.60,
            "returnOnAssets": 0.28,
            "revenueGrowth": 0.05,
            "earningsGrowth": 0.10,
            "debtToEquity": 176.0,
            "currentRatio": 1.07,
            "quickRatio": 1.0,
            "operatingCashflow": 110_000_000_000,
            "netIncomeToCommon": 95_000_000_000,
            "freeCashflow": 100_000_000_000,
            "totalRevenue": 380_000_000_000,
            "marketCap": 3_000_000_000_000,
            "trailingPE": 30.5,
            "priceToBook": 50.0,
            "priceToSalesTrailing12Months": 8.0,
            "industry": "Consumer Electronics",
        }
        mock_yf.Ticker.return_value = mock_ticker

        with patch("tools.fundamental_analysis.yf", mock_yf):
            from tools.fundamental_analysis import fetch_fundamental_profile
            result = fetch_fundamental_profile("AAPL", market="US")

        assert isinstance(result, dict)
        assert result.get("error") is not True
        assert result["market"] == "US"
        assert result["name"] == "Apple Inc."
        assert "profitability" in result
        assert "quality_score" in result
        # ROE = 160% → definitely high score
        assert result["quality_score"]["score"] >= 40

    def test_all_apis_fail(self):
        """When akshare is None → returns error message."""
        with patch("tools.fundamental_analysis.ak", None):
            from tools.fundamental_analysis import fetch_fundamental_profile
            result = fetch_fundamental_profile("600519", market="A")

        assert isinstance(result, dict)
        assert "error" in result or result.get("error") is True

    def test_peer_non_a_market(self):
        """Peer comparison for non-A market → error."""
        from tools.fundamental_analysis import fetch_peer_comparison
        result = fetch_peer_comparison("AAPL", market="US")
        assert result.get("error") is True or "不支持" in str(result.get("message", ""))

    def test_shareholder_non_a_market(self):
        """Shareholder analysis for non-A market → error."""
        from tools.fundamental_analysis import fetch_shareholder_analysis
        result = fetch_shareholder_analysis("AAPL", market="US")
        assert result.get("error") is True or "不支持" in str(result.get("message", ""))

    def test_profile_quality_score_computation_direct(self):
        """Directly test _compute_quality_score with controlled inputs."""
        from tools.fundamental_analysis import _compute_quality_score

        # Excellent company
        profitability = {"roe": 25.0, "gross_margin": 91.0, "net_margin": 53.0}
        growth = {"revenue_yoy": 18.0}
        solvency = {"debt_ratio": 25.0}
        cash_flow = {"ocf_to_profit": 1.5}

        qs = _compute_quality_score(profitability, growth, solvency, cash_flow)
        assert qs["score"] >= 80
        assert qs["grade"] == "A"
        assert len(qs["details"]) > 0

        # Terrible company
        profitability2 = {"roe": 2.0, "gross_margin": 10.0, "net_margin": -5.0}
        growth2 = {"revenue_yoy": -10.0}
        solvency2 = {"debt_ratio": 80.0}
        cash_flow2 = {"ocf_to_profit": 0.3}

        qs2 = _compute_quality_score(profitability2, growth2, solvency2, cash_flow2)
        assert qs2["score"] < 20
        assert qs2["grade"] in ("D", "F")

    def test_profile_with_none_values(self):
        """Profile should handle None values in all fields gracefully."""
        from tools.fundamental_analysis import _compute_quality_score

        profitability = {"roe": None, "gross_margin": None, "net_margin": None}
        growth = {"revenue_yoy": None}
        solvency = {"debt_ratio": None}
        cash_flow = {"ocf_to_profit": None}

        qs = _compute_quality_score(profitability, growth, solvency, cash_flow)
        assert qs["score"] == 0
        assert qs["grade"] == "F"


# ---------------------------------------------------------------------------
# Valuation Percentile Tests (Wave 2)
# ---------------------------------------------------------------------------

class TestValuationPercentile:
    """Test fetch_valuation_percentile."""

    @pytest.fixture
    def mock_hist_with_pe_pb(self):
        """3年日线历史 DataFrame，含市盈率/市净率列。"""
        n = 750  # ~3年交易日
        dates = pd.date_range("2022-01-01", periods=n, freq="B")
        pe_values = [20 + i * 0.02 for i in range(n)]  # PE 从20逐步涨到35
        pb_values = [2.0 + i * 0.004 for i in range(n)]  # PB 从2.0涨到5.0
        return pd.DataFrame({
            "日期": dates.strftime("%Y-%m-%d"),
            "收盘": [100 + i * 0.1 for i in range(n)],
            "市盈率": pe_values,
            "市净率": pb_values,
        })

    @pytest.fixture
    def mock_spot_for_percentile(self):
        """实时行情 DataFrame，提供当前PE/PB。"""
        return pd.DataFrame({
            "代码": ["600519"],
            "名称": ["贵州茅台"],
            "最新价": [1800.0],
            "市盈率-动态": [30.0],
            "市净率": [8.0],
        })

    def test_valuation_percentile_structure(
        self, mock_hist_with_pe_pb, mock_spot_for_percentile,
    ):
        """验证返回结构包含 pe_percentile, pb_percentile, assessment。"""
        mock_ak = MagicMock()
        mock_ak.stock_zh_a_hist.return_value = mock_hist_with_pe_pb
        mock_ak.stock_zh_a_spot_em.return_value = mock_spot_for_percentile

        with patch("tools.fundamental_analysis.ak", mock_ak):
            from tools.fundamental_analysis import fetch_valuation_percentile
            result = fetch_valuation_percentile("600519", market="A")

        assert isinstance(result, dict)
        assert "error" not in result
        assert result["symbol"] == "600519"
        for key in ("pe_ttm", "pe_percentile", "pe_min", "pe_max", "pe_median",
                     "pb", "pb_percentile", "pb_min", "pb_max", "pb_median",
                     "assessment", "history_days"):
            assert key in result, f"Missing key: {key}"
        assert result["pe_ttm"] == 30.0
        assert result["pb"] == 8.0
        assert result["pe_percentile"] is not None
        assert result["pb_percentile"] is not None
        assert isinstance(result["assessment"], str)

    def test_valuation_percentile_high(self):
        """PE 在历史高位 → 高分位。"""
        n = 500
        pe_values = [15 + i * 0.02 for i in range(n)]  # PE: 15 → 25
        hist_df = pd.DataFrame({
            "日期": pd.date_range("2022-06-01", periods=n, freq="B").strftime("%Y-%m-%d"),
            "收盘": [100.0] * n,
            "市盈率": pe_values,
            "市净率": [3.0] * n,
        })
        # 当前PE=24.5，接近最高值25 → 应该在很高的分位
        spot_df = pd.DataFrame({
            "代码": ["600519"],
            "名称": ["贵州茅台"],
            "最新价": [1800.0],
            "市盈率-动态": [24.5],
            "市净率": [3.0],
        })
        mock_ak = MagicMock()
        mock_ak.stock_zh_a_hist.return_value = hist_df
        mock_ak.stock_zh_a_spot_em.return_value = spot_df

        with patch("tools.fundamental_analysis.ak", mock_ak):
            from tools.fundamental_analysis import fetch_valuation_percentile
            result = fetch_valuation_percentile("600519", market="A")

        assert "error" not in result
        assert result["pe_percentile"] >= 80, (
            f"Expected PE percentile >= 80 for high PE, got {result['pe_percentile']}"
        )
        assert "偏高" in result["assessment"]

    def test_valuation_percentile_api_fail(self):
        """历史数据 API 失败时优雅返回错误。"""
        mock_ak = MagicMock()
        mock_ak.stock_zh_a_hist.side_effect = Exception("API 500 error")

        with patch("tools.fundamental_analysis.ak", mock_ak):
            from tools.fundamental_analysis import fetch_valuation_percentile
            result = fetch_valuation_percentile("600519", market="A")

        assert "error" in result

    def test_valuation_percentile_unsupported_market(self):
        """非A股市场返回错误。"""
        from tools.fundamental_analysis import fetch_valuation_percentile
        result = fetch_valuation_percentile("AAPL", market="US")
        assert "error" in result
