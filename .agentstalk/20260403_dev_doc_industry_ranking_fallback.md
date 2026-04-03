# 开发文档: get_industry_ranking 备源系统

> **文件**: `.agentstalk/20260403_dev_doc_industry_ranking_fallback.md`
> **日期**: 2026-04-03
> **状态**: ✅ 已完成 (ROADMAP 3.5.2)
> **关联文件**:
>   - `research_mcp/utils/fallback_sources.py` (新建)
>   - `research_mcp/tools/company_analysis.py` (修改)
>   - `research_mcp/tests/test_fallback_sources.py` (新建, 18项测试)

---

## 一、问题背景

`get_industry_ranking` 工具用于获取 A 股行业/概念板块景气度排名，是投研分析的核心数据入口。

**原有问题**: 所有数据获取路径都依赖 akshare 库，当 akshare 底层 API（东方财富/同花顺）全部返回空数据或超时时，用户只能得到 mock 数据，丧失实用价值。

**根因分析**:
1. akshare 封装了东方财富 API，但其内部解析逻辑在数据格式变动时容易 break
2. 同花顺 API (ths) 在代理环境下稳定性更差
3. 没有绕过 akshare 直接请求数据源的备选路径

---

## 二、架构设计

### 三级 Fallback 链

```
_fetch_board_data(board_type)
  │
  ├── 1️⃣ akshare API 链 (call_akshare 调用)
  │     ├── stock_board_industry_name_em     (东方财富)
  │     ├── stock_board_industry_summary_ths (同花顺)
  │     └── stock_sector_detail              (通用)
  │
  ├── 2️⃣ push2 直连 (fetch_board_eastmoney_push2)
  │     └── https://push2.eastmoney.com/api/qt/clist/get
  │         绕过 akshare, 直接请求东方财富 HTTP API
  │
  └── 3️⃣ 新浪财经 (fetch_board_sina)
        └── https://vip.stock.finance.sina.com.cn/q/view/newFLJK.php
            申万行业分类, JS变量格式解析
```

### 降级策略

| 场景 | 行为 |
|------|------|
| akshare 返回有效数据 | 直接使用, data_source="akshare" |
| akshare 全部失败, push2 成功 | 使用 push2, data_source="eastmoney_push2" |
| akshare+push2 都失败, 新浪成功 | 使用新浪, data_source="sina" |
| 所有源都失败, 有过期缓存 | 返回缓存 + warning, cache_mode="extended_ttl" |
| 所有源都失败, 无缓存 | 返回 mock 排名 + warning, data_source="mock" |

---

## 三、数据源详情

### 3.1 东方财富 push2 API

**端点**: `https://push2.eastmoney.com/api/qt/clist/get`

**关键参数**:
| 参数 | 值 | 说明 |
|------|---|------|
| fs | `m:90+t:2` | 行业板块 |
| fs | `m:90+t:3` | 概念板块 |
| fid | `f3` | 按涨跌幅排序 |
| fields | `f3,f6,f8,...` | 返回字段 |

**字段映射**:
| 字段代码 | 含义 | 映射到列名 |
|----------|------|-----------|
| f14 | 板块名称 | 名称 |
| f3 | 涨跌幅(%) | 涨跌幅 |
| f8 | 换手率(%) | 换手率 |
| f6 | 成交额(元) | 成交额 |
| f20 | 总市值(元) | 总市值 |
| f128 | 领涨股名称 | 领涨股票 |
| f136 | 领涨股涨跌幅 | 领涨股票-涨跌幅 |
| f104 | 上涨家数 | 上涨家数 |
| f105 | 下跌家数 | 下跌家数 |

**注意事项**:
- 必须显式禁用代理 (`proxies={"http": None, "https": None}`)
- 盘后/非交易日可能返回空响应（空 reply），属正常限流
- 无需 API Key，无需认证

### 3.2 新浪财经 API

**端点**: `https://vip.stock.finance.sina.com.cn/q/view/newFLJK.php`

**参数**:
| 参数 | 值 | 说明 |
|------|---|------|
| param | `industry` | 申万行业分类 |
| param | `concept` | 概念板块 |

**返回格式**: JS 变量赋值 (`var S_Finance_bankuai_industry = {...}`)
- 需用正则提取 JSON 对象
- 值为逗号分隔字符串: `code,名称,股票数,均价,涨跌额,涨跌幅%,成交量,成交额,...`
- 编码: GBK

**局限性**:
- 无换手率数据 (返回 None)
- 无领涨股票数据 (返回 "N/A")
- 概念板块可靠性较低
- 这些缺失字段在 `fetch_industry_ranking` 的结果中会显示为 "N/A"

---

## 四、代码结构

### 新建文件

```
research_mcp/utils/fallback_sources.py    # 备源实现
research_mcp/tests/test_fallback_sources.py  # 18项测试
```

### 修改文件

```
research_mcp/tools/company_analysis.py
  - 顶部新增: from utils.fallback_sources import fetch_board_fallback as _fetch_board_fallback
  - _fetch_board_data(): 增加第二轮备源调用
  - fetch_industry_ranking(): 重写，简化逻辑，通过 df.attrs["_fallback_source"] 追踪数据来源
```

### 关键 import 路径

```python
# company_analysis.py 使用 research_mcp/ 内部路径
from utils.fallback_sources import fetch_board_fallback as _fetch_board_fallback

# 测试中 mock 时，必须 patch 模块级引用:
with patch("research_mcp.tools.company_analysis._fetch_board_fallback", ...):
    ...

# ❌ 错误: 不要 patch 原始模块路径
# patch("research_mcp.utils.fallback_sources.fetch_board_fallback")  # 不生效!
```

---

## 五、测试覆盖

### 运行命令

```bash
cd research_mcp && python -m pytest tests/test_fallback_sources.py -v
```

### 测试矩阵 (18项)

| 测试类 | 测试项 | 覆盖场景 |
|--------|--------|----------|
| TestFetchBoardEastmoneyPush2 | test_industry_success | push2 行业板块正常返回 |
| | test_concept_success | push2 概念板块正常返回 |
| | test_empty_diff | push2 返回空数据 → None |
| | test_network_error | push2 网络异常 → None |
| | test_invalid_board_type | 无效类型 → None |
| TestFetchBoardSina | test_industry_success | 新浪行业解析正确 |
| | test_concept_success | 新浪概念解析正确 |
| | test_network_error | 新浪网络异常 → None |
| | test_malformed_response | 新浪格式异常 → None |
| TestFetchBoardFallback | test_push2_success_no_sina_call | push2 成功则不调新浪 |
| | test_push2_fail_fallback_to_sina | push2 失败 → 新浪 |
| | test_all_sources_fail | 全失败 → None |
| | test_push2_empty_df_fallback_to_sina | push2 空 DF → 新浪 |
| TestFetchBoardDataIntegration | test_akshare_fail_push2_success | akshare失败 → 备源 |
| | test_akshare_success_no_fallback | akshare成功不触发备源 |
| TestFetchIndustryRankingFallback | test_fallback_returns_valid_rankings | 端到端结构验证 |
| | test_all_fail_returns_mock | 全失败 → mock |
| | test_data_source_field_accuracy | data_source字段准确性 |

---

## 六、Troubleshooting 指南

### 问题: push2 返回空响应 / Connection refused

**原因**: 东方财富在盘后或被限流时返回空 TCP 响应

**解决**: 这是预期行为，fallback 链会自动降级到新浪。确认 `data_source` 字段为 `"sina"` 即可。

### 问题: 新浪返回乱码

**原因**: 新浪接口使用 GBK 编码

**排查**:
```python
resp = requests.get(url)
print(resp.encoding)  # 应为 gbk 或 iso-8859-1
resp.encoding = 'gbk'
print(resp.text[:200])
```

### 问题: 代理导致请求失败

**排查**:
```bash
echo $HTTP_PROXY $HTTPS_PROXY $ALL_PROXY
```

**代码层处理**: `_no_proxy_get()` 显式传 `proxies={"http": None, "https": None}` 绕过代理。

### 问题: Mock 不生效 (测试中)

**常见错误**: patch 的路径不是模块级引用

```python
# ✅ 正确: patch company_analysis 模块内的引用
patch("research_mcp.tools.company_analysis._fetch_board_fallback", ...)

# ❌ 错误: patch 原始模块 (因为 company_analysis 已经 import 了局部引用)
patch("research_mcp.utils.fallback_sources.fetch_board_fallback", ...)
```

### 问题: 新增测试与旧测试冲突

**原因**: `test_mcp_returns_consistency.py::test_industry_ranking_empty_data` 会 patch `company_analysis.ak`，但该模块未直接 import `ak`（通过 `call_akshare` 间接调用）。

**解决**: 单独运行新测试 `tests/test_fallback_sources.py`，或修复旧测试的 mock 路径。

---

## 七、后续优化方向

1. **push2 请求重试**: 当前无重试，可加入 1-2 次退避重试
2. **新浪换手率补全**: 可通过 `Market_Center.getHQNodeData` 二级接口获取
3. **缓存落地**: 备源数据写入 `DataCache`，TTL=180s (已在 fetch_industry_ranking 中实现)
4. **监控指标**: 记录各数据源的成功/失败率，用于运维告警
