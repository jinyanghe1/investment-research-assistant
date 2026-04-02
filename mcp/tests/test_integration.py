"""集成测试 - 验证模块导入与工具注册"""
import pytest


class TestImportability:
    """验证所有独立函数可成功导入"""

    def test_market_data_imports(self):
        from tools.market_data import (
            fetch_stock_realtime, fetch_stock_history,
            fetch_index_quote, fetch_forex, fetch_commodity,
        )
        assert callable(fetch_stock_realtime)
        assert callable(fetch_stock_history)
        assert callable(fetch_index_quote)
        assert callable(fetch_forex)
        assert callable(fetch_commodity)

    def test_macro_data_imports(self):
        from tools.macro_data import (
            fetch_macro_china, fetch_macro_global, fetch_fund_flow,
        )
        assert callable(fetch_macro_china)
        assert callable(fetch_macro_global)
        assert callable(fetch_fund_flow)

    def test_company_analysis_imports(self):
        from tools.company_analysis import (
            fetch_company_financials, fetch_screen_stocks,
            fetch_industry_ranking,
        )
        assert callable(fetch_company_financials)
        assert callable(fetch_screen_stocks)
        assert callable(fetch_industry_ranking)

    def test_report_generator_imports(self):
        from tools.report_generator import (
            build_report, build_data_table, do_register_report,
        )
        assert callable(build_report)
        assert callable(build_data_table)
        assert callable(do_register_report)

    def test_knowledge_base_imports(self):
        from tools.knowledge_base import (
            fetch_reports_list, fetch_reports_search,
        )
        assert callable(fetch_reports_list)
        assert callable(fetch_reports_search)

    def test_all_16_functions_importable(self):
        """一次性验证全部 16 个独立函数"""
        functions = []
        from tools.market_data import fetch_stock_realtime, fetch_stock_history, fetch_index_quote, fetch_forex, fetch_commodity
        functions.extend([fetch_stock_realtime, fetch_stock_history, fetch_index_quote, fetch_forex, fetch_commodity])

        from tools.macro_data import fetch_macro_china, fetch_macro_global, fetch_fund_flow
        functions.extend([fetch_macro_china, fetch_macro_global, fetch_fund_flow])

        from tools.company_analysis import fetch_company_financials, fetch_screen_stocks, fetch_industry_ranking
        functions.extend([fetch_company_financials, fetch_screen_stocks, fetch_industry_ranking])

        from tools.report_generator import build_report, build_data_table, do_register_report
        functions.extend([build_report, build_data_table, do_register_report])

        from tools.knowledge_base import fetch_reports_list, fetch_reports_search
        functions.extend([fetch_reports_list, fetch_reports_search])

        assert len(functions) == 16
        assert all(callable(f) for f in functions)


class TestInfraImports:
    """验证基础设施模块可导入"""

    def test_config(self):
        from config import config, MCPConfig
        assert config is not None
        assert isinstance(config, MCPConfig)

    def test_cache(self):
        from utils.cache import DataCache, get_cache
        assert callable(DataCache)
        assert callable(get_cache)

    def test_errors(self):
        from utils.errors import handle_errors, MCPToolError, ErrorCode
        assert callable(handle_errors)

    def test_formatters(self):
        from utils.formatters import format_number, format_currency, format_change
        assert callable(format_number)
        assert callable(format_currency)
        assert callable(format_change)


class TestToolRegistration:
    """验证工具注册到 FastMCP"""

    def test_all_modules_have_register_tools(self):
        """每个工具模块都有 register_tools 函数"""
        import tools.market_data
        import tools.macro_data
        import tools.company_analysis
        import tools.report_generator
        import tools.knowledge_base

        for mod in [
            tools.market_data,
            tools.macro_data,
            tools.company_analysis,
            tools.report_generator,
            tools.knowledge_base,
        ]:
            assert hasattr(mod, "register_tools"), f"{mod.__name__} 缺少 register_tools"
            assert callable(mod.register_tools)

    def test_server_importable(self):
        """server.py 可作为模块导入（跳过若 fastmcp 与本地 mcp 包冲突）"""
        try:
            import server
            assert hasattr(server, "mcp")
            assert hasattr(server, "ping")
            assert hasattr(server, "list_available_tools")
        except ImportError as e:
            if "McpError" in str(e) or "fastmcp" in str(e):
                pytest.skip(f"fastmcp 导入冲突（mcp/ 包名遮蔽）: {e}")
            raise
