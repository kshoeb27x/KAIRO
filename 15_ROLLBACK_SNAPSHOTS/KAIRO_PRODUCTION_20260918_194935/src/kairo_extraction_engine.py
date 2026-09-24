from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


# ============================================================
# KAIRO EXTRACTION ENGINE V1
# ============================================================
#
# PURPOSE
# -------
# Read-only extraction/staging engine for KAIRO.
#
# It:
#   1. Scans all source repositories.
#   2. Identifies useful component candidates.
#   3. Scores files by KAIRO capability.
#   4. Preserves source attribution.
#   5. Copies selected candidates into 12_EXTRACTION.
#   6. Generates manifests and reports.
#
# SAFETY
# ------
# - Never modifies source repositories.
# - Never executes repository code.
# - Never deletes source files.
# - Never modifies 11_ARCHIVE.
# - Skips generated environments/build artifacts.
# - Secret matches are indicators only.
#
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_ROOT = (
    PROJECT_ROOT
    / "00_FOUNDATION"
    / "Architecture"
    / "Old_Repositories"
)

EXTRACTION_ROOT = PROJECT_ROOT / "12_EXTRACTION"

STAGING_ROOT = EXTRACTION_ROOT / "STAGING"
REPORT_ROOT = EXTRACTION_ROOT / "REPORTS"
METADATA_ROOT = EXTRACTION_ROOT / "METADATA"


SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".cache",
    "coverage",
    "target",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".idea",
    ".vscode",
    "site-packages",
    "vendor",
}


SKIP_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".whl",
    ".so",
    ".dll",
    ".exe",
    ".bin",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".mp4",
    ".mov",
    ".avi",
    ".zip",
    ".7z",
    ".rar",
    ".tar",
    ".gz",
    ".pdf",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
}


CAPABILITY_PATTERNS = {
    "LLM": [
        r"\bopenai\b",
        r"\banthropic\b",
        r"\bgemini\b",
        r"\bollama\b",
        r"\bvllm\b",
        r"\bllm\b",
        r"\bchatcompletion\b",
        r"\binference\b",
        r"\btransformer\b",
    ],

    "Agent": [
        r"\bagent\b",
        r"\bsubagent\b",
        r"\bmulti.?agent\b",
        r"\bautonomous\b",
        r"\bagentic\b",
    ],

    "Memory": [
        r"\bmemory\b",
        r"\bmem0\b",
        r"\bmemu\b",
        r"\blong.?term memory\b",
        r"\bepisodic memory\b",
        r"\bsemantic memory\b",
    ],

    "RAG": [
        r"\brag\b",
        r"\bretrieval\b",
        r"\bretriever\b",
        r"\bvector.?store\b",
        r"\bembedding\b",
        r"\bknowledge base\b",
    ],

    "Database": [
        r"\bpostgresql\b",
        r"\bpostgres\b",
        r"\bsqlite\b",
        r"\bmysql\b",
        r"\bmongodb\b",
        r"\bredis\b",
        r"\bdatabase\b",
        r"\bsqlalchemy\b",
    ],

    "Tools": [
        r"\btool calling\b",
        r"\bfunction calling\b",
        r"\btool registry\b",
        r"\btool executor\b",
        r"\btool\b",
    ],

    "MCP": [
        r"\bmodel context protocol\b",
        r"\bmcp\b",
        r"\bmcp server\b",
        r"\bmcp client\b",
    ],

    "Browser": [
        r"\bplaywright\b",
        r"\bselenium\b",
        r"\bbrowser.?use\b",
        r"\bbrowser automation\b",
        r"\bchromium\b",
    ],

    "Computer Use": [
        r"\bcomputer use\b",
        r"\bdesktop automation\b",
        r"\bpyautogui\b",
        r"\bxdotool\b",
        r"\bscreen control\b",
        r"\bmouse\b",
        r"\bkeyboard automation\b",
    ],

    "Workflow": [
        r"\bworkflow\b",
        r"\borchestrat",
        r"\bscheduler\b",
        r"\bpipeline\b",
        r"\btask queue\b",
        r"\bjob queue\b",
    ],

    "API": [
        r"\bfastapi\b",
        r"\bflask\b",
        r"\bdjango\b",
        r"\brest api\b",
        r"\bgraphql\b",
        r"\bhttp server\b",
    ],

    "Security": [
        r"\bauth\b",
        r"\boauth\b",
        r"\bpermission\b",
        r"\bsandbox\b",
        r"\bsecret\b",
        r"\bcredential\b",
        r"\bsecurity\b",
        r"\bencryption\b",
        r"\brbac\b",
    ],

    "Voice": [
        r"\bwhisper\b",
        r"\bspeech.?to.?text\b",
        r"\btext.?to.?speech\b",
        r"\btts\b",
        r"\bstt\b",
        r"\bvoice\b",
    ],

    "UI": [
        r"\breact\b",
        r"\bnext\.?js\b",
        r"\bvue\b",
        r"\bsvelte\b",
        r"\bstreamlit\b",
        r"\bgradio\b",
        r"\bwebui\b",
        r"\bfrontend\b",
    ],

    "Coding": [
        r"\bcode.?agent\b",
        r"\bcoding agent\b",
        r"\bdeveloper agent\b",
        r"\bcompiler\b",
        r"\blinter\b",
        r"\bpytest\b",
        r"\bunit test\b",
        r"\bcode generation\b",
    ],

    "Data": [
        r"\bpandas\b",
        r"\bpolars\b",
        r"\bnumpy\b",
        r"\bdata pipeline\b",
        r"\betl\b",
        r"\bdata ingestion\b",
    ],

    "Automation": [
        r"\bautomation\b",
        r"\bintegration\b",
        r"\bwebhook\b",
        r"\bcron\b",
        r"\bn8n\b",
    ],

    "Containers": [
        r"\bdocker\b",
        r"\bcontainer\b",
        r"\bkubernetes\b",
        r"\bsandbox\b",
    ],

    "Observability": [
        r"\blogging\b",
        r"\btelemetry\b",
        r"\btracing\b",
        r"\bmetrics\b",
        r"\bmonitoring\b",
        r"\bopentelemetry\b",
    ],
}


SECRET_PATTERNS = [
    r"(?i)\bapi[\-_]?key\b",
    r"(?i)\bsecret[\-_]?key\b",
    r"(?i)\baccess[\-_]?token\b",
    r"(?i)\bprivate[\-_]?key\b",
    r"(?i)\bpassword\b",
    r"(?i)\bpasswd\b",
    r"(?i)\bclient[_\-]?secret\b",
    r"(?i)\baws[_\-]?access[_\-]?key[_\-]?id\b",
    r"(?i)\baws[_\-]?secret[_\-]?access[_\-]?key\b",
    r"-----BEGIN .*PRIVATE KEY-----",
]


TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".md",
    ".txt",
    ".rst",
    ".html",
    ".css",
    ".scss",
    ".sh",
    ".ps1",
    ".bat",
    ".cmd",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".sql",
    ".xml",
    ".env.example",
}


IMPORTANT_FILENAMES = {
    "README.md",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
}


# ============================================================
# HELPERS
# ============================================================


def now():
    return datetime.now(timezone.utc).isoformat()


def safe_read(path: Path, max_bytes: int = 2_000_000) -> str:
    try:
        if path.stat().st_size > max_bytes:
            return ""

        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )

    except (
        OSError,
        PermissionError,
        UnicodeError,
    ):
        return ""


def sha256(path: Path) -> str | None:
    try:
        h = hashlib.sha256()

        with path.open("rb") as f:
            while True:
                chunk = f.read(1024 * 1024)

                if not chunk:
                    break

                h.update(chunk)

        return h.hexdigest()

    except (
        OSError,
        PermissionError,
    ):
        return None


def iter_files(root: Path):
    if not root.exists():
        return

    for current_root, dirs, files in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        dirs[:] = [
            d for d in dirs
            if d not in SKIP_DIRS
        ]

        current = Path(current_root)

        for filename in files:
            path = current / filename

            try:
                if path.is_symlink():
                    continue

                if not path.exists():
                    continue

                if not path.is_file():
                    continue

                if path.suffix.lower() in SKIP_EXTENSIONS:
                    continue

                yield path

            except (
                OSError,
                PermissionError,
                FileNotFoundError,
            ):
                continue


def python_symbols(text: str):
    result = {
        "classes": [],
        "functions": [],
        "imports": [],
    }

    try:
        tree = ast.parse(text)
    except Exception:
        return result

    for node in ast.walk(tree):

        if isinstance(node, ast.ClassDef):
            result["classes"].append(node.name)

        elif isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            result["functions"].append(node.name)

        elif isinstance(node, ast.Import):
            result["imports"].extend(
                alias.name
                for alias in node.names
            )

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                result["imports"].append(node.module)

    return result


def detect_capabilities(text: str):
    found = []

    if not text:
        return found

    lower = text.lower()

    for capability, patterns in CAPABILITY_PATTERNS.items():

        for pattern in patterns:

            try:
                if re.search(
                    pattern,
                    lower,
                ):
                    found.append(capability)
                    break

            except re.error:
                continue

    return found


def secret_indicators(text: str):
    hits = []

    if not text:
        return hits

    for pattern in SECRET_PATTERNS:

        try:
            matches = re.findall(
                pattern,
                text,
            )

            if matches:
                hits.append({
                    "pattern": pattern,
                    "count": len(matches),
                })

        except re.error:
            continue

    return hits


def score_file(
    path: Path,
    capabilities: list[str],
    text: str,
):
    score = 0

    # Capability value
    score += len(set(capabilities)) * 5

    # Important source-code files
    if path.suffix.lower() in {
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".rs",
        ".go",
    }:
        score += 3

    # Tests are valuable
    if (
        "test" in path.name.lower()
        or "tests" in path.parts
    ):
        score += 3

    # Important documentation/config
    if path.name in IMPORTANT_FILENAMES:
        score += 2

    # Python structural value
    if path.suffix.lower() == ".py":
        symbols = python_symbols(text)

        score += min(
            len(symbols["classes"]),
            5,
        )

        score += min(
            len(symbols["functions"]),
            10,
        )

    # Penalize obvious examples/demos
    lowered = str(path).lower()

    if any(
        word in lowered
        for word in [
            "/example/",
            "/examples/",
            "/demo/",
            "/demos/",
            "/playground/",
        ]
    ):
        score -= 2

    # Penalize generated-looking files
    if any(
        word in lowered
        for word in [
            ".min.",
            ".generated.",
            ".lock",
        ]
    ):
        score -= 3

    return max(score, 0)


def safe_destination(
    source_root: Path,
    source_file: Path,
):
    relative = source_file.relative_to(
        source_root
    )

    repo_name = relative.parts[0]

    repo_relative = Path(
        *relative.parts[1:]
    )

    return (
        STAGING_ROOT
        / repo_name
        / repo_relative
    )


# ============================================================
# MAIN EXTRACTION
# ============================================================


def main():

    print()
    print("=" * 64)
    print(" KAIRO EXTRACTION ENGINE V1")
    print("=" * 64)
    print()

    print("Mode       : READ-ONLY EXTRACTION")
    print("Source     :", SOURCE_ROOT)
    print("Workspace  :", EXTRACTION_ROOT)
    print()

    if not SOURCE_ROOT.exists():

        raise SystemExit(
            f"Source repository directory not found:\n"
            f"{SOURCE_ROOT}"
        )

    # Create only KAIRO extraction directories.
    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    STAGING_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    METADATA_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    repositories = sorted(
        [
            p
            for p in SOURCE_ROOT.iterdir()
            if p.is_dir()
        ],
        key=lambda p: p.name.lower(),
    )

    print(
        f"Repositories detected: {len(repositories)}"
    )
    print()

    all_candidates = []
    repository_summary = []

    capability_counter = Counter()
    extension_counter = Counter()

    total_files = 0
    total_bytes = 0
    unreadable = 0

    # --------------------------------------------------------
    # SCAN
    # --------------------------------------------------------

    for index, repo in enumerate(
        repositories,
        start=1,
    ):

        print(
            f"[{index}/{len(repositories)}] "
            f"Scanning: {repo.name}"
        )

        repo_files = 0
        repo_bytes = 0
        repo_candidates = 0
        repo_capabilities = Counter()
        repo_secrets = 0

        for path in iter_files(repo):

            try:
                size = path.stat().st_size

            except (
                OSError,
                PermissionError,
                FileNotFoundError,
            ):
                unreadable += 1
                continue

            repo_files += 1
            repo_bytes += size

            total_files += 1
            total_bytes += size

            extension = (
                path.suffix.lower()
                or "[no extension]"
            )

            extension_counter[extension] += 1

            text = ""

            if (
                path.suffix.lower()
                in TEXT_EXTENSIONS
            ):
                text = safe_read(path)

            capabilities = detect_capabilities(
                text
            )

            for capability in capabilities:
                capability_counter[
                    capability
                ] += 1

                repo_capabilities[
                    capability
                ] += 1

            secrets = secret_indicators(
                text
            )

            repo_secrets += len(secrets)

            score = score_file(
                path,
                capabilities,
                text,
            )

            # Candidate threshold
            if score >= 5:

                relative = path.relative_to(
                    SOURCE_ROOT
                ).as_posix()

                repo_relative = path.relative_to(
                    repo
                ).as_posix()

                symbols = {}

                if (
                    path.suffix.lower()
                    == ".py"
                    and text
                ):
                    symbols = python_symbols(
                        text
                    )

                candidate = {
                    "repository": repo.name,
                    "source_file": relative,
                    "repository_relative_path": repo_relative,
                    "extension": extension,
                    "size_bytes": size,
                    "sha256": sha256(path),
                    "capabilities": capabilities,
                    "capability_count": len(
                        capabilities
                    ),
                    "score": score,
                    "secret_indicators": secrets,
                    "python_symbols": symbols,
                    "staging_path": str(
                        safe_destination(
                            SOURCE_ROOT,
                            path,
                        )
                    ),
                }

                all_candidates.append(
                    candidate
                )

                repo_candidates += 1

        repository_summary.append({
            "repository": repo.name,
            "files": repo_files,
            "size_bytes": repo_bytes,
            "candidate_files": repo_candidates,
            "capabilities": dict(
                repo_capabilities.most_common()
            ),
            "secret_indicator_files": repo_secrets,
        })

        print(
            f"  Files       : {repo_files:,}"
        )

        print(
            f"  Candidates  : {repo_candidates:,}"
        )

        print(
            f"  Size        : {repo_bytes:,} bytes"
        )

    # --------------------------------------------------------
    # SORT BEST CANDIDATES
    # --------------------------------------------------------

    all_candidates.sort(
        key=lambda item: (
            item["score"],
            item["capability_count"],
            item["size_bytes"],
        ),
        reverse=True,
    )

    # --------------------------------------------------------
    # DUPLICATES
    # --------------------------------------------------------

    hash_groups = {}

    for candidate in all_candidates:

        digest = candidate.get(
            "sha256"
        )

        if not digest:
            continue

        hash_groups.setdefault(
            digest,
            [],
        ).append(candidate)

    duplicate_groups = [
        {
            "sha256": digest,
            "files": [
                {
                    "repository": c[
                        "repository"
                    ],
                    "source_file": c[
                        "source_file"
                    ],
                    "score": c[
                        "score"
                    ],
                }
                for c in candidates
            ],
        }
        for digest, candidates
        in hash_groups.items()
        if len(candidates) > 1
    ]

    # --------------------------------------------------------
    # STAGE CANDIDATES
    # --------------------------------------------------------

    print()
    print(
        "Staging high-value candidates..."
    )
    print()

    staged = 0
    failed_stage = 0

    # Limit is intentionally high.
    # We are NOT artificially limiting useful components.
    MAX_STAGE = 5000

    for candidate in all_candidates[
        :MAX_STAGE
    ]:

        source = (
            SOURCE_ROOT
            / candidate["source_file"]
        )

        destination = Path(
            candidate["staging_path"]
        )

        try:

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copy2(
                source,
                destination,
            )

            staged += 1

        except (
            OSError,
            PermissionError,
            shutil.Error,
        ):

            failed_stage += 1

    # --------------------------------------------------------
    # BUILD MASTER REPORT
    # --------------------------------------------------------

    report = {

        "project": "KAIRO",

        "engine": {
            "name": "KAIRO Extraction Engine",
            "version": "V1",
            "mode": "READ_ONLY_EXTRACTION",
        },

        "generated_at": now(),

        "source_root": str(
            SOURCE_ROOT
        ),

        "extraction_root": str(
            EXTRACTION_ROOT
        ),

        "safety": {
            "source_modified": False,
            "source_deleted": False,
            "source_executed": False,
            "archive_modified": False,
            "secret_indicators_only": True,
        },

        "global": {

            "repositories": len(
                repositories
            ),

            "files_scanned": total_files,

            "total_bytes": total_bytes,

            "unreadable_files": unreadable,

            "candidate_files": len(
                all_candidates
            ),

            "staged_files": staged,

            "failed_staging": failed_stage,

            "duplicate_groups": len(
                duplicate_groups
            ),

            "capabilities": dict(
                capability_counter.most_common()
            ),

            "extensions": dict(
                extension_counter.most_common()
            ),
        },

        "repositories":
            repository_summary,

        "candidates":
            all_candidates,

        "duplicates":
            duplicate_groups,

    }

    # --------------------------------------------------------
    # WRITE REPORTS
    # --------------------------------------------------------

    analysis_path = (
        REPORT_ROOT
        / "kairo_extraction_analysis.json"
    )

    candidates_path = (
        REPORT_ROOT
        / "kairo_extraction_candidates.json"
    )

    duplicates_path = (
        REPORT_ROOT
        / "kairo_extraction_duplicates.json"
    )

    manifest_path = (
        METADATA_ROOT
        / "EXTRACTION_MANIFEST.json"
    )

    analysis_path.write_text(
        json.dumps(
            report,
            indent=2,
        ),
        encoding="utf-8",
    )

    candidates_path.write_text(
        json.dumps(
            all_candidates,
            indent=2,
        ),
        encoding="utf-8",
    )

    duplicates_path.write_text(
        json.dumps(
            duplicate_groups,
            indent=2,
        ),
        encoding="utf-8",
    )

    manifest = {

        "project": "KAIRO",

        "generated_at": now(),

        "engine": "KAIRO Extraction Engine V1",

        "source_root": str(
            SOURCE_ROOT
        ),

        "staging_root": str(
            STAGING_ROOT
        ),

        "rules": [
            "Extract components, not entire repositories.",
            "Preserve source attribution.",
            "Do not modify source repositories.",
            "Do not modify frozen archive.",
            "Do not execute imported code.",
            "Review duplicates before integration.",
            "Review security indicators before activation.",
            "Generated environments remain excluded.",
        ],

        "staged_files": staged,

        "failed_staging": failed_stage,

        "candidate_count": len(
            all_candidates
        ),

        "top_candidates": [
            {
                "repository":
                    c["repository"],

                "source_file":
                    c["source_file"],

                "score":
                    c["score"],

                "capabilities":
                    c["capabilities"],

            }
            for c in all_candidates[:200]
        ],
    }

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
        ),
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # MARKDOWN REPORT
    # --------------------------------------------------------

    md_path = (
        REPORT_ROOT
        / "KAIRO_EXTRACTION_REPORT.md"
    )

    md = []

    md.append(
        "# KAIRO Extraction Engine V1"
    )

    md.append("")

    md.append(
        f"Generated: `{report['generated_at']}`"
    )

    md.append("")

    md.append("## Safety")

    md.append("")

    md.append(
        "- Source repositories were treated as read-only."
    )

    md.append(
        "- Repository code was not executed."
    )

    md.append(
        "- No source files were deleted."
    )

    md.append(
        "- The frozen archive was not modified."
    )

    md.append(
        "- Secret detections are indicators only."
    )

    md.append("")

    md.append("## Global results")

    md.append("")

    md.append(
        f"- Repositories: **{len(repositories):,}**"
    )

    md.append(
        f"- Files scanned: **{total_files:,}**"
    )

    md.append(
        f"- Candidate files: **{len(all_candidates):,}**"
    )

    md.append(
        f"- Staged files: **{staged:,}**"
    )

    md.append(
        f"- Duplicate groups: **{len(duplicate_groups):,}**"
    )

    md.append("")

    md.append(
        "## Capability coverage"
    )

    md.append("")

    for capability, count in (
        capability_counter.most_common()
    ):

        md.append(
            f"- **{capability}** — {count:,} files"
        )

    md.append("")

    md.append(
        "## Top extraction candidates"
    )

    md.append("")

    md.append(
        "| Score | Repository | File | Capabilities |"
    )

    md.append(
        "|---:|---|---|---|"
    )

    for candidate in all_candidates[:100]:

        capabilities = ", ".join(
            candidate["capabilities"]
        )

        md.append(
            f"| {candidate['score']} "
            f"| `{candidate['repository']}` "
            f"| `{candidate['repository_relative_path']}` "
            f"| {capabilities} |"
        )

    md.append("")

    md.append(
        "## Next stage"
    )

    md.append("")

    md.append(
        "The staged components must now undergo semantic review, "
        "dependency review, security review, duplicate consolidation, "
        "interface adaptation, tests, and only then integration into "
        "Original KAIRO."
    )

    md.append("")

    md.append(
        "### Pipeline"
    )

    md.append("")

    md.append(
        "Repositories → Extraction → Review → "
        "Consolidation → Testing → Security → "
        "Original KAIRO"
    )

    md_path.write_text(
        "\n".join(md),
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # FINAL OUTPUT
    # --------------------------------------------------------

    print()
    print("=" * 64)
    print(" KAIRO EXTRACTION ENGINE COMPLETE")
    print("=" * 64)
    print()

    print(
        f"Repositories : {len(repositories):,}"
    )

    print(
        f"Files        : {total_files:,}"
    )

    print(
        f"Candidates   : {len(all_candidates):,}"
    )

    print(
        f"Staged       : {staged:,}"
    )

    print(
        f"Duplicates   : {len(duplicate_groups):,}"
    )

    print(
        f"Unreadable   : {unreadable:,}"
    )

    print()

    print("Reports:")

    print(
        f"  {analysis_path}"
    )

    print(
        f"  {candidates_path}"
    )

    print(
        f"  {duplicates_path}"
    )

    print(
        f"  {manifest_path}"
    )

    print(
        f"  {md_path}"
    )

    print()

    print(
        "NEXT: Review staged components before integration."
    )

    print()


if __name__ == "__main__":
    main()
