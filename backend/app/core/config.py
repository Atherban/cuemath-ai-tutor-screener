from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment / .env file.

    No secrets are hardcoded; all values come from configuration.
    Re-reads `.env` on every process start (no caching) so that editing `.env`
    and restarting the server picks up changes immediately.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_name: str = "AI Tutor Screener"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    # --- Server ---
    host: str = "0.0.0.0"
    port: int = 8000

    # --- CORS ---
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # --- Interview behaviour ---
    session_inactivity_timeout_seconds: int = 120
    max_silence_seconds: float = 10.0
    silence_prompt_seconds: float = 5.0
    short_answer_max_words: int = 3
    max_followups_per_stage: int = 1
    max_total_questions: int = 18

    # --- AI provider ---
    ai_provider: str = "mock"  # one of: openai, ollama, nvidia, mock
    ai_model: str = ""
    ai_models: str = ""  # comma-separated list for multi-model support
    ai_api_key: str = ""
    ai_base_url: str = ""
    ai_temperature: float = 0.7
    ai_timeout_seconds: int = 30
    ai_max_retries: int = 1
    ai_max_tokens: int = 1024

    # --- Gemini fallback (used when the primary AI provider fails) ---
    ai_gemini_api_key: str = ""
    ai_gemini_model: str = ""
    ai_gemini_models: str = "gemini-3.7-flash,gemini-2.5-flash"  # comma-separated list; empty = auto-detect
    ai_gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"

    # --- STT ---
    stt_provider: str = "local"
    stt_model: str = "tiny"
    stt_language: str = "en"
    stt_device: str = "cpu"
    stt_compute_type: str = "int8"
    stt_min_audio_bytes: int = 2000

    # --- TTS ---
    tts_provider: str = "edge"
    tts_voice: str = "en-US-AriaNeural"
    tts_rate: str = "+4%"

    # --- Derived ---
    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def ai_model_list(self) -> list[str]:
        """Primary provider models (comma-separated). Falls back to AI_MODEL."""
        if self.ai_models:
            return [m.strip() for m in self.ai_models.split(",") if m.strip()]
        return [self.ai_model.strip()] if self.ai_model.strip() else []

    @property
    def ai_gemini_model_list(self) -> list[str]:
        """Gemini models (comma-separated). Falls back to AI_GEMINI_MODEL."""
        if self.ai_gemini_models:
            return [m.strip() for m in self.ai_gemini_models.split(",") if m.strip()]
        return [self.ai_gemini_model.strip()] if self.ai_gemini_model.strip() else []

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
