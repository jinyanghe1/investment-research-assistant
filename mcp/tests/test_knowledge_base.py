"""知识库管理工具测试"""
import json
import pytest


class TestFetchReportsList:
    def test_list_all(self, sample_index_json, monkeypatch):
        """列出全部研报"""
        monkeypatch.setattr(
            type(__import__("config", fromlist=["config"]).config),
            "index_json_path",
            property(lambda self: str(sample_index_json)),
        )

        from tools.knowledge_base import fetch_reports_list
        result = fetch_reports_list()
        assert result["total"] == 2
        assert len(result["reports"]) == 2

    def test_filter_category(self, sample_index_json, monkeypatch):
        """按分类筛选"""
        monkeypatch.setattr(
            type(__import__("config", fromlist=["config"]).config),
            "index_json_path",
            property(lambda self: str(sample_index_json)),
        )

        from tools.knowledge_base import fetch_reports_list
        result = fetch_reports_list(category="产业研究")
        assert result["total"] == 1
        assert result["reports"][0]["category"] == "产业研究"

    def test_empty_index(self, tmp_workspace, monkeypatch):
        """空知识库返回 total=0"""
        monkeypatch.setattr(
            type(__import__("config", fromlist=["config"]).config),
            "index_json_path",
            property(lambda self: str(tmp_workspace / "index.json")),
        )

        from tools.knowledge_base import fetch_reports_list
        result = fetch_reports_list()
        assert result["total"] == 0


class TestFetchReportsSearch:
    def test_search_by_title(self, sample_index_json, monkeypatch):
        """标题关键词搜索"""
        monkeypatch.setattr(
            type(__import__("config", fromlist=["config"]).config),
            "index_json_path",
            property(lambda self: str(sample_index_json)),
        )

        from tools.knowledge_base import fetch_reports_search
        result = fetch_reports_search("宏观")
        assert result["total"] >= 1
        assert any("宏观" in r["title"] for r in result["results"])

    def test_search_by_tag(self, sample_index_json, monkeypatch):
        """标签搜索"""
        monkeypatch.setattr(
            type(__import__("config", fromlist=["config"]).config),
            "index_json_path",
            property(lambda self: str(sample_index_json)),
        )

        from tools.knowledge_base import fetch_reports_search
        result = fetch_reports_search("半导体", search_fields="tags")
        assert result["total"] >= 1

    def test_search_no_results(self, sample_index_json, monkeypatch):
        """无匹配结果"""
        monkeypatch.setattr(
            type(__import__("config", fromlist=["config"]).config),
            "index_json_path",
            property(lambda self: str(sample_index_json)),
        )

        from tools.knowledge_base import fetch_reports_search
        result = fetch_reports_search("区块链量子计算")
        assert result["total"] == 0
        assert result["results"] == []

    def test_search_empty_query(self, sample_index_json, monkeypatch):
        """空查询返回零结果"""
        monkeypatch.setattr(
            type(__import__("config", fromlist=["config"]).config),
            "index_json_path",
            property(lambda self: str(sample_index_json)),
        )

        from tools.knowledge_base import fetch_reports_search
        result = fetch_reports_search("")
        assert result["total"] == 0

    def test_search_multi_keyword(self, sample_index_json, monkeypatch):
        """多关键词搜索提高相关性排序"""
        monkeypatch.setattr(
            type(__import__("config", fromlist=["config"]).config),
            "index_json_path",
            property(lambda self: str(sample_index_json)),
        )

        from tools.knowledge_base import fetch_reports_search
        result = fetch_reports_search("测试 宏观 GDP")
        assert result["total"] >= 1
