---
Task Status: IN PROGRESS
Sender: Architect Agent
Receiver: Dev Team
Topic: 数据质量问题修复计划
Priority: P0
Timestamp: 2026-04-02T17:00:00+08:00
---

# 数据质量问题修复计划

## 问题复盘

华工科技(000988.SZ)研报中发现两个严重数据质量问题：

### Issue #1: 股价数据失真 [CRITICAL]
- **现象**: 研报显示41.82元，实际股价约100元
- **根因**: DataAgent使用WebSearch获取股价，而非直接调用yfinance
- **影响**: 估值计算完全错误，投资结论不可信

### Issue #2: 财报数据滞后 [HIGH]
- **现象**: 2025年一季报已发布，但研报使用estimate预测值
- **根因**: 未检查财报发布日期，未获取实际财报数据
- **影响**: 分析基于过时数据

---

## 修复方案

### Phase 1: 立即修复（今天完成）

| 任务 | 负责人 | 状态 | 交付物 |
|------|--------|------|--------|
| 更新DataAgent SOP | Architect | ✅ 完成 | SOP/数据获取SOP.md |
| 创建数据验证中间件 | Architect | ✅ 完成 | tools/data_validator.py |
| 创建标准数据获取脚本 | Architect | ✅ 完成 | tools/fetch_stock_data.py |
| 编写测试文档 | Architect | ✅ 完成 | docs/DATA_FETCH_TEST_GUIDE.md |
| 修复华工科技研报数据 | HubAgent | 🔄 待执行 | 更新后的研报 |

### Phase 2: 工具完善（本周完成）

| 任务 | 优先级 | 说明 |
|------|--------|------|
| 完善数据管道脚本 | P1 | 添加更多数据源支持 |
| 创建批量验证工具 | P1 | 支持多股票批量检查 |
| 集成到MCP | P1 | 注册为MCP工具 |
| 编写完整测试用例 | P1 | 覆盖所有边界条件 |

---

## 已创建文件

### 1. 数据验证中间件
**路径**: `tools/data_validator.py`

**功能**:
- 股价范围验证 (1-1000元)
- 市值交叉验证 (市值 = 股价 × 股本)
- 财报日期新鲜度检查 (< 90天)
- 净利率合理性验证
- 装饰器支持 (`@validate_stock_data`)

**使用示例**:
```python
from tools.data_validator import DataValidator

validator = DataValidator()
is_valid, errors = validator.validate_stock_price(price_data)
```

### 2. 标准数据获取脚本
**路径**: `tools/fetch_stock_data.py`

**特点**:
- 强制使用yfinance（禁止WebSearch股价）
- 内置数据验证
- 支持对比模式
- 自动保存和时间戳

**使用示例**:
```bash
python tools/fetch_stock_data.py --ts-code 000988.SZ --verify --verbose
```

### 3. 测试文档
**路径**: `docs/DATA_FETCH_TEST_GUIDE.md`

**内容**:
- 测试原则和指标
- 股价数据测试用例
- 财务数据测试用例
- 数据验证中间件使用指南
- 问题记录与修复流程

### 4. 数据获取SOP
**路径**: `SOP/数据获取SOP.md`

**核心内容**:
- 数据源优先级（强制yfinance）
- 数据获取标准流程
- 数据验证检查点
- 常见问题修复指南

---

## 修复验证清单

- [x] 数据验证中间件实现
- [x] 强制yfinance数据源
- [x] 测试文档编写
- [ ] 华工科技研报数据修复
- [ ] 重新生成研报
- [ ] 验证修复效果

---

## 预防措施

### 1. 代码层面
- 所有数据获取脚本必须通过data_validator验证
- 强制使用yfinance，禁止使用WebSearch获取股价
- 添加数据源标记（data_source字段）

### 2. 流程层面
- DataAgent输出必须经过验证环节
- HubAgent核查数据来源和时间戳
- 建立数据质量检查清单

### 3. 测试层面
- 每次修改后运行基础测试
- 每周进行全量数据抽样测试
- 建立数据质量监控报表

---

## 后续行动

1. **立即**: 使用新脚本重新获取华工科技数据
2. **今天**: 修复研报中的错误数据
3. **本周**: 完善测试用例，覆盖所有边界条件
4. **持续**: 建立数据质量监控机制

---

**Archtect Agent 报告完毕，等待修复执行。**
