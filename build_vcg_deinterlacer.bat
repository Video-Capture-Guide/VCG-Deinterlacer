@echo off
REM ============================================================
REM VCG Deinterlacer - Nuitka Build Script
REM ============================================================
REM
REM This script compiles VCG Deinterlacer into a standalone
REM Windows executable using Nuitka.
REM
REM PREREQUISITES:
REM   1. Python 3.10+ installed and in PATH
REM   2. Required packages:  pip install -r requirements.txt
REM   3. Visual Studio Build Tools (https://visualstudio.microsoft.com/downloads/)
REM      OR MinGW64 (Nuitka will prompt to download it automatically)
REM
REM ============================================================

echo.
echo ============================================================
echo  VCG Deinterlacer 1.0.6 - Build Script
echo ============================================================
echo.

REM ── Check Python ─────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://www.python.org
    pause
    exit /b 1
)

REM ── Install / update dependencies ────────────────────────────
echo Installing required packages...
pip install --quiet --upgrade Pillow tkinterdnd2 nuitka ordered-set zstandard
if errorlevel 1 (
    echo ERROR: Failed to install required packages.
    pause
    exit /b 1
)

REM ── Move to script directory ──────────────────────────────────
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM ── Verify source file exists ─────────────────────────────────
set SOURCE=vcg_deinterlacer_v106.py
if not exist "%SOURCE%" (
    echo ERROR: %SOURCE% not found in %SCRIPT_DIR%
    pause
    exit /b 1
)

REM ── Locate tkdnd folder (required for drag-and-drop) ──────────
set TKDND_OPTION=
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python314\Lib\site-packages\tkinterdnd2\tkdnd"
    "%LOCALAPPDATA%\Programs\Python\Python313\Lib\site-packages\tkinterdnd2\tkdnd"
    "%LOCALAPPDATA%\Programs\Python\Python312\Lib\site-packages\tkinterdnd2\tkdnd"
    "%LOCALAPPDATA%\Programs\Python\Python311\Lib\site-packages\tkinterdnd2\tkdnd"
    "%LOCALAPPDATA%\Programs\Python\Python310\Lib\site-packages\tkinterdnd2\tkdnd"
    "C:\Python314\Lib\site-packages\tkinterdnd2\tkdnd"
    "C:\Python313\Lib\site-packages\tkinterdnd2\tkdnd"
    "C:\Python312\Lib\site-packages\tkinterdnd2\tkdnd"
    "C:\Python311\Lib\site-packages\tkinterdnd2\tkdnd"
    "C:\Python310\Lib\site-packages\tkinterdnd2\tkdnd"
) do (
    if exist "%%~P" (
        set TKDND_PATH=%%~P
        goto :found_tkdnd
    )
)

REM Try pip show as fallback
for /f "tokens=2 delims=: " %%L in ('pip show tkinterdnd2 2^>nul ^| findstr "Location"') do (
    if exist "%%L\tkinterdnd2\tkdnd" (
        set TKDND_PATH=%%L\tkinterdnd2\tkdnd
        goto :found_tkdnd
    )
)

echo WARNING: tkdnd folder not found. Drag-and-drop will not work in the EXE.
echo          You can still use the Browse button to open files.
set TKDND_OPTION=
goto :check_icon

:found_tkdnd
echo Found tkdnd at: %TKDND_PATH%
set TKDND_OPTION=--include-data-dir="%TKDND_PATH%"=tkdnd

REM ── Icon ──────────────────────────────────────────────────────
:check_icon
set ICON_OPTION=
if exist "vcg_icon.ico" (
    echo Found icon: vcg_icon.ico
    set ICON_OPTION=--windows-icon-from-ico=vcg_icon.ico
) else (
    echo NOTE: vcg_icon.ico not found. Using default Windows icon.
)

REM ── Include logo for welcome page ─────────────────────────────
set LOGO_OPTION=
if exist "logo.png" (
    echo Found logo: logo.png
    set LOGO_OPTION=--include-data-files=logo.png=logo.png
)

REM ── Build ─────────────────────────────────────────────────────
echo.
echo Starting Nuitka compilation...
echo This typically takes 10-30 minutes on first build.
echo Subsequent builds are faster due to caching.
echo.

REM ── Only include the PIL modules VCG actually uses ───────────
REM    Using --include-package=PIL pulls in every obscure image
REM    format plugin (BLP, BUFR, etc.) and causes Zig/LLVM to run
REM    out of memory during LTO.  List only what we need instead.
set PIL_MODULES=^
    --include-module=PIL ^
    --include-module=PIL.Image ^
    --include-module=PIL.ImageTk ^
    --include-module=PIL.ImageDraw ^
    --include-module=PIL.ImageFont ^
    --include-module=PIL.ImageFilter ^
    --include-module=PIL.ImageOps ^
    --include-module=PIL.PngImagePlugin ^
    --include-module=PIL.JpegImagePlugin ^
    --include-module=PIL.BmpImagePlugin ^
    --include-module=PIL.GifImagePlugin ^
    --include-module=PIL.IcoImagePlugin ^
    --nofollow-import-to=PIL.BlpImagePlugin ^
    --nofollow-import-to=PIL.BufrStubImagePlugin ^
    --nofollow-import-to=PIL.DdsImagePlugin ^
    --nofollow-import-to=PIL.EpsImagePlugin ^
    --nofollow-import-to=PIL.FitsImagePlugin ^
    --nofollow-import-to=PIL.FliImagePlugin ^
    --nofollow-import-to=PIL.FpxImagePlugin ^
    --nofollow-import-to=PIL.GribStubImagePlugin ^
    --nofollow-import-to=PIL.Hdf5StubImagePlugin ^
    --nofollow-import-to=PIL.ImImagePlugin ^
    --nofollow-import-to=PIL.ImtImagePlugin ^
    --nofollow-import-to=PIL.IptcImagePlugin ^
    --nofollow-import-to=PIL.McIdasImagePlugin ^
    --nofollow-import-to=PIL.MicImagePlugin ^
    --nofollow-import-to=PIL.MpegImagePlugin ^
    --nofollow-import-to=PIL.MpoImagePlugin ^
    --nofollow-import-to=PIL.MspImagePlugin ^
    --nofollow-import-to=PIL.PalmImagePlugin ^
    --nofollow-import-to=PIL.PcdImagePlugin ^
    --nofollow-import-to=PIL.PcxImagePlugin ^
    --nofollow-import-to=PIL.PdfImagePlugin ^
    --nofollow-import-to=PIL.PixarImagePlugin ^
    --nofollow-import-to=PIL.PpmImagePlugin ^
    --nofollow-import-to=PIL.PsdImagePlugin ^
    --nofollow-import-to=PIL.QoiImagePlugin ^
    --nofollow-import-to=PIL.SgiImagePlugin ^
    --nofollow-import-to=PIL.SpiderImagePlugin ^
    --nofollow-import-to=PIL.SunImagePlugin ^
    --nofollow-import-to=PIL.TgaImagePlugin ^
    --nofollow-import-to=PIL.TiffImagePlugin ^
    --nofollow-import-to=PIL.WebPImagePlugin ^
    --nofollow-import-to=PIL.WmfImagePlugin ^
    --nofollow-import-to=PIL.XbmImagePlugin ^
    --nofollow-import-to=PIL.XpmImagePlugin ^
    --nofollow-import-to=PIL.XVThumbImagePlugin

python -m nuitka ^
    --standalone ^
    --onefile ^
    --onefile-tempdir-spec="{CACHE_DIR}/VCG_Deinterlacer/{VERSION}" ^
    --assume-yes-for-downloads ^
    --lto=no ^
    --jobs=2 ^
    --windows-console-mode=force ^
    --enable-plugin=tk-inter ^
    --include-package=tkinterdnd2 ^
    --nofollow-import-to=urllib ^
    %PIL_MODULES% ^
    %TKDND_OPTION% ^
    %ICON_OPTION% ^
    %LOGO_OPTION% ^
    --company-name="VideoCaptureGuide" ^
    --product-name="VCG Deinterlacer" ^
    --file-version="1.0.6.0" ^
    --product-version="1.0.6.0" ^
    --file-description="VCG Deinterlacer - Analog Video Restoration Tool" ^
    --copyright="Copyright (c) 2026 VideoCaptureGuide" ^
    --output-filename=VCG_Deinterlacer_1.0.6.exe ^
    --output-dir=dist ^
    %SOURCE%

REM ── Check by file existence, not errorlevel ──────────────────
REM    Nuitka may exit non-zero on warnings even when the EXE was
REM    created successfully (e.g. missing Windows Runtime DLLs).
REM    Checking the output file is the reliable way to tell.
if not exist "dist\VCG_Deinterlacer_1.0.6.exe" (
    echo.
    echo ============================================================
    echo  BUILD FAILED  ^(dist\VCG_Deinterlacer_1.0.6.exe not produced^)
    echo ============================================================
    echo.
    echo Common causes:
    echo   - LLVM out of memory: close other apps and try again,
    echo     or change --jobs=2 to --jobs=1 in this script
    echo   - Visual Studio Build Tools not installed
    echo     https://visualstudio.microsoft.com/downloads/
    echo   - Antivirus blocking compilation ^(add folder to exclusions^)
    echo   - Missing tkdnd folder ^(drag-and-drop will not work^)
    echo   - Run as Administrator if you get permission errors
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  BUILD SUCCESSFUL
echo ============================================================
echo.
echo Output:  dist\VCG_Deinterlacer_1.0.6.exe
echo.
echo NOTE: If you see a "Windows Runtime DLLs" warning above, that
echo       is harmless -- the EXE will work on any machine that has
echo       the Visual C++ Redistributable installed (Windows 10/11
echo       ships with it by default).
echo.
echo Next steps:
echo   1. Test the EXE:  dist\VCG_Deinterlacer_1.0.6.exe
echo   2. Package as ZIP (1.0.4 portable -- no installer needed):
echo      - Create a folder:  VCG_Deinterlacer_1.0.6\
echo      - Copy into it:     dist\VCG_Deinterlacer_1.0.6.exe
echo      -                   logo.png
echo      -                   README.txt  (rename from README.md)
echo      -                   LICENSE.txt
echo      - Zip the folder:   VCG_Deinterlacer_1.0.6.zip
echo   3. Distribute the ZIP -- users just extract and double-click the EXE.
echo      Dependencies (FFmpeg + VapourSynth) download automatically on first run.
echo.
pause
