#!/usr/bin/env python3
"""
A股个股/指数日线数据获取脚本

从东方财富获取A股个股和指数的K线数据
支持日线、周线、月线以及分钟级数据

Usage:
    python fetch_stock_daily.py --ts_code 000001.SZ --start_date 20240101 --end_date 20260402
    python fetch_stock_daily.py --ts_code 000300.SH --period weekly --output data/raw/

Example:
    python fetch_stock_daily.py --ts_code 000001.SZ --start_date 20240101 --end_date 20260402
    python fetch_stock_daily.py --ts_code 000300.SH --period daily --output data/raw/
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# 缓存支持（优雅降级）
try:
    from mcp.utils.cache import DataCache, TTL_MARKET
    _cache = DataCache()
    _cache_available = True
except ImportError:
    _cache = None
    _cache_available = False
    TTL_MARKET = 300  # 5分钟默认值

INDEX_CODES = {
    '沪深300': '000300.SH',
    '上证指数': '000001.SH',
    '深证成指': '399001.SZ',
    '创业板指': '399006.SZ',
    '科创50': '000688.SH',
    '上证50': '000016.SH',
}


def setup_args():
    parser = argparse.ArgumentParser(description='获取A股个股/指数日线数据')
    parser.add_argument('--ts_code', '-t', required=True,
                        help='股票/指数代码，如 000001.SZ 或 000300.SH')
    parser.add_argument('--start_date', '-s', default='20200101',
                        help='开始日期，格式YYYYMMDD')
    parser.add_argument('--end_date', '-e', default=None,
                        help='结束日期，格式YYYYMMDD，默认今天')
    parser.add_argument('--period', '-p', default='daily',
                        choices=['daily', 'weekly', 'monthly'],
                        help='K线周期')
    parser.add_argument('--output', '-o', default='data/raw',
                        help='输出目录')
    return parser.parse_args()


def resolve_ts_code(ts_code: str) -> str:
    if ts_code in INDEX_CODES:
        return INDEX_CODES[ts_code]
    return ts_code


def get_stock_data(ts_code: str, start_date: str, end_date: str, period: str = 'daily') -> dict:
    # 构建缓存key
    cache_key = f"stock:{ts_code}:{start_date}:{end_date}"

    # 尝试从缓存读取
    if _cache_available:
        cached = _cache.get(cache_key, TTL_MARKET)
        if cached is not None:
            print(f"[CACHE] 从缓存读取 {ts_code} 数据成功")
            return cached

    try:
        import akshare as ak
    except ImportError:
        print("[ERROR] 请先安装 akshare: pip install akshare")
        sys.exit(1)

    result = {'data': None, 'name': ts_code, 'ts_code': ts_code}

    try:
        is_index = '.SH' in ts_code and ts_code.startswith('000')
        is_index = is_index or ('.SZ' in ts_code and ts_code.startswith('399'))

        if is_index or ts_code in INDEX_CODES.values():
            result['data'] = ak.stock_zh_index_daily(ts_code=ts_code)
            result['name'] = f"指数{ts_code}"
            # 指数数据需要手动过滤日期
            if 'date' in result['data'].columns:
                result['data'] = result['data'][
                    (result['data']['date'] >= start_date) &
                    (result['data']['date'] <= end_date)
                ]
            elif '日期' in result['data'].columns:
                result['data'] = result['data'][
                    (result['data']['日期'] >= start_date) &
                    (result['data']['日期'] <= end_date)
                ]
        else:
            result['data'] = ak.stock_zh_a_hist(
                symbol=ts_code.split('.')[0],
                period=period,
                start_date=start_date,
                end_date=end_date
            )
            if '日期' in result['data'].columns:
                result['data'] = result['data'][
                    (result['data']['日期'] >= start_date) &
                    (result['data']['日期'] <= end_date)
                ]

        print(f"[OK] 获取 {ts_code} 数据成功，共 {len(result['data'])} 条")

        # 写入缓存
        if _cache_available and result['data'] is not None:
            _cache.set(cache_key, result)

        return result

    except Exception as e:
        print(f"[ERROR] 获取 {ts_code} 数据失败: {e}")
        return result


def save_to_csv(data, ts_code: str, period: str, output_dir: str) -> str:
    if data is None or data.empty:
        print(f"[WARN] 数据为空，跳过保存")
        return None

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d')
    period_map = {'daily': '日线', 'weekly': '周线', 'monthly': '月线'}
    period_cn = period_map.get(period, period)
    filename = f"{timestamp}_{ts_code}_{period_cn}.csv"
    filepath = os.path.join(output_dir, filename)

    try:
        data.to_csv(filepath, index=False, encoding='utf-8-sig')
        print(f"[OK] 数据已保存: {filepath}")
        return filepath
    except Exception as e:
        print(f"[ERROR] 保存数据失败: {e}")
        return None


def main():
    args = setup_args()
    ts_code = resolve_ts_code(args.ts_code)

    if args.end_date is None:
        args.end_date = datetime.now().strftime('%Y%m%d')

    print(f"[INFO] 开始获取数据: {ts_code}")
    print(f"[INFO] 周期: {args.period}, 时间范围: {args.start_date} ~ {args.end_date}")

    result = get_stock_data(ts_code, args.start_date, args.end_date, args.period)

    if result['data'] is not None:
        filepath = save_to_csv(result['data'], ts_code, args.period, args.output)
        if filepath:
            print(f"[INFO] 完成!")
            return 0

    print("[WARN] 未获取到数据")
    return 1


if __name__ == '__main__':
    sys.exit(main())
