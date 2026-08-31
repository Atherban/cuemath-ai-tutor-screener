from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.core.exceptions import AIProviderError

router = APIRouter(tags=["AI"])


class AITestRequest(BaseModel):
    prompt: str = Field(
        default="In one sentence, say hello to a future maths tutor.",
        max_length=2000,
        description="Prompt to send to the configured AI provider.",
    )
    temperature: float = Field(default=0.7, ge=0, le=2)


class AITestResponse(BaseModel):
    provider: str
    model: str
    response: str


@router.post(
    "/ai/test",
    response_model=AITestResponse,
    summary="Test the AI provider",
    description=(
        "Sends a prompt to the configured AI provider and returns its response. "
        "Use this to verify your API key / endpoint (e.g. NVIDIA) is working "
        "before starting an interview."
    ),
)
async def test_ai(request: Request, body: AITestRequest | None = None) -> AITestResponse:
    settings = request.app.state.settings
    provider = request.app.state.ai_provider
    payload = body or AITestRequest()

    if provider.name == "mock":
        raise AIProviderError(
            "AI_PROVIDER is set to 'mock'. Set AI_PROVIDER=nvidia (or openai/ollama) "
            "with your model, API key, and base URL in .env to test a real model."
        )

    response = await provider.generate_text(payload.prompt, temperature=payload.temperature)
    return AITestResponse(
        provider=provider.name,
        model=settings.ai_model or "not-set",
        response=response,
    )
