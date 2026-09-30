$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$nativeDir = Join-Path $repoRoot "sp_plugin\rizum_sp_to_ps\native"
$lld = Join-Path $env:USERPROFILE ".rustup\toolchains\stable-x86_64-pc-windows-msvc\lib\rustlib\x86_64-pc-windows-msvc\bin\rust-lld.exe"

if (-not (Test-Path -LiteralPath $lld)) {
    throw "rust-lld.exe was not found in the stable MSVC Rust toolchain."
}

# Each library's file name carries its algorithm version, so a changed
# algorithm ships under a new name instead of silently replacing the old one.
$libraries = @(
    @{ Source = "edge_smoothing.rs"; Output = "rizum_edge_smoothing_v5.dll"; Edition = "2015" },
    @{ Source = "painter_look.rs"; Output = "rizum_painter_look_v1.dll"; Edition = "2021" }
)

foreach ($library in $libraries) {
    $source = Join-Path $nativeDir $library.Source
    $output = Join-Path $nativeDir $library.Output

    rustc $source `
        --edition $library.Edition `
        --crate-type cdylib `
        -C opt-level=3 `
        -C panic=abort `
        -C linker=$lld `
        -o $output

    if ($LASTEXITCODE -ne 0) {
        throw "rustc failed with exit code $LASTEXITCODE for $($library.Source)."
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
}
