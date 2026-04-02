#!/usr/bin/env python3
"""
chart_generator.py - 图表生成器基类

提供时间序列图、柱状图、热力图等图表生成功能
基于UBS风格配置

Usage:
    from chart_generator import TimeSeriesChart, BarChart, HeatmapChart
    ts = TimeSeriesChart(data)
    ts.plot('date', ['col1', 'col2'], '标题', save_path='output.png')
"""

import os
import sys
from pathlib import Path

# 尝试导入matplotlib，如果失败则提供有用提示
try:
    import matplotlib
    matplotlib.use('Agg')  # 非交互式后端
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import numpy as np
    import pandas as pd
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# 导入UBS样式
if HAS_MATPLOTLIB:
    from chart_style import (
        init_ubs_style, UBS_COLORS, UBS_BLUE, UBS_BLUE_LIGHT,
        style_axis, add_source_note, format_percentage
    )


class ChartGenerator:
    """图表生成器基类"""
    
    def __init__(self, data=None, style='ubs'):
        """
        初始化图表生成器
        
        Args:
            data: pandas DataFrame，包含图表数据
            style: 样式名称，目前支持 'ubs'
        """
        if not HAS_MATPLOTLIB:
            print("[ERROR] matplotlib未安装，请运行: pip install matplotlib")
            sys.exit(1)
        
        self.data = data
        if style == 'ubs':
            init_ubs_style()
    
    def save(self, filepath, dpi=150):
        """
        保存图表到文件
        
        Args:
            filepath: 保存路径
            dpi: 分辨率
        """
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(filepath, dpi=dpi, bbox_inches='tight', facecolor='white')
        print(f"[OK] 图表已保存: {filepath}")
    
    def close(self):
        """关闭所有图表，释放内存"""
        plt.close('all')


class TimeSeriesChart(ChartGenerator):
    """时间序列图生成器"""
    
    def plot(self, x_col, y_cols, title, xlabel='日期', ylabel='数值',
             add_markers=False, save_path=None, source=None):
        """
        绘制时间序列图
        
        Args:
            x_col: X轴列名（日期列）
            y_cols: Y轴列名列表
            title: 图表标题
            xlabel: X轴标签
            ylabel: Y轴标签
            add_markers: 是否添加数据点标记
            save_path: 保存路径
            source: 数据来源
            
        Returns:
            fig, ax: matplotlib图形对象
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for i, col in enumerate(y_cols):
            color = UBS_COLORS[i % len(UBS_COLORS)]
            marker = 'o' if add_markers or len(self.data) < 40 else None
            ax.plot(self.data[x_col], self.data[col], 
                   color=color, linewidth=1.5, label=col, marker=marker,
                   markersize=4)
        
        style_axis(ax, title=title, xlabel=xlabel, ylabel=ylabel)
        ax.legend(loc='best')
        
        # X轴日期格式化
        if pd.api.types.is_datetime64_any_dtype(self.data[x_col]):
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        
        if source:
            add_source_note(ax, source)
        
        if save_path:
            self.save(save_path)
        
        return fig, ax
    
    def plot_with_shade(self, x_col, y_col, title, xlabel='日期', ylabel='数值',
                        save_path=None, source=None):
        """
        绘制带置信区间的线图
        
        Args:
            y_col: 主数据列
            y_col_lower: 下界列
            y_col_upper: 上界列
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(self.data[x_col], self.data[y_col], 
               color=UBS_BLUE, linewidth=1.5, label=y_col)
        ax.fill_between(self.data[x_col], 
                        self.data.get(f'{y_col}_lower', self.data[y_col] * 0.95),
                        self.data.get(f'{y_col}_upper', self.data[y_col] * 1.05),
                        alpha=0.2, color=UBS_BLUE_LIGHT)
        
        style_axis(ax, title=title, xlabel=xlabel, ylabel=ylabel)
        ax.legend(loc='best')
        plt.tight_layout()
        
        if source:
            add_source_note(ax, source)
        
        if save_path:
            self.save(save_path)
        
        return fig, ax


class BarChart(ChartGenerator):
    """柱状图生成器"""
    
    def plot_grouped(self, x_col, y_cols, title, ylabel='数值', save_path=None, source=None):
        """
        绘制分组柱状图
        
        Args:
            x_col: X轴分类列名
            y_cols: Y轴数据列名列表
            title: 图表标题
            ylabel: Y轴标签
            save_path: 保存路径
            source: 数据来源
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        
        x = np.arange(len(self.data))
        width = 0.8 / len(y_cols)
        
        for i, col in enumerate(y_cols):
            offset = (i - len(y_cols)/2 + 0.5) * width
            ax.bar(x + offset, self.data[col], width, label=col, color=UBS_COLORS[i])
        
        ax.set_xticks(x)
        ax.set_xticklabels(self.data[x_col], rotation=45, ha='right')
        style_axis(ax, title=title, ylabel=ylabel)
        ax.legend(loc='best')
        plt.tight_layout()
        
        if source:
            add_source_note(ax, source)
        
        if save_path:
            self.save(save_path)
        
        return fig, ax
    
    def plot_stacked(self, x_col, y_cols, title, ylabel='数值', save_path=None, source=None):
        """
        绘制堆叠柱状图
        
        Args:
            x_col: X轴分类列名
            y_cols: Y轴数据列名列表（将堆叠在一起）
            title: 图表标题
            ylabel: Y轴标签
            save_path: 保存路径
            source: 数据来源
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        
        bottom = np.zeros(len(self.data))
        
        for i, col in enumerate(y_cols):
            ax.bar(self.data[x_col], self.data[col], bottom=bottom, 
                   label=col, color=UBS_COLORS[i % len(UBS_COLORS)], width=0.6)
            bottom += self.data[col].values
        
        style_axis(ax, title=title, ylabel=ylabel)
        ax.legend(loc='best')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        if source:
            add_source_note(ax, source)
        
        if save_path:
            self.save(save_path)
        
        return fig, ax
    
    def plot_yoy_qoq(self, categories, yoy_col, qoq_col, title, save_path=None, source=None):
        """
        绘制同比/环比柱状图
        
        Args:
            categories: 分类列表（X轴）
            yoy_col: 同比数据列名
            qoq_col: 环比数据列名
            title: 图表标题
            save_path: 保存路径
            source: 数据来源
        """
        fig, ax = plt.subplots(figsize=(12, 6))
        
        x = np.arange(len(categories))
        width = 0.35
        
        # 同比柱状图
        bars1 = ax.bar(x - width/2, self.data[yoy_col], width, 
                       label='同比(%)', color=UBS_BLUE)
        
        # 环比柱状图
        bars2 = ax.bar(x + width/2, self.data[qoq_col], width,
                       label='环比(%)', color=UBS_BLUE_LIGHT)
        
        # 添加零线
        ax.axhline(y=0, color='black', linestyle('-'), linewidth=0.8)
        
        # 添加数值标签
        for bar in bars1:
            height = bar.get_height()
            va = 'bottom' if height >= 0 else 'top'
            offset = 0.5 if height >= 0 else -0.5
            ax.annotate(f'{height:.1f}%',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, offset),
                       textcoords="offset points",
                       ha='center', va=va, fontsize=9)
        
        for bar in bars2:
            height = bar.get_height()
            va = 'bottom' if height >= 0 else 'top'
            offset = 0.5 if height >= 0 else -0.5
            ax.annotate(f'{height:.1f}%',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, offset),
                       textcoords="offset points",
                       ha='center', va=va, fontsize=9)
        
        ax.set_xticks(x)
        ax.set_xticklabels(categories, rotation=45, ha='right')
        style_axis(ax, title=title, ylabel='变动率(%)')
        ax.legend(loc='upper right')
        plt.tight_layout()
        
        if source:
            add_source_note(ax, source)
        
        if save_path:
            self.save(save_path)
        
        return fig, ax


class HeatmapChart(ChartGenerator):
    """热力图生成器"""
    
    def plot(self, data=None, title='热力图', cmap='RdYlGn_r', 
             center=0, annot=True, fmt='.1f', save_path=None, source=None):
        """
        绘制热力图
        
        Args:
            data: 热力图数据矩阵，如果为None则使用self.data
            title: 图表标题
            cmap: 颜色映射
            center: 中心值
            annot: 是否显示数值
            fmt: 数值格式
            save_path: 保存路径
            source: 数据来源
        """
        import seaborn as sns
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        if data is None:
            data = self.data
        
        sns.heatmap(data, 
                   annot=annot, 
                   fmt=fmt,
                   cmap=cmap,
                   center=center,
                   linewidths=0.5,
                   cbar_kws={'label': '涨跌幅(%)'},
                   ax=ax)
        
        ax.set_title(title, fontsize=14, fontweight='bold', pad=12)
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        plt.tight_layout()
        
        if source:
            add_source_note(ax, source)
        
        if save_path:
            self.save(save_path)
        
        return fig, ax


if __name__ == '__main__':
    # 测试代码
    print("[INFO] 图表生成器测试")
    print("[INFO] 图表生成器测试")
    
    # 创建测试数据
    dates = pd.date_range('2024-01-01', periods=12, freq='M')
    test_data = pd.DataFrame({
        'date': dates,
        'revenue': np.random.randn(12).cumsum() + 100,
        'profit': np.random.randn(12).cumsum() + 20,
    })
    
    # 测试时间序列图
    ts = TimeSeriesChart(test_data)
    print("[OK] TimeSeriesChart 创建成功")
    
    # 测试柱状图
    bar_data = pd.DataFrame({
        'quarter': ['Q1', 'Q2', 'Q3', 'Q4'],
        'revenue': [100, 120, 115, 130],
        'profit': [20, 25, 22, 28]
    })
    bar = BarChart(bar_data)
    print("[OK] BarChart 创建成功")
    
    print("[INFO] 测试完成!")
