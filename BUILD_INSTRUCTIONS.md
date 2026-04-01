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
  using Nuitka with `--onefile` and `--onefile-tempdir-spec={TEMP}\VCGDeinterlacer`

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
   (or a machine without FFmpeg/VapourSynth)
2. Double-click `VCG_Deinterlacer.exe`
3. The First Run Setup window should appear and:
   - Download FFmpeg (~75 MB) into `_deps\ffmpeg\`
   - Download and silently install VapourSynth R73
   - Install plugins via vsrepo
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

On first launch:
1. App checks for `_deps\ffmpeg\ffmpeg.exe` and the VapourSynth `vspipe.exe`
2. If either is missing, `FirstRunSetupWindow` opens
3. FFmpeg zip is downloaded → `ffmpeg.exe` and `ffprobe.exe` extracted to `_deps\ffmpeg\`
4. VapourSynth installer is downloaded and run silently (`/VERYSILENT /NORESTART`)
5. vsrepo installs havsfunc, lsmas, mvtools, fmtconv
6. `paths.json` is written next to the EXE
7. Setup window closes and the main wizard opens

On subsequent launches:
- `_deps\ffmpeg\ffmpeg.exe` is found → FFmpeg check passes
- `vspipe.exe` is found in the system VapourSynth location → VS check passes
- `FirstRunSetupWindow` is skipped entirely

---

## Known Beta-02 Limitations

| Issue | Status |
|-------|--------|
| Brief console window flash on launch | Known — Nuitka limitation |
| VapourSynth installs system-wide (not portable) | By design — VS requires system registration for plugins |
| First run requires internet connection | By design |
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

**First Run Setup fails to download FFmpeg**
- Check internet connection
- Try downloading manually: https://www.gyan.dev/ffmpeg/builds/
- Extract `ffmpeg.exe` and `ffprobe.exe` into a `_deps\ffmpeg\` folder next to the EXE

**First Run Setup fails to install VapourSynth**
- Download manually: https://github.com/vapoursynth/vapoursynth/releases
- Run `VapourSynth64-R73.exe` and install with defaults
- Then open a command prompt and run: `pip install vsrepo` then `vsrepo install havsfunc lsmas mvtools fmtconv`

**App opens but processing fails**
- Check that `paths.json` was written next to the EXE
- Verify FFmpeg: run `_deps\ffmpeg\ffmpeg.exe -version` from a command prompt
- Verify VapourSynth: run `vspipe --version` from a command prompt

**VapourSynth plugins not found**
Run from a command prompt:
```
pip install vsrepo
vsrepo install havsfunc lsmas mvtools fmtconv
```
