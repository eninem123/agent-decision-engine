"""
审计日志模块

记录所有操作的完整链路，支持:
- 按时间范围查询
- 按Agent/动作类型过滤
- 导出JSON
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class AuditEntry:
    """审计条目"""
    timestamp: str
    agent_id: str
    action: str
    context: dict
    result: str  # success / blocked / failed
    details: str = ""
    session_id: str = ""


class AuditLog:
    """
    审计日志

    用法:
        log = AuditLog()
        log.record("lobster", "buy", {"stock": "601166"}, "success")
        entries = log.query(agent_id="lobster")
    """

    def __init__(self):
        self._entries: list[AuditEntry] = []
        self._max_entries = 10000

    def record(self, agent_id: str, action: str, context: dict,
               result: str, details: str = "", session_id: str = ""):
        """记录审计条目"""
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            agent_id=agent_id,
            action=action,
            context=context,
            result=result,
            details=details,
            session_id=session_id
        )
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

    def query(self, agent_id: str = None, action: str = None,
              result: str = None, limit: int = 100) -> list[AuditEntry]:
        """查询审计日志"""
        entries = self._entries

        if agent_id:
            entries = [e for e in entries if e.agent_id == agent_id]
        if action:
            entries = [e for e in entries if e.action == action]
        if result:
            entries = [e for e in entries if e.result == result]

        return entries[-limit:]

    def export_json(self, filepath: str):
        """导出为JSON"""
        data = [
            {
                "timestamp": e.timestamp,
                "agent_id": e.agent_id,
                "action": e.action,
                "context": e.context,
                "result": e.result,
                "details": e.details,
                "session_id": e.session_id
            }
            for e in self._entries
        ]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def stats(self) -> dict:
        """统计"""
        results = {}
        for e in self._entries:
            r = e.result
            results[r] = results.get(r, 0) + 1
        agents = {}
        for e in self._entries:
            a = e.agent_id
            agents[a] = agents.get(a, 0) + 1
        return {
            "total_entries": len(self._entries),
            "by_result": results,
            "by_agent": agents
        }
