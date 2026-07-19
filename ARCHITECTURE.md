# Decision Engine — 通用业务规则引擎

从A股量化交易系统「猎手」抽象而来的通用决策框架。

## 四层架构

```
┌─────────────────────────────────────────┐
│           execution_layer               │
│     自动化执行 + 风控拦截 + 审计日志      │
├─────────────────────────────────────────┤
│           agent_collab                  │
│   多AI协作编排 + 消息队列 + 任务分发      │
├─────────────────────────────────────────┤
│           decision_layer                │
│     规则引擎 + 异常检测 + Regime判断      │
├─────────────────────────────────────────┤
│           data_layer                    │
│     实时数据采集 + 清洗 + 标准化          │
└─────────────────────────────────────────┘
```

## 核心能力

- **规则引擎**: 声明式规则定义，支持优先级/条件组合/动态权重
- **异常检测**: 多维度实时监控，自动识别偏离正常模式的行为
- **Agent协作**: 多AI角色分工，消息驱动的任务编排
- **风控拦截**: 执行前强制校验，支持熔断/降级/回滚

## 快速开始

```python
from decision_layer import RuleEngine
from data_layer import DataCollector

# 定义规则
engine = RuleEngine()
engine.add_rule("库存预警", condition="stock < threshold", action="alert")
engine.add_rule("成本异常", condition="cost > avg * 1.5", action="block")

# 接入数据
collector = DataCollector(source="api")
engine.bind(collector)

# 运行
engine.run()
```

## 场景示例

- `examples/stock_demo.py` — 量化交易场景
- `examples/inventory_demo.py` — 电商库存预警
- `examples/supply_chain_demo.py` — 供应链成本检测
