"""
规则引擎核心模块

设计原则:
- 声明式规则定义（条件+动作）
- 支持优先级排序
- 支持规则组合（AND/OR）
- 支持动态权重调整
- 所有规则返回统一结构: {"triggered": bool, "action": str, "params": dict, "reason": str}
"""

import json
from dataclasses import dataclass, field
from typing import Callable, Optional
from enum import Enum


class RulePriority(Enum):
    P0 = 0  # 最高，强制执行
    P1 = 1  # 高
    P2 = 2  # 中
    P3 = 3  # 低


@dataclass
class RuleResult:
    """规则执行结果"""
    triggered: bool
    action: str
    params: dict = field(default_factory=dict)
    reason: str = ""


@dataclass
class Rule:
    """单条规则定义"""
    id: str
    name: str
    condition: Callable[[dict], bool]
    action: str
    priority: RulePriority = RulePriority.P1
    params: dict = field(default_factory=dict)
    enabled: bool = True

    def evaluate(self, context: dict) -> RuleResult:
        """评估规则，返回结果"""
        if not self.enabled:
            return RuleResult(triggered=False, action="", reason="规则已禁用")

        try:
            triggered = self.condition(context)
        except Exception as e:
            return RuleResult(
                triggered=False,
                action="",
                reason=f"规则执行异常: {e}"
            )

        if triggered:
            return RuleResult(
                triggered=True,
                action=self.action,
                params=self.params,
                reason=f"规则[{self.id}] {self.name} 触发"
            )
        return RuleResult(triggered=False, action="", reason="")


class RuleEngine:
    """
    规则引擎

    用法:
        engine = RuleEngine()
        engine.add_rule(
            id="R001",
            name="库存预警",
            condition=lambda ctx: ctx.get("stock", 0) < ctx.get("threshold", 100),
            action="alert",
            priority=RulePriority.P1
        )
        results = engine.evaluate(context)
    """

    def __init__(self):
        self.rules: list[Rule] = []
        self._sorted = False

    def add_rule(self, id: str, name: str, condition: Callable, action: str,
                 priority: RulePriority = RulePriority.P1, params: dict = None,
                 enabled: bool = True):
        """添加规则"""
        rule = Rule(
            id=id,
            name=name,
            condition=condition,
            action=action,
            priority=priority,
            params=params or {},
            enabled=enabled
        )
        self.rules.append(rule)
        self._sorted = False

    def remove_rule(self, id: str):
        """移除规则"""
        self.rules = [r for r in self.rules if r.id != id]

    def disable_rule(self, id: str):
        """禁用规则"""
        for r in self.rules:
            if r.id == id:
                r.enabled = False

    def enable_rule(self, id: str):
        """启用规则"""
        for r in self.rules:
            if r.id == id:
                r.enabled = True

    def _ensure_sorted(self):
        if not self._sorted:
            self.rules.sort(key=lambda r: r.priority.value)
            self._sorted = True

    def evaluate(self, context: dict) -> list[RuleResult]:
        """
        评估所有规则，按优先级排序
        返回所有触发的规则结果
        """
        self._ensure_sorted()
        results = []
        for rule in self.rules:
            result = rule.evaluate(context)
            if result.triggered:
                results.append(result)
        return results

    def evaluate_first(self, context: dict) -> Optional[RuleResult]:
        """
        评估所有规则，返回第一个触发的（最高优先级）
        用于需要立即中断的场景
        """
        self._ensure_sorted()
        for rule in self.rules:
            result = rule.evaluate(context)
            if result.triggered:
                return result
        return None

    def stats(self) -> dict:
        """返回规则统计"""
        enabled = [r for r in self.rules if r.enabled]
        disabled = [r for r in self.rules if not r.enabled]
        priorities = {}
        for r in self.rules:
            p = r.priority.name
            priorities[p] = priorities.get(p, 0) + 1
        return {
            "total": len(self.rules),
            "enabled": len(enabled),
            "disabled": len(disabled),
            "by_priority": priorities
        }
