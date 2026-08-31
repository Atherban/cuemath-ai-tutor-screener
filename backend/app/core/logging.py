from __future__ import annotations

import json
import logging
import sys
from typing import Any

from app.core.config import settings

_RESERVED = {"name", "msg", "args", "levelname", "levelno", "pathname", "filename", "module",
             "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs",
             "relativeCreated", "thread", "threadName", "processName", "process", "taskName"}


class JsonFormatter(logging.Formatter):
    """Structured JSON log formatter.

    Only safe, non-sensitive fields are included. Candidate transcripts and raw
    audio are never logged; session IDs are used instead.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "session_id": getattr(record, "session_id", None),
            "interview_stage": getattr(record, "interview_stage", None),
            "error_code": getattr(record, "error_code", None),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key not in _RESERVED and key not in payload and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, default=str)


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level.upper())
    logging.getLogger("uvicorn.access").handlers = [handler]
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
