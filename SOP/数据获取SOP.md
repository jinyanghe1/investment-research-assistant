# 数据获取标准作业程序 (SOP)

> 版本：v1.0  
> 创建日期：2026-04-02  
> 适用范围：所有金融数据获取任务

---

## 一、目的

本SOP旨在规范金融数据获取流程，确保数据的**准确性**、**时效性**和**完整性**，避免华工科技研报中出现的股价失真（100元 vs 错误41.82元）和数据滞后问题。

---

## 二、数据源优先级（强制执行）

### 2.1 股价数据

| 优先级 | 数据源 | 调用方式 | 使用条件 |
|--------|--------|----------|----------|
| **P0** | yfinance | `yf.Ticker('000988.SZ')` | **强制首选** |
| P1 | AKShare | `ak.stock_zh_a_spot()` | yfinance失败时 |
| ❌ | 网上搜索 | WebSearch | **禁止使用** |

**为什么禁用网上搜索股价？**
- 网页数据可能过时（缓存问题）
- 难以验证数据来源和时间
- 可能导致股价严重失真（如华工科技41.82元 vs 实际100元）

### 2.2 财务数据

| 优先级 | 数据源 | 调用方式 |
|--------|--------|----------|
| **P0** | yfinance | `ticker.financials` / `ticker.quarterly_financials` |
| P1 | 巨潮资讯 | 官方公告 |
| P2 | AKShare | `ak.stock_financial_report_sina()` |

### 2.3 宏观数据

| 优先级 | 数据源 | 用途 |
|--------|--------|------|
| P0 | 国家统计局 | GDP/CPI/PPI/PMI |
| P1 | AKShare | 封装的国家统计局数据 |
| P2 | FRED API | 美联储数据（美股相关） |

---

## 三、数据获取流程

### 3.1 标准流程图

```
开始
  │
  ▼
确定数据需求（股价/财务/宏观）
  │
  ▼
选择数据源（按优先级）
  │
  ▼
调用API获取数据
  │
  ▼
数据验证（强制环节）
  │  ├─ 通过 → 继续
  │  └─ 失败 → 切换备用源
  │
  ▼
记录数据来源和时间戳
  │
  ▼
保存数据
  │
  ▼
结束
```

### 3.2 代码模板

```python
import yfinance as yf
from tools.data_validator import DataValidator

def fetch_stock_data(ts_code: str) -> dict:
    """获取股票数据（标准模板）"""
    
    # 1. 强制使用yfinance
    ticker = yf.Ticker(ts_code)
    info = ticker.info
    
    # 2. 提取数据
    data = {
        'ts_code': ts_code,
        'current_price': info.get('currentPrice'),
        'market_cap': info.get('marketCap'),
        # ... 其他字段
        'fetch_time': datetime.now().isoformat(),
        'data_source': 'yfinance'  # 必须记录数据源
    }
    
    # 3. 强制数据验证
    validator = DataValidator()
    is_valid, errors = validator.validate_stock_price(data)
    
    if not is_valid:
        raise ValueError(f"数据验证失败: {errors}")
    
    return data
```

---

## 四、数据验证检查点

### 4.1 股价数据验证

```python
# 使用 data_validator.py 自动验证

from tools.data_validator import DataValidator

validator = DataValidator()
is_valid, errors = validator.validate_stock_price(price_data)

# 验证内容：
# ✅ 股价在 1-1000元 范围内
# ✅ 市值与股价×股本匹配（误差<10%）
# ✅ PE在 -100 ~ 200 范围内
# ✅ 股票代码格式正确
```

### 4.2 财务数据验证

```python
# 验证内容：
# ✅ 营收为正数
# ✅ 净利润绝对值 < 营收 × 2
# ✅ 净利率在 -50% ~ 50% 范围内
# ✅ 财报日期在 90天 内
# ✅ 同比增长率在合理范围
```

### 4.3 人工复核清单

获取数据后，必须进行以下检查：

| 检查项 | 方法 | 通过标准 |
|--------|------|----------|
| 股价合理性 | 与东方财富对比 | 差异 < 5% |
| 市值合理性 | 与股价×股本对比 | 差异 < 10% |
| 财报新鲜度 | 检查report_date | < 90天 |
| 同业对比 | 与可比公司对比 | 相对关系合理 |

---

## 五、常见问题与修复

### 5.1 问题记录

| 问题ID | 描述 | 根因 | 修复方案 |
|--------|------|------|----------|
| DATA-001 | 华工科技股价41.82元（实际100元） | 使用WebSearch获取股价 | 强制使用yfinance |
| DATA-002 | 2025年数据使用estimate | 未检查财报发布日期 | 添加财报日期验证 |
| DATA-003 | 无数据验证环节 | 缺少验证中间件 | 使用data_validator.py |

### 5.2 快速修复指南

**场景1：股价数据异常**
```python
# 错误做法（可能导致数据失真）
price = search_web(f"{stock_name} 最新股价")  # ❌ 禁止

# 正确做法
import yfinance as yf
price = yf.Ticker(ts_code).info['currentPrice']  # ✅ 强制
```

**场景2：财报数据滞后**
```python
# 检查财报日期
report_date = data.get('report_date')
if report_date:
    days_diff = (datetime.now() - datetime.strptime(report_date, '%Y-%m-%d')).days
    if days_diff > 90:
        logger.warning(f"财报数据滞后{days_diff}天")
```

---

## 六、工具使用指南

### 6.1 数据验证工具

```bash
# 验证股价数据
python tools/data_validator.py --type price --data '{"current_price": 100, "market_cap": 500}'

# 验证财务数据
python tools/data_validator.py --type financial --file financial_data.json
```

### 6.2 数据获取工具

```bash
# 获取个股数据（自动验证）
python tools/fetch_stock_data.py --ts-code 000988.SZ --verify --verbose

# 获取并对比
python tools/fetch_stock_data.py --ts-code 000988.SZ --compare 300308.SZ --verify
```

### 6.3 批量验证

```python
# 批量验证多只股票
from tools.data_validator import DataValidator

validator = DataValidator()
codes = ['000988.SZ', '300308.SZ', '002281.SZ']

for code in codes:
    data = fetch_stock_data(code)
    is_valid, errors = validator.validate_stock_price(data)
    if not is_valid:
        print(f"{code}: 验证失败 - {errors}")
```

---

## 七、测试要求

### 7.1 每次修改后必测

```bash
# 基础功能测试
python -m pytest tests/test_fetch_stock_data.py -v

# 华工科技股价准确性验证
python tools/fetch_stock_data.py --ts-code 000988.SZ --verify

# 中际旭创对比验证
python tools/fetch_stock_data.py --ts-code 300308.SZ --verify
```

### 7.2 测试文档

详细测试用例见：`docs/DATA_FETCH_TEST_GUIDE.md`

---

## 八、责任与检查

### 8.1 数据获取Agent责任

- [ ] 强制使用yfinance获取股价
- [ ] 调用数据验证中间件
- [ ] 记录数据来源和时间戳
- [ ] 处理验证失败情况

### 8.2 Hub Agent核查

- [ ] 检查数据是否经过验证
- [ ] 验证财报日期新鲜度
- [ ] 抽查股价与公开数据一致性
- [ ] 确认数据来源标记

---

## 九、附录

### 9.1 股票代码格式

| 市场 | 格式示例 | 说明 |
|------|----------|------|
| 深交所 | `000988.SZ` | yfinance标准格式 |
| 上交所 | `688981.SS` 或 `688981.SH` | yfinance格式 |
| 港股 | `0988.HK` | yfinance格式 |
| 美股 | `AAPL` | yfinance格式 |

### 9.2 参考链接

- [yfinance文档](https://pypi.org/project/yfinance/)
- [AKShare文档](https://www.akshare.xyz/)
- [东方财富](https://www.eastmoney.com/)（验证用）

---

**注意**：违反本SOP导致的数据质量问题，将被记录在.agentstalk/ROADMAP.md中并优先修复。
