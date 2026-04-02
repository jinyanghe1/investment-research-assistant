"""期货数据工具测试（全部 mock，无网络调用）"""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def domestic_spot_df():
    """国内期货实时行情 DataFrame。"""
    return pd.DataFrame({
        "symbol": ["AU0", "AG0", "RB0", "I0", "CU0"],
        "name": ["沪金主力", "沪银主力", "螺纹钢主力", "铁矿石主力", "沪铜主力"],
        "current_price": [580.0, 7500.0, 3800.0, 850.0, 72000.0],
        "change": [5.0, 50.0, -20.0, 10.0, 200.0],
        "changepercent": [0.87, 0.67, -0.52, 1.19, 0.28],
        "open": [576.0, 7460.0, 3820.0, 842.0, 71800.0],
        "high": [582.0, 7520.0, 3830.0, 855.0, 72200.0],
        "low": [575.0, 7440.0, 3790.0, 840.0, 71700.0],
        "volume": [100000, 200000, 500000, 300000, 150000],
        "hold": [250000, 400000, 800000, 600000, 350000],
        "settlement": [578.0, 7480.0, 3810.0, 848.0, 71900.0],
    })


@pytest.fixture
def domestic_history_df():
    """国内期货日线历史 DataFrame。"""
    dates = pd.date_range("2025-01-01", periods=30, freq="B")
    return pd.DataFrame({
        "date": dates,
        "open": [3800 + i * 5 for i in range(30)],
        "high": [3820 + i * 5 for i in range(30)],
        "low": [3780 + i * 5 for i in range(30)],
        "close": [3810 + i * 5 for i in range(30)],
        "volume": [500000 + i * 1000 for i in range(30)],
        "hold": [800000 + i * 500 for i in range(30)],
    })


@pytest.fixture
def position_df_with_type():
    """持仓排名 DataFrame（带类型列区分多空）。"""
    return pd.DataFrame({
        "品种": ["rb"] * 6,
        "类型": ["多", "多", "多", "空", "空", "空"],
        "名次": [1, 2, 3, 1, 2, 3],
        "会员简称": ["永安期货", "中信期货", "国泰君安", "海通期货", "银河期货", "华泰期货"],
        "持仓量": [80000, 60000, 45000, 70000, 55000, 40000],
        "增减": [5000, 3000, -2000, -3000, 4000, 1000],
    })


@pytest.fixture
def spot_price_df():
    """现货价格 DataFrame。"""
    return pd.DataFrame({
        "品种": ["AU", "AG", "RB", "CU"],
        "现货价格": [582.0, 7550.0, 3850.0, 72500.0],
    })


# ---------------------------------------------------------------------------
# fetch_futures_realtime Tests
# ---------------------------------------------------------------------------

class TestFuturesRealtime:
    def test_realtime_domestic(self, domestic_spot_df):
        """mock 国内期货实时行情，验证返回字段完整性。"""
        with patch("tools.futures_data.ak") as mock_ak:
            mock_ak.futures_zh_spot.return_value = domestic_spot_df
            from tools.futures_data import fetch_futures_realtime
            result = fetch_futures_realtime("AU0", "domestic")

        assert "error" not in result
        assert result["symbol"] == "AU0"
        assert result["name"] == "沪金主力"
        assert result["price"] == 580.0
        assert result["market"] == "domestic"
        for key in ("change", "change_pct", "open", "high", "low", "volume", "open_interest"):
            assert key in result, f"Missing key: {key}"

    def test_realtime_domestic_fuzzy_match(self, domestic_spot_df):
        """模糊匹配：输入 'au' 应匹配到 AU0。"""
        with patch("tools.futures_data.ak") as mock_ak:
            mock_ak.futures_zh_spot.return_value = domestic_spot_df
            from tools.futures_data import fetch_futures_realtime
            result = fetch_futures_realtime("AU", "domestic")

        # 模糊匹配 AU → AU0
        assert "error" not in result
        assert result["price"] == 580.0

    def test_realtime_domestic_not_found(self, domestic_spot_df):
        """国内期货代码不存在时返回错误。"""
        with patch("tools.futures_data.ak") as mock_ak:
            mock_ak.futures_zh_spot.return_value = domestic_spot_df
            from tools.futures_data import fetch_futures_realtime
            result = fetch_futures_realtime("XXXXXX", "domestic")

        assert "error" in result

    def test_realtime_foreign_yfinance(self):
        """mock yfinance 返回外盘期货行情。"""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "regularMarketPrice": 75.5,
            "previousClose": 74.0,
            "regularMarketOpen": 74.5,
            "regularMarketDayHigh": 76.0,
            "regularMarketDayLow": 73.8,
            "regularMarketVolume": 500000,
        }
        with patch("tools.futures_data.ak", None), \
             patch("tools.futures_data.yf") as mock_yf:
            mock_yf.Ticker.return_value = mock_ticker
            from tools.futures_data import fetch_futures_realtime
            result = fetch_futures_realtime("CL", "foreign")

        assert "error" not in result
        assert result["symbol"] == "CL"
        assert result["name"] == "WTI原油"
        assert result["price"] == 75.5
        assert result["market"] == "foreign"
        assert result["source"] == "yfinance"
        assert result["change_pct"] is not None

    def test_realtime_foreign_akshare(self):
        """外盘期货优先使用 akshare 接口。"""
        foreign_df = pd.DataFrame({
            "name": ["WTI原油"],
            "current_price": [76.0],
            "change": [1.5],
            "changepercent": [2.01],
            "open": [74.5],
            "high": [76.5],
            "low": [74.0],
            "volume": [600000],
        })
        with patch("tools.futures_data.ak") as mock_ak:
            mock_ak.futures_foreign_commodity_realtime.return_value = foreign_df
            from tools.futures_data import fetch_futures_realtime
            result = fetch_futures_realtime("CL", "foreign")

        assert "error" not in result
        assert result["price"] == 76.0
        assert result["source"] == "akshare"

    def test_realtime_invalid_market(self):
        """不支持的市场返回错误。"""
        from tools.futures_data import fetch_futures_realtime
        result = fetch_futures_realtime("AU0", "tokyo")
        assert "error" in result


# ---------------------------------------------------------------------------
# fetch_futures_history Tests
# ---------------------------------------------------------------------------

class TestFuturesHistory:
    def test_history_domestic(self, domestic_history_df):
        """mock 国内期货日线数据，验证返回结构。"""
        with patch("tools.futures_data.ak") as mock_ak:
            mock_ak.futures_zh_daily_sina.return_value = domestic_history_df
            from tools.futures_data import fetch_futures_history
            result = fetch_futures_history("RB0", period="daily")

        assert "error" not in result
        assert result["symbol"] == "RB0"
        assert result["period"] == "daily"
        assert result["market"] == "domestic"
        assert result["count"] > 0
        assert isinstance(result["data"], list)

        # 验证每条记录的字段
        rec = result["data"][0]
        for key in ("date", "open", "high", "low", "close", "volume"):
            assert key in rec, f"Missing key in record: {key}"

    def test_history_domestic_date_filter(self, domestic_history_df):
        """日期过滤应缩小返回数据范围。"""
        with patch("tools.futures_data.ak") as mock_ak:
            mock_ak.futures_zh_daily_sina.return_value = domestic_history_df
            from tools.futures_data import fetch_futures_history
            result = fetch_futures_history(
                "RB0", start_date="2025-01-15", end_date="2025-01-25"
            )

        assert "error" not in result
        assert result["count"] < 30  # 过滤后应少于全部30条

    def test_history_foreign(self):
        """外盘期货历史通过 yfinance 获取。"""
        dates = pd.date_range("2025-01-01", periods=20, freq="B")
        hist_df = pd.DataFrame({
            "Open": [74.0 + i * 0.5 for i in range(20)],
            "High": [75.0 + i * 0.5 for i in range(20)],
            "Low": [73.0 + i * 0.5 for i in range(20)],
            "Close": [74.5 + i * 0.5 for i in range(20)],
            "Volume": [500000 + i * 1000 for i in range(20)],
        }, index=dates)

        with patch("tools.futures_data.ak", None), \
             patch("tools.futures_data.yf") as mock_yf:
            mock_yf.download.return_value = hist_df
            from tools.futures_data import fetch_futures_history
            result = fetch_futures_history("CL", market="foreign")

        assert "error" not in result
        assert result["symbol"] == "CL"
        assert result["name"] == "WTI原油"
        assert result["market"] == "foreign"
        assert result["count"] == 20

    def test_history_empty_data(self):
        """API 返回空 DataFrame 时应返回错误。"""
        with patch("tools.futures_data.ak") as mock_ak:
            mock_ak.futures_zh_daily_sina.return_value = pd.DataFrame()
            from tools.futures_data import fetch_futures_history
            result = fetch_futures_history("RB0")

        assert "error" in result

    def test_history_api_failure(self):
        """akshare 抛出异常时应优雅返回错误。"""
        with patch("tools.futures_data.ak") as mock_ak:
            mock_ak.futures_zh_daily_sina.side_effect = Exception("Connection timeout")
            from tools.futures_data import fetch_futures_history
            result = fetch_futures_history("RB0")

        assert "error" in result


# ---------------------------------------------------------------------------
# fetch_futures_position Tests
# ---------------------------------------------------------------------------

class TestFuturesPosition:
    def test_position_structure(self, position_df_with_type):
        """mock 持仓排名数据，验证 long/short/summary 结构。"""
        with patch("tools.futures_data.ak") as mock_ak:
            mock_ak.futures_dce_position_rank.return_value = position_df_with_type
            from tools.futures_data import fetch_futures_position
            result = fetch_futures_position("rb", exchange="dce", date="20250101")

        assert "error" not in result
        assert result["symbol"] == "rb"
        assert result["exchange"] == "DCE"

        # 多头持仓
        assert isinstance(result["long_positions"], list)
        assert len(result["long_positions"]) == 3

        # 空头持仓
        assert isinstance(result["short_positions"], list)
        assert len(result["short_positions"]) == 3

        # 汇总
        summary = result["summary"]
        assert "total_long" in summary
        assert "total_short" in summary
        assert "net_position" in summary
        assert "long_short_ratio" in summary
        assert summary["total_long"] > 0
        assert summary["total_short"] > 0

    def test_position_exchanges(self):
        """不同交易所参数应调用对应的 akshare 函数。"""
        df = pd.DataFrame({
            "品种": ["au", "au"],
            "类型": ["多", "空"],
            "名次": [1, 1],
            "会员简称": ["永安期货", "海通期货"],
            "持仓量": [50000, 45000],
            "增减": [1000, -500],
        })

        for exchange in ("shfe", "dce", "cffex", "gfex"):
            func_name = f"futures_{exchange}_position_rank"
            with patch("tools.futures_data.ak") as mock_ak:
                setattr(mock_ak, func_name, MagicMock(return_value=df))
                from tools.futures_data import fetch_futures_position
                result = fetch_futures_position("au", exchange=exchange, date="20250101")
            assert "error" not in result, f"Failed for exchange={exchange}: {result}"
            assert result["exchange"] == exchange.upper()

    def test_position_czce(self):
        """郑商所需要额外的 indicator 参数。"""
        df = pd.DataFrame({
            "品种": ["sr", "sr"],
            "类型": ["多", "空"],
            "名次": [1, 1],
            "会员简称": ["永安期货", "海通期货"],
            "持仓量": [30000, 28000],
            "增减": [500, -200],
        })
        with patch("tools.futures_data.ak") as mock_ak:
            mock_ak.futures_czce_position_rank.return_value = df
            from tools.futures_data import fetch_futures_position
            result = fetch_futures_position("sr", exchange="czce", date="20250101")

        assert "error" not in result
        # 验证调用时传入了 indicator 参数
        mock_ak.futures_czce_position_rank.assert_called_once_with(date="20250101", indicator="持仓量")

    def test_position_invalid_exchange(self):
        """不支持的交易所返回错误。"""
        from tools.futures_data import fetch_futures_position
        result = fetch_futures_position("rb", exchange="nyse")
        assert "error" in result

    def test_position_net_calculation(self, position_df_with_type):
        """验证多空净持仓和多空比计算。"""
        with patch("tools.futures_data.ak") as mock_ak:
            mock_ak.futures_dce_position_rank.return_value = position_df_with_type
            from tools.futures_data import fetch_futures_position
            result = fetch_futures_position("rb", exchange="dce", date="20250101")

        summary = result["summary"]
        # 多头: 80000+60000+45000 = 185000
        assert summary["total_long"] == 185000.0
        # 空头: 70000+55000+40000 = 165000
        assert summary["total_short"] == 165000.0
        # 净持仓: 185000-165000 = 20000
        assert summary["net_position"] == 20000.0
        # 多空比: 185000/165000 ≈ 1.12
        assert summary["long_short_ratio"] == pytest.approx(1.12, rel=0.01)


# ---------------------------------------------------------------------------
# fetch_futures_basis Tests
# ---------------------------------------------------------------------------

class TestFuturesBasis:
    def _build_mock_ak(self, spot_price_df, futures_spot_df):
        """构建基差测试用的 mock akshare。"""
        mock_ak = MagicMock()
        mock_ak.futures_spot_price.return_value = spot_price_df
        mock_ak.futures_zh_spot.return_value = futures_spot_df
        return mock_ak

    def test_basis_calculation(self, spot_price_df, domestic_spot_df):
        """验证基差、基差率和合约列表的完整性。"""
        mock_ak = self._build_mock_ak(spot_price_df, domestic_spot_df)
        with patch("tools.futures_data.ak", mock_ak):
            from tools.futures_data import fetch_futures_basis
            result = fetch_futures_basis("AU")

        assert "error" not in result
        assert result["symbol"] == "AU"
        for key in ("spot_price", "futures_price", "basis", "basis_rate",
                     "structure", "contracts", "date"):
            assert key in result, f"Missing key: {key}"
        assert result["spot_price"] == 582.0
        assert result["futures_price"] == 580.0
        # basis = spot - futures = 582 - 580 = 2.0
        assert result["basis"] == 2.0

    def test_basis_backwardation(self):
        """现货 > 期货 → backwardation。"""
        spot_df = pd.DataFrame({
            "品种": ["CU"],
            "现货价格": [73000.0],
        })
        futures_df = pd.DataFrame({
            "symbol": ["CU0"],
            "current_price": [72000.0],
        })
        mock_ak = MagicMock()
        mock_ak.futures_spot_price.return_value = spot_df
        mock_ak.futures_zh_spot.return_value = futures_df

        with patch("tools.futures_data.ak", mock_ak):
            from tools.futures_data import fetch_futures_basis
            result = fetch_futures_basis("CU")

        assert result["structure"] == "backwardation"
        assert result["basis"] > 0

    def test_basis_contango(self):
        """期货 > 现货 → contango。"""
        spot_df = pd.DataFrame({
            "品种": ["RB"],
            "现货价格": [3750.0],
        })
        futures_df = pd.DataFrame({
            "symbol": ["RB0"],
            "current_price": [3800.0],
        })
        mock_ak = MagicMock()
        mock_ak.futures_spot_price.return_value = spot_df
        mock_ak.futures_zh_spot.return_value = futures_df

        with patch("tools.futures_data.ak", mock_ak):
            from tools.futures_data import fetch_futures_basis
            result = fetch_futures_basis("RB")

        assert result["structure"] == "contango"
        assert result["basis"] < 0

    def test_basis_no_spot_price(self, domestic_spot_df):
        """现货价格获取失败时，仅返回期货合约数据并带 warning。"""
        mock_ak = MagicMock()
        mock_ak.futures_spot_price.side_effect = Exception("Spot API down")
        mock_ak.futures_zh_spot.return_value = domestic_spot_df

        with patch("tools.futures_data.ak", mock_ak):
            from tools.futures_data import fetch_futures_basis
            result = fetch_futures_basis("AU")

        # spot_price 为 None，但 futures_price 应该可用
        assert result["spot_price"] is None
        assert result["futures_price"] is not None
        assert "warning" in result

    def test_basis_contracts_list(self):
        """验证返回的合约列表包含多个合约。"""
        spot_df = pd.DataFrame({
            "品种": ["AU"],
            "现货价格": [582.0],
        })
        futures_df = pd.DataFrame({
            "symbol": ["AU0", "AU2406", "AU2412"],
            "current_price": [580.0, 579.0, 585.0],
        })
        mock_ak = MagicMock()
        mock_ak.futures_spot_price.return_value = spot_df
        mock_ak.futures_zh_spot.return_value = futures_df

        with patch("tools.futures_data.ak", mock_ak):
            from tools.futures_data import fetch_futures_basis
            result = fetch_futures_basis("AU")

        contracts = result["contracts"]
        assert len(contracts) == 3
        for c in contracts:
            assert "contract" in c
            assert "price" in c
            assert "basis" in c


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

class TestFuturesEdgeCases:
    def test_empty_data_realtime(self):
        """实时行情 API 返回空 DataFrame。"""
        with patch("tools.futures_data.ak") as mock_ak:
            mock_ak.futures_zh_spot.return_value = pd.DataFrame()
            from tools.futures_data import fetch_futures_realtime
            result = fetch_futures_realtime("AU0", "domestic")

        assert "error" in result

    def test_api_failure_realtime(self):
        """akshare 异常时优雅返回错误。"""
        with patch("tools.futures_data.ak") as mock_ak:
            mock_ak.futures_zh_spot.side_effect = Exception("Network error")
            from tools.futures_data import fetch_futures_realtime
            result = fetch_futures_realtime("AU0", "domestic")

        assert "error" in result

    def test_akshare_none(self):
        """akshare 未安装时返回错误。"""
        with patch("tools.futures_data.ak", None):
            from tools.futures_data import fetch_futures_realtime
            result = fetch_futures_realtime("AU0", "domestic")
        assert "error" in result

        with patch("tools.futures_data.ak", None):
            from tools.futures_data import fetch_futures_basis
            result = fetch_futures_basis("AU")
        assert "error" in result
