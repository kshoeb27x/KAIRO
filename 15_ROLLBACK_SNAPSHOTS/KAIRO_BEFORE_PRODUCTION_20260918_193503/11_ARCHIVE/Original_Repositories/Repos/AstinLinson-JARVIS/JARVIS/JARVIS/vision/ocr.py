"""OCR engine abstraction for the vision pipeline.

Extracts text, bounding boxes, and confidence scores from screenshot images.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class OCRResult:
    """A single OCR detection with text, confidence, and bounding box."""

    text: str
    confidence: float
    bbox: list[list[int]]


class OCREngine(ABC):
    """Abstract base class for OCR engines."""

    @abstractmethod
    def extract(self, image_bytes: bytes) -> list[OCRResult]:
        """Extract text from an image and return structured results."""


class EasyOCREngine(OCREngine):
    """OCR engine backed by EasyOCR with lazy model loading."""

    def __init__(self, *, languages: tuple[str, ...] = ("en",), logger: logging.Logger) -> None:
        self._languages = languages
        self._logger = logger
        self._reader: Any | None = None

    def extract(self, image_bytes: bytes) -> list[OCRResult]:
        """Extract text from image bytes using EasyOCR."""
        import io

        import numpy as np
        from PIL import Image

        self._logger.info("Vision: Running OCR...")

        reader = self._get_reader()
        img = Image.open(io.BytesIO(image_bytes))
        img_array = np.array(img)

        raw_results = reader.readtext(img_array)

        results: list[OCRResult] = []
        for bbox, text, confidence in raw_results:
            # Convert bbox from list of tuples to list of lists of ints
            bbox_int = [[int(x), int(y)] for x, y in bbox]
            results.append(
                OCRResult(text=text.strip(), confidence=round(confidence, 4), bbox=bbox_int)
            )

        # Sort top-to-bottom, left-to-right by the top-left corner
        results.sort(key=lambda r: (r.bbox[0][1], r.bbox[0][0]))

        word_count = sum(len(r.text.split()) for r in results)
        self._logger.info("Vision: OCR completed. %d detections, ~%d words.", len(results), word_count)
        return results

    def _get_reader(self) -> Any:
        if self._reader is not None:
            return self._reader

        try:
            import easyocr
        except ImportError as exc:
            from JARVIS.models.exceptions import InvalidConfigurationError

            raise InvalidConfigurationError(
                "Install 'easyocr' to use the EasyOCR engine."
            ) from exc

        self._logger.info("Vision: Loading EasyOCR model (first use may be slow)...")
        self._reader = easyocr.Reader(list(self._languages), gpu=False)
        return self._reader


def create_ocr_engine(engine_name: str, logger: logging.Logger) -> OCREngine:
    """Factory for OCR engines."""
    if engine_name.strip().lower() == "easyocr":
        return EasyOCREngine(logger=logger)
    from JARVIS.models.exceptions import InvalidConfigurationError

    raise InvalidConfigurationError(f"Unsupported OCR engine: {engine_name}")
