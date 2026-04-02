"""行情数据工具测试（全部 mock，无网络调用）"""
import pytest
import pandas as pd


class TestFetchStockRealtime:
    def test_a_share(self, monkeypatch):
        """mock akshare 返回 A 股行情，验证返回格式"""
        df = pd.DataFrame({
            "代码": ["000001"],
            "名称": ["平安银行"],
            "最新价": [10.50],
            "涨跌幅": [1.23],
            "涨跌额": [0.13],
            "成交量": [500000],
            "成交额": [5250000],
            "市盈率-动态": [8.5],
            "市净率": [0.7],
            "总市值": [200_000_000_000],
            "流通市值": [180_000_000_000],
            "今开": [10.40],
            "最高": [10.60],
            "最低": [10.35],
            "昨收": [10.37],
            "换手率": [0.28],
            "量比": [1.1],
        })

        class MockAk:
            def stock_zh_a_spot_em(self):
                return df

        monkeypatch.setattr("tools.market_data.ak", MockAk())

        from tools.market_data import fetch_stock_realtime
        result = fetch_stock_realtime("000001", "A")

        assert result["名称"] == "平安银行"
        assert result["代码"] == "000001"
        assert result["现价"] == 10.5
        assert result["market"] == "A"
        assert "涨跌幅(%)" in result

    def test_a_share_not_found(self, monkeypatch):
        """A 股代码不存在时返回错误"""
        class MockAk:
            def stock_zh_a_spot_em(self):
                return pd.DataFrame({"代码": ["600000"], "名称": ["浦发银行"]})

        monkeypatch.setattr("tools.market_data.ak", MockAk())

        from tools.market_data import fetch_stock_realtime
        result = fetch_stock_realtime("999999", "A")
        assert "error" in result

    def test_us_stock(self, monkeypatch):
        """mock yfinance 返回美股行情"""
        class MockTicker:
            def __init__(self, symbol):
                self.info = {
                    "shortName": "Apple Inc.",
                    "regularMarketPrice": 195.0,
                    "previousClose": 193.5,
                    "regularMarketVolume": 50000000,
                    "trailingPE": 30.5,
                    "forwardPE": 28.0,
                    "marketCap": 3_000_000_000_000,
                    "fiftyTwoWeekHigh": 200.0,
                    "fiftyTwoWeekLow": 150.0,
                    "currency": "USD",
                }

        class MockYf:
            @staticmethod
            def Ticker(symbol):
                return MockTicker(symbol)

        monkeypatch.setattr("tools.market_data.yf", MockYf())

        from tools.market_data import fetch_stock_realtime
        result = fetch_stock_realtime("AAPL", "US")

        assert result["名称"] == "Apple Inc."
        assert result["现价"] == 195.0
        assert result["market"] == "US"
        assert result["涨跌幅(%)"] is not None

    def test_invalid_market(self):
        """不支持的市场返回错误"""
        from tools.market_data import fetch_stock_realtime
        result = fetch_stock_realtime("000001", "JP")
        assert "error" in result
        assert "不支持" in str(result.get("error", ""))


class TestFetchIndexQuote:
    def test_domestic_index(self, monkeypatch):
        """mock 国内指数行情"""
        df = pd.DataFrame({
            "名称": ["沪深300", "上证指数"],
            "最新价": [3800.0, 3200.0],
            "涨跌幅": [0.5, 0.3],
            "涨跌额": [19.0, 9.6],
            "成交额": [500_000_000_000, 400_000_000_000],
        })

        class MockAk:
            def stock_zh_index_spot_em(self):
                return df

        monkeypatch.setattr("tools.market_data.ak", MockAk())
        monkeypatch.setattr("tools.market_data.yf", None)

        from tools.market_data import fetch_index_quote
        result = fetch_index_quote("沪深300")

        assert result["指数名称"] == "沪深300"
        assert result["最新点位"] == 3800.0
        assert "涨跌幅(%)" in result


class TestFetchCommodity:
    def test_commodity_via_yfinance(self, monkeypatch):
        """mock yfinance 获取大宗商品"""
        class MockTicker:
            def __init__(self, symbol):
                self.info = {
                    "regularMarketPrice": 2400.0,
                    "previousClose": 2380.0,
                }

        class MockYf:
            @staticmethod
            def Ticker(symbol):
                return MockTicker(symbol)

        monkeypatch.setattr("tools.market_data.ak", None)
        monkeypatch.setattr("tools.market_data.yf", MockYf())

        from tools.market_data import fetch_commodity
        result = fetch_commodity("黄金")

        assert result["品种"] == "黄金"
        assert result["最新价"] == 2400.0
        assert "涨跌幅(%)" in result

    def test_commodity_not_found(self, monkeypatch):
        """不支在列表中的商品"""
        monkeypatch.setattr("tools.market_data.ak", None)
        monkeypatch.setattr("tools.market_data.yf", None)

        from tools.market_data import fetch_commodity
        result = fetch_commodity("钻石")
        assert "error" in result


class TestFetchForex:
    def test_unsupported_pair_no_lib(self, monkeypatch):
        """无可用库时返回错误"""
        monkeypatch.setattr("tools.market_data.ak", None)
        monkeypatch.setattr("tools.market_data.yf", None)

        from tools.market_data import fetch_forex
        result = fetch_forex("USDCNY")
        assert "error" in result


# ---------------------------------------------------------------------------
# ETF Tests (Wave 2)
# ---------------------------------------------------------------------------

class TestFetchETFRealtime:
    def test_etf_realtime(self, monkeypatch):
        """mock fund_etf_spot_em 返回ETF行情，验证返回格式。"""
        df = pd.DataFrame({
            "代码": ["510300", "510050", "159919"],
            "名称": ["沪深300ETF", "上证50ETF", "沪深300ETF"],
            "最新价": [4.15, 2.85, 4.10],
            "涨跌幅": [0.50, -0.35, 0.48],
            "成交量": [5000000, 3000000, 2000000],
            "成交额": [20750000, 8550000, 8200000],
            "最新净值": [4.12, 2.83, 4.08],
            "折价率": [0.73, 0.71, 0.49],
            "今开": [4.12, 2.86, 4.08],
            "最高": [4.18, 2.88, 4.13],
            "最低": [4.10, 2.83, 4.06],
            "昨收": [4.13, 2.86, 4.08],
        })

        class MockAk:
            def fund_etf_spot_em(self):
                return df

        monkeypatch.setattr("tools.market_data.ak", MockAk())

        from tools.market_data import fetch_etf_realtime
        result = fetch_etf_realtime("510300")

        assert result["代码"] == "510300"
        assert result["名称"] == "沪深300ETF"
        assert result["现价"] == 4.15
        assert result["market"] == "A"
        assert "涨跌幅(%)" in result
        assert "成交量(手)" in result
        assert "净值" in result

    def test_etf_realtime_not_found(self, monkeypatch):
        """ETF代码不存在时返回错误。"""
        class MockAk:
            def fund_etf_spot_em(self):
                return pd.DataFrame({"代码": ["510300"], "名称": ["沪深300ETF"]})

        monkeypatch.setattr("tools.market_data.ak", MockAk())

        from tools.market_data import fetch_etf_realtime
        result = fetch_etf_realtime("999999")
        assert "error" in result

    def test_etf_realtime_unsupported_market(self):
        """非A股市场返回错误。"""
        from tools.market_data import fetch_etf_realtime
        result = fetch_etf_realtime("SPY", market="US")
        assert "error" in result


class TestFetchETFHistory:
    def test_etf_history(self, monkeypatch):
        """mock fund_etf_hist_em 返回ETF历史数据，验证结构。"""
        df = pd.DataFrame({
            "日期": ["2025-01-02", "2025-01-03", "2025-01-06"],
            "开盘": [4.10, 4.12, 4.15],
            "最高": [4.15, 4.18, 4.20],
            "最低": [4.08, 4.10, 4.12],
            "收盘": [4.12, 4.15, 4.18],
            "成交量": [5000000, 6000000, 5500000],
            "成交额": [20600000, 24900000, 22990000],
        })

        class MockAk:
            def fund_etf_hist_em(self, **kwargs):
                return df

        monkeypatch.setattr("tools.market_data.ak", MockAk())

        from tools.market_data import fetch_etf_history
        result = fetch_etf_history("510300", period="daily")

        assert "error" not in result
        assert "meta" in result
        assert result["meta"]["代码"] == "510300"
        assert result["meta"]["周期"] == "daily"
        assert result["meta"]["数据条数"] == 3
        assert isinstance(result["data"], list)
        assert len(result["data"]) == 3

        rec = result["data"][0]
        for key in ("日期", "开盘", "最高", "最低", "收盘", "成交量"):
            assert key in rec, f"Missing key: {key}"

    def test_etf_history_empty(self, monkeypatch):
        """ETF历史数据为空时返回错误。"""
        class MockAk:
            def fund_etf_hist_em(self, **kwargs):
                return pd.DataFrame()

        monkeypatch.setattr("tools.market_data.ak", MockAk())

        from tools.market_data import fetch_etf_history
        result = fetch_etf_history("510300")
        assert "error" in result


# ---------------------------------------------------------------------------
# Convertible Bond Tests (Wave 2)
# ---------------------------------------------------------------------------

class TestFetchConvertibleBond:
    @pytest.fixture
    def cb_df(self):
        """可转债 DataFrame。"""
        return pd.DataFrame({
            "代码": ["113009", "127012", "128085"],
            "名称": ["广汽转债", "中鼎转2", "鸿达转债"],
            "现价": [110.5, 105.2, 98.3],
            "转股价格": [12.50, 15.80, 8.20],
            "转股价值": [108.0, 100.5, 95.0],
            "溢价率": [2.31, 4.68, 3.47],
            "到期收益率": [1.5, 2.1, 3.5],
            "信用评级": ["AA+", "AA", "AA-"],
            "剩余年限": [3.5, 2.1, 4.2],
        })

    def test_convertible_bond_all(self, monkeypatch, cb_df):
        """获取全部可转债数据列表。"""
        class MockAk:
            def bond_cb_jsl(self):
                return cb_df

        monkeypatch.setattr("tools.market_data.ak", MockAk())

        from tools.market_data import fetch_convertible_bond
        result = fetch_convertible_bond()

        assert "error" not in result
        assert "data" in result
        assert result["count"] == 3
        assert isinstance(result["data"], list)

    def test_convertible_bond_single(self, monkeypatch, cb_df):
        """查询单只可转债。"""
        class MockAk:
            def bond_cb_jsl(self):
                return cb_df

        monkeypatch.setattr("tools.market_data.ak", MockAk())

        from tools.market_data import fetch_convertible_bond
        result = fetch_convertible_bond("113009")

        assert "error" not in result
        assert result["代码"] == "113009"
        assert result["名称"] == "广汽转债"
        assert result["现价"] == 110.5
        for key in ("转股价", "转股价值", "溢价率(%)", "到期收益率(%)", "信用评级"):
            assert key in result, f"Missing key: {key}"

    def test_convertible_bond_not_found(self, monkeypatch, cb_df):
        """查询不存在的可转债代码。"""
        class MockAk:
            def bond_cb_jsl(self):
                return cb_df

        monkeypatch.setattr("tools.market_data.ak", MockAk())

        from tools.market_data import fetch_convertible_bond
        result = fetch_convertible_bond("999999")
        assert "error" in result

    def test_convertible_bond_fallback(self, monkeypatch):
        """主接口失败时使用 fallback 接口。"""
        fallback_df = pd.DataFrame({
            "代码": ["113009"],
            "名称": ["广汽转债"],
            "现价": [110.5],
        })

        class MockAk:
            def bond_cb_jsl(self):
                raise Exception("API unavailable")

            def bond_zh_cov_value_analysis(self):
                return fallback_df

        monkeypatch.setattr("tools.market_data.ak", MockAk())

        from tools.market_data import fetch_convertible_bond
        result = fetch_convertible_bond()

        assert "error" not in result
        assert "data" in result

    def test_convertible_bond_all_fail(self, monkeypatch):
        """主接口和 fallback 都失败时返回错误。"""
        class MockAk:
            def bond_cb_jsl(self):
                raise Exception("Primary fail")

            def bond_zh_cov_value_analysis(self):
                raise Exception("Fallback fail")

        monkeypatch.setattr("tools.market_data.ak", MockAk())

        from tools.market_data import fetch_convertible_bond
        result = fetch_convertible_bond()
        assert "error" in result
