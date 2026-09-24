"""Image preprocessing for the vision pipeline.

Enhances screenshots before OCR and VLM analysis by applying sharpening,
contrast adjustment, and intelligent resizing — all in memory.
"""

from __future__ import annotations

import io
import logging


class ImagePreprocessor:
    """Preprocesses screenshot images for better OCR and VLM accuracy."""

    def __init__(
        self,
        *,
        max_image_size: int = 1080,
        sharpen: bool = True,
        contrast: bool = True,
        logger: logging.Logger,
    ) -> None:
        self._max_image_size = max_image_size
        self._sharpen = sharpen
        self._contrast = contrast
        self._logger = logger

    def preprocess(self, raw_bytes: bytes) -> bytes:
        """Apply preprocessing steps and return compressed JPEG bytes."""
        from PIL import Image, ImageEnhance, ImageFilter

        self._logger.info("Vision: Preprocessing image...")

        img = Image.open(io.BytesIO(raw_bytes))
        if img.mode != "RGB":
            img = img.convert("RGB")

        # 1. Intelligent resize preserving aspect ratio
        if img.width > self._max_image_size or img.height > self._max_image_size:
            img.thumbnail(
                (self._max_image_size, self._max_image_size),
                Image.Resampling.LANCZOS,
            )
            self._logger.info(
                "Vision: Resized to %dx%d.", img.width, img.height,
            )

        # 2. Sharpen for text clarity
        if self._sharpen:
            img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
            self._logger.info("Vision: Sharpening applied.")

        # 3. Contrast enhancement for UI readability
        if self._contrast:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.3)
            self._logger.info("Vision: Contrast enhanced.")

        # 4. Compress to JPEG in memory
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        result = buffer.getvalue()
        self._logger.info("Vision: Preprocessing complete. Output size: %d bytes.", len(result))
        return result
