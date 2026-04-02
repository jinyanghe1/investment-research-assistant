#!/usr/bin/env python3
"""
chart_style.py - UBS风格图表统一样式配置

UBS配色方案和Matplotlib样式配置
用于金融研报图表生成

Usage:
    from chart_style import init_ubs_style, UBS_COLORS, add_source_note
    init_ubs_style()
"""

import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap

# UBS配色常量
UBS_BLUE = '#003366'
UBS_BLUE_LIGHT = '#6B8299'
UBS_RED = '#DC2626'
UBS_GREEN = '#16A34A'
UBS_YELLOW = '#F59E0B'
UBS_PURPLE = '#8B5CF6'

# 颜色列表（用于循环）
UBS_COLORS = [UBS_BLUE, UBS_BLUE_LIGHT, UBS_RED, UBS_GREEN, UBS_YELLOW, UBS_PURPLE]

# 涨跌颜色 (UBS标准：绿涨红跌，符合国际市场惯例)
UP_COLOR = UBS_GREEN   # 上涨 = 绿色
DOWN_COLOR = UBS_RED   # 下跌 = 红色

# 背景和文字
UBS_BACKGROUND = '#FFFFFF'
UBS_TEXT = '#1F2937'
UBS_TEXT_SECONDARY = '#6B7280'


def init_ubs_style():
    """
    初始化UBS风格配置
    调用此函数后，所有matplotlib图表将使用UBS风格
    """
    # 字体设置
    plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Microsoft YaHei', 'SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 尺寸设置
    plt.rcParams['figure.figsize'] = (12, 6)
    plt.rcParams['figure.dpi'] = 150
    plt.rcParams['figure.facecolor'] = UBS_BACKGROUND
    plt.rcParams['axes.facecolor'] = UBS_BACKGROUND
    plt.rcParams['savefig.facecolor'] = UBS_BACKGROUND
    
    # 颜色循环
    plt.rcParams['axes.prop_cycle'] = plt.cycler('color', UBS_COLORS)
    
    # 标题设置
    plt.rcParams['axes.titlesize'] = 14
    plt.rcParams['axes.titleweight'] = 'bold'
    plt.rcParams['axes.titlepad'] = 12
    
    # 标签设置
    plt.rcParams['xtick.labelsize'] = 10
    plt.rcParams['ytick.labelsize'] = 10
    
    # 网格设置
    plt.rcParams['grid.linestyle'] = '--'
    plt.rcParams['grid.linewidth'] = 0.5
    plt.rcParams['grid.alpha'] = 0.6
    
    # 图例设置
    plt.rcParams['legend.frameon'] = True
    plt.rcParams['legend.framealpha'] = 0.9
    plt.rcParams['legend.fancybox'] = True
    plt.rcParams['legend.fontsize'] = 10
    
    # 边距设置
    plt.rcParams['savefig.bbox'] = 'tight'
    plt.rcParams['savefig.pad_inches'] = 0.05
    
    # 边框设置
    mpl.rcParams['axes.spines.top'] = False
    mpl.rcParams['axes.spines.right'] = False


def get_up_down_colors():
    """
    获取涨跌颜色

    Returns:
        tuple: (上涨颜色, 下跌颜色)
    """
    return UP_COLOR, DOWN_COLOR


def create_up_down_cmap():
    """
    创建涨跌颜色映射（绿→白→红）

    Returns:
        LinearSegmentedColormap
    """
    colors = [DOWN_COLOR, 'white', UP_COLOR]
    return LinearSegmentedColormap.from_list('up_down', colors)


def format_percentage(ax, decimals=1):
    """
    格式化Y轴为百分比显示

    Args:
        ax: matplotlib axes对象
        decimals: 小数位数
    """
    ax.yaxis.set_major_formatter(mpl.ticker.PercentFormatter(decimals=decimals))


def add_source_note(ax, source, fontsize=9):
    """
    在图表底部添加数据来源注释

    Args:
        ax: matplotlib axes对象
        source: 数据来源文字
        fontsize: 字体大小
    """
    ax.text(1, -0.15, f'数据来源: {source}', 
            transform=ax.transAxes, fontsize=fontsize,
            color=UBS_TEXT_SECONDARY, style='italic', ha='right')


def style_axis(ax, title=None, xlabel=None, ylabel=None, grid=True):
    """
    通用轴样式设置

    Args:
        ax: matplotlib axes对象
        title: 图表标题
        xlabel: X轴标签
        ylabel: Y轴标签
        grid: 是否显示网格
    """
    if title:
        ax.set_title(title, fontsize=14, fontweight='bold', pad=12)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=11)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=11)
    if grid:
        ax.grid(True, linestyle='--', alpha=0.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)


def get_color_scheme(n_items):
    """
    获取指定数量的颜色方案

    Args:
        n_items: 需要的颜色数量

    Returns:
        list: 颜色列表
    """
    return UBS_COLORS[:n_items] if n_items <= len(UBS_COLORS) else UBS_COLORS * (n_items // len(UBS_COLORS) + 1)


if __name__ == '__main__':
    # 测试样式
    import numpy as np
    
    init_ubs_style()
    
    # 测试图表
    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(10)
    y = np.random.randn(10).cumsum()
    
    ax.plot(x, y, color=UBS_BLUE, linewidth=2, label='示例数据')
    style_axis(ax, title='UBS风格测试图表', xlabel='日期', ylabel='数值')
    add_source_note(ax, '测试数据')
    ax.legend()
    
    plt.tight_layout()
    plt.savefig('test_ubs_style.png', dpi=150)
    print("[OK] 测试图表已保存: test_ubs_style.png")
