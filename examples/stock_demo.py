#!/usr/bin/env python3
"""
Decision Engine — 量化交易场景（简化Demo）

展示四层架构如何协作完成一次交易决策。
完整代码见 GitHub 仓库。
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from decision_layer.engine import RuleEngine, RulePriority
    from decision_layer.detector import AnomalyDetector
    from decision_layer.regime import RegimeJudge, Regime
    from data_layer import DataCollector, Pipeline
    from agent_collab import AgentCoordinator, MessageType
    from execution_layer import ExecutionLayer, AuditLog
except ImportError:
    print("⚠️  核心模块未安装，请从 GitHub 克隆完整仓库")
    print("   git clone git@github.com:eninem123/agent-decision-engine.git")
    sys.exit(1)


def main():
    print("=" * 60)
    print("  Decision Engine — 量化交易场景Demo")
    print("=" * 60)

    # 数据层
    print("\n[1] 数据层 — 采集+清洗")
    collector = DataCollector()
    collector.add_source("market", "mock", lambda: {
        "sh_index": 3250.5, "volume": 4500,
        "up_count": 2800, "down_count": 1200
    })
    collector.add_source("risk", "mock", lambda: {"volatility": 0.35, "drawdown": -0.08})

    pipeline = Pipeline()
    pipeline.add_step("normalize", lambda d: {
        "market_sentiment": 1.0 - (d.get("down_count", 0) / max(d.get("up_count", 1) + d.get("down_count", 1), 1)),
        "risk_level": d.get("volatility", 0.5),
        "volume_ratio": d.get("volume", 0) / 3000
    })

    market_data = collector.fetch("market")["data"]
    risk_data = collector.fetch("risk")["data"]
    normalized = pipeline.process({**market_data, **risk_data})
    print(f"   原始: {market_data}")
    print(f"   清洗: {normalized}")

    # 决策层
    print("\n[2] 决策层 — 规则引擎+状态判断")
    regime_judge = RegimeJudge()
    regime_judge.set_dimension_weight("risk", 0.4)
    regime_judge.set_dimension_weight("sentiment", 0.3)
    regime_judge.set_dimension_weight("trend", 0.3)
    regime_judge.set_regime_rule(Regime.CALM, "aggressive", 0.6)
    regime_judge.set_regime_rule(Regime.VOLATILE, "cautious", 0.3)
    regime_judge.set_regime_rule(Regime.CRISIS, "defensive", 0.0)

    verdict = regime_judge.evaluate({
        "risk": normalized.get("risk_level", 0.5),
        "sentiment": normalized.get("market_sentiment", 0.5),
        "trend": normalized.get("volume_ratio", 1.0)
    })
    print(f"   Regime: {verdict.regime.value} | 建议: {verdict.recommended_action}")

    # Agent协作层
    print("\n[3] Agent协作层 — 任务分发")
    coordinator = AgentCoordinator()
    coordinator.register("lobster", "龙虾", capabilities=["trading"])
    coordinator.register("executor", "执行器", capabilities=["execution"])

    msg = coordinator.send("lobster", "executor", MessageType.TASK, {
        "action": "buy", "stock": "601166", "qty": 100, "regime": verdict.regime.value
    })
    print(f"   {msg.sender} → {msg.receiver}: {msg.payload}")

    # 执行层
    print("\n[4] 执行层 — 风控+执行")
    layer = ExecutionLayer()
    layer.set_guard(lambda ctx: ctx.get("regime") != "crisis", "危机状态禁止交易")
    layer.register_action("buy", lambda ctx: print(f"   ✅ 买入 {ctx['stock']} x{ctx['qty']}"))

    messages = coordinator.recv("executor")
    task = messages[0].payload
    result = layer.execute(task["action"], {
        "stock": task["stock"], "qty": task["qty"], "regime": task["regime"]
    })
    print(f"   结果: {result.status.value}")

    print("\n" + "=" * 60)
    print("  完整代码: git clone git@github.com:eninem123/agent-decision-engine.git")
    print("=" * 60)


if __name__ == "__main__":
    main()
