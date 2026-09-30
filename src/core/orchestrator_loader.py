from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORE_ROOT = PROJECT_ROOT / "01_CORE"
AGENTS_ROOT = PROJECT_ROOT / "02_AGENTS"

for path in (CORE_ROOT, AGENTS_ROOT):
    value = str(path)
    if value not in sys.path:
        sys.path.insert(0, value)

from Orchestration.orchestrator import KairoOrchestrator

__all__ = ["KairoOrchestrator"]
