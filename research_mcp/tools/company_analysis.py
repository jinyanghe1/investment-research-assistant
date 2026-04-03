#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
company_analysis.py - 上市公司基本面分析工具集
提供财务数据查询、多条件选股、行业板块排名三大核心功能。

注册模式: register_tools(mcp) 供 FastMCP 3.2.0 服务端调用
数据源: akshare (A股) + yfinance (美股)

v2.0 更新：
- 集成 data_source.py 的缓存和退避机制
- 修复 screen_stocks 和 get_industry_ranking 的 Rate Limiting 问题
- 增加行业板块数据 N/A 问题的容错处理

v2.1 更新：
- 集成 stock-open-api 东方财富/同花顺接口作为A股公司信息优先数据源
- 公司信息优先级: stock-open-api(东方财富/同花顺) → akshare
"""

import os
import sys
import math
from datetime import datetime
from typing import Optional, Any

_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _base not in sys.path:
    sys.path.insert(0, _base)

from config import config
from utils.errors import handle_errors, MCPToolError, ErrorCode

# 导入新的数据源管理工具
from utils.data_source import (
    call_akshare, try_akshare_apis,
    get_cache, TTL_MARKET, TTL_COMPANY
)

# 导入限速器
from utils.rate_limiter import akshare_limiter, retry_with_backoff

# 导入缓存TTL常量
from utils.cache import TTL_DEFAULT

# 导入备源 (push2 + 新浪)
from utils.fallback_sources import fetch_board_fallback as _fetch_board_fallback

# stock-open-api 数据源
from utils.stock_open_api_source import fetch_company_info as _fetch_stock_open_api_company

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


def _df_to_records(df, limit=None):
    """DataFrame → list[dict]，处理 NaN、Timestamp 等特殊类型。"""
    import pandas as pd

    if limit is None:
        limit = config.max_records
    df = df.head(limit).copy()
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%Y-%m-%d")
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


def _get_cache_key(func_name: str, *args, **kwargs) -> str:
    """生成缓存键。"""
    return f"{func_name}:{str(args)}:{str(sorted(kwargs.items()))}"


# ---------------------------------------------------------------------------
# 选股子函数
# ---------------------------------------------------------------------------

def _apply_filters(ak, df, pd, *, industry, min_pe, max_pe, min_roe,
                   min_market_cap, max_market_cap):
    """对行情 DataFrame 应用行业 + 数值条件过滤，返回过滤后的 df。"""
    # 统一列名映射（东方财富实时行情字段）
    col_map = {
        "代码": "code", "名称": "name", "最新价": "price",
        "涨跌幅": "change_pct", "市盈率-动态": "pe",
        "总市值": "market_cap_raw", "成交额": "amount_raw",
    }
    available = {k: v for k, v in col_map.items() if k in df.columns}
    df = df.rename(columns=available)

    for col in ["price", "change_pct", "pe", "market_cap_raw", "amount_raw"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 行业筛选
    if industry:
        try:
            board_df = call_akshare("stock_board_industry_cons_em", symbol=industry, max_retries=1)
            if board_df is not None and not board_df.empty:
                code_col = "代码" if "代码" in board_df.columns else board_df.columns[0]
                industry_codes = set(board_df[code_col].astype(str).tolist())
                df = df[df["code"].astype(str).isin(industry_codes)]
        except Exception:
            if "行业" in df.columns:
                df = df[df["行业"].str.contains(industry, na=False)]
            elif "所属行业" in df.columns:
                df = df[df["所属行业"].str.contains(industry, na=False)]

    # 数值条件过滤
    if "pe" in df.columns:
        df = df[df["pe"].notna()]
        if min_pe > 0:
            df = df[df["pe"] >= min_pe]
        if max_pe > 0:
            df = df[df["pe"] <= max_pe]

    if min_roe > 0 and "ROE" in df.columns:
        df["ROE"] = pd.to_numeric(df["ROE"], errors="coerce")
        df = df[df["ROE"] >= min_roe]

    if "market_cap_raw" in df.columns:
        df["market_cap"] = df["market_cap_raw"] / 1e8
        if min_market_cap > 0:
            df = df[df["market_cap"] >= min_market_cap]
        if max_market_cap > 0:
            df = df[df["market_cap"] <= max_market_cap]
    else:
        df["market_cap"] = "N/A"

    if "amount_raw" in df.columns:
        df["amount"] = (df["amount_raw"] / 1e8).round(2)
    else:
        df["amount"] = "N/A"

    return df


def _format_screen_results(df, sort_by, limit):
    """对过滤后的 df 排序并格式化为输出列表。"""
    sort_col_map = {
        "market_cap": "market_cap", "pe": "pe",
        "roe": "ROE", "change_pct": "change_pct",
    }
    sort_col = sort_col_map.get(sort_by, "market_cap")
    ascending = sort_by == "pe"
    if sort_col in df.columns:
        df = df.sort_values(by=sort_col, ascending=ascending, na_position="last")

    total_count = len(df)
    df = df.head(limit)

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
    return total_count, stocks


# ===========================================================================
# 独立业务函数（可被 pytest 直接测试）
# ===========================================================================

@handle_errors
def fetch_company_financials(symbol: str, market: str = "A",
                             report_type: str = "summary") -> dict:
    """获取上市公司财务数据核心逻辑。"""
    market = market.upper()
    report_type = report_type.lower()
    if report_type not in ("summary", "income", "balance", "cashflow"):
        raise MCPToolError(ErrorCode.INVALID_PARAM,
                           f"不支持的报表类型: {report_type}，可选: summary/income/balance/cashflow")

    result = {"company": "", "symbol": symbol, "market": market,
              "report_type": report_type, "data": []}

    if market == "A":
        if report_type == "summary":
            # 优先使用 stock-open-api (东方财富/同花顺)
            try:
                soa_info = _fetch_stock_open_api_company(symbol)
                if soa_info and soa_info.get("公司名称"):
                    result["company"] = soa_info.get("A股简称", soa_info.get("公司名称", ""))
                    result["data"] = [{
                        "公司名称": soa_info.get("公司名称", ""),
                        "A股代码": soa_info.get("A股代码", symbol),
                        "A股简称": soa_info.get("A股简称", ""),
                        "所属行业": soa_info.get("所属行业", ""),
                        "总经理": soa_info.get("总经理", ""),
                        "董事长": soa_info.get("董事长", ""),
                        "注册资本(元)": soa_info.get("注册资本(元)", soa_info.get("注册资本", "")),
                        "雇员人数": soa_info.get("雇员人数", soa_info.get("员工人数", "")),
                        "成立日期": soa_info.get("成立日期", ""),
                        "上市日期": soa_info.get("上市日期", ""),
                        "办公地址": soa_info.get("办公地址", ""),
                        "公司网址": soa_info.get("公司网址", ""),
                        "经营范围": soa_info.get("经营范围", soa_info.get("主营业务", "")),
                        "公司介绍": soa_info.get("公司介绍", soa_info.get("公司简介", "")),
                    }]
                    result["data_source"] = soa_info.get("data_source", "stock_open_api")
                    return result
            except Exception:
                pass  # stock-open-api 失败，fallback 到 akshare

            # Fallback: akshare
            import akshare as ak
            return _a_share_summary(ak, symbol, result)
        else:
            # 非summary报表(income/balance/cashflow)仍使用akshare
            import akshare as ak
            return _a_share_statement(ak, symbol, result, report_type)

    elif market == "US":
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        result["company"] = info.get("shortName", info.get("longName", symbol))

        if report_type == "summary":
            result["data"] = _us_summary(ticker, info)
        else:
            df_map = {"income": "financials", "balance": "balance_sheet",
                      "cashflow": "cashflow"}
            df = getattr(ticker, df_map[report_type], None)
            if df is not None and not df.empty:
                df = df.T.reset_index().rename(columns={"index": "报告期"})
                result["data"] = _df_to_records(df, limit=8)

        if not result["data"]:
            result["message"] = f"未获取到 {symbol} 的 {report_type} 数据"
        return result

    else:
        raise MCPToolError(ErrorCode.INVALID_PARAM,
                           f"不支持的市场: {market}，可选: A / US")


def _get_hot_stocks_fallback() -> dict:
    """返回简化版热门股票列表作为最终fallback。"""
    hot_stocks = [
        {"code": "000001", "name": "平安银行", "price": 10.50, "change_pct": 1.25, 
         "pe": 4.82, "market_cap_yi": 2100, "amount_yi": 12.5},
        {"code": "000002", "name": "万科A", "price": 8.20, "change_pct": -0.85, 
         "pe": 8.15, "market_cap_yi": 980, "amount_yi": 8.3},
        {"code": "600519", "name": "贵州茅台", "price": 1580.00, "change_pct": 0.52, 
         "pe": 25.6, "market_cap_yi": 19850, "amount_yi": 25.8},
        {"code": "000858", "name": "五粮液", "price": 145.20, "change_pct": 0.88, 
         "pe": 18.2, "market_cap_yi": 5630, "amount_yi": 15.2},
        {"code": "002594", "name": "比亚迪", "price": 268.50, "change_pct": 2.15, 
         "pe": 32.5, "market_cap_yi": 7820, "amount_yi": 35.6},
        {"code": "300750", "name": "宁德时代", "price": 198.00, "change_pct": 1.85, 
         "pe": 28.3, "market_cap_yi": 8700, "amount_yi": 28.5},
        {"code": "601318", "name": "中国平安", "price": 42.80, "change_pct": 0.65, 
         "pe": 8.52, "market_cap_yi": 7820, "amount_yi": 18.2},
        {"code": "600036", "name": "招商银行", "price": 32.50, "change_pct": 0.42, 
         "pe": 5.85, "market_cap_yi": 8200, "amount_yi": 12.8},
        {"code": "000333", "name": "美的集团", "price": 62.80, "change_pct": 0.95, 
         "pe": 12.8, "market_cap_yi": 4380, "amount_yi": 9.5},
        {"code": "002415", "name": "海康威视", "price": 28.50, "change_pct": -0.35, 
         "pe": 22.5, "market_cap_yi": 2650, "amount_yi": 6.8},
    ]
    return {
        "filters": {"market": "A", "industry": "热门股票", "note": "数据源暂时不可用，返回热门股票示例"},
        "count": len(hot_stocks),
        "returned": len(hot_stocks),
        "stocks": hot_stocks,
        "data_source": "fallback",
        "warning": "实时选股服务暂时不可用，返回示例热门股票数据。请稍后重试。"
    }


@handle_errors
def fetch_screen_stocks(
    market: str = "A",
    industry: str = "",
    min_pe: float = 0,
    max_pe: float = 100,
    min_roe: float = 0,
    min_market_cap: float = 0,
    max_market_cap: float = 0,
    sort_by: str = "market_cap",
    limit: int = 20,
    use_cache_only: bool = False,
) -> dict:
    """多条件股票筛选核心逻辑。
    
    Args:
        market: 市场类型，目前仅支持 "A"
        industry: 行业筛选关键词
        min_pe: 最小市盈率
        max_pe: 最大市盈率
        min_roe: 最小ROE
        min_market_cap: 最小市值（亿元）
        max_market_cap: 最大市值（亿元）
        sort_by: 排序字段
        limit: 返回条数
        use_cache_only: 是否仅使用缓存数据，默认为False
    """
    import pandas as pd
    
    market = market.upper()
    limit = min(max(limit, 1), 50)
    sort_by = sort_by.lower()

    if market != "A":
        raise MCPToolError(ErrorCode.INVALID_PARAM,
                           "stock_screen 目前仅支持 A 股市场 (market='A')")

    cache_key = _get_cache_key("screen_stocks", market, industry, min_pe, max_pe, 
                               min_roe, min_market_cap, max_market_cap, sort_by, limit)
    cache = get_cache()
    
    # 尝试缓存（选股结果缓存1小时）
    if cache:
        cached = cache.get(cache_key, TTL_MARKET)
        if cached:
            if use_cache_only:
                return {**cached, "data_source": "cache", "cache_mode": "forced"}
            return cached
    
    # 如果强制使用缓存但未命中
    if use_cache_only:
        # 尝试获取过期缓存
        if cache:
            expired = cache.get(cache_key, ttl_seconds=0)  # 忽略TTL
            if expired:
                return {**expired, "data_source": "cache", "cache_mode": "expired", 
                        "warning": "返回过期缓存数据（强制缓存模式）"}
        return _get_hot_stocks_fallback()

    filters_applied = {
        "market": market,
        "industry": industry or "不限",
        "pe_range": f"{min_pe} ~ {max_pe}",
        "min_roe": min_roe,
        "market_cap_range": f"{min_market_cap}亿 ~ {'不限' if max_market_cap <= 0 else str(max_market_cap) + '亿'}",
        "sort_by": sort_by,
    }

    try:
        # 使用限速器
        akshare_limiter.wait()
        # 使用 call_akshare 带重试机制
        df = call_akshare("stock_zh_a_spot_em", max_retries=2)
        df = _apply_filters(None, df, pd, industry=industry, min_pe=min_pe,
                            max_pe=max_pe, min_roe=min_roe,
                            min_market_cap=min_market_cap,
                            max_market_cap=max_market_cap)
        total_count, stocks = _format_screen_results(df, sort_by, limit)

        result = {
            "filters": filters_applied, 
            "count": total_count,
            "returned": len(stocks), 
            "stocks": stocks,
            "data_source": "akshare",
        }
        
        # 写入缓存
        if cache:
            cache.set(cache_key, result)
        
        return result
    except Exception as e:
        # akshare失败，尝试返回缓存（即使过期）
        if cache:
            expired = cache.get(cache_key, ttl_seconds=0)  # 忽略TTL
            if expired:
                return {**expired, "warning": f"数据源暂时不可用，使用过期缓存: {str(e)}",
                        "data_source": "cache"}
        
        # 最终fallback：返回简化热门股票
        fallback_result = _get_hot_stocks_fallback()
        fallback_result["filters"] = {**filters_applied, **fallback_result["filters"]}
        return fallback_result


def _fetch_sina_board_data(board_type: str) -> Optional[Any]:
    """从新浪财经API获取板块数据作为备源。
    
    参考API: https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData
    """
    import json
    import re
    import urllib.request
    import urllib.parse
    
    # 新浪财经板块列表API
    try:
        # 行业板块API
        if board_type == "industry":
            url = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=dphy&scale=240&ma=5&datalen=1"
        else:
            # 概念板块API（使用指数作为替代）
            url = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=dpgn&scale=240&ma=5&datalen=1"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read().decode('gbk', errors='ignore')
            # 新浪API返回的是类JSON格式，需要处理
            return data
    except Exception:
        pass
    
    # 尝试新浪行业板块排行API
    try:
        url = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getHQNodes"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode('gbk', errors='ignore')
    except Exception:
        pass
    
    return None


def _get_mock_industry_rankings(board_type: str, limit: int) -> list:
    """返回mock行业/概念板块排名数据。"""
    if board_type == "industry":
        mock_data = [
            {"name": "半导体", "change_pct": 3.52, "turnover": 4.85, "amount_yi": 852.5, "leading_stock": "中芯国际", "leading_change": 5.28},
            {"name": "通信设备", "change_pct": 2.85, "turnover": 3.92, "amount_yi": 425.8, "leading_stock": "中兴通讯", "leading_change": 4.15},
            {"name": "软件开发", "change_pct": 2.36, "turnover": 5.25, "amount_yi": 685.2, "leading_stock": "金山办公", "leading_change": 6.82},
            {"name": "电力", "change_pct": 1.95, "turnover": 2.15, "amount_yi": 285.6, "leading_stock": "长江电力", "leading_change": 2.35},
            {"name": "银行", "change_pct": 1.28, "turnover": 0.85, "amount_yi": 385.2, "leading_stock": "招商银行", "leading_change": 1.85},
            {"name": "白酒", "change_pct": 0.95, "turnover": 1.52, "amount_yi": 425.8, "leading_stock": "贵州茅台", "leading_change": 1.25},
            {"name": "新能源", "change_pct": 0.68, "turnover": 3.25, "amount_yi": 685.5, "leading_stock": "宁德时代", "leading_change": 1.85},
            {"name": "医药商业", "change_pct": 0.42, "turnover": 2.85, "amount_yi": 185.2, "leading_stock": "国药股份", "leading_change": 2.15},
            {"name": "保险", "change_pct": 0.25, "turnover": 0.65, "amount_yi": 125.8, "leading_stock": "中国平安", "leading_change": 0.65},
            {"name": "证券", "change_pct": -0.35, "turnover": 1.85, "amount_yi": 285.6, "leading_stock": "中信证券", "leading_change": -0.85},
            {"name": "房地产", "change_pct": -0.85, "turnover": 2.15, "amount_yi": 225.8, "leading_stock": "万科A", "leading_change": -1.25},
            {"name": "煤炭", "change_pct": -1.25, "turnover": 2.85, "amount_yi": 185.5, "leading_stock": "中国神华", "leading_change": -1.85},
            {"name": "钢铁", "change_pct": -1.52, "turnover": 1.95, "amount_yi": 125.8, "leading_stock": "宝钢股份", "leading_change": -2.15},
            {"name": "石油", "change_pct": -1.85, "turnover": 1.25, "amount_yi": 285.2, "leading_stock": "中国石油", "leading_change": -2.35},
            {"name": "航空", "change_pct": -2.25, "turnover": 3.25, "amount_yi": 185.6, "leading_stock": "中国国航", "leading_change": -3.15},
        ]
    else:
        # 概念板块mock数据
        mock_data = [
            {"name": "ChatGPT概念", "change_pct": 4.52, "turnover": 6.85, "amount_yi": 525.5, "leading_stock": "科大讯飞", "leading_change": 8.25},
            {"name": "AIGC概念", "change_pct": 3.85, "turnover": 5.92, "amount_yi": 425.8, "leading_stock": "万兴科技", "leading_change": 10.02},
            {"name": "算力租赁", "change_pct": 3.25, "turnover": 8.25, "amount_yi": 385.2, "leading_stock": "鸿博股份", "leading_change": 6.85},
            {"name": "芯片概念", "change_pct": 2.95, "turnover": 4.15, "amount_yi": 685.6, "leading_stock": "海光信息", "leading_change": 5.25},
            {"name": "信创", "change_pct": 2.35, "turnover": 5.25, "amount_yi": 425.2, "leading_stock": "中国软件", "leading_change": 4.85},
            {"name": "东数西算", "change_pct": 1.85, "turnover": 4.85, "amount_yi": 325.8, "leading_stock": "浪潮信息", "leading_change": 3.52},
            {"name": "元宇宙", "change_pct": 1.25, "turnover": 4.25, "amount_yi": 285.5, "leading_stock": "歌尔股份", "leading_change": 2.85},
            {"name": "新能源整车", "change_pct": 0.85, "turnover": 3.85, "amount_yi": 485.2, "leading_stock": "比亚迪", "leading_change": 2.15},
            {"name": "储能", "change_pct": 0.52, "turnover": 3.25, "amount_yi": 385.8, "leading_stock": "阳光电源", "leading_change": 1.85},
            {"name": "光伏", "change_pct": -0.25, "turnover": 2.85, "amount_yi": 425.6, "leading_stock": "隆基绿能", "leading_change": -0.85},
            {"name": "医美", "change_pct": -0.85, "turnover": 3.15, "amount_yi": 185.2, "leading_stock": "爱美客", "leading_change": -1.52},
            {"name": "网络游戏", "change_pct": -1.25, "turnover": 3.85, "amount_yi": 225.8, "leading_stock": "三七互娱", "leading_change": -2.15},
            {"name": "CRO", "change_pct": -1.65, "turnover": 2.25, "amount_yi": 185.5, "leading_stock": "药明康德", "leading_change": -2.85},
            {"name": "创新药", "change_pct": -2.15, "turnover": 3.55, "amount_yi": 225.2, "leading_stock": "恒瑞医药", "leading_change": -3.25},
            {"name": "预制菜", "change_pct": -2.85, "turnover": 4.25, "amount_yi": 125.6, "leading_stock": "味知香", "leading_change": -4.15},
        ]
    
    return mock_data[:limit]


@handle_errors
def fetch_industry_ranking(board_type: str = "industry",
                           sort_by: str = "change_pct",
                           period: str = "today",
                           limit: int = 30) -> dict:
    """获取行业/概念板块景气度排名核心逻辑。

    数据获取优先级（由 _fetch_board_data 统一调度）:
      1. akshare API 链 (东方财富 → 同花顺 → 通用)
      2. 东方财富 push2 HTTP 直连
      3. 新浪财经 HTTP API
      4. 过期缓存 / mock 兜底
    """
    import pandas as pd

    board_type = board_type.lower()
    sort_by = sort_by.lower()
    period = period.lower()
    limit = min(max(limit, 1), config.max_records)

    if board_type not in ("industry", "concept"):
        raise MCPToolError(ErrorCode.INVALID_PARAM,
                           f"不支持的板块类型: {board_type}，可选: industry / concept")

    cache_key = _get_cache_key("industry_ranking", board_type, sort_by, period, limit)
    cache = get_cache()

    # 尝试缓存（板块数据缓存3分钟）
    if cache:
        cached = cache.get(cache_key, 180)
        if cached:
            return cached

    result = {
        "board_type": board_type,
        "period": period,
        "sort_by": sort_by,
        "count": 0,
        "rankings": [],
        "data_source": None,
    }

    # _fetch_board_data 内部已包含 akshare + push2 + 新浪 三级 fallback
    df = _fetch_board_data(board_type)

    # 判断备源来源
    data_source = "akshare"
    if df is not None and hasattr(df, "attrs") and df.attrs.get("_fallback_source"):
        data_source = df.attrs["_fallback_source"]

    # 所有数据源都失败 → 过期缓存 → mock
    if df is None or df.empty:
        if cache:
            expired = cache.get(cache_key, ttl_seconds=0)
            if expired:
                return {**expired, "warning": "数据源暂时不可用，使用过期缓存数据",
                        "cache_mode": "extended_ttl"}

        mock_rankings = _get_mock_industry_rankings(board_type, limit)
        result["rankings"] = mock_rankings
        result["count"] = len(mock_rankings)
        result["data_source"] = "mock"
        result["warning"] = "实时数据源暂时不可用，返回示例排名数据。请稍后重试。"
        return result

    # --- 统一列名映射（兼容 akshare / push2 / 新浪） ---
    rename_map = {
        "板块名称": "name", "名称": "name",
        "涨跌幅": "change_pct",
        "换手率": "turnover",
        "成交量": "volume", "成交额": "amount",
        "领涨股票": "leading_stock",
        "领涨股票-涨跌幅": "leading_change",
        "总市值": "total_market_cap",
    }
    available_rename = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=available_rename)

    if "name" not in df.columns:
        for col in df.columns:
            if "名称" in str(col) or "板块" in str(col):
                df = df.rename(columns={col: "name"})
                break

    for col in ["change_pct", "turnover", "volume", "amount"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if period != "today":
        df = _apply_period_data(df, board_type, period)

    sort_col_map = {"change_pct": "change_pct", "turnover": "turnover",
                    "volume": "volume", "amount": "amount"}
    col = sort_col_map.get(sort_by, "change_pct")
    if col in df.columns:
        df = df.sort_values(by=col, ascending=False, na_position="last")

    df = df.head(limit)
    result["count"] = len(df)

    rankings = []
    for _, row in df.iterrows():
        name = row.get("name", "N/A")
        if pd.isna(name) or name is None:
            name = "N/A"
        else:
            name = str(name)

        item = {
            "name": name,
            "change_pct": _safe_float(row.get("change_pct")),
            "turnover": _safe_float(row.get("turnover")),
            "amount_yi": _safe_float(
                row["amount"] / 1e8
                if isinstance(row.get("amount"), (int, float))
                and not math.isnan(row.get("amount", float("nan")))
                else None
            ),
            "leading_stock": str(row.get("leading_stock", "N/A")),
            "leading_change": _safe_float(row.get("leading_change")),
        }
        rankings.append(item)

    result["rankings"] = rankings
    result["data_source"] = data_source

    if cache:
        cache.set(cache_key, result)

    return result


# ===========================================================================
# 注册入口
# ===========================================================================

def register_tools(mcp):
    """将本模块的三个分析工具注册到 FastMCP 实例上。"""

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
        return fetch_company_financials(symbol, market, report_type)

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
        use_cache_only: bool = False,
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
            use_cache_only: 是否仅使用缓存数据，默认 False。设为 True 时
                           强制使用本地缓存，不访问外部数据源。

        Returns:
            dict: 包含 filters（筛选条件）、count（命中数量）、stocks（股票列表）。
        """
        return fetch_screen_stocks(market, industry, min_pe, max_pe, min_roe,
                                   min_market_cap, max_market_cap, sort_by, limit,
                                   use_cache_only)

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
        return fetch_industry_ranking(board_type, sort_by, period, limit)


# ===========================================================================
# A 股财务数据获取 (内部辅助)
# ===========================================================================

def _a_share_summary(ak, symbol: str, result: dict) -> dict:
    """获取 A 股核心财务指标汇总。"""
    data_list = []

    # 策略1: stock_financial_analysis_indicator (财务分析指标)
    try:
        df = call_akshare("stock_financial_analysis_indicator", symbol=symbol, 
                         start_year="2020", max_retries=2)
        if df is not None and not df.empty:
            result["company"] = symbol
            result["data"] = _df_to_records(df, limit=8)
            result["data_source"] = "akshare"
            return result
    except Exception:
        pass

    # 策略2: stock_financial_abstract_ths (同花顺财务摘要)
    try:
        df = call_akshare("stock_financial_abstract_ths", symbol=symbol, 
                         indicator="按报告期", max_retries=2)
        if df is not None and not df.empty:
            result["company"] = symbol
            result["data"] = _df_to_records(df, limit=8)
            result["data_source"] = "akshare"
            return result
    except Exception:
        pass

    # 策略3: 实时行情 + 个股指标拼合
    try:
        spot = call_akshare("stock_zh_a_spot_em", max_retries=2)
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
        info_df = call_akshare("stock_individual_info_em", symbol=symbol, max_retries=2)
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
        result["data_source"] = "akshare"
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
            df = call_akshare(func_name, symbol=symbol, max_retries=2)
            if df is not None and not df.empty:
                result["company"] = symbol
                result["data"] = _df_to_records(df, limit=8)
                result["data_source"] = "akshare"
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
# 板块数据获取 (内部辅助) - 增强版，带多重fallback
# ===========================================================================

def _fetch_board_data(board_type: str):
    """获取行业或概念板块行情数据。带多重fallback机制。

    优先级:
      1. akshare API 链 (东方财富 → 同花顺 → 通用)
      2. 东方财富 push2 HTTP 直连 (绕过 akshare)
      3. 新浪财经 HTTP API
    """
    if board_type == "industry":
        api_list = [
            ("stock_board_industry_name_em", {}),
            ("stock_board_industry_summary_ths", {}),
            ("stock_sector_detail", {"symbol": "行业板块"}),
        ]
    else:
        api_list = [
            ("stock_board_concept_name_em", {}),
            ("stock_board_concept_summary_ths", {}),
            ("stock_sector_detail", {"symbol": "概念板块"}),
        ]

    # 第一轮: akshare API 链
    for func_name, kwargs in api_list:
        try:
            df = call_akshare(func_name, max_retries=2, **kwargs)
            if df is not None and not df.empty:
                return df
        except Exception:
            continue

    # 第二轮: 非 akshare 备源 (push2 直连 + 新浪)
    try:
        df = _fetch_board_fallback(board_type=board_type, limit=200)
        if df is not None and not df.empty:
            return df
    except Exception:
        pass

    return None


def _apply_period_data(df, board_type: str, period: str):
    """为板块数据添加多周期涨跌幅（尽力而为）。"""
    import pandas as pd

    period_map = {"5d": 5, "20d": 20}
    days = period_map.get(period)
    if not days:
        return df

    # 尝试用板块历史行情计算区间涨跌幅
    period_changes = {}
    sample_names = df["name"].head(20).tolist() if "name" in df.columns else []
    
    if not sample_names:
        return df

    func_name = (
        "stock_board_industry_hist_em" if board_type == "industry"
        else "stock_board_concept_hist_em"
    )

    for name in sample_names:
        try:
            hist = call_akshare(func_name, symbol=name, period="日k",
                               start_date=(datetime.now().replace(day=1)).strftime("%Y%m%d"),
                               end_date=datetime.now().strftime("%Y%m%d"),
                               adjust="", max_retries=1)
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
