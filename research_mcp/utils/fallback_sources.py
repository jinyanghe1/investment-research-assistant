#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fallback_sources.py — 非 akshare 备用数据源
当 akshare 板块 API 全部失败时，直接请求东方财富/新浪 HTTP API 获取行业/概念板块数据。

数据源优先级:
  1. 东方财富 push2 API  (JSON, 字段最全, 稳定)
  2. 新浪财经 Market_Center API (JS变量格式, 覆盖申万行业)
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 保护性导入
# ---------------------------------------------------------------------------
try:
    import requests
except ImportError:
    requests = None

try:
    import pandas as pd
except ImportError:
    pd = None

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
_REQUEST_TIMEOUT = 10
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_HEADERS = {"User-Agent": _USER_AGENT}

# 需要临时禁用的代理环境变量 (与 data_source.py 保持一致)
_PROXY_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
               "ALL_PROXY", "all_proxy", "NO_PROXY", "no_proxy")

# 东方财富 push2 字段映射
# f3=涨跌幅  f6=成交额  f8=换手率  f12=板块代码  f14=名称
# f20=总市值  f104=上涨家数  f105=下跌家数  f128=领涨股  f136=领涨股涨跌幅  f140=领涨代码
_EM_FIELDS = "f3,f6,f8,f12,f14,f20,f104,f105,f128,f136,f140"

# fs 参数: m:90+t:2 行业板块, m:90+t:3 概念板块
_EM_FS_MAP = {
    "industry": "m:90+t:2",
    "concept": "m:90+t:3",
}


def _no_proxy_get(url, **kwargs):
    """发送 GET 请求，显式禁用所有代理。"""
    kwargs.setdefault("proxies", {"http": None, "https": None})
    return requests.get(url, **kwargs)


# ---------------------------------------------------------------------------
# 东方财富 push2 直接 HTTP 备源
# ---------------------------------------------------------------------------
def fetch_board_eastmoney_push2(
    board_type: str = "industry",
    limit: int = 60,
) -> Optional["pd.DataFrame"]:
    """通过东方财富 push2 HTTP API 直接获取板块行情。

    与 akshare 的 stock_board_industry_name_em 底层数据源相同，
    但绕过 akshare 封装，避免其内部解析异常导致返回空。

    Args:
        board_type: "industry" 或 "concept"
        limit: 返回条数上限

    Returns:
        DataFrame with columns: [名称, 涨跌幅, 换手率, 成交额, 总市值,
                                  领涨股票, 领涨股票-涨跌幅, 上涨家数, 下跌家数]
        失败返回 None
    """
    if requests is None or pd is None:
        return None

    fs = _EM_FS_MAP.get(board_type)
    if not fs:
        return None

    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": 1,
        "pz": min(limit, 200),
        "po": 1,          # 降序
        "np": 1,
        "fltt": 2,
        "invt": 2,
        "fid": "f3",      # 按涨跌幅排序
        "fs": fs,
        "fields": _EM_FIELDS,
        "ut": "b2884a393a59ad64002292a3e90d46a5",
    }

    try:
        resp = _no_proxy_get(url, params=params, headers=_HEADERS,
                             timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        diff = data.get("data", {}).get("diff")
        if not diff:
            logger.warning("push2 API 返回空 diff, board_type=%s", board_type)
            return None

        rows = []
        for item in diff:
            rows.append({
                "名称": item.get("f14", ""),
                "涨跌幅": item.get("f3"),
                "换手率": item.get("f8"),
                "成交额": item.get("f6"),
                "总市值": item.get("f20"),
                "领涨股票": item.get("f128", ""),
                "领涨股票-涨跌幅": item.get("f136"),
                "上涨家数": item.get("f104"),
                "下跌家数": item.get("f105"),
            })

        df = pd.DataFrame(rows)
        logger.info("push2 备源成功: board_type=%s, rows=%d", board_type, len(df))
        return df

    except Exception as e:
        logger.warning("push2 备源失败: %s", e)
        return None


# ---------------------------------------------------------------------------
# 新浪财经备源
# ---------------------------------------------------------------------------
def fetch_board_sina(
    board_type: str = "industry",
    limit: int = 60,
) -> Optional["pd.DataFrame"]:
    """通过新浪财经 API 获取行业板块数据。

    新浪接口返回 JS 变量赋值格式，需解析为字典。
    仅支持 industry (申万行业分类)，concept 支持有限。

    Args:
        board_type: "industry" 或 "concept"
        limit: 返回条数上限

    Returns:
        DataFrame with columns: [名称, 涨跌幅, 换手率, 成交额]
        失败返回 None
    """
    if requests is None or pd is None:
        return None

    # 新浪的概念板块接口不稳定，仅对 industry 有可靠数据
    if board_type == "concept":
        return _fetch_sina_concept(limit)

    return _fetch_sina_industry(limit)


def _fetch_sina_industry(limit: int = 60) -> Optional["pd.DataFrame"]:
    """新浪财经申万行业板块。"""
    import re
    import json as _json

    url = "https://vip.stock.finance.sina.com.cn/q/view/newFLJK.php"
    params = {"param": "industry"}
    headers = {**_HEADERS, "Referer": "https://finance.sina.com.cn"}

    try:
        resp = _no_proxy_get(url, params=params, headers=headers,
                             timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()

        text = resp.text
        # 格式: var S_Finance_bankuai_industry = {"key":"val,...", ...}
        match = re.search(r"=\s*(\{.*\})", text, re.DOTALL)
        if not match:
            return None

        raw = _json.loads(match.group(1))

        rows = []
        for key, val_str in raw.items():
            parts = val_str.split(",")
            if len(parts) < 8:
                continue
            # parts: [code, name, stock_count, avg_price, avg_change,
            #          avg_change_pct, volume, amount, ...]
            try:
                rows.append({
                    "名称": parts[1],
                    "涨跌幅": float(parts[5]) if parts[5] else None,
                    "成交额": float(parts[7]) if parts[7] else None,
                    "换手率": None,  # 新浪未直接提供
                })
            except (ValueError, IndexError):
                continue

        if not rows:
            return None

        df = pd.DataFrame(rows).head(limit)
        logger.info("新浪备源成功: industry, rows=%d", len(df))
        return df

    except Exception as e:
        logger.warning("新浪 industry 备源失败: %s", e)
        return None


def _fetch_sina_concept(limit: int = 60) -> Optional["pd.DataFrame"]:
    """新浪财经概念板块 (可靠性较低)。"""
    import re
    import json as _json

    url = "https://vip.stock.finance.sina.com.cn/q/view/newFLJK.php"
    params = {"param": "concept"}
    headers = {**_HEADERS, "Referer": "https://finance.sina.com.cn"}

    try:
        resp = _no_proxy_get(url, params=params, headers=headers,
                             timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()

        text = resp.text
        match = re.search(r"=\s*(\{.*\})", text, re.DOTALL)
        if not match:
            return None

        raw = _json.loads(match.group(1))

        rows = []
        for key, val_str in raw.items():
            parts = val_str.split(",")
            if len(parts) < 8:
                continue
            try:
                rows.append({
                    "名称": parts[1],
                    "涨跌幅": float(parts[5]) if parts[5] else None,
                    "成交额": float(parts[7]) if parts[7] else None,
                    "换手率": None,
                })
            except (ValueError, IndexError):
                continue

        if not rows:
            return None

        df = pd.DataFrame(rows).head(limit)
        logger.info("新浪备源成功: concept, rows=%d", len(df))
        return df

    except Exception as e:
        logger.warning("新浪 concept 备源失败: %s", e)
        return None


# ---------------------------------------------------------------------------
# 统一入口
# ---------------------------------------------------------------------------
def fetch_board_fallback(
    board_type: str = "industry",
    limit: int = 60,
) -> Optional["pd.DataFrame"]:
    """按优先级尝试所有非 akshare 备源，返回第一个成功的 DataFrame。

    优先级:
      1. 东方财富 push2 HTTP (最稳定、字段最全)
      2. 新浪财经 (申万行业分类)

    Args:
        board_type: "industry" 或 "concept"
        limit: 返回条数上限

    Returns:
        DataFrame (columns 已统一为中文名) 或 None
    """
    strategies = [
        ("eastmoney_push2", fetch_board_eastmoney_push2),
        ("sina", fetch_board_sina),
    ]

    for source_name, fetch_fn in strategies:
        try:
            df = fetch_fn(board_type=board_type, limit=limit)
            if df is not None and not df.empty:
                df.attrs["_fallback_source"] = source_name
                return df
        except Exception as e:
            logger.warning("备源 %s 失败: %s", source_name, e)
            continue

    logger.error("所有备源均失败: board_type=%s", board_type)
    return None
