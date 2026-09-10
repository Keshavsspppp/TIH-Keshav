# Day 08 — Video Quality Audit and Extraction Risks

**Project:** Optical Camera Communication (OCC) Video Message Decoding
**Dataset:** the 4 supplied videos
**Method:** every frame of every video was read and measured — 75,305 frames in total. Nothing was sampled or skipped.

**Read with:** `DAY_07_FINDINGS.MD` (what the dataset is), `DAY_07.MD` (the inspection protocol).

---

## 1. Originals Are Unchanged

Checked before writing this file:

```
./1LED_92bps.mp4: OK
./2LEDs_92bps.mp4: OK
./3LEDs_92bps.mp4: OK
./4LEDs_92bps.mp4: OK
All files match. The raw copy is untouched.
```

Every fingerprint still matches the one taken on Day 07. All the work in this audit was read-only. `data/raw/` stays locked, and no step below writes to it.

---

## 2. Video Quality Table

The main deliverable. One row per video.

| | 1LED | 2LEDs | 3LEDs | 4LEDs |
|---|---|---|---|---|
| **File and format** | | | | |
| Frames in header | 30,058 | 21,157 | 13,057 | 11,033 |
| Frames actually read | **30,058** | **21,157** | **13,057** | **11,033** |
| Missing or unreadable | 0 | 0 | 0 | 0 |
| Length | 115.6 s | 81.4 s | 50.2 s | 42.4 s |
| Frame rate | 260 fps | 260 fps | 260 fps | 260 fps |
| Frame rate steady? | yes | yes | yes | yes |
| Resolution / codec | 640×360 mpeg4 | 640×360 mpeg4 | 640×360 mpeg4 | 640×360 mpeg4 |
| **Usable part** | | | | |
| Dark at start | 217 fr | 93 fr *(see §5; real transmission from ~975)* | 965 fr | 1,816 fr |
| Dark at end | 1,985 fr | 2,987 fr | 626 fr | 608 fr |
| Transmission length | 107.1 s | 69.5 s | 44.1 s | 33.1 s |
| Bits available | ~9,900 | ~6,400/LED | ~4,100/LED | ~3,000/LED |
| **Transmitter visibility** | | | | |
| Frames with a lamp lit | 48.7% | 67.1% | 74.3% | 83.5% |
| Longest gap with no lamp | 13 fr (5 bits) | **877 fr (310 bits)** | 12 fr (4 bits) | 6 fr (2 bits) |
| Lamp size, median | 8,272 px | 8,337 px | 3,108 px | 9,249 px |
| Lamp size spread (IQR) | 106 px | 4,296 px | 2,559 px | 6,449 px |
| **Brightness** | | | | |
| "On" level, median | 246 | 249 | 239 | 249 |
| "On" level, 5th–95th | 199–248 | 238–250 | 231–249 | 247–250 |
| Ambient (everything else) | 3.5 | 2.6 | 2.5 | 1.8 |
| **Contrast (on − ambient)** | **243** | **246** | **237** | **248** |
| **Camera motion** | | | | |
| Slow drift across the clip | 0.1 px x, 0.8 px y | 8 px x* | 10 px x* | 9 px x, 7 px y* |
| Camera verdict | static | static | static | static |
| **Ambient light change** | | | | |
| Range across 1-second blocks | 0.30 | 0.55 | 0.16 | 0.31 |
| As a share of contrast | 0.12% | 0.22% | 0.07% | 0.12% |
| **Overall verdict** | green | **amber** | green | green |

\* The apparent drift in the multi-LED videos is not camera movement — see §4.

> **Note (2026-09-10, audit):** re-checked on a full read of all 75,305 frames in `../../Videos/`. Frame counts, zero duplicated and zero black frames, lead-in/lead-out, the 877-frame gap, the drift figures and the ambient medians reproduce. "Frames with a lamp lit" is measured **within the trimmed transmission span**, not the whole file (whole-file values are 45 / 57 / 65 / 65 %). "Ambient" here means the mean of pixels not brighter than 180; the per-second range depends on that cut and came out 2–3× larger on the re-check (0.6–0.9 grey levels), still under 0.4 % of contrast. The code that produced this table is not in the repository; `occ_prototype.ipynb` in this folder is unrelated to it (see the note at the top of that notebook).

---

## 3. Readability

All four videos read from first frame to last with no failures. The header count and the counted frames match **exactly** in all four — no dropped frames, no truncation, no black frames.

This is unusual and worth noting. It means the files have not been re-wrapped or repaired, and we can trust frame numbers as a stable way to refer to positions in the video.

---

## 4. Camera Motion

**The camera is static in all four videos.** This is good news, and it removes a whole class of work.

For the single-lamp video the measurement is direct: the lamp's centre moved 0.1 pixels sideways and 0.8 pixels vertically across the **entire 107 seconds**. That is not motion, that is measurement noise.

### Why the multi-LED numbers look worse than they are

The multi-LED videos show 8–10 pixels of apparent movement, and large frame-to-frame jumps of 16–19 pixels. That is not the camera shaking. It is an artefact of how we measured.

We tracked the centre of *all* bright pixels in the frame. In a multi-LED video, different lamps are lit at different moments, so that centre jumps between lamps every few frames. Nothing moved. The measurement was simply the wrong shape for the scene.

Two conclusions follow:

1. **ROI tracking is not needed.** The tracker in M1 can stay switched off. One fixed box per lamp, found once, will hold for the whole video.
2. **Each lamp needs its own box.** A single box around "the bright stuff" is meaningless when several lamps take turns. This is the same conclusion the ROI-finder problems in Day 07 pointed to, arrived at from a different direction.

### One thing we checked and ruled out

The single-lamp video showed a 5-pixel vertical wobble frame to frame, which should not happen with one static lamp. We checked whether a second reflective spot in the room was being picked up. It is not — over 1,500 frames there is exactly **one** bright region, 104×104 pixels.

The wobble comes from partly-lit frames: as the lamp dims through a transition, its edge pixels drop below our brightness cutoff before its centre does, so the measured centre shifts. It is an artefact of the cutoff, not of the scene.

---

## 5. Transmitter Visibility

### The lamps are always there when they should be

Three of the four videos have a longest "no lamp visible" stretch of 6 to 13 frames — that is 2 to 5 bits. Exactly what you expect from a normal run of zeros in the data. **No occlusion, nothing walking in front of the lamp, no dropout.**

### The exception: a false start in 2LEDs

`2LEDs_92bps` has a **877-frame (3.37-second) dark stretch** starting at frame 98.

What happened: there is a brief flash at frame 93, then 3.4 seconds of nothing, then the real transmission begins around frame 975.

This matters because the obvious way to trim a video — "start at the first bright frame" — would lock onto that flash at frame 93 and feed 3.4 seconds of silence into the decoder. The timing recovery would try to find a bit clock in darkness.

**Fix:** trim on *sustained* activity, not on the first bright frame. Require a window of at least, say, one second in which the lamp is lit for a reasonable share of frames. This is a small rule, and it prevents a failure that would otherwise look like a mysterious decoder bug.

### Lamp size

The single-lamp video has a very steady lamp size: median 8,272 pixels with an IQR of only 106. It is the same lamp, fully lit, every time.

The multi-LED videos have a large spread (IQR 2,559 to 6,449) for the expected reason — sometimes one lamp is lit, sometimes three. Once each lamp gets its own box, this spread should collapse.

At 3,000 to 9,000 pixels per lamp, there are plenty of pixels to average over. Small, dim transmitters are not one of our problems.

---

## 6. Ambient Light

**Ambient light is effectively constant.** Measured second by second, the background brightness varies by 0.16 to 0.55 grey levels across an entire recording. The lamp-to-background contrast is around 240.

So the ambient variation is **roughly one part in a thousand** of the signal.

This has a direct consequence for our plan, and it is worth being upfront about:

> The detrending and rolling-normalisation steps in M1 were designed to handle ambient drift and auto-exposure changes. In this dataset there is almost nothing for them to remove.

That does not make them wrong. It means:

- They must be shown to be **harmless** here, not helpful. A step that helps on other data and does no damage on this data is still fine to keep — but we report it honestly as "no measurable benefit on this dataset" rather than claiming a win.
- Their value can still be demonstrated on the synthetic videos, where we control the drift ourselves (experiment E11). That result is real, but it is a synthetic result, and it gets labelled as one.
- This is a second piece of evidence, alongside the clean on/off split from Day 07, that plain accuracy will not separate our methods. **The sensitivity study is the contribution.**

---

## 7. Extraction Risk Checklist

The second deliverable. Each risk has a test that shows whether it has been dealt with.

| # | Risk | How likely | What it breaks | What we do | How we check |
|---|---|---|---|---|---|
| **R1** | Trimming locks onto the false start in 2LEDs and feeds 3.4 s of darkness to the decoder | **Happens today** if we trim naively | Timing recovery on that video | Trim on sustained activity, not the first bright frame | Trimmed start for 2LEDs is near frame 975, not 93 |
| **R2** | One ROI box covers several lamps, mixing two data streams into one signal | **Happens today** — it already did on 2LEDs | Every multi-LED decode | Split touching blobs; one box per lamp | Box count equals the LED count in the filename, for all four videos |
| **R3** | The ROI finder is fooled by a few-pixel speck of glare | **Happens today** — 2–3 px specks were picked on 3LEDs and 4LEDs | Picks the wrong ROI | Reject blobs below a minimum size | No chosen box is under ~100 px |
| **R4** | Only the start of a video is used to find the lamps, and the message opens with a long run of one bit | **Happened once already** (4LEDs, 1,816 dark frames) | ROI finding fails completely | Sample frames across the whole clip | ROI is found on 4LEDs without special handling |
| **R5** | Bits are read from the dark lead-in or lead-out | Likely if trimming is skipped | Extra junk bits at both ends | Trim before decoding; record the trim points | Bit count matches active seconds × 92, within a few percent |
| **R6** | Lamp brightness is clipped at 255, so exact levels are lost | **Certain** — all four videos | Any multi-level reading | Accept it. On/off only. Use pixels away from the clipped centre | Multi-level decoding stays out of scope |
| **R7** | Partly-lit frames at bit boundaries are read as full bits | Certain — 2.83 frames per bit guarantees them | Wrong bits at every boundary | Sample at estimated bit centres, not at every frame | Sampled points sit away from transitions in the eye plot |
| **R8** | Timing drifts over a long clip because 260 fps is nominal, not exact | Possible over 30,000 frames | The tail of long messages | Re-estimate the bit phase in blocks rather than once | Bit error does not rise with position in the clip |
| **R9** | We tune settings and report results on the same frames | Likely, given only 4 videos | Every reported number | Tune on the first 30%, report on the last 70% | Leak check E17 passes |
| **R10** | The multi-LED streams get combined in the wrong order or wrong direction | Likely, since the format is unknown | The final message | Keep each lamp's bits separate and labelled by position | Per-lamp bitstreams saved before any combining |
| **R11** | No ground truth, so a wrong decode looks like a right one | **Certain today** | BER, correctness, the ML branch | Ask faculty (Q1). Meanwhile verify on synthetic data only | Ground truth received, or real-data results marked unverified |
| **R12** | Reading whole videos into memory | **Happened twice** during this audit | The analysis crashes | Process frame by frame; never hold a full video | Peak memory stays under ~500 MB per video |
| **R13** | An original file gets changed or overwritten | Low | Everything, silently | `data/raw` is read-only with fingerprints | `preserve_raw.sh --verify` passes before every reported run |

### Risks we checked and can close

| Risk | Status |
|---|---|
| Camera shake or drift needing a tracker | **Closed.** Camera static; 0.8 px over 107 s |
| Ambient light or auto-exposure drift | **Closed.** Varies by ~0.1% of contrast |
| Dropped, corrupt or unreadable frames | **Closed.** 75,305 of 75,305 frames read |
| Variable frame rate | **Closed.** Steady in all four |
| Occlusion of the transmitter | **Closed.** Longest true gap is 5 bits |
| Transmitter too small or too dim | **Closed.** 3,000–9,000 px, contrast ~240 |
| Duplicate files | **Closed.** All four fingerprints differ |

---

## 8. What This Changes

| Change | Reason |
|---|---|
| Switch ROI tracking **off** by default | Camera is static. Tracking adds risk with no benefit |
| Add a **sustained-activity trim** step before decoding | The 2LEDs false start (R1) |
| One ROI **per lamp**, with blob splitting and a minimum size | R2 and R3, both already observed |
| Report detrending and normalisation as **harmless, not helpful** on this data | Ambient varies by ~0.1% of contrast |
| Re-estimate bit phase **in blocks**, not once per video | Clips run up to 30,000 frames (R8) |
| Save **per-lamp bitstreams** before combining | R10, and it makes the multi-LED result checkable |

---

## 9. Overall Verdict

| Video | Verdict | Why |
|---|---|---|
| `1LED_92bps` | **green** | Clean, static, no gaps, steady lamp. The one to develop against first |
| `2LEDs_92bps` | **amber** | The 3.4-second false start needs handling before anything else works |
| `3LEDs_92bps` | **green** | Clean. Needs per-lamp ROIs |
| `4LEDs_92bps` | **green** | Clean, but the longest dark lead-in (1,816 frames). Trimming is mandatory |

Nothing here is a reason to reject a video. The recording quality is high across the board: static camera, steady light, no dropped frames, and a very strong signal. **Every real risk on the list is either something our own code does wrong, or the missing ground truth** — not a defect in the footage.

Which is a good position to be in on Day 08, because our own code is the part we control.
