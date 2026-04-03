#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stock_open_api_source.py — stock-open-api + 腾讯行情 数据源封装

将 stock-open-api (github.com/mouday/stock-open-api) 的东方财富/同花顺公司信息接口，
以及腾讯行情 API (qt.gtimg.cn) 的实时行情接口统一封装，供 market_data.py 和
company_analysis.py 作为 A股优先数据源使用。

数据源优先级:
  实时行情: 腾讯行情(qt.gtimg.cn) → akshare → yfinance
  公司信息: 东方财富(stock-open-api) → 同花顺(stock-open-api) → akshare
"""

import logging
import re
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
    from stock_open_api.api.eastmoney.company import get_company_info as _em_company_info
except ImportError:
    _em_company_info = None

try:
    from stock_open_api.api.eastmoney.sh_stock import get_company_info as _em_sh_company
except ImportError:
    _em_sh_company = None

try:
    from stock_open_api.api.eastmoney.sz_stock import get_company_info as _em_sz_company
except ImportError:
    _em_sz_company = None

try:
    from stock_open_api.api.jqka.company import get_company_info as _jqka_company_info
except ImportError:
    _jqka_company_info = None


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
_REQUEST_TIMEOUT = 10
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_HEADERS = {"User-Agent": _USER_AGENT}

_PROXY_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
               "ALL_PROXY", "all_proxy", "NO_PROXY", "no_proxy")


def _no_proxy_get(url, **kwargs):
    """发送 GET 请求，显式禁用所有代理。"""
    if requests is None:
        raise ImportError("requests 未安装")
    kwargs.setdefault("proxies", {"http": None, "https": None})
    kwargs.setdefault("headers", _HEADERS)
    kwargs.setdefault("timeout", _REQUEST_TIMEOUT)
    return requests.get(url, **kwargs)


# ---------------------------------------------------------------------------
# 腾讯行情 API — A股/ETF 实时行情
# ---------------------------------------------------------------------------
# 腾讯行情字段索引 (以~分隔)
# [0] 市场(1=SH,51=SZ)  [1] 名称  [2] 代码  [3] 最新价  [4] 昨收
# [5] 今开  [6] 成交量(手)  [7] 外盘  [8] 内盘
# [9-28] 买卖5档  [29] 未知  [30] 时间戳
# [31] 涨跌额  [32] 涨跌幅%  [33] 最高  [34] 最低
# [35] 最新价/成交量/成交额  [36] 成交量(手)  [37] 成交额(万)
# [38] 换手率%  [39] 市盈率

def _symbol_to_tencent(symbol: str) -> str:
    """将纯数字股票代码转为腾讯格式 (sh/sz前缀)。
    
    规则: 6开头→sh, 0/3开头→sz, 4/8开头→bj
    """
    symbol = symbol.strip()
    if symbol.lower().startswith(("sh", "sz", "bj")):
        return symbol.lower()
    if symbol.startswith("6"):
        return f"sh{symbol}"
    elif symbol.startswith(("0", "3")):
        return f"sz{symbol}"
    elif symbol.startswith(("4", "8")):
        return f"bj{symbol}"
    return f"sh{symbol}"


def fetch_realtime_tencent(symbol: str) -> Optional[dict]:
    """通过腾讯行情 API 获取A股实时行情。

    Args:
        symbol: 股票代码，如 "600519" 或 "000001" 或 "sh600519"

    Returns:
        dict with keys: 名称, 代码, 现价, 涨跌幅(%), 涨跌额, 成交量(手),
                        成交额(元), 市盈率, 今开, 最高, 最低, 昨收, 换手率(%)
        失败返回 None
    """
    if requests is None:
        logger.warning("requests 未安装，无法使用腾讯行情API")
        return None

    tencent_code = _symbol_to_tencent(symbol)
    url = f"http://qt.gtimg.cn/q={tencent_code}"

    try:
        resp = _no_proxy_get(url)
        resp.raise_for_status()
        text = resp.text.strip()

        # 解析格式: v_sh600519="1~贵州茅台~600519~1460.00~..."
        match = re.search(r'="(.*?)"', text)
        if not match:
            logger.warning("腾讯行情: 未匹配到数据, symbol=%s", symbol)
            return None

        fields = match.group(1).split("~")
        if len(fields) < 40:
            logger.warning("腾讯行情: 字段不足(%d), symbol=%s", len(fields), symbol)
            return None

        name = fields[1]
        code = fields[2]
        price = _safe_float(fields[3])
        prev_close = _safe_float(fields[4])
        open_price = _safe_float(fields[5])
        volume = _safe_float(fields[6])  # 手
        change_value = _safe_float(fields[31])
        change_pct = _safe_float(fields[32])
        high = _safe_float(fields[33])
        low = _safe_float(fields[34])

        # 成交额: fields[37] 是万元单位
        amount_wan = _safe_float(fields[37])
        amount = round(amount_wan * 10000, 2) if amount_wan is not None else None

        # 换手率
        turnover = _safe_float(fields[38])
        # 市盈率
        pe = _safe_float(fields[39])

        if price is None or price <= 0:
            logger.warning("腾讯行情: 无效价格 %s, symbol=%s", fields[3], symbol)
            return None

        result = {
            "名称": name,
            "代码": code,
            "现价": price,
            "涨跌幅(%)": change_pct,
            "涨跌额": change_value,
            "成交量(手)": volume,
            "成交额(元)": amount,
            "市盈率": pe,
            "今开": open_price,
            "最高": high,
            "最低": low,
            "昨收": prev_close,
            "换手率(%)": turnover,
            "market": "A",
            "data_source": "tencent_qq",
        }

        logger.info("腾讯行情成功: %s(%s) = %.2f", name, code, price)
        return result

    except Exception as e:
        logger.warning("腾讯行情失败: symbol=%s, error=%s", symbol, e)
        return None


def fetch_realtime_tencent_batch(symbols: list[str]) -> dict[str, Optional[dict]]:
    """批量获取多个A股实时行情（一次HTTP请求）。

    Args:
        symbols: 股票代码列表

    Returns:
        {symbol: quote_dict or None}
    """
    if requests is None or not symbols:
        return {}

    codes = [_symbol_to_tencent(s) for s in symbols]
    url = f"http://qt.gtimg.cn/q={','.join(codes)}"

    try:
        resp = _no_proxy_get(url)
        resp.raise_for_status()
        text = resp.text.strip()

        results = {}
        for line in text.split("\n"):
            line = line.strip().rstrip(";")
            if not line:
                continue
            # v_sh600519="1~贵州茅台~..."
            key_match = re.match(r'v_(\w+)="(.*)"', line)
            if not key_match:
                continue

            tencent_code = key_match.group(1)
            fields = key_match.group(2).split("~")
            if len(fields) < 40:
                continue

            code = fields[2]
            price = _safe_float(fields[3])
            if price is None or price <= 0:
                continue

            results[code] = {
                "名称": fields[1],
                "代码": code,
                "现价": price,
                "涨跌幅(%)": _safe_float(fields[32]),
                "涨跌额": _safe_float(fields[31]),
                "成交量(手)": _safe_float(fields[6]),
                "成交额(元)": round(_safe_float(fields[37]) * 10000, 2) if _safe_float(fields[37]) else None,
                "市盈率": _safe_float(fields[39]),
                "今开": _safe_float(fields[5]),
                "最高": _safe_float(fields[33]),
                "最低": _safe_float(fields[34]),
                "昨收": _safe_float(fields[4]),
                "换手率(%)": _safe_float(fields[38]),
                "market": "A",
                "data_source": "tencent_qq",
            }

        # 用原始symbol作为key返回
        final = {}
        for orig_sym in symbols:
            pure_code = re.sub(r'^(sh|sz|bj)', '', orig_sym.lower())
            final[orig_sym] = results.get(pure_code)
        return final

    except Exception as e:
        logger.warning("腾讯批量行情失败: %s", e)
        return {}


# ---------------------------------------------------------------------------
# 东方财富 — A股公司基本信息 (via stock-open-api)
# ---------------------------------------------------------------------------

def _code_to_em_prefix(symbol: str) -> str:
    """将纯数字代码转为东方财富格式 (SH/SZ前缀)。"""
    symbol = symbol.strip()
    if symbol.upper().startswith(("SH", "SZ")):
        return symbol.upper()
    if symbol.startswith("6"):
        return f"SH{symbol}"
    elif symbol.startswith(("0", "3")):
        return f"SZ{symbol}"
    return symbol


def fetch_company_info_eastmoney(symbol: str) -> Optional[dict]:
    """通过 stock-open-api 东方财富接口获取公司基本信息。

    返回统一化的公司信息字典，包含公司名称、行业、高管、注册资本等。
    失败返回 None。
    """
    if _em_company_info is None:
        logger.warning("stock-open-api 未安装，无法使用东方财富公司API")
        return None

    em_code = _code_to_em_prefix(symbol)

    try:
        raw = _em_company_info(em_code)
        if not raw or not raw.get("公司名称"):
            logger.warning("东方财富公司信息: 返回空, symbol=%s", symbol)
            return None

        result = {
            "公司名称": raw.get("公司名称", ""),
            "英文名称": raw.get("英文名称", ""),
            "A股代码": raw.get("A股代码", symbol),
            "A股简称": raw.get("A股简称", ""),
            "证券类别": raw.get("证券类别", ""),
            "上市交易所": raw.get("上市交易所", ""),
            "所属行业": raw.get("所属东财行业", raw.get("所属证监会行业", "")),
            "总经理": raw.get("总经理", ""),
            "法人代表": raw.get("法人代表", ""),
            "董事长": raw.get("董事长", ""),
            "董秘": raw.get("董秘", ""),
            "注册资本(元)": raw.get("注册资本(元)"),
            "雇员人数": raw.get("雇员人数"),
            "成立日期": raw.get("成立日期", ""),
            "上市日期": raw.get("上市日期", ""),
            "公司网址": raw.get("公司网址", ""),
            "办公地址": raw.get("办公地址", ""),
            "区域": raw.get("区域", ""),
            "经营范围": raw.get("经营范围", ""),
            "公司介绍": raw.get("公司介绍", ""),
            "发行市盈率(倍)": raw.get("发行市盈率(倍)"),
            "每股发行价(元)": raw.get("每股发行价(元)"),
            "data_source": "stock_open_api_eastmoney",
        }

        logger.info("东方财富公司信息成功: %s (%s)", result["A股简称"], symbol)
        return result

    except Exception as e:
        logger.warning("东方财富公司信息失败: symbol=%s, error=%s", symbol, e)
        return None


# ---------------------------------------------------------------------------
# 同花顺 — A股公司基本信息 (via stock-open-api, 备源)
# ---------------------------------------------------------------------------

def fetch_company_info_jqka(symbol: str) -> Optional[dict]:
    """通过 stock-open-api 同花顺接口获取公司基本信息（东方财富备源）。

    返回统一化的公司信息字典。失败返回 None。
    """
    if _jqka_company_info is None:
        logger.warning("stock-open-api jqka模块不可用")
        return None

    pure_code = re.sub(r'^(SH|SZ|sh|sz)', '', symbol.strip())

    try:
        raw = _jqka_company_info(pure_code)
        if not raw or not raw.get("公司名称"):
            logger.warning("同花顺公司信息: 返回空, symbol=%s", symbol)
            return None

        result = {
            "公司名称": raw.get("公司名称", ""),
            "英文名称": raw.get("英文名称", ""),
            "A股代码": raw.get("股票代码", pure_code),
            "A股简称": raw.get("股票名称", ""),
            "所属行业": raw.get("所属申万行业", ""),
            "总经理": raw.get("总经理", ""),
            "法人代表": raw.get("法人代表", ""),
            "董事长": raw.get("董事长", ""),
            "董秘": raw.get("董秘", ""),
            "注册资本": raw.get("注册资金", ""),
            "员工人数": raw.get("员工人数", ""),
            "成立日期": raw.get("成立日期", ""),
            "上市日期": raw.get("上市日期", ""),
            "公司网址": raw.get("公司网址", ""),
            "办公地址": raw.get("办公地址", ""),
            "所属地域": raw.get("所属地域", ""),
            "控股股东": raw.get("控股股东", ""),
            "实际控制人": raw.get("实际控制人", ""),
            "主营业务": raw.get("主营业务", ""),
            "公司简介": raw.get("公司简介", ""),
            "data_source": "stock_open_api_jqka",
        }

        logger.info("同花顺公司信息成功: %s (%s)", result["A股简称"], symbol)
        return result

    except Exception as e:
        logger.warning("同花顺公司信息失败: symbol=%s, error=%s", symbol, e)
        return None


# ---------------------------------------------------------------------------
# 统一入口
# ---------------------------------------------------------------------------

def fetch_realtime_quote(symbol: str) -> Optional[dict]:
    """A股实时行情统一入口 — 优先腾讯行情。

    Args:
        symbol: A股代码，如 "600519" 或 "000001"

    Returns:
        实时行情 dict (含 data_source 字段) 或 None
    """
    return fetch_realtime_tencent(symbol)


def fetch_company_info(symbol: str) -> Optional[dict]:
    """A股公司信息统一入口 — 东方财富优先, 同花顺备源。

    Args:
        symbol: A股代码

    Returns:
        公司信息 dict (含 data_source 字段) 或 None
    """
    strategies = [
        ("eastmoney", fetch_company_info_eastmoney),
        ("jqka", fetch_company_info_jqka),
    ]

    for source_name, fetch_fn in strategies:
        try:
            result = fetch_fn(symbol)
            if result:
                return result
        except Exception as e:
            logger.warning("公司信息源 %s 失败: %s", source_name, e)
            continue

    logger.error("所有公司信息源均失败: symbol=%s", symbol)
    return None


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------

def _safe_float(val, decimals=2) -> Optional[float]:
    """安全转换为浮点数，无效值返回 None。"""
    if val is None:
        return None
    try:
        f = float(val)
        if f != f:  # NaN check
            return None
        return round(f, decimals)
    except (ValueError, TypeError):
        return None
