#!/usr/bin/env python3
"""
Decision Engine — 供应链成本异常检测场景Demo

展示同一套四层架构如何复用于采购成本监控。
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from decision_layer.engine import RuleEngine, RulePriority
    from decision_layer.detector import AnomalyDetector
    from data_layer import DataCollector, Pipeline
    from execution_layer import ExecutionLayer, AuditLog
except ImportError:
    print("⚠️  核心模块未安装，请从 GitHub 克隆完整仓库")
    print("   git clone git@github.com:eninem123/agent-decision-engine.git")
    sys.exit(1)


def main():
    print("=" * 60)
    print("  Decision Engine — 供应链成本异常检测")
    print("=" * 60)

    # ========== 数据层 ==========
    print("\n[1] 数据层 — 采购数据采集")
    collector = DataCollector()
    collector.add_source("purchase", "mock", lambda: {
        "item": "PCB主板",
        "supplier": "供应商A",
        "unit_price": 85.5,
        "last_price": 72.0,
        "market_avg": 78.0,
        "qty": 5000,
        "lead_time_days": 15,
        "quality_pass_rate": 0.96
    })
    collector.add_source("contract", "mock", lambda: {
        "contract_price": 75.0,
        "contract_valid_until": "2026-12-31",
        "penalty_rate": 0.05
    })

    pipeline = Pipeline()
    pipeline.add_step("compute", lambda d: {
        **d,
        "price_deviation": round((d.get("unit_price", 0) - d.get("market_avg", 1)) / d.get("market_avg", 1) * 100, 2),
        "contract_violation": d.get("unit_price", 0) > d.get("contract_price", 999),
        "total_cost": round(d.get("unit_price", 0) * d.get("qty", 0), 2),
        "cost_overrun": round((d.get("unit_price", 0) - d.get("contract_price", 0)) * d.get("qty", 0), 2)
    })

    purchase_data = collector.fetch("purchase")["data"]
    contract_data = collector.fetch("contract")["data"]
    metrics = pipeline.process({**purchase_data, **contract_data})

    print(f"   物料: {metrics['item']} | 供应商: {metrics['supplier']}")
    print(f"   本次单价: ¥{metrics['unit_price']} | 市场均价: ¥{metrics['market_avg']} | 合同价: ¥{metrics['contract_price']}")
    print(f"   偏离: {metrics['price_deviation']}% | 超支: ¥{metrics['cost_overrun']}")

    # ========== 决策层 ==========
    print("\n[2] 决策层 — 异常检测+规则引擎")

    # 异常检测
    detector = AnomalyDetector()
    detector.set_threshold("price_deviation", max_val=10.0)
    detector.set_threshold("quality_pass_rate", min_val=0.95)

    alerts = detector.check(metrics)
    if alerts:
        print("   ⚠️  异常告警:")
        for a in alerts:
            print(f"      [{a.severity}] {a.message}")
    else:
        print("   ✅ 无异常")

    # 规则引擎
    engine = RuleEngine()
    engine.add_rule(
        id="SCM-001",
        name="合同违约检测",
        condition=lambda ctx: ctx.get("contract_violation", False),
        action="contract_violation_alert",
        priority=RulePriority.P0,
        params={"notify_legal": True}
    )
    engine.add_rule(
        id="SCM-002",
        name="严重偏离市场价",
        condition=lambda ctx: ctx.get("price_deviation", 0) > 15,
        action="block_purchase",
        priority=RulePriority.P0,
        params={"require_approval": "CPO"}
    )
    engine.add_rule(
        id="SCM-003",
        name="供应商质量预警",
        condition=lambda ctx: ctx.get("quality_pass_rate", 1) < 0.95,
        action="quality_alert",
        priority=RulePriority.P1,
        params={"audit_supplier": True}
    )
    engine.add_rule(
        id="SCM-004",
        name="常规采购确认",
        condition=lambda ctx: abs(ctx.get("price_deviation", 0)) <= 5,
        action="approve",
        priority=RulePriority.P2
    )

    rule_results = engine.evaluate(metrics)
    print(f"   触发规则: {len(rule_results)} 条")
    for r in rule_results:
        print(f"      {r.reason} → {r.action} {r.params}")

    # ========== 执行层 ==========
    print("\n[3] 执行层 — 审批+拦截")
    audit = AuditLog()
    layer = ExecutionLayer()

    layer.set_guard(lambda ctx: ctx.get("qty", 0) <= 10000, "超过10000件需董事会审批")

    layer.register_action("contract_violation_alert",
        lambda ctx: print(f"   🔴 合同违约: {ctx['item']}单价¥{ctx['unit_price']} > 合同价¥{ctx['contract_price']}，超支¥{ctx['cost_overrun']}"))
    layer.register_action("block_purchase",
        lambda ctx: print(f"   🚫 采购拦截: 偏离市场价{ctx['price_deviation']}%，需{ctx['require_approval']}审批"))
    layer.register_action("quality_alert",
        lambda ctx: print(f"   ⚠️  质量预警: 通过率{ctx['quality_pass_rate']*100}%，建议启动供应商审计"))
    layer.register_action("approve",
        lambda ctx: print(f"   ✅ 采购确认: {ctx['item']} x{ctx['qty']}件，总价¥{ctx['total_cost']}"))

    for r in rule_results:
        if r.action in ["contract_violation_alert", "block_purchase", "quality_alert", "approve"]:
            exec_ctx = {**metrics, **r.params}
            result = layer.execute(r.action, exec_ctx)
            audit.record("supply_chain_monitor", r.action, exec_ctx, result.status.value)

    print("\n" + "=" * 60)
    print("  供应链监控统计")
    print("=" * 60)
    print(f"  规则引擎: {engine.stats()}")
    print(f"  执行层: {layer.stats()}")
    print(f"  审计日志: {audit.stats()}")


if __name__ == "__main__":
    main()
