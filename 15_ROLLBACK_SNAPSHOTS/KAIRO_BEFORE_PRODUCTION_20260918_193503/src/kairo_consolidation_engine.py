from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# ============================================================
# KAIRO CONSOLIDATION ENGINE V2
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

EXTRACTION_ROOT = PROJECT_ROOT / "12_EXTRACTION"

INPUT_FILE = (
    EXTRACTION_ROOT
    / "REPORTS"
    / "kairo_extraction_candidates.json"
)

OUTPUT_ROOT = (
    EXTRACTION_ROOT
    / "CONSOLIDATION"
)

ANALYSIS_ROOT = OUTPUT_ROOT / "ANALYSIS"
DECISIONS_ROOT = OUTPUT_ROOT / "DECISIONS"
REPORTS_ROOT = OUTPUT_ROOT / "REPORTS"
METADATA_ROOT = OUTPUT_ROOT / "METADATA"

for directory in [
    ANALYSIS_ROOT,
    DECISIONS_ROOT,
    REPORTS_ROOT,
    METADATA_ROOT,
]:
    directory.mkdir(
        parents=True,
        exist_ok=True
    )


# ============================================================
# CONFIG
# ============================================================

MIN_INTEGRATE_SCORE = 80
MIN_REVIEW_SCORE = 60
MIN_EXTRACT_SCORE = 40
MIN_ARCHIVE_SCORE = 20

MAX_INTEGRATION_PLAN = 5000


# ============================================================
# HELPERS
# ============================================================

def now() -> str:
    return datetime.now().isoformat(
        timespec="seconds"
    )


def normalize_name(path: str) -> str:

    name = Path(path).stem.lower()

    name = re.sub(
        r"[^a-z0-9]+",
        "_",
        name
    )

    return name.strip("_")


def capability_key(value: str) -> str:

    return re.sub(
        r"[^a-z0-9]+",
        "_",
        value.lower()
    ).strip("_")


def target_zone(capabilities: list[str]) -> str:

    caps = {
        capability_key(c)
        for c in capabilities
    }

    if "security" in caps:
        return "06_SECURITY"

    if "computer_use" in caps:
        return "04_TOOLS/Computer_Use"

    if "mcp" in caps:
        return "04_TOOLS/MCP"

    if "trading" in caps:
        return "08_BUSINESS/Trading"

    if "llm" in caps:
        return "01_CORE/AI"

    if "memory" in caps or "rag" in caps:
        return "01_CORE/Memory"

    if "agent" in caps:
        return "02_AGENTS"

    if "workflow" in caps or "automation" in caps:
        return "07_RUNTIME/Workflow"

    if "database" in caps or "data" in caps:
        return "03_DATA"

    if "api" in caps:
        return "04_TOOLS/APIs"

    if "ui" in caps:
        return "05_UI"

    if "voice" in caps:
        return "04_TOOLS/Voice"

    if "containers" in caps:
        return "09_INFRASTRUCTURE/Containers"

    if "observability" in caps:
        return "09_INFRASTRUCTURE/Monitoring"

    if "coding" in caps:
        return "02_AGENTS/Coding"

    return "GENERAL"


def classify_type(
    path: str,
    capabilities: list[str]
) -> str:

    lower = path.lower()

    caps = {
        capability_key(c)
        for c in capabilities
    }

    if any(
        x in lower
        for x in [
            "test_",
            "_test.",
            "/tests/",
            "\\tests\\",
        ]
    ):
        return "TEST"

    if lower.endswith(
        (
            ".yaml",
            ".yml",
            ".toml",
            ".json",
        )
    ):
        return "CONFIGURATION"

    if "security" in caps:
        return "SECURITY"

    if "computer_use" in caps:
        return "COMPUTER_CONTROL"

    if "agent" in caps:
        return "AGENT"

    if "memory" in caps or "rag" in caps:
        return "KNOWLEDGE"

    if "workflow" in caps or "automation" in caps:
        return "WORKFLOW"

    if "llm" in caps:
        return "MODEL"

    if "trading" in caps:
        return "TRADING"

    if "api" in caps:
        return "API"

    if "ui" in caps:
        return "INTERFACE"

    if "data" in caps or "database" in caps:
        return "DATA"

    return "GENERAL"


def decision_for(
    score: float,
    component_type: str
) -> str:

    if component_type == "TEST":
        return "EXTRACT_PATTERNS"

    if score >= MIN_INTEGRATE_SCORE:
        return "INTEGRATE_CANDIDATE"

    if score >= MIN_REVIEW_SCORE:
        return "REVIEW_AND_ADAPT"

    if score >= MIN_EXTRACT_SCORE:
        return "EXTRACT_PATTERNS"

    if score >= MIN_ARCHIVE_SCORE:
        return "ARCHIVE_REFERENCE"

    return "REJECT_FROM_CORE"


def quality_score(
    record: dict
) -> float:

    score = float(
        record.get(
            "score",
            0
        ) or 0
    )

    capabilities = record.get(
        "capabilities",
        []
    )

    capability_count = len(
        capabilities
    )

    extension = str(
        record.get(
            "extension",
            ""
        )
    ).lower()

    path = str(
        record.get(
            "source_file",
            ""
        )
    ).lower()

    # Capability richness
    score += min(
        capability_count * 2,
        30
    )

    # Prefer implementation source files
    if extension in {
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".go",
        ".rs",
    }:
        score += 8

    # Tests/configs are useful but not direct core integrations
    if (
        "/test" in path
        or "\\test" in path
    ):
        score -= 25

    if extension in {
        ".json",
        ".yaml",
        ".yml",
        ".toml",
    }:
        score -= 10

    # Penalize obvious generated/vendor material
    bad_terms = [
        "node_modules",
        ".venv",
        "__pycache__",
        "dist/",
        "build/",
        ".next/",
        "coverage/",
        "vendor/",
        "lockfile",
    ]

    for term in bad_terms:
        if term in path:
            score -= 50

    return round(
        max(score, 0),
        2
    )


def sha256_text(value: str) -> str:

    return hashlib.sha256(
        value.encode(
            "utf-8",
            errors="ignore"
        )
    ).hexdigest()


# ============================================================
# VALIDATE INPUT
# ============================================================

if not INPUT_FILE.exists():

    raise SystemExit(
        f"Extraction input missing:\n{INPUT_FILE}"
    )


print()
print("=" * 70)
print(" KAIRO CONSOLIDATION ENGINE V2")
print("=" * 70)
print()
print(
    f"Input: {INPUT_FILE}"
)
print()


# ============================================================
# LOAD EXTRACTION DATA
# ============================================================

with INPUT_FILE.open(
    "r",
    encoding="utf-8"
) as handle:

    candidates = json.load(
        handle
    )


if not isinstance(
    candidates,
    list
):

    raise SystemExit(
        "Extraction candidate file must contain a JSON array."
    )


print(
    f"Extraction records : {len(candidates):,}"
)


# ============================================================
# NORMALIZE RECORDS
# ============================================================

records = []

for index, raw in enumerate(
    candidates,
    start=1
):

    if not isinstance(
        raw,
        dict
    ):
        continue

    source = raw.get(
        "source_file"
    )

    if not source:
        continue

    capabilities = raw.get(
        "capabilities",
        []
    )

    if not isinstance(
        capabilities,
        list
    ):
        capabilities = []

    score = quality_score(
        raw
    )

    component_type = classify_type(
        source,
        capabilities
    )

    decision = decision_for(
        score,
        component_type
    )

    record = {
        "id": f"component_{index:06d}",

        "repository":
            raw.get(
                "repository"
            ),

        "source_file":
            source,

        "repository_relative_path":
            raw.get(
                "repository_relative_path"
            ),

        "extension":
            raw.get(
                "extension"
            ),

        "size_bytes":
            raw.get(
                "size_bytes",
                0
            ),

        "sha256":
            raw.get(
                "sha256"
            ),

        "capabilities":
            capabilities,

        "capability_count":
            len(capabilities),

        "original_score":
            raw.get(
                "score",
                0
            ),

        "consolidation_score":
            score,

        "secret_indicators":
            raw.get(
                "secret_indicators",
                []
            ),

        "python_symbols":
            raw.get(
                "python_symbols",
                []
            ),

        "staging_path":
            raw.get(
                "staging_path"
            ),

        "component_type":
            component_type,

        "target_zone":
            target_zone(
                capabilities
            ),

        "decision":
            decision,

        "normalized_name":
            normalize_name(
                source
            ),

        "source_fingerprint":
            sha256_text(
                str(
                    raw.get(
                        "sha256",
                        source
                    )
                )
            ),
    }

    records.append(
        record
    )

    if index % 5000 == 0:

        print(
            f"Processed: {index:,} / "
            f"{len(candidates):,}"
        )


print()
print(
    f"Normalized records : {len(records):,}"
)


# ============================================================
# EXACT DUPLICATES
# ============================================================

hash_groups = defaultdict(list)

for record in records:

    digest = record.get(
        "sha256"
    )

    if digest:
        hash_groups[digest].append(
            record["id"]
        )


exact_duplicates = {
    digest: ids
    for digest, ids
    in hash_groups.items()
    if len(ids) > 1
}


# ============================================================
# NAME OVERLAPS
# ============================================================

name_groups = defaultdict(list)

for record in records:

    name_groups[
        record["normalized_name"]
    ].append(
        record["id"]
    )


name_overlaps = {
    name: ids
    for name, ids
    in name_groups.items()
    if name and len(ids) > 1
}


# ============================================================
# BEST BY CAPABILITY
# ============================================================

capability_groups = defaultdict(
    list
)

for record in records:

    for capability in record[
        "capabilities"
    ]:

        capability_groups[
            capability
        ].append(
            record
        )


best_by_capability = {}

for capability, items in (
    capability_groups.items()
):

    ranked = sorted(
        items,
        key=lambda x: (
            x["consolidation_score"],
            x["capability_count"],
            -x["size_bytes"],
        ),
        reverse=True
    )

    best_by_capability[
        capability
    ] = [
        {
            "id": item["id"],
            "repository":
                item["repository"],
            "source_file":
                item["source_file"],
            "score":
                item["consolidation_score"],
            "decision":
                item["decision"],
            "target_zone":
                item["target_zone"],
        }
        for item in ranked[:25]
    ]


# ============================================================
# INTEGRATION PLAN
# ============================================================

decision_priority = {
    "INTEGRATE_CANDIDATE": 5,
    "REVIEW_AND_ADAPT": 4,
    "EXTRACT_PATTERNS": 3,
    "ARCHIVE_REFERENCE": 2,
    "REJECT_FROM_CORE": 1,
}


integration_candidates = [
    record
    for record in records
    if record["decision"]
    in {
        "INTEGRATE_CANDIDATE",
        "REVIEW_AND_ADAPT",
    }
]


integration_candidates.sort(
    key=lambda x: (
        decision_priority.get(
            x["decision"],
            0
        ),
        x["consolidation_score"],
        x["capability_count"],
    ),
    reverse=True
)


integration_plan = []

seen_hashes = set()

for record in integration_candidates:

    digest = record.get(
        "sha256"
    )

    if digest and digest in seen_hashes:
        continue

    if digest:
        seen_hashes.add(
            digest
        )

    integration_plan.append({
        "id":
            record["id"],

        "repository":
            record["repository"],

        "source_file":
            record["source_file"],

        "repository_relative_path":
            record[
                "repository_relative_path"
            ],

        "extension":
            record["extension"],

        "sha256":
            record["sha256"],

        "capabilities":
            record["capabilities"],

        "capability_count":
            record["capability_count"],

        "score":
            record["consolidation_score"],

        "component_type":
            record["component_type"],

        "target_zone":
            record["target_zone"],

        "decision":
            record["decision"],

        "secret_indicators":
            record["secret_indicators"],

        "staging_path":
            record["staging_path"],

        "integration_status":
            "PENDING_SECURITY_REVIEW",
    })

    if len(
        integration_plan
    ) >= MAX_INTEGRATION_PLAN:

        break


# ============================================================
# DECISION SUMMARY
# ============================================================

decision_summary = defaultdict(int)

for record in records:

    decision_summary[
        record["decision"]
    ] += 1


type_summary = defaultdict(int)

for record in records:

    type_summary[
        record["component_type"]
    ] += 1


zone_summary = defaultdict(int)

for record in records:

    zone_summary[
        record["target_zone"]
    ] += 1


# ============================================================
# WRITE OUTPUTS
# ============================================================

def write_json(
    path: Path,
    data
):

    with path.open(
        "w",
        encoding="utf-8"
    ) as handle:

        json.dump(
            data,
            handle,
            indent=2
        )


write_json(
    ANALYSIS_ROOT
    / "component_records.json",
    records
)

write_json(
    ANALYSIS_ROOT
    / "component_analysis.json",
    {
        "generated_at": now(),
        "input_records":
            len(candidates),
        "normalized_records":
            len(records),
        "decision_summary":
            dict(decision_summary),
        "component_types":
            dict(type_summary),
        "target_zones":
            dict(zone_summary),
    }
)

write_json(
    ANALYSIS_ROOT
    / "exact_duplicates.json",
    exact_duplicates
)

write_json(
    ANALYSIS_ROOT
    / "name_overlaps.json",
    name_overlaps
)

write_json(
    ANALYSIS_ROOT
    / "best_by_capability.json",
    best_by_capability
)

write_json(
    DECISIONS_ROOT
    / "integration_plan.json",
    integration_plan
)


# ============================================================
# MANIFEST
# ============================================================

manifest = {
    "engine":
        "KAIRO Consolidation Engine",
    "version":
        "V2",
    "generated_at":
        now(),

    "input":
        str(INPUT_FILE),

    "input_records":
        len(candidates),

    "normalized_records":
        len(records),

    "integration_candidates":
        len(integration_plan),

    "exact_duplicate_groups":
        len(exact_duplicates),

    "name_overlap_groups":
        len(name_overlaps),

    "decision_summary":
        dict(decision_summary),

    "component_types":
        dict(type_summary),

    "target_zones":
        dict(zone_summary),

    "production_modified":
        False,

    "source_repositories_modified":
        False,

    "frozen_archive_modified":
        False,
}


write_json(
    METADATA_ROOT
    / "CONSOLIDATION_MANIFEST.json",
    manifest
)


# ============================================================
# REPORT
# ============================================================

report = [
    "# KAIRO Consolidation Engine V2 Report",
    "",
    f"Generated: `{now()}`",
    "",
    "## Input",
    "",
    f"- Extraction records: **{len(candidates):,}**",
    f"- Normalized records: **{len(records):,}**",
    "",
    "## Decisions",
    "",
]

for key in [
    "INTEGRATE_CANDIDATE",
    "REVIEW_AND_ADAPT",
    "EXTRACT_PATTERNS",
    "ARCHIVE_REFERENCE",
    "REJECT_FROM_CORE",
]:

    report.append(
        f"- `{key}`: "
        f"**{decision_summary.get(key, 0):,}**"
    )


report.extend([
    "",
    "## Integration Plan",
    "",
    f"- Candidates: **{len(integration_plan):,}**",
    f"- Exact duplicate groups: **{len(exact_duplicates):,}**",
    f"- Name overlap groups: **{len(name_overlaps):,}**",
    "",
    "## Target Zones",
    "",
])

for zone, count in sorted(
    zone_summary.items(),
    key=lambda x: x[1],
    reverse=True
):

    report.append(
        f"- `{zone}`: **{count:,}**"
    )


report.extend([
    "",
    "## Safety",
    "",
    "- Source repositories modified: **NO**",
    "- Frozen archive modified: **NO**",
    "- Production KAIRO modified: **NO**",
    "- Extracted code executed: **NO**",
    "",
    "## Next Phase",
    "",
    "**KAIRO Integration Builder V1**",
])


(
    REPORTS_ROOT
    / "KAIRO_CONSOLIDATION_REPORT.md"
).write_text(
    "\n".join(report),
    encoding="utf-8"
)


# ============================================================
# FINAL
# ============================================================

print()
print("=" * 70)
print(" KAIRO CONSOLIDATION V2 COMPLETE")
print("=" * 70)
print()

print(
    f"Input records          : "
    f"{len(candidates):,}"
)

print(
    f"Normalized records     : "
    f"{len(records):,}"
)

print(
    f"Integration candidates : "
    f"{len(integration_plan):,}"
)

print(
    f"Exact duplicate groups : "
    f"{len(exact_duplicates):,}"
)

print(
    f"Name overlap groups    : "
    f"{len(name_overlaps):,}"
)

print()
print("DECISIONS")
print("-" * 45)

for key in [
    "INTEGRATE_CANDIDATE",
    "REVIEW_AND_ADAPT",
    "EXTRACT_PATTERNS",
    "ARCHIVE_REFERENCE",
    "REJECT_FROM_CORE",
]:

    print(
        f"{key:<25}: "
        f"{decision_summary.get(key, 0):,}"
    )

print()
print("OUTPUT")
print("-" * 45)

print(
    DECISIONS_ROOT
    / "integration_plan.json"
)

print(
    REPORTS_ROOT
    / "KAIRO_CONSOLIDATION_REPORT.md"
)

print()
print(
    "Production KAIRO modified : NO"
)

print(
    "Frozen archive modified   : NO"
)

print()
print(
    "NEXT: KAIRO INTEGRATION BUILDER V1"
)

print("=" * 70)
