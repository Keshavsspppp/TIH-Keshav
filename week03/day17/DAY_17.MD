# Day 17 — ML-Assisted Symbol Decision

**Project:** Optical Camera Communication (OCC) Video Message Decoding
**Built:** M2, the ML-assisted symbol classifier from the Day 05 plan — a logistic regression on the frames around each bit window — and the shared library `occlib.py` that Days 17–21 all use.
**Files:** `occlib.py`, `ml_decoder.py`, `ml_report.json`, `ml_model_synthetic.json`, `ml_model_real_pseudo.json`, `fig_ml.png`.

**Read this first.** The task says "where labels permit". They do not: no ground truth was supplied for any video, so there are no labels, and "do not use the final-message content as labels" cannot arise. The classifier is therefore trained and scored in two separate ways, and the two are never mixed:

| | Labels | What the score means |
|---|---|---|
| **A. Synthetic** | True bits, from `occlib.synth` (the *assumed* 92 bps model with the measured contrast 245 and noise 6–11) | A real BER — but of the model, not of the videos |
| **B. Real, DEV part** | The threshold decoder's own phase-independent ("safe", Day 16) bits, first 30 % of each lamp, leave-one-lamp-out | **Agreement with the threshold decoder.** Not correctness. Day 05 §2 predicted this makes M2 copy M1; it does |

The last 70 % of every real signal (TEST) is not touched on Days 17–20.

---

## 1. What Was Built

**Features per bit window** (phase-0 convention, Day 16): the five frames from one before the window start to three after, as `(value − threshold) / range`, plus the fractional position of the window start inside a frame. Six numbers. The last one tells the classifier where the frame grid sits relative to the assumed bit grid — the information the "most confident frame" rule throws away.

**Model:** `sklearn` logistic regression, `C = 1`. The Day 05 plan said "logistic regression, then RBF SVM, then a small 1-D CNN; stop at the first one that beats M1". Logistic regression beat the threshold rule in the only setting where beating it is measurable (§2), so nothing further was tried.

**Saved candidate:** `ml_model_synthetic.json` (weights, intercept, feature definition — 7 numbers) and `ml_model_real_pseudo.json` (same, trained on the real DEV safe bits). Either is applied by `ml_decoder.features()` + a dot product.

**Also built:** `occlib.py` — Signal V1 loader, the DEV/TEST split, the vectorised Day 15/16 decoder with three sampling rules, the phase ensemble and safe mask, the internal-consistency indicators, the synthetic generator and the BER scorer. Its `__main__` self-check confirms it reproduces Day 16's 40.82 % safe bits on `1LED`.

---

## 2. A — Synthetic, True Labels

BER in %, mean of four test streams of 3,000 bits each, phases drawn at random. "true phase" = both decoders told the bit phase (decision quality alone). "phase 0" = both use the Day 16 convention (the realistic case).

| Noise | Exposure | Threshold @ true | Threshold + end margin @ true | **ML @ true** | Threshold @ phase 0 | **ML @ phase 0** |
|---|---|---|---|---|---|---|
| 8 | 0.3 | 0.025 | 0.000 | **0.000** | 18.8 | **13.3** |
| 8 | 1.0 | 0.567 | 0.000 | **0.000** | 0.23 | 0.25 |
| 40 | 0.3 | 0.625 | 0.000 | **0.000** | 17.1 | **12.0** |
| 40 | 1.0 | 2.434 | 0.150 | **0.000** | 7.5 | **4.5** |
| 80 | 0.3 | 2.292 | 1.100 | 1.225 | 12.0 | 11.4 |
| 80 | 1.0 | 5.385 | 2.434 | **1.350** | 8.5 | 11.1 |
| 110 | 0.3 | 5.310 | 4.435 | 4.518 | 13.2 | 11.1 |
| 110 | 1.0 | 9.153 | 6.802 | **5.152** | 16.2 | 14.3 |

Real data sits at noise 6–11 and exposure ≈ 0.3 (Day 13), i.e. the first row.

### Three things this says

**1. With the phase known, the classifier is better than the threshold rule, but the threshold rule's errors were mostly a bug.** Building the synthetic generator exposed it: the Day 15/16 bit window runs to `floor(start + T)`, and with a short exposure that last frame often exposes *inside the next bit*. Trimming 0.3 frame off the end of every window ("end margin", now a parameter in `occlib.decode`) takes the threshold rule from 0.025 % to 0.000 % at the real-data noise level and roughly halves its errors everywhere else. That is a transition-handling fix, not a modelling one, and it is the first thing Day 19 tunes.

**2. With the phase unknown, nothing decodes well, and the classifier's edge is small.** At the real-data settings both decoders sit at 13–19 % BER, all of it from the phase. The classifier's `frac` feature buys about a third of that back (18.8 → 13.3 %), which is worth having but is not a solution. Days 13, 15 and 16 stand: the phase is the problem.

**3. The phase problem is a short-exposure problem.** At exposure 1.0 and low noise, decoding at the wrong phase costs almost nothing (0.23 %), because every transition then leaves an intermediate frame and the confident rule always finds a clean one inside the true bit. At exposure 0.3 there are no intermediate frames (Day 16 §2 measured 5 %), so a wrong phase is invisible and fatal. This is the mechanism behind the Day 16 sub-frame failure, now shown on data where the answer is known.

---

## 3. B — Real DEV Part, Pseudo-Labels

Trained on the safe bits of nine lamps, scored on the tenth. Agreement with the threshold decoder's phase-0 bits, in %.

| Lamp | On phase-independent bits | On phase-dependent bits | ML "confident" (p > 0.95) |
|---|---|---|---|
| 1LED L1 | 96.98 | 50.2 | 67.8 |
| 2LEDs L1 / L2 | 97.30 / 96.33 | 54.5 / 49.7 | 72.9 / 70.2 |
| 3LEDs L1–L3 | 95.19 / 95.28 / 97.35 | 48.2 / 45.6 / 48.6 | 69.1 / 67.3 / 62.5 |
| 4LEDs L1–L4 | 98.51 / 96.98 / 98.38 / 97.32 | 54.1 / 51.5 / 53.8 / 48.8 | 75.9 / 75.9 / 78.1 / 74.7 |

**On the bits the threshold decoder is sure of, the classifier agrees 95–99 %.** It was trained on exactly those bits from other lamps, so this is a consistency check, not evidence of anything.

**On the bits the threshold decoder is *not* sure of, agreement is 46–55 % — a coin toss.** This is the honest result of the day. The classifier has the same six numbers per bit the threshold rule has; for a phase-dependent bit those numbers do not determine the answer, and no model can conjure a label from them. It does report high confidence on 62–78 % of bits, well above the 44 % that are actually phase-independent: that extra confidence is calibration on the training distribution, not knowledge.

---

## 4. Verdict Against the Threshold Baseline

| Question | Answer | Evidence |
|---|---|---|
| Does M2 beat M0/M1 where correctness is measurable? | Yes, at the true phase; marginally at phase 0 | §2, synthetic only |
| Does M2 beat them on the real videos? | **Unknowable** — no ground truth; on phase-dependent bits it agrees with M1 at chance level | §3 |
| Does M2 change the phase problem? | No. It inherits it | §2 rows "phase 0" |
| Cost | Training 0.1 s; prediction ≈ 1 ms per 1,000 bits; six features | `ml_report.json` meta |

**Recommendation for Day 18:** carry M2 forward as a candidate for the comparison table, but the strongest *fixable* lead found today is the end-margin bug in the threshold rule, which affects M0, M1 and v2 alike. The comparison should include the threshold rule both as it was (Day 16) and with the fix.

---

## 5. Limits, Stated

- The synthetic model has a clean 92 bps clock. The real videos contain run lengths that model cannot produce (Day 10), so §2 measures how methods decode the *assumed* signal, not the videos.
- §3's labels are the threshold decoder's own output. If the threshold decoder is wrong about a safe bit, the classifier was trained to be wrong the same way.
- Logistic regression only. Given §3, a bigger model would learn the same coin toss with more parameters.
- The 92 bps period is still the filename's number (Days 10, 13).

---

## 6. Files

| File | What it is |
|---|---|
| `occlib.py` | Shared library for Days 17–21; `python occlib.py` runs its self-check |
| `ml_decoder.py` | Experiments A and B, model saving, figure |
| `ml_report.json` | Every number above, plus timings |
| `ml_model_synthetic.json`, `ml_model_real_pseudo.json` | The saved candidate decision logic (weights + feature definition) |
| `fig_ml.png` | Left: BER vs noise, four decoders. Right: agreement on safe vs unsafe bits per lamp |
