# 投研助手路线图 v1.1

> 创建时间：2026-04-02
> 更新日期：2026-04-02
> 更新说明：添加P0级数据质量问题修复项

---

## 一、核心需求与实现路径

### 1.1 可靠的新闻来源（实时数据）

#### 数据源清单

| 来源 | 类型 | 优先级 | 获取方式 |
|------|------|--------|----------|
| **财新** | 中文财经深度 | P0 | WebSearch |
| **华尔街见闻** | 实时全球财经 | P0 | WebSearch |
| **雪球** | 投资者社区 | P1 | WebSearch |
| **东方财富/同花顺** | 行情+资讯 | P1 | 已有API |
| **FT / Bloomberg / Reuters** | 英文权威媒体 | P1 | WebSearch |
| **国家统计局** | 官方宏观数据 | P0 | AKShare封装 |
| **国务院/证监会/央行** | 政策文件 | P0 | WebSearch |

#### 关键词搜索策略

```
# 宏观政策
"中国经济" OR "GDP" site:gov.cn
"证监会" OR "银保监" filetype:pdf

# 行业公司
"行业研究" OR "研报" filetype:pdf
"公司名称" AND ("业绩" OR "财报" OR "营收")
```

---

### 1.2 实时金融数据

#### 数据源优先级

| 优先级 | 数据类型 | 推荐来源 | 备注 |
|--------|----------|----------|------|
| **P0** | A股指数/日线 | yfinance (primary) / AKShare (fallback) | 免费 |
| **P0** | 个股K线/财务 | yfinance (primary) / Tushare (fallback) | 需注册 |
| **P1** | 宏观指标 | AKShare（国家统计局封装）/ FRED API | 免费 |
| **P1** | 期货/大宗商品 | AKShare + yfinance | 免费 |
| **P2** | 行业数据 | 协会官网/乘联会/奥维云网 | 部分付费 |
| **P2** | 港股 | Yahoo Finance (yfinance) | 免费 |
| **P3** | 美股 | yfinance | 免费 |

> ⚠️ **重要**：yfinance为A股数据源首选（000988.SZ格式），避免使用网上搜索的过时股价数据

#### 推荐Python依赖

```
tushare>=1.4.0        # A股/财务数据（需注册获取Token）
akshare>=1.13.0       # 全市场免费数据（fallback）
yfinance>=0.2.40      # 国际市场行情（A股首选）
pandas>=2.0.0         # 数据处理
requests>=2.31.0       # HTTP请求
fredapi>=0.5.0        # FRED宏观数据（需免费API Key）
```

#### 数据存储规范

```
data/
├── raw/                    # 原始数据（不可修改）
│   ├── 2026-04-02_沪深300日线.csv
│   ├── 2026-04-02_宏观CPI.csv
│   └── 2026-04-02_铜期货主连.csv
├── cleaned/                # 清洗后数据
│   └── *.csv
└── processed/              # 分析用中间数据
    └── *.csv
```

---

### 1.3 投研方法论

#### 宏观分析框架

| 框架 | 用途 | 核心指标 |
|------|------|----------|
| **美林投资时钟** | 大类资产轮动 | CPI、GDP、PMI |
| **信贷周期** | 股市领先信号 | 社融、M2、信用利差 |
| **通胀/利率框架** | 政策环境判断 | PPI、LPR、实际利率 |
| **政策周期追踪** | 政策拐点识别 | 两会、央行表态、专项债 |

#### 行业中观框架

| 框架 | 用途 | 关键问题 |
|------|------|----------|
| **波特五力** | 行业吸引力评估 | 护城河有多宽？ |
| **微笑曲线** | 产业链价值分布 | 哪个环节在变强？ |
| **竞争格局四阶段** | 行业生命周期 | 产能出清到哪了？ |
| **产能/库存周期** | 景气度判断 | 补库还是去库？ |

#### 公司微观框架

| 框架 | 用途 | 核心指标 |
|------|------|----------|
| **杜邦分析** | ROE拆解 | 净利率×周转率×杠杆 |
| **DCF估值** | 绝对估值 | FCFF、WACC、永续增长 |
| **PE/PEG估值** | 相对估值 | 历史分位、增速匹配 |
| **管理层评估** | 治理风险 | 股权激励、大股东增减持 |

#### 三层验证模型

```
宏观层 (Beta) → 行业中观 (轮动) → 公司微观 (Alpha)
     ↓                ↓               ↓
美林时钟/信贷     五力/产能周期     财务/估值/治理
     ↓                ↓               ↓
   资产配置         行业选择         个股筛选
```

---

### 1.4 UBS风格绘图

#### 配色方案

| 用途 | 颜色 | Hex |
|------|------|-----|
| 主色调 | UBS蓝 | `#003366` |
| 辅助色 | 浅蓝灰 | `#6B8299` |
| 强调色(跌) | 红色 | `#DC2626` |
| 强调色(涨) | 绿色 | `#16A34A` |
| 背景色 | 纯白 | `#FFFFFF` |
| 文字色 | 深灰 | `#1F2937` |

#### 技术栈

| 库 | 用途 | 说明 |
|-----|------|------|
| **Matplotlib + Seaborn** | 静态图表 | 首选，论文级 |
| **Plotly** | 交互图表 | Web嵌入 |
| **Pyecharts** | 中文报告 | 中国市场 |
| **mplcairo** | 高质量导出 | SVG/PNG |

#### 图表模板

| 图表类型 | 适用场景 |
|----------|----------|
| 折线图 | 时间序列（股价、指数、宏观指标） |
| 柱状图 | 同比/环比对比 |
| 堆叠柱状图 | 产业链利润分布、收入结构 |
| 热力图 | 行业轮动矩阵、相关性矩阵 |
| 散点图 | PE vs 增速、量价关系 |
| 桑基图 | 产业链流向、资金流向 |

---

## 二、项目当前状态

### 已完成

| 模块 | 状态 | 路径 |
|------|------|------|
| AGENTS.md | ✅ 完成 | `AGENTS.md` |
| index.html | ✅ 完成 | `index.html` |
| index.json | ✅ 完成 | `index.json` |
| 研报样例 | ✅ 完成 | `reports/sample-report-001.html` |
| MCP配置 | ✅ 完成 | `mcp/.mcp.json` |
| SOP文档 | ✅ 完成 | `SOP/研报撰写SOP.md` |
| 数据管道脚本 | ✅ 完成 | `scripts/data-pipeline/fetch_*.py` |
| UBS绘图工具 | ✅ 完成 | `tools/chart_*.py`, `styles/ubs.mplstyle` |
| MCP测试文档 | ✅ 完成 | `docs/MCP_TEST_GUIDE.md` |
| 华工科技研报 | ✅ 完成 | 4个Agent并行完成 |

### 待修复 (P0) - 数据质量问题 【新增】

| 模块 | 问题 | 影响 | 修复方案 |
|------|------|------|----------|
| **股价数据失真** | 华工科技实际100元，研报显示41.82元 | 研报数据不可信 | **强制使用yfinance**，禁止从网上搜索股价 |
| **财报数据滞后** | 2025年一季报已发布，仍使用estimate | 分析基于过时数据 | **添加财报日期检查**，优先使用实际数据 |
| **数据验证缺失** | DataAgent未验证数据合理性 | 错误数据流入研报 | **添加数据校验规则**（如股价范围检查） |

### 数据质量SOP更新 【新增】

```markdown
### 数据获取优先级（强制）

1. **股价数据**
   - P0: yfinance (代码格式: 000988.SZ)
   - P1: 东方财富API
   - ❌ 禁止: 网上搜索的股价数据

2. **财务数据**
   - P0: yfinance (.financials / .quarterly_financials)
   - P1: 巨潮资讯网 (官方财报)
   - 检查点: 必须获取最新已发布财报，而非预测值

3. **数据验证 checklist**
   - [ ] 股价是否在合理范围 (A股一般 1-1000元)
   - [ ] 市值是否与股价×股本匹配
   - [ ] 财报日期是否为最新
   - [ ] PE/PB是否在合理范围
```

---

## 三、待办任务清单

### P0 - 紧急修复 (本周完成)

- [ ] **修复股价获取脚本**
  - [ ] 更新 `tools/fetch_stock_data.py` - 强制使用yfinance
  - [ ] 添加股价合理性校验 (1-1000元)
  - [ ] 添加市值交叉验证

- [ ] **修复财报数据获取**
  - [ ] 添加财报发布日期检查
  - [ ] 优先使用实际财报数据而非预测
  - [ ] 添加季度数据自动获取

- [ ] **数据验证中间件**
  - [ ] 创建 `tools/data_validator.py`
  - [ ] 实现股价/市值/PE范围检查
  - [ ] 实现财报日期新鲜度检查

### P1 - 数据管道完善

- [ ] **数据获取脚本**
  - [ ] `tools/fetch_index_data.py` - 已有，补充文档
  - [ ] `scripts/data-pipeline/fetch_macro_data.py` - 宏观数据
  - [ ] `scripts/data-pipeline/fetch_stock_daily.py` - A股个股日线
  - [ ] `scripts/data-pipeline/fetch_futures.py` - 期货数据

- [ ] **UBS绘图工具**
  - [ ] `tools/chart_style.py` - 统一样式配置
  - [ ] `styles/ubs.mplstyle` - Matplotlib样式文件
  - [ ] `tools/chart_generator.py` - 图表生成器基类

---

## 四、已识别问题详细记录

### Issue #1: 股价数据失真

**现象**: 华工科技(000988.SZ)实际股价约100元，但研报显示41.82元

**根因**: DataAgent使用WebSearch获取股价，而非直接调用yfinance API

**影响**: 
- 研报估值数据完全错误
- 目标价计算失真
- 投资结论不可信

**修复方案**:
1. 强制使用yfinance获取股价：`yf.Ticker('000988.SZ').info['currentPrice']`
2. 添加校验：股价应在1-1000元之间
3. 添加交叉验证：市值 = 股价 × 总股本

### Issue #2: 财报数据滞后

**现象**: 2025年一季报已发布，但研报使用estimate预测值

**根因**: DataAgent未检查财报发布日期，直接引用券商预测

**影响**:
- 分析基于过时数据
- 投资结论可能偏离实际

**修复方案**:
1. 添加财报日期检查逻辑
2. 优先使用 `.quarterly_financials` 获取实际季报
3. 添加数据新鲜度标签（数据获取时间）

---

## 五、技术路径

### Phase 0: 紧急修复（立即执行）

```
1. 更新 DataAgent SOP - 强制使用yfinance
2. 创建 data_validator.py 校验模块
3. 修复华工科技研报中的错误数据
4. 重新生成研报并发布
```

### Phase 1: 数据管道（1-2天）

```
1. 创建 scripts/data-pipeline/ 目录
2. 实现 fetch_macro_data.py (GDP/CPI/PPI/PMI)
3. 实现 fetch_stock_daily.py (个股/指数K线)
4. 实现 fetch_futures.py (国内期货+国际)
5. 编写数据管道测试文档
```

### Phase 2: 绘图工具（2-3天）

```
1. 创建 tools/chart_style.py
2. 创建 styles/ubs.mplstyle
3. 实现 TimeSeriesChart, BarChart, HeatmapChart 类
4. 实现 StackedBarChart (产业链利润)
5. 编写绘图测试文档
```

---

## 六、MCP工具清单

### 已有MCP

| 工具 | 路径 | 状态 |
|------|------|------|
| fetch_index_data | `tools/fetch_index_data.py` | ✅ 可用 |
| init_report | `tools/init_report.py` | ✅ 可用 |
| update_index_json | `tools/update_index_json.py` | ✅ 可用 |
| Notion MCP | 全局集成 | ✅ 可用 |
| WebSearch | 全局集成 | ✅ 可用 |

### 建议新增/修复 MCP

| 工具 | 脚本 | 用途 | 优先级 | 状态 |
|------|------|------|--------|------|
| fetch_stock_data | `tools/fetch_stock_data.py` | 个股数据（强制yfinance） | P0 | ✅ |
| data_validator | `tools/data_validator.py` | 数据质量校验 | P0 | ✅ |
| technical_analysis | `tools/technical_analysis.py` | 基础技术指标 | P1 | ✅ |
| technical_enhanced | `tools/technical_analysis_enhanced.py` | 增强版技术分析 | P1 | ✅ |
| fetch_macro_data | `scripts/data-pipeline/fetch_macro_data.py` | 宏观数据 | P1 | 🔄 |
| fetch_futures_data | `scripts/data-pipeline/fetch_futures.py` | 期货数据 | P1 | 🔄 |
| generate_charts | `tools/chart_generator.py` | 图表生成 | P1 | ✅ |

---

## 七、文件结构

```
投研助手/
├── .agentstalk/              # Agent协作目录
│   └── ROADMAP.md           # 本文件
├── index.html                # Landing Page ✅
├── index.json                # 研报索引 ✅
├── AGENTS.md                 # Agent定义 ✅
├── SOP/                      # 标准作业程序
│   ├── 研报撰写SOP.md       ✅
│   └── 数据获取SOP.md       # 待创建 (P0)
├── reports/                  # 研报存储
│   └── 华工科技深度研报/     # 需修复数据
├── tools/                    # 工具脚本
│   ├── fetch_index_data.py   # ✅ 指数数据
│   ├── fetch_stock_data.py   # ✅ 个股数据
│   ├── data_validator.py     # ✅ 数据验证
│   ├── technical_analysis.py # ✅ 基础技术指标
│   ├── technical_analysis_enhanced.py # ✅ 增强版技术分析
│   ├── init_report.py        # ✅ 研报初始化
│   ├── update_index_json.py  # ✅ 知识库更新
│   ├── chart_style.py        # ✅ 图表样式
│   └── chart_generator.py    # ✅ 图表生成
├── scripts/
│   └── data-pipeline/        # 待完善
│       ├── fetch_macro_data.py
│       ├── fetch_stock_daily.py
│       └── fetch_futures.py
├── styles/
│   └── ubs.mplstyle          # 待创建
├── templates/
│   └── report-template.html  # 已有
├── mcp/
│   └── .mcp.json             # MCP配置 ✅
└── data/                     # 数据目录
    ├── raw/
    ├── cleaned/
    └── processed/
```

---

## 八、备注

- ⚠️ **P0级问题必须立即修复**：股价和财报数据是研报的核心，数据错误将直接导致投资损失
- MCP测试文档需要包含：API连接测试、边界条件测试、错误处理测试
- 所有Python脚本需要包含 `--help` 和 example usage
- 数据管道脚本需要包含 crontab 定时任务配置示例
- 数据验证中间件必须成为数据获取流程的强制环节
