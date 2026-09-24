"""Vision skill for screen capture and analysis."""

from __future__ import annotations

import base64
import io
import logging
from typing import Any

from JARVIS.config.settings import VisionSettings
from JARVIS.models.exceptions import InvalidConfigurationError
from JARVIS.models.interfaces import Skill
from JARVIS.models.types import SkillResult


class VisionSkill(Skill):
    """Captures screen and answers questions using a Vision Language Model."""

    def __init__(self, settings: VisionSettings, logger: logging.Logger) -> None:
        self._settings = settings
        self._logger = logger
        
        # Lazy initialization
        self._pipeline: Any | None = None

    @property
    def name(self) -> str:
        return "vision"

    @property
    def description(self) -> str:
        return "Captures the screen and answers questions about it."

    def can_handle(self, command: str) -> bool:
        import re
        
        # 1. Normalize
        command_lower = command.lower()
        # Strip wake word just in case
        for prefix in ("jarvis, ", "jarvis "):
            if command_lower.startswith(prefix):
                command_lower = command_lower[len(prefix):].strip()
                
        # Remove punctuation and collapse whitespace
        command_clean = re.sub(r'[^\w\s]', '', command_lower)
        command_norm = re.sub(r'\s+', ' ', command_clean).strip()
        
        self._logger.debug("VisionSkill.can_handle normalized command: '%s'", command_norm)
        
        tokens = set(command_norm.split())
        
        # 2. Token-based intent matching (Verb + Target)
        vision_verbs = {"summarize", "explain", "describe", "read", "analyze", "see", "look", "tell", "check"}
        vision_targets = {"screen", "screenshot", "webpage", "page", "website", "article", "error", "window", "button", "this"}
        
        if tokens & vision_verbs and tokens & vision_targets:
            self._logger.debug("VisionSkill matched Rule: Verb + Target intersection")
            return True
            
        # 3. Explicit intent patterns
        explicit_patterns = [
            r"^what is on ",
            r"^whats on ",
            r"what does this .* say",
            r"what am i looking at",
            r"what im looking at",
            r"what i am looking at",
            r"^what is this",
            r"^read this",
            r"what button"
        ]
        
        for pattern in explicit_patterns:
            if re.search(pattern, command_norm):
                self._logger.debug("VisionSkill matched Rule: Explicit pattern '%s'", pattern)
                return True
                
        self._logger.debug("VisionSkill found no matching rules.")
        return False

    def handle(self, command: str) -> SkillResult:
        try:
            if self._pipeline is None:
                from JARVIS.vision.pipeline import VisionPipeline
                self._pipeline = VisionPipeline(self._settings, self._logger)
                
            result = self._pipeline.analyze(command)
            return SkillResult(content=result.content)
        except Exception as exc:
            self._logger.exception("Vision skill failed.")
            return SkillResult(content=f"I couldn't analyze your screen. Error: {exc}")

