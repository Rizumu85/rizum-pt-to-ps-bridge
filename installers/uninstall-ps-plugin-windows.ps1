$ErrorActionPreference = "Stop"

function Write-Step {
    param([string] $Message)
    Write-Host "[Rizum] $Message"
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$manifestPath = Join-Path $repoRoot "ps_plugin\manifest.json"

if (-not (Test-Path -LiteralPath $manifestPath)) {
    throw "Could not find Photoshop UXP manifest: $manifestPath"
}

$manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
$pluginId = [string] $manifest.id

if ([string]::IsNullOrWhiteSpace($pluginId)) {
    throw "manifest.json is missing id."
}

$uxpRoot = Join-Path $env:APPDATA "Adobe\UXP"
$externalRoot = Join-Path $uxpRoot "Plugins\External"
$target = Join-Path $externalRoot $pluginId
$pluginsInfoRoot = Join-Path $uxpRoot "PluginsInfo\v1"
$psRegistryPath = Join-Path $pluginsInfoRoot "PS.json"

Write-Step "Plugin ID: $pluginId"
Write-Step "Target: $target"
Write-Step "Registry: $psRegistryPath"

$resolvedExternalRoot = [System.IO.Path]::GetFullPath($externalRoot)
$resolvedTarget = [System.IO.Path]::GetFullPath($target)
if (-not $resolvedTarget.StartsWith($resolvedExternalRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove target outside Adobe UXP External plugins: $resolvedTarget"
}

if (Test-Path -LiteralPath $target) {
    Remove-Item -LiteralPath $target -Recurse -Force
    Write-Step "Removed UXP plugin folder."
} else {
    Write-Step "UXP plugin folder was already absent."
}

if (Test-Path -LiteralPath $psRegistryPath) {
    $registry = Get-Content -Raw -LiteralPath $psRegistryPath | ConvertFrom-Json
    if ($null -eq $registry.plugins) {
        $registry | Add-Member -NotePropertyName "plugins" -NotePropertyValue @()
    }

    $before = @($registry.plugins).Count
    $registry.plugins = @($registry.plugins | Where-Object { $_.pluginId -ne $pluginId })
    $after = @($registry.plugins).Count

    $json = $registry | ConvertTo-Json -Depth 10
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($psRegistryPath, $json, $utf8NoBom)

    Write-Step "Removed $($before - $after) registry entr$(if (($before - $after) -eq 1) { 'y' } else { 'ies' }) from PS.json."
} else {
    Write-Step "PS.json registry file was already absent."
}

Write-Host ""
Write-Host "Next:"
Write-Host "  1. Close Photoshop completely if it is open."
Write-Host "  2. Reopen Photoshop."
Write-Host "  3. Confirm Plugins -> Rizum PT Bridge is gone."
