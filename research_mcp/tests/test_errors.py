"""错误处理单元测试"""
from utils.errors import handle_errors, MCPToolError, ErrorCode


class TestHandleErrors:
    def test_success_passthrough(self):
        """正常函数透传返回"""
        @handle_errors
        def ok_func():
            return {"status": "ok", "data": [1, 2, 3]}

        result = ok_func()
        assert result == {"status": "ok", "data": [1, 2, 3]}

    def test_mcp_error_captured(self):
        """MCPToolError 捕获为结构化错误"""
        @handle_errors
        def bad_param_func():
            raise MCPToolError(ErrorCode.INVALID_PARAM, "参数 symbol 不能为空")

        result = bad_param_func()
        assert result["error"] is True
        assert result["code"] == ErrorCode.INVALID_PARAM
        assert "symbol" in result["message"]

    def test_timeout_captured(self):
        """TimeoutError 捕获为 API_TIMEOUT"""
        @handle_errors
        def slow_func():
            raise TimeoutError("akshare 请求超时")

        result = slow_func()
        assert result["error"] is True
        assert result["code"] == ErrorCode.API_TIMEOUT
        assert "超时" in result["message"]

    def test_generic_exception(self):
        """其他异常捕获为 INTERNAL_ERROR"""
        @handle_errors
        def crash_func():
            raise ValueError("unexpected value")

        result = crash_func()
        assert result["error"] is True
        assert result["code"] == ErrorCode.INTERNAL_ERROR
        assert "ValueError" in result["message"]

    def test_error_contains_tool_name(self):
        """错误信息包含被装饰函数的名称"""
        @handle_errors
        def my_named_tool():
            raise RuntimeError("boom")

        result = my_named_tool()
        assert result["tool"] == "my_named_tool"

    def test_preserves_function_name(self):
        """装饰器保留原函数名（functools.wraps）"""
        @handle_errors
        def original_name():
            return "hello"

        assert original_name.__name__ == "original_name"

    def test_mcp_error_codes(self):
        """验证所有错误码常量存在"""
        assert ErrorCode.API_ERROR == "API_ERROR"
        assert ErrorCode.API_TIMEOUT == "API_TIMEOUT"
        assert ErrorCode.DATA_NOT_FOUND == "DATA_NOT_FOUND"
        assert ErrorCode.INVALID_PARAM == "INVALID_PARAM"
        assert ErrorCode.PARSE_ERROR == "PARSE_ERROR"
        assert ErrorCode.FILE_ERROR == "FILE_ERROR"
        assert ErrorCode.INTERNAL_ERROR == "INTERNAL_ERROR"

    def test_mcp_tool_error_str(self):
        """MCPToolError 的字符串表示"""
        err = MCPToolError("TEST_CODE", "test message")
        assert "[TEST_CODE]" in str(err)
        assert "test message" in str(err)
        assert err.code == "TEST_CODE"
        assert err.message == "test message"
