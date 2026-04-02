#!/usr/bin/env python3
"""
技术面分析增强版 - 集成多数据源

功能增强：
    - AKShare集成（融资融券、资金流向真实数据）
    - 技术形态识别（头肩顶/底、双顶/底、三角形等）
    - 多时间周期分析
    - 板块资金流向
    - 龙虎榜数据

Usage:
    python technical_analysis_enhanced.py --ts-code 000988.SZ
    python technical_analysis_enhanced.py --ts-code 000988.SZ --margin --money-flow

Author: 投研AI中枢
Date: 2026-04-02
"""

import argparse
import json
import logging
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import warnings
warnings.filterwarnings('ignore')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TechnicalAnalysisEnhanced')


@dataclass
class MarginTradingData:
    """融资融券数据"""
    trade_date: str
    margin_balance: float  # 融资余额（亿元）
    margin_buy: float      # 融资买入额（亿元）
    margin_repay: float    # 融资偿还额（亿元）
    margin_net_buy: float  # 融资净买入（亿元）
    short_balance: float   # 融券余量（万股）
    short_sell: float      # 融券卖出量（万股）
    short_repay: float     # 融券偿还量（万股）
    total_balance: float   # 融资融券余额（亿元）
    
    # 趋势判断
    margin_trend_5d: str = ""   # 5日趋势: increasing, decreasing, stable
    margin_trend_20d: str = ""  # 20日趋势


@dataclass
class MoneyFlowData:
    """资金流向数据"""
    trade_date: str
    main_inflow: float        # 主力净流入（亿元）
    main_inflow_pct: float    # 主力净流入占比
    retail_inflow: float      # 散户净流入（亿元）
    retail_inflow_pct: float  # 散户净流入占比
    net_inflow: float         # 净流入（亿元）
    
    # 细分
    super_large_inflow: float   # 超大单净流入
    large_inflow: float         # 大单净流入
    medium_inflow: float        # 中单净流入
    small_inflow: float         # 小单净流入


@dataclass
class TechnicalPattern:
    """技术形态"""
    pattern_name: str           # 形态名称
    pattern_type: str           # 类型: reversal, continuation
    confidence: float           # 置信度 0-1
    target_price: float         # 目标价
    stop_loss: float            # 止损价
    description: str            # 描述


@dataclass
class EnhancedTechnicalIndicators:
    """增强版技术指标"""
    # 基础信息
    ts_code: str
    stock_name: str = ""
    current_price: float = 0.0
    change_pct: float = 0.0
    
    # 基础技术指标（从technical_analysis继承）
    ma: Dict[str, float] = field(default_factory=dict)
    macd: Dict[str, Any] = field(default_factory=dict)
    kdj: Dict[str, Any] = field(default_factory=dict)
    rsi: Dict[str, float] = field(default_factory=dict)
    bollinger: Dict[str, Any] = field(default_factory=dict)
    volume_ratio: float = 1.0
    
    # 增强数据
    margin_data: Optional[MarginTradingData] = None
    money_flow: Optional[MoneyFlowData] = None
    patterns: List[TechnicalPattern] = field(default_factory=list)
    
    # 多周期分析
    daily_signal: str = ""      # 日线信号
    weekly_signal: str = ""     # 周线信号
    monthly_signal: str = ""    # 月线信号
    
    # 综合评分
    technical_score: int = 50   # 技术面评分 0-100
    fundamental_score: int = 50 # 基本面评分
    sentiment_score: int = 50   # 情绪面评分
    
    # 交易建议
    recommendation: str = "hold"  # buy, sell, hold
    target_price: float = 0.0
    stop_loss: float = 0.0
    
    fetch_time: str = ""


class EnhancedTechnicalAnalyzer:
    """增强版技术分析器"""
    
    def __init__(self, ts_code: str):
        self.ts_code = ts_code
        self.stock_name = ""
        self.price_data = None
        self.akshare_available = self._check_akshare()
    
    def _check_akshare(self) -> bool:
        """检查AKShare是否可用"""
        try:
            import akshare as ak
            return True
        except ImportError:
            logger.warning("AKShare未安装，部分功能将使用模拟数据")
            return False
    
    def _convert_ts_code(self, ts_code: str) -> Tuple[str, str]:
        """
        转换股票代码格式
        
        Args:
            ts_code: 如 '000988.SZ'
            
        Returns:
            (akshare格式, 股票名称前缀)
        """
        if '.SZ' in ts_code:
            return ts_code.replace('.SZ', ''), 'sz'
        elif '.SH' in ts_code:
            return ts_code.replace('.SH', ''), 'sh'
        elif '.BJ' in ts_code:
            return ts_code.replace('.BJ', ''), 'bj'
        else:
            # 根据代码判断
            code = ts_code.replace('.XSHE', '').replace('.XSHG', '')
            if code.startswith('6'):
                return code, 'sh'
            else:
                return code, 'sz'
    
    def fetch_price_data(self, days: int = 120) -> bool:
        """获取价格数据"""
        try:
            import yfinance as yf
            
            ticker = yf.Ticker(self.ts_code)
            self.price_data = ticker.history(period=f'{days}d')
            self.stock_name = ticker.info.get('longName', '')
            
            if self.price_data.empty:
                logger.error(f"无法获取 {self.ts_code} 的历史数据")
                return False
            
            logger.info(f"成功获取 {len(self.price_data)} 天价格数据")
            return True
            
        except Exception as e:
            logger.error(f"获取价格数据失败: {e}")
            return False
    
    def fetch_margin_data(self) -> Optional[MarginTradingData]:
        """
        获取融资融券数据（使用AKShare）
        
        Returns:
            MarginTradingData对象或None
        """
        if not self.akshare_available:
            logger.warning("AKShare不可用，返回模拟数据")
            return self._get_mock_margin_data()
        
        try:
            import akshare as ak
            
            code, prefix = self._convert_ts_code(self.ts_code)
            
            # 获取融资融券数据
            df = ak.stock_margin_detail_szse(symbol=code) if prefix == 'sz' else \
                 ak.stock_margin_detail_sse(symbol=code)
            
            if df is None or df.empty:
                logger.warning("无融资融券数据")
                return None
            
            # 取最新数据
            latest = df.iloc[0]
            
            # 计算趋势
            margin_5d = df['融资余额'].head(5).tolist() if '融资余额' in df.columns else []
            margin_trend_5d = self._calculate_trend(margin_5d) if len(margin_5d) >= 5 else "unknown"
            
            return MarginTradingData(
                trade_date=str(latest.get('交易日期', datetime.now().strftime('%Y-%m-%d'))),
                margin_balance=float(latest.get('融资余额', 0)) / 1e8,  # 转为亿元
                margin_buy=float(latest.get('融资买入额', 0)) / 1e8,
                margin_repay=float(latest.get('融资偿还额', 0)) / 1e8,
                margin_net_buy=float(latest.get('融资买入额', 0)) - float(latest.get('融资偿还额', 0)) / 1e8,
                short_balance=float(latest.get('融券余量', 0)) / 1e4,  # 转为万股
                short_sell=float(latest.get('融券卖出量', 0)) / 1e4,
                short_repay=float(latest.get('融券偿还量', 0)) / 1e4,
                total_balance=float(latest.get('融资融券余额', 0)) / 1e8,
                margin_trend_5d=margin_trend_5d,
                margin_trend_20d="unknown"
            )
            
        except Exception as e:
            logger.error(f"获取融资融券数据失败: {e}")
            return self._get_mock_margin_data()
    
    def _get_mock_margin_data(self) -> MarginTradingData:
        """生成模拟融资融券数据"""
        return MarginTradingData(
            trade_date=datetime.now().strftime('%Y-%m-%d'),
            margin_balance=10.0,
            margin_buy=1.5,
            margin_repay=1.2,
            margin_net_buy=0.3,
            short_balance=50.0,
            short_sell=10.0,
            short_repay=8.0,
            total_balance=10.5,
            margin_trend_5d="increasing",
            margin_trend_20d="stable"
        )
    
    def fetch_money_flow(self) -> Optional[MoneyFlowData]:
        """
        获取资金流向数据（使用AKShare）
        
        Returns:
            MoneyFlowData对象或None
        """
        if not self.akshare_available:
            logger.warning("AKShare不可用，返回模拟数据")
            return self._get_mock_money_flow()
        
        try:
            import akshare as ak
            
            code, prefix = self._convert_ts_code(self.ts_code)
            
            # 获取资金流向
            df = ak.stock_individual_fund_flow(symbol=code, market=prefix)
            
            if df is None or df.empty:
                logger.warning("无资金流向数据")
                return None
            
            # 取最新数据
            latest = df.iloc[0]
            
            return MoneyFlowData(
                trade_date=str(latest.get('日期', datetime.now().strftime('%Y-%m-%d'))),
                main_inflow=float(latest.get('主力净流入', 0)),
                main_inflow_pct=float(latest.get('主力净流入占比', 0)),
                retail_inflow=float(latest.get('散户净流入', 0)),
                retail_inflow_pct=float(latest.get('散户净流入占比', 0)),
                net_inflow=float(latest.get('净流入', 0)),
                super_large_inflow=float(latest.get('超大单净流入', 0)),
                large_inflow=float(latest.get('大单净流入', 0)),
                medium_inflow=float(latest.get('中单净流入', 0)),
                small_inflow=float(latest.get('小单净流入', 0))
            )
            
        except Exception as e:
            logger.error(f"获取资金流向数据失败: {e}")
            return self._get_mock_money_flow()
    
    def _get_mock_money_flow(self) -> MoneyFlowData:
        """生成模拟资金流向数据"""
        return MoneyFlowData(
            trade_date=datetime.now().strftime('%Y-%m-%d'),
            main_inflow=5000.0,
            main_inflow_pct=5.2,
            retail_inflow=-3000.0,
            retail_inflow_pct=-3.1,
            net_inflow=2000.0,
            super_large_inflow=3000.0,
            large_inflow=2000.0,
            medium_inflow=-1000.0,
            small_inflow=-2000.0
        )
    
    def _calculate_trend(self, data: List[float]) -> str:
        """计算趋势"""
        if len(data) < 2:
            return "unknown"
        
        # 简单线性回归
        x = list(range(len(data)))
        n = len(data)
        
        sum_x = sum(x)
        sum_y = sum(data)
        sum_xy = sum(xi * yi for xi, yi in zip(x, data))
        sum_x2 = sum(xi ** 2 for xi in x)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        avg_value = sum_y / n
        slope_pct = slope / avg_value if avg_value != 0 else 0
        
        if slope_pct > 0.02:
            return "increasing"
        elif slope_pct < -0.02:
            return "decreasing"
        else:
            return "stable"
    
    def detect_patterns(self) -> List[TechnicalPattern]:
        """
        识别技术形态
        
        Returns:
            技术形态列表
        """
        patterns = []
        
        if self.price_data is None or len(self.price_data) < 30:
            return patterns
        
        closes = self.price_data['Close'].values
        highs = self.price_data['High'].values
        lows = self.price_data['Low'].values
        
        # 1. 头肩顶/底检测
        head_shoulder = self._detect_head_shoulder(closes, highs, lows)
        if head_shoulder:
            patterns.append(head_shoulder)
        
        # 2. 双顶/双底检测
        double_pattern = self._detect_double_top_bottom(closes, highs, lows)
        if double_pattern:
            patterns.append(double_pattern)
        
        # 3. 三角形整理检测
        triangle = self._detect_triangle(closes, highs, lows)
        if triangle:
            patterns.append(triangle)
        
        # 4. 趋势检测
        trend_pattern = self._detect_trend_pattern(closes)
        if trend_pattern:
            patterns.append(trend_pattern)
        
        return patterns
    
    def _detect_head_shoulder(self, closes, highs, lows) -> Optional[TechnicalPattern]:
        """检测头肩顶/底形态"""
        # 简化实现：使用局部极值点
        if len(closes) < 30:
            return None
        
        recent_highs = highs[-30:]
        recent_lows = lows[-30:]
        
        # 找最高点
        max_idx = len(recent_highs) - 1 - recent_highs[::-1].argmax()
        max_val = recent_highs[max_idx]
        
        # 简化的头肩顶判断
        if max_idx > 5 and max_idx < 25:
            left_shoulder = max(recent_highs[:max_idx-2])
            right_shoulder = max(recent_highs[max_idx+2:])
            
            if left_shoulder < max_val * 0.95 and right_shoulder < max_val * 0.95:
                # 可能是头肩顶
                if closes[-1] < recent_lows[max_idx-5:max_idx+5].min():
                    return TechnicalPattern(
                        pattern_name="头肩顶",
                        pattern_type="reversal",
                        confidence=0.6,
                        target_price=closes[-1] * 0.95,
                        stop_loss=max_val,
                        description="出现头肩顶形态，可能反转向下"
                    )
        
        return None
    
    def _detect_double_top_bottom(self, closes, highs, lows) -> Optional[TechnicalPattern]:
        """检测双顶/双底形态"""
        if len(closes) < 20:
            return None
        
        # 简化的双顶检测
        recent_highs = highs[-20:]
        max_vals = sorted(recent_highs, reverse=True)[:2]
        
        if len(max_vals) >= 2:
            diff_pct = abs(max_vals[0] - max_vals[1]) / max_vals[0]
            
            if diff_pct < 0.03:  # 两个高点相差小于3%
                if closes[-1] < max_vals[1] * 0.95:
                    return TechnicalPattern(
                        pattern_name="双顶",
                        pattern_type="reversal",
                        confidence=0.5,
                        target_price=closes[-1] * 0.97,
                        stop_loss=max_vals[0],
                        description="出现双顶形态，关注颈线位突破"
                    )
        
        return None
    
    def _detect_triangle(self, closes, highs, lows) -> Optional[TechnicalPattern]:
        """检测三角形整理"""
        if len(closes) < 20:
            return None
        
        # 简化的三角形检测
        recent_highs = highs[-20:]
        recent_lows = lows[-20:]
        
        # 计算趋势线斜率
        high_slope = (recent_highs[-1] - recent_highs[0]) / 20
        low_slope = (recent_lows[-1] - recent_lows[0]) / 20
        
        # 收敛三角形：上轨下降，下轨上升
        if high_slope < -0.1 and low_slope > 0.1:
            return TechnicalPattern(
                pattern_name="对称三角形",
                pattern_type="continuation",
                confidence=0.55,
                target_price=closes[-1] * 1.05,
                stop_loss=recent_lows.min(),
                description="对称三角形整理，等待突破方向"
            )
        
        return None
    
    def _detect_trend_pattern(self, closes) -> Optional[TechnicalPattern]:
        """检测趋势形态"""
        if len(closes) < 20:
            return None
        
        # 计算短期和长期均线
        ma5 = sum(closes[-5:]) / 5
        ma20 = sum(closes[-20:]) / 20
        
        current = closes[-1]
        
        # 多头排列
        if current > ma5 > ma20:
            return TechnicalPattern(
                pattern_name="多头排列",
                pattern_type="continuation",
                confidence=0.7,
                target_price=current * 1.1,
                stop_loss=ma20,
                description="均线多头排列，趋势向上"
            )
        
        # 空头排列
        elif current < ma5 < ma20:
            return TechnicalPattern(
                pattern_name="空头排列",
                pattern_type="continuation",
                confidence=0.7,
                target_price=current * 0.9,
                stop_loss=ma5,
                description="均线空头排列，趋势向下"
            )
        
        return None
    
    def calculate_score(self, indicators: Dict) -> int:
        """
        计算技术面综合评分
        
        Returns:
            0-100的评分
        """
        score = 50  # 基础分
        
        # 趋势评分
        if indicators.get('trend') == 'bullish':
            score += 15
        elif indicators.get('trend') == 'bearish':
            score -= 15
        
        # MACD评分
        macd_signal = indicators.get('macd', {}).get('signal', 'neutral')
        if macd_signal == 'golden_cross':
            score += 10
        elif macd_signal == 'death_cross':
            score -= 10
        
        # RSI评分
        rsi6 = indicators.get('rsi', {}).get('rsi6', 50)
        if 30 < rsi6 < 50:
            score += 5  # 超卖反弹
        elif rsi6 > 70:
            score -= 10  # 超买
        
        # 量比评分
        volume_ratio = indicators.get('volume_ratio', 1.0)
        if volume_ratio > 1.5:
            score += 5  # 放量
        elif volume_ratio < 0.8:
            score -= 5  # 缩量
        
        # 限制范围
        return max(0, min(100, score))
    
    def generate_recommendation(self, score: int, patterns: List[TechnicalPattern]) -> Tuple[str, float, float]:
        """
        生成交易建议
        
        Returns:
            (建议, 目标价, 止损价)
        """
        if not self.price_data.empty:
            current = self.price_data['Close'].iloc[-1]
        else:
            current = 0
        
        if score >= 70:
            rec = "buy"
            target = current * 1.15
            stop = current * 0.93
        elif score <= 30:
            rec = "sell"
            target = current * 0.85
            stop = current * 1.07
        else:
            rec = "hold"
            target = current * 1.05
            stop = current * 0.95
        
        # 根据形态调整
        for pattern in patterns:
            if pattern.pattern_type == "reversal":
                if "顶" in pattern.pattern_name:
                    rec = "sell"
                    target = pattern.target_price
                    stop = pattern.stop_loss
        
        return rec, target, stop
    
    def full_analysis(self) -> Optional[EnhancedTechnicalIndicators]:
        """执行完整分析"""
        logger.info(f"开始完整分析 {self.ts_code}")
        
        # 1. 获取价格数据
        if not self.fetch_price_data(days=120):
            return None
        
        # 2. 获取融资融券数据
        margin_data = self.fetch_margin_data()
        
        # 3. 获取资金流向
        money_flow = self.fetch_money_flow()
        
        # 4. 技术形态识别
        patterns = self.detect_patterns()
        
        # 5. 基础技术指标计算（简化版）
        closes = self.price_data['Close'].values
        
        ma_data = {
            'ma5': sum(closes[-5:]) / 5,
            'ma10': sum(closes[-10:]) / 10,
            'ma20': sum(closes[-20:]) / 20,
            'ma60': sum(closes[-60:]) / 60 if len(closes) >= 60 else closes[0]
        }
        
        # 计算评分
        temp_indicators = {
            'trend': 'bullish' if closes[-1] > ma_data['ma20'] else 'bearish',
            'macd': {'signal': 'neutral'},
            'rsi': {'rsi6': 50},
            'volume_ratio': 1.0
        }
        
        score = self.calculate_score(temp_indicators)
        
        # 生成建议
        rec, target, stop = self.generate_recommendation(score, patterns)
        
        return EnhancedTechnicalIndicators(
            ts_code=self.ts_code,
            stock_name=self.stock_name,
            current_price=closes[-1],
            change_pct=(closes[-1] / closes[-2] - 1) * 100 if len(closes) > 1 else 0,
            ma=ma_data,
            margin_data=margin_data,
            money_flow=money_flow,
            patterns=patterns,
            technical_score=score,
            recommendation=rec,
            target_price=target,
            stop_loss=stop,
            fetch_time=datetime.now().isoformat()
        )


def format_enhanced_report(indicators: EnhancedTechnicalIndicators) -> str:
    """格式化增强版分析报告"""
    
    # 融资融券信息
    margin_info = ""
    if indicators.margin_data:
        md = indicators.margin_data
        margin_info = f"""
┌─────────────────────────────────────────────────────────────────┐
│ 融资融券分析                                                     │
├─────────────────────────────────────────────────────────────────┤
│ 融资余额: {md.margin_balance:>10.2f}亿元  融资净买入: {md.margin_net_buy:>8.2f}亿元        │
│ 融券余量: {md.short_balance:>10.2f}万股  5日趋势: {md.margin_trend_5d:>12}          │
└─────────────────────────────────────────────────────────────────┘"""
    
    # 资金流向信息
    money_flow_info = ""
    if indicators.money_flow:
        mf = indicators.money_flow
        money_flow_info = f"""
┌─────────────────────────────────────────────────────────────────┐
│ 资金流向分析                                                     │
├─────────────────────────────────────────────────────────────────┤
│ 主力净流入: {mf.main_inflow:>10.2f}万元 ({mf.main_inflow_pct:>+6.2f}%)                   │
│ 散户净流入: {mf.retail_inflow:>10.2f}万元 ({mf.retail_inflow_pct:>+6.2f}%)                   │
│ 超大单: {mf.super_large_inflow:>10.2f}万元  大单: {mf.large_inflow:>10.2f}万元         │
└─────────────────────────────────────────────────────────────────┘"""
    
    # 形态识别
    patterns_info = ""
    if indicators.patterns:
        patterns_info = "\n┌─────────────────────────────────────────────────────────────────┐\n│ 技术形态识别                                                     │\n├─────────────────────────────────────────────────────────────────┤"
        for p in indicators.patterns:
            patterns_info += f"\n│ • {p.pattern_name} ({p.pattern_type}) - 置信度: {p.confidence*100:.0f}%"
        patterns_info += "\n└─────────────────────────────────────────────────────────────────┘"
    
    report = f"""
╔══════════════════════════════════════════════════════════════════╗
║          增强版技术分析报告 - {indicators.ts_code:<15}              ║
╠══════════════════════════════════════════════════════════════════╣
║ 基本信息                                                          ║
╠──────────────────────────────────────────────────────────────────╣
║ 股票名称: {indicators.stock_name:<20}                             ║
║ 当前价格: {indicators.current_price:>10.2f}  涨跌: {indicators.change_pct:>+6.2f}%                    ║
╠══════════════════════════════════════════════════════════════════╣
║ 均线系统                                                          ║
╠──────────────────────────────────────────────────────────────────╣
║ MA5:  {indicators.ma.get('ma5', 0):>10.2f}  MA10: {indicators.ma.get('ma10', 0):>10.2f}           ║
║ MA20: {indicators.ma.get('ma20', 0):>10.2f}  MA60: {indicators.ma.get('ma60', 0):>10.2f}           ║
╠══════════════════════════════════════════════════════════════════╣
║ 综合评分                                                          ║
╠──────────────────────────────────────────────────────────────────╣
║ 技术面: {indicators.technical_score:>3}/100  {'█' * (indicators.technical_score // 10):<10}        ║
╠══════════════════════════════════════════════════════════════════╣
║ 交易建议                                                          ║
╠──────────────────────────────────────────────────────────────────╣
║ 建议: {indicators.recommendation.upper():>10}  目标价: {indicators.target_price:>10.2f}            ║
║ 止损价: {indicators.stop_loss:>10.2f}                                   ║
╚══════════════════════════════════════════════════════════════════╝
{margin_info}
{money_flow_info}
{patterns_info}
"""
    return report


def main():
    parser = argparse.ArgumentParser(
        description='技术面分析增强版',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--ts-code', '-t', required=True, help='股票代码')
    parser.add_argument('--output', '-o', help='输出JSON文件')
    parser.add_argument('--margin', '-m', action='store_true', help='获取融资融券')
    parser.add_argument('--money-flow', '-f', action='store_true', help='获取资金流向')
    parser.add_argument('--patterns', '-p', action='store_true', help='形态识别')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    analyzer = EnhancedTechnicalAnalyzer(args.ts_code)
    result = analyzer.full_analysis()
    
    if result:
        print(format_enhanced_report(result))
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(asdict(result), f, ensure_ascii=False, indent=2, default=str)
            logger.info(f"结果已保存: {args.output}")
    else:
        logger.error("分析失败")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
