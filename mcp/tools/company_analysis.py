#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
company_analysis.py - 上市公司基本面分析工具集
提供财务数据查询、多条件选股、行业板块排名三大核心功能。

注册模式: register_tools(mcp) 供 FastMCP 3.2.0 服务端调用
数据源: akshare (A股) + yfinance (美股)
"""

import os
import sys
import math
from datetime import datetime

try:
    _base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _base not in sys.path:
        sys.path.insert(0, _base)
    from utils.formatters import format_number, format_change
except Exception:
    def format_number(n, d=2):
        return f"{n:,.{d}f}" if isinstance(n, (int, float)) and not math.isnan(n) else str(n)
    def format_change(n):
        return f"+{n:.2f}%" if n > 0 else f"{n:.2f}%"


# ---------------------------------------------------------------------------
# 内部工具函数
# ---------------------------------------------------------------------------

def _safe_float(val, decimals=2):
    """将值转为保留指定小数位的浮点数，无效值返回 'N/A'。"""
    if val is None:
        return "N/A"
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return "N/A"
        return round(f, decimals)
    except (ValueError, TypeError):
        return "N/A"


def _df_to_records(df, limit=60):
    """DataFrame → list[dict]，处理 NaN、Timestamp 等特殊类型。"""
    import pandas as pd

    df = df.head(limit).copy()
    # 将 Timestamp 列转为字符串
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%Y-%m-%d")
    # NaN / NaT → None，再统一替换为 "N/A"
    records = df.where(df.notna(), None).to_dict(orient="records")
    for rec in records:
        for k, v in rec.items():
            if v is None:
                rec[k] = "N/A"
            elif isinstance(v, float):
                if math.isnan(v) or math.isinf(v):
                    rec[k] = "N/A"
                else:
                    rec[k] = round(v, 2)
    return records


# ===========================================================================
# 注册入口
# ===========================================================================

def register_tools(mcp):
    """将本模块的三个分析工具注册到 FastMCP 实例上。"""

    # -------------------------------------------------------------------
    # 工具1: get_company_financials
    # -------------------------------------------------------------------
    @mcp.tool
    def get_company_financials(
        symbol: str,
        market: str = "A",
        report_type: str = "summary",
    ) -> dict:
        """获取上市公司财务数据（三大报表核心指标）。

        根据股票代码和市场类型，返回最近 4-8 个报告期的财务数据。
        支持 A 股（akshare）和美股（yfinance）两大市场。

        Args:
            symbol: 股票代码。A 股如 "000001"、"600519"；美股如 "AAPL"、"MSFT"。
            market: 市场类型。"A" = A 股，"US" = 美股。默认 "A"。
            report_type: 报表类型，可选值：
                - "summary"  : 核心财务指标汇总（营收、净利润、毛利率、ROE 等）
                - "income"   : 利润表
                - "balance"  : 资产负债表
                - "cashflow" : 现金流量表

        Returns:
            dict: 包含 company、symbol、market、report_type、data 字段。
        """
        market = market.upper()
        report_type = report_type.lower()
        if report_type not in ("summary", "income", "balance", "cashflow"):
            return {"error": f"不支持的报表类型: {report_type}，可选: summary/income/balance/cashflow"}

        result = {
            "company": "",
            "symbol": symbol,
            "market": market,
            "report_type": report_type,
            "data": [],
        }

        # ---- A 股 ----
        if market == "A":
            try:
                import akshare as ak
            except ImportError:
                return {"error": "缺少 akshare 库，请先安装: pip install akshare"}

            if report_type == "summary":
                return _a_share_summary(ak, symbol, result)
            elif report_type == "income":
                return _a_share_statement(ak, symbol, result, "income")
            elif report_type == "balance":
                return _a_share_statement(ak, symbol, result, "balance")
            elif report_type == "cashflow":
                return _a_share_statement(ak, symbol, result, "cashflow")

        # ---- 美股 ----
        elif market == "US":
            try:
                import yfinance as yf
            except ImportError:
                return {"error": "缺少 yfinance 库，请先安装: pip install yfinance"}

            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info or {}
                result["company"] = info.get("shortName", info.get("longName", symbol))

                if report_type == "summary":
                    result["data"] = _us_summary(ticker, info)
                elif report_type == "income":
                    df = ticker.financials
                    if df is not None and not df.empty:
                        df = df.T.reset_index().rename(columns={"index": "报告期"})
                        result["data"] = _df_to_records(df, limit=8)
                elif report_type == "balance":
                    df = ticker.balance_sheet
                    if df is not None and not df.empty:
                        df = df.T.reset_index().rename(columns={"index": "报告期"})
                        result["data"] = _df_to_records(df, limit=8)
                elif report_type == "cashflow":
                    df = ticker.cashflow
                    if df is not None and not df.empty:
                        df = df.T.reset_index().rename(columns={"index": "报告期"})
                        result["data"] = _df_to_records(df, limit=8)

                if not result["data"]:
                    result["message"] = f"未获取到 {symbol} 的 {report_type} 数据"
                return result
            except Exception as e:
                return {"error": f"获取美股 {symbol} 财务数据失败: {str(e)}"}
        else:
            return {"error": f"不支持的市场: {market}，可选: A / US"}

    # -------------------------------------------------------------------
    # 工具2: screen_stocks
    # -------------------------------------------------------------------
    @mcp.tool
    def screen_stocks(
        market: str = "A",
        industry: str = "",
        min_pe: float = 0,
        max_pe: float = 100,
        min_roe: float = 0,
        min_market_cap: float = 0,
        max_market_cap: float = 0,
        sort_by: str = "market_cap",
        limit: int = 20,
    ) -> dict:
        """多条件股票筛选器 —— 按市盈率、ROE、市值、行业等维度快速选股。

        从全市场实时行情中，按用户设定的条件进行过滤和排序，
        返回符合条件的股票列表。

        Args:
            market: 市场类型，目前仅支持 "A"（A 股）。默认 "A"。
            industry: 行业筛选关键词，如 "半导体"、"新能源"、"银行"。
                      为空字符串则不限行业。
            min_pe: 最小市盈率（动态），默认 0。设为 0 则不设下限。
            max_pe: 最大市盈率（动态），默认 100。
            min_roe: 最小 ROE（%），默认 0。
            min_market_cap: 最小总市值（亿元），默认 0（不限）。
            max_market_cap: 最大总市值（亿元），默认 0（不限）。
            sort_by: 排序字段，可选值：
                - "market_cap"  : 按总市值排序（默认）
                - "pe"          : 按市盈率排序
                - "roe"         : 按 ROE 排序
                - "change_pct"  : 按涨跌幅排序
            limit: 返回条数，最大 50，默认 20。

        Returns:
            dict: 包含 filters（筛选条件）、count（命中数量）、stocks（股票列表）。
        """
        market = market.upper()
        limit = min(max(limit, 1), 50)
        sort_by = sort_by.lower()

        if market != "A":
            return {"error": "stock_screen 目前仅支持 A 股市场 (market='A')"}

        try:
            import akshare as ak
            import pandas as pd
        except ImportError:
            return {"error": "缺少 akshare / pandas 库，请先安装"}

        filters_applied = {
            "market": market,
            "industry": industry or "不限",
            "pe_range": f"{min_pe} ~ {max_pe}",
            "min_roe": min_roe,
            "market_cap_range": f"{min_market_cap}亿 ~ {'不限' if max_market_cap <= 0 else str(max_market_cap) + '亿'}",
            "sort_by": sort_by,
        }

        try:
            df = ak.stock_zh_a_spot_em()
        except Exception as e:
            return {"error": f"获取 A 股行情数据失败: {str(e)}"}

        # 统一列名映射（东方财富实时行情字段）
        col_map = {
            "代码": "code",
            "名称": "name",
            "最新价": "price",
            "涨跌幅": "change_pct",
            "市盈率-动态": "pe",
            "总市值": "market_cap_raw",
            "成交额": "amount_raw",
        }
        available = {k: v for k, v in col_map.items() if k in df.columns}
        df = df.rename(columns=available)

        # 数值化处理
        for col in ["price", "change_pct", "pe", "market_cap_raw", "amount_raw"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # ---------- 行业筛选 ----------
        if industry:
            try:
                board_df = ak.stock_board_industry_cons_em(symbol=industry)
                if board_df is not None and not board_df.empty:
                    code_col = "代码" if "代码" in board_df.columns else board_df.columns[0]
                    industry_codes = set(board_df[code_col].astype(str).tolist())
                    df = df[df["code"].astype(str).isin(industry_codes)]
            except Exception:
                # 备选: 模糊匹配板块名称列
                if "行业" in df.columns:
                    df = df[df["行业"].str.contains(industry, na=False)]
                elif "所属行业" in df.columns:
                    df = df[df["所属行业"].str.contains(industry, na=False)]

        # ---------- 数值条件过滤 ----------
        if "pe" in df.columns:
            df = df[df["pe"].notna()]
            if min_pe > 0:
                df = df[df["pe"] >= min_pe]
            if max_pe > 0:
                df = df[df["pe"] <= max_pe]

        if min_roe > 0 and "ROE" in df.columns:
            df["ROE"] = pd.to_numeric(df["ROE"], errors="coerce")
            df = df[df["ROE"] >= min_roe]

        # 市值过滤（原始单位为元，转亿元）
        if "market_cap_raw" in df.columns:
            df["market_cap"] = df["market_cap_raw"] / 1e8
            if min_market_cap > 0:
                df = df[df["market_cap"] >= min_market_cap]
            if max_market_cap > 0:
                df = df[df["market_cap"] <= max_market_cap]
        else:
            df["market_cap"] = "N/A"

        # 成交额（亿元）
        if "amount_raw" in df.columns:
            df["amount"] = (df["amount_raw"] / 1e8).round(2)
        else:
            df["amount"] = "N/A"

        # ---------- 排序 ----------
        sort_col_map = {
            "market_cap": "market_cap",
            "pe": "pe",
            "roe": "ROE",
            "change_pct": "change_pct",
        }
        sort_col = sort_col_map.get(sort_by, "market_cap")
        ascending = sort_by == "pe"
        if sort_col in df.columns:
            df = df.sort_values(by=sort_col, ascending=ascending, na_position="last")

        total_count = len(df)
        df = df.head(limit)

        # ---------- 构造输出 ----------
        stocks = []
        for _, row in df.iterrows():
            stocks.append({
                "code": str(row.get("code", "N/A")),
                "name": str(row.get("name", "N/A")),
                "price": _safe_float(row.get("price")),
                "change_pct": _safe_float(row.get("change_pct")),
                "pe": _safe_float(row.get("pe")),
                "market_cap_yi": _safe_float(row.get("market_cap")),
                "amount_yi": _safe_float(row.get("amount")),
            })

        return {
            "filters": filters_applied,
            "count": total_count,
            "returned": len(stocks),
            "stocks": stocks,
        }

    # -------------------------------------------------------------------
    # 工具3: get_industry_ranking
    # -------------------------------------------------------------------
    @mcp.tool
    def get_industry_ranking(
        board_type: str = "industry",
        sort_by: str = "change_pct",
        period: str = "today",
        limit: int = 30,
    ) -> dict:
        """获取行业 / 概念板块景气度排名。

        支持行业板块和概念板块两种维度，可按涨跌幅、换手率、
        成交量、成交额排序，并支持多时间周期查看。

        Args:
            board_type: 板块类型，可选值：
                - "industry" : 行业板块（默认）
                - "concept"  : 概念板块
            sort_by: 排序字段，可选值：
                - "change_pct" : 涨跌幅（默认）
                - "turnover"   : 换手率
                - "volume"     : 成交量
                - "amount"     : 成交额
            period: 时间周期，可选值：
                - "today" : 今日实时（默认）
                - "5d"    : 近 5 个交易日
                - "20d"   : 近 20 个交易日
            limit: 返回条数，默认 30，最大 60。

        Returns:
            dict: 包含 board_type、period、count、rankings 字段。
        """
        board_type = board_type.lower()
        sort_by = sort_by.lower()
        period = period.lower()
        limit = min(max(limit, 1), 60)

        if board_type not in ("industry", "concept"):
            return {"error": f"不支持的板块类型: {board_type}，可选: industry / concept"}

        try:
            import akshare as ak
            import pandas as pd
        except ImportError:
            return {"error": "缺少 akshare / pandas 库，请先安装"}

        result = {
            "board_type": board_type,
            "period": period,
            "sort_by": sort_by,
            "count": 0,
            "rankings": [],
        }

        try:
            df = _fetch_board_data(ak, board_type)
        except Exception as e:
            return {"error": f"获取板块数据失败: {str(e)}"}

        if df is None or df.empty:
            result["message"] = "未获取到板块数据"
            return result

        # 标准化列名
        rename_map = {
            "板块名称": "name",
            "涨跌幅": "change_pct",
            "换手率": "turnover",
            "成交量": "volume",
            "成交额": "amount",
            "领涨股票": "leading_stock",
            "领涨股票-涨跌幅": "leading_change",
            "总市值": "total_market_cap",
        }
        available_rename = {k: v for k, v in rename_map.items() if k in df.columns}
        df = df.rename(columns=available_rename)

        # 数值化
        for col in ["change_pct", "turnover", "volume", "amount"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # ---------- 多周期处理 ----------
        if period != "today":
            df = _apply_period_data(ak, df, board_type, period)

        # ---------- 排序 ----------
        sort_col_map = {
            "change_pct": "change_pct",
            "turnover": "turnover",
            "volume": "volume",
            "amount": "amount",
        }
        col = sort_col_map.get(sort_by, "change_pct")
        if col in df.columns:
            df = df.sort_values(by=col, ascending=False, na_position="last")

        df = df.head(limit)
        result["count"] = len(df)

        # 构造输出
        rankings = []
        for _, row in df.iterrows():
            item = {
                "name": str(row.get("name", "N/A")),
                "change_pct": _safe_float(row.get("change_pct")),
                "turnover": _safe_float(row.get("turnover")),
                "amount_yi": _safe_float(
                    row["amount"] / 1e8 if isinstance(row.get("amount"), (int, float)) and not math.isnan(row.get("amount", float("nan"))) else None
                ),
                "leading_stock": str(row.get("leading_stock", "N/A")),
                "leading_change": _safe_float(row.get("leading_change")),
            }
            rankings.append(item)

        result["rankings"] = rankings
        return result


# ===========================================================================
# A 股财务数据获取 (内部辅助)
# ===========================================================================

def _a_share_summary(ak, symbol: str, result: dict) -> dict:
    """获取 A 股核心财务指标汇总。"""
    data_list = []

    # 策略1: stock_financial_analysis_indicator (财务分析指标)
    try:
        df = ak.stock_financial_analysis_indicator(symbol=symbol, start_year="2020")
        if df is not None and not df.empty:
            result["company"] = symbol
            result["data"] = _df_to_records(df, limit=8)
            return result
    except Exception:
        pass

    # 策略2: stock_financial_abstract_ths (同花顺财务摘要)
    try:
        df = ak.stock_financial_abstract_ths(symbol=symbol, indicator="按报告期")
        if df is not None and not df.empty:
            result["company"] = symbol
            result["data"] = _df_to_records(df, limit=8)
            return result
    except Exception:
        pass

    # 策略3: 实时行情 + 个股指标拼合
    try:
        spot = ak.stock_zh_a_spot_em()
        row = spot[spot["代码"] == symbol]
        if not row.empty:
            row = row.iloc[0]
            result["company"] = str(row.get("名称", symbol))
            data_list.append({
                "报告期": datetime.now().strftime("%Y-%m-%d") + " (实时)",
                "最新价": _safe_float(row.get("最新价")),
                "市盈率_动态": _safe_float(row.get("市盈率-动态")),
                "市净率": _safe_float(row.get("市净率")),
                "总市值_亿": _safe_float(
                    float(row.get("总市值", 0)) / 1e8
                    if row.get("总市值") else None
                ),
                "流通市值_亿": _safe_float(
                    float(row.get("流通市值", 0)) / 1e8
                    if row.get("流通市值") else None
                ),
                "60日涨跌幅": _safe_float(row.get("60日涨跌幅")),
                "年初至今涨跌幅": _safe_float(row.get("年初至今涨跌幅")),
                "换手率": _safe_float(row.get("换手率")),
                "量比": _safe_float(row.get("量比")),
            })
    except Exception:
        pass

    # 策略4: stock_individual_info_em (个股基本信息)
    try:
        info_df = ak.stock_individual_info_em(symbol=symbol)
        if info_df is not None and not info_df.empty:
            info_dict = {}
            for _, r in info_df.iterrows():
                key = str(r.iloc[0]) if len(r) >= 2 else ""
                val = r.iloc[1] if len(r) >= 2 else ""
                info_dict[key] = val
            if not result["company"]:
                result["company"] = info_dict.get("股票简称", symbol)
            if info_dict:
                data_list.append({"个股基本信息": info_dict})
    except Exception:
        pass

    if data_list:
        result["data"] = data_list
    else:
        result["message"] = f"未能获取 {symbol} 的财务数据，请确认代码正确"
    return result


def _a_share_statement(ak, symbol: str, result: dict, stmt_type: str) -> dict:
    """获取 A 股三大报表数据。"""
    fetch_funcs = {
        "income": [
            "stock_profit_sheet_by_report_em",
            "stock_profit_sheet_by_yearly_em",
        ],
        "balance": [
            "stock_balance_sheet_by_report_em",
            "stock_balance_sheet_by_yearly_em",
        ],
        "cashflow": [
            "stock_cashflow_sheet_by_report_em",
            "stock_cashflow_sheet_by_yearly_em",
        ],
    }

    func_names = fetch_funcs.get(stmt_type, [])
    for func_name in func_names:
        try:
            func = getattr(ak, func_name, None)
            if func is None:
                continue
            df = func(symbol=symbol)
            if df is not None and not df.empty:
                result["company"] = symbol
                result["data"] = _df_to_records(df, limit=8)
                return result
        except Exception:
            continue

    result["message"] = f"未能获取 {symbol} 的 {stmt_type} 报表数据"
    return result


# ===========================================================================
# 美股财务汇总 (内部辅助)
# ===========================================================================

def _us_summary(ticker, info: dict) -> list:
    """从 yfinance Ticker 构建美股核心财务指标汇总。"""
    summary = {
        "company": info.get("shortName", "N/A"),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "market_cap": _safe_float(info.get("marketCap")),
        "enterprise_value": _safe_float(info.get("enterpriseValue")),
        "trailing_pe": _safe_float(info.get("trailingPE")),
        "forward_pe": _safe_float(info.get("forwardPE")),
        "peg_ratio": _safe_float(info.get("pegRatio")),
        "price_to_book": _safe_float(info.get("priceToBook")),
        "revenue": _safe_float(info.get("totalRevenue")),
        "revenue_growth": _safe_float(info.get("revenueGrowth")),
        "gross_margin": _safe_float(info.get("grossMargins")),
        "operating_margin": _safe_float(info.get("operatingMargins")),
        "profit_margin": _safe_float(info.get("profitMargins")),
        "roe": _safe_float(info.get("returnOnEquity")),
        "roa": _safe_float(info.get("returnOnAssets")),
        "debt_to_equity": _safe_float(info.get("debtToEquity")),
        "current_ratio": _safe_float(info.get("currentRatio")),
        "free_cashflow": _safe_float(info.get("freeCashflow")),
        "eps_trailing": _safe_float(info.get("trailingEps")),
        "eps_forward": _safe_float(info.get("forwardEps")),
        "dividend_yield": _safe_float(info.get("dividendYield")),
        "beta": _safe_float(info.get("beta")),
        "52w_high": _safe_float(info.get("fiftyTwoWeekHigh")),
        "52w_low": _safe_float(info.get("fiftyTwoWeekLow")),
    }

    # 尝试获取历史季度财务数据
    hist_data = []
    try:
        fin = ticker.financials
        if fin is not None and not fin.empty:
            for col in fin.columns[:4]:
                period_data = {"period": col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)}
                for idx in fin.index:
                    val = fin.loc[idx, col]
                    period_data[str(idx)] = _safe_float(val, 0)
                hist_data.append(period_data)
    except Exception:
        pass

    result = [summary]
    if hist_data:
        result.append({"historical_financials": hist_data})
    return result


# ===========================================================================
# 板块数据获取 (内部辅助)
# ===========================================================================

def _fetch_board_data(ak, board_type: str):
    """获取行业或概念板块行情数据。"""
    if board_type == "industry":
        funcs = [
            "stock_board_industry_name_em",
            "stock_board_industry_summary_ths",
        ]
    else:
        funcs = [
            "stock_board_concept_name_em",
            "stock_board_concept_summary_ths",
        ]

    for func_name in funcs:
        try:
            func = getattr(ak, func_name, None)
            if func is None:
                continue
            df = func()
            if df is not None and not df.empty:
                return df
        except Exception:
            continue
    return None


def _apply_period_data(ak, df, board_type: str, period: str):
    """为板块数据添加多周期涨跌幅（尽力而为）。"""
    import pandas as pd

    period_map = {"5d": 5, "20d": 20}
    days = period_map.get(period)
    if not days:
        return df

    # 尝试用板块历史行情计算区间涨跌幅
    period_changes = {}
    sample_names = df["name"].head(60).tolist() if "name" in df.columns else []

    func_name = (
        "stock_board_industry_hist_em" if board_type == "industry"
        else "stock_board_concept_hist_em"
    )
    hist_func = getattr(ak, func_name, None)
    if hist_func is None:
        return df

    for name in sample_names:
        try:
            hist = hist_func(
                symbol=name,
                period="日k",
                start_date=(datetime.now().replace(day=1)).strftime("%Y%m%d"),
                end_date=datetime.now().strftime("%Y%m%d"),
                adjust="",
            )
            if hist is not None and len(hist) >= 2:
                close_col = "收盘" if "收盘" in hist.columns else hist.columns[2]
                closes = pd.to_numeric(hist[close_col], errors="coerce").dropna()
                if len(closes) >= min(days, 2):
                    start_val = closes.iloc[-min(days, len(closes))]
                    end_val = closes.iloc[-1]
                    if start_val != 0:
                        period_changes[name] = round((end_val - start_val) / start_val * 100, 2)
        except Exception:
            continue

    if period_changes:
        df["change_pct"] = df["name"].map(period_changes).fillna(df.get("change_pct"))

    return df
