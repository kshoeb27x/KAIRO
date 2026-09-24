"""KAIRO V1 reasoning layer."""

from __future__ import annotations

from dataclasses import dataclass

from AI.ai import KairoAI


@dataclass
class ReasoningResult:
    input_text: str
    intent: str
    confidence: float
    reasoning: str
    context_history: list[str]


class KairoReasoner:
    """Structured reasoning layer backed by KAIRO AI."""

    def __init__(self, ai: KairoAI | None = None) -> None:
        self.ai = ai or KairoAI()

    def analyze(
        self,
        message: str,
        context_history: list[str] | None = None,
    ) -> ReasoningResult:
        message = message.strip()

        if not message:
            raise ValueError("Reasoning input is required.")

        history = list(context_history or [])
        lowered = message.lower()

        if lowered in {"hello", "hi", "hey"}:
            intent = "greeting"
            confidence = 1.0
            reasoning = "Input matches a known greeting."

        elif lowered == "status":
            intent = "status_request"
            confidence = 1.0
            reasoning = "Input explicitly requests system status."

        elif lowered.startswith("create task "):
            intent = "task_creation"
            confidence = 1.0
            reasoning = "Input contains a task creation command."

        elif lowered.startswith("plan "):
            intent = "planning_request"
            confidence = 1.0
            reasoning = "Input explicitly requests a plan."

        elif lowered.startswith("research "):
            intent = "research_request"
            confidence = 1.0
            reasoning = "Input explicitly requests research."

        elif lowered.startswith("code "):
            intent = "coding_request"
            confidence = 1.0
            reasoning = "Input explicitly requests a coding task."

        elif lowered.startswith("data "):
            intent = "data_request"
            confidence = 1.0
            reasoning = "Input explicitly requests a data task."

        else:
            ai_response = self.ai.generate(message)
            intent = "general_request"
            confidence = 0.5
            reasoning = ai_response.content

        return ReasoningResult(
            input_text=message,
            intent=intent,
            confidence=confidence,
            reasoning=reasoning,
            context_history=history,
        )

    def summary(self, result: ReasoningResult) -> dict:
        return {
            "input": result.input_text,
            "intent": result.intent,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "context_history": result.context_history,
        }
