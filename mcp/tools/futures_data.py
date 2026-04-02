#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货数据工具集 —— 提供期货实时行情、历史K线、持仓排名、基差分析能力。
通过 register_tools(mcp) 注册到 FastMCP 实例。
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
def _safe_float(val, decimals=2):
    """安全转换为浮点数并四舍五入，失败返回 None。"""
    if val is None:
        return None
    if pd and pd.isna(val):
        return None
    try:
        return round(float(val), decimals)
    except (TypeError, ValueError):
        return None


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
                rec[k] = _safe_float(v)
    return records


# ---------------------------------------------------------------------------
# 外盘期货代码映射
# ---------------------------------------------------------------------------
_FOREIGN_YF_MAP = {
    "CL": {"yf": "CL=F", "name": "WTI原油"},
    "GC": {"yf": "GC=F", "name": "COMEX黄金"},
    "SI": {"yf": "SI=F", "name": "COMEX白银"},
    "HG": {"yf": "HG=F", "name": "COMEX铜"},
    "NG": {"yf": "NG=F", "name": "天然气"},
    "ZS": {"yf": "ZS=F", "name": "CBOT大豆"},
    "ZC": {"yf": "ZC=F", "name": "CBOT玉米"},
    "ZW": {"yf": "ZW=F", "name": "CBOT小麦"},
}

# 持仓排名: 交易所 → akshare 函数名映射
_POSITION_RANK_FUNCS = {
    "dce":   "futures_dce_position_rank",
    "shfe":  "futures_shfe_position_rank",
    "czce":  "futures_czce_position_rank",
    "cffex": "futures_cffex_position_rank",
    "gfex":  "futures_gfex_position_rank",
}


# ---------------------------------------------------------------------------
# 业务逻辑独立函数
# ---------------------------------------------------------------------------
@handle_errors
def fetch_futures_realtime(symbol: str, market: str = "domestic") -> dict:
    """获取期货实时行情的核心逻辑。"""
    market = market.lower()

    if market == "domestic":
        if ak is None:
            return {"error": "akshare 未安装，无法获取国内期货数据"}
        try:
            df = ak.futures_zh_spot()
        except Exception as e:
            return {"error": f"获取国内期货实时行情失败: {e}"}
        if df is None or df.empty:
            return {"error": "国内期货实时行情数据为空"}

        # 尝试通过 symbol 列匹配（不同版本 akshare 列名可能不同）
        symbol_upper = symbol.upper()
        matched = None
        for col in df.columns:
            if "symbol" in col.lower() or "代码" in col or "合约" in col:
                mask = df[col].astype(str).str.upper() == symbol_upper
                if mask.any():
                    matched = df[mask].iloc[0]
                    break
        if matched is None:
            # 尝试模糊匹配
            for col in df.columns:
                if "symbol" in col.lower() or "代码" in col or "合约" in col:
                    mask = df[col].astype(str).str.upper().str.contains(symbol_upper, na=False)
                    if mask.any():
                        matched = df[mask].iloc[0]
                        break
        if matched is None:
            return {"error": f"未找到国内期货代码 {symbol}，请检查代码是否正确（如 AU0, RB0, I0）"}

        # 通用字段提取（兼容不同列名）
        def _get(row, *keys):
            for k in keys:
                if k in row.index:
                    return row[k]
            return None

        return {
            "symbol": str(_get(matched, "symbol", "代码", "合约") or symbol),
            "name": str(_get(matched, "name", "名称", "品种") or ""),
            "price": _safe_float(_get(matched, "current_price", "最新价", "price", "close")),
            "change": _safe_float(_get(matched, "change", "涨跌额")),
            "change_pct": _safe_float(_get(matched, "changepercent", "涨跌幅", "change_pct")),
            "open": _safe_float(_get(matched, "open", "今开", "开盘")),
            "high": _safe_float(_get(matched, "high", "最高")),
            "low": _safe_float(_get(matched, "low", "最低")),
            "volume": _safe_float(_get(matched, "volume", "成交量"), 0),
            "open_interest": _safe_float(_get(matched, "hold", "持仓量", "open_interest"), 0),
            "settlement": _safe_float(_get(matched, "settlement", "结算价")),
            "market": "domestic",
        }

    elif market == "foreign":
        symbol_upper = symbol.upper()
        mapping = _FOREIGN_YF_MAP.get(symbol_upper)

        # 优先尝试 akshare 外盘接口
        if ak is not None:
            try:
                df = ak.futures_foreign_commodity_realtime(symbol=symbol)
                if df is not None and not df.empty:
                    r = df.iloc[0] if len(df) > 0 else None
                    if r is not None:
                        def _fget(row, *keys):
                            for k in keys:
                                if k in row.index:
                                    return row[k]
                            return None
                        return {
                            "symbol": symbol_upper,
                            "name": str(_fget(r, "name", "名称") or (mapping["name"] if mapping else symbol_upper)),
                            "price": _safe_float(_fget(r, "current_price", "最新价", "price", "value")),
                            "change": _safe_float(_fget(r, "change", "涨跌额")),
                            "change_pct": _safe_float(_fget(r, "changepercent", "涨跌幅")),
                            "open": _safe_float(_fget(r, "open", "开盘")),
                            "high": _safe_float(_fget(r, "high", "最高")),
                            "low": _safe_float(_fget(r, "low", "最低")),
                            "volume": _safe_float(_fget(r, "volume", "成交量"), 0),
                            "market": "foreign",
                            "source": "akshare",
                        }
            except Exception:
                pass  # fallback to yfinance

        # yfinance fallback
        if yf is not None and mapping:
            try:
                ticker = yf.Ticker(mapping["yf"])
                info = ticker.info
                price = info.get("regularMarketPrice") or info.get("previousClose")
                prev = info.get("previousClose")
                change = None
                change_pct = None
                if price and prev and prev != 0:
                    change = _safe_float(price - prev)
                    change_pct = _safe_float((price - prev) / prev * 100)
                return {
                    "symbol": symbol_upper,
                    "name": mapping["name"],
                    "price": _safe_float(price),
                    "change": change,
                    "change_pct": change_pct,
                    "open": _safe_float(info.get("regularMarketOpen")),
                    "high": _safe_float(info.get("regularMarketDayHigh")),
                    "low": _safe_float(info.get("regularMarketDayLow")),
                    "volume": _safe_float(info.get("regularMarketVolume"), 0),
                    "market": "foreign",
                    "source": "yfinance",
                }
            except Exception as e:
                return {"error": f"yfinance 获取外盘期货 {symbol} 失败: {e}"}

        return {"error": f"无法获取外盘期货 {symbol} 数据，请检查代码是否正确（支持: {', '.join(_FOREIGN_YF_MAP.keys())}）"}

    else:
        return {"error": f"不支持的市场代码: {market}，请使用 domestic（国内）或 foreign（外盘）"}


@handle_errors
def fetch_futures_history(symbol: str, period: str = "daily",
                          start_date: str = None, end_date: str = None,
                          market: str = "domestic") -> dict:
    """获取期货历史K线数据的核心逻辑。"""
    max_rows = config.max_records
    market = market.lower()
    period = period.lower()

    if market == "domestic":
        if ak is None:
            return {"error": "akshare 未安装，无法获取国内期货历史数据"}
        try:
            df = ak.futures_zh_daily_sina(symbol=symbol)
        except Exception as e:
            return {"error": f"获取国内期货 {symbol} 日线数据失败: {e}（请检查代码，如 RB0, AU0）"}

        if df is None or df.empty:
            return {"error": f"未找到国内期货 {symbol} 的历史数据"}

        # 日期过滤
        date_col = None
        for col in ("date", "日期"):
            if col in df.columns:
                date_col = col
                break
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            if start_date:
                df = df[df[date_col] >= pd.to_datetime(start_date)]
            if end_date:
                df = df[df[date_col] <= pd.to_datetime(end_date)]

        df = df.tail(max_rows)
        records = []
        for _, r in df.iterrows():
            def _hget(row, *keys):
                for k in keys:
                    if k in row.index:
                        return row[k]
                return None
            records.append({
                "date": _date_str(_hget(r, "date", "日期")),
                "open": _safe_float(_hget(r, "open", "开盘")),
                "high": _safe_float(_hget(r, "high", "最高")),
                "low": _safe_float(_hget(r, "low", "最低")),
                "close": _safe_float(_hget(r, "close", "收盘")),
                "volume": _safe_float(_hget(r, "volume", "成交量"), 0),
                "open_interest": _safe_float(_hget(r, "hold", "持仓量"), 0),
            })
        return {
            "symbol": symbol,
            "period": period,
            "market": "domestic",
            "count": len(records),
            "data": records,
        }

    elif market == "foreign":
        symbol_upper = symbol.upper()
        mapping = _FOREIGN_YF_MAP.get(symbol_upper)
        if yf is None:
            return {"error": "yfinance 未安装，无法获取外盘期货历史数据"}
        if not mapping:
            return {"error": f"不支持的外盘期货代码: {symbol}（支持: {', '.join(_FOREIGN_YF_MAP.keys())}）"}

        period_map = {"daily": "1d", "weekly": "1wk", "monthly": "1mo"}
        interval = period_map.get(period, "1d")

        end_dt = datetime.now()
        start_dt = end_dt - timedelta(days=config.default_history_days)
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        try:
            df = yf.download(
                mapping["yf"],
                start=start_dt.strftime("%Y-%m-%d"),
                end=end_dt.strftime("%Y-%m-%d"),
                interval=interval,
                progress=False,
            )
        except Exception as e:
            return {"error": f"yfinance 获取 {symbol} 历史数据失败: {e}"}

        if df is None or df.empty:
            return {"error": f"未找到外盘期货 {symbol} 的历史数据"}

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.tail(max_rows)
        records = []
        for date_idx, r in df.iterrows():
            records.append({
                "date": _date_str(date_idx),
                "open": _safe_float(r.get("Open")),
                "high": _safe_float(r.get("High")),
                "low": _safe_float(r.get("Low")),
                "close": _safe_float(r.get("Close")),
                "volume": _safe_float(r.get("Volume"), 0),
            })
        return {
            "symbol": symbol_upper,
            "name": mapping["name"],
            "period": period,
            "market": "foreign",
            "count": len(records),
            "data": records,
        }

    else:
        return {"error": f"不支持的市场代码: {market}，请使用 domestic（国内）或 foreign（外盘）"}


@handle_errors
def fetch_futures_position(symbol: str, exchange: str,
                           date: str = None) -> dict:
    """获取期货持仓排名/多空比的核心逻辑。"""
    if ak is None:
        return {"error": "akshare 未安装，无法获取持仓排名数据"}

    exchange = exchange.lower()
    func_name = _POSITION_RANK_FUNCS.get(exchange)
    if not func_name:
        return {"error": f"不支持的交易所: {exchange}（支持: {', '.join(_POSITION_RANK_FUNCS.keys())}）"}

    if not hasattr(ak, func_name):
        return {"error": f"akshare 版本不支持 {func_name}，请升级 akshare"}

    if date is None:
        # 默认使用最近一个交易日（取昨天）
        date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

    try:
        api_func = getattr(ak, func_name)
        # 不同交易所 API 参数格式略有差异
        if exchange == "czce":
            df = api_func(date=date, indicator="持仓量")
        else:
            df = api_func(date=date)
    except Exception as e:
        return {"error": f"获取 {exchange.upper()} 持仓排名失败: {e}（日期: {date}）"}

    if df is None or df.empty:
        return {"error": f"未找到 {exchange.upper()} 在 {date} 的持仓数据"}

    # 按品种过滤
    symbol_lower = symbol.lower()
    symbol_col = None
    for col in df.columns:
        cl = col.lower()
        if cl in ("symbol", "品种", "合约", "variety", "品种代码"):
            symbol_col = col
            break

    if symbol_col:
        mask = df[symbol_col].astype(str).str.lower().str.contains(symbol_lower, na=False)
        df = df[mask]
        if df.empty:
            return {"error": f"未找到品种 {symbol} 在 {exchange.upper()} {date} 的持仓数据"}

    # 提取多头和空头持仓
    long_positions = []
    short_positions = []

    def _pget(row, *keys):
        for k in keys:
            if k in row.index:
                return row[k]
        return None

    # 检测数据中的类型列（不同交易所格式不同）
    type_col = None
    for col in df.columns:
        cl = col.lower()
        if cl in ("type", "类型", "数据类型"):
            type_col = col
            break

    if type_col:
        # 有明确的类型列区分多空
        for _, r in df.iterrows():
            entry = {
                "rank": _safe_float(_pget(r, "rank", "名次", "排名"), 0),
                "broker": str(_pget(r, "member_name", "会员简称", "期货公司", "member") or ""),
                "volume": _safe_float(_pget(r, "vol", "持仓量", "volume", "成交量"), 0),
                "volume_change": _safe_float(_pget(r, "vol_chg", "增减", "变化", "volume_change"), 0),
            }
            row_type = str(r[type_col]).strip()
            if "多" in row_type or "long" in row_type.lower() or "买" in row_type:
                long_positions.append(entry)
            elif "空" in row_type or "short" in row_type.lower() or "卖" in row_type:
                short_positions.append(entry)
    else:
        # 没有类型列，尝试根据列名区分（如 买持仓量 / 卖持仓量）
        for _, r in df.iterrows():
            base = {
                "rank": _safe_float(_pget(r, "rank", "名次", "排名"), 0),
                "broker": str(_pget(r, "member_name", "会员简称", "期货公司", "member") or ""),
            }
            long_vol = _pget(r, "long_vol", "买持仓量", "多单量")
            short_vol = _pget(r, "short_vol", "卖持仓量", "空单量")
            long_chg = _pget(r, "long_vol_chg", "买持仓变化", "多单变化")
            short_chg = _pget(r, "short_vol_chg", "卖持仓变化", "空单变化")

            if long_vol is not None:
                long_positions.append({
                    **base,
                    "volume": _safe_float(long_vol, 0),
                    "volume_change": _safe_float(long_chg, 0),
                })
            if short_vol is not None:
                short_positions.append({
                    **base,
                    "volume": _safe_float(short_vol, 0),
                    "volume_change": _safe_float(short_chg, 0),
                })

        # 兜底：如果还是没有区分出多空，把全部数据作为 raw 返回
        if not long_positions and not short_positions:
            records = _df_to_records(df, config.max_records)
            return {
                "symbol": symbol,
                "exchange": exchange.upper(),
                "date": date,
                "raw_data": records,
                "note": "持仓数据格式无法自动区分多空，已返回原始数据",
            }

    # 汇总统计
    total_long = sum(p.get("volume", 0) or 0 for p in long_positions)
    total_short = sum(p.get("volume", 0) or 0 for p in short_positions)
    net_position = total_long - total_short
    long_short_ratio = _safe_float(total_long / total_short) if total_short else None

    return {
        "symbol": symbol,
        "exchange": exchange.upper(),
        "date": date,
        "long_positions": long_positions,
        "short_positions": short_positions,
        "summary": {
            "total_long": _safe_float(total_long, 0),
            "total_short": _safe_float(total_short, 0),
            "net_position": _safe_float(net_position, 0),
            "long_short_ratio": long_short_ratio,
        },
    }


@handle_errors
def fetch_futures_basis(symbol: str) -> dict:
    """获取期货基差/升贴水分析的核心逻辑。"""
    if ak is None:
        return {"error": "akshare 未安装，无法获取基差数据"}

    symbol_upper = symbol.upper()
    today = datetime.now().strftime("%Y%m%d")

    # 1. 获取现货价格
    spot_price = None
    try:
        spot_df = ak.futures_spot_price(date=today)
        if spot_df is not None and not spot_df.empty:
            for col in spot_df.columns:
                cl = col.lower()
                if cl in ("symbol", "品种", "品种代码", "商品"):
                    mask = spot_df[col].astype(str).str.upper().str.contains(symbol_upper, na=False)
                    if mask.any():
                        row = spot_df[mask].iloc[0]
                        for pcol in ("spot_price", "现货价格", "现货价", "价格"):
                            if pcol in row.index:
                                spot_price = _safe_float(row[pcol])
                                break
                        break
    except Exception:
        pass  # 现货价格获取失败不阻断

    # 2. 获取期货主力合约价格及各合约价格
    futures_price = None
    contracts = []
    try:
        futures_df = ak.futures_zh_spot()
        if futures_df is not None and not futures_df.empty:
            for col in futures_df.columns:
                cl = col.lower()
                if "symbol" in cl or "代码" in cl or "合约" in cl:
                    # 主力合约（如 AU0, RB0）
                    main_mask = futures_df[col].astype(str).str.upper() == f"{symbol_upper}0"
                    if main_mask.any():
                        main_row = futures_df[main_mask].iloc[0]
                        for pcol in ("current_price", "最新价", "price", "close"):
                            if pcol in main_row.index:
                                futures_price = _safe_float(main_row[pcol])
                                break

                    # 收集该品种所有合约
                    all_mask = futures_df[col].astype(str).str.upper().str.startswith(symbol_upper)
                    if all_mask.any():
                        for _, r in futures_df[all_mask].iterrows():
                            contract_code = str(r[col])
                            cprice = None
                            for pcol in ("current_price", "最新价", "price", "close"):
                                if pcol in r.index:
                                    cprice = _safe_float(r[pcol])
                                    break
                            contract_basis = _safe_float(spot_price - cprice) if spot_price and cprice else None
                            contracts.append({
                                "contract": contract_code,
                                "price": cprice,
                                "basis": contract_basis,
                            })
                    break
    except Exception as e:
        if futures_price is None:
            return {"error": f"获取期货行情数据失败: {e}"}

    # 3. 计算基差
    basis = None
    basis_rate = None
    structure = None

    if spot_price is not None and futures_price is not None:
        basis = _safe_float(spot_price - futures_price)
        if futures_price != 0:
            basis_rate = _safe_float(basis / futures_price * 100)
        # 期限结构判断
        if basis > 0:
            structure = "backwardation"  # 现货 > 期货 → 现货升水(back)
        elif basis < 0:
            structure = "contango"       # 现货 < 期货 → 期货升水(contango)
        else:
            structure = "flat"

    result = {
        "symbol": symbol_upper,
        "spot_price": spot_price,
        "futures_price": futures_price,
        "basis": basis,
        "basis_rate": basis_rate,
        "structure": structure,
        "contracts": contracts,
        "date": datetime.now().strftime("%Y-%m-%d"),
    }

    if spot_price is None and futures_price is None:
        result["warning"] = f"未能获取 {symbol_upper} 的现货和期货价格数据"
    elif spot_price is None:
        result["warning"] = f"未能获取 {symbol_upper} 的现货价格，仅返回期货合约数据"

    return result


# ===================================================================
# 注册入口（薄包装器）
# ===================================================================
def register_tools(mcp):
    """将期货数据工具注册到 FastMCP 实例。"""

    @mcp.tool
    def get_futures_realtime(symbol: str, market: str = "domestic") -> dict:
        """获取期货实时行情。

        Args:
            symbol: 期货代码。国内如 "AU0"（黄金主力）、"RB0"（螺纹钢主力）、"I0"（铁矿石主力）；
                     外盘如 "CL"（WTI原油）、"GC"（COMEX黄金）。
            market: 市场。"domestic"=国内期货（默认），"foreign"=外盘期货。

        Returns:
            包含 symbol、name、price、change、change_pct、open、high、low、volume、open_interest 等字段的字典。
        """
        return fetch_futures_realtime(symbol, market)

    @mcp.tool
    def get_futures_history(symbol: str, period: str = "daily",
                            start_date: str = None, end_date: str = None,
                            market: str = "domestic") -> dict:
        """获取期货历史K线数据。

        Args:
            symbol: 期货代码，如 "RB0"（螺纹钢主力）、"CL"（WTI原油）。
            period: K线周期。"daily"=日线（默认），"weekly"=周线，"monthly"=月线。
            start_date: 起始日期，格式 "YYYY-MM-DD"，可选。
            end_date: 结束日期，格式 "YYYY-MM-DD"，可选。
            market: 市场。"domestic"=国内（默认），"foreign"=外盘。

        Returns:
            包含 symbol、period、count 和 data 列表（date、open、high、low、close、volume、open_interest）的字典。
        """
        return fetch_futures_history(symbol, period, start_date, end_date, market)

    @mcp.tool
    def get_futures_position(symbol: str, exchange: str,
                             date: str = None) -> dict:
        """获取期货持仓排名与多空比。

        Args:
            symbol: 品种代码，如 "rb"（螺纹钢）、"au"（黄金）、"i"（铁矿石）。
            exchange: 交易所代码。"shfe"=上期所，"dce"=大商所，"czce"=郑商所，
                      "cffex"=中金所，"gfex"=广期所。
            date: 交易日期，格式 "YYYYMMDD"，可选（默认取最近交易日）。

        Returns:
            包含 long_positions（多头持仓排名）、short_positions（空头持仓排名）、
            summary（total_long、total_short、net_position、long_short_ratio）的字典。
        """
        return fetch_futures_position(symbol, exchange, date)

    @mcp.tool
    def get_futures_basis(symbol: str) -> dict:
        """获取期货基差/升贴水分析。

        Args:
            symbol: 品种代码，如 "RB"（螺纹钢）、"AU"（黄金）、"CU"（铜）。

        Returns:
            包含 spot_price（现货价）、futures_price（期货主力价）、basis（基差）、
            basis_rate（基差率%）、structure（contango/backwardation）、
            contracts（各合约价格与基差）的字典。
        """
        return fetch_futures_basis(symbol)
