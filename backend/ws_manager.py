# -*- coding: utf-8 -*-
"""WebSocket管理器 - 实时事件推送。"""
import json
from typing import Dict, Set
from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        self._connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.add(ws)

    def disconnect(self, ws: WebSocket):
        self._connections.discard(ws)

    async def broadcast(self, event_type: str, plugin: str = "", data: dict = None):
        msg = json.dumps({"type": event_type, "plugin": plugin, "data": data or {}}, ensure_ascii=False)
        dead = set()
        for ws in self._connections:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.add(ws)
        self._connections -= dead

    async def send_progress(self, plugin: str, current: int, total: int, message: str = "", eta: str = ""):
        await self.broadcast("progress", plugin, {
            "current": current, "total": total, "message": message, "eta": eta,
            "percent": round(current / total * 100, 1) if total > 0 else 0,
        })
