"""Logging setup for JARVIS."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from JARVIS.config.settings import LoggingSettings


def configure_logging(settings: LoggingSettings, project_root: Path) -> logging.Logger:
    """Configure console and file logging and return the application logger."""

    logger = logging.getLogger("jarvis")
    logger.handlers.clear()
    logger.setLevel(getattr(logging, settings.level, logging.INFO))
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    log_path = settings.file_path
    if not log_path.is_absolute():
        log_path = project_root / log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
