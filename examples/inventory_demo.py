#!/usr/bin/env python3
"""
Decision Engine — 电商库存预警场景Demo

展示同一套四层架构如何复用于库存管理。
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
    print("  Decision Engine — 电商库存预警场景")
    print("=" * 60)

    # ========== 数据层 ==========
    print("\n[1] 数据层 — 采集+清洗")
    collector = DataCollector()
    collector.add_source("inventory", "mock", lambda: {
        "sku": "SKU-10086",
        "current_stock": 120,
        "daily_sales_avg": 45,
        "lead_time_days": 7,
        "safety_stock": 200,
        "warehouse": "深圳仓",
        "supplier_reliability": 0.92
    })
    collector.add_source("orders", "mock", lambda: {
        "pending_orders": 380,
        "today_orders": 95,
        "return_rate": 0.03
    })

    # 数据管道：计算关键指标
    pipeline = Pipeline()
    pipeline.add_step("compute_metrics", lambda d: {
        **d,
        "days_of_stock": round(d.get("current_stock", 0) / max(d.get("daily_sales_avg", 1), 1), 1),
        "stock_coverage": round(d.get("current_stock", 0) / max(d.get("safety_stock", 1), 1), 2),
        "demand_pressure": round(d.get("pending_orders", 0) / max(d.get("current_stock", 1), 1), 2),
    })

    inv_data = collector.fetch("inventory")["data"]
    order_data = collector.fetch("orders")["data"]
    combined = {**inv_data, **order_data}
    metrics = pipeline.process(combined)

    print(f"   SKU: {metrics['sku']} | 当前库存: {metrics['current_stock']}件")
    print(f"   日均销量: {metrics['daily_sales_avg']}件 | 补货周期: {metrics['lead_time_days']}天")
    print(f"   计算指标: 可售天数={metrics['days_of_stock']}天 | 需求压力={metrics['demand_pressure']}x")

    # ========== 决策层 ==========
    print("\n[2] 决策层 — 规则引擎+异常检测")

    # 异常检测
    detector = AnomalyDetector()
    detector.set_threshold("days_of_stock", min_val=7, max_val=60)
    detector.set_threshold("demand_pressure", max_val=3.0)
    detector.set_threshold("supplier_reliability", min_val=0.85)

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
        id="INV-001",
        name="紧急补货",
        condition=lambda ctx: ctx.get("days_of_stock", 99) < ctx.get("lead_time_days", 7) + 2,
        action="urgent_restock",
        priority=RulePriority.P0,
        params={"qty": 500, "channel": "urgent"}
    )
    engine.add_rule(
        id="INV-002",
        name="需求压力预警",
        condition=lambda ctx: ctx.get("demand_pressure", 0) > 2.0,
        action="demand_alert",
        priority=RulePriority.P0,
        params={"escalate": True}
    )
    engine.add_rule(
        id="INV-003",
        name="常规补货",
        condition=lambda ctx: ctx.get("days_of_stock", 99) < 14,
        action="routine_restock",
        priority=RulePriority.P1,
        params={"qty": 200, "channel": "routine"}
    )
    engine.add_rule(
        id="INV-004",
        name="库存健康",
        condition=lambda ctx: 14 <= ctx.get("days_of_stock", 99) <= 45,
        action="healthy",
        priority=RulePriority.P2
    )

    rule_results = engine.evaluate(metrics)
    print(f"   触发规则: {len(rule_results)} 条")
    for r in rule_results:
        print(f"      {r.reason} → {r.action} {r.params}")

    # ========== 执行层 ==========
    print("\n[3] 执行层 — 风控+执行")
    audit = AuditLog()
    layer = ExecutionLayer()

    layer.set_guard(lambda ctx: ctx.get("supplier_reliability", 0) > 0.8, "供应商可靠性低于80%，暂停自动补货")
    layer.set_guard(lambda ctx: ctx.get("qty", 0) <= 1000, "单次补货超过1000件，需人工审批")

    layer.register_action("urgent_restock", lambda ctx: print(f"   🚨 紧急补货: {ctx['sku']} x{ctx['qty']}件 → {ctx['warehouse']}"))
    layer.register_action("routine_restock", lambda ctx: print(f"   📦 常规补货: {ctx['sku']} x{ctx['qty']}件 → {ctx['warehouse']}"))
    layer.register_action("demand_alert", lambda ctx: print(f"   📢 需求预警: 待处理订单{ctx['pending_orders']}件，建议提前备货"))
    layer.register_action("healthy", lambda ctx: print(f"   ✅ 库存健康: 可售{ctx['days_of_stock']}天"))

    for r in rule_results:
        if r.action in ["urgent_restock", "routine_restock", "demand_alert", "healthy"]:
            exec_ctx = {**metrics, **r.params}
            result = layer.execute(r.action, exec_ctx)
            audit.record("inventory_monitor", r.action, exec_ctx, result.status.value)

    # ========== 统计 ==========
    print("\n" + "=" * 60)
    print("  库存监控统计")
    print("=" * 60)
    print(f"  规则引擎: {engine.stats()}")
    print(f"  执行层: {layer.stats()}")
    print(f"  审计日志: {audit.stats()}")
    print()


if __name__ == "__main__":
    main()
