#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_fallback_sources.py — fallback_sources.py 单元测试

覆盖场景:
  1. push2 API 正常返回
  2. push2 API 返回空数据 → 降级到新浪
  3. push2 API 网络异常 → 降级到新浪
  4. 新浪 API 正常返回 (industry / concept)
  5. 所有备源都失败 → 返回 None
  6. _fetch_board_data 集成测试: akshare失败 → 备源接管
  7. fetch_industry_ranking 端到端: 全路径 fallback
"""

import math
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# push2 eastmoney 测试
# ---------------------------------------------------------------------------
class TestFetchBoardEastmoneyPush2:
    """东方财富 push2 HTTP 备源测试"""

    def _make_push2_response(self, items):
        """构造 push2 API 标准返回"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "data": {
                "total": len(items),
                "diff": items,
            }
        }
        return mock_resp

    def test_industry_success(self):
        """push2 行业板块正常返回"""
        items = [
            {"f14": "金融信息服务", "f3": 4.9, "f8": 5.36, "f6": 2056517573.0,
             "f20": 37171426000, "f128": "翠微股份", "f136": 10.03,
             "f104": 3, "f105": 0},
            {"f14": "激光设备", "f3": 3.52, "f8": 4.97, "f6": 13365896790.0,
             "f20": 254718742000, "f128": "锐科激光", "f136": 10.84,
             "f104": 8, "f105": 2},
        ]
        mock_resp = self._make_push2_response(items)

        with patch("utils.fallback_sources.requests") as mock_requests:
            mock_requests.get.return_value = mock_resp
            from utils.fallback_sources import fetch_board_eastmoney_push2
            df = fetch_board_eastmoney_push2("industry", limit=10)

        assert df is not None
        assert len(df) == 2
        assert "名称" in df.columns
        assert "涨跌幅" in df.columns
        assert "换手率" in df.columns
        assert "领涨股票" in df.columns
        assert df.iloc[0]["名称"] == "金融信息服务"
        assert df.iloc[0]["涨跌幅"] == 4.9

    def test_concept_success(self):
        """push2 概念板块正常返回"""
        items = [
            {"f14": "CPO概念", "f3": 3.04, "f8": 5.08, "f6": 1e10,
             "f20": 3e12, "f128": "德科立", "f136": 10.0,
             "f104": 5, "f105": 1},
        ]
        mock_resp = self._make_push2_response(items)

        with patch("utils.fallback_sources.requests") as mock_requests:
            mock_requests.get.return_value = mock_resp
            from utils.fallback_sources import fetch_board_eastmoney_push2
            df = fetch_board_eastmoney_push2("concept", limit=10)

        assert df is not None
        assert len(df) == 1
        assert df.iloc[0]["名称"] == "CPO概念"

    def test_empty_diff(self):
        """push2 返回空 diff → None"""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"data": {"total": 0, "diff": []}}

        with patch("utils.fallback_sources.requests") as mock_requests:
            mock_requests.get.return_value = mock_resp
            from utils.fallback_sources import fetch_board_eastmoney_push2
            df = fetch_board_eastmoney_push2("industry")

        assert df is None

    def test_network_error(self):
        """push2 网络异常 → None"""
        with patch("utils.fallback_sources.requests") as mock_requests:
            mock_requests.get.side_effect = Exception("Connection refused")
            from utils.fallback_sources import fetch_board_eastmoney_push2
            df = fetch_board_eastmoney_push2("industry")

        assert df is None

    def test_invalid_board_type(self):
        """不支持的板块类型 → None"""
        from utils.fallback_sources import fetch_board_eastmoney_push2
        df = fetch_board_eastmoney_push2("invalid_type")
        assert df is None


# ---------------------------------------------------------------------------
# 新浪财经测试
# ---------------------------------------------------------------------------
class TestFetchBoardSina:
    """新浪财经备源测试"""

    _SINA_INDUSTRY_JS = (
        'var S_Finance_bankuai_industry = {'
        '"hangye_ZA01":"hangye_ZA01,农业,15,9.47,-0.41,-4.14,492417875,3939893044,,0,,,",'
        '"hangye_ZA02":"hangye_ZA02,林业,3,9.72,-0.52,-5.11,365723831,4344533197,,0,,,"'
        '}'
    )

    _SINA_CONCEPT_JS = (
        'var S_Finance_bankuai_concept = {'
        '"gainian_001":"gainian_001,锂电池,20,12.5,0.35,2.88,100000000,500000000,,0,,,",'
        '"gainian_002":"gainian_002,光伏,15,8.9,-0.15,-1.67,200000000,800000000,,0,,,"'
        '}'
    )

    def test_industry_success(self):
        """新浪行业板块解析成功"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.text = self._SINA_INDUSTRY_JS

        with patch("utils.fallback_sources.requests") as mock_requests:
            mock_requests.get.return_value = mock_resp
            from utils.fallback_sources import fetch_board_sina
            df = fetch_board_sina("industry", limit=10)

        assert df is not None
        assert len(df) == 2
        assert "名称" in df.columns
        assert "涨跌幅" in df.columns
        names = df["名称"].tolist()
        assert "农业" in names
        assert "林业" in names

    def test_concept_success(self):
        """新浪概念板块解析成功"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.text = self._SINA_CONCEPT_JS

        with patch("utils.fallback_sources.requests") as mock_requests:
            mock_requests.get.return_value = mock_resp
            from utils.fallback_sources import fetch_board_sina
            df = fetch_board_sina("concept", limit=10)

        assert df is not None
        assert len(df) == 2
        names = df["名称"].tolist()
        assert "锂电池" in names

    def test_network_error(self):
        """新浪网络异常 → None"""
        with patch("utils.fallback_sources.requests") as mock_requests:
            mock_requests.get.side_effect = Exception("Timeout")
            from utils.fallback_sources import fetch_board_sina
            df = fetch_board_sina("industry")

        assert df is None

    def test_malformed_response(self):
        """新浪返回格式异常 → None"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.text = "<html>error page</html>"

        with patch("utils.fallback_sources.requests") as mock_requests:
            mock_requests.get.return_value = mock_resp
            from utils.fallback_sources import fetch_board_sina
            df = fetch_board_sina("industry")

        assert df is None


# ---------------------------------------------------------------------------
# 统一入口 fetch_board_fallback 测试
# ---------------------------------------------------------------------------
class TestFetchBoardFallback:
    """fetch_board_fallback 多源降级测试"""

    def test_push2_success_no_sina_call(self):
        """push2 成功时不应调用新浪"""
        push2_df = pd.DataFrame({
            "名称": ["板块A", "板块B"],
            "涨跌幅": [1.5, -0.3],
        })

        with patch("utils.fallback_sources.fetch_board_eastmoney_push2",
                    return_value=push2_df) as mock_push2, \
             patch("utils.fallback_sources.fetch_board_sina") as mock_sina:
            from utils.fallback_sources import fetch_board_fallback
            df = fetch_board_fallback("industry")

        assert df is not None
        assert len(df) == 2
        mock_push2.assert_called_once()
        mock_sina.assert_not_called()

    def test_push2_fail_fallback_to_sina(self):
        """push2 失败 → 降级到新浪"""
        sina_df = pd.DataFrame({
            "名称": ["新浪板块A"],
            "涨跌幅": [2.0],
        })

        with patch("utils.fallback_sources.fetch_board_eastmoney_push2",
                    return_value=None) as mock_push2, \
             patch("utils.fallback_sources.fetch_board_sina",
                    return_value=sina_df) as mock_sina:
            from utils.fallback_sources import fetch_board_fallback
            df = fetch_board_fallback("industry")

        assert df is not None
        assert len(df) == 1
        assert df.iloc[0]["名称"] == "新浪板块A"
        mock_push2.assert_called_once()
        mock_sina.assert_called_once()

    def test_all_sources_fail(self):
        """所有备源都失败 → 返回 None"""
        with patch("utils.fallback_sources.fetch_board_eastmoney_push2",
                    return_value=None), \
             patch("utils.fallback_sources.fetch_board_sina",
                    return_value=None):
            from utils.fallback_sources import fetch_board_fallback
            df = fetch_board_fallback("industry")

        assert df is None

    def test_push2_empty_df_fallback_to_sina(self):
        """push2 返回空 DataFrame → 降级到新浪"""
        sina_df = pd.DataFrame({
            "名称": ["新浪兜底"],
            "涨跌幅": [0.5],
        })

        with patch("utils.fallback_sources.fetch_board_eastmoney_push2",
                    return_value=pd.DataFrame()), \
             patch("utils.fallback_sources.fetch_board_sina",
                    return_value=sina_df):
            from utils.fallback_sources import fetch_board_fallback
            df = fetch_board_fallback("industry")

        assert df is not None
        assert df.iloc[0]["名称"] == "新浪兜底"


# ---------------------------------------------------------------------------
# _fetch_board_data 集成: akshare 全部失败 → 备源接管
# ---------------------------------------------------------------------------
class TestFetchBoardDataIntegration:
    """_fetch_board_data 三级 fallback 集成测试"""

    def test_akshare_fail_push2_success(self):
        """akshare 全部异常 → push2 备源接管"""
        push2_df = pd.DataFrame({
            "名称": ["push2行业A", "push2行业B"],
            "涨跌幅": [3.1, 1.2],
            "换手率": [5.0, 3.0],
            "成交额": [1e9, 2e9],
            "领涨股票": ["股票X", "股票Y"],
            "领涨股票-涨跌幅": [8.0, 6.0],
        })
        push2_df.attrs["_fallback_source"] = "eastmoney_push2"

        def fail_akshare(*a, **kw):
            raise Exception("akshare fail")

        with patch("research_mcp.tools.company_analysis.call_akshare",
                    side_effect=fail_akshare), \
             patch("research_mcp.tools.company_analysis._fetch_board_fallback",
                    return_value=push2_df):
            from research_mcp.tools.company_analysis import _fetch_board_data
            df = _fetch_board_data("industry")

        assert df is not None
        assert len(df) == 2
        assert df.iloc[0]["名称"] == "push2行业A"

    def test_akshare_success_no_fallback(self):
        """akshare 正常返回 → 不触发备源"""
        akshare_df = pd.DataFrame({
            "板块名称": ["akshare板块"],
            "涨跌幅": [2.0],
        })

        call_count = {"n": 0}

        def mock_call_akshare(func_name, *a, **kw):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return akshare_df
            return pd.DataFrame()

        with patch("research_mcp.tools.company_analysis.call_akshare",
                    side_effect=mock_call_akshare), \
             patch("research_mcp.tools.company_analysis._fetch_board_fallback") as mock_fb:
            from research_mcp.tools.company_analysis import _fetch_board_data
            df = _fetch_board_data("industry")

        assert df is not None
        mock_fb.assert_not_called()


# ---------------------------------------------------------------------------
# fetch_industry_ranking 端到端测试
# ---------------------------------------------------------------------------
class TestFetchIndustryRankingFallback:
    """fetch_industry_ranking 全路径 fallback 端到端测试"""

    def test_fallback_returns_valid_rankings(self):
        """akshare 失败但 push2 成功时，返回结构完整的 rankings"""
        push2_df = pd.DataFrame({
            "名称": ["半导体", "新能源", "AI算力"],
            "涨跌幅": [5.2, 3.1, 2.8],
            "换手率": [8.0, 6.5, 5.3],
            "成交额": [5e9, 3e9, 2e9],
            "领涨股票": ["韦尔股份", "宁德时代", "浪潮信息"],
            "领涨股票-涨跌幅": [10.0, 7.5, 6.2],
        })
        push2_df.attrs["_fallback_source"] = "eastmoney_push2"

        with patch("research_mcp.tools.company_analysis.call_akshare",
                    side_effect=Exception("fail")), \
             patch("research_mcp.tools.company_analysis._fetch_board_fallback",
                    return_value=push2_df):
            from research_mcp.tools.company_analysis import fetch_industry_ranking
            result = fetch_industry_ranking("industry", limit=3)

        assert isinstance(result, dict)
        assert result["data_source"] == "eastmoney_push2"
        assert result["count"] == 3
        assert len(result["rankings"]) == 3

        first = result["rankings"][0]
        assert first["name"] == "半导体"
        assert first["change_pct"] == 5.2
        assert first["turnover"] == 8.0
        assert isinstance(first["amount_yi"], float)
        assert first["leading_stock"] == "韦尔股份"

    def test_all_fail_returns_mock(self):
        """所有数据源全部失败时返回 mock 数据"""
        with patch("research_mcp.tools.company_analysis.call_akshare",
                    side_effect=Exception("fail")), \
             patch("research_mcp.tools.company_analysis._fetch_board_fallback",
                    return_value=None):
            from research_mcp.tools.company_analysis import fetch_industry_ranking
            result = fetch_industry_ranking("industry", limit=5)

        assert isinstance(result, dict)
        assert result["data_source"] == "mock"
        assert "warning" in result
        assert isinstance(result["rankings"], list)

    def test_data_source_field_accuracy(self):
        """data_source 字段准确反映实际使用的数据源"""
        akshare_df = pd.DataFrame({
            "板块名称": ["akshare行业"],
            "涨跌幅": [1.0],
            "成交额": [1e9],
        })

        call_count = {"n": 0}
        def mock_call(func_name, *a, **kw):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return akshare_df
            return pd.DataFrame()

        with patch("research_mcp.tools.company_analysis.call_akshare",
                    side_effect=mock_call):
            from research_mcp.tools.company_analysis import fetch_industry_ranking
            result = fetch_industry_ranking("industry", limit=5)

        assert result["data_source"] == "akshare"
