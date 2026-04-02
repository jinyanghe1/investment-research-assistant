"""
投研MCP Server 统一错误处理
提供 @handle_errors 装饰器和 MCPToolError 异常类
"""
import functools
import logging
import traceback

logger = logging.getLogger("mcp.tools")


class MCPToolError(Exception):
    """MCP工具业务错误"""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


# 常用错误码
class ErrorCode:
    API_ERROR = "API_ERROR"              # 外部API调用失败
    API_TIMEOUT = "API_TIMEOUT"          # API超时
    DATA_NOT_FOUND = "DATA_NOT_FOUND"    # 数据未找到
    INVALID_PARAM = "INVALID_PARAM"      # 参数无效
    PARSE_ERROR = "PARSE_ERROR"          # 数据解析失败
    FILE_ERROR = "FILE_ERROR"            # 文件操作失败
    INTERNAL_ERROR = "INTERNAL_ERROR"    # 内部错误


def handle_errors(func):
    """
    统一错误处理装饰器
    - MCPToolError → 结构化业务错误
    - TimeoutError → API超时错误
    - 其他异常 → 内部错误（含简要traceback）
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except MCPToolError as e:
            logger.warning(f"工具 {func.__name__} 业务错误: {e}")
            return {
                "error": True,
                "code": e.code,
                "message": e.message,
                "tool": func.__name__
            }
        except TimeoutError as e:
            logger.error(f"工具 {func.__name__} 超时: {e}")
            return {
                "error": True,
                "code": ErrorCode.API_TIMEOUT,
                "message": f"请求超时: {str(e)}",
                "tool": func.__name__
            }
        except Exception as e:
            tb = traceback.format_exc().split('\n')[-3:]  # 只保留最后3行
            logger.error(f"工具 {func.__name__} 内部错误: {e}\n{''.join(tb)}")
            return {
                "error": True,
                "code": ErrorCode.INTERNAL_ERROR,
                "message": f"{type(e).__name__}: {str(e)}",
                "tool": func.__name__
            }
    return wrapper
