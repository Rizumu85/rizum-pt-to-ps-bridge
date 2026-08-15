$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$nativeDir = Join-Path $repoRoot "sp_plugin\rizum_sp_to_ps\native"
$source = Join-Path $nativeDir "edge_smoothing.rs"
$output = Join-Path $nativeDir "rizum_edge_smoothing.dll"
$lld = Join-Path $env:USERPROFILE ".rustup\toolchains\stable-x86_64-pc-windows-msvc\lib\rustlib\x86_64-pc-windows-msvc\bin\rust-lld.exe"

if (-not (Test-Path -LiteralPath $lld)) {
    throw "rust-lld.exe was not found in the stable MSVC Rust toolchain."
}

rustc $source `
    --crate-type cdylib `
    -C opt-level=3 `
    -C panic=abort `
    -C linker=$lld `
    -o $output

if ($LASTEXITCODE -ne 0) {
    throw "rustc failed with exit code $LASTEXITCODE."
}

$generatedArtifacts = @(
    "$output.lib",
    [System.IO.Path]::ChangeExtension($output, ".pdb")
)
foreach ($artifact in $generatedArtifacts) {
    if ([System.IO.File]::Exists($artifact)) {
        [System.IO.File]::Delete($artifact)
    }
}

Write-Host "Built $output"
