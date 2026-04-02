# P0: 系统级网络/SSL问题 - 优先修复

**创建日期**: 2026-04-02
**优先级**: P0
**状态**: 部分修复中
**负责人**: 待分配

---

## 已完成的修复

### 1. ✅ 代理清空修复 (commit: 6a5362b)
- 在模块导入时清空所有代理环境变量
- 添加 `_disable_proxy()` 上下文管理器

### 2. ✅ yfinance curl_cffi 禁用 (commit: c9323d8)
- 设置 `YFINANCE_DISABLE_CURL_CFFI=1` 环境变量
- yfinance 将使用 requests 代替 curl_cffi
- 避免 `OPENSSL_internal:invalid library` 错误

---

## 问题概述

MCP工具 `market_data.py` 的代理修复代码已完成，但测试发现存在**系统级问题**，导致多个数据接口不可用。

---

## 问题列表

### 1. yfinance SSL/TLS 错误 (P0)

**错误信息**:
```
curl_cffi.curl.CurlError: Failed to perform, curl: (35)
TLS connect error: error:00000000:invalid library (0):OPENSSL_internal:invalid library (0)
```

**影响**:
- A股股票实时行情 (yfinance fallback)
- 美股/港股行情
- 海外指数
- 大宗商品(黄金、白银、原油等)

**根因分析**:
- `yfinance` 使用 `curl_cffi` 库进行HTTP请求
- 系统 OpenSSL 与 curl_cffi 使用的 SSL 库版本冲突
- 错误码 `OPENSSL_internal:invalid library` 表明 OpenSSL 初始化失败

**可能原因**:
1. 系统安装了多个版本的 OpenSSL
2. curl_cffi 编译时链接的 OpenSSL 版本与运行时不同
3. `pycurl` 或其他 curl 相关库的冲突

**建议修复方案**:
```bash
# 方案1: 重新安装 curl_cffi
pip uninstall curl_cffi -y
pip install curl_cffi

# 方案2: 强制使用 requests 替代 curl_cffi
pip install 'yfinance<0.3.0'  # 旧版本使用 requests

# 方案3: 检查 OpenSSL 版本
openssl version
which openssl
```

---

### 2. akshare 东方财富 API 限速 (P0)

**错误信息**:
```
Too Many Requests. Rate limited. Try after a while.
```

**影响**:
- A股实时行情 (akshare stock_zh_a_spot_em)
- 指数行情 (akshare stock_zh_index_spot_em)
- ETF行情 (akshare fund_etf_spot_em)
- 股票筛选 (akshare stock_zh_a_spot)

**根因分析**:
- 东方财富服务器对同一IP的请求频率限制
- 可能需要在请求中添加延时或使用代理轮换

**建议修复方案**:
1. 添加请求延时（两次请求间隔 >= 1秒）
2. 添加重试机制（最多3次，间隔递增）
3. 考虑使用其他数据源作为替代（如 baostock, tushare）

---

### 3. akshare 直连失败 (P0)

**错误信息**:
```
HTTPSConnectionPool(host='push2.eastmoney.com', port=443):
Max retries exceeded with url: /api/qt/clist/get
(Caused by ProxyError('Cannot connect to proxy.', RemoteDisconnected(...)))
```

**注意**: 这个错误在代理清空后仍然存在，说明是网络层面的问题

**测试结果**:
- `curl -x "" https://push2.eastmoney.com` → 超时/连接被重置
- `curl -x "http://127.0.0.1:7897" https://push2.eastmoney.com` → 连接建立但无响应

**可能原因**:
1. 东方财富API服务器对某些IP段有限制
2. 网络运营商对东方财富API的直连有干扰
3. 防火墙/SGS把东方财富API路径屏蔽

---

## 受影响的MCP工具

| 工具 | 数据源 | 当前状态 | 优先级 |
|------|--------|----------|--------|
| get_stock_realtime | akshare → yfinance | ⚠️ yfinance限速中 | P0 |
| get_index_quote (国内) | akshare | ❌ API限速 | P0 |
| get_etf_realtime | akshare | ❌ API限速 | P0 |
| get_forex | akshare → yfinance | ⚠️ yfinance限速中 | P1 |
| get_commodity | yfinance | ⚠️ yfinance限速中 | P0 |
| screen_stocks | akshare | ❌ API限速 | P0 |
| get_valuation_percentile | akshare history | ❌ 直连失败 | P0 |
| get_peer_comparison | akshare | ❌ API限速 | P0 |
| get_fund_flow | akshare | ⚠️ 返回null | P1 |
| get_industry_ranking | akshare | ⚠️ 数据异常 | P1 |

## 正常工作的工具

| 工具 | 数据源 | 状态 |
|------|--------|------|
| get_convertible_bond | akshare bond_cb_jsl | ✅ |
| get_futures_history | akshare | ✅ |
| get_macro_china | akshare macro | ✅ |
| get_policy_rss | WebFetch | ✅ |
| get_technical_indicators | akshare history | ✅ (使用yfinance fallback) |
| get_technical_signal | akshare history | ✅ |
| search_reports | 本地文件 | ✅ |
| list_reports | 本地文件 | ✅ |

---

## 修复计划

### Step 1: 修复 yfinance SSL 问题
```bash
# 检查当前环境
pip show curl_cffi
openssl version -a

# 尝试修复
pip install --upgrade curl_cffi
```

### Step 2: 为 akshare 添加请求延时和重试
- 在 `market_data.py` 中添加全局请求延时
- 添加自动重试机制

### Step 3: 考虑替代数据源
- baostock (免费，A股数据)
- tushare (需要token)
- 聚宽 (需要注册)

---

## 相关文件

- `research_mcp/tools/market_data.py` - 已完成代理清空修复
- `.agentstalk/20260402_mcp_proxy_fix_test.md` - 详细测试报告
