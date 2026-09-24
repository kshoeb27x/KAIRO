"""Streaming response layer for the JARVIS voice pipeline."""

from __future__ import annotations

import logging
from collections.abc import Iterator

from JARVIS.models.interfaces import SpeechRecognizer


class StreamingSpeechRecognizer(SpeechRecognizer):
    """Wraps an existing speech recognizer to add streaming capabilities.

    Maintains backward compatibility with the `listen()` interface, but allows
    consumers to optionally consume partial transcriptions via `listen_stream()`.
    """

    def __init__(
        self,
        *,
        recognizer: SpeechRecognizer,
        logger: logging.Logger,
    ) -> None:
        self._recognizer = recognizer
        self._logger = logger

    def listen(
        self,
        *,
        timeout_seconds: float | None = None,
        phrase_time_limit_seconds: float | None = None,
    ) -> str:
        """Block and return the final recognized text (backward compatible)."""

        self._logger.info("StreamingSpeechRecognizer: falling back to blocking listen().")
        return self._recognizer.listen(
            timeout_seconds=timeout_seconds,
            phrase_time_limit_seconds=phrase_time_limit_seconds,
        )

    def listen_stream(
        self,
        *,
        timeout_seconds: float | None = None,
        phrase_time_limit_seconds: float | None = None,
    ) -> Iterator[str]:
        """Yield partial text chunks as they are recognized.
        
        Currently a placeholder that yields the final result as a single chunk,
        since the underlying Whisper implementation in v0.1 does not yet expose
        incremental decoding to the STT interface. Future upgrades can plug 
        incremental logic here.
        """

        self._logger.info("StreamingSpeechRecognizer: listen_stream() called.")
        
        # In a real streaming Whisper implementation, this would yield partial
        # segments as they are decoded. Since FasterWhisperSpeechRecognizer currently
        # returns the final string, we yield it as a single chunk for now to establish
        # the architectural pattern.
        
        final_text = self._recognizer.listen(
            timeout_seconds=timeout_seconds,
            phrase_time_limit_seconds=phrase_time_limit_seconds,
        )
        
        # Example of how early intent detection might hook into partials:
        # if _detect_early_intent(partial_text): yield partial_text
        
        yield final_text
