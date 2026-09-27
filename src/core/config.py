from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    telegram_token: str
    admin_ids: frozenset[int]
    database_url: str
    debug: bool
    autonomous_mode: bool
    global_cooldown: float
    group_cooldown: float
    user_cooldown: float
    autonomous_budget_per_hour: int
    autonomous_interval: int
    max_history: int
    max_memories: int
    primary_provider: str
    openai_api_key: str | None
    openai_base_url: str
    openai_model: str
    groq_api_key: str | None
    groq_model: str
    gemini_api_key: str | None
    gemini_model: str
    anthropic_api_key: str | None
    anthropic_model: str
    legacy_ai_url: str | None
    image_url: str | None
    multi_search_key: str | None
    multi_search_url: str
    ai_seek_token: str | None
    ai_seek_model: str
    legacy_query_url: str | None
    auto_tts: bool = True
    tts_language: str = "ar"

    @staticmethod
    def load() -> "Settings":
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
        raw_admins = os.getenv("ADMIN_IDS", "")
        admins = frozenset(int(x.strip()) for x in raw_admins.split(",") if x.strip())
        db = os.getenv("DATABASE_URL", str(BASE_DIR / "data" / "nyra.db"))
        if db.startswith("sqlite:///"):
            db = db[10:]
        return Settings(
            telegram_token=token,
            admin_ids=admins,
            database_url=db,
            debug=env_bool("DEBUG"),
            autonomous_mode=env_bool("AUTONOMOUS_MODE", True),
            global_cooldown=float(os.getenv("GLOBAL_COOLDOWN", "2")),
            group_cooldown=float(os.getenv("GROUP_COOLDOWN", "12")),
            user_cooldown=float(os.getenv("USER_COOLDOWN", "3")),
            autonomous_budget_per_hour=int(os.getenv("AUTONOMOUS_BUDGET_PER_HOUR", "6")),
            autonomous_interval=int(os.getenv("AUTONOMOUS_INTERVAL", "60")),
            max_history=int(os.getenv("MAX_HISTORY", "16")),
            max_memories=int(os.getenv("MAX_MEMORIES", "12")),
            primary_provider="supplied",
            openai_api_key=None,
            openai_base_url="",
            openai_model="",
            groq_api_key=None,
            groq_model="",
            gemini_api_key=None,
            gemini_model="",
            anthropic_api_key=None,
            anthropic_model="",
            legacy_ai_url=None,
            image_url=None,
            multi_search_key=None,
            multi_search_url="https://ai-multi-search-backend-321697147922.europe-west6.run.app/ask",
            ai_seek_token=None,
            ai_seek_model="google/gemini-2.5-flash-lite",
            legacy_query_url=None,
            auto_tts=env_bool("AUTO_TTS", True),
            tts_language=os.getenv("TTS_LANGUAGE", "ar"),
        )
