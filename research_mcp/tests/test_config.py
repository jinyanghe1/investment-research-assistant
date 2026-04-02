"""配置模块单元测试"""
import os


class TestMCPConfig:
    def test_default_values(self):
        """默认配置值正确"""
        from config import MCPConfig
        cfg = MCPConfig()
        assert cfg.cache_ttl_realtime == 300
        assert cfg.cache_ttl_history == 3600
        assert cfg.cache_ttl_macro == 86400
        assert cfg.cache_ttl_financial == 43200
        assert cfg.cache_dir == "data"
        assert cfg.api_timeout == 30
        assert cfg.max_records == 60
        assert cfg.default_history_days == 30
        assert cfg.reports_dir == "reports"

    def test_workspace_auto_detect(self):
        """workspace_root 自动推断为 mcp/ 的父目录"""
        from config import MCPConfig
        cfg = MCPConfig()
        # workspace_root 应为 config.py 所在目录的父目录
        mcp_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        expected_workspace = os.path.dirname(mcp_dir)
        assert cfg.workspace_root == expected_workspace

    def test_abs_paths(self):
        """abs_cache_dir, abs_reports_dir 正确拼接"""
        from config import MCPConfig
        cfg = MCPConfig()
        assert os.path.isabs(cfg.abs_cache_dir)
        assert cfg.abs_cache_dir.endswith("data")
        assert os.path.isabs(cfg.abs_reports_dir)
        assert cfg.abs_reports_dir.endswith("reports")

    def test_mcp_root(self):
        """mcp_root 指向 config.py 所在目录"""
        from config import MCPConfig
        cfg = MCPConfig()
        assert os.path.isabs(cfg.mcp_root)
        assert os.path.isfile(os.path.join(cfg.mcp_root, "config.py"))

    def test_index_json_path(self):
        """index_json_path 拼接正确"""
        from config import MCPConfig
        cfg = MCPConfig()
        assert cfg.index_json_path.endswith("index.json")
        assert cfg.workspace_root in cfg.index_json_path

    def test_env_override(self, monkeypatch):
        """环境变量 MCP_ 前缀可覆盖配置"""
        monkeypatch.setenv("MCP_MAX_RECORDS", "100")
        monkeypatch.setenv("MCP_API_TIMEOUT", "60")
        from config import MCPConfig
        cfg = MCPConfig()
        assert cfg.max_records == 100
        assert cfg.api_timeout == 60

    def test_global_singleton_exists(self):
        """全局 config 单例可导入"""
        from config import config
        assert config is not None
        assert hasattr(config, "max_records")
