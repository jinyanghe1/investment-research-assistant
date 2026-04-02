# Agent Communication Record

## Metadata
- **Timestamp**: 2026-04-02T08:41:00Z
- **Sender**: Architect (首席架构Agent)
- **Receiver**: All Agents
- **Topic**: Phase 2 工程加固 - 开发路线图更新与任务派发

## Task Status
🚀 STARTING Phase 2 — 工程加固

## Payload

### Phase 2 目标
将 MCP Server 从 "能跑" 提升到 "可靠+可测试+可维护"

### 任务分解与分工

| Task ID | 任务 | 输出文件 | 分配Agent | 优先级 |
|---------|------|----------|-----------|--------|
| P2.1 | Pydantic配置管理 | mcp/config.py | infra-agent | P0 |
| P2.2 | 统一错误处理装饰器 | mcp/utils/errors.py | infra-agent | P0 |
| P2.3 | 工具函数可测试化重构 | mcp/tools/*.py (重构) | refactor-agent | P0 |
| P2.4 | pytest测试框架 | mcp/tests/ | test-agent | P0 |
| P2.5 | pandas延迟导入修复 | mcp/utils/formatters.py | infra-agent | P1 |

### 依赖关系
```
P2.1 (配置) ──┐
P2.2 (错误) ──┼──→ P2.3 (重构) ──→ P2.4 (测试)
P2.5 (修复) ──┘
```
- P2.1 + P2.2 + P2.5 可并行
- P2.3 依赖 P2.1 + P2.2 完成（重构时引入新基础设施）
- P2.4 依赖 P2.3 完成（测试需要可测试的函数签名）

### 开发守护协议
每轮开发必须伴随：
- 🔬 tech-research Agent: GitHub调研同类最优实现
- 🏗️ arch-review Agent: 代码审查 + 最小增量原则 + 测试验证

### 技术规范

#### P2.1 Pydantic配置 (config.py)
```python
from pydantic_settings import BaseSettings

class MCPConfig(BaseSettings):
    # 缓存配置
    cache_ttl_realtime: int = 300      # 行情缓存5min
    cache_ttl_macro: int = 86400       # 宏观数据缓存24h
    cache_dir: str = "data"
    
    # 工作区路径
    workspace_root: str = ""           # 自动推断
    reports_dir: str = "reports"
    
    # API配置
    akshare_timeout: int = 30
    yfinance_timeout: int = 30
    
    class Config:
        env_prefix = "MCP_"           # 支持 MCP_CACHE_TTL_REALTIME 环境变量
```

#### P2.2 统一错误处理 (utils/errors.py)
```python
import functools, traceback

class MCPToolError(Exception):
    def __init__(self, code: str, message: str): ...

def handle_errors(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except MCPToolError as e:
            return {"error": True, "code": e.code, "message": e.message}
        except Exception as e:
            return {"error": True, "code": "INTERNAL_ERROR", "message": str(e)}
    return wrapper
```

#### P2.3 重构模式
Before:
```python
def register_tools(mcp):
    @mcp.tool
    def get_stock_realtime(symbol: str, market: str = "A") -> dict:
        # 200行业务逻辑全在闭包内
        ...
```

After:
```python
# 业务逻辑独立函数（可被pytest直接测试）
@handle_errors
def fetch_stock_realtime(symbol: str, market: str = "A") -> dict:
    ...

def register_tools(mcp):
    @mcp.tool
    def get_stock_realtime(symbol: str, market: str = "A") -> dict:
        """获取股票实时行情..."""
        return fetch_stock_realtime(symbol, market)
```

#### P2.4 测试结构
```
mcp/tests/
├── conftest.py          # pytest fixtures (mock akshare/yfinance)
├── test_cache.py        # 缓存单元测试
├── test_formatters.py   # 格式化函数测试
├── test_market_data.py  # 行情工具测试 (mock)
├── test_macro_data.py   # 宏观数据测试 (mock)
├── test_company.py      # 公司分析测试 (mock)
├── test_report.py       # 研报生成测试
├── test_kb.py           # 知识库测试
└── test_integration.py  # 集成测试 (16工具注册)
```

## Next Action
1. 并行启动 infra-agent (P2.1+P2.2+P2.5) + tech-research + arch-review
2. infra完成后启动 refactor-agent (P2.3)
3. 重构完成后启动 test-agent (P2.4)
