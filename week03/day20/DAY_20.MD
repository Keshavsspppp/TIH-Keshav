# Day 20 — Robustness / Ablation Study

**Project:** Optical Camera Communication (OCC) Video Message Decoding
**Files:** `ablation.py`, `ablation_results.json`, `fig_ablation_day20.png`.
**What it is:** the project-specific study named in the brief and in the Day 03 research question — *how far can the ROI, the smoothing, the threshold and the symbol timing be wrong before decoding fails?* — run for the Day 09 rule (**baseline**, most confident frame) and the Day 19 rule (**tuned**, nearest frame to the bit centre), so their degradation can be compared (Day 05 E14).

Each sweep changes one setting and holds everything else at the tuned configuration. Runtime 31 s.

**How to read the numbers.**
- *Synthetic BER* — on the assumed 92 bps model (`occlib.synth`, contrast 245, exposure 0.3), four 3,000-bit streams, noise 8 (the real level) unless stated. "@ true" = phase known; "@ 0" = phase-0 convention, the real situation.
- *Real* — DEV part of all ten lamps, median. "unchanged" = share of bits identical to the default setting. It measures how much the answer *moves*, not whether it is right. No ground truth exists.
- ROI sweeps exist for real data only; a synthetic signal has no box.

---

## 1. ROI choice (real data)

| Box | Gap / noise | Baseline: bits unchanged | Tuned: bits unchanged | Phase-indep. share (tuned) |
|---|---|---|---|---|
| scale 0.5 | 65 | 93.9 % | **99.7 %** | 34.8 % |
| scale 0.7 | 62 | 96.2 % | 99.9 % | 35.0 % |
| scale 0.85 | 56 | 98.6 % | 99.8 % | 35.0 % |
| **scale 1.0 (default)** | 56 | 100 % | 100 % | 34.9 % |
| scale 1.25 | 56 | 97.6 % | 99.6 % | 34.7 % |
| scale 1.5 | 44 | 93.9 % | 99.2 % | 34.5 % |
| scale 2.0 | 15 | 83.2 % | **99.0 %** | 34.3 % |
| shift x −0.50 box | 52 | 92.7 % | 99.5 % | 34.6 % |
| shift x −0.25 | 57 | 97.8 % | 99.9 % | 34.8 % |
| shift x ±0.10 | 56 | 99.0 % | 100 % | 34.9 % |
| shift x +0.25 | 55 | 96.6 % | 99.9 % | 34.8 % |
| shift x +0.50 | 43 | 92.1 % | 99.3 % | 34.3 % |

**Effect quantified.** A box half or double the size, or moved by half its width, changes **under 1.1 %** of the tuned decoder's bits, even when the on/off separation has fallen from 56 to 15. The baseline rule loses up to 17 %. ROI choice is not a sensitivity of this pipeline; the Day 09 detector could be replaced by a hand-drawn box of roughly the right place and nothing downstream would notice.

## 2. Smoothing window

| Window (frames) | Baseline BER @ 0 / @ true | Tuned BER @ 0 / @ true | Baseline unchanged (real) | Tuned unchanged (real) |
|---|---|---|---|---|
| **1 (off, default)** | 13.5 % / 0.27 % | **6.6 % / 0.00 %** | 100 % | 100 % |
| 3 | **8.3 %** / 0.00 % | 6.5 % / 0.00 % | 81.2 % | 95.7 % |
| 5 | 14.6 % / 4.4 % | 8.6 % / 4.0 % | 75.6 % | 82.7 % |
| 7 | 23.5 % / 24.2 % | 24.8 % / 24.8 % | 70.5 % | 71.2 % |
| 9 | 24.8 % / 24.7 % | 24.8 % / 24.7 % | 69.2 % | 73.3 % |

**Effect quantified.** A window of 5 frames (1.8 bits) starts to cost bits; 7 or more (2.5 bits) destroys the signal — BER 24 % with the phase *known*, both rules alike. That is the "smoother erases the edges" prediction of Day 05 §2, now with the number: the break is between 3 and 5 frames, i.e. at about one bit length, exactly where E08 said to look.

**One surprise, stated plainly.** A 3-frame window *helps* the baseline rule at an unknown phase (13.5 → 8.3 %). Day 12 switched smoothing off because it deletes 27 % of level changes in the signal; that is still true, but on the model the confident rule's phase error comes from clean frames belonging to the neighbouring bit, and blurring them makes the rule pick the centre frame more often. For the tuned rule the gain is 0.1 point — it is already looking at the centre. So the Day 12 decision stands for the tuned decoder; for the baseline rule it was worth 5 BER points, and the signal-level indicators Day 12 used could not see that.

## 3. Threshold placement

Threshold moved by a fraction of the signal range (range ≈ 245, so ±0.1 ≈ ±25 grey levels).

| Shift | Baseline BER @ 0 / @ true | Tuned BER @ 0 / @ true | Baseline unchanged (real) | Tuned unchanged (real) |
|---|---|---|---|---|
| −0.3 | 19.0 % / 4.9 % | 6.7 % / **0.00 %** | 69.5 % | **99.3 %** |
| −0.2 | 18.0 % / 3.2 % | 7.0 % / 0.00 % | 70.2 % | 99.5 % |
| −0.1 | 17.0 % / 1.3 % | 6.6 % / 0.00 % | 70.4 % | 99.8 % |
| **0 (default)** | 13.5 % / 0.27 % | 6.6 % / 0.00 % | 100 % | 100 % |
| +0.1 | 17.1 % / 1.5 % | 6.6 % / 0.00 % | 83.1 % | 99.8 % |
| +0.2 | 18.0 % / 3.7 % | 6.7 % / 0.00 % | 82.9 % | 99.5 % |
| +0.3 | 18.9 % / 5.5 % | 6.5 % / 0.02 % | 82.5 % | 99.3 % |

**Effect quantified.** This is test E09b, which Day 09 §2 asked for and never got. Its caveat was right: the most-confident-frame rule "follows a badly placed threshold". Moving the threshold by a tenth of the range changes 17–30 % of its real bits and adds 4 BER points at the true phase; the sign asymmetry (70 % vs 83 %) comes from the on/off split not being 50/50. The tuned rule is flat across the whole ±0.3 band: 0.00 % BER at the true phase, over 99 % of real bits unchanged. **Threshold tolerance of the tuned decoder: at least ±30 % of the range at the real noise level.** At noise 80 both rules collapse beyond ±0.1 — there the noise reaches the threshold, and no sampling rule can help.

## 4. Phase offset (symbol timing, part 1)

Synthetic BER when the assumed phase is offset from the true one; real: bits unchanged from the phase-0 convention.

| Offset (bits) | Baseline BER | Tuned BER | Baseline unchanged | Tuned unchanged |
|---|---|---|---|---|
| −0.40 | 15.4 % | **0.06 %** | 74.0 % | 69.1 % |
| −0.30 | 9.3 % | 0.00 % | 80.6 % | 77.7 % |
| −0.20 | 4.8 % | 0.00 % | 87.1 % | 84.6 % |
| −0.10 | 0.00 % | 0.00 % | 92.9 % | 92.4 % |
| **0** | 0.27 % | 0.00 % | 100 % | 100 % |
| +0.10 | 4.8 % | 0.00 % | 93.0 % | 91.3 % |
| +0.20 | 9.1 % | 0.00 % | 86.4 % | 83.5 % |
| +0.25 | 11.9 % | 2.2 % | 83.3 % | 79.0 % |
| +0.30 | 15.6 % | 8.7 % | 80.2 % | 74.9 % |
| ±0.50 | 22.1 % | 13.2 % | 69.9 % | 62.9 % |

**Effect quantified.** Working range at BER ≤ 1 %: baseline **−0.10 to −0.05 bit** (0.05 wide — and not even including zero, because of the window bug fixed on Day 17); tuned **−0.40 to +0.20 bit**, 0.6 bit wide. The tuned rule decodes correctly across 60 % of all possible phases; the baseline across 5 %. This is the headline number the Day 05 plan asked for ("BER stays under 0.01 while the bit start is off by up to ±… of a bit").

The real-data "unchanged" columns are nearly the same for both rules — another demonstration that the real indicators cannot see the difference the BER sees.

## 5. Period error (symbol timing, part 2)

Assumed bit period off by *e* % from the true one, over 3,000 bits.

| Period error | Baseline BER @ 0 / @ true | Tuned BER @ 0 / @ true | Baseline unchanged | Tuned unchanged |
|---|---|---|---|---|
| ±0.2 % | 41 % / 41 % | 41 % / 41 % | 68–70 % | 62 % |
| ±0.5 % | 46 % / 46 % | 46 % / 46 % | 58–60 % | 55 % |
| ±1 % | 48 % / 48 % | 47–48 % / 48 % | 56 % | 54 % |
| ±3 %, ±10 % | 48 % / 48 % | 48 % / 48 % | 52–53 % | 52–53 % |
| **0** | 13.5 % / 0.27 % | 6.6 % / 0.00 % | 100 % | 100 % |

**Effect quantified.** A 0.2 % error in the assumed bit rate — 92.0 vs 92.2 bps — is already a coin toss over 3,000 bits, for both rules, phase known or not. The reason is arithmetic: 0.2 % of 3,000 bits is a 6-bit slip, and the BER alignment only absorbs whole-sequence shifts. For a 30-second message the rate must be known to about **0.03 %** (one bit of drift). Days 10, 13 and 14 could not confirm it to within **40 %**, and the Day 14 beat candidates sit at 90.8–91.1 bps, 1 % from the filename. **No sampling rule, threshold or ROI choice matters until this number is right.** Block-wise re-estimation of the phase (Day 08 R8) would relax it by the block length, but there is no phase estimate to re-estimate (Day 15).

## 5b. Execution time per condition *(added 2026-09-11)*

Median of 5 runs, one lamp (1LED DEV part, 8,356 frames), `timing.py` → `timing.json`. No tested condition changes the cost by more than a factor of two, and every decode is under a millisecond; runtime is not a discriminating metric on this dataset.

| Condition | Baseline (confident) | Tuned (nearest) | Runner-up (average) |
|---|---|---|---|
| Default decode | 0.49 ms | 0.10 ms | 0.22 ms |
| Smoothing 3 / 9 frames | 0.66 / 0.68 ms | 0.18 / 0.14 ms | 0.29 / 0.29 ms |
| Threshold shift, period error | unchanged (same code path) | unchanged | unchanged |
| 12-phase ensemble (safe mask) | 4.7 ms | 0.8 ms | 2.5 ms |

ROI aggregation (brightest-25 % mean of one box, per frame): 20 µs at scale 0.5, 44 µs at 1.0, 267 µs at 2.0 — the one cost that scales with the setting (box area), and still ~8 s for the longest video at 2×.

---

## 6. In Terms of the Research Question

> *How accurately and robustly can a software-only pipeline recover an OOK message from unsynchronised video … across variation in ROI selection, ambient/exposure conditions, and symbol-timing assumptions?*

| Axis | Working range, tuned decoder (BER ≤ 1 % on the model; < 1 % of real bits change) | Baseline | Verdict |
|---|---|---|---|
| ROI size | 0.5× to 2× the detected box | 0.85× to 1.25× | Insensitive |
| ROI position | ±0.5 box width | ±0.1 | Insensitive |
| Smoothing | 1 to 3 frames | 3 only | Insensitive up to one bit length; fatal beyond |
| Threshold | ±30 % of range (noise 8); ±10 % (noise 80) | ±0 | Insensitive at the real noise level |
| Bit phase | −0.40 to +0.20 bit | −0.10 to −0.05 | Robust over 60 % of phases |
| Bit period | **±0.03 % over 3,000 bits** | same | **The one sensitivity that matters, and the one quantity not known** |
| Execution time | < 1 ms per decode under every condition (§5b) | ×5 slower, still < 1 ms | Not a discriminator |
| Ambient / exposure | not variable on this dataset (Day 08: 0.1 % drift); exposure only via the model | — | Untested on real data |

**The insight.** The pipeline is robust to everything it can control — box, smoothing, threshold, even the phase, once the sampling rule is right — and hostage to the one thing it cannot: the bit period. Every "robustness" number above is conditional on 92.000 bps being exact. The data say it is not confirmed (Day 13) and may be off by a percent (Day 14). So the honest answer to the research question on this dataset is: *accurately enough that the settings do not matter, provided the clock is known; and the clock is not known.* The next real-data step is not decoder work — it is getting the transmitted bits for one video (Q1), or the clock from the beat (Day 14 H5) to better than 0.03 %.

---

## 7. Limits

- Synthetic numbers are on the assumed model; the real videos have run lengths that model cannot produce (Day 10). Robustness of the *model* is what is measured.
- Real-data columns say how much the answer moves, never whether it is right. §2 and §4 show cases where the two disagree on which rule is better.
- Exposure was fixed at the Day 13 inference (0.3 frame); noise at two levels. The ROI sweep shifts in x only.
- Ambient-light and exposure sensitivity could not be tested on real data — the recordings have none (Day 08 §6) and cannot be re-shot (E11 remains synthetic-only, as planned on Day 05).

## 8. Files

| File | What it is |
|---|---|
| `ablation.py` | The five sweeps, both rules, one video pass for the ROI variants |
| `ablation_results.json` | Every number, per setting and rule (ROI rows are medians over the ten lamps) |
| `fig_ablation_day20.png` | Six panels: smoothing, threshold, phase, period (synthetic BER); ROI scale and shift (real) |
| `timing.py`, `timing.json` | Execution time per condition (§5b) |
