"""Configuration loading for JARVIS.

Settings are loaded from ``config/config.yaml`` first and then overridden by
environment variables from ``.env`` and the active shell environment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from JARVIS.models.exceptions import InvalidConfigurationError


@dataclass(frozen=True, slots=True)
class LoggingSettings:
    """Controls console and file logging behavior."""

    level: str
    file_path: Path


@dataclass(frozen=True, slots=True)
class VoiceSettings:
    """Controls speech recognition, wake word, and speech synthesis providers."""

    wake_word: str
    backend: str
    sample_rate: int
    whisper_model: str
    compute_type: str
    vad_enabled: bool
    speech_synthesizer: str
    input_timeout_seconds: float
    phrase_time_limit_seconds: float
    tts_voice_hint: str
    tts_rate: int
    stream_mode: bool
    device: str


@dataclass(frozen=True, slots=True)
class LLMSettings:
    """Controls the language model provider and request behavior."""

    provider: str
    model: str
    timeout_seconds: float
    api_key: str | None = None
    api_base_url: str | None = None


@dataclass(frozen=True, slots=True)
class MemorySettings:
    """Controls the active memory backend."""

    provider: str
    max_messages: int
    memory_enabled: bool
    max_session_memories: int
    max_long_term_memories: int
    auto_save: bool
    retrieval_limit: int


@dataclass(frozen=True, slots=True)
class DesktopSettings:
    """Controls desktop automation limits and preferences."""

    enabled: bool
    search_timeout: float
    max_results: int
    allow_recursive_search: bool
    preferred_browser: str


@dataclass(frozen=True, slots=True)
class PersonalitySettings:
    """Controls the assistant's default conversational profile."""

    traits: tuple[str, ...] = field(default_factory=tuple)
    style: str = "natural conversation"


@dataclass(frozen=True, slots=True)
class SkillSettings:
    """Controls skill discovery and plugin loading."""

    auto_discover_entry_points: bool
    plugin_paths: tuple[Path, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class VisionSettings:
    """Controls the vision language model, OCR, preprocessing, and capture behavior."""

    provider: str
    model: str
    timeout_seconds: float
    max_image_size: int
    use_ocr: bool
    ocr_engine: str
    preprocess: bool
    sharpen: bool
    contrast: bool
    cache_ttl_seconds: float
    api_key: str | None = None
    api_base_url: str | None = None


@dataclass(frozen=True, slots=True)
class Settings:
    """Top-level immutable runtime settings."""

    environment: str
    logging: LoggingSettings
    voice: VoiceSettings
    llm: LLMSettings
    vision: VisionSettings
    memory: MemorySettings
    desktop: DesktopSettings
    personality: PersonalitySettings
    skills: SkillSettings

    @classmethod
    def load(cls, project_root: Path | None = None) -> "Settings":
        """Load settings from YAML and environment variables."""

        root = project_root or Path(__file__).resolve().parents[1]
        cls._load_dotenv(root / ".env")
        config_data = cls._load_yaml(root / "config" / "config.yaml")

        environment = os.getenv("JARVIS_ENV", str(config_data.get("environment", "development")))
        logging_settings = cls._load_logging(config_data)
        voice_settings = cls._load_voice(config_data)
        llm_settings = cls._load_llm(config_data)
        vision_settings = cls._load_vision(config_data)
        memory_settings = cls._load_memory(config_data)
        desktop_settings = cls._load_desktop(config_data)
        personality_settings = cls._load_personality(config_data)
        skill_settings = cls._load_skills(config_data, root)

        settings = cls(
            environment=environment,
            logging=logging_settings,
            voice=voice_settings,
            llm=llm_settings,
            vision=vision_settings,
            memory=memory_settings,
            desktop=desktop_settings,
            personality=personality_settings,
            skills=skill_settings,
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        """Validate critical settings before runtime starts."""

        if not self.voice.wake_word.strip():
            raise InvalidConfigurationError("voice.wake_word must not be empty.")
        if self.voice.backend.strip().lower() != "faster_whisper":
            raise InvalidConfigurationError("voice.backend must be 'faster_whisper'.")
        if self.voice.sample_rate != 16_000:
            raise InvalidConfigurationError("voice.sample_rate must be 16000 for v0.1.")
        if self.voice.whisper_model not in {"tiny", "base", "small"}:
            raise InvalidConfigurationError("voice.whisper_model must be tiny, base, or small.")
        if not self.voice.compute_type.strip():
            raise InvalidConfigurationError("voice.compute_type must not be empty.")
        if self.voice.tts_rate <= 0:
            raise InvalidConfigurationError("voice.tts_rate must be positive.")
        if self.llm.timeout_seconds <= 0:
            raise InvalidConfigurationError("llm.timeout_seconds must be positive.")
        if self.memory.max_messages <= 0:
            raise InvalidConfigurationError("memory.max_messages must be positive.")

    @staticmethod
    def _load_dotenv(env_path: Path) -> None:
        try:
            from dotenv import load_dotenv
        except ImportError:
            return

        load_dotenv(env_path)

    @staticmethod
    def _load_yaml(config_path: Path) -> dict[str, Any]:
        if not config_path.exists():
            raise InvalidConfigurationError(f"Missing configuration file: {config_path}")

        try:
            import yaml
        except ImportError as exc:
            raise InvalidConfigurationError("PyYAML is required to read config.yaml.") from exc

        with config_path.open("r", encoding="utf-8") as stream:
            data = yaml.safe_load(stream) or {}

        if not isinstance(data, dict):
            raise InvalidConfigurationError("config.yaml must contain a mapping at the top level.")
        return data

    @staticmethod
    def _section(data: dict[str, Any], key: str) -> dict[str, Any]:
        section = data.get(key, {})
        if not isinstance(section, dict):
            raise InvalidConfigurationError(f"config.yaml section '{key}' must be a mapping.")
        return section

    @classmethod
    def _load_logging(cls, data: dict[str, Any]) -> LoggingSettings:
        section = cls._section(data, "logging")
        level = os.getenv("JARVIS_LOG_LEVEL", str(section.get("level", "INFO"))).upper()
        file_path = Path(os.getenv("JARVIS_LOG_FILE", str(section.get("file", "logs/jarvis.log"))))
        return LoggingSettings(level=level, file_path=file_path)

    @classmethod
    def _load_voice(cls, data: dict[str, Any]) -> VoiceSettings:
        section = cls._section(data, "voice")
        backend = os.getenv("JARVIS_VOICE_BACKEND", str(section.get("backend", "faster_whisper")))
        return VoiceSettings(
            wake_word=os.getenv("JARVIS_WAKE_WORD", str(section.get("wake_word", "Jarvis"))),
            backend=backend,
            sample_rate=int(
                os.getenv("JARVIS_SAMPLE_RATE", str(section.get("sample_rate", 16000)))
            ),
            whisper_model=os.getenv(
                "JARVIS_WHISPER_MODEL",
                str(section.get("whisper_model", "base")),
            ),
            compute_type=os.getenv(
                "JARVIS_WHISPER_COMPUTE_TYPE",
                str(section.get("compute_type", "int8")),
            ),
            vad_enabled=cls._bool_from_env(
                "JARVIS_VAD_ENABLED",
                section.get("vad_enabled", True),
            ),
            speech_synthesizer=os.getenv(
                "JARVIS_TTS_PROVIDER",
                str(section.get("speech_synthesizer", "pyttsx3")),
            ),
            input_timeout_seconds=float(section.get("input_timeout_seconds", 6.0)),
            phrase_time_limit_seconds=float(section.get("phrase_time_limit_seconds", 12.0)),
            tts_voice_hint=str(section.get("tts_voice_hint", "female")),
            tts_rate=int(section.get("tts_rate", 175)),
            stream_mode=cls._bool_from_env(
                "JARVIS_STREAM_MODE",
                section.get("stream_mode", False),
            ),
            device=os.getenv("JARVIS_VOICE_DEVICE", str(section.get("device", "auto"))).strip().lower(),
        )

    @staticmethod
    def _bool_from_env(name: str, default: Any) -> bool:
        raw_value = os.getenv(name)
        value = default if raw_value is None else raw_value
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        raise InvalidConfigurationError(f"{name} must be a boolean value.")

    @classmethod
    def _load_llm(cls, data: dict[str, Any]) -> LLMSettings:
        section = cls._section(data, "llm")
        provider = os.getenv("JARVIS_LLM_PROVIDER", str(section.get("provider", "echo")))
        api_key = os.getenv("JARVIS_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        api_base_url = os.getenv("JARVIS_LLM_API_BASE_URL", section.get("api_base_url"))
        return LLMSettings(
            provider=provider,
            model=os.getenv("JARVIS_LLM_MODEL", str(section.get("model", "local-echo"))),
            timeout_seconds=float(section.get("timeout_seconds", 30.0)),
            api_key=api_key,
            api_base_url=str(api_base_url) if api_base_url else None,
        )

    @classmethod
    def _load_vision(cls, data: dict[str, Any]) -> VisionSettings:
        section = cls._section(data, "vision")
        provider = os.getenv("JARVIS_VISION_PROVIDER", str(section.get("provider", "openai_compatible")))
        api_key = os.getenv("JARVIS_VISION_API_KEY") or os.getenv("OPENAI_API_KEY")
        api_base_url = os.getenv("JARVIS_VISION_API_BASE_URL", section.get("api_base_url"))
        return VisionSettings(
            provider=provider,
            model=os.getenv("JARVIS_VISION_MODEL", str(section.get("model", "llava"))),
            timeout_seconds=float(section.get("timeout_seconds", 60.0)),
            max_image_size=int(section.get("max_image_size", 1080)),
            use_ocr=cls._bool_from_env(
                "JARVIS_VISION_USE_OCR",
                section.get("use_ocr", True),
            ),
            ocr_engine=str(section.get("ocr_engine", "easyocr")),
            preprocess=cls._bool_from_env(
                "JARVIS_VISION_PREPROCESS",
                section.get("preprocess", True),
            ),
            sharpen=cls._bool_from_env(
                "JARVIS_VISION_SHARPEN",
                section.get("sharpen", True),
            ),
            contrast=cls._bool_from_env(
                "JARVIS_VISION_CONTRAST",
                section.get("contrast", True),
            ),
            cache_ttl_seconds=float(section.get("cache_ttl_seconds", 3.0)),
            api_key=api_key,
            api_base_url=str(api_base_url) if api_base_url else None,
        )

    @classmethod
    def _load_memory(cls, data: dict[str, Any]) -> MemorySettings:
        section = cls._section(data, "memory")
        return MemorySettings(
            provider=str(section.get("provider", "in_memory")),
            max_messages=int(section.get("max_messages", 20)),
            memory_enabled=bool(section.get("memory_enabled", True)),
            max_session_memories=int(section.get("max_session_memories", 50)),
            max_long_term_memories=int(section.get("max_long_term_memories", 1000)),
            auto_save=bool(section.get("auto_save", True)),
            retrieval_limit=int(section.get("retrieval_limit", 5)),
        )

    @classmethod
    def _load_desktop(cls, data: dict[str, Any]) -> DesktopSettings:
        section = cls._section(data, "desktop")
        return DesktopSettings(
            enabled=bool(section.get("enabled", True)),
            search_timeout=float(section.get("search_timeout", 10.0)),
            max_results=int(section.get("max_results", 5)),
            allow_recursive_search=bool(section.get("allow_recursive_search", True)),
            preferred_browser=str(section.get("preferred_browser", "chrome")),
        )

    @classmethod
    def _load_personality(cls, data: dict[str, Any]) -> PersonalitySettings:
        section = cls._section(data, "personality")
        traits = section.get("traits", ["Friendly", "Professional", "Calm", "Helpful"])
        if not isinstance(traits, list) or not all(isinstance(item, str) for item in traits):
            raise InvalidConfigurationError("personality.traits must be a list of strings.")
        return PersonalitySettings(
            traits=tuple(traits),
            style=str(section.get("style", "natural conversation")),
        )

    @classmethod
    def _load_skills(cls, data: dict[str, Any], project_root: Path) -> SkillSettings:
        section = cls._section(data, "skills")
        paths = section.get("plugin_paths", [])
        if not isinstance(paths, list) or not all(isinstance(item, str) for item in paths):
            raise InvalidConfigurationError("skills.plugin_paths must be a list of strings.")

        resolved_paths = tuple(
            Path(item) if Path(item).is_absolute() else project_root / item
            for item in paths
        )
        return SkillSettings(
            auto_discover_entry_points=bool(section.get("auto_discover_entry_points", True)),
            plugin_paths=resolved_paths,
        )
