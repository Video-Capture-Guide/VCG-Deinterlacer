# -*- coding: utf-8 -*-
"""Unit tests for the 1.8.0 telecine detector and the progressive/IVTC pipeline.

No FFmpeg is needed: ``_idet_counts`` is stubbed with scripted per-window frame
counts, so the sampling plan and the majority-vote verdict are tested directly.

Run:  python test_telecine_detection.py
"""
import importlib.util
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


SRC = _newest_source(ROOT)

spec = importlib.util.spec_from_file_location('vcg', SRC)
vcg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vcg)

failures = []


def check(name, cond, detail=''):
    print('[%s] %s%s' % ('PASS' if cond else 'FAIL', name,
                         '' if cond else '  <- ' + str(detail)))
    if not cond:
        failures.append(name)


def idet(tff, bff, prog, rep=0):
    """One window's worth of idet output, in the shape _idet_counts returns."""
    return {'tff': tff, 'bff': bff, 'prog': prog, 'rep': rep,
            'rep_total': tff + bff + prog}


def with_windows(counts, duration=3600.0, fps=30000 / 1001.0, **kw):
    """Run detect_telecine with idet results supplied per sampled window.

    ``counts`` is a list of idet() dicts (or None for a window that fails to
    decode); the last entry is reused if the sampling plan asks for more
    windows than were supplied.
    """
    calls = []

    def fake_idet(filepath, start_seconds, frames, timeout=45):
        calls.append(start_seconds)
        return counts[min(len(calls) - 1, len(counts) - 1)]

    real = vcg._idet_counts
    vcg._idet_counts = fake_idet
    try:
        res = vcg.detect_telecine('dummy.avi', kw.pop('video_format', 'ntsc'),
                                  duration=duration, fps=fps, **kw)
    finally:
        vcg._idet_counts = real
    return res, calls


# ── Sampling plan ───────────────────────────────────────────────────────────
print('\n-- sampling plan --')

plan = vcg._telecine_sample_plan(0, 29.97)
check('unknown duration falls back to one pass from the top',
      plan == [(0.0, 500)], plan)

plan = vcg._telecine_sample_plan(12.0, 29.97)
check('very short file uses one pass', plan == [(0.0, 500)], plan)

plan = vcg._telecine_sample_plan(5400.0, 29.97)   # 90-minute feature
check('feature-length file samples 7 windows', len(plan) == 7, plan)
check('first window skips the opening logo (>60 s in)',
      plan[0][0] >= 60.0, plan[0])
check('last window reaches the end of the file',
      plan[-1][0] > 5400 * 0.75, plan[-1])
check('every window fits inside the file',
      all(t + w / 29.97 <= 5400 for t, w in plan), plan)

plan = vcg._telecine_sample_plan(300.0, 25.0)
check('5-minute clip samples 5 windows', len(plan) == 5, plan)
plan = vcg._telecine_sample_plan(90.0, 25.0)
check('90-second clip samples 3 windows', len(plan) == 3, plan)


# ── The reported bug: a CGI logo at the head of a film transfer ─────────────
print('\n-- film source behind a video-rate logo --')

# 17% progressive and no repeated fields — reads as interlaced video.
LOGO_VIDEO = idet(200, 0, 40)
# 50% progressive plus a 2-in-5 repeated-field cadence — 3:2 pulldown.
FILM_32    = idet(120, 0, 120, rep=96)
# Busy film footage: idet classifies every frame as interlaced, so only the
# repeated-field cadence gives the telecine away (observed on real clips).
FILM_BUSY  = idet(240, 0, 0, rep=96)

res, calls = with_windows([LOGO_VIDEO] + [FILM_32] * 6)
check('film detected despite a video-rate opening logo', res['detected'], res)
check('pattern is 3:2', res['pattern'] == '3:2', res['pattern'])
check('target frame rate is 23.976',
      abs(res['target_fps'] - 24000 / 1001) < 1e-9, res['target_fps'])
check('majority of windows voted film',
      res['film_windows'] == 6 and res['windows'] == 7, res)
check('description names the segment vote',
      '6 of 7 sampled segments' in res['description'], res['description'])
check('the opening seconds are not the only thing sampled',
      len(calls) == 7 and calls[0] >= 60, calls)


# ── The reported bug: DV FourCC must not veto IVTC ─────────────────────────
print('\n-- DV-codec capture of a film source --')

res, _ = with_windows([FILM_32] * 7, capture_method='dv')
check('film in a DV file is still detected', res['detected'], res)
check('dv_bypass is gone', res['dv_bypass'] is False, res)

res, _ = with_windows([LOGO_VIDEO] * 7, capture_method='dv')
check('a genuine DV camcorder tape still reads as video',
      not res['detected'], res)


# ── Repeated fields: the mechanical 3:2 marker ─────────────────────────────
print('\n-- repeated-field route --')

res, _ = with_windows([FILM_BUSY] * 7)
check('busy film is detected from the repeated-field cadence alone',
      res['detected'] and res['pattern'] == '3:2', res)
check('a clear repeated-field ratio is high confidence',
      res['confidence'] == 'high', res['confidence'])
check('repeated-field ratio is reported',
      abs(res['rep_ratio'] - 0.4) < 0.01, res['rep_ratio'])
check('the description names the pulldown signature',
      'repeated field' in res['description'], res['description'])

res, _ = with_windows([FILM_BUSY] * 7, video_format='pal', fps=25.0)
check('PAL ignores repeated fields (a 2:2 transfer repeats none)',
      not res['detected'], res)

res, _ = with_windows([idet(240, 0, 0, rep=8)] * 7)
check('a trickle of repeated fields is not telecine',
      not res['detected'], res)

# ── No false positives ─────────────────────────────────────────────────────
print('\n-- negative cases --')

res, _ = with_windows([idet(250, 0, 10)] * 7)
check('ordinary NTSC interlaced video is not flagged', not res['detected'], res)

res, _ = with_windows([FILM_32] + [idet(250, 0, 10)] * 6)
check('one film-looking scene in a video source is not enough',
      not res['detected'], res)
check('near-miss explains itself and points at the override',
      'Override detection' in res['description'], res['description'])

# PAL 50i with low-motion scenes reads ~50% progressive to idet.
res, _ = with_windows([idet(120, 0, 120)] * 7, video_format='pal', fps=25.0)
check('PAL 50i video with static shots is not flagged as 2:2',
      not res['detected'], res)

res, _ = with_windows([idet(20, 0, 220)] * 7, video_format='pal', fps=25.0)
check('genuine PAL 2:2 film transfer is detected',
      res['detected'] and res['pattern'] == '2:2', res)

res, _ = with_windows([idet(0, 0, 240)] * 7)
check('an already-progressive file is reported as progressive, not telecine',
      res['progressive_source'] and not res['detected'], res)
check('progressive description points at the Progressive field order',
      'Progressive' in res['description'], res['description'])

res, _ = with_windows([None] * 7)
check('all windows failing to decode yields no detection',
      not res['detected'] and res['windows'] == 0, res)


# ── Time budget ────────────────────────────────────────────────────────────
print('\n-- time budget --')
res, calls = with_windows([FILM_32] * 7, time_budget=-1.0)
check('an exhausted time budget stops after the first window',
      len(calls) == 1 and res['windows'] == 1, (len(calls), res['windows']))


# ── Pipeline: IVTC on DV, and progressive skipping deinterlacing ───────────
print('\n-- generated pipeline --')

BASE = {
    'format': 'ntsc', 'field_order': 'tff', 'capture_method': 'dv',
    'crop_preset': 'none', 'color_matrix': 'bt601',
    'input_path': 'in.avi', 'output_path': 'out.mov',
    'source_classification': {'source_class': 'sd'},
}


def script_for(**over):
    cfg = dict(BASE)
    cfg.update(over)
    return vcg.generate_vpy_script(cfg)


sc = script_for(ivtc_mode=True)
check('IVTC is applied to a DV-codec film source', 'vivtc.VFM' in sc, sc[:200])
check('VDecimate drops the pulldown frames for NTSC', 'vivtc.VDecimate' in sc)
check('QTGMC is not also run', 'QTGMC(' not in sc)
check('output frame rate is the film rate',
      vcg._output_frame_rate(dict(BASE, ivtc_mode=True)) == '24000/1001',
      vcg._output_frame_rate(dict(BASE, ivtc_mode=True)))

sc = script_for(ivtc_mode=False)
check('without IVTC a DV source is deinterlaced with QTGMC', 'QTGMC(' in sc)

sc = script_for(field_order='progressive', ivtc_mode=True, noise_level='moderate')
check('progressive source skips deinterlacing', 'QTGMC(' not in sc)
check('progressive source skips IVTC too', 'vivtc.VFM' not in sc)
check('progressive source still gets the rest of the restoration',
      'SMDegrain' in sc or 'Degrain' in sc or 'denoise' in sc.lower(), sc[-600:])
check('progressive output keeps the source frame rate',
      vcg._output_frame_rate(dict(BASE, field_order='progressive')) == '30000/1001')

print('\n' + ('FAILED: ' + ', '.join(failures) if failures
              else 'ALL TELECINE TESTS PASSED'))
sys.exit(1 if failures else 0)
