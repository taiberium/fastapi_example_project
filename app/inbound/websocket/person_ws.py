from typing import Annotated, Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.outbound.channel.channel import MessageChannel
from app.outbound.channel.ws_channel import WebSocketChannel
from app.service.person_service import PersonOverview, PersonService

log = get_logger(__name__)

router = APIRouter()


def _overview_payload(overview: PersonOverview | None) -> dict[str, Any]:
    # Map the domain aggregate -> response shape at the boundary (like an HTTP route).
    if overview is None:
        return {"error": "not found"}
    return {
        "id": overview.person.id,
        "name": overview.person.name,
        "is_premium": overview.is_premium,
    }


@router.websocket("/ws/persons")
async def persons_overview_ws(
    websocket: WebSocket,
    # Same DI as an HTTP route — go through the service, never repositories.
    service: Annotated[PersonService, Depends(PersonService)],
) -> None:
    """Client sends `{"person_id": N}`; the reply is sent out via the channel port."""
    await websocket.accept()
    channel: MessageChannel = WebSocketChannel(websocket)  # outbound: sending replies
    try:
        while True:
            message = await websocket.receive_json()  # inbound: receiving
            overview = service.get_overview(int(message["person_id"]))
            await channel.send(_overview_payload(overview))
    except WebSocketDisconnect:
        log.info("persons ws disconnected")
