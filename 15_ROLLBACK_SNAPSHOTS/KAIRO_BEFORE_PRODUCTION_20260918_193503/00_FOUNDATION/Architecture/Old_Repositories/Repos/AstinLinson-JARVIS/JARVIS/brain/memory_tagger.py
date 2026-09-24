"""Memory tagging heuristics for JARVIS."""

from __future__ import annotations

import logging
import re
from typing import Any


class MemoryTagger:
    """Enriches memory messages with context tags like intent and emotion."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def tag_input(
        self, 
        text: str, 
        is_wake_word_triggered: bool = False
    ) -> dict[str, Any]:
        """Apply heuristic rules to generate metadata tags for user input."""
        tags: dict[str, Any] = {
            "is_wake_word_triggered": is_wake_word_triggered,
        }

        # Intent heuristic
        text_lower = text.lower().strip()
        if text_lower in ("stop listening", "go to sleep", "shut down", "exit", "quit"):
            tags["intent"] = "system_control"
        elif text_lower.startswith(("turn on", "turn off", "open", "close", "set", "play", "stop")):
            tags["intent"] = "command"
        elif any(word in text_lower for word in ("what", "where", "when", "why", "who", "how", "?")):
            tags["intent"] = "question"
        else:
            tags["intent"] = "general_chat"

        # Emotion heuristic
        if re.search(r"\b(happy|great|awesome|excellent|love|thanks|thank you)\b", text_lower):
            tags["emotion"] = "positive"
        elif re.search(r"\b(sad|angry|mad|terrible|bad|hate|annoying)\b", text_lower):
            tags["emotion"] = "negative"
        else:
            tags["emotion"] = "neutral"

        # Memory extraction heuristic
        if match := re.search(r"(?i)\b(?:remember that|i am working on|i'm working on|i finished|we completed)\s+(.+)", text):
            tags["memory_type"] = "event"
            if "remember that" in match.group(0).lower():
                tags["memory_content"] = match.group(1).strip()
            else:
                tags["memory_content"] = match.group(0).strip()
        elif match := re.search(r"(?i)\b(?:my favorite|i prefer|i like)\s+(.+)", text):
            tags["memory_type"] = "preference"
            tags["memory_content"] = match.group(0).strip()
        elif match := re.match(r"(?i)^(?:i am|i'm|my name is)\s+(.+)", text):
            if not re.search(r"\b(happy|sad|angry|mad|terrible|bad|awesome|excellent|tired|good)\b", match.group(1).lower()):
                tags["memory_type"] = "identity"
                tags["memory_content"] = match.group(0).strip()

        self._logger.debug("Tagged input: %s", tags)
        return tags
