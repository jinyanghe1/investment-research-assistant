# 投研助手 (Investment Research Assistant)

> 金融级产业研报生成与可视化知识库。通过多 Agent 协同，将微观基本面与宏观政经数据深度融合，产出具有实操指导意义的独家研报，并以纯前端方式进行沉淀与展示。

## 核心特性

- **多 Agent 协同**：数据抓取、宏观分析、基本面分析、MCP 开发、前端渲染等 Agent 并行协作。
- **纯前端可视化**：基于 `index.html` + `index.json` 的动态研报知识库，支持关键词检索与分类筛选。
- **SOP & MCP 沉淀**：将优秀投研逻辑固化为标准作业程序（SOP）与可复用工具链（脚本 / MCP）。
- **严肃金融级专业度**：术语规范、逻辑严密，拒绝泛泛而谈。

## 仓库目录结构

```
.
├── AGENTS.md                 # Agent 行为规范与项目总览
├── README.md                 # 本文件
├── index.html                # 研报知识库入口（纯前端 Landing Page）
├── index.json                # 研报元数据索引（驱动 index.html）
├── .agentstalk/              # 多 Agent 通信目录（状态同步与任务交接）
├── data/                     # 原始数据与清洗后数据存放目录（由脚本自动生成）
├── mcp/                      # Model Context Protocol 配置与工具包（待填充）
├── reports/                  # 生成的研报 HTML 文件
├── scripts/                  # 轻量级数据抓取 / 清洗 / 追踪脚本（待填充）
├── SOP/                      # 投研标准作业程序（Markdown）
├── templates/                # 研报模板、HTML 组件模板等
└── tools/                    # 实用工具脚本（Python / Node.js）
```

> **当前状态速览**（截至 2026-04-02）：
> - **前端基础设施**：`index.html` 已搭建完成，具备搜索框、分类筛选与卡片网格渲染（Frontend Agent）。
> - **数据索引**：`index.json` 已更新为结构化格式（含 `reports` 数组与 `lastUpdated`），目前注册了 2 条宏观/产业研报元数据；同时保留了早期示例数据。
> - **研报内容**：`reports/sample-report-001.html` 已生成（示例研报）。`index.json` 中引用的 `macro-2026q2-global-outlook.html` 与 `micro-china-manufacturing-tariff.html` 尚在生成中。
> - **SOP 沉淀**：`SOP/多Agent协作SOP.md`、`SOP/研报撰写SOP.md` 已完成 v1.0 版本。
> - **工具链**：`tools/fetch_index_data.py`（A股指数日线数据抓取）、`tools/init_report.py`（研报项目初始化）已上架。
> - **模板**：`templates/report-template.html` 已提供标准化 HTML 研报模板。
> - **Agent 通信**：`.agentstalk/20260402_frontend_to_hub.md` 已同步前端 Agent 的完成状态。

## 快速开始

### 1. 查看研报

直接在浏览器中打开仓库根目录的 `index.html` 即可：

```bash
# macOS
open index.html

# Windows
start index.html

# Linux
xdg-open index.html
```

页面会自动读取 `index.json`，渲染研报列表。你可以通过顶部搜索框检索标题、标签或分类，也可以点击筛选标签进行快速分类。

### 2. 添加新研报

#### 方式 A：使用工具脚本快速初始化（推荐）

```bash
python3 tools/init_report.py --title "你的研报标题" --author "投研AI中枢"
```

该脚本会基于 `templates/report-template.html` 在 `reports/` 下创建日期命名的子文件夹和初始 HTML 文件。接下来：

1. 手动编辑生成的 HTML 文件，替换占位符内容。
2. 编辑 `index.json`，在 `reports` 数组中追加元数据记录：

```json
{
  "id": "RPT-2026-003",
  "title": "你的研报标题",
  "author": "投研AI中枢",
  "date": "2026-04-02",
  "category": "产业研究",
  "tags": ["标签1", "标签2"],
  "summary": "研报摘要...",
  "path": "reports/20260402_你的研报标题/index.html"
}
```

3. 刷新浏览器验证新研报是否正常显示。

#### 方式 B：手动创建

1. 在 `reports/` 下新建 HTML 文件，建议直接复制 `templates/report-template.html`。
2. 按上述步骤更新 `index.json`。
3. 验证页面渲染。

### 3. 运行工具脚本

#### 抓取 A 股指数日线数据

```bash
python3 tools/fetch_index_data.py --index hs300,cy --output data/
```

支持的指数：`hs300`（沪深300）、`cy`（创业板指）、`sz`（上证指数）。数据以 CSV 格式保存到 `data/` 目录。

> 在编写新脚本前，请先检查 `tools/`、`scripts/` 或 `mcp/` 是否已有可复用工具，避免重复造轮子。

## 多 Agent 协作规范

本项目采用 **Agentic Collaboration** 模式。所有 Agent 之间的状态同步、任务委派和数据交接，必须通过读写 `.agentstalk/` 目录下的文件完成。详细规范请参阅 `SOP/多Agent协作SOP.md`。

### 通信协议摘要

- **命名规范**：
  ```
  .agentstalk/[timestamp]_[sender]_to_[receiver]_[topic].md
  ```
  例如：`.agentstalk/20260402T160000_macro-agent_to_hub_policy-update.md`

- **内容规范**：每条通信文件建议包含：
  - **Task Status**：`IN_PROGRESS` / `COMPLETED` / `BLOCKED` / `REVIEW_NEEDED`
  - **Payload**：传递的数据、分析结论、文件路径、关键指标
  - **Next Action**：对接收方的明确执行请求与截止时间
  - **Notes**：补充说明、风险提示、假设条件

### 注意事项

- 不要直接修改其他 Agent 正在编写的文件，除非通信中已明确授权。
- 展现给最终用户的应该是结构清晰的研报或 UI，通信细节应留在 `.agentstalk/` 中。
- 每次完成投研分析后，需反思哪些环节可以脚本化或提炼为新的 MCP，并在 `.agentstalk/` 中通知相关 Agent。

## 贡献者指南

1. **遵循 AGENTS.md**：所有 Agent 在首次参与项目前，必须完整阅读 `AGENTS.md` 与 `SOP/多Agent协作SOP.md`，了解核心目标、工作流与执行原则。
2. **遵循研报撰写SOP**：撰写研报时请严格按照 `SOP/研报撰写SOP.md` 的七章框架与质量检查清单执行。
3. **优先复用**：在新建脚本、模板或 MCP 前，先检索已有目录，尽量基于现有资产扩展。
4. **保持最小变更**：每次提交应聚焦于单一目标（如新增一篇研报、修复一个脚本、更新一个 SOP），避免大而全的 PR。
5. **及时同步通信**：完成关键步骤后，在 `.agentstalk/` 中发送状态更新，确保并行 Agent 获取最新上下文。
6. **前端与数据一致性**：任何新增、删除或移动研报 HTML 文件的操作，都必须同步更新 `index.json`，确保 `index.html` 渲染正常。
7. **Git 提交规范**：
   - 使用中文提交信息，清晰描述变更内容。
   - 例如：`docs: 更新 README 与目录结构`、`feat(report): 添加新能源汽车产业链研报`、`feat(tools): 新增指数数据抓取脚本`。

---

如有疑问或需要协调，请在 `.agentstalk/` 中发起通信，或直接更新本 README 的相关章节。
