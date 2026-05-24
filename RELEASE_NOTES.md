# VCG Deinterlacer — Release Notes

---

## Version 1.4.0 — 2026-05-23

### Bug Fix: Telecine Override Options Not Appearing

When the app detected a 3:2 pulldown (telecine) pattern on the Source Details page, the
"How would you like to process this content?" card — which lets you choose between
**Apply Inverse Telecine** and **Use Standard Deinterlacing** — was silently not rendered.
The orange alert card appeared correctly, but no radio buttons followed it.

**Root cause:** The heading label inside the choice card was constructed with `pady=(10, 6)`
as a widget option. Tkinter's `Label` widget requires a plain integer for internal padding;
a tuple is only valid inside a `.pack()` call. Tkinter raised a `TclError` internally, its
callback handler swallowed it silently, and execution stopped before the radio buttons were
built.

**Fix:** Moved the tuple padding from the Label constructor into `.pack(pady=(10, 6))` where
it is valid. Both radio buttons now render correctly whenever telecine is detected.

### Improvement: Auto-Scroll to Telecine Choice Card

The IVTC detection runs asynchronously (~600 ms after the Source Details page loads). By the
time the result arrives, the choice card is appended below the visible area of the scrollable
page. The page now automatically scrolls to the bottom when a telecine pattern is detected,
bringing the choice card into view without the user needing to scroll manually.

### Change: Output File Suffix Shortened

Output files are now suffixed `_VCGD_01`, `_VCGD_02`, etc.
Previously the suffix was `_VCG-Deinterlacer_01`, which produced very long filenames.

**Before:** `2003-02-25 Reitmans Fashion Show_VCG-Deinterlacer_01.mov`
**After:**  `2003-02-25 Reitmans Fashion Show_VCGD_01.mov`

The `.vpy` VapourSynth script generated alongside the output uses the same suffix.

---

## Version 1.3.0 — 2026-05-18

Initial public build with the following features:

- QTGMC deinterlacing via VapourSynth for SD, AVCHD, and HDV sources
- Automatic field order detection (TFF/BFF) via FFmpeg idet
- Telecine / 3:2 pulldown detection for DVD/MPEG-2 sources with vivtc IVTC option
- Y/C delay (chroma horizontal shift) correction per file
- Upscaling via nnedi3 (960×720 NTSC / 1024×768 PAL)
- Output formats: ProRes 422 HQ, H.264, FFV1, HuffYUV
- Diagnostic log option
- Multi-file batch processing
- Drag-and-drop file loading
- Visual field-order comparison tool
- Portable VapourSynth dependency bundle
