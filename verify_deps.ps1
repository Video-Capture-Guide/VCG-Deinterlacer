# ============================================================
# verify_deps.ps1
# Run this NEXT TO VCG_Deinterlacer.exe on your test machine
# to see if the _deps folder is set up correctly
# ============================================================

$ExeDir = $PSScriptRoot
$DepsDir = Join-Path $ExeDir "_deps"

Write-Host "=== VCG Deinterlacer Deps Verification ==="
Write-Host "EXE folder: $ExeDir"
Write-Host ""

# Check _deps folder
if (Test-Path $DepsDir) {
    Write-Host "[OK] _deps folder exists"
} else {
    Write-Host "[MISSING] _deps folder does NOT exist at: $DepsDir"
    Write-Host "  --> Run VCG_Deinterlacer.exe to trigger the first-run setup"
    exit 1
}

# Check version file
$VerFile = Join-Path $DepsDir "vcg_deps.version"
if (Test-Path $VerFile) {
    $Content = (Get-Content $VerFile -Raw).Trim()
    if ($Content -eq "1") {
        Write-Host "[OK] vcg_deps.version = '$Content' (correct)"
    } else {
        Write-Host "[WRONG] vcg_deps.version contains: '$Content'"
        Write-Host "  --> Expected: '1'"
        Write-Host "  --> This is the bug! The old ZIP had a batch echo bug."
        Write-Host "  --> Delete _deps folder, re-upload the new ZIP, and run EXE again."
    }
} else {
    Write-Host "[MISSING] vcg_deps.version not found in _deps\"
}

# Check key files
$Files = @(
    "_deps\ffmpeg\ffmpeg.exe",
    "_deps\ffmpeg\ffprobe.exe",
    "_deps\vs\vspipe.exe",
    "_deps\vs\python314.dll",
    "_deps\vs\python3.dll",
    "_deps\vs\VSScript.dll",
    "_deps\vs\VapourSynth.dll",
    "_deps\vs\site-packages\vapoursynth.pyd",
    "_deps\vs\site-packages\havsfunc.py",
    "_deps\vs\plugins\LSMASHSource.dll"
)

Write-Host ""
Write-Host "--- Key Files ---"
foreach ($rel in $Files) {
    $full = Join-Path $ExeDir $rel
    if (Test-Path $full) {
        $size = [math]::Round((Get-Item $full).Length / 1KB, 0)
        Write-Host "[OK] $rel ($size KB)"
    } else {
        Write-Host "[MISSING] $rel"
    }
}
Write-Host ""
Write-Host "Done."
