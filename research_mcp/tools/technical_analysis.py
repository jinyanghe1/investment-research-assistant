#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术分析工具集 —— 提供股票技术指标计算与交易信号判断能力。
通过 register_tools(mcp) 注册到 FastMCP 实例。

支持指标: MA, EMA, MACD, RSI, KDJ, BOLL, ATR, OBV
"""

import os
import sys
from datetime import datetime

# ---------------------------------------------------------------------------
# 基础设施
# ---------------------------------------------------------------------------
_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _base not in sys.path:
    sys.path.insert(0, _base)

from config import config
from utils.errors import handle_errors

try:
    from utils.formatters import safe_round as _round, date_to_str as _date_str
except Exception:
    def _round(val, decimals=2):
        try:
            return round(float(val), decimals)
        except (TypeError, ValueError):
            return val

    def _date_str(val):
        if val is None:
            return None
        if isinstance(val, str):
            return val[:10]
        try:
            return val.strftime("%Y-%m-%d")
        except Exception:
            return str(val)[:10]

# ---------------------------------------------------------------------------
# 第三方库（保护性导入）
# ---------------------------------------------------------------------------
try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import numpy as np
except ImportError:
    np = None

from research_mcp.tools.market_data import fetch_stock_history


# ---------------------------------------------------------------------------
# 内部辅助：将 Series 转为 list[float]，处理 NaN
# ---------------------------------------------------------------------------
def _series_to_list(s, decimals: int = 4) -> list:
    """将 pandas Series 转为 Python float 列表，NaN → None。"""
    result = []
    for v in s:
        if pd and pd.isna(v):
            result.append(None)
        else:
            result.append(_round(v, decimals))
    return result


def _safe_float(val, decimals: int = 4):
    """安全取 float，NaN → None。"""
    if val is None:
        return None
    if pd and pd.isna(val):
        return None
    return _round(val, decimals)


# ---------------------------------------------------------------------------
# 内部辅助：从 fetch_stock_history 结果构建 DataFrame
# ---------------------------------------------------------------------------
def _history_to_df(symbol: str, market: str = "A", period: str = "daily",
                   extra_days: int = 200) -> "pd.DataFrame":
    """
    调用 fetch_stock_history 获取历史数据，返回标准化的 OHLCV DataFrame。
    多取 extra_days 天数据以确保长周期指标（如 MA60）有足够前置数据。
    """
    if pd is None:
        raise RuntimeError("pandas 未安装，无法进行技术分析计算")

    result = fetch_stock_history(symbol, market=market, period=period, days=extra_days)
    if not result or result.get("error"):
        msg = result.get("message", result.get("error", "未知错误")) if result else "无数据"
        raise ValueError(f"获取 {symbol} 历史数据失败: {msg}")

    data = result.get("data", [])
    if not data:
        raise ValueError(f"{symbol} 历史数据为空")

    df = pd.DataFrame(data)

    # 统一列名（A 股中文列 → 英文列）
    col_map = {
        "日期": "date", "开盘": "open", "最高": "high",
        "最低": "low", "收盘": "close", "成交量": "volume", "成交额": "amount",
        "涨跌幅(%)": "pct_change",
        # US/HK 英文列保持不变
        "Date": "date", "Open": "open", "High": "high",
        "Low": "low", "Close": "close", "Volume": "volume",
    }
    df.rename(columns={k: v for k, v in col_map.items() if k in df.columns}, inplace=True)

    required = ["date", "open", "high", "low", "close"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"历史数据缺少必要列: {col}")

    # 确保数值列为 float
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 按日期升序
    df.sort_values("date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


# ---------------------------------------------------------------------------
# 指标计算函数
# ---------------------------------------------------------------------------
def _calc_ma(df: "pd.DataFrame", windows: list[int] = None) -> dict:
    """计算简单移动平均线。"""
    if windows is None:
        windows = [5, 10, 20, 60]
    result = {}
    for n in windows:
        if len(df) >= n:
            result[f"MA{n}"] = df["close"].rolling(window=n).mean()
        else:
            result[f"MA{n}"] = pd.Series([None] * len(df), index=df.index)
    return result


def _calc_ema(df: "pd.DataFrame", spans: list[int] = None) -> dict:
    """计算指数移动平均线。"""
    if spans is None:
        spans = [12, 26]
    result = {}
    for n in spans:
        result[f"EMA{n}"] = df["close"].ewm(span=n, adjust=False).mean()
    return result


def _calc_macd(df: "pd.DataFrame", fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """计算 MACD (DIF, DEA, MACD柱)。"""
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd_hist = 2 * (dif - dea)
    return {"DIF": dif, "DEA": dea, "MACD_HIST": macd_hist}


def _calc_rsi(df: "pd.DataFrame", n: int = 14) -> dict:
    """计算 RSI 相对强弱指数。"""
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return {f"RSI{n}": rsi}


def _calc_kdj(df: "pd.DataFrame", n: int = 9, m1: int = 3, m2: int = 3) -> dict:
    """计算 KDJ 随机指标。"""
    low_n = df["low"].rolling(window=n).min()
    high_n = df["high"].rolling(window=n).max()
    rsv = (df["close"] - low_n) / (high_n - low_n) * 100
    rsv = rsv.fillna(50)  # 极端情况下 high == low
    k = rsv.ewm(alpha=1 / m1, adjust=False).mean()
    d = k.ewm(alpha=1 / m2, adjust=False).mean()
    j = 3 * k - 2 * d
    return {"K": k, "D": d, "J": j}


def _calc_boll(df: "pd.DataFrame", n: int = 20, multiplier: float = 2.0) -> dict:
    """计算布林带。"""
    mid = df["close"].rolling(window=n).mean()
    std = df["close"].rolling(window=n).std()
    upper = mid + multiplier * std
    lower = mid - multiplier * std
    return {"UPPER": upper, "MID": mid, "LOWER": lower}


def _calc_atr(df: "pd.DataFrame", n: int = 14) -> dict:
    """计算 ATR 平均真实波幅。"""
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"] - df["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(window=n).mean()
    return {f"ATR{n}": atr}


def _calc_obv(df: "pd.DataFrame") -> dict:
    """计算 OBV 能量潮。"""
    if "volume" not in df.columns:
        return {"OBV": pd.Series([None] * len(df), index=df.index)}
    close_diff = df["close"].diff()
    direction = pd.Series(0, index=df.index, dtype=float)
    direction[close_diff > 0] = 1.0
    direction[close_diff < 0] = -1.0
    obv = (direction * df["volume"]).cumsum()
    return {"OBV": obv}


# 指标名称 → 计算函数映射
_INDICATOR_FUNCS = {
    "MA": _calc_ma,
    "EMA": _calc_ema,
    "MACD": _calc_macd,
    "RSI": _calc_rsi,
    "KDJ": _calc_kdj,
    "BOLL": _calc_boll,
    "ATR": _calc_atr,
    "OBV": _calc_obv,
}

_ALL_INDICATORS = list(_INDICATOR_FUNCS.keys())


# ---------------------------------------------------------------------------
# 业务逻辑独立函数
# ---------------------------------------------------------------------------
@handle_errors
def fetch_technical_indicators(
    symbol: str,
    indicators: list = None,
    period: str = "daily",
    market: str = "A",
    count: int = 60,
) -> dict:
    """获取股票技术指标数据的核心逻辑。"""
    if indicators is None:
        indicators = ["MA", "MACD", "RSI"]

    market = market.upper()
    indicators = [ind.upper() for ind in indicators]
    count = min(count, config.max_records)

    # 多取数据以确保长周期指标有足够前置数据
    fetch_days = max(count + 200, 365)
    df = _history_to_df(symbol, market=market, period=period, extra_days=fetch_days)

    if len(df) < 5:
        return {"error": f"{symbol} 历史数据不足（仅 {len(df)} 条），无法计算技术指标"}

    # 计算所有请求的指标
    indicator_results = {}
    for ind_name in indicators:
        calc_fn = _INDICATOR_FUNCS.get(ind_name)
        if calc_fn is None:
            indicator_results[ind_name] = {"error": f"不支持的指标: {ind_name}"}
            continue
        try:
            raw = calc_fn(df)
            indicator_results[ind_name] = {
                k: _series_to_list(v.tail(count)) for k, v in raw.items()
            }
        except Exception as e:
            indicator_results[ind_name] = {"error": f"计算失败: {str(e)}"}

    # 日期列表（取最后 count 条）
    tail_df = df.tail(count)
    dates = [_date_str(d) for d in tail_df["date"]]

    # 提取最新值
    latest = {}
    for ind_name, ind_data in indicator_results.items():
        if "error" in ind_data:
            latest[ind_name] = ind_data
            continue
        latest[ind_name] = {}
        for sub_key, vals in ind_data.items():
            if vals:
                # 取最后一个非 None 的值
                for v in reversed(vals):
                    if v is not None:
                        latest[ind_name][sub_key] = v
                        break
                else:
                    latest[ind_name][sub_key] = None
            else:
                latest[ind_name][sub_key] = None

    return {
        "symbol": symbol,
        "period": period,
        "market": market,
        "indicators": indicator_results,
        "dates": dates,
        "latest": latest,
        "data_points": len(dates),
    }


@handle_errors
def fetch_technical_signal(symbol: str, market: str = "A") -> dict:
    """生成股票技术面综合交易信号的核心逻辑。"""
    market = market.upper()

    # 获取足够数据用于计算所有指标
    df = _history_to_df(symbol, market=market, period="daily", extra_days=365)

    if len(df) < 26:
        return {"error": f"{symbol} 历史数据不足（仅 {len(df)} 条），无法生成技术信号"}

    # 计算所有需要的指标
    ma_data = _calc_ma(df, [5, 10, 20, 60])
    macd_data = _calc_macd(df)
    rsi_data = _calc_rsi(df, 14)
    kdj_data = _calc_kdj(df)
    boll_data = _calc_boll(df)

    # 取最新值
    latest_close = float(df["close"].iloc[-1])
    prev_close = float(df["close"].iloc[-2]) if len(df) >= 2 else latest_close

    # 成交量数据
    has_volume = "volume" in df.columns and df["volume"].notna().any()
    if has_volume:
        latest_vol = float(df["volume"].iloc[-1])
        prev_vol = float(df["volume"].iloc[-2]) if len(df) >= 2 else latest_vol
    else:
        latest_vol = prev_vol = 0

    signals = {}

    # --- 1. MA 交叉信号 ---
    ma5 = _safe_float(ma_data["MA5"].iloc[-1])
    ma20 = _safe_float(ma_data["MA20"].iloc[-1])
    prev_ma5 = _safe_float(ma_data["MA5"].iloc[-2]) if len(df) >= 2 else None
    prev_ma20 = _safe_float(ma_data["MA20"].iloc[-2]) if len(df) >= 2 else None

    if ma5 is not None and ma20 is not None:
        if ma5 > ma20:
            # 检查是否刚金叉
            if prev_ma5 is not None and prev_ma20 is not None and prev_ma5 <= prev_ma20:
                signals["MA_CROSS"] = {"signal": "BUY", "detail": "MA5上穿MA20, 金叉"}
            else:
                signals["MA_CROSS"] = {"signal": "BUY", "detail": f"MA5({ma5:.2f})>MA20({ma20:.2f}), 多头排列"}
        elif ma5 < ma20:
            if prev_ma5 is not None and prev_ma20 is not None and prev_ma5 >= prev_ma20:
                signals["MA_CROSS"] = {"signal": "SELL", "detail": "MA5下穿MA20, 死叉"}
            else:
                signals["MA_CROSS"] = {"signal": "SELL", "detail": f"MA5({ma5:.2f})<MA20({ma20:.2f}), 空头排列"}
        else:
            signals["MA_CROSS"] = {"signal": "NEUTRAL", "detail": "MA5与MA20交汇, 方向不明"}
    else:
        signals["MA_CROSS"] = {"signal": "NEUTRAL", "detail": "数据不足, 无法判断均线交叉"}

    # --- 2. MACD 信号 ---
    dif = _safe_float(macd_data["DIF"].iloc[-1])
    dea = _safe_float(macd_data["DEA"].iloc[-1])
    hist = _safe_float(macd_data["MACD_HIST"].iloc[-1])
    prev_dif = _safe_float(macd_data["DIF"].iloc[-2]) if len(df) >= 2 else None
    prev_dea = _safe_float(macd_data["DEA"].iloc[-2]) if len(df) >= 2 else None

    if dif is not None and dea is not None:
        if dif > dea and hist is not None and hist > 0:
            if prev_dif is not None and prev_dea is not None and prev_dif <= prev_dea:
                signals["MACD"] = {"signal": "BUY", "detail": "DIF上穿DEA, MACD柱由负转正"}
            else:
                signals["MACD"] = {"signal": "BUY", "detail": f"DIF({dif:.4f})>DEA({dea:.4f}), MACD柱为正"}
        elif dif < dea and hist is not None and hist < 0:
            if prev_dif is not None and prev_dea is not None and prev_dif >= prev_dea:
                signals["MACD"] = {"signal": "SELL", "detail": "DIF下穿DEA, MACD柱由正转负"}
            else:
                signals["MACD"] = {"signal": "SELL", "detail": f"DIF({dif:.4f})<DEA({dea:.4f}), MACD柱为负"}
        else:
            signals["MACD"] = {"signal": "NEUTRAL", "detail": "MACD信号不明确"}
    else:
        signals["MACD"] = {"signal": "NEUTRAL", "detail": "数据不足, 无法判断MACD"}

    # --- 3. RSI 信号 ---
    rsi_val = _safe_float(rsi_data["RSI14"].iloc[-1])
    if rsi_val is not None:
        if rsi_val < 30:
            signals["RSI"] = {"signal": "BUY", "detail": f"RSI={rsi_val:.1f}<30, 超卖区"}
        elif rsi_val > 70:
            signals["RSI"] = {"signal": "SELL", "detail": f"RSI={rsi_val:.1f}>70, 超买区"}
        else:
            signals["RSI"] = {"signal": "NEUTRAL", "detail": f"RSI={rsi_val:.1f}, 中性区间"}
    else:
        signals["RSI"] = {"signal": "NEUTRAL", "detail": "数据不足, 无法计算RSI"}

    # --- 4. KDJ 信号 ---
    k_val = _safe_float(kdj_data["K"].iloc[-1])
    j_val = _safe_float(kdj_data["J"].iloc[-1])
    if k_val is not None and j_val is not None:
        if k_val < 20 and j_val < 0:
            signals["KDJ"] = {"signal": "BUY", "detail": f"K={k_val:.1f}<20, J={j_val:.1f}<0, 超卖区"}
        elif k_val > 80 and j_val > 100:
            signals["KDJ"] = {"signal": "SELL", "detail": f"K={k_val:.1f}>80, J={j_val:.1f}>100, 超买区"}
        else:
            d_val = _safe_float(kdj_data["D"].iloc[-1])
            d_display = f"{d_val:.1f}" if d_val is not None else "N/A"
            signals["KDJ"] = {
                "signal": "NEUTRAL",
                "detail": f"K={k_val:.1f}, D={d_display}, J={j_val:.1f}, 中性区间",
            }
    else:
        signals["KDJ"] = {"signal": "NEUTRAL", "detail": "数据不足, 无法计算KDJ"}

    # --- 5. BOLL 信号 ---
    upper = _safe_float(boll_data["UPPER"].iloc[-1])
    mid = _safe_float(boll_data["MID"].iloc[-1])
    lower = _safe_float(boll_data["LOWER"].iloc[-1])
    if upper is not None and lower is not None:
        if latest_close < lower:
            signals["BOLL"] = {"signal": "BUY", "detail": f"价格({latest_close:.2f})跌破下轨({lower:.2f}), 超卖"}
        elif latest_close > upper:
            signals["BOLL"] = {"signal": "SELL", "detail": f"价格({latest_close:.2f})突破上轨({upper:.2f}), 超买"}
        else:
            signals["BOLL"] = {"signal": "NEUTRAL", "detail": f"价格在布林带内, 中轨={mid:.2f}"}
    else:
        signals["BOLL"] = {"signal": "NEUTRAL", "detail": "数据不足, 无法计算布林带"}

    # --- 6. 量价信号 ---
    if has_volume and latest_vol > 0 and prev_vol > 0:
        price_up = latest_close > prev_close
        vol_up = latest_vol > prev_vol * 1.1  # 放量阈值 10%
        if price_up and vol_up:
            signals["VOLUME"] = {"signal": "BUY", "detail": "放量上涨, 量价配合"}
        elif not price_up and vol_up:
            signals["VOLUME"] = {"signal": "SELL", "detail": "放量下跌, 抛压明显"}
        elif price_up and not vol_up:
            signals["VOLUME"] = {"signal": "NEUTRAL", "detail": "缩量上涨, 上攻动力不足"}
        else:
            signals["VOLUME"] = {"signal": "NEUTRAL", "detail": "缩量调整, 观望为宜"}
    else:
        signals["VOLUME"] = {"signal": "NEUTRAL", "detail": "无成交量数据"}

    # --- 综合信号（加权评分） ---
    SIGNAL_WEIGHTS = {
        "MACD": 0.25,       # 趋势可靠性最高
        "MA_CROSS": 0.20,   # 趋势确认
        "RSI": 0.20,        # 动量/均值回归
        "BOLL": 0.15,       # 波动率/突破
        "KDJ": 0.10,        # 辅助动量
        "VOLUME": 0.10,     # 量价确认
    }

    weighted_score = 0.0
    for name, sig in signals.items():
        weight = SIGNAL_WEIGHTS.get(name, 0.1)
        if sig["signal"] == "BUY":
            weighted_score += weight
        elif sig["signal"] == "SELL":
            weighted_score -= weight

    if weighted_score >= 0.35:
        overall = "BUY"
    elif weighted_score <= -0.35:
        overall = "SELL"
    else:
        overall = "NEUTRAL"

    confidence = _round(min(abs(weighted_score) / 1.0, 1.0), 2)

    buy_count = sum(1 for s in signals.values() if s["signal"] == "BUY")
    sell_count = sum(1 for s in signals.values() if s["signal"] == "SELL")
    total = len(signals)

    # 生成中文总结
    signal_cn = {"BUY": "看多", "SELL": "看空", "NEUTRAL": "中性"}
    summary_parts = [f"技术面综合评价: {signal_cn[overall]}"]
    summary_parts.append(
        f"（加权得分{weighted_score:+.2f}, {buy_count}项看多, {sell_count}项看空, "
        f"{total - buy_count - sell_count}项中性, 置信度{confidence:.0%}）。"
    )

    key_signals = []
    for name, sig in signals.items():
        if sig["signal"] != "NEUTRAL":
            key_signals.append(sig["detail"])
    if key_signals:
        summary_parts.append("关键信号: " + "; ".join(key_signals[:3]) + "。")

    latest_date = _date_str(df["date"].iloc[-1])

    return {
        "symbol": symbol,
        "market": market,
        "date": latest_date,
        "overall_signal": overall,
        "confidence": confidence,
        "weighted_score": _round(weighted_score, 4),
        "signals": signals,
        "summary": "".join(summary_parts),
        "price": _round(latest_close, 2),
    }


# ===================================================================
# 注册入口（薄包装器）
# ===================================================================
def register_tools(mcp):
    """将技术分析工具注册到 FastMCP 实例。"""

    @mcp.tool
    def get_technical_indicators(
        symbol: str,
        indicators: list = None,
        period: str = "daily",
        market: str = "A",
        count: int = 60,
    ) -> dict:
        """获取股票技术指标数据。

        Args:
            symbol: 股票代码，如 "600519"（A股）、"AAPL"（美股）。
            indicators: 需要计算的指标列表。
                        支持: MA, EMA, MACD, RSI, KDJ, BOLL, ATR, OBV。
                        默认 ["MA", "MACD", "RSI"]。
            period: K线周期。daily=日线, weekly=周线, monthly=月线。默认 "daily"。
            market: 市场代码。A=A股, US=美股, HK=港股。默认 "A"。
            count: 返回最近多少条数据点，默认 60。

        Returns:
            包含 symbol, period, market, indicators（各指标数据）,
            dates（日期列表）, latest（最新值）的字典。
        """
        return fetch_technical_indicators(symbol, indicators, period, market, count)

    @mcp.tool
    def get_technical_signal(symbol: str, market: str = "A") -> dict:
        """获取股票技术面综合交易信号。

        综合 MA交叉、MACD、RSI、KDJ、布林带、量价关系 六大维度，
        给出看多/看空/中性的综合判断及置信度。

        Args:
            symbol: 股票代码，如 "600519"（A股）、"AAPL"（美股）。
            market: 市场代码。A=A股, US=美股, HK=港股。默认 "A"。

        Returns:
            包含 overall_signal（BUY/SELL/NEUTRAL）、confidence（0-1）、
            各维度 signals 详情、以及中文 summary 的字典。
        """
        return fetch_technical_signal(symbol, market)
