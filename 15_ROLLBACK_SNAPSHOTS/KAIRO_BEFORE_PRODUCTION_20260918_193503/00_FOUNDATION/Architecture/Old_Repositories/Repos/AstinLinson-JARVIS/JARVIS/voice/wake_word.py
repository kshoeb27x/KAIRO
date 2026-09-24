"""Wake word detection for JARVIS."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from time import monotonic

from JARVIS.models.exceptions import EmptySpeechError
from JARVIS.models.interfaces import SpeechRecognizer
from JARVIS.voice.events import WakeEventBus


@dataclass(frozen=True, slots=True)
class WakeWordResult:
    """Result produced after wake word detection."""

    detected: bool
    heard_text: str
    command_hint: str = ""


class WakeWordDetector:
    """Receives recognized text from STT and waits for the wake word."""

    def __init__(
        self,
        *,
        wake_word: str,
        recognizer: SpeechRecognizer,
        logger: logging.Logger,
        event_bus: WakeEventBus | None = None,
        debounce_seconds: float = 2.0,
    ) -> None:
        self._wake_word = wake_word.strip()
        self._recognizer = recognizer
        self._logger = logger
        self._event_bus = event_bus
        self._debounce_seconds = debounce_seconds
        self._last_detect_time = 0.0

    def check_text(self, text: str) -> WakeWordResult:
        """Check recognized text for the wake word."""

        pattern = rf"\b{re.escape(self._wake_word)}\b"
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match is None:
            return WakeWordResult(detected=False, heard_text=text)

        command_hint = text[match.end() :].strip(" ,.;:-")
        return WakeWordResult(
            detected=True,
            heard_text=text,
            command_hint=command_hint,
        )

    def wait_for_wake_word(
        self,
        *,
        timeout_seconds: float | None,
        phrase_time_limit_seconds: float | None,
    ) -> WakeWordResult:
        """Block until the configured wake word is heard."""

        while True:
            try:
                heard_text = self._recognizer.listen(
                    timeout_seconds=timeout_seconds,
                    phrase_time_limit_seconds=phrase_time_limit_seconds,
                )
            except EmptySpeechError:
                self._logger.info("Speech event: empty phrase while waiting for wake word.")
                continue

            result = self.check_text(heard_text)
            if result.detected:
                now = monotonic()
                if now - self._last_detect_time > self._debounce_seconds:
                    self._last_detect_time = now
                    self._logger.info("Speech event: wake word detected.")
                    if self._event_bus:
                        self._event_bus.emit(
                            "wake_detected", 
                            text=result.heard_text, 
                            command_hint=result.command_hint
                        )
                    return result
                
                self._logger.debug("Speech event: wake word ignored (debounced).")

            self._logger.info("Speech event: ignored phrase before wake word.")
