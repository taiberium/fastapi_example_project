from typing import Any, Protocol


class MessageChannel(Protocol):
    """Outbound port: send a message to a connected client.

    The driving side (a WebSocket handler) receives; sending the reply/event back
    out is a driven concern, behind this port — swap the transport (WebSocket ->
    SSE -> ...) without touching the handler.
    """

    async def send(self, payload: dict[str, Any]) -> None: ...
