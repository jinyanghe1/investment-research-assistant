#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_index_json.py

Usage:
    python3 tools/update_index_json.py \
        --title "半导体周期研判" \
        --author "AI中枢" \
        --category "微观" \
        --tags "半导体,周期,库存" \
        --filepath "reports/20260402_半导体周期研判/index.html"

Description:
    当有新研报生成时，自动读取 index.json 并追加新研报的元数据。
    ID 会自动按年份递增生成（如 RPT-2026-002）。
    如果 index.json 不存在，则自动创建。
"""

import argparse
import json
import os
from datetime import datetime


INDEX_FILE = "index.json"


def load_index():
    if not os.path.exists(INDEX_FILE):
        return []
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception) as e:
        print(f"[WARN] {INDEX_FILE} 解析失败 ({e})，将重新创建。")
        return []


def save_index(data):
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[OK] 已更新 {INDEX_FILE}")


def generate_id(existing):
    """生成递增的ID，格式 RPT-YYYY-NNN。"""
    year = datetime.now().strftime("%Y")
    nums = []
    for item in existing:
        rid = item.get("id", "")
        if rid.startswith(f"RPT-{year}-"):
            try:
                nums.append(int(rid.split("-")[-1]))
            except ValueError:
                pass
    next_num = max(nums, default=0) + 1
    return f"RPT-{year}-{next_num:03d}"


def main():
    parser = argparse.ArgumentParser(description="更新 index.json 研报索引")
    parser.add_argument("--title", required=True, help="研报标题")
    parser.add_argument("--author", required=True, help="作者")
    parser.add_argument("--category", default="微观", help="分类: 微观/宏观/策略")
    parser.add_argument("--tags", default="", help="标签，逗号分隔")
    parser.add_argument("--filepath", required=True, help="研报HTML相对路径")
    args = parser.parse_args()

    index_data = load_index()
    new_entry = {
        "id": generate_id(index_data),
        "title": args.title,
        "author": args.author,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "tags": [t.strip() for t in args.tags.split(",") if t.strip()],
        "category": args.category,
        "filePath": args.filepath,
    }
    index_data.append(new_entry)
    save_index(index_data)
    print(f"[OK] 新增条目 ID={new_entry['id']}")


if __name__ == "__main__":
    main()
