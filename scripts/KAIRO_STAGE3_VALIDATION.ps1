# ============================================================
# KAIRO STAGE 3 — POST-CLEANUP VALIDATION
# ============================================================
# READ-ONLY
# NO DELETE
# NO MOVE
# NO MODIFY
# NO OVERWRITE
# ============================================================

$ErrorActionPreference = "Continue"

$KAIRO = "C:\Users\kshoe\Downloads\KAIRO_Foundation\KAIRO"

Set-Location -LiteralPath $KAIRO

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$ReportDir = Join-Path $KAIRO "99_CLEANUP_REPORT"

New-Item `
    -ItemType Directory `
    -Force `
    -Path $ReportDir |
    Out-Null

$Results = New-Object System.Collections.Generic.List[object]

function Add-Result {
    param(
        [string]$Name,
        [string]$Status,
        [string]$Details
    )

    $Results.Add(
        [PSCustomObject]@{
            Check = $Name
            Status = $Status
            Details = $Details
        }
    )
}

function Test-PathExists {
    param(
        [string]$Relative,
        [string]$Type
    )

    $Path = Join-Path $KAIRO $Relative

    if ($Type -eq "Directory") {
        return Test-Path -LiteralPath $Path -PathType Container
    }

    return Test-Path -LiteralPath $Path -PathType Leaf
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "          KAIRO STAGE 3 POST-CLEANUP VALIDATION" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "READ-ONLY VALIDATION" -ForegroundColor Yellow
Write-Host ""

# ============================================================
# 1. CORE STRUCTURE
# ============================================================

Write-Host "[1/9] Checking KAIRO core structure..." -ForegroundColor Cyan

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

    if (-not (Test-PathExists $Dir "Directory")) {
        $MissingDirectories += $Dir
    }
}

if ($MissingDirectories.Count -eq 0) {

    Add-Result `
        "Core Architecture Directories" `
        "PASS" `
        "All required directories exist."

}
else {

    Add-Result `
        "Core Architecture Directories" `
        "FAIL" `
        ("Missing: " + ($MissingDirectories -join ", "))
}

# ============================================================
# 2. CORE FILES
# ============================================================

Write-Host "[2/9] Checking core files..." -ForegroundColor Cyan

$RequiredFiles = @(
    "src\core\kairo_core.py",
    "src\core\runtime_controller.py",
    "src\api\server.py",
    "07_RUNTIME\Events\event_bus.py",
    "07_RUNTIME\State\runtime_state.py",
    "07_RUNTIME\Task_Manager\task_manager.py",
    "05_UI\Web\index.html",
    "05_UI\Web\style.css",
    "05_UI\Web\app.js",
    "requirements.txt"
)

$MissingFiles = @()

foreach ($File in $RequiredFiles) {

    if (-not (Test-PathExists $File "File")) {
        $MissingFiles += $File
    }
}

if ($MissingFiles.Count -eq 0) {

    Add-Result `
        "Core Runtime/API/UI Files" `
        "PASS" `
        "Required operational files exist."

}
else {

    Add-Result `
        "Core Runtime/API/UI Files" `
        "FAIL" `
        ("Missing: " + ($MissingFiles -join ", "))
}

# ============================================================
# 3. PYTHON SYNTAX
# ============================================================

Write-Host "[3/9] Checking Python syntax..." -ForegroundColor Cyan

$PythonFiles = @(
    Get-ChildItem `
        -LiteralPath $KAIRO `
        -Filter "*.py" `
        -File `
        -Recurse `
        -Force `
        -ErrorAction SilentlyContinue |
    Where-Object {
        $_.FullName -notmatch "\\.venv\\" -and
        $_.FullName -notmatch "\\\.git\\" -and
        $_.FullName -notmatch "\\__pycache__\\" -and
        $_.FullName -notmatch "\\\.test-tmp\\" -and
        $_.FullName -notmatch "\\12_EXTRACTION\\" -and
        $_.FullName -notmatch "\\15_ROLLBACK_SNAPSHOTS\\"
    }
)

$PythonFailures = New-Object System.Collections.Generic.List[object]

foreach ($File in $PythonFiles) {

    try {

        $Output = & python -m py_compile `
            $File.FullName `
            2>&1

        if ($LASTEXITCODE -ne 0) {

            $PythonFailures.Add(
                [PSCustomObject]@{
                    File = $File.FullName
                    Error = ($Output -join " ")
                }
            )
        }

    }
    catch {

        $PythonFailures.Add(
            [PSCustomObject]@{
                File = $File.FullName
                Error = $_.Exception.Message
            }
        )
    }
}

if ($PythonFailures.Count -eq 0) {

    Add-Result `
        "Python Syntax" `
        "PASS" `
        ("Checked " + $PythonFiles.Count + " Python files.")

}
else {

    Add-Result `
        "Python Syntax" `
        "FAIL" `
        ($PythonFailures.Count.ToString() + " Python files failed.")
}

# ============================================================
# 4. JSON VALIDATION
# ============================================================

Write-Host "[4/9] Checking JSON integrity..." -ForegroundColor Cyan

$JsonFiles = @(
    Get-ChildItem `
        -LiteralPath $KAIRO `
        -Filter "*.json" `
        -File `
        -Recurse `
        -Force `
        -ErrorAction SilentlyContinue |
    Where-Object {
        $_.FullName -notmatch "\\\.venv\\" -and
        $_.FullName -notmatch "\\\.git\\" -and
        $_.FullName -notmatch "\\\.test-tmp\\" -and
        $_.FullName -notmatch "\\15_ROLLBACK_SNAPSHOTS\\"
    }
)

$JsonFailures = New-Object System.Collections.Generic.List[object]

foreach ($File in $JsonFiles) {

    try {

        Get-Content `
            -LiteralPath $File.FullName `
            -Raw `
            -ErrorAction Stop |
        ConvertFrom-Json `
            -ErrorAction Stop |
        Out-Null

    }
    catch {

        $JsonFailures.Add(
            [PSCustomObject]@{
                File = $File.FullName
                Error = $_.Exception.Message
            }
        )
    }
}

if ($JsonFailures.Count -eq 0) {

    Add-Result `
        "JSON Integrity" `
        "PASS" `
        ("Checked " + $JsonFiles.Count + " JSON files.")

}
else {

    Add-Result `
        "JSON Integrity" `
        "FAIL" `
        ($JsonFailures.Count.ToString() + " JSON files failed.")
}

# ============================================================
# 5. PROTECTED PATHS
# ============================================================

Write-Host "[5/9] Checking protected repositories..." -ForegroundColor Cyan

$ProtectedPaths = @(
    "00_FOUNDATION\Architecture\Old_Repositories",
    "11_ARCHIVE\Original_Repositories",
    "15_ROLLBACK_SNAPSHOTS"
)

$ProtectedFailures = @()

foreach ($Path in $ProtectedPaths) {

    if (-not (Test-PathExists $Path "Directory")) {
        $ProtectedFailures += $Path
    }
}

if ($ProtectedFailures.Count -eq 0) {

    Add-Result `
        "Protected Paths" `
        "PASS" `
        "All protected paths exist."

}
else {

    Add-Result `
        "Protected Paths" `
        "FAIL" `
        ("Missing: " + ($ProtectedFailures -join ", "))
}

# ============================================================
# 6. ROLLBACK SNAPSHOT
# ============================================================

Write-Host "[6/9] Checking rollback snapshot..." -ForegroundColor Cyan

$RollbackRoot = Join-Path $KAIRO "15_ROLLBACK_SNAPSHOTS"

$Stage2Snapshots = @(
    Get-ChildItem `
        -LiteralPath $RollbackRoot `
        -Directory `
        -Filter "STAGE2_*" `
        -ErrorAction SilentlyContinue
)

if ($Stage2Snapshots.Count -gt 0) {

    $LatestSnapshot = $Stage2Snapshots |
        Sort-Object Name -Descending |
        Select-Object -First 1

    $DeletedBackupDir = Join-Path `
        $LatestSnapshot.FullName `
        "DELETED_FILES"

    if (Test-Path -LiteralPath $DeletedBackupDir -PathType Container) {

        $BackupCount = @(
            Get-ChildItem `
                -LiteralPath $DeletedBackupDir `
                -File `
                -ErrorAction SilentlyContinue
        ).Count

        Add-Result `
            "Rollback Snapshot" `
            "PASS" `
            ("Latest snapshot: " + $LatestSnapshot.Name + "; backup files: " + $BackupCount)

    }
    else {

        Add-Result `
            "Rollback Snapshot" `
            "FAIL" `
            "DELETED_FILES directory missing."

    }

}
else {

    Add-Result `
        "Rollback Snapshot" `
        "FAIL" `
        "No STAGE2 rollback snapshot found."
}

# ============================================================
# 7. CLEANUP MANIFEST
# ============================================================

Write-Host "[7/9] Checking cleanup manifest..." -ForegroundColor Cyan

$ManifestFiles = @(
    Get-ChildItem `
        -LiteralPath $ReportDir `
        -Filter "KAIRO_STAGE2_*.json" `
        -File `
        -ErrorAction SilentlyContinue
)

if ($ManifestFiles.Count -gt 0) {

    $LatestManifest = $ManifestFiles |
        Sort-Object Name -Descending |
        Select-Object -First 1

    try {

        $ManifestObject = Get-Content `
            -LiteralPath $LatestManifest.FullName `
            -Raw |
        ConvertFrom-Json `
            -ErrorAction Stop

        Add-Result `
            "Cleanup Manifest" `
            "PASS" `
            ("Manifest readable: " + $LatestManifest.Name)

    }
    catch {

        Add-Result `
            "Cleanup Manifest" `
            "FAIL" `
            $_.Exception.Message
    }

}
else {

    Add-Result `
        "Cleanup Manifest" `
        "FAIL" `
        "No Stage 2 manifest found."
}

# ============================================================
# 8. ROLLBACK BACKUP HASH VALIDATION
# ============================================================

Write-Host "[8/9] Verifying rollback backup integrity..." -ForegroundColor Cyan

$RollbackHashFailures = New-Object System.Collections.Generic.List[object]

if ($Stage2Snapshots.Count -gt 0) {

    $LatestSnapshot = $Stage2Snapshots |
        Sort-Object Name -Descending |
        Select-Object -First 1

    $BackupDir = Join-Path `
        $LatestSnapshot.FullName `
        "DELETED_FILES"

    if (Test-Path -LiteralPath $BackupDir -PathType Container) {

        $BackupFiles = @(
            Get-ChildItem `
                -LiteralPath $BackupDir `
                -File `
                -ErrorAction SilentlyContinue
        )

        foreach ($BackupFile in $BackupFiles) {

            try {

                $Hash = Get-FileHash `
                    -LiteralPath $BackupFile.FullName `
                    -Algorithm SHA256 `
                    -ErrorAction Stop

                if ([string]::IsNullOrWhiteSpace($Hash.Hash)) {

                    $RollbackHashFailures.Add(
                        $BackupFile.FullName
                    )
                }

            }
            catch {

                $RollbackHashFailures.Add(
                    $BackupFile.FullName
                )
            }
        }
    }
}

if ($RollbackHashFailures.Count -eq 0) {

    Add-Result `
        "Rollback Backup Integrity" `
        "PASS" `
        "Rollback backup files are readable and hashable."

}
else {

    Add-Result `
        "Rollback Backup Integrity" `
        "FAIL" `
        ($RollbackHashFailures.Count.ToString() + " backup files failed.")
}

# ============================================================
# 9. LEGACY / EXTRA STRUCTURE REPORT
# ============================================================

Write-Host "[9/9] Inspecting remaining legacy/build structures..." -ForegroundColor Cyan

$LegacyDirectories = @(
    "07_KAIRO_OS",
    "10_DOCUMENTATION",
    "12_EXTRACTION",
    "13_FINAL_KAIRO",
    "14_KAIRO_PRODUCTION_CANDIDATE",
    "16_POST_MERGE_VALIDATION",
    "17_RUNTIME_VALIDATION",
    "18_LIVE_API_UI_VALIDATION",
    "19_ARCHITECTURE",
    "19_CLEANUP_AUDIT",
    "99_DEEP_SCAN_REPORT"
)

$LegacyFound = @()

foreach ($Dir in $LegacyDirectories) {

    if (Test-PathExists $Dir "Directory") {
        $LegacyFound += $Dir
    }
}

Add-Result `
    "Legacy Structure Inventory" `
    "INFO" `
    ("Remaining structures: " + ($LegacyFound -join ", "))

# ============================================================
# FINAL SUMMARY
# ============================================================

$PassCount = @(
    $Results |
    Where-Object { $_.Status -eq "PASS" }
).Count

$FailCount = @(
    $Results |
    Where-Object { $_.Status -eq "FAIL" }
).Count

$InfoCount = @(
    $Results |
    Where-Object { $_.Status -eq "INFO" }
).Count

if ($FailCount -eq 0) {
    $Overall = "PASS"
}
else {
    $Overall = "REVIEW_REQUIRED"
}

$OutputObject = [ordered]@{
    System = "KAIRO"
    Stage = "STAGE_3_POST_CLEANUP_VALIDATION"
    Timestamp = $Timestamp
    Mode = "READ_ONLY"
    Overall = $Overall

    Statistics = [ordered]@{
        Pass = $PassCount
        Fail = $FailCount
        Info = $InfoCount
        PythonFiles = $PythonFiles.Count
        PythonFailures = $PythonFailures.Count
        JsonFiles = $JsonFiles.Count
        JsonFailures = $JsonFailures.Count
        RollbackHashFailures = $RollbackHashFailures.Count
    }

    Results = $Results

    PythonFailures = $PythonFailures

    JsonFailures = $JsonFailures

    RollbackHashFailures = $RollbackHashFailures
}

$JsonReport = Join-Path `
    $ReportDir `
    ("KAIRO_STAGE3_VALIDATION_" + $Timestamp + ".json")

$MdReport = Join-Path `
    $ReportDir `
    ("KAIRO_STAGE3_VALIDATION_" + $Timestamp + ".md")

$OutputObject |
    ConvertTo-Json -Depth 30 |
    Set-Content `
        -LiteralPath $JsonReport `
        -Encoding UTF8

$Markdown = @"
# KAIRO STAGE 3 — POST-CLEANUP VALIDATION

Timestamp: $Timestamp

Mode: READ-ONLY

Overall Status: $Overall

## Statistics

PASS: $PassCount

FAIL: $FailCount

INFO: $InfoCount

Python files checked: $($PythonFiles.Count)

Python failures: $($PythonFailures.Count)

JSON files checked: $($JsonFiles.Count)

JSON failures: $($JsonFailures.Count)

Rollback hash failures: $($RollbackHashFailures.Count)

## Results

$(
    ($Results |
        Format-Table -AutoSize |
        Out-String)
)

## Important

This validation stage performed no deletion, movement, or modification of KAIRO files.
"@

Set-Content `
    -LiteralPath $MdReport `
    -Value $Markdown `
    -Encoding UTF8

# ============================================================
# CONSOLE OUTPUT
# ============================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "             STAGE 3 VALIDATION FINISHED" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

$Results |
    Format-Table `
        Check,
        Status,
        Details `
        -AutoSize

Write-Host ""
Write-Host "Overall: $Overall" -ForegroundColor $(if ($Overall -eq "PASS") { "Green" } else { "Yellow" })

Write-Host ""
Write-Host "JSON REPORT:"
Write-Host $JsonReport

Write-Host ""
Write-Host "MARKDOWN REPORT:"
Write-Host $MdReport

Write-Host ""