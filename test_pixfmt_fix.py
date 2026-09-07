# -*- coding: utf-8 -*-
"""Smoke test for the 10-bit pix_fmt fix (classify_source + generate_vpy_script).

Creates synthetic 10-bit and 8-bit test clips with the bundled ffmpeg, checks
classification flags, checks generated-script structure, then executes the
full generated IVTC pipeline in-process (pip VapourSynth R74 includes vivtc;
fmtconv/lsmas are LoadPlugin()ed from the real plugins64 by the script).
"""
import importlib.util
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DEPS = os.path.abspath(os.path.join(ROOT, '..', '_deps'))
FFMPEG = os.path.join(DEPS, 'ffmpeg', 'ffmpeg.exe')
FFPROBE = os.path.join(DEPS, 'ffmpeg', 'ffprobe.exe')
OUT = os.path.join(ROOT, '_pixfmt_test')
os.makedirs(OUT, exist_ok=True)

failures = []


def check(name, cond, detail=''):
    status = 'PASS' if cond else 'FAIL'
    print(f'[{status}] {name}' + (f'  ({detail})' if detail and not cond else ''))
    if not cond:
        failures.append(name)


# ── Import the app module (safe: __main__ guard) and point it at real deps ──
spec = importlib.util.spec_from_file_location(
    'vcg', os.path.join(ROOT, 'vcg_deinterlacer_v122.py'))
vcg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vcg)
vcg.FFPROBE_PATH = FFPROBE
vcg.FFMPEG_PATH = FFMPEG
vcg.VS_DEPS_DIR = os.path.join(DEPS, 'vs')

# ── Create test clips (PAL 720x576 25fps) ───────────────────────────────────
clip10 = os.path.join(OUT, 'test_10bit.mkv')
clip8 = os.path.join(OUT, 'test_8bit.mkv')
for path, pixfmt in ((clip10, 'yuv420p10le'), (clip8, 'yuv420p')):
    if not os.path.exists(path):
        r = subprocess.run(
            [FFMPEG, '-y', '-f', 'lavfi', '-i', 'testsrc2=size=720x576:rate=25',
             '-frames:v', '50', '-c:v', 'libx264', '-pix_fmt', pixfmt, path],
            capture_output=True, text=True)
        if r.returncode != 0:
            # 8-bit-only x264 build fallback: FFV1 supports 10-bit everywhere
            r = subprocess.run(
                [FFMPEG, '-y', '-f', 'lavfi', '-i', 'testsrc2=size=720x576:rate=25',
                 '-frames:v', '50', '-c:v', 'ffv1', '-pix_fmt', pixfmt, path],
                capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-2000:]

# ── Test 1: classification flags ─────────────────────────────────────────────
sc10 = vcg.classify_source(clip10)
sc8 = vcg.classify_source(clip8)
check('10-bit pix_fmt detected', sc10['pix_fmt'] == 'yuv420p10le', sc10['pix_fmt'])
check('10-bit flagged for conversion', sc10['needs_pixfmt_conversion'] is True)
check('8-bit pix_fmt detected', sc8['pix_fmt'] == 'yuv420p', sc8['pix_fmt'])
check('8-bit NOT flagged', sc8['needs_pixfmt_conversion'] is False)

# ── Test 2: generated script structure (IVTC mode, DVD rip scenario) ────────
def make_cfg(path, sc):
    return {
        'input_path': path,
        'format': 'pal',
        'capture_method': 'dvd',
        'field_order': 'tff',
        'ivtc_mode': True,
        'noise_level': 'none',
        'dropout_removal': False,
        'color_correction': False,
        'levels_adjustment': False,
        'upscale_enabled': False,
        'output_format': 'h264',
        'source_classification': sc,
    }

script10 = vcg.generate_vpy_script(make_cfg(clip10, sc10))
script8 = vcg.generate_vpy_script(make_cfg(clip8, sc8))

conv_line = 'clip = core.resize.Bicubic(clip, format=vs.YUV420P8)'
check('conversion present for 10-bit', conv_line in script10)
check('conversion absent for 8-bit', conv_line not in script8)
check('conversion before 16-bit lift',
      conv_line in script10 and
      script10.index(conv_line) < script10.index('core.fmtc.bitdepth(clip, bits=16)'))
check('VFM fed 8-bit copy via clip2',
      '_vfm8 = core.fmtc.bitdepth(clip, bits=8)' in script10 and
      'core.vivtc.VFM(_vfm8, order=1, clip2=clip)' in script10)
nn = 'hasattr(core, "nnedi3")'
check('conversion before nnedi3 block (if any)',
      nn not in script10 or script10.index(conv_line) < script10.index(nn))

# ── Test 3: run the full generated pipeline in-process ──────────────────────
# The bundled vspipe.exe fails to initialize on this dev machine, but the
# pip-installed VapourSynth R74 works in-process and includes vivtc, and the
# generated script explicitly LoadPlugin()s fmtconv/lsmas from the real
# plugins64 — so the whole IVTC pipeline can be executed for real.
import vapoursynth as vs

# 3a. Reproduce the original bug: VFM must reject a 16-bit clip (this is the
# crash users hit, since v122 lifts to 16-bit before IVTC).
blank16 = vs.core.std.BlankClip(format=vs.YUV420P16, width=720, height=576, length=10)
try:
    vs.core.vivtc.VFM(blank16, order=1)
    check('VFM rejects 16-bit input (bug reproduced)', False, 'VFM accepted P16?!')
except vs.Error as e:
    check('VFM rejects 16-bit input (bug reproduced)', 'must be constant format' in str(e))

# 3b. Execute the fixed generated scripts and render frames through VFM.
for name, script in (('10bit', script10), ('8bit', script8)):
    ns = {}
    try:
        exec(compile(script, f'gen_{name}.vpy', 'exec'), ns)
        out = ns['clip']
        for i in range(5):
            out.get_frame(i)
        check(f'full IVTC pipeline runs ({name})', True)
        check(f'output is 8-bit YUV420 ({name})', out.format.id == vs.YUV420P8,
              out.format.name)
        check(f'VFM input was YUV420P8 ({name})',
              ns['_vfm8'].format.id == vs.YUV420P8, ns['_vfm8'].format.name)
    except Exception as e:
        check(f'full IVTC pipeline runs ({name})', False, repr(e)[:800])

print()
print('FAILED: ' + ', '.join(failures) if failures else 'ALL TESTS PASSED')
sys.exit(1 if failures else 0)
