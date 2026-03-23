"""
Conversation context management for chatbot sessions.

Stores per-user conversation history so chatbots can maintain context
across turns without each implementation rolling its own storage.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Deque, Dict, List


@dataclass
class Turn:
    """A single user ↔ assistant exchange."""

    user_message: str
    assistant_response: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConversationStore:
    """In-memory conversation history keyed by user ID.

    Keeps at most *max_turns* recent turns per user.
    """

    def __init__(self, max_turns: int = 50):
        self._max_turns = max_turns
        self._histories: Dict[str, Deque[Turn]] = defaultdict(
            lambda: deque(maxlen=max_turns),
        )

    def add_turn(
        self,
        user_id: str,
        user_message: str,
        assistant_response: str,
        **metadata: Any,
    ) -> None:
        self._histories[user_id].append(
            Turn(
                user_message=user_message,
                assistant_response=assistant_response,
                metadata=metadata,
            ),
        )

    def get_history(self, user_id: str, last_n: int = 10) -> List[Turn]:
        """Return the last *last_n* turns for *user_id*."""
        history = self._histories.get(user_id)
        if not history:
            return []
        return list(history)[-last_n:]

    def clear(self, user_id: str) -> None:
        self._histories.pop(user_id, None)
