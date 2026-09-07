# VCG Deinterlacer — Release Notes

---

## Version 1.7.6 — 2026-09-01

### Fix: Manual Field Order Was Being Overwritten by Auto-Detection

When you added several files of the same type (e.g. MiniDV) and manually set the field
order — say **Bottom Field First** — then clicked Next, your choice did not always stick.
Background auto-detection was still running, and when it finished it overwrote your
selection (often flipping it to *Progressive*), so the output came out **not properly
deinterlaced**.

Your manual choice is now **locked in the moment you make it**, and again when you click
Next to leave the Source page. A late-finishing auto-detection result can no longer
change a field order you set by hand.

### Change: Auto-Detection Is Disabled When More Than One File Is in the Timeline

Because every file in a batch could have a different field order (and telecine pattern),
running detection per file was both unreliable and slow. Auto-detection of **field order**
and **telecine / pulldown** is now switched off entirely for multi-file batches. Both
sections show a clear note:

> ⚠ Auto detection will not work if more than one file is added to the timeline.

The badges no longer sit on a spinning *"Detecting…"* / *"Analyzing…"* state that never
resolves — they now read *"Auto-detection disabled (batch)"*. In batch mode you simply set
the field order manually and standard deinterlacing is used. Single-file mode is unchanged:
detection still runs automatically.

### New: Plain-Language Settings Summary on the Output & Process Page

The final page now shows a **📋 Summary of settings** card above the *Start Processing*
button, recapping in plain English exactly what will be applied before you commit:

- **Core settings** are always listed — source (NTSC/PAL + capture method), field order,
  deinterlacing method (QTGMC / Inverse Telecine / skipped), crop, colour matrix, and
  output format.
- **Enhancements** (noise reduction, dehalo, upscale, Y/C delay, colour, levels, film
  grain, watermark, mixed audio) are listed only when you have turned them on, so the card
  stays short — if none are enabled it simply says *"None — deinterlacing only"*.
- The card updates live when you change the output format, and shows the file count for
  batches.

---

## Version 1.7.5 — 2026-08-30

### Fix: Upscaled SD Video Now Has Its Colours Converted 601 → 709 (Correct on YouTube)

Standard-definition video (VHS, DV, DVD) uses the older **BT.601** colour standard;
HD video uses **BT.709**. Previously, when you upscaled an SD capture to an HD size,
the tool relabelled the file as HD but left the pixels in 601 — and it *tagged* them
601. HD platforms like YouTube assume any HD-sized video is 709, so they reinterpreted
those 601 pixels as 709, making the result look **dark and oversaturated**.

Now, whenever upscaling produces an HD frame (**final height ≥ 720**), the tool performs
a real **BT.601 → BT.709 pixel conversion** in the VapourSynth pipeline — not just a tag
change — so the uploaded file displays with correct colour:

- The conversion runs **after the nnedi3 upscale**, at the pipeline's full 16-bit
  precision, using fmtconv's matrix (with a `core.resize`/zimg fallback), and preserves
  **limited (TV) range**.
- It handles both **PAL** (BT.470BG) and **NTSC** (SMPTE 170M) sources — both share the
  same 601 matrix coefficients.
- Chroma subsampling (4:2:0 / 4:1:1 / 4:2:2) is preserved through the conversion.
- After conversion the output is tagged **bt709 / bt709 / bt709** (frame props, the
  FFmpeg `-colorspace/-color_primaries/-color_trc` flags, and the `setparams` stamp) so
  the metadata matches the converted pixels.
- **If you keep the original SD size, nothing changes** — the video stays 601 and is
  tagged bt470bg / smpte170m exactly as before.

This is automatic and correct-by-default: there is no new setting to configure. The
Upscale page now includes a short note explaining it.

---

## Version 1.7.4 — 2026-08-02

### New: Choose Your Own Preview Frame on the Y/C Delay Page

The Y/C Delay page previously always showed frame 200 as the reference frame. A new
**Preview frame** control — a scrub slider plus a type-in frame-number box — lets you
preview any frame in the video (default remains 200):

- The preview reloads automatically about half a second after you stop scrubbing or
  typing, so dragging the slider doesn't fire off dozens of extractions.
- Once the file's duration has been probed, the slider range expands to the video's
  actual last frame.
- Scrubbing uses FFmpeg's fast time-based seek instead of exact-frame decoding, so
  jumping deep into an hours-long capture stays responsive.
- In multi-file batches, the chosen preview frame is remembered per file as you move
  between files.

### New: Live Grain Preview with Zoom on the Add Film Grain Page

The Add Film Grain page now shows a **Grain preview** of your video (frame 200 by
default, changeable via the same frame-number box) so you can judge the grain before
processing:

- **1× / 2× / 4× zoom buttons** — 1× fits the whole frame; 2× and 4× magnify the
  centre of the frame with crisp pixel-doubling so individual grain specks are
  clearly visible.
- The preview updates **live** as you move the strength slider.
- The preview grain is a visual approximation rendered in the app (Gaussian noise
  applied at native resolution); the real AddGrain filter still runs in the
  VapourSynth pipeline at encode time, exactly as before.

### Improvement: Wider, More Obvious Scrollbar

The vertical scrollbar on the right of every wizard page was thin and easy to miss,
so users didn't always realise a page continued below the fold. It is now 26 px wide
with visible up/down arrow buttons, a dark trough matching the UI, and a thumb that
highlights purple on hover. (Windows ignores width settings on classic Tk scrollbars,
so this uses a custom ttk style that honours them.) The About dialog scrollbar was
widened to match.

### Improvement: Diagnostic Log Text Now Points to Support Email

The Troubleshooting section on the Output & Process page now clearly recommends
enabling the diagnostic log, and explains what to do with it: the checkbox reads
*"Save diagnostic log for troubleshooting (recommended — saved alongside the output
video)"*, and the description asks users who hit an error to email the log file to
**videocaptureguide@gmail.com** so the problem can be investigated.

---

## Version 1.7.3 — 2026-07-08

### Fix: Full Overscan Crop Crashed on DVD / MPEG-2 (4:2:0) Sources

Selecting the Full Overscan Clean crop (or a manual top/bottom crop) on any 4:2:0
source — DVD rips, MPEG-2 captures — crashed within seconds. The visible error was
FFmpeg's misleading `Error opening input file pipe:0. Invalid data found when
processing input`; the real failure was QTGMC rejecting the cropped clip:

```
vapoursynth.Error: SeparateFields: clip height must be mod 2 in the smallest subsampled plane
```

The overscan preset crops 2 px top + 4 px bottom *before* deinterlacing, taking
PAL 576 → 570 (NTSC 480 → 474). With 4:2:0 chroma, deinterlacing splits the frame
into fields and each field needs whole chroma rows, which requires the luma height
to be a multiple of 4 — 570 and 474 are not. 4:2:2 capture sources were unaffected,
which is why the presets worked on typical captures but not DVD rips.

The top/bottom crop now runs *after* deinterlacing (the clip is progressive there,
so any even crop is legal — and field lines are no longer discarded before QTGMC
sees them). Left/right crop is unchanged. Output dimensions and aspect-ratio
handling are identical to before (704×474 / 704×570, same SAR). The odd-height
snap guard is also subsampling-aware now; its previous 1-pixel fallback crop was
itself invalid on 4:2:0.

---

## Version 1.7.2 — 2026-07-07

### Fix: PAL Encodes Failed at the FFmpeg Stage (Invalid Color Transfer Tag)

Processing any PAL source failed at the encode step — the VapourSynth pipe produced
frames, then aborted with `fwrite() call failed ... errno: 32` (broken pipe). The real
error was FFmpeg rejecting the output file:

```
[prores_ks] Undefined constant or missing '(' in 'bt470bg'
[prores_ks] Unable to parse "color_trc" option value "bt470bg"
```

FFmpeg accepts `bt470bg` as a name for `-colorspace` and `-color_primaries`, but the
matching **transfer** characteristic is named `gamma28` — passing `bt470bg` to
`-color_trc` kills the encoder before the first frame arrives, which is what broke the
pipe. NTSC was never affected because `smpte170m` happens to be a valid name for all
three flags. The correct transfer name is now used for the output encode and for the
in-app scopes (Vectorscope, RGB Parade, RGB Histogram), which passed the same invalid
flag on their input side for PAL sources.

### Fix: Output Files Were Missing Primaries / Transfer Color Tags (All Formats)

While fixing the above, a second, silent problem surfaced that affected **NTSC too**:
with FFmpeg 8, frame-level color metadata overrides the `-color_primaries` /
`-color_trc` encoder options — and frames arriving over the y4m pipe carry "unknown",
because y4m cannot transport the `_Primaries`/`_Transfer` props set in the `.vpy`. The
result: outputs were tagged with the correct matrix but `unknown` primaries and
transfer.

The encode command now stamps every frame with a `setparams` filter (merged into the
watermark filter chain when one is active, since FFmpeg allows only one `-vf` /
`-filter_complex` per stream). Outputs are now fully tagged, verified with ffprobe:
`bt470bg/bt470bg/bt470bg` (PAL), `smpte170m/smpte170m/smpte170m` (NTSC), tv range.

### Fix: False "Reverse Telecine" Suggestion on Interlaced PAL Video

Ordinary interlaced PAL video (e.g. a PAL DVD of a studio/reality TV show) triggered the
"Telecine detected — Inverse Telecine available" banner. The PAL detector fired when
more than 28% of sampled frames looked progressive to FFmpeg's `idet` — but idet cannot
tell a *static* frame from a progressive one, so normal 50i content with low-motion
shots easily crosses that bar. Genuine PAL 2:2 film transfers read as overwhelmingly
progressive (80%+), so the PAL threshold is now 75% (high confidence above 85%). NTSC
3:2 detection is unchanged.

The PAL wording was also misleading: it promised IVTC would "restore native 25fps" when
the file is already 25fps — 2:2 inverse telecine never changes the frame rate; it
reconstructs progressive frames by pairing fields instead of deinterlacing. The banner,
description, and choice-card labels now say so (and no longer mention 29.97fps on PAL
sources).

### Fix: PAL Inverse Telecine Dropped Every 5th Frame (20fps Judder)

Accepting the IVTC option on a PAL source generated `vivtc.VFM` **plus**
`vivtc.VDecimate`. VDecimate removes one frame in five — correct for NTSC 3:2 pulldown
(29.97 → 23.976), but PAL 2:2 has no duplicate frames to remove, so it discarded every
5th real frame and produced juddery 20fps output. The PAL IVTC path now generates
field matching only; NTSC keeps VFM + VDecimate.

---

## Version 1.7.1 — 2026-07-06

### Fix: Crash on 10-bit Sources with Inverse Telecine (DVD Rip MKVs)

Loading a 10-bit source (e.g. a DVD rip MKV re-encoded as `yuv420p10le`) and applying
Inverse Telecine crashed with a cryptic error:

```
vapoursynth.Error: VFM: input clip must be constant format YUV420P8, YUV422P8,
YUV440P8, YUV444P8, or GRAY8
```

VFM (the IVTC field matcher) only accepts 8-bit YUV, but 10-bit formats passed the
source-format whitelist untouched. Two fixes:

- **Automatic pixel-format detection at load time.** The source's `pix_fmt` is now read
  during source classification, and any 10-bit or non-standard YUV/grayscale format is
  converted to 8-bit YUV420 immediately after the source is loaded, before any other
  filter. A one-line notice appears on the Source Details page when this happens:
  *"Your source is 10-bit or non-standard format — automatically converting to 8-bit
  for processing."* Standard 8-bit sources are untouched — no conversion, no notice.
- **IVTC now works with the 16-bit pipeline.** Version 1.7.0 introduced the 16-bit
  internal pipeline, which lifted the clip to 16-bit *before* the IVTC step — so VFM
  received a 16-bit clip and rejected it for **every** source, not just 10-bit ones.
  Field matching now runs on an 8-bit working copy while the output frames are taken
  from the 16-bit clip via VFM's `clip2` parameter (the documented high-bit-depth
  usage), so IVTC output keeps full 16-bit precision.

DV sources (`yuv411p`) and RGB sources are unaffected — they keep their existing
dedicated conversion paths.

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
