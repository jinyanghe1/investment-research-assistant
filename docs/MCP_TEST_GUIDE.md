# MCP 工具测试指南

> 创建时间：2026-04-02
> 更新时间：2026-04-02

---

## 一、概述

### 1.1 测试范围

本文档涵盖以下 MCP 工具的测试指南：

| 工具类型 | 工具名称 | 状态 |
|----------|----------|------|
| 数据获取 | `fetch_index_data.py` | ✅ 已实现 |
| 数据获取 | `fetch_macro_data.py` | ✅ 已实现 |
| 数据获取 | `fetch_stock_daily.py` | ✅ 已实现 |
| 数据获取 | `fetch_futures.py` | ✅ 已实现 |
| 图表生成 | `chart_style.py` | ✅ 已实现 |
| 图表生成 | `chart_generator.py` | ✅ 已实现 |
| 研报自动化 | `init_report.py` | ✅ 已实现 |
| 研报自动化 | `update_index_json.py` | ✅ 已实现 |
| 研报自动化 | `generate_report.py` | 🔄 待实现 |

### 1.2 测试环境要求

```bash
# Python 版本
Python >= 3.8

# 必需依赖
pip install akshare pandas matplotlib seaborn numpy

# 目录结构
投研助手/
├── data/raw/          # 数据输出目录
├── tools/             # 工具脚本
└── docs/              # 文档目录
```

---

## 二、数据获取工具测试

### 2.1 fetch_index_data.py

#### 测试用例

**TC-INDEX-001: 沪深300指数日线获取**

```bash
python tools/fetch_index_data.py --index 000300 --start 20240101 --end 20260402
```

**预期结果**：
- 输出 CSV 文件到 `data/raw/`
- 文件名格式：`{date}_000300_daily.csv`
- 数据包含：日期、开盘、收盘、最高、最低、成交量

**TC-INDEX-002: 创业板指数据获取**

```bash
python tools/fetch_index_data.py --index 399006 --start 20240101 --end 20260402
```

**预期结果**：同 TC-INDEX-001

**TC-INDEX-003: 无效指数代码**

```bash
python tools/fetch_index_data.py --index INVALID --start 20240101 --end 20260402
```

**预期结果**：输出错误信息，不生成文件

**TC-INDEX-004: 日期范围过滤**

```bash
python tools/fetch_index_data.py --index 000300 --start 20240301 --end 20240331
```

**预期结果**：只返回2024年3月的数据

#### 边界条件测试

| 测试用例 | 输入 | 预期结果 |
|----------|------|----------|
| 空日期范围 | `--start 20990101 --end 20991231` | 警告：无数据 |
| 开始日期晚于结束日期 | `--start 20260402 --end 20240101` | 错误提示 |
| 特殊字符代码 | `--index 000300'; DROP TABLE` | 错误处理 |

---

### 2.2 fetch_macro_data.py

#### 测试用例

**TC-MACRO-001: GDP数据获取**

```bash
python scripts/data-pipeline/fetch_macro_data.py --indicator GDP --region CN --output data/raw/
```

**预期结果**：
- 输出 CSV 文件
- 文件名格式：`{date}_GDP_macro.csv`
- 数据来源：国家统计局

**TC-MACRO-002: CPI数据获取**

```bash
python scripts/data-pipeline/fetch_macro_data.py --indicator CPI --region CN --start_date 202401 --end_date 202603
```

**预期结果**：返回2024年1月至2026年3月的CPI数据

**TC-MACRO-003: PPI数据获取**

```bash
python scripts/data-pipeline/fetch_macro_data.py --indicator PPI --output data/raw/
```

**预期结果**：PPI同比/环比数据

**TC-MACRO-004: PMI数据获取**

```bash
python scripts/data-pipeline/fetch_macro_data.py --indicator PMI --output data/raw/
```

**预期结果**：制造业/非制造业PMI

**TC-MACRO-005: M2货币供应量**

```bash
python scripts/data-pipeline/fetch_macro_data.py --indicator M2 --output data/raw/
```

**预期结果**：广义货币供应量数据

**TC-MACRO-006: 社会融资规模**

```bash
python scripts/data-pipeline/fetch_macro_data.py --indicator SOCIAL_FINANCE --output data/raw/
```

**预期结果**：社融增量/存量数据

#### 边界条件测试

| 测试用例 | 输入 | 预期结果 |
|----------|------|----------|
| 无效指标 | `--indicator INVALID` | 错误：不支持的指标 |
| 网络断开 | (断网状态) | 错误：网络请求失败 |
| 数据源维护 | (统计局维护时间) | 警告：数据获取失败 |

---

### 2.3 fetch_stock_daily.py

#### 测试用例

**TC-STOCK-001: 个股日线获取**

```bash
python scripts/data-pipeline/fetch_stock_daily.py --ts_code 000001.SZ --start_date 20240101 --end_date 20260402
```

**预期结果**：
- 输出 CSV 文件
- 文件名格式：`{date}_000001.SZ_日线.csv`

**TC-STOCK-002: 指数数据获取**

```bash
python scripts/data-pipeline/fetch_stock_daily.py --ts_code 000300.SH --start_date 20240101 --end_date 20260402
```

**预期结果**：指数K线数据

**TC-STOCK-003: 中文指数名称**

```bash
python scripts/data-pipeline/fetch_stock_daily.py --ts_code 沪深300 --start_date 20240101 --end_date 20260402
```

**预期结果**：自动转换为 000300.SH

**TC-STOCK-004: 周线数据**

```bash
python scripts/data-pipeline/fetch_stock_daily.py --ts_code 000001.SZ --period weekly --start_date 20240101 --end_date 20260402
```

**预期结果**：周K线数据

**TC-STOCK-005: 月线数据**

```bash
python scripts/data-pipeline/fetch_stock_daily.py --ts_code 000001.SZ --period monthly --start_date 20240101 --end_date 20260402
```

**预期结果**：月K线数据

#### 边界条件测试

| 测试用例 | 输入 | 预期结果 |
|----------|------|----------|
| 无效股票代码 | `--ts_code 999999.SZ` | 错误：股票代码不存在 |
| 停牌股票 | (长期停牌股票) | 警告：数据可能为空 |
| 科创板股票 | `--ts_code 688001.SH` | 正常获取 |

---

### 2.4 fetch_futures.py

#### 测试用例

**TC-FUTURES-001: 国内铜期货**

```bash
python scripts/data-pipeline/fetch_futures.py --symbol CU --exchange SHFE --start_date 20240101 --end_date 20260402
```

**预期结果**：
- 输出 CSV 文件
- 文件名格式：`{date}_SHFE_CU_futures.csv`

**TC-FUTURES-002: 黄金期货**

```bash
python scripts/data-pipeline/fetch_futures.py --symbol AU --exchange SHFE --output data/raw/
```

**预期结果**：黄金主连数据

**TC-FUTURES-003: 国际原油(WTI)**

```bash
python scripts/data-pipeline/fetch_futures.py --symbol CL --exchange CME --output data/raw/
```

**预期结果**：WTI原油期货数据

**TC-FUTURES-004: 布伦特原油**

```bash
python scripts/data-pipeline/fetch_futures.py --symbol BRENT --exchange ICE --output data/raw/
```

**预期结果**：布伦特原油数据

**TC-FUTURES-005: 农产品期货**

```bash
python scripts/data-pipeline/fetch_futures.py --symbol M --exchange DCE --output data/raw/
```

**预期结果**：豆粕期货数据

---

## 三、绘图工具测试

### 3.1 chart_style.py

#### 测试用例

**TC-STYLE-001: 中文字体渲染**

```python
from tools.chart_style import init_ubs_style
import matplotlib.pyplot as plt

init_ubs_style()
fig, ax = plt.subplots()
ax.plot([1, 2, 3], [1, 4, 9])
ax.set_title('中文标题测试')
ax.set_xlabel('X轴标签')
ax.set_ylabel('Y轴标签')
plt.savefig('test_chinese.png')
```

**预期结果**：
- 中文字体正常显示
- 无乱码
- 文件生成成功

**TC-STYLE-002: UBS配色应用**

```python
from tools.chart_style import UBS_COLORS, UBS_BLUE, UBS_RED, UBS_GREEN

print(f"主色: {UBS_BLUE}")      # #003366
print(f"涨: {UBS_RED}")         # #DC2626
print(f"跌: {UBS_GREEN}")       # #16A34A
```

**预期结果**：输出正确颜色值

**TC-STYLE-003: 涨跌颜色函数**

```python
from tools.chart_style import get_up_down_colors

up, down = get_up_down_colors()
print(f"上涨: {up}, 下跌: {down}")
```

**预期结果**：
- 上涨返回红色
- 下跌返回绿色

---

### 3.2 chart_generator.py

#### 测试用例

**TC-CHART-001: 时间序列图生成**

```python
import pandas as pd
import numpy as np
from tools.chart_generator import TimeSeriesChart

# 创建测试数据
dates = pd.date_range('2024-01-01', periods=12, freq='M')
data = pd.DataFrame({
    'date': dates,
    'revenue': np.random.randn(12).cumsum() + 100,
    'profit': np.random.randn(12).cumsum() + 20
})

# 生成图表
chart = TimeSeriesChart(data)
chart.plot('date', ['revenue', 'profit'], 
           '2024年收入利润走势',
           save_path='test_timeseries.png',
           source='测试数据')
```

**预期结果**：
- 生成 PNG 文件
- 中文字体正常
- 图例正确显示

**TC-CHART-002: 分组柱状图**

```python
from tools.chart_generator import BarChart

data = pd.DataFrame({
    'quarter': ['Q1', 'Q2', 'Q3', 'Q4'],
    'revenue': [100, 120, 115, 130],
    'profit': [20, 25, 22, 28]
})

chart = BarChart(data)
chart.plot_grouped('quarter', ['revenue', 'profit'],
                   '2024年季度数据对比',
                   save_path='test_bar.png')
```

**预期结果**：生成对比柱状图

**TC-CHART-003: 堆叠柱状图**

```python
from tools.chart_generator import BarChart

data = pd.DataFrame({
    'quarter': ['Q1', 'Q2', 'Q3', 'Q4'],
    'domestic': [60, 70, 65, 80],
    'overseas': [40, 50, 50, 50]
})

chart = BarChart(data)
chart.plot_stacked('quarter', ['domestic', 'overseas'],
                   '收入结构分析',
                   save_path='test_stacked.png')
```

**预期结果**：生成堆叠柱状图

**TC-CHART-004: 热力图**

```python
import pandas as pd
import numpy as np
from tools.chart_generator import HeatmapChart

# 创建行业表现矩阵
dates = ['2024-Q1', '2024-Q2', '2024-Q3', '2024-Q4']
industries = ['新能源', '半导体', '医药', '消费', '金融']
data = pd.DataFrame(np.random.randn(5, 4) * 10,
                    index=industries, columns=dates)

chart = HeatmapChart(data)
chart.plot(title='行业季度表现热力图(%)',
           save_path='test_heatmap.png')
```

**预期结果**：生成行业轮动热力图

---

## 四、研报自动化工具测试

### 4.1 init_report.py

#### 测试用例

**TC-INIT-001: 研报项目初始化**

```bash
python tools/init_report.py --name "新能源汽车2026Q1分析"
```

**预期结果**：
- 创建目录 `reports/新能源汽车2026Q1分析/`
- 目录包含 `index.html`
- HTML基于模板生成

**TC-INIT-002: 指定输出路径**

```bash
python tools/init_report.py --name "测试研报" --output custom/path/
```

**预期结果**：在指定路径创建研报目录

---

### 4.2 update_index_json.py

#### 测试用例

**TC-UPDATE-001: 添加新研报到索引**

```bash
python tools/update_index_json.py \
    --id RPT-202604-001 \
    --title "2026年一季度新能源汽车产业链分析" \
    --author "投研AI中枢" \
    --category "微观" \
    --tags "新能源,产业链,产能利用率" \
    --file_path "reports/新能源2026Q1/index.html"
```

**预期结果**：
- `index.json` 中添加新条目
- ID唯一，无重复

**TC-UPDATE-002: 自动ID生成**

```bash
python tools/update_index_json.py \
    --title "测试研报" \
    --author "测试" \
    --category "宏观" \
    --file_path "reports/test/index.html"
```

**预期结果**：自动生成 `RPT-YYYYMM-NNN` 格式ID

**TC-UPDATE-003: 去重测试**

```bash
# 连续两次添加相同标题
python tools/update_index_json.py --title "重复标题" ...
python tools/update_index_json.py --title "重复标题" ...
```

**预期结果**：第二次添加被拒绝或更新而非重复添加

---

## 五、集成测试

### 5.1 数据获取 → 图表生成 → 研报嵌入

```bash
# Step 1: 获取数据
python scripts/data-pipeline/fetch_stock_daily.py \
    --ts_code 000300.SH \
    --start_date 20240101 \
    --end_date 20260402 \
    --output data/raw/

# Step 2: 生成图表
python -c "
import pandas as pd
from tools.chart_generator import TimeSeriesChart

data = pd.read_csv('data/raw/20260402_000300.SH_日线.csv')
chart = TimeSeriesChart(data)
chart.plot('date', ['close'], '沪深300走势')
"

# Step 3: 嵌入研报 HTML
# (手动将图表插入研报模板)
```

### 5.2 批量数据获取测试

```bash
# 创建批量获取脚本
cat > test_batch_fetch.sh << 'EOF'
#!/bin/bash

# 批量获取多个指数
for index in 000300.SH 399006.SZ 000001.SH; do
    echo "获取 $index..."
    python scripts/data-pipeline/fetch_stock_daily.py \
        --ts_code $index \
        --start_date 20240101 \
        --end_date 20260402
done

# 批量获取宏观数据
for indicator in GDP CPI PPI PMI; do
    echo "获取 $indicator..."
    python scripts/data-pipeline/fetch_macro_data.py \
        --indicator $indicator
done

echo "批量获取完成!"
EOF

chmod +x test_batch_fetch.sh
./test_batch_fetch.sh
```

---

## 六、测试执行清单

### 每日构建测试

```bash
# 数据获取工具
python scripts/data-pipeline/fetch_stock_daily.py --ts_code 000300.SH --start_date 20260401 --end_date 20260402
python scripts/data-pipeline/fetch_macro_data.py --indicator CPI

# 检查输出
ls -la data/raw/
```

### 每周完整测试

```bash
# 运行所有测试脚本
find . -name "test_*.py" -o -name "*_test.py" | xargs python

# 生成测试报告
pytest tests/ -v --html=report.html
```

### 发布前验收测试

- [ ] 所有 `--help` 参数正常
- [ ] 数据获取成功生成 CSV
- [ ] 图表生成中文无乱码
- [ ] index.json 更新正常
- [ ] 错误处理正确
- [ ] 目录自动创建成功

---

## 七、CI/CD 集成

### GitHub Actions 示例

```yaml
name: MCP Tools Test

on:
  push:
    paths:
      - 'tools/**'
      - 'scripts/**'
  pull_request:
    paths:
      - 'tools/**'
      - 'scripts/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install akshare pandas matplotlib seaborn numpy pytest
      - name: Run data fetch tests
        run: |
          python tools/fetch_index_data.py --help
          python scripts/data-pipeline/fetch_macro_data.py --help
      - name: Run chart tests
        run: |
          python tools/chart_style.py
          python tools/chart_generator.py
```

---

## 八、已知问题和限制

| 问题 | 描述 | 解决方案 |
|------|------|----------|
| AKShare频率限制 | 频繁调用可能触发限制 | 添加延时或缓存 |
| 中文字体缺失 | 部分Linux环境可能缺失 | 安装字体或使用英文 |
| 网络超时 | 数据源不稳定时超时 | 增加重试机制 |
| 期货数据不完整 | 部分品种数据缺失 | 手动补充或使用替代源 |

---

## 九、联系方式

如发现测试问题或有任何疑问，请通过以下方式联系：

- 提交 Issue: GitHub Issues
- 邮件: [待定]
