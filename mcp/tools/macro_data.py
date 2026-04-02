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
# 缓存模块（可选）
# ---------------------------------------------------------------------------
try:
    _base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _base not in sys.path:
        sys.path.insert(0, _base)
    from utils.cache import DataCache
    _cache = DataCache()
except Exception:
    _cache = None

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
# 工具函数
# ---------------------------------------------------------------------------
def _round2(val):
    """安全地将数值保留2位小数。"""
    try:
        return round(float(val), 2)
    except (TypeError, ValueError):
        return val


def _date_str(val):
    """将各种日期格式统一为 YYYY-MM-DD 字符串。"""
    if val is None:
        return None
    if isinstance(val, str):
        return val[:10]
    try:
        return val.strftime("%Y-%m-%d")
    except Exception:
        return str(val)[:10]


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


# ===================================================================
# 注册入口
# ===================================================================
def register_tools(mcp):
    """将宏观经济数据工具注册到 FastMCP 实例。"""

    # ---------------------------------------------------------------
    # 工具6: get_macro_china
    # ---------------------------------------------------------------
    @mcp.tool
    def get_macro_china(indicator: str = "overview") -> dict:
        """获取中国宏观经济核心指标。

        Args:
            indicator: 指标名称。支持：GDP/CPI/PPI/PMI/M2/social_financing/trade/overview。
                       overview 模式返回所有指标的最新值汇总。默认 "overview"。

        Returns:
            包含指标名称、最新值/趋势数据的字典。overview 模式返回各指标最新值的汇总。
        """
        if ak is None:
            return {"error": "akshare 未安装，无法获取中国宏观数据"}

        indicator = indicator.lower()

        # 各指标获取函数
        def _get_gdp():
            try:
                df = ak.macro_china_gdp()
                records = _safe_records(df, max_rows=12)
                latest = records[-1] if records else {}
                return {"指标": "GDP", "最新数据": latest, "历史数据": records}
            except Exception as e:
                return {"指标": "GDP", "error": f"获取失败: {str(e)}"}

        def _get_cpi():
            try:
                df = ak.macro_china_cpi_monthly()
                records = _safe_records(df, max_rows=12)
                latest = records[-1] if records else {}
                return {"指标": "CPI", "最新数据": latest, "历史数据": records}
            except Exception as e:
                return {"指标": "CPI", "error": f"获取失败: {str(e)}"}

        def _get_ppi():
            try:
                df = ak.macro_china_ppi_yearly()
                records = _safe_records(df, max_rows=12)
                latest = records[-1] if records else {}
                return {"指标": "PPI", "最新数据": latest, "历史数据": records}
            except Exception as e:
                return {"指标": "PPI", "error": f"获取失败: {str(e)}"}

        def _get_pmi():
            try:
                df = ak.macro_china_pmi()
                records = _safe_records(df, max_rows=12)
                latest = records[-1] if records else {}
                return {"指标": "PMI", "最新数据": latest, "历史数据": records}
            except Exception as e:
                return {"指标": "PMI", "error": f"获取失败: {str(e)}"}

        def _get_m2():
            try:
                df = ak.macro_china_money_supply()
                records = _safe_records(df, max_rows=12)
                latest = records[-1] if records else {}
                return {"指标": "M2货币供应", "最新数据": latest, "历史数据": records}
            except Exception as e:
                return {"指标": "M2", "error": f"获取失败: {str(e)}"}

        def _get_social_financing():
            try:
                df = ak.macro_china_shrzgm()
                records = _safe_records(df, max_rows=12)
                latest = records[-1] if records else {}
                return {"指标": "社会融资规模", "最新数据": latest, "历史数据": records}
            except Exception as e:
                return {"指标": "社会融资规模", "error": f"获取失败: {str(e)}"}

        def _get_trade():
            try:
                # 尝试获取进出口数据
                df = ak.macro_china_trade_balance()
                records = _safe_records(df, max_rows=12)
                latest = records[-1] if records else {}
                return {"指标": "进出口贸易差额", "最新数据": latest, "历史数据": records}
            except Exception as e:
                return {"指标": "进出口", "error": f"获取失败: {str(e)}"}

        try:
            indicator_funcs = {
                "gdp": _get_gdp,
                "cpi": _get_cpi,
                "ppi": _get_ppi,
                "pmi": _get_pmi,
                "m2": _get_m2,
                "social_financing": _get_social_financing,
                "trade": _get_trade,
            }

            if indicator == "overview":
                overview = {"模式": "overview", "更新时间": datetime.now().strftime("%Y-%m-%d %H:%M"), "指标汇总": []}
                for name, func in indicator_funcs.items():
                    result = func()
                    # 只取最新值放入 overview
                    overview["指标汇总"].append({
                        "指标": result.get("指标", name),
                        "最新数据": result.get("最新数据"),
                        "error": result.get("error"),
                    })
                return overview

            if indicator in indicator_funcs:
                return indicator_funcs[indicator]()

            return {"error": f"不支持的指标: {indicator}，可选值: GDP/CPI/PPI/PMI/M2/social_financing/trade/overview"}

        except Exception as e:
            return {"error": f"获取中国宏观数据失败: {str(e)}"}

    # ---------------------------------------------------------------
    # 工具7: get_macro_global
    # ---------------------------------------------------------------
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
        if ak is None:
            return {"error": "akshare 未安装，无法获取全球宏观数据"}

        indicator = indicator.lower()

        def _get_us_interest_rate():
            try:
                df = ak.macro_usa_interest_rate()
                records = _safe_records(df, max_rows=12)
                latest = records[-1] if records else {}
                return {"指标": "美联储基准利率", "最新数据": latest, "历史数据": records}
            except Exception as e:
                return {"指标": "美联储基准利率", "error": f"获取失败: {str(e)}"}

        def _get_us_cpi():
            try:
                df = ak.macro_usa_cpi_monthly()
                records = _safe_records(df, max_rows=12)
                latest = records[-1] if records else {}
                return {"指标": "美国CPI", "最新数据": latest, "历史数据": records}
            except Exception as e:
                return {"指标": "美国CPI", "error": f"获取失败: {str(e)}"}

        def _get_us_ppi():
            try:
                df = ak.macro_usa_ppi()
                records = _safe_records(df, max_rows=12)
                latest = records[-1] if records else {}
                return {"指标": "美国PPI", "最新数据": latest, "历史数据": records}
            except Exception as e:
                return {"指标": "美国PPI", "error": f"获取失败: {str(e)}"}

        def _get_us_unemployment():
            try:
                df = ak.macro_usa_unemployment_rate()
                records = _safe_records(df, max_rows=12)
                latest = records[-1] if records else {}
                return {"指标": "美国失业率", "最新数据": latest, "历史数据": records}
            except Exception as e:
                return {"指标": "美国失业率", "error": f"获取失败: {str(e)}"}

        def _get_us_gdp():
            try:
                df = ak.macro_usa_gdp_monthly()
                records = _safe_records(df, max_rows=12)
                latest = records[-1] if records else {}
                return {"指标": "美国GDP", "最新数据": latest, "历史数据": records}
            except Exception as e:
                return {"指标": "美国GDP", "error": f"获取失败: {str(e)}"}

        def _get_us_non_farm():
            try:
                df = ak.macro_usa_non_farm()
                records = _safe_records(df, max_rows=12)
                latest = records[-1] if records else {}
                return {"指标": "美国非农就业", "最新数据": latest, "历史数据": records}
            except Exception as e:
                return {"指标": "美国非农就业", "error": f"获取失败: {str(e)}"}

        def _get_eu_cpi():
            try:
                df = ak.macro_euro_cpi_monthly()
                records = _safe_records(df, max_rows=12)
                latest = records[-1] if records else {}
                return {"指标": "欧元区CPI", "最新数据": latest, "历史数据": records}
            except Exception as e:
                return {"指标": "欧元区CPI", "error": f"获取失败: {str(e)}"}

        try:
            indicator_funcs = {
                "us_interest_rate": _get_us_interest_rate,
                "us_cpi": _get_us_cpi,
                "us_ppi": _get_us_ppi,
                "us_unemployment": _get_us_unemployment,
                "us_gdp": _get_us_gdp,
                "us_non_farm": _get_us_non_farm,
                "eu_cpi": _get_eu_cpi,
            }

            if indicator == "overview":
                overview = {"模式": "overview", "更新时间": datetime.now().strftime("%Y-%m-%d %H:%M"), "指标汇总": []}
                for name, func in indicator_funcs.items():
                    result = func()
                    overview["指标汇总"].append({
                        "指标": result.get("指标", name),
                        "最新数据": result.get("最新数据"),
                        "error": result.get("error"),
                    })
                return overview

            if indicator in indicator_funcs:
                return indicator_funcs[indicator]()

            return {
                "error": f"不支持的指标: {indicator}，可选值: "
                         f"us_interest_rate/us_cpi/us_ppi/us_unemployment/us_gdp/us_non_farm/eu_cpi/overview"
            }

        except Exception as e:
            return {"error": f"获取全球宏观数据失败: {str(e)}"}

    # ---------------------------------------------------------------
    # 工具8: get_fund_flow
    # ---------------------------------------------------------------
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
        if ak is None:
            return {"error": "akshare 未安装，无法获取资金流向数据"}

        flow_type = flow_type.lower()

        try:
            if flow_type == "north":
                return _get_north_flow()
            elif flow_type == "industry":
                return _get_industry_flow()
            elif flow_type == "concept":
                return _get_concept_flow()
            else:
                return {"error": f"不支持的资金流向类型: {flow_type}，可选值: north/industry/concept"}

        except Exception as e:
            return {"error": f"获取资金流向数据失败: {str(e)}"}

    def _get_north_flow() -> dict:
        """获取北向资金净流入数据。"""
        try:
            # 尝试多个可能的 akshare 接口名称（akshare 接口名经常变动）
            df = None
            errors = []

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
                # 再尝试沪股通/深股通分别获取
                try:
                    df = ak.stock_hsgt_north_acc_flow_in_em(symbol="北向")
                    if df is not None and not df.empty:
                        pass  # 成功
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

        except Exception as e:
            return {"指标": "北向资金", "error": f"获取失败: {str(e)}"}

    def _get_industry_flow() -> dict:
        """获取行业板块资金流向排名。"""
        try:
            df = None
            for func_name in [
                "stock_sector_fund_flow_rank",
                "stock_fund_flow_industry",
                "stock_sector_fund_flow_summary",
            ]:
                try:
                    func = getattr(ak, func_name, None)
                    if func is not None:
                        # 部分接口需要传入 indicator 参数
                        try:
                            df = func(indicator="今日")
                        except TypeError:
                            df = func()
                        if df is not None and not df.empty:
                            break
                except Exception:
                    continue

            if df is None or df.empty:
                return {"指标": "行业资金流向", "error": "无法获取行业资金流向数据，akshare 接口可能已变更"}

            df = df.head(20)
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

            return {
                "指标": "行业板块资金流向",
                "数据条数": len(records),
                "说明": "行业板块资金流向排名（前20）",
                "data": records,
            }

        except Exception as e:
            return {"指标": "行业资金流向", "error": f"获取失败: {str(e)}"}

    def _get_concept_flow() -> dict:
        """获取概念板块资金流向排名。"""
        try:
            df = None
            for func_name in [
                "stock_concept_fund_flow_his",
                "stock_fund_flow_concept",
                "stock_board_concept_fund_flow_summary",
            ]:
                try:
                    func = getattr(ak, func_name, None)
                    if func is not None:
                        try:
                            df = func(indicator="今日")
                        except TypeError:
                            df = func()
                        if df is not None and not df.empty:
                            break
                except Exception:
                    continue

            if df is None or df.empty:
                return {"指标": "概念资金流向", "error": "无法获取概念板块资金流向数据，akshare 接口可能已变更"}

            df = df.head(20)
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

            return {
                "指标": "概念板块资金流向",
                "数据条数": len(records),
                "说明": "概念板块资金流向排名（前20）",
                "data": records,
            }

        except Exception as e:
            return {"指标": "概念资金流向", "error": f"获取失败: {str(e)}"}
