#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_index_json.py

Usage:
    python3 tools/update_index_json.py \
        --id "RPT-2026-002" \
        --title "研报标题" \
        --author "投研AI中枢" \
        --category "微观" \
        --tags "新能源,产业链" \
        --filepath "reports/20260402_xxx/index.html"

Description:
    向 index.json 追加一条新的研报元数据记录。
"""

import argparse
import json
import os
import sys
from datetime import datetime


def parse_args():
    parser = argparse.ArgumentParser(description="更新 index.json")
    parser.add_argument("--id", required=True, help="研报唯一ID")
    parser.add_argument("--title", required=True, help="研报标题")
    parser.add_argument("--author", default="投研AI中枢", help="作者")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="日期")
    parser.add_argument("--category", default="微观", choices=["宏观", "微观"], help="分类")
    parser.add_argument("--tags", required=True, help="标签，逗号分隔")
    parser.add_argument("--filepath", required=True, help="HTML文件相对路径")
    parser.add_argument("--index", default="index.json", help="index.json 路径")
    return parser.parse_args()


def main():
    args = parse_args()

    records = []
    if os.path.exists(args.index):
        with open(args.index, "r", encoding="utf-8") as f:
            try:
                records = json.load(f)
            except json.JSONDecodeError:
                print(f"[WARN] {args.index} 解析失败，将重新创建。")
                records = []

    # 去重：如果ID已存在则更新
    existing_ids = {r["id"] for r in records}
    new_record = {
        "id": args.id,
        "title": args.title,
        "author": args.author,
        "date": args.date,
        "tags": [t.strip() for t in args.tags.split(",") if t.strip()],
        "category": args.category,
        "filePath": args.filepath,
    }

    if args.id in existing_ids:
        records = [r if r["id"] != args.id else new_record for r in records]
        print(f"[OK] 已更新现有记录: {args.id}")
    else:
        records.append(new_record)
        print(f"[OK] 已追加新记录: {args.id}")

    with open(args.index, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"[OK] index.json 已更新，当前共 {len(records)} 篇研报。")


if __name__ == "__main__":
    main()
