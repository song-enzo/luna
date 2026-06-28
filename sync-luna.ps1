param(
    [Parameter(Position = 0)]
    [string]$Message = ""
)

$ErrorActionPreference = "Stop"

function Is-SafePath {
    param([string]$Path)

    $normalized = $Path -replace '\\', '/'

    if ($normalized -match '^photos/') { return $false }
    if ($normalized -match '^backups/') { return $false }
    if ($normalized -match '^\.service-logs/') { return $false }
    if ($normalized -match '^__pycache__/') { return $false }
    if ($normalized -match '^\.venv/') { return $false }
    if ($normalized -match '^venv/') { return $false }
    if ($normalized -match '^luna\.db') { return $false }
    if ($normalized -match '^luna_backup\.db$') { return $false }
    if ($normalized -match '^local_config\.json$') { return $false }
    if ($normalized -match '^test_gemini_key\.py$') { return $false }
    if ($normalized -match '\.(log|pyc|db|sqlite|sqlite3|bak|encbak|encbak2|tmp)$') { return $false }
    if ($normalized -match '^(test_out|test_final|test_mobile|served_check)\.html$') { return $false }
    if ($normalized -match '^test\.txt$') { return $false }

    return $true
}

$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot

$changes = git status --porcelain=v1 -uall
$safePaths = New-Object System.Collections.Generic.List[string]
$skippedPaths = New-Object System.Collections.Generic.List[string]

foreach ($line in $changes) {
    if ($line.Length -lt 4) { continue }

    $path = $line.Substring(3)
    if ($path -match ' -> ') {
        $path = ($path -split ' -> ')[-1]
    }
    $path = $path.Trim('"')

    if (Is-SafePath $path) {
        $safePaths.Add($path)
    } else {
        $skippedPaths.Add($path)
    }
}

if ($safePaths.Count -eq 0) {
    Write-Host "No safe code changes to sync."
    if ($skippedPaths.Count -gt 0) {
        Write-Host ""
        Write-Host "Skipped runtime/data files:"
        $skippedPaths | Sort-Object -Unique | ForEach-Object { Write-Host "  $_" }
    }
    exit 0
}

Write-Host "Will sync these files:"
$safePaths | Sort-Object -Unique | ForEach-Object { Write-Host "  $_" }

if ($skippedPaths.Count -gt 0) {
    Write-Host ""
    Write-Host "Will skip runtime/data files:"
    $skippedPaths | Sort-Object -Unique | ForEach-Object { Write-Host "  $_" }
}

foreach ($path in ($safePaths | Sort-Object -Unique)) {
    git add -- $path
}

$staged = git diff --cached --name-only
if (-not $staged) {
    Write-Host "Nothing staged after filtering."
    exit 0
}

if ([string]::IsNullOrWhiteSpace($Message)) {
    $Message = "Sync LUNA updates"
}

git commit -m $Message
git push origin main

Write-Host ""
Write-Host "Done. NAS will auto-update from GitHub within about 1 minute."
