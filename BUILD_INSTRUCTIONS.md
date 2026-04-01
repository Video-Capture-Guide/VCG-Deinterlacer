# VCG Deinterlacer — Beta-02 Build & Release Instructions

## Overview

Beta-02 is a **portable ZIP distribution** — no installer, no UAC prompt, no Windows SmartScreen
installer dialog. Users download a ZIP, extract it anywhere, and double-click the EXE. On first
run the app downloads and installs FFmpeg and VapourSynth automatically via an in-app setup wizard.

## Overview of Files

| File | Purpose |
|------|---------|
| `vcg_deinterlacer_beta_0_5.py` | Main application source code (Beta-02) |
| `build_vcg_deinterlacer.bat` | Compiles the EXE using Nuitka |
| `VCG_Deinterlacer_Setup.iss` | Legacy Inno Setup script (Beta-01 only — not used for Beta-02) |
| `requirements.txt` | Python dependencies |
| `LICENSE.txt` | MIT license (included in ZIP) |
| `README.md` | User-facing documentation (included in ZIP as README.txt) |
| `vcg_icon.ico` | App icon — you must supply this |
| `logo.png` | Welcome screen logo — you must supply this |

---

## Prerequisites (one-time setup)

Before building for the first time, ensure the following are installed:

1. **Python 3.10+** — https://www.python.org
   - Must be in PATH (check "Add Python to PATH" during install)

2. **Nuitka** — installed automatically by the BAT via pip

3. **Visual Studio Build Tools** (or MinGW64)
   - https://visualstudio.microsoft.com/downloads/
   - Scroll down to "Tools for Visual Studio" → "Build Tools for Visual Studio"
   - Nuitka will prompt to download MinGW64 automatically if Build Tools not found

---

## Build Folder Layout

Your build folder must contain these files before running the BAT:

```
vcg_deinterlacer_beta_0_5.py   ← main source (Beta-02)
build_vcg_deinterlacer.bat     ← build script
requirements.txt
LICENSE.txt
README.md
vcg_icon.ico                   ← your icon file
logo.png                       ← your logo file
```

---

## Step 1 — Clean Previous Build (Important!)

If you have built a previous version in this folder, **delete the old
Nuitka cache first** or you may get a segfault on launch.

Open PowerShell in your build folder and run:

```powershell
Remove-Item -Recurse -Force dist\vcg_deinterlacer_beta_0_5.build -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force dist\vcg_deinterlacer_beta_0_5.dist -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force dist\vcg_deinterlacer_beta_0_5.onefile-build -ErrorAction SilentlyContinue
Remove-Item -Force dist\VCG_Deinterlacer.exe -ErrorAction SilentlyContinue
```

Or simply delete the entire `dist\` folder if it exists.

---

## Step 2 — Run the Build Script

Double-click `build_vcg_deinterlacer.bat` or run it from a command prompt.

What it does:
- Installs/updates required Python packages
- Locates the tkdnd drag-and-drop folder
- Compiles `vcg_deinterlacer_beta_0_5.py` into `dist\VCG_Deinterlacer.exe`
  using Nuitka with `--onefile`

**First build takes 10–30 minutes.** Subsequent builds use Nuitka's cache
and are much faster.

### If the build fails:
- **LLVM out of memory** — close other apps, change `--jobs=2` to `--jobs=1`
- **Visual Studio Build Tools not found** — install from the link above
- **Antivirus blocking** — add your build folder to antivirus exclusions
- **Permission errors** — run the BAT as Administrator

---

## Step 3 — Test the EXE

Before packaging, always test the EXE directly:

```powershell
& ".\dist\VCG_Deinterlacer.exe"
```

Confirm:
- App window opens (brief console flash is normal — Nuitka limitation)
- If FFmpeg/VapourSynth are **not** present: the First Run Setup window appears
  and downloads them automatically
- If they **are** present: the main Restoration Wizard opens directly
- Welcome screen displays with logo
- START button advances to Step 1
- No crash or error popup

---

## Step 4 — Package as ZIP (Beta-02 distribution format)

No installer is needed. Package the app as a ZIP:

1. Create a folder called `VCG_Deinterlacer_Beta-02\`
2. Copy into it:
   - `dist\VCG_Deinterlacer.exe`
   - `logo.png`
   - `README.md` (rename to `README.txt` inside the ZIP)
   - `LICENSE.txt`
3. Zip the folder to produce: `VCG_Deinterlacer_Beta-02.zip`

That's the release artifact. No Inno Setup step required.

### PowerShell one-liner to create the ZIP:

```powershell
$out = "VCG_Deinterlacer_Beta-02"
New-Item -ItemType Directory -Force $out | Out-Null
Copy-Item dist\VCG_Deinterlacer.exe $out\
Copy-Item logo.png                  $out\
Copy-Item README.md                 $out\README.txt
Copy-Item LICENSE.txt               $out\
Compress-Archive -Path $out -DestinationPath "$out.zip" -Force
Remove-Item -Recurse -Force $out
Write-Host "Created: $out.zip"
```

---

## Step 5 — Test the ZIP

1. Extract `VCG_Deinterlacer_Beta-02.zip` to a **new folder on a clean user profile**
   (or a machine without FFmpeg/VapourSynth installed)
2. Double-click `VCG_Deinterlacer.exe`
3. The First Run Setup window should appear and:
   - Download `vcg-deps-v6.zip` (~136 MB) from GitHub
   - Extract it, creating a `_deps\` folder next to the EXE containing:
     - `_deps\ffmpeg\` — ffmpeg.exe and ffprobe.exe
     - `_deps\vs\` — portable VapourSynth runtime (vspipe.exe, Python DLLs, site-packages)
     - `_deps\vs\plugins64\` — all VS plugins (lsmas, mvtools, znedi3, etc.)
   - Write `paths.json` next to the EXE
4. After setup completes the main wizard opens automatically
5. On subsequent launches the wizard opens directly (no setup window)

---

## Step 6 — Distribute

Upload `VCG_Deinterlacer_Beta-02.zip` to your distribution channels:
- **GitHub Releases** — create a release tag `Beta-02`, attach the ZIP
- **VideoHelp** — https://www.videohelp.com/software
- **YouTube description** — link in your video tutorials

---

## How Beta-02 Portable Mode Works

The app uses a fully **self-contained portable deps bundle** (`vcg-deps-v6.zip`) hosted on
GitHub Releases. No system-wide installation of FFmpeg or VapourSynth is required or performed.

**On first launch:**
1. App checks for `_deps\vcg_deps.version` containing the expected version number
2. If missing or wrong version, `FirstRunSetupWindow` opens
3. A single ZIP (`vcg-deps-v6.zip`, ~136 MB) is downloaded from the `vcg-deinterlacer-deps` GitHub repo
4. The ZIP is extracted — the root folder is renamed to `_deps\` next to the EXE
5. `paths.json` is written next to the EXE pointing to `_deps\ffmpeg\ffmpeg.exe`,
   `_deps\ffmpeg\ffprobe.exe`, and `_deps\vs\vspipe.exe`
6. Setup window closes and the main wizard opens

**`_deps\` folder layout after setup:**
```
_deps\
  ffmpeg\
    ffmpeg.exe
    ffprobe.exe
  vs\
    vspipe.exe
    python314.dll  (and other VS runtime DLLs)
    python314.zip  (VS stdlib)
    portable.vs    (marker file that enables portable mode)
    site-packages\ (havsfunc, mvsfunc, vsutil, adjust, vapoursynth bindings)
    plugins64\     (lsmas, mvtools, znedi3, fmtconv, etc. + nnedi3_weights.bin)
  vcg_deps.version  (contains "6")
```

**On subsequent launches:**
- `_deps\vcg_deps.version` contains `6` → deps check passes
- `FirstRunSetupWindow` is skipped entirely
- `paths.json` is read to locate ffmpeg/ffprobe/vspipe

**VapourSynth portable mode:**
- `portable.vs` marker file tells VapourSynth to run fully self-contained
- All plugins are explicitly loaded in generated `.vpy` scripts via `core.std.LoadPlugin()`
  (bypasses VapourSynth autoloading, which is unreliable in portable mode)
- No registry entries, no system PATH changes, no files written outside `_deps\`

**Updating the deps bundle:**
- Build a new ZIP using `build_deps_package.bat`
- Upload to `vcg-deinterlacer-deps` GitHub Releases as `vN`
- Bump `DEPS_VERSION` and `DEPS_ZIP_URL` in `vcg_deinterlacer_beta_0_5.py`
- Rebuild the EXE

---

## Known Beta-02 Limitations

| Issue | Status |
|-------|--------|
| Brief console window flash on launch | Known — Nuitka limitation |
| First run requires internet connection (~136 MB download) | By design |
| No auto-update mechanism | Planned for future release |

---

## Version History

| Version | Date | Notes |
|---------|------|-------|
| Beta-02 | 2026-03-28 | Portable ZIP distribution; first-run setup built into app; no installer |
| Beta-01 | 2026-03-23 | Auto-installs FFmpeg + VapourSynth; Inno Setup installer; deploys to %LOCALAPPDATA% |
| Beta 0.4 | 2026-03-17 | First working installer build |
| Beta 0.2 | 2026-03-09 | Initial release |

---

## Troubleshooting

**Segfault on launch**
Delete the `dist\` folder completely and rebuild from scratch (stale Nuitka cache).

**First Run Setup fails to download the deps ZIP**
- Check internet connection
- Try disabling VPN or firewall temporarily
- Download manually: https://github.com/Video-Capture-Guide/vcg-deinterlacer-deps/releases/latest
  - Download `vcg-deps-v6.zip` and extract it — rename the extracted folder to `_deps`
    and place it next to `VCG_Deinterlacer.exe`

**App opens but processing fails immediately**
- Delete the `_deps\` folder next to the EXE and re-launch to re-run setup
- Check that `paths.json` was written next to the EXE
- Verify FFmpeg: run `_deps\ffmpeg\ffmpeg.exe -version` from a command prompt
- Verify VapourSynth: run `_deps\vs\vspipe.exe --version` from a command prompt

**VapourSynth plugins not found / "Could not load plugin"**
- Check that `_deps\vs\plugins64\` exists and contains `.dll` files
- Delete `_deps\` and re-run setup to re-download a clean copy of the deps
