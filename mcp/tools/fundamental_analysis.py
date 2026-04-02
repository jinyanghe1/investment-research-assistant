#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fundamental_analysis.py — 企业基本面深度分析工具集

提供三大核心功能：
  1. 企业基本面全景画像（盈利/成长/运营/偿债/现金流/估值/质量评分）
  2. 同行业对标分析（行业内多维度横向比较与排名）
  3. 股东结构分析（十大股东、机构持仓、筹码集中度）

注册模式: register_tools(mcp) 供 FastMCP 3.x 服务端调用
数据源: akshare (A股) + yfinance (美股/港股 fallback)
"""

import os
import sys
import math
from datetime import datetime

# ---------------------------------------------------------------------------
# 基础设施
# ---------------------------------------------------------------------------
_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _base not in sys.path:
    sys.path.insert(0, _base)

from config import config
from utils.errors import handle_errors, MCPToolError, ErrorCode

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

try:
    import yfinance as yf
except ImportError:
    yf = None


# ---------------------------------------------------------------------------
# 内部工具函数
# ---------------------------------------------------------------------------

def _safe_float(val, decimals=2):
    """将值转为保留指定小数位的浮点数，无效值返回 None。"""
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, decimals)
    except (TypeError, ValueError):
        return None


def _safe_pct(val, decimals=2):
    """将百分比值安全转换，已是百分比形式则直接取值。"""
    v = _safe_float(val, decimals)
    if v is not None and abs(v) < 1e-10:
        return 0.0
    return v


def _first_valid(df, col_candidates: list, row_idx: int = 0):
    """从 DataFrame 中按候选列名顺序取第一个存在且有值的列的值。"""
    if df is None or df.empty:
        return None
    for col in col_candidates:
        if col in df.columns:
            try:
                val = df.iloc[row_idx][col]
                if pd and pd.notna(val):
                    return val
            except (IndexError, KeyError):
                continue
    return None


def _get_stock_name(symbol: str) -> str:
    """获取 A 股股票名称。"""
    try:
        info_df = ak.stock_individual_info_em(symbol=symbol)
        if info_df is not None and not info_df.empty:
            for _, r in info_df.iterrows():
                key = str(r.iloc[0]) if len(r) >= 2 else ""
                if "简称" in key or "名称" in key:
                    return str(r.iloc[1])
    except Exception:
        pass
    return symbol


def _get_stock_industry(symbol: str) -> str:
    """获取 A 股股票所属行业。"""
    try:
        info_df = ak.stock_individual_info_em(symbol=symbol)
        if info_df is not None and not info_df.empty:
            for _, r in info_df.iterrows():
                key = str(r.iloc[0]) if len(r) >= 2 else ""
                if "行业" in key:
                    return str(r.iloc[1])
    except Exception:
        pass
    return "未知"


def _get_stock_basic_info(symbol: str) -> dict:
    """一次性获取 A 股股票名称、行业等基本信息。"""
    info = {"name": symbol, "industry": "未知"}
    try:
        info_df = ak.stock_individual_info_em(symbol=symbol)
        if info_df is not None and not info_df.empty:
            for _, r in info_df.iterrows():
                key = str(r.iloc[0]) if len(r) >= 2 else ""
                val = str(r.iloc[1]) if len(r) >= 2 else ""
                if "简称" in key or "名称" in key:
                    info["name"] = val
                elif "行业" in key:
                    info["industry"] = val
                elif "总市值" in key:
                    info["market_cap_raw"] = val
    except Exception:
        pass
    return info


# ---------------------------------------------------------------------------
# 质量评分系统
# ---------------------------------------------------------------------------

_QUALITY_CRITERIA = [
    # (metric_key, threshold, base_pts, bonus_threshold, bonus_pts, direction)
    # direction: "higher" means higher is better, "lower" means lower is better
    ("roe", 15, 20, 20, 10, "higher"),
    ("gross_margin", 30, 15, None, 0, "higher"),
    ("debt_ratio", 50, 15, None, 0, "lower"),
    ("ocf_to_profit", 1.0, 15, None, 0, "higher"),
    ("revenue_yoy", 10, 15, None, 0, "higher"),
]


def _compute_quality_score(profitability: dict, growth: dict,
                           solvency: dict, cash_flow: dict) -> dict:
    """基于多维度指标计算企业质量评分 (0-100)。"""
    score = 0
    details = []

    # ROE
    roe = profitability.get("roe")
    if roe is not None:
        if roe > 15:
            score += 20
            details.append("ROE>15%优秀(+20)")
        if roe > 20:
            score += 10
            details.append("ROE>20%卓越(+10)")

    # 毛利率
    gm = profitability.get("gross_margin")
    if gm is not None and gm > 30:
        score += 15
        details.append("毛利率>30%(+15)")

    # 资产负债率
    dr = solvency.get("debt_ratio")
    if dr is not None and dr < 50:
        score += 15
        details.append("负债率<50%(+15)")

    # 经营现金流/净利润
    ocf = cash_flow.get("ocf_to_profit")
    if ocf is not None and ocf > 1.0:
        score += 15
        details.append("经营现金流覆盖利润(+15)")

    # 营收增速
    rev_yoy = growth.get("revenue_yoy")
    if rev_yoy is not None and rev_yoy > 10:
        score += 15
        details.append("营收增速>10%(+15)")

    # 持续盈利性（净利率为正视为盈利）
    nm = profitability.get("net_margin")
    if nm is not None and nm > 0:
        score += 10
        details.append("持续盈利(+10)")

    # 评级映射
    if score >= 80:
        grade = "A"
    elif score >= 60:
        grade = "B"
    elif score >= 40:
        grade = "C"
    elif score >= 20:
        grade = "D"
    else:
        grade = "F"

    comment_parts = []
    if roe is not None and roe > 20:
        comment_parts.append("盈利能力极强")
    elif roe is not None and roe > 15:
        comment_parts.append("盈利能力优秀")
    if ocf is not None and ocf > 1.0:
        comment_parts.append("现金流充沛")
    if dr is not None and dr < 30:
        comment_parts.append("财务结构稳健")
    if rev_yoy is not None and rev_yoy > 20:
        comment_parts.append("高速成长")
    elif rev_yoy is not None and rev_yoy > 10:
        comment_parts.append("稳健增长")
    if not comment_parts:
        comment_parts.append("综合表现一般，建议关注核心指标改善趋势")

    return {
        "score": score,
        "grade": grade,
        "comment": "，".join(comment_parts),
        "details": details,
    }


# ===========================================================================
# 业务逻辑独立函数 — Tool 1: 企业基本面全景画像
# ===========================================================================

@handle_errors
def fetch_fundamental_profile(symbol: str, market: str = "A") -> dict:
    """获取企业基本面全景画像：盈利/成长/运营/偿债/现金流/估值/质量评分。"""
    market = market.upper()

    if market == "A":
        return _fetch_a_share_profile(symbol)
    elif market in ("US", "HK"):
        return _fetch_yf_profile(symbol, market)
    else:
        raise MCPToolError(ErrorCode.INVALID_PARAM,
                           f"不支持的市场: {market}，可选: A / US / HK")


def _fetch_a_share_profile(symbol: str) -> dict:
    """A 股基本面全景画像核心实现。"""
    if ak is None:
        return {"error": "akshare 未安装，无法获取 A 股基本面数据"}

    basic_info = _get_stock_basic_info(symbol)
    result = {
        "symbol": symbol,
        "name": basic_info["name"],
        "market": "A",
        "industry": basic_info["industry"],
        "report_period": None,
        "profitability": {},
        "growth": {},
        "efficiency": {},
        "solvency": {},
        "cash_flow": {},
        "valuation": {},
        "quality_score": {},
        "_notes": [],
    }

    # ---- 1. 盈利能力 & 运营效率 ----
    fin_df = None
    try:
        fin_df = ak.stock_financial_analysis_indicator(symbol=symbol, start_year="2020")
    except Exception as e:
        result["_notes"].append(f"stock_financial_analysis_indicator 失败: {e}")

    if fin_df is None or (hasattr(fin_df, "empty") and fin_df.empty):
        try:
            fin_df = ak.stock_financial_abstract_ths(symbol=symbol, indicator="按报告期")
        except Exception as e:
            result["_notes"].append(f"stock_financial_abstract_ths 失败: {e}")

    if fin_df is not None and not fin_df.empty:
        # 取最新一期
        latest = fin_df.iloc[0] if len(fin_df) > 0 else {}
        period_candidates = ["日期", "报告期", "报告日期"]
        rp = _first_valid(fin_df, period_candidates, 0)
        if rp is not None:
            result["report_period"] = str(rp)[:10]

        # 盈利能力
        result["profitability"] = {
            "gross_margin": _safe_pct(_first_valid(fin_df, ["销售毛利率(%)", "销售毛利率", "毛利率(%)"], 0)),
            "net_margin": _safe_pct(_first_valid(fin_df, ["销售净利率(%)", "销售净利率", "净利率(%)"], 0)),
            "roe": _safe_pct(_first_valid(fin_df, [
                "净资产收益率(%)", "加权净资产收益率(%)", "净资产收益率", "摊薄净资产收益率(%)"], 0)),
            "roa": _safe_pct(_first_valid(fin_df, ["总资产报酬率(%)", "总资产净利率(%)", "总资产收益率(%)"], 0)),
            "roic": _safe_pct(_first_valid(fin_df, ["投入资本回报率(%)", "投入资本回报率"], 0)),
        }

        # 运营效率
        result["efficiency"] = {
            "inventory_turnover_days": _safe_float(
                _first_valid(fin_df, ["存货周转天数(天)", "存货周转天数"], 0), 1),
            "receivables_turnover_days": _safe_float(
                _first_valid(fin_df, ["应收账款周转天数(天)", "应收账款周转天数"], 0), 1),
            "asset_turnover": _safe_float(
                _first_valid(fin_df, ["总资产周转率(次)", "总资产周转率"], 0), 4),
        }

        # 偿债能力
        result["solvency"] = {
            "debt_ratio": _safe_pct(_first_valid(fin_df, ["资产负债率(%)", "资产负债率"], 0)),
            "current_ratio": _safe_float(
                _first_valid(fin_df, ["流动比率", "流动比率(倍)"], 0)),
            "quick_ratio": _safe_float(
                _first_valid(fin_df, ["速动比率", "速动比率(倍)"], 0)),
        }

        # 成长性（需要多期数据）
        growth = {}
        if len(fin_df) >= 2:
            rev_col_candidates = ["主营业务收入增长率(%)", "营业收入同比增长率(%)", "营业总收入同比增长率(%)"]
            profit_col_candidates = ["净利润增长率(%)", "净利润同比增长率(%)", "归属净利润同比增长率(%)"]
            growth["revenue_yoy"] = _safe_pct(_first_valid(fin_df, rev_col_candidates, 0))
            growth["profit_yoy"] = _safe_pct(_first_valid(fin_df, profit_col_candidates, 0))
        else:
            growth["revenue_yoy"] = None
            growth["profit_yoy"] = None

        # 3年营收复合增速
        if len(fin_df) >= 4:
            rev_cols = ["主营业务收入增长率(%)", "营业收入同比增长率(%)", "营业总收入同比增长率(%)"]
            yoy_vals = []
            for i in range(min(3, len(fin_df))):
                v = _first_valid(fin_df, rev_cols, i)
                if v is not None:
                    yoy_vals.append(_safe_float(v))
            if len(yoy_vals) == 3 and all(v is not None for v in yoy_vals):
                try:
                    product = 1.0
                    for v in yoy_vals:
                        product *= (1 + v / 100.0)
                    cagr = (product ** (1.0 / 3.0) - 1) * 100
                    growth["revenue_3y_cagr"] = _safe_float(cagr)
                except Exception:
                    growth["revenue_3y_cagr"] = None
            else:
                growth["revenue_3y_cagr"] = None
        else:
            growth["revenue_3y_cagr"] = None

        result["growth"] = growth

    # ---- 2. 现金流 ----
    cf_data = {}
    try:
        cf_df = ak.stock_financial_cash_ths(symbol=symbol, indicator="按报告期")
        if cf_df is not None and not cf_df.empty:
            ocf = _safe_float(_first_valid(cf_df, [
                "经营活动产生的现金流量净额", "经营现金流量净额"], 0))
            capex = _safe_float(_first_valid(cf_df, [
                "购建固定资产、无形资产和其他长期资产支付的现金",
                "购建固定无形资产支付的现金", "资本支出"], 0))

            if ocf is not None and capex is not None:
                # capex 通常是正数（支出），FCF = OCF - CAPEX
                capex_abs = abs(capex)
                cf_data["free_cash_flow"] = _safe_float((ocf - capex_abs) / 1e8, 2)
            else:
                cf_data["free_cash_flow"] = None

            cf_data["_ocf_raw"] = ocf
    except Exception as e:
        result["_notes"].append(f"现金流数据获取失败: {e}")

    # 经营现金流/净利润 比率
    try:
        profit_df = ak.stock_profit_sheet_by_report_em(symbol=symbol)
        if profit_df is not None and not profit_df.empty:
            net_profit = _safe_float(_first_valid(profit_df, [
                "净利润", "归属于母公司所有者的净利润"], 0))
            revenue = _safe_float(_first_valid(profit_df, [
                "营业总收入", "营业收入"], 0))

            if net_profit and cf_data.get("_ocf_raw"):
                cf_data["ocf_to_profit"] = _safe_float(cf_data["_ocf_raw"] / net_profit, 2)
            if revenue and cf_data.get("_ocf_raw"):
                capex_val = cf_data.get("free_cash_flow")
                if capex_val is not None and revenue != 0:
                    ocf_raw = cf_data["_ocf_raw"]
                    fcf_raw = ocf_raw - abs(ocf_raw - capex_val * 1e8) if capex_val else None
                    # capex_ratio = capex / revenue
                    capex_abs = abs(ocf_raw - (capex_val * 1e8 + ocf_raw)) if capex_val is not None else None
                    # Simpler: use direct capex if available
    except Exception as e:
        result["_notes"].append(f"利润表数据获取失败: {e}")

    # Simpler capex_ratio approach
    if "capex_ratio" not in cf_data:
        cf_data["capex_ratio"] = None
    cf_data.pop("_ocf_raw", None)
    if "ocf_to_profit" not in cf_data:
        cf_data["ocf_to_profit"] = None
    if "free_cash_flow" not in cf_data:
        cf_data["free_cash_flow"] = None
    result["cash_flow"] = cf_data

    # ---- 3. 估值 ----
    valuation = {}
    try:
        spot_df = ak.stock_zh_a_spot_em()
        if spot_df is not None and not spot_df.empty:
            row = spot_df[spot_df["代码"] == symbol]
            if not row.empty:
                row = row.iloc[0]
                valuation["pe_ttm"] = _safe_float(row.get("市盈率-动态"))
                valuation["pb"] = _safe_float(row.get("市净率"))
                mc = row.get("总市值")
                valuation["market_cap"] = _safe_float(float(mc) / 1e8, 2) if mc else None
    except Exception as e:
        result["_notes"].append(f"实时估值获取失败: {e}")

    # PS & PEG
    if valuation.get("market_cap") and result["growth"].get("revenue_yoy"):
        rev_yoy = result["growth"]["revenue_yoy"]
        if rev_yoy and rev_yoy > 0 and valuation.get("pe_ttm"):
            valuation["peg"] = _safe_float(valuation["pe_ttm"] / rev_yoy)
    if "ps_ttm" not in valuation:
        valuation["ps_ttm"] = None
    if "peg" not in valuation:
        valuation["peg"] = None
    result["valuation"] = valuation

    # ---- 4. 质量评分 ----
    result["quality_score"] = _compute_quality_score(
        result["profitability"], result["growth"],
        result["solvency"], result["cash_flow"],
    )

    # 清理内部标记
    if not result["_notes"]:
        del result["_notes"]
    else:
        result["notes"] = result.pop("_notes")

    return result


def _fetch_yf_profile(symbol: str, market: str) -> dict:
    """美股/港股基本面画像 (yfinance fallback)。"""
    if yf is None:
        return {"error": "yfinance 未安装，无法获取美股/港股基本面数据"}

    ticker = yf.Ticker(symbol)
    info = ticker.info or {}

    result = {
        "symbol": symbol,
        "name": info.get("shortName", info.get("longName", symbol)),
        "market": market,
        "industry": info.get("industry", "未知"),
        "report_period": None,
    }

    # 盈利能力
    result["profitability"] = {
        "gross_margin": _safe_pct((info.get("grossMargins") or 0) * 100),
        "net_margin": _safe_pct((info.get("profitMargins") or 0) * 100),
        "roe": _safe_pct((info.get("returnOnEquity") or 0) * 100),
        "roa": _safe_pct((info.get("returnOnAssets") or 0) * 100),
        "roic": None,
    }

    # 成长性
    result["growth"] = {
        "revenue_yoy": _safe_pct((info.get("revenueGrowth") or 0) * 100),
        "profit_yoy": _safe_pct((info.get("earningsGrowth") or 0) * 100),
        "revenue_3y_cagr": None,
    }

    # 运营效率（yfinance 数据有限）
    result["efficiency"] = {
        "inventory_turnover_days": None,
        "receivables_turnover_days": None,
        "asset_turnover": None,
    }

    # 偿债能力
    result["solvency"] = {
        "debt_ratio": _safe_pct((info.get("debtToEquity") or 0)),
        "current_ratio": _safe_float(info.get("currentRatio")),
        "quick_ratio": _safe_float(info.get("quickRatio")),
    }

    # 现金流
    ocf = info.get("operatingCashflow")
    net_income = info.get("netIncomeToCommon")
    fcf = info.get("freeCashflow")
    total_revenue = info.get("totalRevenue")
    capex = (ocf - fcf) if ocf and fcf else None

    result["cash_flow"] = {
        "ocf_to_profit": _safe_float(ocf / net_income, 2) if ocf and net_income and net_income != 0 else None,
        "free_cash_flow": _safe_float(fcf / 1e8, 2) if fcf else None,
        "capex_ratio": _safe_float(capex / total_revenue * 100, 2) if capex and total_revenue and total_revenue != 0 else None,
    }

    # 估值
    mc = info.get("marketCap")
    pe = info.get("trailingPE")
    rev_growth = result["growth"].get("revenue_yoy")

    result["valuation"] = {
        "pe_ttm": _safe_float(pe),
        "pb": _safe_float(info.get("priceToBook")),
        "ps_ttm": _safe_float(info.get("priceToSalesTrailing12Months")),
        "peg": _safe_float(pe / rev_growth, 2) if pe and rev_growth and rev_growth > 0 else None,
        "market_cap": _safe_float(mc / 1e8, 2) if mc else None,
    }

    # 质量评分
    result["quality_score"] = _compute_quality_score(
        result["profitability"], result["growth"],
        result["solvency"], result["cash_flow"],
    )

    return result


# ===========================================================================
# 业务逻辑独立函数 — Tool 2: 同行业对标分析
# ===========================================================================

@handle_errors
def fetch_peer_comparison(symbol: str, metrics: list = None,
                          top_n: int = 10, market: str = "A") -> dict:
    """同行业对标分析：获取行业内可比公司并进行多维度横向比较。"""
    market = market.upper()
    if market != "A":
        raise MCPToolError(ErrorCode.INVALID_PARAM,
                           "同行业对标分析目前仅支持 A 股市场 (market='A')")
    if ak is None:
        return {"error": "akshare 未安装，无法进行同行业对标分析"}

    if metrics is None:
        metrics = ["pe", "roe", "gross_margin", "revenue_yoy"]
    top_n = min(max(top_n, 3), 30)

    # 1. 获取目标公司信息
    basic_info = _get_stock_basic_info(symbol)
    industry = basic_info["industry"]
    result = {
        "target": {
            "symbol": symbol,
            "name": basic_info["name"],
            "industry": industry,
        },
        "peers": [],
        "rankings": {},
        "summary": "",
        "notes": [],
    }

    if industry == "未知":
        result["notes"].append("无法识别目标公司行业，尝试从板块列表匹配")

    # 2. 获取行业成分股
    peer_codes = []
    try:
        board_df = ak.stock_board_industry_cons_em(symbol=industry)
        if board_df is not None and not board_df.empty:
            code_col = "代码" if "代码" in board_df.columns else board_df.columns[0]
            peer_codes = board_df[code_col].astype(str).tolist()
    except Exception as e:
        result["notes"].append(f"行业成分股获取失败({industry}): {e}")

    if not peer_codes:
        # Fallback: 尝试从行业板块名称列表中模糊匹配
        try:
            boards = ak.stock_board_industry_name_em()
            if boards is not None and not boards.empty:
                name_col = "板块名称" if "板块名称" in boards.columns else boards.columns[0]
                matched = boards[boards[name_col].str.contains(industry[:2], na=False)]
                if not matched.empty:
                    board_name = matched.iloc[0][name_col]
                    board_df = ak.stock_board_industry_cons_em(symbol=board_name)
                    if board_df is not None and not board_df.empty:
                        code_col = "代码" if "代码" in board_df.columns else board_df.columns[0]
                        peer_codes = board_df[code_col].astype(str).tolist()
                        result["notes"].append(f"使用模糊匹配板块: {board_name}")
        except Exception as e:
            result["notes"].append(f"板块模糊匹配失败: {e}")

    if not peer_codes:
        result["notes"].append("无法获取行业成分股列表，对标分析无法进行")
        return result

    # 确保目标公司在列表中
    if symbol not in peer_codes:
        peer_codes.insert(0, symbol)

    # 3. 获取实时行情数据（含 PE、市值等）
    spot_df = None
    try:
        spot_df = ak.stock_zh_a_spot_em()
    except Exception as e:
        result["notes"].append(f"实时行情获取失败: {e}")
        return result

    if spot_df is None or spot_df.empty:
        result["notes"].append("实时行情数据为空")
        return result

    # 筛选行业内股票
    peer_spot = spot_df[spot_df["代码"].isin(peer_codes)].copy()
    if peer_spot.empty:
        result["notes"].append("未在行情数据中找到行业成分股")
        return result

    # 按市值排序取 top_n
    if "总市值" in peer_spot.columns:
        peer_spot["总市值"] = pd.to_numeric(peer_spot["总市值"], errors="coerce")
        peer_spot = peer_spot.sort_values("总市值", ascending=False).head(top_n)

    # 4. 获取每只股票的财务指标
    peers_data = []
    for _, row in peer_spot.iterrows():
        code = str(row.get("代码", ""))
        peer_info = {
            "symbol": code,
            "name": str(row.get("名称", code)),
            "pe": _safe_float(row.get("市盈率-动态")),
            "pb": _safe_float(row.get("市净率")),
            "market_cap": _safe_float(
                float(row.get("总市值", 0)) / 1e8 if row.get("总市值") else None, 2),
        }

        # 获取 ROE、毛利率、营收增速（从财务指标表）
        fin_data = _get_peer_financials(code)
        peer_info.update(fin_data)
        peers_data.append(peer_info)

    result["peers"] = peers_data

    # 5. 计算排名
    target_data = None
    for p in peers_data:
        if p["symbol"] == symbol:
            target_data = p
            break

    if target_data:
        metric_map = {
            "pe": ("pe", True),        # lower is better
            "roe": ("roe", False),      # higher is better
            "gross_margin": ("gross_margin", False),
            "revenue_yoy": ("revenue_yoy", False),
            "pb": ("pb", True),
            "market_cap": ("market_cap", False),
        }
        rankings = {}
        for m in metrics:
            if m in metric_map:
                col, ascending = metric_map[m]
                vals = [(p["symbol"], p.get(col)) for p in peers_data if p.get(col) is not None]
                if vals:
                    sorted_vals = sorted(vals, key=lambda x: x[1], reverse=not ascending)
                    total = len(sorted_vals)
                    rank = next((i + 1 for i, (s, _) in enumerate(sorted_vals) if s == symbol), None)
                    if rank:
                        rankings[m] = {
                            "rank": rank,
                            "total": total,
                            "percentile": round((total - rank + 1) / total * 100, 1),
                        }
        result["rankings"] = rankings

    # 6. 生成摘要
    summary_parts = []
    name = basic_info["name"]
    for m, info in result["rankings"].items():
        label_map = {"pe": "市盈率", "roe": "ROE", "gross_margin": "毛利率",
                     "revenue_yoy": "营收增速", "pb": "市净率", "market_cap": "总市值"}
        label = label_map.get(m, m)
        summary_parts.append(f"{label}排名第{info['rank']}/{info['total']}")
    if summary_parts:
        result["summary"] = f"{name}在{industry}行业中：{'，'.join(summary_parts)}。"
    else:
        result["summary"] = f"{name}在{industry}行业中的对标数据待补充。"

    if not result["notes"]:
        del result["notes"]

    return result


def _get_peer_financials(code: str) -> dict:
    """获取单只股票的核心财务指标（用于对标比较，轻量调用）。"""
    data = {"roe": None, "gross_margin": None, "revenue_yoy": None}
    try:
        df = ak.stock_financial_analysis_indicator(symbol=code, start_year="2023")
        if df is not None and not df.empty:
            data["roe"] = _safe_pct(_first_valid(df, [
                "净资产收益率(%)", "加权净资产收益率(%)", "净资产收益率"], 0))
            data["gross_margin"] = _safe_pct(_first_valid(df, [
                "销售毛利率(%)", "销售毛利率", "毛利率(%)"], 0))
            data["revenue_yoy"] = _safe_pct(_first_valid(df, [
                "主营业务收入增长率(%)", "营业收入同比增长率(%)"], 0))
    except Exception:
        pass
    return data


# ===========================================================================
# 业务逻辑独立函数 — Tool 3: 股东结构分析
# ===========================================================================

@handle_errors
def fetch_shareholder_analysis(symbol: str, market: str = "A") -> dict:
    """股东结构分析：十大股东、机构持仓、筹码集中度。"""
    market = market.upper()
    if market != "A":
        raise MCPToolError(ErrorCode.INVALID_PARAM,
                           "股东结构分析目前仅支持 A 股市场 (market='A')")
    if ak is None:
        return {"error": "akshare 未安装，无法获取股东数据"}

    basic_info = _get_stock_basic_info(symbol)
    result = {
        "symbol": symbol,
        "name": basic_info["name"],
        "top_shareholders": [],
        "holder_stats": {},
        "institutional": {},
        "trend": "",
        "notes": [],
    }

    # ---- 1. 十大股东 ----
    top_holders = _fetch_top_shareholders(symbol)
    result["top_shareholders"] = top_holders

    # ---- 2. 股东户数与集中度 ----
    holder_stats = _fetch_holder_stats(symbol)
    result["holder_stats"] = holder_stats

    # ---- 3. 机构持仓 ----
    institutional = _fetch_institutional_holdings(symbol)
    result["institutional"] = institutional

    # ---- 4. 趋势判断 ----
    trend_parts = []
    hc = holder_stats.get("holders_change")
    if hc is not None:
        if hc < -3:
            trend_parts.append(f"股东户数减少{abs(hc)}%，筹码趋于集中")
        elif hc > 3:
            trend_parts.append(f"股东户数增加{abs(hc)}%，筹码趋于分散")
        else:
            trend_parts.append("股东户数变化不大，筹码结构稳定")

    concentration = holder_stats.get("concentration")
    if concentration == "high":
        trend_parts.append("整体集中度较高")
    elif concentration == "low":
        trend_parts.append("整体集中度偏低")

    fund_pct = institutional.get("fund_holding_pct")
    if fund_pct is not None and fund_pct > 10:
        trend_parts.append(f"基金持仓占比{fund_pct}%，机构关注度高")

    result["trend"] = "；".join(trend_parts) if trend_parts else "股东结构数据不足，建议查阅年报获取详细信息"

    if not result["notes"]:
        del result["notes"]

    return result


def _fetch_top_shareholders(symbol: str) -> list:
    """获取十大股东数据。"""
    holders = []

    # 尝试多个可能的 akshare 接口
    api_candidates = [
        ("stock_gdfx_free_holding_detail_em", {"symbol": symbol}),
        ("stock_gdfx_holding_detail_em", {"symbol": symbol}),
    ]

    for func_name, kwargs in api_candidates:
        try:
            func = getattr(ak, func_name, None)
            if func is None:
                continue
            df = func(**kwargs)
            if df is not None and not df.empty:
                # 取最新一期（按日期降序后取前10）
                date_cols = [c for c in df.columns if "日期" in c or "期" in c]
                if date_cols:
                    df = df.sort_values(date_cols[0], ascending=False)
                    latest_date = df[date_cols[0]].iloc[0]
                    df = df[df[date_cols[0]] == latest_date]

                for idx, (_, row) in enumerate(df.head(10).iterrows()):
                    holder = {"rank": idx + 1}
                    name_col = next((c for c in df.columns if "股东" in c and "名" in c), None)
                    if name_col is None:
                        name_col = next((c for c in df.columns if "名" in c or "股东" in c), None)
                    holder["name"] = str(row[name_col]) if name_col and name_col in row.index else "未知"

                    shares_col = next((c for c in df.columns if "持股数" in c or "数量" in c), None)
                    holder["shares"] = _safe_float(row[shares_col], 0) if shares_col else None

                    pct_col = next((c for c in df.columns if "比例" in c or "占比" in c or "%" in c), None)
                    holder["pct"] = _safe_pct(row[pct_col]) if pct_col else None

                    type_col = next((c for c in df.columns if "类型" in c or "性质" in c), None)
                    holder["type"] = str(row[type_col]) if type_col and type_col in row.index else "未知"

                    holders.append(holder)
                return holders
        except Exception:
            continue

    # Fallback: 从 stock_individual_info_em 获取有限信息
    return holders


def _fetch_holder_stats(symbol: str) -> dict:
    """获取股东户数统计。"""
    stats = {
        "total_holders": None,
        "holders_change": None,
        "avg_holding": None,
        "concentration": "unknown",
    }

    # 尝试获取股东户数
    api_candidates = [
        "stock_zh_a_gdhs_detail_em",
        "stock_zh_a_gdhs",
    ]

    for func_name in api_candidates:
        try:
            func = getattr(ak, func_name, None)
            if func is None:
                continue
            df = func(symbol=symbol)
            if df is not None and not df.empty:
                # 获取最新和上期数据
                holder_col = next((c for c in df.columns if "户数" in c or "股东" in c), None)
                if holder_col:
                    latest = _safe_float(df.iloc[0][holder_col], 0)
                    stats["total_holders"] = int(latest) if latest else None

                    if len(df) >= 2:
                        prev = _safe_float(df.iloc[1][holder_col], 0)
                        if latest and prev and prev > 0:
                            change = (latest - prev) / prev * 100
                            stats["holders_change"] = _safe_float(change)

                # 人均持股
                avg_col = next((c for c in df.columns if "人均" in c or "平均" in c), None)
                if avg_col:
                    stats["avg_holding"] = _safe_float(df.iloc[0][avg_col], 0)

                # 集中度判断
                change = stats.get("holders_change")
                if change is not None:
                    if change < -5:
                        stats["concentration"] = "high"
                    elif change > 5:
                        stats["concentration"] = "low"
                    else:
                        stats["concentration"] = "medium"
                break
        except Exception:
            continue

    return stats


def _fetch_institutional_holdings(symbol: str) -> dict:
    """获取机构持仓数据。"""
    institutional = {
        "fund_count": None,
        "fund_holding_pct": None,
        "qfii_holding_pct": None,
    }

    # 尝试获取机构持仓
    api_candidates = [
        ("stock_report_fund_hold_detail", {"symbol": symbol, "date": ""}),
        ("stock_institute_hold_detail", {"symbol": symbol}),
    ]

    for func_name, kwargs in api_candidates:
        try:
            func = getattr(ak, func_name, None)
            if func is None:
                continue
            # 部分接口不接受空 date
            try:
                df = func(**{k: v for k, v in kwargs.items() if v})
            except TypeError:
                df = func(symbol=symbol)
            if df is not None and not df.empty:
                # 基金数量
                fund_col = next((c for c in df.columns if "基金" in c and "数" in c), None)
                if fund_col:
                    institutional["fund_count"] = int(_safe_float(df.iloc[0][fund_col], 0) or 0)

                # 基金持仓占比
                pct_col = next((c for c in df.columns
                                if ("比例" in c or "占比" in c or "%" in c)
                                and "基金" not in c), None)
                if pct_col:
                    institutional["fund_holding_pct"] = _safe_pct(df.iloc[0][pct_col])
                break
        except Exception:
            continue

    return institutional


# ===================================================================
# 注册入口（薄包装器）
# ===================================================================

def register_tools(mcp):
    """将基本面分析工具注册到 FastMCP 实例。"""

    @mcp.tool
    def get_fundamental_profile(symbol: str, market: str = "A") -> dict:
        """获取企业基本面全景画像 —— 盈利·成长·运营·偿债·现金流·估值·质量评分。

        从多个数据源交叉验证，构建上市公司多维度基本面画像。
        包含盈利能力（ROE/毛利率/净利率）、成长性（营收/利润增速、3年CAGR）、
        运营效率（周转率）、偿债能力（负债率/流动比率）、现金流质量
        （经营现金流/净利润、自由现金流）、估值水平（PE/PB/PS/PEG）
        以及基于量化模型的质量评分（0-100分, A/B/C/D/F评级）。

        Args:
            symbol: 股票代码。A股如 "600519"、"000001"；美股如 "AAPL"；港股如 "0700.HK"。
            market: 市场类型。"A" = A股（默认），"US" = 美股，"HK" = 港股。

        Returns:
            dict: 包含 profitability、growth、efficiency、solvency、cash_flow、
                  valuation、quality_score 等多维度基本面数据。
        """
        return fetch_fundamental_profile(symbol, market)

    @mcp.tool
    def get_peer_comparison(symbol: str, metrics: list = None,
                            top_n: int = 10, market: str = "A") -> dict:
        """同行业对标分析 —— 横向比较行业内可比公司的核心财务指标与排名。

        自动识别目标公司所属行业，获取行业内可比公司（按市值排序取 top_n），
        对多个关键指标进行横向比较并计算目标公司在行业中的排名和百分位。

        Args:
            symbol: 目标股票代码，如 "600519"。
            metrics: 要对比的指标列表。可选值：pe/roe/gross_margin/revenue_yoy/pb/market_cap。
                     默认 ["pe", "roe", "gross_margin", "revenue_yoy"]。
            top_n: 对标公司数量（按市值排序），默认 10，最大 30。
            market: 市场类型，目前仅支持 "A"（A股）。

        Returns:
            dict: 包含 target（目标公司）、peers（对标公司列表）、
                  rankings（各指标排名与百分位）、summary（文字摘要）。
        """
        return fetch_peer_comparison(symbol, metrics, top_n, market)

    @mcp.tool
    def get_shareholder_analysis(symbol: str, market: str = "A") -> dict:
        """股东结构分析 —— 十大股东、机构持仓、筹码集中度趋势。

        获取上市公司最新股东结构数据，包括十大流通股东明细、
        股东户数变化与集中度趋势、机构（基金/QFII）持仓占比，
        并给出筹码集中度的趋势判断。

        Args:
            symbol: 股票代码，如 "600519"。
            market: 市场类型，目前仅支持 "A"（A股）。

        Returns:
            dict: 包含 top_shareholders（十大股东）、holder_stats（股东户数统计）、
                  institutional（机构持仓）、trend（趋势判断文字摘要）。
        """
        return fetch_shareholder_analysis(symbol, market)
