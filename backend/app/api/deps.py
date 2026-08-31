from __future__ import annotations

from collections.abc import AsyncGenerator

from app.repositories.sessions import SessionRepository

_repo: SessionRepository | None = None


def init_repository() -> SessionRepository:
    global _repo
    if _repo is None:
        _repo = SessionRepository()
    return _repo


async def get_repository() -> AsyncGenerator[SessionRepository, None]:
    yield init_repository()