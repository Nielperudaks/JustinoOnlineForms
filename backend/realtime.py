from typing import List
from fastapi import WebSocket
import asyncio
import json

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, event: str, payload: dict):
        message = json.dumps({
            "event": event,
            "payload": payload
        })
        for ws in list(self.active_connections):
            try:
                await ws.send_text(message)
            except:
                self.disconnect(ws)

manager = ConnectionManager()
