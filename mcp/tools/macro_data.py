#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宏观经济数据工具集 —— 提供中国/全球宏观经济指标与资金流向数据获取能力。
通过 register_tools(mcp) 注册到 FastMCP 实例。
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
    import pandas as pd
except ImportError:
    pd = None


# ---------------------------------------------------------------------------
# 公共辅助函数
# ---------------------------------------------------------------------------
def _safe_records(df, max_rows: int = 12, date_col: str = None) -> list[dict]:
    """安全地将 DataFrame 转为 list[dict]，保留最近 max_rows 条。"""
    if df is None or (hasattr(df, "empty") and df.empty):
        return []
    df = df.tail(max_rows)
    records = df.to_dict(orient="records")
    for rec in records:
        for k, v in list(rec.items()):
            if pd and pd.isna(v):
                rec[k] = None
            elif isinstance(v, float):
                rec[k] = _round2(v)
        if date_col and date_col in rec:
            rec[date_col] = _date_str(rec[date_col])
    return records


def _fetch_single_indicator(func_name: str, label: str, max_rows: int = 12) -> dict:
    """通用 akshare 宏观指标获取：调用 ak.<func_name>() → 标准化返回。"""
    try:
        func = getattr(ak, func_name, None)
        if func is None:
            return {"指标": label, "error": f"akshare 无 {func_name} 接口"}
        df = func()
        records = _safe_records(df, max_rows=max_rows)
        latest = records[-1] if records else {}
        return {"指标": label, "最新数据": latest, "历史数据": records}
    except Exception as e:
        return {"指标": label, "error": f"获取失败: {str(e)}"}


def _build_overview(indicator_map: dict) -> dict:
    """遍历指标表构建 overview 汇总。"""
    overview = {
        "模式": "overview",
        "更新时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "指标汇总": [],
    }
    for _key, (func_name, label) in indicator_map.items():
        result = _fetch_single_indicator(func_name, label)
        overview["指标汇总"].append({
            "指标": result.get("指标", _key),
            "最新数据": result.get("最新数据"),
            "error": result.get("error"),
        })
    return overview


def _df_rows_to_records(df, max_rows: int = 20) -> list[dict]:
    """将 DataFrame 行转为清洗后的 list[dict]（用于资金流向等）。"""
    if df is None or df.empty:
        return []
    df = df.head(max_rows)
    records = []
    for _, r in df.iterrows():
        rec = {}
        for col in df.columns:
            val = r[col]
            if pd and pd.isna(val):
                rec[col] = None
            elif isinstance(val, float):
                rec[col] = _round2(val)
            else:
                rec[col] = str(val)
        records.append(rec)
    return records


def _try_akshare_funcs(func_names: list, with_indicator: bool = False) -> pd.DataFrame | None:
    """依次尝试多个 akshare 接口名，返回第一个成功的 DataFrame。"""
    for func_name in func_names:
        try:
            func = getattr(ak, func_name, None)
            if func is None:
                continue
            if with_indicator:
                try:
                    df = func(indicator="今日")
                except TypeError:
                    df = func()
            else:
                df = func()
            if df is not None and not df.empty:
                return df
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# 指标注册表（消除14个重复闭包的核心数据结构）
# ---------------------------------------------------------------------------
_CHINA_INDICATORS = {
    "gdp":              ("macro_china_gdp",           "GDP"),
    "cpi":              ("macro_china_cpi_monthly",    "CPI"),
    "ppi":              ("macro_china_ppi_yearly",     "PPI"),
    "pmi":              ("macro_china_pmi",            "PMI"),
    "m2":               ("macro_china_money_supply",   "M2货币供应"),
    "social_financing": ("macro_china_shrzgm",         "社会融资规模"),
    "trade":            ("macro_china_trade_balance",   "进出口贸易差额"),
}

_GLOBAL_INDICATORS = {
    "us_interest_rate": ("macro_usa_interest_rate",     "美联储基准利率"),
    "us_cpi":           ("macro_usa_cpi_monthly",       "美国CPI"),
    "us_ppi":           ("macro_usa_ppi",               "美国PPI"),
    "us_unemployment":  ("macro_usa_unemployment_rate", "美国失业率"),
    "us_gdp":           ("macro_usa_gdp_monthly",       "美国GDP"),
    "us_non_farm":      ("macro_usa_non_farm",          "美国非农就业"),
    "eu_cpi":           ("macro_euro_cpi_monthly",      "欧元区CPI"),
}


# ---------------------------------------------------------------------------
# 业务逻辑独立函数
# ---------------------------------------------------------------------------
@handle_errors
def fetch_macro_china(indicator: str = "overview") -> dict:
    """获取中国宏观经济核心指标的核心逻辑。"""
    if ak is None:
        return {"error": "akshare 未安装，无法获取中国宏观数据"}
    indicator = indicator.lower()
    if indicator == "overview":
        return _build_overview(_CHINA_INDICATORS)
    if indicator in _CHINA_INDICATORS:
        func_name, label = _CHINA_INDICATORS[indicator]
        return _fetch_single_indicator(func_name, label)
    return {"error": f"不支持的指标: {indicator}，可选值: GDP/CPI/PPI/PMI/M2/social_financing/trade/overview"}


@handle_errors
def fetch_macro_global(indicator: str = "overview") -> dict:
    """获取全球主要经济体宏观数据的核心逻辑。"""
    if ak is None:
        return {"error": "akshare 未安装，无法获取全球宏观数据"}
    indicator = indicator.lower()
    if indicator == "overview":
        return _build_overview(_GLOBAL_INDICATORS)
    if indicator in _GLOBAL_INDICATORS:
        func_name, label = _GLOBAL_INDICATORS[indicator]
        return _fetch_single_indicator(func_name, label)
    return {
        "error": f"不支持的指标: {indicator}，可选值: "
                 f"us_interest_rate/us_cpi/us_ppi/us_unemployment/us_gdp/us_non_farm/eu_cpi/overview"
    }


@handle_errors
def fetch_fund_flow(flow_type: str = "north") -> dict:
    """获取资金流向数据的核心逻辑。"""
    if ak is None:
        return {"error": "akshare 未安装，无法获取资金流向数据"}
    flow_type = flow_type.lower()

    if flow_type == "north":
        return _fetch_north_flow()
    elif flow_type == "industry":
        return _fetch_sector_flow(
            func_names=["stock_sector_fund_flow_rank", "stock_fund_flow_industry", "stock_sector_fund_flow_summary"],
            label="行业板块资金流向",
            desc="行业板块资金流向排名（前20）",
        )
    elif flow_type == "concept":
        return _fetch_sector_flow(
            func_names=["stock_concept_fund_flow_his", "stock_fund_flow_concept", "stock_board_concept_fund_flow_summary"],
            label="概念板块资金流向",
            desc="概念板块资金流向排名（前20）",
        )
    else:
        return {"error": f"不支持的资金流向类型: {flow_type}，可选值: north/industry/concept"}


def _fetch_north_flow() -> dict:
    """获取北向资金净流入数据。"""
    errors = []
    df = None

    for func_name in [
        "stock_hsgt_north_net_flow_in_em",
        "stock_em_hsgt_north_net_flow_in",
        "stock_hsgt_hist_em",
    ]:
        try:
            func = getattr(ak, func_name, None)
            if func is not None:
                df = func()
                if df is not None and not df.empty:
                    break
        except Exception as e:
            errors.append(f"{func_name}: {str(e)}")
            continue

    if df is None or df.empty:
        try:
            df = ak.stock_hsgt_north_acc_flow_in_em(symbol="北向")
        except Exception as e:
            errors.append(f"stock_hsgt_north_acc_flow_in_em: {str(e)}")

    if df is None or df.empty:
        return {
            "指标": "北向资金",
            "error": f"所有接口均无法获取数据。尝试的接口: {'; '.join(errors) if errors else '无可用接口'}",
        }

    df = df.tail(20)
    records = []
    for _, r in df.iterrows():
        rec = {}
        for col in df.columns:
            val = r[col]
            if pd and pd.isna(val):
                rec[col] = None
            elif isinstance(val, float):
                rec[col] = _round2(val)
            else:
                rec[col] = _date_str(val) if "日期" in col or "date" in str(col).lower() else str(val)
        records.append(rec)

    return {
        "指标": "北向资金",
        "数据条数": len(records),
        "说明": "最近20个交易日北向资金净流入（单位: 亿元）",
        "data": records,
    }


def _fetch_sector_flow(func_names: list, label: str, desc: str) -> dict:
    """通用板块资金流向获取（行业/概念复用）。"""
    df = _try_akshare_funcs(func_names, with_indicator=True)
    if df is None or df.empty:
        return {"指标": label, "error": f"无法获取{label}数据，akshare 接口可能已变更"}
    records = _df_rows_to_records(df, max_rows=20)
    return {"指标": label, "数据条数": len(records), "说明": desc, "data": records}


# ===================================================================
# 注册入口（薄包装器）
# ===================================================================
def register_tools(mcp):
    """将宏观经济数据工具注册到 FastMCP 实例。"""

    @mcp.tool
    def get_macro_china(indicator: str = "overview") -> dict:
        """获取中国宏观经济核心指标。

        Args:
            indicator: 指标名称。支持：GDP/CPI/PPI/PMI/M2/social_financing/trade/overview。
                       overview 模式返回所有指标的最新值汇总。默认 "overview"。

        Returns:
            包含指标名称、最新值/趋势数据的字典。overview 模式返回各指标最新值的汇总。
        """
        return fetch_macro_china(indicator)

    @mcp.tool
    def get_macro_global(indicator: str = "overview") -> dict:
        """获取全球主要经济体宏观数据。

        Args:
            indicator: 指标名称。支持：us_interest_rate/us_cpi/us_ppi/us_unemployment/
                       us_gdp/us_non_farm/eu_cpi/overview。
                       overview 模式返回各指标最新值。默认 "overview"。

        Returns:
            包含指标名称、最新值/趋势数据的字典。
        """
        return fetch_macro_global(indicator)

    @mcp.tool
    def get_fund_flow(flow_type: str = "north") -> dict:
        """获取资金流向数据。

        Args:
            flow_type: 资金流向类型。
                       north = 北向资金（沪深港通北向净流入）；
                       industry = 行业板块资金流向排名；
                       concept = 概念板块资金流向排名。
                       默认 "north"。

        Returns:
            包含资金流向数据列表的字典，最近20个交易日或前20名板块。
        """
        return fetch_fund_flow(flow_type)
