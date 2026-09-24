from pathlib import Path
from datetime import datetime
import shutil
import json
import hashlib

ROOT = Path(__file__).resolve().parents[1]

CANDIDATE = ROOT / "14_KAIRO_PRODUCTION_CANDIDATE"
PRODUCTION = ROOT
BACKUP_ROOT = ROOT / "15_ROLLBACK_SNAPSHOTS"

RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
MERGE_BACKUP = BACKUP_ROOT / f"MERGE_BACKUP_{RUN_ID}"

EXCLUDED_TOP = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "coverage",
    "11_ARCHIVE",
    "12_EXTRACTION",
    "13_FINAL_KAIRO",
    "14_KAIRO_PRODUCTION_CANDIDATE",
    "15_ROLLBACK_SNAPSHOTS",
}

print("=" * 70)
print("KAIRO CONTROLLED PRODUCTION MERGE V2")
print("=" * 70)

print()
print("SAFETY")
print("Production overwrite : DISABLED")
print("Deletion             : DISABLED")
print("Source repositories  : PROTECTED")
print("Frozen archive       : PROTECTED")
print("Code execution       : DISABLED")
print("Dependencies         : NOT INSTALLED")
print("Network              : NOT USED")
print()

if not CANDIDATE.exists():
    print("STATUS: FAIL")
    print("Production candidate missing.")
    raise SystemExit(1)

# ------------------------------------------------------------
# Determine candidate files
# ------------------------------------------------------------

candidate_files = []

for p in CANDIDATE.rglob("*"):
    if not p.is_file():
        continue

    rel = p.relative_to(CANDIDATE)

    if any(part in EXCLUDED_TOP for part in rel.parts):
        continue

    if rel.parts and rel.parts[0] in {"MANIFEST", "REPORTS"}:
        continue

    candidate_files.append(p)

print(
    f"Candidate files : {len(candidate_files):,}"
)

# ------------------------------------------------------------
# Merge backup
# ------------------------------------------------------------

MERGE_BACKUP.mkdir(
    parents=True,
    exist_ok=True
)

records = []

added = 0
identical = 0
conflicts = 0
errors = 0

for source in candidate_files:

    rel = source.relative_to(CANDIDATE)

    # Candidate structure becomes production structure.
    target = PRODUCTION / rel

    try:

        if not target.exists():

            target.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            shutil.copy2(source, target)

            records.append({
                "path": str(rel),
                "action": "ADDED",
            })

            added += 1

        else:

            # Compare hashes.
            def digest(path):
                h = hashlib.sha256()

                with path.open("rb") as f:
                    for chunk in iter(
                        lambda: f.read(1024 * 1024),
                        b""
                    ):
                        h.update(chunk)

                return h.hexdigest()

            source_hash = digest(source)
            target_hash = digest(target)

            if source_hash == target_hash:

                records.append({
                    "path": str(rel),
                    "action": "IDENTICAL_KEEP_EXISTING",
                })

                identical += 1

            else:

                # NEVER overwrite.
                backup_target = MERGE_BACKUP / rel

                backup_target.parent.mkdir(
                    parents=True,
                    exist_ok=True
                )

                shutil.copy2(
                    target,
                    backup_target
                )

                # Put candidate conflict in a separate area.
                conflict_target = (
                    MERGE_BACKUP /
                    "CONFLICT_CANDIDATES" /
                    rel
                )

                conflict_target.parent.mkdir(
                    parents=True,
                    exist_ok=True
                )

                shutil.copy2(
                    source,
                    conflict_target
                )

                records.append({
                    "path": str(rel),
                    "action": "CONFLICT_BACKED_UP",
                    "existing_backup":
                        str(backup_target),
                    "candidate_copy":
                        str(conflict_target),
                })

                conflicts += 1

    except Exception as exc:

        errors += 1

        records.append({
            "path": str(rel),
            "action": "ERROR",
            "error": str(exc),
        })

    total = added + identical + conflicts + errors

    if total % 100 == 0:
        print(
            f"[{total:5d}/{len(candidate_files):5d}] "
            f"ADD={added} "
            f"KEEP={identical} "
            f"CONFLICT={conflicts} "
            f"ERROR={errors}"
        )

# ------------------------------------------------------------
# Manifest
# ------------------------------------------------------------

manifest = {
    "type":
        "KAIRO_CONTROLLED_PRODUCTION_MERGE",

    "created_at":
        datetime.now().isoformat(
            timespec="seconds"
        ),

    "candidate":
        str(CANDIDATE),

    "production":
        str(PRODUCTION),

    "merge_backup":
        str(MERGE_BACKUP),

    "candidate_files":
        len(candidate_files),

    "added":
        added,

    "identical_kept":
        identical,

    "conflicts_backed_up":
        conflicts,

    "errors":
        errors,

    "production_overwrite":
        False,

    "deletion_performed":
        False,

    "source_modified":
        False,

    "archive_modified":
        False,

    "code_executed":
        False,

    "dependencies_installed":
        False,

    "network_used":
        False,

    "records":
        records,
}

manifest_path = (
    MERGE_BACKUP /
    "PRODUCTION_MERGE_MANIFEST.json"
)

manifest_path.write_text(
    json.dumps(
        manifest,
        indent=2,
        ensure_ascii=False
    ),
    encoding="utf-8"
)

print()
print("=" * 70)
print("KAIRO CONTROLLED MERGE COMPLETE")
print("=" * 70)

print(f"Candidate files       : {len(candidate_files):,}")
print(f"Added                 : {added:,}")
print(f"Identical kept        : {identical:,}")
print(f"Conflicts backed up   : {conflicts:,}")
print(f"Errors                : {errors:,}")

print()
print("SAFETY")
print("Deletion              : NONE")
print("Silent overwrite      : NONE")
print("Source repositories   : PROTECTED")
print("Frozen archive        : PROTECTED")
print("Code execution        : NONE")
print("Dependencies          : NONE")
print("Network               : NONE")

print()
print(f"Merge backup : {MERGE_BACKUP}")

if errors == 0:
    print()
    print("STATUS: PASS")
    print("NEXT: POST-MERGE VALIDATION")
else:
    print()
    print("STATUS: REVIEW_REQUIRED")
    print("NEXT: REVIEW MERGE ERRORS")

