# upload_deps_to_github.ps1
# Re-uploads vcg-deps-v1.zip to the GitHub release
# Run from PowerShell inside your VCG_Deinterlacer folder

$REPO  = "Video-Capture-Guide/vcg-deinterlacer-deps"
$TAG   = "v1"
$ASSET = "vcg-deps-v1.zip"

$ZipPath = Join-Path $PSScriptRoot $ASSET
if (-not (Test-Path $ZipPath)) {
    Write-Error "Cannot find $ASSET in $PSScriptRoot"
    exit 1
}

$sizeMB = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
Write-Host "ZIP to upload : $ZipPath"
Write-Host "Size          : $sizeMB MB"
Write-Host ""

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "GitHub CLI (gh) not found. Install from: https://cli.github.com/"
    exit 1
}

Write-Host "Checking GitHub auth..."
gh auth status
if ($LASTEXITCODE -ne 0) {
    Write-Host "Not logged in. Run: gh auth login"
    exit 1
}

Write-Host ""
Write-Host "Deleting old asset from release $TAG ..."
gh release delete-asset $TAG $ASSET --repo $REPO --yes 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  Old asset deleted."
} else {
    Write-Host "  No existing asset found - continuing."
}

Write-Host ""
Write-Host "Uploading $ASSET to release $TAG ..."
gh release upload $TAG $ZipPath --repo $REPO --clobber

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "SUCCESS! $ASSET uploaded to:"
    Write-Host "  https://github.com/$REPO/releases/tag/$TAG"
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "  1. On your TEST machine, delete the _deps folder next to the EXE"
    Write-Host "  2. Run VCG_Deinterlacer.exe"
    Write-Host "  3. Setup window should download, extract, and launch the wizard"
} else {
    Write-Host ""
    Write-Host "UPLOAD FAILED. Check the error above."
}
