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

echo Deleting Nuitka global cache in AppData...

REM ── Nuitka global compilation cache ──────────────────────────
rmdir /s /q "%LOCALAPPDATA%\Nuitka" 2>nul
rmdir /s /q "%APPDATA%\Nuitka"      2>nul

echo Deleting VCG Deinterlacer onefile extraction caches...

REM ── Nuitka onefile extraction dirs (one per released version) ─
REM    These are safe to delete — the EXE re-extracts on next run.
rmdir /s /q "%LOCALAPPDATA%\VCG_Deinterlacer\1.0.9.0"  2>nul
rmdir /s /q "%LOCALAPPDATA%\VCG_Deinterlacer\1.0.10.0" 2>nul
rmdir /s /q "%LOCALAPPDATA%\VCG_Deinterlacer\1.0.11.0" 2>nul
rmdir /s /q "%LOCALAPPDATA%\VCG_Deinterlacer\1.0.12.0" 2>nul
rmdir /s /q "%LOCALAPPDATA%\VCG_Deinterlacer\1.0.13.0" 2>nul
rmdir /s /q "%LOCALAPPDATA%\VCG_Deinterlacer\1.0.14.0" 2>nul
rmdir /s /q "%LOCALAPPDATA%\VCG_Deinterlacer\1.0.15.0" 2>nul
rmdir /s /q "%LOCALAPPDATA%\VCG_Deinterlacer\1.0.16.0" 2>nul
rmdir /s /q "%LOCALAPPDATA%\VCG_Deinterlacer\1.1.0.0"  2>nul

echo.
echo ============================================================
echo  Clean complete. Run build_vcg_deinterlacer.bat to rebuild.
echo ============================================================
echo.
pause
