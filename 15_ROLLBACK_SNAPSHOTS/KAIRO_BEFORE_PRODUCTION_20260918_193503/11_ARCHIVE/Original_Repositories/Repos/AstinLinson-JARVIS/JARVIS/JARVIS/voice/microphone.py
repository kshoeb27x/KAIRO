"""Microphone capture service based on sounddevice."""

from __future__ import annotations

import logging
from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING, Any

from JARVIS.models.exceptions import EmptySpeechError, MicrophoneUnavailableError

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray

    AudioSamples = NDArray[np.float32]
else:
    AudioSamples = Any


class MicrophoneService:
    """Captures mono 16 kHz float32 audio frames from the default microphone."""

    def __init__(self, *, sample_rate: int, logger: logging.Logger) -> None:
        self._sample_rate = sample_rate
        self._channels = 1
        self._dtype = "float32"
        self._logger = logger
        self._sounddevice: Any | None = None
        self._numpy: Any | None = None

    @property
    def sample_rate(self) -> int:
        """Return the configured sample rate."""

        return self._sample_rate

    def ensure_available(self) -> None:
        """Verify that sounddevice can see an input device."""

        sounddevice = self._load_sounddevice()
        try:
            sounddevice.query_devices(kind="input")
        except Exception as exc:
            message = "No usable microphone input device was found."
            raise MicrophoneUnavailableError(message) from exc

    def iter_audio_frames(self, *, frame_duration_ms: int) -> Iterator[AudioSamples]:
        """Yield live microphone audio frames as mono float32 numpy arrays."""

        frame_size = self.frame_size(frame_duration_ms)
        sounddevice = self._load_sounddevice()

        try:
            with sounddevice.InputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype=self._dtype,
                blocksize=frame_size,
            ) as stream:
                while True:
                    data, overflowed = stream.read(frame_size)
                    if overflowed:
                        self._logger.warning("Microphone input overflow detected.")
                    yield self._to_mono_float32(data)
        except MicrophoneUnavailableError:
            raise
        except Exception as exc:
            raise MicrophoneUnavailableError("Microphone capture failed.") from exc

    def record_for_duration(self, *, duration_seconds: float) -> AudioSamples:
        """Record a bounded clip when VAD is explicitly disabled."""

        if duration_seconds <= 0:
            raise EmptySpeechError("Recording duration must be positive.")

        frame_count = int(self._sample_rate * duration_seconds)
        sounddevice = self._load_sounddevice()

        try:
            recording = sounddevice.rec(
                frame_count,
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype=self._dtype,
            )
            sounddevice.wait()
        except Exception as exc:
            raise MicrophoneUnavailableError("Microphone capture failed.") from exc

        return self._to_mono_float32(recording)

    def frame_size(self, frame_duration_ms: int) -> int:
        """Return the number of samples needed for a frame duration."""

        if frame_duration_ms not in {10, 20, 30}:
            raise ValueError("WebRTC VAD requires 10, 20, or 30 ms frames.")
        return int(self._sample_rate * frame_duration_ms / 1000)

    def to_pcm16(self, samples: AudioSamples) -> bytes:
        """Convert float32 samples in [-1.0, 1.0] to 16-bit PCM bytes."""

        numpy = self._load_numpy()
        clipped = numpy.clip(samples, -1.0, 1.0)
        pcm = (clipped * 32767.0).astype(numpy.int16)
        return pcm.tobytes()

    def concatenate(self, frames: Sequence[AudioSamples]) -> AudioSamples:
        """Concatenate audio frames into one float32 numpy array."""

        numpy = self._load_numpy()
        if not frames:
            return numpy.empty(0, dtype=numpy.float32)
        return numpy.concatenate(frames).astype(numpy.float32, copy=False)

    def _to_mono_float32(self, data: Any) -> AudioSamples:
        numpy = self._load_numpy()
        samples = numpy.asarray(data, dtype=numpy.float32)
        if samples.ndim == 2:
            samples = samples[:, 0]
        return numpy.ascontiguousarray(samples, dtype=numpy.float32)

    def _load_sounddevice(self) -> Any:
        if self._sounddevice is not None:
            return self._sounddevice

        try:
            import sounddevice
        except ImportError as exc:
            raise MicrophoneUnavailableError(
                "Install sounddevice to use microphone input."
            ) from exc

        self._sounddevice = sounddevice
        return self._sounddevice

    def _load_numpy(self) -> Any:
        if self._numpy is not None:
            return self._numpy

        try:
            import numpy
        except ImportError as exc:
            raise MicrophoneUnavailableError("Install numpy to capture microphone audio.") from exc

        self._numpy = numpy
        return self._numpy
