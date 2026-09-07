@echo off
REM ============================================================
REM VCG Deinterlacer - Clean Build Script
REM ============================================================
REM Deletes all Nuitka build artifacts and global cache so that
REM the next run of build_vcg_deinterlacer.bat is fully clean.
REM ============================================================

echo.
echo ============================================================
echo  VCG Deinterlacer - Clean Build
echo ============================================================
echo.
echo Deleting dist\ folder entirely...

REM ── Wipe entire dist folder (catches any version name) ────────
rmdir /s /q "dist" 2>nul

echo Deleting _deps\ folder entirely...

REM ── Wipe _deps folder (downloaded VapourSynth/FFmpeg bundle) ──
rmdir /s /q "_deps" 2>nul

echo Deleting __pycache__\ folder...

REM ── Wipe Python bytecode cache ────────────────────────────────
rmdir /s /q "__pycache__" 2>nul

echo Deleting Nuitka global cache in AppData...

REM ── Nuitka global compilation cache ──────────────────────────
rmdir /s /q "%LOCALAPPDATA%\Nuitka" 2>nul
if exist "%LOCALAPPDATA%\Nuitka" (
    echo   WARNING: %%LOCALAPPDATA%%\Nuitka could not be fully removed.
) else (
    echo   OK: %%LOCALAPPDATA%%\Nuitka removed ^(or was already absent^).
)

rmdir /s /q "%APPDATA%\Nuitka" 2>nul
if exist "%APPDATA%\Nuitka" (
    echo   WARNING: %%APPDATA%%\Nuitka could not be fully removed.
) else (
    echo   OK: %%APPDATA%%\Nuitka removed ^(or was already absent^).
)

echo Deleting VCG Deinterlacer onefile extraction caches...

REM ── Nuitka onefile extraction dirs (one per released version) ─
REM    The whole folder is safe to delete — it only holds per-version
REM    extraction caches and the EXE re-extracts on next run.  Deleting
REM    the parent covers every past and future version (1.0.9 … 1.7.2+)
REM    without needing a new line here each release.
rmdir /s /q "%LOCALAPPDATA%\VCG_Deinterlacer" 2>nul
if exist "%LOCALAPPDATA%\VCG_Deinterlacer" (
    echo   WARNING: %%LOCALAPPDATA%%\VCG_Deinterlacer could not be fully removed.
) else (
    echo   OK: %%LOCALAPPDATA%%\VCG_Deinterlacer removed ^(or was already absent^).
)

echo.
echo ============================================================
echo  Clean complete. Run build_vcg_deinterlacer.bat to rebuild.
echo ============================================================
echo.
pause
