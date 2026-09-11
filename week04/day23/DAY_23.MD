# Day 23 — Software Performance and Final Validation

**Project:** Optical Camera Communication (OCC) Video Message Decoding
**Files:** `Day23_Final_Validation.ipynb` (executed; built by `build_day23.py`), `final_validation.json`, `fig_tradeoff.png`.
**Pipeline:** the Day 22 freeze, hash-verified in the notebook's first cell. Nothing changed.

## Performance measurements

| Measure | Value |
|---|---|
| End-to-end, all four videos (75,305 frames) | 98.2 s — 1.30 ms per frame |
| Frame extraction (trim pass) | 26.4 s |
| ROI selection (600-frame stack + k-means) | 22.1 s |
| Signal extraction (brightest-25 % mean, every frame) | 49.5 s |
| Preprocessing | 0 s (off) |
| Synchronisation + decision, all ten lamps | 0.15 s |
| Decode only, 27,856 samples: final / baseline | 0.14 ms / 0.61 ms |
| 12-phase safe mask, 27,856 samples | 1.74 ms |
| Model size | no fitted parameters; 4 settings; `FINAL_CONFIG.json` 4484 bytes; 783 lines of code across three files |
| Memory | ROI sample stack 138 MB (the peak), one frame (0.69 MB) at a time otherwise; process RSS 120 MB in the notebook |

The pipeline is I/O-bound: reading and aggregating video is about three quarters of the runtime, the ROI search most of the rest, the decision a millisecond.

## Final validation on TEST

Identical to the Day 21 opening for every lamp and every indicator (asserted in the notebook). Medians over ten lamps:

| | Baseline (fixed threshold, confident) | Final (fixed threshold, nearest) |
|---|---|---|
| Phase-independent bits | 44.4 % | 35.6 % |
| Phase stability | 89.6 % | 87.6 % |
| Threshold tolerance | 75.2 % | **99.8 %** |
| Synthetic BER @ phase 0 / true, noise 8 | 12.71 % / 0.208 % | **5.56 % / 0.000 %** |
| Phase tolerance band | 0.10 bit | **0.61 bit** |
| Agreement between the two on TEST | 79.2 % | |

Message correctness and real-data BER: not measurable — no ground truth. The lower "safe" share of the final method is expected and is not a regression (Day 19 §3: the indicator ranks the rules backwards where a BER exists).

## Trade-off

No accuracy-versus-cost trade exists on this dataset: the final method is the simplest, the fastest, the most robust to threshold and ROI, and best or tied-best at an unknown phase (`fig_tradeoff.png`). What limits decoding quality is not a method choice but the unknown bit period and phase.
