# VCG Deinterlacer
### Beta-01 — by [VideoCaptureGuide](https://www.youtube.com/@VideoCaptureGuide)

A free Windows tool for deinterlacing VHS, Hi8, Video8, and MiniDV tape captures using **QTGMC** — the industry-standard motion-compensated deinterlacer. Guided step-by-step wizard interface with automatic video analysis.

---

## Features

- **QTGMC deinterlacing** — the gold standard for analog video restoration
- **Automatic video analysis** — detects noise level, color cast, color bleeding, and levels
- **Guided wizard** — walks you through every setting with explanations
- **Batch processing** — queue multiple files and process them overnight
- **Multiple output formats** — ProRes HQ, H.264, FFV1 (lossless), and more
- **PAR correction** — automatically converts non-square pixels to square for NTSC and PAL
- **Temporal denoising** — optional SMDegrain for noisy VHS footage
- **Color correction** — auto-detects and corrects color casts and saturation issues
- **Dropout removal** — reduces tape damage artifacts
- **Comparison video** — generates a side-by-side original vs. enhanced clip
- **Drag and drop** — drop video files directly onto the app window

---

## Requirements

### Required
- **Windows 10 or 11** (64-bit)
- **FFmpeg** — for video encoding
- **VapourSynth** — for QTGMC processing

### VapourSynth Plugins (installed via vsrepo)
- `havsfunc` — QTGMC deinterlacing and SMDegrain denoising
- `lsmas` — video source (LWLibavSource)
- `mvtools` — motion vectors for QTGMC
- `fmtconv` — format conversion

---

## Installation

### Step 1 — Install FFmpeg

1. Download **ffmpeg-release-essentials.zip** from https://www.gyan.dev/ffmpeg/builds/
2. Extract to `C:\ffmpeg` so that `C:\ffmpeg\bin\ffmpeg.exe` exists
3. Verify by opening a command prompt and typing: `ffmpeg -version`

### Step 2 — Install VapourSynth

1. Download the latest installer from https://github.com/vapoursynth/vapoursynth/releases
2. Run the installer with default options
3. Verify by opening a command prompt and typing: `vspipe --version`

### Step 3 — Install VapourSynth Plugins

Open a command prompt and run:

```
vsrepo.py install havsfunc lsmas mvtools fmtconv
```

If `vsrepo.py` is not in your PATH, find it in your VapourSynth installation folder.

### Step 4 — Install VCG Deinterlacer

Run `VCG_Deinterlacer_Beta-01_Setup.exe` and follow the installer prompts.

---

## Usage

1. Launch **VCG Deinterlacer** from the Start Menu or Desktop shortcut
2. Click **START** on the welcome screen
3. **Select File** — drag and drop or browse for your video file(s)
4. **Source** — confirm format (NTSC/PAL), field order (TFF/BFF), and crop settings
5. **Noise** — review the automatic noise analysis and choose a denoising level
6. **Color Bleeding** — review chroma bleed analysis and enable correction if needed
7. **Color Cast** — review color balance and apply correction if needed
8. **Levels** — review luma levels and apply adjustment if needed
9. **Audio** — choose mono-to-stereo mix options if applicable
10. **Finalize** — choose output format, review all settings, and click **Process**

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

**The app opens but processing fails immediately**
- Verify FFmpeg is installed at `C:\ffmpeg\bin\ffmpeg.exe`
- Verify VapourSynth is installed and `vspipe` is in your PATH
- Verify all four VapourSynth plugins are installed (havsfunc, lsmas, mvtools, fmtconv)

**"Could not load source" error**
- Make sure lsmas is installed: `vsrepo.py install lsmas`
- Try a different source file to rule out a corrupt input

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

VCG Deinterlacer uses a conservative QTGMC configuration designed to preserve the original analog character without over-processing:

```
Sharpness=0.1    (very mild — most presets use 0.2–1.0)
Lossless=2       (preserves original pixels where no MC is needed)
SourceMatch=3    (highest quality source matching)
NoiseProcess=2   (temporal denoise within QTGMC)
```

Full QTGMC parameter details are available in the app under **Help → About VCG Deinterlacer**.

---

## License

MIT License — see `LICENSE.txt` for full terms.

This software is free and open source. Third-party components (FFmpeg, VapourSynth, havsfunc) are subject to their own licenses.

---

## About

**VCG Deinterlacer** is developed by [VideoCaptureGuide](https://www.youtube.com/@VideoCaptureGuide) — a YouTube channel dedicated to VHS capture, tape preservation, equipment reviews, and analog video restoration tutorials.

Subscribe for tutorials on getting the most out of your tape archive.

- YouTube: https://www.youtube.com/@VideoCaptureGuide
