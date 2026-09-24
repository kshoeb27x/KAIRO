# ============================================================
# KAIRO STAGE 3 V2 — POST-CLEANUP VALIDATION
# READ-ONLY — NO DELETIONS
# ============================================================

$ErrorActionPreference = "Continue"

$KAIRO = "C:\Users\kshoe\Downloads\KAIRO_Foundation\KAIRO"
$REPORT_DIR = Join-Path $KAIRO "99_CLEANUP_REPORT"

New-Item -ItemType Directory -Force -Path $REPORT_DIR | Out-Null

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$JsonReport = Join-Path $REPORT_DIR "KAIRO_STAGE3_V2_VALIDATION_$Timestamp.json"
$MdReport   = Join-Path $REPORT_DIR "KAIRO_STAGE3_V2_VALIDATION_$Timestamp.md"

Write-Host ""
Write-Host "============================================================"
Write-Host "          KAIRO STAGE 3 V2 POST-CLEANUP VALIDATION"
Write-Host "============================================================"
Write-Host ""
Write-Host "READ-ONLY VALIDATION"
Write-Host ""

$Results = [ordered]@{}
$Failures = @()
$Warnings = @()

# ------------------------------------------------------------
# Helper
# ------------------------------------------------------------

function Add-Result {
    param(
        [string]$Name,
        [string]$Status,
        [string]$Detail
    )

    $Results[$Name] = [ordered]@{
        Status = $Status
        Detail = $Detail
    }

    if ($Status -eq "FAIL") {
        $script:Failures += "$Name : $Detail"
    }

    if ($Status -eq "WARN") {
        $script:Warnings += "$Name : $Detail"
    }
}

# ------------------------------------------------------------
# Safe active-tree traversal
# ------------------------------------------------------------

$ExcludedNames = @(
    ".git",
    ".venv",
    ".pytest_cache",
    ".test-tmp",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".cache",
    "dist",
    "build"
)

$HistoricalRoots = @(
    "11_ARCHIVE",
    "12_EXTRACTION",
    "13_FINAL_KAIRO",
    "14_KAIRO_PRODUCTION_CANDIDATE",
    "15_ROLLBACK_SNAPSHOTS",
    "16_POST_MERGE_VALIDATION",
    "17_RUNTIME_VALIDATION",
    "18_LIVE_API_UI_VALIDATION",
    "19_ARCHITECTURE",
    "19_CLEANUP_AUDIT",
    "99_CLEANUP_REPORT",
    "99_DEEP_SCAN_REPORT"
)

function Get-ActiveFiles {
    param(
        [string]$Root
    )

    $Queue = New-Object System.Collections.Generic.Queue[string]
    $Queue.Enqueue($Root)

    while ($Queue.Count -gt 0) {

        $Current = $Queue.Dequeue()

        try {
            $Children = Get-ChildItem -LiteralPath $Current -Force -ErrorAction Stop
        }
        catch {
            continue
        }

        foreach ($Item in $Children) {

            if ($Item.PSIsContainer) {

                if ($ExcludedNames -contains $Item.Name) {
                    continue
                }

                $Relative = $Item.FullName.Substring($KAIRO.Length).TrimStart("\")
                $TopLevel = ($Relative -split "\\")[0]

                if ($HistoricalRoots -contains $TopLevel) {
                    continue
                }

                $Queue.Enqueue($Item.FullName)
            }
            else {
                yield $Item
            }
        }
    }
}

# ============================================================
# [1/9] CORE STRUCTURE
# ============================================================

Write-Host "[1/9] Checking KAIRO core structure..."

$RequiredDirectories = @(
    "00_FOUNDATION",
    "01_CORE",
    "02_AGENTS",
    "03_DATA",
    "04_TOOLS",
    "05_UI",
    "06_SECURITY",
    "07_RUNTIME",
    "08_BUSINESS",
    "09_INTELLIGENCE",
    "10_INFRASTRUCTURE",
    "config",
    "scripts",
    "src",
    "tests"
)

$MissingDirectories = @()

foreach ($Dir in $RequiredDirectories) {

    $Path = Join-Path $KAIRO $Dir

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        $MissingDirectories += $Dir
    }
}

if ($MissingDirectories.Count -eq 0) {
    Add-Result "CORE_STRUCTURE" "PASS" "All required active KAIRO directories exist."
}
else {
    Add-Result "CORE_STRUCTURE" "FAIL" (
        "Missing directories: " + ($MissingDirectories -join ", ")
    )
}

# ============================================================
# [2/9] CORE FILES
# ============================================================

Write-Host "[2/9] Checking core files..."

$RequiredFiles = @(
    "src\core\kairo_core.py",
    "src\core\runtime_controller.py",
    "src\api\server.py",
    "07_RUNTIME\Events\event_bus.py",
    "07_RUNTIME\State\runtime_state.py",
    "07_RUNTIME\Task_Manager\task_manager.py",
    "05_UI\Web\index.html",
    "05_UI\Web\style.css",
    "05_UI\Web\app.js"
)

$MissingFiles = @()

foreach ($File in $RequiredFiles) {

    $Path = Join-Path $KAIRO $File

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        $MissingFiles += $File
    }
}

if ($MissingFiles.Count -eq 0) {
    Add-Result "CORE_FILES" "PASS" "All required runtime/API/UI files exist."
}
else {
    Add-Result "CORE_FILES" "FAIL" (
        "Missing files: " + ($MissingFiles -join ", ")
    )
}

# ============================================================
# [3/9] PYTHON SYNTAX
# ============================================================

Write-Host "[3/9] Checking Python syntax..."

$ActiveFiles = @(Get-ActiveFiles -Root $KAIRO)
$PythonFiles = @($ActiveFiles | Where-Object { $_.Extension -eq ".py" })

Write-Host ("       Active Python files: " + $PythonFiles.Count)

$PythonFailures = @()
$PythonChecked = 0

foreach ($File in $PythonFiles) {

    $PythonChecked++

    & python -m py_compile $File.FullName 2>$null

    if ($LASTEXITCODE -ne 0) {
        $PythonFailures += $File.FullName
    }
}

if ($PythonFailures.Count -eq 0) {

    Add-Result `
        "PYTHON_SYNTAX" `
        "PASS" `
        "Checked $PythonChecked active Python files; syntax errors: 0."
}
else {

    Add-Result `
        "PYTHON_SYNTAX" `
        "FAIL" `
        "Checked $PythonChecked files; syntax failures: $($PythonFailures.Count)."
}

# ============================================================
# [4/9] JSON INTEGRITY
# ============================================================

Write-Host "[4/9] Checking JSON integrity..."

$JsonFiles = @($ActiveFiles | Where-Object { $_.Extension -eq ".json" })

$JsonFailures = @()
$JsonChecked = 0

foreach ($File in $JsonFiles) {

    $JsonChecked++

    try {
        Get-Content -LiteralPath $File.FullName -Raw -ErrorAction Stop |
            ConvertFrom-Json -ErrorAction Stop |
            Out-Null
    }
    catch {
        $JsonFailures += $File.FullName
    }
}

if ($JsonFailures.Count -eq 0) {

    Add-Result `
        "JSON_INTEGRITY" `
        "PASS" `
        "Checked $JsonChecked active JSON files; invalid JSON: 0."
}
else {

    Add-Result `
        "JSON_INTEGRITY" `
        "FAIL" `
        "Checked $JsonChecked files; invalid JSON: $($JsonFailures.Count)."
}

# ============================================================
# [5/9] PROTECTED REPOSITORIES
# ============================================================

Write-Host "[5/9] Checking protected repositories..."

$ProtectedPaths = @(
    "00_FOUNDATION\Architecture\Old_Repositories",
    "11_ARCHIVE\Original_Repositories",
    "15_ROLLBACK_SNAPSHOTS"
)

$ProtectedFailures = @()

foreach ($RelativePath in $ProtectedPaths) {

    $Path = Join-Path $KAIRO $RelativePath

    if (-not (Test-Path -LiteralPath $Path)) {
        $ProtectedFailures += $RelativePath
    }
}

if ($ProtectedFailures.Count -eq 0) {

    Add-Result `
        "PROTECTED_PATHS" `
        "PASS" `
        "All protected repository/rollback roots remain present."
}
else {

    Add-Result `
        "PROTECTED_PATHS" `
        "FAIL" `
        "Missing protected paths: $($ProtectedFailures -join ', ')"
}

# ============================================================
# [6/9] ROLLBACK SNAPSHOT
# ============================================================

Write-Host "[6/9] Checking rollback snapshots..."

$RollbackRoot = Join-Path $KAIRO "15_ROLLBACK_SNAPSHOTS"

$RollbackDirs = @(
    Get-ChildItem `
        -LiteralPath $RollbackRoot `
        -Directory `
        -ErrorAction SilentlyContinue
)

if ($RollbackDirs.Count -gt 0) {

    $LatestRollback = $RollbackDirs |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    $RollbackFiles = @(
        Get-ChildItem `
            -LiteralPath $LatestRollback.FullName `
            -File `
            -Recurse `
            -ErrorAction SilentlyContinue
    )

    if ($RollbackFiles.Count -gt 0) {

        Add-Result `
            "ROLLBACK" `
            "PASS" `
            "Latest rollback snapshot '$($LatestRollback.Name)' contains $($RollbackFiles.Count) files."
    }
    else {

        Add-Result `
            "ROLLBACK" `
            "WARN" `
            "Rollback snapshot directory exists but contains no files."
    }

}
else {

    Add-Result `
        "ROLLBACK" `
        "FAIL" `
        "No rollback snapshot directories found."
}

# ============================================================
# [7/9] STAGE 2 MANIFEST
# ============================================================

Write-Host "[7/9] Checking Stage 2 cleanup manifest..."

$Stage2Manifests = @(
    Get-ChildItem `
        -LiteralPath $REPORT_DIR `
        -Filter "KAIRO_STAGE2_*.json" `
        -File `
        -ErrorAction SilentlyContinue
)

if ($Stage2Manifests.Count -gt 0) {

    $LatestStage2 = $Stage2Manifests |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    try {

        Get-Content `
            -LiteralPath $LatestStage2.FullName `
            -Raw |
            ConvertFrom-Json |
            Out-Null

        Add-Result `
            "STAGE2_MANIFEST" `
            "PASS" `
            "Latest Stage 2 manifest is valid JSON: $($LatestStage2.Name)"
    }
    catch {

        Add-Result `
            "STAGE2_MANIFEST" `
            "FAIL" `
            "Stage 2 manifest could not be parsed."
    }

}
else {

    Add-Result `
        "STAGE2_MANIFEST" `
        "FAIL" `
        "No Stage 2 cleanup manifest found."
}

# ============================================================
# [8/9] ACTIVE TREE HEALTH
# ============================================================

Write-Host "[8/9] Checking active tree health..."

$ForbiddenNames = @(
    "*.pyc",
    "*.pyo",
    ".DS_Store",
    "Thumbs.db"
)

$ForbiddenFiles = @()

foreach ($File in $ActiveFiles) {

    foreach ($Pattern in $ForbiddenNames) {

        if ($File.Name -like $Pattern) {
            $ForbiddenFiles += $File.FullName
        }
    }
}

$ForbiddenFiles = @($ForbiddenFiles | Sort-Object -Unique)

if ($ForbiddenFiles.Count -eq 0) {

    Add-Result `
        "ACTIVE_TREE_HEALTH" `
        "PASS" `
        "No obvious generated/junk files found in active tree."
}
else {

    Add-Result `
        "ACTIVE_TREE_HEALTH" `
        "WARN" `
        "Found $($ForbiddenFiles.Count) generated/junk files."
}

# ============================================================
# [9/9] ARCHITECTURE DIRECTORIES
# ============================================================

Write-Host "[9/9] Checking architecture directories..."

$ArchitectureDirectories = @(
    "01_CORE",
    "02_AGENTS",
    "03_DATA",
    "04_TOOLS",
    "05_UI",
    "06_SECURITY",
    "07_RUNTIME",
    "08_BUSINESS",
    "09_INTELLIGENCE",
    "10_INFRASTRUCTURE"
)

$ArchitectureMissing = @()

foreach ($Dir in $ArchitectureDirectories) {

    $Path = Join-Path $KAIRO $Dir

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        $ArchitectureMissing += $Dir
    }
}

if ($ArchitectureMissing.Count -eq 0) {

    Add-Result `
        "ARCHITECTURE" `
        "PASS" `
        "All target architecture layers exist."
}
else {

    Add-Result `
        "ARCHITECTURE" `
        "FAIL" `
        "Missing architecture layers: $($ArchitectureMissing -join ', ')"
}

# ============================================================
# FINAL RESULT
# ============================================================

$OverallStatus = "PASS"

if ($Failures.Count -gt 0) {
    $OverallStatus = "FAIL"
}
elseif ($Warnings.Count -gt 0) {
    $OverallStatus = "PASS_WITH_WARNINGS"
}

$ReportObject = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    status = $OverallStatus
    active_files = $ActiveFiles.Count
    active_python_files = $PythonChecked
    active_json_files = $JsonChecked
    failures = $Failures
    warnings = $Warnings
    results = $Results
}

$ReportObject |
    ConvertTo-Json -Depth 10 |
    Set-Content -LiteralPath $JsonReport -Encoding UTF8

$Md = @"
# KAIRO Stage 3 V2 Validation

Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

## Overall Status

**$OverallStatus**

## Active Tree

- Active files: $($ActiveFiles.Count)
- Python files checked: $PythonChecked
- JSON files checked: $JsonChecked

## Results

| Check | Status | Detail |
|---|---|---|
"@

foreach ($Key in $Results.Keys) {

    $Status = $Results[$Key].Status
    $Detail = $Results[$Key].Detail.Replace("|", "\|")

    $Md += "`n| $Key | $Status | $Detail |"
}

$Md += @"

## Failures

"@

if ($Failures.Count -eq 0) {
    $Md += "`nNone."
}
else {
    foreach ($Failure in $Failures) {
        $Md += "`n- $Failure"
    }
}

$Md += @"

## Warnings

"@

if ($Warnings.Count -eq 0) {
    $Md += "`nNone."
}
else {
    foreach ($Warning in $Warnings) {
        $Md += "`n- $Warning"
    }
}

$Md += @"

## Safety

- READ-ONLY validation
- No files deleted
- No files moved
- No files modified intentionally
- Protected repositories were not modified
"@

$Md | Set-Content -LiteralPath $MdReport -Encoding UTF8

Write-Host ""
Write-Host "============================================================"
Write-Host "              STAGE 3 V2 VALIDATION COMPLETE"
Write-Host "============================================================"
Write-Host ""
Write-Host "STATUS: $OverallStatus"
Write-Host ""
Write-Host "Active files:        $($ActiveFiles.Count)"
Write-Host "Python files checked: $PythonChecked"
Write-Host "JSON files checked:   $JsonChecked"
Write-Host "Failures:             $($Failures.Count)"
Write-Host "Warnings:             $($Warnings.Count)"
Write-Host ""
Write-Host "JSON REPORT:"
Write-Host $JsonReport
Write-Host ""
Write-Host "MARKDOWN REPORT:"
Write-Host $MdReport
Write-Host ""
