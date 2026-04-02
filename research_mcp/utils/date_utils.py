#!/usr/bin/env python3
"""
date_utils.py - 日期处理共享工具函数

提供日期标准化和过滤功能，被 data-pipeline 脚本共同使用。

Usage:
    from mcp.utils.date_utils import normalize_date, filter_data_by_date
"""

import pandas as pd
from typing import Optional


def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """
    将日期字符串转换为 YYYY-MM-DD 格式

    Args:
        date_str: 输入日期，格式可能是 YYYYMMDD 或 YYYY-MM 或 YYYY-MM-DD

    Returns:
        YYYY-MM-DD 格式的日期字符串
    """
    if date_str is None:
        return None

    # 移除空格
    date_str = date_str.strip()

    # 如果已经是 YYYY-MM-DD 格式
    if len(date_str) == 10 and '-' in date_str:
        return date_str

    # 如果是 YYYYMMDD 格式
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    # 如果是 YYYY-MM 格式
    if len(date_str) == 7 and '-' in date_str:
        return f"{date_str}-01"

    return date_str


def filter_data_by_date(
    df: pd.DataFrame,
    start_date: Optional[str],
    end_date: Optional[str],
    date_columns: Optional[list] = None
) -> pd.DataFrame:
    """
    根据日期范围过滤数据

    Args:
        df: pandas DataFrame
        start_date: 开始日期 (YYYY-MM 或 YYYYMMDD)
        end_date: 结束日期 (YYYY-MM 或 YYYYMMDD)
        date_columns: 可选，日期列名列表，默认 ['日期', 'date', '时间', 'time', 'datetime', 'trade_date']

    Returns:
        过滤后的 DataFrame
    """
    if df is None or df.empty:
        return df

    # 标准化日期格式
    start_norm = normalize_date(start_date) if start_date else None
    end_norm = normalize_date(end_date) if end_date else None

    if start_norm is None and end_norm is None:
        return df

    # 默认日期列名列表
    if date_columns is None:
        date_columns = ['日期', 'date', '时间', 'time', 'datetime', 'trade_date', '季度', 'period']

    # 查找日期列
    date_col = None
    for col in date_columns:
        if col in df.columns:
            date_col = col
            break

    if date_col is None:
        print(f"[WARN] 未找到日期列，跳过日期过滤")
        return df

    # 标准化数据中的日期列
    df_copy = df.copy()
    try:
        if df_copy[date_col].dtype == object or str(df_copy[date_col].dtype).startswith('str'):
            df_copy[date_col] = df_copy[date_col].apply(
                lambda x: normalize_date(str(x)) if pd.notna(x) else x
            )
        else:
            # 可能是 Period 或 datetime 类型
            df_copy[date_col] = df_copy[date_col].astype(str).apply(
                lambda x: normalize_date(x)
            )
    except Exception:
        return df

    # 执行过滤
    mask = pd.Series([True] * len(df_copy))

    if start_norm:
        mask = mask & (df_copy[date_col] >= start_norm)

    if end_norm:
        mask = mask & (df_copy[date_col] <= end_norm)

    filtered_df = df_copy[mask]

    print(f"[INFO] 日期过滤: {len(df)} -> {len(filtered_df)} 条 (范围: {start_norm or '开始'} ~ {end_norm or '今天'})")

    return filtered_df
