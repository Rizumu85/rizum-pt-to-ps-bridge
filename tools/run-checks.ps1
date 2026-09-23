$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$failed = @()

Push-Location $repo
try {
    python -m pytest tests -q -p no:cacheprovider
    if ($LASTEXITCODE) { $failed += 'Painter tests' }
} finally { Pop-Location }

Push-Location (Join-Path $repo 'desktop')
try {
    bun run typecheck
    if ($LASTEXITCODE) { $failed += 'desktop typecheck' }
    bun run test
    if ($LASTEXITCODE) { $failed += 'desktop tests' }
} finally { Pop-Location }

if ($failed) {
    Write-Host "Failed: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host 'All checks passed.' -ForegroundColor Green
