"""Configurable personality system for assistant responses."""

from __future__ import annotations

from dataclasses import dataclass

from JARVIS.config.settings import PersonalitySettings


@dataclass(frozen=True, slots=True)
class PersonalityProfile:
    """Describes how JARVIS should speak and behave."""

    traits: tuple[str, ...]
    style: str

    def system_prompt(self) -> str:
        """Build the system prompt consumed by language model providers."""

        traits = ", ".join(self.traits)
        return (
            "You are JARVIS, a modular AI operating system assistant. "
            f"Personality traits: {traits}. "
            f"Communication style: {self.style}. "
            "Be concise, practical, calm, and helpful."
        )


class PersonalityManager:
    """Owns the active personality profile and can later support profiles."""

    def __init__(self, profile: PersonalityProfile) -> None:
        self._profile = profile

    @classmethod
    def from_settings(cls, settings: PersonalitySettings) -> "PersonalityManager":
        """Create a manager from configuration."""

        return cls(PersonalityProfile(traits=settings.traits, style=settings.style))

    @property
    def profile(self) -> PersonalityProfile:
        """Return the active personality profile."""

        return self._profile
