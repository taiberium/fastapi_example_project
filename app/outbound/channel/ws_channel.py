from typing import Any

from fastapi import WebSocket


class WebSocketChannel:
    """WebSocket adapter for the MessageChannel port — sends JSON to the client."""

    def __init__(self, websocket: WebSocket):
        self._websocket = websocket

    async def send(self, payload: dict[str, Any]) -> None:
        await self._websocket.send_json(payload)
