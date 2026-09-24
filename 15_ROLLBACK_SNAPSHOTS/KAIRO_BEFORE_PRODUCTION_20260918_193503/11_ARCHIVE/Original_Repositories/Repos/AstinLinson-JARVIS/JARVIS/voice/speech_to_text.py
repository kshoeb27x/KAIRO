"""Speech-to-text provider factory."""

from __future__ import annotations

import logging
from collections.abc import Callable

from JARVIS.config.settings import VoiceSettings
from JARVIS.models.exceptions import InvalidConfigurationError
from JARVIS.models.interfaces import SpeechRecognizer
from JARVIS.voice.microphone import MicrophoneService
from JARVIS.voice.vad import VadSettings, create_vad
from JARVIS.voice.whisper_stt import FasterWhisperSpeechRecognizer


def create_speech_recognizer(
    settings: VoiceSettings,
    logger: logging.Logger,
    *,
    startup_notifier: Callable[[str], None] | None = None,
) -> SpeechRecognizer:
    """Factory for the configured speech recognizer provider."""

    backend = settings.backend.strip().lower()
    if backend != "faster_whisper":
        raise InvalidConfigurationError(f"Unsupported speech backend: {settings.backend}")

    _notify(startup_notifier, "Loading microphone...")
    microphone = MicrophoneService(sample_rate=settings.sample_rate, logger=logger)
    microphone.ensure_available()

    vad_detector = None
    if settings.vad_enabled:
        _notify(startup_notifier, "Loading VAD...")
        vad_detector = create_vad(
            microphone=microphone,
            settings=VadSettings(sample_rate=settings.sample_rate),
            logger=logger,
        )

    _notify(startup_notifier, "Loading Whisper...")
    recognizer = FasterWhisperSpeechRecognizer(
        model_name=settings.whisper_model,
        compute_type=settings.compute_type,
        device=settings.device,
        microphone=microphone,
        vad_detector=vad_detector,
        vad_enabled=settings.vad_enabled,
        logger=logger,
    )
    
    if getattr(settings, "stream_mode", False):
        from JARVIS.voice.streaming import StreamingSpeechRecognizer
        return StreamingSpeechRecognizer(recognizer=recognizer, logger=logger)
        
    return recognizer


def _notify(notifier: Callable[[str], None] | None, message: str) -> None:
    if notifier is not None:
        notifier(message)
