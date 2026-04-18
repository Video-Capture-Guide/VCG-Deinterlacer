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
echo Deleting Nuitka build folders in dist\...

REM ── Local build output folders ────────────────────────────────
rmdir /s /q "dist\vcg_deinterlacer_v104.build"      2>nul
rmdir /s /q "dist\vcg_deinterlacer_v104.dist"       2>nul
rmdir /s /q "dist\vcg_deinterlacer_v104.onefile-build" 2>nul
del /f /q   "dist\VCG_Deinterlacer_1.0.4.exe"      2>nul

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
