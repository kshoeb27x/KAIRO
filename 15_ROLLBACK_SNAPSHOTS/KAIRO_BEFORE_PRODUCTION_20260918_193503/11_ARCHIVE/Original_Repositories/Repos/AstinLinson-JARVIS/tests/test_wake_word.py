"""Tests for wake word detection."""

from __future__ import annotations

import logging

from JARVIS.models.exceptions import EmptySpeechError
from JARVIS.models.interfaces import SpeechRecognizer
from JARVIS.voice.wake_word import WakeWordDetector


class FakeRecognizer(SpeechRecognizer):
    """Recognizer test double that returns queued phrases."""

    def __init__(self, phrases: list[str]) -> None:
        self._phrases = phrases

    def listen(
        self,
        *,
        timeout_seconds: float | None = None,
        phrase_time_limit_seconds: float | None = None,
    ) -> str:
        del timeout_seconds, phrase_time_limit_seconds
        if not self._phrases:
            raise EmptySpeechError("No more phrases.")
        return self._phrases.pop(0)


def test_wake_word_detector_extracts_command_hint() -> None:
    recognizer = FakeRecognizer(["Jarvis list skills"])
    detector = WakeWordDetector(
        wake_word="Jarvis",
        recognizer=recognizer,
        logger=logging.getLogger("test"),
    )

    result = detector.wait_for_wake_word(timeout_seconds=1.0, phrase_time_limit_seconds=1.0)

    assert result.detected is True
    assert result.command_hint == "list skills"


def test_wake_word_detector_ignores_phrases_before_wake_word() -> None:
    recognizer = FakeRecognizer(["hello there", "Jarvis help"])
    detector = WakeWordDetector(
        wake_word="Jarvis",
        recognizer=recognizer,
        logger=logging.getLogger("test"),
    )

    result = detector.wait_for_wake_word(timeout_seconds=1.0, phrase_time_limit_seconds=1.0)

    assert result.heard_text == "Jarvis help"
