"""Memory explicit commands skill for JARVIS."""

from __future__ import annotations

import re

from JARVIS.brain.memory_manager import MemoryManager
from JARVIS.models.interfaces import Skill
from JARVIS.models.types import SkillResult


class MemorySkill(Skill):
    """Handles explicit memory queries and deletions."""

    def __init__(self, memory_manager: MemoryManager) -> None:
        self._memory_manager = memory_manager

    @property
    def name(self) -> str:
        return "memory"

    @property
    def description(self) -> str:
        return "Manages personal memory queries and commands."

    def can_handle(self, command: str) -> bool:
        normalized = command.strip().lower()
        
        # Pending deletion handling
        if getattr(self._memory_manager, "pending_deletion", None):
            return normalized in ("yes", "no", "y", "n", "cancel")
            
        queries = [
            "what do you know about me",
            "what is my favorite",
            "summarize what you've learned",
            "list my projects",
            "forget that",
            "forget my",
            "what is my name",
            "who am i",
        ]
        return any(q in normalized for q in queries)

    def handle(self, command: str) -> SkillResult:
        normalized = command.strip().lower()

        # Handle pending deletion confirmation
        if getattr(self._memory_manager, "pending_deletion", None):
            pending = self._memory_manager.pending_deletion
            self._memory_manager.pending_deletion = None
            if normalized in ("yes", "y"):
                success = False
                if pending["type"] == "preference":
                    success = self._memory_manager.long_term.remove_preference(pending["id"])
                elif pending["type"] == "identity":
                    success = self._memory_manager.long_term.remove_identity(pending["id"])
                
                if success:
                    return SkillResult(content=f"Okay, I've forgotten {pending['desc']}.")
                return SkillResult(content="I couldn't find that memory to delete.")
            else:
                return SkillResult(content="Okay, I will keep that memory.")

        if "what do you know about me" in normalized or "summarize what you've learned" in normalized:
            identities = self._memory_manager.long_term.get_identities()
            if not identities:
                return SkillResult(content="I don't know much about you yet.")
            facts = [v["content"] for v in identities.values()]
            return SkillResult(content="I know that " + ", and ".join(facts) + ".")

        if "what is my favorite" in normalized:
            # simple keyword match
            topic = normalized.replace("what is my favorite", "").strip(" ?.")
            preferences = self._memory_manager.long_term.get_preferences()
            for k, v in preferences.items():
                if topic in v["content"].lower():
                    return SkillResult(content=f"You told me: {v['content']}")
            return SkillResult(content=f"I don't know what your favorite {topic} is.")

        if "list my projects" in normalized:
            events = self._memory_manager.long_term.get_events()
            projects = [e["content"] for e in events if "project" in e["content"].lower() or "working on" in e["content"].lower()]
            if not projects:
                return SkillResult(content="I don't have any projects listed for you.")
            return SkillResult(content="Here are your projects: " + ", ".join(projects))
            
        if "forget my favorite" in normalized:
            topic = normalized.replace("forget my favorite", "").strip(" ?.")
            preferences = self._memory_manager.long_term.get_preferences()
            for k, v in preferences.items():
                if topic in v["content"].lower():
                    self._memory_manager.pending_deletion = {"type": "preference", "id": k, "desc": f"your favorite {topic}"}
                    return SkillResult(content=f"Are you sure you want me to forget that {v['content']}?")
            return SkillResult(content=f"I don't remember your favorite {topic}.")

        return SkillResult(content="I'm not sure how to handle that memory request.")
