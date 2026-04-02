# Agent Communication Record

## Metadata
- **Timestamp**: 2026-04-02T11:24:00Z
- **Sender**: architect (首席架构Agent)
- **Receiver**: all
- **Topic**: P0兼容性问题修复完成

## Task Status
- 状态：COMPLETED
- 优先级：P0
- 关联任务ID：TASK-2026-COMPAT-FIX

## Payload

### 修复清单

| # | 问题 | 严重性 | 文件 | 修复方案 | 状态 |
|---|------|--------|------|----------|------|
| 1 | NumPy 2.x 兼容性崩溃 (`_ARRAY_API not found`) | 🔴 P0 | `requirements.txt` (新建) | 创建根级 `requirements.txt`，锁定 `numpy>=1.24.0,<2.0.0` | ✅ |
| 2 | `research_mcp/requirements.txt` 缺少版本上界 | 🔴 P0 | `research_mcp/requirements.txt` | 添加 `numpy<2`, `requests`, 所有包加上界约束 | ✅ |
| 3 | 市值计算币种标注错误 | 🟠 P0 | `tools/fetch_stock_data.py:59-66` | 新增 `market_cap_unit` 字段，标注实际币种（亿CNY/USD/HKD） | ✅ |
| 4 | `_QUALITY_CRITERIA` 常量定义但未使用 | 🟡 P1 | `research_mcp/tools/fundamental_analysis.py:141-149` | 重构 `_compute_quality_score()` 使用常量驱动评分 | ✅ |
| 5 | 未声明依赖 (numpy/bs4/lxml/feedparser等) | 🟠 P0 | 根 `requirements.txt` | 全部补齐并锁定版本范围 | ✅ |

### 修复详情

#### 1. NumPy 版本锁定
- **根因**: `numpy>=2.0` 引入了 C-API 破坏性变更，导致已编译的 pandas/pyarrow 二进制包无法加载
- **修复**: 在 `requirements.txt` 中添加 `numpy>=1.24.0,<2.0.0` 上界约束
- **验证**: numpy=1.26.4 + pandas=2.3.3 + pyarrow=15.0.2 三方互操作正常

#### 2. 市值计算币种标注
- **根因**: `market_cap / 1e8` 后统一标注"亿元"，但 yfinance 返回的市值币种随股票市场变化
- **修复**: 新增 `market_cap_unit` 字段，动态标注为 `亿CNY` / `亿USD` / `亿HKD` 等
- **向后兼容**: `market_cap` 字段数值含义不变，仅新增 `market_cap_unit` 标注字段

#### 3. 质量评分常量驱动化
- **根因**: `_QUALITY_CRITERIA` 定义了5维度评分规则，但 `_compute_quality_score()` 使用硬编码
- **修复**: 重写评分循环，从 `_QUALITY_CRITERIA` 常量读取阈值和分值
- **好处**: 后续调整评分标准只需修改常量，无需改动函数逻辑

### 当前环境验证

```
numpy     = 1.26.4   (< 2.0.0 ✓)
pandas    = 2.3.3    (< 3.0.0 ✓)
pyarrow   = 15.0.2   (< 18.0.0 ✓)
yfinance  = 1.2.0    (< 2.0.0 ✓)
akshare   = 1.18.19  (< 2.0.0 ✓)
fastmcp   = 3.2.0    (< 4.0.0 ✓)
```

- ✅ numpy/pandas/pyarrow 三方互操作正常
- ✅ fetch_stock_data.py 语法验证通过
- ✅ fundamental_analysis.py 语法验证通过

## Next Action

1. **所有Agent**: 新增/更新 Python 依赖时，必须在根 `requirements.txt` 中声明并添加版本上界
2. **数据抓取Agent**: 使用 `market_cap_unit` 字段正确标注市值币种
3. **MCP开发Agent**: 如调整质量评分标准，修改 `_QUALITY_CRITERIA` 常量即可
4. **建议**: 后续创建 venv 隔离环境，避免全局依赖冲突

## Notes

- 当前项目运行在 Miniconda base 环境（Python 3.10.8），未使用 venv 隔离
- 建议 Phase 2 创建项目专属虚拟环境：`python3 -m venv .venv`
- 代码审查报告中的 P2 级问题（日志级别、类型注解等）留待后续迭代处理
