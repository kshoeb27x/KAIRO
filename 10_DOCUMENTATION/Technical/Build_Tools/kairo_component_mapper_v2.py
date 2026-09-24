from pathlib import Path
import json
from collections import Counter, defaultdict
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]

INPUT = (
    ROOT
    / "12_EXTRACTION"
    / "CONSOLIDATION"
    / "DECISIONS"
    / "integration_plan.json"
)

OUTPUT_DIR = ROOT / "19_ARCHITECTURE"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 72)
print("KAIRO V1 INTELLIGENT COMPONENT MAPPER")
print("=" * 72)

if not INPUT.exists():
    raise SystemExit(f"Missing integration plan: {INPUT}")

data = json.loads(INPUT.read_text(encoding="utf-8"))

if isinstance(data, dict):
    records = (
        data.get("components")
        or data.get("candidates")
        or data.get("items")
        or []
    )
else:
    records = data

print(f"Components received : {len(records):,}")

architecture = {
    "01_CORE": {
        "ai": ["llm", "model", "inference"],
        "reasoning": ["reasoning"],
        "planning": ["planning"],
        "context": ["context"],
        "memory": ["memory"],
        "orchestration": ["orchestration", "agent"],
    },

    "02_AGENTS": {
        "research": ["research"],
        "coding": ["coding"],
        "data": ["data"],
        "finance": ["finance"],
        "trading": ["trading"],
        "operations": ["operations"],
        "security": ["security"],
    },

    "03_DATA": {
        "database": ["database", "db", "sql"],
        "knowledge": ["knowledge"],
        "rag": ["rag", "retrieval"],
        "vector": ["vector", "embedding"],
        "pipelines": ["pipeline", "etl"],
    },

    "04_TOOLS": {
        "browser": ["browser", "playwright", "selenium"],
        "computer_use": ["computer", "desktop", "gui"],
        "api": ["api", "http", "rest"],
        "mcp": ["mcp"],
        "automation": ["automation", "workflow"],
    },

    "05_UI": {
        "command_center": ["command", "chat"],
        "dashboard": ["dashboard", "ui"],
        "interfaces": ["interface", "frontend"],
    },

    "06_SECURITY": {
        "identity": ["identity", "auth"],
        "authority": ["authority", "approval"],
        "permissions": ["permission", "access"],
        "secrets": ["secret", "credential"],
        "sandbox": ["sandbox", "isolation"],
        "audit": ["audit", "logging"],
    },

    "07_RUNTIME": {
        "tasks": ["task"],
        "events": ["event", "bus"],
        "workflows": ["workflow"],
        "scheduler": ["scheduler", "schedule"],
        "state": ["state"],
        "execution": ["execution", "runner"],
    },

    "08_BUSINESS": {
        "finance": ["finance"],
        "trading": ["trading"],
        "research": ["research"],
        "operations": ["operations"],
    },

    "09_INTELLIGENCE": {
        "visual": ["visual", "vision", "image"],
        "analytics": ["analytics", "analysis"],
        "decision_support": ["decision"],
        "self_improvement": ["self", "evaluation", "reflection"],
    },

    "10_INFRASTRUCTURE": {
        "containers": ["container", "docker"],
        "storage": ["storage"],
        "monitoring": ["monitoring", "observability"],
        "deployment": ["deployment", "deploy"],
    },
}

def text_for(record):
    parts = []

    for key in (
        "source_file",
        "repository_relative_path",
        "component_type",
        "classification",
        "decision",
    ):
        value = record.get(key)
        if value:
            parts.append(str(value))

    caps = record.get("capabilities", [])
    if isinstance(caps, list):
        parts.extend(str(x) for x in caps)

    return " ".join(parts).lower()


def map_component(record):
    text = text_for(record)

    scores = defaultdict(int)

    for layer, modules in architecture.items():
        for module, keywords in modules.items():
            for keyword in keywords:
                if keyword in text:
                    scores[(layer, module)] += 1

    if not scores:
        return "01_CORE", "general", "REVIEW"

    best = max(scores, key=scores.get)
    layer, module = best
    score = scores[best]

    if score >= 2:
        action = "INTEGRATE_OR_ADAPT"
    else:
        action = "REVIEW"

    return layer, module, action


mapped = []
layer_counts = Counter()
module_counts = Counter()
action_counts = Counter()

for index, record in enumerate(records, start=1):
    layer, module, action = map_component(record)

    item = {
        "mapping_id": f"ARCH-{index:05d}",
        "repository": record.get("repository"),
        "source_file": record.get("source_file"),
        "repository_relative_path":
            record.get("repository_relative_path"),
        "component_type":
            record.get("component_type"),
        "capabilities":
            record.get("capabilities", []),
        "source_decision":
            record.get("decision"),
        "kairo_layer": layer,
        "kairo_module": module,
        "action": action,
    }

    mapped.append(item)

    layer_counts[layer] += 1
    module_counts[f"{layer}/{module}"] += 1
    action_counts[action] += 1

    if index % 250 == 0:
        print(f"[{index:5d}/{len(records):5d}] mapped")

report = {
    "type": "KAIRO_V1_INTELLIGENT_COMPONENT_MAPPING",
    "generated_at":
        datetime.now().isoformat(timespec="seconds"),

    "input": str(INPUT.relative_to(ROOT)),

    "architecture": architecture,

    "component_count": len(mapped),

    "layer_counts": dict(layer_counts),

    "module_counts": dict(module_counts),

    "action_counts": dict(action_counts),

    "components": mapped,

    "safety": {
        "production_modified": False,
        "source_modified": False,
        "archive_modified": False,
        "deletion": False,
        "code_execution": False,
        "dependency_installation": False,
        "network": False,
    },
}

json_path = OUTPUT_DIR / "KAIRO_V1_COMPONENT_MAP.json"

json_path.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

md = []

md.append("# KAIRO V1 Component Mapping")
md.append("")
md.append(
    f"Generated: {report['generated_at']}"
)
md.append("")
md.append(
    f"Components mapped: **{len(mapped):,}**"
)
md.append("")

md.append("## Architecture Layers")
md.append("")

for layer, count in layer_counts.most_common():
    md.append(f"- **{layer}** — {count:,}")

md.append("")
md.append("## Actions")
md.append("")

for action, count in action_counts.most_common():
    md.append(f"- **{action}** — {count:,}")

md.append("")
md.append("## Safety")
md.append("")
md.append("- Production modified: NO")
md.append("- Source repositories modified: NO")
md.append("- Frozen archive modified: NO")
md.append("- Deletion: NO")
md.append("- Code execution: NO")
md.append("- Dependency installation: NO")
md.append("- Network: NO")

(OUTPUT_DIR / "KAIRO_V1_COMPONENT_MAP.md").write_text(
    "\n".join(md),
    encoding="utf-8"
)

print()
print("=" * 72)
print("KAIRO V1 COMPONENT MAPPING COMPLETE")
print("=" * 72)
print(f"Components mapped : {len(mapped):,}")
print()
print("LAYERS")

for layer, count in layer_counts.most_common():
    print(f"{layer:<25}: {count:,}")

print()
print("ACTIONS")

for action, count in action_counts.most_common():
    print(f"{action:<25}: {count:,}")

print()
print("Production modified : NO")
print("Source modified     : NO")
print("Archive modified    : NO")
print("Deletion            : NO")
print()
print("STATUS: PASS")
print("NEXT: COMPONENT CONSOLIDATION INTO KAIRO V1")
print("=" * 72)
