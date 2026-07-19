"""
数据管道模块

支持:
- 数据清洗（去重/补全/格式化）
- 数据转换（映射/聚合/计算）
- 数据过滤（条件筛选）
"""

from typing import Callable, Optional
from dataclasses import dataclass


@dataclass
class PipelineStep:
    """管道步骤"""
    name: str
    fn: Callable[[dict], dict]
    enabled: bool = True


class Pipeline:
    """
    数据处理管道

    用法:
        pipeline = Pipeline()
        pipeline.add_step("clean", lambda d: {k: v for k, v in d.items() if v is not None})
        pipeline.add_step("transform", lambda d: {**d, "total": d.get("price", 0) * d.get("qty", 0)})

        result = pipeline.process({"price": 10, "qty": 5, "name": "item1"})
    """

    def __init__(self):
        self._steps: list[PipelineStep] = []

    def add_step(self, name: str, fn: Callable, enabled: bool = True):
        """添加管道步骤"""
        self._steps.append(PipelineStep(name=name, fn=fn, enabled=enabled))

    def remove_step(self, name: str):
        """移除步骤"""
        self._steps = [s for s in self._steps if s.name != name]

    def disable_step(self, name: str):
        """禁用步骤"""
        for s in self._steps:
            if s.name == name:
                s.enabled = False

    def process(self, data: dict) -> dict:
        """依次执行所有步骤"""
        result = data.copy()
        for step in self._steps:
            if not step.enabled:
                continue
            try:
                result = step.fn(result)
            except Exception as e:
                raise RuntimeError(f"管道步骤 '{step.name}' 执行失败: {e}") from e
        return result

    def process_batch(self, items: list[dict]) -> list[dict]:
        """批量处理"""
        return [self.process(item) for item in items]
