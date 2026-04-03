#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行情数据工具集 —— 提供股票实时/历史行情、指数、外汇、大宗商品数据获取能力。
通过 register_tools(mcp) 注册到 FastMCP 实例。

v2.0 更新：
- 集成 data_source.py 的缓存和退避机制
- 全工具增加 yfinance fallback
- 修复 Rate Limiting 问题

v2.1 更新：
- 集成 stock-open-api 腾讯行情接口作为A股实时行情优先数据源
- 数据源优先级: 腾讯行情(tencent_qq) → akshare → yfinance
"""

import os
import sys
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# 基础设施
# ---------------------------------------------------------------------------
_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _base not in sys.path:
    sys.path.insert(0, _base)

from config import config
from utils.errors import handle_errors

# 导入新的数据源管理工具
from utils.data_source import (
    call_akshare, try_akshare_apis, yf_price_snapshot, yf_history,
    get_cache, TTL_MARKET, TTL_DEFAULT
)
from utils.rate_limiter import yfinance_limiter
from utils.stock_open_api_source import fetch_realtime_tencent

try:
    from utils.formatters import safe_round as _round2, date_to_str as _date_str
except Exception:
    def _round2(val, decimals=2):
        try: return round(float(val), decimals)
        except (TypeError, ValueError): return val
    def _date_str(val):
        if val is None: return None
        if isinstance(val, str): return val[:10]
        try: return val.strftime("%Y-%m-%d")
        except Exception: return str(val)[:10]

# ---------------------------------------------------------------------------
# 第三方库（保护性导入）
# ---------------------------------------------------------------------------
try:
    import akshare as ak
except ImportError:
    ak = None

# 禁用 curl_cffi，避免 SSL/OpenSSL 版本冲突问题
os.environ["YFINANCE_DISABLE_CURL_CFFI"] = "1"

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    import pandas as pd
except ImportError:
    pd = None


# ---------------------------------------------------------------------------
# 公共辅助函数
# ---------------------------------------------------------------------------
def _df_to_records(df, max_rows: int = None) -> list[dict]:
    """将 DataFrame 转为 list[dict]，限制最大行数。"""
    if df is None or df.empty:
        return []
    if max_rows is None:
        max_rows = config.max_records
    df = df.head(max_rows)
    records = df.to_dict(orient="records")
    for rec in records:
        for k, v in rec.items():
            if pd and pd.isna(v):
                rec[k] = None
            elif isinstance(v, float):
                rec[k] = _round2(v)
    return records


def _yf_change_pct(info: dict) -> float | None:
    """从 yfinance info 计算涨跌幅。"""
    price = info.get("regularMarketPrice") or info.get("currentPrice")
    prev = info.get("previousClose") or info.get("regularMarketPreviousClose")
    if price and prev and prev != 0:
        return _round2((price - prev) / prev * 100)
    return None


def _return_list_or_single(results: list, empty_msg: str) -> dict:
    """统一处理 list → 单条/多条/空 的返回逻辑。"""
    if not results:
        return {"error": empty_msg}
    if len(results) == 1:
        return results[0]
    return {"data": results, "count": len(results)}


def _get_cache_key(func_name: str, *args, **kwargs) -> str:
    """生成缓存键。"""
    return f"{func_name}:{str(args)}:{str(sorted(kwargs.items()))}"


# ---------------------------------------------------------------------------
# 业务逻辑独立函数
# ---------------------------------------------------------------------------
@handle_errors
def fetch_stock_realtime(symbol: str, market: str = "A") -> dict:
    """获取股票实时行情的核心逻辑。"""
    market = market.upper()
    cache_key = _get_cache_key("stock_realtime", symbol, market)
    cache = get_cache()
    
    # 尝试缓存
    if cache:
        cached = cache.get(cache_key, TTL_MARKET)
        if cached:
            return cached
    
    result = None
    
    if market == "A":
        # 优先使用腾讯行情 (stock-open-api)
        try:
            tencent_result = fetch_realtime_tencent(symbol)
            if tencent_result and tencent_result.get("现价"):
                result = {
                    "名称": tencent_result.get("名称", ""),
                    "代码": tencent_result.get("代码", symbol),
                    "现价": _round2(tencent_result.get("现价")),
                    "涨跌幅(%)": _round2(tencent_result.get("涨跌幅(%)")),
                    "涨跌额": _round2(tencent_result.get("涨跌额")),
                    "成交量(手)": _round2(tencent_result.get("成交量(手)")),
                    "成交额(元)": _round2(tencent_result.get("成交额(元)")),
                    "市盈率": _round2(tencent_result.get("市盈率")),
                    "今开": _round2(tencent_result.get("今开")),
                    "最高": _round2(tencent_result.get("最高")),
                    "最低": _round2(tencent_result.get("最低")),
                    "昨收": _round2(tencent_result.get("昨收")),
                    "换手率(%)": _round2(tencent_result.get("换手率(%)")),
                    "market": "A",
                    "data_source": "tencent_qq",
                }
        except Exception:
            pass  # 腾讯行情失败，fallback到akshare
        
        # 腾讯行情失败，尝试 akshare（带重试）
        if result is None and ak is not None:
            try:
                df = call_akshare("stock_zh_a_spot_em", max_retries=2)
                row = df[df["代码"] == symbol]
                if not row.empty:
                    r = row.iloc[0]
                    result = {
                        "名称": str(r.get("名称", "")),
                        "代码": str(r.get("代码", symbol)),
                        "现价": _round2(r.get("最新价")),
                        "涨跌幅(%)": _round2(r.get("涨跌幅")),
                        "涨跌额": _round2(r.get("涨跌额")),
                        "成交量(手)": _round2(r.get("成交量")),
                        "成交额(元)": _round2(r.get("成交额")),
                        "市盈率": _round2(r.get("市盈率-动态")),
                        "市净率": _round2(r.get("市净率")),
                        "总市值": _round2(r.get("总市值")),
                        "流通市值": _round2(r.get("流通市值")),
                        "今开": _round2(r.get("今开")),
                        "最高": _round2(r.get("最高")),
                        "最低": _round2(r.get("最低")),
                        "昨收": _round2(r.get("昨收")),
                        "换手率(%)": _round2(r.get("换手率")),
                        "量比": _round2(r.get("量比")),
                        "market": "A",
                        "data_source": "akshare",
                    }
            except Exception:
                pass  # akshare 失败，fallback 到 yfinance
        
        # akshare 也失败，使用 yfinance fallback
        if result is None:
            yf_result = yf_price_snapshot(symbol, "A")
            if yf_result:
                result = {
                    "名称": yf_result["name"],
                    "代码": symbol,
                    "现价": yf_result["price"],
                    "涨跌幅(%)": yf_result["change_pct"],
                    "涨跌额": _round2(yf_result["price"] - yf_result["previous_close"]) if yf_result["previous_close"] else None,
                    "市盈率": yf_result["pe"],
                    "市净率": yf_result["pb"],
                    "总市值": yf_result["market_cap"],
                    "market": "A",
                    "data_source": "yfinance",
                }
    
    elif market in ("US", "HK"):
        # 美股/港股直接使用 yfinance
        yf_result = yf_price_snapshot(symbol, market)
        if yf_result:
            result = {
                "名称": yf_result["name"],
                "代码": symbol,
                "现价": yf_result["price"],
                "涨跌幅(%)": yf_result["change_pct"],
                "成交量": yf_result["volume"],
                "市盈率": yf_result["pe"],
                "总市值": yf_result["market_cap"],
                "market": market,
                "data_source": "yfinance",
            }
            if market == "US":
                result["currency"] = "USD"
            else:
                result["currency"] = "HKD"
    
    else:
        return {"error": f"不支持的市场代码: {market}，请使用 A/HK/US"}
    
    if result is None:
        return {"error": f"无法获取 {symbol} 的实时行情数据"}
    
    # 写入缓存
    if cache:
        cache.set(cache_key, result)
    
    return result


@handle_errors
def fetch_stock_history(symbol: str, market: str = "A", period: str = "daily", days: int = 30) -> dict:
    """获取股票历史K线数据的核心逻辑。"""
    max_rows = config.max_records
    days = min(days, 365)
    market = market.upper()
    cache_key = _get_cache_key("stock_history", symbol, market, period, days)
    cache = get_cache()
    
    # 尝试缓存
    if cache:
        cached = cache.get(cache_key, TTL_MARKET)
        if cached:
            return cached
    
    result = None
    
    if market == "A":
        # 优先使用 akshare（带重试）
        if ak is not None:
            try:
                period_map = {"daily": "daily", "weekly": "weekly", "monthly": "monthly"}
                end_date = datetime.now().strftime("%Y%m%d")
                start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
                df = call_akshare("stock_zh_a_hist", symbol=symbol, 
                                 period=period_map.get(period, "daily"),
                                 start_date=start_date, end_date=end_date, 
                                 adjust="qfq", max_retries=2)
                if df is not None and not df.empty:
                    df = df.tail(max_rows)
                    records = []
                    for _, r in df.iterrows():
                        records.append({
                            "日期": _date_str(r.get("日期")), 
                            "开盘": _round2(r.get("开盘")),
                            "最高": _round2(r.get("最高")), 
                            "最低": _round2(r.get("最低")),
                            "收盘": _round2(r.get("收盘")), 
                            "成交量": _round2(r.get("成交量")),
                            "成交额": _round2(r.get("成交额")), 
                            "涨跌幅(%)": _round2(r.get("涨跌幅")),
                        })
                    result = {
                        "meta": {"代码": symbol, "market": "A", "周期": period, "数据条数": len(records)},
                        "data": records
                    }
            except Exception:
                pass
        
        # Fallback 到 yfinance
        if result is None:
            result = yf_history(symbol, "A", period, days)
    
    elif market == "US":
        result = yf_history(symbol, "US", period, days)
    
    else:
        return {"error": f"get_stock_history 暂不支持市场: {market}，请使用 A 或 US"}
    
    if result is None:
        return {"error": f"无法获取 {symbol} 的历史数据"}
    
    # 写入缓存
    if cache:
        cache.set(cache_key, result)
    
    return result


@handle_errors
def fetch_index_quote(index_name: str = "all") -> dict:
    """获取主要股指行情的核心逻辑。"""
    cache_key = _get_cache_key("index_quote", index_name)
    cache = get_cache()
    
    # 尝试缓存
    if cache:
        cached = cache.get(cache_key, TTL_MARKET)
        if cached:
            return cached
    
    domestic_indices = {
        "沪深300": "沪深300", "上证指数": "上证指数", "深证成指": "深证成指",
        "创业板指": "创业板指", "科创50": "科创50",
    }
    overseas_indices = {"标普500": "^GSPC", "纳斯达克": "^IXIC", "道琼斯": "^DJI", "恒生指数": "^HSI"}
    results = []

    # --- 国内指数 ---
    need_domestic = index_name == "all" or index_name in domestic_indices
    if need_domestic and ak is not None:
        try:
            df = call_akshare("stock_zh_index_spot_em", max_retries=2)
            if df is not None and not df.empty:
                target_names = list(domestic_indices.values()) if index_name == "all" else [domestic_indices[index_name]]
                for name in target_names:
                    row = df[df["名称"] == name]
                    if row.empty:
                        continue
                    r = row.iloc[0]
                    results.append({
                        "指数名称": name, 
                        "最新点位": _round2(r.get("最新价")),
                        "涨跌幅(%)": _round2(r.get("涨跌幅")), 
                        "涨跌额": _round2(r.get("涨跌额")),
                        "成交额(元)": _round2(r.get("成交额")), 
                        "market": "CN",
                        "data_source": "akshare",
                    })
        except Exception as e:
            results.append({"error": f"获取国内指数失败: {str(e)}"})

    # --- 海外指数 ---
    need_overseas = index_name == "all" or index_name in overseas_indices
    if need_overseas and yf is not None:
        target = overseas_indices.items() if index_name == "all" else [(index_name, overseas_indices[index_name])]
        for cn_name, yf_symbol in target:
            try:
                ticker = yf.Ticker(yf_symbol)
                info = ticker.info
                price = info.get("regularMarketPrice") or info.get("previousClose")
                results.append({
                    "指数名称": cn_name, 
                    "最新点位": _round2(price),
                    "涨跌幅(%)": _yf_change_pct(info), 
                    "market": "OVERSEAS",
                    "data_source": "yfinance",
                })
            except Exception:
                results.append({"指数名称": cn_name, "error": "数据获取失败"})

    result = _return_list_or_single(results, f"未找到指数 '{index_name}' 的数据，请检查名称是否正确")
    
    # 写入缓存
    if cache and "error" not in result:
        cache.set(cache_key, result)
    
    return result


@handle_errors
def fetch_forex(pair: str = "all") -> dict:
    """获取主要货币对汇率的核心逻辑。"""
    cache_key = _get_cache_key("forex", pair)
    cache = get_cache()
    
    # 尝试缓存
    if cache:
        cached = cache.get(cache_key, TTL_MARKET)
        if cached:
            return cached
    
    yf_pairs = {
        "USDCNY": "CNY=X", "EURUSD": "EURUSD=X", "USDJPY": "JPY=X",
        "GBPUSD": "GBPUSD=X", "AUDUSD": "AUDUSD=X", "USDCAD": "CAD=X", "USDHKD": "HKD=X",
    }
    results = []
    pair = pair.upper()

    # 优先尝试 akshare（带重试）
    if ak is not None:
        try:
            df = call_akshare("fx_spot_quote", max_retries=2)
            if df is not None and not df.empty:
                if pair == "ALL":
                    for _, r in df.head(20).iterrows():
                        results.append({
                            "货币对": str(r.iloc[0]) if len(r) > 0 else "",
                            "最新价": _round2(r.iloc[1]) if len(r) > 1 else None,
                            "涨跌幅": _round2(r.iloc[2]) if len(r) > 2 else None,
                            "数据来源": "akshare",
                        })
                else:
                    for _, r in df.iterrows():
                        name = str(r.iloc[0]) if len(r) > 0 else ""
                        if pair.replace("/", "") in name.upper().replace("/", ""):
                            results.append({
                                "货币对": name,
                                "最新价": _round2(r.iloc[1]) if len(r) > 1 else None,
                                "涨跌幅": _round2(r.iloc[2]) if len(r) > 2 else None,
                                "数据来源": "akshare",
                            })
                if results:
                    result = _return_list_or_single(results, "")
                    if cache:
                        cache.set(cache_key, result)
                    return result
        except Exception:
            pass  # fallback to yfinance

    # yfinance fallback
    if yf is not None:
        targets = yf_pairs.items() if pair == "ALL" else [(pair, yf_pairs.get(pair))]
        for name, yf_sym in targets:
            if yf_sym is None:
                results.append({"货币对": name, "error": "不支持该货币对"})
                continue
            try:
                ticker = yf.Ticker(yf_sym)
                info = ticker.info
                price = info.get("regularMarketPrice") or info.get("previousClose")
                prev = info.get("previousClose")
                results.append({
                    "货币对": name, 
                    "最新价": _round2(price), 
                    "前收": _round2(prev),
                    "涨跌幅(%)": _yf_change_pct(info), 
                    "数据来源": "yfinance",
                })
            except Exception:
                results.append({"货币对": name, "error": "数据获取失败"})

    result = _return_list_or_single(results, "无法获取外汇数据，请确认 akshare 或 yfinance 已安装")
    
    if cache and "error" not in result:
        cache.set(cache_key, result)
    
    return result


@handle_errors
def fetch_commodity(commodity: str = "all") -> dict:
    """获取大宗商品价格的核心逻辑。"""
    cache_key = _get_cache_key("commodity", commodity)
    cache = get_cache()
    
    # 尝试缓存
    if cache:
        cached = cache.get(cache_key, TTL_MARKET)
        if cached:
            return cached
    
    yf_commodities = {
        "黄金": {"symbol": "GC=F", "unit": "美元/盎司"},
        "白银": {"symbol": "SI=F", "unit": "美元/盎司"},
        "原油": {"symbol": "CL=F", "unit": "美元/桶"},
        "铜": {"symbol": "HG=F", "unit": "美元/磅"},
        "天然气": {"symbol": "NG=F", "unit": "美元/百万英热"},
        "铁矿石": {"symbol": None, "unit": "元/吨"},
    }
    results = []

    # akshare 获取国内期货（铁矿石）
    if ak is not None and (commodity == "all" or commodity == "铁矿石"):
        try:
            df = call_akshare("futures_main_sina", max_retries=2)
            if df is not None and not df.empty:
                row = df[df["symbol"].str.startswith("I0")]
                if not row.empty:
                    r = row.iloc[0]
                    results.append({
                        "品种": "铁矿石", 
                        "最新价": _round2(r.get("price", r.get("close"))),
                        "涨跌幅(%)": _round2(r.get("changepercent")),
                        "单位": "元/吨", 
                        "数据来源": "akshare",
                    })
        except Exception:
            pass

    # yfinance 获取国际大宗商品
    if yf is not None:
        if commodity == "all":
            targets = yf_commodities.items()
        elif commodity in yf_commodities:
            targets = [(commodity, yf_commodities[commodity])]
        else:
            targets = []
        for cn_name, cfg in targets:
            if cfg["symbol"] is None:
                continue
            try:
                ticker = yf.Ticker(cfg["symbol"])
                info = ticker.info
                price = info.get("regularMarketPrice") or info.get("previousClose")
                results.append({
                    "品种": cn_name, 
                    "最新价": _round2(price),
                    "涨跌幅(%)": _yf_change_pct(info),
                    "单位": cfg["unit"], 
                    "数据来源": "yfinance",
                })
            except Exception:
                results.append({"品种": cn_name, "error": "数据获取失败"})

    result = _return_list_or_single(results, f"未找到商品 '{commodity}' 的数据，请检查名称是否正确")
    
    if cache and "error" not in result:
        cache.set(cache_key, result)
    
    return result


def _convert_etf_to_yf(symbol: str) -> str:
    """将A股ETF代码转换为yfinance格式。
    
    Args:
        symbol: A股ETF代码，如 "510300", "159915"
    
    Returns:
        yfinance格式的代码，如 "510300.SS", "159915.SZ"
    """
    # 如果已经是yfinance格式，直接返回
    if symbol.endswith(".SS") or symbol.endswith(".SZ"):
        return symbol
    
    # 上海ETF：510xxx, 511xxx, 518xxx, 560xxx, 588xxx (科创板ETF)
    # 深圳ETF：159xxx
    if symbol.startswith(("15", "16")):
        return f"{symbol}.SZ"
    else:
        return f"{symbol}.SS"


@handle_errors
def fetch_etf_realtime(symbol: str, market: str = "A") -> dict:
    """获取ETF实时行情数据。
    
    优先使用akshare，失败时自动fallback到yfinance。
    """
    market = market.upper()
    if market != "A":
        return {"error": f"ETF实时数据暂仅支持A股市场，不支持 {market}"}
    
    cache_key = _get_cache_key("etf_realtime", symbol, market)
    cache = get_cache()
    errors = []
    
    # 尝试缓存
    if cache:
        cached = cache.get(cache_key, TTL_MARKET)
        if cached:
            return cached

    # 尝试akshare
    if ak is not None:
        try:
            df = call_akshare("fund_etf_spot_em", max_retries=2)
            if df is not None and not df.empty:
                row = df[df["代码"] == symbol]
                if not row.empty:
                    r = row.iloc[0]
                    result = {
                        "代码": str(r.get("代码", symbol)),
                        "名称": str(r.get("名称", "")),
                        "现价": _round2(r.get("最新价")),
                        "涨跌幅(%)": _round2(r.get("涨跌幅")),
                        "成交量(手)": _round2(r.get("成交量")),
                        "成交额(元)": _round2(r.get("成交额")),
                        "净值": _round2(r.get("最新净值", r.get("基金净值"))),
                        "溢价率(%)": _round2(r.get("折价率", r.get("溢价率"))),
                        "今开": _round2(r.get("今开")),
                        "最高": _round2(r.get("最高")),
                        "最低": _round2(r.get("最低")),
                        "昨收": _round2(r.get("昨收")),
                        "market": "A",
                        "data_source": "akshare",
                    }
                    # 写入缓存
                    if cache:
                        cache.set(cache_key, result)
                    return result
                else:
                    errors.append(f"akshare: 未找到ETF代码 {symbol}")
            else:
                errors.append("akshare: 未获取到ETF行情数据")
        except Exception as e:
            errors.append(f"akshare: {str(e)}")
    else:
        errors.append("akshare: 未安装")

    # Fallback到yfinance
    if yf is not None:
        try:
            yfinance_limiter.wait()
            yf_symbol = _convert_etf_to_yf(symbol)
            ticker = yf.Ticker(yf_symbol)
            info = ticker.info
            hist = ticker.history(period="1d")
            
            if info:
                price = info.get("regularMarketPrice") or info.get("currentPrice")
                prev = info.get("previousClose") or info.get("regularMarketPreviousClose")
                change_pct = None
                if price and prev and prev != 0:
                    change_pct = _round2((price - prev) / prev * 100)
                
                # 获取成交量（优先从当日历史数据获取）
                volume = None
                if hist is not None and not hist.empty:
                    volume = _round2(hist["Volume"].iloc[-1])
                if volume is None:
                    volume = info.get("regularMarketVolume") or info.get("volume")
                
                result = {
                    "代码": symbol,
                    "名称": info.get("shortName") or info.get("longName", ""),
                    "现价": _round2(price),
                    "涨跌幅(%)": change_pct,
                    "成交量(手)": _round2(volume) if volume else None,
                    "成交额(元)": None,  # yfinance不直接提供成交额
                    "净值": _round2(info.get("navPrice")),
                    "溢价率(%)": None,  # yfinance不直接提供溢价率
                    "今开": _round2(info.get("regularMarketOpen") or info.get("open")),
                    "最高": _round2(info.get("regularMarketDayHigh") or info.get("dayHigh")),
                    "最低": _round2(info.get("regularMarketDayLow") or info.get("dayLow")),
                    "昨收": _round2(prev),
                    "market": "A",
                    "data_source": "yfinance",
                }
                # 写入缓存
                if cache:
                    cache.set(cache_key, result)
                return result
            else:
                errors.append("yfinance: 无法获取ETF信息")
        except Exception as e:
            errors.append(f"yfinance: {str(e)}")
    else:
        errors.append("yfinance: 未安装")

    return {"error": f"无法获取ETF {symbol} 的实时行情数据", "details": errors}


@handle_errors
def fetch_etf_history(symbol: str, period: str = "daily",
                      start_date: str = None, end_date: str = None) -> dict:
    """获取ETF历史K线数据。
    
    优先使用akshare，失败时自动fallback到yfinance。
    """
    cache_key = _get_cache_key("etf_history", symbol, period, start_date, end_date)
    cache = get_cache()
    errors = []
    
    # 尝试缓存
    if cache:
        cached = cache.get(cache_key, TTL_MARKET)
        if cached:
            return cached

    # 处理日期参数
    if end_date is None:
        end_date_dt = datetime.now()
        end_date = end_date_dt.strftime("%Y%m%d")
    else:
        end_date_dt = datetime.strptime(end_date.replace("-", ""), "%Y%m%d")
        end_date = end_date.replace("-", "")
    
    if start_date is None:
        start_date_dt = datetime.now() - timedelta(days=180)
        start_date = start_date_dt.strftime("%Y%m%d")
    else:
        start_date_dt = datetime.strptime(start_date.replace("-", ""), "%Y%m%d")
        start_date = start_date.replace("-", "")

    # 尝试akshare
    if ak is not None:
        try:
            period_map = {"daily": "daily", "weekly": "weekly", "monthly": "monthly"}
            ak_period = period_map.get(period, "daily")
            
            df = call_akshare("fund_etf_hist_em", symbol=symbol, period=ak_period,
                             start_date=start_date, end_date=end_date, adjust="qfq", max_retries=2)
            if df is not None and not df.empty:
                max_rows = config.max_records
                df = df.tail(max_rows)
                records = []
                for _, r in df.iterrows():
                    records.append({
                        "日期": _date_str(r.get("日期")),
                        "开盘": _round2(r.get("开盘")),
                        "最高": _round2(r.get("最高")),
                        "最低": _round2(r.get("最低")),
                        "收盘": _round2(r.get("收盘")),
                        "成交量": _round2(r.get("成交量")),
                        "成交额": _round2(r.get("成交额")),
                    })
                
                result = {
                    "meta": {"代码": symbol, "周期": period, "数据条数": len(records), "data_source": "akshare"},
                    "data": records,
                }
                
                # 写入缓存
                if cache:
                    cache.set(cache_key, result)
                
                return result
            else:
                errors.append("akshare: 未找到ETF历史数据")
        except Exception as e:
            errors.append(f"akshare: {str(e)}")
    else:
        errors.append("akshare: 未安装")

    # Fallback到yfinance
    if yf is not None and pd is not None:
        try:
            yfinance_limiter.wait()
            yf_symbol = _convert_etf_to_yf(symbol)
            
            period_map = {"daily": "1d", "weekly": "1wk", "monthly": "1mo"}
            yf_interval = period_map.get(period, "1d")
            
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(
                start=start_date_dt.strftime("%Y-%m-%d"),
                end=(end_date_dt + timedelta(days=1)).strftime("%Y-%m-%d"),
                interval=yf_interval
            )
            
            if df is not None and not df.empty:
                # 处理多级列索引
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                
                max_rows = config.max_records
                df = df.tail(max_rows)
                
                records = []
                for date_idx, r in df.iterrows():
                    date_str = date_idx.strftime("%Y-%m-%d") if hasattr(date_idx, 'strftime') else str(date_idx)[:10]
                    records.append({
                        "日期": date_str,
                        "开盘": _round2(r.get("Open")),
                        "最高": _round2(r.get("High")),
                        "最低": _round2(r.get("Low")),
                        "收盘": _round2(r.get("Close")),
                        "成交量": _round2(r.get("Volume")),
                        "成交额": None,  # yfinance历史数据不直接提供成交额
                    })
                
                result = {
                    "meta": {"代码": symbol, "周期": period, "数据条数": len(records), "data_source": "yfinance"},
                    "data": records,
                }
                
                # 写入缓存
                if cache:
                    cache.set(cache_key, result)
                
                return result
            else:
                errors.append("yfinance: 未找到ETF历史数据")
        except Exception as e:
            errors.append(f"yfinance: {str(e)}")
    else:
        errors.append("yfinance/pandas: 未安装")

    return {"error": f"无法获取ETF {symbol} 的历史数据", "details": errors}


@handle_errors
def fetch_convertible_bond(symbol: str = None) -> dict:
    """获取可转债数据。"""
    if ak is None:
        return {"error": "akshare 未安装，无法获取可转债数据"}
    
    cache_key = _get_cache_key("convertible_bond", symbol)
    cache = get_cache()
    
    # 尝试缓存
    if cache:
        cached = cache.get(cache_key, TTL_MARKET)
        if cached:
            return cached

    try:
        try:
            df = call_akshare("bond_cb_jsl", max_retries=2)
        except Exception:
            try:
                df = call_akshare("bond_zh_cov_value_analysis", max_retries=1)
            except Exception as e:
                return {"error": f"获取可转债数据失败: {str(e)}"}

        if df is None or df.empty:
            return {"error": "未获取到可转债数据"}

        # 标准化列名映射（集思录数据列名可能不同版本有差异）
        col_map = {}
        for col in df.columns:
            col_lower = str(col).lower()
            if "代码" in col or "bond_id" in col_lower:
                col_map["code"] = col
            elif "名称" in col or "bond_nm" in col_lower:
                col_map["name"] = col
            elif "现价" in col or "price" in col_lower:
                col_map["price"] = col
            elif "转股价" in col or "convert_price" in col_lower or "转股价格" in col:
                col_map["conversion_price"] = col
            elif "转股价值" in col or "convert_value" in col_lower:
                col_map["conversion_value"] = col
            elif "溢价率" in col or "premium" in col_lower:
                col_map["premium_rate"] = col
            elif "到期收益率" in col or "ytm" in col_lower:
                col_map["ytm"] = col
            elif "信用" in col or "rating" in col_lower:
                col_map["credit_rating"] = col
            elif "剩余" in col or "remain" in col_lower:
                col_map["remaining_years"] = col

        if symbol is not None:
            code_col = col_map.get("code", df.columns[0])
            row = df[df[code_col].astype(str) == str(symbol)]
            if row.empty:
                return {"error": f"未找到可转债代码 {symbol}"}
            r = row.iloc[0]
            result = {
                "代码": str(r.get(col_map.get("code", ""), symbol)),
                "名称": str(r.get(col_map.get("name", ""), "")),
                "现价": _round2(r.get(col_map.get("price", ""))),
                "转股价": _round2(r.get(col_map.get("conversion_price", ""))),
                "转股价值": _round2(r.get(col_map.get("conversion_value", ""))),
                "溢价率(%)": _round2(r.get(col_map.get("premium_rate", ""))),
                "到期收益率(%)": _round2(r.get(col_map.get("ytm", ""))),
                "信用评级": str(r.get(col_map.get("credit_rating", ""), "")),
                "剩余年限": _round2(r.get(col_map.get("remaining_years", ""))),
                "data_source": "akshare",
            }
            
            if cache:
                cache.set(cache_key, result)
            
            return result

        # 返回全部，按溢价率排序
        premium_col = col_map.get("premium_rate")
        if premium_col and premium_col in df.columns:
            df = df.sort_values(by=premium_col, ascending=True)

        max_rows = config.max_records
        records = _df_to_records(df.head(max_rows))
        
        result = {"data": records, "count": len(records), "data_source": "akshare"}
        
        if cache:
            cache.set(cache_key, result)
        
        return result
    except Exception as e:
        return {"error": f"获取可转债数据失败: {str(e)}"}


# ===================================================================
# 注册入口（薄包装器）
# ===================================================================
def register_tools(mcp):
    """将行情数据工具注册到 FastMCP 实例。"""

    @mcp.tool
    def get_stock_realtime(symbol: str, market: str = "A") -> dict:
        """获取股票实时行情。

        Args:
            symbol: 股票代码，如 "000001"（A股）、"00700"（港股）、"AAPL"（美股）。
            market: 市场代码。A=A股, HK=港股, US=美股。默认 "A"。

        Returns:
            包含名称、代码、现价、涨跌幅、成交量、成交额、市盈率、市值等字段的字典。
        """
        return fetch_stock_realtime(symbol, market)

    @mcp.tool
    def get_stock_history(symbol: str, market: str = "A", period: str = "daily", days: int = 30) -> dict:
        """获取股票历史K线数据。

        Args:
            symbol: 股票代码，如 "000001"（A股）或 "AAPL"（美股）。
            market: 市场代码。A=A股, US=美股。默认 "A"。
            period: K线周期。daily=日线, weekly=周线, monthly=月线。默认 "daily"。
            days: 获取最近多少天的数据，默认30，最多返回60条记录。

        Returns:
            包含 meta 信息和 data 列表（日期、开盘、最高、最低、收盘、成交量）的字典。
        """
        return fetch_stock_history(symbol, market, period, days)

    @mcp.tool
    def get_index_quote(index_name: str = "all") -> dict:
        """获取主要股指行情。

        Args:
            index_name: 指数名称。支持：沪深300/上证指数/深证成指/创业板指/科创50/
                        标普500/纳斯达克/道琼斯/恒生指数，或 "all" 返回全部。

        Returns:
            包含指数名称、点位、涨跌幅、成交额的字典或列表。
        """
        return fetch_index_quote(index_name)

    @mcp.tool
    def get_forex(pair: str = "all") -> dict:
        """获取主要货币对汇率。

        Args:
            pair: 货币对代码。支持：USDCNY/EURUSD/USDJPY/GBPUSD/AUDUSD/USDCAD/USDHKD，
                  或 "all" 返回全部主要货币对。

        Returns:
            包含货币对、买入价、卖出价、中间价、更新时间的字典或列表。
        """
        return fetch_forex(pair)

    @mcp.tool
    def get_commodity(commodity: str = "all") -> dict:
        """获取大宗商品价格。

        Args:
            commodity: 商品名称。支持：黄金/白银/原油/铜/铁矿石/天然气，或 "all" 返回全部。

        Returns:
            包含品种名称、最新价、涨跌幅、单位的字典或列表。
        """
        return fetch_commodity(commodity)

    @mcp.tool
    def get_etf_realtime(symbol: str, market: str = "A") -> dict:
        """获取ETF实时行情数据。

        Args:
            symbol: ETF代码，如 "510300"（沪深300ETF）、"159919"（创业板ETF）。
            market: 市场代码，目前仅支持 "A"（A股）。默认 "A"。

        Returns:
            包含代码、名称、现价、涨跌幅、成交量、净值、溢价率等字段的字典。
        """
        return fetch_etf_realtime(symbol, market)

    @mcp.tool
    def get_etf_history(symbol: str, period: str = "daily",
                        start_date: str = None, end_date: str = None) -> dict:
        """获取ETF历史K线数据。

        Args:
            symbol: ETF代码，如 "510300"。
            period: K线周期。daily=日线, weekly=周线, monthly=月线。默认 "daily"。
            start_date: 起始日期，格式 "YYYYMMDD" 或 "YYYY-MM-DD"，默认近180天。
            end_date: 结束日期，格式同上，默认今天。

        Returns:
            包含 meta 信息和 data 列表（日期、开盘、最高、最低、收盘、成交量、成交额）的字典。
        """
        return fetch_etf_history(symbol, period, start_date, end_date)

    @mcp.tool
    def get_convertible_bond(symbol: str = None) -> dict:
        """获取可转债数据。

        Args:
            symbol: 可转债代码，如 "127045"。不传则返回全部可转债（按溢价率排序）。

        Returns:
            单只可转债返回包含代码、名称、现价、转股价、转股价值、溢价率、到期收益率、
            信用评级、剩余年限的字典；全部则返回列表。
        """
        return fetch_convertible_bond(symbol)
