"""
消息定义

从猎手系统的三Agent通信桥抽象而来。
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional, Any


class MessageType(Enum):
    """消息类型"""
    TASK = "task"           # 任务分发
    RESULT = "result"       # 结果回传
    SYNC = "sync"           # 状态同步
    ALERT = "alert"         # 告警通知
    HEARTBEAT = "heartbeat" # 心跳


@dataclass
class Message:
    """消息体"""
    id: str
    sender: str
    receiver: str
    type: MessageType
    payload: Any
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    reply_to: Optional[str] = None  # 关联的消息ID
    status: str = "pending"  # pending / processing / done / error

    def reply(self, payload: Any) -> "Message":
        """构造回复消息"""
        return Message(
            id=f"{self.id}-reply",
            sender=self.receiver,
            receiver=self.sender,
            type=self.type,
            payload=payload,
            reply_to=self.id
        )
