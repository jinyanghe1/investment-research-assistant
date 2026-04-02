"""
投研MCP Server 测试配置
提供通用 fixtures：mock akshare/yfinance、临时目录、测试config等
"""
import pytest
import sys
import os
import json

# 确保 mcp/ 在 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def tmp_workspace(tmp_path):
    """创建临时工作区，用于测试研报生成和知识库操作"""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    index_json = tmp_path / "index.json"
    index_json.write_text(json.dumps({"reports": [], "lastUpdated": ""}, ensure_ascii=False))
    return tmp_path


@pytest.fixture
def sample_index_json(tmp_path):
    """预填充的 index.json fixture"""
    data = {
        "reports": [
            {
                "id": "test-report-1",
                "title": "测试宏观研报",
                "author": "测试",
                "date": "2026-01-01",
                "category": "宏观研究",
                "tags": ["GDP", "CPI", "宏观经济"],
                "summary": "这是一篇测试宏观研报的摘要内容",
                "path": "reports/test-1.html"
            },
            {
                "id": "test-report-2",
                "title": "测试产业研报半导体",
                "author": "测试",
                "date": "2026-02-01",
                "category": "产业研究",
                "tags": ["半导体", "国产替代"],
                "summary": "半导体产业链分析",
                "path": "reports/test-2.html"
            }
        ],
        "lastUpdated": "2026-03-01T00:00:00Z"
    }
    index_file = tmp_path / "index.json"
    index_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return index_file


@pytest.fixture
def mock_akshare(monkeypatch):
    """Mock akshare 模块，避免真实网络调用"""
    import pandas as pd

    class MockAkshare:
        def __getattr__(self, name):
            def mock_func(*args, **kwargs):
                return pd.DataFrame()
            return mock_func

    mock = MockAkshare()
    monkeypatch.setattr("tools.market_data.ak", mock, raising=False)
    monkeypatch.setattr("tools.macro_data.ak", mock, raising=False)
    monkeypatch.setattr("tools.company_analysis.ak", mock, raising=False)
    return mock


@pytest.fixture
def cache(tmp_path):
    """使用临时目录的缓存实例"""
    from utils.cache import DataCache
    return DataCache(cache_dir=str(tmp_path / "cache"))
