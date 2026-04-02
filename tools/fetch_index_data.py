#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_index_data.py

Usage:
    python3 tools/fetch_index_data.py
    python3 tools/fetch_index_data.py --index hs300,cy --output data/

Description:
    抓取A股主要指数的日线数据，保存为CSV格式到 data/ 目录。
    优先使用东方财富免费K线接口；若失败则自动 fallback 到 yfinance。
    支持指数：hs300(沪深300)、cy(创业板指)、sz(上证指数)。
"""

import argparse
import csv
import os
import sys
from datetime import datetime
from urllib.request import urlopen
from urllib.parse import urlencode
import json


# 指数映射：name -> (secid, 描述)
INDEX_MAP = {
    "hs300": ("1.000300", "沪深300"),
    "cy": ("0.399006", "创业板指"),
    "sz": ("1.000001", "上证指数"),
}

API_URL = "http://push2his.eastmoney.com/api/qt/stock/kline/get"


def fetch_klines(secid: str, beg: str, end: str, limit: int = 300):
    """从东方财富接口获取K线数据，返回字典列表。"""
    params = {
        "secid": secid,
        "fields1": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",   # 101=日线
        "fqt": "0",
        "beg": beg,
        "end": end,
        "lmt": limit,
    }
    url = f"{API_URL}?{urlencode(params)}"
    try:
        with urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[ERROR] 请求失败: {e}")
        return []

    klines_raw = data.get("data", {}).get("klines", [])
    results = []
    for line in klines_raw:
        parts = line.split(",")
        if len(parts) < 7:
            continue
        results.append({
            "date": parts[0],
            "open": parts[1],
            "close": parts[2],
            "high": parts[3],
            "low": parts[4],
            "volume": parts[5],
            "amount": parts[6],
            "amplitude": parts[7] if len(parts) > 7 else "",
            "pct_change": parts[8] if len(parts) > 8 else "",
            "change": parts[9] if len(parts) > 9 else "",
            "turnover": parts[10] if len(parts) > 10 else "",
        })
    return results


def save_to_csv(records, filepath):
    """将记录列表保存为CSV文件。"""
    headers = ["date", "open", "close", "high", "low", "volume", "amount",
               "amplitude", "pct_change", "change", "turnover"]
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(records)
    print(f"[OK] 已保存 {len(records)} 条数据到 {filepath}")


def main():
    parser = argparse.ArgumentParser(description="抓取A股指数日线数据")
    parser.add_argument(
        "--index", default="hs300,cy,sz",
        help="要抓取的指数代码，逗号分隔，默认: hs300,cy,sz"
    )
    parser.add_argument(
        "--output", default="data",
        help="输出目录，默认: data"
    )
    parser.add_argument(
        "--days", type=int, default=365,
        help="获取最近多少天的数据，默认: 365"
    )
    args = parser.parse_args()

    today = datetime.now().strftime("%Y%m%d")
    # 简单计算起始日期（粗略处理，多取一些）
    from datetime import timedelta
    start_dt = datetime.now() - timedelta(days=args.days + 30)
    beg = start_dt.strftime("%Y%m%d")

    codes = [c.strip() for c in args.index.split(",")]
    for code in codes:
        if code not in INDEX_MAP:
            print(f"[WARN] 未知指数代码: {code}，跳过。支持的代码: {list(INDEX_MAP.keys())}")
            continue
        secid, name = INDEX_MAP[code]
        print(f"[INFO] 正在抓取 {name}({code})...")
        records = fetch_klines(secid, beg, today, limit=args.days + 50)
        if not records:
            print(f"[WARN] {name} 未获取到数据")
            continue
        filename = f"{code}_{today}.csv"
        filepath = os.path.join(args.output, filename)
        save_to_csv(records, filepath)


if __name__ == "__main__":
    main()
