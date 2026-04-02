#!/usr/bin/env python3
"""
fetch_macro_data.py - 宏观数据获取脚本

功能说明：
    获取国家统计局发布的宏观经济数据，包括GDP、CPI、PPI、PMI等关键指标。
    使用 AKShare 封装国家统计局数据接口，支持指定指标和地区。

Usage:
    python fetch_macro_data.py --indicator GDP --region CN
    python fetch_macro_data.py --indicator CPI --region CN --start 2023-01 --end 2024-12
    python fetch_macro_data.py --indicator PMI --region CN --output data/raw/

Example:
    python fetch_macro_data.py --indicator PPI --region CN --output data/raw/
    python fetch_macro_data.py --indicator CPI --region US --output data/raw/
"""

import argparse
import os
import sys
from datetime import datetime

import pandas as pd

# 缓存支持（优雅降级）
try:
    from mcp.utils.cache import DataCache, TTL_MACRO
    _cache = DataCache()
    _cache_available = True
except ImportError:
    _cache = None
    _cache_available = False
    TTL_MACRO = 86400  # 24小时默认值

# 尝试导入 akshare，如果未安装则给出提示
try:
    import akshare as ak
except ImportError:
    print("错误: 请先安装 akshare 库")
    print("安装命令: pip install akshare")
    sys.exit(1)

# 共享日期处理工具
try:
    from mcp.utils.date_utils import normalize_date, filter_data_by_date
except ImportError:
    # 备用：本地定义（保持向后兼容）
    def normalize_date(date_str):
        if date_str is None:
            return None
        date_str = date_str.strip()
        if len(date_str) == 10 and '-' in date_str:
            return date_str
        if len(date_str) == 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        if len(date_str) == 7 and '-' in date_str:
            return f"{date_str}-01"
        return date_str

    def filter_data_by_date(df, start, end):
        # 备用实现：如果共享模块不可用，使用简化版本
        if df is None or df.empty:
            return df
        return df  # 日期过滤暂不可用，请安装 mcp.utils.date_utils


def fetch_gdp_data(region: str = "CN", start: str = None, end: str = None) -> dict:
    """
    获取GDP数据

    Args:
        region: 地区代码，CN=中国，US=美国
        start: 开始日期，格式YYYY-MM
        end: 结束日期，格式YYYY-MM

    Returns:
        包含GDP数据的字典
    """
    cache_key = f"macro:GDP:{region}:{start}:{end}"
    if _cache_available:
        cached = _cache.get(cache_key, TTL_MACRO)
        if cached is not None:
            print(f"[CACHE] 从缓存读取 GDP({region}) 数据成功")
            return cached

    try:
        if region == "CN":
            # 中国GDP数据
            df = ak.macro_china_gdp()
            print(f"成功获取中国GDP数据，共 {len(df)} 条记录")
            result = {"status": "success", "data": df, "indicator": "GDP", "region": region}
        elif region == "US":
            # 美国GDP数据
            df = ak.macro_usa_gdp()
            print(f"成功获取美国GDP数据，共 {len(df)} 条记录")
            result = {"status": "success", "data": df, "indicator": "GDP", "region": region}
        else:
            return {"status": "error", "message": f"不支持的地区代码: {region}"}
        if _cache_available and result.get("data") is not None:
            _cache.set(cache_key, result)
        return result
    except Exception as e:
        return {"status": "error", "message": f"获取GDP数据失败: {str(e)}"}


def fetch_cpi_data(region: str = "CN", start: str = None, end: str = None) -> dict:
    """
    获取CPI(居民消费价格指数)数据

    Args:
        region: 地区代码，CN=中国，US=美国
        start: 开始日期
        end: 结束日期

    Returns:
        包含CPI数据的字典
    """
    cache_key = f"macro:CPI:{region}:{start}:{end}"
    if _cache_available:
        cached = _cache.get(cache_key, TTL_MACRO)
        if cached is not None:
            print(f"[CACHE] 从缓存读取 CPI({region}) 数据成功")
            return cached

    try:
        if region == "CN":
            # 中国CPI数据
            df = ak.macro_china_cpi()
            print(f"成功获取中国CPI数据，共 {len(df)} 条记录")
            result = {"status": "success", "data": df, "indicator": "CPI", "region": region}
        elif region == "US":
            # 美国CPI数据
            df = ak.macro_usa_cpi()
            print(f"成功获取美国CPI数据，共 {len(df)} 条记录")
            result = {"status": "success", "data": df, "indicator": "CPI", "region": region}
        else:
            return {"status": "error", "message": f"不支持的地区代码: {region}"}
        if _cache_available and result.get("data") is not None:
            _cache.set(cache_key, result)
        return result
    except Exception as e:
        return {"status": "error", "message": f"获取CPI数据失败: {str(e)}"}


def fetch_ppi_data(region: str = "CN", start: str = None, end: str = None) -> dict:
    """
    获取PPI(工业生产者出厂价格指数)数据

    Args:
        region: 地区代码，CN=中国
        start: 开始日期
        end: 结束日期

    Returns:
        包含PPI数据的字典
    """
    cache_key = f"macro:PPI:{region}:{start}:{end}"
    if _cache_available:
        cached = _cache.get(cache_key, TTL_MACRO)
        if cached is not None:
            print(f"[CACHE] 从缓存读取 PPI({region}) 数据成功")
            return cached

    try:
        if region == "CN":
            # 中国PPI数据
            df = ak.macro_china_ppi()
            print(f"成功获取中国PPI数据，共 {len(df)} 条记录")
            result = {"status": "success", "data": df, "indicator": "PPI", "region": region}
        else:
            return {"status": "error", "message": f"不支持的地区代码: {region}"}
        if _cache_available and result.get("data") is not None:
            _cache.set(cache_key, result)
        return result
    except Exception as e:
        return {"status": "error", "message": f"获取PPI数据失败: {str(e)}"}


def fetch_pmi_data(region: str = "CN") -> dict:
    """
    获取PMI(采购经理指数)数据

    Args:
        region: 地区代码，CN=中国

    Returns:
        包含PMI数据的字典
    """
    cache_key = f"macro:PMI:{region}:None:None"
    if _cache_available:
        cached = _cache.get(cache_key, TTL_MACRO)
        if cached is not None:
            print(f"[CACHE] 从缓存读取 PMI({region}) 数据成功")
            return cached

    try:
        if region == "CN":
            # 中国PMI数据
            df = ak.macro_china_pmi()
            print(f"成功获取中国PMI数据，共 {len(df)} 条记录")
            result = {"status": "success", "data": df, "indicator": "PMI", "region": region}
        else:
            return {"status": "error", "message": f"不支持的地区代码: {region}"}
        if _cache_available and result.get("data") is not None:
            _cache.set(cache_key, result)
        return result
    except Exception as e:
        return {"status": "error", "message": f"获取PMI数据失败: {str(e)}"}


def save_data(result: dict, output_dir: str, start: str = None, end: str = None):
    """
    将数据保存到CSV文件

    Args:
        result: 包含数据的字典
        output_dir: 输出目录路径
        start: 开始日期，用于过滤
        end: 结束日期，用于过滤
    """
    if result["status"] != "success":
        print(f"错误: {result.get('message', '未知错误')}")
        return

    os.makedirs(output_dir, exist_ok=True)
    df = result["data"]
    indicator = result["indicator"]
    region = result["region"]

    # 日期过滤
    df = filter_data_by_date(df, start, end)

    if df is None or df.empty:
        print(f"[WARN] 过滤后数据为空，跳过保存")
        return

    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/{indicator}_{region}_{timestamp}.csv"

    try:
        df.to_csv(filename, index=False, encoding="utf-8-sig")
        print(f"数据已保存至: {filename}")
    except Exception as e:
        print(f"保存数据失败: {str(e)}")


def main():
    parser = argparse.ArgumentParser(
        description="宏观数据获取工具 - 获取GDP/CPI/PPI/PMI等宏观经济指标",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python fetch_macro_data.py --indicator GDP --region CN
  python fetch_macro_data.py --indicator CPI --region CN --output data/raw/
  python fetch_macro_data.py --indicator PPI --region CN
  python fetch_macro_data.py --indicator PMI --region CN

支持指标:
  GDP  - 国内生产总值
  CPI  - 居民消费价格指数
  PPI  - 工业生产者出厂价格指数
  PMI  - 采购经理指数

支持地区:
  CN   - 中国
  US   - 美国 (仅支持GDP和CPI)
        """
    )

    parser.add_argument(
        "--indicator", "-i",
        type=str,
        required=True,
        choices=["GDP", "CPI", "PPI", "PMI"],
        help="宏观经济指标类型"
    )

    parser.add_argument(
        "--region", "-r",
        type=str,
        default="CN",
        choices=["CN", "US"],
        help="地区代码 (默认: CN)"
    )

    parser.add_argument(
        "--start",
        type=str,
        default=None,
        help="开始日期，格式YYYY-MM (可选)"
    )

    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="结束日期，格式YYYY-MM (可选)"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        default="data/raw",
        help="输出目录 (默认: data/raw)"
    )

    args = parser.parse_args()

    # 根据指标类型调用对应的获取函数
    indicator_funcs = {
        "GDP": fetch_gdp_data,
        "CPI": fetch_cpi_data,
        "PPI": fetch_ppi_data,
        "PMI": fetch_pmi_data,
    }

    func = indicator_funcs.get(args.indicator)
    if func:
        result = func(region=args.region, start=args.start, end=args.end)
        save_data(result, args.output, start=args.start, end=args.end)
    else:
        print(f"错误: 不支持的指标类型 {args.indicator}")
        sys.exit(1)


if __name__ == "__main__":
    main()
