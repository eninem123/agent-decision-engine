#!/usr/bin/env python3
"""
Decision Engine — 量化交易场景Demo

展示四层架构如何协作完成一次交易决策。
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decision_layer.engine import RuleEngine, RulePriority
from decision_layer.detector import AnomalyDetector
from decision_layer.regime import RegimeJudge, Regime
from data_layer import DataCollector, Pipeline
from agent_collab import AgentCoordinator, MessageType
from execution_layer import ExecutionLayer, AuditLog


def main():
    print("=" * 60)
    print("  Decision Engine — 量化交易场景Demo")
    print("=" * 60)

    # ========== 数据层 ==========
    print("\n[1] 数据层 — 采集+清洗")
    collector = DataCollector()

    # 模拟数据源
    collector.add_source(
        "market",
        source_type="mock",
        fetch_fn=lambda: {
            "sh_index": 3250.5,
            "volume": 4500,
            "up_count": 2800,
            "down_count": 1200
        }
    )
    collector.add_source(
        "risk",
        source_type="mock",
        fetch_fn=lambda: {"volatility": 0.35, "drawdown": -0.08}
    )

    # 数据管道：清洗+标准化
    pipeline = Pipeline()
    pipeline.add_step("normalize", lambda d: {
        "market_sentiment": 1.0 - (d.get("down_count", 0) / max(d.get("up_count", 1) + d.get("down_count", 1), 1)),
        "risk_level": d.get("volatility", 0.5),
        "volume_ratio": d.get("volume", 0) / 3000  # 基准3000亿
    })

    market_data = collector.fetch("market")["data"]
    risk_data = collector.fetch("risk")["data"]
    combined = {**market_data, **risk_data}
    normalized = pipeline.process(combined)
    print(f"   原始数据: {combined}")
    print(f"   清洗后: {normalized}")

    # ========== 决策层 ==========
    print("\n[2] 决策层 — 规则引擎+状态判断")

    # Regime判断
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
    print(f"   Regime: {verdict.regime.value} | 置信度: {verdict.confidence:.2f}")
    print(f"   建议: {verdict.recommended_action} | 最大仓位: {verdict.max_position_pct*100}%")

    # 异常检测
    detector = AnomalyDetector()
    detector.set_threshold("volume_ratio", min_val=0.5, max_val=3.0)
    detector.set_zscore_threshold("risk_level", z=2.0)

    alerts = detector.check(normalized)
    if alerts:
        print(f"   ⚠️  异常告警:")
        for alert in alerts:
            print(f"      [{alert.severity}] {alert.message}")
    else:
        print("   ✅ 无异常")

    # 规则引擎
    engine = RuleEngine()
    engine.add_rule(
        id="FM-071",
        name="大盘20日线风控",
        condition=lambda ctx: ctx.get("risk_level", 0) > 0.6,
        action="reduce_position",
        priority=RulePriority.P0,
        params={"reduce_pct": 50}
    )
    engine.add_rule(
        id="FM-074",
        name="追高禁令",
        condition=lambda ctx: ctx.get("volume_ratio", 0) > 2.5,
        action="block_buy",
        priority=RulePriority.P0
    )
    engine.add_rule(
        id="FM-073",
        name="仓位管理",
        condition=lambda ctx: ctx.get("position_pct", 0) > 30,
        action="reduce_position",
        priority=RulePriority.P1,
        params={"reduce_pct": 20}
    )

    context = {
        "risk_level": normalized.get("risk_level", 0.5),
        "volume_ratio": normalized.get("volume_ratio", 1.0),
        "position_pct": 25
    }
    rule_results = engine.evaluate(context)
    print(f"   触发规则: {len(rule_results)} 条")
    for r in rule_results:
        print(f"      {r.reason} → {r.action} {r.params}")

    # ========== Agent协作层 ==========
    print("\n[3] Agent协作层 — 任务分发")

    coordinator = AgentCoordinator()
    coordinator.register("lobster", "龙虾", capabilities=["trading", "monitoring"])
    coordinator.register("hermes", "爱马仕", capabilities=["research", "analysis"])
    coordinator.register("executor", "执行器", capabilities=["execution"])

    # 龙虾发送交易信号给执行器
    msg = coordinator.send("lobster", "executor", MessageType.TASK, {
        "action": "buy",
        "stock": "601166",
        "qty": 100,
        "regime": verdict.regime.value,
        "rule_results": [{"action": r.action, "params": r.params} for r in rule_results]
    })
    print(f"   消息发送: {msg.sender} → {msg.receiver}")
    print(f"   消息内容: {msg.payload}")

    # 执行器接收
    messages = coordinator.recv("executor")
    print(f"   执行器收到 {len(messages)} 条消息")

    # ========== 执行层 ==========
    print("\n[4] 执行层 — 风控+执行+审计")

    audit = AuditLog()
    layer = ExecutionLayer()

    # 风控拦截器
    layer.set_guard(
        lambda ctx: ctx.get("regime") != "crisis",
        "危机状态禁止交易"
    )
    layer.set_guard(
        lambda ctx: ctx.get("qty", 0) <= 1000,
        "单笔超过1000股"
    )

    # 注册动作
    layer.register_action(
        "buy",
        lambda ctx: print(f"   ✅ 执行买入: {ctx['stock']} x{ctx['qty']}"),
        rollback_fn=lambda ctx: print(f"   ↩️ 回滚: 取消买入 {ctx['stock']}")
    )
    layer.register_action(
        "sell",
        lambda ctx: print(f"   ✅ 执行卖出: {ctx['stock']} x{ctx['qty']}")
    )

    # 执行
    task = messages[0].payload
    result = layer.execute(task["action"], {
        "stock": task["stock"],
        "qty": task["qty"],
        "regime": task["regime"]
    })
    print(f"   执行结果: {result.status.value}")

    # 审计日志
    audit.record("lobster", "buy", task, result.status.value)
    audit_log = audit.query(agent_id="lobster")
    print(f"   审计记录: {len(audit_log)} 条")

    # ========== 统计 ==========
    print("\n" + "=" * 60)
    print("  系统统计")
    print("=" * 60)
    print(f"  规则引擎: {engine.stats()}")
    print(f"  Agent协作: {coordinator.stats()}")
    print(f"  执行层: {layer.stats()}")
    print(f"  审计日志: {audit.stats()}")
    print()


if __name__ == "__main__":
    main()
