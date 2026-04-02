# Agent Communication Record

## Metadata
- **Timestamp**: 2026-04-02T09:07:53Z
- **Sender**: Architect (首席架构Agent)
- **Receiver**: All Agents
- **Topic**: Phase 3 开发路线图 — 技术面分析 + 基本面研究增强

## Task Status
🚀 Phase 3 INITIATED

---

# Phase 3: 功能增强 — 第一波 (Wave 1)

## 优先级排序
1. **P3.2a 技术面分析模块** ← 用户优先要求
2. **P3.2b 企业基本面深度分析** ← 用户优先要求
3. P3.1 期货/可转债/ETF数据 (Wave 2)
4. P3.3 研报模板增强 (Wave 2)

---

## P3.2a: 技术面分析模块 (`technical_analysis.py`)

### 目标
新增 MCP 工具 `get_technical_indicators`，支持对任意标的计算常用技术指标。

### 功能规格

| 指标 | 参数 | 说明 |
|------|------|------|
| MA | periods: [5,10,20,60,120,250] | 简单移动平均线 |
| EMA | periods: [12,26] | 指数移动平均线 |
| MACD | fast=12, slow=26, signal=9 | 趋势+动量 |
| RSI | period=14 | 相对强弱指标 |
| KDJ | n=9, m1=3, m2=3 | 随机指标 |
| BOLL | period=20, std=2 | 布林带 |
| ATR | period=14 | 真实波动幅度 |
| OBV | — | 能量潮 |

### 技术方案
- **纯pandas计算**：不依赖ta-lib（编译依赖重），全部用pandas/numpy手写
- **复用现有数据**：调用 `fetch_stock_history()` 获取K线，在其基础上计算
- **架构对齐**：遵循 `@handle_errors` + `register_tools()` 模式
- **缓存策略**：技术指标不缓存（实时性要求高），底层K线数据走现有缓存

### 新增工具
1. `get_technical_indicators(symbol, indicators, period, market)` — 综合技术指标
2. `get_technical_signal(symbol, market)` — 技术面信号摘要（买入/卖出/中性）

---

## P3.2b: 企业基本面深度分析 (`fundamental_analysis.py`)

### 目标
新增 MCP 工具，支持获取企业深层基本面数据：

### 功能规格

| 维度 | 具体指标 | 数据源 |
|------|----------|--------|
| 盈利能力 | 毛利率、净利率、ROE、ROA、ROIC | akshare `stock_financial_analysis_indicator` |
| 成长性 | 营收增速、利润增速、复合增长率 | akshare 财务报表 |
| 运营效率 | 应收周转天数、存货周转天数、资产周转率 | akshare 财务分析指标 |
| 偿债能力 | 资产负债率、流动比率、速动比率、利息保障倍数 | akshare 资产负债表 |
| 现金流 | 经营现金流/净利润、自由现金流、资本开支比 | akshare 现金流量表 |
| 估值 | PE/PB/PS/PEG/EV-EBITDA | akshare + yfinance |
| 股东结构 | 十大股东、股东户数变化、机构持仓 | akshare |
| 行业对比 | 同行业公司横向对比（市占率代理指标） | akshare 行业板块 |

### 新增工具
1. `get_fundamental_profile(symbol)` — 企业基本面全景画像
2. `get_peer_comparison(symbol, metrics)` — 同行业对标分析
3. `get_shareholder_analysis(symbol)` — 股东结构分析

### 数据源映射
```
akshare API → 用途
stock_financial_analysis_indicator → 核心财务指标(盈利/运营/偿债)
stock_profit_sheet_by_report_em → 利润表(计算利润率/增速)
stock_zcfz_em → 资产负债表(计算杠杆率)
stock_financial_cash_ths → 现金流量表
stock_individual_info_em → 个股基本信息
stock_board_industry_cons_em → 行业成分股(用于对标)
```

---

## 依赖关系
```
P3.2a (技术面) ← 依赖 market_data.fetch_stock_history
P3.2b (基本面) ← 依赖 company_analysis.fetch_company_financials (部分复用)
P3.2a ∥ P3.2b (可并行开发)
```

## 守护协议
按照 Dev Guardian Protocol，本波开发配置：
- 🔬 tech-research agent: GitHub技术面分析最优实现调研
- 🏗️ arch-review agent: 增量架构审查 + 测试验证
- 📚 fundamental-research agent: 基本面研究方法论调研

## Next Action
- 立即启动 3 个调研Agent + 2 个实现Agent 并行工作
