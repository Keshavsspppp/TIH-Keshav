# Experiment Plan

**Project:** OCC Video Message Decoding

**Read with:** `DAY_05.MD` (the workflow, methods, metrics, folders) and `EXPERIMENT_LOG.MD` (what actually happened).

Every experiment below has an ID, a guess about what will happen, the steps, and a pass mark. All of these are written **before** the experiment runs. If an experiment has no pass mark written first, we do not count its result as evidence.

---

## Naming

```
E<nn>-<method>-<short name>
```

For example: `E02-M0-baseline-all`, `E05-M1-sweep-timing`, `E07-M2-grouped-cv`.

Every single run gets its own `run_id` inside `runs/`. The experiment ID groups those runs together. The mapping is kept in the log index.

---

## Phase A — Build the Setup and Make Our Own Ground Truth

*This runs before the dataset arrives. Goal: have a working, tested pipeline ready on the day the real videos land.*

### E01 — Fake OOK video maker

| | |
|---|---|
| **Goal** | Make videos where we already know the bits, so we can compute BER without waiting for faculty labels |
| **Steps** | Draw a blinking bright circle on a still background. Settings: `fps ∈ {24, 30, 60}`; symbol rate chosen so `sps ∈ {2, 4, 8, 16}` plus one non-whole number like `sps = 3.7`; noise `σ ∈ {0, 2, 5, 10}` grey levels; slow light drift `∈ {0, ±20%}`; H.264 re-encode at `CRF ∈ {18, 23, 28}` |
| **Bits** | A fixed known ASCII message, seeded random generator, saved to `data/synthetic/<id>.json` |
| **Pass mark** | When we read the video back through stage 3, the brightness pattern matches the bits we put in, at `σ = 0, sps = 8` |
| **Why it matters** | The `sps = 3.7` case is the key one. That is where simple per-frame thresholding is supposed to fail, and it is the closest fake copy of the real unsynchronised problem |

### E02 — Test the scoring code

| | |
|---|---|
| **Goal** | Check the scoring code before we trust any number it gives us |
| **Steps** | Test BER lining-up on bit pairs with known offsets. Test that adding one extra bit gives a high BER but a low edit distance. Test the working-range calculation on a hand-made curve |
| **Pass mark** | Everything in `tests/test_metrics.py` passes |

---

## Phase B — Baseline

### E03 — M0 fixed threshold on fake videos

| | |
|---|---|
| **Guess** | M0 will decode almost perfectly when `sps` is a whole number with no noise and no drift, and will fall apart quickly once we add drift or a non-whole `sps` |
| **Steps** | Run M0 across the whole E01 grid, one run per setting |
| **Metrics** | MCR, BER, speed |
| **Pass mark** | BER below 0.01 in the clean whole-number `sps` case. If it fails there, the bug is in our setup, not in the method |
| **Output** | A table of BER for each `(sps, σ, drift, CRF)`. This is the reference every later method is compared to |

### E04 — M0 on the faculty dataset

| | |
|---|---|
| **Needs** | Gates G1 and G2 from `DAY_05.MD` §5 |
| **Steps** | Same method, real videos. ROI set by hand per video. `sps` from faculty metadata if we get it, otherwise swept |
| **Metrics** | MCR, BER (where truth exists), NED, speed |
| **Pass mark** | None. This is a measurement, not a target. Even total failure is a useful baseline result |

---

## Phase C — The Main Method

### E05 — Turn M1's parts on one by one

| | |
|---|---|
| **Guess** | Detrending, adaptive thresholding, and estimating the timing each lower the BER. The biggest single win comes from timing recovery |
| **Steps** | Start from M0 and switch on one M1 part at a time — both one at a time on its own, and stacked up |
| **Settings** | `{M0}`, `{+detrend}`, `{+normalise}`, `{+adaptive threshold}`, `{+estimated sps}`, `{+phase search}`, `{full M1}` |
| **Metrics** | BER, MCR, speed for each setting |
| **Pass mark** | Full M1 has lower BER than M0 on 60% or more of the videos (Gate G3) |
| **Why both ways** | Stacking alone cannot tell the difference between a part that helps and a part that just does no harm when added last |

### E06 — How well M1 finds the light on its own

| | |
|---|---|
| **Guess** | The variance map finds the transmitter without any hand input on most videos |
| **Steps** | Compare the auto box against the hand-drawn box from E04 |
| **Metrics** | IoU per video, how many videos have IoU above 0.5, and BER with auto box vs hand box |
| **Pass mark** | Auto-box BER is within 20% of hand-box BER |

---

## Phase D — Our Own Sensitivity Study

*This is the project's real contribution (`DAY_05.MD` §3). It runs on both fake and real videos. We always report the two separately and never mix them.*

Each sweep changes **one** setting and keeps everything else at the M1 default. Each sweep gives us: a BER curve, an MCR curve, and a working range.

### E07 — ROI sensitivity

| Setting | Values |
|---|---|
| ROI size (compared to the reference box) | `0.5, 0.7, 0.85, 1.0, 1.25, 1.5, 2.0` |
| ROI shift (as a fraction of box width, in x and y) | `-0.5, -0.25, -0.1, 0, +0.1, +0.25, +0.5` |

**We report:** how far the size and position can be off while BER stays under 0.01. This is exactly the gap noted in the Day 02 table — older work reports how well it decodes, but not how much ROI error it can survive.

### E08 — Cleaning sensitivity

| Setting | Values |
|---|---|
| Detrend window `W_d` (in bit lengths) | `2, 5, 10, 20, 50, off` |
| Smoothing window `W_s` (in samples) | `1 (off), 3, 5, 7, 9` |
| Normalise window `W_n` (in bit lengths) | `5, 10, 25, 50, whole signal` |

**Watch for this:** when `W_s` gets close to one bit length, the smoother erases the very edges we are trying to read. Finding exactly where that happens is a result worth writing up.

### E09 — Threshold sensitivity

| Setting | Values |
|---|---|
| Threshold shift away from the middle (in units of signal std) | `-1.0, -0.5, -0.25, 0, +0.25, +0.5, +1.0` |
| Hysteresis width (in units of std) | `0 (off), 0.1, 0.25, 0.5` |

### E10 — Timing sensitivity

| Setting | Values |
|---|---|
| Phase shift `φ` (in bit lengths) | `-0.5` to `+0.5`, step `0.05` |
| Error in assumed `sps` | `-10%` to `+10%`, step `1%` |

**We report:** the phase working range and the rate working range, as defined in `DAY_05.MD` §4.3. We expect this to be the headline robustness result, because the problem statement already says timing recovery is the hardest stage.

### E11 — Condition sensitivity (fake videos only)

| Setting | Values |
|---|---|
| Noise `σ` (grey levels) | `0, 2, 5, 10, 20` |
| Light drift across the clip | `0, ±10%, ±20%, ±40%` |
| Compression CRF | `18, 23, 28, 35` |

This only works on fake videos, because we cannot re-shoot the real ones under controlled conditions. We say that plainly in the write-up instead of skipping over it.

---

## Phase E — ML Classifier (only if Gate G4 passes)

### E12 — Check the labels

Before any training: count how many labelled bits we have, check what level they are at (per bit / per frame / per message), and note how many separate videos they come from. This goes in the log either way. If G4 fails, this check **is** the deliverable and Phase E stops here.

### E13 — Compare the models

| | |
|---|---|
| **Guess** | A small classifier on brightness windows will match or beat M1's threshold, especially for bits that sit close to the middle where a threshold is least reliable |
| **Steps** | Grouped-by-video k-fold on the training videos. Try logistic regression, then RBF SVM, then a small 1-D CNN. Stop at the first one that beats M1 |
| **Metrics** | BER, MCR, training time, test time per video |
| **Pass mark** | Lower BER than M1 on the same held-out videos |
| **Leak guard** | `train.py` asserts that no `video_id` is in both train and test. If it fails, it stops the run — it is not just a warning |

### E14 — Compare how the two degrade

Run the E07–E10 sweeps again, but with M2 making the decisions instead.

**This is the comparison the research question actually asks for.** Not just which method scores better at its best settings, but which one falls off more slowly when the settings drift. A model that wins at its best point and collapses everywhere else is the weaker choice here, and this experiment is what would show it.

---

## Phase F — Wrap Up

### E15 — Speed profiling

Per-stage timing for M0, M1, and M2 on the same set of videos. Middle of 3 runs. Machine details written down once. Report as ms per frame and seconds per video.

### E16 — Full re-run

Delete `runs/`, re-run every logged experiment using only the config files, and compare the new `metrics.json` files against the old ones. Any difference is a reproducibility bug and gets its own log entry. This is the experiment that proves the whole workflow design works, so it gets real time in the schedule and is not squeezed into the last day.

---

## What to Cut First if Time Runs Out

We decide the cut order now, not later when we are panicking.

1. **Never cut:** E01, E02, E03, E04, E05, E10, E16 — the setup, the baseline, the main method, the core timing result, and reproducibility.
2. **Cut first:** E14, then E13, then E12. The whole ML branch was always conditional, and "we could not run it, here is why" is already a valid outcome.
3. **Cut second:** E11 and E08. Make the grids smaller instead of dropping them entirely.
4. **Shrink, do not drop:** E07 and E09. The ROI and threshold ranges are the project's stated contribution. Reduce the number of grid points before removing the experiment.

---

## Schedule (rough, depends on the dataset)

| Week | Experiments | Note |
|---|---|---|
| 2 | E01, E02, E03 | Needs no dataset at all |
| 2–3 | E04, E05, E06 | Starts the day the dataset arrives |
| 3 | E07–E11 | The sensitivity study. Takes the longest to run |
| 3–4 | E12–E14 | Only if Gate G4 passes |
| 4 | E15, E16, report | The re-run gets spare time, not the last hour |
