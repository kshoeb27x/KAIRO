"""Text-to-speech providers."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

from JARVIS.config.settings import VoiceSettings
from JARVIS.models.exceptions import InvalidConfigurationError, SpeechSynthesisError
from JARVIS.models.interfaces import SpeechSynthesizer

# Absolute path to the worker script that runs pyttsx3 in its own Python process.
# Using subprocess.run instead of multiprocessing avoids the Windows "bootstrapping
# phase" RuntimeError that occurs when the parent process was not entered via
# `if __name__ == '__main__'`.
_TTS_WORKER = str(Path(__file__).with_name("tts_worker.py"))


class ConsoleSpeechSynthesizer(SpeechSynthesizer):
    """Development synthesizer that writes responses to the terminal."""

    def speak(self, text: str) -> None:
        """Print text instead of speaking it."""

        print(f"JARVIS: {text}")


class Pyttsx3SpeechSynthesizer(SpeechSynthesizer):
    """Offline speech synthesizer using system voices through pyttsx3.

    Each call to speak() launches a fresh Python subprocess via subprocess.run().
    This completely isolates the SAPI5/COM state from the parent process, preventing
    the silent-audio bug where sounddevice's WASAPI exclusive access corrupts the
    COM apartment and causes runAndWait() to exit prematurely without playing audio.
    Using subprocess.run() rather than multiprocessing.Process avoids the Windows
    'bootstrapping phase' RuntimeError that multiprocessing spawning produces when
    the parent was not entered via `if __name__ == '__main__'`.
    """

    def __init__(self, *, voice_hint: str, rate: int, logger: logging.Logger) -> None:
        self._voice_hint = voice_hint.strip().lower()
        self._rate = rate
        self._logger = logger

    def speak(self, text: str) -> None:
        """Speak text using an isolated subprocess to prevent COM state corruption."""
        if not text.strip():
            return

        # ── DIAGNOSTIC: inspect exactly what arrives at TTS ───────────────────
        self._logger.info("[TTS INPUT] length=%d\n%s", len(text), text)
        non_printable = [
            f"U+{ord(c):04X} at index {i}"
            for i, c in enumerate(text)
            if not c.isprintable() and c not in ("\n", "\r", "\t")
        ]
        if non_printable:
            self._logger.warning("[TTS INPUT] Non-printable chars: %s", non_printable)
        try:
            text.encode("utf-8")
            self._logger.info("[TTS INPUT] UTF-8 encoding: OK")
        except UnicodeEncodeError as enc_err:
            self._logger.error("[TTS INPUT] UTF-8 encoding FAILED: %s", enc_err)
        # ──────────────────────────────────────────────────────────────────────

        try:
            result = subprocess.run(
                [sys.executable, _TTS_WORKER, text, self._voice_hint, str(self._rate)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                self._logger.error(
                    "TTS worker exited with code %d. stderr: %s",
                    result.returncode,
                    result.stderr,
                )
                raise SpeechSynthesisError(
                    f"Speech synthesis process exited with code {result.returncode}"
                )
            if result.stderr:
                # Worker writes diagnostic lines to stderr — forward at DEBUG level
                for line in result.stderr.strip().splitlines():
                    self._logger.debug("[TTS_WORKER] %s", line)
        except FileNotFoundError as exc:
            raise SpeechSynthesisError(
                f"TTS worker script not found: {_TTS_WORKER}"
            ) from exc
        except Exception as exc:
            self._logger.exception("Speech synthesis failed.")
            raise SpeechSynthesisError("Speech synthesis failed.") from exc


def create_speech_synthesizer(settings: VoiceSettings, logger: logging.Logger) -> SpeechSynthesizer:
    """Factory for the configured speech synthesizer provider."""

    provider = settings.speech_synthesizer.strip().lower()
    if provider == "console":
        return ConsoleSpeechSynthesizer()
    if provider == "pyttsx3":
        return Pyttsx3SpeechSynthesizer(
            voice_hint=settings.tts_voice_hint,
            rate=settings.tts_rate,
            logger=logger,
        )
    message = f"Unsupported speech synthesizer: {settings.speech_synthesizer}"
    raise InvalidConfigurationError(message)
