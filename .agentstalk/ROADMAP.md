# 投研助手路线图 v1.0

> 创建时间：2026-04-02
> 更新日期：2026-04-02

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
| **P0** | A股指数/日线 | 东方财富（已集成）/ AKShare | 免费 |
| **P0** | 个股K线/财务 | Tushare / AKShare | 需注册 |
| **P1** | 宏观指标 | AKShare（国家统计局封装）/ FRED API | 免费 |
| **P1** | 期货/大宗商品 | AKShare + yfinance | 免费 |
| **P2** | 行业数据 | 协会官网/乘联会/奥维云网 | 部分付费 |
| **P2** | 港股 | Yahoo Finance (yfinance) | 免费 |
| **P3** | 美股 | yfinance | 免费 |

#### 推荐Python依赖

```
tushare>=1.4.0        # A股/财务数据（需注册获取Token）
akshare>=1.13.0       # 全市场免费数据（首选）
yfinance>=0.2.40      # 国际市场行情
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
| 调研阶段 | ✅ 完成 | 4个调研Agent已完成 |

### 待改进 (P0)

| 模块 | 问题 | 说明 |
|------|------|------|
| 数据管道脚本 | start_date/end_date未使用 | 日期过滤功能缺失 |
| UBS绘图工具 | 样式配置两处重复 | DRY违反 |

### 待开发

| 模块 | 优先级 | 说明 |
|------|--------|------|
| 缓存集成 | P0 | MCP中已有cache.py但未使用 |
| 重试机制 | P1 | 添加tenacity重试 |
| mplfinance集成 | P1 | K线图支持 |
| 增量更新 | P2 | 数据管道优化 |

---

## 三、待办任务清单

### P0 - 核心基础设施

- [ ] **数据获取脚本**
  - [ ] `tools/fetch_index_data.py` - 已有，需补充文档
  - [ ] `scripts/data-pipeline/fetch_macro_data.py` - 宏观GDP/CPI/PPI
  - [ ] `scripts/data-pipeline/fetch_stock_daily.py` - A股个股日线
  - [ ] `scripts/data-pipeline/fetch_futures.py` - 期货数据

- [ ] **UBS绘图工具**
  - [ ] `tools/chart_style.py` - 统一样式配置
  - [ ] `styles/ubs.mplstyle` - Matplotlib样式文件
  - [ ] `tools/chart_generator.py` - 图表生成器基类

### P1 - MCP测试文档

- [ ] **数据获取测试**
  - [ ] Tushare API连接测试
  - [ ] AKShare数据完整性测试
  - [ ] 东方财富接口稳定性测试
  - [ ] FRED API宏数据测试

- [ ] **批量分析测试**
  - [ ] 多股票数据批量抓取测试
  - [ ] 宏观数据定时更新测试
  - [ ] 数据清洗流程测试

- [ ] **绘图脚本测试**
  - [ ] 时间序列图渲染测试
  - [ ] 柱状图/堆叠柱状图测试
  - [ ] 热力图渲染测试
  - [ ] 中文字体显示测试

### P2 - 流程自动化

- [ ] **研报生成闭环**
  - [ ] 数据获取 → 分析 → 图表生成 → HTML输出
  - [ ] index.json自动更新
  - [ ] .agentstalk/状态同步

---

## 四、技术路径

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

### Phase 3: 研报闭环（1-2天）

```
1. 数据获取 → 图表生成 → HTML嵌入
2. index.json 自动更新
3. SOP文档扩充
4. Agent协作流程测试
```

---

## 五、MCP工具清单

### 已有MCP

| 工具 | 路径 | 状态 |
|------|------|------|
| fetch_index_data | `tools/fetch_index_data.py` | ✅ 可用 |
| init_report | `tools/init_report.py` | ✅ 可用 |
| update_index_json | `tools/update_index_json.py` | ✅ 可用 |
| Notion MCP | 全局集成 | ✅ 可用 |
| WebSearch | 全局集成 | ✅ 可用 |

### 建议新增MCP

| 工具 | 脚本 | 用途 |
|------|------|------|
| fetch_macro_data | `scripts/data-pipeline/fetch_macro_data.py` | 宏观数据 |
| fetch_stock_data | `scripts/data-pipeline/fetch_stock_daily.py` | A股数据 |
| fetch_futures_data | `scripts/data-pipeline/fetch_futures.py` | 期货数据 |
| generate_charts | `tools/chart_generator.py` | 图表生成 |

---

## 六、文件结构

```
投研助手/
├── .agentstalk/              # Agent协作目录
│   └── ROADMAP.md           # 本文件
├── index.html                # Landing Page ✅
├── index.json                # 研报索引 ✅
├── AGENTS.md                 # Agent定义 ✅
├── SOP/                      # 标准作业程序
│   └── 研报撰写SOP.md       ✅
├── reports/                  # 研报存储
│   └── sample-report-001.html ✅
├── tools/                    # 工具脚本
│   ├── fetch_index_data.py   # 已有
│   ├── init_report.py        # 已有
│   ├── update_index_json.py  # 已有
│   ├── chart_style.py        # 待创建
│   └── chart_generator.py    # 待创建
├── scripts/
│   └── data-pipeline/        # 待创建
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

## 七、备注

- MCP测试文档需要包含：API连接测试、边界条件测试、错误处理测试
- 所有Python脚本需要包含 `--help` 和 example usage
- 数据管道脚本需要包含 crontab 定时任务配置示例
