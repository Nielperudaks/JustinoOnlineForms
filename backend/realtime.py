from typing import List, Optional
from fastapi import WebSocket
from redis.asyncio import Redis
import asyncio
import json
import logging
import os
import uuid

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.redis: Optional[Redis] = None
        self.pubsub = None
        self.listener_task: Optional[asyncio.Task] = None
        self.redis_channel = os.environ.get("REDIS_CHANNEL", "justino:realtime")
        self.instance_id = str(uuid.uuid4())

    async def startup(self):
        redis_url = os.environ.get("REDIS_URL")
        if not redis_url:
            logger.info("Redis realtime disabled: REDIS_URL not set")
            return

        try:
            self.redis = Redis.from_url(redis_url, decode_responses=True)
            await self.redis.ping()
            self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe(self.redis_channel)
            self.listener_task = asyncio.create_task(self._listen_for_messages())
            logger.info("Redis realtime enabled on channel %s", self.redis_channel)
        except Exception as exc:
            logger.exception("Failed to initialize Redis realtime: %s", exc)
            self.redis = None
            self.pubsub = None
            self.listener_task = None

    async def shutdown(self):
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
            self.listener_task = None

        if self.pubsub:
            try:
                await self.pubsub.unsubscribe(self.redis_channel)
                await self.pubsub.close()
            except Exception as exc:
                logger.warning("Error closing Redis pubsub: %s", exc)
            self.pubsub = None

        if self.redis:
            try:
                await self.redis.close()
            except Exception as exc:
                logger.warning("Error closing Redis connection: %s", exc)
            self.redis = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def _broadcast_local(self, event: str, payload: dict):
        message = json.dumps({
            "event": event,
            "payload": payload
        })
        for ws in list(self.active_connections):
            try:
                await ws.send_text(message)
            except Exception:
                self.disconnect(ws)

    async def _listen_for_messages(self):
        try:
            async for message in self.pubsub.listen():
                if message.get("type") != "message":
                    continue

                raw_data = message.get("data")
                if not raw_data:
                    continue

                try:
                    event_message = json.loads(raw_data)
                    await self._broadcast_local(
                        event_message["event"],
                        event_message["payload"]
                    )
                except Exception as exc:
                    logger.warning("Failed to process realtime message: %s", exc)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Redis realtime listener stopped unexpectedly: %s", exc)

    async def broadcast(self, event: str, payload: dict):
        event_message = {
            "event": event,
            "payload": payload,
            "instance_id": self.instance_id,
        }

        if self.redis:
            try:
                await self.redis.publish(self.redis_channel, json.dumps(event_message))
                return
            except Exception as exc:
                logger.warning("Redis publish failed, falling back to local broadcast: %s", exc)

        await self._broadcast_local(event, payload)


manager = ConnectionManager()
