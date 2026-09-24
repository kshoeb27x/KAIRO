"""Prompt planning for the AI brain."""

from __future__ import annotations

from collections.abc import Sequence

from JARVIS.brain.personality import PersonalityProfile
from JARVIS.models.types import Message


class Planner:
    """Builds the structured message list sent to the language model."""

    def build_messages(
        self,
        command: str,
        *,
        personality: PersonalityProfile,
        memory: Sequence[Message],
        context: Sequence[str] = (),
    ) -> list[Message]:
        """Create the LLM message list for one user command."""

        sys_prompt = personality.system_prompt()
        if context:
            sys_prompt += "\n\nRelevant Personal Context:\n- " + "\n- ".join(context)

        messages = [Message(role="system", content=sys_prompt)]
        messages.extend(memory)
        messages.append(Message(role="user", content=command))
        return messages
