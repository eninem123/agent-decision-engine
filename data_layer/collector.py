"""
数据采集模块

支持:
- API数据源
- 数据库数据源
- 文件数据源
- 自定义数据源（通过插件扩展）
"""

from dataclasses import dataclass
from typing import Callable, Optional
from datetime import datetime


@dataclass
class DataSource:
    """数据源配置"""
    name: str
    source_type: str  # "api" / "db" / "file" / "custom"
    fetch_fn: Optional[Callable] = None
    config: dict = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}


class DataCollector:
    """
    数据采集器

    用法:
        collector = DataCollector()
        collector.add_source(
            name="market",
            source_type="api",
            fetch_fn=lambda: requests.get(url).json()
        )
        data = collector.fetch("market")
    """

    def __init__(self):
        self._sources: dict[str, DataSource] = {}
        self._cache: dict[str, dict] = {}
        self._cache_ttl = {}  # 数据源→过期时间
        self._default_ttl = 60  # 默认缓存60秒

    def add_source(self, name: str, source_type: str, fetch_fn: Callable,
                   config: dict = None, cache_ttl: int = None):
        """注册数据源"""
        self._sources[name] = DataSource(
            name=name,
            source_type=source_type,
            fetch_fn=fetch_fn,
            config=config or {}
        )
        if cache_ttl is not None:
            self._cache_ttl[name] = cache_ttl

    def remove_source(self, name: str):
        """移除数据源"""
        self._sources.pop(name, None)
        self._cache.pop(name, None)

    def fetch(self, name: str, use_cache: bool = True) -> dict:
        """
        从数据源获取数据

        返回:
            {"source": name, "data": ..., "timestamp": "...", "status": "ok"|"error"}
        """
        source = self._sources.get(name)
        if not source:
            return {
                "source": name,
                "data": None,
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": f"数据源 '{name}' 不存在"
            }

        # 检查缓存
        if use_cache and name in self._cache:
            ttl = self._cache_ttl.get(name, self._default_ttl)
            cached = self._cache[name]
            if (datetime.now() - cached["_cached_at"]).seconds < ttl:
                return {
                    "source": name,
                    "data": cached["data"],
                    "timestamp": cached["timestamp"],
                    "status": "ok",
                    "cached": True
                }

        # 实际获取
        try:
            data = source.fetch_fn()
            result = {
                "source": name,
                "data": data,
                "timestamp": datetime.now().isoformat(),
                "status": "ok"
            }
            # 写入缓存
            self._cache[name] = {
                "data": data,
                "timestamp": result["timestamp"],
                "_cached_at": datetime.now()
            }
            return result
        except Exception as e:
            return {
                "source": name,
                "data": None,
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e)
            }

    def fetch_all(self) -> dict:
        """获取所有数据源"""
        results = {}
        for name in self._sources:
            results[name] = self.fetch(name)
        return results
