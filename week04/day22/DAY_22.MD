# Day 22 — Final Model / Pipeline Freeze

**Project:** Optical Camera Communication (OCC) Video Message Decoding
**Files:** `final_pipeline.py` (the frozen end-to-end pipeline), `FINAL_CONFIG.json` (every frozen setting), `FROZEN_MANIFEST.json` (SHA-256 of every artefact), `final_outputs/` (representative final outputs, all four videos), `CHANGES_AFTER_FREEZE.MD` (empty log for anything that changes after today).

**Status: FROZEN as of 2026-09-11.** From here on, any change to the pipeline, its configuration or its evaluation is written in `CHANGES_AFTER_FREEZE.MD` with a reason, and re-validated if it touches a result. The held-out TEST data played no part in today's selection.

---

## 1. The final method

| Component | Frozen value | Source |
|---|---|---|
| Frame extraction | every frame, brightest pixel per frame for trimming | Day 11 |
| Trim | sustained activity: 1-s window, ≥ 15 % lit, level 180; start at the first lit frame | Days 08, 11 |
| ROI | behaviour clustering on 600 frames spread across the transmission, one box per lamp, k-means seeded 1337, fill ≥ 0.40, share ≥ 0.25 | Days 09, 11 |
| Signal | mean of the brightest 25 % of pixels in the box, one value per frame | Day 10 |
| Preprocessing | **none** — detrend, normalise, smooth all off | Day 12 |
| Synchronisation | period 260/92 = 2.826 frames (**assumed**, from the filename); phase 0 by **convention** | Days 13, 15, 16 |
| Symbol decision | fixed threshold = midpoint of 10th/90th percentiles; **nearest frame to the bit centre**; 12-phase ensemble → per-bit safe mask | Days 16, 19 |
| Output | per lamp: bit string, safe-masked bit string (`?` = phase-dependent), signal, indicators | Day 16 |
| Split | within-video: first 30 % DEV, last 70 % TEST (opened once, Day 21) | Day 07 |
| Evaluation | real: safe share, phase stability, threshold tolerance, agreement, runtime; synthetic: BER at true / phase 0, phase band, period band | Days 18–21 |

One command runs all of it: `python final_pipeline.py --raw ../../data/raw --out final_outputs` (100 s for the four videos). Verified today: the signals it extracts are **byte-identical** to the frozen Signal V1, and the bits are **identical** to the Day 21 decoder's.

## 2. Why this method — against the five selection criteria, on validation evidence only

| Criterion | Evidence | Where |
|---|---|---|
| **Validation performance** | Nearest-frame rule: 6.19 % BER at an unknown phase on the validation streams, vs 12.05 % for the Day 09 rule and 7.00 % for the best classifier. Over a uniform phase sweep: 4.82 % (nearest) ≈ 4.79 % (average) vs 11.08 % (confident) | Day 19 §2, Day 21 §3 |
| **Robustness** | Phase band 0.65 bit vs 0.15; threshold tolerance 99.8 % vs 75 %; < 1 % of bits change for a box 0.5–2× or shifted half a width; 3-frame smoothing harmless | Day 20 §1–4 |
| **Generalisation** | Same behaviour on all ten lamps of all four videos (safe share 34–38 %, phase stability 87–88 %, threshold tolerance 99.0–99.9 %). This is consistency across four setups; no generalisation beyond them can be claimed | Day 18 §2.4, Day 21 §1.2 |
| **Simplicity / interpretability** | One sample per bit, one threshold, zero fitted parameters. Every decision can be read off the plot of the signal (`../../week03/day15/fig_decisions.png` shows the mechanism) | Day 19 §3 |
| **Computational complexity** | 0.10 ms per 8,356-frame decode; 0.8 ms for the 12-phase mask; the whole run is dominated by reading video (≈ 30 s per video) | Day 20 §5b |

## 3. Why the alternatives were rejected

| Alternative | Rejected because | Evidence |
|---|---|---|
| **Most-confident-frame rule** (Day 09 choice, Days 15–16 decoder) | Worst of three at an unknown phase (12 %); follows the threshold — a 10 % shift flips a quarter of its bits; its window over-reaches into the next bit | Day 19 §2, Day 20 §3, Day 17 §2 |
| **Average-over-window rule** | Equivalent to nearest on the phase axis (identical 0.65-bit band) and better under heavy noise at the true phase (1.5 % vs 6.7 % at noise 80) — but it is threshold-sensitive at the window ends (97.3 % vs 99.8 %), slightly more code, and the noise regime where it wins (10× the real noise) does not occur in this dataset. A tie broken on simplicity; either would be defensible | Day 21 §3 |
| **Adaptive threshold** | Identical to the fixed threshold on every indicator (the lamp level moves 0.13 grey levels per recording), three times slower | Day 18 F6 |
| **End margin > 0** | Helps only the confident rule; the nearest rule never looks at the window end | Day 19 §2 |
| **Logistic-regression classifier (M2)** | Best synthetic phase tolerance (0.37 bit at Day 18; 0.20 in tuning) but never beats the nearest rule at phase 0, disagrees with the threshold on 19 % of real bits where nothing can say which is right, and inherits the phase problem entirely. Six fitted parameters for no measurable gain | Days 17 §3, 18 F3, 19 §2 |
| **Detrend / normalise / smooth** | Every option lowers the on/off separation; smoothing ≥ 5 frames destroys decoding | Days 12, 20 §2 |
| **Estimated phase** (Day 15 v1) | The estimate is floating-point noise — the score is flat across phase | Day 15 §3 |
| **A different bit rate** | No rate shows clock structure (Day 13); the Day 14 beat candidates (≈ 82, 91, 124, 136 bps) are not confirmed; changing the rate without evidence would be a methodological change based on nothing. The filename's value stays, labelled as an assumption | Days 13, 14, 20 §5 |

## 4. What limitations remain

1. **No correctness measurement exists for any real bit.** No ground truth was supplied. Every real-data number in this project is an internal-consistency indicator; the only BERs are on synthetic signals of the assumed model.
2. **The bit period is an assumption the data argue against.** 22–27 % of level-change runs are impossible at 92 bps (Day 10); the level changes fit a 92 bps grid 0.3 % better than random times (Day 13). A 0.2 % rate error makes the decoded stream a coin toss over 3,000 bits (Day 20). This is the single limitation that dominates all others.
3. **The phase is a convention.** The final decoder is right across about 60 % of possible phases on the model; on the videos we do not know which case applies. About 35 % of the output bits are phase-independent (the safe mask); the rest are provisional.
4. **The framing above the raw bits is unknown.** The bits are not text and not Manchester (Day 7); no message can be produced.
5. **Four videos, four setups.** Consistency across them is shown; generalisation to other cameras, lamps or distances is not.
6. **The noise regime is narrow.** Real noise is 6–11 grey levels; the nearest rule is worse than the alternatives at 10× that noise with the phase known, which does not occur here.
7. **Two artefacts are reconstructions**, labelled as such: `preprocess_v1.yaml` and `METHODOLOGY_V1.MD`. The config reproduces Signal V1 byte-for-byte, so the reconstruction is exact in effect.

## 5. Representative final outputs

`final_outputs/<video>/`: `lampN_bits.txt` (the full provisional bit string), `lampN_safe_bits.txt` (the same string with phase-dependent bits replaced by `?` — the only bits that should be quoted), `lampN_signal.npy`, `summary.json` (boxes, counts, fingerprints, indicators, stage timings). 46,362 bits over ten lamps; 35.4 % phase-independent on average. First 200 characters of `1LED` lamp 1, safe-masked:

```
1????0???0??0????0??????00????1?0?0????000??1??????11??1???1??00???0?????1??????1????0???0??????0??0?0?0000??1??11???1?1?????0?????1?0???0?1??0??11??1?????1?0?00???0????111????110????000???1???????0??
```

That string is the honest deliverable of the project: what can be read without knowing the phase, and how much cannot.

## 6. Reproducibility artefacts

| Artefact | Role |
|---|---|
| `final_pipeline.py` | The frozen pipeline, one entry point, stage timings |
| `FINAL_CONFIG.json` | Every frozen setting with its basis |
| `FROZEN_MANIFEST.json` | SHA-256 of the pipeline, its two dependencies (`occ_pipeline.py`, `occlib.py`), the config, the Signal V1 manifest and every output file — 41 artefacts |
| `../../week02/day12/signal_v1/` | The frozen signal set the pipeline reproduces |
| `../../week03/day19/best_config.json` | The validated selection this freeze implements |
| `../../requirements.txt` | The environment |
| `CHANGES_AFTER_FREEZE.MD` | Empty today. Anything that changes after the freeze is written there first |
