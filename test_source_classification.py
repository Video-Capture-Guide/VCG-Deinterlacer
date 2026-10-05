# -*- coding: utf-8 -*-
"""Unit tests for classify_source() — in particular that a container flagged
Progressive is never labelled or defaulted as interlaced.

No FFmpeg is needed: ``run_hidden`` is stubbed with a canned ffprobe payload.

Run:  python test_source_classification.py
"""
import importlib.util
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def _newest_source(root):
    """Highest-numbered vcg_deinterlacer_vNNN.py in `root`.

    The version lives in the filename, so pin to the newest rather than a
    hard-coded one that goes stale at every release.
    """
    best = None
    for name in os.listdir(root):
        m = re.fullmatch(r'vcg_deinterlacer_v(\d+)\.py', name)
        if m and (best is None or int(m.group(1)) > best[0]):
            best = (int(m.group(1)), name)
    if best is None:
        raise SystemExit('no vcg_deinterlacer_vNNN.py found in ' + root)
    return os.path.join(root, best[1])


spec = importlib.util.spec_from_file_location('vcg', _newest_source(ROOT))
vcg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vcg)

failures = []


def check(name, cond, detail=''):
    print('[%s] %s%s' % ('PASS' if cond else 'FAIL', name,
                         '' if cond else '  <- ' + str(detail)))
    if not cond:
        failures.append(name)


class _Probe:
    def __init__(self, stdout):
        self.returncode = 0
        self.stdout = stdout
        self.stderr = ''


def classify(**stream):
    """Run classify_source() against a canned ffprobe video stream."""
    s = {'codec_name': 'h264', 'width': 1920, 'height': 1080,
         'r_frame_rate': '60/1', 'pix_fmt': 'yuv420p'}
    s.update(stream)
    payload = json.dumps({'streams': [s]})
    real = vcg.run_hidden
    vcg.run_hidden = lambda cmd, **kw: _Probe(payload)
    try:
        return vcg.classify_source('dummy.mov')
    finally:
        vcg.run_hidden = real


# ── The reported bug: a 1080p60 phone clip called "1920x1080i" ──────────────
print('\n-- progressive 1080p source --')

r = classify(field_order='progressive')
check('field order comes back progressive, not forced TFF',
      r['field_order'] == 'progressive', r['field_order'])
check('the progressive flag is set', r['progressive'] is True, r)
check('the display name says 1080p, not 1080i',
      r['display_name'] == 'HD Progressive (1920×1080p)', r['display_name'])
check('nothing in the display name claims interlaced',
      'i)' not in r['display_name'] and 'AVCHD' not in r['display_name'],
      r['display_name'])
check('it still routes to the HD page', r['source_class'] == 'avchd',
      r['source_class'])
check('square-pixel 1920 wide needs no PAR fix', r['par_needed'] is False)

# Anamorphic progressive (1440 wide) keeps the PAR correction.
r = classify(field_order='progressive', width=1440)
check('anamorphic progressive is named 1080p and keeps PAR correction',
      r['display_name'] == 'HD Progressive (1440×1080p anamorphic)'
      and r['par_needed'] is True, r)

# ── Interlaced sources are unchanged ───────────────────────────────────────
print('\n-- interlaced sources unchanged --')

r = classify(field_order='tt')
check('TFF AVCHD keeps its name and field order',
      r['display_name'] == 'AVCHD / MTS (1920×1080i)' and r['field_order'] == 'tff', r)
check('TFF AVCHD is not flagged progressive', r['progressive'] is False)

r = classify(field_order='bb', width=1440)
check('BFF anamorphic AVCHD keeps its name and field order',
      r['display_name'] == 'AVCHD / MTS (1440×1080i anamorphic)'
      and r['field_order'] == 'bff' and r['par_needed'] is True, r)

r = classify()          # no field_order key at all
check('an absent field-order flag still defaults to TFF for HD',
      r['field_order'] == 'tff' and r['display_name'] == 'AVCHD / MTS (1920×1080i)', r)

r = classify(codec_name='mpeg2video', width=1440, r_frame_rate='30000/1001')
check('HDV stays 1080i', r['source_class'] == 'hdv'
      and r['display_name'] == 'HDV (1080i)', r)
r = classify(codec_name='mpeg2video', width=1440, field_order='progressive')
check('progressive HDV is named 1080p', r['display_name'] == 'HDV (1080p)', r)

# ── SD ─────────────────────────────────────────────────────────────────────
print('\n-- SD sources --')

r = classify(codec_name='dvvideo', width=720, height=480,
             r_frame_rate='30000/1001', field_order='bb', pix_fmt='yuv411p')
check('interlaced SD is "SD Interlaced"',
      r['source_class'] == 'sd' and r['display_name'] == 'SD Interlaced', r)

r = classify(codec_name='h264', width=720, height=480,
             r_frame_rate='30000/1001', field_order='progressive')
check('progressive SD is "SD Progressive"',
      r['source_class'] == 'sd' and r['display_name'] == 'SD Progressive'
      and r['field_order'] == 'progressive', r)

# ── 10-bit flagging must survive all of this ───────────────────────────────
print('\n-- pix_fmt flagging --')

r = classify(field_order='progressive', pix_fmt='yuv420p10le')
check('10-bit progressive is still flagged for conversion',
      r['needs_pixfmt_conversion'] is True and r['progressive'] is True, r)
r = classify(field_order='progressive')
check('8-bit progressive is not flagged',
      r['needs_pixfmt_conversion'] is False)

print('\n' + ('FAILED: ' + ', '.join(failures) if failures
              else 'ALL SOURCE CLASSIFICATION TESTS PASSED'))
sys.exit(1 if failures else 0)
