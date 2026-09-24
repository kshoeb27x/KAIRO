"""Voice activity detection for microphone recording.

Two concrete implementations are provided:

* ``VoiceActivityDetector`` – uses the ``webrtcvad`` C extension for
  precise, low-latency frame classification.  This is the preferred mode.
* ``FallbackVAD`` – pure-Python, RMS energy-based classification.  Used
  automatically when ``webrtcvad`` cannot be imported (e.g. missing C++
  Build Tools on Windows / Python 3.14+).

Use ``create_vad()`` to obtain the correct implementation for the current
environment without touching any call-site code.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

from JARVIS.models.exceptions import EmptySpeechError, InvalidConfigurationError
from JARVIS.voice.microphone import AudioSamples, MicrophoneService

# ---------------------------------------------------------------------------
# Availability probe – performed once at import time, zero side-effects
# ---------------------------------------------------------------------------

try:
    import webrtcvad as _webrtcvad_mod

    WEBRTCVAD_AVAILABLE: bool = True
except Exception:  # ImportError or any compile-time OSError on Windows
    _webrtcvad_mod = None  # type: ignore[assignment]
    WEBRTCVAD_AVAILABLE = False


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class VadSettings:
    """Runtime controls for voice activity detection (both modes)."""

    sample_rate: int
    frame_duration_ms: int = 30
    aggressiveness: int = 2
    pre_speech_padding_ms: int = 300
    silence_duration_ms: int = 800
    speech_start_frames: int = 2
    # FallbackVAD only: RMS amplitude threshold (0.0–1.0 float32 scale).
    # Frames whose RMS exceeds this value are classified as speech.
    fallback_energy_threshold: float = 0.01


# ---------------------------------------------------------------------------
# Abstract base – shared recording state machine
# ---------------------------------------------------------------------------


class _BaseVAD(ABC):
    """Shared recording state machine used by both VAD implementations.

    Subclasses must implement :meth:`is_speech` and :meth:`_validate`.
    """

    def __init__(
        self,
        *,
        microphone: MicrophoneService,
        settings: VadSettings,
        logger: logging.Logger,
    ) -> None:
        self._microphone = microphone
        self._settings = settings
        self._logger = logger
        self._validate()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_until_silence(self, *, timeout_seconds: float | None = None) -> AudioSamples:
        """Record until speech starts and then stops after trailing silence.

        The algorithm:
        1. Accumulate frames in a rolling pre-speech buffer.
        2. Once ``speech_start_frames`` consecutive speech frames are seen,
           flush the buffer into ``speech_frames`` and mark *started*.
        3. After *started*, append every frame; count consecutive silence
           frames.  Stop when silence reaches the configured threshold.
        4. Trim the trailing silence frames from the result before returning.
        """

        deadline = monotonic() + timeout_seconds if timeout_seconds is not None else None
        padding_frames = max(
            1,
            self._settings.pre_speech_padding_ms // self._settings.frame_duration_ms,
        )
        silence_frames_required = max(
            1,
            self._settings.silence_duration_ms // self._settings.frame_duration_ms,
        )

        pending_frames: deque[AudioSamples] = deque(maxlen=padding_frames)
        speech_frames: list[AudioSamples] = []
        started = False
        speech_start_count = 0
        silence_count = 0

        for frame in self._microphone.iter_audio_frames(
            frame_duration_ms=self._settings.frame_duration_ms
        ):
            is_speech = self.is_speech(frame)

            if not started:
                pending_frames.append(frame)
                speech_start_count = speech_start_count + 1 if is_speech else 0
                if speech_start_count >= self._settings.speech_start_frames:
                    started = True
                    speech_frames.extend(pending_frames)
                    pending_frames.clear()
                    self._logger.info("Speech event: voice activity started.")
                    continue

                if deadline is not None and monotonic() >= deadline:
                    raise EmptySpeechError("Timed out waiting for speech.")
                continue

            speech_frames.append(frame)
            silence_count = 0 if is_speech else silence_count + 1
            if silence_count >= silence_frames_required:
                self._logger.info("Speech event: voice activity ended after silence.")
                break

        if not speech_frames:
            raise EmptySpeechError("No speech was detected.")

        # Trim trailing silence that was accumulated before the stop condition
        if silence_count > 0 and len(speech_frames) > silence_count:
            speech_frames = speech_frames[:-silence_count]

        audio = self._microphone.concatenate(speech_frames)
        if len(audio) == 0:
            raise EmptySpeechError("Voice activity detector returned empty audio.")
        return audio

    @abstractmethod
    def is_speech(self, frame: AudioSamples) -> bool:
        """Return True when *frame* is classified as containing speech."""

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @abstractmethod
    def _validate(self) -> None:
        """Raise ``InvalidConfigurationError`` if settings are inconsistent."""


# ---------------------------------------------------------------------------
# Primary implementation – webrtcvad
# ---------------------------------------------------------------------------


class VoiceActivityDetector(_BaseVAD):
    """Records speech using the WebRTC VAD C extension (highest accuracy).

    Requires ``webrtcvad`` to be installed.  On Python 3.14+ / Windows you
    may need Microsoft C++ Build Tools; see ``requirements.txt`` for details.
    """

    def __init__(
        self,
        *,
        microphone: MicrophoneService,
        settings: VadSettings,
        logger: logging.Logger,
    ) -> None:
        super().__init__(microphone=microphone, settings=settings, logger=logger)
        # _validate() is called in super().__init__; _vad is set afterwards
        self._vad: Any = self._create_webrtc_vad()

    # ------------------------------------------------------------------
    # _BaseVAD protocol
    # ------------------------------------------------------------------

    def is_speech(self, frame: AudioSamples) -> bool:
        """Return True when WebRTC VAD classifies *frame* as speech."""

        pcm16 = self._microphone.to_pcm16(frame)
        try:
            return bool(self._vad.is_speech(pcm16, self._settings.sample_rate))
        except Exception as exc:
            message = "WebRTC VAD could not process the audio frame."
            raise InvalidConfigurationError(message) from exc

    def _validate(self) -> None:
        if self._settings.sample_rate != 16_000:
            raise InvalidConfigurationError("WebRTC VAD is configured for 16000 Hz audio.")
        if self._settings.frame_duration_ms not in {10, 20, 30}:
            raise InvalidConfigurationError("WebRTC VAD frame duration must be 10, 20, or 30 ms.")
        if not 0 <= self._settings.aggressiveness <= 3:
            raise InvalidConfigurationError("WebRTC VAD aggressiveness must be between 0 and 3.")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _create_webrtc_vad(self) -> Any:
        if not WEBRTCVAD_AVAILABLE or _webrtcvad_mod is None:
            raise InvalidConfigurationError(
                "webrtcvad is not installed.  Use create_vad() to get the appropriate "
                "implementation for this environment, or install webrtcvad manually."
            )
        return _webrtcvad_mod.Vad(self._settings.aggressiveness)


# ---------------------------------------------------------------------------
# Fallback implementation – energy-based (pure Python / numpy)
# ---------------------------------------------------------------------------


class FallbackVAD(_BaseVAD):
    """Energy-threshold VAD that works without any C extension.

    Each 30 ms audio frame is classified as speech when its RMS amplitude
    (computed over the float32 samples in [-1.0, 1.0]) exceeds
    ``settings.fallback_energy_threshold``.

    This mode is activated automatically by ``create_vad()`` when
    ``webrtcvad`` cannot be imported.
    """

    def is_speech(self, frame: AudioSamples) -> bool:
        """Return True when the frame RMS exceeds the configured threshold."""

        try:
            import numpy as np  # noqa: PLC0415
        except ImportError as exc:
            raise InvalidConfigurationError(
                "Install numpy to use the fallback energy VAD."
            ) from exc

        samples = np.asarray(frame, dtype=np.float32)
        if samples.size == 0:
            return False
        rms = float(np.sqrt(np.mean(samples ** 2)))
        return rms > self._settings.fallback_energy_threshold

    def _validate(self) -> None:
        # The fallback works at any sample rate / frame duration since it only
        # performs numpy arithmetic.  We still surface obviously wrong configs.
        if self._settings.sample_rate <= 0:
            raise InvalidConfigurationError("sample_rate must be a positive integer.")
        if self._settings.frame_duration_ms not in {10, 20, 30}:
            raise InvalidConfigurationError(
                "Fallback VAD frame duration must be 10, 20, or 30 ms."
            )
        if not 0.0 <= self._settings.fallback_energy_threshold <= 1.0:
            raise InvalidConfigurationError(
                "fallback_energy_threshold must be in [0.0, 1.0]."
            )


# ---------------------------------------------------------------------------
# Factory – auto-selects the best available implementation
# ---------------------------------------------------------------------------


def create_vad(
    *,
    microphone: MicrophoneService,
    settings: VadSettings,
    logger: logging.Logger,
) -> _BaseVAD:
    """Return the best VAD implementation for the current environment.

    Decision logic
    --------------
    * If ``webrtcvad`` imported successfully → ``VoiceActivityDetector``.
    * Otherwise → ``FallbackVAD`` (energy-threshold, pure Python).

    In both cases the returned object exposes the same
    :meth:`_BaseVAD.record_until_silence` / :meth:`_BaseVAD.is_speech` API
    so all call-sites remain unchanged.
    """

    logger.info("webrtcvad available: %s", str(WEBRTCVAD_AVAILABLE).lower())

    if WEBRTCVAD_AVAILABLE:
        return VoiceActivityDetector(microphone=microphone, settings=settings, logger=logger)

    logger.warning(
        "webrtcvad is not available (missing C extension). "
        "Using fallback VAD mode (energy-threshold). "
        "Install Microsoft C++ Build Tools then `pip install webrtcvad` for best accuracy."
    )
    return FallbackVAD(microphone=microphone, settings=settings, logger=logger)
