from __future__ import annotations

from typing import Any, Dict, Protocol, runtime_checkable


@runtime_checkable
class Chatbot(Protocol):
    """Minimal interface for chatbot implementations used by the API layer."""

    def is_available(self) -> bool: ...

    async def chat(self, message: str, user_id: str = "web_user") -> Dict[str, Any]: ...

