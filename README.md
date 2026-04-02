# 投研助手 (Investment Research Assistant)

> 金融级产业研报生成与可视化知识库。通过多 Agent 协同，将微观基本面与宏观政经数据深度融合，产出具有实操指导意义的独家研报，并以纯前端方式进行沉淀与展示。

## 核心特性

- **多 Agent 协同**：数据抓取、宏观分析、MCP 开发、前端渲染等 Agent 并行协作。
- **纯前端可视化**：基于 `index.html` + `index.json` 的动态研报知识库，支持关键词检索与分类筛选。
- **SOP & MCP 沉淀**：将优秀投研逻辑固化为标准作业程序（SOP）与可复用工具链（MCP / 脚本）。
- **严肃金融级专业度**：术语规范、逻辑严密，拒绝泛泛而谈。

## 仓库目录结构

```
.
├── AGENTS.md                 # Agent 行为规范与项目总览
├── README.md                 # 本文件
├── index.html                # 研报知识库入口（纯前端 Landing Page）
├── index.json                # 研报元数据索引（驱动 index.html）
├── .agentstalk/              # 多 Agent 通信目录（状态同步与任务交接）
├── mcp/                      # Model Context Protocol 配置与工具包
├── reports/                  # 生成的研报 HTML 文件
├── scripts/                  # 轻量级数据抓取 / 清洗 / 追踪脚本
├── SOP/                      # 投研标准作业程序（Markdown）
└── templates/                # 研报模板、HTML 组件模板等
```

> **当前状态速览**（截至 2026-04-02）：
> - `index.html` 已搭建完成，具备搜索框、分类筛选与卡片网格渲染。
> - `index.json` 已初始化，并收录了示例研报元数据（`RPT-2026-001`）。
> - `reports/`、`scripts/`、`SOP/`、`mcp/`、`templates/` 目录已创建，等待各专项 Agent 填充内容。
> - `.agentstalk/` 暂无其他 Agent 的通信文件，说明各子任务尚处于起步阶段。

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

页面会自动读取 `index.json`，渲染研报列表。你可以通过顶部搜索框检索标题、标签或分类，也可以点击“宏观 / 微观”标签进行快速筛选。

### 2. 添加新研报

1. **撰写研报**：在 `reports/` 下新建 HTML 文件（例如 `reports/my-report-001.html`）。建议复用 `templates/` 中的排版模板。
2. **注册元数据**：编辑根目录的 `index.json`，在数组中追加一条新记录，格式如下：

```json
{
  "id": "RPT-2026-002",
  "title": "你的研报标题",
  "author": "投研AI中枢",
  "date": "2026-04-02",
  "tags": ["标签1", "标签2"],
  "category": "宏观",
  "filePath": "reports/my-report-001.html"
}
```

3. **验证**：刷新浏览器中的 `index.html`，确认新研报卡片正常显示且链接可点击。

### 3. 运行工具脚本

`scripts/` 目录用于存放数据抓取、清洗或监控脚本。运行方式取决于脚本语言：

```bash
# 示例：运行 Python 脚本
python scripts/fetch_data.py

# 示例：运行 Node.js 脚本
node scripts/fetch_data.js
```

> 在编写新脚本前，请先检查 `mcp/` 或 `scripts/` 是否已有可复用的 MCP / 工具，避免重复造轮子。

## 多 Agent 协作规范

本项目采用 **Agentic Collaboration** 模式。所有 Agent 之间的状态同步、任务委派和数据交接，必须通过读写 `.agentstalk/` 目录下的文件完成。

### 通信协议

- **命名规范**：
  ```
  .agentstalk/[timestamp]_[sender]_to_[receiver]_[topic].md
  ```
  例如：`.agentstalk/20260402_001200_macroAgent_to_hub_status.md`

- **内容规范**：每条通信文件必须包含以下字段：
  - **Task Status**：任务当前状态（如 `IN_PROGRESS`、`COMPLETED`、`BLOCKED`）。
  - **Payload**：传递的数据、关键结论或文件列表。
  - **Next Action**：对接收方 Agent 的明确执行请求。

### 注意事项

- 不要直接修改其他 Agent 正在编写的文件，除非通信中已明确授权。
- 展现给最终用户的应该是结构清晰的研报或 UI，通信细节应留在 `.agentstalk/` 中。
- 每次完成投研分析后，需反思哪些环节可以脚本化或提炼为新的 MCP，并在 `.agentstalk/` 中通知相关 Agent。

## 贡献者指南

1. **遵循 AGENTS.md**：所有 Agent 在首次参与项目前，必须完整阅读 `AGENTS.md`，了解核心目标、工作流与执行原则。
2. **优先复用**：在新建脚本、模板或 MCP 前，先检索已有目录，尽量基于现有资产扩展。
3. **保持最小变更**：每次提交应聚焦于单一目标（如新增一篇研报、修复一个脚本、更新一个 SOP），避免大而全的 PR。
4. **及时同步通信**：完成关键步骤后，在 `.agentstalk/` 中发送状态更新，确保并行 Agent 获取最新上下文。
5. **前端与数据一致性**：任何新增、删除或移动研报 HTML 文件的操作，都必须同步更新 `index.json`，确保 `index.html` 渲染正常。
6. **Git 提交规范**：
   - 使用中文提交信息，清晰描述变更内容。
   - 例如：`docs: 初始化 README.md` 或 `feat: 添加新能源汽车产业链研报`。

---

如有疑问或需要协调，请在 `.agentstalk/` 中发起通信，或直接更新本 README 的相关章节。
