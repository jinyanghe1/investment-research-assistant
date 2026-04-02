# Agent通信文件：迭代闭环方法论调研报告

---

## Metadata

| 字段 | 值 |
|------|------|
| **Timestamp** | 2026-04-02T08:13:00+08:00 |
| **Sender** | researcher-agent |
| **Receiver** | architect-agent |
| **Topic** | AI Agent + MCP 生态下 SOP 和工具的迭代闭环方法论 |
| **Priority** | HIGH |
| **Format** | 深度调研报告 |

## Task Status

- **状态**: ✅ COMPLETED
- **进度**: 全部5个调研课题已完成
- **数据源**: 6次 web search，覆盖学术论文（NeurIPS/Nature/arXiv）、行业实践（Anthropic/Stanford/Grab）、开源项目（DSPy/TextGrad/MCP-Radar）

---

## Payload

---

# 一、Agent-Driven SOP 迭代范式

## 1.1 Self-Refine 范式

**核心论文**: *Self-Refine: Iterative Refinement with Self-Feedback* (NeurIPS 2023, Madaan et al.)
- **机制**: LLM 生成初始输出 → 同一 LLM 自我批评 → 生成改进建议 → 迭代精炼，直到满足质量阈值
- **效果**: 无需额外训练数据或强化学习，任务性能绝对提升约 20%
- **应用到SOP**: Agent 执行 SOP → 收集执行日志（耗时、错误率、输出质量评分）→ 自动识别瓶颈步骤 → 生成改进版 SOP → 人工确认后更新

**Self-Refine 应用于 SOP 的具体流程**:
```
SOP v1.0 → Agent执行 → 执行日志收集 → Self-Critique Prompt:
  "审查以下SOP执行日志，识别：
   1. 耗时最长的步骤
   2. 失败率最高的步骤  
   3. 输出质量最低的步骤
   给出具体改进建议。"
→ 改进建议 → SOP v1.1
```

## 1.2 Constitutional AI 思路应用于 SOP 审核

**来源**: Anthropic Constitutional AI + 2026年 MarkTechPost/CIO 文章

**核心思路**: 将 SOP 的质量准则编码为"宪法"（Constitution），Agent 在执行和审核时以此为裁判标准。

**SOP 宪法示例**:
```yaml
sop_constitution:
  completeness:
    - "每个步骤必须有明确的输入和输出定义"
    - "每个决策点必须有分支条件"
  accuracy:
    - "所有数据源引用必须可验证"
    - "数值计算必须标注单位和精度"
  timeliness:
    - "数据获取步骤必须标注数据时效性（T+0/T+1/周频/月频）"
  actionability:
    - "结论部分必须包含具体操作建议，而非模糊描述"
```

**双Agent架构**:
- **Worker Agent**: 执行 SOP，产出研报
- **Auditor Agent**: 对照宪法逐条审核，标记违规项，打分

## 1.3 Agent-as-Auditor 机制

**实现模式**: 用一个独立 Agent 审核另一个 Agent 产出的 SOP/研报

**关键设计**:
1. **职责分离**: Worker 和 Auditor 使用不同的 system prompt，避免自我偏见
2. **审核维度结构化**: 使用打分表（Rubric）而非开放式评论
3. **仲裁机制**: 当 Worker 和 Auditor 意见分歧时，引入第三个 Arbiter Agent 或人工介入

## 1.4 关键开源项目与论文

| 项目/论文 | 核心能力 | 与SOP迭代的关联 |
|-----------|---------|-----------------|
| **DSPy** (Stanford, github.com/stanfordnlp/dspy) | 声明式LLM流水线编译与自动优化 | 将SOP步骤建模为DSPy Module，自动优化prompt |
| **TextGrad** (Nature 2025, github.com/zou-group/textgrad) | 反向传播LLM反馈优化 | 用LLM反馈梯度优化SOP中的prompt片段 |
| **Self-Refine** (NeurIPS 2023, arxiv:2303.17651) | 无监督迭代自我精炼 | SOP执行→自评→改进的核心范式 |
| **Grab SOP-Driven Agent** (engineering.grab.com) | SOP驱动的LLM Agent框架 | 企业级SOP自动化，准确率99.8% |
| **GEPA** (arXiv) | 反思式Prompt进化 | 可超越强化学习的prompt优化 |
| **Awesome LLM Agent Optimization** (GitHub) | 论文合集 | 全面覆盖Agent优化方向 |

## 1.5 SOP 结构化评审 Prompt 模板

```markdown
### SOP 结构化评审 Prompt

你是一位资深的投研流程审计专家。请对以下SOP进行结构化评审。

**评审对象**: {{SOP_TITLE}}
**SOP内容**: {{SOP_CONTENT}}
**最近执行日志摘要**: {{EXECUTION_LOG_SUMMARY}}

请按照以下维度逐一评审，每个维度给出1-5分评分和具体改进建议：

#### 维度1: 完整性 (Completeness) [权重30%]
- 是否覆盖了从数据获取到结论输出的全流程？
- 是否有遗漏的边界条件或异常处理？
- 评分: __/5
- 改进建议: 

#### 维度2: 可执行性 (Executability) [权重25%]
- 每个步骤是否足够具体，Agent可以无歧义地执行？
- 工具调用参数是否完整？
- 评分: __/5
- 改进建议:

#### 维度3: 时效性 (Timeliness) [权重15%]
- 数据源是否标注了更新频率？
- 是否有过期数据依赖？
- 评分: __/5
- 改进建议:

#### 维度4: 准确性 (Accuracy) [权重20%]
- 计算逻辑是否正确？
- 数据源交叉验证是否充分？
- 评分: __/5
- 改进建议:

#### 维度5: 可维护性 (Maintainability) [权重10%]
- SOP模块化程度如何？
- 是否易于局部更新而不影响整体？
- 评分: __/5
- 改进建议:

#### 综合评估
- **加权总分**: __/5
- **风险等级**: [低/中/高]
- **TOP3 改进优先级**:
  1. 
  2. 
  3. 
- **建议的下一版本变更摘要**:
```

---

# 二、MCP 工具的迭代最佳实践

## 2.1 MCP 生态中的工具迭代方法论

**来源**: MCP官方规范 (modelcontextprotocol.io)、Peter Steinberger MCP Best Practices、Forbes MCP Evolution 分析

### 核心原则

1. **Contract-First 开发**: 先定义工具接口（JSON Schema），再编码实现
2. **语义化版本控制**: `YYYY-MM` 协议版本 + 工具级语义版本（Major.Minor.Patch）
3. **向后兼容的加法式演进**: 新功能通过添加可选参数实现，不破坏已有调用方
4. **Sensible Defaults**: 每个工具必须有合理的默认值，降低使用门槛

### MCP 工具版本演进策略

```
v1.0: 基础功能发布（核心参数 + 默认值）
  ↓ 收集Agent调用日志，分析失败模式
v1.1: 修正参数描述（基于Agent误用反馈）
  ↓ A/B测试新旧description
v1.2: 添加可选参数（基于高频需求）
  ↓ 观察参数使用率
v2.0: 重构（合并低使用率参数、拆分过于复杂的工具）
```

## 2.2 工具描述（Description）的 A/B 测试方法

**核心基准**: MCP-Radar Benchmark (arXiv:2505.16700) — 首个多维度MCP工具使用评估标准

### 衡量 Tool Description 质量的五维指标

| 维度 | 定义 | 衡量方法 |
|------|------|---------|
| **工具选择准确率** | Agent是否选对了工具 | ground truth对比 |
| **参数构建准确率** | Agent是否正确填写参数 | schema验证 + 值匹配 |
| **答案准确率** | 最终输出是否正确 | 人工/自动评估 |
| **计算效率** | 调用次数和资源消耗 | token计数 + 调用链长度 |
| **执行速度** | 端到端响应时间 | 计时 |

### A/B 测试流程

```python
# 伪代码：Tool Description A/B Testing
test_cases = load_benchmark_queries()

for query in test_cases:
    # 变体A：当前description
    result_a = agent.run(query, tools_with_description_a)
    # 变体B：候选description  
    result_b = agent.run(query, tools_with_description_b)
    
    # 对比指标
    compare(
        tool_selection_accuracy(result_a, result_b),
        parameter_accuracy(result_a, result_b),
        answer_quality(result_a, result_b)
    )
```

### 关键发现

- **工具数量与准确率负相关**: 工具越多，Agent选择准确率越低（工具膨胀问题）
- **Stacklok MCP Optimizer**: 通过动态裁剪工具集，将中等模型准确率从38%提升至69%
- **SOTA模型** (Claude Sonnet 4 / Opus 4.5): 大型benchmark中可达93-94%准确率

### 参数设计的迭代权衡

| 策略 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| **简化** (少参数+智能默认) | Agent容易正确调用 | 灵活性低 | 高频基础操作 |
| **丰富** (多参数+详细schema) | 功能强大 | Agent可能误填或遗漏 | 专业深度操作 |
| **渐进式** (核心必填+可选扩展) | 兼顾易用和强大 | 文档维护成本高 | 推荐的默认策略 |

## 2.3 社区优秀 MCP 项目迭代案例

| 项目 | 迭代亮点 |
|------|---------|
| **Anthropic MCP SDK** | 严格的SEP（规范增强提案）流程，社区驱动 |
| **Block/Goose MCP Testing** | Composable Recipes 自动化验证工具元数据 |
| **mcp-tool-selection-bench** (PyPI) | 开源CLI，支持混淆矩阵分析工具选择 |
| **MCP Registry** (2025) | 公共/私有注册中心，标准化工具发现 |

## 2.4 推荐的工具开发参考

- **Anthropic 官方指南**: [Writing effective tools for AI agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
- **MCP Best Practices**: [steipete.me/posts/2025/mcp-best-practices](https://steipete.me/posts/2025/mcp-best-practices)
- **MCP-Radar 论文**: [arxiv.org/html/2505.16700v1](https://arxiv.org/html/2505.16700v1)

---

# 三、投研领域的知识迭代闭环

## 3.1 研报质量验证体系

### 3.1.1 事后回测：预测准确率追踪

```yaml
backtest_framework:
  tracking_dimensions:
    - 方向性预测: "看多/看空/中性 vs 实际涨跌"
    - 幅度预测: "目标价 vs 实际价格（MAE/MAPE）"
    - 时间窗口: "预测周期 vs 实际兑现时间"
    - 催化剂验证: "预判的驱动因素是否真实发生"
  
  implementation:
    - 在 index.json 中为每篇研报增加 predictions[] 字段
    - 定期脚本自动抓取市场数据，与预测进行对比
    - 生成 accuracy_score 并回写 index.json
    - 累计形成分析师/SOP的历史准确率曲线
```

### 3.1.2 同行评审：交叉验证机制

**双盲Agent评审**:
- Agent A 写研报 → Agent B 独立分析同一标的 → 对比差异
- 差异点自动标记为"争议区域"，触发深度调研或人工仲裁

### 3.1.3 用户反馈指标

| 指标 | 数据来源 | 权重 |
|------|---------|------|
| 阅读量 | 前端页面埋点 | 15% |
| 平均阅读时长 | 页面停留时间 | 20% |
| 引用/转发率 | 分享追踪 | 25% |
| 行动转化率 | 用户是否据此调仓 | 40% |

## 3.2 知识老化管理

### 数据时效性标记

```json
// index.json 中的时效性元数据
{
  "title": "铜期货Q2展望",
  "created_at": "2026-04-01",
  "data_freshness": {
    "macro_data": {"source": "统计局", "as_of": "2026-03", "refresh": "monthly"},
    "price_data": {"source": "交易所", "as_of": "2026-04-01", "refresh": "daily"},
    "policy_data": {"source": "国务院", "as_of": "2026-03-28", "refresh": "event-driven"}
  },
  "expiry_warning": "2026-05-01",
  "status": "active",          // active | outdated | superseded | retracted
  "superseded_by": null,       // 指向更新版研报的path
  "accuracy_score": null       // 回测后填入
}
```

### 自动过期提醒机制

```
每日巡检脚本：
1. 扫描 index.json 中所有 status="active" 的研报
2. 对比 expiry_warning 与当前日期
3. 超期研报自动标记为 "outdated"
4. 生成 .agentstalk/ 通信文件通知 content-agent 进行更新
5. 前端页面对 outdated 研报显示醒目警告标签
```

### 研报观点更新机制

| 操作 | 触发条件 | 执行方式 |
|------|---------|---------|
| **补充** (Supplement) | 出现新数据/事件 | 原报告追加 update section |
| **修正** (Revision) | 核心观点需要调整 | 发布新版本，链接旧版 |
| **撤回** (Retraction) | 重大错误或数据失实 | 标记 retracted，首页移除 |

## 3.3 "投研→验证→改进"正反馈循环

```
┌─────────────────────────────────────────────────────────────┐
│                    投研正反馈循环                              │
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ 1.数据采集 │───→│ 2.分析建模 │───→│ 3.研报产出 │              │
│  └──────────┘    └──────────┘    └──────────┘              │
│       ↑                                │                    │
│       │                                ↓                    │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ 6.SOP更新 │←───│ 5.归因分析 │←───│ 4.事后回测 │              │
│  └──────────┘    └──────────┘    └──────────┘              │
│       │                                                     │
│       ↓                                                     │
│  ┌──────────────────────┐                                   │
│  │ 7.工具/MCP迭代优化    │──→ 回到步骤1                       │
│  └──────────────────────┘                                   │
└─────────────────────────────────────────────────────────────┘
```

**各环节关键动作**:
1. **数据采集**: MCP工具自动抓取 → 日志记录数据质量
2. **分析建模**: SOP引导Agent执行 → 记录每步耗时和质量
3. **研报产出**: 结构化HTML输出 → 元数据写入index.json
4. **事后回测**: 定时任务对比预测vs实际 → 计算准确率
5. **归因分析**: 哪些SOP步骤贡献了准确预测？哪些导致了偏差？
6. **SOP更新**: Self-Refine + Constitutional审核 → 版本化更新
7. **工具迭代**: 基于使用日志优化MCP工具 → A/B测试验证

---

# 四、迭代闭环架构设计

## 4.1 完整架构流程图

```
╔══════════════════════════════════════════════════════════════════════════╗
║                    投研助手迭代闭环架构 v1.0                              ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║  ┌─────────────────────┐                                               ║
║  │  ① SOP/工具开发      │  ← 人工编写 或 Agent自动生成                    ║
║  │  (SOP/*.md, mcp/)   │                                               ║
║  └────────┬────────────┘                                               ║
║           │                                                            ║
║           ▼                                                            ║
║  ┌─────────────────────┐     ┌──────────────────────┐                  ║
║  │  ② 质量门禁检查      │────→│  宪法审核 (Auditor)   │                  ║
║  │  [可完全自动化]      │     │  - 完整性检查          │                  ║
║  │                     │     │  - Schema验证          │                 ║
║  │                     │     │  - 安全性扫描           │                 ║
║  └────────┬────────────┘     └──────────────────────┘                  ║
║           │ PASS                                                       ║
║           ▼                                                            ║
║  ┌─────────────────────┐                                               ║
║  │  ③ Agent 试运行      │  ← 用测试数据集 dry-run                        ║
║  │  [可完全自动化]      │                                               ║
║  └────────┬────────────┘                                               ║
║           │                                                            ║
║           ▼                                                            ║
║  ┌─────────────────────┐     ┌──────────────────────┐                  ║
║  │  ④ 执行日志收集      │────→│  日志存储:             │                  ║
║  │  [可完全自动化]      │     │  - 步骤耗时            │                  ║
║  │                     │     │  - 工具调用成功率       │                  ║
║  │                     │     │  - 输出质量评分         │                  ║
║  └────────┬────────────┘     └──────────────────────┘                  ║
║           │                                                            ║
║           ▼                                                            ║
║  ┌─────────────────────┐                                               ║
║  │  ⑤ 自动化评估        │  ← Self-Refine + MCP-Radar 指标               ║
║  │  [可完全自动化]      │                                               ║
║  │  - SOP评分(5维度)    │                                               ║
║  │  - 工具评分(5指标)   │                                               ║
║  │  - 研报评分(4维度)   │                                               ║
║  └────────┬────────────┘                                               ║
║           │                                                            ║
║           ▼                                                            ║
║  ┌─────────────────────┐                                               ║
║  │  ⑥ 改进建议生成      │  ← Agent-as-Auditor + Constitutional AI       ║
║  │  [可完全自动化]      │                                               ║
║  │  输出: 结构化建议     │                                               ║
║  │  → .agentstalk/     │                                               ║
║  └────────┬────────────┘                                               ║
║           │                                                            ║
║           ▼                                                            ║
║  ┌─────────────────────┐                                               ║
║  │  ⑦ 人工审核确认      │  ← 唯一需要人工介入的环节                       ║
║  │  [半自动化]          │     可设定自动批准阈值:                          ║
║  │                     │     评分>4.0 → 自动批准                         ║
║  │                     │     评分3.0-4.0 → 人工审核                      ║
║  │                     │     评分<3.0 → 驳回重做                         ║
║  └────────┬────────────┘                                               ║
║           │ APPROVED                                                   ║
║           ▼                                                            ║
║  ┌─────────────────────┐                                               ║
║  │  ⑧ SOP/工具更新      │  ← git commit + 版本号递增                     ║
║  │  [可完全自动化]      │     index.json 元数据更新                       ║
║  └────────┬────────────┘                                               ║
║           │                                                            ║
║           └──────────────→ 回到 ① 循环                                  ║
║                                                                        ║
╚══════════════════════════════════════════════════════════════════════════╝
```

## 4.2 各节点具体实现方案

### 节点①: SOP/工具开发
- **实现**: 人工编写初始版本 或 Agent基于模板自动生成
- **存储**: `SOP/` 目录（Markdown格式）、`mcp/` 目录（MCP Server代码）
- **自动化程度**: ⭐⭐⭐ (模板化生成可自动化，创新性内容需人工)

### 节点②: 质量门禁检查 🤖 完全自动化
```bash
# 实现方案: 脚本 + Agent
# 1. 静态检查
scripts/quality-gate.sh:
  - SOP Markdown 格式校验 (标题层级、必需section检查)
  - MCP工具 JSON Schema 校验
  - 安全性扫描 (敏感信息、硬编码凭据)

# 2. 语义检查 (Agent)
  - Constitutional AI 宪法对照审核
  - 输出结构化评审报告到 .agentstalk/
```

### 节点③: Agent 试运行 🤖 完全自动化
- **实现**: 准备标准化测试数据集，Agent按SOP执行一次完整流程
- **关键**: 使用历史数据（已知正确答案）进行 dry-run，而非实时数据
- **输出**: 执行结果 + 结构化日志

### 节点④: 执行日志收集 🤖 完全自动化
```json
// 日志格式
{
  "run_id": "20260402-trial-001",
  "sop_version": "copper-outlook/v1.2",
  "steps": [
    {
      "step_id": "data_collection",
      "tool_calls": ["fetch_futures_data", "fetch_macro_indicators"],
      "duration_ms": 3200,
      "success": true,
      "output_quality": null  // 由评估节点填入
    }
  ],
  "total_duration_ms": 45000,
  "total_tool_calls": 12,
  "errors": []
}
```

### 节点⑤: 自动化评估 🤖 完全自动化
- **SOP评估**: 使用 §1.5 的结构化评审 Prompt 模板
- **工具评估**: MCP-Radar 五维指标
- **研报评估**: 准确性 + 完整性 + 时效性 + 可操作性

### 节点⑥: 改进建议生成 🤖 完全自动化
- **实现**: Agent 分析评估结果，生成结构化改进建议
- **输出**: `.agentstalk/[timestamp]_auditor_to_developer_[topic].md`

### 节点⑦: 人工审核确认 👤 半自动化
- **自动批准阈值**: 评分 > 4.0/5.0 且无安全问题 → 自动通过
- **人工介入**: 评分 3.0-4.0 → 人工判断
- **自动驳回**: 评分 < 3.0 → 返回开发节点

### 节点⑧: SOP/工具更新 🤖 完全自动化
- **实现**: git commit（带结构化 commit message）、版本号自增、index.json 更新

## 4.3 自动化程度总结

| 节点 | 自动化程度 | 说明 |
|------|-----------|------|
| ① SOP/工具开发 | 半自动 | 模板可自动化，创新需人工 |
| ② 质量门禁 | **完全自动** | 静态+语义检查 |
| ③ Agent试运行 | **完全自动** | 标准化测试集 |
| ④ 日志收集 | **完全自动** | 结构化日志 |
| ⑤ 自动化评估 | **完全自动** | 多维度打分 |
| ⑥ 改进建议 | **完全自动** | Agent生成 |
| ⑦ 人工审核 | 半自动 | 阈值自动+人工兜底 |
| ⑧ SOP更新 | **完全自动** | git + 版本管理 |

**结论**: 8个节点中6个可完全自动化，仅①和⑦需要人工介入。

---

# 五、具体落地方案

## 5.1 利用 `.agentstalk/` 实现评审流转

### 评审工作流文件协议

```
.agentstalk/
├── [timestamp]_developer_to_auditor_review-request.md    # 请求评审
├── [timestamp]_auditor_to_developer_review-result.md     # 评审结果
├── [timestamp]_auditor_to_architect_escalation.md        # 升级处理
└── [timestamp]_architect_to_developer_approval.md        # 批准更新
```

### 评审请求模板

```markdown
# Agent通信: 评审请求

## Metadata
| 字段 | 值 |
|------|------|
| Sender | developer-agent |
| Receiver | auditor-agent |
| Topic | SOP评审请求 |

## Task Status
- 状态: PENDING_REVIEW

## Payload
- SOP路径: SOP/copper-outlook-v1.2.md
- 变更摘要: 新增LME库存数据交叉验证步骤
- 变更类型: MINOR_UPDATE
- 自评分数: 4.2/5.0

## Next Action
请 auditor-agent 执行结构化评审并在2小时内回复评审结果。
```

## 5.2 利用 `index.json` 实现研报质量追踪

### 扩展的 index.json Schema

```json
{
  "reports": [
    {
      "id": "rpt-20260401-cu",
      "title": "铜期货Q2展望：供需再平衡下的结构性机会",
      "path": "reports/20260401_copper_q2_outlook.html",
      "author": "macro-agent",
      "created_at": "2026-04-01T10:00:00+08:00",
      "tags": ["期货", "铜", "有色金属", "Q2展望"],
      "category": "micro",
      
      "quality_metrics": {
        "sop_version": "SOP/commodity-analysis/v2.1",
        "generation_duration_ms": 180000,
        "tool_calls_count": 15,
        "tool_success_rate": 0.93,
        "audit_score": 4.1,
        "audit_details": {
          "completeness": 4.5,
          "executability": 4.0,
          "timeliness": 4.0,
          "accuracy": 4.2,
          "maintainability": 3.8
        }
      },
      
      "predictions": [
        {
          "type": "directional",
          "target": "沪铜主力合约",
          "prediction": "bullish",
          "target_price": 72000,
          "horizon": "2026-06-30",
          "confidence": 0.7,
          "actual_outcome": null,
          "accuracy_score": null,
          "evaluated_at": null
        }
      ],
      
      "data_freshness": {
        "macro_data": {"as_of": "2026-03", "refresh": "monthly"},
        "price_data": {"as_of": "2026-04-01", "refresh": "daily"}
      },
      
      "lifecycle": {
        "status": "active",
        "expiry_warning": "2026-05-01",
        "superseded_by": null,
        "update_history": []
      },
      
      "engagement": {
        "views": 0,
        "avg_read_time_sec": 0,
        "shares": 0
      }
    }
  ]
}
```

## 5.3 MCP 中嵌入自我监控和质量报告工具

### 设计方案: 质量监控 MCP Server

```javascript
// mcp/quality-monitor/server.js (概念设计)

const tools = {
  // 工具1: SOP健康检查
  "sop_health_check": {
    description: "扫描所有SOP文件，检查完整性、时效性和一致性",
    parameters: {
      sop_dir: { type: "string", default: "SOP/" }
    },
    handler: async ({ sop_dir }) => {
      // 1. 扫描所有.md文件
      // 2. 检查必需section是否存在
      // 3. 检查数据源引用是否可达
      // 4. 返回健康报告
    }
  },
  
  // 工具2: 研报质量仪表盘
  "report_quality_dashboard": {
    description: "基于index.json生成研报质量统计报告",
    parameters: {
      time_range: { type: "string", enum: ["7d", "30d", "90d"], default: "30d" }
    },
    handler: async ({ time_range }) => {
      // 1. 读取index.json
      // 2. 聚合quality_metrics
      // 3. 计算趋势（质量是否在提升？）
      // 4. 识别低分研报和高频问题
    }
  },
  
  // 工具3: 回测执行器
  "run_backtest": {
    description: "对指定研报的预测进行事后回测",
    parameters: {
      report_id: { type: "string" },
      market_data_source: { type: "string", default: "exchange_api" }
    },
    handler: async ({ report_id, market_data_source }) => {
      // 1. 从index.json读取predictions
      // 2. 获取实际市场数据
      // 3. 计算准确率
      // 4. 回写index.json
    }
  },
  
  // 工具4: 过期内容巡检
  "expiry_scanner": {
    description: "扫描并标记已过期或即将过期的研报",
    parameters: {},
    handler: async () => {
      // 1. 读取index.json中所有active研报
      // 2. 对比expiry_warning
      // 3. 标记过期研报
      // 4. 生成.agentstalk/通知文件
    }
  },

  // 工具5: 工具使用分析
  "tool_usage_analytics": {
    description: "分析MCP工具的调用模式，识别优化机会",
    parameters: {
      log_dir: { type: "string", default: "data/logs/" }
    },
    handler: async ({ log_dir }) => {
      // 1. 聚合工具调用日志
      // 2. 统计各工具调用频率、成功率、平均耗时
      // 3. 识别低使用率工具（候选合并/删除）
      // 4. 识别高失败率工具（候选优化）
    }
  }
};
```

## 5.4 每日/每周自动化质量巡检方案

### 每日巡检 (Daily Health Check) — 5分钟自动完成

```yaml
daily_inspection:
  schedule: "每日 08:00"
  tasks:
    - name: "过期内容扫描"
      tool: expiry_scanner
      action: 标记过期研报，生成.agentstalk/通知
      
    - name: "数据源可达性检查"
      tool: sop_health_check
      action: 验证所有SOP中引用的数据源URL是否可访问
      
    - name: "回测触发"
      tool: run_backtest
      action: 对到期的predictions执行回测
      
  output: ".agentstalk/[date]_monitor_to_all_daily-report.md"
```

### 每周巡检 (Weekly Quality Review) — 30分钟

```yaml
weekly_inspection:
  schedule: "每周一 09:00"
  tasks:
    - name: "研报质量趋势分析"
      tool: report_quality_dashboard
      params: { time_range: "7d" }
      action: 生成周度质量报告
      
    - name: "工具使用分析"  
      tool: tool_usage_analytics
      action: 识别需要优化或淘汰的工具
      
    - name: "SOP全量评审"
      agent: auditor-agent
      action: 使用§1.5评审模板对所有SOP打分
      
    - name: "改进建议汇总"
      agent: architect-agent
      action: 汇总本周所有改进建议，排定优先级
      
  output: 
    - ".agentstalk/[date]_monitor_to_architect_weekly-review.md"
    - "reports/quality/weekly-[date].html"  # 可视化质量报告
```

### 落地脚本示例

```bash
#!/bin/bash
# scripts/daily-quality-check.sh
# 每日质量巡检脚本

WORKSPACE="$(cd "$(dirname "$0")/.." && pwd)"
DATE=$(date +%Y%m%d)
REPORT_FILE="$WORKSPACE/.agentstalk/${DATE}_monitor_to_all_daily-report.md"

echo "# 每日质量巡检报告" > "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "## Metadata" >> "$REPORT_FILE"
echo "| 字段 | 值 |" >> "$REPORT_FILE"
echo "|------|------|" >> "$REPORT_FILE"
echo "| Timestamp | $(date -Iseconds) |" >> "$REPORT_FILE"
echo "| Sender | quality-monitor |" >> "$REPORT_FILE"
echo "| Receiver | all-agents |" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 1. 检查过期研报
echo "## 1. 过期内容检查" >> "$REPORT_FILE"
node -e "
const fs = require('fs');
const idx = JSON.parse(fs.readFileSync('$WORKSPACE/index.json','utf8'));
const now = new Date();
const reports = idx.reports || [];
const expired = reports.filter(r => 
  r.lifecycle?.status === 'active' && 
  r.lifecycle?.expiry_warning && 
  new Date(r.lifecycle.expiry_warning) < now
);
console.log('过期研报数: ' + expired.length);
expired.forEach(r => console.log('- ' + r.title + ' (过期于: ' + r.lifecycle.expiry_warning + ')'));
" >> "$REPORT_FILE" 2>/dev/null || echo "index.json暂无lifecycle字段" >> "$REPORT_FILE"

# 2. SOP文件完整性检查
echo "" >> "$REPORT_FILE"
echo "## 2. SOP完整性检查" >> "$REPORT_FILE"
for sop in "$WORKSPACE"/SOP/*.md; do
  [ -f "$sop" ] || continue
  basename="$(basename "$sop")"
  has_steps=$(grep -c "^##" "$sop" 2>/dev/null || echo 0)
  echo "- $basename: $has_steps 个主要章节" >> "$REPORT_FILE"
done

echo "" >> "$REPORT_FILE"
echo "## Task Status: COMPLETED" >> "$REPORT_FILE"
echo "## Next Action: 请各Agent查阅巡检结果" >> "$REPORT_FILE"
```

## 5.5 自动化评审 Prompt 模板集

### 模板A: SOP评审（已在§1.5给出）

### 模板B: MCP工具评审 Prompt

```markdown
### MCP 工具质量评审 Prompt

你是一位MCP工具设计专家。请评审以下MCP工具定义。

**工具名称**: {{TOOL_NAME}}
**工具描述**: {{TOOL_DESCRIPTION}}
**参数Schema**: {{PARAMETERS_JSON}}
**最近30天调用统计**: 
- 调用次数: {{CALL_COUNT}}
- 成功率: {{SUCCESS_RATE}}
- 平均响应时间: {{AVG_RESPONSE_MS}}ms
- Agent首次选择正确率: {{SELECTION_ACCURACY}}

请评审以下维度：

#### 1. 描述质量 (Description Quality)
- Agent能否仅通过描述理解何时该使用此工具？
- 描述是否过于笼统或过于技术化？
- 评分: __/5
- 改进后的描述建议:

#### 2. 参数设计 (Parameter Design)
- 必填参数是否过多？（推荐≤3个必填）
- 是否提供了合理的默认值？
- 参数名称是否自解释？
- 评分: __/5
- 改进建议:

#### 3. 错误处理 (Error Handling)
- 是否明确定义了错误类型？
- 错误信息是否对Agent友好？
- 评分: __/5
- 改进建议:

#### 4. 性能与效率 (Performance)
- 响应时间是否合理？
- 是否有不必要的重复计算？
- 评分: __/5
- 改进建议:

#### 综合评估
- 加权总分: __/5
- 是否建议: [保留/优化/合并/淘汰]
- 优先改进项:
```

### 模板C: 研报质量评审 Prompt

```markdown
### 投研报告质量评审 Prompt

你是一位资深投研分析师兼质量审核官。请对以下研报进行严格评审。

**研报标题**: {{TITLE}}
**研报内容**: {{CONTENT}}
**使用的SOP版本**: {{SOP_VERSION}}
**数据截止日期**: {{DATA_AS_OF}}

请按以下维度评审：

#### 1. 逻辑严密性 (Logic Rigor) [权重30%]
- 论证链是否完整（前提→推理→结论）？
- 是否存在逻辑跳跃或隐含假设？
- 评分: __/5

#### 2. 数据支撑度 (Data Support) [权重25%]
- 关键结论是否有具体数据支撑？
- 数据源是否权威可靠？
- 是否进行了交叉验证？
- 评分: __/5

#### 3. 前瞻性与独到性 (Insight Quality) [权重25%]
- 是否提供了市场共识之外的独立见解？
- 催化剂/风险点是否具有前瞻性？
- 评分: __/5

#### 4. 可操作性 (Actionability) [权重20%]
- 是否给出明确的操作建议（方向、幅度、时间窗口）？
- 风险控制措施是否具体？
- 评分: __/5

#### 综合评估
- 加权总分: __/5
- 关键风险提示:
- 必须修改的问题:
- 建议补充的内容:
```

---

# 六、参考文献与资源

## 学术论文

| 论文 | 出处 | 核心贡献 |
|------|------|---------|
| Self-Refine: Iterative Refinement with Self-Feedback | NeurIPS 2023, arXiv:2303.17651 | 无监督自我迭代范式 |
| DSPy: Compiling Declarative LM Calls | arXiv:2310.03714 | 声明式LLM流水线优化 |
| TextGrad: Backpropagating LLM Feedback | Nature 2025 | 梯度式prompt优化 |
| MCP-Radar: Multi-Dimensional Benchmark | arXiv:2505.16700 | MCP工具评估基准 |
| Evaluating LLMs on Business Process Modeling | Springer 2025 | BPM与LLM结合基准 |
| PROBAST+AI | BMJ 2024 | AI预测模型质量评估 |

## 行业实践

| 资源 | URL | 核心价值 |
|------|-----|---------|
| Grab SOP-Driven Agent | engineering.grab.com | 企业级SOP自动化案例 |
| MCP Best Practices | steipete.me | MCP开发最佳实践 |
| Anthropic: Writing Tools for Agents | anthropic.com/engineering | 官方工具设计指南 |
| MCP Specification Changelog | modelcontextprotocol.io | MCP协议演进记录 |
| Block/Goose MCP Testing | block.github.io/goose | 自动化MCP测试 |
| Stacklok MCP Optimizer | stacklok.com | 工具集优化实践 |
| Constitutional AI Overview | zenodo.org/records/15461323 | CAI方法论详解 |

## 开源工具

| 工具 | 用途 |
|------|------|
| `dspy` (pip install dspy) | LLM流水线声明式优化 |
| `textgrad` (github.com/zou-group/textgrad) | LLM反馈梯度优化 |
| `mcp-tool-selection-bench` (PyPI) | MCP工具选择准确率基准 |
| Awesome LLM Agent Optimization (GitHub) | 论文与项目索引 |

---

## Next Action

### 分阶段落地计划

#### 🔴 Phase 1: 基础设施 (第1-2周)

| 任务 | 负责Agent | 交付物 |
|------|-----------|--------|
| 扩展 index.json Schema | architect-agent | 含 quality_metrics, predictions, lifecycle 的新Schema |
| 编写 daily-quality-check.sh | tools-agent | scripts/daily-quality-check.sh |
| 制定 SOP 宪法规则集 | architect-agent | SOP/meta/constitution.yaml |
| 建立执行日志格式标准 | architect-agent | docs/log-format-spec.md |

#### 🟡 Phase 2: 评审自动化 (第3-4周)

| 任务 | 负责Agent | 交付物 |
|------|-----------|--------|
| 实现 Auditor Agent prompt 模板 | content-agent | templates/审核prompt模板集 |
| 开发质量监控 MCP Server | tools-agent | mcp/quality-monitor/ |
| 实现 .agentstalk/ 评审流转协议 | coordinator-agent | 评审工作流自动化 |
| 接入 mcp-tool-selection-bench | tools-agent | 工具A/B测试基线数据 |

#### 🟢 Phase 3: 闭环验证 (第5-6周)

| 任务 | 负责Agent | 交付物 |
|------|-----------|--------|
| 端到端迭代闭环试运行 | all-agents | 一次完整的SOP迭代案例 |
| 回测框架实现 | tools-agent | 自动回测脚本 + 准确率追踪 |
| 质量仪表盘页面 | frontend-agent | reports/quality/dashboard.html |
| 迭代闭环SOP文档化 | architect-agent | SOP/meta/iteration-loop.md |

#### 🔵 Phase 4: 持续优化 (持续)

| 任务 | 频率 | 负责方 |
|------|------|--------|
| 每日质量巡检 | Daily 08:00 | 自动化脚本 |
| 每周质量评审 | Weekly 周一 | auditor-agent + 人工 |
| 月度SOP大版本评审 | Monthly | architect-agent + 人工 |
| 季度工具生态盘点 | Quarterly | tools-agent |

---

> **核心理念**: 从"人工驱动迭代"到"Agent自主迭代+人工守门"的范式转换。8个闭环节点中6个可完全自动化，人的角色从"执行者"变为"审批者"和"方向设定者"。
