# -*- coding: utf-8 -*-
"""Off-screen GUI test for the 1.8.0 Source Details page states.

Renders the SD and HD Source Details pages with a pre-seeded telecine result
and checks that:
  * Progressive sits below TFF and BFF in Field Order,
  * Frame Rate Mode is ghosted (and says why) on a film source and on a
    progressive source, and live otherwise,
  * the manual override is offered when nothing was detected, and the two
    options are shown straight away when film was detected,
  * batch mode still offers the override.

Run:  python test_gui_ivtc_states.py
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


spec = importlib.util.spec_from_file_location(
    'vcg', _newest_source(ROOT))
vcg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vcg)

failures = []


def check(name, cond, detail=''):
    print('[%s] %s%s' % ('PASS' if cond else 'FAIL', name,
                         '' if cond else '  <- ' + str(detail)))
    if not cond:
        failures.append(name)


def texts(widget, acc=None):
    """Every piece of visible text on the page — Label text plus the text a
    ModernButton draws on its canvas (which is an attribute, not an option)."""
    acc = [] if acc is None else acc
    try:
        acc.append(str(widget.cget('text')))
    except Exception:
        pass
    if isinstance(widget, vcg.ModernButton):
        acc.append(str(widget.text))
    for ch in widget.winfo_children():
        texts(ch, acc)
    return acc


def button_labels(widget, acc=None):
    acc = [] if acc is None else acc
    if isinstance(widget, vcg.ModernButton):
        acc.append(str(widget.text))
    for ch in widget.winfo_children():
        button_labels(ch, acc)
    return acc


def radios(widget, acc=None):
    acc = [] if acc is None else acc
    if isinstance(widget, vcg.ModernRadioButton):
        acc.append(widget)
    for ch in widget.winfo_children():
        radios(ch, acc)
    return acc


SC_SD = {'source_class': 'sd', 'display_name': 'SD Interlaced', 'codec': 'dvvideo',
         'width': 720, 'height': 480, 'fps': 29.97, 'field_order': 'tff',
         'par_needed': False, 'pix_fmt': 'yuv420p',
         'needs_pixfmt_conversion': False}
SC_HD = dict(SC_SD, source_class='hdv', width=1440, height=1080,
             display_name='HDV (1080i)')
# A progressive 1080p60 phone clip, as classify_source() reports it.
SC_HD_PROG = {'source_class': 'avchd', 'display_name': 'HD Progressive (1920×1080p)',
              'codec': 'h264', 'width': 1920, 'height': 1080, 'fps': 60.0,
              'field_order': 'progressive', 'progressive': True,
              'par_needed': False, 'pix_fmt': 'yuv420p',
              'needs_pixfmt_conversion': False}

FILM = {'detected': True, 'pattern': '3:2', 'confidence': 'high',
        'target_fps': 24000 / 1001, 'dv_bypass': False,
        'progressive_source': False, 'windows': 7, 'film_windows': 6,
        'prog_ratio': 0.42, 'user_override': False,
        'description': '3:2 NTSC pulldown detected in 6 of 7 sampled segments.'}
VIDEO = {'detected': False, 'pattern': None, 'confidence': None,
         'target_fps': None, 'dv_bypass': False, 'progressive_source': False,
         'windows': 7, 'film_windows': 0, 'prog_ratio': 0.12,
         'user_override': False,
         'description': 'No telecine pattern detected (7 segments sampled).'}

wiz = vcg.RestorationWizard()
wiz.withdraw()


def render(sc, files, ivtc_result, field_order='tff', **extra):
    wiz.config_data.clear()
    wiz.config_data.update({
        'source_classification': sc,
        'input_files': files,
        'input_path': files[0],
        'format': 'ntsc',
        'capture_method': 'dv',
        'field_order': field_order,
        # Pretend the user already settled field order so background detection
        # cannot fight the test, and a stored scan so none is launched.
        'field_order_user_set': True,
    })
    if ivtc_result is not None:
        wiz.config_data['ivtc_result'] = ivtc_result
    wiz.config_data.update(extra)
    wiz._show_step(2)
    wiz.update_idletasks()
    wiz.update()          # let the after(0,…) result render
    wiz.update_idletasks()


def frame_rate_radios():
    return [rb for rb in getattr(wiz, '_fr_radios', []) if rb.winfo_exists()]


# ── Field Order offers Progressive, last ────────────────────────────────────
print('\n-- Progressive option --')
for label, sc in (('SD', SC_SD), ('HD', SC_HD)):
    render(sc, ['dummy.avi'], VIDEO)
    vals = [rb.value for rb in radios(wiz.page_container)
            if rb.variable is wiz.field_var]
    check('%s page: Progressive sits below TFF and BFF' % label,
          vals[:3] == ['tff', 'bff', 'progressive'], vals)

# ── Frame Rate Mode live on an ordinary interlaced video source ─────────────
print('\n-- Frame Rate Mode, interlaced video source --')
render(SC_SD, ['dummy.avi'], VIDEO)
frs = frame_rate_radios()
check('two frame-rate options exist', len(frs) == 2, len(frs))
check('they are selectable', all(rb._enabled for rb in frs))
check('badge recommends double-rate',
      'Double-rate recommended' in wiz._fr_badge_lbl.cget('text'),
      wiz._fr_badge_lbl.cget('text'))
check('no "not applicable" note is shown',
      not wiz._fr_note_lbl.winfo_ismapped())

# ── Frame Rate Mode ghosted on a detected film source ──────────────────────
print('\n-- Frame Rate Mode, film source (the reported bug) --')
render(SC_SD, ['dummy.avi'], FILM)
check('inverse telecine is selected by default', wiz.config_data['ivtc_mode'] is True,
      wiz.config_data.get('ivtc_mode'))
frs = frame_rate_radios()
check('frame-rate options are ghosted', frs and not any(rb._enabled for rb in frs))
check('badge says not applicable',
      'Not applicable' in wiz._fr_badge_lbl.cget('text'),
      wiz._fr_badge_lbl.cget('text'))
check('the reason names the film frame rate',
      '23.976' in wiz._fr_note_lbl.cget('text'), wiz._fr_note_lbl.cget('text'))
page = texts(wiz.page_container)
check('both film/video options are shown straight away',
      any('Apply Inverse Telecine' in t for t in page)
      and any('Use Standard Deinterlacing' in t for t in page))
check('output frame rate would be the film rate',
      vcg._output_frame_rate(wiz.config_data) == '24000/1001',
      vcg._output_frame_rate(wiz.config_data))

# Choosing "Use Standard Deinterlacing" must bring the chooser back.
wiz._ivtc_var.set(False)
wiz.update_idletasks()
check('overriding film → video re-enables Frame Rate Mode',
      all(rb._enabled for rb in frame_rate_radios()))
check('the override is recorded', wiz.config_data.get('ivtc_user_override') is True)

# ── Override offered when nothing was detected ─────────────────────────────
print('\n-- override on a video verdict --')
render(SC_SD, ['dummy.avi'], VIDEO)
btns = button_labels(wiz.page_container)
check('an Override detection button is offered',
      any('Override detection' in t for t in btns), btns)
check('a Re-scan button is offered',
      any('Re-scan' in t for t in btns), btns)
check('standard deinterlacing is the default',
      wiz.config_data['ivtc_mode'] is False, wiz.config_data.get('ivtc_mode'))
check('the film/video radios are hidden until the override is used',
      not any(rb.winfo_ismapped() for rb in wiz._ivtc_radios))

# Forcing film through the override must ghost Frame Rate Mode.
wiz._ivtc_var.set(True)
wiz.update_idletasks()
check('forcing IVTC by hand ghosts Frame Rate Mode',
      not any(rb._enabled for rb in frame_rate_radios()))
check('forcing IVTC by hand is recorded as an override',
      wiz.config_data.get('ivtc_user_override') is True)

# ── A progressive field order switches everything off ──────────────────────
print('\n-- progressive field order --')
render(SC_SD, ['dummy.avi'], VIDEO, field_order='progressive')
check('frame-rate options are ghosted on a progressive source',
      not any(rb._enabled for rb in frame_rate_radios()))
check('the reason says the source is already progressive',
      'already progressive' in wiz._fr_note_lbl.cget('text'),
      wiz._fr_note_lbl.cget('text'))
check('the film/video choice is ghosted too',
      not any(rb._enabled for rb in wiz._ivtc_radios))

# Switching back to TFF restores both.
wiz.field_var.set('tff')
wiz.update_idletasks()
check('switching back to TFF restores Frame Rate Mode',
      all(rb._enabled for rb in frame_rate_radios()))
check('switching back to TFF restores the film/video choice',
      all(rb._enabled for rb in wiz._ivtc_radios))

# ── A progressive HD source must not be described as interlaced anywhere ───
print('\n-- progressive HD source (1080p60) --')
render(SC_HD_PROG, ['clip.MOV'], None, field_order='progressive')
page = texts(wiz.page_container)
check('section 1 reports the source as 1080p',
      any('HD Progressive (1920×1080p)' in t for t in page),
      [t for t in page if '1080' in t][:4])
check('nothing on the page claims the source is 1080i',
      not any('1080i' in t for t in page),
      [t for t in page if '1080i' in t])
check('the page subtitle says progressive',
      any('progressive HD video source' in t for t in page))
check('the field-order note does not assert TFF',
      not any('universally Top Field First' in t for t in page))
check('Progressive is the selected field order',
      wiz.field_var.get() == 'progressive', wiz.field_var.get())
check('60 fps is recognised as the NTSC family',
      wiz.config_data['format'] == 'ntsc', wiz.config_data.get('format'))
check('frame-rate options are ghosted',
      not any(rb._enabled for rb in frame_rate_radios()))
check('the pipeline skips deinterlacing for it',
      'QTGMC(' not in vcg.generate_vpy_script(dict(
          wiz.config_data, input_path='clip.MOV', output_path='out.mov')))

# ── Batch mode keeps the override ──────────────────────────────────────────
print('\n-- batch mode --')
render(SC_SD, ['a.avi', 'b.avi'], None)
btns = button_labels(wiz.page_container)
check('batch mode still offers the override',
      any('Override detection' in t for t in btns), btns)
check('batch mode does not offer a per-file re-scan',
      not any('Re-scan' in t for t in btns), btns)
check('batch mode defaults to standard deinterlacing',
      wiz.config_data['ivtc_mode'] is False, wiz.config_data.get('ivtc_mode'))

wiz.destroy()
print('\n' + ('FAILED: ' + ', '.join(failures) if failures
              else 'ALL GUI IVTC STATE TESTS PASSED'))
sys.exit(1 if failures else 0)
