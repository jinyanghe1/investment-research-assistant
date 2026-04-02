"""DataCache 缓存单元测试"""
import time
from utils.cache import DataCache


class TestDataCache:
    """DataCache 核心功能测试"""

    def test_set_and_get(self, cache):
        """写入并读取缓存数据"""
        cache.set("stock:000001", {"price": 10.5, "name": "平安银行"})
        result = cache.get("stock:000001", ttl_seconds=60)
        assert result is not None
        assert result["price"] == 10.5
        assert result["name"] == "平安银行"

    def test_ttl_expiry(self, cache):
        """TTL 过期后返回 None"""
        cache.set("temp_key", {"val": 42})
        # 使用极短TTL，sleep后应过期
        time.sleep(0.1)
        result = cache.get("temp_key", ttl_seconds=0)
        assert result is None

    def test_clear_single(self, cache):
        """清除单个 key"""
        cache.set("key_a", "value_a")
        cache.set("key_b", "value_b")
        assert cache.clear("key_a") is True
        assert cache.get("key_a", ttl_seconds=60) is None
        assert cache.get("key_b", ttl_seconds=60) == "value_b"

    def test_clear_nonexistent(self, cache):
        """清除不存在的 key 返回 False"""
        assert cache.clear("nonexistent") is False

    def test_clear_all(self, cache):
        """清除全部缓存"""
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.set("k3", "v3")
        count = cache.clear_all()
        assert count == 3
        assert cache.get("k1", ttl_seconds=60) is None
        assert cache.get("k2", ttl_seconds=60) is None

    def test_nonexistent_key(self, cache):
        """读取不存在的 key 返回 None"""
        result = cache.get("this_key_does_not_exist", ttl_seconds=60)
        assert result is None

    def test_cache_data_types(self, cache):
        """支持 dict、list、嵌套数据"""
        # dict
        cache.set("type_dict", {"a": 1, "b": "hello"})
        assert cache.get("type_dict", ttl_seconds=60) == {"a": 1, "b": "hello"}

        # list
        cache.set("type_list", [1, 2, 3, "four"])
        assert cache.get("type_list", ttl_seconds=60) == [1, 2, 3, "four"]

        # 嵌套
        nested = {"level1": {"level2": [1, {"level3": True}]}}
        cache.set("type_nested", nested)
        assert cache.get("type_nested", ttl_seconds=60) == nested

    def test_stats(self, cache):
        """缓存统计信息"""
        cache.set("s1", "data")
        cache.set("s2", "data")
        stats = cache.stats()
        assert stats["file_count"] == 2
        assert stats["total_size_kb"] >= 0
        assert "cache_dir" in stats
