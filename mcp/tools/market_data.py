#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行情数据工具集 —— 提供股票实时/历史行情、指数、外汇、大宗商品数据获取能力。
通过 register_tools(mcp) 注册到 FastMCP 实例。
"""

import os
import sys
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# 公共工具（从 utils 导入，带 fallback）
# ---------------------------------------------------------------------------
try:
    _base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _base not in sys.path:
        sys.path.insert(0, _base)
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

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    import pandas as pd
except ImportError:
    pd = None


def _df_to_records(df, max_rows: int = 60) -> list[dict]:
    """将 DataFrame 转为 list[dict]，限制最大行数。"""
    if df is None or df.empty:
        return []
    df = df.head(max_rows)
    records = df.to_dict(orient="records")
    # 清洗 NaN
    for rec in records:
        for k, v in rec.items():
            if pd and pd.isna(v):
                rec[k] = None
            elif isinstance(v, float):
                rec[k] = _round2(v)
    return records


# ===================================================================
# 注册入口
# ===================================================================
def register_tools(mcp):
    """将行情数据工具注册到 FastMCP 实例。"""

    # ---------------------------------------------------------------
    # 工具1: get_stock_realtime
    # ---------------------------------------------------------------
    @mcp.tool
    def get_stock_realtime(symbol: str, market: str = "A") -> dict:
        """获取股票实时行情。

        Args:
            symbol: 股票代码，如 "000001"（A股）、"00700"（港股）、"AAPL"（美股）。
            market: 市场代码。A=A股, HK=港股, US=美股。默认 "A"。

        Returns:
            包含名称、代码、现价、涨跌幅、成交量、成交额、市盈率、市值等字段的字典。
        """
        market = market.upper()
        try:
            if market == "A":
                if ak is None:
                    return {"error": "akshare 未安装，无法获取A股数据"}
                df = ak.stock_zh_a_spot_em()
                row = df[df["代码"] == symbol]
                if row.empty:
                    return {"error": f"未找到A股代码 {symbol}，请检查代码是否正确"}
                r = row.iloc[0]
                return {
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
                }

            elif market == "US":
                if yf is None:
                    return {"error": "yfinance 未安装，无法获取美股数据"}
                ticker = yf.Ticker(symbol)
                info = ticker.info
                if not info or info.get("regularMarketPrice") is None:
                    return {"error": f"未找到美股代码 {symbol}"}
                prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
                price = info.get("regularMarketPrice") or info.get("currentPrice")
                change_pct = None
                if price and prev_close and prev_close != 0:
                    change_pct = _round2((price - prev_close) / prev_close * 100)
                return {
                    "名称": info.get("shortName") or info.get("longName", symbol),
                    "代码": symbol,
                    "现价": _round2(price),
                    "涨跌幅(%)": change_pct,
                    "成交量": info.get("regularMarketVolume"),
                    "市盈率": _round2(info.get("trailingPE")),
                    "前向市盈率": _round2(info.get("forwardPE")),
                    "总市值": info.get("marketCap"),
                    "52周最高": _round2(info.get("fiftyTwoWeekHigh")),
                    "52周最低": _round2(info.get("fiftyTwoWeekLow")),
                    "currency": info.get("currency", "USD"),
                    "market": "US",
                }

            elif market == "HK":
                # 港股通过 yfinance，代码需加 .HK 后缀
                if yf is None:
                    return {"error": "yfinance 未安装，无法获取港股数据"}
                yf_symbol = symbol if symbol.endswith(".HK") else f"{symbol}.HK"
                ticker = yf.Ticker(yf_symbol)
                info = ticker.info
                if not info or info.get("regularMarketPrice") is None:
                    return {"error": f"未找到港股代码 {symbol}"}
                prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
                price = info.get("regularMarketPrice") or info.get("currentPrice")
                change_pct = None
                if price and prev_close and prev_close != 0:
                    change_pct = _round2((price - prev_close) / prev_close * 100)
                return {
                    "名称": info.get("shortName") or info.get("longName", symbol),
                    "代码": symbol,
                    "现价": _round2(price),
                    "涨跌幅(%)": change_pct,
                    "成交量": info.get("regularMarketVolume"),
                    "市盈率": _round2(info.get("trailingPE")),
                    "总市值": info.get("marketCap"),
                    "currency": info.get("currency", "HKD"),
                    "market": "HK",
                }
            else:
                return {"error": f"不支持的市场代码: {market}，请使用 A/HK/US"}

        except Exception as e:
            return {"error": f"获取 {symbol} 实时行情失败: {str(e)}"}

    # ---------------------------------------------------------------
    # 工具2: get_stock_history
    # ---------------------------------------------------------------
    @mcp.tool
    def get_stock_history(
        symbol: str,
        market: str = "A",
        period: str = "daily",
        days: int = 30,
    ) -> dict:
        """获取股票历史K线数据。

        Args:
            symbol: 股票代码，如 "000001"（A股）或 "AAPL"（美股）。
            market: 市场代码。A=A股, US=美股。默认 "A"。
            period: K线周期。daily=日线, weekly=周线, monthly=月线。默认 "daily"。
            days: 获取最近多少天的数据，默认30，最多返回60条记录。

        Returns:
            包含 meta 信息和 data 列表（日期、开盘、最高、最低、收盘、成交量）的字典。
        """
        max_rows = 60
        days = min(days, 365)
        market = market.upper()

        try:
            if market == "A":
                if ak is None:
                    return {"error": "akshare 未安装，无法获取A股数据"}
                period_map = {"daily": "daily", "weekly": "weekly", "monthly": "monthly"}
                ak_period = period_map.get(period, "daily")
                end_date = datetime.now().strftime("%Y%m%d")
                start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period=ak_period,
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq",
                )
                if df is None or df.empty:
                    return {"error": f"未找到 {symbol} 的历史数据"}
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
                return {
                    "meta": {
                        "代码": symbol,
                        "market": "A",
                        "周期": period,
                        "数据条数": len(records),
                    },
                    "data": records,
                }

            elif market == "US":
                if yf is None:
                    return {"error": "yfinance 未安装，无法获取美股数据"}
                period_map = {"daily": "1d", "weekly": "1wk", "monthly": "1mo"}
                yf_interval = period_map.get(period, "1d")
                end = datetime.now()
                start = end - timedelta(days=days)
                df = yf.download(
                    symbol,
                    start=start.strftime("%Y-%m-%d"),
                    end=end.strftime("%Y-%m-%d"),
                    interval=yf_interval,
                    progress=False,
                )
                if df is None or df.empty:
                    return {"error": f"未找到 {symbol} 的历史数据"}
                df = df.tail(max_rows)
                # yfinance 返回的 columns 可能是 MultiIndex
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                records = []
                for date_idx, r in df.iterrows():
                    records.append({
                        "日期": _date_str(date_idx),
                        "开盘": _round2(r.get("Open")),
                        "最高": _round2(r.get("High")),
                        "最低": _round2(r.get("Low")),
                        "收盘": _round2(r.get("Close")),
                        "成交量": _round2(r.get("Volume")),
                    })
                return {
                    "meta": {
                        "代码": symbol,
                        "market": "US",
                        "周期": period,
                        "数据条数": len(records),
                    },
                    "data": records,
                }

            else:
                return {"error": f"get_stock_history 暂不支持市场: {market}，请使用 A 或 US"}

        except Exception as e:
            return {"error": f"获取 {symbol} 历史K线失败: {str(e)}"}

    # ---------------------------------------------------------------
    # 工具3: get_index_quote
    # ---------------------------------------------------------------
    @mcp.tool
    def get_index_quote(index_name: str = "all") -> dict:
        """获取主要股指行情。

        Args:
            index_name: 指数名称。支持：沪深300/上证指数/深证成指/创业板指/科创50/
                        标普500/纳斯达克/道琼斯/恒生指数，或 "all" 返回全部。

        Returns:
            包含指数名称、点位、涨跌幅、成交额的字典或列表。
        """
        domestic_indices = {
            "沪深300": "沪深300",
            "上证指数": "上证指数",
            "深证成指": "深证成指",
            "创业板指": "创业板指",
            "科创50": "科创50",
        }
        overseas_indices = {
            "标普500": "^GSPC",
            "纳斯达克": "^IXIC",
            "道琼斯": "^DJI",
            "恒生指数": "^HSI",
        }

        results = []

        try:
            # --- 国内指数 ---
            need_domestic = index_name == "all" or index_name in domestic_indices
            if need_domestic and ak is not None:
                try:
                    df = ak.stock_zh_index_spot_em()
                    if df is not None and not df.empty:
                        target_names = (
                            list(domestic_indices.values())
                            if index_name == "all"
                            else [domestic_indices[index_name]]
                        )
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
                            })
                except Exception as e:
                    results.append({"error": f"获取国内指数失败: {str(e)}"})

            # --- 海外指数 ---
            need_overseas = index_name == "all" or index_name in overseas_indices
            if need_overseas and yf is not None:
                target = (
                    overseas_indices.items()
                    if index_name == "all"
                    else [(index_name, overseas_indices[index_name])]
                )
                for cn_name, yf_symbol in target:
                    try:
                        ticker = yf.Ticker(yf_symbol)
                        info = ticker.info
                        price = info.get("regularMarketPrice") or info.get("previousClose")
                        prev = info.get("previousClose") or info.get("regularMarketPreviousClose")
                        change_pct = None
                        if price and prev and prev != 0:
                            change_pct = _round2((price - prev) / prev * 100)
                        results.append({
                            "指数名称": cn_name,
                            "最新点位": _round2(price),
                            "涨跌幅(%)": change_pct,
                            "market": "OVERSEAS",
                        })
                    except Exception:
                        results.append({"指数名称": cn_name, "error": "数据获取失败"})

            if not results:
                return {"error": f"未找到指数 '{index_name}' 的数据，请检查名称是否正确"}

            if len(results) == 1:
                return results[0]
            return {"data": results, "count": len(results)}

        except Exception as e:
            return {"error": f"获取指数行情失败: {str(e)}"}

    # ---------------------------------------------------------------
    # 工具4: get_forex
    # ---------------------------------------------------------------
    @mcp.tool
    def get_forex(pair: str = "all") -> dict:
        """获取主要货币对汇率。

        Args:
            pair: 货币对代码。支持：USDCNY/EURUSD/USDJPY/GBPUSD/AUDUSD/USDCAD/USDHKD，
                  或 "all" 返回全部主要货币对。

        Returns:
            包含货币对、买入价、卖出价、中间价、更新时间的字典或列表。
        """
        # yfinance 货币对映射
        yf_pairs = {
            "USDCNY": "CNY=X",
            "EURUSD": "EURUSD=X",
            "USDJPY": "JPY=X",
            "GBPUSD": "GBPUSD=X",
            "AUDUSD": "AUDUSD=X",
            "USDCAD": "CAD=X",
            "USDHKD": "HKD=X",
        }

        results = []
        pair = pair.upper()

        try:
            # 优先尝试 akshare
            if ak is not None:
                try:
                    df = ak.fx_spot_quote()
                    if df is not None and not df.empty:
                        # akshare 外汇数据列名可能变动，做兼容处理
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
                            if len(results) == 1:
                                return results[0]
                            return {"data": results, "count": len(results)}
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
                        change_pct = None
                        if price and prev and prev != 0:
                            change_pct = _round2((price - prev) / prev * 100)
                        results.append({
                            "货币对": name,
                            "最新价": _round2(price),
                            "前收": _round2(prev),
                            "涨跌幅(%)": change_pct,
                            "数据来源": "yfinance",
                        })
                    except Exception:
                        results.append({"货币对": name, "error": "数据获取失败"})

            if not results:
                return {"error": "无法获取外汇数据，请确认 akshare 或 yfinance 已安装"}

            if len(results) == 1:
                return results[0]
            return {"data": results, "count": len(results)}

        except Exception as e:
            return {"error": f"获取外汇数据失败: {str(e)}"}

    # ---------------------------------------------------------------
    # 工具5: get_commodity
    # ---------------------------------------------------------------
    @mcp.tool
    def get_commodity(commodity: str = "all") -> dict:
        """获取大宗商品价格。

        Args:
            commodity: 商品名称。支持：黄金/白银/原油/铜/铁矿石/天然气，或 "all" 返回全部。

        Returns:
            包含品种名称、最新价、涨跌幅、单位的字典或列表。
        """
        # yfinance 商品期货代码映射
        yf_commodities = {
            "黄金": {"symbol": "GC=F", "unit": "美元/盎司"},
            "白银": {"symbol": "SI=F", "unit": "美元/盎司"},
            "原油": {"symbol": "CL=F", "unit": "美元/桶"},
            "铜": {"symbol": "HG=F", "unit": "美元/磅"},
            "天然气": {"symbol": "NG=F", "unit": "美元/百万英热"},
            "铁矿石": {"symbol": None, "unit": "元/吨"},  # 铁矿石无 yfinance 代码
        }

        results = []

        try:
            # 尝试 akshare 获取国内期货主力合约行情
            if ak is not None and (commodity == "all" or commodity == "铁矿石"):
                try:
                    df = ak.futures_main_sina()
                    if df is not None and not df.empty:
                        iron_map = {"铁矿石": "I0"}
                        for cn_name, code_prefix in iron_map.items():
                            if commodity != "all" and commodity != cn_name:
                                continue
                            row = df[df["symbol"].str.startswith(code_prefix)]
                            if not row.empty:
                                r = row.iloc[0]
                                results.append({
                                    "品种": cn_name,
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
                    yf_sym = cfg["symbol"]
                    if yf_sym is None:
                        continue  # 铁矿石已在 akshare 部分处理
                    try:
                        ticker = yf.Ticker(yf_sym)
                        info = ticker.info
                        price = info.get("regularMarketPrice") or info.get("previousClose")
                        prev = info.get("previousClose")
                        change_pct = None
                        if price and prev and prev != 0:
                            change_pct = _round2((price - prev) / prev * 100)
                        results.append({
                            "品种": cn_name,
                            "最新价": _round2(price),
                            "涨跌幅(%)": change_pct,
                            "单位": cfg["unit"],
                            "数据来源": "yfinance",
                        })
                    except Exception:
                        results.append({"品种": cn_name, "error": "数据获取失败"})

            if not results:
                return {"error": f"未找到商品 '{commodity}' 的数据，请检查名称是否正确"}

            if len(results) == 1:
                return results[0]
            return {"data": results, "count": len(results)}

        except Exception as e:
            return {"error": f"获取大宗商品价格失败: {str(e)}"}
