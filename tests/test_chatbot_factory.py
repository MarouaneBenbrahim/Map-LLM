"""Tests for chatbot.factory selection logic."""

import asyncio

from chatbot.base import Chatbot
from chatbot.factory import (
    ManhattanAIChatbotAdapter,
    AsyncChatbotPassthrough,
    select_chatbot,
    _UnavailableChatbot,
)


class _FakeSync:
    """Mimics ai_chatbot.ManhattanAIChatbot (synchronous)."""

    def process_message(self, message, user_id="web_user"):
        return {"text": f"sync:{message}", "type": "response"}


class _FakeAsync:
    """Mimics ultra_intelligent_chatbot or agentic_chatbot."""

    def is_available(self):
        return True

    async def chat(self, message, user_id="web_user"):
        return {"text": f"async:{message}", "type": "response"}


class _FakeAsyncUnavailable:
    def is_available(self):
        return False

    async def chat(self, message, user_id="web_user"):
        return {"text": "unreachable", "type": "error"}


def test_select_prefers_agentic():
    bot = select_chatbot(
        agentic_chatbot=_FakeAsync(),
        ultra_chatbot=_FakeAsync(),
        ai_chatbot=_FakeSync(),
    )
    assert isinstance(bot, AsyncChatbotPassthrough)
    assert bot.is_available()


def test_select_falls_back_to_ultra():
    bot = select_chatbot(
        agentic_chatbot=None,
        ultra_chatbot=_FakeAsync(),
        ai_chatbot=_FakeSync(),
    )
    assert isinstance(bot, AsyncChatbotPassthrough)


def test_select_falls_back_to_sync():
    bot = select_chatbot(
        agentic_chatbot=None,
        ultra_chatbot=None,
        ai_chatbot=_FakeSync(),
    )
    assert isinstance(bot, ManhattanAIChatbotAdapter)
    assert bot.is_available()


def test_select_unavailable_when_all_none():
    bot = select_chatbot(
        agentic_chatbot=None,
        ultra_chatbot=None,
        ai_chatbot=None,
    )
    assert isinstance(bot, _UnavailableChatbot)
    assert not bot.is_available()


def test_sync_adapter_chat():
    adapter = ManhattanAIChatbotAdapter(_FakeSync())
    result = asyncio.run(adapter.chat("hello"))
    assert result["text"] == "sync:hello"


def test_async_passthrough_chat():
    pt = AsyncChatbotPassthrough(_FakeAsync())
    result = asyncio.run(pt.chat("ping"))
    assert result["text"] == "async:ping"


def test_unavailable_agentic_skipped():
    bot = select_chatbot(
        agentic_chatbot=_FakeAsyncUnavailable(),
        ultra_chatbot=_FakeAsync(),
        ai_chatbot=None,
    )
    assert isinstance(bot, AsyncChatbotPassthrough)
