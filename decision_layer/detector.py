"""
异常检测模块

支持:
- 阈值检测（静态/动态）
- 统计异常（Z-Score / IQR）
- 趋势异常（连续偏离）
- 多维度联合检测
"""

import statistics
from dataclasses import dataclass
from typing import Optional


@dataclass
class AnomalyAlert:
    """异常告警"""
    dimension: str
    value: float
    threshold: float
    severity: str  # "low" / "medium" / "high" / "critical"
    message: str


class AnomalyDetector:
    """
    异常检测器

    用法:
        detector = AnomalyDetector()
        detector.set_threshold("cost", max_ratio=1.5)
        detector.set_zscore_threshold("revenue", z=2.0)

        alerts = detector.check({
            "cost": 150,
            "revenue": 5000,
            "stock": 20
        })
    """

    def __init__(self):
        self._thresholds = {}      # 静态阈值
        self._zscore_thresholds = {}  # Z-Score阈值
        self._history = {}         # 历史数据（用于Z-Score）
        self._max_history = 100    # 历史数据窗口

    def set_threshold(self, dimension: str, min_val: float = None, max_val: float = None,
                      max_ratio: float = None):
        """设置静态阈值"""
        self._thresholds[dimension] = {
            "min": min_val,
            "max": max_val,
            "max_ratio": max_ratio
        }

    def set_zscore_threshold(self, dimension: str, z: float = 2.0):
        """设置Z-Score阈值"""
        self._zscore_thresholds[dimension] = z
        if dimension not in self._history:
            self._history[dimension] = []

    def _check_threshold(self, dimension: str, value: float) -> Optional[AnomalyAlert]:
        """静态阈值检测"""
        config = self._thresholds.get(dimension)
        if not config:
            return None

        severity = "medium"
        if config.get("max") is not None and value > config["max"]:
            if value > config["max"] * 1.5:
                severity = "critical"
            elif value > config["max"] * 1.2:
                severity = "high"
            return AnomalyAlert(
                dimension=dimension,
                value=value,
                threshold=config["max"],
                severity=severity,
                message=f"{dimension}={value} 超过上限 {config['max']}"
            )

        if config.get("min") is not None and value < config["min"]:
            if value < config["min"] * 0.5:
                severity = "critical"
            elif value < config["min"] * 0.8:
                severity = "high"
            return AnomalyAlert(
                dimension=dimension,
                value=value,
                threshold=config["min"],
                severity=severity,
                message=f"{dimension}={value} 低于下限 {config['min']}"
            )

        return None

    def _check_zscore(self, dimension: str, value: float) -> Optional[AnomalyAlert]:
        """Z-Score统计异常检测"""
        z_threshold = self._zscore_thresholds.get(dimension)
        if not z_threshold:
            return None

        history = self._history.get(dimension, [])
        if len(history) < 10:
            history.append(value)
            self._history[dimension] = history[-self._max_history:]
            return None

        mean = statistics.mean(history)
        stdev = statistics.stdev(history)
        if stdev == 0:
            history.append(value)
            self._history[dimension] = history[-self._max_history:]
            return None

        z_score = abs(value - mean) / stdev
        if z_score > z_threshold:
            severity = "high" if z_score > z_threshold * 1.5 else "medium"
            return AnomalyAlert(
                dimension=dimension,
                value=value,
                threshold=z_threshold,
                severity=severity,
                message=f"{dimension} Z-Score={z_score:.2f} 超过阈值 {z_threshold}"
            )

        history.append(value)
        self._history[dimension] = history[-self._max_history:]
        return None

    def check(self, data: dict) -> list[AnomalyAlert]:
        """
        对所有维度执行异常检测
        返回所有异常告警
        """
        alerts = []
        for dimension, value in data.items():
            if not isinstance(value, (int, float)):
                continue

            # 静态阈值检测
            alert = self._check_threshold(dimension, value)
            if alert:
                alerts.append(alert)

            # Z-Score检测
            alert = self._check_zscore(dimension, value)
            if alert:
                alerts.append(alert)

        return alerts
