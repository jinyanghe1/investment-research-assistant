#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
init_report.py

Usage:
    python3 tools/init_report.py --title "研报标题" --author "作者名"

Description:
    初始化一个新的研报项目：创建按日期命名的文件夹，并基于模板生成初始HTML文件。
"""

import argparse
import os
import shutil
import sys
from datetime import datetime


def parse_args():
    parser = argparse.ArgumentParser(description="初始化研报项目")
    parser.add_argument("--title", required=True, help="研报标题")
    parser.add_argument("--author", default="投研AI中枢", help="作者名称")
    parser.add_argument("--template", default="templates/report-template.html", help="HTML模板路径")
    parser.add_argument("--output-dir", default="reports", help="输出根目录")
    return parser.parse_args()


def sanitize_filename(text: str) -> str:
    """将标题转换为适合文件名的字符串。"""
    import re
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "_", text.strip())
    return text


def main():
    args = parse_args()
    today = datetime.now().strftime("%Y%m%d")
    safe_title = sanitize_filename(args.title)
    folder_name = f"{today}_{safe_title}"
    folder_path = os.path.join(args.output_dir, folder_name)
    html_path = os.path.join(folder_path, "index.html")

    os.makedirs(folder_path, exist_ok=True)

    if not os.path.exists(args.template):
        print(f"[ERROR] 模板文件不存在: {args.template}")
        sys.exit(1)

    shutil.copy(args.template, html_path)

    # 简单的占位符替换
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    content = content.replace("{{REPORT_TITLE}}", args.title)
    content = content.replace("{{AUTHOR}}", args.author)
    content = content.replace("{{DATE}}", datetime.now().strftime("%Y-%m-%d"))
    content = content.replace("{{YEAR}}", datetime.now().strftime("%Y"))
    content = content.replace("{{CATEGORY}}", "微观")
    content = content.replace("{{RATING}}", "待评定")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[OK] 研报项目已初始化: {folder_path}")
    print(f"[OK] HTML文件: {html_path}")
    print(f"[提示] 接下来请手动编辑HTML内容，然后运行 tools/update_index_json.py 注册到知识库。")


if __name__ == "__main__":
    main()
