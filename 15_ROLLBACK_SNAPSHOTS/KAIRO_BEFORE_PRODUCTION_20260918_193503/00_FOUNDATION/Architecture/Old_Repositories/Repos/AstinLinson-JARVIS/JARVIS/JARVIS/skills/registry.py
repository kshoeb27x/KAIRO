"""Plugin registry for JARVIS skills."""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import logging
from collections.abc import Iterable, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

from JARVIS.models.interfaces import Skill
from JARVIS.models.types import SkillResult


class SkillRegistry:
    """Registry and discovery point for plugin-style assistant skills."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """Register a skill instance by unique name."""

        normalized_name = skill.name.strip().lower()
        if not normalized_name:
            raise ValueError("Skill name must not be empty.")
        if normalized_name in self._skills:
            raise ValueError(f"Skill already registered: {skill.name}")
        self._skills[normalized_name] = skill
        self._logger.info("Registered skill: %s", skill.name)

    def all(self) -> Sequence[Skill]:
        """Return all registered skills."""

        return tuple(self._skills.values())

    def handle(self, command: str) -> SkillResult | None:
        """Route a command to the first skill that can handle it."""

        for skill in self._skills.values():
            self._logger.info("Evaluating skill: %s", skill.name)
            if skill.can_handle(command):
                self._logger.info("Routing command to skill: %s", skill.name)
                return skill.handle(command)
        return None

    def discover_entry_points(self, group: str = "jarvis.skills") -> None:
        """Load skills published through Python package entry points."""

        for entry_point in importlib.metadata.entry_points(group=group):
            loaded = entry_point.load()
            self._register_loaded_plugin(loaded)

    def load_modules(self, module_names: Iterable[str]) -> None:
        """Load skill plugins by module name."""

        for module_name in module_names:
            module = importlib.import_module(module_name)
            self._register_loaded_plugin(module)

    def load_plugin_paths(self, paths: Iterable[Path]) -> None:
        """Load plugin modules from configured file or package paths."""

        for path in paths:
            if not path.exists():
                self._logger.warning("Skill plugin path does not exist: %s", path)
                continue
            if path.is_file() and path.suffix == ".py":
                self._load_plugin_file(path)
                continue
            if path.is_dir():
                self._load_plugin_directory(path)

    def _load_plugin_file(self, path: Path) -> None:
        module_name = f"jarvis_plugin_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            self._logger.warning("Unable to load skill plugin file: %s", path)
            return
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self._register_loaded_plugin(module)

    def _load_plugin_directory(self, path: Path) -> None:
        init_file = path / "__init__.py"
        if not init_file.exists():
            self._logger.warning("Skill plugin directory has no __init__.py: %s", path)
            return
        self._load_plugin_file(init_file)

    def _register_loaded_plugin(self, loaded: Any) -> None:
        if isinstance(loaded, Skill):
            self.register(loaded)
            return

        if isinstance(loaded, type) and issubclass(loaded, Skill):
            self.register(loaded())
            return

        if isinstance(loaded, ModuleType) and hasattr(loaded, "register"):
            loaded.register(self)
            return

        if callable(loaded):
            result = loaded()
            if isinstance(result, Skill):
                self.register(result)
                return
            if isinstance(result, Iterable):
                for skill in result:
                    if isinstance(skill, Skill):
                        self.register(skill)
                return

        self._logger.warning("Loaded plugin did not expose a Skill: %r", loaded)
