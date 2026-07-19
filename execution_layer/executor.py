"""
执行层模块

核心功能:
- 执行前强制校验（规则引擎 + 异常检测）
- 熔断/降级/回滚
- 并发控制（限流）
- 执行日志审计
"""

import json
from dataclasses import dataclass, field
from typing import Callable, Optional, Any
from datetime import datetime
from enum import Enum


class ExecutionStatus(Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    BLOCKED = "blocked"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class ExecutionResult:
    """执行结果"""
    action: str
    status: ExecutionStatus
    data: Any = None
    reason: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ExecutionLayer:
    """
    执行层

    用法:
        layer = ExecutionLayer()
        layer.set_guard(lambda ctx: ctx.get("risk", 0) < 0.8)  # 风控拦截
        layer.register_action("buy", lambda ctx: print(f"买入 {ctx['item']}"))

        result = layer.execute("buy", {"item": "stock_A", "risk": 0.3})
    """

    def __init__(self):
        self._actions: dict[str, Callable] = {}
        self._guards: list[Callable[[dict], bool]] = []
        self._guard_messages: list[str] = []
        self._rollback_actions: dict[str, Callable] = {}
        self._execution_log: list[ExecutionResult] = []
        self._max_executions = 1000  # 日志上限
        self._circuit_breaker = False  # 熔断开关

    def register_action(self, name: str, fn: Callable,
                        rollback_fn: Callable = None):
        """注册执行动作"""
        self._actions[name] = fn
        if rollback_fn:
            self._rollback_actions[name] = rollback_fn

    def set_guard(self, guard_fn: Callable[[dict], bool],
                  message: str = "风控拦截"):
        """设置执行前校验"""
        self._guards.append(guard_fn)
        self._guard_messages.append(message)

    def circuit_break(self):
        """触发熔断"""
        self._circuit_breaker = True

    def reset_circuit_breaker(self):
        """重置熔断"""
        self._circuit_breaker = False

    def _check_guards(self, context: dict) -> Optional[str]:
        """检查所有风控规则"""
        for guard_fn, msg in zip(self._guards, self._guard_messages):
            try:
                if not guard_fn(context):
                    return msg
            except Exception as e:
                return f"风控规则执行异常: {e}"
        return None

    def _log(self, result: ExecutionResult):
        """记录执行日志"""
        self._execution_log.append(result)
        if len(self._execution_log) > self._max_executions:
            self._execution_log = self._execution_log[-self._max_executions:]

    def execute(self, action: str, context: dict) -> ExecutionResult:
        """
        执行动作

        流程: 熔断检查 → 风控校验 → 执行 → 日志
        """
        # 熔断检查
        if self._circuit_breaker:
            result = ExecutionResult(
                action=action,
                status=ExecutionStatus.BLOCKED,
                reason="系统已熔断，拒绝执行"
            )
            self._log(result)
            return result

        # 动作是否存在
        if action not in self._actions:
            result = ExecutionResult(
                action=action,
                status=ExecutionStatus.FAILED,
                reason=f"动作 '{action}' 未注册"
            )
            self._log(result)
            return result

        # 风控校验
        guard_msg = self._check_guards(context)
        if guard_msg:
            result = ExecutionResult(
                action=action,
                status=ExecutionStatus.BLOCKED,
                reason=guard_msg
            )
            self._log(result)
            return result

        # 执行
        try:
            data = self._actions[action](context)
            result = ExecutionResult(
                action=action,
                status=ExecutionStatus.SUCCESS,
                data=data,
                reason="执行成功"
            )
        except Exception as e:
            result = ExecutionResult(
                action=action,
                status=ExecutionStatus.FAILED,
                reason=str(e)
            )
            # 尝试回滚
            if action in self._rollback_actions:
                try:
                    self._rollback_actions[action](context)
                    result.status = ExecutionStatus.ROLLED_BACK
                    result.reason += " (已回滚)"
                except Exception as re:
                    result.reason += f" (回滚失败: {re})"

        self._log(result)
        return result

    def get_log(self, limit: int = 50) -> list[ExecutionResult]:
        """获取执行日志"""
        return self._execution_log[-limit:]

    def stats(self) -> dict:
        """执行统计"""
        status_counts = {}
        for r in self._execution_log:
            s = r.status.value
            status_counts[s] = status_counts.get(s, 0) + 1
        return {
            "total_executions": len(self._execution_log),
            "status_counts": status_counts,
            "circuit_breaker": self._circuit_breaker,
            "registered_actions": list(self._actions.keys()),
            "guard_count": len(self._guards)
        }
