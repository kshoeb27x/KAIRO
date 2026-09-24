"""Command router for the JARVIS brain."""

from __future__ import annotations

import logging
from time import perf_counter

from JARVIS.brain.memory_manager import MemoryManager
from JARVIS.brain.personality import PersonalityManager
from JARVIS.brain.planner import Planner
from JARVIS.models.exceptions import EmptySpeechError
from JARVIS.models.interfaces import LanguageModel
from JARVIS.skills.registry import SkillRegistry


class BrainRouter:
    """Routes commands to skills first and then to the active language model."""

    def __init__(
        self,
        language_model: LanguageModel,
        memory_manager: MemoryManager,
        personality_manager: PersonalityManager,
        planner: Planner,
        skill_registry: SkillRegistry,
        llm_timeout_seconds: float,
        logger: logging.Logger,
    ) -> None:
        self._language_model = language_model
        self._memory_manager = memory_manager
        self._personality_manager = personality_manager
        self._planner = planner
        self._skill_registry = skill_registry
        self._llm_timeout_seconds = llm_timeout_seconds
        self._logger = logger

    @staticmethod
    def _strip_wake_word(text: str) -> str:
        """Remove a leading wake-word prefix so downstream handlers see clean commands."""
        stripped = text.strip()
        lower = stripped.lower()
        for prefix in ("jarvis, ", "jarvis "):
            if lower.startswith(prefix):
                return stripped[len(prefix):].strip()
        return stripped

    def _detect_intent(self, text: str) -> str:
        """Lightweight heuristic intent detection."""
        text_lower = text.lower().strip()

        if text_lower in ("stop listening", "go to sleep", "shut down", "exit", "quit"):
            return "system_control"

        desktop_verbs = ("open", "launch", "start", "find", "search", "take a screenshot", "screenshot")
        if any(text_lower.startswith(v) for v in desktop_verbs):
            return "desktop"

        vision_verbs = (
            "what is on my screen", "what's on my screen", "read this error", 
            "summarize this webpage", "summarize this page", "explain this article",
            "what does this website say", "what does this page say",
            "describe this window", "describe this screen",
            "explain what i'm looking at", "explain what i am looking at",
            "what button", "look at", "see my screen", "screenshot", "read the screen",
            "what am i looking at", "what is this", "read this"
        )
        if any(v in text_lower for v in vision_verbs):
            return "vision"

        if text_lower.startswith(("turn on", "turn off", "close", "set", "play", "stop")):
            return "command"

        if any(word in text_lower for word in ("what", "where", "when", "why", "who", "how", "?")):
            return "question"
        return "general_chat"

    def process(self, command: str) -> str:
        """Process a user command and return assistant text."""

        normalized_command = self._strip_wake_word(command)
        if not normalized_command:
            raise EmptySpeechError("No command was detected after the wake word.")

        start_time = perf_counter()
        self._logger.info("AI request started.")

        try:
            intent = self._detect_intent(normalized_command)
            self._logger.info("Detected intent: %s", intent)

            response = None

            # Fast-path routing based on intent
            if intent == "system_control":
                # Handle system commands directly
                response = "Shutting down systems. Goodbye."
                # In a real system, we'd emit a shutdown event here
            else:
                # Route commands aggressively to skills first
                self._logger.info("Calling SkillRegistry...")
                skill_result = self._skill_registry.handle(normalized_command)
                if skill_result is not None and skill_result.handled:
                    response = skill_result.content

            # Fallback to LLM for questions, chat, or unhandled commands
            if response is None:
                self._logger.info("No skill matched. Falling back to LLM.")
                context = self._memory_manager.retrieve_context(normalized_command)
                messages = self._planner.build_messages(
                    normalized_command,
                    personality=self._personality_manager.profile,
                    memory=self._memory_manager.recent_messages(),
                    context=context,
                )
                response = self._language_model.generate(
                    messages,
                    timeout_seconds=self._llm_timeout_seconds,
                )

            self._memory_manager.add_user_message(normalized_command)
            self._memory_manager.add_assistant_message(response)
            elapsed = perf_counter() - start_time
            self._logger.info("AI request completed in %.3f seconds.", elapsed)
            return response
        except Exception:
            elapsed = perf_counter() - start_time
            self._logger.exception("AI request failed after %.3f seconds.", elapsed)
            raise

