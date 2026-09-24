"""Tests for the brain router."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from JARVIS.brain.memory_manager import InMemoryConversationMemory, MemoryManager
from JARVIS.brain.personality import PersonalityManager, PersonalityProfile
from JARVIS.brain.planner import Planner
from JARVIS.brain.router import BrainRouter
from JARVIS.models.interfaces import LanguageModel
from JARVIS.models.types import Message
from JARVIS.skills.registry import SkillRegistry


class FakeLanguageModel(LanguageModel):
    """Language model test double."""

    def generate(
        self,
        messages: Sequence[Message],
        *,
        timeout_seconds: float | None = None,
    ) -> str:
        del messages, timeout_seconds
        return "Acknowledged."


def test_brain_router_records_user_and_assistant_messages() -> None:
    memory_manager = MemoryManager(InMemoryConversationMemory(max_messages=10))
    router = BrainRouter(
        language_model=FakeLanguageModel(),
        memory_manager=memory_manager,
        personality_manager=PersonalityManager(
            PersonalityProfile(traits=("Helpful",), style="concise")
        ),
        planner=Planner(),
        skill_registry=SkillRegistry(logging.getLogger("test")),
        llm_timeout_seconds=5.0,
        logger=logging.getLogger("test"),
    )

    response = router.process("status report")

    messages = memory_manager.recent_messages()
    assert response == "Acknowledged."
    assert [message.role for message in messages] == ["user", "assistant"]
