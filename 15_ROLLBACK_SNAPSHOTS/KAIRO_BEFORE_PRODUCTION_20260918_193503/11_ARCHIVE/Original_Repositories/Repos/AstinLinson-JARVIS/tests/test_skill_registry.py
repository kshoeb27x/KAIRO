"""Tests for the skill plugin registry."""

from __future__ import annotations

import logging

from JARVIS.models.interfaces import Skill
from JARVIS.models.types import SkillResult
from JARVIS.skills.registry import SkillRegistry


class StatusSkill(Skill):
    """Test skill that handles status commands."""

    @property
    def name(self) -> str:
        return "status"

    @property
    def description(self) -> str:
        return "Reports status."

    def can_handle(self, command: str) -> bool:
        return command.lower() == "status"

    def handle(self, command: str) -> SkillResult:
        del command
        return SkillResult(content="Online.")


def test_registry_routes_to_registered_skill() -> None:
    registry = SkillRegistry(logging.getLogger("test"))
    registry.register(StatusSkill())

    result = registry.handle("status")

    assert result is not None
    assert result.content == "Online."


def test_registry_returns_none_when_no_skill_can_handle_command() -> None:
    registry = SkillRegistry(logging.getLogger("test"))
    registry.register(StatusSkill())

    result = registry.handle("unknown command")

    assert result is None
