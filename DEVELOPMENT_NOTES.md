# VCG Deinterlacer — Development Notes & Known Issues

This document is a briefing file for future Claude sessions working on this
codebase. It records every real problem encountered during development, the
root cause, and the fix that worked. Read this before making any changes.

---

## Implemented in v1.1.0 (2026-04-30)

**HD source routing — AVCHD / HDV wizard path**

Added `classify_source(filepath)` (ffprobe-based) that returns `source_class`
('sd'/'avchd'/'hdv'/'unknown'), dimensions, fps, codec, and `par_needed`.
Called in `_on_files_changed`; result stored in `config_data['source_classification']`.

Step 2 dispatches through `_page_source_dispatch` → `_page_source_details_hd`
(AVCHD/HDV) or existing `_page_source_details` (SD).

`_page_source_details_hd` has four sections: auto-detected source info card,
NTSC/PAL, field order (TFF pre-selected), telecine detection.

`generate_vpy_script` changes: HD sources skip crop and PAR correction;
HDV (1440×1080) adds `core.resize.Spline36(clip,1920,1080)` after QTGMC.

File browser and DnD handlers extended with `.mts .m2ts .m2t .ts`.

**Three HD regression fixes (same session)**

- *idet auto-trigger*: removed `self.after(400, self._run_field_order_detection)`
  from the HD page; badge now shows "✓ TFF (AVCHD/HDV standard)" immediately.
  idet misreads H.264 AVCHD as progressive due to frame-based encoding.
- *Crop page shown for HD*: `_next_step` step-2 now calls
  `_ask_basic_or_advanced()` directly for AVCHD/HDV, skipping the SD crop page.
- *SD resolutions on upscale page*: `_page_upscale` returns early for HD with
  a "Not applicable" card; SD resolution list is never rendered.

**Noise index metric on Noise Analysis page**

Replaced the raw `Avg diff / Variance` technical line with a human-readable
"Noise index: X.X%" derived from TOUT (temporal outlier fraction × 100).
TOUT is the most noise-specific metric because it counts pixels that flicker
independently of smooth scene motion. Thresholds: <2% clean, 2–6% light,
6–12% moderate, >12% heavy.

**Upscale page HD text**

Changed the 1080i HD card text to: "Your source is already 1080i HD. This
software is programmed to upscale to a maximum of 1920×1080."

---

## Pending Changes for Next Release

These are confirmed, scoped changes to implement in the next version bump:

**1. Fix duplicate FFmpeg output in diagnostic log**

When retry 3A (or 3B) succeeds, the FFmpeg progress log appears twice: once
under `[python-direct-3a-result stderr]` and again under `[pipe stderr]`.
Root cause: `_run_piped()` combines producer+consumer stderr into `result.stderr`,
and the diag logger captures it at both the per-retry checkpoint and the final
success point. Fix: at the final `diag.captured("pipe", ...)` call, log only
`result.producer_stderr` (python side) rather than the combined stderr, since
the consumer (FFmpeg) stderr was already captured in the retry section.

**2. Change output filename suffix to `_VCGD_YYYYMMDD`**

Currently output files are named `INPUT_VCG-Deinterlacer_01.mov` (with a
sequential counter). Change to `INPUT_VCGD_YYYYMMDD.mov` where `YYYYMMDD`
is today's date (e.g. `NTSC_SD_VCGD_20260427.mov`). If a file with that name
already exists, append `_02`, `_03`, etc. The `.vpy` script file should use
the same naming.

The suffix is built at the point where `output_path` and `script_path` are
determined (currently around the counter loop that increments `_VCG-Deinterlacer_01`).
Replace with:
```python
import datetime as _dt
_date_str = _dt.date.today().strftime('%Y%m%d')
_base_suffix = f"_VCGD_{_date_str}"
counter = 1
while True:
    suffix = _base_suffix if counter == 1 else f"{_base_suffix}_{counter:02d}"
    output_path = input_path.parent / (input_path.stem + suffix + output_ext)
    script_path = input_path.parent / (input_path.stem + suffix + '.vpy')
    if not output_path.exists() and not script_path.exists():
        break
    counter += 1
```

**3. Fix stale deps download size label in First Run Setup**

Line 8070 in the First Run Setup window shows `~60 MB` but the actual
vcg-deps-v10.zip is ~136 MB. Update the label text to match:

```python
# Before:
tk.Label(self, text="Downloading tools — this only happens once (~60 MB).", ...)
# After:
tk.Label(self, text="Downloading tools — this only happens once (~136 MB).", ...)
```

Also audit any other in-app or README references (README already correct at ~136 MB).

**4. Add Blackmagic Intensity D1 NTSC capture method + fix 720×486 height detection**

Blackmagic Intensity captures at 720×486 (D1 full-raster NTSC) and stores files
with incorrect square-pixel (PAR=1.000) metadata. The current capture method
options (SD / DV) don't handle this format correctly.

**Why 720×486 is different:**
D1 NTSC packs blanking into the active frame — 720×486 contains:
- 704 active columns + 8 blanking left + 8 blanking right
- 480 active lines + 3 blanking top + 3 blanking bottom
After removing blanking: 704×480 at PAR 10:11 = exactly 4:3.
With DV selected and no crop, PAR correction targets 640×480 from 720×480 —
wrong starting height for a 720×486 source.

**What to add — capture method option:**
Add "Blackmagic D1" as a third capture method option alongside SD and DV
in the Source step. When selected:
- Auto-set default crop to Left=8, Right=8, Top=3, Bottom=3
- Use actual detected height (486) for output size display and SAR calculation
- PAR correction path: 704×480 → resize to 640×480 (same as SD cropped path,
  which is already correct — no new PAR logic needed)
- Auto-detect: if FFprobe reports height=486, default capture method to
  "Blackmagic D1" and show a note explaining why

**Bug to fix at the same time — app normalizes source height to 480:**
When source is 720×486, the "Output size" display uses 480 as base height
instead of 486. With manual crop top=3/bottom=3:
- App shows: 704×474 (wrong — 480−3−3=474)
- Correct:   704×480 (right — 486−3−3=480)
The VapourSynth crop is applied to real frames so encoded output is correct,
but the display is misleading. Fix: read actual source height from FFprobe
and use it for output size display, SAR calculation, and crop validation.



---

## Codebase Quick Reference

| File | Purpose |
|------|---------|
| `vcg_deinterlacer_v117.py` | Main application — all logic lives here (see naming convention below) |
| `build_vcg_deinterlacer.bat` | Nuitka compile script |
| `clean_build.bat` | Wipes Nuitka artifacts before a fresh compile |
| `BUILD_INSTRUCTIONS.md` | Step-by-step build and release guide |

**Branch for development:** `main` (single branch — no feature branches needed for solo project)
**Git push method:** PAT must be embedded in URL directly —
`git push "https://Video-Capture-Guide:<PAT>@github.com/Video-Capture-Guide/VCG-Deinterlacer.git" main`
(The local proxy returns 403; do not use the default remote.)

---

## Source File & Release Naming Convention

**Source file:** Each time changes are made, rename the `.py` file by incrementing the number:
```
vcg_deinterlacer_v105.py  ← current
vcg_deinterlacer_v106.py  ← next change
vcg_deinterlacer_v107.py  ← change after that
```
Delete the old `.py` file from the repo when renaming — only one `.py` file should exist at a time.

**GitHub Release tag:** Use a 4-part version number so users can clearly see when a new build
is available, even for small changes:
```
1.0.4.3  ← current release
1.0.5.0  ← next release (when py file becomes v105)
1.0.6.0  ← release after that
```
The fourth number (`.3`, `.4`, etc.) can be incremented for patch releases between full version bumps.

**Rule:** Every new `.py` file = a new EXE build = a new GitHub Release with an incremented version number. This ensures users always know they have the latest version.

---

## Problem 1 — Nuitka Filename: Never Use Dots in Source Filename

**Symptom:** EXE compiles successfully but immediately segfaults on launch with:
```
Nuitka: A segmentation fault has occurred.
```

**Root cause:** The source file was named `vcg_deinterlacer_1.0.4.py`. Nuitka
derives the internal Python module name from the filename. Python module names
cannot contain dots (dots mean submodule separators). Nuitka silently produces
a broken binary when the base filename contains dots.

**Fix:** Rename the source file to use only valid Python identifier characters.
- WRONG: `vcg_deinterlacer_1.0.4.py`
- RIGHT: `vcg_deinterlacer_v104.py`

The VERSION string inside the file can still say `"1.0.4"` — only the
*filename* matters for Nuitka. Always use underscores or letters only in
Python source filenames that Nuitka will compile.

---

## Problem 2 — Nuitka Stale Cache: Must Clear AppData Too

**Symptom:** After renaming or changing the source file, the EXE still
segfaults even after deleting the `dist\` folder and rebuilding.

**Root cause:** Nuitka has a global compilation cache stored in AppData, not
just in the `dist\` folder. Deleting `dist\` is not enough — the stale cache
in AppData persists and contaminates the new build.

**Fix:** Run `clean_build.bat` (or manually run these) before every rebuild
after a rename or after a mysterious segfault:
```powershell
rmdir /s /q "dist\vcg_deinterlacer_v104.build"
rmdir /s /q "dist\vcg_deinterlacer_v104.dist"
rmdir /s /q "dist\vcg_deinterlacer_v104.onefile-build"
del /f /q   "dist\VCG_Deinterlacer_1.0.4.exe"
rmdir /s /q "%LOCALAPPDATA%\Nuitka"
rmdir /s /q "%APPDATA%\Nuitka"
```

The `clean_build.bat` file does all of this automatically.

**Diagnosis tip:** If `python vcg_deinterlacer_v104.py` runs fine but the
compiled EXE segfaults, the problem is always Nuitka build artifacts, never
the Python code itself.

---

## Problem 3 — Antivirus False Positive (Wacatac.C!ml)

**Symptom:** Windows Defender flags the compiled EXE as
`Trojan:Win32/Wacatac.C!ml` (Severity: Severe). The affected file path
looks like: `C:\Users\...\AppData\Local\Temp\onefile_15932_...\vcg_deinterlacer_v104.dll`

**Root cause:** Nuitka's `--onefile` mode extracts the EXE's contents into a
randomly-named subfolder under `%TEMP%` on every launch. This behavior — a
self-extracting EXE writing DLLs into a random temp folder — exactly matches
the pattern of malware that Microsoft's ML model is trained to detect. The
detection is a false positive; the `!ml` suffix on `Wacatac.C!ml` confirms
it is a machine-learning heuristic, not a known malware signature.

**Fix:** Add `--onefile-tempdir-spec="{CACHE_DIR}/VCG_Deinterlacer/{VERSION}"`
to the Nuitka command in the build bat. This makes the EXE extract to a
stable, named folder under `%LOCALAPPDATA%` (e.g.
`C:\Users\...\AppData\Local\VCG_Deinterlacer\1.0.4.0\`) instead of a random
temp folder. Defender does not flag named AppData directories.

This option is already present in `build_vcg_deinterlacer.bat`. Do not remove
it. If you bump the version number, the folder name changes automatically
via the `{VERSION}` token, so old extracted files are not reused.

---

## Problem 4 — havsfunc Import Error in Generated .vpy Scripts

**Symptom:** Processing fails with:
```
ModuleNotFoundError: No module named 'havsfunc'
```
Error appears in the VapourSynth output even though `havsfunc.py` is present
in `_deps\vs\site-packages\`.

**Root cause:** VapourSynth portable mode uses a `python3XX._pth` file to
configure sys.path. In some environments (notably when launched as a
subprocess from a Nuitka-compiled EXE), the `_pth` file does not reliably
add `site-packages` to `sys.path` before the generated `.vpy` script
imports havsfunc.

**Fix:** The `generate_vpy_script()` function explicitly injects a
`sys.path.insert(0, _vcg_sp)` at the top of every generated `.vpy` script,
before any `import havsfunc` call. This is already implemented. The relevant
code block is:
```python
_site_pkg_dir = os.path.join(VS_DEPS_DIR, 'site-packages').replace('\\', '/')
lines.append('import sys as _vcg_sys')
lines.append(f'_vcg_sp = "{_site_pkg_dir}"')
lines.append('if _vcg_sp not in _vcg_sys.path:')
lines.append('    _vcg_sys.path.insert(0, _vcg_sp)')
lines.append('')
lines.append('import havsfunc as haf')
```

**Do not remove this block.** Without it, havsfunc imports will randomly
fail in portable mode. The `_pth` mechanism alone is not reliable enough.

---

## Problem 5 — Drag and Drop Not Working After Fresh Install

**Symptom:** Drag and drop fails silently on a fresh machine even after the
first-run setup wizard completes and installs tkinterdnd2 successfully.
The Browse button works fine.

**Root cause:** At the top of `vcg_deinterlacer_v104.py`, the line
`BaseWindow = TkinterDnD.Tk` is evaluated at module load time. If tkinterdnd2
was not yet installed when the module first loaded (e.g., on a fresh machine
before the first-run setup wizard runs), `HAS_DND` is set to False and
`BaseWindow` falls back to plain `tk.Tk`. Installing tkinterdnd2 during
first-run setup does not help because the class has already been assigned.

**Fix:** A pip-install bootstrap runs at module startup (before the
`BaseWindow` line) that attempts to install tkinterdnd2 if the import fails:
```python
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except Exception:
    try:
        import subprocess as _sp
        _sp.run([sys.executable, '-m', 'pip', 'install', 'tkinterdnd2',
                 '--quiet', '--disable-pip-version-check'],
                capture_output=True, timeout=60)
        from tkinterdnd2 import DND_FILES, TkinterDnD
        HAS_DND = True
    except Exception:
        HAS_DND = False
```
This is already present. Do not move it — it must run before `BaseWindow`
is assigned.

---

## Problem 6 — nnedi3 LoadPlugin "Already Loaded" Error

**Symptom:** Processing fails with:
```
vapoursynth.Error: Plugin .../libnnedi3.dll already loaded
(com.deinterlace.nnedi3) from C:\Users\...\AppData\Roaming\VapourSynth\plugins64\libnnedi3.dll
```

**Root cause:** Some users have VapourSynth installed system-wide with
libnnedi3.dll in their AppData plugins64 folder. VapourSynth auto-loads all
DLLs in that folder at startup. When the generated `.vpy` then calls
`core.std.LoadPlugin(r"..._deps/vs/plugins64/libnnedi3.dll")`, the plugin
is already registered and VapourSynth throws an error.

**Fix:** Guard the LoadPlugin call with a `hasattr` check in the generated
`.vpy`:
```python
if not hasattr(core, "nnedi3"):
    core.std.LoadPlugin(r"..._deps/vs/plugins64/libnnedi3.dll")
```
This is already implemented in `generate_vpy_script()`. Apply the same pattern
to any other plugin that might be auto-loaded from the system.

---

## Problem 7 — Python 3.13+ Breaks VapourSynth Portable Mode

**Symptom:** Processing fails with "Failed to initialize VSScript" in the log.
Error dialog appears:
```
VapourSynth failed to start (VSScript init error).
Your system Python is 3.14.3.
The bundled VapourSynth R73 only supports Python 3.8–3.12.
```
Log output shows:
```
Portable env init failed – retrying with system environment
pip vapoursynth not found – attempting auto-install...
pip install vapoursynth failed.
pip vapoursynth not found – cannot use Python-direct fallback.
```

**Root cause:** The bundled `_deps\vs\vsscript.dll` (from the deps ZIP) was
compiled against Python 3.8–3.12. On a machine with Python 3.13+ as the
system Python, VSScript cannot find the Python runtime DLL and fails to
initialize. This is an R73 limitation; R74+ supports Python 3.12–3.14+.

**The fallback chain (already implemented):**
1. Portable vspipe with custom env — fails (vsscript.dll incompatibility)
2. Portable vspipe with system PATH — still fails (same DLL)
3. pip-installed vspipe (R74+, if available) — succeeds if R74 is installed
4A. **Retry 3A — bundled vapoursynth.pyd, Python-direct** — bypasses vspipe/vsscript entirely.
    Uses `sys.path.insert(0, _deps\vs\site-packages)` to load the bundled `vapoursynth.pyd`
    directly into a system Python subprocess. This is the working fix for Python 3.13+ machines.
4B. **Retry 3B — pip-installed vapoursynth, Python-direct** — fallback if bundled .pyd fails.
    Runs `pip install vapoursynth --quiet` automatically then re-attempts Python-direct.

**Retry 3A implementation detail:**
```python
_bundled_pyd = os.path.join(_site_pkg, 'vapoursynth.pyd')
if os.path.isfile(_bundled_pyd):
    _wrapper_3a = '\n'.join([
        'import sys, os',
        f'for _dll_dir in [{repr(VS_DEPS_DIR)}, {repr(_plugins64)}]:',
        '    if os.path.isdir(_dll_dir) and hasattr(os, "add_dll_directory"):',
        '        os.add_dll_directory(_dll_dir)',
        f'sys.path.insert(0, {repr(_site_pkg)})',
        'import vapoursynth as vs',
        # ... exec the .vpy script and write y4m output ...
    ])
    result = run_hidden([_sys_py, '-c', _wrapper_3a], timeout=None, env=_py_env_3a)
```
The `os.add_dll_directory()` calls are essential — they tell Windows where to find
`vapoursynth.dll` and the plugin DLLs before `import vapoursynth` runs.

**Critical implementation detail — sys.executable in compiled EXE:**
See Problem 11 below. System Python must be discovered via `shutil.which()`.
Try `'py'` (Windows Launcher) first — it handles multiple installed versions.

**Function `_try_upgrade_bundled_vsscript()`:** This function exists in the
code but was never called. Do not rely on it — Retry 3A is the working fix.

**Important:** If you update the deps package (`vcg-deps-vN.zip`), prefer
bundling a VapourSynth version that supports Python 3.13+. The current R73
bundle requires the Retry 3A fallback on Python 3.13+ machines.

---

## Problem 11 — sys.executable Is the EXE, Not Python, in Nuitka Builds

**Symptom:** The auto pip-install of vapoursynth runs but silently fails.
Log shows `pip install vapoursynth failed.` immediately, with no network
or permission error. Processing then shows the error dialog even though
vapoursynth *could* be installed.

**Root cause:** Inside a Nuitka compiled EXE, `sys.executable` is the EXE
file itself (e.g. `VCG_Deinterlacer_1.0.4.exe`), not `python.exe`. Any code
that calls `[sys.executable, '-m', 'pip', ...]` is actually running the EXE
with pip arguments, which exits non-zero immediately. Similarly,
`importlib.util.find_spec('vapoursynth')` runs in the EXE's Python context,
which cannot see system site-packages.

**Two places in the retry chain were affected:**
1. `pip install vapoursynth` — called with `sys.executable`
2. Python-direct command — `_py_cmd = [sys.executable, '-c', _wrapper]`

**Fix:** Use `shutil.which()` to find the real system Python, explicitly
skipping any path that matches `sys.executable`:
```python
import shutil as _sh
_sys_py = None
for _cand in ['py', 'python', 'python3']:  # 'py' = Windows Launcher, handles multi-version installs
    _p = _sh.which(_cand)
    if _p and os.path.normcase(_p) != os.path.normcase(sys.executable):
        _sys_py = _p
        break
if _sys_py is None:
    _sys_py = sys.executable  # running from source, sys.executable IS Python
```
After `pip install` succeeds, ask that same Python where vapoursynth was
installed rather than using `find_spec` (which also can't see system packages
from EXE context):
```python
_loc_r = run_hidden([_sys_py, '-c',
    'import vapoursynth, os; print(os.path.dirname(vapoursynth.__file__))'],
    timeout=15)
_pip_pkg_dir = _loc_r.stdout.strip()
```

**Rule:** Any subprocess that needs to run Python code from within a compiled
EXE must use a discovered system Python, never `sys.executable`. This applies
to pip, importlib checks, and Python-direct script execution.

---

## Problem 8 — Wizard Step Numbering Must Be Updated in 5 Places

**Symptom:** After adding a new Advanced Options step, the wizard skips steps,
shows wrong button labels, or jumps to the wrong page.

**Root cause:** The step count is hardcoded in multiple places. Missing any
one of them causes subtle bugs.

**All 5 places that MUST be updated when adding/removing a wizard step:**

1. **`self.steps` list** — the ordered list of step names
2. **`self.crumbs`** — the breadcrumb group index ranges (Advanced group
   must list all advanced step indices)
3. **`step_methods` list** inside `_show_step()` — maps index → page method
4. **"Finalize →" button condition** — `if step_index == N:` where N is the
   last Advanced step index
5. **`_ask_basic_or_advanced()`** — both `finalize_step = N` (the Finalize
   step index) AND `go_basic()` defaults (must `setdefault` every key that
   the new step would normally set, so "Process Now" users get safe defaults)

**Also update the Advanced button text** in `_ask_basic_or_advanced()` to
mention the new step so users know it's available.

**Current step layout (v1.1.0, 11 steps, indices 0–10):**
```
0  Welcome
1  Select File
2  Source Details
3  Crop Preset
4  Y/C Delay        ← Advanced ①
5  Noise            ← Advanced ②
6  Upscale (nnedi3) ← Advanced ③
7  Color Cast       ← Advanced ④
8  Levels           ← Advanced ⑤
9  Audio            ← Advanced ⑥
10 Finalize
```
- "Finalize →" button condition: `step_index == 9`
- `finalize_step = 10`
- `go_basic()` defaults: noise_level, upscale_enabled, color_correction,
  levels_adjustment, mix_audio

---

## Problem 9 — VapourSynth Plugin Loading: Don't Set PYTHONHOME/PYTHONPATH

**Symptom:** vspipe fails with "Failed to import encodings" or similar Python
bootstrap errors.

**Root cause:** VapourSynth portable mode uses a `._pth` file to configure
its embedded Python's module search path. Setting `PYTHONHOME` or `PYTHONPATH`
environment variables in the subprocess env dict overrides the `._pth`
mechanism and breaks Python's ability to find its own stdlib (encodings,
os, etc.).

**Rule:** The `get_vspipe_env()` function must NOT set `PYTHONHOME` or
`PYTHONPATH`. It should only:
- Put `VS_DEPS_DIR` first on `PATH` (so DLLs are found)
- Set `VSPluginPath` for plugin auto-loading
- REMOVE any inherited `PYTHONHOME` / `PYTHONPATH` (Nuitka sets these
  for its own runtime; they must be stripped before launching vspipe)

This is already correctly implemented. Do not add PYTHONHOME or PYTHONPATH
to `get_vspipe_env()`.

---

## Problem 10 — Levels Default Was "Clamp" Instead of "No Adjustment"

**Symptom:** Levels were being applied (clamping luma to 16–235) even when
the user selected "No adjustment" or used the "Process Now" basic path.

**Root cause:** Two code paths set the levels default: `_show_levels_results()`
and `_show_levels_options_fallback()`. Both were defaulting to `'clamp'`.
Additionally the help text incorrectly described "Clamp" as "Best for most
users."

**Fix:** Both functions now default to `levels_adjustment = 'none'`.
The help text correctly describes "No adjustment" as recommended for analog
captures (VHS/Hi8 often has super-whites and super-blacks that are real
picture content, not noise).

---

## Problem 11 — Nuitka PATH Pollution: Bundled Python ctypes Always Fails

**Symptom:** Smoke test `python.exe -c "import ctypes; print('ok')"` returns
non-zero even though `libffi-8.dll` is present in `_deps\vs\`.

**Root cause:** Nuitka onefile adds its extraction directory
(`%LOCALAPPDATA%\VCG_Deinterlacer\{VERSION}\` or the 8.3 form `VCG_DE~1\`)
to PATH. This extraction dir contains Nuitka's own Python proxy DLLs, which
conflict with the real `python3XX.dll` when the bundled `python.exe` loads
`_ctypes.pyd`.

**Fix:** Strip all PATH entries that start with the `%LOCALAPPDATA%\vcg_`
prefix before launching any subprocess that needs clean DLL resolution.
The `_filtered_path_for(base_path, prepend=())` helper does this. Always
pass `env=_bundled_env` (with filtered PATH) to the ctypes smoke test and
to any Python-direct retry.

**Implementation:** The `_filtered_path_for()` helper and `_bundled_env`
construction live inside the retry-3 block. They are reused for all
Python-direct retries (3A and 3B).

---

## Problem 12 — Missing libffi-8.dll: ctypes Import Fails on Python 3.13+

**Symptom:** Bundled `python.exe` smoke test fails with:
```
ImportError: DLL load failed while importing _ctypes: The specified module could not be found.
```

**Root cause:** Python 3.13+ externalised `libffi` as a separate DLL
(`libffi-8.dll`). The `build_deps_package.bat` script only copied `*.pyd`
files from the embeddable package, not `*.dll` files, so `libffi-8.dll`
was never included in the deps bundle.

**Fix:** Add this line to `build_deps_package.bat` after copying `*.pyd`:
```batch
for %%F in ("%PY_EMBED_DIR%\*.dll") do copy "%%F" "%VS_OUT%\" 2>nul
```
Bump `DEPS_VERSION` to trigger re-download on existing installs.

---

## Problem 13 — Wrong sys.executable Fallback: Nuitka Proxy Instead of Real Python

**Symptom:** Python-direct retry (3A/3B) fails immediately with a cryptic
import error, even though system Python is installed.

**Root cause:** When running as a Nuitka onefile EXE, `sys.executable` is the
Nuitka extraction proxy, not a real `python.exe`. Using it as the interpreter
for `subprocess.run([sys.executable, '-c', wrapper])` silently invokes the
proxy, which cannot import VapourSynth.

**Fix:** Priority 3 (last resort) must use the bundled `python.exe` explicitly:
```python
if _bundled_py and os.path.isfile(_bundled_py):
    _sys_py = _bundled_py
else:
    _sys_py = sys.executable  # running from source only
```
Never use `sys.executable` as a fallback when compiled with Nuitka.

---

## Problem 14 — Batch Processing: PID-based Temp Files Cause PermissionError

**Symptom:** In a large batch (e.g. 199 files), ~60% of files fail with:
```
PermissionError: [Errno 13] Permission denied: 'D:\Photos\2002\temp_48384.y4m'
```
The same file processed alone (new invocation) succeeds.

**Root cause:** All files in a batch run in the same process (same PID). The
temp file was named `temp_{os.getpid()}.y4m` in the *source folder*. When one
file's vspipe crashed and left the temp file locked, all subsequent files tried
to write to the *same path* and hit PermissionError. Also, some source folders
are on read-only drives.

**Fix:** Use `tempfile.mktemp(suffix='.y4m', prefix='vcg_')` — this generates
a unique path in `%TEMP%` (system temp folder) for every file, eliminating
both the shared-name collision and the source-folder write permission issue.
The same fix applies to the audio temp file.

---

## Problem 15 — Disk Space Exhaustion: Temp y4m File Is Enormous

**Symptom:** Processing fails after ~1h47m with:
```
OSError: [Errno 28] No space left on device
```
The user had 253 GB free on C:, but the job was a 31-minute 1440×1080
YUV422P8 capture with nnedi3 upscale (doubles fps via QTGMC).

**Root cause:** QTGMC doubles the frame rate (50i → 100fps). The intermediate
y4m file for a 31-minute clip at 1440×1080 YUV422P8 @ 100fps:
- 1440 × 1080 × 3 bytes (YUV422P8 ~= 3 bytes/pixel) × 100fps × 1860s ≈ 275 GB
- Written to `%TEMP%` (C: drive), which only had 253 GB free.

**Fix (v1.0.16):** Pipe vspipe stdout directly into FFmpeg stdin using
`subprocess.Popen`. The `_run_piped(prod_cmd, cons_cmd, ...)` helper handles
this. The intermediate y4m file is eliminated entirely — disk usage drops
to zero for the intermediate step.

Key implementation details:
- vspipe output flag: `temp_y4m` path → `-` (stdout)
- FFmpeg input flag: `'-i', temp_y4m` → `'-i', 'pipe:0'`
- Python-direct wrappers (3A/3B): `open(temp_y4m, 'wb')` → `sys.stdout.buffer`
- `_run_piped()` must set `prod.stdout.close()` *after* passing it to cons,
  so the producer receives SIGPIPE if the consumer exits early (FFmpeg error).
- `result.returncode` = producer_rc if producer failed, else consumer_rc.
  This preserves the "Failed to initialize VSScript" detection in stderr.

---

## Problem 16 — Git Tracking Ref After PAT Push

**Symptom:** After a successful PAT push, `git status` still shows
"Your branch is ahead of 'origin/main' by N commits."

**Root cause:** When pushing with an inlined PAT URL
(`git push "https://user:TOKEN@github.com/..."`) while the configured
remote URL is a proxy that returns 403, git does not update the tracking
ref for `origin/main`.

**Fix:**
```bash
git fetch origin <branch>
git branch --set-upstream-to=origin/<branch>
```
Or permanently fix the remote URL so normal pushes work:
```bash
git remote set-url origin "https://Video-Capture-Guide:<PAT>@github.com/Video-Capture-Guide/VCG-Deinterlacer.git"
```

---

## Build & Release Checklist

Before compiling a new release:
1. Copy current `.py` to `vcg_deinterlacer_vNNN.py` (increment number)
2. Update `VERSION`, `BUILD_DATE` at the top of the new `.py` file
3. Update `--file-version`, `--product-version`, `--output-filename` in `build_vcg_deinterlacer.bat`
4. Update `set SOURCE=vcg_deinterlacer_vNNN.py` in `build_vcg_deinterlacer.bat`
5. Add new version entry to `clean_build.bat`
6. Run `clean_build.bat` to wipe ALL Nuitka artifacts
7. Run `build_vcg_deinterlacer.bat`
8. Test the EXE on a machine WITHOUT the source Python installed
   (use the compiled EXE, not `python vcg_deinterlacer_v117.py`)
9. Test on Python 3.13+ if possible (to verify the pip fallback works)
10. Create GitHub Release, attach the ZIP
11. Upload ZIP contains: EXE + logo.png + README.txt + LICENSE.txt

---

## Deps Package Notes

The portable deps bundle is `vcg-deps-v10.zip` hosted on the
`vcg-deinterlacer-deps` GitHub repo (separate repo). It contains:
- FFmpeg (ffmpeg.exe, ffprobe.exe)
- VapourSynth R73 portable runtime (vspipe.exe, python314.dll, etc.)
- VS plugins: lsmas, mvtools, znedi3, fmtconv, nnedi3, etc.
- nnedi3_weights.bin
- havsfunc.py, vsutil, mvsfunc, adjust (in site-packages)

**To update the deps bundle:**
1. Build new ZIP using `build_deps_package.bat` (in the deps repo)
2. Upload to `vcg-deinterlacer-deps` GitHub Releases as a new tag (v7, v8, …)
3. Bump `DEPS_VERSION` and `DEPS_ZIP_URL` in the current `vcg_deinterlacer_vNNN.py`
4. Rebuild the EXE

**nnedi3 is already in the deps bundle** — `libnnedi3.dll` and
`nnedi3_weights.bin` are in `_deps\vs\plugins64\`. No deps update is needed
to use nnedi3 features.

---

## Git Workflow

All development goes directly to `main`. The local git remote points to a
proxy that returns 403 — always push using the PAT embedded in the URL:

```bash
git remote set-url origin https://<PAT>@github.com/Video-Capture-Guide/VCG-Deinterlacer.git
git push -u origin HEAD:main
```

If the push is rejected because the remote is ahead (e.g. user edited on GitHub):
```bash
git fetch origin main
git rebase origin/main
git push origin HEAD:main
```

**Getting a PAT:** GitHub → Settings → Developer settings → Personal access tokens → Fine-grained.
Scope needed: Contents (read + write) on the VCG-Deinterlacer repo.
