# Day 21 — Best-Candidate Review

**Project:** Optical Camera Communication (OCC) Video Message Decoding
**Files:** `final_eval.py`, `final_eval.json`, `phase_band_all_rules.json`, `fig_final.png`.
**Checkpoint:** the configurations frozen on Day 19, run once on the TEST part (last 70 % of every real signal) and on fresh synthetic seeds. This is the first and only opening of TEST.

Three decoders are shown. All use the fixed threshold (midpoint of the 10th/90th percentiles), the phase-0 convention and the Day 16 window; they differ only in the sampling rule.

| | Rule | Origin |
|---|---|---|
| **Baseline** | most confident frame in the window | Day 09 choice; Days 15–16 decoder |
| **Tuned** | nearest frame to the bit centre | Day 19 selection, E19-02 |
| **Runner-up** | average over the window | Day 19 E19-03, 0.4 points behind |

---

## 1. Baseline vs Tuned

### 1.1 Synthetic TEST (seeds 50–53, bits known)

| | Noise 8 (real level): BER @ phase 0 / @ true phase | Phase tolerance | Noise 80: BER @ phase 0 / @ true |
|---|---|---|---|
| Baseline | 12.71 % / 0.21 % | 0.10 bit | 11.87 % / 1.97 % |
| **Tuned** | **5.56 % / 0.00 %** | **0.61 bit** | **8.29 %** / 6.65 % |
| Runner-up | 0.00 % / 0.00 % | 0.66 bit | 12.23 % / 1.48 % |

Confirms Day 19: the tuned rule halves the phase-0 error and widens the tolerance band six-fold. It is also worse at the true phase under heavy noise (6.65 % — a single sample is a noisy sample). See §3 on the runner-up's 0.00 %.

### 1.2 Real TEST (no ground truth — consistency indicators, medians over ten lamps)

| | Safe bits | Phase stability | **Threshold tolerance** | Ones | Flip rate | Time per signal |
|---|---|---|---|---|---|---|
| Baseline | 44.4 % | 89.6 % | 75.2 % | 38–60 % | 43–49 % | 5–39 ms |
| **Tuned** | 35.6 % | 87.6 % | **99.8 %** | 48–57 % | 52–55 % | 2–4 ms |
| Runner-up | 40.6 % | 89.5 % | 97.3 % | 50–62 % | 45–53 % | 4–10 ms |

Baseline and tuned agree on **79.2 %** of TEST bits (77–81 % per lamp). Per-lamp values in `final_eval.json`.

**Reading it.** Every number went the way Day 19 §3 predicted. The tuned decoder's *safe* share is 9 points lower and its phase stability 2 points lower — the real-data indicators favour the baseline, and they are wrong to, because they measure how little the output moves, not whether it is right (Day 19 §3, Day 20 §4). The one indicator that does move the right way is threshold tolerance: 75 % → 99.8 %, the E09b failure of the baseline rule removed. Everything else on the real data is unverifiable.

### 1.3 Robustness / ablation findings (Day 20, summarised)

Working ranges at BER ≤ 1 % on the model (or < 1 % of real bits changed). Full tables and figure in `../day20/`.

| Setting swept | Baseline | Tuned | What decides it |
|---|---|---|---|
| ROI scale 0.5×–2× | 83–100 % bits unchanged | **99.0–100 %** | box on the lamp = same bits |
| ROI shift ±0.5 box | 92–100 % | **99.3–100 %** | same |
| Smoothing window | 1–3 frames ok; ≥ 5 fatal | same | window longer than a bit erases edges |
| Threshold ±0.3 of range | 17–30 % of bits flip; +5 BER points | **0.00 % BER, > 99 % unchanged** | confident rule follows the threshold, nearest does not |
| Phase offset | −0.10 to −0.05 bit (0.05 wide) | **−0.40 to +0.20 bit (0.60 wide)** | single centre sample vs straddling window |
| Bit period | **±0.2 % → 41 % BER** | **same** | 6-bit slip over 3,000 bits; no rule can absorb it |
| Execution time | < 1 ms | < 1 ms | not a discriminator |

**Generalisation limit, stated plainly.** Every one of these ranges was measured on the DEV part of four videos that are four different setups and on a synthetic model of the assumed clock. They show the same behaviour on all four recordings; they cannot show that the behaviour would hold on a fifth setup, a different camera, or a different lamp. The Day 14 difficult windows (`1LED` at 50 s and 95 s, the highest near-threshold rates in the set) fall inside TEST (DEV ends at 32 s); baseline and tuned agree on 82 % and 80 % of the bits in those two 5-second windows against 81 % for the whole of TEST (index-aligned), and the tuned rule's phase-independent share there is 30 % and 40 % against 34 % overall — nothing singles them out.

---

## 2. Representative Successes and Failures

### 2.1 Where the two decoders disagree (1LED TEST, 6,899 bits)

1,448 bits differ (21.0 %). **97.3 % of them are windows that contain both a fully-on and a fully-off frame**, though such windows are only 48.8 % of all windows. That is the whole story of the disagreement: the assumed bit window straddles a real level change, and the two rules pick different sides.

Six of them, as frames ([one before] + window + [one after], brightness 0–255, threshold 126):

| Bit | Frames | Baseline picks | Tuned picks | Which is "right"? |
|---|---|---|---|---|
| 1 | 244 · **249 249 2** · 2 | 0 (the 2) | 1 (centre = 249) | Unknowable. Two on-frames and one off-frame; the bit boundary is somewhere in the window |
| 6 | 2 · **250 250 2** · 2 | 0 | 1 | Same shape |
| 14 | 59 · **2 247 247** · 248 | 0 (the 2) | 1 (247) | Same shape, mirrored |
| 21 | 246 · **4 5 250** · 250 | 1 (250) | 0 (5) | Same |
| 32 | 188 · **250 8 2** · 2 | 1 | 0 (8) | Same |
| 34 | 250 · **2 185 250** | 0 | 1 (185 — a straddling frame) | Same, with the rare intermediate frame |

**A success, by construction:** every window that holds only one level — 51 % of them — decodes identically under every rule, every threshold shift and every phase, and those bits are the Day 16 "safe" set. **A failure, by construction:** the other 49 % are decided by which frame the rule prefers, and no rule can know which of two clean frames belongs to *this* bit without the phase. The tuned rule's advantage is statistical (Day 20 §4: right across 60 % of phases instead of 5 %), not per-bit.

### 2.2 Unusual streams

| Stream | Observation | Baseline | Tuned | Runner-up | Reading |
|---|---|---|---|---|---|
| `2LEDs` L1 | share of ones far from 50 % | 60.0 % | 56.5 % | 60.9 % | Persists under all three rules and on TEST as on DEV (Day 16 §5). Either the data are unbalanced or the on-level of this lamp biases every rule the same way; the other 2LEDs lamp is at 40–53 %, so a shared bias is less likely. Unresolvable without truth |
| `3LEDs` L3 | lowest contrast in the set, 227 vs 250 | safe 42.1 % | 35.0 % | 37.1 % | Indicators in line with its siblings; lower contrast has no visible effect (matches Day 14 §4) |
| all lamps, tuned | flip rate 52–55 %, above the 43–49 % of the baseline | — | — | — | The nearest rule reads more transitions. On the model that is the correct behaviour (baseline under-reads them, Day 19 §3); on the real data it cannot be checked |

### 2.3 Remaining weaknesses

1. **The bit period.** Day 20 §5: a 0.2 % rate error is a coin toss over 3,000 bits, for any rule. The rate is the filename's number, unconfirmed (Day 13), possibly 1 % off (Day 14). Every result above is conditional on it.
2. **The phase.** Tuned decoding is right across 60 % of phases on the model. The other 40 % of phases give 8–25 % BER, and on the real videos we do not know which case we are in.
3. **Noise at the true phase.** The tuned single-sample rule is worse than the baseline when the phase *is* known and noise is high (6.65 % vs 1.97 % at noise 80). At the real noise level (6–11) both are 0.0–0.2 %; this only matters if the assumption "phase unknown" is ever removed.
4. **No correctness measurement at all on real data.** Unchanged since Day 07.
5. **Split discipline has a dated start.** DEV/TEST was instituted on Day 17; Days 15–16 decoded the full signals (no tuning was done on them, but their reported indicators include TEST frames). From Day 17 on, TEST was opened once, here.

---

## 3. A Correction to Day 19's Selection, on Validation Evidence

On the synthetic TEST the runner-up scored 0.00 % at phase 0 (noise 8) where the tuned rule scored 5.56 % — the reverse of Day 19's validation (6.59 % vs 6.19 %). Both figures are means over **four random phases**, and a rule's phase-0 BER is either ~0 or ~15 % depending on which side of its tolerance band the drawn phase falls; four draws cannot separate two rules whose bands are the same width.

Measured properly — BER at 21 evenly spaced phase offsets, Day 20's validation streams, `phase_band_all_rules.json`:

| Rule | Mean BER over all phases | Band with BER ≤ 1 % |
|---|---|---|
| Baseline | 11.08 % | −0.10 to 0.00 bit (0.15 wide) |
| Tuned (nearest) | 4.82 % | −0.40 to +0.20 (0.65 wide) |
| Runner-up (average) | 4.79 % | −0.35 to +0.25 (0.65 wide) |

**Nearest and average are the same decoder on the phase axis.** They differ only at the true phase under noise, where average is better (Day 19: 0.86 % vs 3.26 %; today: 1.48 % vs 6.65 % at noise 80) at the cost of the window-end sensitivity (Day 20 §2–3: 97.3 % vs 99.8 % threshold tolerance). This is not a TEST-driven change of mind — the validation set already showed the true-phase gap — it is a refinement of the Day 19 metric from four random phases to a uniform sweep, and it is recorded here rather than by re-running Day 19.

---

## 4. Week-4 Direction — For Mentor Approval

**Best candidate (checkpoint):** fixed threshold, phase-0 convention, **average-over-window or nearest-frame sampling** (equivalent on phase robustness; average preferred for its noise behaviour, nearest for simplicity and threshold immunity). Either halves the phase error and removes the threshold sensitivity of the Day 09 rule. Saved configurations: `../day19/best_config.json`; decoder: `../day17/occlib.decode(rule=…)`.

**Proposed Week-4 work, in priority order:**

1. **The clock, not the decoder.** Pursue the Day 14 beat (H5) to fix the bit period to better than 0.03 %, or obtain the transmitted bits for one video (Q1). Day 20 §5 shows nothing else moves the outcome until this is done.
2. **Block-wise phase decoding.** With the period fixed, decode in blocks of ~500 bits with the phase chosen per block by the *nearest-rule* bit agreement across blocks — a phase estimator that, unlike Day 15's, has something to see (Day 20 §4 shows the BER-vs-phase curve is not flat for the tuned rules).
3. **Report and reproducibility run** (E16): delete every generated file and rebuild Days 11–21 from `Videos/` and the configs.
4. **Not proposed:** further threshold or ROI tuning (Day 20: insensitive), the ML classifier (Day 17–18: inherits the phase problem, unverifiable on real data), the adaptive threshold (Day 18: redundant).

**What we will say in the final report if nothing changes:** the pipeline decodes the assumed signal model to 0 % BER when the timing is known and to ~5 % over a random phase; it is insensitive to ROI, smoothing and threshold; it produces stable, deterministic, fingerprinted bit streams for all four videos; and it cannot say whether a single one of those bits is correct, because the bit clock could not be recovered from the videos and no reference was supplied.

**Mentor decision on the Week-4 direction:** *(to be recorded at the review)*

---

## 5. Files

| File | What it is |
|---|---|
| `final_eval.py` | The single TEST opening; synthetic TEST; disagreement examples; figure |
| `final_eval.json` | Every number, per lamp and per decoder |
| `phase_band_all_rules.json` | §3: BER over a uniform phase sweep for all three rules |
| `fig_final.png` | Threshold tolerance per lamp on TEST; synthetic BER at phase 0 vs true; one disagreement window |
