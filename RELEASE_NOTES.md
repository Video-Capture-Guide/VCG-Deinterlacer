# VCG Deinterlacer — Release Notes

---

## Version 1.7.0 — 2026-07-04

### New: Sidebar Wizard Navigation

The horizontal breadcrumb has been replaced by a persistent **navigation sidebar** on the
left of the window, so you always know where you are in the wizard, what's done, and
what's coming next.

- The four phases — **Select File, Source, Advanced, Finalize** — are listed vertically
  with numbered pills: purple = current, green ✓ = completed, dimmed – = skipped
  (defaults in effect, e.g. after choosing *Process Now*).
- While you're inside the **Advanced** section it expands to show all of its optional
  sub-steps (Trim, Y/C Delay, Noise, Dehalo, Upscale, Color Cast, Levels, Audio,
  Watermark, Add Grain, Dithering) with per-page status: ▶ current, ✓ visited,
  ○ upcoming. When you're elsewhere it collapses to a one-line summary
  (*"11 optional steps"*).
- **Click any step you've already reached to jump straight back to it** — no more
  pressing Back repeatedly. Forward movement stays linear through the Next button.
- The Advanced group is tagged **optional**, with a hint explaining that every step in
  it can be skipped.
- Trim is hidden from the sidebar for multi-file batches (it is a single-file feature).
- The default window is now 1120×900 (minimum 980×600) to make room for the sidebar.

### New: Trim / Segment Export Page (Advanced ⓪ — single file)

Export only part of a capture, or cut unwanted sections out of it, with frame accuracy —
before any processing time is spent:

- **Output entire video (default)** — new first option so users who don't want to trim
  aren't confronted with trimming controls at all; the segment tools stay hidden unless
  Keep or Cut mode is selected.
- **Keep mode** — mark the good parts; everything else is discarded.
  **Cut mode** — mark the bad parts (static, blank tape, private moments); everything
  else is exported.
- Frame preview with a scrubber, a color-coded segment timeline, direct timecode entry
  (`H:MM:SS.frames`), and nudge buttons (±10 s / ±1 s / ±1 frame).
- Mark any number of segments; overlapping segments are merged automatically.
- Kept segments can be **joined into one output file** or exported as
  **one file per segment** (`…_part01`, `…_part02`, …).
- Audio cuts are computed from the exact source frame rate (30000/1001 NTSC, 25 PAL) so
  sound stays in sync at every splice point.

### Change: Watermark, Film Grain, and Output Dithering Are Now Separate Pages

The former combined Watermark page (watermark + "Fun Extras" grain + dithering) has been
split into three dedicated wizard pages, growing the wizard to 16 steps:

- **Watermark** (Advanced ⑧) — text or logo overlay, unchanged.
- **Add Film Grain** (Advanced ⑨) — grain-strength slider plus an explainer covering
  which filter is used (**AddGrain**, VapourSynth's `grain.Add`, a port of AviSynth's
  AddGrainC) and why grain helps: it keeps denoised footage from looking plasticky, and
  it prevents banding after YouTube's re-compression by breaking up smooth gradients.
- **Output Dithering** (Advanced ⑩) — the dithering checkbox and method dropdown moved
  from the Finalize-adjacent "Output Quality" section to their own page, now naming the
  filter used (fmtconv's `fmtc.bitdepth`).

### Fix: Film Grain Was Far Too Strong and Too Coarse

Selecting even strength 1–2 produced heavy, blotchy grain. Two bugs, both fixed:

- **Strength was ~16× too high.** The code multiplied the slider value by 256 to
  "convert 8-bit units to the 16-bit pipeline", but AddGrain already normalises `var`
  to the clip's bit depth internally — measured on a 16-bit clip: `var=1` → σ≈1.0,
  `var=4` → σ≈2.0 (8-bit equivalents), while the old `var=512` produced σ≈22.7.
  The slider value is now passed through unscaled.
- **Grain was applied before PAR correction and the NNEDI3 upscale**, so each grain
  speck was enlarged by the upscale factor (2.25× at 1440×1080) and looked large and
  smeared instead of pixel-fine. Grain is now added at the **final resolution**, after
  any upscale and immediately before output dithering, while the pipeline is still
  16-bit.

Expected feel after the fix: 1–2 ≈ barely visible fine texture, 3–4 ≈ classic subtle
film grain, 10 ≈ clearly visible (σ≈3).

---

## Version 1.6.0 — 2026-06-29

### New: 16-bit Internal Pipeline

The entire VapourSynth processing chain now runs at 16-bit integer precision. The source
is lifted to 16-bit at the start of the script (`fmtc.bitdepth`) and all subsequent
operations — QTGMC, BM3D, FineDehalo, colour cast, levels, film grain — work natively at
that depth. No intermediate round-trips to 8-bit occur.

Numeric constants in every generated Expr and Levels call have been scaled accordingly
(chroma neutral 128 → 32768; luma legal black/white 16/235 → 4096/60160; BM3D sigma
3 → 768 and 6 → 1536; FineDehalo edge thresholds scaled ×256; film grain var scaled ×256).

### New: Output Dithering via fmtconv (Fully Automatic)

The final step of every encode now dithers the 16-bit pipeline down to the codec's
native depth using **fmtconv error-diffusion dithering** (`fmtc.bitdepth`, dmode=3 —
verified against the installed mvsfunc.py). This eliminates banding in skies, fades,
and gradients that is common in tape captures.

- **ProRes HQ** outputs at **10-bit** (filling the container fully).
- All other formats (H.264, FFV1, HuffYUV, etc.) output at **8-bit**.
- A `try/except` fallback to `core.resize.Spline36` is generated so the same script
  works if fmtconv is not available.
- No new wizard step: dithering is on by default and requires no user action.

**Optional power-user control:** a new *Advanced — Output Quality* section on the
Finalize page exposes an "Output dithering (recommended)" checkbox and a dither method
dropdown (*Error diffusion* default; *Ordered / Bayer* alternative). These are hidden
from the default flow.

### New: Colorspace / Matrix Tagging

All output files are now tagged with the correct colorspace metadata, and the in-app
video scopes (Vectorscope, RGB Histogram, RGB Parade) now convert colours using the
correct matrix, so the scope display matches what the video actually looks like.

#### Source Details page — Source Color Matrix dropdown

A new **Source Color Matrix** control appears on the Source Details page (step 2), below
the existing format and field-order controls:

- **SD / VHS capture** → *BT.601 (recommended)* pre-selected automatically.
- **HD / AVCHD / HDV** → *BT.709 (recommended)* pre-selected automatically.
- Users can override, but the correct value is pre-selected and labeled in plain English.
  No video-engineering knowledge required.

#### VapourSynth script tagging

The generated `.vpy` script now calls `core.std.SetFrameProps` to set `_Matrix`,
`_Primaries`, `_Transfer`, and `_ColorRange=1` (limited) on the output clip before
encoding, so the container metadata is set by VapourSynth rather than guessed by FFmpeg.

VS matrix constants used: 1 = BT.709, 5 = BT.470BG (PAL BT.601), 6 = SMPTE 170M
(NTSC BT.601).

#### FFmpeg output tagging

All output format commands (`prores_ks`, `libx264`, `ffv1`, `huffyuv`, `utvideo`,
`lagarith`) now include `-colorspace`, `-color_primaries`, and `-color_trc` flags
derived from the selected matrix and source format (PAL vs NTSC).

#### Correct scope colors

`generate_histogram_image`, `generate_vectorscope_image`, and `generate_rgb_histogram`
now accept `color_matrix` and `video_format` parameters and pass the matching FFmpeg
colorspace flags to the scope filter chain. Previously, YUV→RGB conversion inside
FFmpeg used its default matrix (usually BT.709), causing incorrect hue on BT.601 SD
sources in the Vectorscope and RGB Parade.

---

## Version 1.5.0 — 2026-06-10

The wizard is now 13 steps: two new Advanced pages (**Dehalo** and **Watermark**) were added,
and the existing analysis pages gained quantified scores and sampling transparency.

### New: Dehalo Page with Automatic Halo Analysis (Advanced step ③)

Removes the bright ghost outlines along strong edges caused by VHS sharpening circuits and
camcorder edge enhancement.

- **Automatic analysis** samples 8 frames and measures the two-sided sharpening signature
  (bright-side overshoot + dark-side undershoot on strong edges, verified across adjacent
  rows so organic texture doesn't false-trigger). The halo score is shown as
  *% of strong edges showing ringing* with the threshold band next to the recommendation.
- **Light dehalo** removes bright halos only and protects dark edges (`darkstr=0`);
  **Strong dehalo** removes bright and dark halos with a larger radius.
- The filter is a faithful, self-contained **FineDehalo port** (edge-masked DeHalo_alpha,
  luma only) generated directly into the `.vpy` script — the bundled havsfunc removed its
  own FineDehalo, so the port uses only bundled components (std/resize, RemoveGrainVS
  Repair, and havsfunc's surviving mask utilities).
- Calibration reference: clean camcorder MPEG-2 ≈ 8 %, real VHS capture ≈ 13 %, consumer DV
  with in-camera sharpening ≈ 17 %, artificially over-sharpened control ≈ 21 %.

### New: Watermark Page (Advanced step ⑧)

Optional text or logo overlay applied at encode time, after all restoration:

- **Text watermark** — custom text (default `@VideoCaptureGuide`), position (4 corners +
  center), opacity 20–100 %, font size Small/Medium/Large. Rendered with a system
  sans-serif font (Segoe UI → Arial fallback).
- **Logo watermark** — any PNG/JPG (transparency supported), position, size 5–30 % of
  frame width, opacity.
- **✨ Fun Extras: film grain** — optional `grain.Add` overlay (strength 0–10) applied
  after denoising; useful for masking BM3D's smoothing on heavily denoised tapes.

### New: BM3D Denoising (with Automatic Fallback)

Temporal denoising now tries **BM3D** first (frequency-domain, the current community
standard for analog tape noise), then GPU-accelerated **KNLMeansCL**, then **SMDegrain**
(MVTools) — the try/except chain lives in the generated `.vpy`, so the same script works
on any deps bundle. Light = BM3D sigma 3, Heavy = BM3D sigma 6 profile "lc"; luma only.

### Improvement: Noise Analysis — Better Detection and Full Transparency

- The classifier now leads on **TOUT** (temporal outlier pixels — noise-specific, ignores
  smooth motion) with lower thresholds (1.2 / 3 / 8 %). The old thresholds missed most
  genuine VHS noise.
- The recommendation line shows the quantified score and its band, e.g.
  *"Light denoising · noise score 4.50 % — moderate 3–8 %"*. When the motion metric
  (YDIF) triggered the classification instead, the line says so explicitly.
- A **Motion index (YDIF)** debug readout was added below the noise index so expert users
  can see why the tool recommended what it did and override intelligently.

### Improvement: RGB Parade Replaces the Waveform Monitor

The Video Levels page now shows a true **RGB Parade** — R, G, and B waveform columns side
by side (the standard pro levels tool), making per-channel clipping and color casts
immediately visible. The frame scrubber regenerates the parade at any point in the video.
The Color Analysis tab was relabeled *RGB Histogram (stacked)* to distinguish the two.

### Improvement: "Where the samples come from" Notes

Every analysis page (Noise, Dehalo, Color Cast, Levels) now explains exactly where its
samples were taken — Noise/Dehalo sample evenly through the **middle 60 %** of the video
(first/last 20 % skipped to avoid leaders, static, and credits); Color/Levels sample evenly
across the **full duration** — so users can judge whether the result represents their tape.

### Improvement: Comparison Video — Two-Part Layout with Readable Labels

The 20-second comparison is now **10 s side-by-side at normal size + 10 s side-by-side at
300 % zoom** (center of the frame at 3×), labeled *Original* / *Deinterlaced* in a
mixed-case sans-serif font. Short clips automatically split their available duration in
half. Fixes in the process:

- The previous labels never actually rendered — `drawtext` was called without a font file,
  and the bundled FFmpeg's fontconfig cannot find a default font on Windows, so the text
  silently drew nothing. All drawtext calls now pass an explicit system font.
- A literal `%` in any drawtext string (including user watermark text) silently killed the
  whole label; it is now escaped correctly.
- The zoom segment changes the sample aspect ratio, which made `concat` reject the filter
  graph; SAR is now normalized after each composite.

---

## Version 1.4.1 — 2026-06-07

### New: .MOD File Support (HDD Camera)

VCG Deinterlacer now accepts `.mod` files produced by Panasonic, JVC, and Canon HDD and
SD-card camcorders (e.g. Panasonic SDR series, JVC Everio). These files are MPEG-2 Program
Stream with a renamed extension and are processed identically to `.mpg` sources.

Supported input methods: Browse dialog, drag-and-drop (single file and batch).

### Fix: 16:9 Widescreen Sources Output Correct Square-Pixel Resolution

Sources with a 16:9 pixel aspect ratio (SAR `64:45` for PAL, `32:27` for NTSC — used by
HDD cameras, widescreen DVD, and some MPEG-2 captures) were previously scaled to the 4:3
square-pixel dimensions (768×576 PAL, 640×480 NTSC), producing a horizontally squished image.

The PAR correction step now detects the source SAR and outputs the correct widescreen
square-pixel resolution:

| Source | SAR | Correct Output |
|--------|-----|----------------|
| PAL 16:9 | 64:45 | **1024×576** |
| NTSC 16:9 | 32:27 | **854×480** |
| PAL 4:3 | 16:15 / 59:54 | 768×576 (unchanged) |
| NTSC 4:3 | 8:9 / 10:11 | 640×480 (unchanged) |

### Improvement: Crop Options Page — Source-Aware Recommendation

The Crop Options page now displays a **Suggested** banner identifying the recommended
option for the detected source type:

- **SD analog capture** (VHS, Hi8, S-VHS, Video8) → Option 1 — BT.601 Active Picture
- **DV / MiniDV** → Option 4 — No Crop
- **DVD / MPEG-2 / HDD camera** → Option 4 — No Crop
- **16:9 widescreen sources** → Option 4 — No Crop (with a note that Options 1 and 2
  apply 4:3 SAR corrections incompatible with 16:9 content)

The default selection now also follows this logic: DVD, MPEG-2, and widescreen sources
automatically pre-select Option 4 instead of Option 1.

The Option 4 description bracket note has been updated from *(default for DV/MiniDV)* to
*(default for DV/MiniDV/DVD)* to reflect this.

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
