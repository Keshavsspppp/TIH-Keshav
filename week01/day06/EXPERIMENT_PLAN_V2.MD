# Experiment Plan — Version 2

**Project:** OCC Video Message Decoding
**Replaces:** `EXPERIMENT_PLAN.MD` (version 1, Day 05). Version 1 is kept for the record, not deleted.
**Read with:** `METHODOLOGY_V1.MD` (the plan), `DAY_05.MD` (workflow and folders), `EXPERIMENT_LOG.MD` (results).

> **Note (2026-09-10, audit):** `METHODOLOGY_V1.MD` is not in the repository, so the §3 checklist and §6.3 split rule it cites cannot be checked; `EXPERIMENT_LOG.MD` lives in `../day05/`. After the data arrived: E00 ran (Day 07); the DEV/TEST role split (E00, E17, E19) was replaced by a within-video time split (`../day04/DAY_04.MD` §3 note); Gate G3 in E05 could not be evaluated and Gate G4 failed (`../day05/DAY_05.MD` §5 note); the detrend/normalise settings swept in E05 and E08 were switched off on measurement (`DAY_06.MD` §2.2 note).

---

## What Changed Since Version 1

| Change | Why |
|---|---|
| Added **E00 — data readiness check** | Version 1 jumped straight to running methods. Nothing on real data counts until every video has a readiness verdict |
| Added **DEV / TEST / FAKE roles** to every experiment | Version 1 did not say which videos each experiment was allowed to touch. That is a leak waiting to happen |
| Added **E17 — leak check** | We need a run that proves the split rules were actually followed, not just written down |
| Added **E18 — timing estimate accuracy** | If faculty give us the true frame rate and symbol rate, how close our estimate gets is a result on its own |
| Split marks added to E05–E11 | These are tuning experiments. They run on DEV only. Version 1 did not say so |
| Cut order updated | E17 moved into the never-cut list |

---

## Naming

```
E<nn>-<method>-<short name>
```

Every single run gets its own `run_id` under `runs/`. The experiment ID groups them.

Each experiment now also says which data it may touch:

- **FAKE** — our own generated videos. Unlimited use.
- **DEV** — real videos we are allowed to tune on.
- **TEST** — real videos opened once, at the end. Every open is logged.

---

## Phase A — Setup and Data Readiness

### E00 — Data readiness check *(real data, no role yet)*

| | |
|---|---|
| **Goal** | Know exactly what we have before we run anything on it |
| **Steps** | Run the full checklist in `METHODOLOGY_V1.MD` §3: inventory, SHA-256, frame rate, fixed-or-variable frame rate, real frame count, resolution, codec, saturation check, stripe check, light visibility, movement, ground-truth format |
| **Output** | `data/raw/MANIFEST.csv` fully filled, plus a green / amber / red verdict per video in the log |
| **Pass mark** | Every video has a verdict. Not "most videos" — every one |
| **Then** | Assign DEV and TEST roles using the rule in `METHODOLOGY_V1.MD` §6.3, and write the TEST video IDs in the log **before** any tuning starts |
| **Why first** | If the frame rate turns out to be variable, our timing method needs changing. Finding that out in week 3 instead of day one would cost the project a week |

### E01 — Fake OOK video maker *(FAKE)*

| | |
|---|---|
| **Goal** | Make videos where we already know the bits, so we can compute BER without waiting for faculty labels |
| **Steps** | Draw a blinking bright circle on a still background. `fps ∈ {24, 30, 60}`; symbol rate chosen so `sps ∈ {2, 4, 8, 16}` plus one non-whole value like `3.7`; noise `σ ∈ {0, 2, 5, 10}` grey levels; light drift `∈ {0, ±20%}`; re-encode at `CRF ∈ {18, 23, 28}` |
| **Bits** | A fixed known message, seeded random generator, saved to `data/synthetic/<id>.json` |
| **Pass mark** | Reading the video back through stage 3 gives the pattern we put in, at `σ = 0, sps = 8` |
| **Why the 3.7 case matters** | That is where simple per-frame thresholding is supposed to fail. It is the closest fake copy of the real unsynchronised problem |

### E02 — Test the scoring code *(FAKE)*

| | |
|---|---|
| **Goal** | Check the scoring code before trusting any number from it |
| **Steps** | Test BER line-up on bit pairs with known offsets. Test that one extra inserted bit gives a high BER but a low edit distance. Test the working-range calculation on a hand-made curve |
| **Pass mark** | Everything in `tests/test_metrics.py` passes |

---

## Phase B — Baseline

### E03 — M0 on fake videos *(FAKE)*

| | |
|---|---|
| **Guess** | Near-perfect when `sps` is a whole number with no noise or drift. Falls apart with drift or a non-whole `sps` |
| **Steps** | Run M0 across the whole E01 grid |
| **Metrics** | MCR, BER, speed |
| **Pass mark** | BER under 0.01 in the clean whole-number case. Failing there means our code is broken, not the method |

### E04 — M0 on real videos *(DEV only)*

| | |
|---|---|
| **Needs** | E00 finished, and Gates G1 and G2 |
| **Steps** | Same method, DEV videos only. ROI set by hand. `sps` from faculty metadata if given, otherwise swept |
| **Metrics** | MCR, BER (where truth exists), NED, speed |
| **Pass mark** | None. This is a measurement, not a target. Total failure is still a useful baseline |
| **Do not** | Touch TEST videos here, not even to look at them |

---

## Phase C — Main Method

### E05 — Turn M1's parts on one by one *(DEV)*

| | |
|---|---|
| **Guess** | Detrending, adaptive thresholding and estimated timing each lower BER. The biggest single win is timing recovery |
| **Steps** | Start from M0 and switch on one M1 part at a time — individually and stacked |
| **Settings** | `{M0}`, `{+detrend}`, `{+normalise}`, `{+adaptive threshold}`, `{+estimated sps}`, `{+phase search}`, `{full M1}` |
| **Metrics** | BER, MCR, speed |
| **Pass mark** | Full M1 beats M0 on 60% or more of DEV videos (Gate G3) |
| **Why both ways** | Stacking alone cannot separate a part that helps from a part that just does no harm when added last |

### E06 — Does M1 find the light on its own? *(DEV)*

| | |
|---|---|
| **Guess** | The variance map finds the transmitter without hand input on most videos |
| **Steps** | Compare the auto box against the hand box from E04 |
| **Metrics** | IoU per video, share of videos above IoU 0.5, BER with auto box vs hand box |
| **Pass mark** | Auto-box BER within 20% of hand-box BER |

### E18 — How good is our timing estimate? *(FAKE + DEV)* — **new in v2**

| | |
|---|---|
| **Goal** | Measure `sps_hat` against the true `sps` wherever the truth is known |
| **Steps** | On fake videos the truth is exact. On DEV videos, use the faculty frame rate and symbol rate if they give them |
| **Metrics** | Relative error `|sps_hat − sps_true| / sps_true`, and how that error grows with noise and with clip length |
| **Why it is its own experiment** | Timing recovery is the hardest stage in the whole problem. How well we estimate it is a result worth reporting on its own, separate from whether the final message came out right |

---

## Phase D — The Sensitivity Study (our own contribution)

*Runs on DEV and FAKE. Fake and real results are always reported separately, never averaged together.*

Each sweep changes **one** setting, keeping everything else at the M1 default. Each gives a BER curve, an MCR curve, and a working range.

### E07 — ROI sensitivity *(DEV + FAKE)*

| Setting | Values |
|---|---|
| ROI size (relative to reference box) | `0.5, 0.7, 0.85, 1.0, 1.25, 1.5, 2.0` |
| ROI shift (fraction of box width, x and y) | `-0.5, -0.25, -0.1, 0, +0.1, +0.25, +0.5` |

**We report:** how far the size and position can be off with BER still under 0.01. This is the exact gap named in the Day 02 table.

### E08 — Cleaning sensitivity *(DEV + FAKE)*

| Setting | Values |
|---|---|
| Detrend window `W_d` (in bit lengths) | `2, 5, 10, 20, 50, off` |
| Smoothing window `W_s` (samples) | `1 (off), 3, 5, 7, 9` |
| Normalise window `W_n` (bit lengths) | `5, 10, 25, 50, whole signal` |

**Watch for:** when `W_s` approaches one bit length, the smoother erases the edges we are reading. Finding that exact point is a result.

### E09 — Threshold sensitivity *(DEV + FAKE)*

| Setting | Values |
|---|---|
| Threshold shift from the middle (units of std) | `-1.0, -0.5, -0.25, 0, +0.25, +0.5, +1.0` |
| Hysteresis width (units of std) | `0 (off), 0.1, 0.25, 0.5` |

### E10 — Timing sensitivity *(DEV + FAKE)*

| Setting | Values |
|---|---|
| Phase shift `φ` (bit lengths) | `-0.5` to `+0.5`, step `0.05` |
| Error in assumed `sps` | `-10%` to `+10%`, step `1%` |

**We report:** phase working range and rate working range. Expected to be the headline result.

### E11 — Condition sensitivity *(FAKE only)*

| Setting | Values |
|---|---|
| Noise `σ` | `0, 2, 5, 10, 20` |
| Light drift across the clip | `0, ±10%, ±20%, ±40%` |
| Compression CRF | `18, 23, 28, 35` |

Only possible on fake videos, because the real ones cannot be re-shot. We say that plainly rather than skipping past it.

---

## Phase E — ML Branch *(only if Gate G4 passes)*

### E12 — Check the labels *(DEV)*

Count the labelled bits, check their level (per bit / per frame / per message), and note how many separate videos they cover. This goes in the log either way. **If G4 fails, this check is the deliverable** and Phase E stops here — "we could not run it, and here is exactly why" is a valid outcome.

### E13 — Compare the models *(DEV, grouped k-fold)*

| | |
|---|---|
| **Guess** | A small classifier on brightness windows matches or beats M1's threshold, especially for bits near the middle where a threshold is least reliable |
| **Steps** | Grouped-by-video k-fold inside DEV. Logistic regression, then RBF SVM, then a small 1-D CNN. Stop at the first that beats M1 |
| **Metrics** | BER, MCR, training time, test time per video |
| **Pass mark** | Lower BER than M1 on the same held-out DEV folds |
| **Leak guard** | `train.py` asserts no `video_id` is on both sides. Failure stops the run |

### E14 — Compare how the two degrade *(DEV)*

Run the E07–E10 sweeps again with M2 making the decision instead of the threshold.

**This is what the research question actually asks.** Not which method scores better at its best settings, but which one gets worse more slowly when settings drift. A model that wins at its best point and collapses everywhere else is the weaker choice here.

---

## Phase F — Final and Reproduction

### E17 — Leak check *(all)* — **new in v2**

| | |
|---|---|
| **Goal** | Prove the split rules were followed, not just written down |
| **Steps** | For every logged run, check that: no run before the freeze date touched a TEST video; no ML fold has a `video_id` on both sides; the TEST evaluation count is 2 or fewer |
| **Output** | A pass/fail table, one row per rule, in the log |
| **If it fails** | Say so in the report and mark the affected numbers as tuning numbers. Do not quietly re-run and hope |
| **Why** | A split plan that nobody checked is just a paragraph. This turns it into a fact |

### E15 — Speed profiling *(DEV)*

Per-stage timing for M0, M1 and M2 on the same video set. Middle of 3 runs. Machine details written once in the log header. Reported as ms per frame and seconds per video.

### E19 — The single TEST evaluation *(TEST — one time only)* — **new in v2**

| | |
|---|---|
| **When** | After every method is frozen. Configs must not change after this point |
| **Steps** | Run M0, M1, and M2 if it exists, once each, on the TEST videos |
| **Output** | The numbers that go in the final report |
| **Rule** | Log the date, the run IDs and the evaluation count. If we ever have to open TEST again, that second open is logged too and reported |

### E16 — Full re-run *(all)*

Delete `runs/`, re-run every logged experiment from the config files alone, and compare the new `metrics.json` files with the old ones. Any difference is a reproducibility bug and gets its own log entry. This proves the whole workflow design works, so it gets real scheduled time, not the last hour.

---

## What to Cut First if Time Runs Out

| Priority | Experiments | Note |
|---|---|---|
| **Never cut** | E00, E01, E02, E03, E04, E05, E10, E17, E19, E16 | Readiness, setup, baseline, main method, the core timing result, the leak check, the final test, reproducibility |
| **Cut first** | E14, then E13, then E12 | The ML branch was always conditional. Not running it is a documented outcome, not a failure |
| **Cut second** | E11, then E08 | Shrink the grids rather than dropping them |
| **Shrink, do not drop** | E07, E09, E18 | These are our stated contribution. Fewer grid points, but the experiment stays |

---

## Schedule (rough, depends on the dataset)

| Week | Experiments | Note |
|---|---|---|
| 2 | E01, E02, E03 | Needs no dataset |
| 2 | E00 | The day the dataset lands, before anything else |
| 2–3 | E04, E05, E06, E18 | DEV only |
| 3 | E07–E11 | The sensitivity study. Longest to run |
| 3–4 | E12–E14 | Only if Gate G4 passes |
| 4 | E15, E17, E19, E16, report | Leak check before the final test. Final test before the report. Re-run with spare time, not at the last minute |

**Order rule for week 4:** leak check first, then the single TEST run, then the report. Running TEST before the leak check would mean finding a problem after the number we cannot un-see.
