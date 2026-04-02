# Agent 通信消息

| 字段 | 值 |
|---|---|
| **From** | TechResearchAgent |
| **To** | ArchitectAgent |
| **Topic** | Phase 2 工程加固 — 技术调研报告 |
| **Task Status** | ✅ COMPLETED |
| **Timestamp** | 2026-04-02T08:41:00+08:00 |

---

## Payload: Phase 2 工程加固技术调研报告

基于对 GitHub 上 30+ 个 MCP Server / FastMCP 开源项目的代码审查，以下是三个调研主题的详细结论。

---

## 主题 1: MCP Server 的 Pydantic 配置管理最佳实践

### 1.1 调研发现

在社区中，MCP Server 配置管理已形成两个清晰的流派：

#### 流派 A: pydantic-settings `BaseSettings`（推荐 ⭐）

**代表项目**：
- [bodywave-jira](https://github.com/mottysisam/bodywave-jira/blob/main/src/config.py) — 最佳实践范本
- [1C_MCP_SERVER_OWN](https://github.com/AlexMiaWat/1C_MCP_SERVER_OWN/blob/main/config.py) — 精简示例
- [SE347_IE104_Backend](https://github.com/baominh5xx2/SE347_IE104_Backend/blob/main/app/v1/mcp/config.py) — 最简模板
- [mcpharness](https://github.com/BerdTan/mcpharness/blob/main/src/config.py) — 含 singleton + reload

**核心代码模式**（bodywave-jira — 最完整实现）：

```python
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # 忽略未知环境变量，避免部署时报错
    )

    # 连接配置 —— 必填项用 ... 标记
    jira_base_url: str = Field(..., alias="JIRA_BASE_URL", description="Jira Cloud base URL")
    jira_api_token: str | None = Field(default=None, alias="JIRA_API_TOKEN")

    # 运行时配置 —— 有默认值
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    jira_timeout: int = Field(default=30, alias="JIRA_TIMEOUT")
    jira_rate_limit: int = Field(default=100, alias="JIRA_RATE_LIMIT")

    @field_validator("jira_base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        v = v.rstrip("/")
        if not v.startswith("https://"):
            raise ValueError("URL must use HTTPS")
        return v
```

**关键亮点**：
- 使用 `alias` 将 `SCREAMING_SNAKE_CASE` 环境变量映射到 `snake_case` Python 属性
- `extra="ignore"` 防止生产环境多余环境变量导致启动失败
- `field_validator` 做启动时校验（URL 格式、日志等级枚举等）
- 自定义 `ConfigurationError` 异常包装 Pydantic 错误

#### 流派 B: dataclass（轻量场景）

**代表项目**：[mcp-tool-shop-org/brain-dev](https://github.com/mcp-tool-shop-org/brain-dev/blob/main/dev_brain/config.py)

```python
from dataclasses import dataclass

@dataclass
class DevBrainConfig:
    server_name: str = "dev-brain"
    min_gap_support: float = 0.05
    max_suggestions: int = 20
    default_test_framework: str = "pytest"
```

**适用场景**：纯内部参数调优，无外部 API 密钥或环境变量需求。

### 1.2 配置项组织规范

社区共识的配置分组方式（按注释分区）：

| 分组 | 典型配置项 | 示例 |
|------|-----------|------|
| **Server Identity** | `server_name`, `server_version` | `"invest-research-mcp"`, `"1.0.0"` |
| **External API** | API URL, Key, Timeout | `AKSHARE_TIMEOUT=30` |
| **Security** | `secret_key`, `cors_origins`, `auth_mode` | `auth_mode: Literal["none", "oauth2"]` |
| **Logging** | `log_level`, `log_format` | `"INFO"`, `"json"` |
| **Rate Limiting** | `rate_limit`, `timeout` | `100` req/min |
| **Storage** | `upload_dir`, `cache_dir`, `database_url` | `"./data/cache"` |

### 1.3 环境变量命名规范

```
# 推荐格式: {SERVICE_PREFIX}_{CATEGORY}_{FIELD}
MCP_SERVER_NAME=invest-research
MCP_LOG_LEVEL=INFO
MCP_AKSHARE_TIMEOUT=30
MCP_YFINANCE_API_KEY=xxx

# 1C MCP 的 env_prefix 模式（最佳实践）
class Config(BaseSettings):
    class Config:
        env_prefix = "MCP_"   # 所有环境变量自动加前缀
```

来源: [1C_MCP_SERVER_OWN config.py](https://github.com/AlexMiaWat/1C_MCP_SERVER_OWN/blob/main/config.py) 使用 `env_prefix = "MCP_"` 自动添加前缀。

### 1.4 配置热重载

**结论：对 MCP Server 不必要，但 singleton + reload 函数值得保留。**

[mcpharness](https://github.com/BerdTan/mcpharness/blob/main/src/config.py) 提供了最佳参考：

```python
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """Singleton 模式获取配置"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

def reload_settings() -> Settings:
    """测试或配置变更时手动重载"""
    global _settings
    _settings = Settings()
    return _settings
```

**理由**：MCP Server 通常运行为 stdio 进程，生命周期短暂。热重载的主要价值在于**测试**（不同配置切换），而非生产环境。

### 1.5 对 Phase 2 的具体建议

```python
# mcp/config.py — 推荐实现
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class MCPSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="INVEST_MCP_",
        extra="ignore",
    )

    # Server
    server_name: str = "invest-research-mcp"
    server_version: str = "1.0.0"
    debug: bool = False

    # Data Sources
    akshare_timeout: int = Field(default=30, description="AKShare API timeout (seconds)")
    yfinance_timeout: int = Field(default=30, description="yfinance API timeout (seconds)")
    data_cache_ttl: int = Field(default=3600, description="Data cache TTL (seconds)")

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")

    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return v.upper()

# Singleton
_settings: Optional[MCPSettings] = None

def get_settings() -> MCPSettings:
    global _settings
    if _settings is None:
        _settings = MCPSettings()
    return _settings

def reload_settings() -> MCPSettings:
    """For testing only"""
    global _settings
    _settings = MCPSettings()
    return _settings
```

---

## 主题 2: Python 工具函数的可测试化模式

### 2.1 调研发现

#### 关键模式：业务逻辑与 MCP 注册分离

**最佳参考**：[panther-labs/mcp-panther](https://github.com/panther-labs/mcp-panther/blob/main/docs/mcp-testing-guide.md) — 提供了完整的 MCP 测试指南。

社区中最成熟的分离模式：

```
# 项目结构
src/
├── tools/           # 纯业务逻辑（可独立测试）
│   ├── stock_data.py
│   └── macro_analysis.py
├── server.py        # MCP 注册层（薄包装）
└── config.py
tests/
├── conftest.py
├── unit/
│   ├── test_stock_data.py
│   └── test_macro_analysis.py
└── integration/
    └── test_server.py
```

**分离示例**（来自 brain-dev 的 `create_server` 模式）：

```python
# server.py — 薄包装层
from fastmcp import FastMCP
from .tools.stock_data import fetch_stock_price  # 纯函数
from .config import DevBrainConfig

def create_server(config: DevBrainConfig) -> FastMCP:
    mcp = FastMCP(config.server_name)

    @mcp.tool()
    async def get_stock_price(symbol: str) -> dict:
        """MCP 工具 — 仅做参数转发"""
        return await fetch_stock_price(symbol, timeout=config.akshare_timeout)

    return mcp
```

```python
# tools/stock_data.py — 纯业务逻辑
async def fetch_stock_price(symbol: str, timeout: int = 30) -> dict:
    """可独立测试的纯函数"""
    import akshare as ak
    df = ak.stock_zh_a_spot_em()
    row = df[df["代码"] == symbol]
    return {"symbol": symbol, "price": float(row["最新价"].iloc[0])}
```

#### FastMCP 官方推荐的 In-Memory 测试模式

```python
from fastmcp import Client

@pytest.mark.asyncio
async def test_tool_via_mcp(server):
    async with Client(server) as client:
        result = await client.call_tool("get_stock_price", {"symbol": "000001"})
        assert result.is_success
```

来源: [panther-labs MCP Testing Guide](https://github.com/panther-labs/mcp-panther/blob/main/docs/mcp-testing-guide.md)

### 2.2 外部 API 的 Mock 策略

#### AKShare Mock 模式

**来源**: [edtechre/pybroker](https://github.com/edtechre/pybroker/blob/main/tests/test_data.py) — 最佳参考（同时 mock akshare 和 yfinance）

```python
from unittest import mock
import pandas as pd

# 方式1: mock.patch.object 替换模块级函数
@pytest.fixture()
def mock_akshare():
    with mock.patch("akshare.stock_zh_a_spot_em") as mock_fn:
        mock_fn.return_value = pd.DataFrame({
            "代码": ["000001", "600519"],
            "名称": ["平安银行", "贵州茅台"],
            "最新价": [12.5, 1800.0],
        })
        yield mock_fn

# 方式2: mock 整个下载函数
with mock.patch.object(yfinance, "download", return_value=expected_df):
    df = yf.query(symbols, START_DATE, END_DATE)
```

#### yfinance Mock 模式

```python
@pytest.fixture()
def yfinance_df():
    """使用预存的 pickle 文件作为 golden data"""
    return pd.read_pickle(
        os.path.join(os.path.dirname(__file__), "testdata/yfinance.pkl")
    )

# 在测试中使用
def test_yfinance_query(yfinance_df):
    with mock.patch.object(yfinance, "download", return_value=yfinance_df):
        result = YFinance().query(["AAPL"], START_DATE, END_DATE)
        assert set(result.columns) == {"date", "open", "high", "low", "close", "volume", "symbol"}
```

**关键策略**：
| 策略 | 适用场景 | 示例 |
|------|---------|------|
| `mock.patch.object` | Mock 模块级函数 | `mock.patch.object(akshare, "stock_zh_a_spot_em")` |
| `mock.patch` 路径 | Mock 被 import 的函数 | `mock.patch("src.tools.akshare.stock_zh_a_spot_em")` |
| Pickle golden data | 稳定的大 DataFrame | `pd.read_pickle("testdata/xxx.pkl")` |
| `AsyncMock` | Mock 异步 API 调用 | `AsyncMock(return_value={"data": ...})` |

### 2.3 conftest.py Fixture 设计

**最佳参考**: [mcp-tool-shop-org/brain-dev conftest.py](https://github.com/mcp-tool-shop-org/brain-dev/blob/main/tests/conftest.py)

```python
# conftest.py 分层设计
import pytest
from config import MCPSettings
from server import create_server

# Layer 1: 配置 fixture
@pytest.fixture
def config():
    return MCPSettings(
        akshare_timeout=5,
        debug=True,
        log_level="DEBUG",
    )

# Layer 2: 服务器 fixture（依赖 config）
@pytest.fixture
def server(config):
    return create_server(config)

# Layer 3: Mock 数据 fixtures
@pytest.fixture
def sample_stock_data():
    return pd.DataFrame({
        "代码": ["000001"], "名称": ["平安银行"], "最新价": [12.5]
    })

# Layer 4: Mock 外部服务
@pytest.fixture
def mock_akshare_api(sample_stock_data):
    with mock.patch("akshare.stock_zh_a_spot_em", return_value=sample_stock_data):
        yield

# Layer 5: 环境变量 fixture
@pytest.fixture
def mock_environment():
    with mock.patch.dict(os.environ, {
        "INVEST_MCP_LOG_LEVEL": "DEBUG",
        "INVEST_MCP_AKSHARE_TIMEOUT": "5",
    }):
        yield
```

### 2.4 对 Phase 2 的具体建议

1. **立即实施 `create_server(config)` 工厂模式** — 这是可测试性的基石
2. **所有工具函数放在 `tools/` 目录** — 作为可独立 import 的纯函数
3. **创建 `tests/testdata/` 目录** — 存放 akshare/yfinance 的 pickle golden data
4. **pytest 配置**:
   ```ini
   # pyproject.toml
   [tool.pytest.ini_options]
   asyncio_mode = "auto"
   testpaths = ["tests"]
   addopts = "--cov=mcp --cov-report=term-missing -v"
   ```

---

## 主题 3: 统一错误处理装饰器模式

### 3.1 调研发现

**最佳参考项目**:
- [Xthebuilder/JRVS](https://github.com/Xthebuilder/JRVS/tree/main/mcp/) — 最完整的 production-ready 错误处理体系（含 Circuit Breaker、Retry、Timeout、Bulkhead）
- [mottysisam/bodywave-jira](https://github.com/mottysisam/bodywave-jira/blob/main/src/exceptions.py) — 简洁的层级异常体系

### 3.2 层级异常体系（必须实现）

```python
# exceptions.py — 来自 JRVS 项目的最佳实践
class MCPToolException(Exception):
    """所有 MCP 工具错误的基类"""
    def __init__(self, message: str, details: dict = None, recoverable: bool = False):
        self.message = message
        self.details = details or {}
        self.recoverable = recoverable
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "recoverable": self.recoverable,
        }

# 数据源异常
class DataSourceError(MCPToolException):
    """数据源访问异常"""
    pass

class AKShareError(DataSourceError):
    def __init__(self, func_name: str, original_error: Exception = None):
        super().__init__(
            f"AKShare {func_name} failed",
            details={"function": func_name, "original_error": str(original_error)},
            recoverable=True,
        )

class YFinanceError(DataSourceError):
    def __init__(self, symbol: str, original_error: Exception = None):
        super().__init__(
            f"yfinance query failed for {symbol}",
            details={"symbol": symbol, "original_error": str(original_error)},
            recoverable=True,
        )

# 分析异常
class AnalysisError(MCPToolException):
    """分析计算异常"""
    pass

# 配置异常
class ConfigurationError(MCPToolException):
    def __init__(self, field: str, reason: str):
        super().__init__(
            f"Invalid config '{field}': {reason}",
            details={"field": field, "reason": reason},
            recoverable=False,
        )
```

来源: [JRVS exceptions.py](https://github.com/Xthebuilder/JRVS/blob/main/mcp/exceptions.py)

### 3.3 装饰器模式（核心）

#### 3.3.1 统一错误捕获装饰器

```python
# decorators.py
import functools
import logging
from typing import Callable

logger = logging.getLogger(__name__)

def mcp_tool_handler(func: Callable) -> Callable:
    """统一错误处理装饰器 — 将异常转换为结构化错误响应"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> dict:
        try:
            result = await func(*args, **kwargs)
            return {"success": True, "data": result}
        except MCPToolException as e:
            logger.warning(f"Tool error in {func.__name__}: {e.message}", extra=e.details)
            return {
                "success": False,
                "error": e.to_dict(),
            }
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            return {
                "success": False,
                "error": {
                    "error_type": "InternalError",
                    "message": f"Unexpected error: {str(e)}",
                    "recoverable": False,
                },
            }
    return wrapper
```

#### 3.3.2 Retry 装饰器（指数退避）

来自 [JRVS resilience.py](https://github.com/Xthebuilder/JRVS/blob/main/mcp/resilience.py)：

```python
def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0,
          exceptions: tuple = (Exception,)):
    """指数退避重试装饰器"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        raise
                    logger.warning(f"Retry {attempt+1}/{max_attempts} for {func.__name__}")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator
```

#### 3.3.3 Timeout 装饰器

```python
def timeout(seconds: float):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                raise MCPToolException(
                    f"{func.__name__} timed out after {seconds}s",
                    recoverable=True,
                )
        return wrapper
    return decorator
```

#### 3.3.4 组合使用示例（JRVS 的装饰器堆叠模式 ⭐）

```python
@mcp.tool()
@mcp_tool_handler                                    # 最外层：统一错误格式
@retry(max_attempts=3, delay=1.0, exceptions=(DataSourceError,))  # 重试
@timeout(30)                                          # 超时保护
async def get_stock_price(symbol: str) -> dict:
    """获取A股实时行情"""
    df = ak.stock_zh_a_spot_em()
    row = df[df["代码"] == symbol]
    if row.empty:
        raise DataSourceError(f"Symbol {symbol} not found")
    return {"symbol": symbol, "price": float(row["最新价"].iloc[0])}
```

来源: [JRVS server_enhanced.py](https://github.com/Xthebuilder/JRVS/blob/main/mcp/server_enhanced.py) — 第 87-100 行展示了 `@track_request` → `@cached` → `@retry` → `@timeout` 的堆叠模式。

### 3.4 结构化错误返回格式

社区共识的 JSON 格式：

```json
// 成功
{
    "success": true,
    "data": { "symbol": "000001", "price": 12.5 }
}

// 业务错误（可恢复）
{
    "success": false,
    "error": {
        "error_type": "AKShareError",
        "message": "AKShare stock_zh_a_spot_em failed",
        "details": {"function": "stock_zh_a_spot_em", "original_error": "Connection timeout"},
        "recoverable": true
    }
}

// 系统错误（不可恢复）
{
    "success": false,
    "error": {
        "error_type": "InternalError",
        "message": "Unexpected error: division by zero",
        "recoverable": false
    }
}
```

### 3.5 Circuit Breaker（选择性实施）

JRVS 项目实现了完整的 Circuit Breaker 模式：

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = CircuitState.CLOSED  # CLOSED → OPEN → HALF_OPEN

    async def call_async(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if not self._should_attempt_reset():
                raise Exception("Circuit breaker OPEN")
            self.state = CircuitState.HALF_OPEN
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

# 全局实例
akshare_circuit = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
yfinance_circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
```

来源: [JRVS resilience.py](https://github.com/Xthebuilder/JRVS/blob/main/mcp/resilience.py)

**建议**：Phase 2 初期不实现 Circuit Breaker，但预留接口。在数据源调用频繁且不稳定时再引入。

### 3.6 对 Phase 2 的具体建议

1. **必须实现**：`mcp_tool_handler` 统一错误装饰器 + 层级异常体系
2. **推荐实现**：`retry` 指数退避装饰器（akshare/yfinance 网络请求必备）
3. **推荐实现**：`timeout` 装饰器（防止数据源请求无限等待）
4. **延后实现**：Circuit Breaker、Bulkhead（Phase 3 或数据源不稳定时引入）

---

## 值得警惕的反模式 ⚠️

### 反模式 1: 配置直接硬编码全局变量

```python
# ❌ 坏例子 — 无法测试，无法覆盖
API_KEY = os.getenv("API_KEY", "default")
TIMEOUT = 30

# ✅ 好例子 — 使用 BaseSettings
class Settings(BaseSettings):
    api_key: str = Field(default="default")
    timeout: int = Field(default=30)
```

### 反模式 2: 工具函数直接定义在全局 mcp 对象上

```python
# ❌ 坏例子 — 无法在测试中注入不同配置
mcp = FastMCP("server")

@mcp.tool()
async def my_tool():
    ...  # 隐式依赖全局状态

# ✅ 好例子 — create_server 工厂函数
def create_server(config):
    mcp = FastMCP(config.name)
    @mcp.tool()
    async def my_tool():
        return await pure_business_logic(config.timeout)
    return mcp
```

### 反模式 3: 裸 try/except 吞掉所有异常

```python
# ❌ 坏例子
@mcp.tool()
async def get_data(symbol: str):
    try:
        return ak.stock_zh_a_spot_em()
    except:
        return "Error occurred"  # 无信息，无分类

# ✅ 好例子 — 结构化错误
@mcp.tool()
@mcp_tool_handler
async def get_data(symbol: str):
    try:
        return ak.stock_zh_a_spot_em()
    except ConnectionError as e:
        raise AKShareError("stock_zh_a_spot_em", original_error=e)
```

### 反模式 4: 测试中直接调用外部 API

```python
# ❌ 坏例子 — 依赖网络，不确定性高
def test_stock_price():
    result = ak.stock_zh_a_spot_em()  # 真实网络调用!
    assert len(result) > 0

# ✅ 好例子 — Mock + Golden Data
def test_stock_price(mock_akshare_api, sample_stock_data):
    result = fetch_stock_price("000001")
    assert result["price"] == 12.5
```

### 反模式 5: case_sensitive=True + 全大写 Python 属性

```python
# ❌ 坏例子 — 违反 Python 命名惯例
class Settings(BaseSettings):
    MCP_SERVER_NAME: str = "server"
    MCP_DEBUG: bool = True
    class Config:
        case_sensitive = True

# ✅ 好例子 — 使用 alias 映射
class Settings(BaseSettings):
    server_name: str = Field(alias="MCP_SERVER_NAME")
    debug: bool = Field(alias="MCP_DEBUG")
```

---

## Next Action

请 Architect Agent 基于本调研报告：

1. **确认优先级排序**：建议 P0: 配置管理 + 异常体系 → P1: 工具函数分离 + conftest → P2: 装饰器堆叠
2. **确认文件结构**：
   ```
   mcp/
   ├── config.py          # Pydantic BaseSettings
   ├── exceptions.py      # 层级异常
   ├── decorators.py      # mcp_tool_handler, retry, timeout
   ├── server.py           # create_server 工厂
   ├── tools/
   │   ├── stock_data.py   # 纯业务逻辑
   │   └── macro_data.py
   └── tests/
       ├── conftest.py
       ├── testdata/        # pickle golden data
       └── unit/
   ```
3. **启动 Phase 2 Sprint 1 实施**

---

*本报告基于对 GitHub 上 30+ 个 MCP Server 开源项目的代码审查生成。关键参考仓库已附 URL，可供交叉验证。*
