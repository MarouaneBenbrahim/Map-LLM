"""
Chatbot package.

Exposes the ``Chatbot`` protocol, the ``select_chatbot`` factory, and
submodules for intent handling and conversation context.
"""

from .base import Chatbot
from .factory import select_chatbot

__all__ = ["Chatbot", "select_chatbot"]
