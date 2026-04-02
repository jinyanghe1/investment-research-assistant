# Agent Communication Record

## Metadata
- **Timestamp**: 2026-04-02T08:15:00Z
- **Sender**: Architect (首席架构Agent)
- **Receiver**: All Agents
- **Topic**: 开发规范确立 - 双Agent守护协议

## Task Status
📋 POLICY ESTABLISHED

## Payload

### 开发守护协议 (Development Guardian Protocol)

自本次起，**每一轮开发迭代**必须伴随至少两个守护Agent并行运行：

#### 1. 🔬 技术调研Agent (tech-research)
- **职责**：在GitHub搜索同类项目的最优实现，提供benchmark对标
- **输出**：`.agentstalk/` 中的调研报告，包含：
  - 同类开源项目的架构对比
  - 最佳实践与反模式
  - 具体的改进建议（附代码示例）

#### 2. 🏗️ 架构审查Agent (arch-review)
- **职责**：审查每次代码变更，确保遵循两大原则：
  - **最小增量原则**：只做必要的修改，不引入多余变更
  - **必要更改原则**：所有变更必须有明确的目的和收益
- **输出**：
  - 代码审查报告（问题清单 + 严重度评级）
  - 测试验证结果（语法检查 + 单元测试 + 集成测试）
  - 改进建议（优先级排序）

### 工作流
```
[需求/迭代触发]
    ├── tech-research Agent → 调研最优实践 → .agentstalk/报告
    ├── arch-review Agent → 审查代码质量 → .agentstalk/报告
    └── dev Agent(s) → 执行开发 → 代码产出
         ↓
    [Architect汇总] → 集成测试 → 修复问题 → 验收通过
```

## Next Action
- 立即对当前MCP代码执行首轮守护检查
- tech-research: 调研GitHub上最优MCP Server实现
- arch-review: 审查当前16个工具的代码质量并执行测试
