from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, Protocol

from app.core.config import Settings
from app.core.exceptions import AIProviderError
from app.services.ai.base import AIProvider, AIResponse, ChatMessage

logger = logging.getLogger(__name__)

# -- Local default responses used when no AI backend is configured. ----------

_DEFAULT_OPENING = (
    "Hello, welcome to the interview! Tell me a little about yourself and why "
    "you'd like to become a maths tutor."
)

_MOCK_BANKS: dict[str, list[str]] = {
    "INTRO": [
        "Tell me a bit about yourself and why you want to be a maths tutor.",
        "What is your background, and what drew you to teaching maths?",
        "Could you introduce yourself and share why you're interested in this role?",
    ],
    "SIMPLIFICATION": [
        "Imagine you are explaining fractions to a seven-year-old. How would you describe what one half means using only everyday objects?",
        "How would you explain the concept of area to a child who has just learned to multiply?",
        "A young student asks you what multiplication really is. How would you explain it in the simplest possible way?",
    ],
    "ROLEPLAY": [
        "A student has been staring at a problem for five minutes and says they don't understand. What would you say to them?",
        "A child tells you they are too dumb to learn maths. How do you respond in that moment?",
        "A student keeps making the same mistake even after you've explained it twice. What do you do?",
    ],
    "METHODOLOGY": [
        "How would you check whether a student truly understands a concept versus just memorising the steps?",
        "What question would you ask a student to tell if they really get the idea or are just repeating the method?",
        "A student solves a problem correctly but cannot explain why it works. How would you assess their understanding?",
    ],
    "SCENARIO": [
        "A student is distracted and not paying attention to the lesson. How would you handle that situation?",
        "A parent disagrees with your teaching approach and says you are moving too slowly. How would you communicate with them?",
        "A child becomes frustrated and starts crying during a lesson. What would you do to support them?",
    ],
}

_MOCK_PROBE = [
    "Thanks for that. Could you give me a concrete example of what you would actually say?",
    "I'd love a little more detail — what would that look like in a real session?",
    "Could you walk me through that step by step?",
]


class MockAIProvider:
    """Local provider so the backend runs with zero external services.

    Used for development and tests only. Returns independent, parameter-specific
    questions per stage so the mock flow mirrors the independent-question design.
    """

    name = "mock"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._rng = random.Random()

    async def generate_response(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AIResponse:
        await asyncio.sleep(0.01)
        text = _DEFAULT_OPENING
        for message in reversed(messages):
            lowered = message.content.lower()
            for stage, bank in _MOCK_BANKS.items():
                if stage.lower() in lowered:
                    text = self._rng.choice(bank)
                    break
            if text != _DEFAULT_OPENING:
                break
        return AIResponse(text=text)

    async def generate_text(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        await asyncio.sleep(0.01)
        stage = _detect_stage(prompt)
        if stage in _MOCK_BANKS:
            return self._rng.choice(_MOCK_BANKS[stage])
        if "encouraging them to elaborate" in prompt.lower() or "very short answer" in prompt.lower():
            return self._rng.choice(_MOCK_PROBE)
        return self._rng.choice(_MOCK_BANKS["SIMPLIFICATION"])

    async def probe(self) -> bool:
        return True


def _detect_stage(prompt: str) -> str | None:
    """Extract the stage name from 'Your current task for this stage (STAGE)'."""
    marker = "this stage ("
    idx = prompt.find(marker)
    if idx == -1:
        return None
    rest = prompt[idx + len(marker):]
    end = rest.find(")")
    return rest[:end].upper() if end != -1 else None


# -- Model endpoint protocol --------------------------------------------------


class ModelEndpoint(Protocol):
    """A single (provider, model) pair that can be probed and called."""

    name: str
    provider: str
    model: str

    async def probe(self) -> bool:
        """Return True if this model is up and can serve a request."""
        ...

    async def generate_text(
        self, prompt: str, *, temperature: float = 0.7, max_tokens: int | None = None
    ) -> str:
        ...

    async def generate_response(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AIResponse:
        ...


# -- OpenAI-compatible endpoint (NVIDIA / OpenAI / Ollama) ---------------------


class OpenAIEndpoint:
    """One model served by an OpenAI-compatible endpoint."""

    def __init__(self, settings: Settings, model: str) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover
            raise AIProviderError("The 'openai' package is not installed.") from exc

        kwargs: dict[str, Any] = {
            "api_key": settings.ai_api_key or "local",
            "timeout": settings.ai_timeout_seconds,
            "max_retries": settings.ai_max_retries,
        }
        if settings.ai_base_url:
            kwargs["base_url"] = settings.ai_base_url

        self._client = AsyncOpenAI(**kwargs)
        self._settings = settings
        self.name = f"{settings.ai_provider}:{model}"
        self.provider = settings.ai_provider
        self.model = model

    async def probe(self) -> bool:
        try:
            await self.generate_text("ping", max_tokens=1)
            return True
        except AIProviderError:
            return False

    async def generate_response(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AIResponse:
        try:
            kwargs = {
                "model": self.model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "temperature": temperature,
                "max_tokens": max_tokens or self._settings.ai_max_tokens,
            }
            completion = await self._client.chat.completions.create(**kwargs)
            choice = completion.choices[0]
            return AIResponse(
                text=(choice.message.content or "").strip(),
                finish_reason=choice.finish_reason or "stop",
                usage=completion.usage.model_dump() if completion.usage else None,
            )
        except Exception as exc:  # noqa: BLE001 - convert all SDK errors uniformly
            logger.warning("AI provider error (%s): %s", self.model, exc)
            raise AIProviderError() from exc

    async def generate_text(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        response = await self.generate_response(
            [ChatMessage(role="user", content=prompt)],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.text


# -- Gemini endpoint -----------------------------------------------------------


class GeminiEndpoint:
    """One model served by the Google Gemini Interactions API.

    Uses the latest `/interactions` endpoint with `Api-Revision` header.
    Auth is always `x-goog-api-key` — the key works for both API key (AIza)
    and OAuth token (AQ. / ya29.) values.
    """

    _API_REVISION = "2026-05-20"

    def __init__(self, settings: Settings, model: str) -> None:
        self._settings = settings
        self._base_url = settings.ai_gemini_base_url.rstrip("/")
        self.name = f"gemini:{model}"
        self.provider = "gemini"
        self.model = model

    async def probe(self) -> bool:
        try:
            await self.generate_text("ping", max_tokens=1)
            return True
        except AIProviderError:
            return False

    async def generate_response(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AIResponse:
        import httpx

        # Flatten the conversation into a single input string. The new
        # Interactions API takes a single `input`, not a history array.
        # Role prefixes preserve the conversation structure.
        parts = []
        for m in messages:
            prefix = f"{m.role.upper()}: " if m.role in ("system", "user", "assistant") else ""
            parts.append(f"{prefix}{m.content}")
        input_text = "\n\n".join(parts)

        payload: dict[str, Any] = {
            "model": self.model,
            "input": input_text,
        }
        if max_tokens or temperature != 0.7:
            payload["generation_config"] = {
                "temperature": temperature,
                "max_output_tokens": max_tokens or self._settings.ai_max_tokens,
            }

        headers = _gemini_headers(self._settings)
        try:
            async with httpx.AsyncClient(timeout=self._settings.ai_timeout_seconds) as client:
                resp = await client.post(
                    f"{self._base_url}/interactions",
                    json=payload,
                    headers=headers,
                )
            if resp.status_code >= 400:
                logger.warning(
                    "Gemini error %s (%s): %s",
                    resp.status_code, self.model, resp.text[:300],
                )
                raise AIProviderError()
            data = resp.json()
            text = _extract_gemini_text(data)
            if not text:
                logger.warning(
                    "Gemini returned empty text for model %s (status=%s)",
                    self.model, data.get("status"),
                )
                raise AIProviderError()
            return AIResponse(text=text)
        except AIProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("Gemini provider error (%s): %s", self.model, exc)
            raise AIProviderError() from exc

    async def generate_text(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        response = await self.generate_response(
            [ChatMessage(role="user", content=prompt)],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.text


def _gemini_headers(settings: Settings) -> dict[str, str]:
    key = settings.ai_gemini_api_key
    if not key:
        raise AIProviderError("AI_GEMINI_API_KEY is not configured.")
    # The Interactions API accepts all key types (AIza, AQ., ya29.) via
    # x-goog-api-key — never send Bearer for AQ. tokens.
    return {
        "x-goog-api-key": key,
        "Api-Revision": GeminiEndpoint._API_REVISION,
    }


def _extract_gemini_text(data: dict[str, Any]) -> str:
    """Extract the model's reply from the new Interactions API response.

    The response has a `steps` array; the final `model_output` step carries
    the text content. A `thought` step precedes it.
    """
    try:
        for step in data.get("steps", []):
            if step.get("type") == "model_output":
                content = step.get("content", [])
                texts = [c["text"] for c in content if c.get("type") == "text"]
                if texts:
                    return " ".join(texts)
        return ""
    except (KeyError, IndexError, TypeError):
        return ""


# -- Model router ---------------------------------------------------------------


class ModelRouter(AIProvider):
    """Routes requests to the first working model, starting with NVIDIA.

    No upfront health probing — that added a multi-request delay before the
    first question. Instead we just try models in order (primary NVIDIA models
    first, then Gemini). The first one that succeeds is cached and reused for
    subsequent calls (fast path). If it later fails, we fall through to the
    next model and re-cache.
    """

    name = "router"

    def __init__(self, endpoints: list[ModelEndpoint]) -> None:
        self._endpoints: list[ModelEndpoint] = endpoints
        self._working: ModelEndpoint | None = None

    async def generate_response(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AIResponse:
        # Fast path: reuse the last working model.
        if self._working is not None:
            try:
                return await self._working.generate_response(
                    messages, temperature=temperature, max_tokens=max_tokens
                )
            except AIProviderError:
                logger.warning("Cached model %s failed, re-routing", self._working.name)
                self._working = None

        # Slow path: try each model in order until one works.
        last_exc: Exception | None = None
        for ep in self._endpoints:
            try:
                result = await ep.generate_response(
                    messages, temperature=temperature, max_tokens=max_tokens
                )
                self._working = ep
                logger.info("AI model selected: %s", ep.name)
                return result
            except AIProviderError as exc:
                last_exc = exc
                logger.warning("AI model %s failed, trying next", ep.name)
        logger.warning("All AI models failed")
        raise AIProviderError() from last_exc

    async def generate_text(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        response = await self.generate_response(
            [ChatMessage(role="user", content=prompt)],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.text


# -- Build ---------------------------------------------------------------------


def build_provider(settings: Settings) -> AIProvider:
    provider_name = settings.ai_provider.lower()

    if provider_name == "mock":
        return MockAIProvider(settings)

    endpoints: list[ModelEndpoint] = []

    # Primary provider models (NVIDIA/OpenAI/Ollama) — supports multiple models.
    if provider_name in ("openai", "ollama", "nvidia"):
        for model in settings.ai_model_list:
            if model:
                endpoints.append(OpenAIEndpoint(settings, model))
    elif provider_name == "gemini":
        endpoints.extend(_build_gemini_endpoints(settings))
    else:
        raise AIProviderError(f"Unknown AI provider: {settings.ai_provider}")

    if not endpoints:
        raise AIProviderError(
            f"No models configured for provider '{settings.ai_provider}'. "
            "Set AI_MODELS (comma-separated) in .env."
        )

    # Gemini fallback (always appended when a key is configured, unless the
    # primary provider is already Gemini — otherwise we'd have duplicates).
    if settings.ai_gemini_api_key and provider_name != "gemini":
        endpoints.extend(_build_gemini_endpoints(settings))

    # Fast path: single model, no router needed.
    if len(endpoints) == 1:
        return endpoints[0]

    return ModelRouter(endpoints)


def _build_gemini_endpoints(settings: Settings) -> list[GeminiEndpoint]:
    models = settings.ai_gemini_model_list
    if not models:
        # Default fast models; the router tries them in order and falls through
        # to the first one that works — no blocking network call at build time.
        models = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash"]
    return [GeminiEndpoint(settings, m) for m in models if m]
