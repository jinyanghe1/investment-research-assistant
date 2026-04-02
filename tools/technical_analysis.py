#!/usr/bin/env python3
"""
技术面分析工具 - 全面的股票技术分析

功能：
    - 量比分析
    - 多空头判断
    - 融资融券数据
    - 技术指标计算 (MACD, KDJ, RSI, BOLL, MA等)
    - 技术形态识别

Usage:
    python technical_analysis.py --ts-code 000988.SZ --days 60
    python technical_analysis.py --ts-code 000988.SZ --output analysis.json
    python technical_analysis.py --ts-code 000988.SZ --full-analysis

Example:
    python technical_analysis.py --ts-code 000988.SZ --full-analysis --verbose
"""

import argparse
import json
import logging
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TechnicalAnalysis')


@dataclass
class TechnicalIndicators:
    """技术指标数据类"""
    # 基础价格数据
    ts_code: str
    current_price: float
    prev_close: float
    open_price: float
    high_price: float
    low_price: float
    volume: float
    
    # 趋势指标
    ma5: float
    ma10: float
    ma20: float
    ma60: float
    ma120: float
    ma250: float
    
    # MACD指标
    macd_dif: float
    macd_dea: float
    macd_histogram: float
    macd_signal: str  # 'golden_cross', 'death_cross', 'neutral'
    
    # KDJ指标
    k_value: float
    d_value: float
    j_value: float
    kdj_signal: str  # 'overbought', 'oversold', 'neutral'
    
    # RSI指标
    rsi6: float
    rsi12: float
    rsi24: float
    rsi_signal: str  # 'overbought', 'oversold', 'neutral'
    
    # 布林带
    boll_upper: float
    boll_middle: float
    boll_lower: float
    boll_position: str  # 'upper', 'middle', 'lower', 'break_upper', 'break_lower'
    boll_width: float  # 布林带宽度
    
    # 量比
    volume_ratio: float
    volume_signal: str  # 'high', 'normal', 'low'
    
    # 资金流向
    main_force_inflow: float  # 主力净流入
    retail_inflow: float  # 散户净流入
    net_inflow: float  # 净流入
    
    # 融资融券
    margin_balance: float  # 融资余额
    margin_buy: float  # 融资买入额
    margin_repay: float  # 融资偿还额
    short_balance: float  # 融券余量
    
    # 综合判断
    trend: str  # 'bullish', 'bearish', 'neutral'
    strength: str  # 'strong', 'medium', 'weak'
    support_level: float
    resistance_level: float
    
    # 时间戳
    fetch_time: str


class TechnicalAnalyzer:
    """技术分析器"""
    
    def __init__(self, ts_code: str):
        self.ts_code = ts_code
        self.price_data = None
        self.volume_data = None
    
    def fetch_data(self, days: int = 120) -> bool:
        """
        获取历史数据
        
        Args:
            days: 获取天数
            
        Returns:
            是否成功
        """
        try:
            import yfinance as yf
            
            ticker = yf.Ticker(self.ts_code)
            
            # 获取历史价格数据
            self.price_data = ticker.history(period=f'{days}d')
            
            if self.price_data.empty:
                logger.error(f"无法获取 {self.ts_code} 的历史数据")
                return False
            
            logger.info(f"成功获取 {len(self.price_data)} 天历史数据")
            return True
            
        except Exception as e:
            logger.error(f"获取数据失败: {e}")
            return False
    
    def calculate_ma(self, data: np.ndarray, period: int) -> float:
        """计算移动平均线"""
        if len(data) < period:
            return np.nan
        return np.mean(data[-period:])
    
    def calculate_macd(self, closes: np.ndarray, 
                       fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float, float]:
        """
        计算MACD指标
        
        Returns:
            (DIF, DEA, MACD Histogram)
        """
        # 计算EMA
        ema_fast = self._calculate_ema(closes, fast)
        ema_slow = self._calculate_ema(closes, slow)
        
        # DIF = EMA(12) - EMA(26)
        dif = ema_fast - ema_slow
        
        # DEA = EMA(DIF, 9)
        dea = self._calculate_ema_value(dif, signal)
        
        # MACD Histogram = (DIF - DEA) * 2
        histogram = (dif - dea) * 2
        
        return dif, dea, histogram
    
    def _calculate_ema(self, data: np.ndarray, period: int) -> float:
        """计算EMA序列的最后值"""
        alpha = 2 / (period + 1)
        ema = data[0]
        for price in data[1:]:
            ema = alpha * price + (1 - alpha) * ema
        return ema
    
    def _calculate_ema_value(self, value: float, period: int, prev_ema: float = None) -> float:
        """计算EMA单值"""
        if prev_ema is None:
            return value
        alpha = 2 / (period + 1)
        return alpha * value + (1 - alpha) * prev_ema
    
    def calculate_kdj(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                      n: int = 9, m1: int = 3, m2: int = 3) -> Tuple[float, float, float]:
        """
        计算KDJ指标
        
        Returns:
            (K, D, J)
        """
        # RSV = (今日收盘价 - N日内最低价) / (N日内最高价 - N日内最低价) * 100
        low_n = np.min(lows[-n:])
        high_n = np.max(highs[-n:])
        
        if high_n == low_n:
            rsv = 50
        else:
            rsv = (closes[-1] - low_n) / (high_n - low_n) * 100
        
        # 初始化K、D值
        k = 50
        d = 50
        
        # 计算K、D值
        for i in range(max(0, len(closes) - n), len(closes)):
            low_n = np.min(lows[max(0, i-n+1):i+1])
            high_n = np.max(highs[max(0, i-n+1):i+1])
            
            if high_n == low_n:
                rsv = 50
            else:
                rsv = (closes[i] - low_n) / (high_n - low_n) * 100
            
            k = (2/3) * k + (1/3) * rsv
            d = (2/3) * d + (1/3) * k
        
        # J = 3K - 2D
        j = 3 * k - 2 * d
        
        return k, d, j
    
    def calculate_rsi(self, closes: np.ndarray, period: int = 14) -> float:
        """
        计算RSI指标
        
        Args:
            closes: 收盘价数组
            period: 周期
            
        Returns:
            RSI值
        """
        if len(closes) < period + 1:
            return 50
        
        # 计算价格变化
        deltas = np.diff(closes)
        
        # 分离上涨和下跌
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # 计算平均涨跌
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_bollinger(self, closes: np.ndarray, period: int = 20, 
                           std_dev: float = 2.0) -> Tuple[float, float, float]:
        """
        计算布林带
        
        Returns:
            (上轨, 中轨, 下轨)
        """
        if len(closes) < period:
            return closes[-1], closes[-1], closes[-1]
        
        # 中轨 = N日移动平均线
        middle = np.mean(closes[-period:])
        
        # 标准差
        std = np.std(closes[-period:])
        
        # 上轨和下轨
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        
        return upper, middle, lower
    
    def calculate_volume_ratio(self, volumes: np.ndarray, period: int = 5) -> float:
        """
        计算量比
        
        量比 = 当日成交量 / 过去N日平均成交量
        
        Args:
            volumes: 成交量数组
            period: 对比周期
            
        Returns:
            量比值
        """
        if len(volumes) < period + 1:
            return 1.0
        
        current_volume = volumes[-1]
        avg_volume = np.mean(volumes[-(period+1):-1])  # 排除当日
        
        if avg_volume == 0:
            return 1.0
        
        return current_volume / avg_volume
    
    def analyze_trend(self, closes: np.ndarray, ma5: float, ma20: float, ma60: float) -> str:
        """
        分析趋势
        
        Returns:
            'bullish', 'bearish', 'neutral'
        """
        current = closes[-1]
        
        # 多头排列判断
        if current > ma5 > ma20 > ma60:
            return 'bullish'
        
        # 空头排列判断
        if current < ma5 < ma20 < ma60:
            return 'bearish'
        
        return 'neutral'
    
    def calculate_support_resistance(self, highs: np.ndarray, lows: np.ndarray, 
                                    closes: np.ndarray, period: int = 20) -> Tuple[float, float]:
        """
        计算支撑位和阻力位
        
        Returns:
            (支撑位, 阻力位)
        """
        recent_highs = highs[-period:]
        recent_lows = lows[-period:]
        
        resistance = np.max(recent_highs)
        support = np.min(recent_lows)
        
        # 更精确的算法：使用枢轴点
        pivot = (highs[-1] + lows[-1] + closes[-1]) / 3
        
        # 第一支撑位和阻力位
        r1 = 2 * pivot - lows[-1]
        s1 = 2 * pivot - highs[-1]
        
        return s1, r1
    
    def fetch_margin_data(self) -> Dict[str, float]:
        """
        获取融资融券数据（模拟数据，实际需要接入交易所API）
        
        Returns:
            融资融券数据字典
        """
        # TODO: 接入实际融资融券API
        # 目前返回模拟数据
        return {
            'margin_balance': 0,  # 融资余额
            'margin_buy': 0,      # 融资买入额
            'margin_repay': 0,    # 融资偿还额
            'short_balance': 0,   # 融券余量
            'short_sell': 0,      # 融券卖出量
            'short_repay': 0,     # 融券偿还量
        }
    
    def fetch_money_flow(self) -> Dict[str, float]:
        """
        获取资金流向数据（模拟数据，实际需要接入AKShare或同花顺API）
        
        Returns:
            资金流向数据字典
        """
        # TODO: 接入实际资金流向API
        # 目前返回模拟数据
        return {
            'main_force_inflow': 0,  # 主力净流入
            'retail_inflow': 0,      # 散户净流入
            'net_inflow': 0,         # 净流入
        }
    
    def full_analysis(self) -> Optional[TechnicalIndicators]:
        """
        执行完整的技术分析
        
        Returns:
            TechnicalIndicators对象或None
        """
        if not self.fetch_data(days=120):
            return None
        
        data = self.price_data
        
        # 提取数据
        closes = data['Close'].values
        highs = data['High'].values
        lows = data['Low'].values
        volumes = data['Volume'].values
        
        current_price = closes[-1]
        prev_close = closes[-2] if len(closes) > 1 else current_price
        open_price = data['Open'].iloc[-1]
        high_price = highs[-1]
        low_price = lows[-1]
        volume = volumes[-1]
        
        # 计算均线
        ma5 = self.calculate_ma(closes, 5)
        ma10 = self.calculate_ma(closes, 10)
        ma20 = self.calculate_ma(closes, 20)
        ma60 = self.calculate_ma(closes, 60)
        ma120 = self.calculate_ma(closes, 120)
        ma250 = self.calculate_ma(closes, 250)
        
        # 计算MACD
        macd_dif, macd_dea, macd_histogram = self.calculate_macd(closes)
        
        # MACD信号判断
        if macd_dif > macd_dea and macd_dif > 0:
            macd_signal = 'golden_cross'
        elif macd_dif < macd_dea and macd_dif < 0:
            macd_signal = 'death_cross'
        else:
            macd_signal = 'neutral'
        
        # 计算KDJ
        k, d, j = self.calculate_kdj(highs, lows, closes)
        
        # KDJ信号判断
        if k > 80 and d > 80:
            kdj_signal = 'overbought'
        elif k < 20 and d < 20:
            kdj_signal = 'oversold'
        else:
            kdj_signal = 'neutral'
        
        # 计算RSI
        rsi6 = self.calculate_rsi(closes, 6)
        rsi12 = self.calculate_rsi(closes, 12)
        rsi24 = self.calculate_rsi(closes, 24)
        
        # RSI信号判断
        if rsi6 > 70:
            rsi_signal = 'overbought'
        elif rsi6 < 30:
            rsi_signal = 'oversold'
        else:
            rsi_signal = 'neutral'
        
        # 计算布林带
        boll_upper, boll_middle, boll_lower = self.calculate_bollinger(closes)
        
        # 布林带位置判断
        if current_price > boll_upper:
            boll_position = 'break_upper'
        elif current_price < boll_lower:
            boll_position = 'break_lower'
        elif current_price > boll_middle:
            boll_position = 'upper'
        elif current_price < boll_middle:
            boll_position = 'lower'
        else:
            boll_position = 'middle'
        
        boll_width = (boll_upper - boll_lower) / boll_middle if boll_middle != 0 else 0
        
        # 计算量比
        volume_ratio = self.calculate_volume_ratio(volumes)
        
        # 量比信号
        if volume_ratio > 2:
            volume_signal = 'high'
        elif volume_ratio < 0.8:
            volume_signal = 'low'
        else:
            volume_signal = 'normal'
        
        # 获取融资融券数据
        margin_data = self.fetch_margin_data()
        
        # 获取资金流向
        money_flow = self.fetch_money_flow()
        
        # 趋势分析
        trend = self.analyze_trend(closes, ma5, ma20, ma60)
        
        # 强度分析
        if rsi6 > 50 and macd_histogram > 0 and volume_ratio > 1.5:
            strength = 'strong'
        elif rsi6 < 50 and macd_histogram < 0:
            strength = 'weak'
        else:
            strength = 'medium'
        
        # 支撑位和阻力位
        support, resistance = self.calculate_support_resistance(highs, lows, closes)
        
        return TechnicalIndicators(
            ts_code=self.ts_code,
            current_price=current_price,
            prev_close=prev_close,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            volume=volume,
            ma5=ma5,
            ma10=ma10,
            ma20=ma20,
            ma60=ma60,
            ma120=ma120,
            ma250=ma250,
            macd_dif=macd_dif,
            macd_dea=macd_dea,
            macd_histogram=macd_histogram,
            macd_signal=macd_signal,
            k_value=k,
            d_value=d,
            j_value=j,
            kdj_signal=kdj_signal,
            rsi6=rsi6,
            rsi12=rsi12,
            rsi24=rsi24,
            rsi_signal=rsi_signal,
            boll_upper=boll_upper,
            boll_middle=boll_middle,
            boll_lower=boll_lower,
            boll_position=boll_position,
            boll_width=boll_width,
            volume_ratio=volume_ratio,
            volume_signal=volume_signal,
            main_force_inflow=money_flow['main_force_inflow'],
            retail_inflow=money_flow['retail_inflow'],
            net_inflow=money_flow['net_inflow'],
            margin_balance=margin_data['margin_balance'],
            margin_buy=margin_data['margin_buy'],
            margin_repay=margin_data['margin_repay'],
            short_balance=margin_data['short_balance'],
            trend=trend,
            strength=strength,
            support_level=support,
            resistance_level=resistance,
            fetch_time=datetime.now().isoformat()
        )


def format_analysis_report(indicators: TechnicalIndicators) -> str:
    """格式化分析报告"""
    report = f"""
╔══════════════════════════════════════════════════════════════════╗
║              技术分析报告 - {indicators.ts_code}                     ║
╠══════════════════════════════════════════════════════════════════╣
║ 基本信息                                                         ║
╠──────────────────────────────────────────────────────────────────╣
║ 当前价格: {indicators.current_price:>10.2f}  昨收: {indicators.prev_close:>10.2f}          ║
║ 今开: {indicators.open_price:>10.2f}  最高: {indicators.high_price:>10.2f}  最低: {indicators.low_price:>10.2f}  ║
║ 成交量: {indicators.volume:>10.0f}                                    ║
╠══════════════════════════════════════════════════════════════════╣
║ 均线系统                                                         ║
╠──────────────────────────────────────────────────────────────────╣
║ MA5:  {indicators.ma5:>10.2f}  {'✓' if indicators.current_price > indicators.ma5 else '✗'}          ║
║ MA10: {indicators.ma10:>10.2f}  {'✓' if indicators.current_price > indicators.ma10 else '✗'}          ║
║ MA20: {indicators.ma20:>10.2f}  {'✓' if indicators.current_price > indicators.ma20 else '✗'}          ║
║ MA60: {indicators.ma60:>10.2f}  {'✓' if indicators.current_price > indicators.ma60 else '✗'}          ║
╠══════════════════════════════════════════════════════════════════╣
║ MACD指标                                                         ║
╠──────────────────────────────────────────────────────────────────╣
║ DIF: {indicators.macd_dif:>10.4f}  DEA: {indicators.macd_dea:>10.4f}          ║
║ MACD柱状图: {indicators.macd_histogram:>10.4f}  信号: {indicators.macd_signal:>12}  ║
╠══════════════════════════════════════════════════════════════════╣
║ KDJ指标                                                          ║
╠──────────────────────────────────────────────────────────────────╣
║ K值: {indicators.k_value:>10.2f}  D值: {indicators.d_value:>10.2f}  J值: {indicators.j_value:>10.2f}  ║
║ 信号: {indicators.kdj_signal:>15}                                 ║
╠══════════════════════════════════════════════════════════════════╣
║ RSI指标                                                          ║
╠──────────────────────────────────────────────────────────────────╣
║ RSI6:  {indicators.rsi6:>10.2f}  RSI12: {indicators.rsi12:>10.2f}  RSI24: {indicators.rsi24:>10.2f}  ║
║ 信号: {indicators.rsi_signal:>15}                                 ║
╠══════════════════════════════════════════════════════════════════╣
║ 布林带                                                           ║
╠──────────────────────────────────────────────────────────────────╣
║ 上轨: {indicators.boll_upper:>10.2f}  中轨: {indicators.boll_middle:>10.2f}  下轨: {indicators.boll_lower:>10.2f}  ║
║ 位置: {indicators.boll_position:>15}  宽度: {indicators.boll_width:>10.4f}     ║
╠══════════════════════════════════════════════════════════════════╣
║ 量比分析                                                         ║
╠──────────────────────────────────────────────────────────────────╣
║ 量比: {indicators.volume_ratio:>10.2f}  信号: {indicators.volume_signal:>15}          ║
╠══════════════════════════════════════════════════════════════════╣
║ 综合判断                                                         ║
╠──────────────────────────────────────────────────────────────────╣
║ 趋势: {indicators.trend:>15}  强度: {indicators.strength:>15}          ║
║ 支撑位: {indicators.support_level:>10.2f}  阻力位: {indicators.resistance_level:>10.2f}         ║
╚══════════════════════════════════════════════════════════════════╝
"""
    return report


def main():
    parser = argparse.ArgumentParser(
        description='技术面分析工具 - 全面的股票技术分析',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python technical_analysis.py --ts-code 000988.SZ
    python technical_analysis.py --ts-code 000988.SZ --days 60 --output analysis.json
    python technical_analysis.py --ts-code 000988.SZ --full-analysis --verbose
        """
    )
    
    parser.add_argument('--ts-code', '-t', required=True,
                        help='股票代码，如 000988.SZ')
    parser.add_argument('--days', '-d', type=int, default=120,
                        help='获取历史数据天数 (默认: 120)')
    parser.add_argument('--output', '-o',
                        help='输出JSON文件路径')
    parser.add_argument('--full-analysis', '-f', action='store_true',
                        help='执行完整分析')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='详细输出')
    
    args = parser.parse_args()
    
    logger.info(f"开始分析 {args.ts_code}")
    
    analyzer = TechnicalAnalyzer(args.ts_code)
    
    if args.full_analysis:
        indicators = analyzer.full_analysis()
        
        if indicators is None:
            logger.error("分析失败")
            return 1
        
        # 打印报告
        report = format_analysis_report(indicators)
        print(report)
        
        # 保存到文件
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(indicators), f, ensure_ascii=False, indent=2)
            
            logger.info(f"结果已保存: {output_path}")
    else:
        # 仅获取基础数据
        if not analyzer.fetch_data(days=args.days):
            return 1
        
        data = analyzer.price_data
        print(f"\n{args.ts_code} 最近5日数据:")
        print(data.tail())
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
