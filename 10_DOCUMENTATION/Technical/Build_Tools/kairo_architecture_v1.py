from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

folders = [
    "00_FOUNDATION/Architecture",
    "01_CORE/AI",
    "01_CORE/Reasoning",
    "01_CORE/Planning",
    "01_CORE/Context",
    "01_CORE/Memory",
    "01_CORE/Orchestration",

    "02_AGENTS/Research",
    "02_AGENTS/Coding",
    "02_AGENTS/Data",
    "02_AGENTS/Finance",
    "02_AGENTS/Trading",
    "02_AGENTS/Operations",
    "02_AGENTS/Security",

    "03_DATA/Database",
    "03_DATA/Knowledge",
    "03_DATA/RAG",
    "03_DATA/Vector",
    "03_DATA/Pipelines",

    "04_TOOLS/Browser",
    "04_TOOLS/Computer_Use",
    "04_TOOLS/API",
    "04_TOOLS/MCP",
    "04_TOOLS/Automation",

    "05_UI/Command_Center",
    "05_UI/Dashboard",
    "05_UI/Interfaces",

    "06_SECURITY/Identity",
    "06_SECURITY/Authority",
    "06_SECURITY/Permissions",
    "06_SECURITY/Secrets",
    "06_SECURITY/Sandbox",
    "06_SECURITY/Audit",

    "07_RUNTIME/Tasks",
    "07_RUNTIME/Events",
    "07_RUNTIME/Workflows",
    "07_RUNTIME/Scheduler",
    "07_RUNTIME/State",
    "07_RUNTIME/Execution",

    "08_BUSINESS/Finance",
    "08_BUSINESS/Trading",
    "08_BUSINESS/Research",
    "08_BUSINESS/Operations",

    "09_INTELLIGENCE/Visual",
    "09_INTELLIGENCE/Analytics",
    "09_INTELLIGENCE/Decision_Support",
    "09_INTELLIGENCE/Self_Improvement",

    "10_INFRASTRUCTURE/Containers",
    "10_INFRASTRUCTURE/Storage",
    "10_INFRASTRUCTURE/Monitoring",
    "10_INFRASTRUCTURE/Deployment",
]

created = 0

for folder in folders:
    path = ROOT / folder
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        created += 1

print("=" * 70)
print("KAIRO V1 MASTER ARCHITECTURE")
print("=" * 70)
print(f"Architecture directories created : {created}")
print("Existing files                  : PRESERVED")
print("Original repositories            : PROTECTED")
print("Frozen archive                   : PROTECTED")
print("Production deletion              : NONE")
print("=" * 70)
print("STATUS: ARCHITECTURE SKELETON READY")
print("NEXT: COMPONENT MAPPING + INTEGRATION")
print("=" * 70)
