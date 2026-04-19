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

echo.
echo ============================================================
echo  Clean complete. Run build_vcg_deinterlacer.bat to rebuild.
echo ============================================================
echo.
pause
