"""Tests for conversation memory."""

from __future__ import annotations

from JARVIS.brain.memory_manager import InMemoryConversationMemory, MemoryManager


def test_memory_manager_records_recent_messages() -> None:
    store = InMemoryConversationMemory(max_messages=4)
    manager = MemoryManager(store)

    manager.add_user_message("Hello")
    manager.add_assistant_message("Good evening.")

    messages = manager.recent_messages()

    assert [message.role for message in messages] == ["user", "assistant"]
    assert messages[0].content == "Hello"


def test_in_memory_store_respects_message_limit() -> None:
    store = InMemoryConversationMemory(max_messages=2)
    manager = MemoryManager(store)

    manager.add_user_message("one")
    manager.add_assistant_message("two")
    manager.add_user_message("three")

    messages = manager.recent_messages()

    assert [message.content for message in messages] == ["two", "three"]
