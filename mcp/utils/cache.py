"""
数据缓存工具 - 基于本地JSON文件的轻量级缓存系统

支持 TTL（过期时间）、线程安全、自动清理。
缓存文件存储在 mcp/data/cache/ 目录下。
"""

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Optional


# 预设 TTL 常量（秒）
TTL_MARKET = 300       # 行情数据：5分钟
TTL_MACRO = 86400      # 宏观数据：24小时
TTL_COMPANY = 3600     # 公司数据：1小时
TTL_DEFAULT = 1800     # 默认：30分钟


class DataCache:
    """基于本地JSON文件的线程安全缓存系统"""

    def __init__(self, cache_dir: Optional[str] = None):
        """
        初始化缓存

        Args:
            cache_dir: 缓存文件存储目录，默认为 mcp/data/cache/
        """
        if cache_dir:
            self._cache_dir = Path(cache_dir)
        else:
            # 基于当前文件位置定位到 mcp/data/cache/
            self._cache_dir = Path(__file__).parent.parent / "data" / "cache"

        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _key_to_path(self, key: str) -> Path:
        """将缓存key哈希为文件路径"""
        hashed = hashlib.md5(key.encode("utf-8")).hexdigest()
        return self._cache_dir / f"{hashed}.json"

    def get(self, key: str, ttl_seconds: int = TTL_DEFAULT) -> Optional[Any]:
        """
        获取缓存数据

        Args:
            key: 缓存键
            ttl_seconds: 过期时间（秒），超过则返回 None

        Returns:
            缓存的数据，若不存在或已过期则返回 None
        """
        with self._lock:
            path = self._key_to_path(key)
            if not path.exists():
                return None

            try:
                with open(path, "r", encoding="utf-8") as f:
                    entry = json.load(f)

                cached_time = entry.get("timestamp", 0)
                if time.time() - cached_time > ttl_seconds:
                    # 已过期，删除缓存文件
                    path.unlink(missing_ok=True)
                    return None

                return entry.get("data")
            except (json.JSONDecodeError, KeyError, OSError):
                # 缓存文件损坏，删除
                path.unlink(missing_ok=True)
                return None

    def set(self, key: str, data: Any) -> None:
        """
        写入缓存数据

        Args:
            key: 缓存键
            data: 要缓存的数据（必须可 JSON 序列化）
        """
        with self._lock:
            path = self._key_to_path(key)
            entry = {
                "key": key,
                "timestamp": time.time(),
                "data": data,
            }
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(entry, f, ensure_ascii=False, indent=2)
            except OSError:
                # 静默处理写入失败，缓存不应影响主流程
                pass

    def clear(self, key: str) -> bool:
        """
        清除指定key的缓存

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        with self._lock:
            path = self._key_to_path(key)
            if path.exists():
                path.unlink(missing_ok=True)
                return True
            return False

    def clear_all(self) -> int:
        """
        清除所有缓存文件

        Returns:
            删除的文件数量
        """
        with self._lock:
            count = 0
            for f in self._cache_dir.glob("*.json"):
                try:
                    f.unlink()
                    count += 1
                except OSError:
                    pass
            return count

    def stats(self) -> dict:
        """
        获取缓存统计信息

        Returns:
            包含文件数量和总大小的字典
        """
        with self._lock:
            files = list(self._cache_dir.glob("*.json"))
            total_size = sum(f.stat().st_size for f in files if f.exists())
            return {
                "cache_dir": str(self._cache_dir),
                "file_count": len(files),
                "total_size_kb": round(total_size / 1024, 2),
            }


# 全局单例缓存实例
_default_cache: Optional[DataCache] = None
_instance_lock = threading.Lock()


def get_cache() -> DataCache:
    """获取全局缓存单例"""
    global _default_cache
    if _default_cache is None:
        with _instance_lock:
            if _default_cache is None:
                _default_cache = DataCache()
    return _default_cache
