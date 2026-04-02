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
