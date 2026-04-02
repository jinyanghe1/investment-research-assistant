# Agent Communication Record

## Metadata
- **Timestamp**: 2026-04-02T09:29:00Z
- **Sender**: Architect (首席架构Agent)
- **Receiver**: All Agents
- **Topic**: Phase 3 Wave 2 开发路线图 — 期货/ETF/可转债 + 信号增强

## Task Status
🚀 Phase 3 Wave 2 INITIATED

---

# Wave 2 任务分解

## P3.1a: 期货数据工具 (`futures_data.py`)

### 新增工具
1. `get_futures_realtime(symbol)` — 期货实时行情 (内外盘)
2. `get_futures_history(symbol, period)` — 期货历史K线
3. `get_futures_position(symbol)` — 持仓排名/多空比
4. `get_futures_basis(symbol)` — 基差/升贴水分析

### akshare API 映射
- `futures_zh_spot` / `futures_main_sina` → 实时行情
- `futures_zh_daily_sina` / `futures_zh_minute_sina` → 历史K线  
- `futures_dce_position_rank` / `futures_shfe_position_rank` → 持仓排名
- `futures_spot_price` → 现货价格 (基差计算)

## P3.1b: ETF数据工具 (嵌入 `market_data.py`)

### 新增工具
1. `get_etf_realtime(symbol)` — ETF实时行情+净值
2. `get_etf_history(symbol, period)` — ETF历史数据

### akshare API
- `fund_etf_spot_em` → 实时行情
- `fund_etf_hist_em` → 历史K线

## P3.1c: 可转债工具 (嵌入 `market_data.py`)

### 新增工具
1. `get_convertible_bond(symbol)` — 可转债行情+转股价值

### akshare API
- `bond_cb_jsl` → 集思录可转债数据
- `bond_zh_cov_value_analysis` → 转债价值分析

## P3.2c: 技术面增强 (修改 `technical_analysis.py`)

### 增强内容
1. **加权信号评分**: MACD(40%) > RSI(30%) > BOLL(20%) > KDJ(10%)
2. **估值历史分位数**: PE/PB历史百分位 (新增到 fundamental_analysis.py)

## 并行分工
- Agent 1: futures_data.py (期货独立模块)
- Agent 2: market_data.py增强 (ETF+可转债) + technical_analysis.py加权信号
- Guardian: tech-research + arch-review

## 依赖关系
```
P3.1a (期货) ∥ P3.1b+c (ETF/可转债) ∥ P3.2c (信号增强)
        ↓                ↓                    ↓
               P3-W2-tests (统一测试)
                      ↓
               P3-W2-arch-review
```
