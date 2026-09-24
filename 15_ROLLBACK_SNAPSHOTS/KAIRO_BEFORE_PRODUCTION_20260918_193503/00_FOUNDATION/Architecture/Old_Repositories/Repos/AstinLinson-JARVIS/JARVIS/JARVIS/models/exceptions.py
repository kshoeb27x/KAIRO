"""Domain-specific exceptions used by the JARVIS runtime."""


class JarvisError(Exception):
    """Base class for recoverable JARVIS runtime errors."""


class InvalidConfigurationError(JarvisError):
    """Raised when configuration values are missing or invalid."""


class MicrophoneUnavailableError(JarvisError):
    """Raised when microphone hardware or drivers are unavailable."""


class InternetUnavailableError(JarvisError):
    """Raised when a provider needs the internet but cannot reach it."""


class EmptySpeechError(JarvisError):
    """Raised when speech input contains no recognizable command."""


class LLMTimeoutError(JarvisError):
    """Raised when the configured language model does not respond in time."""


class SpeechSynthesisError(JarvisError):
    """Raised when speech output fails."""
