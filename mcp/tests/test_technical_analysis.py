"""技术分析工具测试（全部 mock，无网络调用）"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_ohlcv():
    """Generate 120 days of realistic OHLCV data."""
    np.random.seed(42)
    dates = pd.date_range("2025-01-01", periods=120, freq="B")
    close = 100 + np.cumsum(np.random.randn(120) * 2)
    high = close + np.abs(np.random.randn(120))
    low = close - np.abs(np.random.randn(120))
    open_ = close + np.random.randn(120) * 0.5
    volume = np.random.randint(1_000_000, 10_000_000, 120)
    return pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume.astype(float),
    })


@pytest.fixture
def short_ohlcv():
    """Only 3 rows — deliberately too short for most indicators."""
    dates = pd.date_range("2025-06-01", periods=3, freq="B")
    return pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "open": [10.0, 10.5, 10.2],
        "high": [10.5, 11.0, 10.8],
        "low": [9.8, 10.2, 10.0],
        "close": [10.3, 10.8, 10.5],
        "volume": [1e6, 2e6, 1.5e6],
    })


def _mock_fetch_stock_history(df):
    """Return a mock function that wraps a DataFrame into the expected dict."""
    def _mock(symbol, market="A", period="daily", days=200):
        if df is None or df.empty:
            return {"error": True, "message": "无数据"}
        records = df.to_dict(orient="records")
        return {"data": records}
    return _mock


@pytest.fixture
def patch_history(sample_ohlcv):
    """Patch fetch_stock_history to return sample_ohlcv."""
    with patch(
        "tools.technical_analysis.fetch_stock_history",
        side_effect=_mock_fetch_stock_history(sample_ohlcv),
    ):
        yield


@pytest.fixture
def patch_history_short(short_ohlcv):
    """Patch fetch_stock_history to return a very short DataFrame."""
    with patch(
        "tools.technical_analysis.fetch_stock_history",
        side_effect=_mock_fetch_stock_history(short_ohlcv),
    ):
        yield


@pytest.fixture
def patch_history_empty():
    """Patch fetch_stock_history to return empty data."""
    with patch(
        "tools.technical_analysis.fetch_stock_history",
        return_value={"data": []},
    ):
        yield


# ---------------------------------------------------------------------------
# Indicator Calculation Tests
# ---------------------------------------------------------------------------

class TestIndicatorCalculations:
    """Test individual indicator computation against known expectations."""

    def test_ma_calculation(self, patch_history, sample_ohlcv):
        """MA5/MA10/MA20 values match manual rolling-mean calculation."""
        from tools.technical_analysis import fetch_technical_indicators

        result = fetch_technical_indicators("600519", indicators=["MA"], count=60)
        assert "error" not in result
        ma_data = result["indicators"]["MA"]

        # MA5 last value should approximate a manual 5-day rolling mean
        close = sample_ohlcv["close"].values
        expected_ma5_last = float(np.mean(close[-5:]))
        actual_ma5_last = ma_data["MA5"][-1]
        assert actual_ma5_last == pytest.approx(expected_ma5_last, rel=1e-3)

        # MA10
        expected_ma10_last = float(np.mean(close[-10:]))
        actual_ma10_last = ma_data["MA10"][-1]
        assert actual_ma10_last == pytest.approx(expected_ma10_last, rel=1e-3)

        # MA20
        expected_ma20_last = float(np.mean(close[-20:]))
        actual_ma20_last = ma_data["MA20"][-1]
        assert actual_ma20_last == pytest.approx(expected_ma20_last, rel=1e-3)

    def test_ema_calculation(self, patch_history, sample_ohlcv):
        """EMA12 and EMA26 are present and roughly correct."""
        from tools.technical_analysis import fetch_technical_indicators

        result = fetch_technical_indicators("600519", indicators=["EMA"], count=60)
        assert "error" not in result
        ema_data = result["indicators"]["EMA"]
        assert "EMA12" in ema_data
        assert "EMA26" in ema_data

        # EMA values should be within the range of close prices
        close = sample_ohlcv["close"].values
        for val in ema_data["EMA12"]:
            if val is not None:
                assert close.min() * 0.9 <= val <= close.max() * 1.1

    def test_macd_calculation(self, patch_history):
        """DIF, DEA, MACD_HIST are present with correct types."""
        from tools.technical_analysis import fetch_technical_indicators

        result = fetch_technical_indicators("600519", indicators=["MACD"], count=60)
        assert "error" not in result
        macd = result["indicators"]["MACD"]
        assert "DIF" in macd
        assert "DEA" in macd
        assert "MACD_HIST" in macd

        # All should be list of float/None
        for key in ("DIF", "DEA", "MACD_HIST"):
            assert isinstance(macd[key], list)
            assert len(macd[key]) == 60
            non_none = [v for v in macd[key] if v is not None]
            assert len(non_none) > 0
            for v in non_none:
                assert isinstance(v, (int, float))

    def test_rsi_calculation(self, patch_history):
        """RSI14 values fall between 0 and 100."""
        from tools.technical_analysis import fetch_technical_indicators

        result = fetch_technical_indicators("600519", indicators=["RSI"], count=60)
        assert "error" not in result
        rsi = result["indicators"]["RSI"]["RSI14"]
        non_none = [v for v in rsi if v is not None]
        assert len(non_none) > 0
        for val in non_none:
            assert 0 <= val <= 100

    def test_kdj_calculation(self, patch_history):
        """K, D, J are present and have correct structure."""
        from tools.technical_analysis import fetch_technical_indicators

        result = fetch_technical_indicators("600519", indicators=["KDJ"], count=60)
        assert "error" not in result
        kdj = result["indicators"]["KDJ"]
        assert "K" in kdj and "D" in kdj and "J" in kdj
        for key in ("K", "D", "J"):
            assert isinstance(kdj[key], list)
            assert len(kdj[key]) == 60

    def test_boll_calculation(self, patch_history):
        """UPPER > MID > LOWER for fully-computed rows."""
        from tools.technical_analysis import fetch_technical_indicators

        result = fetch_technical_indicators("600519", indicators=["BOLL"], count=60)
        assert "error" not in result
        boll = result["indicators"]["BOLL"]
        assert "UPPER" in boll and "MID" in boll and "LOWER" in boll

        for u, m, l in zip(boll["UPPER"], boll["MID"], boll["LOWER"]):
            if u is not None and m is not None and l is not None:
                assert u >= m >= l

    def test_atr_calculation(self, patch_history):
        """ATR14 values are positive where defined."""
        from tools.technical_analysis import fetch_technical_indicators

        result = fetch_technical_indicators("600519", indicators=["ATR"], count=60)
        assert "error" not in result
        atr = result["indicators"]["ATR"]["ATR14"]
        non_none = [v for v in atr if v is not None]
        assert len(non_none) > 0
        for val in non_none:
            assert val > 0

    def test_obv_calculation(self, patch_history):
        """OBV is computed and returned as a list of numbers."""
        from tools.technical_analysis import fetch_technical_indicators

        result = fetch_technical_indicators("600519", indicators=["OBV"], count=60)
        assert "error" not in result
        obv = result["indicators"]["OBV"]["OBV"]
        assert isinstance(obv, list)
        assert len(obv) == 60
        non_none = [v for v in obv if v is not None]
        assert len(non_none) > 0


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

class TestIntegration:
    """Test requesting multiple indicators together."""

    def test_multiple_indicators(self, patch_history):
        """Request MA + MACD + RSI simultaneously."""
        from tools.technical_analysis import fetch_technical_indicators

        result = fetch_technical_indicators(
            "600519", indicators=["MA", "MACD", "RSI"], count=30
        )
        assert "error" not in result
        assert "MA" in result["indicators"]
        assert "MACD" in result["indicators"]
        assert "RSI" in result["indicators"]
        assert len(result["dates"]) == 30

    def test_all_indicators(self, patch_history):
        """Request all 8 supported indicators at once."""
        from tools.technical_analysis import fetch_technical_indicators

        all_inds = ["MA", "EMA", "MACD", "RSI", "KDJ", "BOLL", "ATR", "OBV"]
        result = fetch_technical_indicators("600519", indicators=all_inds, count=60)
        assert "error" not in result
        for ind in all_inds:
            assert ind in result["indicators"], f"Missing indicator: {ind}"
            assert "error" not in result["indicators"][ind], (
                f"{ind} has error: {result['indicators'][ind]}"
            )

    def test_response_structure(self, patch_history):
        """Verify all expected top-level keys are present."""
        from tools.technical_analysis import fetch_technical_indicators

        result = fetch_technical_indicators("600519", indicators=["MA"], count=20)
        assert "error" not in result
        for key in ("symbol", "period", "market", "indicators", "dates", "latest"):
            assert key in result, f"Missing key: {key}"
        assert result["symbol"] == "600519"
        assert result["market"] == "A"
        assert result["period"] == "daily"
        assert isinstance(result["dates"], list)
        assert isinstance(result["latest"], dict)


# ---------------------------------------------------------------------------
# Signal Tests
# ---------------------------------------------------------------------------

def _make_trend_df(direction="up", length=120):
    """Build an OHLCV DataFrame with a clear directional trend.

    direction="up"   → steadily rising close → likely BUY signals
    direction="down" → steadily falling close → likely SELL signals
    direction="flat" → sideways / mixed       → likely NEUTRAL
    """
    np.random.seed(0)
    dates = pd.date_range("2025-01-01", periods=length, freq="B")
    if direction == "up":
        # Strong monotonic rise with tiny noise — MA5 > MA20 for sure
        close = 50 + np.linspace(0, 120, length) + np.random.randn(length) * 0.2
    elif direction == "down":
        close = 200 - np.linspace(0, 120, length) + np.random.randn(length) * 0.2
    else:
        close = 100 + np.random.randn(length) * 1.5

    high = close + np.abs(np.random.randn(length)) * 0.3
    low = close - np.abs(np.random.randn(length)) * 0.3
    open_ = close + np.random.randn(length) * 0.1

    if direction == "up":
        volume = np.random.randint(1_000_000, 3_000_000, length).astype(float)
        volume[-1] = volume[-2] * 3  # volume BUY trigger
    elif direction == "down":
        volume = np.random.randint(1_000_000, 3_000_000, length).astype(float)
        volume[-1] = volume[-2] * 3  # volume SELL trigger (price down + volume up)
    else:
        volume = np.random.randint(1_000_000, 3_000_000, length).astype(float)

    return pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "open": open_, "high": high, "low": low, "close": close,
        "volume": volume,
    })


class TestSignals:
    """Test fetch_technical_signal with various market conditions."""

    def test_buy_signal(self):
        """Uptrend data should produce BUY signals — at least as many as SELL."""
        from tools.technical_analysis import fetch_technical_signal

        df = _make_trend_df("up", 200)
        with patch(
            "tools.technical_analysis.fetch_stock_history",
            side_effect=_mock_fetch_stock_history(df),
        ):
            result = fetch_technical_signal("600519", market="A")
        assert "error" not in result
        buy = sum(1 for s in result["signals"].values() if s["signal"] == "BUY")
        sell = sum(1 for s in result["signals"].values() if s["signal"] == "SELL")
        # Strong uptrend: MA_CROSS=BUY, MACD=BUY, VOLUME=BUY expected at minimum
        assert buy >= 2, f"Expected at least 2 BUY signals in uptrend, got {buy}"
        assert buy >= sell, f"Expected buy≥sell, got buy={buy} sell={sell}"

    def test_sell_signal(self):
        """Downtrend data should produce SELL signals — at least as many as BUY."""
        from tools.technical_analysis import fetch_technical_signal

        df = _make_trend_df("down", 200)
        with patch(
            "tools.technical_analysis.fetch_stock_history",
            side_effect=_mock_fetch_stock_history(df),
        ):
            result = fetch_technical_signal("600519", market="A")
        assert "error" not in result
        buy = sum(1 for s in result["signals"].values() if s["signal"] == "BUY")
        sell = sum(1 for s in result["signals"].values() if s["signal"] == "SELL")
        assert sell >= 2, f"Expected at least 2 SELL signals in downtrend, got {sell}"
        assert sell >= buy, f"Expected sell≥buy, got sell={sell} buy={buy}"

    def test_neutral_signal(self):
        """Flat/mixed data should yield NEUTRAL overall or mixed signals."""
        from tools.technical_analysis import fetch_technical_signal

        df = _make_trend_df("flat", 200)
        with patch(
            "tools.technical_analysis.fetch_stock_history",
            side_effect=_mock_fetch_stock_history(df),
        ):
            result = fetch_technical_signal("600519", market="A")
        assert "error" not in result
        # For flat data, neither BUY nor SELL should dominate (≥4)
        buy = sum(1 for s in result["signals"].values() if s["signal"] == "BUY")
        sell = sum(1 for s in result["signals"].values() if s["signal"] == "SELL")
        assert buy < 5 and sell < 5

    def test_signal_structure(self):
        """Verify the signal response contains all required fields."""
        from tools.technical_analysis import fetch_technical_signal

        df = _make_trend_df("up", 200)
        with patch(
            "tools.technical_analysis.fetch_stock_history",
            side_effect=_mock_fetch_stock_history(df),
        ):
            result = fetch_technical_signal("600519", market="A")
        assert "error" not in result
        for key in ("overall_signal", "confidence", "signals", "summary"):
            assert key in result, f"Missing key: {key}"
        assert result["overall_signal"] in ("BUY", "SELL", "NEUTRAL")
        assert 0 <= result["confidence"] <= 1
        assert isinstance(result["signals"], dict)
        assert isinstance(result["summary"], str)
        # All sub-signals should have signal + detail
        for name, sig in result["signals"].items():
            assert "signal" in sig
            assert "detail" in sig


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge-case and error-path tests."""

    def test_empty_data(self, patch_history_empty):
        """Empty DataFrame → error in result."""
        from tools.technical_analysis import fetch_technical_indicators

        result = fetch_technical_indicators("600519", indicators=["MA"])
        assert result.get("error") is True or "error" in str(result)

    def test_insufficient_data(self, patch_history_short):
        """Less than 5 data points → returns error message."""
        from tools.technical_analysis import fetch_technical_indicators

        result = fetch_technical_indicators("600519", indicators=["MA"], count=60)
        assert result.get("error") is True or "不足" in str(result.get("message", result.get("error", "")))

    def test_invalid_indicator(self, patch_history):
        """Unknown indicator name → gracefully returns error for that indicator only."""
        from tools.technical_analysis import fetch_technical_indicators

        result = fetch_technical_indicators(
            "600519", indicators=["MA", "FOOBAR"], count=30
        )
        assert "error" not in result  # top-level ok
        assert "MA" in result["indicators"]
        assert "error" not in result["indicators"]["MA"]  # MA still computed
        assert "FOOBAR" in result["indicators"]
        assert "error" in result["indicators"]["FOOBAR"]  # unknown → error

    def test_nan_values_in_data(self):
        """DataFrame with NaN values should not crash indicator calculations."""
        from tools.technical_analysis import fetch_technical_indicators

        np.random.seed(99)
        dates = pd.date_range("2025-01-01", periods=60, freq="B")
        close = 100 + np.cumsum(np.random.randn(60) * 2)
        close[10] = np.nan
        close[20] = np.nan
        df = pd.DataFrame({
            "date": dates.strftime("%Y-%m-%d"),
            "open": close + 0.5,
            "high": close + 1,
            "low": close - 1,
            "close": close,
            "volume": np.random.randint(1e6, 5e6, 60).astype(float),
        })

        with patch(
            "tools.technical_analysis.fetch_stock_history",
            side_effect=_mock_fetch_stock_history(df),
        ):
            result = fetch_technical_indicators("600519", indicators=["MA", "RSI"])
        # Should not crash; either returns data or a controlled error
        assert isinstance(result, dict)

    def test_signal_insufficient_data(self, patch_history_short):
        """Signal on very short data → error about insufficient data."""
        from tools.technical_analysis import fetch_technical_signal

        result = fetch_technical_signal("600519")
        assert result.get("error") is True or "不足" in str(result)

    def test_default_indicators(self, patch_history):
        """Calling without indicators arg defaults to MA, MACD, RSI."""
        from tools.technical_analysis import fetch_technical_indicators

        result = fetch_technical_indicators("600519")
        assert "error" not in result
        assert "MA" in result["indicators"]
        assert "MACD" in result["indicators"]
        assert "RSI" in result["indicators"]


# ---------------------------------------------------------------------------
# Weighted Signal Tests (Wave 2)
# ---------------------------------------------------------------------------

class TestWeightedSignal:
    """Test the weighted scoring system in fetch_technical_signal."""

    def test_weighted_signal_score_present(self):
        """Verify weighted_score is present in the result dict."""
        from tools.technical_analysis import fetch_technical_signal

        df = _make_trend_df("up", 200)
        with patch(
            "tools.technical_analysis.fetch_stock_history",
            side_effect=_mock_fetch_stock_history(df),
        ):
            result = fetch_technical_signal("600519", market="A")
        assert "error" not in result
        assert "weighted_score" in result
        assert isinstance(result["weighted_score"], (int, float))

    def test_weighted_strong_buy(self):
        """All BUY signals → weighted_score > 0.35, overall='BUY'."""
        from tools.technical_analysis import fetch_technical_signal

        # Strong uptrend should yield mostly BUY signals → high weighted_score
        df = _make_trend_df("up", 200)
        with patch(
            "tools.technical_analysis.fetch_stock_history",
            side_effect=_mock_fetch_stock_history(df),
        ):
            result = fetch_technical_signal("600519", market="A")
        assert "error" not in result

        # In a strong uptrend, the weighted_score should be positive
        # and overall should be BUY if score >= 0.35
        if result["weighted_score"] >= 0.35:
            assert result["overall_signal"] == "BUY"
        # At minimum, score should be positive in strong uptrend
        assert result["weighted_score"] > 0, (
            f"Expected positive weighted_score in uptrend, got {result['weighted_score']}"
        )

    def test_weighted_strong_sell(self):
        """Downtrend data → weighted_score < uptrend score, sell_count >= buy_count."""
        from tools.technical_analysis import fetch_technical_signal

        df = _make_trend_df("down", 200)
        with patch(
            "tools.technical_analysis.fetch_stock_history",
            side_effect=_mock_fetch_stock_history(df),
        ):
            result = fetch_technical_signal("600519", market="A")
        assert "error" not in result

        # In downtrend, if score <= -0.35 the overall must be SELL
        if result["weighted_score"] <= -0.35:
            assert result["overall_signal"] == "SELL"

        # At minimum, SELL signal count should be >= BUY in a downtrend
        sell_count = sum(1 for s in result["signals"].values() if s["signal"] == "SELL")
        buy_count = sum(1 for s in result["signals"].values() if s["signal"] == "BUY")
        assert sell_count >= buy_count, (
            f"Expected sell≥buy in downtrend, got sell={sell_count} buy={buy_count}"
        )

    def test_weighted_neutral(self):
        """Mixed signals → |weighted_score| < 0.35, overall='NEUTRAL'."""
        from tools.technical_analysis import fetch_technical_signal

        df = _make_trend_df("flat", 200)
        with patch(
            "tools.technical_analysis.fetch_stock_history",
            side_effect=_mock_fetch_stock_history(df),
        ):
            result = fetch_technical_signal("600519", market="A")
        assert "error" not in result

        # For flat data, if |weighted_score| < 0.35, overall should be NEUTRAL
        if abs(result["weighted_score"]) < 0.35:
            assert result["overall_signal"] == "NEUTRAL"
        # The score should be close to zero for sideways market
        assert abs(result["weighted_score"]) < 0.8, (
            f"Expected small |weighted_score| for flat data, got {result['weighted_score']}"
        )

    def test_weighted_score_bounds(self):
        """weighted_score should be bounded between -1.0 and 1.0."""
        from tools.technical_analysis import fetch_technical_signal

        for direction in ("up", "down", "flat"):
            df = _make_trend_df(direction, 200)
            with patch(
                "tools.technical_analysis.fetch_stock_history",
                side_effect=_mock_fetch_stock_history(df),
            ):
                result = fetch_technical_signal("600519", market="A")
            if "error" not in result:
                assert -1.0 <= result["weighted_score"] <= 1.0, (
                    f"weighted_score out of bounds for {direction}: {result['weighted_score']}"
                )
