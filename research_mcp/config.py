"""
投研MCP Server 配置管理
使用 Pydantic BaseSettings，支持环境变量覆盖（前缀 MCP_）
"""
import os
from pydantic_settings import BaseSettings


class MCPConfig(BaseSettings):
    """MCP Server 全局配置"""

    # 缓存配置
    cache_ttl_realtime: int = 300       # 行情数据缓存TTL（秒），默认5分钟
    cache_ttl_history: int = 3600       # 历史数据缓存TTL（秒），默认1小时
    cache_ttl_macro: int = 86400        # 宏观数据缓存TTL（秒），默认24小时
    cache_ttl_financial: int = 43200    # 财务数据缓存TTL（秒），默认12小时
    cache_dir: str = "data"             # 缓存文件目录（相对于MCP根目录）

    # API超时配置
    api_timeout: int = 30               # 通用API请求超时（秒）
    akshare_timeout: int = 30           # akshare请求超时（秒）
    yfinance_timeout: int = 30          # yfinance请求超时（秒）

    # 数据限制
    max_records: int = 60               # 单次返回最大记录数
    default_history_days: int = 30      # 默认历史数据天数

    # 工作区路径（自动推断，也可手动指定）
    workspace_root: str = ""            # 投研助手根目录
    reports_dir: str = "reports"        # 研报输出目录（相对于workspace_root）

    model_config = {"env_prefix": "MCP_"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.workspace_root:
            # 自动推断：mcp/ 的父目录
            mcp_root = os.path.dirname(os.path.abspath(__file__))
            self.workspace_root = os.path.dirname(mcp_root)

    @property
    def mcp_root(self) -> str:
        """MCP Server 根目录"""
        return os.path.dirname(os.path.abspath(__file__))

    @property
    def abs_cache_dir(self) -> str:
        """缓存目录绝对路径"""
        if os.path.isabs(self.cache_dir):
            return self.cache_dir
        return os.path.join(self.mcp_root, self.cache_dir)

    @property
    def abs_reports_dir(self) -> str:
        """研报目录绝对路径"""
        if os.path.isabs(self.reports_dir):
            return self.reports_dir
        return os.path.join(self.workspace_root, self.reports_dir)

    @property
    def index_json_path(self) -> str:
        """index.json 绝对路径"""
        return os.path.join(self.workspace_root, "index.json")


# 全局单例
config = MCPConfig()
