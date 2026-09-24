"""
KAIRO MASTER CONSOLIDATION SCANNER
One-pass, read-only analysis of all repositories under:
    00_FOUNDATION/Architecture/Old_Repositories

Outputs:
    10_DOCUMENTATION/Technical/kairo_master_analysis.json
    10_DOCUMENTATION/Technical/KAIRO_MASTER_CHANGE_PLAN.md

IMPORTANT:
- READ-ONLY: this script does not modify, delete, move, or execute repository code.
- It ignores generated/build/environment directories.
- Secret matches are indicators only, not confirmed secrets.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "00_FOUNDATION" / "Architecture" / "Old_Repositories"
REPORT_ROOT = PROJECT_ROOT / "10_DOCUMENTATION" / "Technical"

SKIP_DIRS = {
    ".git", ".venv", "venv", "env", "node_modules", "__pycache__",
    "dist", "build", ".next", ".cache", "coverage", "target",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    "vendor", "site-packages", ".idea"
}
SKIP_EXTS = {
    ".pyc", ".pyo", ".whl", ".so", ".dll", ".exe", ".bin",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov",
    ".zip", ".7z", ".rar", ".tar", ".gz", ".pdf"
}

CAPABILITY_PATTERNS = {
    "LLM": r"\b(openai|anthropic|gemini|ollama|vllm|llm|chatcompletion|inference)\b",
    "Agent": r"\b(agent|subagent|multi.?agent|autonomous)\b",
    "Memory": r"\b(memory|mem0|memu|long.?term memory|episodic|semantic memory)\b",
    "RAG": r"\b(rag|retrieval|retriever|vector.?store|embedding|knowledge base)\b",
    "Database": r"\b(postgresql|postgres|sqlite|mysql|mongodb|redis|database|sqlalchemy)\b",
    "Tools": r"\b(tool calling|function calling|tools? registry|tool executor)\b",
    "MCP": r"\b(model context protocol|mcp\b|mcp server|mcp client)\b",
    "Browser": r"\b(playwright|selenium|browser-use|browser automation|chromium)\b",
    "Computer Use": r"\b(computer use|desktop automation|pyautogui|xdotool|screen control)\b",
    "Workflow": r"\b(workflow|orchestrat|scheduler|pipeline|task queue)\b",
    "API": r"\b(fastapi|flask|django|http server|rest api|graphql)\b",
    "Security": r"\b(auth|oauth|permission|sandbox|secret|credential|security|encryption|rbac)\b",
    "Voice": r"\b(whisper|speech.?to.?text|text.?to.?speech|tts|stt|voice)\b",
    "UI": r"\b(react|next\.js|vue|svelte|streamlit|gradio|webui|frontend)\b",
    "Coding": r"\b(code.?agent|coding agent|developer agent|compiler|linter|pytest|unit test)\b",
    "Data": r"\b(pandas|polars|numpy|data pipeline|etl|data ingestion)\b",
    "Automation": r"\b(automation|integration|webhook|cron|n8n)\b",
    "Containers": r"\b(docker|container|kubernetes|sandbox)\b",
    "Observability": r"\b(logging|telemetry|tracing|metrics|monitoring|opentelemetry)\b",
}

SECRET_PATTERNS = [
    r"(?i)\b(api[_-]?key|secret[_-]?key|access[_-]?token|private[_-]?key)\b",
    r"(?i)\b(password|passwd|client_secret)\s*[:=]",
    r"(?i)\b(aws_access_key_id|aws_secret_access_key)\b",
    r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----",
]

MANIFESTS = {
    "pyproject.toml", "requirements.txt", "requirements-dev.txt",
    "package.json", "pnpm-lock.yaml", "yarn.lock", "package-lock.json",
    "Cargo.toml", "go.mod", "Dockerfile", "docker-compose.yml",
    "docker-compose.yaml", "environment.yml"
}

def iter_files(root: Path):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in SKIP_EXTS:
            continue
        yield p

def safe_text(path: Path, limit=400_000):
    try:
        raw = path.read_bytes()
        if len(raw) > limit:
            raw = raw[:limit]
        return raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""

def sha256(path: Path):
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None

def python_symbols(text):
    result = {"classes": [], "functions": [], "imports": []}
    try:
        tree = ast.parse(text)
    except Exception:
        return result
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            result["classes"].append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result["functions"].append(node.name)
        elif isinstance(node, ast.Import):
            result["imports"].extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result["imports"].append(node.module)
    return result

def decision_for(capabilities, file_count, repo_name):
    strong = {"Agent", "LLM", "Memory", "RAG", "Tools", "Browser",
              "Computer Use", "Security", "Workflow", "API", "MCP"}
    score = len(set(capabilities) & strong)
    if repo_name == "Repos":
        return "EXTRACT_ONLY"
    if score >= 5:
        return "ADAPT"
    if score >= 2:
        return "EXTRACT"
    if file_count <= 5:
        return "REVIEW"
    return "ARCHIVE_CANDIDATE"

def main():
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    if not SOURCE_ROOT.exists():
        raise SystemExit(f"Source repository directory not found: {SOURCE_ROOT}")

    repos = [p for p in SOURCE_ROOT.iterdir() if p.is_dir()]
    report = {
        "project": "KAIRO",
        "analysis_mode": "READ_ONLY_ONE_PASS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_root": str(SOURCE_ROOT),
        "repositories": [],
        "global": {
            "file_count": 0,
            "duplicate_groups": 0,
            "capability_file_counts": {},
            "extension_counts": {},
            "manifest_files": [],
            "secret_indicator_count": 0,
        },
        "master_actions": [],
    }

    hashes = defaultdict(list)
    cap_counts = Counter()
    ext_counts = Counter()

    for repo in sorted(repos):
        files = list(iter_files(repo))
        capabilities = Counter()
        repo_secret_hits = []
        manifests = []
        python_details = []
        total_bytes = 0

        for path in files:
            rel = path.relative_to(repo).as_posix()
            ext_counts[path.suffix.lower() or "[no extension]"] += 1
            total_bytes += path.stat().st_size

            if path.name in MANIFESTS or path.name.lower() in {x.lower() for x in MANIFESTS}:
                manifests.append(rel)

            text = safe_text(path)
            if text:
                for cap, pattern in CAPABILITY_PATTERNS.items():
                    if re.search(pattern, text):
                        capabilities[cap] += 1
                        cap_counts[cap] += 1

                for pattern in SECRET_PATTERNS:
                    hits = re.findall(pattern, text)
                    if hits:
                        repo_secret_hits.append({
                            "file": rel,
                            "pattern": pattern,
                            "count": len(hits)
                        })

                if path.suffix.lower() == ".py":
                    syms = python_symbols(text)
                    if syms["classes"] or syms["functions"]:
                        python_details.append({
                            "file": rel,
                            **syms
                        })

            # Hash reasonably-sized source/text files for exact duplicate detection.
            if path.stat().st_size <= 5_000_000:
                digest = sha256(path)
                if digest:
                    hashes[digest].append(str(path))

        report["repositories"].append({
            "repository": repo.name,
            "file_count": len(files),
            "size_bytes": total_bytes,
            "capability_file_counts": dict(capabilities.most_common()),
            "manifests": manifests,
            "secret_indicators": repo_secret_hits,
            "python_symbols": python_details[:5000],
            "proposed_decision": decision_for(list(capabilities), len(files), repo.name),
        })

    duplicate_groups = []
    for digest, paths in hashes.items():
        if len(paths) > 1:
            duplicate_groups.append({"sha256": digest, "files": paths})
    duplicate_groups.sort(key=lambda x: len(x["files"]), reverse=True)

    report["global"]["file_count"] = sum(r["file_count"] for r in report["repositories"])
    report["global"]["duplicate_groups"] = len(duplicate_groups)
    report["global"]["capability_file_counts"] = dict(cap_counts.most_common())
    report["global"]["extension_counts"] = dict(ext_counts.most_common())
    report["global"]["manifest_files"] = [
        {"repository": r["repository"], "files": r["manifests"]}
        for r in report["repositories"] if r["manifests"]
    ]
    report["global"]["secret_indicator_count"] = sum(
        len(r["secret_indicators"]) for r in report["repositories"]
    )
    report["global"]["exact_duplicate_groups"] = duplicate_groups[:200]

    # Master decisions: preserve useful capability coverage, consolidate duplicates,
    # and never modify the frozen archive.
    for r in report["repositories"]:
        decision = r["proposed_decision"]
        report["master_actions"].append({
            "repository": r["repository"],
            "action": decision,
            "reason": (
                "Extract useful capabilities into Original KAIRO; do not copy the repository wholesale."
                if decision in {"EXTRACT", "EXTRACT_ONLY", "ADAPT"}
                else "Keep outside production KAIRO until a concrete capability is selected."
            )
        })

    json_path = REPORT_ROOT / "kairo_master_analysis.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    md = []
    md.append("# KAIRO Master Consolidation Change Plan")
    md.append("")
    md.append(f"Generated: `{report['generated_at']}`")
    md.append("")
    md.append("## Rule")
    md.append("Extract **all genuinely useful capabilities** from the repositories, consolidate duplicate implementations, adapt strong subsystems, rewrite weak-but-useful concepts, and keep the frozen original archive untouched.")
    md.append("")
    md.append("## Repository actions")
    md.append("")
    md.append("| Repository | Files | Decision |")
    md.append("|---|---:|---|")
    for r in report["repositories"]:
        md.append(f"| `{r['repository']}` | {r['file_count']:,} | **{r['proposed_decision']}** |")
    md.append("")
    md.append("## Capability coverage")
    md.append("")
    for cap, count in cap_counts.most_common():
        md.append(f"- **{cap}** — detected in {count:,} files")
    md.append("")
    md.append("## Batch integration order")
    md.extend([
        "",
        "1. **Create extraction workspace** outside the frozen archive.",
        "2. **Extract components, not repositories** — preserve source attribution for every imported component.",
        "3. **Consolidate interfaces** around KAIRO Core, Runtime, Agents, Tools, Data, Security, and UI.",
        "4. **Resolve duplicates** by comparing implementation quality, dependencies, tests, maintainability, and security.",
        "5. **Rewrite conflicts** instead of forcing incompatible frameworks into KAIRO.",
        "6. **Run tests and static checks** before activating any imported capability.",
        "7. **Clean generated artifacts** such as `.venv`, `node_modules`, caches, build output, binaries, and copied secrets.",
        "8. **Leave unused source in archive**, not production.",
    ])
    md.append("")
    md.append("## Exact duplicate groups")
    md.append(f"Detected: **{len(duplicate_groups):,}** exact-hash duplicate groups.")
    md.append("")
    md.append("The scanner does not delete duplicates automatically. They require consolidation after semantic review.")
    md.append("")
    md.append("## Security")
    md.append(f"Secret-pattern indicators: **{report['global']['secret_indicator_count']:,}**. These are pattern hits only, not confirmed secrets.")
    md.append("")
    md.append("## Production boundary")
    md.append("`11_ARCHIVE/Original_Repositories` is a frozen reference archive and must not be modified by the consolidation process.")
    md.append("")

    md_path = REPORT_ROOT / "KAIRO_MASTER_CHANGE_PLAN.md"
    md_path.write_text("\n".join(md), encoding="utf-8")

    print("==========================================")
    print(" KAIRO MASTER CONSOLIDATION ANALYSIS DONE")
    print("==========================================")
    print(f"Repositories : {len(repos)}")
    print(f"Files        : {report['global']['file_count']:,}")
    print(f"Duplicates   : {len(duplicate_groups):,} exact groups")
    print(f"Reports:")
    print(f"  {json_path}")
    print(f"  {md_path}")
    print("")
    print("NEXT: use the master analysis to perform the batch extraction/integration.")

if __name__ == "__main__":
    main()
