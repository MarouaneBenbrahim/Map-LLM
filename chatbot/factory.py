from __future__ import annotations

from typing import Any, Dict, Optional

from .base import Chatbot


class _UnavailableChatbot:
    def is_available(self) -> bool:
        return False

    async def chat(self, message: str, user_id: str = "web_user") -> Dict[str, Any]:
        return {"text": "No AI system available. Please check configuration.", "type": "error"}


class ManhattanAIChatbotAdapter:
    """Adapter for `ai_chatbot.ManhattanAIChatbot` (sync) to async `Chatbot`."""

    def __init__(self, impl: Any):
        self.impl = impl

    def is_available(self) -> bool:
        return self.impl is not None

    async def chat(self, message: str, user_id: str = "web_user") -> Dict[str, Any]:
        # ai_chatbot is synchronous and returns a dict
        result = self.impl.process_message(message, user_id=user_id)
        if isinstance(result, dict):
            return result
        return {"text": str(result), "type": "response"}


class AsyncChatbotPassthrough:
    """Adapter for chatbots that already implement `async chat()` and `is_available()`."""

    def __init__(self, impl: Any):
        self.impl = impl

    def is_available(self) -> bool:
        return bool(self.impl) and bool(getattr(self.impl, "is_available", lambda: True)())

    async def chat(self, message: str, user_id: str = "web_user") -> Dict[str, Any]:
        out = await self.impl.chat(message, user_id=user_id)
        if isinstance(out, dict):
            return out
        return {"text": str(out), "type": "response"}


def select_chatbot(
    *,
    agentic_chatbot: Optional[Any],
    ultra_chatbot: Optional[Any],
    ai_chatbot: Optional[Any],
) -> Chatbot:
    """Central selection logic for which chatbot to use."""

    if agentic_chatbot is not None:
        try:
            if agentic_chatbot.is_available():
                return AsyncChatbotPassthrough(agentic_chatbot)
        except Exception:
            pass

    if ultra_chatbot is not None:
        # ultra_chatbot exposes async chat()
        return AsyncChatbotPassthrough(ultra_chatbot)

    if ai_chatbot is not None:
        return ManhattanAIChatbotAdapter(ai_chatbot)

    return _UnavailableChatbot()

