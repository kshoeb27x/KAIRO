"""Built-in utility skills shipped with JARVIS v0.1."""

from __future__ import annotations

from JARVIS.models.interfaces import Skill
from JARVIS.models.types import SkillResult
from JARVIS.skills.registry import SkillRegistry


class HelpSkill(Skill):
    """Lists registered skills when the user asks for capabilities."""

    def __init__(self, registry: SkillRegistry) -> None:
        self._registry = registry

    @property
    def name(self) -> str:
        """Unique skill name."""

        return "help"

    @property
    def description(self) -> str:
        """Human-readable skill description."""

        return "Lists available skills."

    def can_handle(self, command: str) -> bool:
        """Return True when the command asks about available skills."""

        normalized = command.strip().lower()
        return normalized in {"help", "what can you do", "list skills", "skills"}

    def handle(self, command: str) -> SkillResult:
        """Return a concise list of registered skills."""

        skills = ", ".join(skill.name for skill in self._registry.all())
        return SkillResult(content=f"Available skills: {skills}.")


def register_builtin_skills(registry: SkillRegistry) -> None:
    """Register skills that are part of the core distribution."""

    registry.register(HelpSkill(registry))
