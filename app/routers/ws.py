import json
from typing import ClassVar

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Simple WebSocket manager for real-time order notifications."""

    active_connections: ClassVar[list[WebSocket]] = []

    @classmethod
    async def connect(cls, websocket: WebSocket) -> None:
        await websocket.accept()
        cls.active_connections.append(websocket)

    @classmethod
    def disconnect(cls, websocket: WebSocket) -> None:
        if websocket in cls.active_connections:
            cls.active_connections.remove(websocket)

    @classmethod
    async def broadcast(cls, message: dict) -> None:
        """Send a message to all connected clients."""
        dead: list[WebSocket] = []
        for connection in cls.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                dead.append(connection)
        for d in dead:
            if d in cls.active_connections:
                cls.active_connections.remove(d)


manager = ConnectionManager()


@router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket):
    """WebSocket endpoint for real-time notifications.
    Admin panel connects here to receive new order and status update alerts."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; client can send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
