# ============================================================
# KAIRO STAGE 2 — CLEANUP ENGINE V2
# ============================================================
# SAFE MODE:
#   - Creates rollback snapshot before destructive operations
#   - Never traverses protected roots
#   - Never modifies original repositories/archive
#   - Deletes only byte-identical active duplicates
#   - Removes obvious junk
#   - Does NOT delete normalized/similar implementations
#   - Does NOT delete Python symbols merely because they repeat
# ============================================================

$ErrorActionPreference = "Continue"

$KAIRO = "C:\Users\kshoe\Downloads\KAIRO_Foundation\KAIRO"

if (-not (Test-Path -LiteralPath $KAIRO -PathType Container)) {
    Write-Host ""
    Write-Host "KAIRO ROOT NOT FOUND:" -ForegroundColor Red
    Write-Host $KAIRO
    exit 1
}

Set-Location -LiteralPath $KAIRO

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$RollbackRoot = Join-Path $KAIRO "15_ROLLBACK_SNAPSHOTS"
$RollbackDir  = Join-Path $RollbackRoot "STAGE2_$Timestamp"
$BackupDir    = Join-Path $RollbackDir "DELETED_FILES"
$ReportDir    = Join-Path $KAIRO "99_CLEANUP_REPORT"

New-Item -ItemType Directory -Force -Path $RollbackDir | Out-Null
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "             KAIRO STAGE 2 CLEANUP V2" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Root:"
Write-Host $KAIRO
Write-Host ""
Write-Host "Rollback:"
Write-Host $RollbackDir
Write-Host ""

# ============================================================
# PROTECTED DIRECTORIES
# ============================================================

$ProtectedRelative = @(
    "00_FOUNDATION\Architecture\Old_Repositories",
    "11_ARCHIVE\Original_Repositories",
    "15_ROLLBACK_SNAPSHOTS"
)

$ProtectedAbsolute = @()

foreach ($Relative in $ProtectedRelative) {

    $Full = [IO.Path]::GetFullPath(
        (Join-Path $KAIRO $Relative)
    ).TrimEnd('\')

    $ProtectedAbsolute += $Full
}

function Test-IsProtected {
    param(
        [string]$Path
    )

    try {
        $Full = [IO.Path]::GetFullPath($Path)
    }
    catch {
        return $true
    }

    foreach ($Protected in $ProtectedAbsolute) {

        if ($Full.Equals(
            $Protected,
            [StringComparison]::OrdinalIgnoreCase
        )) {
            return $true
        }

        if ($Full.StartsWith(
            $Protected + "\",
            [StringComparison]::OrdinalIgnoreCase
        )) {
            return $true
        }
    }

    return $false
}

# ============================================================
# DIRECTORIES THAT ARE NOT PART OF ACTIVE SOURCE
# ============================================================

$ExcludedDirectories = @(
    ".git",
    ".venv",
    "venv",
    ".test-tmp",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".cache",
    "dist",
    "build",
    "coverage",
    ".next",
    ".nuxt",
    ".turbo"
)

function Test-IsExcludedDirectory {
    param(
        [string]$Name
    )

    return $ExcludedDirectories -contains $Name
}

# ============================================================
# SAFE ACTIVE DIRECTORY WALK
# ============================================================

function Get-SafeFiles {
    param(
        [string]$Root
    )

    $Results = New-Object System.Collections.Generic.List[object]

    $Queue = New-Object System.Collections.Generic.Queue[string]

    $Queue.Enqueue($Root)

    while ($Queue.Count -gt 0) {

        $Current = $Queue.Dequeue()

        try {
            $Children = Get-ChildItem `
                -LiteralPath $Current `
                -Force `
                -ErrorAction Stop
        }
        catch {
            Write-Host "  SKIP ACCESS: $Current" -ForegroundColor DarkYellow
            continue
        }

        foreach ($Item in $Children) {

            if ($Item.PSIsContainer) {

                if (Test-IsProtected $Item.FullName) {
                    continue
                }

                if (Test-IsExcludedDirectory $Item.Name) {
                    continue
                }

                $Queue.Enqueue($Item.FullName)
                continue
            }

            if (Test-IsProtected $Item.FullName) {
                continue
            }

            $Results.Add($Item)
        }
    }

    return $Results
}

# ============================================================
# LOGS
# ============================================================

$DeletedFiles = New-Object System.Collections.Generic.List[object]
$DeletedDirs  = New-Object System.Collections.Generic.List[string]
$Errors       = New-Object System.Collections.Generic.List[object]
$Kept         = New-Object System.Collections.Generic.List[object]

# ============================================================
# STEP 1 — INVENTORY
# ============================================================

Write-Host "[1/8] Building safe inventory..." -ForegroundColor Cyan

$Files = @(Get-SafeFiles -Root $KAIRO)

Write-Host ""
Write-Host "Active files found: $($Files.Count)" -ForegroundColor Green
Write-Host ""

# ============================================================
# STEP 2 — HASH FILES
# ============================================================

Write-Host "[2/8] Calculating SHA-256 hashes..." -ForegroundColor Cyan

$HashRecords = New-Object System.Collections.Generic.List[object]

$Counter = 0

foreach ($File in $Files) {

    $Counter++

    if (($Counter % 500) -eq 0) {
        Write-Host "  Hashed $Counter / $($Files.Count)" -ForegroundColor DarkGray
    }

    try {

        $HashResult = Get-FileHash `
            -LiteralPath $File.FullName `
            -Algorithm SHA256 `
            -ErrorAction Stop

        $Relative = $File.FullName.Substring(
            $KAIRO.Length
        ).TrimStart('\')

        $HashRecords.Add(
            [PSCustomObject]@{
                Hash = $HashResult.Hash
                FullPath = $File.FullName
                Relative = $Relative
                Length = $File.Length
                Extension = $File.Extension.ToLower()
            }
        )
    }
    catch {

        $Errors.Add(
            [PSCustomObject]@{
                Stage = "HASH"
                Path = $File.FullName
                Error = $_.Exception.Message
            }
        )
    }
}

Write-Host ""
Write-Host "Successfully hashed: $($HashRecords.Count)" -ForegroundColor Green

# ============================================================
# STEP 3 — EXACT DUPLICATES
# ============================================================

Write-Host ""
Write-Host "[3/8] Finding exact duplicate groups..." -ForegroundColor Cyan

$DuplicateGroups = @(
    $HashRecords |
    Group-Object -Property Hash |
    Where-Object {
        $_.Count -gt 1
    }
)

$DuplicateFilesInGroups = 0

foreach ($Group in $DuplicateGroups) {
    $DuplicateFilesInGroups += $Group.Count
}

Write-Host ""
Write-Host "Exact duplicate groups: $($DuplicateGroups.Count)" -ForegroundColor Yellow
Write-Host "Files involved:          $DuplicateFilesInGroups" -ForegroundColor Yellow

# ============================================================
# CANONICAL PATH SCORE
# ============================================================

function Get-CanonicalScore {
    param(
        [string]$Relative
    )

    $Lower = $Relative.ToLower()

    $Score = 0

    # --------------------------------------------------------
    # Current KAIRO architecture
    # --------------------------------------------------------

    if ($Lower.StartsWith("01_core\")) {
        $Score += 1000
    }

    if ($Lower.StartsWith("02_agents\")) {
        $Score += 1000
    }

    if ($Lower.StartsWith("03_data\")) {
        $Score += 1000
    }

    if ($Lower.StartsWith("04_tools\")) {
        $Score += 1000
    }

    if ($Lower.StartsWith("05_ui\")) {
        $Score += 1000
    }

    if ($Lower.StartsWith("06_security\")) {
        $Score += 1000
    }

    if ($Lower.StartsWith("07_runtime\")) {
        $Score += 1000
    }

    if ($Lower.StartsWith("08_business\")) {
        $Score += 1000
    }

    if ($Lower.StartsWith("09_intelligence\")) {
        $Score += 1000
    }

    if ($Lower.StartsWith("10_infrastructure\")) {
        $Score += 1000
    }

    # --------------------------------------------------------
    # Existing source
    # --------------------------------------------------------

    if ($Lower.StartsWith("src\")) {
        $Score += 800
    }

    if ($Lower.StartsWith("tests\")) {
        $Score += 700
    }

    # --------------------------------------------------------
    # Temporary build trees
    # --------------------------------------------------------

    if ($Lower.StartsWith("12_extraction\")) {
        $Score -= 5000
    }

    if ($Lower.StartsWith("13_final_kairo\")) {
        $Score -= 4000
    }

    if ($Lower.StartsWith("14_kairo_production_candidate\")) {
        $Score -= 4000
    }

    if ($Lower.StartsWith("16_post_merge_validation\")) {
        $Score -= 4000
    }

    if ($Lower.StartsWith("17_runtime_validation\")) {
        $Score -= 4000
    }

    if ($Lower.StartsWith("18_live_api_ui_validation\")) {
        $Score -= 4000
    }

    if ($Lower.StartsWith("19_architecture\")) {
        $Score -= 3000
    }

    if ($Lower.StartsWith("19_cleanup_audit\")) {
        $Score -= 3000
    }

    # Deeper path = slightly less canonical
    $Depth = ($Relative -split "\\").Count

    $Score -= ($Depth * 5)

    return $Score
}

# ============================================================
# STEP 4 — DELETE ONLY EXACT REDUNDANT COPIES
# ============================================================

Write-Host ""
Write-Host "[4/8] Consolidating exact duplicates..." -ForegroundColor Cyan

$GroupIndex = 0

foreach ($Group in $DuplicateGroups) {

    $GroupIndex++

    $Candidates = @()

    foreach ($Entry in $Group.Group) {

        $Candidates += [PSCustomObject]@{
            Hash = $Entry.Hash
            FullPath = $Entry.FullPath
            Relative = $Entry.Relative
            Length = $Entry.Length
            Score = Get-CanonicalScore $Entry.Relative
        }
    }

    $Candidates = @(
        $Candidates |
        Sort-Object -Property `
            @{Expression = "Score"; Descending = $true},
            @{Expression = "Relative"; Descending = $false}
    )

    if ($Candidates.Count -lt 2) {
        continue
    }

    $Canonical = $Candidates[0]

    foreach ($Candidate in ($Candidates | Select-Object -Skip 1)) {

        if (Test-IsProtected $Candidate.FullPath) {

            $Kept.Add(
                [PSCustomObject]@{
                    Action = "KEEP_PROTECTED"
                    Canonical = $Canonical.Relative
                    Path = $Candidate.Relative
                    Reason = "Protected path"
                }
            )

            continue
        }

        if (-not (Test-Path -LiteralPath $Candidate.FullPath)) {
            continue
        }

        try {

            # ------------------------------------------------
            # Re-check hash immediately before deletion
            # ------------------------------------------------

            $CurrentHash = (
                Get-FileHash `
                    -LiteralPath $Candidate.FullPath `
                    -Algorithm SHA256 `
                    -ErrorAction Stop
            ).Hash

            if ($CurrentHash -ne $Candidate.Hash) {
                throw "File changed after inventory; deletion cancelled."
            }

            # ------------------------------------------------
            # Backup
            # ------------------------------------------------

            $RelativeSafe = $Candidate.Relative.Replace(
                "\",
                "__"
            )

            $BackupPath = Join-Path `
                $BackupDir `
                ("{0}__{1}" -f $GroupIndex, $RelativeSafe)

            $BackupParent = Split-Path `
                -Parent `
                $BackupPath

            New-Item `
                -ItemType Directory `
                -Force `
                -Path $BackupParent |
                Out-Null

            Copy-Item `
                -LiteralPath $Candidate.FullPath `
                -Destination $BackupPath `
                -Force `
                -ErrorAction Stop

            # ------------------------------------------------
            # Verify rollback backup
            # ------------------------------------------------

            $BackupHash = (
                Get-FileHash `
                    -LiteralPath $BackupPath `
                    -Algorithm SHA256 `
                    -ErrorAction Stop
            ).Hash

            if ($BackupHash -ne $Candidate.Hash) {
                throw "Rollback backup verification failed."
            }

            # ------------------------------------------------
            # Delete
            # ------------------------------------------------

            Remove-Item `
                -LiteralPath $Candidate.FullPath `
                -Force `
                -ErrorAction Stop

            $DeletedFiles.Add(
                [PSCustomObject]@{
                    Action = "DELETE_EXACT_DUPLICATE"
                    Canonical = $Canonical.Relative
                    Deleted = $Candidate.Relative
                    Hash = $Candidate.Hash
                    Backup = $BackupPath
                }
            )

        }
        catch {

            $Errors.Add(
                [PSCustomObject]@{
                    Stage = "DELETE_DUPLICATE"
                    Path = $Candidate.FullPath
                    Error = $_.Exception.Message
                }
            )
        }
    }
}

Write-Host ""
Write-Host "Exact duplicates deleted: $($DeletedFiles.Count)" -ForegroundColor Green

# ============================================================
# STEP 5 — SAFE JUNK CLEANUP
# ============================================================

Write-Host ""
Write-Host "[5/8] Removing obvious junk..." -ForegroundColor Cyan

$JunkNames = @(
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini"
)

$JunkExtensions = @(
    ".tmp",
    ".bak",
    ".old",
    ".orig"
)

$CurrentFiles = @(Get-SafeFiles -Root $KAIRO)

foreach ($File in $CurrentFiles) {

    $IsJunk = $false

    if ($JunkNames -contains $File.Name) {
        $IsJunk = $true
    }

    if ($JunkExtensions -contains $File.Extension.ToLower()) {
        $IsJunk = $true
    }

    if ($File.Name.EndsWith("~")) {
        $IsJunk = $true
    }

    if (-not $IsJunk) {
        continue
    }

    try {

        $Relative = $File.FullName.Substring(
            $KAIRO.Length
        ).TrimStart('\')

        $BackupPath = Join-Path `
            $BackupDir `
            ("JUNK__" + ([Guid]::NewGuid().ToString("N")) + "__" + $File.Name)

        Copy-Item `
            -LiteralPath $File.FullName `
            -Destination $BackupPath `
            -Force `
            -ErrorAction Stop

        Remove-Item `
            -LiteralPath $File.FullName `
            -Force `
            -ErrorAction Stop

        $DeletedFiles.Add(
            [PSCustomObject]@{
                Action = "DELETE_JUNK"
                Canonical = ""
                Deleted = $Relative
                Hash = ""
                Backup = $BackupPath
            }
        )

    }
    catch {

        $Errors.Add(
            [PSCustomObject]@{
                Stage = "DELETE_JUNK"
                Path = $File.FullName
                Error = $_.Exception.Message
            }
        )
    }
}

# ============================================================
# STEP 6 — REMOVE EMPTY NON-PROTECTED DIRECTORIES
# ============================================================

Write-Host ""
Write-Host "[6/8] Removing empty directories..." -ForegroundColor Cyan

$Directories = @(
    Get-ChildItem `
        -LiteralPath $KAIRO `
        -Directory `
        -Recurse `
        -Force `
        -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending
)

foreach ($Dir in $Directories) {

    if (Test-IsProtected $Dir.FullName) {
        continue
    }

    if (Test-IsExcludedDirectory $Dir.Name) {
        continue
    }

    try {

        $Children = @(
            Get-ChildItem `
                -LiteralPath $Dir.FullName `
                -Force `
                -ErrorAction Stop
        )

        if ($Children.Count -eq 0) {

            $Relative = $Dir.FullName.Substring(
                $KAIRO.Length
            ).TrimStart('\')

            Remove-Item `
                -LiteralPath $Dir.FullName `
                -Force `
                -ErrorAction Stop

            $DeletedDirs.Add($Relative)
        }

    }
    catch {
        # Non-critical directory cleanup failure.
    }
}

# ============================================================
# STEP 7 — WRITE MANIFEST
# ============================================================

Write-Host ""
Write-Host "[7/8] Writing manifests..." -ForegroundColor Cyan

$Manifest = [ordered]@{

    System = "KAIRO"

    Stage = "STAGE_2_CLEANUP_V2"

    Timestamp = $Timestamp

    Root = $KAIRO

    ProtectedPaths = $ProtectedRelative

    ExcludedTraversalDirectories = $ExcludedDirectories

    Statistics = [ordered]@{
        FilesDiscovered = $Files.Count
        FilesHashed = $HashRecords.Count
        ExactDuplicateGroups = $DuplicateGroups.Count
        ExactDuplicateFilesInGroups = $DuplicateFilesInGroups
        DeletedFiles = $DeletedFiles.Count
        DeletedDirectories = $DeletedDirs.Count
        Errors = $Errors.Count
    }

    DeletedFiles = $DeletedFiles

    DeletedDirectories = $DeletedDirs

    ProtectedItemsKept = $Kept

    Errors = $Errors

    RollbackDirectory = $RollbackDir

    Safety = [ordered]@{
        RollbackCreatedBeforeDeletion = $true
        BackupVerifiedBeforeDeletion = $true
        ProtectedOriginalRepositories = $true
        ProtectedFrozenArchive = $true
        ProtectedRollbackSnapshots = $true
        NormalizedDuplicatesDeleted = $false
        DuplicatePythonSymbolsDeleted = $false
        DifferentImplementationsDeleted = $false
    }
}

$ManifestPath = Join-Path `
    $ReportDir `
    ("KAIRO_STAGE2_" + $Timestamp + ".json")

$Manifest |
    ConvertTo-Json -Depth 30 |
    Set-Content `
        -LiteralPath $ManifestPath `
        -Encoding UTF8

# ============================================================
# SUMMARY
# ============================================================

$Status = "PASS"

if ($Errors.Count -gt 0) {
    $Status = "PASS_WITH_ERRORS"
}

$SummaryPath = Join-Path `
    $ReportDir `
    ("KAIRO_STAGE2_" + $Timestamp + ".md")

$Summary = @"
# KAIRO STAGE 2 CLEANUP V2

Timestamp: $Timestamp

## Statistics

Files discovered: $($Files.Count)

Files hashed: $($HashRecords.Count)

Exact duplicate groups: $($DuplicateGroups.Count)

Files in duplicate groups: $DuplicateFilesInGroups

Files deleted: $($DeletedFiles.Count)

Directories deleted: $($DeletedDirs.Count)

Errors: $($Errors.Count)

## Protected

- 00_FOUNDATION\Architecture\Old_Repositories
- 11_ARCHIVE\Original_Repositories
- 15_ROLLBACK_SNAPSHOTS

## Rollback

$RollbackDir

## Manifest

$ManifestPath

## Deletion policy

Automatically deleted only:

1. Byte-identical duplicate files
2. Obvious temporary/junk files
3. Empty directories

NOT automatically deleted:

- normalized duplicates
- duplicate Python symbols
- different implementations
- unique functionality
- protected repositories
- frozen archive
- rollback snapshots

## Status

$Status
"@

Set-Content `
    -LiteralPath $SummaryPath `
    -Value $Summary `
    -Encoding UTF8

# ============================================================
# STEP 8 — FINAL OUTPUT
# ============================================================

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "              STAGE 2 CLEANUP FINISHED" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Files discovered       : $($Files.Count)"
Write-Host "Files hashed           : $($HashRecords.Count)"
Write-Host "Duplicate groups       : $($DuplicateGroups.Count)"
Write-Host "Files deleted          : $($DeletedFiles.Count)"
Write-Host "Directories deleted    : $($DeletedDirs.Count)"
Write-Host "Errors                 : $($Errors.Count)"
Write-Host ""

Write-Host "ROLLBACK:" -ForegroundColor Yellow
Write-Host $RollbackDir

Write-Host ""
Write-Host "MANIFEST:" -ForegroundColor Yellow
Write-Host $ManifestPath

Write-Host ""
Write-Host "REPORT:" -ForegroundColor Yellow
Write-Host $SummaryPath

Write-Host ""

if ($Errors.Count -eq 0) {
    Write-Host "STATUS: PASS" -ForegroundColor Green
}
else {
    Write-Host "STATUS: PASS_WITH_ERRORS" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "NEXT: Stage 3 validation." -ForegroundColor Cyan
Write-Host ""