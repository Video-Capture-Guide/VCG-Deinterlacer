#!/usr/bin/env python3
# ============================================================
# VCG DEINTERLACER
# ============================================================
#
# Version:    Beta-02
# Build Date: 2026-03-28
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
VERSION = "Beta-02"
BUILD_DATE = "2026-03-28"
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

# Check for tkinterdnd2 for drag and drop
# Catch all exceptions, not just ImportError — in a Nuitka onefile build the
# tkdnd DLL can fail to load with OSError after a successful import.
try:
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
DEPS_VERSION    = '2'   # bump when you upload a new deps ZIP
print(f"[VCG Diag] DEPS_DIR  = {DEPS_DIR}")
print(f"[VCG Diag] deps exist= {os.path.isdir(DEPS_DIR)}")

# !! IMPORTANT: After uploading vcg-deps-v1.zip to your GitHub releases,
# replace this URL with the direct link to your asset.
DEPS_ZIP_URL = (
    'https://github.com/Video-Capture-Guide/vcg-deinterlacer-deps'
    '/releases/download/v2/vcg-deps-v2.zip'
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

VSPIPE_PATH  = (os.path.join(VS_DEPS_DIR, 'vspipe.exe')
                if os.path.exists(os.path.join(VS_DEPS_DIR, 'vspipe.exe'))
                else _tool_paths.get('vspipe_path')
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
      - plugins\\        (lsmas.dll, libmvtools.dll, fmtconv.dll)

    The ._pth file handles module search paths.  We must NOT set PYTHONHOME
    or PYTHONPATH — those conflict with the ._pth mechanism and can cause
    "Failed to import encodings" when the embedded Python starts up.

    We only need to:
      - Put VS_DEPS_DIR first on PATH (so DLLs are found there)
      - Set VSPluginPath for VapourSynth plugin auto-loading
      - REMOVE any inherited PYTHONHOME / PYTHONPATH from Nuitka's runtime
    """
    if not os.path.isdir(VS_DEPS_DIR):
        return None   # not in portable mode, use system environment

    env = os.environ.copy()

    # ── Remove Python variables that conflict with the ._pth file ──
    # Nuitka's runtime may have set these; they must not leak into vspipe.
    for key in ('PYTHONHOME', 'PYTHONPATH', 'PYTHONNOUSERSITE',
                'PYTHONSTARTUP', 'PYTHONPLATLIBDIR'):
        env.pop(key, None)

    # ── Set VapourSynth plugin path ──
    env['VSPluginPath'] = os.path.join(VS_DEPS_DIR, 'plugins64')

    # ── Prepend VS_DEPS_DIR to PATH so Windows finds python3XX.dll,
    #    VapourSynth.dll, VSScript.dll there first (before any Nuitka
    #    temp dir or system-installed copies). ──
    env['PATH'] = VS_DEPS_DIR + os.pathsep + env.get('PATH', '')

    return env


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
    Detect video format (NTSC/PAL) and capture method (SD/DV) using ffprobe
    by reading sample_aspect_ratio, resolution, and codec_name.

    SAR mapping:
      10:11  -> NTSC SD analog capture
       8:9   -> NTSC DV25 (MiniDV / Digital8 FireWire)
      59:54  -> PAL SD analog capture
      16:15  -> PAL DV25
    codec_name == 'dvvideo' also confirms DV capture.

    Returns dict with keys:
      'format'         : 'ntsc' | 'pal' | None
      'capture_method' : 'sd'   | 'dv'  | None
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
        if sar in ('10:11', '8:9'):
            result['format'] = 'ntsc'
        elif sar in ('59:54', '16:15'):
            result['format'] = 'pal'
        elif height == 480:
            result['format'] = 'ntsc'
        elif height == 576:
            result['format'] = 'pal'

        # ── Determine capture method from codec or SAR ──
        if codec == 'dvvideo' or sar in ('8:9', '16:15'):
            result['capture_method'] = 'dv'
        elif sar in ('10:11', '59:54'):
            result['capture_method'] = 'sd'
        elif sar in ('1:1', '0:1', ''):
            # Square pixels — typical of SD capture cards; treat as SD
            result['capture_method'] = 'sd'

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
            # Analyze 1 second of video at this point for temporal noise
            cmd = [
                FFMPEG_PATH, '-ss', str(timestamp), '-i', filepath, 
                '-t', '1',  # 1 second segment
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
    # Old thresholds (4/8/15 for YDIF, OR logic) flagged virtually all motion
    # video as noisy.  New thresholds:
    #   - YDIF raised to 10/20/30 to account for normal motion.
    #   - For "light" noise we require BOTH YDIF AND TOUT to be elevated,
    #     so motion alone does not trigger a recommendation.
    #   - "Moderate" and "heavy" still trigger on TOUT alone because high
    #     temporal outlier counts are nearly always genuine noise.
    if avg_diff > 30 or avg_variance > 0.12:
        noise_level = 'heavy'
        noise_desc = 'Heavy noise detected'
        recommendation = 'heavy'
    elif avg_diff > 20 or avg_variance > 0.06:
        noise_level = 'moderate'
        noise_desc = 'Moderate noise detected'
        recommendation = 'moderate'
    elif avg_diff > 10 and avg_variance > 0.02:
        # Require BOTH to be elevated — prevents flagging clean fast-motion video.
        noise_level = 'light'
        noise_desc = 'Light noise detected'
        recommendation = 'moderate'
    else:
        noise_level = 'clean'
        noise_desc = 'Video appears clean'
        recommendation = 'none'
    
    return {
        'noise_level': noise_level,
        'noise_desc': noise_desc,
        'recommendation': recommendation,
        'avg_diff': avg_diff,
        'std_diff': std_diff,
        'avg_variance': avg_variance,
        'samples_analyzed': len(diff_values),
        'analyzed': True
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

def generate_histogram_image(filepath):
    """Generate waveform/histogram image."""
    try:
        cmd = [FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', filepath]
        result = run_hidden(cmd, timeout=30)
        duration = float(result.stdout.strip())
    except:
        duration = 30
    
    timestamp = duration / 2
    temp_dir = os.environ.get('TEMP', os.path.dirname(filepath))
    histogram_path = os.path.join(temp_dir, f'levels_analysis_{os.getpid()}.png')
    
    try:
        # Simpler filter - just waveform, no side-by-side
        cmd = [
            FFMPEG_PATH, '-ss', str(timestamp), '-i', filepath, '-vframes', '1',
            '-vf', 'waveform=mode=column:intensity=0.4:graticule=green:flags=numbers+dots,scale=550:-1',
            '-y', histogram_path
        ]
        result = run_hidden(cmd, timeout=60)
        if result.returncode == 0 and os.path.exists(histogram_path):
            return histogram_path
        # Log error for debugging
        print(f"Waveform generation failed: {result.stderr}")
    except Exception as e:
        print(f"Waveform exception: {e}")
    return None

def generate_vectorscope_image(filepath):
    """Generate vectorscope image."""
    try:
        cmd = [FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', filepath]
        result = run_hidden(cmd, timeout=30)
        duration = float(result.stdout.strip())
    except:
        duration = 30
    
    timestamp = duration / 2
    temp_dir = os.environ.get('TEMP', os.path.dirname(filepath))
    vectorscope_path = os.path.join(temp_dir, f'color_analysis_{os.getpid()}.png')
    
    try:
        # Simpler filter - just vectorscope, no side-by-side
        cmd = [
            FFMPEG_PATH, '-ss', str(timestamp), '-i', filepath, '-vframes', '1',
            '-vf', 'vectorscope=mode=color4:graticule=green:opacity=0.5:envelope=instant,scale=400:-1',
            '-y', vectorscope_path
        ]
        result = run_hidden(cmd, timeout=60)
        if result.returncode == 0 and os.path.exists(vectorscope_path):
            return vectorscope_path
        print(f"Vectorscope generation failed: {result.stderr}")
    except Exception as e:
        print(f"Vectorscope exception: {e}")
    return None

# ============================================================
# Script Generation
# ============================================================

def generate_vpy_script(config):
    """Generate VapourSynth script based on configuration."""
    lines = []
    lines.append('# -*- coding: utf-8 -*-')
    lines.append('# VapourSynth Restoration Script')
    lines.append(f'# Generated by VCG Deinterlacer {VERSION_STRING}')
    lines.append(f'# {AUTHOR_HANDLE}')
    lines.append('')
    lines.append('import vapoursynth as vs')
    lines.append('from vapoursynth import core')
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
    lines.append('# Load source video with forced frame rate (fixes sync issues)')
    lines.append('try:')
    lines.append(f'    clip = core.lsmas.LWLibavSource(r"{filepath}", stream_index=0, cache=0, fpsnum={fpsnum}, fpsden={fpsden})')
    lines.append('except:')
    lines.append('    try:')
    lines.append(f'        clip = core.ffms2.Source(r"{filepath}")')
    lines.append(f'        clip = core.std.AssumeFPS(clip, fpsnum={fpsnum}, fpsden={fpsden})')
    lines.append('    except:')
    lines.append(f'        clip = core.bs.VideoSource(r"{filepath}")')
    lines.append(f'        clip = core.std.AssumeFPS(clip, fpsnum={fpsnum}, fpsden={fpsden})')
    lines.append('')
    
    # Convert to YUV420 or YUV422 if needed (DV uses YUV411 which QTGMC doesn't support)
    lines.append('# Convert to YUV422 if needed (DV 4:1:1 is not supported by QTGMC)')
    lines.append('if clip.format.subsampling_w == 2 and clip.format.subsampling_h == 0:')
    lines.append('    # YUV411 detected, convert to YUV422')
    lines.append('    clip = core.resize.Spline36(clip, format=vs.YUV422P8)')
    lines.append('elif clip.format.id not in [vs.YUV420P8, vs.YUV422P8, vs.YUV444P8, vs.YUV420P10, vs.YUV422P10, vs.YUV444P10, vs.GRAY8, vs.GRAY16]:')
    lines.append('    # Convert other unsupported formats to YUV422')
    lines.append('    clip = core.resize.Spline36(clip, format=vs.YUV422P8)')
    lines.append('')
    
    # Crop - only for SD capture (DV doesn't need edge crop)
    capture_method = config.get('capture_method', 'sd')
    if capture_method == 'sd':
        lines.append('# Crop edges (SD capture only)')
        lines.append(f'clip = core.std.Crop(clip, left={config.get("crop_left", 8)}, right={config.get("crop_right", 8)})')
        lines.append('')
    
    # QTGMC
    tff = config.get('field_order') == 'tff'
    lines.append('# QTGMC Deinterlacing')
    lines.append('clip = haf.QTGMC(')
    lines.append('    clip,')
    lines.append(f'    TFF={tff},')
    for key, value in QTGMC_SETTINGS.items():
        lines.append(f'    {key}={value},')
    lines[-1] = lines[-1].rstrip(',')
    lines.append(')')
    lines.append('')
    
    # Denoising
    noise_level = config.get('noise_level', 'none')
    if noise_level == 'moderate':
        lines.append('# Temporal denoising (moderate)')
        lines.append('clip = haf.SMDegrain(clip, tr=1, thSAD=300)')
        lines.append('')
    elif noise_level == 'heavy':
        lines.append('# Temporal denoising (heavy)')
        lines.append('clip = haf.SMDegrain(clip, tr=2, thSAD=400)')
        lines.append('')
    
    # Chroma shift
    if config.get('chroma_shift', False):
        lines.append('# Chroma shift correction')
        lines.append('clip = core.resize.Point(clip, src_left=2, src_top=2)')
        lines.append('')
    
    # Dropout removal
    if config.get('dropout_removal', False):
        lines.append('# Dropout removal')
        lines.append('clip = core.rgvs.Clense(clip)')
        lines.append('')
    
    # Color correction
    color_corr = config.get('color_correction', 'none')
    if color_corr == 'auto_fix':
        u_corr = config.get('u_correction', 0)
        v_corr = config.get('v_correction', 0)
        lines.append('# Auto color cast correction')
        lines.append(f'# Shifting U by {u_corr:.1f} and V by {v_corr:.1f} toward neutral')
        u_expr = f"x {u_corr:.1f} +" if u_corr >= 0 else f"x {abs(u_corr):.1f} -"
        v_expr = f"x {v_corr:.1f} +" if v_corr >= 0 else f"x {abs(v_corr):.1f} -"
        lines.append(f'clip = core.std.Expr([clip], ["", "{u_expr}", "{v_expr}"])')
        lines.append('')
    elif color_corr == 'auto_fix_boost':
        u_corr = config.get('u_correction', 0)
        v_corr = config.get('v_correction', 0)
        lines.append('# Auto color cast correction + saturation boost')
        lines.append(f'# Shifting U by {u_corr:.1f} and V by {v_corr:.1f} toward neutral, then boosting saturation')
        # Combined expression: first shift toward neutral, then boost saturation
        # (x + correction - 128) * 1.2 + 128 = x * 1.2 + correction * 1.2 - 128 * 1.2 + 128
        # Simplified: shift then scale around 128
        u_expr = f"x {u_corr:.1f} + 128 - 1.2 * 128 +" if u_corr >= 0 else f"x {abs(u_corr):.1f} - 128 - 1.2 * 128 +"
        v_expr = f"x {v_corr:.1f} + 128 - 1.2 * 128 +" if v_corr >= 0 else f"x {abs(v_corr):.1f} - 128 - 1.2 * 128 +"
        lines.append(f'clip = core.std.Expr([clip], ["", "{u_expr}", "{v_expr}"])')
        lines.append('')
    elif color_corr == 'boost_sat':
        lines.append('# Boost saturation')
        lines.append('clip = core.std.Expr([clip], ["", "x 128 - 1.2 * 128 +", "x 128 - 1.2 * 128 +"])')
        lines.append('')
    elif color_corr == 'reduce_sat':
        lines.append('# Reduce saturation')
        lines.append('clip = core.std.Expr([clip], ["", "x 128 - 0.8 * 128 +", "x 128 - 0.8 * 128 +"])')
        lines.append('')
    
    # Levels (Y plane only)
    levels_adj = config.get('levels_adjustment', 'none')
    if levels_adj == 'clamp':
        lines.append('# Clamp luma levels to legal range (16-235)')
        lines.append('clip = core.std.Levels(clip, min_in=0, max_in=255, min_out=16, max_out=235, planes=[0])')
        lines.append('')
    elif levels_adj == 'stretch':
        lines.append('# Stretch luma to legal range (16-235)')
        lines.append('clip = core.std.Levels(clip, min_in=0, max_in=255, min_out=16, max_out=235, gamma=1.0, planes=[0])')
        lines.append('')
    
    # PAR correction - scale to standard square pixel resolutions
    # Note: We scale to fixed output sizes regardless of input crop
    if config.get('par_correction', True):
        if config.get('format') == 'ntsc':
            # NTSC: Output 640x480 (standard square pixel SD)
            lines.append('# PAR correction to 640x480 square pixels')
            lines.append('clip = core.resize.Spline36(clip, width=640, height=480)')
        else:
            # PAL: Output 768x576 (standard square pixel SD) 
            lines.append('# PAR correction to 768x576 square pixels')
            lines.append('clip = core.resize.Spline36(clip, width=768, height=576)')
        lines.append('')
    
    lines.append('clip.set_output()')
    return '\n'.join(lines)

def get_ffmpeg_output_args(config):
    fmt = config.get('output_format', 'prores')
    if fmt == 'prores':
        return ['-c:v', 'prores_ks', '-profile:v', '3', '-pix_fmt', 'yuv422p10le'], '.mov'
    elif fmt == 'h264':
        return ['-c:v', 'libx264', '-crf', '18', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k'], '.mp4'
    elif fmt == 'ffv1':
        return ['-c:v', 'ffv1', '-level', '3', '-coder', '1', '-slicecrc', '1'], '.mkv'
    elif fmt == 'huffyuv':
        return ['-c:v', 'huffyuv', '-pix_fmt', 'yuv422p'], '.avi'
    elif fmt == 'utvideo':
        return ['-c:v', 'utvideo', '-pix_fmt', 'yuv422p'], '.avi'
    elif fmt == 'lagarith':
        return ['-c:v', 'lagarith', '-pix_fmt', 'yuv420p'], '.avi'
    return ['-c:v', 'prores_ks', '-profile:v', '3'], '.mov'

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


class BreadcrumbBar(tk.Frame):
    """Horizontal breadcrumb strip that supports *grouped* crumbs.

    Each crumb may span several step indices (e.g. "Advanced" covers steps 3-6).
    Pass `crumbs` as a list of (label, [step_indices]) tuples.
    If omitted, each step from index 1 onwards gets its own crumb.

    Call set_step(index) to refresh the visual state.
    """

    PILL_D = 28      # pill diameter
    LINE_W = 36      # connector line width
    PAD    = 8       # horizontal padding around connector

    def __init__(self, parent, steps, crumbs=None, **kwargs):
        super().__init__(parent, bg=Colors.BG_MAIN, **kwargs)
        self.steps       = steps
        self.crumbs      = crumbs or [(s, [i]) for i, s in enumerate(steps) if i > 0]
        self.current_step = 0

    def set_step(self, index):
        self.current_step = index
        self._redraw()

    def _redraw(self):
        for w in self.winfo_children():
            w.destroy()

        container = tk.Frame(self, bg=Colors.BG_MAIN)
        container.pack(anchor='center', pady=10)

        for crumb_i, (label, step_indices) in enumerate(self.crumbs):
            crumb_num  = crumb_i + 1
            is_done    = all(s < self.current_step for s in step_indices)
            is_active  = self.current_step in step_indices
            is_future  = not is_done and not is_active

            # ── pill ───────────────────────────────────────────────────
            c = tk.Canvas(container, width=self.PILL_D, height=self.PILL_D,
                          bg=Colors.BG_MAIN, highlightthickness=0)
            c.pack(side='left')
            r = self.PILL_D // 2 - 2
            cx = cy = self.PILL_D // 2

            if is_done:
                c.create_oval(2, 2, self.PILL_D-2, self.PILL_D-2,
                              fill=Colors.SUCCESS, outline='')
                c.create_text(cx, cy, text='✓',
                              fill='white', font=('Segoe UI', 12, 'bold'))
            elif is_active:
                c.create_oval(2, 2, self.PILL_D-2, self.PILL_D-2,
                              fill=Colors.ACCENT, outline='')
                c.create_text(cx, cy, text=str(crumb_num),
                              fill='black', font=('Segoe UI', 10, 'bold'))
            else:
                c.create_oval(2, 2, self.PILL_D-2, self.PILL_D-2,
                              outline=Colors.TEXT_DISABLED, width=2)
                c.create_text(cx, cy, text=str(crumb_num),
                              fill=Colors.TEXT_DISABLED, font=('Segoe UI', 10))

            # ── label ──────────────────────────────────────────────────
            lbl_color = (Colors.TEXT_PRIMARY if (is_done or is_active) else Colors.TEXT_DISABLED)
            lbl_font  = (('Segoe UI', 10, 'bold') if is_active else ('Segoe UI', 10))
            tk.Label(container, text=label, font=lbl_font,
                     fg=lbl_color, bg=Colors.BG_MAIN).pack(side='left', padx=(5, 0))

            # ── connector (not after last crumb) ───────────────────────
            if crumb_i < len(self.crumbs) - 1:
                line_col = Colors.SUCCESS if is_done else Colors.TEXT_DISABLED
                lc = tk.Canvas(container, width=self.LINE_W, height=2,
                               bg=Colors.BG_MAIN, highlightthickness=0)
                lc.pack(side='left', padx=(self.PAD, self.PAD))
                lc.create_line(0, 1, self.LINE_W, 1, fill=line_col, width=2)


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
        if filepath.lower().endswith(('.avi', '.mp4', '.mkv', '.mov', '.m4v', '.mpg', '.mpeg')):
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
        valid_extensions = ('.avi', '.mp4', '.mkv', '.mov', '.m4v', '.mpg', '.mpeg')
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
        
        # Window size
        window_width = 950
        window_height = 900
        
        # Center window on screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2 - 40  # Slight offset up for taskbar
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        self.configure(bg=Colors.BG_DARK)
        self.resizable(True, True)
        self.minsize(820, 600)   # prevent layout from collapsing below a usable size
        
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
            "Welcome",         # 0  — hidden from breadcrumb
            "Select File",     # 1  → crumb 1
            "Source",          # 2  → crumb 2
            "Noise",           # 3  → crumb 3 "Advanced"
            "Color Bleeding",  # 4  → crumb 3 "Advanced"
            "Color Cast",      # 5  → crumb 3 "Advanced"
            "Levels",          # 6  → crumb 3 "Advanced"
            "Audio",           # 7  → crumb 3 "Advanced"
            "Finalize",        # 8  → crumb 4
        ]
        # Breadcrumb display groups: each entry = (label, [step_indices])
        self.crumbs = [
            ("Select File", [1]),
            ("Source",      [2]),
            ("Advanced",    [3, 4, 5, 6, 7]),
            ("Finalize",    [8]),
        ]
        self.current_step = 0
        
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
        body_label("When Advanced Mode denoising is enabled, SMDegrain runs after QTGMC:")
        card_text(
            "Light:   haf.SMDegrain(clip, tr=1, thSAD=300)\n"
            "Heavy:   haf.SMDegrain(clip, tr=2, thSAD=400)\n\n"
            "tr = temporal radius (frames to compare)\n"
            "thSAD = SAD threshold — higher = more aggressive noise removal",
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
        
        # Content area (full width — no sidebar)
        self.content_frame = tk.Frame(main_frame, bg=Colors.BG_MAIN)
        self.content_frame.pack(side='right', fill='both', expand=True)

        # Breadcrumb bar at the top of content_frame (hidden on welcome screen)
        self.breadcrumb = BreadcrumbBar(self.content_frame, self.steps,
                                        crumbs=self.crumbs)
        # Will be shown/hidden by _show_step
        
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
        self._clear_page()

        # Breadcrumb bar — hide on Welcome screen, show and update on all others
        if step_index == 0:
            self.breadcrumb.pack_forget()
        else:
            if not self.breadcrumb.winfo_ismapped():
                self.breadcrumb.pack(side='top', fill='x',
                                     before=self._page_canvas)
            self.breadcrumb.set_step(step_index)

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
        if step_index == 7:
            self.next_btn.text = "Finalize →"
        else:
            self.next_btn.text = "Next →"
        self.next_btn.set_disabled(False)
        self.next_btn._draw()

        # Show appropriate page (9-step navigation)
        step_methods = [
            self._page_welcome,         # 0
            self._page_select_file,     # 1
            self._page_source_details,  # 2
            self._page_noise,           # 3  Advanced ①
            self._page_chroma,          # 4  Advanced ② Color Bleeding
            self._page_color,           # 5  Advanced ③ Color Cast
            self._page_levels,          # 6  Advanced ④
            self._page_audio,           # 7  Advanced ⑤
            self._page_finalize,        # 8
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
                # Run batch type validation then advance if OK
                self._validate_batch_types(files, on_ok=lambda: self._show_step(2))
                return

        # ── Step 2: Source Details → show "Process Now or Advanced?" ──────────
        if self.current_step == 2:
            self._ask_basic_or_advanced()
            return

        # ── Last step: nothing to do ──────────────────────────────────────────
        if self.current_step >= len(self.steps) - 1:
            return

        self._show_step(self.current_step + 1)

    def _ask_basic_or_advanced(self):
        """After Field Order, let the user choose to process now or configure advanced options."""
        finalize_step = 8   # "Finalize" in the 9-step list
        advanced_step = 3   # First advanced page ("Noise")

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
                      "optional enhancements (noise removal, color analysis, levels, audio).",
                 font=('Segoe UI', 11), fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN,
                 wraplength=490, justify='left').pack(anchor='w', pady=(8, 20))

        def go_basic():
            dlg.destroy()
            self.bind('<Return>', lambda e: self._next_step())
            # Set defaults for all skipped advanced pages
            self.config_data.setdefault('noise_level', 'none')
            self.config_data.setdefault('color_correction', 'none')
            self.config_data.setdefault('levels_adjustment', 'none')
            self.config_data.setdefault('mix_audio', False)
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
                           text="⚙   Advanced Options  (noise removal, color, levels, audio)",
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
            self._show_step(self.current_step - 1)
    
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

        else:
            self.config_data.pop('input_path', None)
            self.config_data.pop('guessed_format', None)
            self.config_data.pop('auto_format', None)
            self.config_data.pop('auto_capture_method', None)
            self.config_data.pop('detected_sar', None)
    
    def _browse_files(self):
        # Use last folder if available
        initial_dir = self.saved_settings.get('last_folder', '')
        
        filepaths = filedialog.askopenfilenames(
            title="Select Video Files",
            initialdir=initial_dir if os.path.exists(initial_dir) else '',
            filetypes=[
                ("Video files", "*.avi *.mp4 *.mkv *.mov *.m4v *.mpg *.mpeg"),
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
                     ('SD' if auto_capture == 'sd' else None))
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
            # Point the existing badge variable at our new badge label
            self.detect_badge_lbl = self._fo_badge_lbl
            # Auto-trigger detection after a short delay
            self.after(400, self._run_field_order_detection)

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
            cap_name = 'DV Capture' if auto_capture == 'dv' else 'SD Capture'
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
            cap_name = 'DV Capture' if auto_capture == 'dv' else 'SD Capture'
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
                     "NTSC DV25 (MiniDV)  →  720×480, PAR 8:9  →  corrected to 640×480 square pixels\n"
                     "PAL SD capture  →  720×576, PAR 59:54  →  corrected to 768×576 square pixels\n"
                     "PAL DV25  →  720×576, PAR 16:15  →  corrected to 768×576 square pixels\n\n"
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
                    text="Generating waveform and measuring luma range",
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
        
        # Technical details (smaller)
        samples = data.get('samples_analyzed', 0)
        tech_text = f"Analyzed {samples} samples  •  Avg diff: {data.get('avg_diff', 0):.1f}  •  Variance: {data.get('avg_variance', 0):.3f}"
        self._selectable_label(result_card, tech_text,
                font=('Segoe UI', 12),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD).pack(anchor='w', pady=(2, 0))
        
        # === RECOMMENDATION ===
        ttk.Separator(result_card, orient='horizontal').pack(fill='x', pady=(10, 8))
        
        rec = data.get('recommendation', 'none')
        if rec == 'heavy':
            rec_text = "💡 Recommendation: Heavy denoising"
        elif rec == 'moderate':
            rec_text = "💡 Recommendation: Light denoising"
        else:
            rec_text = "💡 Recommendation: No denoising needed"
        
        tk.Label(result_card, text=rec_text,
                font=('Segoe UI', 10, 'bold'),
                fg=Colors.ACCENT, bg=Colors.BG_CARD).pack(anchor='w')
        
        # Show options
        card = tk.Frame(self.noise_options_frame, bg=Colors.BG_CARD)
        card.pack(fill='x', pady=(10, 0))
        
        options = [
            ("No noise removal", "none", "Keep original grain/noise"),
            ("Light denoising", "moderate", "SMDegrain with moderate settings"),
            ("Heavy denoising", "heavy", "SMDegrain with stronger settings")
        ]
        
        for i, (label, value, desc) in enumerate(options):
            ModernRadioButton(card, label, self.noise_var, value, desc).pack(fill='x')
            if i < len(options) - 1:
                ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
        
        # Pre-select based on recommendation
        self.noise_var.set(rec)
        self.config_data['noise_level'] = rec
        
        self.noise_var.trace_add('write', lambda *_: self.config_data.update({'noise_level': self.noise_var.get()}))
    
    def _page_chroma(self):
        tk.Label(self.page_container, text="Color Bleeding",
                font=('Segoe UI', 22, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')

        self._show_artifact_example(self.page_container, 'chroma',
            "What color bleeding looks like — colors smearing horizontally from composite video:")
        self._show_experimental_notice(self.page_container)

        # Check if multiple files selected
        num_files = len(self.config_data.get('input_files', []))
        if num_files > 1:
            # For batch processing, show simple options without analysis
            tk.Label(self.page_container, text="Select color bleeding fix for all files",
                    font=('Segoe UI', 12),
                    fg=Colors.TEXT_SECONDARY, bg=Colors.BG_MAIN).pack(anchor='w', pady=(4, 20))
            
            initial_chroma = 'yes' if self.config_data.get('chroma_shift') else 'no'
            self.config_data['chroma_shift'] = (initial_chroma == 'yes')
            self.chroma_var = tk.StringVar(value=initial_chroma)
            
            card = tk.Frame(self.page_container, bg=Colors.BG_CARD)
            card.pack(fill='x')
            
            ModernRadioButton(card, "No color bleeding fix", self.chroma_var, "no",
                             "Colors look properly aligned").pack(fill='x')
            ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
            ModernRadioButton(card, "Yes, fix color bleeding", self.chroma_var, "yes",
                             "Colors appear smeared or shifted sideways").pack(fill='x')
            
            self.chroma_var.trace_add('write', lambda *_: self.config_data.update({'chroma_shift': self.chroma_var.get() == 'yes'}))
            return
        
        # Single file - show analysis with progress indicator
        
        # Progress indicator card (prominent)
        self.chroma_progress_card = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=20, pady=20)
        self.chroma_progress_card.pack(fill='x', pady=(10, 0))
        
        # Spinner animation
        self.chroma_spinner_label = tk.Label(self.chroma_progress_card, text="⏳",
                font=('Segoe UI', 28),
                fg=Colors.ACCENT, bg=Colors.BG_CARD)
        self.chroma_spinner_label.pack()
        
        self.chroma_status_label = tk.Label(self.chroma_progress_card, 
                text="Analyzing color bleeding...",
                font=('Segoe UI', 12, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD)
        self.chroma_status_label.pack(pady=(10, 5))
        
        self.chroma_progress_label = tk.Label(self.chroma_progress_card, 
                text="Sampling frame 1 of 10",
                font=('Segoe UI', 12),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD)
        self.chroma_progress_label.pack()
        
        self.chroma_detail_label = tk.Label(self.chroma_progress_card, 
                text="Checking chroma channel spread for bleeding artifacts",
                font=('Segoe UI', 9, 'italic'),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD)
        self.chroma_detail_label.pack(pady=(10, 0))
        
        # Analysis results frame (hidden until analysis complete)
        self.chroma_results_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        self.chroma_results_frame.pack(fill='x')
        
        # Options frame (populated after analysis)
        self.chroma_options_frame = tk.Frame(self.page_container, bg=Colors.BG_MAIN)
        self.chroma_options_frame.pack(fill='x', pady=(10, 0))
        
        # Get initial value
        initial_chroma = 'yes' if self.config_data.get('chroma_shift') else 'no'
        self.config_data['chroma_shift'] = (initial_chroma == 'yes')
        self.chroma_var = tk.StringVar(value=initial_chroma)
        
        # Disable Next button during analysis
        self.chroma_analysis_complete = False
        if hasattr(self, 'next_btn'):
            self.next_btn.configure(state='disabled')
        
        # Start spinner animation
        self._animate_chroma_spinner()
        
        # Run analysis in thread
        threading.Thread(target=self._run_chroma_analysis, daemon=True).start()
    
    def _animate_chroma_spinner(self):
        """Animate the spinner during analysis."""
        if not hasattr(self, 'chroma_analysis_complete') or self.chroma_analysis_complete:
            return
        
        if not hasattr(self, 'chroma_spinner_label') or not self.chroma_spinner_label.winfo_exists():
            return
            
        spinners = ['⏳', '⌛']
        current = self.chroma_spinner_label.cget('text')
        next_idx = (spinners.index(current) + 1) % len(spinners) if current in spinners else 0
        self.chroma_spinner_label.config(text=spinners[next_idx])
        
        self.after(500, self._animate_chroma_spinner)
    
    def _update_chroma_progress(self, current, total):
        """Update the chroma analysis progress indicator."""
        if hasattr(self, 'chroma_progress_label') and self.chroma_progress_label.winfo_exists():
            self.after(0, lambda: self.chroma_progress_label.config(
                text=f"Sampling frame {current} of {total}"))
    
    def _run_chroma_analysis(self):
        if 'input_path' not in self.config_data:
            self.after(0, self._finish_chroma_analysis_error, "❌ No file selected")
            return
        
        try:
            # Run color bleeding analysis with progress callback
            bleed_data = analyze_color_bleeding(
                self.config_data['input_path'],
                sample_frames=10,
                progress_callback=self._update_chroma_progress
            )
            
            if bleed_data and bleed_data.get('analyzed'):
                self.config_data['bleed_data'] = bleed_data
                self.after(0, lambda: self._show_chroma_results(bleed_data))
            else:
                self.after(0, self._finish_chroma_analysis_error, "Could not analyze color bleeding")
        except Exception as e:
            self.after(0, self._finish_chroma_analysis_error, f"Analysis error: {str(e)[:30]}")
    
    def _finish_chroma_analysis_error(self, message):
        """Handle analysis error - show message and fallback options."""
        self.chroma_analysis_complete = True
        if hasattr(self, 'next_btn'):
            self.next_btn.configure(state='normal')
        
        # Hide progress card
        if hasattr(self, 'chroma_progress_card'):
            self.chroma_progress_card.pack_forget()
        
        # Show error
        error_label = tk.Label(self.chroma_results_frame, text=message,
                font=('Segoe UI', 12),
                fg=Colors.ERROR, bg=Colors.BG_MAIN)
        error_label.pack(anchor='w', pady=(0, 10))
        
        self._show_chroma_options_fallback()
    
    def _show_chroma_results(self, data):
        """Display chroma analysis results."""
        # Mark analysis complete and re-enable Next button
        self.chroma_analysis_complete = True
        if hasattr(self, 'next_btn'):
            self.next_btn.configure(state='normal')
        
        # Hide progress card
        if hasattr(self, 'chroma_progress_card'):
            self.chroma_progress_card.pack_forget()
        
        # Show analysis results
        result_card = tk.Frame(self.chroma_results_frame, bg=Colors.BG_CARD, padx=15, pady=12)
        result_card.pack(fill='x')
        
        tk.Label(result_card, text="🎨 Color Bleeding Analysis",
                font=('Segoe UI', 10, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD).pack(anchor='w')
        
        # Level indicator
        level = data.get('bleed_level', 'unknown')
        desc = data.get('bleed_desc', 'Unknown')
        
        if level == 'significant':
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
        
        # Technical details
        samples = data.get('samples_analyzed', 0)
        score = data.get('bleeding_score', 0)
        tech_text = f"Analyzed {samples} samples  •  Chroma spread score: {score:.1f}"
        tk.Label(result_card, text=tech_text,
                font=('Segoe UI', 12),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD).pack(anchor='w', pady=(2, 0))
        
        # Recommendation
        recommendation = data.get('recommendation', False)
        if recommendation:
            rec_text = "💡 Recommendation: Fix color bleeding"
            self.chroma_var.set('yes')
        else:
            rec_text = "💡 Recommendation: No fix needed"
            self.chroma_var.set('no')
        
        tk.Label(result_card, text=rec_text,
                font=('Segoe UI', 10, 'bold'),
                fg=Colors.ACCENT, bg=Colors.BG_CARD).pack(anchor='w', pady=(10, 0))
        
        # Show options
        self._show_chroma_options()
    
    def _show_chroma_options_fallback(self):
        """Show basic chroma options without analysis."""
        card = tk.Frame(self.chroma_options_frame, bg=Colors.BG_CARD)
        card.pack(fill='x')
        
        ModernRadioButton(card, "No color bleeding fix", self.chroma_var, "no",
                         "Colors look properly aligned").pack(fill='x')
        ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(card, "Yes, fix color bleeding", self.chroma_var, "yes",
                         "Colors appear smeared or shifted sideways").pack(fill='x')
        
        self.chroma_var.trace_add('write', lambda *_: self.config_data.update({'chroma_shift': self.chroma_var.get() == 'yes'}))
    
    def _show_chroma_options(self):
        """Show chroma options."""
        card = tk.Frame(self.chroma_options_frame, bg=Colors.BG_CARD)
        card.pack(fill='x', pady=(10, 0))
        
        ModernRadioButton(card, "No color bleeding fix", self.chroma_var, "no",
                         "Keep original colors").pack(fill='x')
        ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(card, "Yes, fix color bleeding", self.chroma_var, "yes",
                         "Shift chroma to correct horizontal bleeding").pack(fill='x')
        
        self.chroma_var.trace_add('write', lambda *_: self.config_data.update({'chroma_shift': self.chroma_var.get() == 'yes'}))
    
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
    
    def _page_color(self):
        tk.Label(self.page_container, text="Color Analysis",
                font=('Segoe UI', 22, 'bold'),
                fg=Colors.TEXT_PRIMARY, bg=Colors.BG_MAIN).pack(anchor='w')

        self._show_artifact_example(self.page_container, 'color_cast',
            "What a color cast looks like — a warm or cool tint over the whole image:")
        self._show_experimental_notice(self.page_container)

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
        
        # Update status
        self.after(0, lambda: self.color_status_label.config(text="Generating vectorscope..."))
        
        # Generate vectorscope image
        try:
            vectorscope_path = generate_vectorscope_image(self.config_data['input_path'])
            if vectorscope_path:
                self.temp_images.append(vectorscope_path)
        except Exception as e:
            vectorscope_path = None
        
        # Update status
        self.after(0, lambda: self.color_status_label.config(text="Analyzing color channels..."))
        self.after(0, lambda: self.color_progress_label.config(text="Measuring U/V chroma and saturation"))
        
        # Analyze color data
        color_data = analyze_color_data(self.config_data['input_path'])
        
        if color_data:
            self.config_data['color_data'] = color_data
            self.config_data['u_correction'] = color_data['u_correction']
            self.config_data['v_correction'] = color_data['v_correction']
            self.after(0, lambda: self._show_color_results(color_data, vectorscope_path))
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
    
    def _show_color_results(self, data, vectorscope_path=None):
        # Mark analysis complete; unlock Next only when all analyses are done
        self.color_analysis_complete = True
        self._on_analysis_section_done()
        
        # Hide progress card
        if hasattr(self, 'color_progress_card'):
            self.color_progress_card.pack_forget()
        
        # Show vectorscope if available
        if vectorscope_path:
            self.color_preview.pack(fill='x', before=self.color_results_frame)
            self.color_preview.load_image(vectorscope_path)
        
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
                text="Generating waveform and measuring luma range",
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
        
        # Update status
        self.after(0, lambda: self.levels_status_label.config(text="Generating waveform..."))
        
        # Generate waveform image
        waveform_path = None
        try:
            waveform_path = generate_histogram_image(self.config_data['input_path'])
            if waveform_path:
                self.temp_images.append(waveform_path)
        except Exception as e:
            pass
        
        # Update status
        self.after(0, lambda: self.levels_status_label.config(text="Analyzing luma levels..."))
        self.after(0, lambda: self.levels_progress_label.config(text="Measuring min/max brightness"))
        
        # Analyze levels
        levels_data = analyze_video_levels(self.config_data['input_path'])
        
        if levels_data and levels_data['min_y'] is not None:
            self.config_data['levels_data'] = levels_data
            self.after(0, lambda: self._show_levels_results(levels_data, waveform_path))
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
    
    def _show_levels_results(self, data, waveform_path=None):
        # Mark analysis complete; unlock Next only when all analyses are done
        self.levels_analysis_complete = True
        self._on_analysis_section_done()
        
        # Hide progress card
        if hasattr(self, 'levels_progress_card'):
            self.levels_progress_card.pack_forget()
        
        # Show waveform if available
        if waveform_path:
            self.levels_preview.pack(fill='x', before=self.levels_results_frame)
            self.levels_preview.load_image(waveform_path)
        
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
        
        # Options
        card = tk.Frame(self.levels_options_frame, bg=Colors.BG_CARD)
        card.pack(fill='x')
        
        ModernRadioButton(card, "No adjustment", self.levels_var, "none",
                         "Leave levels as-is").pack(fill='x')
        ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
        
        # Add "(recommended)" to clamp if adjustment needed
        clamp_label = "Clamp to legal (16-235)"
        if data['needs_adjustment']:
            clamp_label = "Clamp to legal (16-235) — recommended"
        ModernRadioButton(card, clamp_label, self.levels_var, "clamp",
                         "Clips extreme values, preserves contrast").pack(fill='x')
        ttk.Separator(card, orient='horizontal').pack(fill='x', padx=12)
        ModernRadioButton(card, "Stretch to legal", self.levels_var, "stretch",
                         "Compresses full range, may reduce contrast").pack(fill='x')
        
        if data['needs_adjustment']:
            self.levels_var.set('clamp')
            # Save immediately since trace_add hasn't been set yet
            self.config_data['levels_adjustment'] = 'clamp'
        
        self.levels_var.trace_add('write', lambda *_: self.config_data.update({'levels_adjustment': self.levels_var.get()}))
        
        # Help box explaining the options
        help_frame = tk.Frame(self.page_container, bg=Colors.BG_CARD, padx=15, pady=12)
        help_frame.pack(fill='x', pady=(15, 0))
        
        tk.Label(help_frame, text="ℹ️ Which should I choose?",
                font=('Segoe UI', 10, 'bold'),
                fg=Colors.ACCENT, bg=Colors.BG_CARD).pack(anchor='w')
        
        help_text = (
            "Clamp: Best for most analog/DV captures. Out-of-range values are usually "
            "noise or artifacts, not real picture detail. Preserves the original contrast.\n\n"
            "Stretch: Use only if the video was incorrectly captured at full range (0-255) "
            "when it should have been studio range. Keeps all detail but reduces contrast."
        )
        tk.Label(help_frame, text=help_text,
                font=('Segoe UI', 12),
                fg=Colors.TEXT_SECONDARY, bg=Colors.BG_CARD,
                justify='left', wraplength=550).pack(anchor='w', pady=(5, 0))
    
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
        
        for i, filepath in enumerate(self.files_to_process):
            self.current_file_index = i
            self._update_overall_progress()
            self._update_current_file(filepath)
            self._update_progress(0)
            
            self._log(f"\n{'='*50}")
            self._log(f"Processing file {i+1} of {total_files}: {os.path.basename(filepath)}")
            self._log(f"{'='*50}")
            
            try:
                output_path = self._process_single_file(filepath)
                self.completed_files.append((filepath, output_path))
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
    
    def _process_single_file(self, filepath):
        """Process a single file and return the output path."""
        self._log("Generating VapourSynth script...")
        self._update_status("Generating script...")
        self._update_progress(0.1)
        
        # Create config for this file
        file_config = self.config_data.copy()
        file_config['input_path'] = filepath
        
        # Generate script
        script = generate_vpy_script(file_config)
        
        # Save script with auto-numbering
        input_path = Path(filepath)
        output_args, output_ext = get_ffmpeg_output_args(file_config)
        
        # Find next available number
        counter = 1
        while True:
            suffix = f"_VCG-Deinterlacer_{counter:02d}"
            output_path = input_path.parent / (input_path.stem + suffix + output_ext)
            script_path = input_path.parent / (input_path.stem + suffix + '.vpy')
            if not output_path.exists() and not script_path.exists():
                break
            counter += 1
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script)
        
        self._log(f"Script saved: {script_path}")
        
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
        
        temp_audio = str(input_path.parent / f'temp_audio_{os.getpid()}.wav')
        
        self._log("Extracting audio to WAV...")
        self._log(f"  Detected: {audio_channels} channels @ {audio_sample_rate}Hz")
        
        # Check if user wants to mix audio channels
        mix_audio = self.config_data.get('mix_audio', False)
        
        if mix_audio:
            # Mix both channels together - useful when audio is only on one channel
            # pan=stereo|c0=c0+c1|c1=c0+c1 mixes L+R into both channels
            audio_extract_cmd = [
                FFMPEG_PATH,
                '-y',
                '-i', filepath,
                '-vn', '-sn',  # No video, no subtitles
                '-af', 'pan=stereo|c0=c0+c1|c1=c0+c1',  # Mix both channels to both outputs
                '-ar', '48000', # 48kHz sample rate
                '-acodec', 'pcm_s16le',  # PCM 16-bit
                '-f', 'wav',
                temp_audio
            ]
            self._log("  Mixing channels to ensure audio in both L+R")
        else:
            # Preserve original audio channels
            audio_extract_cmd = [
                FFMPEG_PATH,
                '-y',
                '-i', filepath,
                '-vn', '-sn',  # No video, no subtitles
                '-ac', '2',  # Stereo output
                '-ar', '48000', # 48kHz sample rate
                '-acodec', 'pcm_s16le',  # PCM 16-bit
                '-f', 'wav',
                temp_audio
            ]
            self._log("  Preserving original audio channels")
        
        result = run_hidden(audio_extract_cmd, timeout=None)
        
        # If pan filter failed, retry with simple conversion
        if result.returncode != 0:
            self._log("  Retrying audio extraction with simple stereo conversion...")
            audio_extract_cmd = [
                FFMPEG_PATH,
                '-y',
                '-i', filepath,
                '-vn', '-sn',
                '-ac', '2',
                '-ar', '48000',
                '-acodec', 'pcm_s16le',
                '-f', 'wav',
                temp_audio
            ]
            result = run_hidden(audio_extract_cmd, timeout=None)
        
        has_audio = result.returncode == 0 and os.path.exists(temp_audio) and os.path.getsize(temp_audio) > 1000
        if not has_audio:
            self._log("  No audio stream found or extraction failed, continuing without audio")
            try:
                os.remove(temp_audio)
            except:
                pass
        else:
            self._log("  Audio extracted successfully")
        
        self._update_status("Running VapourSynth...")
        self._update_progress(0.2)
        
        # Step 2: Run vspipe to Y4M
        temp_y4m = str(input_path.parent / f'temp_{os.getpid()}.y4m')
        
        self._log("Running vspipe...")
        vspipe_cmd = [VSPIPE_PATH, '-c', 'y4m', str(script_path), temp_y4m]
        # Pass portable Python/plugin environment when using bundled deps
        _vs_env = get_vspipe_env()
        result = run_hidden(vspipe_cmd, timeout=None,
                            **({'env': _vs_env} if _vs_env else {}))
        
        if result.returncode != 0:
            err_text = (result.stderr or result.stdout or "").strip()
            self._log(f"vspipe error:\n{err_text}")
            # Show the actual vspipe error so the user can report it
            def _show_vs_err():
                import tkinter.messagebox as _mb
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
            raise Exception("vspipe failed")
        
        self._update_progress(0.6)
        self._update_status("Encoding video...")
        
        # Step 3: FFmpeg encode video
        self._log("Running FFmpeg...")
        ffmpeg_cmd = [FFMPEG_PATH, '-i', temp_y4m]
        ffmpeg_cmd.extend(output_args)
        ffmpeg_cmd.extend(['-y', str(output_path)])
        
        result = run_hidden(ffmpeg_cmd, timeout=None)
        
        # Clean up temp Y4M file
        try:
            os.remove(temp_y4m)
        except:
            pass
        
        if result.returncode != 0:
            self._log(f"FFmpeg error: {result.stderr}")
            # Clean up temp audio if it exists
            try:
                os.remove(temp_audio)
            except:
                pass
            raise Exception("FFmpeg failed")
        
        self._update_progress(0.9)
        self._update_status("Muxing audio...")
        
        # Step 4: Mux video with clean extracted audio
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
            run_hidden(mux_cmd, timeout=None)
            
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
        
        self._update_progress(1.0)

        # Cleanup: delete .vpy script and any temp files created during this run
        for cleanup_path in [script_path]:
            try:
                if os.path.exists(str(cleanup_path)):
                    os.remove(str(cleanup_path))
                    self._log(f"  Cleaned up: {os.path.basename(str(cleanup_path))}")
            except Exception as e:
                self._log(f"  Note: could not delete {os.path.basename(str(cleanup_path))}: {e}")

        return str(output_path)

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
        
        # Comparison video option - only for single file processing
        elif len(self.files_to_process) == 1 and self.completed_output_path:
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
                               text="Generate 15-second comparison video",
                               variable=self.compare_var,
                               font=('Segoe UI', 12),
                               fg=Colors.TEXT_PRIMARY, bg=Colors.BG_CARD,
                               selectcolor=Colors.BG_DARK,
                               activebackground=Colors.BG_CARD,
                               activeforeground=Colors.TEXT_PRIMARY)
            cb.pack(side='left')
            
            tk.Label(compare_card, 
                    text="Side-by-side original vs enhanced",
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
                
                # Create two temp files: normal and closeup
                # Try to detect if drawtext is available
                test_cmd = [FFMPEG_PATH, '-filters']
                test_result = run_hidden(test_cmd, timeout=10)
                has_drawtext = 'drawtext' in test_result.stdout if test_result.stdout else False

                # Single 20-second side-by-side with ORIGINAL | DEINTERLACED labels throughout
                if has_drawtext:
                    filter_comp = (
                        f"[0:v]{par_scale}[orig_scaled];"
                        "[1:v]scale=640:480[enh_scaled];"
                        "[orig_scaled]crop=320:480:0:0[left_half];"
                        "[enh_scaled]crop=320:480:320:0[right_half];"
                        "[left_half][right_half]hstack=inputs=2[stacked];"
                        "[stacked]drawbox=x=319:y=0:w=2:h=ih:c=white:t=fill,"
                        "drawbox=x=10:y=10:w=130:h=30:c=black@0.7:t=fill,"
                        "drawtext=text='ORIGINAL':x=20:y=15:fontsize=20:fontcolor=yellow,"
                        "drawbox=x=510:y=10:w=155:h=30:c=black@0.7:t=fill,"
                        "drawtext=text='DEINTERLACED':x=520:y=15:fontsize=20:fontcolor=yellow"
                    )
                    self.after(0, lambda: self._log("  Using drawtext labels..."))
                else:
                    # Fallback: colored bars (red = Original, green = Deinterlaced)
                    filter_comp = (
                        f"[0:v]{par_scale}[orig_scaled];"
                        "[1:v]scale=640:480[enh_scaled];"
                        "[orig_scaled]crop=320:480:0:0[left_half];"
                        "[enh_scaled]crop=320:480:320:0[right_half];"
                        "[left_half][right_half]hstack=inputs=2[stacked];"
                        "[stacked]drawbox=x=319:y=0:w=2:h=ih:c=white:t=fill,"
                        "drawbox=x=5:y=5:w=80:h=8:c=red:t=fill,"
                        "drawbox=x=555:y=5:w=80:h=8:c=green:t=fill"
                    )
                    self.after(0, lambda: self._log("  Note: drawtext not available (Red=Original, Green=Deinterlaced)"))

                # Single 20-second output — labels stay the same throughout
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
                        f"Left: ORIGINAL  |  Right: DEINTERLACED"))
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
            'par_correction': True
        }
        # Clear batch processing state
        self.files_to_process = []
        self.completed_files = []
        self.failed_files = []
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

    Structure of vcg-deps-v2.zip:
        vcg-deps-v2/
          ffmpeg/    ffmpeg.exe  ffprobe.exe
          vs/        vspipe.exe  VapourSynth.dll  VSScript.dll
                     python3XX.dll  python3XX.zip  python3XX._pth
                     site-packages/  vapoursynth.pyd  havsfunc.py ...
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

        tk.Label(self, text="Downloading tools — this only happens once (~60 MB).",
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
        """Extract vcg-deps-v1.zip to DEPS_DIR."""
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

            # ZIP contains vcg-deps-v2\ as root folder — rename to _deps
            extracted_root = os.path.join(os.path.dirname(DEPS_DIR), 'vcg-deps-v2')
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

    def _run_setup(self):
        global FFMPEG_PATH, FFPROBE_PATH, VSPIPE_PATH

        self._set_status("Downloading VCG Deinterlacer tools…")
        self._log_line(f"Downloading deps package from:")
        self._log_line(f"  {DEPS_ZIP_URL}")

        tmp_zip = os.path.join(tempfile.gettempdir(), 'vcg-deps-v2.zip')
        ok = self._download(DEPS_ZIP_URL, tmp_zip)

        if not ok:
            self._log_line("")
            self._log_line("✘ Download failed.")
            self._log_line("  Please check your internet connection.")
            self._log_line("  You can also download the file manually:")
            self._log_line(f"  {DEPS_ZIP_URL}")
            self._log_line(f"  and place vcg-deps-v2.zip next to the EXE,")
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
            "2. Extract it — you should get a  vcg-deps-v2  folder.\n\n"
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
