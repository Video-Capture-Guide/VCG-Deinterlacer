@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM  VCG Deinterlacer — Portable Deps Package Builder
REM ============================================================
REM
REM  Run this ONCE on your dev machine (where VapourSynth R73
REM  and Python are already installed) to produce:
REM
REM    vcg-deps-v1.zip   (~50-80 MB)
REM
REM  Then upload vcg-deps-v1.zip as a GitHub Release asset at:
REM    https://github.com/Video-Capture-Guide/vcg-deinterlacer-deps/releases
REM
REM  The app will download this single file on first launch
REM  and extract it to  _deps\  next to the EXE.
REM  No installer.  No UAC.  No admin rights.
REM ============================================================

echo.
echo ============================================================
echo  VCG Deinterlacer - Portable Deps Builder
echo ============================================================
echo.

REM ── Working directories ───────────────────────────────────────
set SCRIPT_DIR=%~dp0
set BUILD_DIR=%SCRIPT_DIR%deps_build
set OUT_DIR=%BUILD_DIR%\vcg-deps-v6
set VS_OUT=%OUT_DIR%\vs
set FF_OUT=%OUT_DIR%\ffmpeg

if exist "%BUILD_DIR%" (
    echo Cleaning previous build...
    rmdir /s /q "%BUILD_DIR%"
)
mkdir "%BUILD_DIR%"
mkdir "%OUT_DIR%"
mkdir "%VS_OUT%"
mkdir "%VS_OUT%\plugins64"
mkdir "%VS_OUT%\site-packages"
mkdir "%FF_OUT%"

REM ── Step 1: Locate VapourSynth R73 installation ──────────────
echo.
echo [1/7] Locating VapourSynth installation...

set VS_DIR=
for %%P in (
    "%LOCALAPPDATA%\Programs\VapourSynth"
    "%PROGRAMFILES%\VapourSynth"
    "%PROGRAMFILES(X86)%\VapourSynth"
) do (
    if exist "%%~P\core\vspipe.exe" (
        set VS_DIR=%%~P
        goto :found_vs
    )
)
echo ERROR: VapourSynth not found.  Install R73 from vapoursynth.com first.
pause
exit /b 1

:found_vs
echo   Found VS at: %VS_DIR%

REM ── Step 2: Locate Python (must match what VS uses) ──────────
echo.
echo [2/7] Locating Python installation...

set PYTHON_EXE=
set PYTHON_DLL=
set PYTHON_VER=

REM Try py launcher first
for /f "tokens=*" %%V in ('py --version 2^>^&1') do set PY_VER_STR=%%V
if "%PY_VER_STR%"=="" goto :try_python_direct

for /f "tokens=2 delims= " %%V in ('py --version 2^>^&1') do set PY_FULL=%%V
for /f "tokens=1,2 delims=." %%A in ("%PY_FULL%") do set PY_MAJOR=%%A& set PY_MINOR=%%B
set PYTHON_VER=%PY_MAJOR%%PY_MINOR%
for /f "tokens=*" %%P in ('py -c "import sys; print(sys.executable)"') do set PYTHON_EXE=%%P
goto :found_python

:try_python_direct
for /f "tokens=*" %%P in ('where python 2^>nul') do (
    set PYTHON_EXE=%%P
    goto :found_python_direct
)
echo ERROR: Python not found.  Install Python 3.8-3.12 first.
pause
exit /b 1

:found_python_direct
for /f "tokens=2 delims= " %%V in ('python --version 2^>^&1') do set PY_FULL=%%V
for /f "tokens=1,2 delims=." %%A in ("%PY_FULL%") do set PY_MAJOR=%%A& set PY_MINOR=%%B
set PYTHON_VER=%PY_MAJOR%%PY_MINOR%

:found_python
echo   Found Python %PY_FULL% at: %PYTHON_EXE%
echo   Python DLL version number: %PYTHON_VER%

REM Find python DLL — derive everything from the python.exe path (no nested-quote issues)
REM Standard layout: python.exe lives in the prefix dir; site-packages is Lib\site-packages
for %%E in ("%PYTHON_EXE%") do set PY_PREFIX=%%~dpE
REM Remove trailing backslash
if "%PY_PREFIX:~-1%"=="\" set PY_PREFIX=%PY_PREFIX:~0,-1%
set PY_SITE=%PY_PREFIX%\Lib\site-packages

set PYTHON_DLL=
if exist "%PY_PREFIX%\python%PYTHON_VER%.dll"              set PYTHON_DLL=%PY_PREFIX%\python%PYTHON_VER%.dll
if "%PYTHON_DLL%"=="" if exist "%SystemRoot%\System32\python%PYTHON_VER%.dll" set PYTHON_DLL=%SystemRoot%\System32\python%PYTHON_VER%.dll

if "%PYTHON_DLL%"=="" (
    echo ERROR: python%PYTHON_VER%.dll not found.
    echo   Looked in: %PY_PREFIX%\  and  %SystemRoot%\System32\
    pause
    exit /b 1
)
echo   Found python DLL: %PYTHON_DLL%
echo   Site-packages:    %PY_SITE%

REM ── Step 3: Copy VapourSynth core files ──────────────────────
echo.
echo [3/7] Copying VapourSynth core files...

copy "%VS_DIR%\core\vspipe.exe"         "%VS_OUT%\" || goto :err
copy "%VS_DIR%\core\VapourSynth.dll"    "%VS_OUT%\" 2>nul
copy "%VS_DIR%\core\VSScript.dll"       "%VS_OUT%\" 2>nul
copy "%VS_DIR%\core\vapoursynth.pyd"    "%VS_OUT%\" 2>nul

REM Some VS versions put vapoursynth.pyd in Python site-packages
if exist "%PY_SITE%\vapoursynth.pyd" (
    copy "%PY_SITE%\vapoursynth.pyd" "%VS_OUT%\site-packages\"
    echo   Copied vapoursynth.pyd from site-packages
)

REM Python 3.8+ no longer uses PATH when loading DLLs for extension modules (.pyd).
REM vapoursynth.pyd needs VapourSynth.dll and VSScript.dll in the SAME folder as the .pyd,
REM so copy the core VS DLLs into site-packages alongside vapoursynth.pyd.
copy "%VS_DIR%\core\VapourSynth.dll" "%VS_OUT%\site-packages\" 2>nul
copy "%VS_DIR%\core\VSScript.dll"    "%VS_OUT%\site-packages\" 2>nul
echo   Copied VapourSynth.dll + VSScript.dll to site-packages (DLL search fix^)

REM Copy python DLL and python3.dll next to vspipe.exe
REM python3.dll MUST come from the same Python installation as python314.dll — NOT System32
copy "%PYTHON_DLL%"  "%VS_OUT%\"
if exist "%PY_PREFIX%\python3.dll" (
    copy "%PY_PREFIX%\python3.dll" "%VS_OUT%\"
    echo   Copied python3.dll from Python installation
) else if exist "%SystemRoot%\System32\python3.dll" (
    copy "%SystemRoot%\System32\python3.dll" "%VS_OUT%\"
    echo   Copied python3.dll from System32 ^(fallback^)
) else (
    echo   WARNING: python3.dll not found - VSScript may fail to initialize
)

REM Copy VS-related DLLs from core folder
for %%F in ("%VS_DIR%\core\*.dll") do (
    copy "%%F" "%VS_OUT%\" 2>nul
)

REM Copy any other VS DLLs from system32 that VS needs
for %%F in (vcruntime140.dll vcruntime140_1.dll msvcp140.dll) do (
    if exist "%SystemRoot%\System32\%%F" copy "%SystemRoot%\System32\%%F" "%VS_OUT%\" 2>nul
)

echo   Done.

REM ── Step 4: Set up embeddable Python stdlib ───────────────────
echo.
echo [4/7] Setting up Python stdlib for embedded mode...

REM Download Python embeddable package (matching version)
set PY_EMBED_URL=https://www.python.org/ftp/python/%PY_FULL%/python-%PY_FULL%-embed-amd64.zip
set PY_EMBED_ZIP=%BUILD_DIR%\python_embed.zip

echo   Downloading Python %PY_FULL% embeddable from python.org...
powershell -NoProfile -NonInteractive -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%PY_EMBED_URL%' -OutFile '%PY_EMBED_ZIP%' -UseBasicParsing" 2>nul
if not exist "%PY_EMBED_ZIP%" (
    REM Try curl.exe
    curl.exe -L -o "%PY_EMBED_ZIP%" "%PY_EMBED_URL%" --silent --show-error
)
if not exist "%PY_EMBED_ZIP%" (
    echo ERROR: Could not download Python embeddable package.
    echo        Download manually from: %PY_EMBED_URL%
    echo        Save as: %PY_EMBED_ZIP%
    pause
    exit /b 1
)
echo   Downloaded. Extracting...

REM Extract embeddable Python to a temp subfolder
set PY_EMBED_DIR=%BUILD_DIR%\python_embed
mkdir "%PY_EMBED_DIR%"
powershell -NoProfile -NonInteractive -Command "Expand-Archive -Path '%PY_EMBED_ZIP%' -DestinationPath '%PY_EMBED_DIR%' -Force"

REM Copy python stdlib zip and pyd files to VS_OUT
echo   Copying Python stdlib...
copy "%PY_EMBED_DIR%\python%PYTHON_VER%.zip"  "%VS_OUT%\" 2>nul
copy "%PY_EMBED_DIR%\python3.dll"              "%VS_OUT%\" 2>nul
REM Copy extension pyd files needed by Python/VapourSynth scripts
for %%F in ("%PY_EMBED_DIR%\*.pyd") do copy "%%F" "%VS_OUT%\" 2>nul

REM Write the _pth file to enable site-packages in embeddable mode
echo python%PYTHON_VER%.zip>  "%VS_OUT%\python%PYTHON_VER%._pth"
echo .>>                       "%VS_OUT%\python%PYTHON_VER%._pth"
echo site-packages>>            "%VS_OUT%\python%PYTHON_VER%._pth"
echo import site>>              "%VS_OUT%\python%PYTHON_VER%._pth"
echo   Created python%PYTHON_VER%._pth

REM ── Step 5: Copy Python scripts and packages ──────────────────
echo.
echo [5/7] Copying Python packages (havsfunc, mvsfunc)...

set PY_SITE_DEST=%VS_OUT%\site-packages

REM ── Collect havsfunc / mvsfunc / adjust from all known locations ──────────
REM vsrepo installs scripts to %APPDATA%\Python\PythonXXX\site-packages OR
REM %APPDATA%\VapourSynth.  Check all locations in priority order.

REM Build the per-user Python site-packages path (%APPDATA%\Python\PythonXXX\site-packages)
set PY_APPDATA_SITE=%APPDATA%\Python\Python%PYTHON_VER%\site-packages

for %%F in (havsfunc.py adjust.py) do (
    REM 1. Per-user Python AppData site-packages (where vsrepo installs on Python 3.14+)
    if exist "%PY_APPDATA_SITE%\%%F"              copy "%PY_APPDATA_SITE%\%%F"              "%PY_SITE_DEST%\" 2>nul
    REM 2. Python site-packages (standard install)
    if exist "%PY_SITE%\%%F"                      copy "%PY_SITE%\%%F"                      "%PY_SITE_DEST%\" 2>nul
    REM 3. %APPDATA%\VapourSynth  (vsrepo legacy per-user install)
    if exist "%APPDATA%\VapourSynth\%%F"          copy "%APPDATA%\VapourSynth\%%F"          "%PY_SITE_DEST%\" 2>nul
    REM 4. VS install dir root / core
    if exist "%VS_DIR%\%%F"                        copy "%VS_DIR%\%%F"                        "%PY_SITE_DEST%\" 2>nul
    if exist "%VS_DIR%\core\%%F"                   copy "%VS_DIR%\core\%%F"                   "%PY_SITE_DEST%\" 2>nul
)

REM ── mvsfunc: copy as package directory if present, else flat .py ─────────
set FOUND_MVS=0
if exist "%PY_APPDATA_SITE%\mvsfunc\__init__.py" (
    xcopy /E /I /Y /Q "%PY_APPDATA_SITE%\mvsfunc" "%PY_SITE_DEST%\mvsfunc\" >nul
    echo   Copied mvsfunc\ package from AppData
    set FOUND_MVS=1
)
if "%FOUND_MVS%"=="0" if exist "%PY_SITE%\mvsfunc\__init__.py" (
    xcopy /E /I /Y /Q "%PY_SITE%\mvsfunc" "%PY_SITE_DEST%\mvsfunc\" >nul
    echo   Copied mvsfunc\ package from site-packages
    set FOUND_MVS=1
)
if "%FOUND_MVS%"=="0" if exist "%PY_APPDATA_SITE%\mvsfunc.py" (
    copy "%PY_APPDATA_SITE%\mvsfunc.py" "%PY_SITE_DEST%\" 2>nul
    set FOUND_MVS=1
)
if "%FOUND_MVS%"=="0" if exist "%PY_SITE%\mvsfunc.py" (
    copy "%PY_SITE%\mvsfunc.py" "%PY_SITE_DEST%\" 2>nul
    set FOUND_MVS=1
)
if "%FOUND_MVS%"=="0" if exist "%APPDATA%\VapourSynth\mvsfunc.py" (
    copy "%APPDATA%\VapourSynth\mvsfunc.py" "%PY_SITE_DEST%\" 2>nul
    set FOUND_MVS=1
)

REM ── If havsfunc still missing, download from GitHub (latest main) ─────────
if not exist "%PY_SITE_DEST%\havsfunc.py" (
    echo   havsfunc.py not found locally — downloading from GitHub...
    set HAV_URL=https://raw.githubusercontent.com/HomeOfVapourSynthEvolution/havsfunc/master/havsfunc.py
    powershell -NoProfile -NonInteractive -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '!HAV_URL!' -OutFile '%PY_SITE_DEST%\havsfunc.py' -UseBasicParsing" 2>nul
    if not exist "%PY_SITE_DEST%\havsfunc.py" (
        curl.exe -L -o "%PY_SITE_DEST%\havsfunc.py" "!HAV_URL!" --silent --show-error 2>nul
    )
)

REM ── If adjust still missing, download it ────────────────────────────────
if not exist "%PY_SITE_DEST%\adjust.py" (
    echo   adjust.py not found locally — downloading from GitHub...
    set ADJ_URL=https://raw.githubusercontent.com/dubhater/vapoursynth-adjust/master/adjust.py
    powershell -NoProfile -NonInteractive -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '!ADJ_URL!' -OutFile '%PY_SITE_DEST%\adjust.py' -UseBasicParsing" 2>nul
    if not exist "%PY_SITE_DEST%\adjust.py" (
        curl.exe -L -o "%PY_SITE_DEST%\adjust.py" "!ADJ_URL!" --silent --show-error 2>nul
    )
)

REM ── vsutil: required by havsfunc at module load time ────────────────────
REM vsutil is installed to system site-packages by pip install vsutil
set FOUND_VSUTIL=0
if exist "%APPDATA%\Python\Python%PYTHON_VER%\site-packages\vsutil\__init__.py" (
    xcopy /E /I /Y /Q "%APPDATA%\Python\Python%PYTHON_VER%\site-packages\vsutil" "%PY_SITE_DEST%\vsutil\" >nul
    echo   Copied vsutil\ from AppData Python site-packages
    set FOUND_VSUTIL=1
)
if "%FOUND_VSUTIL%"=="0" if exist "%PY_SITE%\vsutil\__init__.py" (
    xcopy /E /I /Y /Q "%PY_SITE%\vsutil" "%PY_SITE_DEST%\vsutil\" >nul
    echo   Copied vsutil\ from system site-packages
    set FOUND_VSUTIL=1
)
if "%FOUND_VSUTIL%"=="0" (
    echo   WARNING: vsutil not found.  Install with:  pip install vsutil
    echo   Then re-run this script.
    pause
    exit /b 1
)

REM ── Verify havsfunc (required) — must be real Python, not a 404 page ─────
set HAV_OK=0
if exist "%PY_SITE_DEST%\havsfunc.py" (
    for %%A in ("%PY_SITE_DEST%\havsfunc.py") do (
        if %%~zA GTR 10000 set HAV_OK=1
    )
)
if "%HAV_OK%"=="1" (
    echo   Copied havsfunc.py OK
) else (
    if exist "%PY_SITE_DEST%\havsfunc.py" del "%PY_SITE_DEST%\havsfunc.py"
    echo   ERROR: havsfunc.py could not be found ^(got 404 or too small^).
    echo   Please run:  vsrepo install havsfunc
    echo   Then re-run this script.
    pause
    exit /b 1
)
REM ── Check mvsfunc was found ──
if "%FOUND_MVS%"=="1" (
    echo   Copied mvsfunc OK
) else (
    echo   WARNING: mvsfunc not found locally. havsfunc may fail at runtime.
    REM Non-fatal — continue
)
REM ── Remove any stale placeholder below size threshold ────────────────────
if exist "%PY_SITE_DEST%\mvsfunc.py" (
    for %%A in ("%PY_SITE_DEST%\mvsfunc.py") do (
        if %%~zA GTR 1000 (
            echo   mvsfunc.py size OK
        ) else (
            echo   WARNING: mvsfunc.py looks too small — removing stale placeholder.
            del "%PY_SITE_DEST%\mvsfunc.py"
        )
    )
)
if exist "%PY_SITE_DEST%\adjust.py"   echo   Copied adjust.py OK

REM ── Step 6: Copy plugin DLLs ──────────────────────────────────
echo.
echo [6/7] Copying VapourSynth plugin DLLs...

set PLUGIN_DEST=%VS_OUT%\plugins64

REM Common plugin locations
set PLUGIN_SRC1=%APPDATA%\VapourSynth\plugins64
set PLUGIN_SRC2=%VS_DIR%\plugins64
set PLUGIN_SRC3=%PY_SITE%\vapoursynth

REM Required plugins
REM NOTE: lsmas is installed by vsrepo as LSMASHSource.dll (not lsmas.dll)
REM       libmvtools is installed as libmvtools.dll  (may also appear as mvtools.dll)

set PLUGIN_MISSING=0

REM ── lsmas / LSMASHSource ──────────────────────────────────────
set FOUND_LSMAS=0
for %%S in ("%PLUGIN_SRC1%" "%PLUGIN_SRC2%" "%PLUGIN_SRC3%") do (
    if !FOUND_LSMAS!==0 if exist "%%~S\LSMASHSource.dll" (
        copy "%%~S\LSMASHSource.dll" "%PLUGIN_DEST%\"
        echo   Copied LSMASHSource.dll  (lsmas^)
        set FOUND_LSMAS=1
    )
    if !FOUND_LSMAS!==0 if exist "%%~S\lsmas.dll" (
        copy "%%~S\lsmas.dll" "%PLUGIN_DEST%\"
        echo   Copied lsmas.dll
        set FOUND_LSMAS=1
    )
)
if !FOUND_LSMAS!==0 (
    echo   WARNING: LSMASHSource.dll ^(lsmas^) not found.
    set PLUGIN_MISSING=1
)

REM ── libmvtools ────────────────────────────────────────────────
set FOUND_MVT=0
for %%S in ("%PLUGIN_SRC1%" "%PLUGIN_SRC2%" "%PLUGIN_SRC3%") do (
    if !FOUND_MVT!==0 if exist "%%~S\libmvtools.dll" (
        copy "%%~S\libmvtools.dll" "%PLUGIN_DEST%\"
        echo   Copied libmvtools.dll
        set FOUND_MVT=1
    )
    if !FOUND_MVT!==0 if exist "%%~S\mvtools.dll" (
        copy "%%~S\mvtools.dll" "%PLUGIN_DEST%\"
        echo   Copied mvtools.dll
        set FOUND_MVT=1
    )
)
if !FOUND_MVT!==0 (
    echo   WARNING: libmvtools.dll not found.
    set PLUGIN_MISSING=1
)

REM ── fmtconv ──────────────────────────────────────────────────
set FOUND_FMT=0
for %%S in ("%PLUGIN_SRC1%" "%PLUGIN_SRC2%" "%PLUGIN_SRC3%") do (
    if !FOUND_FMT!==0 if exist "%%~S\fmtconv.dll" (
        copy "%%~S\fmtconv.dll" "%PLUGIN_DEST%\"
        echo   Copied fmtconv.dll
        set FOUND_FMT=1
    )
)
if !FOUND_FMT!==0 (
    echo   WARNING: fmtconv.dll not found.
    set PLUGIN_MISSING=1
)

REM Also copy any other plugins found (user may have extras)
if exist "%PLUGIN_SRC1%" for %%F in ("%PLUGIN_SRC1%\*.dll") do copy "%%F" "%PLUGIN_DEST%\" 2>nul
if exist "%PLUGIN_SRC2%" for %%F in ("%PLUGIN_SRC2%\*.dll") do copy "%%F" "%PLUGIN_DEST%\" 2>nul

REM ── nnedi3_weights.bin (required by znedi3/NNEDI3 for QTGMC interpolation) ──
REM This binary weights file MUST be present next to vsznedi3.dll / libnnedi3.dll.
REM Without it, QTGMC fails with "znedi3: error reading weights".
set FOUND_WEIGHTS=0
for %%S in ("%PLUGIN_SRC1%" "%PLUGIN_SRC2%" "%PLUGIN_SRC3%") do (
    if !FOUND_WEIGHTS!==0 if exist "%%~S\nnedi3_weights.bin" (
        copy "%%~S\nnedi3_weights.bin" "%PLUGIN_DEST%\"
        echo   Copied nnedi3_weights.bin
        set FOUND_WEIGHTS=1
    )
)
if !FOUND_WEIGHTS!==0 (
    echo   WARNING: nnedi3_weights.bin not found. QTGMC will fail at runtime.
    echo   Install with:  vsrepo install nnedi3
    set PLUGIN_MISSING=1
)

if "%PLUGIN_MISSING%"=="1" (
    echo.
    echo   Some plugins were not found. Make sure these are installed:
    echo     vsrepo install lsmas mvtools fmtconv
    echo   Then re-run this script.
    pause
    exit /b 1
)

REM Write a plugins.conf so VS auto-loads from our plugins dir
echo   Writing VS plugin path config...

REM ── Step 7: Download FFmpeg binaries ─────────────────────────
echo.
echo [7/7] Getting FFmpeg binaries...

REM Check if ffmpeg.exe is already in dist\ (from a previous build)
if exist "%SCRIPT_DIR%dist_ffmpeg\ffmpeg.exe" (
    echo   Using cached FFmpeg from dist_ffmpeg\
    copy "%SCRIPT_DIR%dist_ffmpeg\ffmpeg.exe"  "%FF_OUT%\"
    copy "%SCRIPT_DIR%dist_ffmpeg\ffprobe.exe" "%FF_OUT%\" 2>nul
    goto :ffmpeg_done
)

REM Download FFmpeg essentials ZIP
set FF_URL=https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
set FF_ZIP=%BUILD_DIR%\ffmpeg.zip
echo   Downloading FFmpeg (~75 MB) from gyan.dev...
powershell -NoProfile -NonInteractive -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%FF_URL%' -OutFile '%FF_ZIP%' -UseBasicParsing" 2>nul
if not exist "%FF_ZIP%" (
    curl.exe -L -o "%FF_ZIP%" "%FF_URL%" --silent --show-error
)
if not exist "%FF_ZIP%" (
    echo ERROR: Could not download FFmpeg.
    pause
    exit /b 1
)
echo   Extracting ffmpeg.exe and ffprobe.exe...
set FF_EXTRACT=%BUILD_DIR%\ffmpeg_extracted
mkdir "%FF_EXTRACT%"
powershell -NoProfile -NonInteractive -Command "Expand-Archive -Path '%FF_ZIP%' -DestinationPath '%FF_EXTRACT%' -Force"
for /r "%FF_EXTRACT%" %%F in (ffmpeg.exe)  do copy "%%F" "%FF_OUT%\"
for /r "%FF_EXTRACT%" %%F in (ffprobe.exe) do copy "%%F" "%FF_OUT%\"

:ffmpeg_done
if not exist "%FF_OUT%\ffmpeg.exe" (
    echo ERROR: ffmpeg.exe not found after extraction.
    pause
    exit /b 1
)
echo   FFmpeg ready.

REM ── Write version marker ──────────────────────────────────────
REM NOTE: must use (echo 1) — plain "echo 1>" is parsed as stdout redirect, not text
(echo 6) > "%OUT_DIR%\vcg_deps.version"

REM ── Portable marker for VapourSynth ─────────────────────────────
REM VSScript.dll checks for this file to enable portable mode.
REM Without it, VSScript tries to find Python via the Windows registry,
REM which fails on machines without a system-wide Python installation.
type nul > "%VS_OUT%\portable.vs"
echo   portable.vs marker created.

REM ── Create ZIP ────────────────────────────────────────────────
echo.
echo Creating vcg-deps-v6.zip...

set OUT_ZIP=%SCRIPT_DIR%vcg-deps-v6.zip
if exist "%OUT_ZIP%" del "%OUT_ZIP%"

powershell -NoProfile -NonInteractive -Command ^
    "Compress-Archive -Path '%OUT_DIR%' -DestinationPath '%OUT_ZIP%' -Force"

if not exist "%OUT_ZIP%" (
    echo ERROR: Failed to create ZIP.
    pause
    exit /b 1
)

for %%F in ("%OUT_ZIP%") do (
    set /a ZIP_MB=%%~zF / 1048576
)
echo Done! Created: vcg-deps-v6.zip  (!ZIP_MB! MB)

REM ── Cleanup ───────────────────────────────────────────────────
rmdir /s /q "%BUILD_DIR%"

echo.
echo ============================================================
echo  NEXT STEPS:
echo ============================================================
echo.
echo  1. Upload vcg-deps-v6.zip to GitHub as a release asset:
echo       https://github.com/Video-Capture-Guide/vcg-deinterlacer-deps/releases
echo       Tag: v6
echo       Asset filename: vcg-deps-v6.zip
echo.
echo  2. Copy the direct download URL and update DEPS_ZIP_URL
echo     in vcg_deinterlacer_beta_0_5.py:
echo       https://github.com/Video-Capture-Guide/vcg-deinterlacer-deps/releases/download/v6/vcg-deps-v6.zip
echo.
echo  3. Rebuild the app EXE with build_vcg_deinterlacer.bat
echo.
pause
exit /b 0

:err
echo ERROR: A required file was not found.
pause
exit /b 1
