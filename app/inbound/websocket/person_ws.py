from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.service.person_service import PersonService

log = get_logger(__name__)

router = APIRouter()


@router.websocket("/ws/persons")
async def persons_overview_ws(
    websocket: WebSocket,
    # Same DI as an HTTP route — FastAPI resolves the service (and its session) for
    # the connection. The handler only talks to the service, never repositories.
    service: Annotated[PersonService, Depends(PersonService)],
) -> None:
    """Client sends `{"person_id": N}`; server replies with that person's overview."""
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_json()
            overview = service.get_overview(int(message["person_id"]))
            if overview is None:
                await websocket.send_json({"error": "not found"})
            else:
                await websocket.send_json(
                    {
                        "id": overview.person.id,
                        "name": overview.person.name,
                        "is_premium": overview.is_premium,
                    }
                )
    except WebSocketDisconnect:
        log.info("persons ws disconnected")
