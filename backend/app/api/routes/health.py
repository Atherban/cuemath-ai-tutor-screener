from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness check", description="Returns service status.")
async def health() -> dict[str, str]:
    return {"status": "ok"}
