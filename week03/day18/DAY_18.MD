# Day 18 — Method Comparison and Mentor Review

**Project:** Optical Camera Communication (OCC) Video Message Decoding
**Files:** `compare_methods.py`, `comparison.json`, `comparison.md`, this file (the 3-slide pack is §1 — written as three Markdown slides rather than a PDF like Days 03 and 09).
**Data:** DEV part (first 30 %) of every Signal V1 lamp; synthetic streams from `occlib.synth`. TEST (last 70 %) untouched.

---

## 1. Progress Pack (3 slides)

### Slide 1 — Completed work, Days 15–17

- **Threshold decoders** (Day 15): fixed and adaptive, most-confident-frame sampling, 46,372 preliminary bits at the assumed 92 bps.
- **Decoder v2** (Day 16): phase declared a convention, not an estimate; per-bit "safe" mask — about 44 % of every stream is decided whatever the phase.
- **ML symbol classifier** (Day 17): logistic regression on six features per bit window. Trained on synthetic true labels (the only labels that exist) and separately on the threshold decoder's own safe bits.
- **A bug found and fixed** (Day 17): the bit window reached one frame into the next bit. A 0.3-frame end margin takes the threshold rule's synthetic BER at the true phase from 0.06 % to 0.00 %.
- One comparison over all four methods, same inputs, same metrics, timed (this pack).

### Slide 2 — The comparison

| Method | BER synth, true phase / phase 0 | Phase tolerance (bits, BER ≤ 1 %) | Period tolerance | Safe bits (real) | Threshold tolerance (real) | Agrees with M0 | Time |
|---|---|---|---|---|---|---|---|
| M0 fixed threshold | 0.058 % / 9.5 % | 0.10 | 0 % | 43.6 % | 76.0 % | — | 0.1 ms / 1k frames |
| M1 adaptive threshold | 0.050 % / 9.5 % | 0.10 | 0 % | 44.0 % | 76.0 % | 98.7 % | 0.3 |
| **M0 + end margin** | **0.000 % / 8.6 %** | 0.20 | 0 % | 39.7 % | 80.0 % | 95.9 % | 0.1 |
| **M2 ML classifier** | **0.000 % / 7.4 %** | **0.37** | 0 % | 49.7 % | 87.2 % | 80.7 % | 0.1 |

Message correctness and real-data BER: **not measurable, no ground truth.** Real-data columns are internal-consistency indicators.

**Read across, not down.** At the true phase every method is near-perfect on synthetic data and the differences are the window bug. At phase 0 — the real situation — every method loses 7–10 % of bits to the unknown phase, and no method tolerates a 1 % error in the assumed bit rate.

### Slide 3 — Shortlist and what we need

**Shortlisted for Day 19–20:**
1. **M0 + end margin** — simplest method with zero synthetic BER at the true phase; the fix helps every threshold variant; 4 parameters to tune.
2. **M2 classifier** — widest phase tolerance (0.37 bit) and lowest phase-0 BER on synthetic data; but it disagrees with M0 on 19 % of real bits and nothing can say which is right.

**Dropped:** M1 adaptive threshold — identical to M0 on every indicator, three times slower, nothing to adapt to (lamp level moves 0.13 grey levels per recording, Day 08).

**Still blocking, five weeks old:** Q1 — the transmitted bits for one video. It would turn every "agrees with M0" into a BER and settle the phase in one step.

---

## 2. The Comparison, in Full

`comparison.json` holds every number per lamp; `comparison.md` the summary table. Medians over the ten lamps' DEV parts; synthetic figures are means over four 3,000-bit streams with random phases.

### 2.1 What each column measures, and for which data

| Column | Data | Measures | Is it correctness? |
|---|---|---|---|
| Decoded-message correctness | — | — | Not available: no message is known |
| BER (real) | — | — | Not available: no bits are known |
| BER synth @ true phase | synthetic | decision quality when the timing is known | Yes, of the *model* |
| BER synth @ phase 0 | synthetic | what the decoder actually produces when the phase is unknown | Yes, of the model |
| Phase tolerance | synthetic | width of the band of phase offsets around the truth where BER ≤ 1 % | Yes, of the model |
| Period tolerance | synthetic | band of assumed-period errors where BER ≤ 1 % over 500 bits | Yes, of the model |
| Safe bits | real DEV | share of bits identical at all 12 phases | **No** — consistency |
| Phase stability | real DEV | bits unchanged under a ±0.15-bit shift | **No** — consistency |
| Threshold tolerance | real DEV | bits unchanged when the threshold moves ±10 % of range | **No** — consistency |
| Agrees with M0 | real DEV | bits identical to M0's | **No** |
| Time | real DEV | ms per 1,000 frames, single decode | — |

### 2.2 Findings

**F1. The methods do not differ where it matters.** At phase 0 all four sit at 7–10 % synthetic BER; on real data all four have 40–50 % safe bits and 89–92 % phase stability. The unrecoverable phase (Day 13) dominates every method equally.

**F2. The end-margin fix is real and cheap.** It removes all of the threshold rule's true-phase errors at the real-data noise level, halves them at noise 80, doubles the phase tolerance (0.10 → 0.20 bit) and raises real-data threshold tolerance from 76 % to 80 %. It changes 4 % of the real bits. It costs nothing.

**F3. M2 has the best synthetic numbers and the least checkable real ones.** 0.37-bit phase tolerance is the widest by far, and 7.4 % at phase 0 is the lowest. But on real data it disagrees with M0 on 19 % of bits; Day 17 §3 showed that on phase-dependent bits its agreement with the threshold is a coin toss. Its 49.7 % "safe" share is higher than M0's because the classifier's decisions move less with phase — not because more of them are right.

**F4. Threshold tolerance is worse than Day 09 assumed.** Moving the threshold by 10 % of the range flips about a quarter of the bits under the most-confident-frame rule (76 % unchanged). Day 09 §2 flagged exactly this risk ("if the threshold itself is badly placed, this rule will confidently follow it") and scheduled test E09b, which was never run. It is now on the Day 20 list. The mechanism: in a window containing frames of both levels, which frame is "most confident" depends on which side of the midpoint the threshold sits.

**F5. Period tolerance is zero for every method.** A 1 % error in the assumed 92 bps drifts one bit every 100 bits; over 500 bits that is a 5-bit slip and the BER criterion fails. The rate must be right to about 0.2 % for a 500-bit block — and Days 10/13/14 could not confirm it to within 40 %.

**F6. M1 is redundant here.** The adaptive threshold tracks a level that does not move. Same indicators as M0, three times the cost.

### 2.3 Overfitting, data limits, complexity, failure patterns

**Overfitting.** M2 trained on synthetic data and applied to real data is the clean case — no real-data training. Day 17's real-pseudo-label model is the dangerous one: it is trained on the threshold decoder's own decisions and would reproduce its mistakes. It is saved but not used in this comparison. The threshold methods have 2–4 parameters and nothing to overfit — but see Day 19: even those must be tuned on DEV and reported on TEST once.

**Data limitations.** (1) No ground truth — the single fact that shapes everything above. (2) Four videos, four different setups — no repeat of any condition, so no generalisation claim is possible (Day 07 §6). (3) The synthetic model has a clean bit clock that the real videos demonstrably lack (Day 10: 22–27 % impossible run lengths). Synthetic BER measures decoding of the assumption, not of the recordings. (4) The DEV/TEST split is within-video; it protects against tuning on the reported frames, not against a setting that happens to suit one clip.

**Complexity.** M0: threshold + argmax, 0.1 ms per 1,000 frames. M2: six multiplies per bit, trained in 0.1 s. Nothing here is expensive; runtime is not a selection criterion on this dataset.

**Failure patterns.** The same one everywhere: bits whose window straddles a level change at an unknown phase. They are 50–60 % of every stream, they flip under a half-bit shift, and they flip under a threshold shift. The isolated-bit case is worst (Day 16 §3 note: 7.8 % of single-bit runs survive a phase change). The `2LEDs` L1 stream has 60 % ones (Day 16 §5) — it is either genuinely unbalanced data or a systematic decision bias, and without truth there is no way to tell.

### 2.4 Generalisation across videos and sensitivity to signal quality

**Across the four videos** (per-lamp values in `comparison.json`). The indicators barely move between recordings, which is the most that can be said with one video per condition:

| Method | Safe bits, range over 10 lamps | Phase stability | Threshold tolerance |
|---|---|---|---|
| M0 fixed threshold | 40.4–48.8 % | 89.2–91.8 % | 74.0–77.7 % |
| M1 adaptive threshold | 40.9–48.0 % | 88.9–91.8 % | 74.0–77.7 % |
| M0 + end margin 0.3 | 36.8–44.9 % | 87.7–91.0 % | 78.0–81.4 % |
| M2 ML classifier | 37.5–53.4 % | 88.7–93.4 % | 85.3–88.5 % |

The spread within a method (a few points) is smaller than the spread between methods on the synthetic BER, and the lowest-contrast lamp (`3LEDs` L3, 227 vs 250) sits inside every range. **This is consistency across recordings, not generalisation:** four videos of four different lamp counts, no repeat of any condition, so a setting that suits one clip cannot be told from a method that works (Day 07 §6). Any claim beyond "the same behaviour on all four" is unsupported.

**Sensitivity to signal quality.** Only the synthetic model can vary it. At the real noise level (6–11) every method is at 0.00–0.06 % BER with the phase known; at ten times that noise (80) they sit at 0.9–2.1 %, and at phase 0 the noise adds only 1–2 points to a 7–10 % phase-driven error. Signal quality is not the limiting factor on this dataset; the phase is. Day 20 §3 adds the one quality-related failure: beyond a ±10 % threshold shift at noise 80, every rule collapses, because the noise then reaches the threshold.

---

## 3. Mentor Review — Points to Confirm

1. Shortlist as in slide 3: tune **M0 + end margin** first, keep **M2** as the secondary candidate.
2. Selection rule for Day 19, fixed now: primary = synthetic BER at phase 0 (the realistic case, averaged over noise 8 and 80); secondary = synthetic phase tolerance; real-DEV indicators reported but **not** used to select, because they cannot measure correctness.
3. TEST (last 70 % of each signal) is opened once, on Day 21.
4. Q1 (transmitted bits for one video) remains the request. Without it, Day 21's "best candidate" is the best-behaved decoder, not the most correct one.

**Mentor decisions:** *(to be recorded at the review)*

---

## 4. Files

| File | What it is |
|---|---|
| `compare_methods.py` | Runs all four methods on real DEV and synthetic data, timed |
| `comparison.json` | Every number, per lamp and per synthetic condition |
| `comparison.md` | The summary table |
