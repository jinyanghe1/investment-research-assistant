# Agent Communication: Script Quality Verification & Iteration Framework

---

## Metadata

| Field        | Value |
|:-------------|:------|
| **Timestamp**  | 2026-04-02 08:13:00 |
| **Sender**     | Quality-Research-Agent (Researcher) |
| **Receiver**   | Chief-Architect-Agent |
| **Topic**      | Python脚本/MCP工具质量验证体系与持续迭代框架 |
| **Priority**   | 🔴 HIGH |
| **Format**     | Research Report v1.0 |

---

## Task Status

| Phase | Status | Notes |
|:------|:-------|:------|
| Web调研 | ✅ Done | 已检索6个维度的最新行业实践 (2025) |
| 项目审计 | ✅ Done | 已完成当前项目质量基础设施审计 |
| 方案设计 | ✅ Done | 已产出可执行的工具链方案 |
| 文档输出 | ✅ Done | 本文档 |

### 当前项目质量基础设施审计结论

| 维度 | 状态 | 评级 |
|:-----|:-----|:-----|
| 代码组织 | MCP结构清晰，缺少 pyproject.toml | B+ |
| **测试** | **零测试文件** | **F** 🔴 |
| **CI/CD** | **无自动化** | **F** 🔴 |
| 包管理 | 仅 mcp/requirements.txt | C |
| 文档 | AGENTS.md + SOP/ 完善 | A |
| Agent协作 | .agentstalk/ 协议完善 | A |
| 代码质量工具 | 无lint/format/pre-commit | C |

---

## Payload: 完整调研结果

---

# 一、Python脚本/工具的质量验证体系

## 1.1 静态分析层

### 1.1.1 代码风格检查：Ruff（2025年首选，替代pylint/flake8/black/isort）

**为什么选Ruff？**
- 速度：比 flake8 快 10-100x（Rust实现）
- 统一：一个工具替代 flake8 + black + isort + pyupgrade
- 配置简洁：全部集中在 `pyproject.toml`

**推荐配置（投研MCP项目适用）：**

```toml
# pyproject.toml
[tool.ruff]
line-length = 120          # 金融脚本数据处理行较长，适当放宽
target-version = "py311"
src = ["mcp", "tools", "scripts"]

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "F",    # pyflakes
    "W",    # pycodestyle warnings
    "I",    # isort
    "UP",   # pyupgrade
    "B",    # bugbear（常见bug模式）
    "SIM",  # simplify（代码简化建议）
    "N",    # pep8-naming
    "S",    # bandit（安全检查子集）
    "RUF",  # ruff特有规则
]
ignore = [
    "E501",  # 由formatter处理行长
    "S101",  # assert在测试中允许
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "S106"]  # 测试文件允许assert和硬编码

[tool.ruff.lint.isort]
combine-as-imports = true
known-first-party = ["mcp"]
```

**日常命令：**
```bash
ruff check .              # 检查代码问题
ruff check --fix .        # 自动修复
ruff format .             # 格式化代码
ruff format --check .     # CI中检查格式（不修改）
```

### 1.1.2 类型检查：mypy（金融数据脚本适用）

**为什么在金融脚本中尤其重要？**
- 金融数据类型混乱（价格可能是float/Decimal/str/None）
- 防止数值计算的隐式类型转换错误
- 捕获Pandas DataFrame操作中的常见类型错误

**推荐配置：**

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true        # 强制函数签名有类型注解
check_untyped_defs = true
ignore_missing_imports = true       # 第三方库（akshare等）可能缺少stub
no_implicit_optional = true
strict_equality = true

[[tool.mypy.overrides]]
module = "akshare.*"
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = "yfinance.*"
ignore_missing_imports = true
```

**金融脚本类型注解示例：**
```python
from typing import Optional
from decimal import Decimal
import pandas as pd

def calculate_pe_ratio(
    price: float,
    eps: float,
    trailing_months: int = 12
) -> Optional[float]:
    """计算市盈率，EPS为零时返回None"""
    if eps == 0:
        return None
    return price / eps

def validate_price_series(
    df: pd.DataFrame,
    column: str = "close"
) -> tuple[bool, list[str]]:
    """验证价格序列连续性，返回(是否有效, 异常列表)"""
    ...
```

### 1.1.3 安全扫描：Bandit

**金融脚本的关键安全检查项：**
- `B105/B106/B107`: 硬编码密码/API Key检测
- `B301/B302`: pickle反序列化风险（金融数据缓存常用）
- `B608`: SQL注入检测
- `B501`: 不安全的HTTPS请求（verify=False）
- `B603/B604`: 子进程调用安全

**推荐配置：**
```toml
# pyproject.toml
[tool.bandit]
exclude_dirs = ["tests", ".venv"]
skips = ["B101"]  # assert在非测试代码中的使用

[tool.bandit.assert_used]
skips = ["*_test.py", "test_*.py"]
```

**命令：**
```bash
bandit -r mcp/ tools/ scripts/ -f json -o bandit-report.json
bandit -r mcp/ -ll  # 只报告中/高严重级别
```

### 1.1.4 复杂度分析

**圈复杂度阈值标准：**

| 复杂度 | 等级 | 含义 | 行动 |
|:------:|:----:|:-----|:-----|
| 1-5 | A | 简单，低风险 | ✅ 无需行动 |
| 6-10 | B | 中等复杂度 | ⚠️ 考虑简化 |
| 11-20 | C | 复杂 | 🔴 必须重构 |
| 21+ | D | 非常复杂 | 🔴🔴 立即重构 |

**工具与命令：**
```bash
# 使用 radon 分析复杂度
pip install radon
radon cc mcp/ -a -nc          # 显示平均复杂度，隐藏A/B级
radon mi mcp/ -nc             # 可维护性指数

# Ruff内置复杂度检查
# 在 pyproject.toml 中添加：
# [tool.ruff.lint.mccabe]
# max-complexity = 10
```

### 1.1.5 代码覆盖率：pytest-cov

**最佳实践：**

```toml
# pyproject.toml
[tool.coverage.run]
source = ["mcp", "tools", "scripts"]
branch = true                # 启用分支覆盖
omit = [
    "*/tests/*",
    "*/__pycache__/*",
    "*/migrations/*",
]

[tool.coverage.report]
fail_under = 70              # 初始阈值70%，逐步提高到85%
show_missing = true
precision = 1
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if __name__ == .__main__.",
    "raise NotImplementedError",
    "pass",
    "except ImportError",
]

[tool.coverage.html]
directory = "htmlcov"
```

**覆盖率阈值演进策略：**
```
Phase 1 (现在): fail_under = 0    # 先建立基线
Phase 2 (1月后): fail_under = 50  # 核心路径覆盖
Phase 3 (3月后): fail_under = 70  # 关键逻辑全覆盖
Phase 4 (6月后): fail_under = 85  # 成熟期目标
```

**命令：**
```bash
pytest --cov=mcp --cov=tools --cov-report=html --cov-report=term-missing
pytest --cov=mcp --cov-fail-under=70   # CI中使用
```

---

## 1.2 动态测试层

### 1.2.1 单元测试：pytest框架

**项目结构建议：**
```
mcp/
├── tools/
│   ├── market_data.py
│   ├── macro_data.py
│   ├── company_analysis.py
│   ├── report_generator.py
│   └── knowledge_base.py
├── tests/
│   ├── conftest.py              # 共享fixtures
│   ├── test_market_data.py
│   ├── test_macro_data.py
│   ├── test_company_analysis.py
│   ├── test_report_generator.py
│   ├── test_knowledge_base.py
│   ├── test_server.py           # 服务端集成测试
│   └── fixtures/                # 测试数据
│       ├── sample_stock_data.csv
│       ├── sample_macro_data.json
│       └── sample_report.html
├── server.py
└── requirements.txt
```

**pytest配置：**
```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["mcp/tests", "tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--tb=short",
    "--strict-markers",
    "-x",            # 首次失败即停止（开发阶段）
]
markers = [
    "slow: 标记慢速测试（需要网络请求）",
    "integration: 集成测试",
    "data_quality: 数据质量测试",
]
asyncio_mode = "auto"  # MCP工具多为async
```

**Mock外部API的金融数据测试策略：**

```python
# mcp/tests/conftest.py
import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

@pytest.fixture
def sample_stock_data() -> pd.DataFrame:
    """生成模拟股票行情数据"""
    dates = pd.date_range(end=datetime.now(), periods=30, freq='B')
    return pd.DataFrame({
        'date': dates,
        'open': [3000 + i * 10 for i in range(30)],
        'high': [3010 + i * 10 for i in range(30)],
        'low':  [2990 + i * 10 for i in range(30)],
        'close': [3005 + i * 10 for i in range(30)],
        'volume': [1_000_000 + i * 50000 for i in range(30)],
    })

@pytest.fixture
def mock_akshare():
    """Mock akshare的API调用"""
    with patch('akshare.stock_zh_a_hist') as mock:
        mock.return_value = pd.DataFrame({
            '日期': ['2026-01-01', '2026-01-02'],
            '开盘': [10.0, 10.5],
            '收盘': [10.2, 10.8],
            '最高': [10.5, 11.0],
            '最低': [9.8, 10.3],
            '成交量': [100000, 120000],
        })
        yield mock

@pytest.fixture
def mock_yfinance():
    """Mock yfinance的API调用"""
    with patch('yfinance.download') as mock:
        mock.return_value = pd.DataFrame({
            'Open': [10.0, 10.5],
            'Close': [10.2, 10.8],
            'High': [10.5, 11.0],
            'Low': [9.8, 10.3],
            'Volume': [100000, 120000],
        })
        yield mock


# mcp/tests/test_market_data.py
import pytest

class TestMarketData:
    """市场数据工具测试"""

    def test_fetch_returns_valid_dataframe(self, mock_akshare):
        """验证数据获取返回有效DataFrame"""
        # ... 调用工具函数 ...
        assert not result.empty
        assert 'close' in result.columns or '收盘' in result.columns

    def test_fallback_to_yfinance(self, mock_akshare, mock_yfinance):
        """验证akshare失败后回退到yfinance"""
        mock_akshare.side_effect = Exception("API限流")
        # ... 调用工具函数 ...
        mock_yfinance.assert_called_once()

    def test_handles_empty_data_gracefully(self, mock_akshare):
        """验证空数据的优雅处理"""
        mock_akshare.return_value = pd.DataFrame()
        # ... 应返回有意义的错误信息 ...

    @pytest.mark.parametrize("invalid_code", [
        "", "INVALID", "12345678", None
    ])
    def test_invalid_stock_code(self, invalid_code):
        """参数化测试：无效股票代码"""
        # ... 应返回参数错误 ...

    @pytest.mark.slow
    def test_real_api_integration(self):
        """真实API集成测试（标记为slow，CI中可选跳过）"""
        # ... 实际调用API验证 ...
```

### 1.2.2 集成测试：MCP工具的端到端测试

**使用FastMCP内置测试客户端（核心方法）：**

```python
# mcp/tests/test_server.py
import pytest
from fastmcp import Client
from mcp.server import mcp  # 你的FastMCP实例

class TestMCPServer:
    """MCP服务端到端测试"""

    @pytest.fixture
    async def client(self):
        """创建测试客户端"""
        async with Client(mcp) as client:
            yield client

    async def test_list_tools(self, client):
        """验证所有工具都正确注册"""
        tools = await client.list_tools()
        tool_names = [t.name for t in tools]
        assert "get_stock_data" in tool_names
        assert "get_macro_data" in tool_names
        assert "generate_report" in tool_names

    async def test_tool_schema_completeness(self, client):
        """验证工具schema完整性"""
        tools = await client.list_tools()
        for tool in tools:
            assert tool.description, f"Tool {tool.name} 缺少description"
            assert len(tool.description) >= 20, \
                f"Tool {tool.name} description过短，LLM难以理解"
            # 验证参数有描述
            if tool.inputSchema and 'properties' in tool.inputSchema:
                for param, schema in tool.inputSchema['properties'].items():
                    assert 'description' in schema, \
                        f"Tool {tool.name} 参数 {param} 缺少description"

    async def test_tool_returns_structured_response(self, client):
        """验证工具返回LLM可解读的结构化响应"""
        result = await client.call_tool("get_stock_data", {
            "symbol": "000001",
            "period": "daily",
            "count": 5
        })
        # 验证返回内容非空
        assert len(result) > 0
        # 验证返回的是文本内容（LLM可读）
        assert result[0].text is not None

    async def test_tool_error_handling(self, client):
        """验证工具错误时返回结构化错误信息"""
        result = await client.call_tool("get_stock_data", {
            "symbol": "INVALID_CODE_999999"
        })
        # 应返回错误信息而非抛出异常
        assert "错误" in result[0].text or "error" in result[0].text.lower()
```

### 1.2.3 数据验证测试（金融数据schema验证）

```python
# mcp/tests/test_data_quality.py
import pytest
import pandas as pd
import pandera as pa
from pandera import Column, Check, DataFrameSchema

# === Pandera Schema定义 ===

stock_price_schema = DataFrameSchema({
    "date": Column(pa.DateTime, nullable=False),
    "open": Column(float, Check.greater_than(0), nullable=False),
    "high": Column(float, Check.greater_than(0), nullable=False),
    "low": Column(float, Check.greater_than(0), nullable=False),
    "close": Column(float, Check.greater_than(0), nullable=False),
    "volume": Column(int, Check.greater_than_or_equal_to(0), nullable=False),
}, checks=[
    # high >= low (基本逻辑约束)
    Check(lambda df: (df["high"] >= df["low"]).all(),
          error="High price must be >= Low price"),
    # high >= open 和 high >= close
    Check(lambda df: (df["high"] >= df["open"]).all(),
          error="High price must be >= Open price"),
    # low <= open 和 low <= close
    Check(lambda df: (df["low"] <= df["close"]).all(),
          error="Low price must be <= Close price"),
])

pe_ratio_schema = DataFrameSchema({
    "symbol": Column(str, nullable=False),
    "pe_ttm": Column(float, [
        Check.greater_than(-1000),  # PE可以为负但需有界
        Check.less_than(10000),     # PE过高可能数据异常
    ], nullable=True),
    "pe_static": Column(float, nullable=True),
})


class TestDataQuality:
    """金融数据质量验证"""

    @pytest.mark.data_quality
    def test_stock_price_schema(self, sample_stock_data):
        """验证股票价格数据符合schema"""
        validated = stock_price_schema.validate(sample_stock_data)
        assert validated is not None

    @pytest.mark.data_quality
    def test_price_continuity(self, sample_stock_data):
        """检查价格连续性（异常跳空检测）"""
        df = sample_stock_data.sort_values('date')
        pct_change = df['close'].pct_change().dropna()
        # A股涨跌幅限制一般为10%（创业板/科创板20%）
        MAX_PCT_CHANGE = 0.22  # 留一定余量
        outliers = pct_change[pct_change.abs() > MAX_PCT_CHANGE]
        assert len(outliers) == 0, \
            f"发现{len(outliers)}个异常跳空: {outliers.to_dict()}"

    @pytest.mark.data_quality
    def test_trading_day_completeness(self, sample_stock_data):
        """检查交易日完整性"""
        df = sample_stock_data.sort_values('date')
        date_range = pd.bdate_range(
            start=df['date'].min(),
            end=df['date'].max()
        )
        missing_days = set(date_range) - set(df['date'])
        # 允许节假日缺失，但不应有超过5天连续缺失
        assert len(missing_days) < len(date_range) * 0.1, \
            f"缺失交易日比例过高: {len(missing_days)}/{len(date_range)}"

    @pytest.mark.data_quality
    def test_cross_source_consistency(self):
        """跨数据源一致性检查（akshare vs yfinance）"""
        # 获取同一标的的两个数据源
        # ... 对比 close 价格的相关系数应 > 0.99 ...
        pass
```

### 1.2.4 性能测试

```python
# mcp/tests/test_performance.py
import pytest
import time
import tracemalloc

class TestPerformance:
    """性能基准测试"""

    @pytest.mark.slow
    async def test_tool_response_time(self, client):
        """验证工具响应时间 < 5秒"""
        start = time.monotonic()
        await client.call_tool("get_stock_data", {
            "symbol": "000001", "period": "daily", "count": 30
        })
        elapsed = time.monotonic() - start
        assert elapsed < 5.0, f"响应时间 {elapsed:.2f}s 超过5秒阈值"

    def test_memory_usage(self, sample_stock_data):
        """验证数据处理不超过内存阈值"""
        tracemalloc.start()
        # ... 执行数据处理操作 ...
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        assert peak < 100 * 1024 * 1024, \
            f"内存峰值 {peak/1024/1024:.1f}MB 超过100MB阈值"

    @pytest.mark.parametrize("count", [10, 100, 1000, 5000])
    def test_data_processing_scalability(self, count):
        """数据处理可扩展性测试"""
        # 验证处理时间与数据量线性关系
        pass
```

### 1.2.5 容错测试

```python
# mcp/tests/test_resilience.py
import pytest
from unittest.mock import patch, AsyncMock
import asyncio

class TestResilience:
    """容错与异常场景测试"""

    async def test_network_timeout(self, client):
        """测试网络超时处理"""
        with patch('aiohttp.ClientSession.get',
                   side_effect=asyncio.TimeoutError):
            result = await client.call_tool("get_stock_data", {
                "symbol": "000001"
            })
            assert "超时" in result[0].text or "timeout" in result[0].text.lower()

    async def test_api_rate_limit(self, client):
        """测试API限流处理"""
        # 模拟 429 Too Many Requests
        pass

    async def test_missing_data_fields(self, client):
        """测试数据字段缺失的优雅处理"""
        pass

    async def test_concurrent_requests(self, client):
        """测试并发请求处理"""
        tasks = [
            client.call_tool("get_stock_data", {"symbol": f"00000{i}"})
            for i in range(1, 6)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        errors = [r for r in results if isinstance(r, Exception)]
        assert len(errors) == 0, f"并发请求出现异常: {errors}"
```

---

## 1.3 数据质量验证（金融数据专项）

### 1.3.1 数据验证框架选择

| 框架 | 适用场景 | 学习曲线 | 推荐度 |
|:-----|:---------|:---------|:------:|
| **Pandera** | 轻量级、Pythonic、与Pandas紧密集成 | ⭐ 低 | ⭐⭐⭐⭐⭐ |
| Great Expectations | 企业级数据管道、合规审计 | ⭐⭐⭐ 高 | ⭐⭐⭐ |
| 自定义断言 | 简单场景、快速验证 | ⭐ 低 | ⭐⭐⭐ |

**推荐：对于我们的投研MCP项目，优先使用 Pandera**（轻量、Pythonic、零配置开销）。

### 1.3.2 金融数据质量检查清单

```python
# mcp/utils/data_validators.py
"""金融数据质量验证工具集"""

import pandas as pd
from dataclasses import dataclass
from typing import Optional

@dataclass
class DataQualityReport:
    """数据质量报告"""
    is_valid: bool
    total_checks: int
    passed_checks: int
    failed_checks: list[str]
    warnings: list[str]

def validate_price_series(df: pd.DataFrame) -> DataQualityReport:
    """
    股票价格序列质量验证

    检查项：
    1. 价格非负
    2. High >= Low
    3. OHLC逻辑一致性
    4. 涨跌幅在合理范围（±22%）
    5. 成交量非负
    6. 时间序列单调递增
    7. 无重复日期
    """
    checks_passed = 0
    total = 7
    failures = []
    warnings = []

    # 1. 价格非负
    if (df[['open','high','low','close']] >= 0).all().all():
        checks_passed += 1
    else:
        failures.append("存在负价格")

    # 2. High >= Low
    if (df['high'] >= df['low']).all():
        checks_passed += 1
    else:
        failures.append("存在 High < Low 的异常数据")

    # 3. OHLC一致性
    if (df['high'] >= df['open']).all() and (df['high'] >= df['close']).all():
        checks_passed += 1
    else:
        failures.append("OHLC逻辑不一致")

    # 4. 涨跌幅范围
    pct = df['close'].pct_change().dropna()
    if (pct.abs() <= 0.22).all():
        checks_passed += 1
    else:
        n_outliers = (pct.abs() > 0.22).sum()
        failures.append(f"发现{n_outliers}个涨跌幅超22%的异常")

    # 5. 成交量非负
    if (df['volume'] >= 0).all():
        checks_passed += 1
    else:
        failures.append("存在负成交量")

    # 6. 时间序列单调递增
    if df['date'].is_monotonic_increasing:
        checks_passed += 1
    else:
        warnings.append("时间序列未排序（已自动排序）")
        checks_passed += 1  # 非致命问题

    # 7. 无重复日期
    if not df['date'].duplicated().any():
        checks_passed += 1
    else:
        failures.append(f"存在{df['date'].duplicated().sum()}个重复日期")

    return DataQualityReport(
        is_valid=len(failures) == 0,
        total_checks=total,
        passed_checks=checks_passed,
        failed_checks=failures,
        warnings=warnings,
    )
```

---

# 二、MCP工具的专项质量验证

## 2.1 MCP协议合规性检查清单

### 工具Schema规范性

| 检查项 | 要求 | 检查方法 |
|:-------|:-----|:---------|
| 工具名称 | snake_case，描述性 | 自动化命名检查 |
| 工具描述 | ≥ 30字符，说明用途+使用场景+输入输出 | 长度+关键词检查 |
| 参数类型 | 使用JSON Schema标准类型 | Schema校验 |
| 参数描述 | 每个参数有description | Schema遍历检查 |
| 必填参数 | required字段正确设置 | Schema校验 |
| 返回值格式 | 纯文本/Markdown，LLM可读 | 返回值解析测试 |
| 错误返回 | 结构化错误信息（含错误类型+原因+建议） | 错误场景测试 |

### 工具描述的Prompt Engineering质量标准

```python
# 好的工具描述（LLM友好）
@mcp.tool(description="""
获取A股个股历史行情数据。

使用场景：当用户询问某只股票的历史价格走势、成交量变化、
技术分析等问题时调用此工具。

输入：
- symbol: 股票代码，如 "000001"（平安银行）、"600519"（贵州茅台）
- period: 数据周期，"daily"（日线）/ "weekly"（周线）/ "monthly"（月线）
- count: 返回数据条数，默认30

输出：包含日期、开高低收、成交量的表格数据

注意：
- 仅支持A股市场
- 非交易日无数据
- 数据可能有15分钟延迟
""")
async def get_stock_data(symbol: str, period: str = "daily", count: int = 30):
    ...

# ❌ 不好的工具描述
@mcp.tool(description="获取股票数据")  # 太短，LLM无法判断何时使用
async def get_stock_data(symbol: str):
    ...
```

## 2.2 MCP工具测试方法详解

### 方法一：FastMCP 内置测试客户端（推荐）

```python
# 最轻量级，直接在pytest中使用
from fastmcp import Client

async def test_my_tool():
    async with Client(mcp_server) as client:
        # 列出工具
        tools = await client.list_tools()
        # 调用工具
        result = await client.call_tool("tool_name", {"param": "value"})
        # 断言结果
        assert "expected" in result[0].text
```

### 方法二：MCP Inspector（手动探索性测试）

```bash
# 启动Inspector GUI
npx @modelcontextprotocol/inspector python3 mcp/server.py

# 功能：
# - 可视化浏览所有注册的工具
# - 手动输入参数并执行工具
# - 查看原始JSON-RPC通信
# - 实时查看stderr日志
```

### 方法三：模拟LLM调用测试

```python
# 使用脚本模拟LLM的工具调用流程
import json

class MockLLMToolCaller:
    """模拟LLM调用工具的行为"""

    def __init__(self, client):
        self.client = client

    async def simulate_query(self, user_query: str):
        """模拟用户查询 → LLM选择工具 → 执行 → 返回"""
        tools = await self.client.list_tools()

        # 基于简单关键词匹配模拟LLM的工具选择
        selected = self._match_tool(user_query, tools)
        if not selected:
            return "no_tool_matched"

        # 模拟参数提取
        params = self._extract_params(user_query, selected)

        # 执行工具
        result = await self.client.call_tool(selected.name, params)
        return result

    def _match_tool(self, query, tools):
        """简单的工具匹配逻辑"""
        for tool in tools:
            if any(kw in query for kw in tool.description.split()):
                return tool
        return None
```

## 2.3 Benchmark指标体系

```python
# mcp/tests/benchmarks.py
"""MCP工具性能基准测试"""

import time
import statistics
from collections import defaultdict

class MCPBenchmark:
    """MCP工具性能基准收集器"""

    def __init__(self):
        self.metrics = defaultdict(list)

    async def measure_tool(self, client, tool_name, params, iterations=20):
        """测量工具性能指标"""
        latencies = []
        errors = 0

        for _ in range(iterations):
            start = time.monotonic()
            try:
                result = await client.call_tool(tool_name, params)
                elapsed = time.monotonic() - start
                latencies.append(elapsed)
            except Exception:
                errors += 1

        return {
            "tool": tool_name,
            "p50": statistics.median(latencies),
            "p95": sorted(latencies)[int(len(latencies) * 0.95)],
            "p99": sorted(latencies)[int(len(latencies) * 0.99)],
            "error_rate": errors / iterations,
            "iterations": iterations,
        }
```

**关键Benchmark阈值（建议）：**

| 指标 | 目标值 | 告警阈值 | 说明 |
|:-----|:-------|:---------|:-----|
| P50响应时间 | < 1s | > 3s | 日常数据查询 |
| P95响应时间 | < 3s | > 8s | 含网络请求 |
| P99响应时间 | < 5s | > 15s | 极端场景 |
| 错误率 | < 2% | > 5% | 包含API超时 |
| 缓存命中率 | > 60% | < 30% | 重复查询场景 |
| LLM正确调用率 | > 90% | < 70% | 工具描述质量的间接指标 |

---

# 三、持续迭代的工程化框架

## 3.1 迭代循环模型（Quality Flywheel）

```
┌─────────────────────────────────────────────────────────────┐
│                    质量飞轮 (Quality Flywheel)                │
│                                                              │
│    ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│    │  1.开发   │───▶│  2.测试   │───▶│  3.部署   │            │
│    │  (Dev)   │    │  (Test)  │    │ (Deploy) │             │
│    └──────────┘    └──────────┘    └──────────┘             │
│         ▲                                │                   │
│         │                                ▼                   │
│    ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│    │  6.改进   │◀───│  5.反馈   │◀───│  4.监控   │            │
│    │(Improve) │    │(Feedback)│    │(Monitor) │             │
│    └──────────┘    └──────────┘    └──────────┘             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 各环节具体实践

#### 1️⃣ 开发阶段 (Dev)

```
实践：
├── 编写代码 + 类型注解
├── 本地运行 ruff check + ruff format
├── 编写/更新单元测试
├── pre-commit hooks 自动检查
│   ├── ruff (lint + format)
│   ├── mypy (类型检查)
│   ├── bandit (安全扫描)
│   └── pytest (快速测试)
└── 使用 MCP Inspector 手动验证新工具
```

#### 2️⃣ 测试阶段 (Test)

```
实践：
├── 单元测试 (pytest)
│   ├── 工具函数逻辑正确性
│   ├── 数据验证schema
│   └── 错误处理路径
├── 集成测试 (FastMCP Client)
│   ├── 工具注册完整性
│   ├── 端到端调用链
│   └── Schema合规性
├── 数据质量测试
│   ├── Pandera schema验证
│   ├── 价格连续性检查
│   └── 跨源一致性对比
├── 性能测试
│   └── P50/P95响应时间基准
└── 代码覆盖率报告生成
```

#### 3️⃣ 部署阶段 (Deploy)

```
实践：
├── 版本号更新 (SemVer)
├── CHANGELOG更新
├── Git tag打标签
├── MCP配置更新 (.mcp.json)
└── 本地验证: fastmcp dev / mcp inspector
```

#### 4️⃣ 监控阶段 (Monitor)

```
实践：
├── 运行日志
│   ├── 工具调用日志 (tool_name, params, duration, status)
│   ├── 错误日志 (traceback, error_type)
│   └── 日志存储: data/logs/mcp_tool_calls.jsonl
├── 指标收集
│   ├── 各工具调用次数
│   ├── 各工具成功/失败率
│   ├── 平均响应时间趋势
│   └── 数据新鲜度（上次更新时间）
└── 告警
    ├── 错误率 > 5% 告警
    └── 响应时间 P95 > 8s 告警
```

**轻量级日志收集实现：**

```python
# mcp/utils/telemetry.py
"""轻量级MCP工具调用遥测"""

import json
import time
from pathlib import Path
from datetime import datetime
from functools import wraps

LOG_FILE = Path("data/logs/mcp_tool_calls.jsonl")

def track_tool_call(func):
    """装饰器：追踪工具调用指标"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.monotonic()
        status = "success"
        error_msg = None

        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            status = "error"
            error_msg = str(e)
            raise
        finally:
            duration = time.monotonic() - start
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "tool": func.__name__,
                "duration_ms": round(duration * 1000),
                "status": status,
                "error": error_msg,
                "params_summary": str(kwargs)[:200],
            }
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    return wrapper

# 使用示例
@track_tool_call
async def get_stock_data(symbol: str, period: str = "daily"):
    ...
```

#### 5️⃣ 反馈阶段 (Feedback)

```
实践：
├── 日志分析
│   ├── 哪些工具调用最多？（优先优化）
│   ├── 哪些经常失败？（优先修复）
│   └── 哪些从未被调用？（考虑移除或改进描述）
├── LLM调用质量反馈
│   ├── 工具是否被正确选择？
│   ├── 参数是否被正确提取？
│   └── 返回值是否被LLM正确解读？
└── 用户反馈
    └── 研报质量评价 → 反推数据工具质量
```

#### 6️⃣ 改进阶段 (Improve)

```
实践：
├── Bug修复 (根据错误日志)
├── 性能优化 (根据响应时间趋势)
├── 工具描述优化 (Prompt Engineering)
│   ├── A/B测试不同描述
│   └── 观察LLM调用成功率变化
├── 新工具开发 (根据用户需求)
├── SOP更新 (SOP/目录)
├── 测试用例补充 (根据发现的新边界条件)
└── → 回到开发阶段，开始新的循环
```

## 3.2 版本管理策略

### 语义化版本（SemVer）在MCP工具中的应用

```
MAJOR.MINOR.PATCH

MAJOR (主版本): 不兼容的API变更
  例: 工具名称变更、参数结构重大调整、删除工具
  → 需更新所有依赖此工具的Agent prompt

MINOR (次版本): 向后兼容的功能新增
  例: 新增工具、新增可选参数、增强返回信息
  → 现有调用不受影响

PATCH (修订版本): 向后兼容的问题修复
  例: Bug修复、性能优化、描述改进
  → 透明升级
```

**版本记录位置：**
```python
# mcp/server.py
mcp = FastMCP(
    "investment-research-assistant",
    version="0.2.0",  # 每次发布更新
)
```

**CHANGELOG维护模板：**
```markdown
# Changelog

## [0.2.0] - 2026-04-10

### Added
- 新增 `get_futures_data` 工具（期货行情数据）
- `get_stock_data` 新增 `adjust` 参数（前/后复权）

### Changed
- `generate_report` 优化HTML模板输出质量

### Fixed
- 修复 akshare API超时时的回退逻辑

### Performance
- `get_macro_data` P95响应时间从 4.2s 降至 1.8s（新增缓存）
```

## 3.3 监控与可观测性

### 数据新鲜度监控

```python
# mcp/utils/freshness.py
"""数据新鲜度监控"""

from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class FreshnessCheck:
    data_source: str
    last_updated: datetime
    max_age: timedelta
    is_fresh: bool
    staleness: str  # "2小时前更新" 或 "⚠️ 过期3天"

FRESHNESS_SLA = {
    # 数据类型: 最大允许延迟
    "stock_daily":   timedelta(hours=4),    # 日行情: 收盘后4小时内
    "stock_realtime": timedelta(minutes=15), # 实时行情: 15分钟
    "macro_monthly": timedelta(days=7),      # 月度宏观: 7天
    "macro_quarterly": timedelta(days=30),   # 季度数据: 30天
    "company_annual": timedelta(days=90),    # 年报数据: 90天
    "futures_daily": timedelta(hours=4),     # 期货日行情: 4小时
}
```

## 3.4 工具描述优化迭代方法

**Prompt Engineering for Tool Descriptions 的迭代框架：**

```
第1轮: 写基础描述 → 观察LLM是否正确调用
  ↓ 如果调用率 < 80%
第2轮: 增加使用场景示例 → 再观察
  ↓ 如果参数提取错误 > 10%
第3轮: 增加参数示例值 → 再观察
  ↓ 如果返回值被误解
第4轮: 优化返回值格式说明 → 达标
```

**描述质量评估rubric：**

| 维度 | 权重 | 评分标准 |
|:-----|:----:|:---------|
| 用途清晰度 | 30% | LLM能否判断何时使用此工具 |
| 参数说明 | 25% | 每个参数有类型+示例+约束 |
| 场景覆盖 | 20% | 列出了典型使用场景 |
| 限制说明 | 15% | 说明了工具的边界和限制 |
| 返回格式 | 10% | 说明了返回数据的结构 |

---

# 四、金融数据工具的特化质量标准

## 4.1 数据准确性验证

```python
# 交叉验证策略
CROSS_VALIDATION_RULES = {
    "stock_price": {
        "primary": "akshare",
        "secondary": "yfinance",
        "tolerance": 0.001,  # 价格允许0.1%偏差（汇率/复权差异）
        "check_fields": ["close", "volume"],
    },
    "macro_gdp": {
        "primary": "akshare",
        "secondary": "国家统计局API",
        "tolerance": 0.0,    # 宏观数据必须完全一致
    },
}
```

## 4.2 实时性SLA

| 数据类型 | 时效性要求 | 检查频率 | 告警条件 |
|:---------|:----------|:---------|:---------|
| A股日行情 | T日收盘后4小时 | 每日18:00 | 超时未更新 |
| 期货行情 | T日收盘后2小时 | 每日17:00 | 超时未更新 |
| 宏观月度数据 | 发布后7天内 | 每周一 | 超时未入库 |
| 公司财报 | 披露后3天内 | 每日检查 | 超时未入库 |

## 4.3 合规性检查

```python
DATA_COMPLIANCE_CHECKS = [
    "数据源是否有合法的使用协议？",
    "是否遵守了数据源的API调用频率限制？",
    "衍生数据是否标注了原始来源？",
    "是否包含非公开信息？(内幕信息禁止)",
    "数据存储是否符合个人信息保护规定？",
]
```

## 4.4 回测验证

```python
# 历史数据回测一致性
def validate_historical_consistency(symbol: str, date: str):
    """
    验证历史数据的一致性：
    1. 同一日期多次查询返回相同结果
    2. 复权数据与原始数据逻辑一致
    3. 分钟线聚合后与日线一致
    """
    pass
```

---

# 五、推荐工具链与自动化方案（可立即落地）

## 5.1 工具链总览

```
┌─────────────────────────────────────────────────────────────────┐
│                   投研MCP项目 质量保障工具链                      │
│                                                                  │
│  ┌──── 开发阶段 ────┐  ┌──── CI/CD ────┐  ┌──── 运行时 ────┐  │
│  │                   │  │               │  │                │  │
│  │  Ruff (lint)      │  │  GitHub       │  │  Telemetry     │  │
│  │  mypy (types)     │  │  Actions      │  │  decorator     │  │
│  │  bandit (sec)     │  │               │  │                │  │
│  │  pytest (test)    │  │  ┌─────────┐  │  │  JSONL logs    │  │
│  │  pre-commit       │  │  │ Stage 1 │  │  │                │  │
│  │                   │  │  │ Lint    │  │  │  Freshness     │  │
│  │  MCP Inspector    │  │  │ Type    │  │  │  monitor       │  │
│  │  (manual debug)   │  │  │ Sec     │  │  │                │  │
│  │                   │  │  ├─────────┤  │  └────────────────┘  │
│  │  Pandera          │  │  │ Stage 2 │  │                      │
│  │  (data schema)    │  │  │ Test    │  │                      │
│  │                   │  │  │ Cover   │  │                      │
│  └───────────────────┘  │  └─────────┘  │                      │
│                          └───────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

## 5.2 pre-commit 配置（立即可用）

```yaml
# .pre-commit-config.yaml
repos:
  # Ruff: 代码风格 + 格式化
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  # mypy: 类型检查
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.14.0
    hooks:
      - id: mypy
        additional_dependencies: [pandas-stubs, types-requests]
        args: [--ignore-missing-imports]
        files: ^(mcp|tools|scripts)/

  # Bandit: 安全扫描
  - repo: https://github.com/PyCQA/bandit
    rev: 1.8.3
    hooks:
      - id: bandit
        args: [-r, -ll, --skip, B101]
        files: ^(mcp|tools|scripts)/

  # 通用检查
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
        args: [--maxkb=500]
```

**安装命令：**
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files  # 首次全量运行
```

## 5.3 GitHub Actions CI/CD 配置

```yaml
# .github/workflows/quality.yml
name: Quality Gate

on:
  push:
    branches: [main]
    paths: ['mcp/**', 'tools/**', 'scripts/**']
  pull_request:
    branches: [main]
    paths: ['mcp/**', 'tools/**', 'scripts/**']

jobs:
  quality:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r mcp/requirements.txt
          pip install ruff mypy bandit pytest pytest-cov pytest-asyncio pandera

      # Stage 1: 静态分析
      - name: 🔍 Ruff Lint
        run: ruff check mcp/ tools/ scripts/

      - name: 🔍 Ruff Format Check
        run: ruff format --check mcp/ tools/ scripts/

      - name: 🔒 Bandit Security Scan
        run: bandit -r mcp/ tools/ scripts/ -ll --skip B101 -f json -o bandit-report.json
        continue-on-error: true  # 初期不阻断，逐步收紧

      - name: 📝 mypy Type Check
        run: mypy mcp/ --ignore-missing-imports
        continue-on-error: true  # 初期不阻断

      # Stage 2: 测试
      - name: 🧪 Run Tests
        run: |
          pytest mcp/tests/ \
            --cov=mcp \
            --cov-report=term-missing \
            --cov-report=html:htmlcov \
            --cov-fail-under=0 \
            -v --tb=short

      # Stage 3: 报告
      - name: 📊 Upload Coverage Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: htmlcov/

      - name: 📊 Upload Security Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: security-report
          path: bandit-report.json
```

## 5.4 pyproject.toml 统一配置

```toml
# pyproject.toml (项目根目录)

[project]
name = "investment-research-mcp"
version = "0.2.0"
description = "AI驱动的全链路投研MCP工具集"
requires-python = ">=3.11"

[project.dependencies]
fastmcp = ">=3.0.0"
akshare = ">=1.10.0"
yfinance = ">=0.2.0"
pandas = ">=2.0.0"

[project.optional-dependencies]
dev = [
    "ruff>=0.9.0",
    "mypy>=1.14.0",
    "bandit>=1.8.0",
    "pytest>=8.0.0",
    "pytest-cov>=6.0.0",
    "pytest-asyncio>=0.24.0",
    "pandera>=0.20.0",
    "pandas-stubs",
    "radon>=6.0.0",
    "pre-commit>=4.0.0",
]

# ===== Ruff 配置 =====
[tool.ruff]
line-length = 120
target-version = "py311"
src = ["mcp", "tools", "scripts"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "N", "S", "RUF"]
ignore = ["E501", "S101"]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "S106"]

[tool.ruff.lint.isort]
combine-as-imports = true
known-first-party = ["mcp"]

# ===== mypy 配置 =====
[tool.mypy]
python_version = "3.11"
warn_return_any = true
disallow_untyped_defs = true
check_untyped_defs = true
ignore_missing_imports = true
no_implicit_optional = true

# ===== pytest 配置 =====
[tool.pytest.ini_options]
testpaths = ["mcp/tests", "tests"]
python_files = ["test_*.py"]
addopts = ["-v", "--tb=short", "--strict-markers"]
markers = [
    "slow: 慢速测试(网络请求)",
    "integration: 集成测试",
    "data_quality: 数据质量测试",
]
asyncio_mode = "auto"

# ===== coverage 配置 =====
[tool.coverage.run]
source = ["mcp", "tools", "scripts"]
branch = true
omit = ["*/tests/*", "*/__pycache__/*"]

[tool.coverage.report]
fail_under = 0
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.",
    "raise NotImplementedError",
    "pass",
]

# ===== bandit 配置 =====
[tool.bandit]
exclude_dirs = ["tests", ".venv"]
skips = ["B101"]
```

---

# 六、可执行质量验证Checklist

## 🏁 每次提交前 (Pre-commit)

- [ ] `ruff check --fix .` — 代码风格通过
- [ ] `ruff format .` — 代码格式化
- [ ] `mypy mcp/` — 类型检查无严重错误
- [ ] `bandit -r mcp/ -ll` — 无高危安全漏洞
- [ ] `pytest mcp/tests/ -x` — 所有测试通过

## 🔄 每次新增/修改MCP工具后

- [ ] 工具有 ≥30字符的description
- [ ] 每个参数有description和类型注解
- [ ] 必填参数在required中
- [ ] 错误场景返回结构化错误信息（非异常抛出）
- [ ] 新增至少3个单元测试用例
- [ ] MCP Inspector手动验证通过
- [ ] 更新 CHANGELOG

## 📊 每次发布新版本前

- [ ] 版本号按SemVer更新
- [ ] CHANGELOG已更新
- [ ] 所有测试通过 (包括slow标记的集成测试)
- [ ] 代码覆盖率 ≥ 当前阈值
- [ ] Bandit安全扫描无HIGH级别问题
- [ ] 工具schema完整性自动检查通过
- [ ] 性能基准无退化

## 📈 每月质量审查

- [ ] 分析工具调用日志，识别高频失败工具
- [ ] 审查覆盖率趋势，评估是否提升阈值
- [ ] 检查数据新鲜度SLA达标情况
- [ ] 评估工具描述质量（LLM调用成功率）
- [ ] 清理未使用的工具或参数
- [ ] 更新依赖版本

---

# 七、迭代流程图（完整生命周期）

```
                    ┌─────────────────────┐
                    │   需求/问题识别      │
                    │  (用户反馈/日志分析)  │
                    └─────────┬───────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │      Phase 1: 开发 (Dev)       │
              │                                │
              │  1. 编写/修改代码              │
              │  2. 添加类型注解              │
              │  3. 编写单元测试              │
              │  4. 本地 pre-commit 通过       │
              └───────────────┬───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │    Phase 2: 验证 (Verify)      │
              │                                │
              │  ┌─── 静态分析 ───┐           │
              │  │ ruff check     │           │
              │  │ mypy           │           │
              │  │ bandit         │           │
              │  └────────────────┘           │
              │  ┌─── 动态测试 ───┐           │
              │  │ pytest         │           │
              │  │ coverage       │           │
              │  │ Pandera schema │           │
              │  └────────────────┘           │
              │  ┌─── MCP专项 ────┐           │
              │  │ FastMCP Client │           │
              │  │ MCP Inspector  │           │
              │  │ Schema完整性   │           │
              │  └────────────────┘           │
              └───────────────┬───────────────┘
                              │
                     ┌────────┴────────┐
                     │  所有检查通过？   │
                     └───┬────────┬────┘
                    Yes  │        │ No
                         │        └──────▶ 返回 Phase 1
                         ▼
              ┌───────────────────────────────┐
              │    Phase 3: 发布 (Release)     │
              │                                │
              │  1. 更新版本号 (SemVer)        │
              │  2. 更新 CHANGELOG             │
              │  3. Git tag                    │
              │  4. 更新 .mcp.json             │
              │  5. 通知 .agentstalk/          │
              └───────────────┬───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │    Phase 4: 运行 (Runtime)     │
              │                                │
              │  1. @track_tool_call 遥测      │
              │  2. 调用日志 → JSONL           │
              │  3. 错误率监控                 │
              │  4. 响应时间追踪               │
              │  5. 数据新鲜度检查             │
              └───────────────┬───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │    Phase 5: 洞察 (Insight)     │
              │                                │
              │  1. 工具使用频率分析            │
              │  2. 错误模式聚类               │
              │  3. 性能趋势分析               │
              │  4. 用户满意度/研报质量评估     │
              └───────────────┬───────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │   需求/问题识别      │
                    │  (新一轮迭代开始)    │
                    └─────────────────────┘
```

---

## Next Action: 对当前投研MCP项目的具体落地建议

### 🔴 立即执行（本周）

| # | 任务 | 预计工时 | 执行者 |
|:-:|:-----|:---------|:-------|
| 1 | 在项目根目录创建 `pyproject.toml`（上面Section 5.4的完整配置） | 0.5h | Tools Agent |
| 2 | 安装 pre-commit 并配置 `.pre-commit-config.yaml` | 0.5h | Tools Agent |
| 3 | 创建 `mcp/tests/` 目录结构和 `conftest.py` | 1h | Tools Agent |
| 4 | 为 `market_data.py` 编写首批5个单元测试 | 2h | Tools Agent |
| 5 | 为 MCP server 编写3个集成测试（工具注册、schema完整性、基本调用） | 2h | Tools Agent |
| 6 | 运行一次完整的 `ruff check` + `mypy` 基线扫描，记录当前问题数 | 0.5h | Tools Agent |

### 🟠 短期规划（2周内）

| # | 任务 | 预计工时 |
|:-:|:-----|:---------|
| 7 | 为剩余4个工具模块编写单元测试 | 8h |
| 8 | 添加 Pandera 数据质量schema | 2h |
| 9 | 实现 `@track_tool_call` 遥测装饰器 | 1h |
| 10 | 创建 `.github/workflows/quality.yml` CI配置 | 1h |
| 11 | 修复 ruff/mypy 扫描出的高优先级问题 | 4h |

### 🟡 中期规划（1-3个月）

| # | 任务 |
|:-:|:-----|
| 12 | 覆盖率阈值提升至 50% → 70% |
| 13 | 性能基准测试建立与监控 |
| 14 | 工具描述优化迭代（基于LLM调用日志） |
| 15 | 数据新鲜度自动监控脚本 |
| 16 | 跨数据源一致性自动对比 |

### 💡 成本效益评估

| 方案 | 成本 | 收益 | 推荐 |
|:-----|:-----|:-----|:----:|
| pre-commit + ruff | 零成本（开源） | 阻止90%风格问题 | ⭐⭐⭐⭐⭐ |
| pytest + conftest | 零成本（开源） | 核心逻辑保障 | ⭐⭐⭐⭐⭐ |
| GitHub Actions | 免费（公开仓库）/ 2000分钟/月（私有） | 自动化门禁 | ⭐⭐⭐⭐ |
| Pandera | 零成本（开源） | 数据质量保障 | ⭐⭐⭐⭐ |
| @track_tool_call | 零成本（自建） | 运行时可观测 | ⭐⭐⭐⭐ |
| Great Expectations | 零成本但学习曲线高 | 企业级数据验证 | ⭐⭐⭐（后期） |

---

## References

1. [FastMCP Testing Patterns](https://fastmcp.wiki/en/patterns/testing)
2. [MCP Inspector Official Docs](https://modelcontextprotocol.io/docs/tools/inspector)
3. [Ruff Python Linter](https://docs.astral.sh/ruff/)
4. [pytest Best Practices 2025](https://pytest-with-eric.com/pytest-best-practices/)
5. [Pandera Data Validation](https://pandera.readthedocs.io/)
6. [Bandit Security Scanner](https://bandit.readthedocs.io/)
7. [MCP Evals Guide](https://dev.to/matt_lenhard_650f4412cb21/mcp-evals-how-to-test-your-mcp-tools-13h1)
8. [Python Best Practices 2025](https://github.com/jtgsystems/PYTHON-BEST-PRACTICES-2025)
9. [coverage.py Documentation](https://coverage.readthedocs.io/)
10. [Comprehensive MCP Testing Strategy 2025](https://markaicode.com/model-context-protocol-testing-strategy-2025/)

---

*本文档由 Quality-Research-Agent 基于2025年最新行业实践调研生成，供 Chief-Architect-Agent 决策参考。*
