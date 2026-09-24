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
        self._client: Any | None = None

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
            self._logger.info("VisionSkill taking screenshot...")
            image_base64 = self._capture_screen_base64()

            client = self._get_client()

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"You are JARVIS, an AI desktop assistant. The user has asked you a question about their current screen. Here is a screenshot of their primary monitor.\n\nUser Question: {command}",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                        },
                    ],
                }
            ]

            self._logger.info("VisionSkill sending prompt to VLM...")
            response = client.chat.completions.create(
                model=self._settings.model,
                messages=messages,
                timeout=self._settings.timeout_seconds,
            )

            content = response.choices[0].message.content
            
            import re
            content_str = str(content)
            # Remove reasoning blocks emitted by models like Qwen3 or DeepSeek
            content_str = re.sub(r'<think>.*?</think>', '', content_str, flags=re.DOTALL).strip()
            
            return SkillResult(content=content_str)

        except Exception as exc:
            self._logger.exception("Vision skill failed.")
            return SkillResult(content=f"I couldn't analyze your screen. Error: {exc}")

    def _capture_screen_base64(self) -> str:
        """Capture the primary monitor, compress, and return as base64."""
        try:
            import mss
            from PIL import Image
        except ImportError as exc:
            raise InvalidConfigurationError(
                "Install 'mss' and 'Pillow' to use the VisionSkill."
            ) from exc

        with mss.mss() as sct:
            # Capture the primary monitor (monitor 1)
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)

            # Convert to PIL Image
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

            # Resize if it's too large to save tokens/bandwidth
            max_size = self._settings.max_image_size
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            # Compress to JPEG
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)

            return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise InvalidConfigurationError(
                "Install the 'openai' package to use the VisionSkill."
            ) from exc

        if not self._settings.api_key and not self._settings.api_base_url:
            raise InvalidConfigurationError("VisionSkill requires api_key or api_base_url.")

        if self._settings.api_base_url:
            self._client = OpenAI(
                api_key=self._settings.api_key or "sk-dummy",
                base_url=self._settings.api_base_url,
            )
        else:
            self._client = OpenAI(api_key=self._settings.api_key)

        return self._client
