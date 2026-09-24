"""Prompt engineering for the multimodal vision pipeline."""

from __future__ import annotations


def build_vision_prompt(question: str, ocr_text: str | None = None) -> str:
    """Build a structured system prompt combining instructions, context, and OCR."""
    
    prompt = [
        "You are JARVIS, an AI desktop assistant.",
        "This image is a screenshot of a Windows desktop or application.",
    ]
    
    if ocr_text:
        prompt.extend([
            "You also have OCR text extracted from the screenshot.",
            "Prefer the exact OCR text over guessing for any written content.",
            "Never invent information.",
            "If something is uncertain, explicitly say you are uncertain.",
            "Read text exactly as it appears.",
            "",
            "--- OCR TEXT START ---",
            ocr_text,
            "--- OCR TEXT END ---",
        ])
    else:
        prompt.extend([
            "Never invent information.",
            "If something is uncertain, explicitly say you are uncertain.",
        ])

    prompt.extend([
        "",
        f"User question: {question}",
        "",
        "Now answer.",
    ])
    
    return "\n".join(prompt)
