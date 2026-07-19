"""
Regime判断模块

从量化交易的市场环境判断抽象而来，可用于任何需要"当前处于什么状态"的场景。

支持:
- 多维度评估（宏观/风险/情绪/趋势）
- 状态机管理（状态切换带冷却期）
- 状态→策略映射
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from typing import Optional


class Regime(Enum):
    """系统状态"""
    CALM = "calm"           # 平稳
    VOLATILE = "volatile"   # 波动
    CRISIS = "crisis"       # 危机
    RECOVERY = "recovery"   # 恢复


@dataclass
class RegimeVerdict:
    """状态判定结果"""
    regime: Regime
    confidence: float  # 0-1
    dimensions: dict   # 各维度评分
    recommended_action: str
    max_position_pct: float  # 建议最大仓位比例
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class RegimeJudge:
    """
    状态判断器

    用法:
        judge = RegimeJudge()
        judge.set_dimension_weight("risk", 0.4)
        judge.set_dimension_weight("sentiment", 0.3)
        judge.set_dimension_weight("trend", 0.3)

        verdict = judge.evaluate({
            "risk": 0.7,       # 0-1, 越高越危险
            "sentiment": 0.3,  # 0-1, 越高越乐观
            "trend": 0.6       # 0-1, 越高越强
        })
    """

    def __init__(self):
        self._weights = {}  # 维度权重
        self._current_regime = Regime.CALM
        self._last_switch = None
        self._cooldown = timedelta(minutes=30)  # 状态切换冷却期
        self._regime_rules = {}  # 状态→策略映射

    def set_dimension_weight(self, dimension: str, weight: float):
        """设置维度权重"""
        self._weights[dimension] = weight

    def set_regime_rule(self, regime: Regime, action: str, max_position: float):
        """设置状态→策略映射"""
        self._regime_rules[regime] = {
            "action": action,
            "max_position": max_position
        }

    def _normalize_weights(self) -> dict:
        """归一化权重"""
        total = sum(self._weights.values())
        if total == 0:
            return {k: 1.0 / len(self._weights) for k in self._weights}
        return {k: v / total for k, v in self._weights.items()}

    def _compute_composite_score(self, dimensions: dict) -> float:
        """计算综合评分"""
        weights = self._normalize_weights()
        score = 0.0
        for dim, weight in weights.items():
            value = dimensions.get(dim, 0.5)
            score += value * weight
        return score

    def _score_to_regime(self, score: float) -> Regime:
        """评分转状态"""
        if score >= 0.7:
            return Regime.CRISIS
        elif score >= 0.5:
            return Regime.VOLATILE
        elif score >= 0.3:
            return Regime.RECOVERY
        else:
            return Regime.CALM

    def _can_switch(self) -> bool:
        """检查是否可以切换状态"""
        if self._last_switch is None:
            return True
        return datetime.now() - self._last_switch > self._cooldown

    def evaluate(self, dimensions: dict) -> RegimeVerdict:
        """
        评估当前状态

        参数:
            dimensions: 各维度评分，值域0-1
        返回:
            RegimeVerdict 包含状态、置信度、建议动作
        """
        score = self._compute_composite_score(dimensions)
        new_regime = self._score_to_regime(score)

        # 冷却期内不切换
        if new_regime != self._current_regime and not self._can_switch():
            new_regime = self._current_regime
            score = 1 - score  # 置信度反转

        if new_regime != self._current_regime:
            self._last_switch = datetime.now()
            self._current_regime = new_regime

        # 获取策略映射
        rule = self._regime_rules.get(new_regime, {})
        action = rule.get("action", "hold")
        max_pos = rule.get("max_position", 0.5)

        return RegimeVerdict(
            regime=new_regime,
            confidence=1 - abs(score - 0.5) * 2,  # 离中间越远越确定
            dimensions=dimensions,
            recommended_action=action,
            max_position_pct=max_pos
        )
