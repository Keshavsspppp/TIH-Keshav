# Dataset Inspection Report — Day 07

**Raw folder:** `data/raw` (the locked copy of `Videos/`)  
**Videos found:** 4  
**Verdicts:** 0 green, 4 amber, 0 red  
**With ground truth:** 0 of 4

Nothing in the raw folder was changed. This run only read the files.

## 1. Every video at a glance

| video | frames | size | fps | truth? | on/off split | verdict |
|---|---|---|---|---|---|---|
| 1LED_92bps | 30058 | 640x360 | 260.0 | no | 12.72 | **amber** |
| 2LEDs_92bps | 21157 | 640x360 | 260.0 | no | 13.24 | **amber** |
| 3LEDs_92bps | 13057 | 640x360 | 260.0 | no | 18.54 | **amber** |
| 4LEDs_92bps | 11033 | 640x360 | 260.0 | no | 6.35 | **amber** |

## 2. Problems found

- **1LED_92bps** (amber): the light reaches 255 out of 255, so its brightness is clipped at the top — on/off still works, but the exact level is lost; no ground truth — BER cannot be computed for this video
- **2LEDs_92bps** (amber): the light reaches 255 out of 255, so its brightness is clipped at the top — on/off still works, but the exact level is lost; no ground truth — BER cannot be computed for this video
- **3LEDs_92bps** (amber): the light reaches 255 out of 255, so its brightness is clipped at the top — on/off still works, but the exact level is lost; no clear repeating rhythm in the brightness (peak strength 2.47); no ground truth — BER cannot be computed for this video
- **4LEDs_92bps** (amber): the light reaches 255 out of 255, so its brightness is clipped at the top — on/off still works, but the exact level is lost; no clear repeating rhythm in the brightness (peak strength 2.77); no ground truth — BER cannot be computed for this video

## 3. Duplicates

- No two files are byte-for-byte identical.
- No two videos share the same blinking pattern.

Note: duplicates are judged by the blinking pattern, not by how the frames look. Every video in this dataset looks alike, so appearance would flag almost every pair.

## 4. Ground-truth coverage

No ground-truth files were found. BER cannot be computed on any video. All BER work must move to the synthetic videos.

## 5. First-look signal check

The **on/off split** score says how cleanly the brightness falls into two groups. Above about 2 is clean. Below 1 means the two levels overlap and a simple threshold will struggle.

The **strongest rhythm** is a hint at the blink rate. It is only a hint: if the light blinks faster than the camera samples, this number is an alias and will be wrong.

| video | on/off split | strongest rhythm (Hz) | peak strength |
|---|---|---|---|
| 1LED_92bps | 12.72 | 62.4 | 3.19 |
| 2LEDs_92bps | 13.24 | 49.4 | 3.5 |
| 3LEDs_92bps | 18.54 | 72.222 | 2.47 |
| 4LEDs_92bps | 6.35 | 1.313 | 2.77 |

## 6. Figures

**1LED_92bps**
- variance_map: `figures\1LED_92bps_variance_map.png`
- brightness_trace: `figures\1LED_92bps_brightness_trace.png`
- histogram: `figures\1LED_92bps_histogram.png`
- spectrum: `figures\1LED_92bps_spectrum.png`

**2LEDs_92bps**
- variance_map: `figures\2LEDs_92bps_variance_map.png`
- brightness_trace: `figures\2LEDs_92bps_brightness_trace.png`
- histogram: `figures\2LEDs_92bps_histogram.png`
- spectrum: `figures\2LEDs_92bps_spectrum.png`

**3LEDs_92bps**
- variance_map: `figures\3LEDs_92bps_variance_map.png`
- brightness_trace: `figures\3LEDs_92bps_brightness_trace.png`
- histogram: `figures\3LEDs_92bps_histogram.png`
- spectrum: `figures\3LEDs_92bps_spectrum.png`

**4LEDs_92bps**
- variance_map: `figures\4LEDs_92bps_variance_map.png`
- brightness_trace: `figures\4LEDs_92bps_brightness_trace.png`
- histogram: `figures\4LEDs_92bps_histogram.png`
- spectrum: `figures\4LEDs_92bps_spectrum.png`

## 7. What to do next

- [ ] Check every amber and red video by eye before deciding to keep or drop it
- [ ] Copy this MANIFEST into `data/raw/MANIFEST.csv`
- [ ] Assign DEV and TEST roles, and write the TEST video IDs in the log **before** any tuning starts
- [ ] Send the open questions to the faculty (see `MENTOR_REVIEW.MD`)
- [ ] Do not clean, crop, re-encode or delete anything yet
