from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT = (
    PROJECT_ROOT
    / "12_EXTRACTION"
    / "CONSOLIDATION"
    / "DECISIONS"
    / "integration_plan.json"
)

OUTPUT_ROOT = PROJECT_ROOT / "12_EXTRACTION" / "ARCHITECTURE_MAPPING"

ANALYSIS_DIR = OUTPUT_ROOT / "ANALYSIS"
MAP_DIR = OUTPUT_ROOT / "MAPS"
DECISION_DIR = OUTPUT_ROOT / "DECISIONS"
MANIFEST_DIR = OUTPUT_ROOT / "MANIFEST"
REPORT_DIR = OUTPUT_ROOT / "REPORTS"

for directory in [
    ANALYSIS_DIR,
    MAP_DIR,
    DECISION_DIR,
    MANIFEST_DIR,
    REPORT_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)


KAIRO_LAYERS = {
    "FOUNDATION": "00_FOUNDATION",
    "CORE": "01_CORE",
    "AGENTS": "02_AGENTS",
    "DATA": "03_DATA",
    "TOOLS": "04_TOOLS",
    "UI": "05_UI",
    "SECURITY": "06_SECURITY",
    "RUNTIME": "07_RUNTIME",
    "BUSINESS": "08_BUSINESS",
    "INFRASTRUCTURE": "09_INFRASTRUCTURE",
    "DOCUMENTATION": "10_DOCUMENTATION",
}


CAPABILITY_LAYER_MAP = {
    "LLM": "CORE",
    "Memory": "CORE",
    "RAG": "DATA",
    "Database": "DATA",
    "Data": "DATA",

    "Agent": "AGENTS",
    "Coding": "AGENTS",
    "Research": "AGENTS",
    "Trading": "BUSINESS",
    "Finance": "BUSINESS",

    "Tools": "TOOLS",
    "Browser": "TOOLS",
    "Computer Use": "TOOLS",
    "MCP": "TOOLS",
    "API": "TOOLS",

    "UI": "UI",
    "Voice": "UI",

    "Security": "SECURITY",

    "Workflow": "RUNTIME",
    "Automation": "RUNTIME",
    "Observability": "RUNTIME",

    "Containers": "INFRASTRUCTURE",
}


LAYER_PATHS = {
    layer: PROJECT_ROOT / path
    for layer, path in KAIRO_LAYERS.items()
}


GENERATED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "coverage",
    ".next",
    ".turbo",
}


EXTENSION_GROUPS = {
    "python": {".py", ".pyi"},
    "javascript": {".js", ".jsx", ".mjs", ".cjs"},
    "typescript": {".ts", ".tsx"},
    "rust": {".rs"},
    "go": {".go"},
    "shell": {".sh", ".bash", ".ps1", ".bat"},
    "config": {".json", ".yaml", ".yml", ".toml", ".ini", ".env"},
    "web": {".html", ".css", ".scss", ".vue"},
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def infer_capabilities(record: dict) -> list[str]:
    capabilities = record.get("capabilities", [])

    if isinstance(capabilities, dict):
        capabilities = list(capabilities.keys())

    return sorted(
        {
            str(item)
            for item in capabilities
            if item
        }
    )


def classify_component(record: dict) -> str:
    path = str(
        record.get("repository_relative_path")
        or record.get("source_file")
        or ""
    )

    name = Path(path).name.lower()
    normalized = normalize_text(path)

    if any(token in normalized for token in [
        "test", "tests", "spec", "fixture", "mock"
    ]):
        return "TEST"

    if any(token in name for token in [
        "config", "settings", "schema", "manifest"
    ]):
        return "CONFIGURATION"

    if any(token in normalized for token in [
        "security", "auth", "permission", "credential", "secret"
    ]):
        return "SECURITY"

    if any(token in normalized for token in [
        "agent", "assistant", "orchestrat"
    ]):
        return "AGENT"

    if any(token in normalized for token in [
        "memory", "rag", "knowledge", "retrieval", "embedding"
    ]):
        return "KNOWLEDGE"

    if any(token in normalized for token in [
        "browser", "computer", "playwright", "selenium"
    ]):
        return "COMPUTER_CONTROL"

    if any(token in normalized for token in [
        "workflow", "automation", "scheduler", "task"
    ]):
        return "WORKFLOW"

    if any(token in normalized for token in [
        "model", "llm", "provider", "inference"
    ]):
        return "MODEL"

    if any(token in normalized for token in [
        "database", "db", "storage", "repository"
    ]):
        return "DATA"

    if any(token in normalized for token in [
        "api", "server", "client", "http", "grpc"
    ]):
        return "API"

    if any(token in normalized for token in [
        "trading", "strategy", "portfolio", "market", "broker"
    ]):
        return "TRADING"

    if any(token in normalized for token in [
        "ui", "frontend", "component", "dashboard", "voice"
    ]):
        return "INTERFACE"

    return "GENERAL"


def choose_primary_layer(capabilities: list[str], component_type: str) -> str:
    priority = []

    type_map = {
        "SECURITY": "SECURITY",
        "AGENT": "AGENTS",
        "KNOWLEDGE": "DATA",
        "COMPUTER_CONTROL": "TOOLS",
        "WORKFLOW": "RUNTIME",
        "MODEL": "CORE",
        "DATA": "DATA",
        "API": "TOOLS",
        "TRADING": "BUSINESS",
        "INTERFACE": "UI",
        "CONFIGURATION": "FOUNDATION",
        "TEST": "DOCUMENTATION",
        "GENERAL": "CORE",
    }

    if component_type in type_map:
        priority.append(type_map[component_type])

    for capability in capabilities:
        layer = CAPABILITY_LAYER_MAP.get(capability)
        if layer:
            priority.append(layer)

    if not priority:
        return "CORE"

    counts = Counter(priority)

    return counts.most_common(1)[0][0]


def choose_secondary_layers(
    capabilities: list[str],
    primary_layer: str,
) -> list[str]:

    layers = set()

    for capability in capabilities:
        layer = CAPABILITY_LAYER_MAP.get(capability)
        if layer and layer != primary_layer:
            layers.add(layer)

    return sorted(layers)


def integration_action(
    record: dict,
    component_type: str,
    primary_layer: str,
) -> str:

    score = float(record.get("score", 0) or 0)

    if component_type == "TEST":
        return "REFERENCE_ONLY"

    if component_type == "CONFIGURATION":
        return "ADAPT_CONFIGURATION"

    if primary_layer == "SECURITY":
        return "SECURITY_REVIEW"

    if score >= 90:
        return "DIRECT_ADAPT"

    if score >= 80:
        return "INTEGRATE"

    if score >= 60:
        return "ADAPT"

    if score >= 40:
        return "PATTERN_EXTRACTION"

    return "ARCHIVE_REFERENCE"


def dependency_risk(record: dict) -> str:
    indicators = record.get("secret_indicators", [])

    if isinstance(indicators, int):
        count = indicators
    elif isinstance(indicators, list):
        count = len(indicators)
    else:
        count = 0

    path = str(
        record.get("repository_relative_path")
        or record.get("source_file")
        or ""
    ).lower()

    dangerous_terms = [
        "subprocess",
        "os.system",
        "shell=true",
        "eval(",
        "exec(",
        "powershell",
        "rm -rf",
        "delete",
        "credential",
        "token",
    ]

    if count >= 3:
        return "HIGH"

    if any(term in path for term in dangerous_terms):
        return "MEDIUM"

    return "LOW"


def file_family(path: str) -> str:
    extension = Path(path).suffix.lower()

    for family, extensions in EXTENSION_GROUPS.items():
        if extension in extensions:
            return family

    return "other"


def safe_relative(path: str) -> str:
    return path.replace("\\", "/").strip("/")


def build_record(index: int, record: dict) -> dict:
    source_path = (
        record.get("repository_relative_path")
        or record.get("source_file")
        or ""
    )

    capabilities = infer_capabilities(record)

    component_type = classify_component(record)

    primary_layer = choose_primary_layer(
        capabilities,
        component_type,
    )

    secondary_layers = choose_secondary_layers(
        capabilities,
        primary_layer,
    )

    action = integration_action(
        record,
        component_type,
        primary_layer,
    )

    risk = dependency_risk(record)

    return {
        "mapping_id": f"MAP-{index:05d}",
        "repository": record.get("repository"),
        "source_file": record.get("source_file"),
        "repository_relative_path": safe_relative(source_path),
        "staging_path": record.get("staging_path"),
        "extension": record.get("extension"),
        "file_family": file_family(source_path),
        "size_bytes": record.get("size_bytes", 0),
        "score": record.get("score", 0),
        "capabilities": capabilities,
        "capability_count": len(capabilities),
        "component_type": component_type,
        "primary_layer": primary_layer,
        "primary_layer_path": KAIRO_LAYERS[primary_layer],
        "secondary_layers": secondary_layers,
        "integration_action": action,
        "risk": risk,
        "source_protected": True,
        "production_modified": False,
        "archive_modified": False,
    }


def write_json(path: Path, data):
    with path.open("w", encoding="utf-8") as handle:
        json.dump(
            data,
            handle,
            indent=2,
            ensure_ascii=False,
        )


def write_report(
    mappings: list[dict],
    layer_counts: Counter,
    action_counts: Counter,
    risk_counts: Counter,
    capability_counts: Counter,
    type_counts: Counter,
):
    report = []

    report.append("# KAIRO ARCHITECTURE MAPPING REPORT")
    report.append("")
    report.append(
        f"Generated: {datetime.now().isoformat(timespec='seconds')}"
    )
    report.append("")
    report.append("## Status")
    report.append("")
    report.append("- Production KAIRO modified: **NO**")
    report.append("- Frozen archive modified: **NO**")
    report.append("- Source repositories modified: **NO**")
    report.append("- Extracted code executed: **NO**")
    report.append("")
    report.append("## Summary")
    report.append("")
    report.append(f"- Components mapped: **{len(mappings):,}**")
    report.append("")
    report.append("## Primary Layer Distribution")
    report.append("")

    for layer, count in layer_counts.most_common():
        report.append(f"- {layer}: {count:,}")

    report.append("")
    report.append("## Integration Actions")
    report.append("")

    for action, count in action_counts.most_common():
        report.append(f"- {action}: {count:,}")

    report.append("")
    report.append("## Risk Distribution")
    report.append("")

    for risk, count in risk_counts.most_common():
        report.append(f"- {risk}: {count:,}")

    report.append("")
    report.append("## Component Types")
    report.append("")

    for component_type, count in type_counts.most_common():
        report.append(f"- {component_type}: {count:,}")

    report.append("")
    report.append("## Capability Distribution")
    report.append("")

    for capability, count in capability_counts.most_common():
        report.append(f"- {capability}: {count:,}")

    report.append("")
    report.append("## Architecture")
    report.append("")
    report.append("```text")
    report.append("KAIRO")
    report.append("│")
    report.append("├── 00_FOUNDATION")
    report.append("├── 01_CORE")
    report.append("├── 02_AGENTS")
    report.append("├── 03_DATA")
    report.append("├── 04_TOOLS")
    report.append("├── 05_UI")
    report.append("├── 06_SECURITY")
    report.append("├── 07_RUNTIME")
    report.append("├── 08_BUSINESS")
    report.append("├── 09_INFRASTRUCTURE")
    report.append("└── 10_DOCUMENTATION")
    report.append("```")
    report.append("")
    report.append("## Integration Principle")
    report.append("")
    report.append(
        "The mapping is an architectural decision layer. "
        "It does not mean every mapped component will enter production KAIRO. "
        "Components may be integrated, adapted, converted into patterns, "
        "kept as reference material, or rejected during later validation."
    )
    report.append("")

    path = REPORT_DIR / "KAIRO_ARCHITECTURE_MAPPING_REPORT.md"

    path.write_text(
        "\n".join(report),
        encoding="utf-8",
    )


def main():
    print("=" * 62)
    print("KAIRO ARCHITECTURE MAPPING ENGINE V1")
    print("=" * 62)

    if not INPUT.exists():
        raise FileNotFoundError(
            f"Integration plan not found: {INPUT}"
        )

    plan = load_json(INPUT)

    # integration_plan.json may be either:
    # 1. a direct list of candidate records
    # 2. a dictionary containing candidates/records
    if isinstance(plan, list):
        candidates = plan

    elif isinstance(plan, dict):
        candidates = (
            plan.get("integration_candidates")
            or plan.get("candidates")
            or plan.get("records")
            or []
        )

        if isinstance(candidates, dict):
            candidates = list(candidates.values())

    else:
        raise TypeError(
            "Unsupported integration plan format: "
            f"{type(plan).__name__}"
        )

    print(f"Integration candidates : {len(candidates):,}")
    print("Production modified    : NO")
    print("Frozen archive modified: NO")
    print("Source repositories    : NO")
    print()

    mappings = []

    for index, record in enumerate(candidates, start=1):
        mappings.append(
            build_record(index, record)
        )

        if index % 100 == 0 or index == len(candidates):
            print(
                f"[{index:5d}/{len(candidates):5d}] "
                "MAPPED"
            )

    layer_counts = Counter(
        item["primary_layer"]
        for item in mappings
    )

    action_counts = Counter(
        item["integration_action"]
        for item in mappings
    )

    risk_counts = Counter(
        item["risk"]
        for item in mappings
    )

    type_counts = Counter(
        item["component_type"]
        for item in mappings
    )

    capability_counts = Counter()

    for item in mappings:
        for capability in item["capabilities"]:
            capability_counts[capability] += 1

    by_layer = defaultdict(list)

    for item in mappings:
        by_layer[item["primary_layer"]].append(
            item["mapping_id"]
        )

    architecture_map = {
        layer: {
            "path": KAIRO_LAYERS[layer],
            "component_count": len(
                by_layer.get(layer, [])
            ),
            "mapping_ids": by_layer.get(layer, []),
        }
        for layer in KAIRO_LAYERS
    }

    decisions = {
        "generated_at": datetime.now().isoformat(
            timespec="seconds"
        ),
        "status": "MAPPING_COMPLETE",
        "components_mapped": len(mappings),
        "production_modified": False,
        "archive_modified": False,
        "source_modified": False,
        "layers": dict(layer_counts),
        "actions": dict(action_counts),
        "risks": dict(risk_counts),
        "component_types": dict(type_counts),
    }

    write_json(
        ANALYSIS_DIR / "architecture_component_mapping.json",
        mappings,
    )

    write_json(
        MAP_DIR / "kairo_layer_map.json",
        architecture_map,
    )

    write_json(
        MAP_DIR / "kairo_capability_ownership.json",
        {
            "capabilities": dict(capability_counts),
            "ownership": {
                capability: CAPABILITY_LAYER_MAP.get(
                    capability,
                    "CORE",
                )
                for capability in capability_counts
            },
        },
    )

    write_json(
        DECISION_DIR / "architecture_decisions.json",
        decisions,
    )

    manifest = {
        "engine": "KAIRO Architecture Mapping Engine V1",
        "generated_at": datetime.now().isoformat(
            timespec="seconds"
        ),
        "input": str(INPUT),
        "output_root": str(OUTPUT_ROOT),
        "components_received": len(candidates),
        "components_mapped": len(mappings),
        "production_modified": False,
        "frozen_archive_modified": False,
        "source_repositories_modified": False,
        "extracted_code_executed": False,
    }

    write_json(
        MANIFEST_DIR / "ARCHITECTURE_MAPPING_MANIFEST.json",
        manifest,
    )

    write_report(
        mappings,
        layer_counts,
        action_counts,
        risk_counts,
        capability_counts,
        type_counts,
    )

    print()
    print("=" * 62)
    print("KAIRO ARCHITECTURE MAPPING COMPLETE")
    print("=" * 62)
    print(f"Components mapped : {len(mappings):,}")
    print()
    print("PRIMARY LAYERS")

    for layer, count in layer_counts.most_common():
        print(f"{layer:20s}: {count:,}")

    print()
    print("ACTIONS")

    for action, count in action_counts.most_common():
        print(f"{action:20s}: {count:,}")

    print()
    print("RISK")

    for risk, count in risk_counts.most_common():
        print(f"{risk:20s}: {count:,}")

    print()
    print("Production modified    : NO")
    print("Frozen archive modified: NO")
    print("Source repositories    : NO")
    print()
    print(
        "Manifest : "
        f"{MANIFEST_DIR / 'ARCHITECTURE_MAPPING_MANIFEST.json'}"
    )
    print(
        "Report   : "
        f"{REPORT_DIR / 'KAIRO_ARCHITECTURE_MAPPING_REPORT.md'}"
    )
    print()
    print("STATUS: PASS")
    print("NEXT: FINAL STAGING + VALIDATION")


if __name__ == "__main__":
    main()
