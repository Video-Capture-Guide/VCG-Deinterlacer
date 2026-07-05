# VCG Deinterlacer
### Version 1.7.0 — by [VideoCaptureGuide](https://www.VideoCaptureGuide.com)

A free Windows tool for deinterlacing VHS, Hi8, Video8, and MiniDV tape captures using **QTGMC** — the industry-standard motion-compensated deinterlacer. Guided step-by-step wizard interface with automatic video analysis.

---

## Download

**[Download VCG_Deinterlacer.exe — 1.7.0](https://github.com/Video-Capture-Guide/VCG-Deinterlacer/releases/latest)**

Extract the ZIP anywhere and double-click `VCG_Deinterlacer.exe`. On first launch, the app automatically downloads and installs FFmpeg and VapourSynth — no manual setup required.

---

## Features

- **QTGMC deinterlacing** — the gold standard for analog video restoration
- **Automatic first-run setup** — downloads FFmpeg and VapourSynth automatically on first launch
- **Automatic video analysis** — detects noise level, edge halos, color cast, color bleeding, and brightness levels, with quantified scores shown next to every recommendation and notes explaining where the analysis samples were taken from
- **Guided wizard with sidebar navigation** — walks you through every setting with explanations; a navigation sidebar shows every step, what's done, and what's next, and lets you click any visited step to jump back to it
- **Trim / segment export** — keep or cut frame-accurate segments before processing, with a preview scrubber, timecode entry, and the choice of joining kept parts into one file or exporting one file per segment
- **AVCHD and HDV support** — automatically detects and processes interlaced HD camcorder footage (.mts, .m2ts, .m2t, .ts) with a dedicated HD wizard path
- **Batch processing** — queue multiple files and process them overnight
- **Multiple output formats** — ProRes HQ, H.264, FFV1 (lossless), and more
- **PAR correction** — automatically converts non-square pixels to square for NTSC, PAL, and HDV sources
- **16-bit pipeline** — the full processing chain (QTGMC, BM3D, dehalo, colour correction, levels) runs at 16-bit precision; fmtconv error-diffusion dithering converts to the output bit depth at the very end, eliminating banding in skies and fades
- **Colorspace tagging** — auto-detects the correct matrix (BT.601 for SD, BT.709 for HD), tags VapourSynth frames and the output container, and uses the same matrix for all in-app video scopes so scope colors are accurate
- **Temporal denoising** — BM3D (with KNLMeansCL/SMDegrain fallback) for noisy VHS footage
- **Dehalo** — removes edge halos from VHS sharpening circuits and camcorder edge enhancement, with automatic halo analysis and a quantified halo score
- **Upscaling** — optional upscale to presets with NNEDI3 (SD sources only)
- **Mono-to-stereo** — optional fix if your video has audio in only one channel
- **Color correction** — auto-detects and corrects color casts and saturation issues
- **Video scopes** — Vectorscope and RGB Histogram on the Color Analysis page; RGB Parade with frame scrubber on the Video Levels page
- **Watermark** — optional text or logo overlay (position, size, opacity)
- **Film grain** — optional AddGrain overlay applied at the final resolution; keeps denoised footage from looking plasticky and prevents banding after YouTube's re-compression
- **Comparison video** — 20-second side-by-side original vs. enhanced clip: 10 s normal view + 10 s at 300% zoom
- **Drag and drop** — drop video files directly onto the app window, including MTS and AVCHD files
- **Portable** — no installer, no UAC prompt, no admin rights required

---

## Screenshots

<table>
<tr>
<td align="center"><img src="docs/screenshots/VCGD-001.jpg" width="380"><br><sub>Welcome screen</sub></td>
<td align="center"><img src="docs/screenshots/VCGD-002.jpg" width="380"><br><sub>Step 1 — Select video files</sub></td>
</tr>
<tr>
<td align="center"><img src="docs/screenshots/VCGD-003.jpg" width="380"><br><sub>Step 1 — File loaded and ready</sub></td>
<td align="center"><img src="docs/screenshots/VCGD-004.jpg" width="380"><br><sub>Step 2 — Source details (auto-detected)</sub></td>
</tr>
<tr>
<td align="center"><img src="docs/screenshots/VCGD-005.jpg" width="380"><br><sub>Step 2 — Quick-process option</sub></td>
<td align="center"><img src="docs/screenshots/VCGD-006.jpg" width="380"><br><sub>Step 3 — Noise removal analysis</sub></td>
</tr>
<tr>
<td align="center"><img src="docs/screenshots/VCGD-007.jpg" width="380"><br><sub>Step 3 — Color analysis</sub></td>
<td align="center"><img src="docs/screenshots/VCGD-008.jpg" width="380"><br><sub>Step 3 — Video levels</sub></td>
</tr>
<tr>
<td align="center"><img src="docs/screenshots/VCGD-009.jpg" width="380"><br><sub>Step 4 — Choose output format</sub></td>
<td align="center"><img src="docs/screenshots/VCGD-010.jpg" width="380"><br><sub>Step 4 — Processing complete</sub></td>
</tr>
</table>

---

## System Requirements

- **Windows 10 or 11** (64-bit)
- **Internet connection** on first launch (to download FFmpeg and VapourSynth, ~136 MB)

FFmpeg and VapourSynth are downloaded automatically into a `_deps\` folder next to the EXE. No system-wide installation is required.

---

## Installation

1. Download `VCG_Deinterlacer_1.7.0.zip` from the [Releases page](https://github.com/Video-Capture-Guide/VCG-Deinterlacer/releases/latest)
2. Extract the ZIP to any folder (e.g. `C:\Tools\VCG_Deinterlacer\`)
3. Double-click `VCG_Deinterlacer.exe`
4. On first launch, the **First Run Setup** window appears and downloads the required tools (~136 MB). This only happens once.
5. After setup completes, the main wizard opens automatically.

On all future launches the wizard opens directly with no setup step.

---

## Usage

1. Launch **VCG Deinterlacer** from the folder where you extracted it
2. Click **START** on the welcome screen
3. **Select File** — drag and drop or browse for your video file(s)
4. **Source** — confirm format (NTSC/PAL), field order (TFF/BFF), crop settings, and source color matrix (BT.601 auto-selected for SD; BT.709 for HD)
5. **Trim** — output the entire video (default), or keep/cut frame-accurate segments (single file only)
6. **Y/C Delay** — correct horizontal chroma shift if present
7. **Noise** — review the automatic noise analysis (noise score shown) and choose a denoising level
8. **Dehalo** — review the automatic halo analysis (halo score shown) and choose a dehalo level
9. **Upscale** — optionally upscale SD sources with NNEDI3
10. **Color Cast** — review color balance and apply correction if needed
11. **Levels** — review luma levels on the RGB Parade and apply adjustment if needed
12. **Audio** — choose mono-to-stereo mix options if applicable
13. **Watermark** — optionally add a text or logo watermark
14. **Add Grain** — optionally add fine film grain (masks the "plasticky" look of denoised video and prevents banding on YouTube)
15. **Dithering** — leave output dithering at its recommended default, or adjust the method
16. **Finalize** — choose output format, review all settings, and click **Process**

All Advanced steps (5–15) are optional — the sidebar marks them as such, and the **Process Now** shortcut after the Source step skips straight to Finalize with safe defaults.

Processing time depends on video length and your CPU. A one-hour VHS capture typically takes 2–4 hours.

---

## Output Formats

| Format | Extension | Best For |
|--------|-----------|----------|
| ProRes HQ | .mov | Editing in DaVinci Resolve, Premiere, Final Cut |
| H.264 | .mp4 | Sharing, uploading to YouTube |
| FFV1 | .mkv | Archiving (lossless) |
| DNxHD 115 | .mov | Editing in Avid |

---

## Field Order Reference

| Source Format | Field Order |
|---------------|-------------|
| VHS (most decks) | TFF (Top Field First) |
| S-VHS | TFF |
| Video8 / Hi8 | TFF |
| MiniDV / Digital8 | BFF (Bottom Field First) |
| Betacam | TFF |

If motion looks jerky or stuttery after processing, try switching the field order.

---

## Troubleshooting

**First Run Setup fails to download**
- Check your internet connection
- Try disabling your VPN or firewall temporarily
- You can download the tools manually — see the instructions shown in the setup window

**The app opens but processing fails immediately**
- Delete the `_deps\` folder next to the EXE and re-launch to re-run the setup
- Check that `_deps\ffmpeg\ffmpeg.exe` and `_deps\vs\vspipe.exe` exist

**"Could not load source" error**
- Make sure `_deps\vs\plugins64\LSMASHSource.dll` exists
- Try re-running the setup by deleting the `_deps\` folder

**Processing is very slow**
- QTGMC is CPU-intensive — this is normal
- Close other applications to free up CPU
- Consider reducing the denoising level if enabled

**Output video has wrong aspect ratio**
- Enable PAR correction in the Source step
- Make sure the correct format (NTSC/PAL) is selected

**Audio is missing from output**
- Check the Audio step — ensure the correct audio option is selected
- Verify the source file has an audio track using MediaInfo

---

## Technical Details

### Processing Pipeline (v1.7.0)

Every encode runs through a **16-bit VapourSynth pipeline**. The source is lifted to 16-bit integer at the very start (`fmtc.bitdepth`) and all operations — QTGMC, BM3D, FineDehalo, colour cast correction, levels — run natively at that depth with no mid-chain round-trips to 8-bit.

Optional **film grain** (AddGrain) is applied at the final resolution — after PAR correction and any NNEDI3 upscale — so the grain stays pixel-fine rather than being enlarged by the upscaler.

At the end, **fmtconv error-diffusion dithering** (`fmtc.bitdepth`, dmode=3) converts back to the codec's native depth:
- **ProRes HQ** → 10-bit (fills the container fully)
- **H.264, FFV1, and all other formats** → 8-bit

This eliminates the banding in skies, fades, and gradients that is common in tape captures processed through an 8-bit chain.

All output files are tagged with the correct **colorspace metadata** (BT.601 for SD, BT.709 for HD) in both the VapourSynth frame properties and the FFmpeg container flags. The in-app video scopes use the same matrix, so scope colors match the actual video signal.

### QTGMC Configuration

VCG Deinterlacer uses a conservative QTGMC configuration designed to preserve the original analog character without over-processing:

```
Sharpness=0.1    (very mild — most presets use 0.2–1.0)
Lossless=2       (preserves original pixels where no MC is needed)
SourceMatch=3    (highest quality source matching)
NoiseProcess=2   (temporal denoise within QTGMC)
```

Full QTGMC parameter details are available in the app under **Help → About VCG Deinterlacer**.

---

## Building from Source

See [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md) for full build instructions.

**Quick start:**
```
pip install -r requirements.txt
build_vcg_deinterlacer.bat
```

Requires Python 3.10+, Visual Studio Build Tools (or MinGW64).

---

## License

MIT License — see `LICENSE.txt` for full terms.

This software is free and open source. Third-party components (FFmpeg, VapourSynth, havsfunc) are subject to their own licenses.

---

## Version History

| Version | Date | Notes |
|---------|------|-------|
| 1.7.0 | 2026-07-04 | Sidebar wizard navigation with clickable visited steps; Trim / Segment Export page (keep or cut segments, join or split output); Watermark, Add Grain, and Output Dithering split into separate pages; film grain fixed — correct strength (16× too strong before) and applied at final resolution |
| 1.6.0 | 2026-06-29 | 16-bit pipeline; fmtconv error-diffusion output dithering (auto, ProRes 10-bit); colorspace/matrix tagging (BT.601/BT.709 auto-select); correct scope colors; Source Color Matrix dropdown on Source Details page |
| 1.5.0 | 2026-06-10 | Dehalo page with halo analysis; Watermark page + film grain; BM3D denoising; RGB Parade; quantified analysis scores; sampling notes; reworked comparison video (10 s + 10 s at 300%) |
| 1.4.1 | 2026-06-07 | .MOD file support; 16:9 widescreen PAR fix; crop page recommendation |
| Beta-02b | 2026-04-05 | Fix RGB source support; faster launch via persistent cache dir |
| Beta-02 | 2026-03-28 | Portable ZIP; first-run auto-setup; no installer |
| Beta-01 | 2026-03-23 | Inno Setup installer; manual FFmpeg/VapourSynth install |
| Beta 0.4 | 2026-03-17 | First working installer build |
| Beta 0.2 | 2026-03-09 | Initial release |

---

## About

**VCG Deinterlacer** is developed by [VideoCaptureGuide](https://www.youtube.com/@VideoCaptureGuide) — a YouTube channel dedicated to VHS capture, tape preservation, equipment reviews, and analog video restoration tutorials.

Subscribe for tutorials on getting the most out of your tape archive.

- YouTube: https://www.youtube.com/@VideoCaptureGuide
