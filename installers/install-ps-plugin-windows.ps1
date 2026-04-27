$ErrorActionPreference = "Stop"

function Write-Step {
    param([string] $Message)
    Write-Host "[Rizum] $Message"
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$source = Join-Path $repoRoot "ps_plugin"
$manifestPath = Join-Path $source "manifest.json"

if (-not (Test-Path -LiteralPath $manifestPath)) {
    throw "Could not find Photoshop UXP manifest: $manifestPath"
}

$manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
$pluginId = [string] $manifest.id
$pluginName = [string] $manifest.name
$pluginVersion = [string] $manifest.version
$hostMinVersion = [string] $manifest.host.minVersion

if ([string]::IsNullOrWhiteSpace($pluginId)) {
    throw "manifest.json is missing id."
}

$uxpRoot = Join-Path $env:APPDATA "Adobe\UXP"
$externalRoot = Join-Path $uxpRoot "Plugins\External"
$target = Join-Path $externalRoot $pluginId
$pluginsInfoRoot = Join-Path $uxpRoot "PluginsInfo\v1"
$psRegistryPath = Join-Path $pluginsInfoRoot "PS.json"

Write-Step "Source: $source"
Write-Step "Target: $target"
Write-Step "Registry: $psRegistryPath"

$resolvedExternalRoot = [System.IO.Path]::GetFullPath($externalRoot)
$resolvedTarget = [System.IO.Path]::GetFullPath($target)
if (-not $resolvedTarget.StartsWith($resolvedExternalRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to clean target outside Adobe UXP External plugins: $resolvedTarget"
}

New-Item -ItemType Directory -Force -Path $target | Out-Null
Get-ChildItem -LiteralPath $target -Force | Remove-Item -Recurse -Force
Copy-Item -Path (Join-Path $source "*") -Destination $target -Recurse -Force
Write-Step "Copied UXP plugin files."

New-Item -ItemType Directory -Force -Path $pluginsInfoRoot | Out-Null

if (Test-Path -LiteralPath $psRegistryPath) {
    $registry = Get-Content -Raw -LiteralPath $psRegistryPath | ConvertFrom-Json
    if ($null -eq $registry.plugins) {
        $registry | Add-Member -NotePropertyName "plugins" -NotePropertyValue @()
    }
} else {
    $registry = [pscustomobject]@{
        plugins = @()
    }
}

$entry = [pscustomobject]@{
    hostMinVersion = $hostMinVersion
    name = $pluginName
    path = ('$localPlugins\External\' + $pluginId)
    pluginId = $pluginId
    status = "enabled"
    type = "uxp"
    versionString = $pluginVersion
}

$plugins = @($registry.plugins | Where-Object { $_.pluginId -ne $pluginId })
$plugins += $entry
$registry.plugins = $plugins

$json = $registry | ConvertTo-Json -Depth 10
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($psRegistryPath, $json, $utf8NoBom)
Write-Step "Registered plugin in PS.json."

Write-Host ""
Write-Host "Next:"
Write-Host "  1. Close Photoshop completely."
Write-Host "  2. Reopen Photoshop."
Write-Host "  3. Check Plugins -> Rizum PT Bridge."
Write-Host ""
Write-Host "If it still does not appear, check whether your Photoshop version is at least $hostMinVersion."
