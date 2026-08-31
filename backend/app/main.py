from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.deps import init_repository
from app.api.routes import ai, assessments, health, sessions
from app.api.websocket.interview import InterviewWebSocketController
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import setup_logging
from app.services.ai.provider import build_provider
from app.services.assessment.evaluator import AssessmentEvaluator
from app.services.interview.engine import InterviewEngine
from app.services.stt.local import build_stt
from app.services.tts.local import build_tts

setup_logging()
logger = logging.getLogger(__name__)

# The built frontend, mounted by the backend so a single service serves both
# the SPA and the API (same origin — no CORS, and WebSockets share the host).
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    repo = init_repository()
    ai_provider = build_provider(settings)
    stt = build_stt(settings)
    tts = build_tts(settings)
    engine = InterviewEngine(settings, ai_provider)
    evaluator = AssessmentEvaluator(ai_provider)

    app.state.repository = repo
    app.state.ai_provider = ai_provider
    app.state.settings = settings
    app.state.interview_controller = InterviewWebSocketController(
        repository=repo,
        engine=engine,
        stt=stt,
        tts=tts,
        evaluator=evaluator,
        settings=settings,
    )
    logger.info("Application started", extra={"env": settings.app_env})
    yield
    logger.info("Application stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "Backend for an AI-powered first-round tutor screening interview for "
            "Cuemath. Conducts a voice interview over WebSocket and produces an "
            "evidence-backed assessment."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(_request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled exception", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                }
            },
        )

    app.include_router(health.router, prefix=settings.api_v1_prefix)
    app.include_router(sessions.router, prefix=settings.api_v1_prefix)
    app.include_router(assessments.router, prefix=settings.api_v1_prefix)
    app.include_router(ai.router, prefix=settings.api_v1_prefix)

    # Serve the built frontend SPA so a single origin hosts the UI and the API.
    if FRONTEND_DIST.is_dir():
        assets_dir = FRONTEND_DIST / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa(full_path: str) -> FileResponse:
            # Return a real asset if it exists, otherwise the SPA shell so
            # client-side routes (/interview/..., /complete, ...) keep working.
            candidate = FRONTEND_DIST / full_path
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(FRONTEND_DIST / "index.html")

    @app.websocket("/ws/interview/{session_id}")
    async def interview_socket(websocket: WebSocket, session_id: str) -> None:
        controller: InterviewWebSocketController = app.state.interview_controller
        await controller.handle(websocket, session_id)

    return app


app = create_app()
