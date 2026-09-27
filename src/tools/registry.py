from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any

@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    handler: Callable[..., Any]
    enabled: bool = True

class ToolRegistry:
    def __init__(self): self._tools: dict[str, Tool] = {}
    def register(self, name: str, description: str, handler: Callable[..., Any], enabled: bool=True):
        if not name or not callable(handler): raise ValueError("Invalid tool")
        self._tools[name] = Tool(name, description, handler, enabled)
    def get(self, name: str): return self._tools.get(name)
    def list(self): return [t for t in self._tools.values() if t.enabled]
    def describe(self): return "\n".join(f"- {t.name}: {t.description}" for t in self.list())
    def call(self, name: str, **kwargs):
        tool=self.get(name)
        if not tool or not tool.enabled: raise PermissionError(f"Tool not allowed: {name}")
        return tool.handler(**kwargs)
