# Agent 通信：架构审查 → 架构师

- **时间戳**: 2026-04-02 08:41:00
- **发送方**: archreview (架构审查Agent)
- **接收方**: architect (首席架构师)
- **主题**: Phase 2 代码基线审查报告

---

## Task Status: ✅ COMPLETED

## Payload

---

### 一、工具函数分析矩阵

#### 1. market_data.py（561行，5个 @mcp.tool）

| 函数名 | 行号 | 行数 | 嵌套函数 | 外部依赖 | 错误处理 | 可提取逻辑块 | 复杂度 |
|--------|------|------|----------|----------|----------|-------------|--------|
| `get_stock_realtime` | L74-172 | 99 | 无 | akshare, yfinance | 外层 try/except + 各 market 分支内检查 | ①A股实时行情提取 ②US/HK yfinance 提取（重复模式） | **中** |
| `get_stock_history` | L177-283 | 107 | 无 | akshare, yfinance, pandas | 外层 try/except | ①A股历史K线获取 ②US历史K线获取 ③手动iterrows→records | **中** |
| `get_index_quote` | L288-377 | 90 | 无 | akshare, yfinance | 嵌套 try/except per index | ①国内指数批量提取 ②海外指数yfinance提取 | **中** |
| `get_forex` | L382-472 | 91 | 无 | akshare, yfinance | try/except + akshare→yfinance fallback | ①akshare外汇查询 ②yfinance fallback 查询 | **中** |
| `get_commodity` | L477-561 | 85 | 无 | akshare, yfinance | try/except + 双源 | ①akshare期货主力 ②yfinance国际商品 | **中** |

**模块级辅助**: `_df_to_records` (L49-62, 14行), import fallback block (L15-46)

#### 2. macro_data.py（494行，3个 @mcp.tool）

| 函数名 | 行号 | 行数 | 嵌套函数 | 外部依赖 | 错误处理 | 可提取逻辑块 | 复杂度 |
|--------|------|------|----------|----------|----------|-------------|--------|
| `get_macro_china` | L76-185 | 110 | ⚠️ **7个**闭包 (_get_gdp/_get_cpi/_get_ppi/_get_pmi/_get_m2/_get_social_financing/_get_trade) | akshare | 每个闭包各有 try/except + 外层 try/except | ①7个闭包→统一宏观指标获取器 ②overview聚合逻辑 | **高** |
| `get_macro_global` | L190-301 | 112 | ⚠️ **7个**闭包 (_get_us_interest_rate/_get_us_cpi/...) | akshare | 同上 | ①7个闭包→统一全球指标获取器 ②overview聚合逻辑（与china完全重复） | **高** |
| `get_fund_flow` | L306-336 | 31 | 无（委派给模块级函数） | akshare | 外层 try/except + 路由 | 已较好分离 | **低** |

**模块级辅助**:
- `_safe_records` (L49-63, 15行) — 与 market_data 的 `_df_to_records` 功能重叠
- `_get_north_flow` (L338-397, 60行) — 含多API fallback循环
- `_get_industry_flow` (L399-446, 48行) — 与 `_get_concept_flow` 几乎完全相同
- `_get_concept_flow` (L448-494, 47行) — 与 `_get_industry_flow` 几乎完全相同

#### 3. company_analysis.py（692行，3个 @mcp.tool）

| 函数名 | 行号 | 行数 | 嵌套函数 | 外部依赖 | 错误处理 | 可提取逻辑块 | 复杂度 |
|--------|------|------|----------|----------|----------|-------------|--------|
| `get_company_financials` | L78-166 | 89 | 无（委派模块函数） | akshare, yfinance | try/except + import检查 | 已合理拆分 | **中** |
| `screen_stocks` | L171-328 | **158** | 无 | akshare, pandas | try/except | ①列名映射 ②行业筛选 ③数值过滤 ④排序 ⑤输出构建（至少5块可拆） | **⚠️ 极高** |
| `get_industry_ranking` | L333-447 | 115 | 无（委派模块函数） | akshare, pandas | try/except | ①列名标准化 ②排序 ③输出构建 | **中** |

**模块级辅助**:
- `_safe_float` (L32-42, 11行) — 与 `safe_round` 功能重叠
- `_df_to_records` (L45-65, 21行) — ⚠️ **同名但实现不同于 market_data.py**
- `_a_share_summary` (L454-526, 73行) — 含4个策略的瀑布式 fallback
- `_a_share_statement` (L529-561, 33行) — 多API名称 fallback 模式
- `_us_summary` (L568-615, 48行)
- `_fetch_board_data` (L622-645, 24行) — 多API fallback
- `_apply_period_data` (L648-692, 45行) — 循环调用历史API，性能隐患

#### 4. report_generator.py（758行，3个 @mcp.tool）

| 函数名 | 行号 | 行数 | 嵌套函数 | 外部依赖 | 错误处理 | 可提取逻辑块 | 复杂度 |
|--------|------|------|----------|----------|----------|-------------|--------|
| `generate_report` | L488-579 | 92 | 无 | 文件I/O | 外层 try/except | ①模板加载 ②md→html调用 ③TOC生成 ④模板替换 ⑤写文件 ⑥注册索引 | **中** |
| `create_data_table` | L584-669 | 86 | `_is_numeric`(3行闭包) | 无（纯字符串） | 外层 try/except | ①HTML表格构建 ②Markdown表格构建 | **低** |
| `register_report` | L674-731 | 58 | 无 | 文件I/O | 外层 try/except | 逻辑已简洁 | **低** |

**模块级组件（体量巨大）**:
- `DEFAULT_TEMPLATE` (L25-242, **218行**) — 内联HTML模板，应迁移到独立文件
- `_md_to_html` (L249-353, **105行**) — 手写Markdown解析器，含 `_inline` 闭包
- `_is_block_start` (L356-375, 20行)
- `_parse_table` (L378-415, 38行) — 含 `split_row` 闭包
- `_extract_toc` (L418-430, 13行)
- `_read_index` (L450-463, 14行) — ⚠️ **与 knowledge_base.py 完全重复**
- `_write_index` (L466-475, 10行)
- `_auto_register` (L736-758, 23行) — 与 `register_report` 逻辑重复

#### 5. knowledge_base.py（178行，2个 @mcp.tool）

| 函数名 | 行号 | 行数 | 嵌套函数 | 外部依赖 | 错误处理 | 可提取逻辑块 | 复杂度 |
|--------|------|------|----------|----------|----------|-------------|--------|
| `list_reports` | L54-101 | 48 | 无 | 文件I/O (index.json) | 外层 try/except | 逻辑清晰，可保持 | **低** |
| `search_reports` | L106-165 | 60 | 无 | 文件I/O (index.json) | 外层 try/except | ①分词 ②多字段匹配评分 ③排序 | **低** |

**模块级辅助**:
- `_read_index` (L19-32, 14行) — ⚠️ 与 report_generator.py 完全重复
- `_slim_record` (L35-45, 11行)
- `_get_field_text` (L168-178, 11行)

---

### 二、重复代码清单

#### 🔴 严重重复（必须消除）

| # | 重复模式 | 涉及位置 | 重复行数 | 建议提取的公共函数 |
|---|---------|---------|---------|-----------------|
| D1 | `_read_index()` 完全相同 | `report_generator.py:450-463` + `knowledge_base.py:19-32` | 28行 | → `utils/index_io.py::read_index()` |
| D2 | 宏观指标闭包模式（14个几乎相同的闭包） | `macro_data.py:92-154` (china) + `macro_data.py:207-268` (global) | ~210行 | → 通用 `_fetch_macro_indicator(api_func, label)` 工厂函数，可削减至 ~30行 |
| D3 | `_get_industry_flow` ≈ `_get_concept_flow` | `macro_data.py:399-446` + `macro_data.py:448-494` | 96行 | → `_get_sector_flow(sector_type, api_names, label)` 参数化 |
| D4 | overview 聚合逻辑 | `macro_data.py:167-177` + `macro_data.py:281-290` | 20行 | → `_build_overview(indicator_funcs)` |
| D5 | `_df_to_records` 同名不同实现 | `market_data.py:49-62` + `company_analysis.py:45-65` | 35行 | → `utils/formatters.py::df_to_records()` 统一版本 |

#### 🟡 中度重复（建议消除）

| # | 重复模式 | 涉及位置 | 建议 |
|---|---------|---------|------|
| D6 | yfinance ticker 价格提取模式 | `market_data.py` L119-141, L148-167, L353-367, L447-462, L536-551 (5处) | → `_yf_price_snapshot(symbol) -> dict` |
| D7 | akshare 多API fallback 循环 | `macro_data.py:345-357`, `macro_data.py:403-418`, `company_analysis.py:546-558`, `company_analysis.py:635-644` (4处) | → `_try_akshare_apis(func_names, **kwargs) -> DataFrame` |
| D8 | import/fallback 块 | `market_data.py:15-28`, `macro_data.py:15-28`, `company_analysis.py:16-25` (3处几乎相同) | → 统一由 `utils/__init__.py` 导出 |
| D9 | `_safe_float` ≈ `safe_round` ≈ `_round2` | `company_analysis.py:32-42`, `utils/formatters.py:236-241`, 内联fallback | → 统一使用 `utils.formatters.safe_round` |
| D10 | `_safe_records` ≈ `_df_to_records` | `macro_data.py:49-63` ≈ `market_data.py:49-62` | → 合并为 `utils/formatters.py::df_to_records()` |
| D11 | `_auto_register` ≈ `register_report` 内逻辑 | `report_generator.py:736-758` ≈ `report_generator.py:701-731` | → 合并为单一 `_upsert_index()` 函数 |

#### 🟢 轻度重复（可选优化）

| # | 重复模式 | 说明 |
|---|---------|------|
| D12 | 手动 iterrows→records 转换 | `macro_data.py` L376-387, L426-436, L474-484; `market_data.py` L218-228, L260-268 — 应统一使用 `df_to_records` |
| D13 | 错误返回 `{"error": msg}` | 所有16个工具一致使用此模式，但无统一 helper —— 可考虑 `_err(msg)` 缩写 |
| D14 | akshare None 检查 `if ak is None` | `market_data.py` 4处, `macro_data.py` 2处 — 可用装饰器统一 |

---

### 三、重构风险评估

#### 🔴 高风险函数

| 函数 | 风险原因 | 缓解策略 |
|------|---------|---------|
| `screen_stocks` (158行) | ①最复杂的单函数 ②列名映射依赖东方财富实时数据格式（会变） ③行业筛选有 fallback 路径 ④测试覆盖困难（需要完整行情数据） | 分步拆分：先提取 filter/sort 为纯函数并单元测试，再改造主函数 |
| `get_macro_china` / `get_macro_global` | ①14个嵌套闭包，耦合在 register_tools 作用域 ②overview 模式会串行调用所有 API（极慢） ③akshare API 名称频繁变化 | 先抽出指标配置表 (name→api_func 映射)，再实现工厂函数 |
| `_apply_period_data` | ①循环调用 akshare 历史API（最多60次网络请求） ②无错误累积/超时控制 ③性能极差 | 添加采样限制 + 超时机制，重构为批量获取 |
| `_a_share_summary` | ①4层策略瀑布式 fallback ②每层都可能触发网络请求 ③失败静默 | 保持瀑布逻辑但加日志，提取为独立模块 |

#### 🟡 中风险函数

| 函数 | 风险原因 | 缓解策略 |
|------|---------|---------|
| `get_stock_realtime` | A/US/HK 三分支各有不同数据结构 | 拆为 `_fetch_a_realtime` / `_fetch_us_realtime` / `_fetch_hk_realtime` |
| `get_stock_history` | US分支涉及 yfinance MultiIndex 处理 | 拆分时保留 MultiIndex 处理逻辑 |
| `_md_to_html` (105行) | 手写解析器逻辑精密，修改易引入 bug | 单独提取为 `utils/markdown.py`，配备专项单元测试后再动 |
| `_get_north_flow` | 4层 API fallback + 手动 iterrows | 使用 `_try_akshare_apis` 通用函数替代 |

#### 🟢 低风险函数

| 函数 | 说明 |
|------|------|
| `get_fund_flow` | 仅 31 行，纯路由，已良好分离 |
| `list_reports` / `search_reports` | 逻辑简洁，仅依赖文件 I/O |
| `register_report` | 简单的 CRUD |
| `create_data_table` | 纯字符串处理，无外部依赖 |
| `generate_report` | 主要是胶水代码，各组件已独立 |
| `get_index_quote` / `get_forex` / `get_commodity` | 结构清晰，中等体量 |

---

### 四、推荐的重构顺序（低风险 → 高风险）

#### Phase 2-A：基础设施层（风险最低，收益最高）

```
Step 1: 消除 _read_index 重复 [D1]
  Before: report_generator.py 和 knowledge_base.py 各自维护 _read_index
  After:  utils/index_io.py::read_index() + utils/index_io.py::write_index()
  提取内容: index.json 的读/写/锁逻辑
  风险: 极低 — 纯文件 I/O，两处实现完全相同
  工作量: ~30分钟

Step 2: 统一 DataFrame→records 转换 [D5, D10]
  Before: market_data._df_to_records (14行) + company_analysis._df_to_records (21行) + macro_data._safe_records (15行)
  After:  utils/formatters.py::df_to_records(df, max_rows, date_cols, nan_placeholder) — 统一版本 (~25行)
  提取内容: NaN处理 + Timestamp转换 + 可选"N/A"填充
  风险: 低 — 需验证 company_analysis 的 "N/A" 行为是否影响下游
  工作量: ~45分钟

Step 3: 统一 safe_float/safe_round [D9]
  Before: company_analysis._safe_float + utils.formatters.safe_round + 内联 _round2
  After:  utils/formatters.py::safe_number(val, decimals, fallback="N/A"|None)
  提取内容: 数值安全转换逻辑
  风险: 极低
  工作量: ~20分钟

Step 4: 统一 import/fallback 块 [D8]
  Before: 3个文件各有15行 import fallback
  After:  各文件简化为 `from utils.formatters import safe_round, date_to_str`（fallback 已内置于 utils）
  提取内容: 移除冗余 fallback 定义
  风险: 低 — utils 模块已有 fallback 机制
  工作量: ~15分钟
```

#### Phase 2-B：数据获取层重构

```
Step 5: akshare 多API fallback 统一 [D7]
  Before: 4处手写 for-getattr-try 循环
  After:  utils/akshare_helpers.py::try_akshare_apis(func_names, **kwargs) -> DataFrame
  提取内容: 通用的"按优先级尝试多个 akshare 函数名"模式
  风险: 低 — 纯提取，不改变行为
  工作量: ~30分钟

Step 6: yfinance 价格快照统一 [D6]
  Before: 5处重复的 ticker.info 价格/涨跌幅计算
  After:  utils/yfinance_helpers.py::yf_price_snapshot(symbol) -> dict
  提取内容: price/prev_close/change_pct 计算 + 通用字段映射
  风险: 低 — 5处逻辑高度一致
  工作量: ~30分钟

Step 7: 资金流向合并 [D3]
  Before: _get_industry_flow (48行) + _get_concept_flow (47行) ≈ 95行
  After:  _get_sector_flow(sector_type, api_names, label) (~35行) + 2个 3 行包装器
  提取内容: 参数化的板块资金流向获取
  风险: 低
  工作量: ~20分钟
```

#### Phase 2-C：宏观数据重构（中等风险）

```
Step 8: 宏观指标工厂函数 [D2, D4]
  Before: get_macro_china 内 7 个闭包 + get_macro_global 内 7 个闭包 = 14 个闭包 (~210行)
  After:  配置表驱动:
    CHINA_INDICATORS = {
      "gdp": {"api": "macro_china_gdp", "label": "GDP"},
      "cpi": {"api": "macro_china_cpi_monthly", "label": "CPI"},
      ...
    }
    def _fetch_indicator(api_name, label, max_rows=12) -> dict  # 通用获取器 (~10行)
    def _build_overview(indicator_config) -> dict               # 通用聚合器 (~15行)
  提取内容: 14个重复闭包 → 配置表 + 2个通用函数
  削减: ~210行 → ~60行 (节省 ~150行)
  风险: 中 — 需确认每个 akshare API 无特殊参数差异
  工作量: ~1小时
```

#### Phase 2-D：复杂函数拆分（较高风险）

```
Step 9: screen_stocks 拆分 (158行 → ~80行 + 3个纯函数)
  Before: register_tools 内的 158 行巨型闭包
  After:
    - _apply_stock_filters(df, industry, pe_range, roe, cap_range) -> DataFrame  (~40行)
    - _sort_stocks(df, sort_by) -> DataFrame  (~15行)
    - _format_stock_list(df, limit) -> list[dict]  (~20行)
    - screen_stocks 薄包装器  (~30行)
  提取内容: 筛选逻辑、排序逻辑、格式化逻辑
  风险: 中高 — 列名映射与 pandas 操作需仔细测试
  工作量: ~1.5小时

Step 10: get_stock_realtime 拆分 (99行 → ~30行 + 3个获取器)
  Before: A/US/HK 三分支混在一起
  After:
    - _fetch_a_stock_realtime(symbol) -> dict  (~25行)
    - _fetch_us_stock_realtime(symbol) -> dict  (~20行)
    - _fetch_hk_stock_realtime(symbol) -> dict  (~20行)
    - get_stock_realtime 薄包装器 + 市场路由  (~15行)
  提取内容: 各市场的数据获取和字段映射
  风险: 中 — HK/US 共享 yfinance 逻辑，可进一步合并
  工作量: ~45分钟
```

#### Phase 2-E：Markdown解析器独立化（需谨慎）

```
Step 11: _md_to_html 迁移
  Before: report_generator.py 内含 105行解析器 + 20行 _is_block_start + 38行 _parse_table = 163行
  After:  utils/markdown.py 独立模块 (~170行)
  提取内容: 完整的 Markdown→HTML 转换器
  风险: 中 — 解析器逻辑精密，需配套单元测试
  前置条件: 先编写 _md_to_html 的单元测试覆盖所有 block 类型
  工作量: ~1.5小时（含测试编写）

Step 12: DEFAULT_TEMPLATE 外置
  Before: report_generator.py 内嵌 218 行 HTML 模板字符串
  After:  mcp/templates/report_base.html（已有加载逻辑，只需确保文件存在即可）
  提取内容: 模板字符串 → 文件
  风险: 极低 — 加载逻辑已存在 (L519-524)
  工作量: ~15分钟
```

---

### 五、重构后预期效果

| 指标 | 重构前 | 重构后 | 变化 |
|------|--------|--------|------|
| 总代码行数 | 2,683 | ~2,100 | -22% |
| 重复代码 | ~400行 | ~20行 | -95% |
| 最大函数行数 | 158 (screen_stocks) | ~40 | -75% |
| 可独立测试函数数 | ~12 | ~35 | +190% |
| 外部依赖点 | 分散 | 集中于 2 个 helper 模块 | 可控 |

---

### 六、基线测试结果

```
✅ 基线验证: 工具注册成功
```

**详细结果:**
- 5 个模块均成功 import 并完成 `register_tools(mcp)` 调用
- 工具注册无运行时异常
- **注意**: 存在 NumPy 2.x 与 pyarrow/numexpr/bottleneck 的兼容性警告（`_ARRAY_API not found`），
  这是环境层面的依赖版本冲突，不影响工具注册但可能影响运行时 pandas 功能
- `mcp.list_tools()` 返回 coroutine（异步方法），验证脚本中未 await，但不影响注册验证

**环境风险提示:**
```
⚠️ NumPy 2.2.6 与 pyarrow/numexpr/bottleneck 编译版本不兼容
   建议: pip install "numpy<2" 或重新编译相关包
   影响范围: pandas 的高性能计算路径可能回退到纯 Python
```

---

### 七、新增公共模块建议

重构应新增以下文件:

```
mcp/utils/
├── __init__.py          # 已有，更新导出
├── formatters.py        # 已有，扩展 df_to_records + safe_number
├── cache.py             # 已有，未被任何工具使用 ⚠️
├── index_io.py          # 新增：index.json 读写
├── akshare_helpers.py   # 新增：akshare 多API fallback + 宏观指标工厂
├── yfinance_helpers.py  # 新增：yfinance 价格快照
└── markdown.py          # 新增：Markdown→HTML 转换器
```

**⚠️ 发现**: `utils/cache.py` 已实现完整的缓存系统（DataCache 类 + TTL 支持），
但 **16个工具函数无一使用缓存**。Phase 2 应将缓存集成到高频调用的工具中
（尤其是 `get_macro_china`/`get_macro_global` 的 overview 模式，串行7个API极慢）。

---

## Next Action

请架构师基于本报告:

1. **确认重构顺序** — 是否按 Phase 2-A → 2-E 的顺序执行？
2. **决定缓存集成优先级** — 是否在 Phase 2 同步集成 `DataCache`？
3. **分配任务** — 每个 Step 可独立并行分配给不同 Agent
4. **测试策略** — 建议为每个 Step 先写测试再重构（TDD）

---

*报告生成时间: 2026-04-02 08:41*
*审查范围: mcp/tools/ 5个模块 + mcp/utils/ 3个模块*
*总扫描代码: 2,683行工具代码 + 459行工具函数*
