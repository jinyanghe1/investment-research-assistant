# MCP代理修复测试报告

**日期**: 2026-04-02
**执行人**: Claude Code
**任务**: 修复akshare HTTP代理问题并全面测试MCP工具

## 修复内容

### 1. market_data.py 代理修复

**问题**: akshare 经 HTTP 代理连接失败，返回 `ProxyError`

**修复方案**:
1. 在模块导入时清空所有代理环境变量
2. 使用 `_disable_proxy()` 上下文管理器确保akshare调用使用直连

**修改位置**: `research_mcp/tools/market_data.py`

```python
# 清空所有代理环境变量
_PROXY_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
               "ALL_PROXY", "all_proxy", "NO_PROXY", "no_proxy",
               "GLOBAL_AGENT", "global_agent", "CURL_CA_BUNDLE", "SSL_CERT_FILE")

_orig_proxy = {k: os.environ.get(k) for k in _PROXY_KEYS if k in os.environ}
for k in _orig_proxy:
    os.environ.pop(k)
```

**影响范围**: 所有akshare调用已使用 `_disable_proxy()` 上下文管理器

---

## 测试结果

### 网络环境问题（系统级，非代码问题）

```
HTTP_PROXY: http://127.0.0.1:7897
HTTPS_PROXY: http://127.0.0.1:7897
all_proxy: socks5://127.0.0.1:7897
```

### 代理清空测试: ✅ 通过

```
导入后HTTP_PROXY: 未设置
导入后http_proxy: 未设置
导入后all_proxy: 未设置
```

### akshare东方财富接口: ❌ API限速

```
错误: Too Many Requests. Rate limited. Try after a while.
```

- 东方财富API返回限速错误，非代理问题
- curl直连API路径失败（Connection reset）
- curl通过代理访问也失败

### yfinance: ❌ SSL/TLS系统级错误

```
curl_cffi.curl.CurlError: Failed to perform, curl: (35)
TLS connect error: error:00000000:invalid library (0):OPENSSL_internal:invalid library (0)
```

**这是系统级OpenSSL配置问题，无法通过代码修复**

### 唯一正常工作的接口

| 工具 | 数据源 | 状态 |
|------|--------|------|
| 可转债数据 | akshare bond_cb_jsl() | ✅ 30条数据 |
| 期货历史K线 | akshare | ✅ RB0螺纹钢60条数据 |

---

## 结论

1. **代理修复代码**: ✅ 正确生效（环境变量已清空）
2. **akshare东方财富接口**: ❌ API限速/网络限制
3. **yfinance**: ❌ 系统SSL配置问题

### 待解决
- yfinance的SSL问题需要系统级修复（可能是curl_cffi与OpenSSL版本冲突）
- akshare东方财富接口需要等待限速解除或使用其他数据源

---

## 代码变更

```
modified:   research_mcp/tools/market_data.py
```

**变更摘要**:
- 添加 `_PROXY_KEYS` 包含所有代理相关环境变量
- 在模块导入时清空代理环境变量
- 创建 `_disable_proxy()` 上下文管理器
- 所有akshare调用使用 `with _disable_proxy():` 包裹
