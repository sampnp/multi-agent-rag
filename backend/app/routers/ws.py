import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self._connections[client_id] = websocket

    def disconnect(self, client_id: str):
        self._connections.pop(client_id, None)

    async def send_personal(self, message: dict, client_id: str):
        ws = self._connections.get(client_id)
        if ws:
            await ws.send_text(json.dumps(message))

    async def broadcast(self, message: dict):
        for ws in self._connections.values():
            await ws.send_text(json.dumps(message))

    @property
    def active_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    await manager.send_personal(
        {"type": "system", "payload": {"message": "Connected to Enterprise AI OS", "client_id": client_id}},
        client_id,
    )
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"type": "chat", "payload": {"content": raw}}

            await manager.send_personal(
                {"type": "echo", "payload": {"client_id": client_id, "original": data}},
                client_id,
            )
    except WebSocketDisconnect:
        manager.disconnect(client_id)
