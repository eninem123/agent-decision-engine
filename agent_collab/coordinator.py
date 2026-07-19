"""
Agent协调器

从猎手系统的三Agent通信桥抽象而来，支持:
- 多Agent注册与发现
- 消息路由与投递
- 任务分发与结果收集
- 消息过滤与优先级
"""

from dataclasses import dataclass, field
from typing import Callable, Optional, Any
from .message import Message, MessageType


@dataclass
class Agent:
    """Agent定义"""
    id: str
    name: str
    capabilities: list[str] = field(default_factory=list)  # 能力标签
    handler: Optional[Callable[[Message], Any]] = None  # 消息处理器
    inbox: list[Message] = field(default_factory=list)  # 收件箱
    max_inbox: int = 100  # 收件箱容量


class AgentCoordinator:
    """
    Agent协调器

    用法:
        coordinator = AgentCoordinator()
        coordinator.register("lobster", "龙虾", capabilities=["trading", "analysis"])
        coordinator.register("hermes", "爱马仕", capabilities=["research", "memory"])

        coordinator.send("lobster", "hermes", MessageType.TASK, {"action": "research"})
        messages = coordinator.recv("hermes")
    """

    def __init__(self):
        self._agents: dict[str, Agent] = {}
        self._global_inbox: list[Message] = []

    def register(self, id: str, name: str, capabilities: list[str] = None,
                 handler: Callable = None):
        """注册Agent"""
        self._agents[id] = Agent(
            id=id,
            name=name,
            capabilities=capabilities or [],
            handler=handler
        )

    def unregister(self, id: str):
        """注销Agent"""
        self._agents.pop(id, None)

    def send(self, sender: str, receiver: str, msg_type: MessageType,
             payload: any) -> Optional[Message]:
        """
        发送消息

        返回发送成功的消息，失败返回None
        """
        if receiver not in self._agents:
            return None

        msg = Message(
            id=f"{sender}-{receiver}-{len(self._global_inbox)}",
            sender=sender,
            receiver=receiver,
            type=msg_type,
            payload=payload
        )

        agent = self._agents[receiver]
        if len(agent.inbox) >= agent.max_inbox:
            agent.inbox.pop(0)  # 丢弃最旧的

        agent.inbox.append(msg)
        self._global_inbox.append(msg)
        return msg

    def recv(self, agent_id: str, msg_type: MessageType = None) -> list[Message]:
        """
        接收消息（从收件箱取出）

        参数:
            agent_id: Agent ID
            msg_type: 过滤消息类型，None表示取全部
        """
        if agent_id not in self._agents:
            return []

        agent = self._agents[agent_id]
        if msg_type:
            messages = [m for m in agent.inbox if m.type == msg_type]
            agent.inbox = [m for m in agent.inbox if m.type != msg_type]
        else:
            messages = agent.inbox[:]
            agent.inbox.clear()

        return messages

    def broadcast(self, sender: str, msg_type: MessageType, payload: any):
        """广播消息给所有非发送者Agent"""
        for agent_id in self._agents:
            if agent_id != sender:
                self.send(sender, agent_id, msg_type, payload)

    def find_by_capability(self, capability: str) -> list[str]:
        """按能力查找Agent"""
        return [
            agent.id for agent in self._agents.values()
            if capability in agent.capabilities
        ]

    def stats(self) -> dict:
        """返回协调器统计"""
        return {
            "agents": len(self._agents),
            "total_messages": len(self._global_inbox),
            "inbox_sizes": {
                agent.id: len(agent.inbox)
                for agent in self._agents.values()
            }
        }
