#!/usr/bin/env python3
# ============================================================
# VCG DEINTERLACER
# ============================================================
#
# Version:    1.3.0
# Build Date: 2026-05-18
# Author:     VideoCaptureGuide
# Website:    https://www.youtube.com/@VideoCaptureGuide
#
# Modern Windows 11 GUI for enhancing analog video tapes
# (VHS, Video8, Hi8) using VapourSynth and QTGMC.
#
# ============================================================
# LICENSE (MIT)
# ============================================================
#
# Copyright (c) 2026 VideoCaptureGuide
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# ============================================================
# DISCLAIMER
# ============================================================
#
# This software is provided for free and is offered "as is"
# without any warranty. The author makes no guarantees about
# the software's functionality, reliability, or suitability
# for any particular purpose. Use at your own risk.
#
# This software relies on third-party components (FFmpeg,
# VapourSynth, and various plugins) which are subject to
# their own licenses. Users are responsible for ensuring
# compliance with all applicable licenses.
#
# ============================================================

# Version constants
VERSION = "1.7.3"
BUILD_DATE = "2026-07-08"
VERSION_STRING = f"{VERSION} ({BUILD_DATE})"
AUTHOR = "VideoCaptureGuide"
AUTHOR_HANDLE = "@VideoCaptureGuide"
WEBSITE = "https://www.youtube.com/@VideoCaptureGuide"
COPYRIGHT_YEAR = "2026"

import os
import sys
import subprocess
import json
import threading
import time
import zipfile
import shutil
import tempfile
from pathlib import Path

# ============================================================
# Check for tkinter before importing
# ============================================================

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    from tkinter import font as tkfont
except ImportError:
    # Show error using Windows message box if tkinter not available
    import ctypes
    ctypes.windll.user32.MessageBoxW(
        0,
        "Python tkinter is not installed.\n\n"
        "To fix this:\n"
        "1. Open 'Apps & Features' in Windows Settings\n"
        "2. Find Python, click 'Modify'\n"
        "3. Ensure 'tcl/tk and IDLE' is checked\n"
        "4. Click Install\n\n"
        "Or reinstall Python from python.org with default options.",
        "VCG Deinterlacer - Missing Component",
        0x10  # MB_ICONERROR
    )
    sys.exit(1)

# Check for PIL/Pillow for image display
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# Check for tkinterdnd2 for drag and drop.
# Catch all exceptions, not just ImportError — in a Nuitka onefile build the
# tkdnd DLL can fail to load with OSError after a successful import.
# On a fresh machine tkinterdnd2 may not be installed yet.  We attempt a
# silent pip install here (before BaseWindow is defined) so that the first
# run after setup gets DnD support without requiring a restart.
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except Exception:
    try:
        import subprocess as _sp
        _sp.run(
            [sys.executable, '-m', 'pip', 'install', 'tkinterdnd2',
             '--quiet', '--disable-pip-version-check'],
            capture_output=True, timeout=60
        )
        from tkinterdnd2 import DND_FILES, TkinterDnD
        HAS_DND = True
    except Exception:
        HAS_DND = False

# ============================================================
# Configuration
# ============================================================

# In a Nuitka onefile build both sys.executable and __file__ resolve to the
# temporary extraction folder — NOT the folder containing the real EXE.
# We need __nuitka_binary_dir (set by Nuitka) or fall back to sys.argv[0]
# to find the real EXE location so _deps\ is created next to the EXE.
_IS_COMPILED = getattr(sys, 'frozen', False) or '__compiled__' in globals()
if _IS_COMPILED:
    # Nuitka sets __nuitka_binary_dir to the folder holding the real EXE.
    # Fall back to sys.argv[0] if that variable isn't available.
    SCRIPT_DIR = globals().get(
        '__nuitka_binary_dir',
        os.path.dirname(os.path.abspath(sys.argv[0]))
    )
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Startup diagnostic (visible in the console window) ─────────
print(f"[VCG Diag] compiled     = {_IS_COMPILED}")
print(f"[VCG Diag] sys.exe      = {sys.executable}")
print(f"[VCG Diag] sys.argv[0]  = {sys.argv[0]}")
print(f"[VCG Diag] __file__     = {__file__}")
print(f"[VCG Diag] nuitka_dir   = {globals().get('__nuitka_binary_dir', 'N/A')}")
print(f"[VCG Diag] SCRIPT_DIR   = {SCRIPT_DIR}")
PATHS_FILE = os.path.join(SCRIPT_DIR, 'paths.json')

# ── Beta-02 portable deps (VapourBox-style) ───────────────────
# Single ZIP downloaded from our own GitHub releases on first run.
# Everything lives in  _deps\  next to the EXE — fully portable.
#
#   _deps\
#     ffmpeg\    ffmpeg.exe  ffprobe.exe
#     vs\        vspipe.exe  VapourSynth.dll  VSScript.dll
#                python3XX.dll  python3XX.zip  python3XX._pth
#                site-packages\  vapoursynth.pyd  havsfunc.py ...
#                plugins\        lsmas.dll  libmvtools.dll  fmtconv.dll
#     vcg_deps.version
#
# Build the ZIP once with  build_deps_package.bat  (on the dev machine)
# then upload to GitHub releases and set DEPS_ZIP_URL below.

DEPS_DIR        = os.path.join(SCRIPT_DIR, '_deps')
FFMPEG_DEPS_DIR = os.path.join(DEPS_DIR, 'ffmpeg')
VS_DEPS_DIR     = os.path.join(DEPS_DIR, 'vs')
DEPS_VERSION    = '10'  # bump when you upload a new deps ZIP
print(f"[VCG Diag] DEPS_DIR  = {DEPS_DIR}")
print(f"[VCG Diag] deps exist= {os.path.isdir(DEPS_DIR)}")

# URL is derived from DEPS_VERSION above — bump that constant to update the URL.
DEPS_ZIP_URL = (
    'https://github.com/Video-Capture-Guide/vcg-deinterlacer-deps'
    f'/releases/download/v{DEPS_VERSION}/vcg-deps-v{DEPS_VERSION}.zip'
)


def load_tool_paths():
    """Load tool paths from paths.json if it exists."""
    if os.path.exists(PATHS_FILE):
        try:
            with open(PATHS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

_tool_paths = load_tool_paths()

# ── Path resolution: portable _deps\ takes priority ──────────
FFMPEG_PATH  = (os.path.join(FFMPEG_DEPS_DIR, 'ffmpeg.exe')
                if os.path.exists(os.path.join(FFMPEG_DEPS_DIR, 'ffmpeg.exe'))
                else _tool_paths.get('ffmpeg_path') or r'C:\ffmpeg\bin\ffmpeg.exe')

FFPROBE_PATH = (os.path.join(FFMPEG_DEPS_DIR, 'ffprobe.exe')
                if os.path.exists(os.path.join(FFMPEG_DEPS_DIR, 'ffprobe.exe'))
                else _tool_paths.get('ffprobe_path') or r'C:\ffmpeg\bin\ffprobe.exe')

def _find_pip_vspipe():
    """Find vspipe.exe from pip-installed VapourSynth (R74+, supports Python 3.12+).

    VapourSynth R74 can be installed via 'pip install vapoursynth' and ships
    vspipe.exe alongside the package. R74 supports Python 3.12-3.14+, unlike
    R73 which only supports Python 3.8-3.12.
    """
    try:
        import importlib.util
        spec = importlib.util.find_spec('vapoursynth')
        if spec and spec.origin:
            pkg_dir = os.path.dirname(spec.origin)
            # R74 places vspipe.exe inside the vapoursynth package directory
            # or as a console_script in Scripts/
            candidates = [
                os.path.join(pkg_dir, 'vspipe.exe'),
                os.path.normpath(os.path.join(pkg_dir, '..', 'vspipe.exe')),
                os.path.join(os.path.dirname(sys.executable), 'vspipe.exe'),
                os.path.join(os.path.dirname(sys.executable), 'Scripts', 'vspipe.exe'),
                os.path.join(sys.prefix, 'Scripts', 'vspipe.exe'),
            ]
            for c in candidates:
                if os.path.exists(c):
                    return c
    except Exception:
        pass
    return None


def _find_pip_vapoursynth_dlls():
    """Return a list of (src_path, dll_name) for VSScript/VapourSynth DLLs
    found in the pip-installed vapoursynth package.

    The pip-installed vapoursynth==73 for Python 3.14 contains VSScript.dll
    and VapourSynth.dll compiled against Python 3.14.  Copying these to
    VS_DEPS_DIR lets the bundled vspipe.exe (R73) use Python 3.14.
    """
    results = []
    try:
        import importlib.util
        spec = importlib.util.find_spec('vapoursynth')
        if not spec or not spec.origin:
            return results

        # Build candidate search directories
        pkg_dir = os.path.dirname(spec.origin)
        site_dir = os.path.dirname(pkg_dir)  # one level up = site-packages root
        search_dirs = [pkg_dir, site_dir]
        if spec.submodule_search_locations:
            search_dirs.extend(list(spec.submodule_search_locations))

        target_names = {'vsscript.dll', 'vapoursynth.dll'}
        seen = set()
        for d in search_dirs:
            if not os.path.isdir(d):
                continue
            try:
                for fname in os.listdir(d):
                    if fname.lower() in target_names and fname.lower() not in seen:
                        results.append((os.path.join(d, fname), fname))
                        seen.add(fname.lower())
            except Exception:
                pass
    except Exception:
        pass
    return results


def _try_upgrade_bundled_vsscript():
    """Copy Python-3.14-compatible DLLs from pip package to _deps/vs/.

    The bundled R73 vsscript.dll was compiled to find Python 3.8-3.12 only.
    The pip-installed vapoursynth==73 for Python 3.14 has a vsscript.dll
    that was compiled for Python 3.14.  Replacing the bundled DLL fixes the
    'Failed to initialize VSScript' error without needing a new deps package.

    Returns True if at least one DLL was copied successfully.
    """
    if not os.path.isdir(VS_DEPS_DIR):
        return False
    dlls = _find_pip_vapoursynth_dlls()
    copied = 0
    for src, name in dlls:
        dst = os.path.join(VS_DEPS_DIR, name)
        try:
            shutil.copy2(src, dst)
            copied += 1
        except Exception:
            pass
    return copied > 0


_PIP_VSPIPE = _find_pip_vspipe()

VSPIPE_PATH  = (os.path.join(VS_DEPS_DIR, 'vspipe.exe')
                if os.path.exists(os.path.join(VS_DEPS_DIR, 'vspipe.exe'))
                else _tool_paths.get('vspipe_path')
                or _PIP_VSPIPE
                or os.path.join(os.environ.get('LOCALAPPDATA', ''),
                                'Programs', 'VapourSynth', 'core', 'vspipe.exe'))


# ── Dependency check ──────────────────────────────────────────

def deps_ready():
    """Return True when the portable _deps package is fully extracted."""
    version_file = os.path.join(DEPS_DIR, 'vcg_deps.version')
    if not os.path.exists(version_file):
        return False
    try:
        with open(version_file) as f:
            return f.read().strip() == DEPS_VERSION
    except Exception:
        return False

# Legacy aliases so the rest of the code still compiles
def ffmpeg_ok():
    return os.path.exists(FFMPEG_PATH)

def vapoursynth_ok():
    return os.path.exists(VSPIPE_PATH)

def check_deps():
    return ffmpeg_ok(), vapoursynth_ok()


# ── Portable environment for vspipe subprocess calls ─────────

def get_vspipe_env():
    """Return an env dict that makes portable vspipe find its Python runtime.

    The _deps\\vs\\ folder contains:
      - python3XX.dll   (Python runtime DLL)
      - python3XX.zip   (Python stdlib — encodings, etc.)
      - python3XX._pth  (tells Python where to find stdlib + site-packages)
      - site-packages\\  (vapoursynth.pyd, havsfunc.py, ...)
      - plugins64\\ or plugins\\  (lsmas.dll, libmvtools.dll, fmtconv.dll)
      - portable.vs     (marker that tells VSScript to use portable Python mode)

    The ._pth file handles module search paths.  We must NOT set PYTHONHOME
    or PYTHONPATH — those conflict with the ._pth mechanism and can cause
    "Failed to import encodings" when the embedded Python starts up.

    We only need to:
      - Ensure portable.vs marker file is present (VSScript portable mode)
      - Put VS_DEPS_DIR first on PATH (so DLLs are found there)
      - Set VSPluginPath for VapourSynth plugin auto-loading
      - REMOVE any inherited PYTHONHOME / PYTHONPATH from Nuitka's runtime
    """
    if not os.path.isdir(VS_DEPS_DIR):
        return None   # not in portable mode, use system environment

    # ── Ensure portable.vs marker exists.
    #    VSScript.dll checks for this file next to itself to enable portable mode.
    #    Without it, VSScript tries to find Python via the Windows registry,
    #    which fails (or finds the wrong version) when system Python differs.
    portable_marker = os.path.join(VS_DEPS_DIR, 'portable.vs')
    if not os.path.exists(portable_marker):
        try:
            open(portable_marker, 'w').close()
        except Exception:
            pass  # non-fatal; continue and hope VSScript finds Python anyway

    env = os.environ.copy()

    # ── Remove ALL Python-related env vars to prevent Nuitka's embedded
    #    Python from conflicting with the portable Python inside _deps\vs\.
    for _k in list(env.keys()):
        if _k.upper().startswith('PYTHON'):
            env.pop(_k, None)
    # Also remove virtual-env and launcher markers
    for _k in ('__PYVENV_LAUNCHER__', 'VIRTUAL_ENV', 'VIRTUAL_ENV_PROMPT'):
        env.pop(_k, None)

    # ── Find the plugins directory (build script may use plugins64\ or plugins\)
    plugins64_dir = os.path.join(VS_DEPS_DIR, 'plugins64')
    plugins_dir   = os.path.join(VS_DEPS_DIR, 'plugins')
    if os.path.isdir(plugins64_dir):
        plugin_dir = plugins64_dir
    elif os.path.isdir(plugins_dir):
        plugin_dir = plugins_dir
    else:
        plugin_dir = plugins64_dir  # default even if missing

    # ── Set VapourSynth plugin path ──────────────────────────────────────────
    env['VSPluginPath'] = plugin_dir

    # ── Prepend VS_DEPS_DIR and plugin_dir to PATH.
    #    VS_DEPS_DIR  → Windows finds python3XX.dll, VapourSynth.dll, VSScript.dll
    #    plugin_dir   → Windows finds libfftw3-3.dll and other plugin sub-deps
    #                   when core.std.LoadPlugin() loads DFTTest, fft3dfilter, etc.
    env['PATH'] = (VS_DEPS_DIR + os.pathsep
                   + plugin_dir + os.pathsep
                   + env.get('PATH', ''))

    return env


def _collect_vs_deps_diagnostic():
    """Return a multi-line string listing key files in VS_DEPS_DIR for diagnostics."""
    lines = []
    lines.append(f"VS_DEPS_DIR : {VS_DEPS_DIR}")
    lines.append(f"  exists    : {os.path.isdir(VS_DEPS_DIR)}")
    if not os.path.isdir(VS_DEPS_DIR):
        return '\n'.join(lines)

    # List top-level files
    try:
        top = sorted(os.listdir(VS_DEPS_DIR))
    except Exception as e:
        lines.append(f"  listdir error: {e}")
        return '\n'.join(lines)

    lines.append(f"  top-level files ({len(top)}):")
    for name in top:
        full = os.path.join(VS_DEPS_DIR, name)
        if os.path.isfile(full):
            size = os.path.getsize(full)
            lines.append(f"    {name}  ({size:,} bytes)")
        else:
            lines.append(f"    {name}/  [dir]")

    # Check specific key files
    key_files = [
        'vspipe.exe', 'VSScript.dll', 'VapourSynth.dll',
        'portable.vs',
    ]
    # Python DLL and stdlib — detect by pattern
    try:
        for f in top:
            if f.lower().startswith('python3') and (f.lower().endswith('.dll')
                    or f.lower().endswith('.zip') or f.lower().endswith('._pth')):
                key_files.append(f)
    except Exception:
        pass

    lines.append("  key file check:")
    for kf in key_files:
        if kf == 'VapourSynth.dll':
            # R74 renamed VapourSynth.dll → libvapoursynth.dll; accept either
            exists = (os.path.exists(os.path.join(VS_DEPS_DIR, 'VapourSynth.dll')) or
                      os.path.exists(os.path.join(VS_DEPS_DIR, 'libvapoursynth.dll')))
            label = 'VapourSynth.dll / libvapoursynth.dll'
        else:
            exists = os.path.exists(os.path.join(VS_DEPS_DIR, kf))
            label = kf
        lines.append(f"    {'OK  ' if exists else 'MISS'} {label}")

    # List site-packages
    sp = os.path.join(VS_DEPS_DIR, 'site-packages')
    if os.path.isdir(sp):
        try:
            sp_files = sorted(os.listdir(sp))
            lines.append(f"  site-packages ({len(sp_files)} items): " + ', '.join(sp_files[:30]))
        except Exception as e:
            lines.append(f"  site-packages listdir error: {e}")
    else:
        lines.append("  site-packages/: MISSING")

    # List plugins directory
    for pdir in ('plugins64', 'plugins'):
        pd = os.path.join(VS_DEPS_DIR, pdir)
        if os.path.isdir(pd):
            try:
                pd_files = sorted(os.listdir(pd))
                lines.append(f"  {pdir}/ ({len(pd_files)} items): " + ', '.join(pd_files[:20]))
            except Exception as e:
                lines.append(f"  {pdir}/ listdir error: {e}")
            break
    else:
        lines.append("  plugins64/ and plugins/: BOTH MISSING")

    return '\n'.join(lines)


def write_paths_json():
    """Persist resolved tool paths for the next launch."""
    try:
        data = {
            'ffmpeg_path':  FFMPEG_PATH,
            'ffprobe_path': FFPROBE_PATH,
            'vspipe_path':  VSPIPE_PATH,
        }
        with open(PATHS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

# Config file for remembering settings
CONFIG_FILE = os.path.join(os.environ.get('APPDATA', ''), 'RestorationWizard', 'config.json')

# QTGMC settings
QTGMC_SETTINGS = {
    'TR0': 2, 'TR1': 2, 'TR2': 1,
    'Rep0': 1, 'Rep1': 0, 'Rep2': 4,
    'DCT': 5, 'ThSCD1': 300, 'ThSCD2': 110,
    'SourceMatch': 3, 'Lossless': 2, 'Sharpness': 0.1,
    'Sbb': 0, 'MatchPreset': '"slow"',
    'NoiseProcess': 2, 'GrainRestore': 0.0, 'NoiseRestore': 0.4,
    'NoisePreset': '"slow"', 'StabilizeNoise': False,
    'NoiseTR': 0, 'NoiseDeint': '"bob"'
}

# Tips and Tricks displayed during processing
TIPS = [
    ("What is interlacing?",
     "Interlaced video displays odd and even lines in alternating fields, a technique from the CRT era to reduce flicker. Each frame is split into two fields captured 1/60th (NTSC) or 1/50th (PAL) of a second apart."),
    
    ("Why deinterlace?",
     "Modern displays are progressive — they show complete frames. Playing interlaced video on a progressive display creates \"combing\" artifacts where motion appears jagged. QTGMC reconstructs full frames from the interlaced fields."),
    
    ("What is QTGMC?",
     "QTGMC (Quality Temporal Gaussian Motion Compensated) is widely considered the gold standard for deinterlacing. It analyzes motion between fields and uses advanced algorithms to reconstruct missing lines with remarkable accuracy."),
    
    ("TFF vs BFF: What's the difference?",
     "TFF (Top Field First) and BFF (Bottom Field First) describe which set of lines is captured first. Most SD capture cards use TFF, while MiniDV/Digital8 camcorders use BFF. Using the wrong setting causes jerky, stuttering motion."),
    
    ("What is a field?",
     "A field is half of an interlaced frame — either all odd lines or all even lines. NTSC video has 60 fields per second (30 frames), PAL has 50 fields per second (25 frames). Each field captures a slightly different moment in time."),
    
    ("Why does my video look \"combed\"?",
     "Combing occurs when you view interlaced footage on a progressive display without deinterlacing. The two fields from different moments in time are shown simultaneously, creating a horizontal striped pattern on moving objects."),
    
    ("Deinterlacing vs Upscaling",
     "Deinterlacing converts interlaced video to progressive by reconstructing missing lines. Upscaling increases resolution (e.g., 480p to 1080p). VCG Deinterlacer focuses on deinterlacing — upscaling is a separate process best done afterward."),
    
    ("What is temporal denoising?",
     "Temporal denoising (like SMDegrain) analyzes multiple frames to identify noise versus actual detail. Since noise is random but detail persists across frames, this method can remove noise while preserving sharpness."),
    
    ("Why do analog tapes have noise?",
     "Magnetic tape physically degrades over time, and the analog recording process itself introduces noise. VHS in particular has limited bandwidth and resolution, making noise more visible. Temporal denoising helps clean this up."),
    
    ("What does \"legal range\" mean?",
     "Broadcast video uses levels 16-235 (not 0-255) for luma. Values below 16 are \"super black\" and above 235 are \"super white.\" These can cause problems on some displays or when uploading to video platforms."),
    
    ("NTSC vs PAL: What's the difference?",
     "NTSC (North America, Japan) runs at 29.97fps with 480 lines. PAL (Europe, Australia) runs at 25fps with 576 lines. PAL has higher resolution but NTSC has smoother motion. They also use different color encoding systems."),
    
    ("What about SECAM?",
     "SECAM was used in France, Russia, and parts of Africa. It has the same resolution as PAL (576 lines, 25fps) but encodes color differently. Most SECAM equipment also plays PAL, and SECAM captures are typically converted to PAL for editing."),
    
    ("Why is my VHS video only 240 lines?",
     "VHS actually records about 240 lines of horizontal resolution, though the vertical is still 480/576 lines. S-VHS improved this to about 400 lines. This is why VHS looks softer than broadcast TV or laserdisc."),
    
    ("What is Hi8 vs Video8?",
     "Video8 was Sony's compact tape format from 1985 with similar quality to VHS. Hi8 (1989) improved resolution to S-VHS levels (~400 lines) and added better color. Both use the same tape size but Hi8 requires Hi8 equipment."),
    
    ("Why is MiniDV \"digital\"?",
     "MiniDV records video as digital data using DV compression (DV25), not analog signals. This means no generation loss when copying and consistent quality. DV has about 500 lines of resolution — better than any analog format."),
    
    ("What is Digital8?",
     "Digital8 records DV-format digital video onto Hi8/Video8 tapes. It offers the same quality as MiniDV but uses larger, cheaper tapes. Digital8 camcorders can also play back analog Video8/Hi8 tapes."),
    
    ("What is DV25 vs DV50?",
     "DV25 (standard DV/MiniDV) compresses video at 25 Mbps using 4:1:1 color sampling (NTSC) or 4:2:0 (PAL). DV50 (DVCPRO50) doubles the bitrate to 50 Mbps with 4:2:2 color, used in professional broadcast."),
    
    ("Why do some tapes look better?",
     "Tape quality depends on: the original recording equipment, tape grade (standard vs high-grade), storage conditions, number of plays, and the playback deck used for capture. Premium tapes stored properly can last decades."),
    
    ("What is \"rainbow\" noise on VHS?",
     "The swirling rainbow patterns on VHS are caused by crosstalk between the luma and chroma signals. This is inherent to composite video and VHS's limited bandwidth. S-VHS and S-Video connections reduce this significantly."),
    
    ("Can I capture PAL tapes in North America?",
     "Yes, but you need a PAL-compatible VCR or camcorder. Some decks are multi-system (PAL/NTSC). The capture card also needs to support PAL. You can then edit and convert to any format for playback."),
    
    ("Why is S-Video better than composite?",
     "Composite combines luma (brightness) and chroma (color) into one signal, causing interference. S-Video keeps them separate, resulting in sharper images with less color bleeding and no rainbow artifacts. Always use S-Video when available."),
    
    ("What is color bleeding?",
     "Color bleeding occurs when color information \"leaks\" into adjacent areas, causing red to smear into neighboring objects. It's caused by composite video's combined signal and VHS's limited color bandwidth. S-Video reduces this significantly."),
    
    ("What is a timebase corrector (TBC)?",
     "A TBC stabilizes the timing of video signals from tape, fixing horizontal jitter and sync issues. Professional decks have built-in TBCs. External TBCs (like the DataVideo TBC-1000) can dramatically improve capture quality from consumer decks."),
    
    ("VCR or camcorder for capture?",
     "For VHS/S-VHS, a quality VCR (especially S-VHS decks like JVC HR-S9911U) usually gives better results. For Video8/Hi8, the original camcorder often works best. MiniDV should use FireWire, not analog outputs."),
    
    ("What capture card should I use?",
     "For SD capture, use an IO-Data GV-USB2 (Windows 11 version) or an older ATI TV Wonder 600. Other capture methods include SDI capture, HDMI capture, DV-25 capture via FireWire, and RF capture for broadcast recordings."),
    
    ("Why use FireWire for MiniDV?",
     "FireWire (IEEE 1394) transfers the digital DV data directly from tape — no conversion, no quality loss. Analog outputs convert to composite/S-Video, losing quality. Always capture MiniDV via FireWire when possible."),
    
    ("What software for capture?",
     "VirtualDub (Windows) is popular for analog capture. OBS Studio works for many devices. For FireWire/DV, use Windows Movie Maker (old), Adobe Premiere, or specialized tools like ScenalyzerLive. Always capture to AVI or MOV, not MP4."),
    
    ("What is \"dropped frames\"?",
     "Dropped frames occur when your computer can't keep up with the incoming video data. This causes jerky playback. Fix by: closing other programs, using a faster hard drive (SSD), lowering capture resolution, or using a dedicated capture PC."),
    
    ("Should I capture at highest quality?",
     "Yes! Always capture uncompressed or with lossless codecs (like Huffyuv, Lagarith, or FFV1). You can compress later. Capturing directly to H.264/MP4 throws away quality you can never recover. Storage is cheap; quality is priceless."),
    
    ("What is 3:2 pulldown?",
     "When 24fps film is transferred to 29.97fps NTSC video, extra fields are added in a 3:2 pattern. This can be reversed (\"inverse telecine\") to recover the original 24fps. VCG Deinterlacer handles standard interlaced video, not telecined film."),
    
    ("What is \"stepping\" artifact?",
     "Stepping appears as jagged stair-step patterns on diagonal lines and edges. It's caused by poor deinterlacing or viewing interlaced content on a progressive display. Quality deinterlacing with QTGMC eliminates this."),
    
    ("Why horizontal lines in my video?",
     "Horizontal lines during playback usually indicate head tracking issues in the VCR. Try adjusting the tracking control, cleaning the video heads, or using a different deck. Some tapes are damaged beyond recovery."),
    
    ("What causes \"snow\" or static?",
     "Snow indicates a weak signal, often from: dirty video heads, a damaged tape, or poor cable connections. Clean the VCR heads with a cleaning tape, check all connections, and try a different tape to isolate the problem."),
    
    ("Why is my video black and white?",
     "This usually means: wrong input selected (composite vs S-Video), a PAL/NTSC mismatch, or a damaged tape. Check your connections and ensure your equipment matches the tape format. Some very old tapes may have lost color."),
    
    ("What is \"flagging\"?",
     "Flagging (wavy distortion at the top) is caused by timing instability in the video signal. A timebase corrector (TBC) can fix this. Some capture cards handle it better than others. It's common with worn tapes."),
    
    ("Why do colors look wrong?",
     "Tape degradation, misaligned equipment, or wrong color settings during capture can cause color issues. VCG Deinterlacer's color analysis can detect and correct color casts automatically using vectorscope data."),
    
    ("What causes audio sync drift?",
     "Audio drift happens when audio and video run at slightly different speeds. It's common with analog capture. Most editing software can fix this. Capture both streams together when possible, not separately."),
    
    ("Why a black bar on one side?",
     "This is the \"head switching\" area where VCRs switch between video heads. It's normally hidden in the overscan area of CRT TVs. VCG Deinterlacer crops 8 pixels from each side for SD captures to remove this."),
    
    ("What are \"dropouts\"?",
     "Dropouts are brief white flashes, sparkles, or horizontal streaks caused by tape damage or debris on the tape surface. They can sometimes be reduced with temporal filtering, which is why VCG Deinterlacer offers dropout removal."),
    
    ("Why does my video look soft?",
     "VHS is inherently soft due to limited bandwidth (~240 lines horizontal resolution). Avoid over-sharpening which creates harsh artifacts. Embrace the vintage look, or upgrade to S-VHS/Hi8 captures for better source material."),
    
    ("Preserve your originals!",
     "After capture, store your original tapes properly: vertical position, cool and dry environment, away from magnets and electronics. Magnetic tape degrades over time — your digital capture may outlast the original."),
    
    ("Why capture in 4:3 aspect ratio?",
     "SD video (VHS, Hi8, MiniDV) was recorded in 4:3 aspect ratio. Stretching to 16:9 distorts the image. Keep the original 4:3 ratio and add pillarboxing (black bars on sides) for widescreen displays if desired."),
    
    ("What is Pixel Aspect Ratio (PAR)?",
     "SD video uses non-square pixels. NTSC DV is 720x480 with 10:11 PAR (or 8:9 for some DV). PAL is 720x576 with 59:54 PAR. VCG Deinterlacer converts to square pixels (1:1 PAR) so your video displays correctly on modern screens."),
    
    ("Should I denoise heavily?",
     "Less is more with denoising. Heavy denoising removes tape noise but can also remove fine detail, creating a \"waxy\" look. Use light denoising for most content. Some grain is authentic to the format and era."),
    
    ("What output format should I choose?",
     "ProRes HQ: Best for editing, large files. H.264: Good balance of quality and size, widely compatible. FFV1: Mathematically lossless, perfect for archiving. Choose based on your workflow and storage."),
    
    ("Why does processing take so long?",
     "QTGMC is computationally intensive — it analyzes motion across multiple frames for each output frame. A 1-hour video might take 2-4 hours to process depending on your CPU. Quality takes time, but it's worth it!"),
]

# Promo text appended to each tip
TIP_PROMO = "Subscribe to VideoCaptureGuide on YouTube for tutorials on VHS capture, tape preservation, equipment reviews, and more: www.YouTube.com/@VideoCaptureGuide"

# ============================================================
# Settings Persistence
# ============================================================

def load_settings():
    """Load saved settings from config file."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_settings(settings):
    """Save settings to config file."""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
    except:
        pass

# ============================================================
# Modern Windows 11 Color Palette
# ============================================================

class Colors:
    BG_DARK = "#0F0F0F"
    BG_MAIN = "#1A1A1A"
    BG_CARD = "#252525"
    BG_CARD_HOVER = "#2E2E2E"
    BG_SIDEBAR = "#141414"
    ACCENT = "#7C6FF7"
    ACCENT_HOVER = "#9488FA"
    ACCENT_DARK = "#5A51C9"
    ACCENT_DIM = "#3D3770"
    TEXT_PRIMARY = "#F0F0F0"
    TEXT_SECONDARY = "#909090"
    TEXT_DISABLED = "#505050"
    TEXT_HINT = "#606060"
    SUCCESS = "#5DBB6B"
    WARNING = "#F5C542"
    ERROR = "#EF5350"
    INFO = "#5BC4E0"
    BORDER = "#333333"
    BORDER_LIGHT = "#444444"
    BORDER_FOCUS = "#7C6FF7"
    SEPARATOR = "#2A2A2A"

# ============================================================
# Subprocess helper - hide console windows
# ============================================================

def run_hidden(cmd, **kwargs):
    """Run subprocess with hidden console window on Windows.
    
    Handles Nuitka onefile compilation where stdin/stdout handles may not exist.
    """
    startupinfo = None
    creationflags = 0
    
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        # CREATE_NO_WINDOW prevents console window from appearing
        creationflags = subprocess.CREATE_NO_WINDOW
    
    # For Nuitka onefile builds, we need to explicitly use PIPE
    # instead of capture_output=True which can fail with invalid handles
    try:
        return subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            startupinfo=startupinfo,
            creationflags=creationflags,
            **kwargs
        )
    except OSError as e:
        # If we still get handle errors, return a fake failed result
        class FakeResult:
            returncode = -1
            stdout = ""
            stderr = str(e)
        return FakeResult()

# ============================================================
# Piped subprocess helper (producer → consumer, no temp file)
# ============================================================

def _run_piped(prod_cmd, cons_cmd, prod_env=None, prod_cwd=None):
    """Pipe producer stdout directly into consumer stdin.

    Used to stream vspipe y4m output straight into FFmpeg, eliminating the
    need for an intermediate temp file that can exhaust disk space.
    Returns a namespace whose .returncode, .stderr, .producer_rc, .consumer_rc
    fields mirror run_hidden() enough for the existing retry logic to work.
    """
    import types as _types
    startupinfo = None
    creationflags = 0
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        creationflags = subprocess.CREATE_NO_WINDOW
    prod = subprocess.Popen(
        prod_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        startupinfo=startupinfo,
        creationflags=creationflags,
        env=prod_env,
        cwd=prod_cwd,
    )
    cons = subprocess.Popen(
        cons_cmd,
        stdin=prod.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        startupinfo=startupinfo,
        creationflags=creationflags,
    )
    prod.stdout.close()  # let producer receive SIGPIPE if consumer exits early
    cons_out, cons_err = cons.communicate()
    prod.wait()
    prod_err = prod.stderr.read()
    r = _types.SimpleNamespace(
        producer_rc=prod.returncode,
        producer_stderr=prod_err.decode('utf-8', errors='replace'),
        consumer_rc=cons.returncode,
        consumer_stderr=cons_err.decode('utf-8', errors='replace'),
        stdout='',
    )
    r.returncode = r.producer_rc if r.producer_rc != 0 else r.consumer_rc
    r.stderr = r.producer_stderr + (
        '\n' + r.consumer_stderr if r.consumer_stderr.strip() else '')
    return r

# ============================================================
# Preview Frame Extraction
# ============================================================

def extract_preview_frame(filepath, frame_num=200):
    """Extract a single preview frame from a video file using FFmpeg.

    Tries frame *frame_num* first; falls back to frame 0 for short clips.
    Returns the path to a temp PNG file, or None on failure.
    """
    tmp = os.path.join(tempfile.gettempdir(),
                       f'vcg_preview_{os.getpid()}_{frame_num}.png')
    # Select frame by index (0-based)
    cmd = [FFMPEG_PATH, '-y', '-i', filepath,
           '-vf', f'select=eq(n\\,{frame_num})',
           '-vframes', '1', '-pix_fmt', 'rgb24', tmp]
    result = run_hidden(cmd, timeout=30)
    if result.returncode == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 100:
        return tmp
    # Fallback: first frame
    cmd0 = [FFMPEG_PATH, '-y', '-i', filepath,
            '-vframes', '1', '-pix_fmt', 'rgb24', tmp]
    result0 = run_hidden(cmd0, timeout=30)
    if result0.returncode == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 100:
        return tmp
    return None


def extract_preview_frame_at_time(filepath, seconds, tag=0):
    """Extract a preview frame at *seconds* using FFmpeg fast seek (-ss before -i).

    Fast seek lands on the nearest keyframe then decodes forward, so it stays
    responsive even when scrubbing hours-long captures.  Returns the path to a
    temp PNG, or None on failure.  *tag* makes the temp filename unique so
    overlapping scrub requests never read a half-written file.
    """
    tmp = os.path.join(tempfile.gettempdir(),
                       f'vcg_trimprev_{os.getpid()}_{tag}.png')
    cmd = [FFMPEG_PATH, '-y', '-ss', f'{max(0.0, seconds):.3f}', '-i', filepath,
           '-vframes', '1', '-pix_fmt', 'rgb24', tmp]
    result = run_hidden(cmd, timeout=30)
    if result.returncode == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 100:
        return tmp
    return None


# ============================================================
# Telecine / IVTC Detection
# ============================================================

def detect_telecine(filepath, video_format, capture_method=None):
    """Detect 3:2 (NTSC) or 2:2 (PAL) pulldown patterns via FFmpeg idet.

    Runs idet on up to 500 frames.  A significant fraction of progressive
    frames embedded in otherwise-interlaced content is the signature of
    film-to-video telecine transfer.

    Returns a dict::

        {
          'detected'   : bool,
          'pattern'    : '3:2' | '2:2' | None,
          'confidence' : 'high' | 'low' | None,
          'target_fps' : float | None,
          'description': str,
          'dv_bypass'  : bool,  # True when skipped because source is DV
        }
    """
    # DV camcorder footage is natively interlaced — it is never film-sourced
    # telecined content.  idet can produce false positives on DV because the
    # intraframe DV codec sometimes causes field pairs to look "progressive" to
    # the detector, which would incorrectly enable IVTC and skip QTGMC entirely.
    if capture_method == 'dv':
        return {
            'detected': False, 'pattern': None, 'confidence': None,
            'target_fps': None,
            'description': (
                'DV/MiniDV source detected — IVTC is not applicable. '
                'Native DV camcorder footage is interlaced video, not telecined film. '
                'Standard QTGMC deinterlacing will be used.'
            ),
            'dv_bypass': True,
        }

    result = {
        'detected': False, 'pattern': None, 'confidence': None,
        'target_fps': None,
        'description': 'No telecine pattern detected.',
        'dv_bypass': False,
    }
    try:
        import re
        cmd = [FFMPEG_PATH, '-i', filepath, '-vf', 'idet',
               '-frames:v', '500', '-an', '-f', 'null', '-']
        r = run_hidden(cmd, timeout=90)
        output = r.stderr or ''

        tff = bff = prog = 0
        for line in output.split('\n'):
            if 'Multi frame detection' in line:
                m = re.search(r'TFF:\s*(\d+)', line, re.IGNORECASE)
                if m: tff = int(m.group(1))
                m = re.search(r'BFF:\s*(\d+)', line, re.IGNORECASE)
                if m: bff = int(m.group(1))
                m = re.search(r'Progressive:\s*(\d+)', line, re.IGNORECASE)
                if m: prog = int(m.group(1))

        total = tff + bff + prog
        if total < 20:
            return result

        interlaced = tff + bff
        prog_ratio = prog / total if total > 0 else 0

        # Telecine: significant progressive frames inside interlaced content.
        # NTSC 3:2 pulldown produces ~40% progressive frames (2 of every 5).
        # PAL film transfers are 2:2 — every frame's two fields come from the
        # same instant — so genuine film material reads as overwhelmingly
        # progressive to idet (80%+).  Ordinary interlaced PAL video with
        # static or low-motion shots easily shows 30-50% "progressive" frames
        # (idet cannot tell a still frame from a progressive one), so the PAL
        # threshold must be high to avoid false positives on true 50i content.
        if interlaced > 0 and prog_ratio > 0.15:
            if video_format == 'ntsc' and prog_ratio > 0.28:
                result.update({
                    'detected': True,
                    'pattern': '3:2',
                    'confidence': 'high' if prog_ratio > 0.35 else 'low',
                    'target_fps': 24000 / 1001,
                    'description': (
                        f'3:2 NTSC pulldown detected '
                        f'({prog_ratio*100:.0f}% progressive frames in sample). '
                        f'This is 24fps film transferred to 29.97fps. '
                        f'Inverse telecine will restore the native 23.976fps.'
                    ),
                })
            elif video_format == 'pal' and prog_ratio > 0.75:
                result.update({
                    'detected': True,
                    'pattern': '2:2',
                    'confidence': 'high' if prog_ratio > 0.85 else 'low',
                    'target_fps': 25.0,
                    'description': (
                        f'2:2 PAL film transfer detected '
                        f'({prog_ratio*100:.0f}% progressive frames in sample). '
                        f'This is 25fps film material carried as interlaced fields. '
                        f'The frame rate stays 25fps either way — inverse telecine '
                        f'reconstructs the original progressive frames by pairing '
                        f'fields instead of deinterlacing.'
                    ),
                })
    except Exception as exc:
        result['description'] = f'Telecine detection error: {exc}'
    return result


# ============================================================
# Analysis Functions (from v2.4)
# ============================================================

def get_video_info(filepath):
    """Get video information using ffprobe."""
    try:
        cmd = [
            FFPROBE_PATH, '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', filepath
        ]
        result = run_hidden(cmd, timeout=30)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    fps_parts = stream.get('r_frame_rate', '30/1').split('/')
                    fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0
                    return {
                        'width': stream.get('width', 0),
                        'height': stream.get('height', 0),
                        'fps': fps,
                        'duration': float(data.get('format', {}).get('duration', 0))
                    }
    except:
        pass
    return None

def detect_par_format(filepath):
    """
    Detect video format (NTSC/PAL) and capture method (SD/DV/DVD) using ffprobe
    by reading codec_name, sample_aspect_ratio, and resolution.

    Codec takes priority over SAR because NTSC DVD (mpeg2video, SAR 8:9) and
    NTSC DV25 (dvvideo, SAR 8:9) share the same pixel aspect ratio.

    SAR mapping:
      10:11  -> NTSC SD analog capture
       8:9   -> NTSC DV25 (MiniDV / Digital8) OR NTSC DVD 4:3
      32:27  -> NTSC DVD 16:9 anamorphic
      59:54  -> PAL SD analog capture
      16:15  -> PAL DV25 OR PAL DVD 4:3
      64:45  -> PAL DVD 16:9 anamorphic
    codec_name == 'dvvideo'   -> DV capture
    codec_name == 'mpeg2video' at SD resolution -> DVD/MPEG-2

    Returns dict with keys:
      'format'         : 'ntsc' | 'pal' | None
      'capture_method' : 'sd'   | 'dv'  | 'dvd' | None
      'sar'            : raw SAR string from ffprobe (e.g. '10:11')
    """
    result = {'format': None, 'capture_method': None, 'sar': ''}
    try:
        cmd = [
            FFPROBE_PATH, '-v', 'quiet', '-print_format', 'json',
            '-show_streams', '-select_streams', 'v:0', filepath
        ]
        probe = run_hidden(cmd, timeout=30)
        if probe.returncode != 0:
            return result
        data = json.loads(probe.stdout)
        streams = data.get('streams', [])
        if not streams:
            return result
        s = streams[0]

        width  = s.get('width', 0)
        height = s.get('height', 0)
        sar    = s.get('sample_aspect_ratio', '').strip()
        codec  = s.get('codec_name', '').lower()

        result['sar'] = sar

        # ── Determine format from SAR first (most precise), fall back to height ──
        if sar in ('10:11', '8:9', '32:27'):
            result['format'] = 'ntsc'
        elif sar in ('59:54', '16:15', '64:45'):
            result['format'] = 'pal'
        elif height == 480:
            result['format'] = 'ntsc'
        elif height == 576:
            result['format'] = 'pal'

        # ── Determine capture method — codec takes priority over SAR ──
        # dvvideo is unambiguous DV; mpeg2video at SD resolution is DVD.
        # SAR 8:9 / 16:15 is shared by both DV and DVD so codec must decide.
        if codec == 'dvvideo':
            result['capture_method'] = 'dv'
        elif codec == 'mpeg2video' and height in (480, 576):
            result['capture_method'] = 'dvd'
        elif sar in ('8:9', '16:15'):
            # No mpeg2video/dvvideo codec tag — fall back to DV assumption
            result['capture_method'] = 'dv'
        elif sar in ('10:11', '59:54'):
            result['capture_method'] = 'sd'
        elif sar in ('1:1', '0:1', ''):
            # Square pixels — typical of SD capture cards; treat as SD
            result['capture_method'] = 'sd'

    except Exception:
        pass
    return result

def classify_source(filepath):
    """Classify a video file as SD, AVCHD, or HDV by probing codec and resolution.

    Returns a dict with keys:
      source_class : 'sd' | 'avchd' | 'hdv' | 'unknown'
      display_name : human-readable string
      codec        : raw codec_name from ffprobe
      width, height: integers
      fps          : float
      field_order  : 'tff' | 'bff' | 'unknown'
      par_needed   : bool — True only for HDV 1440x1080 (needs 1920x1080 scale)
      pix_fmt      : raw pix_fmt from ffprobe (e.g. 'yuv420p', 'yuv420p10le')
      needs_pixfmt_conversion : bool — True for 10-bit / non-standard YUV that
                     must be normalized to 8-bit right after source load

    Classification rules:
      h264   + height 1080              → avchd
      mpeg2video + height 1080 + w 1440 → hdv
      anything else                     → sd
    """
    result = {
        'source_class': 'sd',
        'display_name': 'SD Interlaced',
        'codec': '',
        'width': 0,
        'height': 0,
        'fps': 0.0,
        'field_order': 'unknown',
        'par_needed': False,
        'pix_fmt': '',
        'needs_pixfmt_conversion': False,
    }
    try:
        cmd = [
            FFPROBE_PATH, '-v', 'quiet', '-print_format', 'json',
            '-show_streams', '-select_streams', 'v:0', filepath
        ]
        probe = run_hidden(cmd, timeout=30)
        if probe.returncode != 0:
            return result
        data = json.loads(probe.stdout)
        streams = data.get('streams', [])
        if not streams:
            return result
        s = streams[0]

        codec = s.get('codec_name', '').lower()
        width = s.get('width', 0)
        height = s.get('height', 0)
        fps_parts = s.get('r_frame_rate', '30/1').split('/')
        try:
            fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0
        except (ZeroDivisionError, ValueError):
            fps = 30.0
        fo_raw = s.get('field_order', '').lower()

        result['codec'] = codec
        result['width'] = width
        result['height'] = height
        result['fps'] = fps

        # VFM (IVTC) only accepts 8-bit YUV/gray.  10-bit sources (e.g. DVD rip
        # MKVs re-encoded as yuv420p10le) pass the loader format whitelist and
        # crash VFM with a cryptic format error, so flag anything YUV/gray that
        # is not a standard 8-bit format for conversion right after source load.
        # RGB and packed formats are excluded — generate_vpy_script() already
        # converts those with an explicit matrix.  yuv411p (DV) is excluded too:
        # the existing YUV411→YUV422P8 path handles it with better chroma.
        pix_fmt = s.get('pix_fmt', '').lower()
        result['pix_fmt'] = pix_fmt
        vfm_safe = {'yuv420p', 'yuvj420p', 'yuv422p', 'yuvj422p',
                    'yuv440p', 'yuvj440p', 'yuv444p', 'yuvj444p',
                    'yuv411p', 'yuvj411p', 'gray'}
        if pix_fmt.startswith(('yuv', 'gray')) and pix_fmt not in vfm_safe:
            result['needs_pixfmt_conversion'] = True

        if fo_raw in ('tt', 'tff'):
            result['field_order'] = 'tff'
        elif fo_raw in ('bb', 'bff'):
            result['field_order'] = 'bff'

        if codec == 'h264' and height == 1080:
            result['source_class'] = 'avchd'
            if result['field_order'] == 'unknown':
                result['field_order'] = 'tff'
            # Some Sony/Panasonic AVCHD camcorders record at 1440x1080 with non-square
            # pixels (4:3 PAR) that must be scaled to 1920x1080 — same as HDV.
            # Canon and most others record native 1920x1080 square pixels.
            if width == 1440:
                result['display_name'] = 'AVCHD / MTS (1440×1080i anamorphic)'
                result['par_needed'] = True
            else:
                result['display_name'] = 'AVCHD / MTS (1920×1080i)'
                result['par_needed'] = False
        elif codec == 'mpeg2video' and height == 1080 and width == 1440:
            result['source_class'] = 'hdv'
            result['display_name'] = 'HDV (1080i)'
            if result['field_order'] == 'unknown':
                result['field_order'] = 'tff'
            result['par_needed'] = True
        else:
            result['source_class'] = 'sd'
            result['display_name'] = 'SD Interlaced'

    except Exception:
        pass
    return result


def analyze_video_levels(filepath, sample_frames=10):
    """Analyze video levels to detect out-of-range values."""
    try:
        cmd = [FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', filepath]
        result = run_hidden(cmd, timeout=30)
        duration = float(result.stdout.strip())
    except:
        duration = 60
    
    intervals = [duration * i / (sample_frames + 1) for i in range(1, sample_frames + 1)]
    min_y, max_y = 255, 0
    
    for timestamp in intervals:
        try:
            cmd = [FFMPEG_PATH, '-ss', str(timestamp), '-i', filepath, '-vframes', '1',
                   '-vf', 'signalstats=stat=tout+vrep+brng,metadata=mode=print', '-f', 'null', '-']
            result = run_hidden(cmd, timeout=30)
            for line in result.stderr.split('\n'):
                if 'YMIN' in line:
                    try: min_y = min(min_y, int(line.split('=')[-1].strip()))
                    except: pass
                elif 'YMAX' in line:
                    try: max_y = max(max_y, int(line.split('=')[-1].strip()))
                    except: pass
        except:
            continue
    
    needs_adjustment = min_y < 16 or max_y > 235
    return {
        'min_y': min_y if min_y != 255 else None,
        'max_y': max_y if max_y != 0 else None,
        'needs_adjustment': needs_adjustment
    }

def analyze_color_data(filepath, sample_frames=10):
    """Analyze color data to detect color casts."""
    try:
        cmd = [FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', filepath]
        result = run_hidden(cmd, timeout=30)
        duration = float(result.stdout.strip())
    except:
        duration = 60
    
    intervals = [duration * i / (sample_frames + 1) for i in range(1, sample_frames + 1)]
    u_values, v_values, sat_values = [], [], []
    
    for timestamp in intervals:
        try:
            cmd = [FFMPEG_PATH, '-ss', str(timestamp), '-i', filepath, '-vframes', '1',
                   '-vf', 'signalstats=stat=tout+vrep+brng,metadata=mode=print', '-f', 'null', '-']
            result = run_hidden(cmd, timeout=30)
            for line in result.stderr.split('\n'):
                if 'UAVG' in line and '=' in line:
                    try: u_values.append(float(line.split('=')[-1].strip()))
                    except: pass
                elif 'VAVG' in line and '=' in line:
                    try: v_values.append(float(line.split('=')[-1].strip()))
                    except: pass
                elif 'SATAVG' in line and '=' in line:
                    try: sat_values.append(float(line.split('=')[-1].strip()))
                    except: pass
        except:
            continue
    
    if not u_values or not v_values:
        return None

    u_avg = sum(u_values) / len(u_values)
    v_avg = sum(v_values) / len(v_values)
    sat_avg = sum(sat_values) / len(sat_values) if sat_values else 0

    u_offset = u_avg - 128
    v_offset = v_avg - 128

    # Calculate consistency (standard deviation) across sampled frames.
    # A real color cast is persistent — low stddev relative to the offset.
    # Random variation across scenes should NOT trigger a correction recommendation.
    n = len(u_values)
    if n > 1:
        u_std = (sum((x - u_avg) ** 2 for x in u_values) / n) ** 0.5
        v_std = (sum((x - v_avg) ** 2 for x in v_values) / n) ** 0.5
    else:
        u_std = v_std = 0.0

    # Threshold rationale:
    #   3 units (old) = 2.3% shift — normal analog variation, far too aggressive.
    #  10 units        = 7.8% shift — visibly warm/cool, worth flagging.
    # Additionally require that the cast is consistent (stddev < 1.5× the offset),
    # so a single bright or dark scene doesn't mislead the analysis.
    CAST_THRESHOLD = 10
    color_cast = None
    u_notable = abs(u_offset) > CAST_THRESHOLD and (u_std < abs(u_offset) * 1.5 or n <= 1)
    v_notable = abs(v_offset) > CAST_THRESHOLD and (v_std < abs(v_offset) * 1.5 or n <= 1)

    if u_notable or v_notable:
        if abs(u_offset) >= abs(v_offset):
            color_cast = "blue" if u_offset > 0 else "yellow"
        else:
            color_cast = "red/magenta" if v_offset > 0 else "green/cyan"

    sat_issue = None
    if sat_avg < 20: sat_issue = "very_low"
    elif sat_avg < 35: sat_issue = "low"
    elif sat_avg > 80: sat_issue = "high"

    return {
        'u_avg': u_avg, 'v_avg': v_avg, 'sat_avg': sat_avg,
        'u_offset': u_offset, 'v_offset': v_offset,
        'u_std': u_std, 'v_std': v_std,
        'color_cast': color_cast, 'sat_issue': sat_issue,
        'u_correction': -u_offset, 'v_correction': -v_offset
    }

def analyze_noise_level(filepath, sample_frames=15, progress_callback=None):
    """
    Analyze noise level using temporal frame difference.
    Compares consecutive frames - in static areas, high difference indicates noise.
    Samples multiple points throughout the video for accuracy.
    """
    try:
        cmd = [FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', filepath]
        result = run_hidden(cmd, timeout=30)
        duration = float(result.stdout.strip())
    except:
        duration = 60
    
    diff_values = []
    variance_values = []
    
    # Sample frames from 20% to 80% of video (avoid intros/outros)
    sample_points = [0.2 + (0.6 * i / (sample_frames - 1)) for i in range(sample_frames)]
    
    for idx, offset in enumerate(sample_points):
        if progress_callback:
            progress_callback(idx + 1, sample_frames)
        
        timestamp = duration * offset
        
        try:
            # Analyze 1 second of video at this point for temporal noise.
            # -fflags +discardcorrupt prevents H.264 seek decode errors from
            # aborting the run before signalstats can measure any frames.
            cmd = [
                FFMPEG_PATH, '-fflags', '+discardcorrupt',
                '-ss', str(timestamp), '-i', filepath,
                '-t', '1',
                '-vf', 'signalstats=stat=tout+vrep+brng,metadata=mode=print',
                '-f', 'null', '-'
            ]
            result = run_hidden(cmd, timeout=30)
            
            # Parse temporal info
            for line in result.stderr.split('\n'):
                # YDIF = frame difference (temporal noise indicator)
                if 'YDIF' in line and '=' in line:
                    try:
                        diff_values.append(float(line.split('=')[-1].strip()))
                    except:
                        pass
                # TOUT = temporal outliers (noise/flicker)
                elif 'TOUT' in line and '=' in line:
                    try:
                        variance_values.append(float(line.split('=')[-1].strip()))
                    except:
                        pass
        except:
            pass
    
    # Analyze results
    if diff_values:
        avg_diff = sum(diff_values) / len(diff_values)
        # Also calculate standard deviation for consistency check
        if len(diff_values) > 1:
            variance = sum((x - avg_diff) ** 2 for x in diff_values) / len(diff_values)
            std_diff = variance ** 0.5
        else:
            std_diff = 0
    else:
        avg_diff = 0
        std_diff = 0
    
    if variance_values:
        avg_variance = sum(variance_values) / len(variance_values)
    else:
        avg_variance = 0
    
    # ── Classify noise level ──────────────────────────────────────────────────
    # IMPORTANT: avg_diff (YDIF) measures inter-frame pixel difference, which
    # reflects BOTH scene motion AND noise.  A busy scene (people moving, camera
    # panning) will have high YDIF even if the video is clean.  avg_variance
    # (TOUT — temporal outliers) is a better noise-specific indicator because it
    # counts pixels that change in a way that is inconsistent with their neighbours
    # (i.e. speckle/grain, not smooth motion).
    #
    # TOUT thresholds were previously too conservative (0.06 for moderate) and
    # missed most genuine VHS tape noise.  TOUT > 0.03 (3% of pixels are
    # temporal outliers) is a reliable indicator of tape noise on VHS content,
    # so the classifier now leads on TOUT with lower cut-offs (0.012 / 0.03 /
    # 0.08) and keeps YDIF as a secondary trigger.
    # 'trigger' records which metric crossed the threshold, so the UI can show
    # the right number next to the recommendation (a quiet tape with heavy
    # motion can be classified via YDIF while its TOUT score stays low).
    if avg_variance > 0.08 or avg_diff > 30:
        noise_level = 'heavy'
        noise_desc = 'Heavy noise detected'
        recommendation = 'heavy'
        trigger = 'tout' if avg_variance > 0.08 else 'ydif'
    elif avg_variance > 0.03 or avg_diff > 20:
        noise_level = 'moderate'
        noise_desc = 'Moderate noise detected'
        recommendation = 'moderate'
        trigger = 'tout' if avg_variance > 0.03 else 'ydif'
    elif avg_variance > 0.012 or avg_diff > 12:
        noise_level = 'light'
        noise_desc = 'Light noise detected'
        recommendation = 'moderate'
        trigger = 'tout' if avg_variance > 0.012 else 'ydif'
    else:
        noise_level = 'clean'
        noise_desc = 'Video appears clean'
        recommendation = 'none'
        trigger = 'tout'

    return {
        'noise_level': noise_level,
        'noise_desc': noise_desc,
        'recommendation': recommendation,
        'trigger': trigger,
        'avg_diff': avg_diff,
        'std_diff': std_diff,
        'avg_variance': avg_variance,
        'samples_analyzed': len(diff_values),
        'analyzed': len(diff_values) >= 3,  # require at least 3 good samples
    }

def analyze_halo_level(filepath, sample_frames=8, progress_callback=None):
    """Detect edge halos (sharpening ringing) by measuring luma overshoot.

    Halos from VHS sharpening circuits / capture-card edge enhancement appear
    as bright ghost bands a few pixels to the side of strong vertical edges.
    For each sampled frame this scans luma rows horizontally: at every strong
    edge it compares the pixels just past the bright side (where a halo would
    sit) against the plateau further out.  An edge "has a halo" when the near
    zone overshoots the plateau.  The halo score is the fraction of strong
    edges that overshoot.

    Horizontal-only scanning is deliberate: analog sharpening operates along
    the scanline, and row-wise reads are immune to interlacing comb.
    """
    if not HAS_PIL:
        return {'analyzed': False, 'halo_ratio': 0, 'edges_analyzed': 0,
                'halo_level': 'unknown', 'recommendation': 'none'}

    try:
        cmd = [FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', filepath]
        result = run_hidden(cmd, timeout=30)
        duration = float(result.stdout.strip())
    except:
        duration = 60

    EDGE_THRESH = 40        # min luma gradient to count as a strong edge
    OVERSHOOT_THRESH = 14   # near-zone excess over the plateau = halo

    sample_points = [0.2 + (0.6 * i / (sample_frames - 1)) for i in range(sample_frames)]
    temp_dir = os.environ.get('TEMP', os.path.dirname(filepath))
    total_edges = 0
    halo_edges = 0

    for idx, offset in enumerate(sample_points):
        if progress_callback:
            progress_callback(idx + 1, sample_frames)
        frame_path = os.path.join(temp_dir, f'halo_frame_{os.getpid()}_{idx}.png')
        try:
            cmd = [
                FFMPEG_PATH, '-fflags', '+discardcorrupt',
                '-ss', str(duration * offset), '-i', filepath, '-vframes', '1',
                '-update', '1', '-y', frame_path
            ]
            result = run_hidden(cmd, timeout=30)
            if result.returncode != 0 or not os.path.exists(frame_path):
                continue

            img = Image.open(frame_path).convert('L')
            w, h = img.size
            if w < 64 or h < 64:
                continue
            px = img.load()

            def probe(x, y):
                """Classify the pixel column at (x, y).

                Returns None if there is no strong edge here, or either side's
                far zone is not a settled plateau (busy texture is
                indeterminate and must not vote, otherwise detailed scenes all
                read as haloed).  Returns True only when the edge shows the
                two-sided sharpening signature — bright-side overshoot AND
                dark-side undershoot.  Content that merely has a bright line
                near an edge (straw, blinds, text) rings on one side only.
                """
                grad = px[x + 2, y] - px[x - 2, y]
                if abs(grad) < EDGE_THRESH:
                    return None
                if grad > 0:
                    bright_dir, dark_dir = 1, -1
                else:
                    bright_dir, dark_dir = -1, 1
                b_near = max(px[x + bright_dir * 4, y], px[x + bright_dir * 5, y],
                             px[x + bright_dir * 6, y], px[x + bright_dir * 7, y])
                b_far_vals = [px[x + bright_dir * 11, y], px[x + bright_dir * 12, y],
                              px[x + bright_dir * 13, y], px[x + bright_dir * 14, y]]
                d_near = min(px[x + dark_dir * 4, y], px[x + dark_dir * 5, y],
                             px[x + dark_dir * 6, y], px[x + dark_dir * 7, y])
                d_far_vals = [px[x + dark_dir * 11, y], px[x + dark_dir * 12, y],
                              px[x + dark_dir * 13, y], px[x + dark_dir * 14, y]]
                if max(b_far_vals) - min(b_far_vals) > 20:
                    return None
                if max(d_far_vals) - min(d_far_vals) > 20:
                    return None
                overshoot = b_near - sum(b_far_vals) / 4 >= OVERSHOOT_THRESH
                undershoot = sum(d_far_vals) / 4 - d_near >= OVERSHOOT_THRESH * 0.7
                return overshoot and undershoot

            # Central 75% of rows, every 4th row.  An edge only counts if it
            # persists two rows down (vertical coherence): real halos are
            # continuous lines that track their edge, while overshoot from
            # random texture (foliage, straw, fabric) is incoherent.
            for y in range(h // 8, h * 7 // 8, 4):
                x = 16
                while x < w - 16:
                    here = probe(x, y)
                    if here is None:
                        x += 2
                        continue
                    below = None
                    for dx in (0, -1, 1, -2, 2):
                        below = probe(x + dx, y + 2)
                        if below is not None:
                            break
                    if below is not None:
                        total_edges += 1
                        if here and below:
                            halo_edges += 1
                    x += 10  # skip past this edge
        except Exception:
            pass
        finally:
            try:
                os.remove(frame_path)
            except Exception:
                pass

    if total_edges < 50:
        # Not enough strong edges to judge (flat/dark content)
        return {'analyzed': total_edges > 0, 'halo_ratio': 0,
                'edges_analyzed': total_edges,
                'halo_level': 'clean', 'recommendation': 'none'}

    halo_ratio = halo_edges / total_edges

    # Thresholds are experimental, calibrated against sample captures: a clean
    # modern camcorder file measured ~8%, a real VHS capture ~13%, consumer DV
    # with in-camera sharpening ~17%, and the same camcorder file artificially
    # over-sharpened (unsharp la=1.8) ~21%.
    if halo_ratio > 0.30:
        halo_level = 'strong'
        recommendation = 'strong'
    elif halo_ratio > 0.18:
        halo_level = 'moderate'
        recommendation = 'light'
    elif halo_ratio > 0.10:
        halo_level = 'light'
        recommendation = 'light'
    else:
        halo_level = 'clean'
        recommendation = 'none'

    return {
        'analyzed': True,
        'halo_ratio': halo_ratio,
        'edges_analyzed': total_edges,
        'halo_level': halo_level,
        'recommendation': recommendation,
    }

def analyze_color_bleeding(filepath, sample_frames=10, progress_callback=None):
    """
    Analyze color bleeding (chroma shift) in video.
    Color bleeding appears as horizontal smearing of color, especially red/blue on edges.
    This is common in VHS and composite video due to limited chroma bandwidth.
    
    Method: Compare horizontal vs vertical color gradients - bleeding causes
    horizontal chroma spread that exceeds vertical spread abnormally.
    """
    try:
        cmd = [FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', filepath]
        result = run_hidden(cmd, timeout=30)
        duration = float(result.stdout.strip())
    except:
        duration = 60
    
    # Sample frames from 20% to 80% of video
    sample_points = [0.2 + (0.6 * i / (sample_frames - 1)) for i in range(sample_frames)]
    
    h_chroma_spread = []
    v_chroma_spread = []
    saturation_values = []
    
    for idx, offset in enumerate(sample_points):
        if progress_callback:
            progress_callback(idx + 1, sample_frames)
        
        timestamp = duration * offset
        
        try:
            # Analyze chroma channel characteristics
            # Use signalstats to measure U/V channel variance
            cmd = [
                FFMPEG_PATH, '-ss', str(timestamp), '-i', filepath,
                '-vframes', '1',
                '-vf', 'signalstats=stat=tout+vrep+brng,metadata=mode=print',
                '-f', 'null', '-'
            ]
            result = run_hidden(cmd, timeout=30)
            
            uavg = vavg = 0
            uhigh = vhigh = ulow = vlow = 128
            
            for line in result.stderr.split('\n'):
                if 'UAVG' in line and '=' in line:
                    try: uavg = float(line.split('=')[-1].strip())
                    except: pass
                elif 'VAVG' in line and '=' in line:
                    try: vavg = float(line.split('=')[-1].strip())
                    except: pass
                elif 'UHIGH' in line and '=' in line:
                    try: uhigh = float(line.split('=')[-1].strip())
                    except: pass
                elif 'VHIGH' in line and '=' in line:
                    try: vhigh = float(line.split('=')[-1].strip())
                    except: pass
                elif 'ULOW' in line and '=' in line:
                    try: ulow = float(line.split('=')[-1].strip())
                    except: pass
                elif 'VLOW' in line and '=' in line:
                    try: vlow = float(line.split('=')[-1].strip())
                    except: pass
                elif 'SATAVG' in line and '=' in line:
                    try: saturation_values.append(float(line.split('=')[-1].strip()))
                    except: pass
            
            # Chroma spread = range of U and V channels
            u_spread = uhigh - ulow
            v_spread = vhigh - vlow
            h_chroma_spread.append(u_spread)
            v_chroma_spread.append(v_spread)
            
        except:
            pass
    
    # Calculate averages
    if h_chroma_spread:
        avg_h_spread = sum(h_chroma_spread) / len(h_chroma_spread)
    else:
        avg_h_spread = 0
    
    if v_chroma_spread:
        avg_v_spread = sum(v_chroma_spread) / len(v_chroma_spread)
    else:
        avg_v_spread = 0
    
    if saturation_values:
        avg_saturation = sum(saturation_values) / len(saturation_values)
    else:
        avg_saturation = 0
    
    # Color bleeding typically shows as wide chroma spread (fuzzy color edges)
    # Combined with high saturation = likely bleeding visible
    total_spread = avg_h_spread + avg_v_spread
    
    # Thresholds (experimental - tuned for VHS/composite artifacts)
    # High spread + high saturation = bleeding is visible
    # Low saturation = bleeding less noticeable even if present
    bleeding_score = total_spread * (avg_saturation / 100) if avg_saturation > 0 else total_spread
    
    if bleeding_score > 80 or total_spread > 120:
        bleed_level = 'significant'
        bleed_desc = 'Significant color bleeding detected'
        recommendation = True
    elif bleeding_score > 40 or total_spread > 80:
        bleed_level = 'moderate'
        bleed_desc = 'Moderate color bleeding detected'
        recommendation = True
    elif bleeding_score > 20 or total_spread > 50:
        bleed_level = 'light'
        bleed_desc = 'Light color bleeding may be present'
        recommendation = False
    else:
        bleed_level = 'none'
        bleed_desc = 'No obvious color bleeding detected'
        recommendation = False
    
    return {
        'bleed_level': bleed_level,
        'bleed_desc': bleed_desc,
        'recommendation': recommendation,
        'avg_h_spread': avg_h_spread,
        'avg_v_spread': avg_v_spread,
        'avg_saturation': avg_saturation,
        'bleeding_score': bleeding_score,
        'samples_analyzed': len(h_chroma_spread),
        'analyzed': True
    }

def _resolve_cs_tag(color_matrix, video_format):
    """Return the FFmpeg colorspace tag string for the given matrix + format."""
    if color_matrix == 'bt709':
        return 'bt709'
    elif video_format == 'pal':
        return 'bt470bg'
    else:
        return 'smpte170m'

def _resolve_trc_tag(cs_tag):
    """Return the FFmpeg -color_trc name matching a colorspace tag.

    'bt470bg' is only a valid constant for -colorspace/-color_primaries;
    the corresponding transfer characteristic (5, gamma 2.8) is named
    'gamma28'.  Passing 'bt470bg' to -color_trc makes FFmpeg fail with
    "Undefined constant" and abort the encode.
    """
    return 'gamma28' if cs_tag == 'bt470bg' else cs_tag

def _cs_tag_args(cs_tag):
    """FFmpeg colorspace tagging args for a resolved colorspace tag."""
    return ['-colorspace', cs_tag, '-color_primaries', cs_tag,
            '-color_trc', _resolve_trc_tag(cs_tag)]

def _setparams_filter_str(cs_tag):
    """setparams filter tagging frame-level color properties.

    The y4m pipe from vspipe drops the _Primaries/_Transfer frame props set
    in the .vpy, and with FFmpeg 8 the frame-level values (unknown) override
    the -color_primaries/-color_trc encoder options, leaving the output
    untagged.  setparams stamps the props on each frame so they survive to
    the encoder.  Filter-table names differ from encoder-option names: here
    the PAL transfer is spelled 'bt470bg', not 'gamma28'.
    """
    return (f'setparams=range=tv:colorspace={cs_tag}'
            f':color_primaries={cs_tag}:color_trc={cs_tag}')

def _merge_video_filter(wm_filter_args, cs_tag):
    """Merge the colorspace setparams filter into the watermark filter args.

    FFmpeg allows only one -vf / -filter_complex per stream, so setparams is
    appended to the existing chain (after the watermark, right before the
    encoder) rather than passed as a second filter option.
    """
    setp = _setparams_filter_str(cs_tag)
    if not wm_filter_args:
        return ['-vf', setp]
    flag, graph = wm_filter_args[0], wm_filter_args[1]
    return [flag, f'{graph},{setp}']

def generate_histogram_image(filepath, timestamp=None, color_matrix='bt601', video_format='ntsc'):
    """Generate an RGB Parade image (side-by-side R/G/B waveform columns).

    The parade view is the standard pro levels tool — each color channel gets
    its own waveform column, making per-channel clipping/crush and color casts
    immediately visible.
    """
    try:
        cmd = [FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', filepath]
        result = run_hidden(cmd, timeout=30)
        duration = float(result.stdout.strip())
    except:
        duration = 30

    if timestamp is None:
        timestamp = duration / 2
    temp_dir = os.environ.get('TEMP', os.path.dirname(filepath))
    histogram_path = os.path.join(temp_dir, f'levels_analysis_{os.getpid()}.png')

    _cs = _resolve_cs_tag(color_matrix, video_format)
    try:
        # RGB Parade: display=parade puts each color channel in its own column;
        # components=7 (bitmask plane0|1|2) shows all three channels.
        # Tag the input colorspace so FFmpeg uses the correct matrix for YUV→GBR
        # conversion; without this the scope colours are wrong for BT.601 sources.
        # shuffleplanes reorders GBR storage to RGB so columns read R/G/B left to right.
        cmd = [
            FFMPEG_PATH, '-fflags', '+discardcorrupt',
            '-ss', str(timestamp),
            *_cs_tag_args(_cs),
            '-i', filepath, '-vframes', '1',
            '-vf', 'format=gbrp,shuffleplanes=2:0:1,'
                   'waveform=mode=column:display=parade:intensity=0.4:graticule=green:flags=numbers+dots:components=7,'
                   'scale=640:256',
            '-update', '1', '-y', histogram_path
        ]
        result = run_hidden(cmd, timeout=60)
        if result.returncode == 0 and os.path.exists(histogram_path):
            return histogram_path
        print(f"RGB parade generation failed: {result.stderr[:300]}")
    except Exception as e:
        print(f"RGB parade exception: {e}")
    return None

def generate_vectorscope_image(filepath, timestamp=None, color_matrix='bt601', video_format='ntsc'):
    """Generate vectorscope image."""
    try:
        cmd = [FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', filepath]
        result = run_hidden(cmd, timeout=30)
        duration = float(result.stdout.strip())
    except:
        duration = 30

    if timestamp is None:
        timestamp = duration / 2
    temp_dir = os.environ.get('TEMP', os.path.dirname(filepath))
    vectorscope_path = os.path.join(temp_dir, f'color_analysis_{os.getpid()}.png')

    _cs = _resolve_cs_tag(color_matrix, video_format)
    try:
        cmd = [
            FFMPEG_PATH, '-fflags', '+discardcorrupt',
            '-ss', str(timestamp),
            *_cs_tag_args(_cs),
            '-i', filepath, '-vframes', '1',
            '-vf', 'vectorscope=mode=color4:graticule=green:opacity=0.5:envelope=instant,scale=400:-1',
            '-update', '1', '-y', vectorscope_path
        ]
        result = run_hidden(cmd, timeout=60)
        if result.returncode == 0 and os.path.exists(vectorscope_path):
            return vectorscope_path
        print(f"Vectorscope generation failed: {result.stderr[:300]}")
    except Exception as e:
        print(f"Vectorscope exception: {e}")
    return None

def generate_rgb_histogram(filepath, timestamp=None, color_matrix='bt601', video_format='ntsc'):
    """Generate RGB channel histogram image (like VirtualDub's histogram tool)."""
    try:
        cmd = [FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', filepath]
        result = run_hidden(cmd, timeout=30)
        duration = float(result.stdout.strip())
    except:
        duration = 30

    if timestamp is None:
        timestamp = duration / 2
    temp_dir = os.environ.get('TEMP', os.path.dirname(filepath))
    hist_path = os.path.join(temp_dir, f'rgb_histogram_{os.getpid()}.png')

    _cs = _resolve_cs_tag(color_matrix, video_format)
    try:
        cmd = [
            FFMPEG_PATH, '-fflags', '+discardcorrupt',
            '-ss', str(timestamp),
            *_cs_tag_args(_cs),
            '-i', filepath, '-vframes', '1',
            '-vf', ('histogram=display_mode=stack:levels_mode=logarithmic'
                    ':fgopacity=0.9:bgopacity=0.1,scale=520:-1'),
            '-update', '1', '-y', hist_path
        ]
        result = run_hidden(cmd, timeout=60)
        if result.returncode == 0 and os.path.exists(hist_path):
            return hist_path
        print(f"RGB histogram generation failed: {result.stderr[:300]}")
    except Exception as e:
        print(f"RGB histogram exception: {e}")
    return None

# ============================================================
# Diagnostic Logger  (Feature 5)
# ============================================================

class DiagnosticLogger:
    """Incrementally-written diagnostic log for troubleshooting.

    Written with line buffering (buffering=1) so that a crash mid-process
    still produces a useful partial log.
    """

    def __init__(self, log_path):
        self.log_path = log_path
        self._f = open(log_path, 'w', encoding='utf-8', buffering=1)
        self._start_time = time.time()

    # ── Public helpers ──────────────────────────────────────────────────────

    def section(self, title):
        self._write(f"\n{'='*60}")
        self._write(f" {title}")
        self._write(f"{'='*60}")

    def kv(self, key, value):
        self._write(f"  {key:<32} {value}")

    def raw(self, text):
        for line in str(text).splitlines():
            self._write(f"  {line}")

    def cmd(self, cmd_list):
        self._write(f"  CMD: {' '.join(str(c) for c in cmd_list)}")

    def captured(self, label, stdout, stderr):
        if stdout and stdout.strip():
            self._write(f"  [{label} stdout]")
            for line in stdout.strip().splitlines():
                self._write(f"    {line}")
        if stderr and stderr.strip():
            self._write(f"  [{label} stderr]")
            for line in stderr.strip().splitlines():
                self._write(f"    {line}")

    def exception(self, exc, tb_text=''):
        self._write(f"  EXCEPTION: {exc}")
        if tb_text:
            for line in tb_text.splitlines():
                self._write(f"    {line}")

    def timing(self, label):
        elapsed = time.time() - self._start_time
        self._write(f"  {label}: {elapsed:.1f}s elapsed")

    def close(self, success=True):
        total = time.time() - self._start_time
        self.section("Processing Complete")
        self._write(f"  Status  : {'SUCCESS' if success else 'FAILED'}")
        self._write(f"  Duration: {total:.1f} seconds  ({total/60:.1f} min)")
        self._write(f"  End time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            self._f.close()
        except Exception:
            pass

    # ── Internal ────────────────────────────────────────────────────────────

    def _write(self, text):
        ts = time.strftime('%H:%M:%S')
        try:
            self._f.write(f"[{ts}] {text}\n")
        except Exception:
            pass


def _diag_collect_system_info():
    """Return a dict of OS / hardware info for the diagnostic log."""
    info = {}
    try:
        import platform
        info['os']      = platform.platform()
        info['python']  = platform.python_version()
        info['machine'] = platform.machine()
        info['cpu']     = platform.processor() or 'unknown'
    except Exception:
        pass
    try:
        import ctypes
        ms = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetPhysicallyInstalledSystemMemory(ctypes.byref(ms))
        info['ram_gb'] = f"{ms.value / (1024**2):.1f} GB"
    except Exception:
        info['ram_gb'] = 'unknown'
    return info


# ============================================================
# Script Generation
# ============================================================

def generate_vpy_script(config):
    """Generate VapourSynth script based on configuration."""
    lines = []
    lines.append('# -*- coding: utf-8 -*-')
    lines.append('# ============================================================')
    lines.append('# VapourSynth Restoration Script')
    lines.append(f'# VCG Deinterlacer {VERSION_STRING}')
    lines.append(f'# {AUTHOR_HANDLE}')
    lines.append('# ============================================================')
    lines.append('')
    lines.append('import vapoursynth as vs')
    lines.append('from vapoursynth import core')
    lines.append('')

    # ── Explicit plugin loading (portable mode) ──────────────────────────────
    # VapourSynth R73 portable autoloading is unreliable — the plugins dir
    # is sometimes not found via the portable.vs mechanism.  Load every DLL
    # explicitly so we never depend on autoloading.  Failures are silently
    # ignored (already-loaded plugins, non-VS DLLs like libfftw3-3.dll, etc.).
    # Support both plugins64\ and plugins\ directory names.
    _plugin_dir_candidates = [
        os.path.join(VS_DEPS_DIR, 'plugins64'),
        os.path.join(VS_DEPS_DIR, 'plugins'),
    ]
    plugins64_dir = next((d for d in _plugin_dir_candidates if os.path.isdir(d)), None)
    if plugins64_dir:
        # Use forward slashes — safe on Windows, avoids escape issues in vpy
        p64 = plugins64_dir.replace('\\', '/')
        lines.append('# Explicitly load all plugins from portable _deps (bypass autoloading)')
        lines.append('import os as _vcg_os')
        lines.append(f'_vcg_p = "{p64}"')
        lines.append('for _vcg_dll in sorted(_vcg_os.listdir(_vcg_p)):')
        lines.append('    if _vcg_dll.lower().endswith(".dll"):')
        lines.append('        try:')
        lines.append('            core.std.LoadPlugin(_vcg_os.path.join(_vcg_p, _vcg_dll))')
        lines.append('        except Exception:')
        lines.append('            pass')
        lines.append('')

    # Inject the bundled site-packages path so vspipe's embedded Python can
    # find havsfunc.py, vsutil.py, etc. even if the _pth file is incomplete.
    _site_pkg_dir = os.path.join(VS_DEPS_DIR, 'site-packages').replace('\\', '/')
    lines.append('# Ensure bundled site-packages is on sys.path for havsfunc / vsutil')
    lines.append('import sys as _vcg_sys')
    lines.append(f'_vcg_sp = "{_site_pkg_dir}"')
    lines.append('if _vcg_sp not in _vcg_sys.path:')
    lines.append('    _vcg_sys.path.insert(0, _vcg_sp)')
    lines.append('')
    lines.append('import havsfunc as haf')
    lines.append('')

    # Determine frame rate based on video format
    video_format = config.get('format', 'ntsc')
    if video_format == 'ntsc':
        fpsnum = 30000
        fpsden = 1001
    else:
        fpsnum = 25
        fpsden = 1
    
    # Load source - pass fpsnum/fpsden directly to decoder (like Hybrid does)
    # This forces exact frame rate at the decoder level for proper sync
    filepath = config['input_path'].replace('\\', '\\\\')
    # For AVCHD/HDV sources use ffms2 as primary loader.
    # lsmas relies on container metadata for num_frames; AVCHD files moved out of
    # their BDMV directory structure have corrupt duration metadata (e.g. 26 hours)
    # causing lsmas to think there are millions of frames.  It processes the real
    # frames fine then fails trying to read beyond the file.  ffms2 scans the file
    # physically so it always reports the correct actual frame count.
    _source_class_early = config.get('source_classification', {}).get('source_class', 'sd')
    use_ffms2_first = _source_class_early in ('avchd', 'hdv')
    lines.append('# Load source — tries multiple loaders in order, testing frame 0 each time')
    lines.append('# to catch lazy failures (e.g. lsmas succeeds on open but fails mid-output).')
    lines.append('# AVCHD/HDV files moved out of their BDMV directory have corrupt duration')
    lines.append('# metadata; ffms2 scans the file physically and always gets the right frame count.')
    lines.append('def _try_src(fn):')
    lines.append('    try:')
    lines.append('        c = fn()')
    lines.append('        c.get_frame(0)')
    lines.append('        return c')
    lines.append('    except Exception:')
    lines.append('        return None')
    lines.append('')
    if use_ffms2_first:
        # AVCHD/HDV: ffms2 first (immune to corrupt container duration metadata)
        lines.append(f'clip = (')
        lines.append(f'    _try_src(lambda: core.std.AssumeFPS(core.ffms2.Source(r"{filepath}"), fpsnum={fpsnum}, fpsden={fpsden}))')
        lines.append(f'    or _try_src(lambda: core.lsmas.LWLibavSource(r"{filepath}", stream_index=0, cache=0, fpsnum={fpsnum}, fpsden={fpsden}))')
        lines.append(f'    or _try_src(lambda: core.std.AssumeFPS(core.bs.VideoSource(r"{filepath}"), fpsnum={fpsnum}, fpsden={fpsden}))')
        lines.append(f')')
    else:
        # SD: lsmas first (better performance for normal files)
        lines.append(f'clip = (')
        lines.append(f'    _try_src(lambda: core.lsmas.LWLibavSource(r"{filepath}", stream_index=0, cache=0, fpsnum={fpsnum}, fpsden={fpsden}))')
        lines.append(f'    or _try_src(lambda: core.std.AssumeFPS(core.ffms2.Source(r"{filepath}"), fpsnum={fpsnum}, fpsden={fpsden}))')
        lines.append(f'    or _try_src(lambda: core.std.AssumeFPS(core.bs.VideoSource(r"{filepath}"), fpsnum={fpsnum}, fpsden={fpsden}))')
        lines.append(f')')
    lines.append('if clip is None:')
    lines.append(f'    raise RuntimeError("All source loaders failed for: {filepath}")')
    lines.append('')

    # ── Normalize non-standard pixel formats (10-bit DVD rips etc.) ─────────
    # classify_source() flagged a pix_fmt VFM can't accept (yuv420p10le and
    # friends).  Convert to 8-bit YUV420 immediately, before any other filter,
    # so the rest of the pipeline sees a standard clip.
    if config.get('source_classification', {}).get('needs_pixfmt_conversion'):
        _src_pixfmt = config.get('source_classification', {}).get('pix_fmt', '') or 'unknown'
        lines.append(f'# Source pix_fmt "{_src_pixfmt}" is 10-bit / non-standard — normalize to')
        lines.append('# 8-bit YUV420 before any filtering (VFM requires standard 8-bit YUV)')
        lines.append('clip = core.resize.Bicubic(clip, format=vs.YUV420P8)')
        lines.append('')

    # ── Trim to selected segments (Feature: Trim / Segment Export) ──────────
    # Applied on SOURCE frames, before any processing, so cut material is
    # never deinterlaced/filtered (saves time) and audio (trimmed separately
    # with matching timestamps in _process_single_file) stays in sync.
    trim_ranges = config.get('trim_ranges') or []
    if trim_ranges:
        lines.append('# Trim to selected segments (frame-accurate, source frames)')
        lines.append('# Frame numbers are clamped to the actual clip length in case the')
        lines.append('# container duration over-reported the frame count.')
        lines.append('def _vcg_trim(c, a, b):')
        lines.append('    b = min(b, c.num_frames - 1)')
        lines.append('    a = max(0, min(a, b))')
        lines.append('    return core.std.Trim(c, first=a, last=b)')
        lines.append('_vcg_src = clip')
        splice = ' + '.join(f'_vcg_trim(_vcg_src, {int(s)}, {int(e)})'
                            for s, e in trim_ranges)
        lines.append(f'clip = {splice}')
        lines.append('')

    # Convert to YUV422 if needed (QTGMC requires YUV; RGB needs matrix specified)
    lines.append('# Convert to YUV422 if needed (DV 4:1:1 and RGB not supported by QTGMC directly)')
    lines.append('if clip.format.subsampling_w == 2 and clip.format.subsampling_h == 0:')
    lines.append('    # YUV411 (DV) detected, convert to YUV422')
    lines.append('    clip = core.resize.Spline36(clip, format=vs.YUV422P8)')
    lines.append('elif clip.format.color_family == vs.RGB:')
    lines.append('    # RGB source (e.g. Lagarith RGB, HuffYUV RGB) — must specify matrix for RGB->YUV')
    # matrix_s = OUTPUT matrix (required when converting TO YUV from RGB)
    # "170m" = SMPTE 170M / BT.601 for NTSC;  "470bg" = BT.470BG / BT.601 for PAL
    rgb_matrix = '"470bg"' if config.get('format') == 'pal' else '"170m"'
    lines.append(f'    clip = core.resize.Spline36(clip, format=vs.YUV422P8, matrix_s={rgb_matrix})')
    lines.append('elif clip.format.id not in [vs.YUV420P8, vs.YUV422P8, vs.YUV444P8, vs.YUV420P10, vs.YUV422P10, vs.YUV444P10, vs.GRAY8, vs.GRAY16]:')
    lines.append('    # Convert other unsupported formats to YUV422')
    lines.append('    clip = core.resize.Spline36(clip, format=vs.YUV422P8)')
    lines.append('')

    # ── Lift to 16-bit ────────────────────────────────────────────────────────
    # The whole pipeline (QTGMC, BM3D, colour ops, levels) runs at 16-bit.
    # fmtc.bitdepth dithers back to the codec target depth at the very end.
    # dmode=3 = error diffusion — verified against the installed fmtconv via
    # site-packages/mvsfunc/mvsfunc.py:230 ("else: 3 | 'error_diffusion'").
    lines.append('# Lift to 16-bit so QTGMC/BM3D/colour ops have full precision')
    lines.append('clip = core.fmtc.bitdepth(clip, bits=16)')
    lines.append('')

    # ── Crop ─────────────────────────────────────────────────────────────────
    # Four crop presets (Feature 3).  DV defaults to 'none'; SD defaults to 'bt601'.
    # HD sources (AVCHD/HDV) skip all cropping — set crop_preset to 'none'.
    capture_method = config.get('capture_method', 'sd')
    crop_preset = config.get('crop_preset', 'none' if capture_method == 'dv' else 'bt601')
    source_class = config.get('source_classification', {}).get('source_class', 'sd')
    _is_hd = source_class in ('avchd', 'hdv')
    if _is_hd:
        crop_preset = 'none'

    # SAR metadata is only adjusted for the overscan preset (Option 2).
    # Options:
    #   bt601   — BT.601 Active Picture: 8px L+R, 0 top/bottom (default SD)
    #             NTSC: 704×480   PAL: 704×576
    #   overscan — Full Overscan Clean: 8px L+R, 2px top, 4px bottom
    #             NTSC: 704×474   PAL: 704×570
    #             SAR adjusted so DAR = 4:3:
    #               NTSC 704×474 → SAR 79:88  (display width ≈ 632, 632/474 ≈ 4:3)
    #               PAL  704×570 → SAR 95:88  (display width ≈ 760, 760/570 ≈ 4:3)
    #   manual  — user-defined left/right/top/bottom offsets
    #   none    — no crop (DV default)

    # Vertical (top/bottom) crop is deferred until after deinterlacing: QTGMC/
    # SeparateFields needs each field to have whole chroma rows, so a 4:2:0
    # source must keep its luma height mod 4 — the overscan crop (576−6=570,
    # 480−6=474) violates that and crashed on DVD rips.  After deinterlacing
    # the clip is progressive and any mod-2 height is legal, and cropping
    # there no longer throws away field lines.  Horizontal crop stays here so
    # the whole pipeline works on the narrower frame.
    overscan_sar = False
    deferred_vcrop = []
    if crop_preset == 'bt601':
        lines.append('# Crop to BT.601 Active Picture area (SD capture — removes blanking edges)')
        lines.append('clip = core.std.Crop(clip, left=8, right=8, top=0, bottom=0)')
        lines.append('')
    elif crop_preset == 'overscan':
        if video_format == 'ntsc':
            lines.append('# Full Overscan Clean crop, horizontal part (NTSC → 704×474 after')
            lines.append('# the post-deinterlace vertical crop; SAR 79:88 for 4:3 DAR)')
        else:
            lines.append('# Full Overscan Clean crop, horizontal part (PAL → 704×570 after')
            lines.append('# the post-deinterlace vertical crop; SAR 95:88 for 4:3 DAR)')
        lines.append('clip = core.std.Crop(clip, left=8, right=8)')
        lines.append('')
        deferred_vcrop = [
            '# Full Overscan Clean crop, vertical part (after deinterlacing so',
            '# 4:2:0 field chroma stays intact — luma height 570/474 is not mod 4)',
            'clip = core.std.Crop(clip, top=2, bottom=4)',
            '',
        ]
        overscan_sar = True
    elif crop_preset == 'manual':
        cl = config.get('crop_left', 8)
        cr = config.get('crop_right', 8)
        ct = config.get('crop_top', 0)
        cb_px = config.get('crop_bottom', 0)
        lines.append(f'# Manual crop, horizontal part (left={cl}, right={cr}) — top/bottom')
        lines.append('# applied after deinterlacing so 4:2:0 field chroma stays intact')
        lines.append(f'_vcg_l, _vcg_r = {cl}, {cr}')
        lines.append('if _vcg_l % 2 != 0: _vcg_l += 1  # YUV422: left offset must be even')
        lines.append('if (clip.width  - _vcg_l - _vcg_r) % 2 != 0: _vcg_r += 1')
        lines.append('clip = core.std.Crop(clip, left=_vcg_l, right=_vcg_r)')
        lines.append('')
        deferred_vcrop = [
            f'# Manual crop, vertical part (top={ct}, bottom={cb_px}, deferred from',
            '# before deinterlacing)',
            f'_vcg_t, _vcg_b = {ct}, {cb_px}',
            'if _vcg_t % 2 != 0: _vcg_t += 1  # YUV420: top offset must be even',
            'if (clip.height - _vcg_t - _vcg_b) % 2 != 0: _vcg_b += 1',
            'clip = core.std.Crop(clip, top=_vcg_t, bottom=_vcg_b)',
            '',
        ]
    # crop_preset == 'none': no crop

    # ── Snap height (SeparateFields / QTGMC requirement) ─────────────────────
    # 4:2:0 needs luma height mod 4 (each field must have whole chroma rows);
    # everything else needs mod 2.  Guards odd/nonstandard source heights.
    lines.append('# Snap height for SeparateFields: 4:2:0 needs mod 4, others mod 2')
    lines.append('_vcg_hmod = 4 if clip.format.subsampling_h else 2')
    lines.append('if clip.height % _vcg_hmod:')
    lines.append('    clip = core.std.Crop(clip, bottom=clip.height % _vcg_hmod)')
    lines.append('')

    # ── Deinterlacing / IVTC ─────────────────────────────────────────────────
    field_order = config.get('field_order', 'tff')
    ivtc_mode   = config.get('ivtc_mode', False)

    if field_order == 'progressive':
        lines.append('# Progressive source — deinterlacing skipped')
        lines.append('')
    elif ivtc_mode and capture_method != 'dv':
        # Inverse Telecine via vivtc — restores native progressive frame rate.
        # Guard: DV sources are natively interlaced (not telecined film), so IVTC
        # is never applied to them even if ivtc_mode was somehow set to True.
        order = 1 if field_order == 'tff' else 0
        lines.append('# Inverse Telecine (vivtc) — removing 3:2 / 2:2 pulldown')
        lines.append('# VFM only accepts 8-bit YUV and the clip was lifted to 16-bit above, so')
        lines.append('# field-match on an 8-bit copy and pull the output frames from the 16-bit')
        lines.append('# clip via clip2 (documented VFM usage — no precision loss).')
        lines.append('_vfm8 = core.fmtc.bitdepth(clip, bits=8)')
        lines.append(f'clip = core.vivtc.VFM(_vfm8, order={order}, clip2=clip)')
        if video_format == 'pal':
            # PAL 2:2 has no duplicate frames to remove — VDecimate (cycle=5)
            # would discard every 5th real frame, producing 20fps judder.
            # Field matching alone restores the 25 progressive frames.
            lines.append('# PAL 2:2 — no decimation: there are no duplicate frames to drop')
        else:
            lines.append('clip = core.vivtc.VDecimate(clip)')
        lines.append('')
    else:
        tff = field_order == 'tff'
        lines.append('# QTGMC Deinterlacing')
        lines.append('clip = haf.QTGMC(')
        lines.append('    clip,')
        lines.append(f'    TFF={tff},')
        for key, value in QTGMC_SETTINGS.items():
            lines.append(f'    {key}={value},')
        lines[-1] = lines[-1].rstrip(',')
        lines.append(')')
        lines.append('')

    # ── Deferred vertical crop (overscan / manual presets) ───────────────────
    # The clip is progressive from here on, so any even top/bottom crop is
    # legal for 4:2:0 chroma.
    if deferred_vcrop:
        lines.extend(deferred_vcrop)

    # ── PAR correction for 1440×1080 sources (HDV and anamorphic AVCHD) ──────
    # HDV (MPEG-2) and some AVCHD camcorders (Sony, Panasonic) record 1440×1080
    # with non-square pixels (4:3 PAR).  Must be scaled to 1920×1080 for correct
    # 16:9 display.  Canon and most AVCHD cameras record 1920×1080 square pixels
    # and do not need this step.
    if _is_hd:
        par_needed = config.get('source_classification', {}).get('par_needed', False)
        if par_needed:
            lines.append('# PAR correction: scale 1440x1080 non-square pixels to 1920x1080')
            lines.append('clip = core.resize.Spline36(clip, width=1920, height=1080)')
            lines.append('')

    # ── Y/C Delay correction (Feature 1) ─────────────────────────────────────
    # Per-file horizontal chroma shift: split planes, shift U+V, merge back.
    # The luma (Y) plane is unchanged; only the U and V chroma planes are shifted.
    yc_delay = config.get('yc_delay', 0)
    if yc_delay != 0:
        lines.append(f'# Y/C delay correction — chroma horizontal shift: {yc_delay:+d} px')
        lines.append('_yp = core.std.ShufflePlanes(clip, planes=0, colorfamily=vs.GRAY)')
        lines.append('_up = core.std.ShufflePlanes(clip, planes=1, colorfamily=vs.GRAY)')
        lines.append('_vp = core.std.ShufflePlanes(clip, planes=2, colorfamily=vs.GRAY)')
        lines.append(f'_us = core.resize.Point(_up, src_left={yc_delay})')
        lines.append(f'_vs = core.resize.Point(_vp, src_left={yc_delay})')
        lines.append('clip = core.std.ShufflePlanes([_yp, _us, _vs], planes=[0, 0, 0], colorfamily=vs.YUV)')
        lines.append('')

    # ── Denoising ─────────────────────────────────────────────────────────────
    # BM3D (frequency-domain, best quality for analog tape noise) is tried
    # first, then GPU-accelerated KNLMeansCL, then SMDegrain (havsfunc /
    # MVTools — always bundled) as the final fallback.  The try/except chain
    # lives in the generated .vpy so the same script works on any _deps set.
    noise_level = config.get('noise_level', 'none')
    if noise_level == 'moderate':
        # sigma scaled ×256 for 16-bit input (3×256=768); SMDegrain thSAD also ×256
        lines.append('# Temporal denoising (moderate) — BM3D with SMDegrain fallback (16-bit sigmas)')
        lines.append('try:')
        lines.append('    clip = core.bm3d.BM3D(clip, sigma=[768, 0, 0], radius=1, profile="fast")')
        lines.append('    clip = core.bm3d.BM3D(clip, ref=clip, sigma=[768, 0, 0], radius=1, profile="fast")')
        lines.append('except AttributeError:')
        lines.append('    try:')
        lines.append('        clip = core.knlm.KNLMeansCL(clip, d=1, a=2, s=4, h=1.2, channels="Y")')
        lines.append('    except AttributeError:')
        lines.append('        clip = haf.SMDegrain(clip, tr=1, thSAD=300)  # fallback')
        lines.append('')
    elif noise_level == 'heavy':
        # sigma scaled ×256 for 16-bit input (6×256=1536)
        lines.append('# Temporal denoising (heavy) — BM3D with SMDegrain fallback (16-bit sigmas)')
        lines.append('try:')
        lines.append('    clip = core.bm3d.BM3D(clip, sigma=[1536, 0, 0], radius=2, profile="lc")')
        lines.append('    clip = core.bm3d.BM3D(clip, ref=clip, sigma=[1536, 0, 0], radius=2, profile="lc")')
        lines.append('except AttributeError:')
        lines.append('    try:')
        lines.append('        clip = core.knlm.KNLMeansCL(clip, d=2, a=2, s=4, h=2.0, channels="Y")')
        lines.append('    except AttributeError:')
        lines.append('        clip = haf.SMDegrain(clip, tr=2, thSAD=400)  # fallback')
        lines.append('')

    # ── Dehalo ────────────────────────────────────────────────────────────────
    # The bundled havsfunc removed FineDehalo/DeHalo_alpha (they raise
    # vs.Error pointing to vs-dehalo, which is not bundled), so a faithful
    # self-contained port is emitted into the script instead.  It only needs
    # core std/resize ops, rgvs.Repair (RemoveGrainVS.dll — bundled) and the
    # havsfunc mask utilities that DO still exist (AvsPrewitt,
    # mt_expand_multi, mt_inpand_multi).  Luma-only, like the original.
    dehalo_mode = config.get('dehalo_mode', 'none')
    if dehalo_mode in ('light', 'strong'):
        if dehalo_mode == 'light':
            dh_params = 'rx=2.0, darkstr=0.0, brightstr=0.8'
        else:
            dh_params = 'rx=2.4, darkstr=0.3, brightstr=1.0'
        lines.append(f'# Dehalo ({dehalo_mode}) — FineDehalo port (edge-masked DeHalo_alpha)')
        lines.append('import math as _vcg_math')
        lines.append('def _vcg_fine_dehalo(src, rx=2.0, darkstr=0.0, brightstr=1.0):')
        lines.append('    _m4 = lambda v: max(16, int(_vcg_math.floor(v / 4 + 0.5)) * 4)')
        lines.append('    y = core.std.ShufflePlanes(src, planes=0, colorfamily=vs.GRAY)')
        lines.append('    ox, oy = y.width, y.height')
        lines.append('    # --- DeHalo_alpha: blur-and-repair, masked to halo-prone zones ---')
        lines.append('    halos = core.resize.Bicubic(y, _m4(ox / rx), _m4(oy / rx))')
        lines.append('    halos = core.resize.Bicubic(halos, ox, oy, filter_param_a=1, filter_param_b=0)')
        lines.append("    are  = core.std.Expr([core.std.Maximum(y), core.std.Minimum(y)], 'x y -')")
        lines.append("    ugly = core.std.Expr([core.std.Maximum(halos), core.std.Minimum(halos)], 'x y -')")
        # Expr constants scaled for 16-bit (×256): 255→65535, 50→12800, 256→65536,
        # 512→131072, 80→20480, 48→12288. Ratios (0.001, 0.5) are scale-invariant.
        lines.append("    so   = core.std.Expr([ugly, are], 'y x - y 0.001 + / 65535 * 12800 - y 65536 + 131072 / 0.5 + *')")
        lines.append('    lets = core.std.MaskedMerge(halos, y, so)')
        lines.append('    remove = core.rgvs.Repair(y, lets, 1)')
        lines.append("    them = core.std.Expr([y, remove], f'x y < x x y - {darkstr} * - x x y - {brightstr} * - ?')")
        lines.append('    # --- FineDehalo edge mask: act on strong edges, protect fine detail ---')
        lines.append('    edges  = haf.AvsPrewitt(y)')
        lines.append("    strong = core.std.Expr(edges, 'x 20480 - 12288 / 65535 *')")
        lines.append('    large  = haf.mt_expand_multi(strong, sw=2, sh=2)')
        lines.append("    light  = core.std.Expr(edges, 'x 12800 - 12800 / 65535 *')")
        lines.append("    shrink = haf.mt_expand_multi(light, mode='ellipse', sw=2, sh=2)")
        lines.append("    shrink = core.std.Expr(shrink, 'x 4 *')")
        lines.append("    shrink = haf.mt_inpand_multi(shrink, mode='ellipse', sw=2, sh=2)")
        lines.append('    shrink = core.std.Convolution(shrink, matrix=[1] * 9)')
        lines.append('    shrink = core.std.Convolution(shrink, matrix=[1] * 9)')
        lines.append("    outside = core.std.Expr([large, shrink], 'x y max')")
        lines.append("    outside = core.std.Expr(core.std.Convolution(outside, matrix=[1] * 9), 'x 2 *')")
        lines.append('    y_out = core.std.MaskedMerge(y, them, outside)')
        lines.append('    if src.format.color_family == vs.GRAY:')
        lines.append('        return y_out')
        lines.append('    return core.std.ShufflePlanes([y_out, src, src], planes=[0, 1, 2], colorfamily=vs.YUV)')
        lines.append('')
        lines.append('try:')
        lines.append(f'    clip = _vcg_fine_dehalo(clip, {dh_params})')
        lines.append('except Exception:')
        lines.append('    pass  # dehalo prerequisites unavailable — skipping')
        lines.append('')

    # ── Legacy chroma-shift flag (kept for back-compat) ──────────────────────
    if config.get('chroma_shift', False):
        lines.append('# Chroma shift correction (legacy color-bleeding fix)')
        lines.append('clip = core.resize.Point(clip, src_left=2, src_top=2)')
        lines.append('')

    # ── Dropout removal ───────────────────────────────────────────────────────
    if config.get('dropout_removal', False):
        lines.append('# Dropout removal')
        lines.append('clip = core.rgvs.Clense(clip)')
        lines.append('')

    # ── Color correction ──────────────────────────────────────────────────────
    # chroma neutral in 16-bit YUV = 32768 (vs 128 in 8-bit).
    # u_correction / v_correction arrive from signalstats (0-255 scale) so scale ×256.
    color_corr = config.get('color_correction', 'none')
    if color_corr == 'auto_fix':
        u_corr = config.get('u_correction', 0)
        v_corr = config.get('v_correction', 0)
        u16 = u_corr * 256
        v16 = v_corr * 256
        lines.append('# Auto color cast correction (16-bit: chroma neutral = 32768)')
        lines.append(f'# Shifting U by {u_corr:.1f} → {u16:.0f} and V by {v_corr:.1f} → {v16:.0f} (×256 for 16-bit)')
        u_expr = f"x {u16:.1f} +" if u16 >= 0 else f"x {abs(u16):.1f} -"
        v_expr = f"x {v16:.1f} +" if v16 >= 0 else f"x {abs(v16):.1f} -"
        lines.append(f'clip = core.std.Expr([clip], ["", "{u_expr}", "{v_expr}"])')
        lines.append('')
    elif color_corr == 'auto_fix_boost':
        u_corr = config.get('u_correction', 0)
        v_corr = config.get('v_correction', 0)
        u16 = u_corr * 256
        v16 = v_corr * 256
        lines.append('# Auto color cast correction + saturation boost (16-bit)')
        lines.append(f'# Shifting U by {u16:.0f} and V by {v16:.0f}, then boosting saturation')
        u_expr = f"x {u16:.1f} + 32768 - 1.2 * 32768 +" if u16 >= 0 else f"x {abs(u16):.1f} - 32768 - 1.2 * 32768 +"
        v_expr = f"x {v16:.1f} + 32768 - 1.2 * 32768 +" if v16 >= 0 else f"x {abs(v16):.1f} - 32768 - 1.2 * 32768 +"
        lines.append(f'clip = core.std.Expr([clip], ["", "{u_expr}", "{v_expr}"])')
        lines.append('')
    elif color_corr == 'boost_sat':
        lines.append('# Boost saturation (16-bit chroma neutral = 32768)')
        lines.append('clip = core.std.Expr([clip], ["", "x 32768 - 1.2 * 32768 +", "x 32768 - 1.2 * 32768 +"])')
        lines.append('')
    elif color_corr == 'reduce_sat':
        lines.append('# Reduce saturation (16-bit chroma neutral = 32768)')
        lines.append('clip = core.std.Expr([clip], ["", "x 32768 - 0.8 * 32768 +", "x 32768 - 0.8 * 32768 +"])')
        lines.append('')

    # ── Levels (Y plane only) ─────────────────────────────────────────────────
    # 16-bit limited luma: 16×256=4096 (black), 235×256=60160 (white)
    levels_adj = config.get('levels_adjustment', 'none')
    if levels_adj == 'clamp':
        lines.append('# Clamp luma to legal range (16-235 in 8-bit = 4096-60160 in 16-bit)')
        lines.append('clip = core.std.Levels(clip, min_in=0, max_in=65535, min_out=4096, max_out=60160, planes=[0])')
        lines.append('')
    elif levels_adj == 'stretch':
        lines.append('# Stretch luma to legal range (16-235 in 8-bit = 4096-60160 in 16-bit)')
        lines.append('clip = core.std.Levels(clip, min_in=0, max_in=65535, min_out=4096, max_out=60160, gamma=1.0, planes=[0])')
        lines.append('')

    # ── PAR correction / output sizing ────────────────────────────────────────
    # Overscan preset: preserve exact cropped dimensions; set SAR so player
    # renders the clip at the correct 4:3 display aspect ratio.
    if overscan_sar:
        if video_format == 'ntsc':
            # 704×474, SAR 79:88 → display width = 704×79/88 ≈ 632 → 632/474 ≈ 4:3
            lines.append('# Set pixel aspect ratio for 4:3 DAR (NTSC overscan clean 704×474)')
            lines.append('clip = core.std.SetFrameProps(clip, _SARNum=79, _SARDen=88)')
        else:
            # 704×570, SAR 95:88 → display width = 704×95/88 ≈ 760 → 760/570 ≈ 4:3
            lines.append('# Set pixel aspect ratio for 4:3 DAR (PAL overscan clean 704×570)')
            lines.append('clip = core.std.SetFrameProps(clip, _SARNum=95, _SARDen=88)')
        lines.append('')
    elif config.get('par_correction', True) and crop_preset != 'none':
        if video_format == 'ntsc':
            if config.get('detected_sar', '') == '32:27':
                lines.append('# PAR correction → 854×480 square pixels (16:9 widescreen)')
                lines.append('clip = core.resize.Spline36(clip, width=854, height=480)')
            else:
                lines.append('# PAR correction → 640×480 square pixels')
                lines.append('clip = core.resize.Spline36(clip, width=640, height=480)')
        else:
            if config.get('detected_sar', '') == '64:45':
                lines.append('# PAR correction → 1024×576 square pixels (16:9 widescreen)')
                lines.append('clip = core.resize.Spline36(clip, width=1024, height=576)')
            else:
                lines.append('# PAR correction → 768×576 square pixels')
                lines.append('clip = core.resize.Spline36(clip, width=768, height=576)')
        lines.append('')
    elif not _is_hd and config.get('par_correction', True) and crop_preset == 'none':
        # No crop (DV or explicit none): still correct PAR
        if video_format == 'ntsc':
            if config.get('detected_sar', '') == '32:27':
                lines.append('# PAR correction → 854×480 square pixels (16:9 widescreen, no crop path)')
                lines.append('clip = core.resize.Spline36(clip, width=854, height=480)')
            else:
                lines.append('# PAR correction → 640×480 square pixels (no crop path)')
                lines.append('clip = core.resize.Spline36(clip, width=640, height=480)')
        else:
            if config.get('detected_sar', '') == '64:45':
                lines.append('# PAR correction → 1024×576 square pixels (16:9 widescreen, no crop path)')
                lines.append('clip = core.resize.Spline36(clip, width=1024, height=576)')
            else:
                lines.append('# PAR correction → 768×576 square pixels (no crop path)')
                lines.append('clip = core.resize.Spline36(clip, width=768, height=576)')
        lines.append('')

    # ── nnedi3 upscale (applied last, after PAR correction) ───────────────────
    if config.get('upscale_enabled', False):
        nnedi3_dll = os.path.join(VS_DEPS_DIR, 'plugins64', 'libnnedi3.dll').replace('\\', '/')
        res_str = config.get('upscale_resolution', '960x720' if video_format == 'ntsc' else '1024x768')
        try:
            out_w, out_h = (int(x) for x in res_str.split('x'))
        except ValueError:
            out_w, out_h = (960, 720) if video_format == 'ntsc' else (1024, 768)
        lines.append(f'# nnedi3 upscale → {out_w}×{out_h} (nsize=0, nns=3, rfactor=2)')
        lines.append('if not hasattr(core, "nnedi3"):')
        lines.append(f'    core.std.LoadPlugin(r"{nnedi3_dll}")')
        lines.append('# First pass: double height')
        lines.append('clip = core.nnedi3.nnedi3(clip, field=1, dh=True, nsize=0, nns=3)')
        lines.append('# Rotate 90°, double height again, rotate back')
        lines.append('clip = core.std.Transpose(clip)')
        lines.append('clip = core.nnedi3.nnedi3(clip, field=1, dh=True, nsize=0, nns=3)')
        lines.append('clip = core.std.Transpose(clip)')
        lines.append(f'# Resize to target {out_w}×{out_h}')
        lines.append(f'clip = core.resize.Spline36(clip, width={out_w}, height={out_h})')
        lines.append('')

    # ── Film grain overlay ────────────────────────────────────────────────────
    # Added at final resolution (after any upscale) so the grain stays
    # pixel-fine, and before dithering while the pipeline is still 16-bit.
    # AddGrain normalises `var` to the clip's bit depth internally, so the
    # slider value is passed through unscaled (var ≈ variance in 8-bit units;
    # measured on 16-bit: var=1 → σ≈1.0, var=4 → σ≈2.0).  Skipped silently
    # if the AddGrain plugin is not present in this _deps set.
    grain_strength = float(config.get('grain_strength', 0) or 0)
    if grain_strength > 0:
        lines.append(f'# Film grain overlay (AddGrain, strength/var {grain_strength:g})')
        lines.append('try:')
        lines.append(f'    clip = core.grain.Add(clip, var={grain_strength:.1f}, uvar=0)')
        lines.append('except AttributeError:')
        lines.append('    pass  # grain plugin not available — skipping')
        lines.append('')

    # ── Colorspace / matrix tagging (Feature 2) ──────────────────────────────
    # VS _Matrix values: 1=BT.709, 5=BT.470BG (PAL BT.601), 6=SMPTE170M (NTSC BT.601)
    # VS _ColorRange: 0=full, 1=limited
    color_matrix = config.get('color_matrix', 'bt601')
    if color_matrix == 'bt709':
        _mat, _pri, _trc = 1, 1, 1
    elif video_format == 'pal':
        _mat, _pri, _trc = 5, 5, 5   # BT.470BG
    else:
        _mat, _pri, _trc = 6, 6, 6   # SMPTE 170M (NTSC BT.601)
    lines.append(f'# Tag colorspace — {color_matrix.upper()} (_Matrix={_mat}, limited range)')
    lines.append(f'clip = core.std.SetFrameProps(clip, _Matrix={_mat}, _Primaries={_pri}, _Transfer={_trc}, _ColorRange=1)')
    lines.append('')

    # ── Output dithering (Feature 1) ─────────────────────────────────────────
    # Dither from 16-bit down to the codec's native depth.
    # ProRes → 10-bit (fully populates the container, no free LSBs).
    # All other formats → 8-bit.
    # fmtc dmode=3 = error diffusion (Floyd-Steinberg), verified against
    # installed mvsfunc.py:230. dmode=0 = ordered Bayer (alternative).
    dither_enabled = config.get('dither_enabled', True)
    output_fmt = config.get('output_format', 'prores')
    out_bits = 10 if output_fmt == 'prores' else 8
    dither_method = config.get('dither_method', 'error_diffusion')
    dmode = 3 if dither_method != 'ordered' else 0
    dmode_label = 'error diffusion' if dmode == 3 else 'ordered Bayer'
    if dither_enabled:
        lines.append(f'# Dither 16-bit → {out_bits}-bit ({dmode_label}, fmtc dmode={dmode})')
        lines.append('try:')
        lines.append(f'    clip = core.fmtc.bitdepth(clip, bits={out_bits}, dmode={dmode})')
        lines.append('except Exception:')
        vs_fmt = 'vs.YUV422P10' if out_bits == 10 else 'vs.YUV422P8'
        lines.append(f'    clip = core.resize.Spline36(clip, format={vs_fmt})  # fallback: no dither')
    else:
        vs_fmt = 'vs.YUV422P10' if out_bits == 10 else 'vs.YUV422P8'
        lines.append(f'# Output at {out_bits}-bit (dithering disabled by user)')
        lines.append(f'clip = core.resize.Spline36(clip, format={vs_fmt})')
    lines.append('')

    lines.append('clip.set_output()')
    return '\n'.join(lines)


def get_ffmpeg_output_args(config):
    fmt = config.get('output_format', 'prores')

    # Colorspace tags for the output container — derived from user-selected matrix.
    # FFmpeg flag names: bt601/smpte170m for NTSC BT.601, bt470bg for PAL BT.601
    # (transfer for PAL is 'gamma28' — see _resolve_trc_tag).
    _cs = _resolve_cs_tag(config.get('color_matrix', 'bt601'),
                          config.get('format', 'ntsc'))
    cs_args = _cs_tag_args(_cs)

    if fmt == 'prores':
        # vspipe now outputs 10-bit (dithered by fmtc); -pix_fmt keeps the encoder explicit
        return ['-c:v', 'prores_ks', '-profile:v', '3', '-pix_fmt', 'yuv422p10le'] + cs_args, '.mov'
    elif fmt == 'h264':
        return ['-c:v', 'libx264', '-crf', '18', '-preset', 'slow', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '192k'] + cs_args, '.mp4'
    elif fmt == 'ffv1':
        return ['-c:v', 'ffv1', '-level', '3', '-coder', '1', '-slicecrc', '1'] + cs_args, '.mkv'
    elif fmt == 'huffyuv':
        return ['-c:v', 'huffyuv', '-pix_fmt', 'yuv422p'] + cs_args, '.avi'
    elif fmt == 'utvideo':
        return ['-c:v', 'utvideo', '-pix_fmt', 'yuv422p'] + cs_args, '.avi'
    elif fmt == 'lagarith':
        return ['-c:v', 'lagarith', '-pix_fmt', 'yuv420p'] + cs_args, '.avi'
    return ['-c:v', 'prores_ks', '-profile:v', '3'] + cs_args, '.mov'


def _estimate_output_width(config):
    """Best-effort output frame width, mirroring generate_vpy_script() sizing.

    Used to size a logo watermark as a percentage of frame width — the encode
    input arrives over a pipe, so it cannot be probed.  A small error here is
    only cosmetic (slightly larger/smaller logo).
    """
    if config.get('upscale_enabled', False):
        try:
            return int(str(config.get('upscale_resolution', '')).split('x')[0])
        except (ValueError, IndexError):
            return 960 if config.get('format', 'ntsc') == 'ntsc' else 1024
    source_class = config.get('source_classification', {}).get('source_class', 'sd')
    if source_class in ('avchd', 'hdv'):
        return 1920
    capture_method = config.get('capture_method', 'sd')
    crop_preset = config.get('crop_preset', 'none' if capture_method == 'dv' else 'bt601')
    video_format = config.get('format', 'ntsc')
    if crop_preset == 'overscan':
        return 704
    if config.get('par_correction', True):
        if video_format == 'ntsc':
            return 854 if config.get('detected_sar', '') == '32:27' else 640
        return 1024 if config.get('detected_sar', '') == '64:45' else 768
    return 704 if crop_preset == 'bt601' else 720


def _drawtext_fontfile_arg():
    """Return a "fontfile='...':" prefix for drawtext, or '' if none found.

    The bundled FFmpeg's fontconfig cannot locate a default font on Windows,
    so drawtext silently renders nothing unless given an explicit font file.
    Colons in the path must be escaped for the filter parser.  All candidates
    are sans-serif system fonts.
    """
    fonts_dir = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')
    for fname in ('segoeui.ttf', 'arial.ttf', 'calibri.ttf', 'tahoma.ttf'):
        fpath = os.path.join(fonts_dir, fname)
        if os.path.exists(fpath):
            escaped = fpath.replace('\\', '/').replace(':', '\\:')
            return f"fontfile='{escaped}':"
    return ''


def build_watermark_args(config):
    """Build FFmpeg watermark arguments from config.

    Returns (extra_inputs, filter_args):
      extra_inputs — extra ['-i', <path>] args (logo image, if any)
      filter_args  — ['-vf', <filter>] or ['-filter_complex', <graph>], or []
    """
    wm_type = config.get('wm_type', 'none')
    wm_position = config.get('wm_position', 'bottomright')
    alpha = float(config.get('wm_opacity', 0.6))

    if wm_type == 'text':
        text = str(config.get('wm_text', '') or '').strip()
        if not text:
            return [], []
        # drawtext escaping: backslash, colon and quote are filter specials.
        # % needs \\% — one backslash survives the option parser, the second
        # escapes the % for drawtext's text expander (a bare % is treated as
        # a broken %{...} sequence and kills the whole label).
        text = (text.replace('\\', '\\\\').replace('%', r'\\%')
                    .replace(':', '\\:').replace("'", "\\'"))
        # drawtext positioning: w/W is the INPUT width (unlike overlay), so the
        # text box dimensions are tw/th (text_w/text_h).
        pos_map = {
            'bottomright': 'x=w-tw-20:y=h-th-20',
            'bottomleft':  'x=20:y=h-th-20',
            'topright':    'x=w-tw-20:y=20',
            'topleft':     'x=20:y=20',
            'center':      'x=(w-tw)/2:y=(h-th)/2',
        }
        pos_expr = pos_map.get(wm_position, 'x=w-tw-20:y=h-th-20')
        fsize = int(config.get('wm_fontsize', 28))
        font_arg = _drawtext_fontfile_arg()
        wm_filter = (f"drawtext={font_arg}text='{text}':fontcolor=white@{alpha:.2f}"
                     f":fontsize={fsize}:box=1:boxcolor=black@0.3"
                     f":boxborderw=4:{pos_expr}")
        return [], ['-vf', wm_filter]

    elif wm_type == 'logo':
        logo_path = config.get('wm_logo_path', '')
        if not logo_path or not os.path.exists(logo_path):
            return [], []
        logo_size = float(config.get('wm_logo_size', 0.10))
        pos_map_logo = {
            'bottomright': 'W-w-20:H-h-20',
            'bottomleft':  '20:H-h-20',
            'topright':    'W-w-20:20',
            'topleft':     '20:20',
            'center':      '(W-w)/2:(H-h)/2',
        }
        pos_expr = pos_map_logo.get(wm_position, 'W-w-20:H-h-20')
        # Size the logo as a percentage of the (estimated) output frame width
        logo_px = max(16, int(round(_estimate_output_width(config) * logo_size)))
        wm_filter = (f"[1:v]scale={logo_px}:-1,format=rgba,"
                     f"colorchannelmixer=aa={alpha:.2f}[wm];"
                     f"[0:v][wm]overlay={pos_expr}")
        return ['-i', logo_path], ['-filter_complex', wm_filter]

    return [], []

# ============================================================
# Modern UI Components
# ============================================================

class ModernButton(tk.Canvas):
    """Modern Windows 11 style button."""
    
    def __init__(self, parent, text, command=None, primary=False, width=120, height=36, **kwargs):
        super().__init__(parent, width=width, height=height, 
                        bg=parent.cget('bg'), highlightthickness=0, **kwargs)
        
        self.command = command
        self.primary = primary
        self.text = text
        self.width = width
        self.height = height
        self.hover = False
        self.disabled = False
        
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<Button-1>', self._on_click)
        
        self._draw()
    
    def _draw(self):
        self.delete('all')
        
        if self.disabled:
            bg = Colors.BG_CARD
            fg = Colors.TEXT_DISABLED
        elif self.primary:
            bg = Colors.ACCENT_HOVER if self.hover else Colors.ACCENT
            fg = "#000000"
        else:
            bg = Colors.BG_CARD_HOVER if self.hover else Colors.BG_CARD
            fg = Colors.TEXT_PRIMARY
        
        # Rounded rectangle
        r = 4
        self.create_rounded_rect(2, 2, self.width-2, self.height-2, r, fill=bg, outline=Colors.BORDER_LIGHT)
        
        # Text
        self.create_text(self.width//2, self.height//2, text=self.text, 
                        fill=fg, font=('Segoe UI', 12))
    
    def create_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
            x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
            x1, y2, x1, y2-r, x1, y1+r, x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)
    
    def _on_enter(self, e):
        if not self.disabled:
            self.hover = True
            self._draw()
    
    def _on_leave(self, e):
        self.hover = False
        self._draw()
    
    def _on_click(self, e):
        if not self.disabled and self.command:
            self.command()
    
    def set_disabled(self, disabled):
        self.disabled = disabled
        self._draw()


class ModernRadioButton(tk.Frame):
    """Modern Windows 11 style radio button."""
    
    def __init__(self, parent, text, variable, value, description=None, **kwargs):
        super().__init__(parent, bg=Colors.BG_CARD, **kwargs)
        
        self.variable = variable
        self.value = value
        self.selected = False
        
        # Container with hover effect
        self.container = tk.Frame(self, bg=Colors.BG_CARD, padx=12, pady=10)
        self.container.pack(fill='x')
        
        # Radio circle
        self.canvas = tk.Canvas(self.container, width=20, height=20, 
                               bg=Colors.BG_CARD, highlightthickness=0)
        self.canvas.pack(side='left', padx=(0, 12))
        
        # Text container
        text_frame = tk.Frame(self.container, bg=Colors.BG_CARD)
        text_frame.pack(side='left', fill='x', expand=True)
        
        self.label = tk.Label(text_frame, text=text, 
                             font=('Segoe UI', 12),
                             fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD,
                             anchor='w')
        self.label.pack(fill='x')
        
        if description:
            self.desc_label = tk.Label(text_frame, text=description,
                                       font=('Segoe UI', 12),
                                       fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                                       anchor='w', justify='left', wraplength=600)
            self.desc_label.pack(fill='x')
            # Keep wraplength in sync with the actual widget width so text only
            # wraps when it genuinely runs out of horizontal room.
            self.desc_label.bind('<Configure>',
                                 lambda e: self.desc_label.configure(wraplength=max(100, e.width)))
        
        # Bindings
        for widget in [self, self.container, self.canvas, self.label]:
            widget.bind('<Enter>', self._on_enter)
            widget.bind('<Leave>', self._on_leave)
            widget.bind('<Button-1>', self._on_click)
        
        if description:
            self.desc_label.bind('<Enter>', self._on_enter)
            self.desc_label.bind('<Leave>', self._on_leave)
            self.desc_label.bind('<Button-1>', self._on_click)
        
        self.variable.trace_add('write', self._on_var_change)
        self._draw_radio()
    
    def _draw_radio(self):
        self.canvas.delete('all')
        self.selected = self.variable.get() == self.value
        
        # Outer circle
        if self.selected:
            self.canvas.create_oval(2, 2, 18, 18, outline=Colors.ACCENT, width=2)
            self.canvas.create_oval(6, 6, 14, 14, fill=Colors.ACCENT, outline='')
        else:
            self.canvas.create_oval(2, 2, 18, 18, outline=Colors.TEXT_SECONDARY, width=2)
    
    def _on_enter(self, e):
        self.container.config(bg=Colors.BG_CARD_HOVER)
        self.canvas.config(bg=Colors.BG_CARD_HOVER)
        self.label.config(bg=Colors.BG_CARD_HOVER)
        if hasattr(self, 'desc_label'):
            self.desc_label.config(bg=Colors.BG_CARD_HOVER)
    
    def _on_leave(self, e):
        self.container.config(bg=Colors.BG_CARD)
        self.canvas.config(bg=Colors.BG_CARD)
        self.label.config(bg=Colors.BG_CARD)
        if hasattr(self, 'desc_label'):
            self.desc_label.config(bg=Colors.BG_CARD)
    
    def _on_click(self, e):
        self.variable.set(self.value)
    
    def _on_var_change(self, *args):
        self._draw_radio()


class StepIndicator(tk.Frame):
    """Sidebar step indicator."""
    
    def __init__(self, parent, steps, **kwargs):
        super().__init__(parent, bg=Colors.BG_SIDEBAR, **kwargs)
        
        self.steps = steps
        self.current_step = 0
        self.step_widgets = []
        
        # Title
        title = tk.Label(self, text="VCG\nDEINTERLACER",
                        font=('Segoe UI', 14, 'bold'),
                        fg=Colors.ACCENT, bg=Colors.BG_SIDEBAR,
                        justify='left')
        title.pack(anchor='w', padx=20, pady=(20, 5))
        
        # Version label
        version_label = tk.Label(self, text=VERSION_STRING,
                                font=('Segoe UI', 8),
                                fg=Colors.TEXT_DISABLED, bg=Colors.BG_SIDEBAR,
                                justify='left')
        version_label.pack(anchor='w', padx=20, pady=(0, 25))
        
        # Steps
        for i, step in enumerate(steps):
            step_frame = tk.Frame(self, bg=Colors.BG_SIDEBAR)
            step_frame.pack(fill='x', padx=20, pady=4)
            
            # Number circle
            canvas = tk.Canvas(step_frame, width=28, height=28,
                              bg=Colors.BG_SIDEBAR, highlightthickness=0)
            canvas.pack(side='left', padx=(0, 12))
            
            # Step name
            label = tk.Label(step_frame, text=step,
                           font=('Segoe UI', 12),
                           fg=Colors.TEXT_SECONDARY, bg=Colors.BG_SIDEBAR,
                           anchor='w')
            label.pack(side='left', fill='x')
            
            self.step_widgets.append((canvas, label))
        
        self._update_display()
    
    def set_step(self, step_index):
        self.current_step = step_index
        self._update_display()
    
    def _update_display(self):
        for i, (canvas, label) in enumerate(self.step_widgets):
            canvas.delete('all')
            
            if i < self.current_step:
                # Completed
                canvas.create_oval(2, 2, 26, 26, fill=Colors.SUCCESS, outline='')
                canvas.create_text(14, 14, text="✓", fill='white', font=('Segoe UI', 12, 'bold'))
                label.config(fg=Colors.TEXT_PRIMARY)
            elif i == self.current_step:
                # Current
                canvas.create_oval(2, 2, 26, 26, fill=Colors.ACCENT, outline='')
                canvas.create_text(14, 14, text=str(i+1), fill='black', font=('Segoe UI', 10, 'bold'))
                label.config(fg=Colors.TEXT_PRIMARY, font=('Segoe UI', 10, 'bold'))
            else:
                # Upcoming
                canvas.create_oval(2, 2, 26, 26, outline=Colors.TEXT_DISABLED, width=2)
                canvas.create_text(14, 14, text=str(i+1), fill=Colors.TEXT_DISABLED, font=('Segoe UI', 12))
                label.config(fg=Colors.TEXT_DISABLED, font=('Segoe UI', 12))


class SidebarNav(tk.Frame):
    """Vertical wizard-navigation sidebar with grouped steps and sub-steps.

    `groups` is a list of (label, [step_indices]) tuples covering the wizard's
    step ids; a group spanning several steps expands to one row per sub-step
    while the current step is inside it.  Steps the user has already reached
    are clickable (reported via `on_navigate`); steps in `disabled` are hidden
    entirely (e.g. Trim during batch jobs).  Group labels listed in
    `optional_groups` get an "optional" tag and a skip hint.

    Call set_state(current, visited, disabled) to refresh the visual state.
    """

    WIDTH  = 218     # fixed sidebar width in px
    PILL_D = 24      # group pill diameter

    def __init__(self, parent, steps, groups, on_navigate=None,
                 optional_groups=(), **kwargs):
        super().__init__(parent, bg=Colors.BG_SIDEBAR, width=self.WIDTH, **kwargs)
        self.pack_propagate(False)
        self.steps           = steps
        self.groups          = groups
        self.on_navigate     = on_navigate
        self.optional_groups = set(optional_groups)
        self.current_step    = 0
        self.visited         = set()
        self.disabled        = set()

    def set_state(self, current_step, visited, disabled=()):
        self.current_step = current_step
        self.visited      = set(visited)
        self.disabled     = set(disabled)
        self._redraw()

    def _reachable(self, step):
        """A step is clickable once the user has progressed at least that far."""
        max_reached = max(self.visited) if self.visited else 0
        return step not in self.disabled and 1 <= step <= max_reached

    def _make_clickable(self, widgets, target):
        def _go(_e):
            if self.on_navigate:
                self.on_navigate(target)
        def _hover(bg):
            def _h(_e):
                for w in widgets:
                    if w.winfo_exists():
                        w.config(bg=bg)
            return _h
        for w in widgets:
            w.config(cursor='hand2')
            w.bind('<Button-1>', _go)
            w.bind('<Enter>', _hover(Colors.BG_CARD))
            w.bind('<Leave>', _hover(Colors.BG_SIDEBAR))

    def _redraw(self):
        for w in self.winfo_children():
            w.destroy()

        tk.Label(self, text="WORKFLOW", font=('Segoe UI', 9, 'bold'),
                 fg=Colors.TEXT_HINT, bg=Colors.BG_SIDEBAR
                 ).pack(anchor='w', padx=20, pady=(20, 10))

        in_optional = False
        for group_i, (label, step_indices) in enumerate(self.groups):
            group_num = group_i + 1
            is_active = self.current_step in step_indices
            is_past   = all(s < self.current_step for s in step_indices)
            was_seen  = any(s in self.visited for s in step_indices)
            optional  = label in self.optional_groups
            if is_active and optional:
                in_optional = True

            row = tk.Frame(self, bg=Colors.BG_SIDEBAR)
            row.pack(fill='x', pady=1)

            # ── pill ───────────────────────────────────────────────────
            d = self.PILL_D
            pill = tk.Canvas(row, width=d + 2, height=d + 2,
                             bg=Colors.BG_SIDEBAR, highlightthickness=0)
            pill.pack(side='left', padx=(16, 8), pady=4)
            cx = cy = (d + 2) // 2
            if is_active:
                pill.create_oval(2, 2, d, d, fill=Colors.ACCENT, outline='')
                pill.create_text(cx, cy, text=str(group_num),
                                 fill='black', font=('Segoe UI', 9, 'bold'))
            elif is_past and was_seen:
                pill.create_oval(2, 2, d, d, fill=Colors.SUCCESS, outline='')
                pill.create_text(cx, cy, text='✓',
                                 fill='white', font=('Segoe UI', 10, 'bold'))
            elif is_past:
                # Passed without visiting → skipped, defaults in effect
                pill.create_oval(2, 2, d, d, outline=Colors.TEXT_DISABLED, width=2)
                pill.create_text(cx, cy, text='–',
                                 fill=Colors.TEXT_SECONDARY, font=('Segoe UI', 10))
            else:
                pill.create_oval(2, 2, d, d, outline=Colors.TEXT_DISABLED, width=2)
                pill.create_text(cx, cy, text=str(group_num),
                                 fill=Colors.TEXT_DISABLED, font=('Segoe UI', 9))

            # ── label + optional tag ───────────────────────────────────
            lbl_color = (Colors.TEXT_PRIMARY if (is_active or is_past)
                         else Colors.TEXT_DISABLED)
            lbl_font  = ('Segoe UI', 11, 'bold') if is_active else ('Segoe UI', 11)
            lbl = tk.Label(row, text=label, font=lbl_font,
                           fg=lbl_color, bg=Colors.BG_SIDEBAR, anchor='w')
            lbl.pack(side='left', fill='x', expand=True)
            group_widgets = [row, pill, lbl]
            if optional:
                tag = tk.Label(row, text='optional', font=('Segoe UI', 8),
                               fg=Colors.TEXT_HINT, bg=Colors.BG_SIDEBAR)
                tag.pack(side='right', padx=(0, 14))
                group_widgets.append(tag)

            # Click → first reachable step in the group
            target = next((s for s in step_indices if self._reachable(s)), None)
            if target is not None and not is_active:
                self._make_clickable(group_widgets, target)

            visible_subs = [s for s in step_indices if s not in self.disabled]
            if is_active and len(step_indices) > 1:
                # ── expanded sub-steps ─────────────────────────────────
                for s in visible_subs:
                    self._sub_row(s)
            elif optional and len(visible_subs) > 1:
                # Collapsed summary so users know what the group contains
                tk.Label(self, text=f"{len(visible_subs)} optional steps",
                         font=('Segoe UI', 9), fg=Colors.TEXT_HINT,
                         bg=Colors.BG_SIDEBAR).pack(anchor='w', padx=(50, 0))

        if in_optional:
            tk.Label(self,
                     text="These steps are all optional.\n"
                          "Use Next to move through them,\n"
                          "or click a step to revisit it.",
                     font=('Segoe UI', 9), fg=Colors.TEXT_HINT,
                     bg=Colors.BG_SIDEBAR, justify='left'
                     ).pack(side='bottom', anchor='w', padx=20, pady=16)

    def _sub_row(self, step):
        cur  = (step == self.current_step)
        seen = step in self.visited
        if cur:
            icon, icon_fg = '▶', Colors.ACCENT
        elif seen:
            icon, icon_fg = '✓', Colors.SUCCESS
        else:
            icon, icon_fg = '○', Colors.TEXT_DISABLED

        row = tk.Frame(self, bg=Colors.BG_SIDEBAR)
        row.pack(fill='x')
        # Accent bar marks the current sub-step
        bar = tk.Frame(row, width=3,
                       bg=(Colors.ACCENT if cur else Colors.BG_SIDEBAR))
        bar.pack(side='left', fill='y')
        ic = tk.Label(row, text=icon, font=('Segoe UI', 9), fg=icon_fg,
                      bg=Colors.BG_SIDEBAR, width=2)
        ic.pack(side='left', padx=(31, 2), pady=1)
        name_fg = (Colors.TEXT_PRIMARY if cur
                   else Colors.TEXT_SECONDARY if seen
                   else Colors.TEXT_DISABLED)
        name_font = ('Segoe UI', 10, 'bold') if cur else ('Segoe UI', 10)
        lbl = tk.Label(row, text=self.steps[step], font=name_font,
                       fg=name_fg, bg=Colors.BG_SIDEBAR, anchor='w')
        lbl.pack(side='left', fill='x', expand=True)
        if not cur and self._reachable(step):
            self._make_clickable([row, ic, lbl], step)


class ProgressBar(tk.Canvas):
    """Modern progress bar."""
    
    def __init__(self, parent, width=400, height=6, **kwargs):
        super().__init__(parent, width=width, height=height,
                        bg=Colors.BG_MAIN, highlightthickness=0, **kwargs)
        self.progress_width = width
        self.progress = 0
        self._draw()
    
    def _draw(self):
        self.delete('all')
        # Background
        self.create_rounded_rect(0, 0, self.progress_width, 6, 3, fill=Colors.BG_CARD)
        # Progress
        if self.progress > 0:
            w = int(self.progress_width * self.progress)
            if w > 6:
                self.create_rounded_rect(0, 0, w, 6, 3, fill=Colors.ACCENT)
    
    def create_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y2-r, x2, y2, x2-r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y1+r, x1, y1]
        return self.create_polygon(points, smooth=True, **kwargs)
    
    def set_progress(self, value):
        self.progress = max(0, min(1, value))
        self._draw()


class TipsBox(tk.Frame):
    """Tips and tricks display box with Next button and auto-rotate."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=Colors.BG_CARD, **kwargs)
        
        self.tips = TIPS.copy()
        self.current_tip_index = 0
        self.auto_rotate_id = None
        import random
        random.shuffle(self.tips)
        
        self.config(padx=15, pady=12)
        
        # Header with lightbulb icon
        header_frame = tk.Frame(self, bg=Colors.BG_CARD)
        header_frame.pack(fill='x', pady=(0, 8))
        
        tk.Label(header_frame, text="💡",
                font=('Segoe UI', 14),
                fg=Colors.ACCENT, bg=Colors.BG_CARD).pack(side='left')
        
        tk.Label(header_frame, text="Learn While You Wait",
                font=('Segoe UI', 11, 'bold'),
                fg=Colors.ACCENT, bg=Colors.BG_CARD).pack(side='left', padx=(8, 0))
        
        # Tip title
        self.title_label = tk.Label(self, text="",
                                   font=('Segoe UI', 10, 'bold'),
                                   fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD,
                                   anchor='w', wraplength=540, justify='left')
        self.title_label.pack(fill='x', pady=(0, 5))
        
        # Tip content
        self.content_label = tk.Label(self, text="",
                                     font=('Segoe UI', 12),
                                     fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                                     anchor='w', wraplength=540, justify='left')
        self.content_label.pack(fill='x')
        
        # Separator
        ttk.Separator(self, orient='horizontal').pack(fill='x', pady=(12, 8))
        
        # Promo text
        self.promo_label = tk.Label(self, text=TIP_PROMO,
                                   font=('Segoe UI', 8),
                                   fg=Colors.TEXT_DISABLED, bg=Colors.BG_CARD,
                                   anchor='w', wraplength=540, justify='left')
        self.promo_label.pack(fill='x')
        
        # Next button
        btn_frame = tk.Frame(self, bg=Colors.BG_CARD)
        btn_frame.pack(fill='x', pady=(10, 0))
        
        self.next_btn = tk.Label(btn_frame, text="Next Tip →",
                                font=('Segoe UI', 9, 'underline'),
                                fg=Colors.ACCENT, bg=Colors.BG_CARD,
                                cursor='hand2')
        self.next_btn.pack(side='right')
        self.next_btn.bind('<Button-1>', lambda e: self.show_next_tip())
        self.next_btn.bind('<Enter>', lambda e: self.next_btn.config(fg=Colors.TEXT_PRIMARY))
        self.next_btn.bind('<Leave>', lambda e: self.next_btn.config(fg=Colors.ACCENT))
        
        # Tip counter
        self.counter_label = tk.Label(btn_frame, text="",
                                     font=('Segoe UI', 8),
                                     fg=Colors.TEXT_DISABLED, bg=Colors.BG_CARD)
        self.counter_label.pack(side='left')
        
        # Show first tip
        self.show_tip(0)
        
        # Start auto-rotate
        self._start_auto_rotate()
    
    def _start_auto_rotate(self):
        """Start the auto-rotate timer."""
        self._cancel_auto_rotate()
        self.auto_rotate_id = self.after(20000, self._auto_rotate_tip)  # 20 seconds
    
    def _cancel_auto_rotate(self):
        """Cancel any pending auto-rotate."""
        if self.auto_rotate_id:
            self.after_cancel(self.auto_rotate_id)
            self.auto_rotate_id = None
    
    def _auto_rotate_tip(self):
        """Auto-rotate to next tip."""
        if self.winfo_exists():
            self.show_next_tip()
            self._start_auto_rotate()
    
    def show_tip(self, index):
        """Display a specific tip."""
        if 0 <= index < len(self.tips):
            self.current_tip_index = index
            title, content = self.tips[index]
            self.title_label.config(text=title)
            self.content_label.config(text=content)
            self.counter_label.config(text=f"Tip {index + 1} of {len(self.tips)}")
    
    def show_next_tip(self):
        """Show the next tip in the list."""
        next_index = (self.current_tip_index + 1) % len(self.tips)
        self.show_tip(next_index)
        # Reset auto-rotate timer when manually advancing
        self._start_auto_rotate()
    
    def destroy(self):
        """Clean up on destroy."""
        self._cancel_auto_rotate()
        super().destroy()


class ImagePreview(tk.Frame):
    """Image preview widget that displays images inline."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=Colors.BG_CARD, **kwargs)
        
        self.image_label = tk.Label(self, bg=Colors.BG_CARD)
        self.image_label.pack(padx=10, pady=10)
        
        self.current_image = None
        self.photo_image = None
        
        # Show loading message initially
        self.image_label.config(
            text="⏳ Generating preview...",
            fg=Colors.TEXT_SECONDARY,
            font=('Segoe UI', 12)
        )
    
    def load_image(self, filepath, max_width=500, max_height=180):
        """Load and display an image, scaled to fit."""
        if not HAS_PIL:
            self.image_label.config(
                text="Image preview requires Pillow.\nInstall with: pip install Pillow",
                fg=Colors.TEXT_SECONDARY,
                font=('Segoe UI', 12)
            )
            return False
        
        if not filepath:
            self.image_label.config(
                text="❌ Could not generate preview image",
                fg=Colors.ERROR,
                font=('Segoe UI', 12)
            )
            return False
        
        if not os.path.exists(filepath):
            self.image_label.config(
                text=f"❌ Image file not found",
                fg=Colors.ERROR,
                font=('Segoe UI', 12)
            )
            return False
        
        try:
            img = Image.open(filepath)
            
            # Scale to fit
            ratio = min(max_width / img.width, max_height / img.height)
            if ratio < 1:
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            self.photo_image = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.photo_image, text='')
            self.current_image = filepath
            return True
        except Exception as e:
            self.image_label.config(
                text=f"❌ Error loading image: {str(e)[:50]}",
                fg=Colors.ERROR,
                font=('Segoe UI', 12)
            )
            return False
    
    def clear(self):
        """Clear the image display."""
        self.image_label.config(image='', text='')
        self.photo_image = None
        self.current_image = None


class DropZone(tk.Frame):
    """Drag and drop zone for files."""
    
    def __init__(self, parent, on_drop, **kwargs):
        super().__init__(parent, bg=Colors.BG_CARD, **kwargs)
        
        self.on_drop = on_drop
        self.config(padx=30, pady=30)
        
        # Icon
        self.icon_label = tk.Label(self, text="📁", font=('Segoe UI', 32),
                             fg=Colors.ACCENT, bg=Colors.BG_CARD)
        self.icon_label.pack(pady=(0, 10))
        
        # Text
        if HAS_DND:
            drop_text = "Drag and drop a video file here\nor click Browse to select"
        else:
            drop_text = "Click Browse to select a video file"
        
        self.text_label = tk.Label(self, 
                                   text=drop_text,
                                   font=('Segoe UI', 12),
                                   fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                                   justify='center')
        self.text_label.pack()
        
        # Setup drag and drop if available
        if HAS_DND:
            self._setup_dnd()
    
    def _setup_dnd(self):
        """Setup drag and drop using tkinterdnd2."""
        try:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self._on_dnd_drop)
            self.dnd_bind('<<DragEnter>>', self._on_drag_enter)
            self.dnd_bind('<<DragLeave>>', self._on_drag_leave)
        except Exception as e:
            pass  # DnD not available for this widget
    
    def _on_dnd_drop(self, event):
        """Handle file drop."""
        filepath = event.data
        # Clean up the path (tkdnd adds braces around paths with spaces)
        if filepath.startswith('{') and filepath.endswith('}'):
            filepath = filepath[1:-1]
        # Handle multiple files - just take the first one
        if '\n' in filepath:
            filepath = filepath.split('\n')[0]
        if filepath.lower().endswith(('.avi', '.mp4', '.mkv', '.mov', '.m4v', '.mpg', '.mpeg',
                                       '.mts', '.m2ts', '.m2t', '.ts', '.mod')):
            self.on_drop(filepath)
        self._on_drag_leave(None)
    
    def _on_drag_enter(self, event):
        """Highlight when dragging over."""
        self.config(bg=Colors.BG_CARD_HOVER)
        self.icon_label.config(bg=Colors.BG_CARD_HOVER)
        self.text_label.config(bg=Colors.BG_CARD_HOVER)
    
    def _on_drag_leave(self, event):
        """Remove highlight."""
        self.config(bg=Colors.BG_CARD)
        self.icon_label.config(bg=Colors.BG_CARD)
        self.text_label.config(bg=Colors.BG_CARD)
    
    def set_file(self, filepath):
        """Update display to show selected file."""
        filename = os.path.basename(filepath)
        self.icon_label.config(text="✓", fg=Colors.SUCCESS)
        self.text_label.config(text=filename, fg=Colors.TEXT_PRIMARY)


class MultiFileDropZone(tk.Frame):
    """Drag and drop zone for multiple files with file list display."""
    
    def __init__(self, parent, on_files_changed, **kwargs):
        super().__init__(parent, bg=Colors.BG_CARD, **kwargs)
        
        self.on_files_changed = on_files_changed
        self.files = []
        
        # Top section - drop zone (tall, easy target)
        self.drop_frame = tk.Frame(self, bg=Colors.BG_CARD, padx=20, pady=30)
        self.drop_frame.pack(fill='x')

        # Big video icon + VIDEO label
        icon_col = tk.Frame(self.drop_frame, bg=Colors.BG_CARD)
        icon_col.pack()

        self.icon_label = tk.Label(icon_col, text="🎬",
                                   font=('Segoe UI', 44),
                                   fg=Colors.ACCENT, bg=Colors.BG_CARD)
        self.icon_label.pack()

        tk.Label(icon_col, text="VIDEO",
                 font=('Segoe UI', 10, 'bold'),
                 fg=Colors.ACCENT, bg=Colors.BG_CARD).pack()

        if HAS_DND:
            drop_text = "Drag and drop video files here\nor click Browse to select multiple files"
        else:
            drop_text = "Click Browse to select video files"

        self.text_label = tk.Label(self.drop_frame, text=drop_text,
                                   font=('Segoe UI', 13),
                                   fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                                   justify='center')
        self.text_label.pack(pady=(12, 0))

        # Stub top_row for compatibility
        top_row = tk.Frame(self.drop_frame, bg=Colors.BG_CARD)
        
        # File list section (hidden until files added)
        self.list_frame = tk.Frame(self, bg=Colors.BG_MAIN)
        
        # List header
        self.header_frame = tk.Frame(self.list_frame, bg=Colors.BG_MAIN)
        self.header_frame.pack(fill='x', pady=(0, 5))
        
        self.count_label = tk.Label(self.header_frame, text="0 files selected",
                                    font=('Segoe UI', 10, 'bold'),
                                    fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN)
        self.count_label.pack(side='left')
        
        self.clear_btn = tk.Label(self.header_frame, text="Clear all",
                                  font=('Segoe UI', 9, 'underline'),
                                  fg=Colors.ACCENT, bg=Colors.BG_MAIN, cursor='hand2')
        self.clear_btn.pack(side='right')
        self.clear_btn.bind('<Button-1>', lambda e: self.clear_files())
        
        # Scrollable file list
        self.list_container = tk.Frame(self.list_frame, bg=Colors.BG_CARD)
        self.list_container.pack(fill='both', expand=True)
        
        # Canvas for scrolling
        self.canvas = tk.Canvas(self.list_container, bg=Colors.BG_CARD, 
                               highlightthickness=0, height=150)
        self.scrollbar = ttk.Scrollbar(self.list_container, orient='vertical', 
                                       command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=Colors.BG_CARD)
        
        self.scrollable_frame.bind('<Configure>', 
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        
        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw')
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side='left', fill='both', expand=True)
        self.scrollbar.pack(side='right', fill='y')
        
        # Bind canvas resize to update scrollable frame width
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Setup drag and drop if available
        if HAS_DND:
            self._setup_dnd()
    
    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_frame, width=event.width)
    
    def _setup_dnd(self):
        """Setup drag and drop using tkinterdnd2."""
        try:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind('<<Drop>>', self._on_dnd_drop)
            self.drop_frame.dnd_bind('<<DragEnter>>', self._on_drag_enter)
            self.drop_frame.dnd_bind('<<DragLeave>>', self._on_drag_leave)
        except Exception as e:
            pass
    
    def _on_dnd_drop(self, event):
        """Handle file drop - supports multiple files."""
        data = event.data
        
        # Parse dropped files (handles various formats)
        filepaths = []
        if '{' in data:
            # Multiple files with spaces are wrapped in braces
            import re
            matches = re.findall(r'\{([^}]+)\}|(\S+)', data)
            for match in matches:
                path = match[0] if match[0] else match[1]
                if path:
                    filepaths.append(path)
        else:
            filepaths = data.split()
        
        # Filter to video files only
        valid_extensions = ('.avi', '.mp4', '.mkv', '.mov', '.m4v', '.mpg', '.mpeg',
                             '.mts', '.m2ts', '.m2t', '.ts', '.mod')
        for filepath in filepaths:
            if filepath.lower().endswith(valid_extensions):
                if filepath not in self.files:
                    self.files.append(filepath)
        
        self._update_display()
        self._on_drag_leave(None)
        self.on_files_changed(self.files)
    
    def _on_drag_enter(self, event):
        self.drop_frame.config(bg=Colors.BG_CARD_HOVER)
        self.icon_label.config(bg=Colors.BG_CARD_HOVER)
        self.text_label.config(bg=Colors.BG_CARD_HOVER)
    
    def _on_drag_leave(self, event):
        self.drop_frame.config(bg=Colors.BG_CARD)
        self.icon_label.config(bg=Colors.BG_CARD)
        self.text_label.config(bg=Colors.BG_CARD)
    
    def add_files(self, filepaths):
        """Add files from browse dialog."""
        for filepath in filepaths:
            if filepath not in self.files:
                self.files.append(filepath)
        self._update_display()
        self.on_files_changed(self.files)
    
    def remove_file(self, filepath):
        """Remove a file from the list."""
        if filepath in self.files:
            self.files.remove(filepath)
        self._update_display()
        self.on_files_changed(self.files)
    
    def clear_files(self):
        """Clear all files."""
        self.files = []
        self._update_display()
        self.on_files_changed(self.files)
    
    def _update_display(self):
        """Update the file list display."""
        # Clear existing items
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        if not self.files:
            self.list_frame.pack_forget()
            self.icon_label.config(text="🎬", fg=Colors.ACCENT)
            if HAS_DND:
                self.text_label.config(text="Drag and drop video files here\nor click Browse to select multiple files")
            else:
                self.text_label.config(text="Click Browse to select video files")
            return
        
        # Show list frame
        self.list_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Update header
        count = len(self.files)
        self.count_label.config(text=f"{count} file{'s' if count != 1 else ''} selected")
        
        # Update drop zone text
        self.icon_label.config(text="✓", fg=Colors.SUCCESS)
        self.text_label.config(text=f"{count} file{'s' if count != 1 else ''} ready\nDrop more to add")
        
        # Add file items
        for i, filepath in enumerate(self.files):
            self._create_file_item(filepath, i)
    
    def _create_file_item(self, filepath, index):
        """Create a file list item."""
        item = tk.Frame(self.scrollable_frame, bg=Colors.BG_CARD)
        item.pack(fill='x', padx=5, pady=2)
        
        # Alternating background
        bg_color = Colors.BG_CARD if index % 2 == 0 else Colors.BG_MAIN
        item.config(bg=bg_color)
        
        # File icon
        icon = tk.Label(item, text="🎬", font=('Segoe UI', 12),
                       fg=Colors.TEXT_SECONDARY, bg=bg_color)
        icon.pack(side='left', padx=(10, 5), pady=5)
        
        # Filename
        filename = os.path.basename(filepath)
        name_label = tk.Label(item, text=filename, font=('Segoe UI', 12),
                             fg=Colors.TEXT_PRIMARY, bg=bg_color, anchor='w')
        name_label.pack(side='left', fill='x', expand=True, pady=5)
        
        # Get video info
        info = get_video_info(filepath)
        if info:
            duration_str = f"{int(info['duration']//60)}:{int(info['duration']%60):02d}"
            info_text = f"{info['width']}×{info['height']} • {duration_str}"
            info_label = tk.Label(item, text=info_text, font=('Segoe UI', 8),
                                 fg=Colors.TEXT_SECONDARY, bg=bg_color)
            info_label.pack(side='left', padx=10, pady=5)
        
        # Remove button
        remove_btn = tk.Label(item, text="✕", font=('Segoe UI', 12),
                             fg=Colors.TEXT_SECONDARY, bg=bg_color, cursor='hand2')
        remove_btn.pack(side='right', padx=10, pady=5)
        remove_btn.bind('<Button-1>', lambda e, f=filepath: self.remove_file(f))
        remove_btn.bind('<Enter>', lambda e, l=remove_btn: l.config(fg=Colors.ERROR))
        remove_btn.bind('<Leave>', lambda e, l=remove_btn, bg=bg_color: l.config(fg=Colors.TEXT_SECONDARY))


# ============================================================
# Main Application
# ============================================================

# Use TkinterDnD.Tk as base class if available for drag-and-drop support
if HAS_DND:
    BaseWindow = TkinterDnD.Tk
else:
    BaseWindow = tk.Tk


# ============================================================
# Artifact Example Images (synthetic, for UI education)
# ============================================================

def _draw_audio_channels_example():
    """Create a PIL Image showing BEFORE (mono: one waveform + flat) vs AFTER (stereo: both channels have waveforms)."""
    if not HAS_PIL:
        return None
    try:
        from PIL import Image, ImageDraw
        import math
        W, H = 560, 160
        BG = '#1A1A1A'
        TRACK_BG = '#111111'
        LABEL_BG = '#0D0D0D'
        WAVE_BEFORE = '#5DBB6B'   # green waveform on active channel
        FLAT_LINE = '#444444'     # flat (silent) line
        WAVE_AFTER = '#7C6FF7'    # purple waveforms on both channels after mixing
        DIVIDER = '#444444'
        HEADER_BG = '#111111'

        img = Image.new('RGB', (W, H), BG)
        draw = ImageDraw.Draw(img)

        half = W // 2
        # Vertical divider
        draw.rectangle([half-1, 0, half+1, H], fill=DIVIDER)

        # ── Headers ──────────────────────────────────────────────────────────
        draw.rectangle([0, 0, half-2, 22], fill=LABEL_BG)
        draw.text((6, 4), "BEFORE  (mono — one channel)", fill='#EF5350')
        draw.rectangle([half+2, 0, W, 22], fill=LABEL_BG)
        draw.text((half+8, 4), "AFTER  (mixed — both channels)", fill=WAVE_AFTER)

        # ── Track rows: each side has two lanes ──────────────────────────────
        lane_y = [28, 94]          # top-left of each lane
        lane_h = 56
        label_w = 28

        def draw_lane(x0, x1, y, label_text, wave_color, draw_wave):
            """Draw one audio lane with label and waveform area."""
            # Label area
            draw.rectangle([x0, y, x0 + label_w, y + lane_h], fill='#0D0D0D')
            # Vertical text approximation: write label rotated — PIL doesn't rotate easily,
            # so write abbreviated text horizontally
            draw.text((x0 + 3, y + lane_h // 2 - 6), label_text, fill='#888888')
            # Track body
            draw.rectangle([x0 + label_w, y, x1, y + lane_h], fill=TRACK_BG)
            cx = (x0 + label_w + x1) // 2
            cy = y + lane_h // 2
            if draw_wave:
                # Draw a realistic-looking waveform using sine waves + noise
                pts = []
                track_w = x1 - (x0 + label_w)
                for px in range(0, track_w, 1):
                    t = px / track_w * 4 * math.pi
                    amp = (lane_h // 2 - 6) * (0.6 + 0.4 * abs(math.sin(t * 0.5)))
                    val = amp * math.sin(t * 3.1) * math.cos(t * 1.3)
                    pts.append((x0 + label_w + px, cy - int(val)))
                for i in range(len(pts) - 1):
                    draw.line([pts[i], pts[i+1]], fill=wave_color, width=1)
            else:
                # Flat silent line
                draw.line([(x0 + label_w + 4, cy), (x1 - 4, cy)], fill=FLAT_LINE, width=1)

        # BEFORE left half
        draw_lane(0, half-2, lane_y[0], "L", WAVE_BEFORE, draw_wave=True)
        draw_lane(0, half-2, lane_y[1], "R", WAVE_BEFORE, draw_wave=False)

        # AFTER right half
        draw_lane(half+2, W, lane_y[0], "L", WAVE_AFTER, draw_wave=True)
        draw_lane(half+2, W, lane_y[1], "R", WAVE_AFTER, draw_wave=True)

        return img
    except Exception:
        return None


def _draw_artifact_example(artifact_type):
    """Create a PIL Image showing a before/after comparison for a given artifact."""
    if not HAS_PIL:
        return None
    try:
        from PIL import Image, ImageDraw
        import random
        W, H = 440, 130
        img = Image.new('RGB', (W, H), '#1A1A1A')
        draw = ImageDraw.Draw(img)
        half = W // 2
        draw.rectangle([half-1, 0, half+1, H], fill='#444444')
        draw.rectangle([0, 0, half-2, 18], fill='#111111')
        draw.text((6, 2), "BEFORE", fill='#EF5350')
        draw.rectangle([half+2, 0, W, 18], fill='#111111')
        draw.text((half+8, 2), "AFTER", fill='#5DBB6B')
        if artifact_type == 'combing':
            for y in range(20, H-10):
                offset = 3 if y % 2 == 0 else -3
                draw.line([(60+offset, y), (half-20+offset, y)], fill='#CCCCCC', width=1)
            for y in range(35, H-25):
                draw.line([(70, y), (half-30, y)], fill='#888888', width=1)
            draw.rectangle([half+20, 35, W-20, H-25], fill='#BBBBBB')
            draw.rectangle([half+25, 40, W-25, H-30], fill='#DDDDDD')
        elif artifact_type == 'noise':
            rng = random.Random(42)
            for y in range(20, H):
                for x in range(0, half-2):
                    base = 80 + rng.randint(-40, 40)
                    draw.point((x, y), fill=(base, base, base))
            draw.rectangle([15, 40, half-15, H-20], fill=None, outline='#FFFFFF')
            for y in range(20, H):
                v = int(60 + (y - 20) / (H - 20) * 60)
                draw.line([(half+2, y), (W, y)], fill=(v, v, v))
            draw.rectangle([half+15, 40, W-15, H-20], fill=None, outline='#FFFFFF')
        elif artifact_type == 'chroma':
            # BEFORE half: gray background, bold red block whose right edge smears/bleeds
            BG = (72, 72, 72)
            RED = (210, 38, 38)
            draw.rectangle([0, 0, half - 2, H], fill=BG)
            block_right = (half - 2) // 3          # red block ends at ~33% of left half
            draw.rectangle([2, 22, block_right, H - 12], fill=RED)
            # Horizontal bleed: decreasing-opacity smear from block_right to right edge
            bleed_zone = (half - 2) - block_right
            for bleed in range(1, bleed_zone):
                ratio = 1.0 - (bleed / bleed_zone) ** 0.55
                if ratio <= 0.01:
                    break
                r = int(RED[0] * ratio + BG[0] * (1.0 - ratio))
                g = int(RED[1] * ratio + BG[1] * (1.0 - ratio))
                b = int(RED[2] * ratio + BG[2] * (1.0 - ratio))
                x = block_right + bleed
                if x < half - 2:
                    draw.line([(x, 22), (x, H - 12)], fill=(r, g, b))
            # AFTER half: gray background, same red block with perfectly clean edge
            draw.rectangle([half + 2, 0, W, H], fill=BG)
            block_right2 = half + 2 + (W - half - 2) // 3
            draw.rectangle([half + 4, 22, block_right2, H - 12], fill=RED)
        elif artifact_type == 'color_cast':
            for y in range(20, H):
                for x in range(0, half-2):
                    base = int(50 + (x / (half-2)) * 150)
                    r = min(255, base + 60)
                    g = min(255, base + 40)
                    b = max(0, base - 40)
                    draw.point((x, y), fill=(r, g, b))
            for y in range(20, H):
                for x in range(half+2, W):
                    base = int(50 + ((x - half - 2) / (W - half - 2)) * 150)
                    draw.point((x, y), fill=(base, base, base))
        elif artifact_type == 'levels':
            for y in range(20, H):
                for x in range(0, half-2):
                    v = int(10 + (x / (half-2)) * 170)
                    draw.point((x, y), fill=(v, v, v))
            for y in range(20, H):
                for x in range(half+2, W):
                    v = int((x - half - 2) / (W - half - 2) * 255)
                    draw.point((x, y), fill=(v, v, v))
        return img
    except:
        return None

class RestorationWizard(BaseWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        self.title(f"VCG Deinterlacer {VERSION_STRING}")
        
        # Window size (wide enough for the nav sidebar + content)
        window_width = 1120
        window_height = 900
        
        # Center window on screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2 - 40  # Slight offset up for taskbar
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        self.configure(bg=Colors.BG_DARK)
        self.resizable(True, True)
        self.minsize(980, 600)   # prevent layout from collapsing below a usable size
        
        # Try to set dark title bar on Windows 11
        self._set_dark_titlebar()
        
        # Load saved settings
        self.saved_settings = load_settings()
        
        # Configuration
        self.config_data = {
            'crop_left': 8,
            'crop_right': 8,
            'par_correction': True
        }
        
        # Steps
        self.steps = [
            "Welcome",         # 0  — hidden from sidebar
            "Select File",     # 1  → group 1
            "Source",          # 2  → group 2
            "Crop",            # 3  → group 2
            "Trim",            # 4  → group 3 "Advanced" ⓪ (single file only)
            "Y/C Delay",       # 5  → group 3 "Advanced" ①
            "Noise",           # 6  → group 3 "Advanced" ②
            "Dehalo",          # 7  → group 3 "Advanced" ③
            "Upscale",         # 8  → group 3 "Advanced" ④
            "Color Cast",      # 9  → group 3 "Advanced" ⑤
            "Levels",          # 10 → group 3 "Advanced" ⑥
            "Audio",           # 11 → group 3 "Advanced" ⑦
            "Watermark",       # 12 → group 3 "Advanced" ⑧
            "Add Grain",       # 13 → group 3 "Advanced" ⑨
            "Dithering",       # 14 → group 3 "Advanced" ⑩
            "Finalize",        # 15 → group 4
        ]
        # Sidebar display groups: each entry = (label, [step_indices])
        self.nav_groups = [
            ("Select File", [1]),
            ("Source",      [2, 3]),
            ("Advanced",    [4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]),
            ("Finalize",    [15]),
        ]
        self.current_step = 0
        self.visited_steps = set()   # steps the user has actually seen
        
        # Temp image paths for cleanup
        self.temp_images = []
        
        # Build UI
        self._build_ui()
        self._show_step(0)
        
        # Setup window close handler
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _on_close(self):
        """Clean up temp files on close."""
        for path in self.temp_images:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except:
                pass
        self.destroy()
    
    def _set_dark_titlebar(self):
        """Try to enable dark title bar on Windows 11."""
        try:
            import ctypes
            self.update()
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
            )
        except:
            pass
    
    def _create_menu(self):
        """Create the application menu bar."""
        menubar = tk.Menu(self, bg=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY,
                         activebackground=Colors.ACCENT, activeforeground='white',
                         borderwidth=0)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0, bg=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY,
                           activebackground=Colors.ACCENT, activeforeground='white')
        help_menu.add_command(label="About VCG Deinterlacer", command=self._show_about)
        help_menu.add_separator()
        help_menu.add_command(label="Visit Website", command=self._open_website)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.config(menu=menubar)
    
    def _show_about(self):
        """Show the About / Help dialog with scrollable technical details."""
        about_window = tk.Toplevel(self)
        about_window.title("About VCG Deinterlacer")
        about_window.configure(bg=Colors.BG_MAIN)
        about_window.resizable(True, True)

        # Size and center
        width, height = 660, 620
        x = self.winfo_x() + (self.winfo_width() - width) // 2
        y = self.winfo_y() + (self.winfo_height() - height) // 2
        about_window.geometry(f"{width}x{height}+{x}+{y}")
        about_window.minsize(500, 400)

        # Make modal
        about_window.transient(self)
        about_window.grab_set()

        # ── Scrollable canvas ──────────────────────────────────────
        outer = tk.Frame(about_window, bg=Colors.BG_MAIN)
        outer.pack(fill='both', expand=True)

        canvas = tk.Canvas(outer, bg=Colors.BG_MAIN, highlightthickness=0)
        vsb = tk.Scrollbar(outer, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)

        inner = tk.Frame(canvas, bg=Colors.BG_MAIN)
        win_id = canvas.create_window((0, 0), window=inner, anchor='nw')

        def _on_inner_configure(e):
            canvas.configure(scrollregion=canvas.bbox('all'))
        def _on_canvas_configure(e):
            canvas.itemconfig(win_id, width=e.width)
        inner.bind('<Configure>', _on_inner_configure)
        canvas.bind('<Configure>', _on_canvas_configure)

        def _on_mousewheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), 'units')
        canvas.bind_all('<MouseWheel>', _on_mousewheel)
        about_window.bind('<Destroy>', lambda e: canvas.unbind_all('<MouseWheel>'))

        # ── Content inside inner frame ──────────────────────────────
        pad = tk.Frame(inner, bg=Colors.BG_MAIN, padx=30, pady=25)
        pad.pack(fill='x')

        def section_label(text):
            f = tk.Frame(pad, bg=Colors.BG_MAIN)
            f.pack(fill='x', pady=(18, 4))
            tk.Label(f, text=text,
                     font=('Segoe UI', 13, 'bold'),
                     fg=Colors.ACCENT, bg=Colors.BG_MAIN).pack(anchor='w')
            tk.Frame(f, bg=Colors.BORDER, height=1).pack(fill='x', pady=(3, 0))

        def body_label(text, mono=False):
            font = ('Consolas', 9) if mono else ('Segoe UI', 11)
            tk.Label(pad, text=text,
                     font=font,
                     fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
                     wraplength=580, justify='left').pack(anchor='w', pady=(2, 0))

        def card_text(text, mono=False):
            font = ('Consolas', 9) if mono else ('Segoe UI', 10)
            f = tk.Frame(pad, bg=Colors.BG_CARD, padx=14, pady=10)
            f.pack(fill='x', pady=(4, 0))
            tk.Label(f, text=text,
                     font=font,
                     fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                     wraplength=560, justify='left').pack(anchor='w')

        # ── Header ─────────────────────────────────────────────────
        tk.Label(pad, text="VCG Deinterlacer",
                 font=('Segoe UI', 20, 'bold'),
                 fg=Colors.ACCENT, bg=Colors.BG_MAIN).pack(anchor='w')
        tk.Label(pad, text=f"{VERSION_STRING}  ·  {AUTHOR}  ·  {AUTHOR_HANDLE}",
                 font=('Segoe UI', 11),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(2, 8))
        body_label(
            "A Windows tool for deinterlacing VHS, Hi8, MiniDV and other tape captures "
            "using QTGMC — the industry-standard motion-compensated deinterlacer."
        )

        # ── QTGMC Settings ──────────────────────────────────────────
        section_label("QTGMC Settings")
        body_label(
            "VCG uses a conservative QTGMC configuration designed to be clean and "
            "non-destructive — preserving the original analog character without over-sharpening."
        )

        qtgmc_params = (
            "TR0=2          Temporal radius for noise analysis (more = cleaner)\n"
            "TR1=2          Temporal radius for motion compensation\n"
            "TR2=1          Temporal radius for final output blend\n"
            "Rep0=1         Repair strength on input (1 = gentle)\n"
            "Rep1=0         Repair on motion-compensated frames (off)\n"
            "Rep2=4         Repair on final output\n"
            "DCT=5          Block matching: spatial + temporal\n"
            "ThSCD1=300     Scene change detection threshold (conservative)\n"
            "ThSCD2=110     Scene change: second threshold\n"
            "SourceMatch=3  Highest quality source matching — most accurate\n"
            "Lossless=2     Preserve exact source pixels where no MC is needed\n"
            "Sharpness=0.1  Minimal sharpening — preserves the analog look\n"
            "Sbb=0          Sub-pixel blending off\n"
            "MatchPreset=slow  Quality preset for motion search\n"
            "NoiseProcess=2 Temporal denoise within QTGMC\n"
            "GrainRestore=0.0  Grain restore off (clean output)\n"
            "NoiseRestore=0.4  Noise restoration strength (moderate)\n"
            "NoisePreset=slow  Quality preset for noise processing\n"
            "StabilizeNoise=False\n"
            "NoiseTR=0      Temporal radius for noise (single frame)\n"
            "NoiseDeint=bob Noise deinterlacing method"
        )
        card_text(qtgmc_params, mono=True)

        body_label(
            "Key design choices:  Sharpness=0.1 is very mild (most presets use 0.2–1.0). "
            "Lossless=2 preserves original pixels where no motion compensation is needed. "
            "SourceMatch=3 catches high-frequency detail that lower settings miss."
        )

        # ── Denoising ───────────────────────────────────────────────
        section_label("Denoising (Advanced Mode)")
        body_label("When Advanced Mode denoising is enabled, BM3D (or SMDegrain if "
                   "unavailable) runs after QTGMC:")
        card_text(
            "Light:   BM3D sigma=3 (or SMDegrain fallback)\n"
            "Heavy:   BM3D sigma=6, profile=lc (or SMDegrain fallback)\n\n"
            "sigma = denoising strength (luma only — chroma untouched)\n"
            "Fallback order: BM3D → KNLMeansCL (GPU) → SMDegrain (MVTools)",
            mono=True
        )

        # ── Pixel Aspect Ratio & Cropping ───────────────────────────
        section_label("Pixel Aspect Ratio Correction & Edge Cropping")
        body_label(
            "Standard-definition video is stored with non-square pixels. "
            "VCG corrects the pixel aspect ratio (PAR) and, for SD captures, crops overscan "
            "edges automatically. DV captures default to no crop because native MiniDV/Digital8 "
            "recordings have clean frame edges."
        )
        card_text(
            "NTSC SD (USB/composite capture)\n"
            "  Storage:  720 × 480,  SAR 10:11\n"
            "  Crop:     8 px left + 8 px right  →  704 × 480\n"
            "  Display:  704 × (10÷11) = 640 × 480  (4:3, square pixels)\n"
            "\n"
            "NTSC DV (native MiniDV / FireWire)\n"
            "  Storage:  720 × 480,  SAR 8:9\n"
            "  Crop:     none by default (clean edges on native DV recordings)\n"
            "  Display:  720 × (8÷9) = 640 × 480  (4:3, square pixels)\n"
            "\n"
            "PAL SD (USB/composite capture)\n"
            "  Storage:  720 × 576,  SAR 59:54\n"
            "  Crop:     8 px left + 8 px right  →  704 × 576\n"
            "  Display:  704 × (59÷54) ≈ 768 × 576  (4:3, square pixels)\n"
            "\n"
            "PAL DV (native MiniDV / FireWire)\n"
            "  Storage:  720 × 576,  SAR 16:15\n"
            "  Crop:     none by default (clean edges on native DV recordings)\n"
            "  Display:  720 × (16÷15) = 768 × 576  (4:3, square pixels)",
            mono=True
        )
        body_label(
            "Why 8 pixels for SD captures?  ITU-R BT.601 defines 720 samples per line but only "
            "704 are 'active picture' — the outer 8 on each side are blanking/overscan that "
            "frequently contain noise, color-burst bleed, or black bars from the capture card. "
            "Cropping them before PAR correction produces a clean 4:3 frame with square pixels."
        )
        body_label(
            "DV passthrough note:  If you used a MiniDV camcorder to digitise an analog source "
            "(VHS, Video8, Hi8) via its AV-in / DV passthrough, the resulting DV file may have "
            "overscan noise on the left/right edges — just like an SD capture. In that case, "
            "set the crop to 8 px each side manually in the Finalize settings."
        )

        # ── Output Formats ──────────────────────────────────────────
        section_label("Output Format Technical Specifications")

        formats = [
            ("ProRes HQ (.mov)",
             "Codec: prores_ks  |  Pixel format: yuv422p10le  |  Profile: 3 (HQ)\n"
             "Audio: PCM 16-bit 48kHz\n"
             "10-bit 4:2:2. Best for editing in DaVinci Resolve, Premiere, Final Cut."),
            ("H.264 (.mp4)",
             "Codec: libx264  |  Pixel format: yuv420p  |  CRF 18, preset slow\n"
             "Audio: AAC 192k\n"
             "Visually lossless at CRF 18. Widely compatible. Smallest file size."),
            ("FFV1 (.mkv)",
             "Codec: ffv1  |  Level 3, coder 1, slicecrc 1  |  Pixel format: source\n"
             "Audio: PCM 16-bit 48kHz\n"
             "Mathematically lossless. Ideal for archival. Large files."),
        ]
        for fmt_name, fmt_detail in formats:
            f = tk.Frame(pad, bg=Colors.BG_CARD, padx=14, pady=10)
            f.pack(fill='x', pady=(6, 0))
            tk.Label(f, text=fmt_name,
                     font=('Segoe UI', 10, 'bold'),
                     fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD).pack(anchor='w')
            tk.Label(f, text=fmt_detail,
                     font=('Consolas', 9),
                     fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                     wraplength=560, justify='left').pack(anchor='w', pady=(4, 0))

        # ── Upscaling ───────────────────────────────────────────────
        section_label("Upscaling (NNEDI3)")
        body_label(
            "Nnedi3 is a high-quality neural-network upscaler originally developed for anime "
            "but it also works well for analog video. It uses a 2× transpose-double pass "
            "(rfactor=2) followed by a Spline36 resize to your chosen target resolution."
        )
        body_label(
            "Parameters are fixed for best quality: nsize=0 (8×6 neighbourhood), nns=3 "
            "(128 neurons). These settings maximise quality at the cost of processing time — "
            "expect upscaling to add several minutes per minute of footage."
        )

        # ── Third-party / License ───────────────────────────────────
        section_label("License & Third-Party Components")
        card_text(
            f"Copyright © {COPYRIGHT_YEAR} {AUTHOR}  —  MIT License\n\n"
            "FFmpeg (LGPL/GPL) · VapourSynth (LGPL) · QTGMC / havsfunc · "
            "mvtools · Python (PSF) · Tkinter\n\n"
            "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND."
        )

        tk.Frame(pad, bg=Colors.BG_MAIN, height=20).pack()

        # ── Close button (fixed at bottom outside scroll area) ──────
        btn_bar = tk.Frame(about_window, bg=Colors.BG_MAIN, pady=10)
        btn_bar.pack(fill='x', side='bottom')
        ModernButton(btn_bar, "Close", about_window.destroy, primary=True, width=80).pack(side='right', padx=20)
    
    def _open_website(self):
        """Open the website in the default browser."""
        import webbrowser
        webbrowser.open(WEBSITE)
    
    def _build_ui(self):
        # Create menu bar
        self._create_menu()
        
        # Main container
        main_frame = tk.Frame(self, bg=Colors.BG_DARK)
        main_frame.pack(fill='both', expand=True)

        # Wizard navigation sidebar — shown/hidden by _show_step
        self.sidebar = SidebarNav(main_frame, self.steps, self.nav_groups,
                                  on_navigate=self._jump_to_step,
                                  optional_groups={'Advanced'})

        # Content area
        self.content_frame = tk.Frame(main_frame, bg=Colors.BG_MAIN)
        self.content_frame.pack(side='right', fill='both', expand=True)


        # Navigation buttons — packed FIRST so they stay pinned to bottom
        nav_frame = tk.Frame(self.content_frame, bg=Colors.BG_MAIN)
        nav_frame.pack(side='bottom', fill='x', padx=30, pady=(0, 20))

        self.back_btn = ModernButton(nav_frame, "← Back", self._prev_step, width=100)
        self.back_btn.pack(side='left')

        self.next_btn = ModernButton(nav_frame, "Next →", self._next_step, primary=True, width=100)
        self.next_btn.pack(side='right')

        # Scrollable content container (so long pages don't clip)
        self._page_canvas = tk.Canvas(self.content_frame, bg=Colors.BG_MAIN, highlightthickness=0)
        self._page_scrollbar = tk.Scrollbar(self.content_frame, orient='vertical',
                                             command=self._page_canvas.yview)
        self._page_canvas.configure(yscrollcommand=self._page_scrollbar.set)
        self._page_scrollbar.pack(side='right', fill='y')
        self._page_canvas.pack(fill='both', expand=True)

        self.page_container = tk.Frame(self._page_canvas, bg=Colors.BG_MAIN)
        self._page_win = self._page_canvas.create_window((0, 0), window=self.page_container, anchor='nw')

        def _on_page_configure(e):
            self._page_canvas.configure(scrollregion=self._page_canvas.bbox('all'))
        def _on_canvas_configure(e):
            self._page_canvas.itemconfig(self._page_win, width=e.width - 60)
            self.page_container.config(padx=30)
        self.page_container.bind('<Configure>', _on_page_configure)
        self._page_canvas.bind('<Configure>', _on_canvas_configure)
        self._page_canvas.bind('<MouseWheel>',
            lambda e: self._page_canvas.yview_scroll(-1*(e.delta//120), 'units'))

        # Bind Enter key to Next throughout the wizard
        self.bind('<Return>', lambda e: self._next_step())
    
    def _clear_page(self):
        for widget in self.page_container.winfo_children():
            widget.destroy()
    
    def _show_step(self, step_index):
        self.current_step = step_index
        self.visited_steps.add(step_index)
        self._clear_page()

        # Sidebar — hide on Welcome screen, show and update on all others
        if step_index == 0:
            self.sidebar.pack_forget()
        else:
            if not self.sidebar.winfo_ismapped():
                self.sidebar.pack(side='left', fill='y',
                                  before=self.content_frame)
            # Trim is single-file only — hide it from the sidebar for batches
            disabled = ({4} if len(self.config_data.get('input_files', [])) > 1
                        else set())
            self.sidebar.set_state(step_index, self.visited_steps, disabled)

        # On the welcome page the START canvas button replaces the nav buttons;
        # re-show them for every other step.
        if step_index == 0:
            self.back_btn.pack_forget()
            self.next_btn.pack_forget()
        else:
            if not self.back_btn.winfo_ismapped():
                self.back_btn.pack(side='left')
            if not self.next_btn.winfo_ismapped():
                self.next_btn.pack(side='right')

        # Update navigation buttons
        self.back_btn.set_disabled(step_index <= 1)
        # On the last advanced page, label the button to indicate Finalize is next
        if step_index == 14:
            self.next_btn.text = "Finalize →"
        else:
            self.next_btn.text = "Next →"
        self.next_btn.set_disabled(False)
        self.next_btn._draw()

        # Show appropriate page (16-step navigation)
        step_methods = [
            self._page_welcome,         # 0
            self._page_select_file,     # 1
            self._page_source_dispatch,  # 2  SD or HD routing
            self._page_crop_preset,     # 3  Crop Preset
            self._page_trim,            # 4  Advanced ⓪ Trim / Segment Export
            self._page_yc_delay,        # 5  Advanced ① Y/C Delay
            self._page_noise,           # 6  Advanced ②
            self._page_dehalo,          # 7  Advanced ③ Dehalo
            self._page_upscale,         # 8  Advanced ④ Upscale
            self._page_color,           # 9  Advanced ⑤ Color Cast
            self._page_levels,          # 10 Advanced ⑥
            self._page_audio,           # 11 Advanced ⑦
            self._page_watermark,       # 12 Advanced ⑧ Watermark
            self._page_grain,           # 13 Advanced ⑨ Add Film Grain
            self._page_dither,          # 14 Advanced ⑩ Output Dithering
            self._page_finalize,        # 15
        ]

        if step_index < len(step_methods):
            step_methods[step_index]()
    
    def _next_step(self):
        # ── Step 1: validate file selection + batch type check ────────────────
        if self.current_step == 1:
            files = self.config_data.get('input_files', [])
            if not files:
                messagebox.showwarning("No Files Selected",
                                       "Please select at least one video file.")
                return
            if len(files) > 1:
                self._validate_batch_types(files, on_ok=lambda: self._show_step(2))
                return

        # ── Step 2: Source Details → Crop ────────────────────────────────────
        if self.current_step == 2:
            sc = self.config_data.get('source_classification', {}).get('source_class', 'sd')
            if sc in ('avchd', 'hdv'):
                self._ask_basic_or_advanced()
                return
            self._show_step(3)
            return

        # ── Step 3: Crop → "Process Now or Advanced?" ────────────────────────
        if self.current_step == 3:
            self._ask_basic_or_advanced()
            return

        # ── Step 4: Trim → validate segment selection before leaving ─────────
        if self.current_step == 4 and not self._validate_trim():
            return

        # ── Last step: nothing to do ──────────────────────────────────────────
        if self.current_step >= len(self.steps) - 1:
            return

        next_step = self.current_step + 1
        # Trim is a single-file feature — skip the page for multi-file batches
        if next_step == 4 and len(self.config_data.get('input_files', [])) > 1:
            next_step = 5
        self._show_step(next_step)

    def _ask_basic_or_advanced(self):
        """After Crop, let the user choose to process now or configure advanced options."""
        finalize_step = 15  # "Finalize" in the 16-step list
        # First advanced page: Trim (single file) — skipped for batches
        advanced_step = 4 if len(self.config_data.get('input_files', [])) <= 1 else 5

        dlg = tk.Toplevel(self)
        dlg.title("Ready to process?")
        dlg.configure(bg=Colors.BG_MAIN)
        dlg.resizable(False, False)
        w, h = 540, 320
        dlg.geometry(f"{w}x{h}+{self.winfo_x()+(self.winfo_width()-w)//2}+"
                     f"{self.winfo_y()+(self.winfo_height()-h)//2}")
        dlg.transient(self)
        dlg.grab_set()
        self.bind('<Return>', lambda e: None)  # disable Enter while dialog open

        f = tk.Frame(dlg, bg=Colors.BG_MAIN, padx=28, pady=24)
        f.pack(fill='both', expand=True)

        tk.Label(f, text="Basic settings are complete.",
                 font=('Segoe UI', 16, 'bold'), fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')
        tk.Label(f,
                 text="You can process now using just deinterlacing, or continue to configure "
                      "optional enhancements (trim, Y/C delay, noise removal, dehalo, upscale, "
                      "color analysis, levels, audio, watermark, film grain, dithering).",
                 font=('Segoe UI', 11), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
                 wraplength=490, justify='left').pack(anchor='w', pady=(8, 20))

        def go_basic():
            dlg.destroy()
            self.bind('<Return>', lambda e: self._next_step())
            # Set defaults for all skipped advanced pages
            self.config_data.setdefault('noise_level', 'none')
            self.config_data.setdefault('dehalo_mode', 'none')
            self.config_data.setdefault('upscale_enabled', False)
            self.config_data.setdefault('color_correction', 'none')
            self.config_data.setdefault('levels_adjustment', 'none')
            self.config_data.setdefault('mix_audio', False)
            self.config_data.setdefault('wm_type', 'none')
            self.config_data.setdefault('grain_strength', 0.0)
            self._show_step(finalize_step)

        def go_advanced():
            dlg.destroy()
            self.bind('<Return>', lambda e: self._next_step())
            self._show_step(advanced_step)

        btn_row = tk.Frame(f, bg=Colors.BG_MAIN)
        btn_row.pack(fill='x')

        proc_btn = tk.Frame(btn_row, bg=Colors.ACCENT, cursor='hand2')
        proc_btn.pack(fill='x', ipady=10, pady=(0, 10))
        proc_lbl = tk.Label(proc_btn, text="▶   Process Now  (recommended for most users)",
                            font=('Segoe UI', 12, 'bold'), fg='white', bg=Colors.ACCENT, cursor='hand2')
        proc_lbl.pack()
        proc_btn.bind('<Button-1>', lambda e: go_basic())
        proc_lbl.bind('<Button-1>', lambda e: go_basic())
        proc_btn.bind('<Enter>', lambda e: (proc_btn.config(bg=Colors.ACCENT_HOVER), proc_lbl.config(bg=Colors.ACCENT_HOVER)))
        proc_btn.bind('<Leave>', lambda e: (proc_btn.config(bg=Colors.ACCENT), proc_lbl.config(bg=Colors.ACCENT)))

        adv_btn = tk.Frame(btn_row, bg=Colors.BG_CARD, cursor='hand2')
        adv_btn.pack(fill='x', ipady=8)
        adv_lbl = tk.Label(adv_btn,
                           text="⚙   Advanced Options",
                           font=('Segoe UI', 11), fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD, cursor='hand2')
        adv_lbl.pack()
        adv_btn.bind('<Button-1>', lambda e: go_advanced())
        adv_lbl.bind('<Button-1>', lambda e: go_advanced())
        adv_btn.bind('<Enter>', lambda e: (adv_btn.config(bg=Colors.BG_CARD_HOVER), adv_lbl.config(bg=Colors.BG_CARD_HOVER)))
        adv_btn.bind('<Leave>', lambda e: (adv_btn.config(bg=Colors.BG_CARD), adv_lbl.config(bg=Colors.BG_CARD)))

        dlg.bind('<Return>', lambda e: go_basic())
    
    def _validate_batch_types(self, files, on_ok):
        """Check that all batch files share the same format and capture method.

        Runs ffprobe in a background thread so the UI stays responsive.
        Calls *on_ok()* if all files are compatible, otherwise shows a warning.
        """
        def _run():
            results = []
            for fp in files:
                try:
                    info = detect_par_format(fp)
                    results.append((fp, info))
                except Exception:
                    results.append((fp, {}))
            self.after(0, lambda: _check(results))

        def _check(results):
            formats  = [r[1].get('format')  for r in results if r[1].get('format')]
            captures = [r[1].get('capture_method') for r in results if r[1].get('capture_method')]

            fmt_set = set(formats)
            cap_set = set(captures)

            warnings = []
            if len(fmt_set) > 1:
                warnings.append(
                    f"Mixed broadcast standards detected: "
                    f"{', '.join(sorted(f.upper() for f in fmt_set))}.\n"
                    "Batch processing requires all files to be the same standard."
                )
            if len(cap_set) > 1:
                warnings.append(
                    f"Mixed capture methods detected: "
                    f"{', '.join(sorted(c.upper() for c in cap_set))}.\n"
                    "Batch processing requires all files to use the same capture method."
                )

            if warnings:
                msg = "\n\n".join(warnings)
                msg += "\n\nContinue anyway? (Results may be incorrect for mismatched files.)"
                if messagebox.askyesno("Mixed File Types Detected", msg,
                                       icon='warning', default='no'):
                    on_ok()
                # else: user stays on Select File page
            else:
                on_ok()

        threading.Thread(target=_run, daemon=True).start()

    def _prev_step(self):
        if self.current_step > 0:
            prev_step = self.current_step - 1
            # Trim is a single-file feature — skip the page for multi-file batches
            if prev_step == 4 and len(self.config_data.get('input_files', [])) > 1:
                prev_step = 3
            self._show_step(prev_step)

    def _jump_to_step(self, step_index):
        """Navigate via a sidebar click to a step the user has already reached."""
        if step_index == self.current_step:
            return
        # Same guard as Next: don't leave Trim with a selection that exports nothing
        if self.current_step == 4 and not self._validate_trim():
            return
        self._show_step(step_index)
    
    # ==================== STEP PAGES ====================
    
    def _page_welcome(self):
        # ── Title ─────────────────────────────────────────────────────────────
        tk.Label(self.page_container, text="VCG Deinterlacer",
                 font=('Segoe UI', 32, 'bold'),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN,
                 justify='center').pack(pady=(8, 4))

        # ── Logo image ────────────────────────────────────────────────────────
        # Look for logo.png / vcg_logo.png / vcg_deinterlacer.png (etc.) next to
        # the script or exe.  Image is displayed centred at a fixed display height
        # that preserves the 1214 × 1220 (≈ 1:1) original aspect ratio.
        # Drop any of the following files beside the script to activate:
        logo_names = ['logo.png', 'vcg_logo.png', 'vcg_deinterlacer.png',
                      'logo.jpg', 'vcg_logo.jpg']
        logo_path = None
        for search_dir in [os.path.dirname(os.path.abspath(__file__)),
                           os.path.dirname(sys.executable) if _IS_COMPILED else None]:
            if not search_dir:
                continue
            for name in logo_names:
                candidate = os.path.join(search_dir, name)
                if os.path.exists(candidate):
                    logo_path = candidate
                    break
            if logo_path:
                break

        # Native aspect ratio of the target image: 1214 × 1220 ≈ 1 : 1.005
        LOGO_RATIO = 1214 / 1220
        LOGO_DISPLAY_H = 220   # display height in pixels

        logo_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        logo_frame.pack(pady=(4, 8))

        if logo_path and HAS_PIL:
            try:
                raw = Image.open(logo_path)
                orig_w, orig_h = raw.size
                display_w = int(LOGO_DISPLAY_H * orig_w / orig_h)
                resized = raw.resize((display_w, LOGO_DISPLAY_H), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(resized)
                lbl = tk.Label(logo_frame, image=photo, bg=Colors.BG_MAIN)
                lbl.image = photo   # prevent GC
                lbl.pack()
            except Exception:
                logo_path = None

        if not logo_path or not HAS_PIL:
            # Minimal placeholder at the correct ratio — no distracting hint text
            ph_w = int(LOGO_DISPLAY_H * LOGO_RATIO)
            ph = tk.Frame(logo_frame, bg=Colors.BG_CARD,
                          width=ph_w, height=LOGO_DISPLAY_H)
            ph.pack()
            ph.pack_propagate(False)
            tk.Label(ph, text="▶",
                     font=('Segoe UI', 60),
                     fg=Colors.ACCENT, bg=Colors.BG_CARD).place(relx=0.5, rely=0.5, anchor='center')

        # ── START button ──────────────────────────────────────────────────────
        btn_outer = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        btn_outer.pack(pady=(28, 10))

        start_btn = tk.Canvas(btn_outer, width=260, height=62,
                              bg=Colors.BG_MAIN, highlightthickness=0, cursor='hand2')
        start_btn.pack()

        def _draw_start(hovered=False):
            start_btn.delete('all')
            fill = Colors.ACCENT_HOVER if hovered else Colors.ACCENT
            # Rounded rectangle (simulate with oval + rect)
            r = 12
            w, h = 260, 62
            start_btn.create_arc(0, 0, r*2, r*2, start=90, extent=90, fill=fill, outline='')
            start_btn.create_arc(w-r*2, 0, w, r*2, start=0, extent=90, fill=fill, outline='')
            start_btn.create_arc(0, h-r*2, r*2, h, start=180, extent=90, fill=fill, outline='')
            start_btn.create_arc(w-r*2, h-r*2, w, h, start=270, extent=90, fill=fill, outline='')
            start_btn.create_rectangle(r, 0, w-r, h, fill=fill, outline='')
            start_btn.create_rectangle(0, r, w, h-r, fill=fill, outline='')
            start_btn.create_text(w//2, h//2, text="START  ▶",
                                  font=('Segoe UI', 20, 'bold'), fill='white')

        _draw_start()
        start_btn.bind('<Enter>',    lambda e: _draw_start(True))
        start_btn.bind('<Leave>',    lambda e: _draw_start(False))
        start_btn.bind('<Button-1>', lambda e: self._next_step())

        # ── Tagline ───────────────────────────────────────────────────────────
        tk.Label(self.page_container,
                 text="Deinterlace your VHS, Hi8, and MiniDV tapes using QTGMC — the professional standard.",
                 font=('Segoe UI', 11), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
                 wraplength=700, justify='center').pack(pady=(0, 0))

        # Hide the nav-bar Next button on the welcome page — START replaces it
        self.next_btn.pack_forget()
        self.back_btn.pack_forget()

    
    def _page_select_file(self):
        # Title
        tk.Label(self.page_container, text="Select Video Files",
                font=('Segoe UI', 22, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')
        
        tk.Label(self.page_container, text="Choose one or more video files to restore (same settings will apply to all)",
                font=('Segoe UI', 13, 'bold'),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(4, 20))
        
        # Multi-file drop zone
        self.drop_zone = MultiFileDropZone(self.page_container, self._on_files_changed)
        self.drop_zone.pack(fill='both', expand=True)
        
        # Restore files if returning to this page
        if 'input_files' in self.config_data and self.config_data['input_files']:
            self.drop_zone.files = self.config_data['input_files'].copy()
            self.drop_zone._update_display()
        
        # Browse button
        btn_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        btn_frame.pack(fill='x', pady=(15, 0))
        ModernButton(btn_frame, "Browse...", self._browse_files, width=120).pack(anchor='w')
    
    def _on_files_changed(self, files):
        """Handle file list changes."""
        # Trim segments are frame positions in a specific file — discard them
        # whenever the selection changes (mode/output preferences are kept).
        if files != self.config_data.get('input_files', []):
            self.config_data.pop('trim_segments', None)
            self.config_data.pop('trim_total_frames', None)
            self.config_data.pop('trim_fps', None)

        self.config_data['input_files'] = files.copy()

        # For backwards compatibility, also set input_path to first file
        if files:
            self.config_data['input_path'] = files[0]

            # FPS-based format guess (fallback)
            info = get_video_info(files[0])
            if info:
                if abs(info['fps'] - 29.97) < 0.5:
                    self.config_data['guessed_format'] = 'ntsc'
                elif abs(info['fps'] - 25.0) < 0.5:
                    self.config_data['guessed_format'] = 'pal'

            # SAR-based auto-detection (more precise — uses pixel aspect ratio + codec)
            par_info = detect_par_format(files[0])

            if par_info.get('format'):
                self.config_data['auto_format'] = par_info['format']
                # Pre-fill format so the radio button on the next page is already correct
                self.config_data['format'] = par_info['format']
                self.config_data['guessed_format'] = par_info['format']
            else:
                self.config_data.pop('auto_format', None)

            if par_info.get('capture_method'):
                self.config_data['auto_capture_method'] = par_info['capture_method']
                # Pre-fill capture method so the radio button is already correct
                self.config_data['capture_method'] = par_info['capture_method']
            else:
                self.config_data.pop('auto_capture_method', None)

            # Store SAR string for display on the pages
            self.config_data['detected_sar'] = par_info.get('sar', '')

            # Source classification for HD routing (AVCHD/HDV vs SD)
            sc = classify_source(files[0])
            self.config_data['source_classification'] = sc

        else:
            self.config_data.pop('input_path', None)
            self.config_data.pop('guessed_format', None)
            self.config_data.pop('auto_format', None)
            self.config_data.pop('auto_capture_method', None)
            self.config_data.pop('detected_sar', None)
            self.config_data.pop('source_classification', None)
    
    def _browse_files(self):
        # Use last folder if available
        initial_dir = self.saved_settings.get('last_folder', '')
        
        filepaths = filedialog.askopenfilenames(
            title="Select Video Files",
            initialdir=initial_dir if os.path.exists(initial_dir) else '',
            filetypes=[
                ("Video files", "*.avi *.mp4 *.mkv *.mov *.m4v *.mpg *.mpeg *.mts *.m2ts *.m2t *.ts *.mod"),
                ("All files", "*.*")
            ]
        )
        if filepaths:
            # Save folder for next time
            folder = os.path.dirname(filepaths[0])
            self.saved_settings['last_folder'] = folder
            save_settings(self.saved_settings)
            
            self.drop_zone.add_files(filepaths)
    
    def _page_source_details(self):
        """Step 2 — Source Details (Gemini-style): Format + Capture + Field Order.

        Each section has:
          • Numbered heading in accent colour (left)
          • Auto-detected badge in green (right, same row)
          • Radio-button card below the heading row
        Field order detection auto-triggers in background and updates the badge.
        """
        # ── Page header ────────────────────────────────────────────────────────
        tk.Label(self.page_container, text="Source Details",
                 font=('Segoe UI', 22, 'bold'),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')
        tk.Label(self.page_container, text="Configure how the video was digitized.",
                 font=('Segoe UI', 13),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(2, 20))

        # Non-blocking notice for 10-bit / non-standard sources (auto-converted)
        if self.config_data.get('source_classification', {}).get('needs_pixfmt_conversion'):
            tk.Label(self.page_container,
                     text="ℹ  Your source is 10-bit or non-standard format — automatically "
                          "converting to 8-bit for processing.",
                     font=('Segoe UI', 11), fg=Colors.ACCENT, bg=Colors.BG_MAIN,
                     wraplength=620, justify='left').pack(anchor='w', pady=(0, 14))

        auto_format  = self.config_data.get('auto_format')
        auto_capture = self.config_data.get('auto_capture_method')
        sar          = self.config_data.get('detected_sar', '')

        def section_hdr_row(number, title, badge_text=None):
            """Return the header frame; badge_text shown in green if provided."""
            row = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
            row.pack(fill='x', pady=(0, 6))
            tk.Label(row, text=f"{number}. {title}",
                     font=('Segoe UI', 13, 'bold'),
                     fg=Colors.ACCENT, bg=Colors.BG_MAIN).pack(side='left')
            badge_lbl = None
            if badge_text:
                badge_lbl = tk.Label(row, text=f"  ✓ Auto-Detected: {badge_text}",
                                     font=('Segoe UI', 11, 'bold'),
                                     fg='#22CC66', bg=Colors.BG_MAIN)
                badge_lbl.pack(side='right')
            return badge_lbl

        # ════════════════════════════════════════════════════════════════════
        # 1 — VIDEO FORMAT
        # ════════════════════════════════════════════════════════════════════
        fmt_badge = 'NTSC' if auto_format == 'ntsc' else ('PAL' if auto_format == 'pal' else None)
        section_hdr_row("1", "Video Format", fmt_badge)

        initial_format = self.config_data.get('format',
                         self.config_data.get('guessed_format', 'ntsc'))
        self.config_data['format'] = initial_format
        self.format_var = tk.StringVar(value=initial_format)

        fmt_card = tk.Frame(self.page_container, bg=Colors.BG_CARD)
        fmt_card.pack(fill='x')
        ModernRadioButton(fmt_card, "NTSC (29.97fps, 480 lines)", self.format_var, "ntsc",
                          "North America, Japan, South Korea").pack(fill='x')
        ttk.Separator(fmt_card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(fmt_card, "PAL (25fps, 576 lines)", self.format_var, "pal",
                          "Europe, Australia, most of Asia").pack(fill='x')
        self.format_var.trace_add('write',
            lambda *_: self.config_data.update({'format': self.format_var.get()}))

        # ════════════════════════════════════════════════════════════════════
        # 2 — CAPTURE METHOD
        # ════════════════════════════════════════════════════════════════════
        cap_badge = ('DV' if auto_capture == 'dv' else
                     ('DVD/MPEG-2' if auto_capture == 'dvd' else
                      ('SD' if auto_capture == 'sd' else None)))
        section_hdr_row("2", "Capture Method", cap_badge)

        initial_capture = self.config_data.get('capture_method', 'sd')
        self.config_data['capture_method'] = initial_capture
        self.capture_var = tk.StringVar(value=initial_capture)

        cap_card = tk.Frame(self.page_container, bg=Colors.BG_CARD)
        cap_card.pack(fill='x', pady=(0, 0))
        ModernRadioButton(cap_card, "SD Capture Device (USB card, VirtualDub)",
                          self.capture_var, "sd",
                          "Elgato, Hauppauge, ATI, etc. — crops 8px each side").pack(fill='x')
        ttk.Separator(cap_card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(cap_card, "MPEG-2 / DVD (VOB, MPG ripped from disc)",
                          self.capture_var, "dvd",
                          "DVD-sourced MPEG-2. Field order TFF. "
                          "Telecine detection enabled — 3:2 pulldown is common on film DVDs.").pack(fill='x')
        ttk.Separator(cap_card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(cap_card, "DV Capture Device (FireWire/MiniDV)",
                          self.capture_var, "dv",
                          "Native MiniDV/Digital8 — no edge crop (clean frame). "
                          "If digitising VHS/Video8 via DV passthrough, crop manually in Finalize.").pack(fill='x')

        def _on_capture_changed(*_):
            method = self.capture_var.get()
            crop = 0 if method == 'dv' else 8
            self.config_data.update({
                'capture_method': method,
                'crop_left': crop,
                'crop_right': crop,
            })
        self.capture_var.trace_add('write', _on_capture_changed)
        # Apply crop for the initial selection immediately
        _on_capture_changed()

        # ════════════════════════════════════════════════════════════════════
        # 3 — FIELD ORDER
        # ════════════════════════════════════════════════════════════════════
        num_files = len(self.config_data.get('input_files', []))

        # Header row — badge is updated when detection finishes
        fo_row = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        fo_row.pack(fill='x', pady=(20, 6))
        tk.Label(fo_row, text="3. Field Order",
                 font=('Segoe UI', 13, 'bold'),
                 fg=Colors.ACCENT, bg=Colors.BG_MAIN).pack(side='left')

        # Create the badge label — starts empty or with a previously known value
        prior_fo = self.config_data.get('detected_field_order')
        initial_badge = f"  ✓ Auto-Detected: {prior_fo.upper()}" if prior_fo else "  ⏳ Detecting…"
        self._fo_badge_lbl = tk.Label(fo_row, text=initial_badge,
                                      font=('Segoe UI', 11, 'bold'),
                                      fg=('#22CC66' if prior_fo else Colors.ACCENT),
                                      bg=Colors.BG_MAIN)
        self._fo_badge_lbl.pack(side='right')

        # Field order description
        fo_desc = ("Field order determines which video field is drawn first — it must match "
                   "how the video was originally encoded or motion will look jagged.")
        if num_files > 1:
            fo_desc = ("Batch mode — the same field order will be applied to all files. "
                       "Manually select the correct order below.")
        tk.Label(self.page_container, text=fo_desc,
                 font=('Segoe UI', 11), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
                 wraplength=620, justify='left').pack(anchor='w', pady=(0, 8))

        initial_fo = self.config_data.get('field_order',
                     self.config_data.get('detected_field_order', 'tff'))
        self.config_data['field_order'] = initial_fo
        self.field_var = tk.StringVar(value=initial_fo)

        fo_card = tk.Frame(self.page_container, bg=Colors.BG_CARD)
        fo_card.pack(fill='x')
        ModernRadioButton(fo_card, "TFF — Top Field First (Most SD Cards)",
                          self.field_var, "tff",
                          "Typical for SD capture cards (Elgato, Hauppauge, etc.)").pack(fill='x')
        ttk.Separator(fo_card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(fo_card, "BFF — Bottom Field First (DV/FireWire)",
                          self.field_var, "bff",
                          "Typical for MiniDV, Digital8, FireWire captures").pack(fill='x')
        ttk.Separator(fo_card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(fo_card, "Progressive (no deinterlacing needed)",
                          self.field_var, "progressive",
                          "Video was already progressive — only PAR correction applied").pack(fill='x')

        self.field_var.trace_add('write',
            lambda *_: self.config_data.update({'field_order': self.field_var.get()}))

        # Re-run button + auto-trigger detection for single files
        if num_files <= 1:
            rerun_row = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
            rerun_row.pack(anchor='w', pady=(8, 0))
            ModernButton(rerun_row, "Re-run Detection",
                         self._run_field_order_detection, width=150).pack(side='left')
            ModernButton(rerun_row, "Visual Comparison",
                         self._run_field_order_visual, width=150).pack(side='left', padx=(10, 0))
            # Point the existing badge variable at our new badge label
            self.detect_badge_lbl = self._fo_badge_lbl
            # Auto-trigger detection after a short delay
            self.after(400, self._run_field_order_detection)

        # ════════════════════════════════════════════════════════════════════
        # 4 — TELECINE / INVERSE TELECINE DETECTION  (Feature 2)
        # ════════════════════════════════════════════════════════════════════
        ttk.Separator(self.page_container, orient='horizontal').pack(fill='x', pady=(20, 0))

        ivtc_row = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        ivtc_row.pack(fill='x', pady=(12, 6))
        tk.Label(ivtc_row, text="4. Telecine / Pulldown Detection",
                 font=('Segoe UI', 13, 'bold'),
                 fg=Colors.ACCENT, bg=Colors.BG_MAIN).pack(side='left')

        prior_ivtc = self.config_data.get('ivtc_result')
        _ivtc_badge_text = '  ⏳ Analyzing…'
        _ivtc_badge_color = Colors.ACCENT
        if prior_ivtc:
            if prior_ivtc.get('dv_bypass'):
                _ivtc_badge_text = '  ✓ Not applicable (DV source)'
                _ivtc_badge_color = Colors.SUCCESS
            elif prior_ivtc.get('detected'):
                _ivtc_badge_text = f"  ⚠  Telecine detected ({prior_ivtc['pattern']})"
                _ivtc_badge_color = Colors.WARNING
            else:
                _ivtc_badge_text = '  ✓ No telecine detected'
                _ivtc_badge_color = Colors.SUCCESS

        self._ivtc_badge = tk.Label(ivtc_row, text=_ivtc_badge_text,
                                     font=('Segoe UI', 11, 'bold'),
                                     fg=_ivtc_badge_color, bg=Colors.BG_MAIN)
        self._ivtc_badge.pack(side='right')

        ivtc_desc = tk.Label(
            self.page_container,
            text="Telecine (3:2 pulldown) is applied when film is transferred to interlaced video. "
                 "If detected, VCG can apply Inverse Telecine (IVTC) to restore the original "
                 "progressive frame rate instead of running standard deinterlacing.",
            font=('Segoe UI', 11), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
            wraplength=620, justify='left')
        ivtc_desc.pack(anchor='w', pady=(0, 8))

        # Container for detection result card (populated when detection finishes)
        self._ivtc_result_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        self._ivtc_result_frame.pack(fill='x')

        # IVTC mode radio buttons (shown when detection result arrives)
        self._ivtc_mode_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        self._ivtc_mode_frame.pack(fill='x')

        # Show previously-detected result immediately if available
        if prior_ivtc:
            self.after(0, lambda: self._show_ivtc_result(prior_ivtc))

        # Trigger detection for single-file mode
        if num_files <= 1:
            self.after(600, self._run_ivtc_detection)

        # ════════════════════════════════════════════════════════════════════
        # 5 — SOURCE COLOR MATRIX
        # ════════════════════════════════════════════════════════════════════
        ttk.Separator(self.page_container, orient='horizontal').pack(fill='x', pady=(20, 0))

        matrix_hdr = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        matrix_hdr.pack(fill='x', pady=(12, 6))
        tk.Label(matrix_hdr, text="5. Source Color Matrix",
                 font=('Segoe UI', 13, 'bold'),
                 fg=Colors.ACCENT, bg=Colors.BG_MAIN).pack(side='left')
        tk.Label(matrix_hdr, text="  ✓ Auto-selected for SD",
                 font=('Segoe UI', 11, 'bold'),
                 fg='#22CC66', bg=Colors.BG_MAIN).pack(side='right')

        tk.Label(self.page_container,
                 text="Determines how colours are decoded from the video signal. "
                      "SD captures almost always use BT.601 — leave this as-is unless you know otherwise.",
                 font=('Segoe UI', 11), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
                 wraplength=620, justify='left').pack(anchor='w', pady=(0, 8))

        _matrix_choices = [
            ("Standard Definition / VHS capture — BT.601 (recommended)", 'bt601'),
            ("High Definition — BT.709", 'bt709'),
        ]
        _matrix_labels = [lbl for lbl, _ in _matrix_choices]
        _matrix_values = {lbl: val for lbl, val in _matrix_choices}
        _matrix_labels_inv = {val: lbl for lbl, val in _matrix_choices}

        # Pre-select: honour any previously saved value, else default to bt601 for SD
        _initial_matrix = self.config_data.get('color_matrix', 'bt601')
        _initial_label = _matrix_labels_inv.get(_initial_matrix, _matrix_labels[0])
        self.config_data['color_matrix'] = _initial_matrix

        self._matrix_var_sd = tk.StringVar(value=_initial_label)

        matrix_card = tk.Frame(self.page_container, bg=Colors.BG_CARD)
        matrix_card.pack(fill='x')
        inner = tk.Frame(matrix_card, bg=Colors.BG_CARD)
        inner.pack(fill='x', padx=14, pady=10)
        tk.Label(inner, text="Source type:", font=('Segoe UI', 11),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD).pack(side='left')
        matrix_dd = ttk.Combobox(inner, textvariable=self._matrix_var_sd,
                                  values=_matrix_labels, state='readonly', width=52)
        matrix_dd.pack(side='left', padx=(10, 0))

        def _on_matrix_sd(*_):
            chosen = _matrix_values.get(self._matrix_var_sd.get(), 'bt601')
            self.config_data['color_matrix'] = chosen

        self._matrix_var_sd.trace_add('write', _on_matrix_sd)

    # ── IVTC detection helpers ──────────────────────────────────────────────

    def _run_ivtc_detection(self):
        """Run telecine detection in a background thread."""
        files = self.config_data.get('input_files', [])
        filepath = files[0] if files else self.config_data.get('input_path')
        if not filepath:
            return
        video_format = self.config_data.get('format', 'ntsc')
        capture_method = self.config_data.get('capture_method')

        def worker():
            result = detect_telecine(filepath, video_format, capture_method=capture_method)
            self.config_data['ivtc_result'] = result
            self.after(0, lambda: self._show_ivtc_result(result))

        threading.Thread(target=worker, daemon=True).start()

    def _show_ivtc_result(self, result):
        """Display IVTC detection result on the Source Details page."""
        if not hasattr(self, '_ivtc_badge') or not self._ivtc_badge.winfo_exists():
            return

        # Update badge
        if result.get('detected'):
            pattern = result.get('pattern', '?:?')
            conf = result.get('confidence', '')
            self._ivtc_badge.config(
                text=f"  ⚠  {pattern} pulldown detected  ({conf} confidence)",
                fg=Colors.WARNING)
        else:
            self._ivtc_badge.config(text='  ✓ No telecine detected', fg=Colors.SUCCESS)

        # Clear previous result widgets
        for w in self._ivtc_result_frame.winfo_children():
            w.destroy()
        for w in self._ivtc_mode_frame.winfo_children():
            w.destroy()

        if result.get('dv_bypass'):
            # DV source — IVTC is not applicable; show an informational card
            self.config_data['ivtc_mode'] = False
            self._ivtc_badge.config(text='  ✓ Not applicable (DV source)', fg=Colors.SUCCESS)
            dv_card = tk.Frame(self._ivtc_result_frame, bg=Colors.BG_CARD, padx=12, pady=10)
            dv_card.pack(fill='x', pady=(4, 8))
            tk.Label(dv_card,
                     text="ℹ  IVTC not applicable — DV camcorder source",
                     font=('Segoe UI', 11, 'bold'),
                     fg=Colors.ACCENT, bg=Colors.BG_CARD).pack(anchor='w')
            tk.Label(dv_card,
                     text=result.get('description', ''),
                     font=('Segoe UI', 10), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                     wraplength=580, justify='left').pack(anchor='w', pady=(4, 0))
        elif result.get('detected'):
            # Alert card
            alert = tk.Frame(self._ivtc_result_frame, bg='#2A1E00', padx=14, pady=12)
            alert.pack(fill='x', pady=(4, 8))
            hdr = tk.Frame(alert, bg='#2A1E00')
            hdr.pack(fill='x')
            tk.Label(hdr, text="⚠", font=('Segoe UI', 16), fg=Colors.WARNING,
                     bg='#2A1E00').pack(side='left', padx=(0, 8))
            tk.Label(hdr, text="Telecined content detected — Inverse Telecine available",
                     font=('Segoe UI', 11, 'bold'), fg=Colors.WARNING,
                     bg='#2A1E00').pack(side='left')
            pattern = result.get('pattern', '')
            target_fps = result.get('target_fps', 0)
            if pattern == '3:2':
                fps_str = '23.976 fps'
                method_line = ("VCG will apply vivtc.VFM + vivtc.VDecimate to "
                               "reconstruct the original progressive frames.")
                apply_desc = f"Restore original {fps_str} — removes pulldown fields"
                keep_desc = "Keep 29.97fps output using QTGMC (ignores telecine)"
            else:
                fps_str = '25 fps progressive'
                method_line = ("VCG will apply vivtc.VFM to pair fields back into "
                               "the original progressive frames — the frame rate "
                               "stays 25fps.")
                apply_desc = "Reconstruct 25fps progressive frames by pairing fields"
                keep_desc = "Keep 25fps output using QTGMC (ignores the film transfer)"
            detail = (
                f"Pattern: {pattern} pulldown  →  native frame rate: {fps_str}\n"
                f"{result.get('description', '')}\n\n"
                f"{method_line}"
            )
            tk.Label(alert, text=detail, font=('Segoe UI', 10),
                     fg='#D0A060', bg='#2A1E00',
                     wraplength=580, justify='left').pack(anchor='w', pady=(6, 0))

            # User choice
            initial_ivtc = self.config_data.get('ivtc_mode', True)
            self.config_data['ivtc_mode'] = initial_ivtc
            ivtc_var = tk.BooleanVar(value=initial_ivtc)
            choice_card = tk.Frame(self._ivtc_mode_frame, bg=Colors.BG_CARD)
            choice_card.pack(fill='x', pady=(0, 8))
            tk.Label(choice_card, text="How would you like to process this content?",
                     font=('Segoe UI', 11, 'bold'), fg=Colors.TEXT_PRIMARY,
                     bg=Colors.BG_CARD, padx=12).pack(anchor='w', pady=(10, 6))

            def _on_ivtc_change(*_):
                self.config_data['ivtc_mode'] = ivtc_var.get()

            for row_text, row_desc, row_val in [
                ("Apply Inverse Telecine (recommended)", apply_desc, True),
                ("Use Standard Deinterlacing", keep_desc, False),
            ]:
                rb = ModernRadioButton(choice_card, row_text, ivtc_var, row_val, row_desc)
                rb.pack(fill='x')
                ttk.Separator(choice_card, orient='horizontal').pack(fill='x', padx=12)

            ivtc_var.trace_add('write', _on_ivtc_change)

            # Scroll the page canvas down so the choice card is visible.
            # Detection runs asynchronously; by the time the result arrives the
            # choice card is often below the visible fold.
            def _scroll_to_choice():
                self.page_container.update_idletasks()
                self._page_canvas.configure(
                    scrollregion=self._page_canvas.bbox('all'))
                self._page_canvas.yview_moveto(1.0)
            self.after(80, _scroll_to_choice)
        else:
            # No telecine — ensure ivtc_mode is False
            self.config_data['ivtc_mode'] = False
            no_tc = tk.Frame(self._ivtc_result_frame, bg=Colors.BG_CARD, padx=12, pady=10)
            no_tc.pack(fill='x', pady=(4, 8))
            tk.Label(no_tc, text="✓ No telecine pattern detected — standard deinterlacing will be used.",
                     font=('Segoe UI', 11), fg=Colors.SUCCESS, bg=Colors.BG_CARD).pack(anchor='w')

    # ── Source Details dispatcher ──────────────────────────────────────────────

    def _page_source_dispatch(self):
        """Route to the SD or HD Source Details page based on source classification."""
        sc = self.config_data.get('source_classification', {})
        is_hd = sc.get('source_class') in ('avchd', 'hdv')

        # Pre-set color_matrix default based on resolution so the dropdown is
        # pre-selected correctly when the page renders. The page can still override.
        if 'color_matrix' not in self.config_data:
            self.config_data['color_matrix'] = 'bt709' if is_hd else 'bt601'

        if is_hd:
            self._page_source_details_hd()
        else:
            self._page_source_details()

    def _page_source_details_hd(self):
        """Step 2 — Source Details (HD): for AVCHD/MTS and HDV interlaced sources.

        Mirrors the structure of _page_source_details but without the SD/DV
        Capture Method section and with HD-appropriate field-order defaults.
        """
        # ── Page header ────────────────────────────────────────────────────────
        tk.Label(self.page_container, text="Source Details (HD)",
                 font=('Segoe UI', 22, 'bold'),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')
        tk.Label(self.page_container, text="Configure your interlaced HD video source.",
                 font=('Segoe UI', 13),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(2, 20))

        sc = self.config_data.get('source_classification', {})

        def section_hdr_row(number, title, badge_text=None):
            """Return the header frame; badge_text shown in green if provided."""
            row = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
            row.pack(fill='x', pady=(0, 6))
            tk.Label(row, text=str(number) + ". " + title,
                     font=('Segoe UI', 13, 'bold'),
                     fg=Colors.ACCENT, bg=Colors.BG_MAIN).pack(side='left')
            badge_lbl = None
            if badge_text:
                badge_lbl = tk.Label(row, text="  ✓ Auto-Detected: " + badge_text,
                                     font=('Segoe UI', 11, 'bold'),
                                     fg='#22CC66', bg=Colors.BG_MAIN)
                badge_lbl.pack(side='right')
            return badge_lbl

        # ════════════════════════════════════════════════════════════════════
        # 1 — DETECTED SOURCE  (read-only info card)
        # ════════════════════════════════════════════════════════════════════
        section_hdr_row("1", "Detected Source", sc.get('display_name', 'HD Source'))

        info_card = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=14, pady=12)
        info_card.pack(fill='x')

        fps_val = sc.get('fps', 0.0)
        fps_str = '{:.3f}'.format(fps_val).rstrip('0').rstrip('.') + ' fps'
        details = [
            ("Source",     sc.get('display_name', 'HD Source')),
            ("Resolution", str(sc.get('width', 0)) + '×' + str(sc.get('height', 0))),
            ("Frame Rate", fps_str),
            ("Codec",      sc.get('codec', 'unknown')),
        ]
        for lbl_text, val_text in details:
            detail_row = tk.Frame(info_card, bg=Colors.BG_CARD)
            detail_row.pack(fill='x', pady=2)
            tk.Label(detail_row, text=lbl_text + ':',
                     font=('Segoe UI', 11, 'bold'),
                     fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                     width=14, anchor='w').pack(side='left')
            tk.Label(detail_row, text=val_text,
                     font=('Segoe UI', 11),
                     fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD,
                     anchor='w').pack(side='left')

        # Non-blocking notice for 10-bit / non-standard sources (auto-converted)
        if sc.get('needs_pixfmt_conversion'):
            tk.Label(info_card,
                     text="ℹ  Your source is 10-bit or non-standard format — automatically "
                          "converting to 8-bit for processing.",
                     font=('Segoe UI', 11), fg=Colors.ACCENT, bg=Colors.BG_CARD,
                     wraplength=560, justify='left').pack(anchor='w', pady=(6, 0))

        # ════════════════════════════════════════════════════════════════════
        # 2 — VIDEO STANDARD
        # ════════════════════════════════════════════════════════════════════
        fps_val = sc.get('fps', 0.0)
        if abs(fps_val - 29.97) < 0.5 or abs(fps_val - 30.0) < 0.1:
            auto_format = 'ntsc'
        elif abs(fps_val - 25.0) < 0.5:
            auto_format = 'pal'
        else:
            auto_format = self.config_data.get('auto_format')

        fmt_badge = 'NTSC' if auto_format == 'ntsc' else ('PAL' if auto_format == 'pal' else None)
        section_hdr_row("2", "Video Standard", fmt_badge)

        initial_format = auto_format or self.config_data.get('format',
                         self.config_data.get('guessed_format', 'ntsc'))
        self.config_data['format'] = initial_format
        self.format_var = tk.StringVar(value=initial_format)

        fmt_card = tk.Frame(self.page_container, bg=Colors.BG_CARD)
        fmt_card.pack(fill='x')
        ModernRadioButton(fmt_card, "NTSC (29.97 fps)", self.format_var, "ntsc",
                          "North America, Japan, South Korea").pack(fill='x')
        ttk.Separator(fmt_card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(fmt_card, "PAL (25 fps)", self.format_var, "pal",
                          "Europe, Australia, most of Asia").pack(fill='x')
        self.format_var.trace_add('write',
            lambda *_: self.config_data.update({'format': self.format_var.get()}))

        # ════════════════════════════════════════════════════════════════════
        # 3 — FIELD ORDER
        # ════════════════════════════════════════════════════════════════════
        num_files = len(self.config_data.get('input_files', []))

        fo_row = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        fo_row.pack(fill='x', pady=(20, 6))
        tk.Label(fo_row, text="3. Field Order",
                 font=('Segoe UI', 13, 'bold'),
                 fg=Colors.ACCENT, bg=Colors.BG_MAIN).pack(side='left')

        prior_fo = self.config_data.get('detected_field_order')
        if prior_fo and prior_fo not in ('unknown', ''):
            initial_badge = "  ✓ Auto-Detected: " + prior_fo.upper()
        else:
            initial_badge = "  ✓ TFF (AVCHD/HDV standard)"
        badge_color = '#22CC66'
        self._fo_badge_lbl = tk.Label(fo_row, text=initial_badge,
                                      font=('Segoe UI', 11, 'bold'),
                                      fg=badge_color, bg=Colors.BG_MAIN)
        self._fo_badge_lbl.pack(side='right')

        # HD sources default to TFF — pre-select it
        initial_fo = self.config_data.get('field_order',
                     self.config_data.get('detected_field_order', 'tff'))
        self.config_data['field_order'] = initial_fo
        self.field_var = tk.StringVar(value=initial_fo)

        fo_card = tk.Frame(self.page_container, bg=Colors.BG_CARD)
        fo_card.pack(fill='x')
        ModernRadioButton(fo_card, "TFF — Top Field First",
                          self.field_var, "tff",
                          "Standard for all AVCHD and HDV cameras").pack(fill='x')
        ttk.Separator(fo_card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(fo_card, "BFF — Bottom Field First",
                          self.field_var, "bff",
                          "Uncommon for HD — only select if you have confirmed otherwise").pack(fill='x')
        ttk.Separator(fo_card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(fo_card, "Progressive (no deinterlacing needed)",
                          self.field_var, "progressive",
                          "Video was already progressive — no deinterlacing applied").pack(fill='x')

        self.field_var.trace_add('write',
            lambda *_: self.config_data.update({'field_order': self.field_var.get()}))

        # Note about HD field order universally being TFF
        tk.Label(self.page_container,
                 text="AVCHD and HDV sources are universally Top Field First (TFF). "
                      "Only change this if you have confirmed otherwise.",
                 font=('Segoe UI', 10), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
                 wraplength=620, justify='left').pack(anchor='w', pady=(6, 0))

        if num_files <= 1:
            rerun_row = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
            rerun_row.pack(anchor='w', pady=(8, 0))
            ModernButton(rerun_row, "Re-run Detection",
                         self._run_field_order_detection, width=150).pack(side='left')
            # Wire badge label so _run_field_order_detection / _show_detection_result
            # can update it exactly as they do for the SD page.
            self.detect_badge_lbl = self._fo_badge_lbl

        # ════════════════════════════════════════════════════════════════════
        # 4 — TELECINE / INVERSE TELECINE DETECTION
        # ════════════════════════════════════════════════════════════════════
        ttk.Separator(self.page_container, orient='horizontal').pack(fill='x', pady=(20, 0))

        ivtc_row = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        ivtc_row.pack(fill='x', pady=(12, 6))
        tk.Label(ivtc_row, text="4. Telecine / Pulldown Detection",
                 font=('Segoe UI', 13, 'bold'),
                 fg=Colors.ACCENT, bg=Colors.BG_MAIN).pack(side='left')

        prior_ivtc = self.config_data.get('ivtc_result')
        if prior_ivtc:
            if prior_ivtc.get('dv_bypass'):
                _ivtc_badge_text = '  ✓ Not applicable (DV source)'
                _ivtc_badge_color = Colors.SUCCESS
            elif prior_ivtc.get('detected'):
                _ivtc_badge_text = "  ⚠  Telecine detected (" + prior_ivtc['pattern'] + ")"
                _ivtc_badge_color = Colors.WARNING
            else:
                _ivtc_badge_text = '  ✓ No telecine detected'
                _ivtc_badge_color = Colors.SUCCESS
        else:
            _ivtc_badge_text = '  ⏳ Analyzing…'
            _ivtc_badge_color = Colors.ACCENT

        self._ivtc_badge = tk.Label(ivtc_row, text=_ivtc_badge_text,
                                     font=('Segoe UI', 11, 'bold'),
                                     fg=_ivtc_badge_color, bg=Colors.BG_MAIN)
        self._ivtc_badge.pack(side='right')

        tk.Label(
            self.page_container,
            text="Telecine (3:2 pulldown) is applied when film is transferred to interlaced video. "
                 "If detected, VCG can apply Inverse Telecine (IVTC) to restore the original "
                 "progressive frame rate instead of running standard deinterlacing.",
            font=('Segoe UI', 11), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
            wraplength=620, justify='left').pack(anchor='w', pady=(0, 8))

        # Container frames for detection result — populated by _show_ivtc_result
        self._ivtc_result_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        self._ivtc_result_frame.pack(fill='x')

        self._ivtc_mode_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        self._ivtc_mode_frame.pack(fill='x')

        if prior_ivtc:
            self.after(0, lambda: self._show_ivtc_result(prior_ivtc))

        if num_files <= 1:
            self.after(600, self._run_ivtc_detection)

        # ════════════════════════════════════════════════════════════════════
        # 5 — SOURCE COLOR MATRIX
        # ════════════════════════════════════════════════════════════════════
        ttk.Separator(self.page_container, orient='horizontal').pack(fill='x', pady=(20, 0))

        matrix_hdr_hd = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        matrix_hdr_hd.pack(fill='x', pady=(12, 6))
        tk.Label(matrix_hdr_hd, text="5. Source Color Matrix",
                 font=('Segoe UI', 13, 'bold'),
                 fg=Colors.ACCENT, bg=Colors.BG_MAIN).pack(side='left')
        tk.Label(matrix_hdr_hd, text="  ✓ Auto-selected for HD",
                 font=('Segoe UI', 11, 'bold'),
                 fg='#22CC66', bg=Colors.BG_MAIN).pack(side='right')

        tk.Label(self.page_container,
                 text="Determines how colours are decoded from the video signal. "
                      "HD sources use BT.709 — only change this for unusual sources.",
                 font=('Segoe UI', 11), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
                 wraplength=620, justify='left').pack(anchor='w', pady=(0, 8))

        _matrix_choices_hd = [
            ("High Definition — BT.709 (recommended)", 'bt709'),
            ("Standard Definition / VHS capture — BT.601", 'bt601'),
        ]
        _matrix_labels_hd = [lbl for lbl, _ in _matrix_choices_hd]
        _matrix_values_hd = {lbl: val for lbl, val in _matrix_choices_hd}
        _matrix_labels_inv_hd = {val: lbl for lbl, val in _matrix_choices_hd}

        # HD default is bt709; honour a previously saved value if present
        _initial_matrix_hd = self.config_data.get('color_matrix', 'bt709')
        if _initial_matrix_hd not in ('bt709', 'bt601'):
            _initial_matrix_hd = 'bt709'
        self.config_data['color_matrix'] = _initial_matrix_hd
        _initial_label_hd = _matrix_labels_inv_hd.get(_initial_matrix_hd, _matrix_labels_hd[0])

        self._matrix_var_hd = tk.StringVar(value=_initial_label_hd)

        matrix_card_hd = tk.Frame(self.page_container, bg=Colors.BG_CARD)
        matrix_card_hd.pack(fill='x')
        inner_hd = tk.Frame(matrix_card_hd, bg=Colors.BG_CARD)
        inner_hd.pack(fill='x', padx=14, pady=10)
        tk.Label(inner_hd, text="Source type:", font=('Segoe UI', 11),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD).pack(side='left')
        matrix_dd_hd = ttk.Combobox(inner_hd, textvariable=self._matrix_var_hd,
                                     values=_matrix_labels_hd, state='readonly', width=52)
        matrix_dd_hd.pack(side='left', padx=(10, 0))

        def _on_matrix_hd(*_):
            chosen = _matrix_values_hd.get(self._matrix_var_hd.get(), 'bt709')
            self.config_data['color_matrix'] = chosen

        self._matrix_var_hd.trace_add('write', _on_matrix_hd)

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 3 — Y/C DELAY CORRECTION  (Feature 1)
    # ══════════════════════════════════════════════════════════════════════════

    # ==================== TRIM / SEGMENT EXPORT (Advanced ⓪) ====================

    def _trim_fps_value(self):
        """Exact source frame rate used for all trim frame↔time math.

        Must match the fpsnum/fpsden forced at the decoder in
        generate_vpy_script so audio cut times line up with video frames.
        """
        if self.config_data.get('format', 'ntsc') == 'pal':
            return 25.0
        return 30000.0 / 1001.0

    def _trim_fmt_tc(self, frame):
        """Format a source frame number as H:MM:SS.ff (ff = frame within second).

        ff is defined as frame − round(whole_seconds × fps) so that
        _trim_parse_tc is an exact inverse — with NTSC's 29.97 fps a
        naive fractional-second calculation drifts by one frame.
        """
        fps = self._trim_fps_value()
        secs = int(frame / fps)
        ff = int(frame) - int(round(secs * fps))
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        return f"{h}:{m:02d}:{s:02d}.{ff:02d}"

    def _trim_parse_tc(self, text):
        """Parse 'H:MM:SS.ff', 'MM:SS.ff', 'MM:SS' or plain seconds → frame number.

        The part after '.' is a frame count within the second, not decimals.
        Returns None on invalid input.
        """
        text = (text or '').strip()
        if not text:
            return None
        fps = self._trim_fps_value()
        try:
            frames = 0
            if '.' in text:
                text, ff_part = text.rsplit('.', 1)
                frames = int(ff_part) if ff_part else 0
            parts = [int(p) for p in text.split(':')]
            if not parts or len(parts) > 3:
                return None
            secs = 0
            for p in parts:
                if p < 0:
                    return None
                secs = secs * 60 + p
            return int(round(secs * fps)) + frames
        except (ValueError, TypeError):
            return None

    def _get_trim_plan(self):
        """Compute the final export plan from the Trim page selections.

        Returns None when trimming is not in effect (entire-video mode, batch,
        no segments, or a selection equivalent to the whole file).  Otherwise::

            {'ranges': [(first, last), ...],   # inclusive SOURCE frames to KEEP
             'output': 'join' | 'separate'}

        'ranges' can be empty when a cut selection removes everything —
        _validate_trim blocks that before processing can start.
        """
        if self.config_data.get('trim_mode', 'full') == 'full':
            return None
        segs = self.config_data.get('trim_segments') or []
        if len(self.config_data.get('input_files', [])) > 1 or not segs:
            return None
        total = int(self.config_data.get('trim_total_frames') or 0)

        # Sort and merge overlapping / adjacent segments
        segs = sorted((int(a), int(b)) for a, b in segs)
        merged = []
        for a, b in segs:
            if merged and a <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(merged[-1][1], b))
            else:
                merged.append((a, b))

        if self.config_data.get('trim_mode', 'keep') == 'keep':
            ranges = merged
        else:
            # Cut mode → keep the complement over [0, total-1]
            ranges = []
            pos = 0
            for a, b in merged:
                if a > pos:
                    ranges.append((pos, a - 1))
                pos = max(pos, b + 1)
            if total and pos <= total - 1:
                ranges.append((pos, total - 1))

        # A single range spanning the whole file is the same as no trim
        if total and ranges == [(0, total - 1)]:
            return None
        return {'ranges': ranges,
                'output': self.config_data.get('trim_output', 'join')}

    def _validate_trim(self):
        """Block leaving the Trim page when the selection would export nothing."""
        segs = self.config_data.get('trim_segments') or []
        if not segs:
            return True
        plan = self._get_trim_plan()
        if plan is not None and not plan['ranges']:
            messagebox.showwarning(
                "Nothing to Export",
                "Your cut segments remove the entire video, so there is "
                "nothing left to export.\n\n"
                "Delete a segment, or switch to Keep mode.")
            return False
        return True

    def _page_trim(self):
        """Advanced ⓪ — Trim / Segment Export: pick parts to keep or cut (single file)."""
        files = self.config_data.get('input_files', [])
        if not files and 'input_path' in self.config_data:
            files = [self.config_data['input_path']]

        tk.Label(self.page_container, text="Trim / Segment Export",
                 font=('Segoe UI', 22, 'bold'),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')
        tk.Label(self.page_container,
                 text="Export the whole capture, export only part of it, or cut "
                      "unwanted sections out of it.",
                 font=('Segoe UI', 13),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
                 wraplength=640, justify='left').pack(anchor='w', pady=(4, 12))

        # Safety net — navigation skips this page for batches, but render a
        # friendly notice if it is ever reached with more than one file.
        if len(files) != 1:
            card = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=16, pady=14)
            card.pack(fill='x', pady=(8, 0))
            tk.Label(card, text="🎬  Single-file feature",
                     font=('Segoe UI', 12, 'bold'),
                     fg=Colors.ACCENT, bg=Colors.BG_CARD).pack(anchor='w')
            tk.Label(card,
                     text="Trimming is only available when exactly one file is selected. "
                          "Every file in this batch will be processed in full.",
                     font=('Segoe UI', 11), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                     wraplength=580, justify='left').pack(anchor='w', pady=(5, 0))
            return

        filepath = files[0]
        self._trim_total = int(self.config_data.get('trim_total_frames') or 0)
        self._trim_pending_start = None
        self._trim_preview_gen = 0
        self._trim_preview_after = None
        self.config_data.setdefault('trim_segments', [])
        self.config_data.setdefault('trim_mode', 'full')
        self.config_data.setdefault('trim_output', 'join')

        # ── Mode: entire video vs keep vs cut ───────────────────────────────
        mode_card = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=4, pady=4)
        mode_card.pack(fill='x')
        self._trim_mode_var = tk.StringVar(value=self.config_data['trim_mode'])
        ModernRadioButton(
            mode_card, "Output entire video — no trimming",
            self._trim_mode_var, 'full',
            "The whole capture is exported from start to finish. Choose this "
            "if you don't want to cut anything out."
        ).pack(fill='x')
        ttk.Separator(mode_card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(
            mode_card, "Keep mode — segments you mark are exported",
            self._trim_mode_var, 'keep',
            "Mark the good parts. Everything outside your segments is discarded."
        ).pack(fill='x')
        ttk.Separator(mode_card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(
            mode_card, "Cut mode — segments you mark are removed",
            self._trim_mode_var, 'cut',
            "Mark the bad parts (static, blank tape, private moments). "
            "Everything outside your segments is exported."
        ).pack(fill='x')

        # All trim controls live in one container so "Output entire video"
        # mode can show/hide them together.
        trim_body = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        if self._trim_mode_var.get() != 'full':
            trim_body.pack(fill='x')

        # ── Preview + scrubber ──────────────────────────────────────────────
        prev_card = tk.Frame(trim_body, bg=Colors.BG_CARD, padx=14, pady=12)
        prev_card.pack(fill='x', pady=(10, 0))

        prev_canvas = tk.Canvas(prev_card, width=480, height=280,
                                bg=Colors.BG_DARK, highlightthickness=1,
                                highlightbackground=Colors.BORDER)
        prev_canvas.pack()
        self._trim_preview_canvas = prev_canvas

        status_lbl = tk.Label(prev_card, text="⏳ Reading video duration…",
                              font=('Segoe UI', 10), fg=Colors.ACCENT,
                              bg=Colors.BG_CARD)
        status_lbl.pack(pady=(4, 0))

        # Position slider (frames) — configured once the duration probe returns
        self._trim_pos_var = tk.IntVar(value=0)
        pos_slider = tk.Scale(prev_card, from_=0, to=1, orient='horizontal',
                              variable=self._trim_pos_var, length=620,
                              showvalue=False, state='disabled',
                              bg=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY,
                              highlightthickness=0, troughcolor=Colors.BG_DARK,
                              activebackground=Colors.ACCENT)
        pos_slider.pack(fill='x', pady=(8, 0))

        # Timeline bar — segments drawn green (keep) or red (cut) + playhead
        timeline = tk.Canvas(prev_card, height=20, bg=Colors.BG_CARD,
                             highlightthickness=0)
        timeline.pack(fill='x', pady=(2, 4))
        self._trim_timeline = timeline

        # Current-position readout + timecode entry
        tc_row = tk.Frame(prev_card, bg=Colors.BG_CARD)
        tc_row.pack(fill='x', pady=(2, 0))
        pos_lbl = tk.Label(tc_row, text="Position: 0:00:00.00",
                           font=('Consolas', 12, 'bold'),
                           fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD)
        pos_lbl.pack(side='left')
        tk.Label(tc_row, text="Go to:", font=('Segoe UI', 10),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD).pack(side='left', padx=(20, 4))
        tc_entry = tk.Entry(tc_row, width=12, font=('Consolas', 11),
                            bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                            insertbackground=Colors.TEXT_PRIMARY,
                            relief='flat', highlightthickness=1,
                            highlightbackground=Colors.BORDER,
                            highlightcolor=Colors.ACCENT)
        tc_entry.pack(side='left', ipady=2)

        def _goto_tc(*_):
            frame = self._trim_parse_tc(tc_entry.get())
            if frame is None or not self._trim_total:
                return
            self._trim_pos_var.set(max(0, min(frame, self._trim_total - 1)))
        tc_entry.bind('<Return>', lambda e: (_goto_tc(), 'break')[1])
        ModernButton(tc_row, "Go", _goto_tc, width=44, height=26).pack(side='left', padx=(6, 0))
        tk.Label(tc_row, text="H:MM:SS.frames", font=('Segoe UI', 9),
                 fg=Colors.TEXT_HINT, bg=Colors.BG_CARD).pack(side='left', padx=(8, 0))
        dur_lbl = tk.Label(tc_row, text="", font=('Consolas', 11),
                           fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD)
        dur_lbl.pack(side='right')

        # Step buttons — frame-accurate nudging
        step_row = tk.Frame(prev_card, bg=Colors.BG_CARD)
        step_row.pack(pady=(8, 0))

        def _nudge(frames):
            if not self._trim_total:
                return
            cur = self._trim_pos_var.get()
            self._trim_pos_var.set(max(0, min(cur + frames, self._trim_total - 1)))

        fps_i = int(round(self._trim_fps_value()))
        for label, delta in [("−10s", -10 * fps_i), ("−1s", -fps_i), ("−1 frame", -1),
                             ("+1 frame", 1), ("+1s", fps_i), ("+10s", 10 * fps_i)]:
            ModernButton(step_row, label, lambda d=delta: _nudge(d),
                         width=76, height=28).pack(side='left', padx=3)

        # ── Mark segment ────────────────────────────────────────────────────
        mark_row = tk.Frame(prev_card, bg=Colors.BG_CARD)
        mark_row.pack(pady=(10, 0))

        pending_lbl = tk.Label(prev_card, text="",
                               font=('Segoe UI', 10),
                               fg=Colors.WARNING, bg=Colors.BG_CARD)
        pending_lbl.pack(pady=(4, 0))

        def _set_start():
            self._trim_pending_start = self._trim_pos_var.get()
            pending_lbl.config(
                text=f"Start set at {self._trim_fmt_tc(self._trim_pending_start)} — "
                     f"scrub to the end point and click Set End.")

        def _set_end():
            if self._trim_pending_start is None:
                messagebox.showinfo("Set Start First",
                                    "Click 'Set Start' at the beginning of the "
                                    "segment before setting its end.",
                                    parent=self)
                return
            start = self._trim_pending_start
            end = self._trim_pos_var.get()
            if end <= start:
                messagebox.showwarning("Invalid Segment",
                                       "The end point must be after the start point.",
                                       parent=self)
                return
            self.config_data['trim_segments'].append([start, end])
            self._trim_pending_start = None
            pending_lbl.config(text="")
            _refresh_segments()
            _redraw_timeline()

        ModernButton(mark_row, "⇤ Set Start", _set_start, width=110, height=32).pack(side='left', padx=4)
        ModernButton(mark_row, "Set End ⇥", _set_end, primary=True, width=110, height=32).pack(side='left', padx=4)

        # ── Segment list ────────────────────────────────────────────────────
        seg_card = tk.Frame(trim_body, bg=Colors.BG_CARD, padx=14, pady=12)
        seg_card.pack(fill='x', pady=(10, 0))
        seg_head = tk.Frame(seg_card, bg=Colors.BG_CARD)
        seg_head.pack(fill='x')
        seg_title = tk.Label(seg_head, text="Segments",
                             font=('Segoe UI', 12, 'bold'),
                             fg=Colors.ACCENT, bg=Colors.BG_CARD)
        seg_title.pack(side='left')

        def _clear_all():
            if not self.config_data['trim_segments']:
                return
            if messagebox.askyesno("Clear All Segments",
                                   "Remove all segments?", parent=self):
                self.config_data['trim_segments'] = []
                _refresh_segments()
                _redraw_timeline()
        ModernButton(seg_head, "Clear All", _clear_all, width=90, height=26).pack(side='right')

        seg_list = tk.Frame(seg_card, bg=Colors.BG_CARD)
        seg_list.pack(fill='x', pady=(6, 0))

        def _refresh_segments():
            if not seg_list.winfo_exists():
                return
            for w in seg_list.winfo_children():
                w.destroy()
            segs = self.config_data['trim_segments']
            mode = self._trim_mode_var.get()
            seg_title.config(
                text=f"Segments to {'keep' if mode == 'keep' else 'cut'}  ({len(segs)})")
            if not segs:
                tk.Label(seg_list,
                         text="No segments yet — the whole file will be exported.",
                         font=('Segoe UI', 11), fg=Colors.TEXT_SECONDARY,
                         bg=Colors.BG_CARD).pack(anchor='w', pady=(2, 2))
                return
            for i, (s, e) in enumerate(segs):
                row = tk.Frame(seg_list, bg=Colors.BG_CARD)
                row.pack(fill='x', pady=1)
                icon = "✅" if mode == 'keep' else "✂"
                dur = self._trim_fmt_tc(e - s + 1)
                tk.Label(row,
                         text=f"{icon}  Segment {i + 1}:  "
                              f"{self._trim_fmt_tc(s)}  →  {self._trim_fmt_tc(e)}"
                              f"   (length {dur})",
                         font=('Consolas', 11), fg=Colors.TEXT_PRIMARY,
                         bg=Colors.BG_CARD).pack(side='left')

                def _remove(idx=i):
                    del self.config_data['trim_segments'][idx]
                    _refresh_segments()
                    _redraw_timeline()
                ModernButton(row, "✕", _remove, width=30, height=24).pack(side='right')

        # ── Output: join vs separate files ──────────────────────────────────
        out_card = tk.Frame(trim_body, bg=Colors.BG_CARD, padx=4, pady=4)
        out_card.pack(fill='x', pady=(10, 0))
        self._trim_output_var = tk.StringVar(value=self.config_data['trim_output'])
        ModernRadioButton(
            out_card, "Join into one file",
            self._trim_output_var, 'join',
            "The kept parts are spliced together into a single output video."
        ).pack(fill='x')
        ttk.Separator(out_card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(
            out_card, "One file per segment",
            self._trim_output_var, 'separate',
            "Each kept part becomes its own output file (…_part01, _part02, …)."
        ).pack(fill='x')

        # ── Timeline drawing ────────────────────────────────────────────────
        def _redraw_timeline(*_):
            if not timeline.winfo_exists():
                return
            timeline.delete('all')
            w = timeline.winfo_width()
            if w < 10:
                w = 620
            timeline.create_rectangle(0, 5, w, 15, fill=Colors.BG_DARK,
                                      outline=Colors.BORDER)
            total = max(1, self._trim_total)
            mode = self._trim_mode_var.get()
            color = Colors.SUCCESS if mode == 'keep' else Colors.ERROR
            for s, e in self.config_data['trim_segments']:
                x1 = int(s / total * w)
                x2 = max(x1 + 2, int((e + 1) / total * w))
                timeline.create_rectangle(x1, 5, x2, 15, fill=color, outline='')
            # Playhead
            x = int(self._trim_pos_var.get() / total * w)
            timeline.create_line(x, 0, x, 20, fill=Colors.ACCENT, width=2)
        timeline.bind('<Configure>', _redraw_timeline)

        # ── Preview extraction (debounced, background thread) ───────────────
        def _show_preview(gen, img):
            if gen != self._trim_preview_gen or not prev_canvas.winfo_exists():
                return
            if img is None:
                status_lbl.config(text="⚠ Could not extract preview frame")
                return
            fw, fh = img.size
            scale = min(480 / fw, 280 / fh)
            thumb = img.resize((int(fw * scale), int(fh * scale)), Image.LANCZOS)
            photo = ImageTk.PhotoImage(thumb)
            prev_canvas._vcg_photo = photo
            prev_canvas.delete('all')
            prev_canvas.create_image(240, 140, image=photo)
            status_lbl.config(text="")

        def _load_preview():
            self._trim_preview_after = None
            self._trim_preview_gen += 1
            gen = self._trim_preview_gen
            secs = self._trim_pos_var.get() / self._trim_fps_value()

            def _worker():
                img = None
                path = extract_preview_frame_at_time(filepath, secs, tag=gen % 4)
                if path and HAS_PIL:
                    try:
                        img = Image.open(path).convert('RGB')
                        img.load()
                    except Exception:
                        img = None
                try:
                    self.after(0, lambda: _show_preview(gen, img))
                except Exception:
                    pass
            threading.Thread(target=_worker, daemon=True).start()

        def _on_pos_change(*_):
            if not pos_lbl.winfo_exists():
                return
            pos_lbl.config(text=f"Position: {self._trim_fmt_tc(self._trim_pos_var.get())}")
            _redraw_timeline()
            if self._trim_preview_after is not None:
                self.after_cancel(self._trim_preview_after)
            self._trim_preview_after = self.after(250, _load_preview)
        self._trim_pos_var.trace_add('write', _on_pos_change)

        # ── Persist mode/output changes ─────────────────────────────────────
        def _on_mode_change(*_):
            mode = self._trim_mode_var.get()
            self.config_data['trim_mode'] = mode
            if trim_body.winfo_exists():
                if mode == 'full':
                    trim_body.pack_forget()
                elif not trim_body.winfo_ismapped():
                    trim_body.pack(fill='x')
            if seg_list.winfo_exists():
                _refresh_segments()
                _redraw_timeline()
        self._trim_mode_var.trace_add('write', _on_mode_change)
        self._trim_output_var.trace_add(
            'write',
            lambda *_: self.config_data.update({'trim_output': self._trim_output_var.get()}))

        # ── Duration probe (background) ─────────────────────────────────────
        def _apply_probe(total_frames):
            if not pos_slider.winfo_exists():
                return
            if total_frames <= 0:
                status_lbl.config(text="⚠ Could not read video duration — trimming unavailable")
                return
            self._trim_total = total_frames
            self.config_data['trim_total_frames'] = total_frames
            self.config_data['trim_fps'] = self._trim_fps_value()
            pos_slider.config(state='normal', to=total_frames - 1)
            dur_lbl.config(text=f"Length: {self._trim_fmt_tc(total_frames)}  "
                                f"({total_frames} frames)")
            status_lbl.config(text="⏳ Loading preview…")
            _redraw_timeline()
            _load_preview()

        def _probe():
            info = get_video_info(filepath)
            duration = info['duration'] if info else 0
            total = int(round(duration * self._trim_fps_value()))
            try:
                self.after(0, lambda: _apply_probe(total))
            except Exception:
                pass

        _refresh_segments()
        if self._trim_total > 0:
            _apply_probe(self._trim_total)
        else:
            threading.Thread(target=_probe, daemon=True).start()

    def _page_yc_delay(self):
        """Step 5 (Advanced ①) — Y/C Delay (chroma horizontal shift) per file."""
        files = self.config_data.get('input_files', [])
        if not files and 'input_path' in self.config_data:
            files = [self.config_data['input_path']]

        # Initialise per-file settings storage
        if 'per_file_settings' not in self.config_data:
            self.config_data['per_file_settings'] = {}
        for fp in files:
            self.config_data['per_file_settings'].setdefault(fp, {})

        self._yc_files = files
        self._yc_file_idx = 0
        self._yc_src_img = None   # PIL Image of the current preview frame
        self._render_yc_page()

    def _render_yc_page(self):
        """(Re-)build the Y/C Delay page for the current file index."""
        self._clear_page()
        files = self._yc_files
        if not files:
            tk.Label(self.page_container, text="No files selected.",
                     font=('Segoe UI', 13), fg=Colors.ERROR,
                     bg=Colors.BG_MAIN).pack(anchor='w', pady=20)
            return

        current_file = files[self._yc_file_idx]
        per_file = self.config_data['per_file_settings'][current_file]
        current_delay = per_file.get('yc_delay', 0)

        # ── Page title ──────────────────────────────────────────────────────
        tk.Label(self.page_container, text="Y/C Delay Correction",
                 font=('Segoe UI', 22, 'bold'),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')

        if len(files) > 1:
            tk.Label(self.page_container,
                     text=f"File {self._yc_file_idx + 1} of {len(files)}: "
                          f"{os.path.basename(current_file)}",
                     font=('Segoe UI', 12, 'bold'),
                     fg=Colors.ACCENT, bg=Colors.BG_MAIN).pack(anchor='w', pady=(4, 0))

        # ── Info card ──────────────────────────────────────────────────────
        info = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=15, pady=12)
        info.pack(fill='x', pady=(12, 8))
        tk.Label(info, text="What is Y/C Delay?",
                 font=('Segoe UI', 11, 'bold'),
                 fg=Colors.ACCENT, bg=Colors.BG_CARD).pack(anchor='w')
        tk.Label(
            info,
            text="Y/C delay is a horizontal misalignment between the luma (Y) brightness "
                 "signal and the chroma (C) colour signal. It is common with analog composite "
                 "formats (VHS, Hi8) and worsens with multigenerational copies or worn tapes. "
                 "It appears as a coloured fringe — usually red/cyan or blue/yellow — "
                 "on sharp vertical edges.\n\n"
                 "Adjust the slider until the coloured fringe on vertical edges disappears. "
                 "Use the zoom region to spot subtle misalignment. Typical values: −3 to +3 px.",
            font=('Segoe UI', 11), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
            wraplength=580, justify='left').pack(anchor='w', pady=(5, 0))

        # ── Preview row: full frame + zoom region ──────────────────────────
        prev_outer = tk.Frame(self.page_container, bg=Colors.BG_CARD)
        prev_outer.pack(fill='x', pady=(8, 4))

        prev_row = tk.Frame(prev_outer, bg=Colors.BG_CARD)
        prev_row.pack(padx=10, pady=10, anchor='w')

        # Full frame canvas
        full_col = tk.Frame(prev_row, bg=Colors.BG_CARD)
        full_col.pack(side='left', padx=(0, 12))
        tk.Label(full_col, text="Preview (frame 200)",
                 font=('Segoe UI', 9, 'bold'), fg=Colors.TEXT_SECONDARY,
                 bg=Colors.BG_CARD).pack(anchor='w', pady=(0, 3))
        full_canvas = tk.Canvas(full_col, width=400, height=240,
                                bg=Colors.BG_DARK, highlightthickness=1,
                                highlightbackground=Colors.BORDER)
        full_canvas.pack()

        # Zoom region canvas
        zoom_col = tk.Frame(prev_row, bg=Colors.BG_CARD)
        zoom_col.pack(side='left')
        tk.Label(zoom_col, text="Zoom — centre region (shows chroma fringing)",
                 font=('Segoe UI', 9, 'bold'), fg=Colors.TEXT_SECONDARY,
                 bg=Colors.BG_CARD).pack(anchor='w', pady=(0, 3))
        zoom_canvas = tk.Canvas(zoom_col, width=280, height=240,
                                bg=Colors.BG_DARK, highlightthickness=1,
                                highlightbackground=Colors.BORDER)
        zoom_canvas.pack()
        tk.Label(zoom_col,
                 text="Live preview updates as you move the slider",
                 font=('Segoe UI', 8), fg=Colors.TEXT_HINT,
                 bg=Colors.BG_CARD).pack(anchor='w', pady=(3, 0))

        loading_lbl = tk.Label(prev_outer, text="⏳ Loading preview frame…",
                               font=('Segoe UI', 10), fg=Colors.ACCENT,
                               bg=Colors.BG_CARD)
        loading_lbl.pack(pady=(0, 6))

        # ── Slider ─────────────────────────────────────────────────────────
        sl_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        sl_frame.pack(fill='x', pady=(8, 0))

        tk.Label(sl_frame, text="Chroma Horizontal Shift",
                 font=('Segoe UI', 13, 'bold'),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')
        tk.Label(sl_frame, text="Range: −20 to +20 pixels.  Negative = shift chroma left;  "
                                "Positive = shift chroma right.",
                 font=('Segoe UI', 10), fg=Colors.TEXT_SECONDARY,
                 bg=Colors.BG_MAIN).pack(anchor='w', pady=(2, 6))

        sl_row = tk.Frame(sl_frame, bg=Colors.BG_MAIN)
        sl_row.pack(fill='x')
        tk.Label(sl_row, text="−20", font=('Segoe UI', 10),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(side='left')

        self._yc_var = tk.IntVar(value=current_delay)
        slider = tk.Scale(sl_row, from_=-20, to=20, orient='horizontal',
                          variable=self._yc_var, length=420, showvalue=True,
                          bg=Colors.BG_MAIN, fg=Colors.TEXT_PRIMARY,
                          highlightthickness=0, troughcolor=Colors.BG_CARD,
                          activebackground=Colors.ACCENT,
                          font=('Segoe UI', 10))
        slider.pack(side='left', padx=(8, 8))
        tk.Label(sl_row, text="+20", font=('Segoe UI', 10),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(side='left')

        val_lbl = tk.Label(sl_frame,
                           text=f"Current value: {current_delay:+d} px",
                           font=('Segoe UI', 11),
                           fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN)
        val_lbl.pack(anchor='w', pady=(4, 0))

        # ── Buttons ─────────────────────────────────────────────────────────
        btn_row = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        btn_row.pack(fill='x', pady=(10, 0))

        def _reset():
            self._yc_var.set(0)

        ModernButton(btn_row, "Reset to 0", _reset, width=100).pack(side='left')

        if len(files) > 1:
            if self._yc_file_idx < len(files) - 1:
                def _next_file():
                    self._yc_save_value()
                    self._yc_file_idx += 1
                    self._render_yc_page()
                ModernButton(btn_row, "Next File →",
                             _next_file, primary=True, width=120).pack(
                    side='left', padx=(10, 0))
            if self._yc_file_idx > 0:
                def _prev_file():
                    self._yc_save_value()
                    self._yc_file_idx -= 1
                    self._render_yc_page()
                ModernButton(btn_row, "← Prev File",
                             _prev_file, width=110).pack(side='left', padx=(10, 0))

        # ── Wire up slider changes ──────────────────────────────────────────
        def _on_slider(*_):
            val = self._yc_var.get()
            val_lbl.config(text=f"Current value: {val:+d} px")
            self._yc_save_value()
            if self._yc_src_img is not None and HAS_PIL:
                self._update_yc_zoom(zoom_canvas, self._yc_src_img, val)

        self._yc_var.trace_add('write', _on_slider)

        # ── Load preview frame in background ───────────────────────────────
        def _load():
            path = extract_preview_frame(current_file)
            if path:
                self.temp_images.append(path)
                self.after(0, lambda p=path: self._show_yc_full(
                    full_canvas, zoom_canvas, loading_lbl, p, self._yc_var.get()))
            else:
                self.after(0, lambda: loading_lbl.config(
                    text="⚠ Could not extract preview frame"))

        threading.Thread(target=_load, daemon=True).start()

    def _yc_save_value(self):
        """Persist current slider value to per-file settings."""
        if not hasattr(self, '_yc_files') or not self._yc_files:
            return
        fp = self._yc_files[self._yc_file_idx]
        self.config_data['per_file_settings'][fp]['yc_delay'] = self._yc_var.get()

    def _show_yc_full(self, full_canvas, zoom_canvas, loading_lbl, path, initial_delay):
        """Display the full preview frame and initial zoom region."""
        if not HAS_PIL:
            loading_lbl.config(text="(PIL not available — install Pillow for preview)")
            return
        try:
            img = Image.open(path).convert('RGB')
            self._yc_src_img = img

            # Full frame → fit into 400×240
            fw, fh = img.size
            scale = min(400 / fw, 240 / fh)
            display_w, display_h = int(fw * scale), int(fh * scale)
            thumb = img.resize((display_w, display_h), Image.LANCZOS)
            photo = ImageTk.PhotoImage(thumb)
            full_canvas._vcg_photo = photo
            full_canvas.delete('all')
            full_canvas.create_image(200, 120, image=photo)

            loading_lbl.config(text="")
            self._update_yc_zoom(zoom_canvas, img, initial_delay)
        except Exception as exc:
            loading_lbl.config(text=f"Preview error: {exc}")

    def _update_yc_zoom(self, zoom_canvas, src_img, yc_delay):
        """Render the zoom region with simulated chroma shift.

        Uses PIL ImageChops.offset (no numpy required).  Numpy is used when
        available for a marginally faster roll, but PIL alone is sufficient.
        """
        if not HAS_PIL:
            return
        try:
            from PIL import ImageChops
            w, h = src_img.size
            # Crop centre 30% width × 50% height
            cw, ch = max(80, w // 3), max(60, h // 2)
            cx, cy = w // 2, h // 2
            region = src_img.crop((cx - cw // 2, cy - ch // 2,
                                   cx + cw // 2, cy + ch // 2))
            # Simulate chroma shift: split YCbCr, offset Cb and Cr horizontally
            ycbcr = region.convert('YCbCr')
            y_ch, cb_ch, cr_ch = ycbcr.split()
            if yc_delay != 0:
                cb_ch = ImageChops.offset(cb_ch, yc_delay, 0)
                cr_ch = ImageChops.offset(cr_ch, yc_delay, 0)
            shifted = Image.merge('YCbCr', (y_ch, cb_ch, cr_ch)).convert('RGB')
            zoom = shifted.resize((280, 240), Image.NEAREST)
            photo = ImageTk.PhotoImage(zoom)
            zoom_canvas._vcg_photo = photo
            zoom_canvas.delete('all')
            zoom_canvas.create_image(140, 120, image=photo)
        except Exception as _e:
            zoom_canvas.delete('all')
            zoom_canvas.create_text(140, 120, text=f"Zoom error: {_e}",
                                    fill=Colors.TEXT_SECONDARY,
                                    font=('Segoe UI', 9), width=260)

    # ══════════════════════════════════════════════════════════════════════════
    # STEP 4 — CROP PRESET  (Features 3 & 4)
    # ══════════════════════════════════════════════════════════════════════════

    def _page_crop_preset(self):
        """Step 4 — Crop Preset selector."""
        capture_method = self.config_data.get('capture_method', 'sd')
        video_format   = self.config_data.get('format', 'ntsc')
        files = self.config_data.get('input_files', [])
        if not files and 'input_path' in self.config_data:
            files = [self.config_data['input_path']]
        num_files = len(files)

        detected_sar = self.config_data.get('detected_sar', '')
        is_widescreen = detected_sar in ('64:45', '32:27')

        # Default preset: DV / DVD / widescreen → none; SD analog → bt601
        if 'crop_preset' not in self.config_data:
            if capture_method in ('dv', 'dvd') or is_widescreen:
                self.config_data['crop_preset'] = 'none'
            else:
                self.config_data['crop_preset'] = 'bt601'

        # ── Page title ──────────────────────────────────────────────────────
        tk.Label(self.page_container, text="Crop Options",
                 font=('Segoe UI', 22, 'bold'),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')
        tk.Label(self.page_container,
                 text="Choose how VCG crops the edges of your video.",
                 font=('Segoe UI', 13), fg=Colors.TEXT_SECONDARY,
                 bg=Colors.BG_MAIN).pack(anchor='w', pady=(2, 12))

        # ── Recommendation banner ───────────────────────────────────────────
        if capture_method == 'dv':
            rec_label = "Option 4 — No Crop"
            rec_body  = ("Recommended for DV/MiniDV captures. Digital recordings have no "
                         "tape overscan; cropping is not needed.")
        elif capture_method == 'dvd' or is_widescreen:
            rec_label = "Option 4 — No Crop"
            if is_widescreen:
                rec_body = ("Recommended for widescreen (16:9) sources. Options 1 and 2 "
                            "apply 4:3 SAR adjustments and are not suitable for 16:9 content.")
            else:
                rec_body = ("Recommended for DVD and HDD camera sources. These are clean "
                            "digital recordings with no tape overscan to remove.")
        else:
            rec_label = "Option 1 — BT.601 Active Picture"
            rec_body  = ("Recommended for analog SD captures (VHS, Hi8, S-VHS, Video8). "
                         "Crops the standard 8 px overscan region on each side.")

        rec_frame = tk.Frame(self.page_container, bg='#091509', padx=14, pady=10)
        rec_frame.pack(fill='x', pady=(0, 12))
        tk.Label(rec_frame, text=f"✓  Suggested: {rec_label}",
                 font=('Segoe UI', 11, 'bold'),
                 fg='#4EC94E', bg='#091509').pack(anchor='w')
        tk.Label(rec_frame, text=rec_body,
                 font=('Segoe UI', 10), fg='#8DC88D', bg='#091509',
                 wraplength=580, justify='left').pack(anchor='w', pady=(4, 0))

        # ── Preset radio buttons ────────────────────────────────────────────
        if video_format == 'ntsc':
            opt1_desc = "NTSC: crops 8px left+right → 704×480  (default for SD capture)"
            opt2_desc = ("NTSC: 8px left+right, 2px top, 4px bottom → 704×474  "
                         "Removes head-switching noise. SAR adjusted for 4:3 display.")
            opt4_desc = "720×480 full frame, no crop  (default for DV/MiniDV/DVD)"
        else:
            opt1_desc = "PAL: crops 8px left+right → 704×576  (default for SD capture)"
            opt2_desc = ("PAL: 8px left+right, 2px top, 4px bottom → 704×570  "
                         "Removes head-switching noise. SAR adjusted for 4:3 display.")
            opt4_desc = "720×576 full frame, no crop  (default for DV/MiniDV/DVD)"

        initial_preset = self.config_data['crop_preset']
        self._crop_var = tk.StringVar(value=initial_preset)

        preset_card = tk.Frame(self.page_container, bg=Colors.BG_CARD)
        preset_card.pack(fill='x')

        ModernRadioButton(preset_card,
                          "Option 1 — BT.601 Active Picture (recommended for SD capture)",
                          self._crop_var, 'bt601', opt1_desc).pack(fill='x')
        ttk.Separator(preset_card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(preset_card,
                          "Option 2 — Full Overscan Clean",
                          self._crop_var, 'overscan', opt2_desc).pack(fill='x')
        ttk.Separator(preset_card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(preset_card,
                          "Option 3 — Manual Crop (4:3 constrained, with live preview)",
                          self._crop_var, 'manual',
                          "Adjust each edge independently; output resolution auto-calculated.").pack(fill='x')
        ttk.Separator(preset_card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(preset_card,
                          "Option 4 — No Crop",
                          self._crop_var, 'none', opt4_desc).pack(fill='x')

        # ── Multi-file batch warning ────────────────────────────────────────
        if num_files > 1:
            warn_frame = tk.Frame(self.page_container, bg='#1A1500', padx=14, pady=10)
            warn_frame.pack(fill='x', pady=(14, 0))
            tk.Label(warn_frame, text="⚠  Batch mode warning",
                     font=('Segoe UI', 11, 'bold'),
                     fg=Colors.WARNING, bg='#1A1500').pack(anchor='w')
            tk.Label(warn_frame,
                     text=f"You are processing {num_files} files. Options 2, 3, and 4 apply "
                          "the same crop to all files. If your tapes have different overscan "
                          "amounts or head-switching positions, process each file individually "
                          "to set a custom crop per file.",
                     font=('Segoe UI', 10), fg='#C0A040', bg='#1A1500',
                     wraplength=580, justify='left').pack(anchor='w', pady=(4, 0))

        # ── Manual crop controls (shown when Option 3 is selected) ─────────
        self._manual_crop_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        self._manual_crop_frame.pack(fill='x', pady=(12, 0))

        # ── Preview area (for manual crop, populated on demand) ─────────────
        self._crop_preview_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        self._crop_preview_frame.pack(fill='x', pady=(8, 0))

        # State for manual crop iteration (Feature 4)
        if 'per_file_settings' not in self.config_data:
            self.config_data['per_file_settings'] = {}
        for fp in files:
            self.config_data['per_file_settings'].setdefault(fp, {})
        self._crop_files = files
        self._crop_file_idx = 0

        def _on_preset_change(*_):
            preset = self._crop_var.get()
            self.config_data['crop_preset'] = preset
            # Clear manual/preview frames
            for w in self._manual_crop_frame.winfo_children():
                w.destroy()
            for w in self._crop_preview_frame.winfo_children():
                w.destroy()
            if preset == 'manual':
                self._build_manual_crop_ui(files, video_format)
            # For option 1, update crop_left/right in config
            if preset == 'bt601':
                self.config_data.update({'crop_left': 8, 'crop_right': 8,
                                         'crop_top': 0, 'crop_bottom': 0})
            elif preset == 'overscan':
                self.config_data.update({'crop_left': 8, 'crop_right': 8,
                                         'crop_top': 2, 'crop_bottom': 4})
            elif preset == 'none':
                self.config_data.update({'crop_left': 0, 'crop_right': 0,
                                         'crop_top': 0, 'crop_bottom': 0})

        self._crop_var.trace_add('write', _on_preset_change)
        # Trigger immediately to build any initial state
        _on_preset_change()

    def _build_manual_crop_ui(self, files, video_format):
        """Build the manual crop controls + live preview (Feature 4)."""
        num_files = len(files)
        parent = self._manual_crop_frame

        if num_files > 1:
            self._crop_nav_lbl = tk.Label(
                parent,
                text=f"File {self._crop_file_idx + 1} of {num_files}: "
                     f"{os.path.basename(files[self._crop_file_idx])}",
                font=('Segoe UI', 11, 'bold'), fg=Colors.ACCENT, bg=Colors.BG_MAIN)
            self._crop_nav_lbl.pack(anchor='w', pady=(0, 8))

        # Get or initialise per-file crop values
        fp = files[self._crop_file_idx]
        pf = self.config_data['per_file_settings'][fp]
        cl = tk.IntVar(value=pf.get('crop_left', 8))
        cr = tk.IntVar(value=pf.get('crop_right', 8))
        ct = tk.IntVar(value=pf.get('crop_top', 0))
        cb = tk.IntVar(value=pf.get('crop_bottom', 0))

        # Resolution / SAR display
        res_lbl = tk.Label(parent, text="",
                           font=('Segoe UI', 11), fg=Colors.TEXT_SECONDARY,
                           bg=Colors.BG_MAIN)
        res_lbl.pack(anchor='w', pady=(0, 8))

        def _update_res(*_):
            if video_format == 'ntsc':
                ow = max(0, 720 - cl.get() - cr.get())
                oh = max(0, 480 - ct.get() - cb.get())
            else:
                ow = max(0, 720 - cl.get() - cr.get())
                oh = max(0, 576 - ct.get() - cb.get())
            res_lbl.config(text=f"Output size: {ow}×{oh}")
            # Save to per-file
            self.config_data['per_file_settings'][fp].update({
                'crop_left': cl.get(), 'crop_right': cr.get(),
                'crop_top': ct.get(), 'crop_bottom': cb.get(),
            })
            # Also update top-level crop for script generation
            self.config_data.update({
                'crop_left': cl.get(), 'crop_right': cr.get(),
                'crop_top': ct.get(), 'crop_bottom': cb.get(),
            })

        for var in (cl, cr, ct, cb):
            var.trace_add('write', _update_res)

        # Spinbox grid for crop values
        grid = tk.Frame(parent, bg=Colors.BG_MAIN)
        grid.pack(anchor='w', pady=(0, 8))
        for col_lbl, var in [("Left:", cl), ("Right:", cr),
                              ("Top:", ct), ("Bottom:", cb)]:
            f = tk.Frame(grid, bg=Colors.BG_MAIN)
            f.pack(side='left', padx=(0, 18))
            tk.Label(f, text=col_lbl, font=('Segoe UI', 11),
                     fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w')
            sb = tk.Spinbox(f, from_=0, to=80, textvariable=var, width=5,
                            font=('Segoe UI', 12),
                            bg=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY,
                            buttonbackground=Colors.BG_CARD,
                            insertbackground=Colors.TEXT_PRIMARY)
            sb.pack()

        # Trigger initial resolution display
        _update_res()

        # ── Live preview canvas ─────────────────────────────────────────────
        prev_lbl = tk.Label(parent, text="⏳ Loading preview frame…",
                            font=('Segoe UI', 10), fg=Colors.ACCENT,
                            bg=Colors.BG_MAIN)
        prev_lbl.pack(anchor='w')

        canvas_frame = tk.Frame(parent, bg=Colors.BG_CARD, padx=6, pady=6)
        canvas_frame.pack(anchor='w', pady=(4, 0))
        preview_canvas = tk.Canvas(canvas_frame, width=640, height=360,
                                   bg=Colors.BG_DARK, highlightthickness=0)
        preview_canvas.pack()
        tk.Label(canvas_frame,
                 text="Green overlay = crop region that will be kept",
                 font=('Segoe UI', 8), fg=Colors.TEXT_HINT,
                 bg=Colors.BG_CARD).pack(anchor='w', pady=(4, 0))

        # Navigation for batch per-file preview
        if num_files > 1:
            nav_row = tk.Frame(parent, bg=Colors.BG_MAIN)
            nav_row.pack(anchor='w', pady=(10, 0))

            def _prev_file_crop():
                if self._crop_file_idx > 0:
                    self._crop_file_idx -= 1
                    for w in self._manual_crop_frame.winfo_children():
                        w.destroy()
                    self._build_manual_crop_ui(files, video_format)

            def _next_file_crop():
                if self._crop_file_idx < num_files - 1:
                    self._crop_file_idx += 1
                    for w in self._manual_crop_frame.winfo_children():
                        w.destroy()
                    self._build_manual_crop_ui(files, video_format)

            if self._crop_file_idx > 0:
                ModernButton(nav_row, "← Prev File",
                             _prev_file_crop, width=110).pack(side='left')
            if self._crop_file_idx < num_files - 1:
                ModernButton(nav_row, "Next File →",
                             _next_file_crop, primary=True, width=110).pack(
                    side='left', padx=(10, 0))

        self._crop_src_img = None

        def _draw_preview():
            """Overlay the crop rectangle on the preview canvas."""
            if self._crop_src_img is None or not HAS_PIL:
                return
            try:
                img = self._crop_src_img.copy()
                w_src, h_src = img.size
                # Scale to canvas
                scale_x = 640 / w_src
                scale_y = 360 / h_src
                display = img.resize((640, 360), Image.LANCZOS)
                photo = ImageTk.PhotoImage(display)
                preview_canvas._vcg_photo = photo
                preview_canvas.delete('all')
                preview_canvas.create_image(0, 0, anchor='nw', image=photo)
                # Crop overlay rectangle
                x1 = int(cl.get() * scale_x)
                y1 = int(ct.get() * scale_y)
                x2 = 640 - int(cr.get() * scale_x)
                y2 = 360 - int(cb.get() * scale_y)
                preview_canvas.create_rectangle(x1, y1, x2, y2,
                                                outline='#00FF00', width=2)
            except Exception:
                pass

        def _on_crop_change(*_):
            _update_res()
            _draw_preview()

        for var in (cl, cr, ct, cb):
            var.trace_add('write', _on_crop_change)

        def _load_preview():
            path = extract_preview_frame(fp)
            if path:
                self.temp_images.append(path)
                try:
                    img = Image.open(path).convert('RGB')
                    self._crop_src_img = img
                    self.after(0, lambda: (prev_lbl.config(text=""),
                                           _draw_preview()))
                except Exception as exc:
                    self.after(0, lambda: prev_lbl.config(text=f"Preview error: {exc}"))
            else:
                self.after(0, lambda: prev_lbl.config(text="⚠ Could not extract preview"))

        threading.Thread(target=_load_preview, daemon=True).start()

    def _page_source_setup(self):
        """Step 2 — Source Setup: Video Format + Capture Method on one page."""
        tk.Label(self.page_container, text="Source Setup",
                 font=('Segoe UI', 22, 'bold'),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')
        tk.Label(self.page_container,
                 text="Tell VCG how your video was originally recorded and captured.",
                 font=('Segoe UI', 13),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(2, 18))

        # ── Section 1: Video Format ───────────────────────────────────────────
        tk.Label(self.page_container, text="Video Format",
                 font=('Segoe UI', 14, 'bold'),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')

        auto_format = self.config_data.get('auto_format')
        sar = self.config_data.get('detected_sar', '')

        if auto_format:
            fmt_name = 'NTSC' if auto_format == 'ntsc' else 'PAL'
            row = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
            row.pack(anchor='w', pady=(2, 2), fill='x')
            tk.Label(row, text="Auto-detected from file",
                     font=('Segoe UI', 11),
                     fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(side='left')
            badge = f"   ✓ {fmt_name}" + (f"  (SAR {sar})" if sar else "")
            tk.Label(row, text=badge,
                     font=('Segoe UI', 11, 'bold'),
                     fg='#22CC66', bg=Colors.BG_MAIN).pack(side='left')
            tk.Label(self.page_container,
                     text="You can change this if the detection is wrong.",
                     font=('Segoe UI', 10),
                     fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(0, 8))
        else:
            hint = "Select the broadcast standard of your source video"
            if self.config_data.get('guessed_format') == 'ntsc':
                hint = "Based on frame rate, this appears to be NTSC"
            elif self.config_data.get('guessed_format') == 'pal':
                hint = "Based on frame rate, this appears to be PAL"
            tk.Label(self.page_container, text=hint,
                     font=('Segoe UI', 11),
                     fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(2, 8))

        initial_format = self.config_data.get('format', self.config_data.get('guessed_format', 'ntsc'))
        self.config_data['format'] = initial_format
        self.format_var = tk.StringVar(value=initial_format)

        fmt_card = tk.Frame(self.page_container, bg=Colors.BG_CARD)
        fmt_card.pack(fill='x')
        ModernRadioButton(fmt_card, "NTSC", self.format_var, "ntsc",
                          "North America, Japan, South Korea — 29.97fps, 480 lines").pack(fill='x')
        ttk.Separator(fmt_card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(fmt_card, "PAL", self.format_var, "pal",
                          "Europe, Australia, most of Asia — 25fps, 576 lines").pack(fill='x')
        self.format_var.trace_add('write',
            lambda *_: self.config_data.update({'format': self.format_var.get()}))

        # ── Separator ─────────────────────────────────────────────────────────
        ttk.Separator(self.page_container, orient='horizontal').pack(fill='x', pady=20)

        # ── Section 2: Capture Method ─────────────────────────────────────────
        tk.Label(self.page_container, text="Capture Method",
                 font=('Segoe UI', 14, 'bold'),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')

        auto_capture = self.config_data.get('auto_capture_method')
        if auto_capture:
            cap_name = ('DV Capture' if auto_capture == 'dv' else
                        ('MPEG-2 / DVD' if auto_capture == 'dvd' else 'SD Capture'))
            row2 = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
            row2.pack(anchor='w', pady=(2, 2), fill='x')
            tk.Label(row2, text="Auto-detected from file",
                     font=('Segoe UI', 11),
                     fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(side='left')
            badge2 = f"   ✓ {cap_name}" + (f"  (SAR {sar})" if sar else "")
            tk.Label(row2, text=badge2,
                     font=('Segoe UI', 11, 'bold'),
                     fg='#22CC66', bg=Colors.BG_MAIN).pack(side='left')
            tk.Label(self.page_container,
                     text="You can change this if the detection is wrong.",
                     font=('Segoe UI', 10),
                     fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(0, 8))
        else:
            tk.Label(self.page_container, text="How was this video digitized?",
                     font=('Segoe UI', 11),
                     fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(2, 8))

        initial_capture = self.config_data.get('capture_method', 'sd')
        self.config_data['capture_method'] = initial_capture
        self.capture_var = tk.StringVar(value=initial_capture)

        cap_card = tk.Frame(self.page_container, bg=Colors.BG_CARD)
        cap_card.pack(fill='x')
        ModernRadioButton(cap_card, "SD Capture Device", self.capture_var, "sd",
                          "USB capture card, VirtualDub, ATI, Elgato, Hauppauge, etc. — crops 8px each side").pack(fill='x')
        ttk.Separator(cap_card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(cap_card, "MPEG-2 / DVD", self.capture_var, "dvd",
                          "DVD-sourced MPEG-2 (VOB, MPG). Field order TFF. "
                          "Telecine detection enabled — 3:2 pulldown is common on film DVDs.").pack(fill='x')
        ttk.Separator(cap_card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(cap_card, "DV Capture Device", self.capture_var, "dv",
                          "Native MiniDV/Digital8 — no edge crop (clean frame). "
                          "VHS/Video8 via DV passthrough: adjust crop manually in Finalize.").pack(fill='x')

        def _on_cap_changed(*_):
            method = self.capture_var.get()
            crop = 0 if method == 'dv' else 8
            self.config_data.update({'capture_method': method, 'crop_left': crop, 'crop_right': crop})
        self.capture_var.trace_add('write', _on_cap_changed)
        _on_cap_changed()

        # ── PAR info card ──────────────────────────────────────────────────────
        info_frame = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=15, pady=12)
        info_frame.pack(fill='x', pady=(20, 0))
        tk.Label(info_frame, text="ℹ️ Why this matters:",
                 font=('Segoe UI', 10, 'bold'),
                 fg=Colors.ACCENT, bg=Colors.BG_CARD).pack(anchor='w')
        tk.Label(info_frame,
                 text="Different capture methods use different pixel aspect ratios (PAR).\n\n"
                      "NTSC SD capture  →  720×480, PAR 10:11  →  corrected to 640×480 square pixels\n"
                      "NTSC DV25 (MiniDV)  →  720×480, PAR 8:9  →  corrected to 640×480 square pixels\n"
                      "PAL SD capture  →  720×576, PAR 59:54  →  corrected to 768×576 square pixels\n"
                      "PAL DV25  →  720×576, PAR 16:15  →  corrected to 768×576 square pixels\n\n"
                      "VCG automatically handles the correct conversion based on your selection.",
                 font=('Segoe UI', 11),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                 justify='left').pack(anchor='w', pady=(5, 0))

    def _page_video_format(self):
        tk.Label(self.page_container, text="Video Format",
                font=('Segoe UI', 22, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')
        
        auto_format = self.config_data.get('auto_format')
        sar = self.config_data.get('detected_sar', '')

        if auto_format:
            fmt_name = 'NTSC' if auto_format == 'ntsc' else 'PAL'
            subtitle_row = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
            subtitle_row.pack(anchor='w', pady=(4, 2), fill='x')
            tk.Label(subtitle_row, text="Auto-detected from file",
                    font=('Segoe UI', 13, 'bold'),
                    fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(side='left')
            badge_text = f"   ✓ {fmt_name}" + (f"  (SAR {sar})" if sar else "")
            tk.Label(subtitle_row, text=badge_text,
                    font=('Segoe UI', 12, 'bold'),
                    fg='#22CC66', bg=Colors.BG_MAIN).pack(side='left')
            tk.Label(self.page_container,
                    text="You can change this if the detection is wrong.",
                    font=('Segoe UI', 11),
                    fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(0, 14))
        else:
            hint = "Select the broadcast standard of your source video"
            if self.config_data.get('guessed_format') == 'ntsc':
                hint = "Based on frame rate, this appears to be NTSC"
            elif self.config_data.get('guessed_format') == 'pal':
                hint = "Based on frame rate, this appears to be PAL"
            tk.Label(self.page_container, text=hint,
                    font=('Segoe UI', 13, 'bold'),
                    fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(4, 20))
        
        # Get initial value and save it immediately
        initial_format = self.config_data.get('format', self.config_data.get('guessed_format', 'ntsc'))
        self.config_data['format'] = initial_format  # Save immediately
        self.format_var = tk.StringVar(value=initial_format)
        
        card = tk.Frame(self.page_container, bg=Colors.BG_CARD)
        card.pack(fill='x')
        
        ModernRadioButton(card, "NTSC", self.format_var, "ntsc",
                         "North America, Japan, South Korea — 29.97fps, 480 lines").pack(fill='x')
        
        ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
        
        ModernRadioButton(card, "PAL", self.format_var, "pal",
                         "Europe, Australia, most of Asia — 25fps, 576 lines").pack(fill='x')
        
        self.format_var.trace_add('write', lambda *_: self.config_data.update({'format': self.format_var.get()}))
    
    def _page_capture_method(self):
        tk.Label(self.page_container, text="Capture Method",
                font=('Segoe UI', 22, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')
        
        auto_capture = self.config_data.get('auto_capture_method')
        sar = self.config_data.get('detected_sar', '')

        if auto_capture:
            cap_name = ('DV Capture' if auto_capture == 'dv' else
                        ('MPEG-2 / DVD' if auto_capture == 'dvd' else 'SD Capture'))
            subtitle_row = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
            subtitle_row.pack(anchor='w', pady=(4, 2), fill='x')
            tk.Label(subtitle_row, text="Auto-detected from file",
                    font=('Segoe UI', 13, 'bold'),
                    fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(side='left')
            badge_text = f"   ✓ {cap_name}" + (f"  (SAR {sar})" if sar else "")
            tk.Label(subtitle_row, text=badge_text,
                    font=('Segoe UI', 12, 'bold'),
                    fg='#22CC66', bg=Colors.BG_MAIN).pack(side='left')
            tk.Label(self.page_container,
                    text="You can change this if the detection is wrong.",
                    font=('Segoe UI', 11),
                    fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(0, 14))
        else:
            tk.Label(self.page_container, text="How was this video digitized?",
                    font=('Segoe UI', 13, 'bold'),
                    fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(4, 20))

        # Get initial value and save it immediately
        initial_capture = self.config_data.get('capture_method', 'sd')
        self.config_data['capture_method'] = initial_capture
        self.capture_var = tk.StringVar(value=initial_capture)

        card = tk.Frame(self.page_container, bg=Colors.BG_CARD)
        card.pack(fill='x')

        ModernRadioButton(card, "SD Capture Device", self.capture_var, "sd",
                         "USB capture card, VirtualDub, ATI, Elgato, Hauppauge, etc. — crops 8px each side").pack(fill='x')

        ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)

        ModernRadioButton(card, "MPEG-2 / DVD", self.capture_var, "dvd",
                         "DVD-sourced MPEG-2 (VOB, MPG ripped from disc). Field order TFF. "
                         "Telecine detection enabled — 3:2 pulldown is common on film DVDs.").pack(fill='x')

        ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)

        ModernRadioButton(card, "DV Capture Device", self.capture_var, "dv",
                         "Native MiniDV/Digital8 — no edge crop (clean frame). "
                         "VHS/Video8 via DV passthrough: adjust crop manually in Finalize.").pack(fill='x')

        def _on_capture_method_changed(*_):
            method = self.capture_var.get()
            crop = 0 if method == 'dv' else 8
            self.config_data.update({'capture_method': method, 'crop_left': crop, 'crop_right': crop})
        self.capture_var.trace_add('write', _on_capture_method_changed)
        _on_capture_method_changed()

        # Info about PAR
        info_frame = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=15, pady=12)
        info_frame.pack(fill='x', pady=(20, 0))

        tk.Label(info_frame, text="ℹ️ Why this matters:",
                font=('Segoe UI', 10, 'bold'),
                fg=Colors.ACCENT, bg=Colors.BG_CARD).pack(anchor='w')

        tk.Label(info_frame,
                text="Different capture methods use different pixel aspect ratios (PAR).\n\n"
                     "NTSC SD capture  →  720×480, PAR 10:11  →  corrected to 640×480 square pixels\n"
                     "NTSC DV25 (MiniDV)  →  720×480, PAR 8:9   →  corrected to 640×480 square pixels\n"
                     "NTSC DVD (4:3)      →  720×480, PAR 8:9   →  corrected to 640×480 square pixels\n"
                     "PAL SD capture   →  720×576, PAR 59:54 →  corrected to 768×576 square pixels\n"
                     "PAL DV25         →  720×576, PAR 16:15 →  corrected to 768×576 square pixels\n"
                     "PAL DVD (4:3)    →  720×576, PAR 16:15 →  corrected to 768×576 square pixels\n\n"
                     "VCG automatically handles the correct conversion based on your format selection.",
                font=('Segoe UI', 12),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                justify='left').pack(anchor='w', pady=(5, 0))
    
    def _page_field_order(self):
        tk.Label(self.page_container, text="Field Order",
                font=('Segoe UI', 22, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')

        num_files = len(self.config_data.get('input_files', []))

        # ── Badge row — same pattern as Video Format / Capture Method ─────────
        badge_row = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        badge_row.pack(anchor='w', pady=(4, 2), fill='x')

        if num_files > 1:
            tk.Label(badge_row, text="Batch mode — select field order for all files",
                     font=('Segoe UI', 13, 'bold'),
                     fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(side='left')
            self.detect_badge_lbl = None
            # Stub so detection code doesn't crash
            self.detect_status_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        else:
            tk.Label(badge_row, text="Auto-detecting from file",
                     font=('Segoe UI', 13, 'bold'),
                     fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(side='left')
            self.detect_badge_lbl = tk.Label(badge_row, text="   ⏳ Analyzing...",
                     font=('Segoe UI', 12, 'bold'),
                     fg=Colors.ACCENT, bg=Colors.BG_MAIN)
            self.detect_badge_lbl.pack(side='left')
            tk.Label(self.page_container,
                     text="You can change this if the detection is wrong.",
                     font=('Segoe UI', 11),
                     fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(0, 14))

        # ── Radio buttons ─────────────────────────────────────────────────────
        initial_field = self.config_data.get('field_order', 'tff')
        self.config_data['field_order'] = initial_field
        self.field_var = tk.StringVar(value=initial_field)

        card = tk.Frame(self.page_container, bg=Colors.BG_CARD)
        card.pack(fill='x')

        ModernRadioButton(card, "TFF (Top Field First)", self.field_var, "tff",
                         "SD capture cards (ATI 600, IO-Data GV-USB2)").pack(fill='x')

        ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)

        ModernRadioButton(card, "BFF (Bottom Field First)", self.field_var, "bff",
                         "MiniDV camcorder, DV-25, or FireWire passthrough").pack(fill='x')

        self.field_var.trace_add('write', lambda *_: self.config_data.update({'field_order': self.field_var.get()}))

        # ── Re-run button + detail area (single-file only) ────────────────────
        if num_files <= 1:
            btn_row = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
            btn_row.pack(anchor='w', pady=(10, 0))
            ModernButton(btn_row, "🔄 Re-run Detection", self._run_field_order_detection,
                         primary=False, width=180).pack(side='left')
            # Status frame — populated by _run_field_order_detection (detail text only)
            self.detect_status_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
            self.detect_status_frame.pack(fill='x', pady=(4, 0))

        # ── Educational card ──────────────────────────────────────────────────
        edu_card = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=16, pady=14)
        edu_card.pack(fill='x', pady=(18, 0))

        tk.Label(edu_card, text="What is field order and why does it matter?",
                 font=('Segoe UI', 11, 'bold'),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD).pack(anchor='w', pady=(0, 6))

        tk.Label(edu_card,
                 text="Interlaced video stores each frame as two \"fields\" — one containing "
                      "the odd scan lines and one containing the even lines. Field order determines "
                      "which field was captured first. Choosing the wrong setting causes "
                      "\"combing\" — jagged horizontal lines that appear on moving objects in "
                      "the deinterlaced output.",
                 font=('Segoe UI', 11),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                 wraplength=580, justify='left').pack(anchor='w', pady=(0, 10))

        # Bullet guide
        bullets = [
            ("SD capture card  (VirtualDub, AmarecTV, ATI, IO-Data GV-USB2, Elgato, etc.)",
             "Almost certainly  TFF  (Top Field First)"),
            ("MiniDV camcorder or Digital8 via FireWire / IEEE 1394",
             "Almost certainly  BFF  (Bottom Field First)"),
            ("MPEG-2 files ripped from a DVD disc",
             "Usually  TFF  for both NTSC and PAL DVDs, "
             "though some PAL discs use BFF — check the disc specs if unsure"),
            ("AVI / HuffYUV files from analog capture",
             "Almost always  TFF"),
        ]
        for source, field_info in bullets:
            row = tk.Frame(edu_card, bg=Colors.BG_CARD)
            row.pack(fill='x', pady=(0, 4))
            tk.Label(row, text="•",
                     font=('Segoe UI', 11, 'bold'),
                     fg=Colors.ACCENT, bg=Colors.BG_CARD).pack(side='left', anchor='n', padx=(0, 6))
            col = tk.Frame(row, bg=Colors.BG_CARD)
            col.pack(side='left', fill='x', expand=True)
            tk.Label(col, text=source,
                     font=('Segoe UI', 10),
                     fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                     wraplength=520, justify='left').pack(anchor='w')
            tk.Label(col, text=field_info,
                     font=('Segoe UI', 10, 'bold'),
                     fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD,
                     wraplength=520, justify='left').pack(anchor='w')

        tk.Label(edu_card,
                 text="💡  If the output video still looks wrong (jagged horizontal lines on "
                      "edges, or motion that looks \"stepped\" or \"stuttery\"), try re-processing "
                      "with the opposite field order.",
                 font=('Segoe UI', 10),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                 wraplength=580, justify='left').pack(anchor='w', pady=(8, 0))

        # ── QTGMC info ────────────────────────────────────────────────────────
        info_frame = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=15, pady=12)
        info_frame.pack(fill='x', pady=(15, 0))

        tk.Label(info_frame, text="ℹ️  About QTGMC Deinterlacing",
                font=('Segoe UI', 10, 'bold'),
                fg=Colors.ACCENT, bg=Colors.BG_CARD).pack(anchor='w')

        qtgmc_info = (
            "VCG Deinterlacer uses QTGMC (Quality Temporal Gaussian Motion Compensated), "
            "the gold standard for deinterlacing quality. Our settings are tuned to be "
            "non-destructive — QTGMC will convert interlaced fields to progressive frames "
            "without affecting the rest of the image. Sharpening is set to minimal (0.1) "
            "to preserve the original look of your footage."
        )
        tk.Label(info_frame, text=qtgmc_info,
                font=('Segoe UI', 12),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                wraplength=550, justify='left').pack(anchor='w', pady=(5, 0))

        # ── Auto-trigger detection ─────────────────────────────────────────────
        if num_files <= 1:
            self.after(400, self._run_field_order_detection)

    def _on_analysis_section_done(self):
        """Called when any analysis section (noise/color/levels) finishes.

        Unlocks the Next button only when ALL three analyses are complete,
        which allows _page_enhancements to run them in parallel without
        prematurely enabling navigation.  On individual pages the other two
        flags default to True so the button is unlocked immediately.
        """
        noise_ok  = getattr(self, 'noise_analysis_complete',  True)
        color_ok  = getattr(self, 'color_analysis_complete',  True)
        levels_ok = getattr(self, 'levels_analysis_complete', True)
        if noise_ok and color_ok and levels_ok:
            if hasattr(self, 'next_btn'):
                try:
                    self.next_btn.set_disabled(False)
                    self.next_btn._draw()
                except Exception:
                    pass

    def _sampling_note(self, parent, text):
        """Small card explaining where this page's analysis samples came from,
        so users can judge whether the result is representative of their tape."""
        note = tk.Frame(parent, bg=Colors.BG_CARD, padx=12, pady=8)
        note.pack(fill='x', pady=(8, 0))
        tk.Label(note, text="ⓘ Where the samples come from",
                 font=('Segoe UI', 9, 'bold'),
                 fg=Colors.INFO, bg=Colors.BG_CARD).pack(anchor='w')
        tk.Label(note, text=text,
                 font=('Segoe UI', 9),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                 wraplength=560, justify='left').pack(anchor='w', pady=(2, 0))
        return note

    def _selectable_label(self, parent, text, font=None, fg=None, bg=None, **kwargs):
        """Create a readonly Entry that looks like a Label but allows text selection/copy."""
        bg = bg or parent.cget('bg')
        fg = fg or Colors.TEXT_SECONDARY
        font = font or ('Segoe UI', 12)
        e = tk.Entry(parent,
                     readonlybackground=bg,
                     disabledbackground=bg,
                     fg=fg,
                     disabledforeground=fg,
                     font=font,
                     relief='flat',
                     bd=0,
                     highlightthickness=0,
                     state='readonly',
                     **kwargs)
        e.insert(0, text)
        e.configure(state='readonly')
        return e

    # ─────────────────────────────────────────────────────────────────────────
    def _page_enhancements(self):
        """Step 4 — Enhancements: Noise, Color, Levels analysis + Audio options."""
        tk.Label(self.page_container, text="Enhancements",
                 font=('Segoe UI', 22, 'bold'),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')

        num_files = len(self.config_data.get('input_files', []))
        is_batch  = num_files > 1

        if is_batch:
            tk.Label(self.page_container,
                     text=f"Batch mode — {num_files} files selected. "
                          "Auto-analysis runs on one file at a time. "
                          "Choose settings to apply to all files.",
                     font=('Segoe UI', 12),
                     fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
                     wraplength=620, justify='left').pack(anchor='w', pady=(4, 14))
        else:
            tk.Label(self.page_container,
                     text="VCG will analyze your video and suggest settings. "
                          "You can accept or change each one.",
                     font=('Segoe UI', 12),
                     fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(4, 14))

        # ── reset all completion flags so _on_analysis_section_done waits ────
        if not is_batch:
            self.noise_analysis_complete  = False
            self.color_analysis_complete  = False
            self.levels_analysis_complete = False
            # Disable Next until all three analyses finish
            self.next_btn.set_disabled(True)
            self.next_btn._draw()

        def section_heading(title, number):
            hdr = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
            hdr.pack(fill='x', pady=(14, 4))
            tk.Label(hdr, text=f"{number}  {title}",
                     font=('Segoe UI', 14, 'bold'),
                     fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(side='left')

        # ════════════════════════════════════════════════════════════════
        # 1 — NOISE REMOVAL
        # ════════════════════════════════════════════════════════════════
        section_heading("Noise Removal", "①")

        self._show_experimental_notice(self.page_container)

        initial_noise = self.config_data.get('noise_level', 'none')
        self.config_data['noise_level'] = initial_noise
        self.noise_var = tk.StringVar(value=initial_noise)

        if is_batch:
            batch_card = tk.Frame(self.page_container, bg=Colors.BG_CARD)
            batch_card.pack(fill='x')
            for i, (lbl, val, desc) in enumerate([
                ("No noise removal", "none", "Picture looks clean"),
                ("Light denoising",  "moderate", "Some grain or speckling visible"),
                ("Heavy denoising",  "heavy",    "Heavy static or snow"),
            ]):
                ModernRadioButton(batch_card, lbl, self.noise_var, val, desc).pack(fill='x')
                if i < 2:
                    ttk.Separator(batch_card, orient='horizontal').pack(fill='x', padx=12)
            self.noise_var.trace_add('write',
                lambda *_: self.config_data.update({'noise_level': self.noise_var.get()}))
        else:
            self.noise_progress_card = tk.Frame(self.page_container, bg=Colors.BG_CARD,
                                                 padx=20, pady=18)
            self.noise_progress_card.pack(fill='x', pady=(4, 0))
            self.noise_spinner_label = tk.Label(self.noise_progress_card, text="⏳",
                    font=('Segoe UI', 24), fg=Colors.ACCENT, bg=Colors.BG_CARD)
            self.noise_spinner_label.pack()
            self.noise_status_label = tk.Label(self.noise_progress_card,
                    text="Analyzing noise levels…",
                    font=('Segoe UI', 11, 'bold'), fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD)
            self.noise_status_label.pack(pady=(8, 4))
            self.noise_progress_label = tk.Label(self.noise_progress_card,
                    text="Sampling frame 1 of 15",
                    font=('Segoe UI', 11), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD)
            self.noise_progress_label.pack()
            self.noise_detail_label = tk.Label(self.noise_progress_card,
                    text="This may take 15–30 seconds",
                    font=('Segoe UI', 9, 'italic'), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD)
            self.noise_detail_label.pack(pady=(8, 0))
            self.noise_results_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
            self.noise_results_frame.pack(fill='x')
            self.noise_options_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
            self.noise_options_frame.pack(fill='x', pady=(8, 0))
            self._animate_noise_spinner()
            threading.Thread(target=self._run_noise_analysis, daemon=True).start()

        # ════════════════════════════════════════════════════════════════
        # 2 — COLOR ANALYSIS
        # ════════════════════════════════════════════════════════════════
        ttk.Separator(self.page_container, orient='horizontal').pack(fill='x', pady=(20, 0))
        section_heading("Color Analysis", "②")

        self._show_experimental_notice(self.page_container)

        self.color_var = tk.StringVar(value='none')

        if is_batch:
            self.config_data['color_correction'] = 'none'
            tk.Label(self.page_container,
                     text="Auto color analysis not available in batch mode — set to No correction.",
                     font=('Segoe UI', 11), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
                     wraplength=620).pack(anchor='w', pady=(4, 0))
        else:
            self.color_progress_card = tk.Frame(self.page_container, bg=Colors.BG_CARD,
                                                 padx=20, pady=18)
            self.color_progress_card.pack(fill='x', pady=(4, 0))
            self.color_spinner_label = tk.Label(self.color_progress_card, text="⏳",
                    font=('Segoe UI', 24), fg=Colors.ACCENT, bg=Colors.BG_CARD)
            self.color_spinner_label.pack()
            self.color_status_label = tk.Label(self.color_progress_card,
                    text="Analyzing video colors…",
                    font=('Segoe UI', 11, 'bold'), fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD)
            self.color_status_label.pack(pady=(8, 4))
            self.color_progress_label = tk.Label(self.color_progress_card,
                    text="Generating vectorscope and analyzing color channels",
                    font=('Segoe UI', 11), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD)
            self.color_progress_label.pack()
            self.color_preview = ImagePreview(self.page_container)
            self.color_results_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
            self.color_results_frame.pack(fill='x', pady=(8, 0))
            self.color_options_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
            self.color_options_frame.pack(fill='x', pady=(8, 0))
            self._animate_color_spinner()
            threading.Thread(target=self._run_color_analysis, daemon=True).start()

        # ════════════════════════════════════════════════════════════════
        # 3 — VIDEO LEVELS
        # ════════════════════════════════════════════════════════════════
        ttk.Separator(self.page_container, orient='horizontal').pack(fill='x', pady=(20, 0))
        section_heading("Video Levels", "③")

        self._show_experimental_notice(self.page_container)

        self.levels_var = tk.StringVar(value='none')

        if is_batch:
            self.config_data['levels_adjustment'] = 'none'
            tk.Label(self.page_container,
                     text="Auto levels analysis not available in batch mode — set to No adjustment.",
                     font=('Segoe UI', 11), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
                     wraplength=620).pack(anchor='w', pady=(4, 0))
        else:
            self.levels_progress_card = tk.Frame(self.page_container, bg=Colors.BG_CARD,
                                                  padx=20, pady=18)
            self.levels_progress_card.pack(fill='x', pady=(4, 0))
            self.levels_spinner_label = tk.Label(self.levels_progress_card, text="⏳",
                    font=('Segoe UI', 24), fg=Colors.ACCENT, bg=Colors.BG_CARD)
            self.levels_spinner_label.pack()
            self.levels_status_label = tk.Label(self.levels_progress_card,
                    text="Analyzing brightness levels…",
                    font=('Segoe UI', 11, 'bold'), fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD)
            self.levels_status_label.pack(pady=(8, 4))
            self.levels_progress_label = tk.Label(self.levels_progress_card,
                    text="Generating RGB parade and measuring luma range",
                    font=('Segoe UI', 11), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD)
            self.levels_progress_label.pack()
            self.levels_preview = ImagePreview(self.page_container)
            self.levels_results_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
            self.levels_results_frame.pack(fill='x', pady=(8, 0))
            self.levels_options_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
            self.levels_options_frame.pack(fill='x', pady=(8, 0))
            self._animate_levels_spinner()
            threading.Thread(target=self._run_levels_analysis, daemon=True).start()

        # ════════════════════════════════════════════════════════════════
        # 4 — AUDIO OPTIONS
        # ════════════════════════════════════════════════════════════════
        ttk.Separator(self.page_container, orient='horizontal').pack(fill='x', pady=(20, 0))
        section_heading("Audio Options", "④")

        cb_card = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=16, pady=14)
        cb_card.pack(fill='x', pady=(4, 0))

        self.mix_audio_var = tk.BooleanVar(value=self.config_data.get('mix_audio', False))
        cb = tk.Checkbutton(cb_card,
                            text="Mix audio channels (copy left channel to right channel)",
                            variable=self.mix_audio_var,
                            font=('Segoe UI', 12),
                            fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD,
                            selectcolor=Colors.BG_DARK,
                            activebackground=Colors.BG_CARD,
                            activeforeground=Colors.TEXT_PRIMARY,
                            command=lambda: self.config_data.update(
                                {'mix_audio': self.mix_audio_var.get()}))
        cb.pack(anchor='w')

        info_lbl = tk.Label(cb_card,
                 text="Enable if your tape has audio on only one channel and you want it "
                      "on both speakers. Do NOT enable for normal stereo audio.",
                 font=('Segoe UI', 11),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                 wraplength=580, justify='left')
        info_lbl.pack(anchor='w', pady=(6, 0))

        # spacer at bottom
        tk.Frame(self.page_container, bg=Colors.BG_MAIN, height=20).pack()

    def _page_noise(self):
        tk.Label(self.page_container, text="Noise Removal",
                font=('Segoe UI', 22, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')

        self._show_artifact_example(self.page_container, 'noise',
            "What tape noise looks like — before and after denoising:")
        self._show_experimental_notice(self.page_container)

        # Check if multiple files selected
        num_files = len(self.config_data.get('input_files', []))
        if num_files > 1:
            # For batch processing, show simple options without analysis
            tk.Label(self.page_container,
                    text=f"Analysis not available in batch mode ({num_files} files selected). "
                         "Choose a level to apply to all files, or process one at a time for auto-analysis.",
                    font=('Segoe UI', 13, 'bold'),
                    fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
                    wraplength=580, justify='left').pack(anchor='w', pady=(4, 20))
            
            initial_noise = self.config_data.get('noise_level', 'none')
            self.config_data['noise_level'] = initial_noise
            self.noise_var = tk.StringVar(value=initial_noise)
            
            card = tk.Frame(self.page_container, bg=Colors.BG_CARD)
            card.pack(fill='x')
            
            options = [
                ("No noise removal", "none", "Picture looks clean"),
                ("Light denoising", "moderate", "Some grain or speckling visible"),
                ("Heavy denoising", "heavy", "Heavy static or snow")
            ]
            
            for i, (label, value, desc) in enumerate(options):
                ModernRadioButton(card, label, self.noise_var, value, desc).pack(fill='x')
                if i < len(options) - 1:
                    ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
            
            self.noise_var.trace_add('write', lambda *_: self.config_data.update({'noise_level': self.noise_var.get()}))
            return
        
        # Single file - show analysis with prominent progress indicator
        
        # Progress indicator card (prominent)
        self.noise_progress_card = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=20, pady=20)
        self.noise_progress_card.pack(fill='x', pady=(10, 0))
        
        # Spinner animation (using text)
        self.noise_spinner_label = tk.Label(self.noise_progress_card, text="⏳",
                font=('Segoe UI', 28),
                fg=Colors.ACCENT, bg=Colors.BG_CARD)
        self.noise_spinner_label.pack()
        
        self.noise_status_label = tk.Label(self.noise_progress_card, 
                text="Analyzing video...",
                font=('Segoe UI', 12, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD)
        self.noise_status_label.pack(pady=(10, 5))
        
        self.noise_progress_label = tk.Label(self.noise_progress_card, 
                text="Sampling frame 1 of 15",
                font=('Segoe UI', 12),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD)
        self.noise_progress_label.pack()
        
        self.noise_detail_label = tk.Label(self.noise_progress_card, 
                text="This may take 15-30 seconds depending on video length",
                font=('Segoe UI', 9, 'italic'),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD)
        self.noise_detail_label.pack(pady=(10, 0))
        
        # Analysis results frame (hidden until analysis complete)
        self.noise_results_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        self.noise_results_frame.pack(fill='x')
        
        # Options frame (populated after analysis)
        self.noise_options_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        self.noise_options_frame.pack(fill='x', pady=(10, 0))
        
        # Get initial value
        initial_noise = self.config_data.get('noise_level', 'none')
        self.config_data['noise_level'] = initial_noise
        self.noise_var = tk.StringVar(value=initial_noise)
        
        # Disable Next button during analysis
        self.noise_analysis_complete = False
        if hasattr(self, 'next_btn'):
            self.next_btn.configure(state='disabled')
        
        # Start spinner animation
        self._animate_noise_spinner()
        
        # Run analysis in thread
        threading.Thread(target=self._run_noise_analysis, daemon=True).start()
    
    def _animate_noise_spinner(self):
        """Animate the spinner during analysis."""
        if not hasattr(self, 'noise_analysis_complete') or self.noise_analysis_complete:
            return
        
        if not hasattr(self, 'noise_spinner_label') or not self.noise_spinner_label.winfo_exists():
            return
            
        # Cycle through spinner frames
        spinners = ['⏳', '⌛']
        current = self.noise_spinner_label.cget('text')
        next_idx = (spinners.index(current) + 1) % len(spinners) if current in spinners else 0
        self.noise_spinner_label.config(text=spinners[next_idx])
        
        # Continue animation
        self.after(500, self._animate_noise_spinner)
    
    def _update_noise_progress(self, current, total):
        """Update the noise analysis progress indicator."""
        if hasattr(self, 'noise_progress_label') and self.noise_progress_label.winfo_exists():
            self.after(0, lambda: self.noise_progress_label.config(
                text=f"Sampling frame {current} of {total}"))
    
    def _run_noise_analysis(self):
        if 'input_path' not in self.config_data:
            self.after(0, self._finish_noise_analysis_error, "❌ No file selected")
            return
        
        try:
            # Update status
            self.after(0, lambda: self.noise_status_label.config(text="Analyzing noise levels..."))
            
            # Run noise analysis with progress callback
            noise_data = analyze_noise_level(
                self.config_data['input_path'],
                sample_frames=15,
                progress_callback=self._update_noise_progress
            )
            
            if noise_data and noise_data.get('analyzed'):
                self.config_data['noise_data'] = noise_data
                self.after(0, lambda: self._show_noise_results(noise_data))
            else:
                self.after(0, self._finish_noise_analysis_error, "Could not analyze noise levels")
        except Exception as e:
            self.after(0, self._finish_noise_analysis_error, f"Analysis error: {str(e)[:30]}")
    
    def _finish_noise_analysis_error(self, message):
        """Handle analysis error - show message and fallback options."""
        self.noise_analysis_complete = True
        self._on_analysis_section_done()
        
        # Hide progress card
        if hasattr(self, 'noise_progress_card'):
            self.noise_progress_card.pack_forget()
        
        # Show error
        error_label = tk.Label(self.noise_results_frame, text=message,
                font=('Segoe UI', 12),
                fg=Colors.ERROR, bg=Colors.BG_MAIN)
        error_label.pack(anchor='w', pady=(0, 10))
        
        self._show_noise_options_fallback_direct()
    
    def _show_noise_options_fallback(self):
        """Show basic noise options without analysis."""
        def show():
            card = tk.Frame(self.noise_options_frame, bg=Colors.BG_CARD)
            card.pack(fill='x')
            
            options = [
                ("No noise removal", "none", "Picture looks clean"),
                ("Light denoising", "moderate", "Some grain or speckling visible"),
                ("Heavy denoising", "heavy", "Heavy static or snow")
            ]
            
            for i, (label, value, desc) in enumerate(options):
                ModernRadioButton(card, label, self.noise_var, value, desc).pack(fill='x')
                if i < len(options) - 1:
                    ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
            
            self.noise_var.trace_add('write', lambda *_: self.config_data.update({'noise_level': self.noise_var.get()}))
        
        self.after(0, show)
    
    def _show_noise_options_fallback_direct(self):
        """Show basic noise options directly (not via after)."""
        card = tk.Frame(self.noise_options_frame, bg=Colors.BG_CARD)
        card.pack(fill='x')
        
        options = [
            ("No noise removal", "none", "Picture looks clean"),
            ("Light denoising", "moderate", "Some grain or speckling visible"),
            ("Heavy denoising", "heavy", "Heavy static or snow")
        ]
        
        for i, (label, value, desc) in enumerate(options):
            ModernRadioButton(card, label, self.noise_var, value, desc).pack(fill='x')
            if i < len(options) - 1:
                ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
        
        self.noise_var.trace_add('write', lambda *_: self.config_data.update({'noise_level': self.noise_var.get()}))
    
    def _show_noise_results(self, data):
        # Mark analysis complete; unlock Next only when all analyses are done
        self.noise_analysis_complete = True
        self._on_analysis_section_done()
        
        # Hide progress card
        if hasattr(self, 'noise_progress_card'):
            self.noise_progress_card.pack_forget()
        
        # Show analysis results
        result_card = tk.Frame(self.noise_results_frame, bg=Colors.BG_CARD, padx=15, pady=12)
        result_card.pack(fill='x')
        
        # === NOISE ANALYSIS ===
        tk.Label(result_card, text="📊 Noise Analysis",
                font=('Segoe UI', 10, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD).pack(anchor='w')
        
        # Noise level indicator
        level = data.get('noise_level', 'unknown')
        desc = data.get('noise_desc', 'Unknown')
        
        if level == 'heavy':
            icon = "🔴"
            color = Colors.ERROR
        elif level == 'moderate':
            icon = "🟠"
            color = Colors.WARNING
        elif level == 'light':
            icon = "🟡"
            color = Colors.WARNING
        else:
            icon = "🟢"
            color = Colors.SUCCESS
        
        tk.Label(result_card, text=f"{icon} {desc}",
                font=('Segoe UI', 12),
                fg=color, bg=Colors.BG_CARD).pack(anchor='w', pady=(3, 0))
        
        # Noise index: TOUT (temporal outlier fraction) as a percentage —
        # the most noise-specific metric since it ignores smooth motion.
        samples = data.get('samples_analyzed', 0)
        tout_pct = data.get('avg_variance', 0) * 100
        if samples == 0:
            tech_text = "Noise index: unavailable (no frames sampled — try a different format)"
        else:
            tech_text = (f"Noise index: {tout_pct:.1f}%  "
                         f"(temporal outlier pixels, {samples} samples analyzed)")
        self._selectable_label(result_card, tech_text,
                font=('Segoe UI', 12),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD).pack(anchor='w', pady=(2, 0))

        # Debug readout: raw YDIF so expert users can see why the tool
        # recommended what it did and override intelligently.
        ydif_text = f"Motion index: {data.get('avg_diff', 0):.2f}  (YDIF — inter-frame difference; elevated by both noise and scene motion)"
        self._selectable_label(result_card, ydif_text,
            font=('Segoe UI', 10),
            fg=Colors.TEXT_HINT, bg=Colors.BG_CARD).pack(anchor='w', pady=(1, 0))

        # === RECOMMENDATION ===
        ttk.Separator(result_card, orient='horizontal').pack(fill='x', pady=(10, 8))
        
        rec = data.get('recommendation', 'none')
        # Quantified score next to the recommendation: show the metric that
        # actually crossed the threshold, with the band it landed in.
        bands = {
            'heavy':    'heavy ≥ 8%',
            'moderate': 'moderate 3–8%',
            'light':    'light 1.2–3%',
            'clean':    'clean < 1.2%',
        }
        if data.get('trigger') == 'ydif':
            score_str = (f"motion index {data.get('avg_diff', 0):.1f} crossed the "
                         f"{level} threshold (noise score {tout_pct:.2f}%)")
        else:
            score_str = f"noise score {tout_pct:.2f}% — {bands.get(level, '')}"
        if rec == 'heavy':
            rec_text = f"💡 Recommendation: Heavy denoising  ·  {score_str}"
        elif rec == 'moderate':
            rec_text = f"💡 Recommendation: Light denoising  ·  {score_str}"
        else:
            rec_text = (f"💡 Recommendation: No denoising needed  ·  {score_str} — "
                        "but you can still enable it below if your tape looks grainy.")

        tk.Label(result_card, text=rec_text,
                font=('Segoe UI', 10, 'bold'),
                fg=Colors.ACCENT, bg=Colors.BG_CARD,
                wraplength=580, justify='left').pack(anchor='w')

        self._sampling_note(self.noise_results_frame,
            "Noise was measured in 15 one-second segments spaced evenly through "
            "the middle of the video (20% to 80% of its length — the first and "
            "last 20% are skipped to avoid leaders, static, and credits). The "
            "score is the average of all segments, so noise confined to one "
            "section of the tape may read lower than it looks.")

        # Show options
        card = tk.Frame(self.noise_options_frame, bg=Colors.BG_CARD)
        card.pack(fill='x', pady=(10, 0))
        
        options = [
            ("No noise removal", "none", "Keep original grain/noise"),
            ("Light denoising", "moderate", "BM3D (or SMDegrain if unavailable) with moderate settings"),
            ("Heavy denoising", "heavy", "BM3D (or SMDegrain if unavailable) with stronger settings")
        ]
        
        for i, (label, value, desc) in enumerate(options):
            ModernRadioButton(card, label, self.noise_var, value, desc).pack(fill='x')
            if i < len(options) - 1:
                ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
        
        # Pre-select based on recommendation
        self.noise_var.set(rec)
        self.config_data['noise_level'] = rec
        
        self.noise_var.trace_add('write', lambda *_: self.config_data.update({'noise_level': self.noise_var.get()}))
    
    # ==================== DEHALO PAGE ====================

    def _page_dehalo(self):
        tk.Label(self.page_container, text="Dehalo",
                font=('Segoe UI', 22, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')

        tk.Label(self.page_container,
                text="Halos are bright ghost outlines along strong edges, caused by VHS "
                     "sharpening circuits or capture-card edge enhancement.",
                font=('Segoe UI', 13, 'bold'),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
                wraplength=620, justify='left').pack(anchor='w', pady=(4, 14))

        self._show_experimental_notice(self.page_container)

        initial_dehalo = self.config_data.get('dehalo_mode', 'none')
        self.config_data['dehalo_mode'] = initial_dehalo
        self.dehalo_var = tk.StringVar(value=initial_dehalo)

        # Batch mode: no analysis, just the options
        num_files = len(self.config_data.get('input_files', []))
        if num_files > 1:
            tk.Label(self.page_container,
                    text=f"Analysis not available in batch mode ({num_files} files selected). "
                         "Choose a level to apply to all files, or process one at a time for auto-analysis.",
                    font=('Segoe UI', 13, 'bold'),
                    fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
                    wraplength=580, justify='left').pack(anchor='w', pady=(4, 20))
            self._show_dehalo_options(self.page_container)
            return

        # Single file — progress card + threaded analysis
        self.dehalo_progress_card = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=20, pady=20)
        self.dehalo_progress_card.pack(fill='x', pady=(10, 0))

        self.dehalo_spinner_label = tk.Label(self.dehalo_progress_card, text="⏳",
                font=('Segoe UI', 28),
                fg=Colors.ACCENT, bg=Colors.BG_CARD)
        self.dehalo_spinner_label.pack()

        self.dehalo_status_label = tk.Label(self.dehalo_progress_card,
                text="Analyzing edges for halos...",
                font=('Segoe UI', 12, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD)
        self.dehalo_status_label.pack(pady=(10, 5))

        self.dehalo_progress_label = tk.Label(self.dehalo_progress_card,
                text="Sampling frame 1 of 8",
                font=('Segoe UI', 12),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD)
        self.dehalo_progress_label.pack()

        self.dehalo_results_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        self.dehalo_results_frame.pack(fill='x')

        self.dehalo_options_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        self.dehalo_options_frame.pack(fill='x', pady=(10, 0))

        self.dehalo_analysis_complete = False
        self._animate_dehalo_spinner()
        threading.Thread(target=self._run_dehalo_analysis, daemon=True).start()

    def _show_dehalo_options(self, parent):
        """The three dehalo radio options (shared by analysis/batch/error paths)."""
        card = tk.Frame(parent, bg=Colors.BG_CARD)
        card.pack(fill='x')

        options = [
            ("No dehalo", "none", "Edges look clean — no ghost outlines"),
            ("Light dehalo", "light", "Removes bright halos only, protects fine detail and dark edges"),
            ("Strong dehalo", "strong", "Removes bright and dark halos — for heavily oversharpened tapes"),
        ]
        for i, (label, value, desc) in enumerate(options):
            ModernRadioButton(card, label, self.dehalo_var, value, desc).pack(fill='x')
            if i < len(options) - 1:
                ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)

        self.dehalo_var.trace_add('write', lambda *_: self.config_data.update(
            {'dehalo_mode': self.dehalo_var.get()}))

    def _animate_dehalo_spinner(self):
        if not hasattr(self, 'dehalo_analysis_complete') or self.dehalo_analysis_complete:
            return
        if not hasattr(self, 'dehalo_spinner_label') or not self.dehalo_spinner_label.winfo_exists():
            return
        spinners = ['⏳', '⌛']
        current = self.dehalo_spinner_label.cget('text')
        next_idx = (spinners.index(current) + 1) % len(spinners) if current in spinners else 0
        self.dehalo_spinner_label.config(text=spinners[next_idx])
        self.after(500, self._animate_dehalo_spinner)

    def _update_dehalo_progress(self, current, total):
        if hasattr(self, 'dehalo_progress_label') and self.dehalo_progress_label.winfo_exists():
            self.after(0, lambda: self.dehalo_progress_label.config(
                text=f"Sampling frame {current} of {total}"))

    def _run_dehalo_analysis(self):
        if 'input_path' not in self.config_data:
            self.after(0, self._finish_dehalo_analysis_error, "❌ No file selected")
            return
        try:
            halo_data = analyze_halo_level(
                self.config_data['input_path'],
                sample_frames=8,
                progress_callback=self._update_dehalo_progress
            )
            if halo_data and halo_data.get('analyzed'):
                self.config_data['halo_data'] = halo_data
                self.after(0, lambda: self._show_dehalo_results(halo_data))
            else:
                self.after(0, self._finish_dehalo_analysis_error,
                           "Could not analyze halos (not enough edges found)")
        except Exception as e:
            self.after(0, self._finish_dehalo_analysis_error, f"Analysis error: {str(e)[:30]}")

    def _finish_dehalo_analysis_error(self, message):
        self.dehalo_analysis_complete = True
        if hasattr(self, 'dehalo_progress_card'):
            self.dehalo_progress_card.pack_forget()
        tk.Label(self.dehalo_results_frame, text=message,
                font=('Segoe UI', 12),
                fg=Colors.ERROR, bg=Colors.BG_MAIN).pack(anchor='w', pady=(0, 10))
        self._show_dehalo_options(self.dehalo_options_frame)

    def _show_dehalo_results(self, data):
        self.dehalo_analysis_complete = True
        # User may have navigated away while the analysis thread was running
        if not (hasattr(self, 'dehalo_results_frame')
                and self.dehalo_results_frame.winfo_exists()):
            return
        if hasattr(self, 'dehalo_progress_card'):
            self.dehalo_progress_card.pack_forget()

        result_card = tk.Frame(self.dehalo_results_frame, bg=Colors.BG_CARD, padx=15, pady=12)
        result_card.pack(fill='x')

        tk.Label(result_card, text="📊 Halo Analysis",
                font=('Segoe UI', 10, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD).pack(anchor='w')

        level = data.get('halo_level', 'unknown')
        if level == 'strong':
            icon, color, desc = "🔴", Colors.ERROR, "Strong halos detected"
        elif level == 'moderate':
            icon, color, desc = "🟠", Colors.WARNING, "Moderate halos detected"
        elif level == 'light':
            icon, color, desc = "🟡", Colors.WARNING, "Light halos detected"
        else:
            icon, color, desc = "🟢", Colors.SUCCESS, "Edges appear clean"

        tk.Label(result_card, text=f"{icon} {desc}",
                font=('Segoe UI', 12),
                fg=color, bg=Colors.BG_CARD).pack(anchor='w', pady=(3, 0))

        ratio_pct = data.get('halo_ratio', 0) * 100
        edges = data.get('edges_analyzed', 0)
        tech_text = (f"Halo score: {ratio_pct:.1f}% of strong edges show ringing  "
                     f"({edges} edges analyzed)")
        self._selectable_label(result_card, tech_text,
                font=('Segoe UI', 12),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD).pack(anchor='w', pady=(2, 0))

        # === RECOMMENDATION ===
        ttk.Separator(result_card, orient='horizontal').pack(fill='x', pady=(10, 8))

        rec = data.get('recommendation', 'none')
        bands = {'strong': 'strong > 30%', 'moderate': 'moderate 18–30%',
                 'light': 'light 10–18%', 'clean': 'clean < 10%'}
        score_str = f"halo score {ratio_pct:.1f}% — {bands.get(level, '')}"
        if rec == 'strong':
            rec_text = f"💡 Recommendation: Strong dehalo  ·  {score_str}"
        elif rec == 'light':
            rec_text = f"💡 Recommendation: Light dehalo  ·  {score_str}"
        else:
            rec_text = (f"💡 Recommendation: No dehalo needed  ·  {score_str} — "
                        "but you can still enable it below if you see edge ghosting.")

        tk.Label(result_card, text=rec_text,
                font=('Segoe UI', 10, 'bold'),
                fg=Colors.ACCENT, bg=Colors.BG_CARD,
                wraplength=580, justify='left').pack(anchor='w')

        self._sampling_note(self.dehalo_results_frame,
            "Edges were examined in 8 frames spaced evenly through the middle "
            "of the video (20% to 80% of its length — the first and last 20% "
            "are skipped to avoid leaders, static, and credits). If halos only "
            "affect certain scenes, the average may understate them.")

        self._show_dehalo_options(self.dehalo_options_frame)

        # Pre-select based on recommendation
        self.dehalo_var.set(rec)
        self.config_data['dehalo_mode'] = rec

    def _page_dropouts(self):
        tk.Label(self.page_container, text="Dropout Removal",
                font=('Segoe UI', 22, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')
        
        tk.Label(self.page_container,
                text="Dropouts are brief flashes, spots, or streaks from tape damage",
                font=('Segoe UI', 13, 'bold'),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(4, 20))
        
        # Get initial value and save it immediately
        initial_dropout = 'yes' if self.config_data.get('dropout_removal') else 'no'
        self.config_data['dropout_removal'] = (initial_dropout == 'yes')
        self.dropout_var = tk.StringVar(value=initial_dropout)
        
        card = tk.Frame(self.page_container, bg=Colors.BG_CARD)
        card.pack(fill='x')
        
        ModernRadioButton(card, "No", self.dropout_var, "no",
                         "Video looks clean, no dropouts").pack(fill='x')
        ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(card, "Yes, fix dropouts", self.dropout_var, "yes",
                         "Video has momentary glitches or streaks").pack(fill='x')
        
        self.dropout_var.trace_add('write', lambda *_: self.config_data.update({'dropout_removal': self.dropout_var.get() == 'yes'}))

    def _page_upscale(self):
        tk.Label(self.page_container, text="Upscale with NNEDI3",
                font=('Segoe UI', 22, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')

        sc = self.config_data.get('source_classification', {}).get('source_class', 'sd')
        if sc in ('avchd', 'hdv'):
            self.config_data['upscale_enabled'] = False
            card = tk.Frame(self.page_container, bg=Colors.BG_CARD)
            card.pack(fill='x', pady=(14, 0))
            tk.Label(card,
                     text="Not applicable for HD sources.",
                     font=('Segoe UI', 13, 'bold'),
                     fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD).pack(anchor='w', padx=16, pady=(12, 4))
            tk.Label(card,
                     text="Your source is already 1080i HD. This software is programmed to upscale to a maximum of 1920×1080.",
                     font=('Segoe UI', 12),
                     fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                     wraplength=560, justify='left').pack(anchor='w', padx=16, pady=(0, 12))
            return

        tk.Label(self.page_container,
                text=("Upscaling resizes your standard definition capture. Platforms like YouTube "
                      "often apply better compression to HD uploads, making your final video look "
                      "much cleaner online. Please note that upscaled videos take up significantly "
                      "more hard drive space."),
                font=('Segoe UI', 13),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
                wraplength=580, justify='left').pack(anchor='w', pady=(4, 14))

        # ── Resolution selector (includes No Upscale) ────────────────────────
        video_format = self.config_data.get('format', 'ntsc')
        if video_format == 'ntsc':
            res_options = [
                ("No Upscale",  "none",      "Keep original resolution (640×480)"),
                ("960×720",     "960x720",   "1.5× upscale — good quality/speed balance"),
                ("1280×960",    "1280x960",  "2× upscale — high quality, slower"),
                ("1440×1080",   "1440x1080", "2.25× upscale — highest quality, slowest"),
            ]
        else:
            res_options = [
                ("No Upscale",  "none",      "Keep original resolution (768×576)"),
                ("1024×768",    "1024x768",  "1.33× upscale — good quality/speed balance"),
                ("1280×960",    "1280x960",  "1.67× upscale — high quality, slower"),
                ("1440×1080",   "1440x1080", "1.875× upscale — highest quality, slowest"),
            ]

        if self.config_data.get('upscale_enabled', False):
            saved = self.config_data.get('upscale_resolution',
                                         '960x720' if video_format == 'ntsc' else '1024x768')
        else:
            saved = 'none'

        self.upscale_res_var = tk.StringVar(value=saved)

        def _on_res_change(*_):
            val = self.upscale_res_var.get()
            self.config_data['upscale_enabled'] = (val != 'none')
            if val != 'none':
                self.config_data['upscale_resolution'] = val

        self.upscale_res_var.trace_add('write', _on_res_change)

        card = tk.Frame(self.page_container, bg=Colors.BG_CARD)
        card.pack(fill='x')

        for i, (label, value, desc) in enumerate(res_options):
            ModernRadioButton(card, label, self.upscale_res_var, value, desc).pack(fill='x')
            if i < len(res_options) - 1:
                ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)

    def _page_color(self):
        tk.Label(self.page_container, text="Color Analysis",
                font=('Segoe UI', 22, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')

        self._show_artifact_example(self.page_container, 'color_cast',
            "What a color cast looks like — a warm or cool tint over the whole image:")
        self._show_experimental_notice(self.page_container)

        # DaVinci Resolve recommendation note
        resolve_card = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=15, pady=12)
        resolve_card.pack(fill='x', pady=(8, 0))
        tk.Label(resolve_card,
                 text="💡 Tip: Consider color correcting in DaVinci Resolve instead",
                 font=('Segoe UI', 10, 'bold'),
                 fg=Colors.ACCENT, bg=Colors.BG_CARD).pack(anchor='w')
        tk.Label(resolve_card,
                 text=("My recommendation in general is to not change the color in this app. "
                       "Instead, after you export the video, bring it into the free DaVinci Resolve "
                       "and color correct in there. It's the best and easiest tool to use for color work."),
                 font=('Segoe UI', 11),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                 wraplength=580, justify='left').pack(anchor='w', pady=(4, 0))

        # Check if multiple files selected
        num_files = len(self.config_data.get('input_files', []))
        if num_files > 1:
            self._show_batch_disabled_message("Color Analysis")
            # Set default to no correction
            self.config_data['color_correction'] = 'none'
            return
        
        # Progress indicator card
        self.color_progress_card = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=20, pady=20)
        self.color_progress_card.pack(fill='x', pady=(10, 0))
        
        self.color_spinner_label = tk.Label(self.color_progress_card, text="⏳",
                font=('Segoe UI', 28),
                fg=Colors.ACCENT, bg=Colors.BG_CARD)
        self.color_spinner_label.pack()
        
        self.color_status_label = tk.Label(self.color_progress_card, 
                text="Analyzing video colors...",
                font=('Segoe UI', 12, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD)
        self.color_status_label.pack(pady=(10, 5))
        
        self.color_progress_label = tk.Label(self.color_progress_card, 
                text="Generating vectorscope and analyzing color channels",
                font=('Segoe UI', 12),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD)
        self.color_progress_label.pack()
        
        # Image preview for vectorscope (hidden initially)
        self.color_preview = ImagePreview(self.page_container)
        
        # Analysis results 
        self.color_results_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        self.color_results_frame.pack(fill='x', pady=(10, 0))
        
        # Options frame (hidden until analysis complete)
        self.color_options_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        self.color_options_frame.pack(fill='x', pady=(10, 0))
        
        self.color_var = tk.StringVar(value='none')
        
        # Disable Next button during analysis
        self.color_analysis_complete = False
        if hasattr(self, 'next_btn'):
            self.next_btn.configure(state='disabled')
        
        # Start spinner animation
        self._animate_color_spinner()
        
        # Run analysis in thread
        threading.Thread(target=self._run_color_analysis, daemon=True).start()
    
    def _animate_color_spinner(self):
        """Animate the spinner during analysis."""
        if not hasattr(self, 'color_analysis_complete') or self.color_analysis_complete:
            return
        
        if not hasattr(self, 'color_spinner_label') or not self.color_spinner_label.winfo_exists():
            return
            
        spinners = ['⏳', '⌛']
        current = self.color_spinner_label.cget('text')
        next_idx = (spinners.index(current) + 1) % len(spinners) if current in spinners else 0
        self.color_spinner_label.config(text=spinners[next_idx])
        
        self.after(500, self._animate_color_spinner)
    
    def _show_batch_disabled_message(self, feature_name):
        """Show message explaining why a feature is disabled for batch processing."""
        tk.Label(self.page_container, 
                text="Skipped for batch processing",
                font=('Segoe UI', 13, 'bold'),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(4, 20))
        
        # Info card
        card = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=20, pady=20)
        card.pack(fill='x')
        
        # Icon and message
        tk.Label(card, text="ℹ️",
                font=('Segoe UI', 24),
                fg=Colors.ACCENT, bg=Colors.BG_CARD).pack(anchor='w')
        
        message = (
            f"When multiple videos are selected, the {feature_name} tool is not available.\n\n"
            f"Each video may have different color characteristics, so automatic correction "
            f"based on one file would not produce accurate results for the others.\n\n"
            f"If you would like to analyze and correct color for your videos, "
            f"process them one at a time."
        )
        
        tk.Label(card, text=message,
                font=('Segoe UI', 12),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                justify='left', wraplength=500).pack(anchor='w', pady=(10, 0))
        
        # File count reminder
        num_files = len(self.config_data.get('input_files', []))
        tk.Label(card, text=f"📁 {num_files} files selected for batch processing",
                font=('Segoe UI', 10, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD).pack(anchor='w', pady=(15, 0))
    
    def _run_color_analysis(self):
        if 'input_path' not in self.config_data:
            self.after(0, self._finish_color_analysis_error, "❌ No file selected")
            return
        
        filepath = self.config_data['input_path']

        # Generate vectorscope
        self.after(0, lambda: self.color_status_label.config(text="Generating vectorscope..."))
        try:
            vectorscope_path = generate_vectorscope_image(
                filepath,
                color_matrix=self.config_data.get('color_matrix', 'bt601'),
                video_format=self.config_data.get('format', 'ntsc'))
            if vectorscope_path:
                self.temp_images.append(vectorscope_path)
        except Exception:
            vectorscope_path = None

        # Generate RGB histogram
        self.after(0, lambda: self.color_status_label.config(text="Generating RGB histogram..."))
        try:
            color_histogram_path = generate_rgb_histogram(
                filepath,
                color_matrix=self.config_data.get('color_matrix', 'bt601'),
                video_format=self.config_data.get('format', 'ntsc'))
            if color_histogram_path:
                self.temp_images.append(color_histogram_path)
        except Exception:
            color_histogram_path = None

        # Analyze color channels
        self.after(0, lambda: self.color_status_label.config(text="Analyzing color channels..."))
        self.after(0, lambda: self.color_progress_label.config(text="Measuring U/V chroma and saturation"))
        color_data = analyze_color_data(filepath)

        if color_data:
            self.config_data['color_data'] = color_data
            self.config_data['u_correction'] = color_data['u_correction']
            self.config_data['v_correction'] = color_data['v_correction']
            self.after(0, lambda: self._show_color_results(
                color_data, vectorscope_path, color_histogram_path))
        else:
            self.after(0, self._finish_color_analysis_error, "Could not analyze colors")
    
    def _finish_color_analysis_error(self, message):
        """Handle color analysis error."""
        self.color_analysis_complete = True
        self._on_analysis_section_done()
        
        # Hide progress card
        if hasattr(self, 'color_progress_card'):
            self.color_progress_card.pack_forget()
        
        # Show error
        error_label = tk.Label(self.color_results_frame, text=message,
                font=('Segoe UI', 12),
                fg=Colors.ERROR, bg=Colors.BG_MAIN)
        error_label.pack(anchor='w', pady=(0, 10))
        
        # Show basic options
        self._show_color_options_fallback()
    
    def _show_color_options_fallback(self):
        """Show basic color options without analysis."""
        card = tk.Frame(self.color_options_frame, bg=Colors.BG_CARD)
        card.pack(fill='x')
        
        ModernRadioButton(card, "No correction", self.color_var, "none",
                         "Keep original colors").pack(fill='x')
        ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(card, "Boost saturation", self.color_var, "boost_sat",
                         "Make colors more vibrant").pack(fill='x')
        ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(card, "Reduce saturation", self.color_var, "reduce_sat",
                         "Tone down oversaturated colors").pack(fill='x')
        
        self.config_data['color_correction'] = 'none'
        self.color_var.trace_add('write', lambda *_: self.config_data.update({'color_correction': self.color_var.get()}))
    
    def _show_color_results(self, data, vectorscope_path=None, color_histogram_path=None):
        # Mark analysis complete; unlock Next only when all analyses are done
        self.color_analysis_complete = True
        self._on_analysis_section_done()

        # Hide progress card
        if hasattr(self, 'color_progress_card'):
            self.color_progress_card.pack_forget()

        # ── Scope tabs: Vectorscope / RGB Histogram ───────────────────────────
        if vectorscope_path or color_histogram_path:
            scope_outer = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
            scope_outer.pack(fill='x', pady=(10, 0), before=self.color_results_frame)

            tab_bar = tk.Frame(scope_outer, bg=Colors.BG_MAIN)
            tab_bar.pack(fill='x', pady=(0, 4))
            tk.Label(tab_bar, text="Color Scopes",
                     font=('Segoe UI', 11, 'bold'),
                     fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(side='left')

            color_scope_active = tk.StringVar(value='vectorscope')
            scope_img = ImagePreview(scope_outer)
            scope_img.pack(fill='x')

            def _show_color_scope():
                path = (vectorscope_path if color_scope_active.get() == 'vectorscope'
                        else color_histogram_path)
                if path:
                    scope_img.load_image(path, max_width=520, max_height=280)
                else:
                    scope_img.image_label.config(
                        text="⚠ Scope image not available",
                        fg=Colors.WARNING, font=('Segoe UI', 11))

            def _make_color_tab(text, value):
                lbl = tk.Label(tab_bar, text=text,
                               font=('Segoe UI', 10, 'bold'), cursor='hand2',
                               padx=10, pady=4, relief='flat',
                               fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD)
                lbl.pack(side='right', padx=(4, 0))
                def _activate(lbl=lbl, value=value):
                    color_scope_active.set(value)
                    _refresh_color_tab_style()
                    _show_color_scope()
                lbl.bind('<Button-1>', lambda _e, a=_activate: a())
                return lbl

            _tab_hist = _make_color_tab("RGB Histogram (stacked)", 'histogram')
            _tab_vs   = _make_color_tab("Vectorscope",   'vectorscope')

            def _refresh_color_tab_style():
                active = color_scope_active.get()
                for lbl, val in ((_tab_vs, 'vectorscope'), (_tab_hist, 'histogram')):
                    if val == active:
                        lbl.configure(fg=Colors.ACCENT, bg=Colors.BG_MAIN,
                                      relief='solid', bd=1)
                    else:
                        lbl.configure(fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                                      relief='flat', bd=0)

            _refresh_color_tab_style()
            _show_color_scope()
        
        # Show numeric results
        result_card = tk.Frame(self.color_results_frame, bg=Colors.BG_CARD, padx=15, pady=10)
        result_card.pack(fill='x')
        
        result_text = f"U: {data['u_avg']:.1f} ({data['u_offset']:+.1f})  •  "
        result_text += f"V: {data['v_avg']:.1f} ({data['v_offset']:+.1f})  •  "
        result_text += f"Saturation: {data['sat_avg']:.1f}"
        
        self._selectable_label(result_card, result_text,
                font=('Segoe UI', 12),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD).pack(anchor='w', fill='x')

        if data['color_cast']:
            tk.Label(result_card, text=f"⚠️ Detected {data['color_cast']} color cast",
                    font=('Segoe UI', 12),
                    fg=Colors.WARNING, bg=Colors.BG_CARD).pack(anchor='w', pady=(5, 0))

        self._sampling_note(self.color_results_frame,
            "Color was measured in 10 frames spaced evenly across the full "
            "length of the video. A cast must be consistent across those "
            "samples to be flagged, so a tint affecting only one scene won't "
            "trigger a recommendation. The vectorscope/histogram image shows a "
            "single frame from the midpoint of the video.")

        # Show options
        card = tk.Frame(self.color_options_frame, bg=Colors.BG_CARD)
        card.pack(fill='x')
        
        ModernRadioButton(card, "No correction", self.color_var, "none",
                         "Colors look fine").pack(fill='x')
        
        if data['color_cast']:
            ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
            ModernRadioButton(card, f"Auto-fix {data['color_cast']} cast (recommended)", 
                            self.color_var, "auto_fix",
                            f"Shift U by {data['u_correction']:+.1f}, V by {data['v_correction']:+.1f}").pack(fill='x')
            self.color_var.set('auto_fix')
            # Save immediately since trace_add hasn't been set yet
            self.config_data['color_correction'] = 'auto_fix'
            
            ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
            ModernRadioButton(card, f"Auto-fix {data['color_cast']} cast + boost saturation", 
                            self.color_var, "auto_fix_boost",
                            f"Fix color cast and make colors more vibrant").pack(fill='x')
        
        ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(card, "Boost saturation only", self.color_var, "boost_sat",
                         "Make colors more vibrant (no color cast fix)").pack(fill='x')
        
        ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(card, "Reduce saturation", self.color_var, "reduce_sat",
                         "Tone down oversaturated colors").pack(fill='x')
        
        self.color_var.trace_add('write', lambda *_: self.config_data.update({'color_correction': self.color_var.get()}))
    
    def _page_levels(self):
        tk.Label(self.page_container, text="Video Levels",
                font=('Segoe UI', 22, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')

        self._show_experimental_notice(self.page_container)

        # Check if multiple files selected
        num_files = len(self.config_data.get('input_files', []))
        if num_files > 1:
            self._show_batch_disabled_message("Video Levels")
            # Set default to no adjustment
            self.config_data['levels_adjustment'] = 'none'
            return
        
        # Progress indicator card
        self.levels_progress_card = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=20, pady=20)
        self.levels_progress_card.pack(fill='x', pady=(10, 0))
        
        self.levels_spinner_label = tk.Label(self.levels_progress_card, text="⏳",
                font=('Segoe UI', 28),
                fg=Colors.ACCENT, bg=Colors.BG_CARD)
        self.levels_spinner_label.pack()
        
        self.levels_status_label = tk.Label(self.levels_progress_card, 
                text="Analyzing brightness levels...",
                font=('Segoe UI', 12, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD)
        self.levels_status_label.pack(pady=(10, 5))
        
        self.levels_progress_label = tk.Label(self.levels_progress_card, 
                text="Generating RGB parade and measuring luma range",
                font=('Segoe UI', 12),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD)
        self.levels_progress_label.pack()
        
        # Image preview for waveform (hidden initially)
        self.levels_preview = ImagePreview(self.page_container)
        
        # Analysis results
        self.levels_results_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        self.levels_results_frame.pack(fill='x', pady=(10, 0))
        
        # Options frame
        self.levels_options_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        self.levels_options_frame.pack(fill='x', pady=(10, 0))
        
        self.levels_var = tk.StringVar(value='none')
        
        # Disable Next button during analysis
        self.levels_analysis_complete = False
        if hasattr(self, 'next_btn'):
            self.next_btn.configure(state='disabled')
        
        # Start spinner animation
        self._animate_levels_spinner()
        
        # Run analysis in thread
        threading.Thread(target=self._run_levels_analysis, daemon=True).start()
    
    def _animate_levels_spinner(self):
        """Animate the spinner during analysis."""
        if not hasattr(self, 'levels_analysis_complete') or self.levels_analysis_complete:
            return
        
        if not hasattr(self, 'levels_spinner_label') or not self.levels_spinner_label.winfo_exists():
            return
            
        spinners = ['⏳', '⌛']
        current = self.levels_spinner_label.cget('text')
        next_idx = (spinners.index(current) + 1) % len(spinners) if current in spinners else 0
        self.levels_spinner_label.config(text=spinners[next_idx])
        
        self.after(500, self._animate_levels_spinner)
    
    def _run_levels_analysis(self):
        if 'input_path' not in self.config_data:
            self.after(0, self._finish_levels_analysis_error, "❌ No file selected")
            return

        filepath = self.config_data['input_path']

        # Determine video duration for scope scrubbing
        try:
            dur_result = run_hidden([FFPROBE_PATH, '-v', 'error', '-show_entries',
                                     'format=duration', '-of', 'csv=p=0', filepath], timeout=30)
            scope_duration = float(dur_result.stdout.strip())
        except Exception:
            scope_duration = 60.0
        scope_ts = scope_duration * 0.5

        # Generate RGB parade image
        self.after(0, lambda: self.levels_status_label.config(text="Generating RGB parade..."))
        waveform_path = None
        try:
            waveform_path = generate_histogram_image(
                filepath, timestamp=scope_ts,
                color_matrix=self.config_data.get('color_matrix', 'bt601'),
                video_format=self.config_data.get('format', 'ntsc'))
            if waveform_path:
                self.temp_images.append(waveform_path)
        except Exception:
            pass

        # Analyze luma levels
        self.after(0, lambda: self.levels_status_label.config(text="Analyzing luma levels..."))
        self.after(0, lambda: self.levels_progress_label.config(text="Measuring min/max brightness"))
        levels_data = analyze_video_levels(filepath)

        if levels_data and levels_data['min_y'] is not None:
            self.config_data['levels_data'] = levels_data
            self.after(0, lambda: self._show_levels_results(
                levels_data, waveform_path, scope_duration))
        else:
            self.after(0, self._finish_levels_analysis_error, "Could not analyze levels")
    
    def _finish_levels_analysis_error(self, message):
        """Handle levels analysis error."""
        self.levels_analysis_complete = True
        self._on_analysis_section_done()
        
        # Hide progress card
        if hasattr(self, 'levels_progress_card'):
            self.levels_progress_card.pack_forget()
        
        # Show error
        error_label = tk.Label(self.levels_results_frame, text=message,
                font=('Segoe UI', 12),
                fg=Colors.ERROR, bg=Colors.BG_MAIN)
        error_label.pack(anchor='w', pady=(0, 10))
        
        # Show basic options
        self._show_levels_options_fallback()
    
    def _show_levels_options_fallback(self):
        """Show basic levels options without analysis."""
        card = tk.Frame(self.levels_options_frame, bg=Colors.BG_CARD)
        card.pack(fill='x')
        
        ModernRadioButton(card, "No adjustment", self.levels_var, "none",
                         "Keep original levels").pack(fill='x')
        ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(card, "Expand to full range", self.levels_var, "expand",
                         "Stretch levels to use full 16-235 range").pack(fill='x')
        
        self.config_data['levels_adjustment'] = 'none'
        self.levels_var.trace_add('write', lambda *_: self.config_data.update({'levels_adjustment': self.levels_var.get()}))
    
    def _show_levels_results(self, data, waveform_path=None, scope_duration=60.0):
        # Mark analysis complete; unlock Next only when all analyses are done
        self.levels_analysis_complete = True
        self._on_analysis_section_done()

        # Hide progress card
        if hasattr(self, 'levels_progress_card'):
            self.levels_progress_card.pack_forget()

        # ── Waveform monitor + frame scrubber ─────────────────────────────────
        self._scope_waveform_path = waveform_path
        self._scope_duration      = scope_duration
        self._scope_filepath      = self.config_data.get('input_path', '')

        scope_outer = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        scope_outer.pack(fill='x', pady=(10, 0), before=self.levels_results_frame)

        hdr = tk.Frame(scope_outer, bg=Colors.BG_MAIN)
        hdr.pack(fill='x', pady=(0, 4))
        tk.Label(hdr, text="RGB Parade (R · G · B)",
                 font=('Segoe UI', 11, 'bold'),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(side='left')
        tk.Label(scope_outer,
                 text="Red / Green / Blue channels shown left to right — used for "
                      "level-matching and color cast diagnosis.",
                 font=('Segoe UI', 10),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
                 wraplength=580, justify='left').pack(anchor='w', pady=(0, 4))

        self._scope_preview = ImagePreview(scope_outer)
        self._scope_preview.pack(fill='x')

        def _show_scope_image():
            if self._scope_waveform_path:
                self._scope_preview.load_image(
                    self._scope_waveform_path, max_width=580, max_height=300)
            else:
                self._scope_preview.image_label.config(
                    text="⚠ RGB parade not available", fg=Colors.WARNING,
                    font=('Segoe UI', 11))

        _show_scope_image()
        self._show_scope_image = _show_scope_image

        # Frame scrubber
        scrub_frame = tk.Frame(scope_outer, bg=Colors.BG_MAIN)
        scrub_frame.pack(fill='x', pady=(6, 0))
        tk.Label(scrub_frame, text="Frame:",
                 font=('Segoe UI', 10), fg=Colors.TEXT_SECONDARY,
                 bg=Colors.BG_MAIN).pack(side='left')
        self._scope_slider = tk.Scale(scrub_frame, from_=0, to=100,
                                      orient='horizontal', showvalue=False,
                                      bg=Colors.BG_MAIN, fg=Colors.TEXT_PRIMARY,
                                      troughcolor=Colors.BG_CARD,
                                      highlightthickness=0, bd=0, length=340)
        self._scope_slider.set(50)
        self._scope_slider.pack(side='left', padx=(6, 8))
        self._scope_pct_label = tk.Label(scrub_frame, text="50%",
                                          font=('Segoe UI', 10),
                                          fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
                                          width=4)
        self._scope_pct_label.pack(side='left')
        self._scope_slider.configure(
            command=lambda v: self._scope_pct_label.config(text=f"{int(float(v))}%"))
        tk.Button(scrub_frame, text="Refresh",
                  font=('Segoe UI', 9, 'bold'),
                  fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD,
                  activebackground=Colors.ACCENT,
                  relief='flat', cursor='hand2', padx=8, pady=3,
                  command=self._refresh_scope_display).pack(side='left', padx=(4, 0))

        if hasattr(self, 'levels_preview'):
            try:
                self.levels_preview.pack_forget()
            except Exception:
                pass
        
        # Show numeric results
        result_card = tk.Frame(self.levels_results_frame, bg=Colors.BG_CARD, padx=15, pady=10)
        result_card.pack(fill='x')
        
        result_text = f"Min Y: {data['min_y']}  •  Max Y: {data['max_y']}  •  Legal range: 16-235"
        self._selectable_label(result_card, result_text,
                font=('Segoe UI', 12),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD).pack(anchor='w', fill='x')
        
        if data['needs_adjustment']:
            tk.Label(result_card, text="⚠️ Levels outside legal range detected",
                    font=('Segoe UI', 12),
                    fg=Colors.WARNING, bg=Colors.BG_CARD).pack(anchor='w', pady=(5, 0))
        else:
            tk.Label(result_card, text="✓ Levels within legal range",
                    font=('Segoe UI', 12),
                    fg=Colors.SUCCESS, bg=Colors.BG_CARD).pack(anchor='w', pady=(5, 0))

        self._sampling_note(self.levels_results_frame,
            "Brightness was measured in 10 frames spaced evenly across the "
            "full length of the video; Min/Max are the extremes seen in any of "
            "those samples. The RGB parade above shows a single frame (the "
            "midpoint by default) — use the Frame scrubber to inspect other "
            "parts of the tape.")

        # Options
        card = tk.Frame(self.levels_options_frame, bg=Colors.BG_CARD)
        card.pack(fill='x')
        
        ModernRadioButton(card, "No adjustment — recommended", self.levels_var, "none",
                         "Preserves all captured data including super-whites and super-blacks").pack(fill='x')
        ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
        
        # Add note to clamp option; do NOT auto-recommend it — clamping discards
        # super-white/super-black data that is often genuine picture content on
        # analog tape captures and cannot be recovered after encoding.
        clamp_label = "Clamp to legal (16-235)"
        ModernRadioButton(card, clamp_label, self.levels_var, "clamp",
                         "Clips values outside 16-235 — use only if broadcast compliance is required").pack(fill='x')
        ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(card, "Stretch to legal", self.levels_var, "stretch",
                         "Compresses full range, may reduce contrast").pack(fill='x')
        
        # Always default to 'none' — clamping permanently loses data.
        # The analysis result is shown for information; user decides.
        self.levels_var.set('none')
        self.config_data['levels_adjustment'] = 'none'
        
        self.levels_var.trace_add('write', lambda *_: self.config_data.update({'levels_adjustment': self.levels_var.get()}))
        
        # Help box explaining the options
        help_frame = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=15, pady=12)
        help_frame.pack(fill='x', pady=(15, 0))
        
        tk.Label(help_frame, text="ℹ️ Which should I choose?",
                font=('Segoe UI', 10, 'bold'),
                fg=Colors.ACCENT, bg=Colors.BG_CARD).pack(anchor='w')
        
        help_text = (
            "No adjustment: Recommended for analog captures. Preserves every value the "
            "capture card recorded — super-whites and super-blacks are often real picture "
            "content on VHS/Hi8 tape, not noise.\n\n"
            "Clamp: Permanently discards values outside 16-235. Only use this if you "
            "specifically need broadcast-legal output and have confirmed the out-of-range "
            "values are noise.\n\n"
            "Stretch: Compresses the full 0-255 range into 16-235. Use only if the video "
            "was captured at full range by mistake."
        )
        tk.Label(help_frame, text=help_text,
                font=('Segoe UI', 12),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                justify='left', wraplength=550).pack(anchor='w', pady=(5, 0))
    
    def _refresh_scope_display(self):
        """Re-generate the waveform at the timestamp selected by the scrubber."""
        pct = self._scope_slider.get()
        ts  = self._scope_duration * (pct / 100.0)
        fp  = self._scope_filepath

        if hasattr(self, '_scope_preview'):
            self._scope_preview.image_label.config(
                text="⏳ Refreshing…", image='', fg=Colors.ACCENT,
                font=('Segoe UI', 11))

        def _worker():
            wave = generate_histogram_image(
                fp, timestamp=ts,
                color_matrix=self.config_data.get('color_matrix', 'bt601'),
                video_format=self.config_data.get('format', 'ntsc'))
            if wave:
                self.temp_images.append(wave)
            self.after(0, lambda: self._apply_refreshed_scopes(wave))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_refreshed_scopes(self, waveform_path):
        if waveform_path:
            self._scope_waveform_path = waveform_path
        if hasattr(self, '_show_scope_image'):
            self._show_scope_image()

    def _page_audio(self):
        tk.Label(self.page_container, text="Audio Options",
                font=('Segoe UI', 22, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')

        tk.Label(self.page_container, text="Mix Audio Channels",
                font=('Segoe UI', 13, 'bold'),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(4, 14))

        # ── PIL illustration ──────────────────────────────────────────────────
        if HAS_PIL:
            try:
                from PIL import ImageTk
                audio_img = _draw_audio_channels_example()
                if audio_img:
                    illus_frame = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=0, pady=0)
                    illus_frame.pack(fill='x', pady=(0, 14))
                    photo = ImageTk.PhotoImage(audio_img)
                    lbl = tk.Label(illus_frame, image=photo, bg=Colors.BG_CARD)
                    lbl.image = photo
                    lbl.pack(anchor='w')
                    self.temp_images.append(photo)
            except Exception:
                pass

        # ── Explanation text ──────────────────────────────────────────────────
        desc_frame = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=16, pady=12)
        desc_frame.pack(fill='x', pady=(0, 12))

        info_text = ("When enabled, left and right audio channels are combined and sent to "
                     "both speakers. This is useful when your source tape has audio recorded "
                     "on only one channel, which can happen with mono camcorders or damaged tapes.")
        tk.Label(desc_frame, text=info_text,
                font=('Segoe UI', 12),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                wraplength=580, justify='left').pack(anchor='w')

        # ── Checkbox ──────────────────────────────────────────────────────────
        cb_card = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=16, pady=14)
        cb_card.pack(fill='x', pady=(0, 12))

        self.mix_audio_var = tk.BooleanVar(value=self.config_data.get('mix_audio', False))

        cb = tk.Checkbutton(cb_card, text="Mix audio channels (copy left channel to right channel)",
                            variable=self.mix_audio_var,
                            font=('Segoe UI', 12),
                            fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD,
                            selectcolor=Colors.BG_DARK,
                            activebackground=Colors.BG_CARD,
                            activeforeground=Colors.TEXT_PRIMARY,
                            command=lambda: self.config_data.update({'mix_audio': self.mix_audio_var.get()}))
        cb.pack(anchor='w')

        # ── Warning box ───────────────────────────────────────────────────────
        warn_frame = tk.Frame(self.page_container, bg='#2A1500', padx=14, pady=12)
        warn_frame.pack(fill='x', pady=(0, 0))

        warn_top = tk.Frame(warn_frame, bg='#2A1500')
        warn_top.pack(fill='x')

        tk.Label(warn_top, text="⚠",
                 font=('Segoe UI', 16),
                 fg=Colors.WARNING, bg='#2A1500').pack(side='left', padx=(0, 8))

        tk.Label(warn_top, text="Important — read before enabling",
                 font=('Segoe UI', 11, 'bold'),
                 fg=Colors.WARNING, bg='#2A1500').pack(side='left')

        tk.Label(warn_frame,
                 text="If the audio already plays from both speakers normally, do NOT enable "
                      "this option. Mixing channels on audio that is already stereo will "
                      "collapse the stereo image to mono and cannot be undone.",
                 font=('Segoe UI', 11),
                 fg='#D0A060', bg='#2A1500',
                 wraplength=580, justify='left').pack(anchor='w', pady=(6, 0))
    
    def _page_watermark(self):
        tk.Label(self.page_container, text="Watermark",
                font=('Segoe UI', 22, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')

        tk.Label(self.page_container,
                text="Optionally overlay text or a logo on the restored video.",
                font=('Segoe UI', 13, 'bold'),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(4, 14))

        self._show_experimental_notice(self.page_container)

        # Defaults (persist across page revisits within the session)
        self.config_data.setdefault('wm_type', 'none')
        self.config_data.setdefault('wm_text', '@VideoCaptureGuide')
        self.config_data.setdefault('wm_position', 'bottomright')
        self.config_data.setdefault('wm_opacity', 0.6)
        self.config_data.setdefault('wm_fontsize', 28)
        self.config_data.setdefault('wm_logo_path', '')
        self.config_data.setdefault('wm_logo_size', 0.10)

        self.wm_type_var = tk.StringVar(value=self.config_data['wm_type'])

        card = tk.Frame(self.page_container, bg=Colors.BG_CARD)
        card.pack(fill='x')
        wm_options = [
            ("No watermark", "none", "Clean output — recommended for archival copies"),
            ("Text watermark", "text", "Overlay a caption such as your channel handle"),
            ("Logo / image watermark", "logo", "Overlay a PNG/image logo (transparency supported)"),
        ]
        for i, (label, value, desc) in enumerate(wm_options):
            ModernRadioButton(card, label, self.wm_type_var, value, desc).pack(fill='x')
            if i < len(wm_options) - 1:
                ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)

        # ── Shared option vars / styled widget helpers ────────────────────────
        positions = [("Bottom-right", 'bottomright'), ("Bottom-left", 'bottomleft'),
                     ("Top-right", 'topright'), ("Top-left", 'topleft'),
                     ("Center", 'center')]
        pos_by_label = dict(positions)
        label_by_pos = {v: k for k, v in positions}

        self._wm_pos_label_var = tk.StringVar(
            value=label_by_pos.get(self.config_data['wm_position'], "Bottom-right"))
        self._wm_pos_label_var.trace_add('write', lambda *_: self.config_data.update(
            {'wm_position': pos_by_label.get(self._wm_pos_label_var.get(), 'bottomright')}))

        # Opacity is shared between text and logo modes (single config key)
        self._wm_opacity_var = tk.IntVar(value=int(round(self.config_data['wm_opacity'] * 100)))
        self._wm_opacity_var.trace_add('write', lambda *_: self.config_data.update(
            {'wm_opacity': self._wm_opacity_var.get() / 100.0}))

        def dark_optionmenu(parent, var, values):
            om = tk.OptionMenu(parent, var, *values)
            om.config(bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                      activebackground=Colors.BG_CARD_HOVER,
                      activeforeground=Colors.TEXT_PRIMARY,
                      highlightthickness=1, highlightbackground=Colors.BORDER,
                      relief='flat', font=('Segoe UI', 10))
            om['menu'].config(bg=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY,
                              activebackground=Colors.ACCENT,
                              activeforeground='white',
                              font=('Segoe UI', 10))
            return om

        def dark_scale(parent, frm, to, var):
            return tk.Scale(parent, from_=frm, to=to, orient='horizontal',
                            variable=var, length=300, showvalue=True,
                            bg=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY,
                            highlightthickness=0, troughcolor=Colors.BG_DARK,
                            activebackground=Colors.ACCENT,
                            font=('Segoe UI', 9))

        def option_row(parent, label_text):
            row = tk.Frame(parent, bg=Colors.BG_CARD)
            row.pack(fill='x', pady=(8, 0))
            tk.Label(row, text=label_text, font=('Segoe UI', 11),
                     fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD,
                     width=14, anchor='w').pack(side='left')
            return row

        # ── Text watermark sub-options (shown when 'text' selected) ──────────
        self._wm_text_frame = tk.Frame(self.page_container, bg=Colors.BG_CARD,
                                       padx=16, pady=12)

        row = option_row(self._wm_text_frame, "Text")
        self._wm_text_var = tk.StringVar(value=self.config_data['wm_text'])
        self._wm_text_var.trace_add('write', lambda *_: self.config_data.update(
            {'wm_text': self._wm_text_var.get()}))
        tk.Entry(row, textvariable=self._wm_text_var,
                 font=('Segoe UI', 11), width=32,
                 bg=Colors.BG_DARK, fg=Colors.TEXT_PRIMARY,
                 insertbackground=Colors.TEXT_PRIMARY,
                 relief='flat', highlightthickness=1,
                 highlightbackground=Colors.BORDER,
                 highlightcolor=Colors.BORDER_FOCUS).pack(side='left', ipady=4)

        row = option_row(self._wm_text_frame, "Position")
        dark_optionmenu(row, self._wm_pos_label_var,
                        [p[0] for p in positions]).pack(side='left')

        row = option_row(self._wm_text_frame, "Opacity")
        dark_scale(row, 20, 100, self._wm_opacity_var).pack(side='left')
        tk.Label(row, text="%", font=('Segoe UI', 10),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD).pack(side='left', padx=(6, 0))

        row = option_row(self._wm_text_frame, "Font size")
        fontsizes = [("Small", 18), ("Medium", 28), ("Large", 42)]
        size_by_label = dict(fontsizes)
        label_by_size = {v: k for k, v in fontsizes}
        self._wm_fontsize_var = tk.StringVar(
            value=label_by_size.get(self.config_data['wm_fontsize'], "Medium"))
        self._wm_fontsize_var.trace_add('write', lambda *_: self.config_data.update(
            {'wm_fontsize': size_by_label.get(self._wm_fontsize_var.get(), 28)}))
        dark_optionmenu(row, self._wm_fontsize_var,
                        [f[0] for f in fontsizes]).pack(side='left')

        # ── Logo watermark sub-options (shown when 'logo' selected) ──────────
        self._wm_logo_frame = tk.Frame(self.page_container, bg=Colors.BG_CARD,
                                       padx=16, pady=12)

        row = option_row(self._wm_logo_frame, "Logo file")
        _logo_name = os.path.basename(self.config_data['wm_logo_path'])
        self._wm_logo_lbl = tk.Label(row, text=_logo_name or "No file selected",
                font=('Segoe UI', 10),
                fg=Colors.TEXT_PRIMARY if _logo_name else Colors.TEXT_SECONDARY,
                bg=Colors.BG_CARD)

        def _pick_logo():
            path = filedialog.askopenfilename(
                title="Choose a logo image",
                filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"),
                           ("All files", "*.*")])
            if path:
                self.config_data['wm_logo_path'] = path
                self._wm_logo_lbl.config(text=os.path.basename(path),
                                         fg=Colors.TEXT_PRIMARY)

        ModernButton(row, "Browse…", command=_pick_logo,
                     width=110, height=30).pack(side='left')
        self._wm_logo_lbl.pack(side='left', padx=(10, 0))

        row = option_row(self._wm_logo_frame, "Position")
        dark_optionmenu(row, self._wm_pos_label_var,
                        [p[0] for p in positions]).pack(side='left')

        row = option_row(self._wm_logo_frame, "Size")
        self._wm_logo_size_var = tk.IntVar(
            value=int(round(self.config_data['wm_logo_size'] * 100)))
        self._wm_logo_size_var.trace_add('write', lambda *_: self.config_data.update(
            {'wm_logo_size': self._wm_logo_size_var.get() / 100.0}))
        dark_scale(row, 5, 30, self._wm_logo_size_var).pack(side='left')
        tk.Label(row, text="% of frame width", font=('Segoe UI', 10),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD).pack(side='left', padx=(6, 0))

        row = option_row(self._wm_logo_frame, "Opacity")
        dark_scale(row, 20, 100, self._wm_opacity_var).pack(side='left')
        tk.Label(row, text="%", font=('Segoe UI', 10),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD).pack(side='left', padx=(6, 0))

        # ── Show/hide sub-option frames based on watermark type ──────────────
        def _update_wm_subframes(*_):
            t = self.wm_type_var.get()
            self.config_data['wm_type'] = t
            self._wm_text_frame.pack_forget()
            self._wm_logo_frame.pack_forget()
            if t == 'text':
                self._wm_text_frame.pack(fill='x', pady=(10, 0))
            elif t == 'logo':
                self._wm_logo_frame.pack(fill='x', pady=(10, 0))

        self.wm_type_var.trace_add('write', _update_wm_subframes)
        _update_wm_subframes()

    def _page_grain(self):
        """Advanced ⑨ — Add Film Grain."""
        tk.Label(self.page_container, text="Add Film Grain",
                 font=('Segoe UI', 22, 'bold'),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')
        tk.Label(self.page_container,
                 text="Optionally overlay a fine layer of synthetic grain on the finished video.",
                 font=('Segoe UI', 13),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(4, 14))

        self.config_data.setdefault('grain_strength', 0.0)

        card = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=16, pady=14)
        card.pack(fill='x')
        tk.Label(card, text="Grain strength",
                 font=('Segoe UI', 12, 'bold'),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD).pack(anchor='w')

        grain_row = tk.Frame(card, bg=Colors.BG_CARD)
        grain_row.pack(fill='x', pady=(6, 0))
        self._grain_var = tk.IntVar(value=int(round(self.config_data['grain_strength'])))
        self._grain_var.trace_add('write', lambda *_: self.config_data.update(
            {'grain_strength': float(self._grain_var.get())}))
        tk.Scale(grain_row, from_=0, to=10, orient='horizontal',
                 variable=self._grain_var, length=300, showvalue=True,
                 bg=Colors.BG_CARD, fg=Colors.TEXT_PRIMARY,
                 highlightthickness=0, troughcolor=Colors.BG_DARK,
                 activebackground=Colors.ACCENT,
                 font=('Segoe UI', 9)).pack(side='left')
        tk.Label(grain_row, text="0 = off (default)", font=('Segoe UI', 10),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD).pack(side='left', padx=(8, 0))
        tk.Label(card,
                 text="2–4 gives a subtle, film-like texture; higher values are a "
                      "deliberate stylistic effect.",
                 font=('Segoe UI', 10), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                 wraplength=560, justify='left').pack(anchor='w', pady=(4, 0))

        info_card = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=16, pady=14)
        info_card.pack(fill='x', pady=(12, 0))
        tk.Label(info_card, text="ℹ  Why add grain?",
                 font=('Segoe UI', 12, 'bold'),
                 fg=Colors.ACCENT, bg=Colors.BG_CARD).pack(anchor='w')
        tk.Label(info_card,
                 text="Grain is generated by the AddGrain filter (VapourSynth's "
                      "grain.Add, a port of the classic AviSynth AddGrainC plugin).\n\n"
                      "Denoising can leave skin and flat surfaces looking smooth and "
                      "plasticky — a light layer of grain restores natural texture. "
                      "It also helps prevent banding when the video is uploaded to "
                      "YouTube: YouTube's heavy re-compression tends to turn smooth "
                      "gradients (skies, fades, shadows) into visible stair-step "
                      "bands, and grain breaks those gradients up so they survive "
                      "the re-encode.",
                 font=('Segoe UI', 10), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                 wraplength=560, justify='left').pack(anchor='w', pady=(5, 0))

    def _page_dither(self):
        """Advanced ⑩ — Output Dithering."""
        tk.Label(self.page_container, text="Output Dithering",
                 font=('Segoe UI', 22, 'bold'),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')
        tk.Label(self.page_container,
                 text="Controls how the 16-bit processing pipeline is reduced to the "
                      "output bit depth. Most users should leave this at the default.",
                 font=('Segoe UI', 13),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
                 wraplength=640, justify='left').pack(anchor='w', pady=(4, 14))

        self.config_data.setdefault('dither_enabled', True)
        self.config_data.setdefault('dither_method', 'error_diffusion')

        dither_card = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=16, pady=14)
        dither_card.pack(fill='x')

        # Enable checkbox
        self._dither_enabled_var = tk.BooleanVar(
            value=self.config_data.get('dither_enabled', True))
        self._dither_enabled_var.trace_add('write', lambda *_: self.config_data.update(
            {'dither_enabled': self._dither_enabled_var.get()}))

        dither_chk = tk.Checkbutton(
            dither_card, text="Output dithering (recommended)",
            variable=self._dither_enabled_var,
            font=('Segoe UI', 11, 'bold'),
            fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD,
            activeforeground=Colors.TEXT_PRIMARY, activebackground=Colors.BG_CARD,
            selectcolor=Colors.BG_DARK, relief='flat', anchor='w')
        dither_chk.pack(anchor='w')
        tk.Label(dither_card,
                 text="Dithering (fmtconv's fmtc.bitdepth) spreads quantisation error "
                      "across pixels when converting the 16-bit internal pipeline to "
                      "the output bit depth — this prevents banding in gradients such "
                      "as skies and fades. Error diffusion is highest quality.",
                 font=('Segoe UI', 10), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                 wraplength=540, justify='left').pack(anchor='w', pady=(2, 8))

        # Method dropdown
        _dither_choices = [
            ("Error diffusion (recommended)", 'error_diffusion'),
            ("Ordered / Bayer", 'ordered'),
        ]
        _dither_labels = [lbl for lbl, _ in _dither_choices]
        _dither_values = {lbl: val for lbl, val in _dither_choices}
        _dither_labels_inv = {val: lbl for lbl, val in _dither_choices}

        _init_dm = self.config_data.get('dither_method', 'error_diffusion')
        _init_dm_label = _dither_labels_inv.get(_init_dm, _dither_labels[0])
        self._dither_method_var = tk.StringVar(value=_init_dm_label)

        method_row = tk.Frame(dither_card, bg=Colors.BG_CARD)
        method_row.pack(fill='x')
        tk.Label(method_row, text="Dither method:", font=('Segoe UI', 11),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD,
                 width=14, anchor='w').pack(side='left')
        dither_dd = ttk.Combobox(method_row, textvariable=self._dither_method_var,
                                  values=_dither_labels, state='readonly', width=34)
        dither_dd.pack(side='left', padx=(8, 0))

        def _on_dither_method(*_):
            chosen = _dither_values.get(self._dither_method_var.get(), 'error_diffusion')
            self.config_data['dither_method'] = chosen

        self._dither_method_var.trace_add('write', _on_dither_method)

    def _page_finalize(self):
        """Step 7 — Finalize (alias for _page_output_and_process)."""
        self._page_output_and_process()

    def _page_output_and_process(self):
        """Output & Process: format selection then in-page processing UI."""
        # ── Page header ────────────────────────────────────────────────────────
        tk.Label(self.page_container, text="Output & Process",
                 font=('Segoe UI', 22, 'bold'),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')
        tk.Label(self.page_container, text="Choose an output format, then start processing.",
                 font=('Segoe UI', 13),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(2, 18))

        # ── Trim summary (from the Trim / Segment Export page) ────────────────
        _trim_plan = self._get_trim_plan()
        if _trim_plan and _trim_plan['ranges']:
            _n = len(_trim_plan['ranges'])
            if _trim_plan['output'] == 'separate' and _n > 1:
                _trim_txt = f"✂  Trim active: {_n} segments will be exported as separate files."
            elif _n > 1:
                _trim_txt = f"✂  Trim active: {_n} segments will be joined into one output file."
            else:
                _trim_txt = "✂  Trim active: only the selected part of the video will be exported."
            tk.Label(self.page_container, text=_trim_txt,
                     font=('Segoe UI', 11, 'bold'),
                     fg=Colors.WARNING, bg=Colors.BG_MAIN).pack(anchor='w', pady=(0, 14))

        # ── Output format selection ────────────────────────────────────────────
        # We'll hide this section when processing starts
        self._output_select_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        self._output_select_frame.pack(fill='x')

        initial_output = self.config_data.get('output_format', 'prores')
        self.config_data['output_format'] = initial_output
        self.output_var = tk.StringVar(value=initial_output)

        fmt_card = tk.Frame(self._output_select_frame, bg=Colors.BG_CARD)
        fmt_card.pack(fill='x')

        options = [
            ("ProRes HQ (.mov)", "prores", "High quality, large files — best for editing"),
            ("H.264 (.mp4)",     "h264",   "Good quality, smaller files — widely compatible"),
            ("FFV1 (.mkv)",      "ffv1",   "Mathematically lossless — archival quality"),
        ]
        for i, (label, value, desc) in enumerate(options):
            ModernRadioButton(fmt_card, label, self.output_var, value, desc).pack(fill='x')
            if i < len(options) - 1:
                ttk.Separator(fmt_card, orient='horizontal').pack(fill='x', padx=12)
        self.output_var.trace_add('write',
            lambda *_: self.config_data.update({'output_format': self.output_var.get()}))

        # ── Diagnostic Log checkbox (Feature 5) ───────────────────────────────
        diag_outer = tk.Frame(self._output_select_frame, bg=Colors.BG_CARD,
                              padx=16, pady=14)
        diag_outer.pack(fill='x', pady=(16, 0))

        diag_top = tk.Frame(diag_outer, bg=Colors.BG_CARD)
        diag_top.pack(fill='x')
        tk.Label(diag_top, text="🔍  Troubleshooting",
                 font=('Segoe UI', 11, 'bold'),
                 fg=Colors.ACCENT, bg=Colors.BG_CARD).pack(side='left')

        self._diag_var = tk.BooleanVar(
            value=self.config_data.get('save_diagnostic_log', False))

        diag_cb = tk.Checkbutton(
            diag_outer,
            text="Save diagnostic log for troubleshooting  (saved alongside the output video)",
            variable=self._diag_var,
            font=('Segoe UI', 11),
            fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD,
            selectcolor=Colors.BG_DARK,
            activebackground=Colors.BG_CARD,
            activeforeground=Colors.TEXT_PRIMARY,
            command=lambda: self.config_data.update(
                {'save_diagnostic_log': self._diag_var.get()}))
        diag_cb.pack(anchor='w', pady=(8, 0))

        tk.Label(diag_outer,
                 text="Logs: VCG version, system info, ffprobe data, detected parameters, "
                      "VapourSynth script, FFmpeg command, full stdout/stderr, exceptions, "
                      "and processing timing.  Written incrementally so crash logs are useful.",
                 font=('Segoe UI', 10), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                 wraplength=580, justify='left').pack(anchor='w', pady=(4, 0))

        # ── Start Processing button ────────────────────────────────────────────
        btn_outer = tk.Frame(self._output_select_frame, bg=Colors.BG_MAIN)
        btn_outer.pack(pady=(24, 8))

        start_canvas = tk.Canvas(btn_outer, width=280, height=64,
                                 bg=Colors.BG_MAIN, highlightthickness=0, cursor='hand2')
        start_canvas.pack()

        def _draw_start(hover=False):
            start_canvas.delete('all')
            col = Colors.ACCENT_HOVER if hover else Colors.ACCENT
            r = 10
            x1, y1, x2, y2 = 0, 0, 280, 64
            # Rounded rect
            start_canvas.create_arc(x1, y1, x1+2*r, y1+2*r, start=90, extent=90, fill=col, outline='')
            start_canvas.create_arc(x2-2*r, y1, x2, y1+2*r, start=0, extent=90, fill=col, outline='')
            start_canvas.create_arc(x1, y2-2*r, x1+2*r, y2, start=180, extent=90, fill=col, outline='')
            start_canvas.create_arc(x2-2*r, y2-2*r, x2, y2, start=270, extent=90, fill=col, outline='')
            start_canvas.create_rectangle(x1+r, y1, x2-r, y2, fill=col, outline='')
            start_canvas.create_rectangle(x1, y1+r, x2, y2-r, fill=col, outline='')
            start_canvas.create_text(140, 32, text="▶  Start Processing",
                                     font=('Segoe UI', 16, 'bold'), fill='black')

        _draw_start()
        start_canvas.bind('<Enter>',    lambda e: _draw_start(True))
        start_canvas.bind('<Leave>',    lambda e: _draw_start(False))
        start_canvas.bind('<Button-1>', lambda e: self._begin_processing())

        # ── Processing UI (hidden until Start is clicked) ──────────────────────
        self._processing_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        # (NOT packed yet — shown by _begin_processing)

        # Pre-build the processing widgets so they're ready
        self._build_processing_ui(self._processing_frame)

        # Hide the nav Next button — Start button is the action on this page
        self.next_btn.pack_forget()

    def _build_processing_ui(self, parent):
        """Create progress/log widgets inside *parent* (used by _page_output_and_process)."""
        self.files_to_process = self.config_data.get('input_files', [])
        if not self.files_to_process and 'input_path' in self.config_data:
            self.files_to_process = [self.config_data['input_path']]
        self.current_file_index = 0
        self.completed_files = []
        self.failed_files    = []

        tk.Label(parent, text="Processing",
                 font=('Segoe UI', 20, 'bold'),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')

        if len(self.files_to_process) > 1:
            self.overall_label = tk.Label(parent,
                    text=f"File 1 of {len(self.files_to_process)}",
                    font=('Segoe UI', 11, 'bold'), fg=Colors.ACCENT, bg=Colors.BG_MAIN)
            self.overall_label.pack(anchor='w', pady=(4, 4))
            self.overall_progress = ProgressBar(parent, width=580)
            self.overall_progress.pack(anchor='w', pady=(0, 12))

        self.proc_status = tk.Label(parent, text="Preparing…",
                                    font=('Segoe UI', 12),
                                    fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN)
        self.proc_status.pack(anchor='w', pady=(4, 4))
        self.current_file_label = tk.Label(parent, text="",
                                            font=('Segoe UI', 12),
                                            fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN)
        self.current_file_label.pack(anchor='w', pady=(0, 8))

        self.progress = ProgressBar(parent, width=580)
        self.progress.pack(anchor='w', pady=(0, 12))

        log_frame = tk.Frame(parent, bg=Colors.BG_CARD)
        log_frame.pack(fill='both', expand=True)
        self.log_text = tk.Text(log_frame, bg=Colors.BG_CARD, fg=Colors.TEXT_SECONDARY,
                                font=('Consolas', 9), height=14, wrap='word',
                                relief='flat', padx=10, pady=10)
        self.log_text.pack(fill='both', expand=True)

        promo_card = tk.Frame(parent, bg=Colors.BG_CARD, padx=16, pady=12)
        promo_card.pack(fill='x', pady=(10, 0))
        vcg_link = tk.Label(promo_card,
                    text="📺  Learn more about video capture at the Video Capture Guide channel.",
                    font=('Segoe UI', 13, 'bold', 'underline'),
                    fg=Colors.ACCENT, bg=Colors.BG_CARD,
                    cursor='hand2', wraplength=680, justify='left')
        vcg_link.pack(anchor='w')
        vcg_link.bind('<Button-1>', lambda e: self._open_website())
        vcg_link.bind('<Enter>', lambda e: vcg_link.config(fg=Colors.TEXT_PRIMARY))
        vcg_link.bind('<Leave>', lambda e: vcg_link.config(fg=Colors.ACCENT))

    def _begin_processing(self):
        """Hide the format selector, show the processing UI, and start the thread."""
        self._output_select_frame.pack_forget()
        self._processing_frame.pack(fill='both', expand=True)
        # Also hide Back button so user can't navigate away mid-process
        self.back_btn.set_disabled(True)
        threading.Thread(target=self._run_batch_processing, daemon=True).start()

    def _page_output(self):
        tk.Label(self.page_container, text="Output Format",
                font=('Segoe UI', 22, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')
        
        tk.Label(self.page_container, text="Choose the output video format",
                font=('Segoe UI', 13, 'bold'),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(4, 20))
        
        # Get initial value and save it immediately
        initial_output = self.config_data.get('output_format', 'prores')
        self.config_data['output_format'] = initial_output
        self.output_var = tk.StringVar(value=initial_output)
        
        card = tk.Frame(self.page_container, bg=Colors.BG_CARD)
        card.pack(fill='x')
        
        options = [
            ("ProRes HQ (.mov)", "prores", "High quality, large files — best for editing"),
            ("H.264 (.mp4)", "h264", "Good quality, smaller files — widely compatible"),
            ("FFV1 (.mkv)", "ffv1", "Mathematically lossless — archival quality"),
        ]
        
        for i, (label, value, desc) in enumerate(options):
            ModernRadioButton(card, label, self.output_var, value, desc).pack(fill='x')
            if i < len(options) - 1:
                ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
        
        self.output_var.trace_add('write', lambda *_: self.config_data.update({'output_format': self.output_var.get()}))
        
        self.next_btn.text = "Process →"
        self.next_btn._draw()
    
    def _show_artifact_example(self, parent, artifact_type, caption):
        """Show a before/after artifact example image in a card."""
        if not HAS_PIL:
            return
        img = _draw_artifact_example(artifact_type)
        if img is None:
            return
        example_frame = tk.Frame(parent, bg=Colors.BG_CARD, padx=12, pady=10)
        example_frame.pack(fill='x', pady=(0, 12))
        tk.Label(example_frame, text=caption,
                 font=('Segoe UI', 10, 'bold'),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD).pack(anchor='w', pady=(0, 6))
        try:
            photo = ImageTk.PhotoImage(img)
            lbl = tk.Label(example_frame, image=photo, bg=Colors.BG_CARD)
            lbl.image = photo
            lbl.pack(anchor='w')
            self.temp_images.append(photo)
        except:
            pass

    def _show_experimental_notice(self, parent):
        """Show an 'experimental' warning card."""
        notice = tk.Frame(parent, bg='#2A2010', padx=14, pady=10)
        notice.pack(fill='x', pady=(0, 12))
        tk.Label(notice,
                 text="⚠  Experimental Feature",
                 font=('Segoe UI', 11, 'bold'),
                 fg=Colors.WARNING, bg='#2A2010').pack(anchor='w')
        tk.Label(notice,
                 text="The analysis and recommendations below are an experimental feature. "
                      "They may not be accurate for all videos. Review suggestions carefully "
                      "before applying them.",
                 font=('Segoe UI', 10),
                 fg='#D0B060', bg='#2A2010',
                 wraplength=560, justify='left').pack(anchor='w', pady=(4, 0))

    def _run_field_order_detection(self):
        """Use FFmpeg idet filter to auto-detect field order."""
        files = self.config_data.get('input_files', [])
        if not files and 'input_path' not in self.config_data:
            messagebox.showwarning("No File", "Please select a video file first (Step 2).")
            return
        filepath = self.config_data.get('input_files', [self.config_data.get('input_path')])[0]
        # Reset badge to "Analyzing..." while detection runs
        if hasattr(self, 'detect_badge_lbl') and self.detect_badge_lbl:
            self.detect_badge_lbl.config(text="   ⏳ Analyzing...", fg=Colors.ACCENT)
        # Clear any previous detail text (only exists on the standalone Field Order page)
        if hasattr(self, 'detect_status_frame') and self.detect_status_frame.winfo_exists():
            for w in self.detect_status_frame.winfo_children():
                w.destroy()
        self.update()
        def detect_worker():
            try:
                import re

                # ── Step 1: Check container-level field_order flag ──────────
                probe_cmd = [
                    FFPROBE_PATH, '-v', 'error',
                    '-select_streams', 'v:0',
                    '-show_entries', 'stream=field_order',
                    '-of', 'csv=p=0',
                    filepath
                ]
                probe_result = run_hidden(probe_cmd, timeout=15)
                container_flag = (probe_result.stdout or '').strip().lower()

                if container_flag == 'progressive':
                    self.after(0, lambda: self._show_detection_result(
                        None, 'Progressive — no deinterlacing needed', Colors.INFO,
                        "This file is flagged as Progressive in its metadata. "
                        "It does not contain interlaced fields and does not need to be deinterlaced. "
                        "You can still continue if you believe the flag is incorrect."
                    ))
                    return

                if container_flag in ('tt', 'tff'):
                    self.after(0, lambda: self._show_detection_result(
                        'tff', 'High confidence (container flag)', Colors.SUCCESS,
                        "File metadata indicates Top Field First (TFF)."
                    ))
                    return

                if container_flag in ('bb', 'bff'):
                    self.after(0, lambda: self._show_detection_result(
                        'bff', 'High confidence (container flag)', Colors.SUCCESS,
                        "File metadata indicates Bottom Field First (BFF)."
                    ))
                    return

                # ── Step 2: No reliable flag — run idet analysis ────────────
                cmd = [FFMPEG_PATH, '-i', filepath, '-vf', 'idet', '-frames:v', '200', '-an', '-f', 'null', '-']
                result = run_hidden(cmd, timeout=60)
                output = result.stderr
                tff_count = bff_count = prog_count = 0
                for line in output.split('\n'):
                    if 'Multi frame detection' in line or 'multi frame detection' in line.lower():
                        m = re.search(r'TFF:\s*(\d+)', line, re.IGNORECASE)
                        if m: tff_count = int(m.group(1))
                        m = re.search(r'BFF:\s*(\d+)', line, re.IGNORECASE)
                        if m: bff_count = int(m.group(1))
                        m = re.search(r'Progressive:\s*(\d+)', line, re.IGNORECASE)
                        if m: prog_count = int(m.group(1))
                if tff_count == 0 and bff_count == 0:
                    for line in output.split('\n'):
                        if 'Single frame detection' in line or 'single frame' in line.lower():
                            m = re.search(r'TFF:\s*(\d+)', line, re.IGNORECASE)
                            if m: tff_count = int(m.group(1))
                            m = re.search(r'BFF:\s*(\d+)', line, re.IGNORECASE)
                            if m: bff_count = int(m.group(1))
                if tff_count > bff_count * 2:
                    verdict, confidence, color, desc = 'tff', 'High confidence', Colors.SUCCESS, f"TFF detected ({tff_count} TFF vs {bff_count} BFF frames)"
                elif bff_count > tff_count * 2:
                    verdict, confidence, color, desc = 'bff', 'High confidence', Colors.SUCCESS, f"BFF detected ({bff_count} BFF vs {tff_count} TFF frames)"
                elif prog_count > (tff_count + bff_count):
                    verdict, confidence, color, desc = None, 'Likely Progressive', Colors.INFO, f"Video content appears to be progressive ({prog_count} progressive frames). Deinterlacing may not be needed."
                elif tff_count > bff_count:
                    verdict, confidence, color, desc = 'tff', 'Low confidence', Colors.WARNING, f"Likely TFF ({tff_count} TFF vs {bff_count} BFF frames) — verify visually"
                elif bff_count > tff_count:
                    verdict, confidence, color, desc = 'bff', 'Low confidence', Colors.WARNING, f"Likely BFF ({bff_count} BFF vs {tff_count} TFF frames) — verify visually"
                else:
                    verdict, confidence, color, desc = None, 'Uncertain', Colors.WARNING, f"Could not determine ({tff_count} TFF, {bff_count} BFF, {prog_count} Progressive)"
                self.after(0, lambda: self._show_detection_result(verdict, confidence, color, desc))
            except Exception as e:
                self.after(0, lambda: self._show_detection_result(None, 'Error', Colors.ERROR, str(e)))
        threading.Thread(target=detect_worker, daemon=True).start()

    def _show_detection_result(self, verdict, confidence, color, desc):
        """Display idet detection result — updates badge at top and detail text below radio buttons."""

        # ── Update the green badge at the top (same style as Format/Capture pages) ──
        if hasattr(self, 'detect_badge_lbl') and self.detect_badge_lbl:
            if verdict:
                badge_text = f"   ✓ {verdict.upper()} detected  ({confidence})"
            elif color == Colors.INFO:
                badge_text = f"   ℹ  {confidence}"
            else:
                icon = '⚠' if color == Colors.WARNING else '✗'
                badge_text = f"   {icon}  {confidence}"
            self.detect_badge_lbl.config(text=badge_text, fg=color)

        # ── Auto-apply the verdict to the radio button (no Apply button needed) ──
        if verdict and hasattr(self, 'field_var'):
            self.field_var.set(verdict)
            self.config_data['field_order'] = verdict

        # ── Show compact detail text below the radio buttons (field order page only) ──
        if hasattr(self, 'detect_status_frame') and self.detect_status_frame.winfo_exists():
            for w in self.detect_status_frame.winfo_children():
                w.destroy()
            tk.Label(self.detect_status_frame, text=desc,
                     font=('Segoe UI', 10), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
                     wraplength=560, justify='left').pack(anchor='w', pady=(4, 0))
        # Also store the detected result for the badge text
        if verdict:
            self.config_data['detected_field_order'] = verdict

    def _run_field_order_visual(self):
        """Show visual TFF vs BFF comparison."""
        files = self.config_data.get('input_files', [])
        if not files and 'input_path' not in self.config_data:
            messagebox.showwarning("No File", "Please select a video file first (Step 2).")
            return
        filepath = self.config_data.get('input_files', [self.config_data.get('input_path')])[0]
        dialog = tk.Toplevel(self)
        dialog.title("Visual Field Order Comparison")
        dialog.configure(bg=Colors.BG_MAIN)
        dialog.resizable(False, False)
        w, h = 760, 580
        dialog.geometry(f"{w}x{h}+{self.winfo_x()+(self.winfo_width()-w)//2}+{self.winfo_y()+(self.winfo_height()-h)//2}")
        dialog.transient(self)
        dialog.grab_set()
        outer = tk.Frame(dialog, bg=Colors.BG_MAIN, padx=20, pady=16)
        outer.pack(fill='both', expand=True)
        tk.Label(outer, text="Visual Field Order Test",
                 font=('Segoe UI', 16, 'bold'), fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')
        tk.Label(outer,
                 text="Extracting frames from your video using TFF and BFF. Look for combing (horizontal lines) on moving objects.",
                 font=('Segoe UI', 10), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
                 wraplength=660).pack(anchor='w', pady=(4, 14))
        status_lbl = tk.Label(outer, text="⏳  Extracting frames...",
                              font=('Segoe UI', 11, 'bold'), fg=Colors.ACCENT, bg=Colors.BG_MAIN)
        status_lbl.pack(anchor='w')
        panels = tk.Frame(outer, bg=Colors.BG_MAIN)
        tff_card = tk.Frame(panels, bg=Colors.BG_CARD, padx=4, pady=4)
        tff_card.pack(side='left', fill='both', expand=True, padx=(0, 8))
        tk.Label(tff_card, text="TFF — Top Field First",
                 font=('Segoe UI', 10, 'bold'), fg=Colors.ACCENT, bg=Colors.BG_CARD).pack(pady=(4, 2))
        tff_canvas = tk.Canvas(tff_card, width=340, height=255, bg=Colors.BG_DARK, highlightthickness=0)
        tff_canvas.pack(padx=4, pady=(0, 4))
        tk.Label(tff_card, text="VHS, Hi8, SD capture cards",
                 font=('Segoe UI', 8), fg=Colors.TEXT_HINT, bg=Colors.BG_CARD).pack(pady=(0, 6))
        bff_card = tk.Frame(panels, bg=Colors.BG_CARD, padx=4, pady=4)
        bff_card.pack(side='left', fill='both', expand=True)
        tk.Label(bff_card, text="BFF — Bottom Field First",
                 font=('Segoe UI', 10, 'bold'), fg=Colors.ACCENT, bg=Colors.BG_CARD).pack(pady=(4, 2))
        bff_canvas = tk.Canvas(bff_card, width=340, height=255, bg=Colors.BG_DARK, highlightthickness=0)
        bff_canvas.pack(padx=4, pady=(0, 4))
        tk.Label(bff_card, text="MiniDV, Digital8, FireWire",
                 font=('Segoe UI', 8), fg=Colors.TEXT_HINT, bg=Colors.BG_CARD).pack(pady=(0, 6))
        hint = tk.Frame(outer, bg=Colors.BG_CARD, padx=12, pady=10)
        btn_row = tk.Frame(outer, bg=Colors.BG_MAIN)
        _photos = []
        def load_images(tff_path, bff_path):
            nonlocal _photos
            try:
                status_lbl.config(text="✓  Frames extracted — choose the cleaner image")
                panels.pack(fill='x', pady=(10, 0))
                hint.pack(fill='x', pady=(8, 8))
                tk.Label(hint,
                         text="🔍  Showing 500% zoom of center region.  "
                              "Look for horizontal \"combing\" lines (zigzag edges) on moving objects. "
                              "The image with smooth, clean edges is the correct field order.",
                         font=('Segoe UI', 9), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                         wraplength=640, justify='left').pack(anchor='w')
                btn_row.pack(fill='x')
                if HAS_PIL:
                    from PIL import Image, ImageTk
                    for path, canvas in [(tff_path, tff_canvas), (bff_path, bff_canvas)]:
                        try:
                            if os.path.exists(path) and os.path.getsize(path) > 100:
                                img = Image.open(path).convert('RGB')
                                w_full, h_full = img.size
                                # 500% zoom: crop a small center region and scale it up
                                # Canvas is 340×255; at 5x zoom we show a 68×51 px source patch
                                crop_w = max(68, w_full // 5)
                                crop_h = max(51, h_full // 5)
                                cx, cy = w_full // 2, h_full // 2
                                box = (cx - crop_w // 2, cy - crop_h // 2,
                                       cx + crop_w // 2, cy + crop_h // 2)
                                zoomed = img.crop(box).resize((340, 255), Image.NEAREST)
                                photo = ImageTk.PhotoImage(zoomed)
                                # Store on the canvas widget itself to prevent GC
                                canvas._vcg_photo = photo
                                _photos.append(photo)
                                canvas.create_image(170, 127, image=photo)
                        except Exception as img_err:
                            canvas.create_text(150, 112, text=f"Preview error:\n{img_err}",
                                               fill='white', font=('Segoe UI', 9), justify='center')
            except:
                pass
        def cleanup_and_close(verdict=None):
            if verdict:
                self.field_var.set(verdict)
                self.config_data['field_order'] = verdict
                name = 'TFF (Top Field First)' if verdict == 'tff' else 'BFF (Bottom Field First)'
                messagebox.showinfo("Field Order Set", f"Field order set to {name}.")
            for p in [tff_temp, bff_temp]:
                try:
                    if os.path.exists(p): os.remove(p)
                except: pass
            dialog.destroy()
        import tempfile
        tmp_dir = tempfile.gettempdir()
        tff_temp = os.path.join(tmp_dir, f'vcg_tff_{os.getpid()}.png')
        bff_temp = os.path.join(tmp_dir, f'vcg_bff_{os.getpid()}.png')
        def worker():
            try:
                cmd = [FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', filepath]
                result = run_hidden(cmd, timeout=30)
                duration = 60.0
                try: duration = float(result.stdout.strip())
                except: pass
                for pct in [0.35, 0.20, 0.50]:
                    seek = duration * pct
                    # deint=1 forces deinterlacing on ALL frames regardless of interlace flag
                    # pix_fmt rgb24 ensures PIL can always open the output PNG
                    t_cmd = [FFMPEG_PATH, '-y', '-ss', str(seek), '-i', filepath,
                             '-vf', 'yadif=mode=0:parity=0:deint=1',
                             '-vframes', '1', '-pix_fmt', 'rgb24', tff_temp]
                    b_cmd = [FFMPEG_PATH, '-y', '-ss', str(seek), '-i', filepath,
                             '-vf', 'yadif=mode=0:parity=1:deint=1',
                             '-vframes', '1', '-pix_fmt', 'rgb24', bff_temp]
                    run_hidden(t_cmd, timeout=30)
                    run_hidden(b_cmd, timeout=30)
                    if (os.path.exists(tff_temp) and os.path.getsize(tff_temp) > 500
                            and os.path.exists(bff_temp) and os.path.getsize(bff_temp) > 500):
                        break
                dialog.after(0, lambda: load_images(tff_temp, bff_temp))
            except:
                pass
        ModernButton(btn_row, "✓  Use TFF", lambda: cleanup_and_close('tff'), primary=True, width=150).pack(side='left', padx=(0, 10))
        ModernButton(btn_row, "✓  Use BFF", lambda: cleanup_and_close('bff'), primary=True, width=150).pack(side='left', padx=(0, 10))
        ModernButton(btn_row, "Cancel", lambda: cleanup_and_close(None), width=90).pack(side='right')
        threading.Thread(target=worker, daemon=True).start()

    def _page_processing(self):
        self.back_btn.set_disabled(True)
        self.next_btn.set_disabled(True)
        
        # Get file list
        self.files_to_process = self.config_data.get('input_files', [])
        if not self.files_to_process and 'input_path' in self.config_data:
            self.files_to_process = [self.config_data['input_path']]
        
        self.current_file_index = 0
        self.completed_files = []
        self.failed_files = []
        
        tk.Label(self.page_container, text="Processing",
                font=('Segoe UI', 22, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')
        
        # Overall progress (for multiple files)
        if len(self.files_to_process) > 1:
            self.overall_label = tk.Label(self.page_container, 
                text=f"File 1 of {len(self.files_to_process)}",
                font=('Segoe UI', 11, 'bold'),
                fg=Colors.ACCENT, bg=Colors.BG_MAIN)
            self.overall_label.pack(anchor='w', pady=(4, 5))
            
            self.overall_progress = ProgressBar(self.page_container, width=580)
            self.overall_progress.pack(anchor='w', pady=(0, 15))
        
        # Current file status
        self.proc_status = tk.Label(self.page_container, text="Preparing...",
                                    font=('Segoe UI', 12),
                                    fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN)
        self.proc_status.pack(anchor='w', pady=(4, 5))
        
        # Current file name
        self.current_file_label = tk.Label(self.page_container, text="",
                                           font=('Segoe UI', 12),
                                           fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN)
        self.current_file_label.pack(anchor='w', pady=(0, 10))
        
        # Progress bar for current file
        self.progress = ProgressBar(self.page_container, width=580)
        self.progress.pack(anchor='w', pady=(0, 15))
        
        # Log output
        log_frame = tk.Frame(self.page_container, bg=Colors.BG_CARD)
        log_frame.pack(fill='both', expand=True)
        
        self.log_text = tk.Text(log_frame, bg=Colors.BG_CARD, fg=Colors.TEXT_SECONDARY,
                               font=('Consolas', 9), height=14, wrap='word',
                               relief='flat', padx=10, pady=10)
        self.log_text.pack(fill='both', expand=True)

        # Promo box below log — boxed card, two lines, stands out
        promo_card = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=16, pady=12)
        promo_card.pack(fill='x', pady=(10, 0))

        vcg_link = tk.Label(promo_card,
                            text="📺  Learn more about video capture at the Video Capture Guide channel.",
                            font=('Segoe UI', 13, 'bold', 'underline'),
                            fg=Colors.ACCENT, bg=Colors.BG_CARD,
                            cursor='hand2', wraplength=680, justify='left')
        vcg_link.pack(anchor='w')
        vcg_link.bind('<Button-1>', lambda e: self._open_website())
        vcg_link.bind('<Enter>', lambda e: vcg_link.config(fg=Colors.TEXT_PRIMARY))
        vcg_link.bind('<Leave>', lambda e: vcg_link.config(fg=Colors.ACCENT))

        # Start processing
        threading.Thread(target=self._run_batch_processing, daemon=True).start()
    
    def _log(self, text):
        self.after(0, lambda: self._append_log(text))
    
    def _append_log(self, text):
        self.log_text.insert('end', text + '\n')
        self.log_text.see('end')
    
    def _update_status(self, text):
        self.after(0, lambda: self.proc_status.config(text=text))
    
    def _update_progress(self, value):
        self.after(0, lambda: self.progress.set_progress(value))
    
    def _update_overall_progress(self):
        if len(self.files_to_process) > 1:
            progress = self.current_file_index / len(self.files_to_process)
            self.after(0, lambda: self.overall_progress.set_progress(progress))
            self.after(0, lambda: self.overall_label.config(
                text=f"File {self.current_file_index + 1} of {len(self.files_to_process)}"))
    
    def _update_current_file(self, filepath):
        filename = os.path.basename(filepath)
        self.after(0, lambda: self.current_file_label.config(text=f"📁 {filename}"))
    
    def _run_batch_processing(self):
        """Process all files in the queue."""
        total_files = len(self.files_to_process)
        self.completed_log_paths = []

        # Trim / Segment Export plan (single-file feature; None for batches)
        trim_plan = self._get_trim_plan() if total_files == 1 else None
        if trim_plan and not trim_plan['ranges']:
            trim_plan = None  # cut selection removed everything — export full file

        for i, filepath in enumerate(self.files_to_process):
            self.current_file_index = i
            self._update_overall_progress()
            self._update_current_file(filepath)
            self._update_progress(0)

            self._log(f"\n{'='*50}")
            self._log(f"Processing file {i+1} of {total_files}: {os.path.basename(filepath)}")
            self._log(f"{'='*50}")

            try:
                if trim_plan and trim_plan['output'] == 'separate' and len(trim_plan['ranges']) > 1:
                    # One output file per kept segment
                    n_segs = len(trim_plan['ranges'])
                    self._log(f"Trim: exporting {n_segs} segments as separate files")
                    for k, rng in enumerate(trim_plan['ranges'], start=1):
                        self._log(f"\n--- Segment {k} of {n_segs}: "
                                  f"frames {rng[0]}–{rng[1]} ---")
                        output_path, log_path = self._process_single_file(
                            filepath, trim_ranges=[rng],
                            part_suffix=f"_part{k:02d}")
                        self.completed_files.append((filepath, output_path))
                        if log_path:
                            self.completed_log_paths.append(log_path)
                            self._log(f"✓ Complete: {output_path}")
                            self._log(f"  Log: {log_path}")
                        else:
                            self._log(f"✓ Complete: {output_path}")
                else:
                    trim_ranges = trim_plan['ranges'] if trim_plan else None
                    if trim_ranges:
                        self._log(f"Trim: exporting {len(trim_ranges)} segment(s), joined")
                    output_path, log_path = self._process_single_file(
                        filepath, trim_ranges=trim_ranges)
                    self.completed_files.append((filepath, output_path))
                    if log_path:
                        self.completed_log_paths.append(log_path)
                        self._log(f"✓ Complete: {output_path}")
                        self._log(f"  Log: {log_path}")
                    else:
                        self._log(f"✓ Complete: {output_path}")
            except Exception as e:
                self.failed_files.append((filepath, str(e)))
                self._log(f"❌ Failed: {str(e)}")
        
        # Final summary
        self._log(f"\n{'='*50}")
        self._log(f"BATCH COMPLETE")
        self._log(f"{'='*50}")
        self._log(f"✓ Successful: {len(self.completed_files)}")
        if self.failed_files:
            self._log(f"❌ Failed: {len(self.failed_files)}")
        
        if len(self.files_to_process) > 1:
            self.after(0, lambda: self.overall_progress.set_progress(1.0))
        
        self._update_progress(1.0)
        self._update_status(f"Complete! {len(self.completed_files)} of {total_files} files processed")
        
        # Show completion UI
        self.after(0, self._show_batch_complete)
    
    def _process_single_file(self, filepath, trim_ranges=None, part_suffix=''):
        """Process a single file and return (output_path_str, log_path_or_None).

        *trim_ranges* — optional list of (first, last) inclusive SOURCE frame
        ranges to keep (from the Trim / Segment Export page).  Applied to the
        video in the VapourSynth script and to the audio extraction with
        matching timestamps.  *part_suffix* is appended to the output name
        when exporting segments as separate files (e.g. "_part01").
        """
        import traceback as _traceback

        self._log("Generating VapourSynth script...")
        self._update_status("Generating script...")
        self._update_progress(0.1)

        # ── Build per-file config ──────────────────────────────────────────
        # Start from global config, then apply any per-file overrides.
        file_config = self.config_data.copy()
        file_config['input_path'] = filepath
        file_config['trim_ranges'] = trim_ranges
        per_file_overrides = self.config_data.get('per_file_settings', {}).get(filepath, {})
        file_config.update(per_file_overrides)

        if trim_ranges:
            self._log(f"  Trim: keeping {len(trim_ranges)} frame range(s): " +
                      ", ".join(f"{s}-{e}" for s, e in trim_ranges))

        # Generate script
        script = generate_vpy_script(file_config)

        # Save script with auto-numbering
        input_path = Path(filepath)
        output_args, output_ext = get_ffmpeg_output_args(file_config)

        # Find next available number
        counter = 1
        while True:
            suffix = f"_VCGD_{counter:02d}{part_suffix}"
            output_path = input_path.parent / (input_path.stem + suffix + output_ext)
            script_path = input_path.parent / (input_path.stem + suffix + '.vpy')
            if not output_path.exists() and not script_path.exists():
                break
            counter += 1

        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script)

        self._log(f"Script saved: {script_path}")

        # ── Diagnostic logger ──────────────────────────────────────────────
        diag = None
        diag_log_path = None
        if file_config.get('save_diagnostic_log'):
            diag_log_path = str(output_path.parent / (output_path.stem + '_vcg_log.txt'))
            try:
                diag = DiagnosticLogger(diag_log_path)

                diag.section(f"VCG Deinterlacer {VERSION_STRING} — Diagnostic Log")
                diag.kv("Build date", BUILD_DATE)
                diag.kv("Log start", time.strftime('%Y-%m-%d %H:%M:%S'))
                diag.kv("Input file", filepath)
                diag.kv("Output file", str(output_path))
                diag.kv("Script file", str(script_path))

                diag.section("System Information")
                sys_info = _diag_collect_system_info()
                for _k, _v in sys_info.items():
                    diag.kv(_k, _v)

                diag.section("FFprobe Analysis (JSON)")
                try:
                    _probe_cmd = [
                        FFPROBE_PATH, '-v', 'quiet',
                        '-print_format', 'json',
                        '-show_format', '-show_streams',
                        filepath
                    ]
                    _probe_res = run_hidden(_probe_cmd, timeout=30)
                    diag.raw(_probe_res.stdout or '(no output)')
                except Exception as _pe:
                    diag.exception(_pe)

                diag.section("Detected Parameters / Settings")
                _diag_keys = [
                    'video_format', 'field_order', 'capture_method', 'crop_preset',
                    'yc_delay', 'ivtc_mode', 'noise_level', 'dehalo_mode',
                    'color_cast_correction', 'levels_correction', 'audio_mode',
                    'output_format', 'par_correction', 'mix_audio', 'save_diagnostic_log',
                    'wm_type', 'wm_text', 'wm_position', 'wm_opacity', 'wm_fontsize',
                    'wm_logo_path', 'wm_logo_size', 'grain_strength',
                    'trim_mode', 'trim_output', 'trim_ranges',
                ]
                for _k in _diag_keys:
                    if _k in file_config:
                        diag.kv(_k, str(file_config[_k]))
                # Per-file overrides (if any)
                if per_file_overrides:
                    diag.kv("per_file_overrides", str(per_file_overrides))

                diag.section("VapourSynth Script")
                diag.raw(script)

            except Exception as _de:
                self._log(f"  Warning: could not start diagnostic logger: {_de}")
                diag = None
                diag_log_path = None

        # Step 1: Extract audio to clean WAV first (like Hybrid does)
        # This strips container metadata that can cause sync issues
        self._update_status("Extracting audio...")
        self._update_progress(0.1)

        # First, detect audio properties
        audio_channels = 0
        audio_sample_rate = 48000
        try:
            probe_cmd = [
                FFPROBE_PATH, '-v', 'error',
                '-select_streams', 'a:0',
                '-show_entries', 'stream=channels,sample_rate',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                filepath
            ]
            probe_result = run_hidden(probe_cmd, timeout=30)
            if probe_result.returncode == 0 and probe_result.stdout.strip():
                lines = probe_result.stdout.strip().split('\n')
                # FFprobe returns in alphabetical order: channels, sample_rate
                # But let's be smart - sample_rate is usually > 8000, channels is usually 1-8
                for line in lines:
                    val = line.strip()
                    if val.isdigit():
                        num = int(val)
                        if num > 8000:  # This is sample rate
                            audio_sample_rate = num
                        elif num <= 8:  # This is channels
                            audio_channels = num
        except:
            pass

        temp_audio = tempfile.mktemp(suffix='.wav', prefix='vcg_audio_')

        self._log("Extracting audio to WAV...")
        self._log(f"  Detected: {audio_channels} channels @ {audio_sample_rate}Hz")

        # Check if user wants to mix audio channels
        mix_audio = self.config_data.get('mix_audio', False)

        # Audio cut times must match the video Trim ranges exactly, using the
        # same frame rate that generate_vpy_script forces at the decoder.
        _fps_num, _fps_den = (25, 1) if file_config.get('format') == 'pal' else (30000, 1001)

        def _build_audio_cmd(mix):
            """Audio extraction command; *mix* folds both channels into L+R.

            When trim_ranges is set, the same segments kept in the video are
            cut from the audio with atrim + concat (sample-accurate).
            """
            cmd = [FFMPEG_PATH, '-y', '-i', filepath, '-vn', '-sn']
            pan = 'pan=stereo|c0=c0+c1|c1=c0+c1'  # mix L+R into both channels
            if trim_ranges:
                chains, labels = [], []
                for _i, (_s, _e) in enumerate(trim_ranges):
                    _st = _s * _fps_den / _fps_num
                    _en = (_e + 1) * _fps_den / _fps_num
                    chains.append(f'[0:a]atrim=start={_st:.6f}:end={_en:.6f},'
                                  f'asetpts=PTS-STARTPTS[a{_i}]')
                    labels.append(f'[a{_i}]')
                fc = ';'.join(chains)
                fc += f';{"".join(labels)}concat=n={len(trim_ranges)}:v=0:a=1'
                if mix:
                    fc += f'[acat];[acat]{pan}[aout]'
                else:
                    fc += '[aout]'
                cmd.extend(['-filter_complex', fc, '-map', '[aout]'])
            elif mix:
                cmd.extend(['-af', pan])
            if not mix:
                cmd.extend(['-ac', '2'])   # Stereo output
            cmd.extend(['-ar', '48000',    # 48kHz sample rate
                        '-acodec', 'pcm_s16le',  # PCM 16-bit
                        '-f', 'wav', temp_audio])
            return cmd

        audio_extract_cmd = _build_audio_cmd(mix_audio)
        if trim_ranges:
            self._log(f"  Trimming audio to match {len(trim_ranges)} video segment(s)")
        if mix_audio:
            self._log("  Mixing channels to ensure audio in both L+R")
        else:
            self._log("  Preserving original audio channels")

        if diag:
            diag.section("Step 1: Audio Extraction")
            diag.cmd(audio_extract_cmd)

        result = run_hidden(audio_extract_cmd, timeout=None)

        # If pan filter failed, retry without mixing (trim cuts are kept)
        if result.returncode != 0:
            self._log("  Retrying audio extraction with simple stereo conversion...")
            audio_extract_cmd = _build_audio_cmd(False)
            if diag:
                diag.kv("audio-extract-retry", "first attempt failed, retrying without pan")
                diag.cmd(audio_extract_cmd)
            result = run_hidden(audio_extract_cmd, timeout=None)

        has_audio = result.returncode == 0 and os.path.exists(temp_audio) and os.path.getsize(temp_audio) > 1000
        if not has_audio:
            self._log("  No audio stream found or extraction failed, continuing without audio")
            if diag:
                diag.captured("audio-extract", result.stdout, result.stderr)
                diag.kv("audio-extract", "FAILED or no audio stream — continuing without audio")
            try:
                os.remove(temp_audio)
            except:
                pass
        else:
            self._log("  Audio extracted successfully")
            if diag:
                diag.captured("audio-extract", result.stdout, result.stderr)
                diag.kv("audio-extract", "SUCCESS")

        self._update_status("Processing (VapourSynth → FFmpeg)...")
        self._update_progress(0.2)

        # Step 2: Run vspipe piped directly into FFmpeg.
        # vspipe writes y4m to stdout ('-'); FFmpeg reads from pipe:0.
        # This eliminates the intermediate temp y4m file that can be hundreds
        # of GB for long HQ captures, causing "No space left on device" errors.
        # Watermark overlay (if any) is applied here, after all VS processing.
        wm_inputs, wm_filter_args = build_watermark_args(file_config)
        if wm_filter_args:
            self._log(f"  Applying {file_config.get('wm_type')} watermark")
        # Stamp frame-level color props (setparams) so primaries/transfer
        # survive the y4m pipe — encoder-option tags alone are ignored by
        # FFmpeg 8 when frames carry 'unknown'.
        _enc_cs = _resolve_cs_tag(file_config.get('color_matrix', 'bt601'),
                                  file_config.get('format', 'ntsc'))
        _filter_args = _merge_video_filter(wm_filter_args, _enc_cs)
        _ffmpeg_encode_cmd = [FFMPEG_PATH, '-i', 'pipe:0']
        _ffmpeg_encode_cmd.extend(wm_inputs)
        _ffmpeg_encode_cmd.extend(_filter_args)
        _ffmpeg_encode_cmd.extend(output_args)
        _ffmpeg_encode_cmd.extend(['-y', str(output_path)])

        self._log("Running vspipe | ffmpeg (piped)...")
        vspipe_cmd = [VSPIPE_PATH, '-c', 'y4m', str(script_path), '-']
        # Pass portable Python/plugin environment when using bundled deps
        _vs_env = get_vspipe_env()
        # cwd=VS_DEPS_DIR ensures Windows DLL search starts from the VS folder,
        # which is especially important for side-by-side DLL loading on Win10+.
        _vs_cwd = VS_DEPS_DIR if (os.path.isdir(VS_DEPS_DIR) and _vs_env) else None

        if diag:
            diag.section("Step 2: VapourSynth + FFmpeg (piped)")
            diag.kv("VSPIPE_PATH", VSPIPE_PATH)
            diag.kv("vspipe exists", str(os.path.exists(VSPIPE_PATH)))
            diag.kv("vspipe cwd", str(_vs_cwd))
            _deps_info = _collect_vs_deps_diagnostic()
            diag.raw(_deps_info)
            diag.cmd(vspipe_cmd)
            diag.cmd(_ffmpeg_encode_cmd)
            diag.timing("pipe start")

        result = _run_piped(vspipe_cmd, _ffmpeg_encode_cmd,
                            prod_env=_vs_env if _vs_env else None,
                            prod_cwd=_vs_cwd)

        # ── Retry chain for "Failed to initialize VSScript" ─────────────────
        # Root cause: the bundled VapourSynth R73 vsscript.dll only knows how
        # to find Python 3.8–3.12. With Python 3.14 it never finds a DLL.
        #
        # Retry 1: same vspipe, system PATH (no custom env).
        # Retry 2: pip-installed vspipe.exe if available (R74+, Python 3.14 native).
        # Retry 3: run the .vpy script directly via Python + pip vapoursynth,
        #          bypassing vspipe.exe and vsscript.dll entirely.
        _init_failed = ('Failed to initialize VSScript' in (result.stderr or ''))

        if result.returncode != 0 and _vs_env and _init_failed:
            self._log("  Portable env init failed — retrying with system environment...")
            if diag:
                diag.captured("vspipe-attempt-1", result.stdout, result.stderr)
                diag.kv("vspipe-retry-1", "init failed with portable env, retrying system env")
                diag.cmd(vspipe_cmd)
            result = _run_piped(vspipe_cmd, _ffmpeg_encode_cmd,
                                prod_cwd=_vs_cwd)

        # Retry 2: pip-installed vspipe.exe (VapourSynth R74+, Python 3.14 native).
        _init_failed2 = ('Failed to initialize VSScript' in (result.stderr or ''))
        if result.returncode != 0 and _init_failed2 and _PIP_VSPIPE and _PIP_VSPIPE != VSPIPE_PATH:
            self._log(f"  Trying pip-installed vspipe: {_PIP_VSPIPE}")
            pip_cmd = [_PIP_VSPIPE, '-c', 'y4m', str(script_path), '-']
            if diag:
                diag.captured("vspipe-attempt-2", result.stdout, result.stderr)
                diag.kv("vspipe-retry-2", f"trying pip vspipe at {_PIP_VSPIPE}")
                diag.cmd(pip_cmd)
            result = _run_piped(pip_cmd, _ffmpeg_encode_cmd)

        # Retry 3A & 3B: Python-direct — bypass vspipe/vsscript entirely.
        # Root cause: vsscript.dll (R73 bundled) cannot find Python 3.13+.
        # 3A: use bundled vapoursynth.pyd from _deps/vs/site-packages/ —
        #     the bundle ships a .pyd compiled for the same Python it bundles,
        #     so no pip install is needed at all.
        # 3B: pip-install fallback for environments where 3A is unavailable.
        _init_failed3 = ('Failed to initialize VSScript' in (result.stderr or ''))
        if result.returncode != 0 and _init_failed3:
            # ── Discover Python interpreter for retry 3A ─────────────────
            # Priority order:
            #   1. Bundled python.exe inside _deps/vs/ — self-contained,
            #      no system Python required (deps v9+).
            #   2. System Python via shutil.which with PATH filtering —
            #      fallback for older deps bundles that lack python.exe.
            import shutil as _sh
            _sys_py = None

            def _long_path(p):
                try:
                    import ctypes
                    _buf = ctypes.create_unicode_buffer(32768)
                    if ctypes.windll.kernel32.GetLongPathNameW(p, _buf, 32768) > 0:
                        return _buf.value
                except Exception:
                    pass
                return p

            # ── Build Nuitka extraction-dir filter (used by all priorities) ──
            # Nuitka adds {LOCALAPPDATA}\VCG_Deinterlacer\{VERSION}\ to PATH
            # (sometimes as 8.3 short VCG_DE~1\). Build the prefix once so
            # every subprocess we spawn gets a clean PATH.
            _la_root = os.path.normcase(os.path.normpath(
                os.environ.get('LOCALAPPDATA', '')))
            _vcg_prefix = (_la_root + os.sep + 'vcg_') if _la_root else ''

            def _filtered_path_for(base_path, prepend=()):
                _entries = base_path.split(os.pathsep)
                _clean = [e for e in _entries
                          if not (e and _vcg_prefix and
                                  os.path.normcase(os.path.normpath(e)).startswith(_vcg_prefix))]
                return os.pathsep.join(list(prepend) + _clean)

            # ── Priority 1: bundled python.exe with CLEAN PATH ────────────
            # deps v10+ includes python.exe from the Windows embeddable package
            # (python3XX.dll, stdlib zip, libffi-8.dll, all *.dll).
            # Pass a clean PATH (Nuitka extraction dir stripped, VS_DEPS_DIR
            # prepended) so DLL resolution uses only our known-good deps folder.
            _bundled_py = os.path.join(VS_DEPS_DIR, 'python.exe')
            _bundled_env = None
            if os.path.isfile(_bundled_py):
                _bundled_env = dict(os.environ)
                _bundled_env['PATH'] = _filtered_path_for(
                    os.environ.get('PATH', ''), prepend=(VS_DEPS_DIR,))
                try:
                    _ct_test = run_hidden([_bundled_py, '-c', 'import ctypes; print("ok")'],
                                          timeout=10, env=_bundled_env)
                    if _ct_test.returncode == 0 and 'ok' in (_ct_test.stdout or ''):
                        _sys_py = _bundled_py
                    else:
                        self._log("  Bundled python.exe smoke test failed — trying system Python.")
                        diag.kv("bundled-python-ctypes-fail",
                                (_ct_test.stderr or _ct_test.stdout or '').strip()[:200])
                except Exception as _ct_exc:
                    self._log(f"  Bundled python.exe smoke test error: {_ct_exc}")

            if _sys_py is None:
                # ── Priority 2: system Python with filtered PATH ──────────────
                _filtered_path = _filtered_path_for(os.environ.get('PATH', ''))
                _exe_dir = os.path.normcase(os.path.dirname(_long_path(sys.executable)))
                for _cand in ['py', 'python', 'python3']:
                    _p = _sh.which(_cand, path=_filtered_path)
                    if not _p:
                        continue
                    _p_long = _long_path(_p)
                    _p_norm = os.path.normcase(_p_long)
                    if _p_norm == os.path.normcase(_long_path(sys.executable)):
                        continue
                    if os.path.normcase(os.path.dirname(_p_norm)) == _exe_dir:
                        continue
                    if _vcg_prefix and _p_norm.startswith(_vcg_prefix):
                        continue
                    try:
                        _ver_r = run_hidden([_p, '--version'], timeout=10)
                        _ver_out = (_ver_r.stdout or '') + (_ver_r.stderr or '')
                        if _ver_r.returncode == 0 and 'Python' in _ver_out:
                            _sys_py = _p
                            break
                    except Exception:
                        pass

            if _sys_py is None:
                # ── Priority 3: bundled python as last resort ─────────────────
                # Prefer the bundled python over sys.executable (which is the
                # Nuitka EXE / extraction-dir proxy, not a real python.exe).
                if _bundled_py and os.path.isfile(_bundled_py):
                    _sys_py = _bundled_py
                    diag.kv("bundled-python-last-resort",
                            "no system Python found; retrying bundled python anyway")
                else:
                    _sys_py = sys.executable  # running from source

            _site_pkg  = os.path.join(VS_DEPS_DIR, 'site-packages')
            _plugins64 = os.path.join(VS_DEPS_DIR, 'plugins64')
            if not os.path.isdir(_plugins64):
                _plugins64 = os.path.join(VS_DEPS_DIR, 'plugins')

            # ── Retry 3A: bundled vapoursynth.pyd ────────────────────────
            # sys.path.insert(0, ...) loads the bundled .pyd before any
            # system-installed vapoursynth — no pip install needed.
            _bundled_pyd = os.path.join(_site_pkg, 'vapoursynth.pyd')
            _3a_tried = False
            if os.path.isfile(_bundled_pyd):
                _3a_tried = True
                self._log("  Trying Python-direct with bundled vapoursynth.pyd (retry 3A)...")
                _wrapper_3a = '\n'.join([
                    'import sys, os',
                    f'for _dll_dir in [{repr(VS_DEPS_DIR)}, {repr(_plugins64)}]:',
                    '    if os.path.isdir(_dll_dir) and hasattr(os, "add_dll_directory"):',
                    '        os.add_dll_directory(_dll_dir)',
                    f'sys.path.insert(0, {repr(_site_pkg)})',
                    'import vapoursynth as vs',
                    f'with open({repr(str(script_path))}, "r", encoding="utf-8") as _f:',
                    '    _code = _f.read()',
                    f'exec(compile(_code, {repr(str(script_path))}, "exec"))',
                    '_result = vs.get_output(0)',
                    '_node = _result.clip if hasattr(_result, "clip") else _result',
                    '_node.output(sys.stdout.buffer, y4m=True)',
                ])
                _py_env_3a = (_bundled_env.copy()
                              if _bundled_env and _sys_py == _bundled_py
                              else os.environ.copy())
                _py_env_3a['PATH'] = (VS_DEPS_DIR + os.pathsep
                                      + _plugins64 + os.pathsep
                                      + _filtered_path_for(_py_env_3a.get('PATH', '')))
                if diag:
                    diag.captured("vspipe-attempt-3a", result.stdout, result.stderr)
                    diag.kv("vspipe-retry-3a", f"Python-direct bundled pyd: {_sys_py}")
                    diag.raw(f"wrapper-3a:\n{_wrapper_3a}")
                result = _run_piped([_sys_py, '-c', _wrapper_3a], _ffmpeg_encode_cmd,
                                    prod_env=_py_env_3a)
                if diag:
                    diag.captured("python-direct-3a-result", result.stdout, result.stderr)
                    diag.kv("python-direct-3a-returncode", str(result.returncode))

            # ── Retry 3B: pip-installed vapoursynth (fallback) ───────────
            if not _3a_tried or result.returncode != 0:
                _has_pip_vs = False
                _pip_pkg_dir = ''
                try:
                    import importlib.util as _ilu
                    _spec = _ilu.find_spec('vapoursynth')
                    if _spec and _spec.origin:
                        _has_pip_vs = True
                        _pip_pkg_dir = os.path.dirname(_spec.origin)
                except Exception:
                    pass

                if not _has_pip_vs:
                    self._log("  Bundled pyd unavailable — attempting pip install vapoursynth...")
                    try:
                        _pip_r = run_hidden(
                            [_sys_py, '-m', 'pip', 'install', 'vapoursynth',
                             '--quiet', '--disable-pip-version-check'],
                            timeout=180
                        )
                        if _pip_r.returncode == 0:
                            _loc_r = run_hidden(
                                [_sys_py, '-c',
                                 'import vapoursynth, os; '
                                 'print(os.path.dirname(vapoursynth.__file__))'],
                                timeout=15
                            )
                            if _loc_r.returncode == 0 and _loc_r.stdout.strip():
                                _has_pip_vs = True
                                _pip_pkg_dir = _loc_r.stdout.strip()
                                self._log(
                                    f"  pip install vapoursynth succeeded ({_pip_pkg_dir}).")
                        else:
                            self._log("  pip install vapoursynth failed.")
                    except Exception as _pip_ex:
                        self._log(f"  pip install vapoursynth error: {_pip_ex}")

                if _has_pip_vs:
                    self._log("  Trying Python-direct with pip vapoursynth (retry 3B)...")
                    # sys.path.append (not insert) — pip .pyd is in standard
                    # site-packages; append _site_pkg so havsfunc.py is importable.
                    _wrapper_3b = '\n'.join([
                        'import sys, os',
                        f'for _dll_dir in [{repr(VS_DEPS_DIR)}, {repr(_plugins64)}, {repr(_pip_pkg_dir)}]:',
                        '    if os.path.isdir(_dll_dir) and hasattr(os, "add_dll_directory"):',
                        '        os.add_dll_directory(_dll_dir)',
                        f'sys.path.append({repr(_site_pkg)})',
                        'import vapoursynth as vs',
                        f'with open({repr(str(script_path))}, "r", encoding="utf-8") as _f:',
                        '    _code = _f.read()',
                        f'exec(compile(_code, {repr(str(script_path))}, "exec"))',
                        '_result = vs.get_output(0)',
                        '_node = _result.clip if hasattr(_result, "clip") else _result',
                        '_node.output(sys.stdout.buffer, y4m=True)',
                    ])
                    _py_env_3b = os.environ.copy()
                    _py_env_3b['PATH'] = (VS_DEPS_DIR + os.pathsep
                                         + _plugins64 + os.pathsep
                                         + _pip_pkg_dir + os.pathsep
                                         + _py_env_3b.get('PATH', ''))
                    if diag:
                        diag.captured("vspipe-attempt-3b", result.stdout, result.stderr)
                        diag.kv("vspipe-retry-3b",
                                f"Python-direct pip: {_sys_py} (at {_pip_pkg_dir})")
                        diag.raw(f"wrapper-3b:\n{_wrapper_3b}")
                    result = _run_piped([_sys_py, '-c', _wrapper_3b], _ffmpeg_encode_cmd,
                                        prod_env=_py_env_3b)
                    if diag:
                        diag.captured("python-direct-3b-result", result.stdout, result.stderr)
                        diag.kv("python-direct-3b-returncode", str(result.returncode))
                else:
                    self._log("  pip vapoursynth not available — Python-direct fallback exhausted.")

        if result.returncode != 0:
            err_text = (result.stderr or result.stdout or "").strip()
            self._log(f"Processing error:\n{err_text}")
            if diag:
                diag.captured("pipe", result.stdout, result.stderr)
                diag.kv("producer_rc", str(result.producer_rc))
                diag.kv("consumer_rc", str(result.consumer_rc))
                diag.kv("pipe", f"FAILED (returncode={result.returncode})")
                diag.close(success=False)

            # Detect the Python/VapourSynth version incompatibility specifically.
            _is_vsscript_fail = 'Failed to initialize VSScript' in err_text
            _bundled_py_ver = 'unknown'
            try:
                for _f in os.listdir(VS_DEPS_DIR):
                    if _f.lower().startswith('python3') and _f.lower().endswith('._pth'):
                        _bundled_py_ver = _f[6:-4]   # e.g. "314"
                        break
            except Exception:
                pass
            _sys_py_ver = f"{sys.version_info.major}{sys.version_info.minor}"

            def _show_vs_err():
                import tkinter.messagebox as _mb
                if _is_vsscript_fail:
                    msg = (
                        "VapourSynth failed to start (VSScript init error).\n\n"
                        f"Your system Python is "
                        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}.\n"
                        "The bundled VapourSynth R73 only supports Python 3.8–3.12.\n\n"
                        "The app tried all fallback methods including auto-installing "
                        "vapoursynth via pip, but all attempts failed.\n\n"
                        "To fix, run this in a terminal and restart the app:\n\n"
                        "    pip install vapoursynth\n\n"
                        "You do NOT need to delete _deps or change your Python version."
                    )
                    _mb.showerror("VapourSynth Version Incompatibility", msg,
                                  parent=self.winfo_toplevel() if self.winfo_exists() else None)
                else:
                    short = err_text[:1200] if len(err_text) > 1200 else err_text
                    _mb.showerror(
                        "VapourSynth Error",
                        "vspipe failed to process the video.\n\n"
                        "Error details:\n" + (short if short else "(no output captured)"),
                        parent=self.winfo_toplevel() if self.winfo_exists() else None
                    )
            self.after(0, _show_vs_err)
            # Clean up temp audio if it exists
            try:
                os.remove(temp_audio)
            except Exception:
                pass
            raise Exception("processing failed")

        if diag:
            diag.captured("pipe", result.stdout, result.stderr)
            diag.kv("pipe", "SUCCESS")
            diag.timing("pipe end")

        self._update_progress(0.9)
        self._update_status("Muxing audio...")

        # Step 3: Mux video with clean extracted audio
        if has_audio:
            temp_output = str(output_path) + '.temp' + output_ext
            os.rename(output_path, temp_output)

            # Determine audio codec based on output format
            if output_ext == '.mp4':
                audio_args = ['-c:a', 'aac', '-b:a', '192k']
            else:
                # For MOV/MKV, copy PCM audio directly
                audio_args = ['-c:a', 'pcm_s16le']

            # Set explicit frame rate for proper sync (like Hybrid does)
            mux_cmd = [
                FFMPEG_PATH,
                '-y',
                '-r', '60000/1001',  # Explicit 59.94fps for doubled frame rate
                '-i', temp_output,
                '-i', temp_audio,
                '-c:v', 'copy',
                '-map', '0:v:0',
                '-map', '1:a:0',
            ]
            mux_cmd.extend(audio_args)
            mux_cmd.extend(['-r', '60000/1001', str(output_path)])

            self._log("Muxing video with extracted audio...")
            if diag:
                diag.section("Step 3: Audio Mux")
                diag.cmd(mux_cmd)

            mux_result = run_hidden(mux_cmd, timeout=None)

            if diag:
                diag.captured("mux", mux_result.stdout, mux_result.stderr)
                diag.kv("mux", "SUCCESS" if mux_result.returncode == 0
                        else f"FAILED (returncode={mux_result.returncode})")
                diag.timing("mux end")

            # Clean up temp files
            try:
                os.remove(temp_output)
            except:
                pass
            try:
                os.remove(temp_audio)
            except:
                pass
        else:
            self._log("No audio to mux, video-only output")
            if diag:
                diag.section("Step 3: Audio Mux")
                diag.kv("mux", "SKIPPED — no audio stream")

        self._update_progress(1.0)

        # Cleanup: delete .vpy script and any temp files created during this run
        for cleanup_path in [script_path]:
            try:
                if os.path.exists(str(cleanup_path)):
                    os.remove(str(cleanup_path))
                    self._log(f"  Cleaned up: {os.path.basename(str(cleanup_path))}")
            except Exception as e:
                self._log(f"  Note: could not delete {os.path.basename(str(cleanup_path))}: {e}")

        if diag:
            diag.section("Output")
            diag.kv("output_file", str(output_path))
            diag.kv("output_size", f"{os.path.getsize(str(output_path)) // 1024} KB"
                    if os.path.exists(str(output_path)) else "unknown")
            diag.close(success=True)

        return str(output_path), diag_log_path

    def _show_batch_complete(self):
        """Show completion UI for batch processing."""
        # Store last output path for comparison
        if self.completed_files:
            self.completed_output_path = self.completed_files[-1][1]
        else:
            self.completed_output_path = None
        
        btn_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        btn_frame.pack(fill='x', pady=(15, 0))
        
        if self.completed_files:
            # Open folder button (opens folder of first completed file)
            first_output = self.completed_files[0][1]
            ModernButton(btn_frame, "Open Folder",
                        lambda: os.startfile(os.path.dirname(first_output)),
                        width=120).pack(side='left', padx=(0, 10))

            # Play last video
            if len(self.completed_files) == 1:
                ModernButton(btn_frame, "Play Video",
                            lambda: os.startfile(self.completed_files[0][1]),
                            primary=True, width=120).pack(side='left', padx=(0, 10))

        ModernButton(btn_frame, "Process More Files",
                    self._reset_wizard,
                    width=140).pack(side='left')

        # Show diagnostic log paths if any were created
        log_paths = getattr(self, 'completed_log_paths', [])
        if log_paths:
            log_card = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=15, pady=10)
            log_card.pack(fill='x', pady=(10, 0))
            tk.Label(log_card,
                     text="Diagnostic log saved:",
                     font=('Segoe UI', 10, 'bold'),
                     fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD).pack(anchor='w')
            for _lp in log_paths:
                _lp_copy = _lp
                row = tk.Frame(log_card, bg=Colors.BG_CARD)
                row.pack(fill='x', pady=(2, 0))
                tk.Label(row,
                         text=os.path.basename(_lp_copy),
                         font=('Segoe UI', 10),
                         fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD).pack(side='left')
                ModernButton(row, "Open",
                             lambda p=_lp_copy: os.startfile(p),
                             width=60).pack(side='left', padx=(10, 0))
        
        # Show summary if multiple files
        if len(self.files_to_process) > 1:
            summary_frame = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=15, pady=10)
            summary_frame.pack(fill='x', pady=(15, 0))
            
            tk.Label(summary_frame, text="Summary",
                    font=('Segoe UI', 10, 'bold'),
                    fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD).pack(anchor='w')
            
            for filepath, output in self.completed_files:
                tk.Label(summary_frame, 
                        text=f"✓ {os.path.basename(filepath)} → {os.path.basename(output)}",
                        font=('Segoe UI', 12),
                        fg=Colors.SUCCESS, bg=Colors.BG_CARD).pack(anchor='w')
            
            for filepath, error in self.failed_files:
                tk.Label(summary_frame, 
                        text=f"❌ {os.path.basename(filepath)}: {error[:50]}",
                        font=('Segoe UI', 12),
                        fg=Colors.ERROR, bg=Colors.BG_CARD).pack(anchor='w')
        
        # Comparison video option - only for single file processing.
        # Hidden when trimming was used: the output timeline no longer lines
        # up with the original, so a side-by-side would compare different scenes.
        elif (len(self.files_to_process) == 1 and self.completed_output_path
              and not self._get_trim_plan()):
            compare_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
            compare_frame.pack(fill='x', pady=(15, 0))

            self.compare_var = tk.BooleanVar(value=False)

            compare_card = tk.Frame(compare_frame, bg=Colors.BG_CARD, padx=15, pady=12)
            compare_card.pack(fill='x')

            top_row = tk.Frame(compare_card, bg=Colors.BG_CARD)
            top_row.pack(fill='x')

            cb = tk.Checkbutton(top_row,
                                text="Generate 20-second comparison video",
                                variable=self.compare_var,
                                command=self._generate_comparison,
                                font=('Segoe UI', 12),
                                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD,
                                selectcolor=Colors.BG_DARK,
                                activebackground=Colors.BG_CARD,
                                activeforeground=Colors.TEXT_PRIMARY)
            cb.pack(side='left')

            tk.Label(top_row,
                     text="Split-screen: 10s normal + 10s 300% zoom",
                     font=('Segoe UI', 11),
                     fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD).pack(side='left', padx=(10, 0))
    
    def _show_complete(self, output_path):
        """Legacy single-file completion (for backwards compatibility)."""
        self._show_batch_complete()
        
        # Comparison video option
        if output_path:
            compare_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
            compare_frame.pack(fill='x', pady=(20, 0))
            
            self.compare_var = tk.BooleanVar(value=False)
            
            compare_card = tk.Frame(compare_frame, bg=Colors.BG_CARD, padx=15, pady=12)
            compare_card.pack(fill='x')
            
            cb = tk.Checkbutton(compare_card,
                               text="Generate 20-second comparison video",
                               variable=self.compare_var,
                               font=('Segoe UI', 12),
                               fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD,
                               selectcolor=Colors.BG_DARK,
                               activebackground=Colors.BG_CARD,
                               activeforeground=Colors.TEXT_PRIMARY)
            cb.pack(side='left')

            tk.Label(compare_card,
                    text="Side-by-side original vs enhanced (10 s normal + 10 s at 300%)",
                    font=('Segoe UI', 12),
                    fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD).pack(side='left', padx=(10, 0))
            
            ModernButton(compare_card, "Create", 
                        self._generate_comparison,
                        width=80).pack(side='right')
    
    def _generate_comparison(self):
        """Generate a split-screen comparison video (left half original, right half enhanced).
        First 10 seconds: normal view. Second 10 seconds: 300% zoom closeup."""
        if not self.compare_var.get():
            return  # Checkbox was just unchecked — do nothing

        if not self.completed_output_path:
            messagebox.showwarning("Not Ready", "No processed video found. Please process a file first.")
            return
        
        output_path = Path(self.completed_output_path)

        # Get original input path from the first file processed
        if self.completed_files:
            input_path = self.completed_files[0][0]
        else:
            input_path = self.config_data.get('input_path')

        if not input_path or not os.path.exists(str(input_path)):
            messagebox.showwarning("Original Not Found",
                                   f"Cannot find the original source file:\n{input_path}\n\n"
                                   "Make sure the source file hasn't moved.")
            self.compare_var.set(False)
            return

        self._log("\n📊 Starting comparison video generation...")
        self._log(f"  Original : {os.path.basename(str(input_path))}")
        self._log(f"  Enhanced : {os.path.basename(str(output_path))}")
        self._update_status("Creating comparison video...")
            
        video_format = self.config_data.get('format', 'ntsc')
        
        # Create comparison filename
        comparison_path = output_path.parent / (output_path.stem + '_COMPARISON.mp4')
        
        # (status/log already written above)
        
        # Run in thread to not block UI
        def generate():
            try:
                # Determine PAR correction for original based on format
                if video_format == 'ntsc':
                    par_scale = "scale=640:480"
                else:
                    par_scale = "scale=768:576,scale=640:480"
                
                # Try to detect if drawtext is usable.  Note: the bundled
                # FFmpeg's fontconfig finds no default font on Windows, so
                # drawtext only renders when given an explicit fontfile —
                # without one it must be treated as unavailable.
                test_cmd = [FFMPEG_PATH, '-filters']
                test_result = run_hidden(test_cmd, timeout=10)
                font_arg = _drawtext_fontfile_arg()
                has_drawtext = (bool(font_arg)
                                and 'drawtext' in (test_result.stdout or ''))

                # 300% zoom = center third of the frame blown up to full size
                zoom = "crop=iw/3:ih/3,scale=640:480"

                if has_drawtext:
                    def seg_labels(left_text, right_text):
                        return (
                            "drawbox=x=319:y=0:w=2:h=ih:c=white:t=fill,"
                            f"drawtext={font_arg}text='{left_text}':x=20:y=15"
                            ":fontsize=20:fontcolor=yellow:box=1:boxcolor=black@0.7:boxborderw=6,"
                            f"drawtext={font_arg}text='{right_text}':x=w-tw-20:y=15"
                            ":fontsize=20:fontcolor=yellow:box=1:boxcolor=black@0.7:boxborderw=6"
                        )
                    seg_a_lbl = seg_labels('Original', 'Deinterlaced')
                    # A literal % needs \\% in the filter string: the option
                    # parser strips one backslash, drawtext's text expander
                    # uses the second to escape the % (a bare % is treated as
                    # a broken %{...} sequence and kills the whole label).
                    seg_b_lbl = seg_labels(r'Original (300\\%)', r'Deinterlaced (300\\%)')
                    self.after(0, lambda: self._log("  Using drawtext labels..."))
                else:
                    # Fallback: colored bars (red = Original, green = Deinterlaced)
                    bars = (
                        "drawbox=x=319:y=0:w=2:h=ih:c=white:t=fill,"
                        "drawbox=x=5:y=5:w=80:h=8:c=red:t=fill,"
                        "drawbox=x=555:y=5:w=80:h=8:c=green:t=fill"
                    )
                    seg_a_lbl = seg_b_lbl = bars
                    self.after(0, lambda: self._log("  Note: drawtext not available (Red=Original, Green=Deinterlaced)"))

                # Probe the enhanced clip's duration so short clips still get
                # both halves (e.g. a 12 s tape → 6 s normal + 6 s zoomed).
                try:
                    _p = run_hidden([FFPROBE_PATH, '-v', 'error', '-show_entries',
                                     'format=duration', '-of', 'csv=p=0',
                                     str(output_path)], timeout=30)
                    _dur = float(_p.stdout.strip())
                except Exception:
                    _dur = 20.0
                t_mid = min(10.0, _dur / 2)
                t_end = min(20.0, _dur)

                # 20-second comparison in two halves:
                #   0–10 s  side-by-side at normal size
                #  10–20 s  the same side-by-side at 300% (center third, 3×)
                # setsar=1 after each hstack: the zoom path changes the SAR and
                # concat refuses to join segments whose SARs differ.
                filter_comp = (
                    "[0:v]split=2[orig_a][orig_b];"
                    "[1:v]split=2[enh_a][enh_b];"
                    # Segment A — normal view
                    f"[orig_a]trim=0:{t_mid:.2f},setpts=PTS-STARTPTS,{par_scale}[oA];"
                    f"[enh_a]trim=0:{t_mid:.2f},setpts=PTS-STARTPTS,scale=640:480[eA];"
                    "[oA]crop=320:480:0:0[lA];"
                    "[eA]crop=320:480:320:0[rA];"
                    "[lA][rA]hstack=inputs=2,setsar=1[sA];"
                    f"[sA]{seg_a_lbl}[segA];"
                    # Segment B — 300% zoom on the center of the frame
                    f"[orig_b]trim={t_mid:.2f}:{t_end:.2f},setpts=PTS-STARTPTS,{par_scale},{zoom}[oB];"
                    f"[enh_b]trim={t_mid:.2f}:{t_end:.2f},setpts=PTS-STARTPTS,scale=640:480,{zoom}[eB];"
                    "[oB]crop=320:480:0:0[lB];"
                    "[eB]crop=320:480:320:0[rB];"
                    "[lB][rB]hstack=inputs=2,setsar=1[sB];"
                    f"[sB]{seg_b_lbl}[segB];"
                    "[segA][segB]concat=n=2:v=1:a=0"
                )
                cmd_comp = [
                    FFMPEG_PATH,
                    '-i', input_path,
                    '-i', str(output_path),
                    '-t', '20',
                    '-filter_complex', filter_comp,
                    '-an',
                    '-c:v', 'libx264',
                    '-crf', '18',
                    '-preset', 'fast',
                    '-y',
                    str(comparison_path)
                ]

                self.after(0, lambda: self._log("  Generating 20-second comparison..."))
                result = run_hidden(cmd_comp, timeout=300)

                if result.returncode == 0 and comparison_path.exists():
                    self.after(0, lambda: self._log(f"✓ Comparison saved: {comparison_path}"))
                    self.after(0, lambda: self._update_status("Comparison created!"))
                    self.after(0, lambda: messagebox.showinfo("Comparison Created",
                        f"20-second comparison saved:\n{comparison_path}\n\n"
                        f"Left: Original  |  Right: Deinterlaced\n"
                        f"0–10 s: normal view  ·  10–20 s: 300% zoom"))
                else:
                    self.after(0, lambda: self._log(f"❌ Comparison failed: {result.stderr[:300]}"))
                    self.after(0, lambda: self._update_status("Comparison failed"))
            except Exception as e:
                self.after(0, lambda: self._log(f"❌ Comparison error: {str(e)}"))
        
        threading.Thread(target=generate, daemon=True).start()
    
    def _reset_wizard(self):
        """Reset the wizard to process more files."""
        # Clear config but keep last folder
        last_folder = self.saved_settings.get('last_folder', '')
        self.config_data = {
            'crop_left': 8,
            'crop_right': 8,
            'par_correction': True,
            'per_file_settings': {},
        }
        # Clear batch processing state
        self.files_to_process = []
        self.completed_files = []
        self.failed_files = []
        self.completed_log_paths = []
        self.current_file_index = 0
        # Clear temp images
        for path in self.temp_images:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except:
                pass
        self.temp_images = []
        # Go to Select File step (step 1) so user can immediately pick new files
        self._show_step(1)




# ============================================================
# First-Run Setup Window  (Beta-02 — VapourBox-style)
# ============================================================

class FirstRunSetupWindow(tk.Tk):
    """
    Shown on first launch when _deps\ is absent.
    Downloads ONE zip from a URL we control (our own GitHub releases),
    extracts it to _deps\ next to the EXE, then hands off to the wizard.

    Structure of vcg-deps-vN.zip:
        vcg-deps-vN/
          ffmpeg/    ffmpeg.exe  ffprobe.exe
          vs/        vspipe.exe  VapourSynth.dll  VSScript.dll  portable.vs
                     python3XX.dll  python3XX.zip  python3XX._pth
                     site-packages/  vapoursynth.pyd  havsfunc.py
                                     mvsfunc/  adjust.py
                     plugins64/      lsmas.dll  libmvtools.dll  fmtconv.dll
          vcg_deps.version
    """

    WIN_W = 560
    WIN_H = 340

    def __init__(self):
        super().__init__()
        self.title("VCG Deinterlacer — First Run Setup")
        self.resizable(False, False)
        self.configure(bg=Colors.BG_DARK)
        self._center_window()
        self._build_ui()
        threading.Thread(target=self._run_setup, daemon=True).start()

    # ── Geometry ────────────────────────────────────────────────

    def _center_window(self):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - self.WIN_W) // 2
        y  = (sh - self.WIN_H) // 2
        self.geometry(f"{self.WIN_W}x{self.WIN_H}+{x}+{y}")

    # ── UI ──────────────────────────────────────────────────────

    def _build_ui(self):
        tk.Label(self, text="Setting Up VCG Deinterlacer",
                 font=("Segoe UI", 16, "bold"),
                 fg=Colors.TEXT_PRIMARY, bg=Colors.BG_DARK).pack(pady=(28, 4))

        tk.Label(self, text="Downloading tools — this only happens once (~136 MB).",
                 font=("Segoe UI", 10),
                 fg=Colors.TEXT_SECONDARY, bg=Colors.BG_DARK).pack(pady=(0, 18))

        # Progress bar
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Setup.Horizontal.TProgressbar",
                        troughcolor=Colors.BG_CARD, background=Colors.ACCENT,
                        borderwidth=0, thickness=10)
        self._pb_var = tk.DoubleVar(value=0)
        self._pb = ttk.Progressbar(self, variable=self._pb_var,
                                   style="Setup.Horizontal.TProgressbar",
                                   maximum=100, length=self.WIN_W - 60)
        self._pb.pack(padx=30, fill="x")

        # Percentage label
        self._pct_lbl = tk.Label(self, text="0 %",
                                  font=("Segoe UI", 9),
                                  fg=Colors.TEXT_SECONDARY, bg=Colors.BG_DARK)
        self._pct_lbl.pack(pady=(4, 0))

        # Log box
        log_frame = tk.Frame(self, bg=Colors.BG_CARD)
        log_frame.pack(fill="both", expand=True, padx=30, pady=(12, 0))
        self._log = tk.Text(log_frame, font=("Consolas", 8),
                             bg=Colors.BG_CARD, fg=Colors.TEXT_SECONDARY,
                             bd=0, relief="flat", wrap="word",
                             state="disabled", height=6)
        self._log.pack(fill="both", expand=True, padx=8, pady=8)

        self._status_lbl = tk.Label(self, text="Please wait…",
                                     font=("Segoe UI", 9),
                                     fg=Colors.TEXT_HINT, bg=Colors.BG_DARK)
        self._status_lbl.pack(pady=(6, 16))

    # ── Thread-safe helpers ──────────────────────────────────────

    def _log_line(self, msg):
        def _do():
            self._log.configure(state="normal")
            self._log.insert("end", msg + "\n")
            self._log.see("end")
            self._log.configure(state="disabled")
        self.after(0, _do)

    def _set_progress(self, pct):
        def _do():
            self._pb_var.set(pct)
            self._pct_lbl.configure(text=f"{int(pct)} %")
        self.after(0, _do)

    def _set_status(self, msg):
        self.after(0, lambda: self._status_lbl.configure(text=msg))

    # ── Download (PowerShell → curl.exe fallback) ────────────────

    def _download(self, url, dest_path):
        """Download url to dest_path.  Returns True on success."""
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        # ── Try PowerShell first ──
        ps_cmd = (
            '[Net.ServicePointManager]::SecurityProtocol = '
            '[Net.SecurityProtocolType]::Tls12; '
            '$ProgressPreference = "SilentlyContinue"; '
            f'Invoke-WebRequest -Uri "{url}" -OutFile "{dest_path}" -UseBasicParsing'
        )
        self._dl_done = False
        self._dl_error = None

        def _run(cmd_args):
            try:
                r = subprocess.run(cmd_args, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   creationflags=subprocess.CREATE_NO_WINDOW,
                                   timeout=900)
                if r.returncode != 0:
                    self._dl_error = (r.stderr or r.stdout or b"").decode(
                        errors="replace")[:300]
            except Exception as exc:
                self._dl_error = str(exc)
            finally:
                self._dl_done = True

        import math
        def _animate_and_wait():
            frame = 0
            while not self._dl_done:
                pct = 50 + 45 * math.sin(frame * 0.12)
                self._set_progress(pct)
                time.sleep(0.08)
                frame += 1

        threading.Thread(target=_run,
                         args=(['powershell', '-NoProfile', '-NonInteractive',
                                '-Command', ps_cmd],),
                         daemon=True).start()
        _animate_and_wait()

        if self._dl_error or not os.path.exists(dest_path):
            self._log_line(f"  PowerShell failed — trying curl.exe…")
            self._dl_done = False
            self._dl_error = None
            threading.Thread(target=_run,
                             args=(['curl.exe', '-L', '-o', dest_path, url,
                                    '--silent', '--show-error',
                                    '--max-time', '900'],),
                             daemon=True).start()
            _animate_and_wait()

        if self._dl_error or not os.path.exists(dest_path):
            return False

        size_mb = os.path.getsize(dest_path) / 1_048_576
        if size_mb < 1.0:
            self._log_line(f"  ✘ Downloaded only {size_mb:.2f} MB — likely blocked.")
            try:
                os.remove(dest_path)
            except Exception:
                pass
            return False

        self._log_line(f"  ✔ Download complete ({size_mb:.1f} MB).")
        return True

    # ── Extract ZIP ──────────────────────────────────────────────

    def _extract(self, zip_path):
        """Extract vcg-deps-vN.zip to DEPS_DIR."""
        self._set_status("Extracting…")
        extract_target = os.path.dirname(DEPS_DIR)
        self._log_line("Extracting deps package…")
        self._log_line(f"  Target: {extract_target}")
        self._log_line(f"  DEPS_DIR: {DEPS_DIR}")
        try:
            if os.path.exists(DEPS_DIR):
                shutil.rmtree(DEPS_DIR, ignore_errors=True)

            with zipfile.ZipFile(zip_path, 'r') as zf:
                total = len(zf.infolist())
                for i, member in enumerate(zf.infolist(), 1):
                    zf.extract(member, os.path.dirname(DEPS_DIR))
                    self._set_progress(50 + i * 45 // total)

            # ZIP root folder is vcg-deps-vN — rename to _deps
            extracted_root = os.path.join(os.path.dirname(DEPS_DIR), f'vcg-deps-v{DEPS_VERSION}')
            if os.path.isdir(extracted_root) and extracted_root != DEPS_DIR:
                if os.path.exists(DEPS_DIR):
                    shutil.rmtree(DEPS_DIR, ignore_errors=True)
                os.rename(extracted_root, DEPS_DIR)

            self._set_progress(100)
            self._log_line("  ✔ Extraction complete.")
            # ── Diagnostic: verify version file was extracted correctly ──
            ver_file = os.path.join(DEPS_DIR, 'vcg_deps.version')
            if os.path.exists(ver_file):
                try:
                    with open(ver_file) as _vf:
                        raw = _vf.read()
                    self._log_line(f"  ✔ Version file OK: {repr(raw.strip())}")
                except Exception as _ve:
                    self._log_line(f"  ✘ Version file read error: {_ve}")
            else:
                self._log_line(f"  ✘ Version file NOT found at: {ver_file}")
            return True
        except Exception as e:
            self._log_line(f"  ✘ Extraction failed: {e}")
            return False

    # ── Main orchestration ───────────────────────────────────────

    def _pip_install_packages(self, packages):
        """Install Python packages via pip during first-run setup.

        Installs Pillow (image previews) and vapoursynth (video processing).
        Failures are logged but do not block setup — the app degrades gracefully.
        """
        self._set_status("Installing Python dependencies…")
        self._log_line("")
        self._log_line(f"Installing Python packages: {', '.join(packages)}")
        try:
            cmd = [sys.executable, '-m', 'pip', 'install',
                   '--quiet', '--disable-pip-version-check'] + packages
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if result.returncode == 0:
                self._log_line("  ✔ Python packages installed.")
            else:
                err = (result.stderr or result.stdout or '').strip()[:400]
                self._log_line(f"  ✘ pip install failed (non-fatal): {err}")
        except Exception as e:
            self._log_line(f"  ✘ pip install error (non-fatal): {e}")

    def _run_setup(self):
        global FFMPEG_PATH, FFPROBE_PATH, VSPIPE_PATH

        self._set_status("Downloading VCG Deinterlacer tools…")
        self._log_line(f"Downloading deps package from:")
        self._log_line(f"  {DEPS_ZIP_URL}")

        tmp_zip = os.path.join(tempfile.gettempdir(), f'vcg-deps-v{DEPS_VERSION}.zip')
        ok = self._download(DEPS_ZIP_URL, tmp_zip)

        if not ok:
            self._log_line("")
            self._log_line("✘ Download failed.")
            self._log_line("  Please check your internet connection.")
            self._log_line("  You can also download the file manually:")
            self._log_line(f"  {DEPS_ZIP_URL}")
            self._log_line(f"  and place vcg-deps-v{DEPS_VERSION}.zip next to the EXE,")
            self._log_line(f"  then re-launch VCG Deinterlacer.")
            self._set_status("Download failed — see log for details.")
            self.after(0, lambda: self._show_manual_instructions())
            return

        ok = self._extract(tmp_zip)
        try:
            os.remove(tmp_zip)
        except Exception:
            pass

        if not ok:
            self._set_status("Extraction failed.")
            return

        # Update global path constants for this session
        FFMPEG_PATH  = os.path.join(DEPS_DIR, 'ffmpeg', 'ffmpeg.exe')
        FFPROBE_PATH = os.path.join(DEPS_DIR, 'ffmpeg', 'ffprobe.exe')
        VSPIPE_PATH  = os.path.join(DEPS_DIR, 'vs', 'vspipe.exe')
        write_paths_json()

        # Install Python packages: Pillow for image previews, vapoursynth for
        # Python-direct fallback processing when the bundled R73 vsscript.dll
        # cannot find the user's Python (e.g. Python 3.13/3.14 with R73).
        self._pip_install_packages(['Pillow', 'numpy', 'tkinterdnd2', 'vapoursynth'])

        self._set_status("Setup complete — launching VCG Deinterlacer…")
        self._log_line("")
        self._log_line("✔ All tools ready.  Launching wizard…")
        self.after(1200, self.destroy)

    def _show_manual_instructions(self):
        msg = (
            "The tools package could not be downloaded automatically.\n\n"
            "To install manually:\n\n"
            "1. Download this file in your browser:\n"
            f"   {DEPS_ZIP_URL}\n\n"
            f"2. Extract it — you should get a  vcg-deps-v{DEPS_VERSION}  folder.\n\n"
            "3. Rename that folder to  _deps\n"
            "   and place it next to VCG_Deinterlacer.exe\n\n"
            "4. Re-launch VCG Deinterlacer."
        )
        tk.messagebox.showinfo("Manual Setup Required", msg, parent=self)

# ============================================================
# Entry Point
# ============================================================

if __name__ == '__main__':
    try:
        # ── Beta-02: check deps and run first-run setup if needed ──
        if not deps_ready():
            setup_win = FirstRunSetupWindow()
            setup_win.mainloop()  # blocks until setup window is destroyed

        # ── Post-setup diagnostic (prints to console) ─────────────
        print(f"[VCG Diag] ── Post-setup check ──")
        print(f"[VCG Diag] DEPS_DIR   = {DEPS_DIR}")
        print(f"[VCG Diag] dir exists  = {os.path.isdir(DEPS_DIR)}")
        _ver_path = os.path.join(DEPS_DIR, 'vcg_deps.version')
        print(f"[VCG Diag] ver exists  = {os.path.exists(_ver_path)}")
        if os.path.exists(_ver_path):
            try:
                with open(_ver_path) as _vf:
                    _raw = _vf.read()
                print(f"[VCG Diag] ver content = {repr(_raw)}")
                print(f"[VCG Diag] stripped    = {repr(_raw.strip())}")
                print(f"[VCG Diag] matches '1' = {_raw.strip() == DEPS_VERSION}")
            except Exception as _e:
                print(f"[VCG Diag] ver read err= {_e}")
        if os.path.isdir(DEPS_DIR):
            print(f"[VCG Diag] contents    = {os.listdir(DEPS_DIR)}")
        print(f"[VCG Diag] deps_ready()= {deps_ready()}")
        print(f"[VCG Diag] ── end ──")

        # Re-check after setup — only launch wizard if deps are ready
        if not deps_ready():
            import tkinter as _tk2
            import tkinter.messagebox as _mb2
            _r = _tk2.Tk(); _r.withdraw()
            _mb2.showwarning(
                "Setup Incomplete",
                "The required tools were not installed.\n\n"
                "Please re-launch VCG Deinterlacer and complete the setup,\n"
                "or manually place the  _deps  folder next to the EXE.\n\n"
                f"Download from:\n{DEPS_ZIP_URL}"
            )
            _r.destroy()
        else:
            # ── Re-import optional packages installed by setup ────
            if not HAS_PIL:
                try:
                    from PIL import Image, ImageTk  # noqa: F811,F401
                    HAS_PIL = True  # noqa: F811
                    print("[VCG Diag] PIL re-imported after setup install.")
                except ImportError:
                    pass
            if not HAS_DND:
                try:
                    from tkinterdnd2 import DND_FILES, TkinterDnD  # noqa: F811,F401
                    HAS_DND = True  # noqa: F811
                    print("[VCG Diag] tkinterdnd2 re-imported after setup install.")
                except Exception:
                    pass

            # ── Main wizard ──────────────────────────────────────
            app = RestorationWizard()
            app.mainloop()

    except Exception:
        import traceback
        _tb = traceback.format_exc()
        # Show the error in a messagebox so it's visible even without a console
        try:
            import tkinter as _tk
            import tkinter.messagebox as _mb
            _root = _tk.Tk()
            _root.withdraw()
            _mb.showerror(
                "VCG Deinterlacer — Startup Error",
                "The application failed to start.\n\n"
                "Please report this error at videocaptureguide.com\n\n"
                + _tb
            )
            _root.destroy()
        except Exception:
            pass
