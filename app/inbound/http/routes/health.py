from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    # Liveness check — no DB, just confirms the app is up and serving.
    return {"status": "ok"}
