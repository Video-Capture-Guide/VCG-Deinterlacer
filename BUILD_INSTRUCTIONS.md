# VCG Deinterlacer — 1.6.0 Build & Release Instructions

## Overview

VCG Deinterlacer ships as a **portable ZIP distribution** — no installer, no UAC prompt, no
Windows SmartScreen installer dialog. Users download a ZIP, extract it anywhere, and double-click
the EXE. On first run the app downloads and installs FFmpeg and VapourSynth automatically via an
in-app setup wizard.

## Overview of Files

| File | Purpose |
|------|---------|
| `vcg_deinterlacer_v122.py` | Main application source code (VERSION 1.6.0) |
| `build_vcg_deinterlacer.bat` | Compiles the EXE using Nuitka |
| `clean_build.bat` | Wipes dist\, _deps\, and all Nuitka caches for a fully clean rebuild |
| `VCG_Deinterlacer_Setup.iss` | Legacy Inno Setup script (Beta-01 only — not used) |
| `requirements.txt` | Python dependencies |
| `RELEASE_NOTES.md` | Per-version change log |
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
vcg_deinterlacer_v122.py       ← main source (1.6.0)
build_vcg_deinterlacer.bat     ← build script
clean_build.bat                ← cache cleaner
requirements.txt
LICENSE.txt
README.md
vcg_icon.ico                   ← your icon file
logo.png                       ← your logo file
```

---

## Step 1 — Clean Previous Build (Important!)

If you have built a previous version in this folder, **delete the old
Nuitka cache first** or you may get a segfault or instant-close on launch.

Run `clean_build.bat` — it wipes:

| What | Why |
|------|-----|
| `dist\` | Removes all prior build output and intermediate `.build`/`.dist` folders |
| `_deps\` | Forces a fresh dependency download on next launch |
| `__pycache__\` | Removes stale Python bytecode that can cause import errors in the compiled EXE |
| `%LOCALAPPDATA%\Nuitka` | **Global Nuitka compilation cache** — stale entries here can produce a corrupt onefile bundle that opens and immediately closes |
| `%APPDATA%\Nuitka` | Secondary Nuitka cache location — also wiped |
| `%LOCALAPPDATA%\VCG_Deinterlacer\<version>` | Onefile extraction cache for each released version — stale extractions are re-created clean on next run |

After deleting the Nuitka caches the script now prints either:

```
  OK: %LOCALAPPDATA%\Nuitka removed (or was already absent).
  OK: %APPDATA%\Nuitka removed (or was already absent).
```

or a `WARNING:` line if a cache directory could not be removed (e.g.
locked by another process). If you see the warning, close any open
command prompts that may have run Nuitka previously and re-run
`clean_build.bat` before proceeding.

---

## Step 2 — Run the Build Script

Double-click `build_vcg_deinterlacer.bat` or run it from a command prompt.

What it does:
- Installs/updates required Python packages
- Locates the tkdnd drag-and-drop folder
- Compiles `vcg_deinterlacer_v122.py` into `dist\VCG_Deinterlacer_1.6.0.exe`
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
& ".\dist\VCG_Deinterlacer_1.6.0.exe"
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

## Step 4 — Package as ZIP (portable distribution format)

No installer is needed. Package the app as a ZIP:

1. Create a folder called `VCG_Deinterlacer_1.6.0\`
2. Copy into it:
   - `dist\VCG_Deinterlacer_1.6.0.exe`
   - `logo.png`
   - `README.md` (rename to `README.txt` inside the ZIP)
   - `LICENSE.txt`
3. Zip the folder to produce: `VCG_Deinterlacer_1.6.0.zip`

That's the release artifact. No Inno Setup step required.

### PowerShell one-liner to create the ZIP:

```powershell
$out = "VCG_Deinterlacer_1.6.0"
New-Item -ItemType Directory -Force $out | Out-Null
Copy-Item dist\VCG_Deinterlacer_1.6.0.exe $out\
Copy-Item logo.png                  $out\
Copy-Item README.md                 $out\README.txt
Copy-Item LICENSE.txt               $out\
Compress-Archive -Path $out -DestinationPath "$out.zip" -Force
Remove-Item -Recurse -Force $out
Write-Host "Created: $out.zip"
```

---

## Step 5 — Test the ZIP

1. Extract `VCG_Deinterlacer_1.6.0.zip` to a **new folder on a clean user profile**
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

Upload `VCG_Deinterlacer_1.6.0.zip` to your distribution channels:
- **GitHub Releases** — create a release tag `v1.6.0`, attach the ZIP
- **VideoHelp** — https://www.videohelp.com/software
- **YouTube description** — link in your video tutorials

---

## How Portable Mode Works

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
- Bump `DEPS_VERSION` and `DEPS_ZIP_URL` in `vcg_deinterlacer_v122.py`
- Rebuild the EXE

---

## Known Limitations

| Issue | Status |
|-------|--------|
| Brief console window flash on launch | Known — Nuitka limitation |
| First run requires internet connection (~136 MB download) | By design |
| No auto-update mechanism | Planned for future release |

---

## Development Notes — 1.5.0 Session (2026-06-10): Obstacles & Solutions

Lessons learned while building 1.5.0 (RGB Parade, BM3D, Dehalo, Watermark, comparison
rework). Each of these cost real debugging time; read this before touching the FFmpeg
filter strings or the generated `.vpy` code.

### 1. drawtext renders NOTHING without an explicit fontfile

The bundled FFmpeg (gyan.dev 8.1 essentials) is built with fontconfig, but on Windows
fontconfig cannot load its default config ("Cannot load default config file") and finds no
font. `drawtext` then **silently draws nothing — exit code is still 0**. The old
comparison-video labels never actually rendered because of this.

**Fix:** every `drawtext` must pass an explicit system font. Use the shared helper
`_drawtext_fontfile_arg()` (Segoe UI → Arial → Calibri → Tahoma), which also escapes the
drive-colon for the filter parser (`C\:/Windows/Fonts/segoeui.ttf`). If no font is found,
treat drawtext as unavailable and fall back (the comparison falls back to colored bars).

### 2. drawtext positioning: `w`/`W` is the INPUT width, not the text width

In the `overlay` filter, `W/H` = main video and `w/h` = overlaid element — so `W-w-20`
means "right-aligned". In `drawtext`, however, **both `w` and `W` mean the input frame
width**; the text box dimensions are `tw`/`th`. `x=W-w-20` evaluates to `-20` and pushes
the label off-screen. Use `x=w-tw-20:y=h-th-20` for bottom-right.

### 3. A literal `%` in drawtext silently kills the whole label

drawtext's text expander treats `%` as the start of a `%{...}` sequence. A bare `%`
(e.g. `300%` or user watermark text like `100% Family`) logs "Stray % near ..." and the
**entire label is dropped** — again with exit code 0. Two escape layers are needed: the
filter option parser strips one backslash, the text expander uses the second. So the
filter string must contain `\\%` (in Python source: `r'\\%'` or `'\\\\%'`).
`%%` does NOT work — that is printf escaping, not drawtext escaping.

### 4. FFmpeg `waveform` shows the input's native planes — not RGB

`waveform=display=parade:components=7` on YUV input produces a **Y/U/V parade**, not an
RGB parade. Convert first: `format=gbrp` — and because GBR planar stores planes in
G,B,R order, add `shuffleplanes=2:0:1` so the columns read **R,G,B left to right**.
Also: parade output is `3 × input_width` wide (≈2160 px); `scale=640:-1` squashes it to
~76 px tall. Use `scale=640:256` to keep the scope's native 256-level height.

### 5. `concat` rejects segments whose SAR differs

The 300%-zoom segment of the comparison (`crop=iw/3:ih/3,scale=640:480`) ends up with a
different sample aspect ratio than the normal segment, and `concat` fails with
"Input link parameters do not match". **Fix:** `setsar=1` after each `hstack` so both
segments are explicitly square-pixel before concat. Also use explicit `split=2` when
feeding the same input into both segments.

### 6. The bundled havsfunc REMOVED FineDehalo / DeHalo_alpha

The havsfunc in the deps bundle is a modern release where `FineDehalo`, `DeHalo_alpha`,
`HQDeringmod`, etc. are **stubs that raise `vs.Error` ("outdated, use vs-dehalo")** — and
vs-dehalo is not in the bundle. Calling `haf.FineDehalo` crashes every encode.

**Fix:** the generated `.vpy` now contains a self-contained FineDehalo port built only
from components that ARE bundled: `core.std`/`core.resize` ops, `core.rgvs.Repair`
(RemoveGrainVS.dll), and the havsfunc mask utilities that still exist (`AvsPrewitt`,
`mt_expand_multi`, `mt_inpand_multi`). Check what the bundled havsfunc actually exports
before calling anything from it — the docstring at the top of `_deps\vs\site-packages\havsfunc.py`
lists the surviving functions.

### 7. Testing generated .vpy scripts with system Python 3.14

`vspipe.exe` from the bundle fails with "Failed to initialize VSScript" under Python 3.14
(bundled VapourSynth R73 supports 3.8–3.12 only — this is why the app has its retry
chain). For development testing, run the script Python-direct with pip-installed
vapoursynth, registering DLL directories first:

```python
for d in (VS_DEPS_DIR, plugins64_dir, pip_vapoursynth_dir):
    os.add_dll_directory(d)
sys.path.append(site_packages_dir)
import vapoursynth as vs
exec(open(script_path).read())
node = vs.get_output(0).clip
node = node[0:3]          # render a few frames only
node.output(open(out_y4m, 'wb'), y4m=True)
```

### 8. Heuristic analyzers need negative AND positive controls

The first halo detector scored *everything* 40–60% "haloed" — busy texture (straw,
foliage) reads as edge overshoot. It took three refinements to make it honest:
require a **flat far plateau** (busy zones don't vote), require **vertical coherence**
(halos track their edge across rows; texture is random), and require the **two-sided
sharpening signature** (bright-side overshoot AND dark-side undershoot together).
Calibrate against controls: the same clip artificially sharpened
(`unsharp=lx=7:ly=7:la=1.8`) must score clearly higher than the original.
Reference scores: clean MPEG-2 ≈ 8%, VHS ≈ 13%, consumer DV ≈ 17%, sharpened control ≈ 21%.

### 9. Inserting a wizard page touches more places than `step_methods`

Adding a step (Dehalo, Watermark) requires updating ALL of: `self.steps`, `self.crumbs`
(breadcrumb groups), `step_methods[]` in `_show_step()`, the hard-coded
`if step_index == N` that renames the Next button to "Finalize →", `finalize_step` in
`_ask_basic_or_advanced()`, the skipped-page defaults in `go_basic()`, the two Advanced
dialog description strings, and `_diag_keys` for the diagnostic log. Grep for
`step_index ==`, `finalize_step`, and `current_step ==` after any insertion.

### 10. Offscreen UI smoke testing works well

The whole wizard can be regression-tested without showing a window:
instantiate `RestorationWizard()`, call `.withdraw()`, then `_show_step(n)` +
`update_idletasks()` for every step, and drive page widgets directly (set the tk
variables, call the `_show_*_results()` methods with fake data dicts).
Analysis threads that outlive the destroyed window print
`RuntimeError: main thread is not in main loop` tracebacks — these are harmless test
artifacts (in the real app the mainloop is running).

---

## Development Notes — 1.6.0 Session (2026-06-29): Obstacles & Solutions

Lessons learned while building 1.6.0 (16-bit pipeline, fmtconv dithering, colorspace
tagging). Read this before touching the VapourSynth script generator or the scope code.

### 1. BM3D sigma is in 8-bit units regardless of clip bit depth — you must scale

`core.bm3d.BM3D(clip, sigma=3)` on a 16-bit clip gives the **same visual result as
sigma=0.012 on an 8-bit clip** — almost no denoising. The sigma parameter is in the
same integer units as an 8-bit pixel value. For a 16-bit clip, multiply by 256:
moderate sigma 3 → 768, heavy sigma 6 → 1536.

### 2. Chroma Expr neutral point shifts with bit depth

8-bit YUV chroma neutral is 128. 16-bit YUV chroma neutral is 32768. Every `core.std.Expr`
that does `x 128 - …` must become `x 32768 - …` after the pipeline lifts to 16-bit.
The same applies to luma legal levels: 16→4096 (black), 235→60160 (white).

### 3. fmtconv dmode=3 is error diffusion — verify against mvsfunc, not the README

The fmtconv documentation uses different dmode integer values across versions. The
installed version's dmode was verified by reading
`_deps\vs\site-packages\mvsfunc\mvsfunc.py` line 230, which maps
`'error_diffusion'` → `3` for fmtconv. Do not assume the value; re-verify if the deps
bundle is ever updated.

### 4. ProRes container carries 10-bit natively — lift all the way from 16-bit

After `fmtc.bitdepth(bits=10, dmode=3)` the clip is `YUV422P10`. The FFmpeg command
already specifies `-pix_fmt yuv422p10le`, so no extra conversion step is needed. The
fallback (`core.resize.Spline36(format=vs.YUV422P10)`) does a truncated conversion with
no dither — this is intentional (prefer a working encode over a crash if fmtconv fails).

### 5. FFmpeg `-colorspace` must be set BEFORE `-i` to tag the input

When tagging a source for scope generation (so FFmpeg uses the correct matrix for
YUV→GBR conversion inside the waveform filter), the flags must appear on the input side:

```
ffmpeg -ss T -colorspace bt470bg -color_primaries bt470bg -color_trc bt470bg \
       -i file.vob -vframes 1 -vf "format=gbrp,…" out.png
```

Placing them after `-i` tags the output container only and has no effect on the filter
graph's conversion matrix.

### 6. VS _Matrix constants differ from FFmpeg string names

VapourSynth `_Matrix` frame property integer constants:
- 1 = BT.709
- 5 = BT.470BG (PAL BT.601)
- 6 = SMPTE 170M (NTSC BT.601)

FFmpeg string names for the same standards:
- `bt709` = BT.709
- `bt470bg` = PAL BT.601
- `smpte170m` = NTSC BT.601

The PAL/NTSC distinction within BT.601 is real: PAL sources should use `bt470bg` /
`_Matrix=5`, NTSC sources `smpte170m` / `_Matrix=6`. The `_resolve_cs_tag()` helper
handles this using the `video_format` config key.

---

## Version History

| Version | Date | Notes |
|---------|------|-------|
| 1.6.0 | 2026-06-29 | 16-bit pipeline; fmtconv error-diffusion output dithering (auto, ProRes 10-bit); colorspace/matrix tagging (BT.601/BT.709 auto-select); correct scope colors; Source Color Matrix dropdown |
| 1.5.0 | 2026-06-10 | Dehalo page + halo analysis; Watermark page + film grain; BM3D denoising; RGB Parade; quantified scores; sampling notes; comparison rework |
| 1.4.1 | 2026-06-07 | .MOD file support; 16:9 widescreen PAR fix; crop page recommendation |
| 1.4.0 | 2026-05-23 | Telecine override fix; auto-scroll; shorter `_VCGD_NN` output suffix |
| 1.3.0 | 2026-05-18 | First 1.x public build |
| Beta-02b | 2026-04-05 | Fix RGB source (Lagarith/HuffYUV RGB); EXE now caches to AppData instead of Temp |
| Beta-02 | 2026-03-28 | Portable ZIP distribution; first-run setup built into app; no installer |
| Beta-01 | 2026-03-23 | Auto-installs FFmpeg + VapourSynth; Inno Setup installer; deploys to %LOCALAPPDATA% |
| Beta 0.4 | 2026-03-17 | First working installer build |
| Beta 0.2 | 2026-03-09 | Initial release |

---

## Troubleshooting

**EXE opens a black screen for ~3 seconds then closes with no error message**

This is a crash at Nuitka onefile startup — the EXE extracted itself to
`%LOCALAPPDATA%\VCG_Deinterlacer\<version>\` but something in the extracted
bundle is corrupt or stale. Reported by a user on 1.5.0.

Root cause: the Nuitka global compilation caches (`%LOCALAPPDATA%\Nuitka` and
`%APPDATA%\Nuitka`) can hold stale object files or precompiled modules from an
earlier version. When those are reused in a new build they can produce an EXE that
passes the file-existence check but crashes immediately at runtime, with the console
window appearing and disappearing too fast to read the error.

**Fix:** run `clean_build.bat` before rebuilding. As of 1.6.0 the script wipes both
Nuitka cache locations and prints an explicit `OK:` or `WARNING:` confirmation for
each. Verify both show `OK:` before starting the build. The script also removes
`__pycache__\` (stale bytecode) and the per-version onefile extraction cache under
`%LOCALAPPDATA%\VCG_Deinterlacer\`.

If the clean succeeded but the symptom persists, the issue may be antivirus quarantining
a file during EXE extraction. Add `%LOCALAPPDATA%\VCG_Deinterlacer\` to your AV
exclusions and re-test.

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
