from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.outbound.channel.ws_channel import WebSocketChannel
from app.service.person_service import PersonService

log = get_logger(__name__)

router = APIRouter()


@router.websocket("/ws/persons")
async def persons_overview_ws(
    websocket: WebSocket,
    # Same DI as an HTTP route — go through the service, never repositories.
    service: Annotated[PersonService, Depends(PersonService)],
) -> None:
    """Client sends `{"person_id": N}`. Input -> service -> output: the handler only
    receives and calls the service; the SERVICE pushes the reply via the channel."""
    await websocket.accept()
    channel = WebSocketChannel(
        websocket
    )  # per-connection output port (handler owns the socket)
    try:
        while True:
            message = await websocket.receive_json()
            await service.push_overview(int(message["person_id"]), channel)
    except WebSocketDisconnect:
        log.info("persons ws disconnected")
