#!/usr/bin/env python3
"""
stock-open-api 集成测试 — 真实数据严格验证

遵循测试SOP:
  1. 绝对禁止Mock数据
  2. 每个测试有超时控制
  3. 验证 data_source != "mock"
  4. 验证数据合理范围

测试覆盖:
  - 腾讯行情API (qt.gtimg.cn) 实时行情
  - 东方财富公司信息 (stock-open-api eastmoney)
  - 同花顺公司信息 (stock-open-api jqka)
  - fetch_stock_realtime 集成测试 (tencent_qq优先)
  - fetch_company_financials 集成测试 (stock_open_api优先)
  - 批量行情测试
  - 深圳/上海/北交所覆盖

运行方式:
    cd /Users/hejinyang/投研助手
    python3 tests/test_stock_open_api.py
"""

import sys
import os
import signal
import time
from typing import Callable

# 确保项目路径正确
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'research_mcp'))

# ---------------------------------------------------------------------------
# 测试基础设施 (遵循SOP模板)
# ---------------------------------------------------------------------------
TIMEOUT_SECONDS = 30


class TestTimeoutError(Exception):
    pass


def with_timeout(seconds: int = TIMEOUT_SECONDS):
    """超时装饰器 — 每个测试必须设置超时"""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            def handler(signum, frame):
                raise TestTimeoutError(f"执行超过{seconds}秒")
            old_handler = signal.signal(signal.SIGALRM, handler)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
                signal.alarm(0)
                return result
            finally:
                signal.signal(signal.SIGALRM, old_handler)
        return wrapper
    return decorator


def check_real_data(result: dict, test_name: str) -> bool:
    """验证是否为真实数据 — 必须调用此函数验证"""
    if not isinstance(result, dict):
        raise AssertionError(f"{test_name}: 返回类型错误 {type(result)}")

    if "error" in result:
        raise AssertionError(f"{test_name}: 返回错误 - {result['error']}")

    data_source = str(result.get("data_source", "")).lower()

    if data_source == "mock":
        raise AssertionError(
            f"{test_name}: 返回MOCK数据！\n"
            f"警告: {result.get('warning', 'N/A')}\n"
            f"测试失败：必须使用真实数据！"
        )

    if data_source in ("", "unknown"):
        raise AssertionError(f"{test_name}: 数据源标记异常 '{data_source}'")

    return True


class TestSuite:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def run_test(self, name: str, test_func: Callable):
        print(f"\n{'='*60}")
        print(f"测试: {name}")
        print(f"{'='*60}")
        start = time.time()

        try:
            test_func()
            elapsed = time.time() - start
            print(f"\033[92m✓ 通过 ({elapsed:.1f}s)\033[0m")
            self.passed += 1
            return True
        except TestTimeoutError as e:
            print(f"\033[91m✗ 超时: {e}\033[0m")
            self.failed += 1
            self.errors.append(f"{name}: TIMEOUT - {e}")
            return False
        except AssertionError as e:
            print(f"\033[91m✗ 失败: {e}\033[0m")
            self.failed += 1
            self.errors.append(f"{name}: ASSERT - {e}")
            return False
        except Exception as e:
            print(f"\033[91m✗ 异常: {type(e).__name__}: {e}\033[0m")
            self.failed += 1
            self.errors.append(f"{name}: EXCEPTION - {type(e).__name__}: {e}")
            return False

    def print_summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"测试汇总")
        print(f"{'='*60}")
        print(f"总计: {total} | 通过: {self.passed} | 失败: {self.failed}")
        if total > 0:
            rate = self.passed / total * 100
            color = "\033[92m" if rate == 100 else "\033[91m"
            print(f"通过率: {color}{rate:.1f}%\033[0m")

        if self.errors:
            print(f"\n失败详情:")
            for err in self.errors:
                print(f"  ✗ {err}")

        return self.failed == 0


# ---------------------------------------------------------------------------
# 底层 API 测试
# ---------------------------------------------------------------------------

@with_timeout(15)
def test_tencent_realtime_sh():
    """腾讯行情API — 上海A股 (600519 贵州茅台)"""
    from research_mcp.utils.stock_open_api_source import fetch_realtime_tencent

    result = fetch_realtime_tencent("600519")
    assert result is not None, "腾讯行情返回None"
    assert result.get("data_source") == "tencent_qq", f"数据源异常: {result.get('data_source')}"
    assert result.get("data_source") != "mock", "返回mock数据！"

    # 价格范围验证 (茅台 500-3000元)
    price = result.get("现价")
    assert price is not None and 500 <= price <= 3000, f"茅台价格异常: {price}"

    # 名称验证
    assert "茅台" in result.get("名称", ""), f"名称异常: {result.get('名称')}"

    # 代码验证
    assert result.get("代码") == "600519", f"代码异常: {result.get('代码')}"

    # 涨跌幅范围验证
    change_pct = result.get("涨跌幅(%)")
    if change_pct is not None:
        assert -11 <= change_pct <= 11, f"涨跌幅异常: {change_pct}%"

    # 关键字段存在性
    for field in ["今开", "最高", "最低", "昨收", "成交量(手)", "市盈率"]:
        assert field in result, f"缺少字段: {field}"

    print(f"  价格: {price}, 涨跌: {change_pct}%, 来源: {result['data_source']}")


@with_timeout(15)
def test_tencent_realtime_sz():
    """腾讯行情API — 深圳A股 (000001 平安银行)"""
    from research_mcp.utils.stock_open_api_source import fetch_realtime_tencent

    result = fetch_realtime_tencent("000001")
    assert result is not None, "腾讯行情返回None"
    assert result.get("data_source") == "tencent_qq"

    price = result.get("现价")
    assert price is not None and 1 <= price <= 100, f"平安银行价格异常: {price}"
    assert result.get("代码") == "000001"

    print(f"  价格: {price}, 来源: {result['data_source']}")


@with_timeout(15)
def test_tencent_realtime_cyb():
    """腾讯行情API — 创业板 (300750 宁德时代)"""
    from research_mcp.utils.stock_open_api_source import fetch_realtime_tencent

    result = fetch_realtime_tencent("300750")
    assert result is not None, "腾讯行情返回None"
    assert result.get("data_source") == "tencent_qq"

    price = result.get("现价")
    assert price is not None and 50 <= price <= 800, f"宁德时代价格异常: {price}"

    print(f"  价格: {price}, 来源: {result['data_source']}")


@with_timeout(15)
def test_tencent_batch():
    """腾讯行情API — 批量查询"""
    from research_mcp.utils.stock_open_api_source import fetch_realtime_tencent_batch

    symbols = ["600519", "000001", "300750"]
    results = fetch_realtime_tencent_batch(symbols)

    assert isinstance(results, dict), f"返回类型错误: {type(results)}"
    assert len(results) >= 2, f"返回数量过少: {len(results)}"

    for sym in symbols:
        data = results.get(sym)
        if data is not None:
            assert data.get("现价") is not None and data["现价"] > 0, f"{sym} 价格异常"
            assert data.get("data_source") == "tencent_qq"

    print(f"  成功获取 {sum(1 for v in results.values() if v)} / {len(symbols)} 只股票")


@with_timeout(15)
def test_eastmoney_company_info():
    """东方财富公司信息API — 600519 贵州茅台"""
    from research_mcp.utils.stock_open_api_source import fetch_company_info_eastmoney

    result = fetch_company_info_eastmoney("600519")
    assert result is not None, "东方财富公司信息返回None"
    assert result.get("data_source") == "stock_open_api_eastmoney"
    assert result.get("data_source") != "mock", "返回mock数据！"

    # 公司名称验证
    assert "茅台" in result.get("公司名称", ""), f"公司名称异常: {result.get('公司名称')}"

    # 关键字段存在性
    for field in ["A股代码", "A股简称", "所属行业", "董事长", "成立日期", "上市日期"]:
        assert field in result and result[field], f"缺少关键字段: {field}"

    assert result["A股代码"] == "600519"

    print(f"  公司: {result['公司名称']}, 行业: {result.get('所属行业')}")


@with_timeout(15)
def test_jqka_company_info():
    """同花顺公司信息API — 600519 贵州茅台"""
    from research_mcp.utils.stock_open_api_source import fetch_company_info_jqka

    result = fetch_company_info_jqka("600519")
    assert result is not None, "同花顺公司信息返回None"
    assert result.get("data_source") == "stock_open_api_jqka"
    assert result.get("data_source") != "mock", "返回mock数据！"

    assert "茅台" in result.get("公司名称", ""), f"公司名称异常: {result.get('公司名称')}"

    for field in ["A股代码", "A股简称", "所属行业", "董事长"]:
        assert field in result and result[field], f"缺少关键字段: {field}"

    print(f"  公司: {result['公司名称']}, 行业: {result.get('所属行业')}")


@with_timeout(15)
def test_company_info_unified():
    """统一公司信息入口 — 东方财富优先, 同花顺备源"""
    from research_mcp.utils.stock_open_api_source import fetch_company_info

    result = fetch_company_info("000001")
    assert result is not None, "统一公司信息返回None"
    assert result.get("data_source") in ("stock_open_api_eastmoney", "stock_open_api_jqka")
    assert result.get("data_source") != "mock"
    assert result.get("公司名称"), "公司名称为空"

    print(f"  公司: {result['公司名称']}, 来源: {result['data_source']}")


# ---------------------------------------------------------------------------
# 集成测试 (MCP工具层)
# ---------------------------------------------------------------------------

@with_timeout(20)
def test_fetch_stock_realtime_integration():
    """集成测试: fetch_stock_realtime 优先使用tencent_qq"""
    from research_mcp.tools.market_data import fetch_stock_realtime

    result = fetch_stock_realtime("600519", "A")
    check_real_data(result, "fetch_stock_realtime")

    # 验证优先使用tencent_qq
    assert result.get("data_source") == "tencent_qq", \
        f"应优先使用tencent_qq，实际: {result.get('data_source')}"

    price = result.get("现价")
    assert price is not None and 500 <= price <= 3000, f"茅台价格异常: {price}"
    assert result.get("market") == "A"

    print(f"  价格: {price}, 来源: {result['data_source']}")


@with_timeout(20)
def test_fetch_stock_realtime_sz_integration():
    """集成测试: fetch_stock_realtime 深圳A股"""
    from research_mcp.tools.market_data import fetch_stock_realtime

    result = fetch_stock_realtime("000858", "A")
    check_real_data(result, "fetch_stock_realtime SZ")

    assert result.get("data_source") == "tencent_qq"
    price = result.get("现价")
    assert price is not None and 30 <= price <= 500, f"五粮液价格异常: {price}"

    print(f"  价格: {price}, 来源: {result['data_source']}")


@with_timeout(20)
def test_fetch_company_financials_integration():
    """集成测试: fetch_company_financials 优先使用stock_open_api"""
    from research_mcp.tools.company_analysis import fetch_company_financials

    result = fetch_company_financials("600519", "A", "summary")

    assert "error" not in result, f"返回错误: {result.get('error')}"
    assert result.get("data_source") in ("stock_open_api_eastmoney", "stock_open_api_jqka"), \
        f"应优先使用stock_open_api，实际: {result.get('data_source')}"

    data = result.get("data", [])
    assert len(data) > 0, "数据为空"
    assert "茅台" in data[0].get("公司名称", ""), f"公司名称异常: {data[0].get('公司名称')}"

    print(f"  公司: {result.get('company')}, 来源: {result.get('data_source')}")


@with_timeout(20)
def test_fetch_company_financials_sz():
    """集成测试: fetch_company_financials 深圳A股"""
    from research_mcp.tools.company_analysis import fetch_company_financials

    result = fetch_company_financials("000001", "A", "summary")

    assert "error" not in result
    assert result.get("data_source") in ("stock_open_api_eastmoney", "stock_open_api_jqka")

    data = result.get("data", [])
    assert len(data) > 0, "数据为空"

    print(f"  公司: {result.get('company')}, 来源: {result.get('data_source')}")


# ---------------------------------------------------------------------------
# 边界条件测试
# ---------------------------------------------------------------------------

@with_timeout(15)
def test_tencent_invalid_symbol():
    """腾讯行情: 无效股票代码应返回None"""
    from research_mcp.utils.stock_open_api_source import fetch_realtime_tencent

    result = fetch_realtime_tencent("999999")
    # 无效代码应返回None或价格为0
    if result is not None:
        price = result.get("现价")
        assert price is None or price <= 0, f"无效代码返回非零价格: {price}"

    print(f"  无效代码正确处理 (返回: {'None' if result is None else '价格<=0'})")


@with_timeout(15)
def test_price_logic_consistency():
    """价格逻辑一致性: 最低 <= 现价 <= 最高"""
    from research_mcp.utils.stock_open_api_source import fetch_realtime_tencent

    result = fetch_realtime_tencent("600519")
    assert result is not None

    price = result.get("现价")
    high = result.get("最高")
    low = result.get("最低")

    if price and high and low:
        assert low <= price <= high * 1.001, \
            f"价格逻辑错误: 最低{low} <= 现价{price} <= 最高{high}"
        assert low <= high, f"最低{low} > 最高{high}"

    print(f"  价格逻辑一致: {low} <= {price} <= {high}")


# ---------------------------------------------------------------------------
# 主程序
# ---------------------------------------------------------------------------

def main():
    suite = TestSuite()

    print("\n" + "="*60)
    print("stock-open-api 集成测试 (真实数据, 禁止mock)")
    print("="*60)

    # 底层API测试
    print("\n--- 底层 API 测试 ---")
    suite.run_test("腾讯行情: 上海A股(600519)", test_tencent_realtime_sh)
    suite.run_test("腾讯行情: 深圳A股(000001)", test_tencent_realtime_sz)
    suite.run_test("腾讯行情: 创业板(300750)", test_tencent_realtime_cyb)
    suite.run_test("腾讯行情: 批量查询", test_tencent_batch)
    suite.run_test("东方财富: 公司信息(600519)", test_eastmoney_company_info)
    suite.run_test("同花顺: 公司信息(600519)", test_jqka_company_info)
    suite.run_test("统一入口: 公司信息(000001)", test_company_info_unified)

    # 集成测试
    print("\n--- MCP工具集成测试 ---")
    suite.run_test("fetch_stock_realtime: 上海A股", test_fetch_stock_realtime_integration)
    suite.run_test("fetch_stock_realtime: 深圳A股", test_fetch_stock_realtime_sz_integration)
    suite.run_test("fetch_company_financials: 上海A股", test_fetch_company_financials_integration)
    suite.run_test("fetch_company_financials: 深圳A股", test_fetch_company_financials_sz)

    # 边界条件
    print("\n--- 边界条件测试 ---")
    suite.run_test("腾讯行情: 无效代码", test_tencent_invalid_symbol)
    suite.run_test("价格逻辑一致性", test_price_logic_consistency)

    all_pass = suite.print_summary()
    return all_pass


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
