from __future__ import annotations

"""
KAIRO MASTER CONSOLIDATION SCANNER
==================================

One-pass, READ-ONLY analysis of all repositories under:

    00_FOUNDATION/Architecture/Old_Repositories

Outputs:

    10_DOCUMENTATION/Technical/kairo_master_analysis.json
    10_DOCUMENTATION/Technical/KAIRO_MASTER_CHANGE_PLAN.md

IMPORTANT
---------
- READ-ONLY scanner.
- Does NOT modify, delete, move, or execute repository code.
- Generated/environment directories are skipped.
- Inaccessible/invalid files are skipped safely.
- Secret matches are indicators only, not confirmed secrets.
- Exact duplicates are reported but never deleted automatically.
"""

import ast
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

SOURCE_ROOT = (
    PROJECT_ROOT
    / "00_FOUNDATION"
    / "Architecture"
    / "Old_Repositories"
)

REPORT_ROOT = (
    PROJECT_ROOT
    / "10_DOCUMENTATION"
    / "Technical"
)


# ============================================================
# SCANNER LIMITS
# ============================================================

# Files larger than this will not be decoded for text analysis.
MAX_TEXT_SIZE = 2_000_000

# Files larger than this will not be hashed for duplicate detection.
MAX_HASH_SIZE = 5_000_000


# ============================================================
# DIRECTORIES TO SKIP
# ============================================================

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    ".env",
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
    "vendor",
    "site-packages",
    ".turbo",
    ".parcel-cache",
    ".gradle",
    ".cargo",
}


# ============================================================
# FILES TO SKIP
# ============================================================

SKIP_EXTS = {
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
    ".ico",

    ".mp3",
    ".wav",
    ".ogg",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",

    ".zip",
    ".7z",
    ".rar",
    ".tar",
    ".gz",
    ".bz2",

    ".pdf",
}


# ============================================================
# CAPABILITY DETECTION
# ============================================================

CAPABILITY_PATTERNS = {
    "LLM": (
        r"\b(openai|anthropic|gemini|ollama|vllm|"
        r"llm|chatcompletion|inference|transformer)\b"
    ),

    "Agent": (
        r"\b(agent|subagent|multi.?agent|autonomous|agentic)\b"
    ),

    "Memory": (
        r"\b(memory|mem0|memu|long.?term memory|"
        r"episodic|semantic memory|working memory)\b"
    ),

    "RAG": (
        r"\b(rag|retrieval|retriever|vector.?store|"
        r"embedding|knowledge base|semantic search)\b"
    ),

    "Database": (
        r"\b(postgresql|postgres|sqlite|mysql|mongodb|"
        r"redis|database|sqlalchemy|supabase)\b"
    ),

    "Tools": (
        r"\b(tool calling|function calling|tool.?registry|"
        r"tool executor|tool use)\b"
    ),

    "MCP": (
        r"\b(model context protocol|mcp\b|mcp server|mcp client)\b"
    ),

    "Browser": (
        r"\b(playwright|selenium|browser.?use|"
        r"browser automation|chromium|puppeteer)\b"
    ),

    "Computer Use": (
        r"\b(computer use|desktop automation|pyautogui|"
        r"xdotool|screen control|desktop control)\b"
    ),

    "Workflow": (
        r"\b(workflow|orchestrat|scheduler|pipeline|"
        r"task queue|workflow engine)\b"
    ),

    "API": (
        r"\b(fastapi|flask|django|http server|"
        r"rest api|graphql|websocket)\b"
    ),

    "Security": (
        r"\b(auth|oauth|permission|sandbox|secret|"
        r"credential|security|encryption|rbac|authentication)\b"
    ),

    "Voice": (
        r"\b(whisper|speech.?to.?text|text.?to.?speech|"
        r"\btts\b|\bstt\b|voice|audio)\b"
    ),

    "UI": (
        r"\b(react|next\.?js|vue|svelte|streamlit|"
        r"gradio|webui|frontend|dashboard)\b"
    ),

    "Coding": (
        r"\b(code.?agent|coding agent|developer agent|"
        r"compiler|linter|pytest|unit test|code generation)\b"
    ),

    "Data": (
        r"\b(pandas|polars|numpy|data pipeline|"
        r"etl|data ingestion|data processing)\b"
    ),

    "Automation": (
        r"\b(automation|integration|webhook|cron|"
        r"n8n|automate|automation engine)\b"
    ),

    "Containers": (
        r"\b(docker|container|kubernetes|sandbox|podman)\b"
    ),

    "Observability": (
        r"\b(logging|telemetry|tracing|metrics|"
        r"monitoring|opentelemetry|observability)\b"
    ),

    "Search": (
        r"\b(search engine|semantic search|"
        r"web search|internet search|crawler)\b"
    ),

    "Planning": (
        r"\b(planning|planner|task planning|"
        r"reasoning loop|plan.?execute)\b"
    ),

    "Security Operations": (
        r"\b(security monitoring|threat detection|"
        r"audit log|security event|intrusion)\b"
    ),
}


# ============================================================
# SECRET INDICATORS
# ============================================================

SECRET_PATTERNS = [
    r"(?i)\bapi[\_-]?key\b",
    r"(?i)\bsecret[\_-]?key\b",
    r"(?i)\baccess[\_-]?token\b",
    r"(?i)\bprivate[\_-]?key\b",
    r"(?i)\bpassword\b",
    r"(?i)\bpasswd\b",
    r"(?i)\bclient[\_-]?secret\b",
    r"(?i)\baws[\_-]?access[\_-]?key[\_-]?id\b",
    r"(?i)\baws[\_-]?secret[\_-]?access[\_-]?key\b",
    r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----",
]


# ============================================================
# MANIFEST FILES
# ============================================================

MANIFESTS = {
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "package.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "package-lock.json",
    "Cargo.toml",
    "go.mod",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "environment.yml",
    "environment.yaml",
    "setup.py",
    "setup.cfg",
}


# ============================================================
# TEXT FILE EXTENSIONS
# ============================================================

TEXT_EXTS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".vue",
    ".svelte",

    ".html",
    ".css",
    ".scss",

    ".json",
    ".yaml",
    ".yml",
    ".toml",

    ".md",
    ".txt",

    ".sh",
    ".bash",
    ".zsh",

    ".ps1",
    ".bat",
    ".cmd",

    ".rs",
    ".go",
    ".java",
    ".kt",
    ".kts",
    ".cpp",
    ".c",
    ".h",
    ".hpp",

    ".sql",

    ".xml",
    ".graphql",
    ".gql",

    ".env.example",
    ".ini",
    ".conf",
}


# ============================================================
# SAFE FILE ITERATOR
# ============================================================

def iter_files(root: Path):
    """
    Safely walk a repository.

    Important:
    - Never follows symlinks.
    - Skips generated/environment directories.
    - Handles Windows path/access errors.
    - Does not crash the complete scan because of one bad file.
    """

    if not root.exists():
        return

    def on_error(error):
        # Intentionally ignore inaccessible directories/files.
        return

    try:
        for current_root, dirs, files in os.walk(
            str(root),
            topdown=True,
            followlinks=False,
            onerror=on_error,
        ):
            # Modify dirs in-place so os.walk never enters skipped folders.
            dirs[:] = [
                d
                for d in dirs
                if d not in SKIP_DIRS
                and not d.startswith(".git")
            ]

            for filename in files:
                try:
                    path = Path(current_root) / filename

                    if path.is_symlink():
                        continue

                    suffix = path.suffix.lower()

                    if suffix in SKIP_EXTS:
                        continue

                    # Avoid obvious generated lock/temp files.
                    if filename.endswith((".tmp", ".temp", ".log")):
                        continue

                    if path.is_file():
                        yield path

                except (
                    OSError,
                    PermissionError,
                    FileNotFoundError,
                ):
                    continue

    except (
        OSError,
        PermissionError,
        FileNotFoundError,
    ):
        return


# ============================================================
# SAFE TEXT READER
# ============================================================

def safe_text(path: Path) -> str:
    """
    Read a text file safely.

    Returns empty string when:
    - file is too large
    - file is binary
    - permission denied
    - path disappeared
    """

    try:
        size = path.stat().st_size

        if size > MAX_TEXT_SIZE:
            return ""

        # Read bytes first to avoid encoding crashes.
        raw = path.read_bytes()

        if b"\x00" in raw:
            return ""

        return raw.decode("utf-8", errors="ignore")

    except (
        OSError,
        PermissionError,
        FileNotFoundError,
    ):
        return ""


# ============================================================
# SHA256
# ============================================================

def sha256(path: Path) -> str | None:
    """
    Calculate SHA256 safely for duplicate detection.
    """

    try:
        size = path.stat().st_size

        if size > MAX_HASH_SIZE:
            return None

        digest = hashlib.sha256()

        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)

                if not chunk:
                    break

                digest.update(chunk)

        return digest.hexdigest()

    except (
        OSError,
        PermissionError,
        FileNotFoundError,
    ):
        return None


# ============================================================
# PYTHON SYMBOL EXTRACTION
# ============================================================

def python_symbols(text: str) -> dict:
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
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            result["functions"].append(node.name)

        elif isinstance(node, ast.Import):
            for item in node.names:
                result["imports"].append(item.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                result["imports"].append(node.module)

    return result


# ============================================================
# DECISION ENGINE
# ============================================================

def decision_for(
    capabilities,
    file_count: int,
    repo_name: str,
) -> str:

    strong = {
        "Agent",
        "LLM",
        "Memory",
        "RAG",
        "Tools",
        "Browser",
        "Computer Use",
        "Security",
        "Workflow",
        "API",
        "MCP",
        "Planning",
    }

    score = len(set(capabilities) & strong)

    # Repos is a giant collection, not one application.
    if repo_name == "Repos":
        return "EXTRACT_ONLY"

    if score >= 6:
        return "ADAPT"

    if score >= 3:
        return "EXTRACT"

    if file_count <= 5:
        return "REVIEW"

    return "ARCHIVE_CANDIDATE"


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("==========================================")
    print(" KAIRO MASTER CONSOLIDATION SCANNER")
    print("==========================================")
    print()

    print(f"PROJECT ROOT:")
    print(f"  {PROJECT_ROOT}")
    print()

    print("SOURCE ROOT:")
    print(f"  {SOURCE_ROOT}")
    print()

    # --------------------------------------------------------
    # Prepare report directory
    # --------------------------------------------------------

    REPORT_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Validate source
    # --------------------------------------------------------

    if not SOURCE_ROOT.exists():
        print("ERROR: Source repository directory not found.")
        print()
        print(f"Expected:")
        print(SOURCE_ROOT)
        print()
        raise SystemExit(1)

    if not SOURCE_ROOT.is_dir():
        print("ERROR: Source path exists but is not a directory.")
        print()
        raise SystemExit(1)

    # --------------------------------------------------------
    # Find repositories
    # --------------------------------------------------------

    try:
        repos = [
            p
            for p in SOURCE_ROOT.iterdir()
            if p.is_dir() and not p.is_symlink()
        ]
    except (
        OSError,
        PermissionError,
    ) as error:

        print("ERROR: Could not read source directory.")
        print(error)
        raise SystemExit(1)

    repos = sorted(
        repos,
        key=lambda p: p.name.lower(),
    )

    print(f"Repositories detected: {len(repos)}")
    print()

    for repo in repos:
        print(f"  - {repo.name}")

    print()
    print("------------------------------------------")
    print("Starting read-only analysis...")
    print("------------------------------------------")
    print()

    # --------------------------------------------------------
    # Global report
    # --------------------------------------------------------

    report = {
        "project": "KAIRO",

        "analysis_mode": (
            "READ_ONLY_ONE_PASS"
        ),

        "generated_at": (
            datetime.now(timezone.utc).isoformat()
        ),

        "source_root": str(SOURCE_ROOT),

        "repositories": [],

        "global": {
            "file_count": 0,
            "duplicate_groups": 0,
            "capability_file_counts": {},
            "extension_counts": {},
            "manifest_files": [],
            "secret_indicator_count": 0,
            "unreadable_files": 0,
            "skipped_large_text_files": 0,
        },

        "master_actions": [],
    }

    # --------------------------------------------------------
    # Global counters
    # --------------------------------------------------------

    hashes = defaultdict(list)

    cap_counts = Counter()
    ext_counts = Counter()

    total_unreadable = 0
    total_large_text_skipped = 0

    # --------------------------------------------------------
    # Repository processing
    # --------------------------------------------------------

    for repo_index, repo in enumerate(repos, start=1):

        print(
            f"[{repo_index}/{len(repos)}] "
            f"Scanning: {repo.name}"
        )

        repo_files = []
        capabilities = Counter()

        repo_secret_hits = []
        manifests = []
        python_details = []

        total_bytes = 0
        unreadable_files = 0
        large_text_files = 0

        # ----------------------------------------------------
        # Iterate files
        # ----------------------------------------------------

        for path in iter_files(repo):

            repo_files.append(path)

            try:
                size = path.stat().st_size

            except (
                OSError,
                PermissionError,
                FileNotFoundError,
            ):
                unreadable_files += 1
                total_unreadable += 1
                continue

            total_bytes += size

            # ------------------------------------------------
            # Extension statistics
            # ------------------------------------------------

            suffix = path.suffix.lower()

            ext_key = (
                suffix
                if suffix
                else "[no extension]"
            )

            ext_counts[ext_key] += 1

            # ------------------------------------------------
            # Relative path
            # ------------------------------------------------

            try:
                rel = path.relative_to(repo).as_posix()
            except ValueError:
                rel = path.name

            # ------------------------------------------------
            # Manifest detection
            # ------------------------------------------------

            if path.name.lower() in {
                item.lower()
                for item in MANIFESTS
            }:
                manifests.append(rel)

            # ------------------------------------------------
            # Text analysis
            # ------------------------------------------------

            text = ""

            if size <= MAX_TEXT_SIZE:

                text = safe_text(path)

                if not text and size > 0:
                    # Could be binary or unreadable.
                    unreadable_files += 1

            else:
                large_text_files += 1
                total_large_text_skipped += 1

            # ------------------------------------------------
            # Capability detection
            # ------------------------------------------------

            if text:

                for capability, pattern in CAPABILITY_PATTERNS.items():

                    try:
                        if re.search(
                            pattern,
                            text,
                            flags=re.IGNORECASE,
                        ):
                            capabilities[capability] += 1
                            cap_counts[capability] += 1

                    except re.error:
                        continue

                # ------------------------------------------------
                # Secret indicators
                # ------------------------------------------------

                for pattern in SECRET_PATTERNS:

                    try:
                        matches = re.findall(
                            pattern,
                            text,
                        )
                    except re.error:
                        matches = []

                    if matches:

                        repo_secret_hits.append(
                            {
                                "file": rel,
                                "pattern": pattern,
                                "count": len(matches),
                            }
                        )

                # ------------------------------------------------
                # Python symbols
                # ------------------------------------------------

                if suffix == ".py":

                    symbols = python_symbols(text)

                    if (
                        symbols["classes"]
                        or symbols["functions"]
                    ):

                        python_details.append(
                            {
                                "file": rel,
                                **symbols,
                            }
                        )

            # ------------------------------------------------
            # Exact duplicate hashing
            # ------------------------------------------------

            if size <= MAX_HASH_SIZE:

                digest = sha256(path)

                if digest:
                    hashes[digest].append(
                        str(path)
                    )

        # ----------------------------------------------------
        # Repository decision
        # ----------------------------------------------------

        decision = decision_for(
            list(capabilities),
            len(repo_files),
            repo.name,
        )

        # ----------------------------------------------------
        # Repository report
        # ----------------------------------------------------

        repo_report = {
            "repository": repo.name,

            "path": str(repo),

            "file_count": len(repo_files),

            "size_bytes": total_bytes,

            "capability_file_counts": dict(
                capabilities.most_common()
            ),

            "manifests": sorted(manifests),

            "secret_indicators": repo_secret_hits,

            "python_symbols": (
                python_details[:5000]
            ),

            "unreadable_files": unreadable_files,

            "large_text_files_skipped": (
                large_text_files
            ),

            "proposed_decision": decision,
        }

        report["repositories"].append(
            repo_report
        )

        print(
            f"    Files: {len(repo_files):,}"
        )

        print(
            f"    Size: {total_bytes:,} bytes"
        )

        print(
            f"    Capabilities: "
            f"{len(capabilities)}"
        )

        print(
            f"    Decision: {decision}"
        )

        print()

    # ========================================================
    # EXACT DUPLICATES
    # ========================================================

    print("------------------------------------------")
    print("Analyzing exact duplicates...")
    print("------------------------------------------")
    print()

    duplicate_groups = []

    for digest, paths in hashes.items():

        if len(paths) > 1:

            duplicate_groups.append(
                {
                    "sha256": digest,
                    "files": paths,
                }
            )

    duplicate_groups.sort(
        key=lambda item: len(item["files"]),
        reverse=True,
    )

    # ========================================================
    # GLOBAL STATISTICS
    # ========================================================

    report["global"]["file_count"] = sum(
        item["file_count"]
        for item in report["repositories"]
    )

    report["global"]["duplicate_groups"] = (
        len(duplicate_groups)
    )

    report["global"]["capability_file_counts"] = dict(
        cap_counts.most_common()
    )

    report["global"]["extension_counts"] = dict(
        ext_counts.most_common()
    )

    report["global"]["manifest_files"] = [
        {
            "repository": item["repository"],
            "files": item["manifests"],
        }
        for item in report["repositories"]
        if item["manifests"]
    ]

    report["global"]["secret_indicator_count"] = sum(
        len(item["secret_indicators"])
        for item in report["repositories"]
    )

    report["global"]["unreadable_files"] = (
        total_unreadable
    )

    report["global"]["skipped_large_text_files"] = (
        total_large_text_skipped
    )

    # Keep the report manageable.
    report["global"]["exact_duplicate_groups"] = (
        duplicate_groups[:500]
    )

    # ========================================================
    # MASTER ACTIONS
    # ========================================================

    for item in report["repositories"]:

        decision = item["proposed_decision"]

        if decision in {
            "EXTRACT",
            "EXTRACT_ONLY",
            "ADAPT",
        }:

            reason = (
                "Extract useful capabilities into "
                "Original KAIRO. Do not copy the "
                "repository wholesale."
            )

        elif decision == "REVIEW":

            reason = (
                "Small repository. Review manually "
                "for any unique useful capability."
            )

        else:

            reason = (
                "Keep outside production KAIRO "
                "until a concrete useful capability "
                "is selected."
            )

        report["master_actions"].append(
            {
                "repository": item["repository"],
                "action": decision,
                "reason": reason,
            }
        )

    # ========================================================
    # WRITE JSON REPORT
    # ========================================================

    json_path = (
        REPORT_ROOT
        / "kairo_master_analysis.json"
    )

    json_path.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # ========================================================
    # MARKDOWN CHANGE PLAN
    # ========================================================

    md = []

    md.append(
        "# KAIRO Master Consolidation Change Plan"
    )

    md.append("")

    md.append(
        f"Generated: "
        f"`{report['generated_at']}`"
    )

    md.append("")

    md.append("## Rule")

    md.append("")

    md.append(
        "Extract **all genuinely useful capabilities** "
        "from the repositories, consolidate duplicate "
        "implementations, adapt strong subsystems, "
        "rewrite weak-but-useful concepts, and keep "
        "the frozen original archive untouched."
    )

    md.append("")

    md.append("## Repository Actions")

    md.append("")

    md.append(
        "| Repository | Files | Decision |"
    )

    md.append(
        "|---|---:|---|"
    )

    for item in report["repositories"]:

        md.append(
            f"| `{item['repository']}` "
            f"| {item['file_count']:,} "
            f"| **{item['proposed_decision']}** |"
        )

    md.append("")

    md.append("## Capability Coverage")

    md.append("")

    for capability, count in (
        cap_counts.most_common()
    ):

        md.append(
            f"- **{capability}** — "
            f"detected in {count:,} files"
        )

    md.append("")

    md.append("## Batch Integration Order")

    md.append("")

    md.extend(
        [
            "1. **Create extraction workspace** "
            "outside the frozen archive.",

            "2. **Extract components, not repositories** "
            "— preserve source attribution for every "
            "imported component.",

            "3. **Consolidate interfaces** around "
            "KAIRO Core, Runtime, Agents, Tools, "
            "Data, Security, and UI.",

            "4. **Resolve duplicates** by comparing "
            "implementation quality, dependencies, "
            "tests, maintainability, and security.",

            "5. **Rewrite conflicts** instead of forcing "
            "incompatible frameworks into KAIRO.",

            "6. **Run tests and static checks** before "
            "activating any imported capability.",

            "7. **Clean generated artifacts** such as "
            "`.venv`, `node_modules`, caches, build "
            "output, binaries, and copied secrets.",

            "8. **Leave unused source in archive**, "
            "not production.",

            "9. **Do not delete source repositories** "
            "from the frozen archive.",

            "10. **Preserve the strongest useful "
            "implementation of each capability** "
            "inside Original KAIRO.",
        ]
    )

    md.append("")

    md.append("## Exact Duplicate Groups")

    md.append("")

    md.append(
        f"Detected: **{len(duplicate_groups):,}** "
        "exact-hash duplicate groups."
    )

    md.append("")

    md.append(
        "The scanner does not delete duplicates "
        "automatically. They require semantic review "
        "before consolidation."
    )

    md.append("")

    md.append("## Security")

    md.append("")

    md.append(
        f"Secret-pattern indicators: "
        f"**{report['global']['secret_indicator_count']:,}**."
    )

    md.append("")

    md.append(
        "These are pattern hits only, not confirmed "
        "secrets."
    )

    md.append("")

    md.append("## Scanner Limitations")

    md.append("")

    md.append(
        f"- Unreadable/inaccessible files skipped: "
        f"**{total_unreadable:,}**"
    )

    md.append(
        f"- Files larger than text-analysis limit "
        f"skipped: **{total_large_text_skipped:,}**"
    )

    md.append(
        f"- Text analysis limit: "
        f"**{MAX_TEXT_SIZE:,} bytes**"
    )

    md.append(
        f"- Duplicate hashing limit: "
        f"**{MAX_HASH_SIZE:,} bytes**"
    )

    md.append("")

    md.append("## Production Boundary")

    md.append("")

    md.append(
        "`11_ARCHIVE/Original_Repositories` is a "
        "frozen reference archive and must not be "
        "modified by the consolidation process."
    )

    md.append("")

    md.append(
        "Only validated, selected components should "
        "enter production Original KAIRO."
    )

    md.append("")

    md_path = (
        REPORT_ROOT
        / "KAIRO_MASTER_CHANGE_PLAN.md"
    )

    md_path.write_text(
        "\n".join(md),
        encoding="utf-8",
    )

    # ========================================================
    # FINAL OUTPUT
    # ========================================================

    print()
    print("==========================================")
    print(" KAIRO MASTER CONSOLIDATION ANALYSIS DONE")
    print("==========================================")
    print()

    print(
        f"Repositories : "
        f"{len(repos):,}"
    )

    print(
        f"Files        : "
        f"{report['global']['file_count']:,}"
    )

    print(
        f"Duplicates   : "
        f"{len(duplicate_groups):,} exact groups"
    )

    print(
        f"Secret hits  : "
        f"{report['global']['secret_indicator_count']:,}"
    )

    print(
        f"Skipped      : "
        f"{total_unreadable:,} unreadable"
    )

    print()

    print("Reports:")

    print(
        f"  {json_path}"
    )

    print(
        f"  {md_path}"
    )

    print()

    print(
        "NEXT: use the master analysis to perform "
        "batch extraction/integration."
    )

    print()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()