from __future__ import annotations
import logging
from src.providers.source_ai import MultiSearchProvider, AISeekProvider
from src.providers.private_credentials import (
    MULTI_SEARCH_FIREBASE_KEY, AI_SEEK_ACCESS_TOKEN,
)

log = logging.getLogger("AI")


class ProviderManager:
    """Internal AI source router. No provider/API key is requested from the user.

    The credentials/endpoints here come from the AI source files supplied with
    the project. The Telegram bot token is the only runtime secret the user
    needs to provide.
    """

    def __init__(self, settings):
        self.providers = [
            MultiSearchProvider(
                MULTI_SEARCH_FIREBASE_KEY,
                settings.multi_search_url,
                ["gemini", "openai", "deepseek", "claude", "perplexity", "llama"],
            ),
            AISeekProvider(AI_SEEK_ACCESS_TOKEN, settings.ai_seek_model),
        ]

    def generate(self, messages, system=None, max_tokens=900):
        errors = []
        for source in self.providers:
            try:
                result = source.generate(messages, system, max_tokens)
                log.info("ai_source=%s model=%s latency_ms=%s", result.provider, result.model, result.latency_ms)
                return result
            except Exception as exc:
                errors.append(f"{source.name}: {exc}")
                log.exception("AI source failed: %s", source.name)
        raise RuntimeError("All supplied AI sources failed: " + " | ".join(errors))
