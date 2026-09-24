"""Abstract interfaces for replaceable JARVIS subsystems."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from JARVIS.models.types import Message, SkillResult


class SpeechRecognizer(ABC):
    """Converts spoken input into text.

    Implementations may use cloud speech APIs, local engines, typed console
    input, or future hotword-capable audio streams. The conversation loop only
    depends on this interface.
    """

    @abstractmethod
    def listen(
        self,
        *,
        timeout_seconds: float | None = None,
        phrase_time_limit_seconds: float | None = None,
    ) -> str:
        """Capture one phrase and return recognized text."""


class SpeechSynthesizer(ABC):
    """Converts assistant text into spoken audio."""

    @abstractmethod
    def speak(self, text: str) -> None:
        """Speak text to the user."""


class LanguageModel(ABC):
    """Generates assistant responses from structured conversation messages."""

    @abstractmethod
    def generate(
        self,
        messages: Sequence[Message],
        *,
        timeout_seconds: float | None = None,
    ) -> str:
        """Return an assistant response for the supplied messages."""


class MemoryStore(ABC):
    """Stores conversation messages behind a replaceable persistence boundary."""

    @abstractmethod
    def add(self, message: Message) -> None:
        """Persist a message."""

    @abstractmethod
    def recent(self, *, limit: int | None = None) -> Sequence[Message]:
        """Return recent messages in chronological order."""

    @abstractmethod
    def clear(self) -> None:
        """Delete stored messages."""


class Skill(ABC):
    """A plugin capability that can handle selected user commands."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique skill name."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable skill description."""

    @abstractmethod
    def can_handle(self, command: str) -> bool:
        """Return True when this skill can handle the command."""

    @abstractmethod
    def handle(self, command: str) -> SkillResult:
        """Handle a command and return a skill result."""
