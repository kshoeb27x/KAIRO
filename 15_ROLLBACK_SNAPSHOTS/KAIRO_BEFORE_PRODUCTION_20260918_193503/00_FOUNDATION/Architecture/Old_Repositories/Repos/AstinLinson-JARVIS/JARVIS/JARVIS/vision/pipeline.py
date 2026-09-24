"""Vision pipeline orchestrator."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from JARVIS.config.settings import VisionSettings
from JARVIS.models.exceptions import InvalidConfigurationError
from JARVIS.vision.ocr import create_ocr_engine
from JARVIS.vision.preprocessor import ImagePreprocessor
from JARVIS.vision.providers import create_vision_provider
from JARVIS.vision.reasoning import VisionReasoner


@dataclass(frozen=True, slots=True)
class VisionResult:
    """The final result of the vision pipeline."""
    content: str


class VisionPipeline:
    """Orchestrates image capture, preprocessing, OCR, VLM, and reasoning."""

    def __init__(self, settings: VisionSettings, logger: logging.Logger) -> None:
        self._settings = settings
        self._logger = logger
        
        self._preprocessor = ImagePreprocessor(
            max_image_size=settings.max_image_size,
            sharpen=settings.sharpen,
            contrast=settings.contrast,
            logger=logger,
        )
        
        self._ocr_engine = (
            create_ocr_engine(settings.ocr_engine, logger)
            if settings.use_ocr
            else None
        )
        
        self._provider = create_vision_provider(settings, logger)
        self._reasoner = VisionReasoner(logger)
        
        # Cache for rapid follow-up questions
        self._last_capture_time = 0.0
        self._last_image_base64: str | None = None
        self._last_ocr_text: str | None = None

    def analyze(self, question: str) -> VisionResult:
        """Run the full vision pipeline on the current screen."""
        try:
            image_base64, ocr_text = self._get_or_capture_screen()
            
            # Phase 3/4: Vision Model + Prompt Engineering
            raw_response = self._provider.analyze(image_base64, ocr_text, question)
            
            # Phase 5: Reasoning
            final_content = self._reasoner.reason(raw_response)
            
            return VisionResult(content=final_content)
            
        except InvalidConfigurationError as exc:
            self._logger.error("Vision Pipeline Configuration Error: %s", exc)
            return VisionResult(content=f"Vision configuration error: {exc}")
        except Exception as exc:
            self._logger.exception("Vision Pipeline failed.")
            return VisionResult(content=f"I couldn't analyze your screen. Error: {exc}")

    def _get_or_capture_screen(self) -> tuple[str, str | None]:
        """Capture the screen and perform preprocessing/OCR, or reuse cached results."""
        now = time.monotonic()
        
        if (
            self._last_image_base64 is not None
            and (now - self._last_capture_time) < self._settings.cache_ttl_seconds
        ):
            self._logger.info("Vision: Reusing cached screenshot and OCR (< %.1fs).", self._settings.cache_ttl_seconds)
            return self._last_image_base64, self._last_ocr_text

        self._logger.info("Vision: Capturing screen...")
        raw_bytes = self._capture_raw_screen_bytes()
        
        if self._settings.preprocess:
            processed_bytes = self._preprocessor.preprocess(raw_bytes)
        else:
            processed_bytes = raw_bytes
            
        import base64
        self._last_image_base64 = base64.b64encode(processed_bytes).decode("utf-8")
        
        if self._ocr_engine:
            ocr_results = self._ocr_engine.extract(processed_bytes)
            if ocr_results:
                self._last_ocr_text = "\n".join(r.text for r in ocr_results)
            else:
                self._last_ocr_text = None
        else:
            self._last_ocr_text = None
            
        self._last_capture_time = time.monotonic()
        return self._last_image_base64, self._last_ocr_text

    def _capture_raw_screen_bytes(self) -> bytes:
        try:
            import mss
            from PIL import Image
        except ImportError as exc:
            raise InvalidConfigurationError(
                "Install 'mss' and 'Pillow' to capture screens."
            ) from exc

        with mss.mss() as sct:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            
            import io
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=100)
            return buffer.getvalue()
