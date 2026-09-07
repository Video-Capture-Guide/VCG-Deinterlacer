# -*- coding: utf-8 -*-
"""Off-screen GUI smoke test: render the Source Details pages (SD + HD) with
needs_pixfmt_conversion set and confirm the one-line notice appears."""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    'vcg', os.path.join(ROOT, 'vcg_deinterlacer_v123.py'))
vcg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vcg)

NOTICE = 'Your source is 10-bit or non-standard format'


def collect_texts(widget, acc):
    try:
        acc.append(str(widget.cget('text')))
    except Exception:
        pass
    for ch in widget.winfo_children():
        collect_texts(ch, acc)


failures = []
wiz = vcg.RestorationWizard()
wiz.withdraw()

sc_flagged_sd = {'source_class': 'sd', 'display_name': 'SD Interlaced',
                 'codec': 'h264', 'width': 720, 'height': 576, 'fps': 25.0,
                 'field_order': 'tff', 'par_needed': False,
                 'pix_fmt': 'yuv420p10le', 'needs_pixfmt_conversion': True}
sc_clean_sd = dict(sc_flagged_sd, pix_fmt='yuv420p', needs_pixfmt_conversion=False)
sc_flagged_hd = dict(sc_flagged_sd, source_class='hdv', width=1440, height=1080,
                     display_name='HDV (1080i)')

cases = [
    ('SD flagged shows notice', sc_flagged_sd, True),
    ('SD clean hides notice', sc_clean_sd, False),
    ('HD flagged shows notice', sc_flagged_hd, True),
]
for name, sc, expect in cases:
    wiz.config_data['source_classification'] = sc
    wiz.config_data['input_files'] = ['dummy.mkv']
    wiz._show_step(2)
    wiz.update_idletasks()
    texts = []
    collect_texts(wiz.page_container, texts)
    shown = any(NOTICE in t for t in texts)
    status = 'PASS' if shown == expect else 'FAIL'
    print(f'[{status}] {name}')
    if shown != expect:
        failures.append(name)

wiz.destroy()
print('FAILED: ' + ', '.join(failures) if failures else 'GUI SMOKE PASSED')
sys.exit(1 if failures else 0)
