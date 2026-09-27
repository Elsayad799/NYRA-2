from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol

@dataclass
class AIResult:
    text: str
    provider: str
    model: str
    latency_ms: int

class Provider(Protocol):
    name: str
    model: str
    def generate(self, messages: list[dict], system: str | None = None, max_tokens: int = 900) -> AIResult: ...
