# MCP 代码架构审查报告

**Task Status**: ✅ 完成  
**Sender**: archreview (代码审查Agent)  
**Receiver**: architect (架构师)  
**Topic**: MCP 全模块代码审查与测试  
**Date**: 2025-07-02  

---

## 1. 文件审查矩阵

| 文件 | 行数 | 代码质量 | 可维护性 | 测试覆盖 | 总评 |
|------|------|----------|----------|----------|------|
| `server.py` | 91 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 精简清晰，职责单一 |
| `utils/cache.py` | 165 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 线程安全、文档完整 |
| `utils/formatters.py` | 292 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 函数职责清晰，边界处理好 |
| `utils/__init__.py` | 6 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | N/A | 纯导出，无逻辑 |
| `tools/__init__.py` | 1 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | N/A | 纯文档 |
| `tools/market_data.py` | 578 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | 工具丰富，多数据源降级设计好 |
| `tools/macro_data.py` | 506 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | 嵌套函数重复模式可优化 |
| `tools/company_analysis.py` | 695 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | 多策略回退设计好，略长 |
| `tools/report_generator.py` | 758 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | MD→HTML手写实现完整 |
| `tools/knowledge_base.py` | 179 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 简洁高效 |
| `templates/report_base.html` | 398 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | CSS设计专业 |

---

## 2. 问题清单（已修复项标记 ✅）

### 🔴 Critical

| # | 问题 | 文件 | 状态 |
|---|------|------|------|
| C1 | **模板变量大小写不匹配** — `report_base.html` 使用 `{{title}}` 等小写变量，而 `report_generator.py` 替换 `{{TITLE}}` 等大写变量，导致外部模板渲染完全失效 | `templates/report_base.html` | ✅ 已修复 |
| C2 | **`{{disclaimer}}` 占位符从未被替换** — 模板含 `{{disclaimer}}`，但 generator 无对应替换，导致研报中显示原始占位符 | `templates/report_base.html` | ✅ 已修复（改为固定免责声明文本） |
| C3 | **`{{YEAR}}` 缺失** — 外部模板无 `{{YEAR}}` 变量，页脚年份无法动态替换 | `templates/report_base.html` | ✅ 已修复 |

### 🟠 High

| # | 问题 | 文件 | 状态 |
|---|------|------|------|
| H1 | **`_round2` 函数重复定义** — `market_data.py` 和 `macro_data.py` 中完全相同的函数各定义一次 | `market_data.py`, `macro_data.py` | ✅ 已修复（提取到 `utils/formatters.py` 为 `safe_round`） |
| H2 | **`_date_str` 函数重复定义** — 同上，两个文件完全相同 | `market_data.py`, `macro_data.py` | ✅ 已修复（提取到 `utils/formatters.py` 为 `date_to_str`） |
| H3 | **`_cache` 变量声明但从未使用** — 3个工具模块导入并实例化 DataCache 但从未调用其任何方法，是纯死代码 | `market_data.py`, `macro_data.py`, `company_analysis.py` | ✅ 已修复（移除无用的缓存导入） |

### 🟡 Medium

| # | 问题 | 文件 | 状态 |
|---|------|------|------|
| M1 | **`_read_index()` 重复实现** — `report_generator.py` 和 `knowledge_base.py` 各自独立实现了相同的函数 | 两个文件 | ⚠️ 未修复（保留以避免循环依赖风险） |
| M2 | **`_df_to_records()` 两个不同实现** — `market_data.py` 和 `company_analysis.py` 各有一个，功能类似但实现不同 | 两个文件 | ⚠️ 未修复（两个实现针对各自场景有不同需求） |
| M3 | **`datetime` 未使用导入** — `knowledge_base.py` 导入了 `datetime` 但从未使用 | `knowledge_base.py` | ✅ 已修复 |
| M4 | **缓存 `get()` 方法破坏性删除** — 当 TTL 过期时直接删除缓存文件，若不同调用者使用不同 TTL 会互相干扰 | `utils/cache.py` | ⚠️ 未修复（当前实际使用场景无此问题） |
| M5 | **`macro_data.py` 嵌套函数模板化** — 7个指标获取函数结构完全相同（try→ak.xxx→_safe_records→return），可抽象为通用模式 | `macro_data.py` | ⚠️ 未修复（可读性尚可，属优化项） |

### 🔵 Low

| # | 问题 | 文件 | 状态 |
|---|------|------|------|
| L1 | `report_generator.py` 含242行内联 DEFAULT_TEMPLATE 与独立模板文件功能重叠 | `report_generator.py` | 保留为 fallback 设计 |
| L2 | `company_analysis.py` 695行偏长，可考虑拆分 A股/美股逻辑 | `company_analysis.py` | 当前可接受 |
| L3 | `market_data.py` 的 `get_forex` 函数86行偏长 | `market_data.py` | 多数据源降级逻辑所致，可接受 |
| L4 | `report_generator.py` 使用 `fcntl` 文件锁（仅 Unix），跨平台兼容性问题 | `report_generator.py` | 当前仅运行在 macOS/Linux |

---

## 3. 测试结果摘要

| 类别 | 通过 | 失败 | 跳过 |
|------|------|------|------|
| 模块导入 | 2 | 0 | 0 |
| 工具注册 | 5 | 0 | 0 |
| 缓存功能 | 3 | 0 | 0 |
| 格式化函数 | 12 | 0 | 0 |
| 研报生成 | 11 | 0 | 0 |
| 模板一致性 | 16 | 0 | 0 |
| 知识库 | 3 | 0 | 0 |
| **合计** | **52** | **0** | **0** |

> 语法检查：10/10 文件全部通过 AST 解析  
> 数据工具冒烟测试：跳过（依赖 akshare 网络请求，环境存在 numpy 版本兼容问题）

---

## 4. 代码修复记录

### Fix 1: 模板变量大小写统一 (C1+C2+C3)
**文件**: `templates/report_base.html`  
**变更**: 将所有模板变量从小写 (`{{title}}` 等) 改为大写 (`{{TITLE}}` 等)，与 `report_generator.py` 的替换逻辑保持一致。同时将 `{{disclaimer}}` 改为固定免责声明文本，新增 `{{YEAR}}` 变量。`{{tags}}` 改为 `{{TAGS_HTML}}`。

### Fix 2: 提取公共工具函数 (H1+H2)
**文件**: `utils/formatters.py`, `utils/__init__.py`, `tools/market_data.py`, `tools/macro_data.py`  
**变更**: 将 `_round2` → `safe_round`、`_date_str` → `date_to_str` 提取到 `utils/formatters.py` 并导出。两个工具模块改为从 utils 导入（带 fallback）。

### Fix 3: 移除死代码 (H3)
**文件**: `tools/market_data.py`, `tools/macro_data.py`, `tools/company_analysis.py`  
**变更**: 移除未使用的 `_cache = DataCache()` 声明及相关缓存导入样板代码。

### Fix 4: 移除未使用导入 (M3)
**文件**: `tools/knowledge_base.py`  
**变更**: 删除 `from datetime import datetime`（未使用）。

---

## 5. 改进建议（按优先级排序）

### P1 — 短期改进
1. **统一 `_read_index()` 实现** — 创建 `utils/index_io.py` 封装 index.json 读写逻辑，消除 `report_generator.py` 与 `knowledge_base.py` 的代码重复
2. **统一 `_df_to_records()` 实现** — 将 DataFrame→dict 转换逻辑合并到 `utils/formatters.py`
3. **为 `macro_data.py` 抽象指标获取模板** — 用高阶函数替代7个结构完全相同的 `_get_xxx()` 嵌套函数

### P2 — 中期改进
4. **启用缓存** — 当前3个数据工具模块（market_data/macro_data/company_analysis）均未实际使用缓存。应在高频数据获取接口中集成缓存，减少 akshare API 调用
5. **添加 `pyflakes`/`ruff` 静态分析** — 自动检测未使用导入和死代码
6. **`fcntl` 跨平台兼容** — 为 `_write_index()` 添加 Windows 兼容的文件锁方案

### P3 — 长期改进
7. **拆分 `company_analysis.py`** — 将 A股/美股财务数据获取分离为子模块
8. **添加单元测试** — 为缓存、格式化、MD→HTML 转换添加自动化单元测试
9. **缓存 TTL 策略优化** — 改为"读取时不删除，仅返回 None"的策略，避免跨调用者 TTL 冲突

---

## Next Action

建议架构师审阅修复内容并 git commit。重点关注：
1. 模板修复是否影响已生成的研报（已有研报不受影响，仅影响新生成的）
2. 是否需要在 P1 改进周期内启用缓存功能
3. 是否增加 CI 静态检查流程
