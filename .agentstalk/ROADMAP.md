# 投研助手路线图 v2.1

> 创建时间：2026-04-02
> 更新日期：2026-04-03 (v2.1 — 快消研报实战 + MCP评估 + 数据源修复)
> 版本历史：v1.0 初版 → v1.1 添加P0数据质量修复 → v2.0 全面审计+阶段重规划 → **v2.1 MCP实战评估+数据源加固**

---

## 一、项目总览

**投研助手** 是一个多智能体协作的金融投研平台，通过 MCP Server 集成数据获取、基本面/技术面分析、HTML 研报生成及前端知识库，目标是产出具有实操指导意义的独家产业研报。**当前处于"功能MVP已就绪、工程化加固进行中"阶段**——核心投研流水线已跑通首份深度研报，但测试覆盖、数据可靠性保障、以及研报内容多元化仍是下一阶段重点。

---

## 二、已完成里程碑（按时间线）

### 里程碑 1：基础设施搭建 (04-02 早间)

| 时间 | 完成项 | 负责Agent |
|------|--------|-----------|
| 08:00 | 项目初始化：AGENTS.md、README.md、目录结构 | coord_agent |
| 08:00 | 前端 Landing Page：index.html + index.json + 示例研报 | frontend_agent |
| 08:00 | SOP文档：研报撰写SOP.md、多Agent协作SOP.md | content_agent |
| 08:00 | 基础工具链：fetch_index_data.py、init_report.py、update_index_json.py | tools_agent |
| 08:00 | MCP配置：mcp/.mcp.json + README.md | tools_agent |
| 08:00 | HTML 研报模板：templates/report-template.html | content_agent |

### 里程碑 2：MCP Server v0.1.0 功能基线 (04-02 08:00-08:20)

| 完成项 | 详情 |
|--------|------|
| MCP Server 16个工具 | 数据获取8个 + 分析3个 + 研报生成3个 + 知识库2个 |
| 架构审查 (archreview) | 修复3个Critical + 3个High + 1个Medium 问题 |
| 技术对标 (techresearch) | 对标7个GitHub开源MCP项目，产出改进建议 |
| SOP质量评估框架 | 10+5维评分矩阵（满分150分），当前评分104/150 |
| 脚本质量验证体系 | 推荐ruff + mypy + pytest + Pandera工具链 |
| 迭代闭环方法论 | 8节点迭代架构 + 3套Agent评审Prompt模板 |

### 里程碑 3：Phase 2 工程加固 (04-02 08:20-09:35)

| 完成项 | 详情 |
|--------|------|
| Pydantic配置管理 | `research_mcp/config.py` — BaseSettings + 环境变量前缀 MCP_ |
| 统一错误处理 | `research_mcp/utils/errors.py` — @handle_errors 装饰器 100% 覆盖 |
| 工具函数可测试化 | 所有 fetch_* 提取为模块级纯函数 + register_tools 薄包装器 |
| Phase 2 代码审查 | 重构质量 4.5/5，16 工具注册通过 |
| MCP Server 扩展至 29 个工具 | 新增: ETF/可转债/期货/基本面/技术分析/信号 等13个工具 |
| MCP三端安装 | Claude Desktop + Kimi CLI + VS Code Copilot 全部配置完毕 |
| 测试基础设施 | pytest 框架 + conftest.py + 12个测试文件，186 passed |

### 里程碑 4：数据管道 & 工具完善 (04-02 09:00-12:00)

| 完成项 | 详情 |
|--------|------|
| 数据管道脚本 | fetch_macro_data.py / fetch_stock_daily.py / fetch_futures.py |
| UBS 绘图工具 | chart_style.py + chart_generator.py + ubs.mplstyle |
| 技术分析工具 | 基础版(8大指标) + 增强版(形态识别/融资融券/评分系统) |
| 基本面调研方法论 | 7大分析维度覆盖度评估 + _EM→_THS fallback 策略 |
| NumPy兼容性修复 | requirements.txt 锁定 numpy<2，解决 _ARRAY_API 崩溃 |
| 市值币种标注修复 | 新增 market_cap_unit 字段（亿CNY/USD/HKD） |

### 里程碑 5：首份深度研报 (04-02 15:30-16:45)

| 完成项 | 详情 |
|--------|------|
| 华工科技(000988.SZ)数据收集 | 6个JSON数据文件，4个Agent并行，22分钟完成 |
| 华工科技深度研报 | ~4,500字，含行业竞争格局+三大业务拆解+估值分析 |
| 多Agent协作验证 | DataAgent + ResearchAgent + MacroAgent + HubAgent 并行流水线验证 |

### 里程碑 6：P0 数据质量修复 & 自动化 (04-02 16:00-19:30)

| 完成项 | 详情 |
|--------|------|
| 数据质量SOP | SOP/数据获取SOP.md — 强制yfinance + 验证checklist |
| 数据验证中间件 | tools/data_validator.py — 股价/市值/PE范围校验 |
| 代码审查报告 | CODE_REVIEW_REPORT.md — P0/P1/P2分级问题清单 |
| 多Agent并行任务 | MCP-Fixer(导入修复) + Pipeline-Auto(crontab/logrotate) + Template-Enhancer(模板增强) |
| 数据管道自动化 | crontab配置 + run.sh统一运行脚本 + logrotate日志轮转 |
| 研报模板增强 | 图表占位符/风险提示/同业对比表/分析师栏/页脚增强 样式 |
| 质量评分常量驱动化 | _QUALITY_CRITERIA 常量替代硬编码评分逻辑 |

### 里程碑 7：其他研报产出 (04-02 全天)

| 研报 | ID | 状态 |
|------|----|------|
| 新能源汽车产业链2026Q1基本面追踪 | RPT-2026-001 | ✅ 已发布 |
| AI算力产业链景气度跟踪 | RPT-2026-002 | ✅ 已发布 |
| 华工科技深度研究报告 | RPT-2026-003 | ✅ 已发布 |
| ICT行业2026-2027业绩展望 | — | ✅ 文件存在，未注册到index.json |

### 里程碑 8：附加调研报告

| 报告 | 内容 |
|------|------|
| Git历史清理调研 | git-filter-repo vs BFG 对比，推荐方案 |
| 政策监控模块 | policy_monitor/core.py + websites.yaml + SOP.md |

### 里程碑 9：快消研报实战 + MCP评估 + 数据源加固 (04-03)

| 完成项 | 详情 |
|--------|------|
| 中国快消行业深度研究（已撤回） | 尝试使用MCP工具链撰写产业研报，发现MCP使用率仅~5%，大量数据改用web_search获取 |
| MCP工具链使用评估 | 系统性评估29个工具的可用性，产出评分5.3/10，详见 .agentstalk/20260403_analyst_to_all_mcp-usage-evaluation.md |
| **数据源Fallback审计** | 发现仅28%工具函数(5/18)有非akshare备源；macro_data.py 100%依赖akshare且0缓存 |
| **rate_limiter.py** | 新增 `utils/rate_limiter.py` — 令牌桶限速器(每2秒1次) + 指数退避重试装饰器 |
| **@handle_errors 增强** | 支持 `max_retries` + 指数退避，自动区分可重试异常(Timeout/Connection)和业务错误 |
| **macro_data.py 缓存集成** | 为 fetch_macro_china/global 添加 DataCache 集成(TTL=24h)，overview模式不再串行7次API |
| **macro_data.py 限速** | 所有 akshare 直调函数添加 akshare_limiter.wait() 限速 |
| **data_validator.py 类型安全修复** | 修复净利润/营收非数值时 abs()/乘法 TypeError 崩溃(L208/215) |

### 里程碑 10：宏观数据源重构 (04-03 下午)

| 完成项 | 详情 |
|--------|------|
| 中国快消行业深度研究（已撤回） | 尝试使用MCP工具链撰写产业研报，发现MCP使用率仅~5%，大量数据改用web_search获取 |
| MCP工具链使用评估 | 系统性评估29个工具的可用性，产出评分5.3/10，详见 .agentstalk/20260403_analyst_to_all_mcp-usage-evaluation.md |
| **数据源Fallback审计** | 发现仅28%工具函数(5/18)有非akshare备源；macro_data.py 100%依赖akshare且0缓存 |
| **rate_limiter.py** | 新增 `utils/rate_limiter.py` — 令牌桶限速器(每2秒1次) + 指数退避重试装饰器 |
| **@handle_errors 增强** | 支持 `max_retries` + 指数退避，自动区分可重试异常(Timeout/Connection)和业务错误 |
| **macro_data.py 缓存集成** | 为 fetch_macro_china/global 添加 DataCache 集成(TTL=24h)，overview模式不再串行7次API |
| **macro_data.py 限速** | 所有 akshare 直调函数添加 akshare_limiter.wait() 限速 |
| **data_validator.py 类型安全修复** | 修复净利润/营收非数值时 abs()/乘法 TypeError 崩溃(L208/215) |

---

### 3.1 模块成熟度矩阵

| 模块 | 成熟度 | 说明 |
|------|--------|------|
| **MCP Server (research_mcp)** | 🟢 完善 | 29个工具，Pydantic配置，统一错误处理(含重试)，186测试通过 |
| **数据获取层** | 🟡 基本可用 | yfinance/akshare双源+rate_limiter限速，macro缓存已启用，但仅28%函数有fallback |
| **数据验证** | 🟢 完善 | data_validator.py 覆盖股价/市值/PE/财报验证，类型安全已修复 |
| **技术分析** | 🟢 完善 | 8大指标 + 形态识别 + 综合评分，MCP工具已注册 |
| **基本面分析** | 🟡 基本可用 | 7维覆盖，_EM→_THS fallback，但估值分位数/客户集中度待补 |
| **研报生成** | 🟡 基本可用 | Markdown→HTML，模板增强，但图表嵌入仍需手动 |
| **前端知识库** | 🟡 基本可用 | index.html 搜索/筛选可用，缺分页/排序/移动端优化 |
| **数据管道自动化** | 🟡 基本可用 | crontab/run.sh/logrotate 已配置，未实际部署验证 |
| **SOP文档体系** | 🟡 基本可用 | 4份SOP(研报/数据/协作/政策)，评分104/150 |
| **测试覆盖** | 🟡 基本可用 | research_mcp 186测试通过，但 tools/ scripts/ 零测试 |
| **CI/CD** | 🔴 需改进 | 无GitHub Actions，无pre-commit hooks |
| **环境管理** | 🔴 需改进 | 运行在conda base环境，未创建项目专属venv |
| **政策监控** | 🔴 需改进 | 框架代码存在，配置硬编码，未集成到MCP |
| **研报内容多元化** | 🔴 需改进 | 仅有微观/产业链研报，缺宏观策略/期货/晨会纪要 |
| **图表自动化** | 🔴 需改进 | chart_generator存在但未与研报生成流水线集成 |

### 3.2 量化指标

| 指标 | 数值 |
|------|------|
| MCP 工具总数 | 29 |
| 核心代码行数 | ~5,000+ 行 (research_mcp + tools + scripts) |
| 测试通过数 | 186 passed, 1 skipped |
| 已发布研报 | 3 份 (均已注册index.json) |
| SOP文档 | 4 份 |
| .agentstalk通信记录 | 30+ 份 |
| Python依赖 | 8 个核心包 (numpy<2 已锁定) |
| MCP客户端覆盖 | 3端 (Claude Desktop / Kimi CLI / VS Code) |
| **MCP实战使用率** | **~5% (快消研报场景)** |
| **Fallback覆盖率** | **33% (6/18个函数有非akshare备源)** |
| **缓存启用率** | **market_data 100% + macro_data 100% (新增)** |

---

## 四、下一阶段规划

### Phase 3.5：MCP 数据源修复 (优先级 P0 — 进行中)

> **目标**：修复本次使用中发现的核心数据获取问题

| # | 任务 | 详情 | 状态 |
|---|------|------|------|
| 3.5.1 | **screen_stocks yfinance fallback** | `fetch_screen_stocks` 直接调用akshare，代理环境下失败 | ⏳ 待完成 |
| 3.5.2 | **get_industry_ranking 备源** | ✅ 新增 `fallback_sources.py`，push2直连+新浪双备源，18项测试全通过 | ✅ 已完成 |
| 3.5.3 | **宏观数据源重构** | ✅ 已完成。修复3个根因：(1) `_safe_records()` 数据排序问题 → 按日期排序；(2) akshare函数名错误 → `macro_bank_usa_interest_rate`/`macro_euro_cpi_yoy`；(3) 中文日期格式解析 → `2025年第1季度`→`2025-Q1` | ✅ 已完成 (2026-04-03) |
| 3.5.4 | ~~WebSearch API 修复~~ | ~~`mcp__MiniMax__web_search` 返回token错误~~ | 🔄 外部依赖 |
| 3.5.5 | **Rate Limiting 优化** | 全局限速器 + 指数退避重试 | ✅ 已完成 (rate_limiter.py + handle_errors增强 + macro_data限速) |
| 3.5.6 | **返回值格式统一** | 统一错误返回格式 `{"success": false, "error": {...}}` | ⏳ 待完成 |
| 3.5.7 | **macro_data 缓存集成** | overview模式串行7个API极慢，启用DataCache(TTL=24h) | ✅ 已完成 |
| 3.5.8 | **data_validator 类型安全** | 非数值类型导致 TypeError 崩溃 | ✅ 已完成 |
| 3.5.9 | **@handle_errors 重试支持** | 支持 max_retries 参数，自动区分可重试/不可重试异常 | ✅ 已完成 |

### Phase 4：工程稳固 & 数据可靠性 (优先级 P0)

> **目标**：确保数据正确性与系统可靠性，消除"研报数据不可信"的根本风险

#### 任务清单

| # | 任务 | 详情 | 依赖 | 验收标准 |
|---|------|------|------|----------|
| 4.1 | **创建项目虚拟环境** | `python3 -m venv .venv`，从 conda base 迁移 | 无 | `.venv/` 可正常运行所有脚本和MCP Server |
| 4.2 | **启用缓存系统** | 将 `utils/cache.py` 集成到高频数据获取工具中 (尤其是 macro_china/macro_global) | 无 | 宏观数据overview模式响应 <5s (当前串行7个API极慢) |
| 4.3 | **数据管道日期过滤修复** | fetch_futures.py 的 start_date/end_date 参数实际生效 | 无 | `--start_date 20240101 --end_date 20260101` 返回正确范围 |
| 4.4 | **ICT研报注册到index.json** | 将已存在的 ICT 行业研报注册到知识库 | 无 | index.json含该条目，Landing Page可见 |
| 4.5 | **测试报告条目清理** | 删除 index.json 中的测试条目 (RPT-20260402193234) | 无 | index.json 无测试数据 |
| 4.6 | **pre-commit hooks** | 安装 ruff + 基础 lint 检查 | 4.1 | `git commit` 自动触发格式检查 |

### Phase 5：测试 & 质量门禁 (优先级 P1)

> **目标**：建立自动化质量保障体系，防止回归

#### 任务清单

| # | 任务 | 详情 | 依赖 | 验收标准 |
|---|------|------|------|----------|
| 5.1 | **tools/ 目录单元测试** | 为 fetch_stock_data / data_validator / technical_analysis 编写 pytest 用例 | Phase 4 | 工具模块测试覆盖率 > 60% |
| 5.2 | **数据管道集成测试** | mock akshare/yfinance 的端到端测试 | Phase 4 | scripts/data-pipeline/ 有对应测试 |
| 5.3 | **Markdown→HTML 单元测试** | 为 _md_to_html 手写解析器编写专项测试 | 无 | 覆盖所有 block 类型 (代码块/表格/标题/列表) |
| 5.4 | **GitHub Actions CI** | push/PR 触发 lint + test | 5.1 | CI badge 绿色 |
| 5.5 | **数据质量 Pandera 规则** | 为宏观/个股数据定义 Schema 约束 | 5.1 | 异常数据自动阻断 |

### Phase 6：研报产能 & 内容多元化 (优先级 P1)

> **目标**：扩大研报覆盖面，验证投研流水线的通用性

#### 任务清单

| # | 任务 | 详情 | 依赖 | 验收标准 |
|---|------|------|------|----------|
| 6.1 | **宏观策略研报** | 2026Q2全球宏观展望（CPI/PMI/美联储/中国政策周期） | 无 | 已发布HTML + 注册index.json |
| 6.2 | **期货专题研报** | 铜/原油/黄金基本面追踪（利用已有期货数据工具） | 无 | 已发布HTML + 利用 get_futures_* MCP工具 |
| 6.3 | **多模板支持** | 宏观策略模板 / 晨会纪要模板 / 行业比较模板 | 无 | templates/ 目录下3个以上模板 |
| 6.4 | **研报图表自动嵌入** | chart_generator → SVG/Base64 → HTML 内联 | 无 | 研报中包含至少1张自动生成的图表 |
| 6.5 | **个股深度研报MCP流水线** | 封装"选题→数据→分析→撰写→发布"全流程为可复用MCP | 6.1-6.4 | 一句话触发自动生成深度研报 |

### Phase 7：MCP Server 工程优化 (优先级 P2)

> **目标**：提升MCP Server的健壮性和可维护性

#### 任务清单

| # | 任务 | 详情 | 依赖 | 验收标准 |
|---|------|------|------|----------|
| 7.1 | **消除重复代码** | _read_index (D1) / _df_to_records (D5,D10) / 宏观指标闭包 (D2) 等 | 无 | 重复代码 <50行 (当前~400行) |
| 7.2 | **Pydantic Input/Output 模型** | 为核心工具添加输入验证和类型安全 | 无 | 至少5个工具有 I/O 模型 |
| 7.3 | **akshare/yfinance helper统一** | 提取 try_akshare_apis / yf_price_snapshot 通用函数 | 7.1 | 4处 akshare fallback 和 5处 yfinance 重复消除 |
| 7.4 | **screen_stocks 拆分** | 158行巨型函数 → 纯函数 filter/sort/format | 7.1 | 最大函数 <50 行 |
| 7.5 | **pyproject.toml 规范化** | 替代 requirements.txt，统一项目元数据 | 无 | `pip install -e .` 可用 |
| 7.6 | **条件性工具加载** | 按数据源可用性动态启用/禁用工具 | 7.2 | 无 akshare 环境仍可启动 Server |

### Phase 8：生态扩展 (优先级 P3)

> **目标**：平台能力延伸

#### 任务清单

| # | 任务 | 详情 | 依赖 |
|---|------|------|------|
| 8.1 | 政策监控集成 | policy_monitor 配置外置 + 接入MCP工具 | Phase 7 |
| 8.2 | PDF导出 | HTML → PDF（weasyprint/puppeteer） | Phase 6 |
| 8.3 | 研报版本管理 | 修订/更新/撤回机制 | Phase 6 |
| 8.4 | 估值历史分位数 | PE/PB 历史分位数计算工具 | Phase 7 |
| 8.5 | WebSocket 实时推送 | 行情实时订阅 | Phase 7 |
| 8.6 | 多Agent研报交叉审核 | Agent互相审阅、质疑、修正 | Phase 6 |
| 8.7 | Docker 集成测试 | 多数据源端到端验证 | Phase 5 |

---

## 五、技术债务清单

| # | 技术债 | 严重度 | 来源 | 建议处理时间 |
|---|--------|--------|------|-------------|
| TD-1 | **缓存已实现但未使用** — `utils/cache.py` DataCache 类功能完整，但16→29个工具函数均未调用 | 🟠 高 | Phase 2 代码审查 | Phase 4 |
| TD-2 | **重复代码 ~400行** — _read_index / _df_to_records / 14个宏观闭包 / _safe_float 等 | 🟠 高 | Phase 2 基线审查 | Phase 7 |
| TD-3 | **screen_stocks 158行巨函数** — 高圈复杂度，列名映射硬编码 | 🟡 中 | Phase 2 基线审查 | Phase 7 |
| TD-4 | **tools/ scripts/ 零测试** — MCP外的脚本无任何自动化测试保障 | 🟠 高 | 代码审查报告 | Phase 5 |
| TD-5 | **运行在conda base环境** — 全局依赖冲突风险 | 🟡 中 | 兼容性修复通信 | Phase 4 |
| TD-6 | **UBS绘图样式双源** — chart_style.py 与 ubs.mplstyle 配色定义重复 | 🟡 中 | dev_review 报告 | Phase 7 |
| TD-7 | **index.json含测试数据** — 测试条目(RPT-20260402193234)未清理 | 🟢 低 | 当前审计 | Phase 4 |
| TD-8 | **ICT研报未注册** — 文件存在但 index.json 无对应条目 | 🟢 低 | 当前审计 | Phase 4 |
| TD-9 | **fcntl 仅Unix** — report_generator.py 文件锁跨平台不兼容 | 🟢 低 | 代码审查 | Phase 8+ |
| TD-10 | **policy_monitor 配置硬编码** — websites.yaml 路径硬编码在 core.py 中 | 🟡 中 | 代码审查报告 | Phase 8 |
| TD-11 | **_apply_period_data 性能隐患** — 循环调用最多60次网络请求无超时/采样限制 | 🟡 中 | Phase 2 基线审查 | Phase 7 |
| TD-12 | **.venv/ 误提交到 Git 历史** — 仓库体积膨胀，已有 git-filter-repo 清理方案 | 🟡 中 | Git清理调研 | Phase 4 |
| TD-13 | **_safe_float() 返回值不一致** — company_analysis返回"N/A"(str)，fundamental_analysis返回None，下游处理需要分别兼容 | 🟠 高 | 里程碑9审计 | Phase 4 |
| TD-14 | **macro_data.py 不走 data_source.py** — 直接调用 `ak.*` 而非 `call_akshare()`，缺少统一的代理控制/重试/缓存 | 🟠 高 | 里程碑9审计 | Phase 4 |
| TD-15 | **config.py timeout 未强制执行** — akshare_timeout/yfinance_timeout 配置存在但未传递给实际 API 调用 | 🟡 中 | 里程碑9审计 | Phase 5 |

---

## 六、风险项

| # | 风险 | 可能性 | 影响 | 缓解措施 |
|---|------|--------|------|----------|
| R-1 | **akshare API 名称变更** — akshare 频繁更新，函数名可能失效 | 🟠 高 | 数据获取工具批量失效 | 多API名称 fallback 机制(已有) + 版本锁定 + 定期回归测试 |
| R-2 | **yfinance A股数据不稳定** — 部分代码(如创业板指399006.SZ)历史数据获取失败 | 🟡 中 | 部分个股/指数无法获取 | 双源 fallback(yfinance→akshare) + 数据缓存 |
| R-3 | **NumPy 2.x 生态迁移** — 当前锁定 numpy<2，但上游包终将要求 numpy≥2 | 🟡 中 | 长期依赖锁定不可持续 | 定期测试 numpy 2.x 兼容性，跟踪 pandas/pyarrow 更新 |
| R-4 | **研报数据失真复发** — Agent 绕过验证中间件 | 🟡 中 | 投资决策错误 | DataValidator 强制门禁 + SOP 约束 + 人工抽检 |
| R-5 | **Git 历史膨胀** — .venv/ 未清理，仓库体积大 | 🟢 低 | clone 缓慢 | 执行 git-filter-repo 清理方案(已调研) |
| R-6 | **单点依赖** — 项目依赖免费API，无付费数据源备份 | 🟡 中 | 数据质量上限有限 | 后续考虑 Tushare Pro / Wind 付费接入 |
| R-7 | **MCP工具链实战可用性低** — 快消研报场景仅~5%使用率，Agent倾向跳过MCP直接web_search | 🟠 高 | 研报质量与效率受限 | 改善数据源可靠性 + 添加行业级分析工具 + 提升fallback覆盖率 |

---

## 七、MCP 工具全景 (29个)

### 行情数据 (10)
| 工具 | 功能 | 数据源 |
|------|------|--------|
| get_stock_realtime | A/港/美实时行情 | akshare + yfinance |
| get_stock_history | 历史K线 | akshare + yfinance |
| get_index_quote | 主要股指 | akshare + yfinance |
| get_forex | 汇率 | akshare |
| get_commodity | 大宗商品 | akshare + yfinance |
| get_etf_realtime | ETF实时 | akshare |
| get_etf_history | ETF历史 | akshare |
| get_convertible_bond | 可转债 | akshare |
| get_futures_realtime | 期货实时 | akshare |
| get_futures_history | 期货历史 | akshare |

### 期货专项 (2)
| get_futures_position | 持仓数据 | akshare |
| get_futures_basis | 基差数据 | akshare |

### 宏观分析 (3)
| get_macro_china | 中国宏观(GDP/CPI/PMI/M2等) | akshare |
| get_macro_global | 全球宏观(美联储/CPI/非农等) | akshare |
| get_fund_flow | 北向资金/行业资金流向 | akshare |

### 公司研究 (7)
| get_company_financials | 三大报表+核心指标 | akshare + yfinance |
| screen_stocks | 多条件选股 | akshare |
| get_industry_ranking | 行业景气度排名 | akshare + push2直连 + 新浪 |
| get_fundamental_profile | 基本面画像 | akshare |
| get_peer_comparison | 同行对标 | akshare |
| get_shareholder_analysis | 股东分析 | akshare |
| get_valuation_percentile | 估值分位 | akshare |

### 技术分析 (2)
| get_technical_indicators | 8大指标计算 | 内置计算 |
| get_technical_signal | 加权共识信号 | 内置计算 |

### 研报生成 (3)
| generate_report | Markdown→HTML研报 | 内置 |
| create_data_table | 数据表格生成 | 内置 |
| register_report | 注册研报到index.json | 内置 |

### 知识库 (2)
| list_reports | 列出/筛选研报 | 内置 |
| search_reports | 关键词搜索 | 内置 |

---

## 八、文件结构 (当前)

```
投研助手/
├── .agentstalk/              # Agent协作目录 (30+ 通信记录)
│   ├── ROADMAP.md            # 本文件
│   ├── archived/             # 归档通信
│   └── backups/              # 回滚备份
├── index.html                # Landing Page ✅
├── index.json                # 研报索引 (5条，含1条测试待清理) ⚠️
├── AGENTS.md                 # Agent系统定义 ✅
├── README.md                 # 项目说明 ✅
├── requirements.txt          # Python依赖 (numpy<2 已锁定) ✅
├── CODE_REVIEW_REPORT.md     # 代码审查报告 ✅
├── MCP_INSTALL.md            # MCP安装指南 ✅
│
├── research_mcp/             # MCP Server 主体 ✅
│   ├── server.py             # FastMCP入口
│   ├── config.py             # Pydantic BaseSettings
│   ├── tools/                # 10个工具模块 (29个MCP工具)
│   ├── utils/                # 缓存/格式化/错误处理
│   ├── templates/            # 研报HTML模板
│   ├── tests/                # 12个测试文件, 186 passed
│   └── requirements.txt      # MCP专用依赖
│
├── SOP/                      # 标准作业程序 ✅
│   ├── 研报撰写SOP.md
│   ├── 数据获取SOP.md
│   ├── 多Agent协作SOP.md
│   ├── 政策获取SOP.md
│   └── sources/              # 数据源参考
│
├── reports/                  # 研报存储 (3份研报)
│   ├── 新能源汽车产业链2026Q1基本面追踪.html
│   ├── 20260402_AI算力产业链景气度跟踪/
│   └── 20260402_ICT行业2026-2027业绩展望.../
│
├── tools/                    # 独立工具脚本 ✅
│   ├── fetch_stock_data.py   # 个股数据(强制yfinance)
│   ├── fetch_index_data.py   # 指数数据
│   ├── data_validator.py     # 数据验证中间件
│   ├── technical_analysis.py # 基础技术指标
│   ├── technical_analysis_enhanced.py # 增强版技术分析
│   ├── chart_style.py        # UBS图表样式
│   ├── chart_generator.py    # 图表生成器
│   ├── init_report.py        # 研报初始化
│   └── update_index_json.py  # 知识库更新
│
├── scripts/
│   ├── data-pipeline/        # 数据管道 ✅
│   │   ├── fetch_macro_data.py / fetch_stock_daily.py / fetch_futures.py
│   │   ├── data_manager.py / scheduler.py
│   │   ├── run.sh / crontab.config / logrotate.conf
│   │   └── README.md
│   └── update-mcp.sh
│
├── policy_monitor/           # 政策监控 (框架阶段) ⚠️
│   ├── core.py / websites.yaml / SOP.md
│
├── styles/
│   └── ubs.mplstyle          # Matplotlib样式 ✅
├── templates/
│   └── report-template.html  # 研报HTML模板 ✅
├── docs/                     # 测试文档 ✅
│   ├── DATA_FETCH_TEST_GUIDE.md
│   ├── MCP_TEST_GUIDE.md
│   └── TECHNICAL_ANALYSIS_TEST_GUIDE.md
├── data/                     # 数据目录
│   ├── raw/ / cleaned/ / processed/
│   └── research/000988_华工科技/  # 研报原始数据
└── mcp/                      # MCP配置 (旧版，功能已迁移至 research_mcp/)
    └── utils/
```

---

## 九、数据源与方法论速查

### 数据源优先级（强制执行）

| 数据类型 | P0 首选 | P1 备选 | ❌ 禁止 |
|----------|---------|---------|---------|
| 股价/行情 | yfinance (000988.SZ格式) | 东方财富API (akshare) | WebSearch股价 |
| 财务报表 | yfinance (.financials) | 巨潮资讯网 | 券商预测值替代实际值 |
| 宏观指标 | AKShare(国统局封装) | FRED API | — |
| 期货 | AKShare + yfinance | — | — |

### 三层验证模型

```
宏观层 (Beta) → 行业中观 (轮动) → 公司微观 (Alpha)
     ↓                ↓               ↓
美林时钟/信贷     五力/产能周期     财务/估值/治理
     ↓                ↓               ↓
   资产配置         行业选择         个股筛选
```

### 数据验证 Checklist（每次出报前必检）

- [ ] 股价是否在合理范围 (A股一般 1-1000元)
- [ ] 市值是否与股价×股本匹配，币种标注正确
- [ ] 财报日期是否为最新已发布（非预测值）
- [ ] PE/PB 是否在合理范围
- [ ] 数据来源字段 (data_source) 已标注

---

## 十、备注

- **MCP 三端配置均指向源码**：代码变更即时生效，无需重新安装
- **numpy<2 是当前硬约束**：等待 pandas/pyarrow 上游完成 NumPy 2.x 兼容后解除
- **项目运行环境**：macOS, Python 3.10.8, Miniconda base (建议迁移至 .venv)
- **Git仓库**：.venv/ 误提交到历史，建议使用 git-filter-repo 清理
- **通信协议**：`.agentstalk/[timestamp]_[sender]_to_[receiver]_[topic].md`

---

## 补充：测试SOP要求 (2026-04-03)

### 新增规范

**测试代码绝对禁止Mock数据要求**已写入SOP：
- `SOP/数据获取SOP.md` - 第7.2节
- `SOP/测试编写SOP.md` - 完整文档

**核心要求：**
1. 测试代码必须使用真实API数据
2. 每个测试必须检查 `data_source != "mock"`
3. 每个测试必须设置超时控制
4. Mock数据视为测试失败

**背景：**
- 快消研报测试使用mock数据，导致MCP工具链实际不可用率95%
- 华工科技研报测试使用mock股价，未发现真实数据获取问题

**执行：**
- 所有编写测试的Agent必须阅读 `SOP/测试编写SOP.md`
- 代码审查必须检查mock数据使用情况
- 违规测试将被退回修改
