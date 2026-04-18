# VCG Deinterlacer — Development Notes & Known Issues

This document is a briefing file for future Claude sessions working on this
codebase. It records every real problem encountered during development, the
root cause, and the fix that worked. Read this before making any changes.

---

## Codebase Quick Reference

| File | Purpose |
|------|---------|
| `vcg_deinterlacer_v104.py` | Main application — all logic lives here |
| `build_vcg_deinterlacer.bat` | Nuitka compile script |
| `clean_build.bat` | Wipes Nuitka artifacts before a fresh compile |
| `BUILD_INSTRUCTIONS.md` | Step-by-step build and release guide |

**Branch for development:** `claude/vcg-deinterlacer-update-8l66j`
**Git push method:** PAT must be embedded in URL directly —
`git push "https://Video-Capture-Guide:<PAT>@github.com/Video-Capture-Guide/vcg-deinterlacer.git" <branch>`
(The local proxy returns 403; do not use the default remote.)

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
4. Python-direct execution (bypasses vspipe/vsscript entirely) — succeeds
   if `vapoursynth` is importable via pip

**The auto-fix (already implemented):** Before attempting retry 4, the code
runs `pip install vapoursynth --quiet` automatically if vapoursynth is not
yet pip-installed. After a successful install, retry 4 (Python-direct)
can proceed without user intervention.

**Critical implementation detail — sys.executable in compiled EXE:**
See Problem 11 below. This is the reason the first attempt at auto-install
failed silently and required a second fix.

**Function `_try_upgrade_bundled_vsscript()`:** This function exists in the
code but was never called. Do not rely on it — the auto-install approach in
the retry chain is the working fix.

**Important:** If you update the deps package (`vcg-deps-vN.zip`), prefer
bundling a VapourSynth version that supports Python 3.13+. The current R73
bundle requires the pip fallback on Python 3.13+ machines.

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
for _cand in ['python', 'python3', 'py']:
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

**Current step layout (v1.0.4, 11 steps, indices 0–10):**
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

## Build & Release Checklist

Before compiling a new release:
1. Update `BUILD_DATE` at the top of `vcg_deinterlacer_v104.py`
2. Update `VERSION` if this is a version bump
3. Update `--file-version` and `--product-version` in `build_vcg_deinterlacer.bat`
4. Update `--output-filename` in `build_vcg_deinterlacer.bat`
5. Run `clean_build.bat` to wipe ALL Nuitka artifacts
6. Run `build_vcg_deinterlacer.bat`
7. Test the EXE on a machine WITHOUT the source Python installed
   (use the compiled EXE, not `python vcg_deinterlacer_v104.py`)
8. Test on Python 3.13+ if possible (to verify the pip fallback works)
9. Create GitHub Release, attach the ZIP
10. Upload ZIP contains: EXE + logo.png + README.txt + LICENSE.txt

---

## Deps Package Notes

The portable deps bundle is `vcg-deps-v6.zip` hosted on the
`vcg-deinterlacer-deps` GitHub repo (separate repo). It contains:
- FFmpeg (ffmpeg.exe, ffprobe.exe)
- VapourSynth R73 portable runtime (vspipe.exe, python314.dll, etc.)
- VS plugins: lsmas, mvtools, znedi3, fmtconv, nnedi3, etc.
- nnedi3_weights.bin
- havsfunc.py, vsutil, mvsfunc, adjust (in site-packages)

**To update the deps bundle:**
1. Build new ZIP using `build_deps_package.bat` (in the deps repo)
2. Upload to `vcg-deinterlacer-deps` GitHub Releases as a new tag (v7, v8, …)
3. Bump `DEPS_VERSION` and `DEPS_ZIP_URL` in `vcg_deinterlacer_v104.py`
4. Rebuild the EXE

**nnedi3 is already in the deps bundle** — `libnnedi3.dll` and
`nnedi3_weights.bin` are in `_deps\vs\plugins64\`. No deps update is needed
to use nnedi3 features.

---

## Git Workflow

The local git remote points to a proxy that occasionally returns 403.
Always push using the PAT embedded in the URL:
```bash
git push "https://Video-Capture-Guide:<PAT>@github.com/Video-Capture-Guide/vcg-deinterlacer.git" <branch>
```

After pushing, the local tracking ref will show "1 unpushed commit" until
you fetch to update it:
```bash
git fetch "https://Video-Capture-Guide:<PAT>@github.com/Video-Capture-Guide/vcg-deinterlacer.git" \
  <branch>:refs/remotes/origin/<branch>
```

Development happens on `claude/vcg-deinterlacer-update-8l66j`. After testing,
merge into `main` using a local branch tracking `origin/main`:
```bash
git checkout -b main-local origin/main
git merge --no-ff claude/vcg-deinterlacer-update-8l66j -m "Merge message"
git push "https://..." main-local:main
```
