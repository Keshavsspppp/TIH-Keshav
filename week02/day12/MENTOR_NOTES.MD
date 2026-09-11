# Mentor Notes — Day 12 Signal Pipeline Review

**Status: not recorded at the time.** `DAY_12_SIGNAL_V1.MD` §4 asks for three approvals; no decision or correction is recorded. Template added 2026-09-11; nothing filled in on the author's behalf.

| | |
|---|---|
| Date of review | |
| Mentor | |

## Presented

- Selected ROI — `../day09/DAY_09_ROI_SIGNAL_PLAN.MD` §1, `../day09/fig_roi.png`, candidate comparison `../day09/ROI_CANDIDATES.MD`
- Preprocessing pipeline — `../day11/occ_pipeline.py`, `../day11/configs/preprocess_v1.yaml`
- Extracted signal and plots — `signal_v1/`, `../day11/fig_signals.png`, `fig_ablation.png`

## Choices defended (§2) and the mentor's view

| Choice | Our evidence | Mentor correction |
|---|---|---|
| ROI selection | Days 09–10; `ROI_CANDIDATES.MD` | |
| Smoothing off | 27 % of transitions deleted at window 3 | |
| Normalisation off | separation halves; no drift to remove | |
| Aggregation — brightest 25 % | Day 10 §2 | |
| Trim on sustained activity | Day 08 R1 | |

## Items for approval (§4)

| Item | Decision |
|---|---|
| Extraction pipeline | |
| Cleaning off | |
| Signal V1 as frozen | |

## Corrections incorporated before the freeze

*(none recorded)*
