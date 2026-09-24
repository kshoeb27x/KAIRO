"""Reasoning layer for the vision pipeline."""

from __future__ import annotations

import logging
import re


class VisionReasoner:
    """Cleans and reasons over VLM responses."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def reason(self, raw_vlm_response: str) -> str:
        """Process the raw response into a final answer.
        
        Currently strips `<think>` blocks emitted by models like Qwen3 or DeepSeek.
        Future capabilities could include post-hoc validation against OCR bounding boxes.
        """
        
        content = raw_vlm_response
        
        # Remove reasoning blocks
        if "<think>" in content:
            self._logger.debug("Vision: Stripping <think> block from response.")
            content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
            
        content = content.strip()
        
        if not content:
            self._logger.warning("Vision: VLM returned empty response after stripping.")
            return "I analyzed the screen but the model returned an empty response."
            
        return content
