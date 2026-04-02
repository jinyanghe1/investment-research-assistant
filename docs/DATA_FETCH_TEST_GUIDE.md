# 数据获取脚本测试指南

> 版本：v1.0  
> 创建日期：2026-04-02  
> 适用范围：所有金融数据获取MCP脚本

---

## 一、测试原则

### 1.1 为什么需要严格测试

金融数据的准确性直接影响投资决策。华工科技研报中出现的**股价数据失真**（实际100元 vs 错误41.82元）和**财报数据滞后**问题，根本原因是缺乏严格的测试验证。

### 1.2 测试目标

| 测试类型 | 目标 | 关键指标 |
|----------|------|----------|
| **准确性测试** | 数据与权威来源一致 | 错误率 < 0.1% |
| **时效性测试** | 数据为最新可用 | 延迟 < 1个交易日 |
| **完整性测试** | 所有字段成功获取 | 缺失率 < 1% |
| **稳定性测试** | API持续可用 | 成功率 > 95% |

---

## 二、测试用例模板

### 2.1 股价数据获取测试

#### 测试对象
- 脚本：`tools/fetch_stock_data.py`
- 函数：`get_stock_price(ts_code: str) -> dict`

#### 测试用例

```python
# test_fetch_stock_price.py

import unittest
from fetch_stock_data import get_stock_price

class TestStockPriceFetch(unittest.TestCase):
    
    # ========== 基础功能测试 ==========
    
    def test_hgtech_price_accuracy(self):
        """华工科技股价准确性测试 - P0级"""
        result = get_stock_price('000988.SZ')
        
        # 验证数据存在
        self.assertIn('current_price', result)
        self.assertIn('market_cap', result)
        
        # 验证股价合理性 (A股一般 1-1000元)
        price = result['current_price']
        self.assertGreater(price, 1, "股价低于1元，可能存在错误")
        self.assertLess(price, 1000, "股价超过1000元，可能存在错误")
        
        # 验证市值合理性 (华工科技应在 300-600亿)
        market_cap = result['market_cap']
        self.assertGreater(market_cap, 300, "市值低于300亿，可能数据错误")
        self.assertLess(market_cap, 600, "市值超过600亿，可能数据错误")
        
        # 交叉验证：市值 = 股价 × 总股本
        shares = result.get('total_shares', 0)
        if shares > 0:
            calculated_cap = price * shares / 1e8  # 转换为亿元
            self.assertAlmostEqual(
                market_cap, calculated_cap, 
                delta=market_cap * 0.05,  # 允许5%误差
                msg="市值与股价×股本不匹配"
            )
    
    def test_zhongji_innolight_comparison(self):
        """中际旭创对比测试 - 验证相对估值合理性"""
        hgtech = get_stock_price('000988.SZ')
        zhongji = get_stock_price('300308.SZ')
        
        # 中际旭创市值应大于华工科技
        self.assertGreater(
            zhongji['market_cap'], 
            hgtech['market_cap'],
            "中际旭创市值应大于华工科技"
        )
    
    # ========== 边界条件测试 ==========
    
    def test_invalid_code(self):
        """无效代码处理测试"""
        result = get_stock_price('INVALID.CODE')
        self.assertIn('error', result)
        self.assertIsNone(result.get('current_price'))
    
    def test_suspended_stock(self):
        """停牌股票处理测试"""
        # 假设000001.XSHE为停牌股票
        result = get_stock_price('000001.XSHE')
        # 应返回特殊标记而非错误
        self.assertIn('status', result)
    
    # ========== 数据源对比测试 ==========
    
    def test_multi_source_consistency(self):
        """多数据源一致性测试"""
        from_yfinance = get_stock_price('000988.SZ', source='yfinance')
        from_akshare = get_stock_price('000988.SZ', source='akshare')
        
        # 两个数据源的价格差异应小于2%
        diff = abs(from_yfinance['current_price'] - from_akshare['current_price'])
        avg = (from_yfinance['current_price'] + from_akshare['current_price']) / 2
        self.assertLess(diff / avg, 0.02, "数据源差异超过2%")
```

#### 运行测试

```bash
# 运行所有测试
python -m pytest test_fetch_stock_price.py -v

# 运行特定测试
python -m pytest test_fetch_stock_price.py::TestStockPriceFetch::test_hgtech_price_accuracy -v

# 生成测试报告
python -m pytest test_fetch_stock_price.py --html=report.html
```

---

### 2.2 财务数据获取测试

#### 测试对象
- 脚本：`tools/fetch_financial_data.py`
- 函数：`get_financial_data(ts_code: str) -> dict`

#### 测试用例

```python
# test_fetch_financial_data.py

import unittest
from datetime import datetime
from fetch_financial_data import get_financial_data

class TestFinancialDataFetch(unittest.TestCase):
    
    def test_latest_report_date(self):
        """最新财报日期检查 - P0级"""
        result = get_financial_data('000988.SZ')
        
        # 获取最新财报日期
        latest_date = result.get('latest_report_date')
        self.assertIsNotNone(latest_date, "未获取到财报日期")
        
        # 转换为日期对象
        report_date = datetime.strptime(latest_date, '%Y-%m-%d')
        today = datetime.now()
        
        # 财报不应超过90天（假设季度报告周期）
        days_diff = (today - report_date).days
        self.assertLess(
            days_diff, 90,
            f"财报数据滞后{days_diff}天，可能使用了过期数据"
        )
    
    def test_revenue_consistency(self):
        """营收数据一致性检查"""
        result = get_financial_data('000988.SZ')
        
        revenue = result.get('total_revenue')
        net_profit = result.get('net_profit')
        
        # 营收应为正值
        self.assertGreater(revenue, 0, "营收应为正值")
        
        # 净利润应小于营收
        self.assertLess(
            abs(net_profit), revenue,
            "净利润绝对值不应超过营收"
        )
        
        # 净利率应在合理范围 (-50% ~ 50%)
        margin = net_profit / revenue
        self.assertGreater(margin, -0.5, "净利率低于-50%，可能数据错误")
        self.assertLess(margin, 0.5, "净利率超过50%，可能数据错误")
    
    def test_quarterly_vs_annual(self):
        """季报与年报一致性检查"""
        data = get_financial_data('000988.SZ')
        
        # Q4营收应约等于年报营收
        q4_revenue = data.get('quarterly', {}).get('Q4', {}).get('revenue', 0)
        annual_revenue = data.get('annual', {}).get('revenue', 0)
        
        if q4_revenue > 0 and annual_revenue > 0:
            self.assertAlmostEqual(
                q4_revenue, annual_revenue,
                delta=annual_revenue * 0.1,  # 允许10%差异
                msg="Q4营收与年报营收差异过大"
            )
    
    def test_year_over_year_growth(self):
        """同比增长合理性检查"""
        data = get_financial_data('000988.SZ')
        
        revenue_growth = data.get('revenue_growth_yoy')
        
        # 增长率应在合理范围 (-80% ~ +200%)
        if revenue_growth is not None:
            self.assertGreater(revenue_growth, -0.8, "营收下降超过80%，需核实")
            self.assertLess(revenue_growth, 2.0, "营收增长超过200%，需核实")
```

---

## 三、数据验证中间件

### 3.1 使用方式

```python
from data_validator import DataValidator

# 验证股价数据
validator = DataValidator()
price_data = get_stock_price('000988.SZ')

is_valid, errors = validator.validate_stock_price(price_data)
if not is_valid:
    print(f"数据验证失败: {errors}")
    # 使用备用数据源或报错
```

### 3.2 验证规则清单

| 数据类型 | 验证规则 | 错误处理 |
|----------|----------|----------|
| **股价** | 1-1000元 | 标记异常，切换数据源 |
| **市值** | 与股价×股本匹配 | 记录日志，人工核查 |
| **PE** | -100 ~ 200 | 负PE标记为亏损，超高PE核查 |
| **营收** | > 0 | 报错，数据不可用 |
| **净利润** | < 营收 | 报错，数据矛盾 |
| **财报日期** | < 90天 | 标记为过期数据 |

---

## 四、测试执行清单

### 4.1 每次代码修改后必测

- [ ] 基础功能测试（股价/财务数据可获取）
- [ ] 华工科技股价准确性验证（与东方财富对比）
- [ ] 中际旭创股价合理性验证
- [ ] 最新财报日期检查

### 4.2 每周定期测试

- [ ] 全部A股指数成分股抽样测试（10只）
- [ ] 多数据源一致性对比
- [ ] API稳定性统计（成功率）

### 4.3 每月全面测试

- [ ] 全量股票代码测试
- [ ] 边界条件测试
- [ ] 性能测试（响应时间）

---

## 五、问题记录与修复

### 5.1 已知问题

| 问题ID | 描述 | 影响 | 状态 | 修复方案 |
|--------|------|------|------|----------|
| DATA-001 | 华工科技股价41.82元（实际100元） | 研报估值错误 | 🔴 待修复 | 强制使用yfinance |
| DATA-002 | 2025年数据使用estimate | 分析过时 | 🔴 待修复 | 添加财报日期检查 |
| DATA-003 | 无数据验证中间件 | 错误数据流入 | 🔴 待修复 | 创建data_validator.py |

### 5.2 修复验证流程

```
发现问题 → 编写测试用例（复现问题） → 修复代码 → 测试通过 → 更新文档
```

---

## 六、附录：测试工具

### 6.1 快速验证脚本

```bash
# 验证股价准确性
python tools/verify_stock_price.py --code 000988.SZ --expected 100

# 验证财报日期
python tools/verify_report_date.py --code 000988.SZ --max-days 90
```

### 6.2 参考数据源

| 数据源 | 用途 | 验证方式 |
|--------|------|----------|
| 东方财富 | 股价验证 | 网页对比 |
| 巨潮资讯 | 财报验证 | 官方公告 |
| yfinance | 主要数据源 | API直接获取 |
| AKShare | 备用数据源 | API直接获取 |

---

**注意**：所有数据获取脚本在部署前必须通过本指南的全部测试用例。
