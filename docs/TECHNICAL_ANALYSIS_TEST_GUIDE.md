# 技术面分析工具测试指南

> 版本：v1.0  
> 创建日期：2026-04-02  
> 适用范围：technical_analysis.py / technical_analysis_enhanced.py

---

## 一、测试概述

### 1.1 测试目标

验证技术面分析工具的准确性、稳定性和数据完整性，确保技术指标计算正确，融资融券和资金流向数据获取正常。

### 1.2 测试范围

| 模块 | 测试内容 | 优先级 |
|------|----------|--------|
| 基础技术指标 | MA, MACD, KDJ, RSI, BOLL | P0 |
| 量比计算 | 成交量比率 | P0 |
| 融资融券 | 融资余额、融券数据 | P1 |
| 资金流向 | 主力/散户净流入 | P1 |
| 形态识别 | 头肩顶/底、双顶/底 | P2 |
| 综合评分 | 技术面评分算法 | P1 |

---

## 二、测试用例

### 2.1 基础技术指标测试

```python
# test_technical_indicators.py

import unittest
import numpy as np
from technical_analysis import TechnicalAnalyzer

class TestTechnicalIndicators(unittest.TestCase):
    
    def setUp(self):
        self.analyzer = TechnicalAnalyzer('000988.SZ')
        # 模拟价格数据
        self.closes = np.array([100, 102, 101, 103, 105, 104, 106, 108, 107, 109])
        self.highs = np.array([101, 103, 102, 104, 106, 105, 107, 109, 108, 110])
        self.lows = np.array([99, 101, 100, 102, 104, 103, 105, 107, 106, 108])
        self.volumes = np.array([10000, 12000, 11000, 13000, 15000, 14000, 16000, 18000, 17000, 19000])
    
    def test_ma_calculation(self):
        """测试移动平均线计算"""
        ma5 = self.analyzer.calculate_ma(self.closes, 5)
        expected = np.mean(self.closes[-5:])  # [104, 106, 108, 107, 109]
        self.assertAlmostEqual(ma5, expected, places=2)
    
    def test_macd_calculation(self):
        """测试MACD计算"""
        # 使用更长的数据
        closes = np.random.randn(100).cumsum() + 100
        dif, dea, hist = self.analyzer.calculate_macd(closes)
        
        # 验证DIF和DEA的关系
        self.assertIsInstance(dif, float)
        self.assertIsInstance(dea, float)
        self.assertAlmostEqual(hist, (dif - dea) * 2, places=5)
    
    def test_kdj_calculation(self):
        """测试KDJ计算"""
        k, d, j = self.analyzer.calculate_kdj(self.highs, self.lows, self.closes)
        
        # K、D应在0-100之间
        self.assertGreaterEqual(k, 0)
        self.assertLessEqual(k, 100)
        self.assertGreaterEqual(d, 0)
        self.assertLessEqual(d, 100)
        
        # J = 3K - 2D
        self.assertAlmostEqual(j, 3*k - 2*d, places=5)
    
    def test_rsi_calculation(self):
        """测试RSI计算"""
        rsi = self.analyzer.calculate_rsi(self.closes, period=6)
        
        # RSI应在0-100之间
        self.assertGreaterEqual(rsi, 0)
        self.assertLessEqual(rsi, 100)
    
    def test_bollinger_calculation(self):
        """测试布林带计算"""
        upper, middle, lower = self.analyzer.calculate_bollinger(self.closes)
        
        # 上轨 > 中轨 > 下轨
        self.assertGreater(upper, middle)
        self.assertGreater(middle, lower)
    
    def test_volume_ratio(self):
        """测试量比计算"""
        ratio = self.analyzer.calculate_volume_ratio(self.volumes, period=5)
        
        # 量比应大于0
        self.assertGreater(ratio, 0)
        
        # 验证计算逻辑
        current = self.volumes[-1]
        avg = np.mean(self.volumes[-6:-1])  # 前5日平均
        expected = current / avg
        self.assertAlmostEqual(ratio, expected, places=5)
```

### 2.2 数据获取测试

```python
# test_data_fetch.py

import unittest
from technical_analysis_enhanced import EnhancedTechnicalAnalyzer

class TestDataFetch(unittest.TestCase):
    
    def setUp(self):
        self.analyzer = EnhancedTechnicalAnalyzer('000988.SZ')
    
    def test_price_data_fetch(self):
        """测试价格数据获取"""
        result = self.analyzer.fetch_price_data(days=30)
        self.assertTrue(result)
        self.assertIsNotNone(self.analyzer.price_data)
        self.assertGreater(len(self.analyzer.price_data), 20)
    
    def test_margin_data_fetch(self):
        """测试融资融券数据获取"""
        margin_data = self.analyzer.fetch_margin_data()
        
        if margin_data:  # 可能无数据
            self.assertGreaterEqual(margin_data.margin_balance, 0)
            self.assertIsNotNone(margin_data.trade_date)
    
    def test_money_flow_fetch(self):
        """测试资金流向数据获取"""
        money_flow = self.analyzer.fetch_money_flow()
        
        if money_flow:
            # 主力 + 散户 = 总流入（近似）
            total = money_flow.main_inflow + money_flow.retail_inflow
            self.assertAlmostEqual(total, money_flow.net_inflow, delta=1)
```

### 2.3 形态识别测试

```python
# test_pattern_recognition.py

import unittest
import numpy as np
from technical_analysis_enhanced import EnhancedTechnicalAnalyzer

class TestPatternRecognition(unittest.TestCase):
    
    def setUp(self):
        self.analyzer = EnhancedTechnicalAnalyzer('000988.SZ')
    
    def test_head_shoulder_pattern(self):
        """测试头肩顶形态识别"""
        # 构造头肩顶形态数据
        highs = np.array([100, 102, 105, 103, 108, 104, 102, 100, 98])
        lows = np.array([95, 97, 100, 98, 102, 99, 97, 95, 93])
        closes = np.array([98, 100, 103, 101, 106, 102, 99, 97, 95])
        
        pattern = self.analyzer._detect_head_shoulder(closes, highs, lows)
        
        if pattern:
            self.assertEqual(pattern.pattern_name, "头肩顶")
            self.assertEqual(pattern.pattern_type, "reversal")
    
    def test_double_top_pattern(self):
        """测试双顶形态识别"""
        # 构造双顶形态
        highs = np.array([100, 105, 102, 108, 104, 107, 103, 100, 98])
        lows = np.array([95, 98, 96, 100, 98, 101, 98, 95, 93])
        closes = np.array([98, 103, 99, 106, 101, 105, 100, 97, 95])
        
        pattern = self.analyzer._detect_double_top_bottom(closes, highs, lows)
        
        if pattern:
            self.assertIn(pattern.pattern_name, ["双顶", "双底"])
```

---

## 三、性能测试

### 3.1 响应时间测试

```python
# test_performance.py

import unittest
import time
from technical_analysis import TechnicalAnalyzer
from technical_analysis_enhanced import EnhancedTechnicalAnalyzer

class TestPerformance(unittest.TestCase):
    
    def test_basic_analysis_speed(self):
        """测试基础分析速度"""
        analyzer = TechnicalAnalyzer('000988.SZ')
        
        start = time.time()
        result = analyzer.full_analysis()
        elapsed = time.time() - start
        
        self.assertIsNotNone(result)
        self.assertLess(elapsed, 10)  # 应在10秒内完成
    
    def test_enhanced_analysis_speed(self):
        """测试增强版分析速度"""
        analyzer = EnhancedTechnicalAnalyzer('000988.SZ')
        
        start = time.time()
        result = analyzer.full_analysis()
        elapsed = time.time() - start
        
        self.assertIsNotNone(result)
        self.assertLess(elapsed, 15)  # 应在15秒内完成
```

---

## 四、边界条件测试

| 测试场景 | 预期结果 |
|----------|----------|
| 新股（数据少于20天） | 返回部分指标，无错误 |
| 停牌股票 | 返回空数据，给出提示 |
| 退市股票 | 返回错误，建议检查代码 |
| 数据缺失 | 使用可用数据计算，标记缺失 |
| 极值数据 | 正常处理，不溢出 |

---

## 五、运行测试

```bash
# 运行所有测试
python -m pytest tests/test_technical_analysis.py -v

# 运行特定测试
python -m pytest tests/test_technical_analysis.py::TestTechnicalIndicators::test_ma_calculation -v

# 生成覆盖率报告
python -m pytest tests/test_technical_analysis.py --cov=technical_analysis --cov-report=html

# 性能测试
python -m pytest tests/test_performance.py -v
```

---

## 六、验证清单

发布前必须通过的测试：

- [ ] MA计算正确性
- [ ] MACD计算正确性
- [ ] KDJ计算正确性
- [ ] RSI计算正确性
- [ ] 布林带计算正确性
- [ ] 量比计算正确性
- [ ] 数据获取成功
- [ ] 融资融券数据解析正确
- [ ] 资金流向数据解析正确
- [ ] 响应时间 < 15秒
- [ ] 异常处理正确

---

**注意**：所有测试必须在真实数据源上运行，确保计算结果与市场软件一致。
