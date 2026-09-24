"""Application entry point for JARVIS v0.1."""

from __future__ import annotations

import logging
from pathlib import Path
from time import sleep

from JARVIS.brain.memory_manager import InMemoryConversationMemory, MemoryManager
from JARVIS.brain.personality import PersonalityManager
from JARVIS.brain.planner import Planner
from JARVIS.brain.router import BrainRouter
from JARVIS.config.settings import Settings
from JARVIS.models.exceptions import (
    EmptySpeechError,
    InternetUnavailableError,
    InvalidConfigurationError,
    JarvisError,
    LLMTimeoutError,
    MicrophoneUnavailableError,
    SpeechSynthesisError,
)
from JARVIS.models.interfaces import SpeechRecognizer, SpeechSynthesizer
from JARVIS.models.language_model import create_language_model
from JARVIS.skills.builtin import register_builtin_skills
from JARVIS.skills.registry import SkillRegistry
from JARVIS.utils.logging import configure_logging
from JARVIS.voice.speech_to_text import create_speech_recognizer
from JARVIS.voice.text_to_speech import create_speech_synthesizer
from JARVIS.voice.wake_word import WakeWordDetector


class JarvisApplication:
    """Owns the v0.1 wake-word driven conversation loop."""

    def __init__(
        self,
        *,
        settings: Settings,
        recognizer: SpeechRecognizer,
        wake_word_detector: WakeWordDetector,
        brain_router: BrainRouter,
        synthesizer: SpeechSynthesizer,
        logger: logging.Logger,
    ) -> None:
        self._settings = settings
        self._recognizer = recognizer
        self._wake_word_detector = wake_word_detector
        self._brain_router = brain_router
        self._synthesizer = synthesizer
        self._logger = logger

    def run_forever(self) -> int:
        """Run the assistant until interrupted or a fatal hardware error occurs."""

        self._logger.info("JARVIS startup complete.")
        self._logger.info("Waiting for wake word: %s", self._settings.voice.wake_word)

        while True:
            try:
                wake_result = self._wake_word_detector.wait_for_wake_word(
                    timeout_seconds=self._settings.voice.input_timeout_seconds,
                    phrase_time_limit_seconds=self._settings.voice.phrase_time_limit_seconds,
                )
                command = wake_result.command_hint or self._listen_for_command()
                response = self._brain_router.process(command)
                self._speak(response)
            except KeyboardInterrupt:
                self._logger.info("Shutdown requested by user.")
                return 0
            except EmptySpeechError:
                self._logger.info("Speech event: empty command ignored.")
            except MicrophoneUnavailableError:
                self._logger.exception("Fatal audio input error.")
                return 2
            except InternetUnavailableError:
                self._logger.exception("Network-dependent speech service failed.")
                self._safe_speak("I cannot reach the speech service right now.")
                sleep(1)
            except LLMTimeoutError:
                self._logger.exception("Language model timeout.")
                self._safe_speak("The language model timed out. Please try again.")
            except SpeechSynthesisError:
                self._logger.exception("Speech synthesis failed; continuing without spoken output.")
            except JarvisError:
                self._logger.exception("Recoverable JARVIS error.")
                self._safe_speak("I ran into an internal error, but I am still online.")
            except Exception:
                self._logger.exception("Unexpected runtime error.")
                self._safe_speak("An unexpected error occurred.")
                sleep(1)

    def _listen_for_command(self) -> str:
        self._logger.info("Speech event: listening for command after wake word.")
        return self._recognizer.listen(
            timeout_seconds=self._settings.voice.input_timeout_seconds,
            phrase_time_limit_seconds=self._settings.voice.phrase_time_limit_seconds,
        )

    def _speak(self, text: str) -> None:
        self._logger.info("Speech event: speaking response.")
        self._synthesizer.speak(text)

    def _safe_speak(self, text: str) -> None:
        try:
            self._synthesizer.speak(text)
        except SpeechSynthesisError:
            self._logger.exception("Failed to speak fallback message.")


def build_application(project_root: Path) -> JarvisApplication:
    """Build the application graph with explicit dependency injection."""

    settings = Settings.load(project_root)
    logger = configure_logging(settings.logging, project_root)
    startup_notifier = _display_startup_step

    recognizer = create_speech_recognizer(
        settings.voice,
        logger,
        startup_notifier=startup_notifier,
    )
    synthesizer = create_speech_synthesizer(settings.voice, logger)
    wake_word_detector = WakeWordDetector(
        wake_word=settings.voice.wake_word,
        recognizer=recognizer,
        logger=logger,
    )

    startup_notifier("Loading Brain...")
    memory_store = InMemoryConversationMemory(max_messages=settings.memory.max_messages)
    from JARVIS.brain.memory_tagger import MemoryTagger
    memory_tagger = MemoryTagger(logger)
    memory_manager = MemoryManager(memory_store, tagger=memory_tagger, settings=settings)
    personality_manager = PersonalityManager.from_settings(settings.personality)
    planner = Planner()

    skill_registry = SkillRegistry(logger)
    register_builtin_skills(skill_registry)
    from JARVIS.skills.memory_skill import MemorySkill
    skill_registry.register(MemorySkill(memory_manager))
    
    language_model = create_language_model(settings.llm, logger)
    from JARVIS.skills.desktop_skill import DesktopSkill
    skill_registry.register(DesktopSkill(language_model, settings.desktop, logger))

    from JARVIS.skills.vision_skill import VisionSkill
    skill_registry.register(VisionSkill(settings.vision, logger))

    if settings.skills.auto_discover_entry_points:
        skill_registry.discover_entry_points()
    skill_registry.load_plugin_paths(settings.skills.plugin_paths)

    brain_router = BrainRouter(
        language_model=language_model,
        memory_manager=memory_manager,
        personality_manager=personality_manager,
        planner=planner,
        skill_registry=skill_registry,
        llm_timeout_seconds=settings.llm.timeout_seconds,
        logger=logger,
    )

    startup_notifier("Ready.")
    logger.info("Startup complete for environment: %s", settings.environment)

    return JarvisApplication(
        settings=settings,
        recognizer=recognizer,
        wake_word_detector=wake_word_detector,
        brain_router=brain_router,
        synthesizer=synthesizer,
        logger=logger,
    )


def _display_startup_step(message: str) -> None:
    print(message, flush=True)


def main() -> int:
    """CLI entry point."""

    project_root = Path(__file__).resolve().parent
    try:
        app = build_application(project_root)
    except InvalidConfigurationError as exc:
        print(f"JARVIS configuration error: {exc}")
        return 1
    except JarvisError as exc:
        print(f"JARVIS startup error: {exc}")
        return 1
    return app.run_forever()


if __name__ == "__main__":
    raise SystemExit(main())
