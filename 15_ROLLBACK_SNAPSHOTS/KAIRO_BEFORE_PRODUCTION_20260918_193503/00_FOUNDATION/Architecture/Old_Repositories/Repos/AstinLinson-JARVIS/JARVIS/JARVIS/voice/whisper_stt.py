"""Faster-Whisper speech-to-text provider."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any, Protocol

from JARVIS.models.exceptions import EmptySpeechError, InvalidConfigurationError
from JARVIS.models.interfaces import SpeechRecognizer
from JARVIS.voice.microphone import AudioSamples, MicrophoneService
from JARVIS.voice.vad import _BaseVAD


class WhisperModelProtocol(Protocol):
    """Subset of the Faster-Whisper model API used by JARVIS."""

    def transcribe(self, audio: AudioSamples, **kwargs: Any) -> tuple[Iterable[Any], Any]:
        """Transcribe one audio array and return segment objects."""


class FasterWhisperSpeechRecognizer(SpeechRecognizer):
    """Speech recognizer that records local audio and transcribes it with Whisper."""

    _SUPPORTED_MODELS = {"tiny", "base", "small"}

    def __init__(
        self,
        *,
        model_name: str,
        compute_type: str,
        device: str,
        microphone: MicrophoneService,
        vad_detector: _BaseVAD | None,
        vad_enabled: bool,
        logger: logging.Logger,
        model: WhisperModelProtocol | None = None,
    ) -> None:
        self._model_name = model_name.strip().lower()
        self._compute_type = compute_type.strip()
        self._device = device.strip().lower()
        self._current_device = self._device
        self._microphone = microphone
        self._vad_detector = vad_detector
        self._vad_enabled = vad_enabled
        self._logger = logger
        self._validate()
        self._model = model if model is not None else self._load_model()

    def listen(
        self,
        *,
        timeout_seconds: float | None = None,
        phrase_time_limit_seconds: float | None = None,
    ) -> str:
        """Record one spoken phrase and return recognized text."""

        self._logger.info("Speech event: listening with Faster-Whisper.")
        audio = self._record_audio(
            timeout_seconds=timeout_seconds,
            phrase_time_limit_seconds=phrase_time_limit_seconds,
        )
        text = self._transcribe(audio)
        if not text:
            raise EmptySpeechError("Whisper returned empty speech text.")

        self._logger.info("Speech event: recognized text.")
        return text

    def _record_audio(
        self,
        *,
        timeout_seconds: float | None,
        phrase_time_limit_seconds: float | None,
    ) -> AudioSamples:
        if self._vad_enabled:
            if self._vad_detector is None:
                message = "VAD is enabled but no VAD detector was configured."
                raise InvalidConfigurationError(message)
            return self._vad_detector.record_until_silence(timeout_seconds=timeout_seconds)

        if phrase_time_limit_seconds is None:
            raise InvalidConfigurationError("Set a phrase time limit when VAD is disabled.")
        return self._microphone.record_for_duration(duration_seconds=phrase_time_limit_seconds)

    def _transcribe(self, audio: AudioSamples) -> str:
        try:
            return self._do_transcribe(audio)
        except Exception as exc:
            if self._device == "auto" and self._current_device == "cuda":
                self._logger.warning("CUDA verification failed. (%s)", exc)
                self._logger.info("Falling back to CPU.")
                
                # Unload CUDA model
                self._model = None
                
                # Recreate on CPU
                try:
                    from faster_whisper import WhisperModel
                    self._model = WhisperModel(self._model_name, device="cpu", compute_type="int8")
                    self._current_device = "cpu"
                    self._logger.info("CPU Whisper initialized successfully.")
                except Exception as fallback_exc:
                    raise InvalidConfigurationError("Unable to load the Faster-Whisper model on CPU fallback.") from fallback_exc
                
                # Retry once
                return self._do_transcribe(audio)
            
            if self._device == "cuda":
                raise InvalidConfigurationError(f"CUDA transcription failed: {exc}") from exc
                
            raise

    def _do_transcribe(self, audio: AudioSamples) -> str:
        segments, _info = self._model.transcribe(
            audio,
            beam_size=5,
            vad_filter=False,
        )
        text_parts = [
            str(getattr(segment, "text", "")).strip()
            for segment in segments
            if str(getattr(segment, "text", "")).strip()
        ]
        return " ".join(text_parts).strip()

    def _validate(self) -> None:
        if self._model_name not in self._SUPPORTED_MODELS:
            supported = ", ".join(sorted(self._SUPPORTED_MODELS))
            raise InvalidConfigurationError(f"Whisper model must be one of: {supported}.")
        if not self._compute_type:
            raise InvalidConfigurationError("Whisper compute_type must not be empty.")

    def _load_model(self) -> WhisperModelProtocol:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise InvalidConfigurationError(
                "Install faster-whisper to use the Faster-Whisper STT backend."
            ) from exc

        # Determine target device and compute type
        target_device = self._device
        target_compute = self._compute_type

        if target_device == "auto":
            try:
                import ctranslate2
                if ctranslate2.get_cuda_device_count() > 0:
                    target_device = "cuda"
                else:
                    target_device = "cpu"
                    target_compute = "int8"
            except ImportError:
                target_device = "cpu"
                target_compute = "int8"
                
        self._current_device = target_device

        try:
            if target_device == "cuda":
                self._logger.info("Initializing Whisper on CUDA...")
            else:
                self._logger.info("Initializing Whisper on %s with compute_type=%s", target_device, target_compute)
            
            return WhisperModel(self._model_name, device=target_device, compute_type=target_compute)
        except Exception as exc:
            if self._device == "auto" and target_device == "cuda":
                self._logger.warning("CUDA verification failed during initialization (%s).", exc)
                self._logger.info("Falling back to CPU.")
                try:
                    self._current_device = "cpu"
                    model = WhisperModel(self._model_name, device="cpu", compute_type="int8")
                    self._logger.info("CPU Whisper initialized successfully.")
                    return model
                except Exception as cpu_exc:
                    raise InvalidConfigurationError(
                        "Unable to load the Faster-Whisper model on CPU fallback."
                    ) from cpu_exc
            
            if self._device == "cuda":
                raise InvalidConfigurationError(f"CUDA initialization failed: {exc}") from exc
                
            raise InvalidConfigurationError(
                "Unable to load the Faster-Whisper model. Check the model name, "
                "compute type, and model cache."
            ) from exc
