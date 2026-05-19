# -*- coding: utf-8 -*-
"""WebSocket路由 - 实时事件流。"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app import ws_manager

router = APIRouter()


@router.websocket("/events")
async def ws_events(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
