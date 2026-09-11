# Day 19 — Controlled Parameter Experiments

**Project:** Optical Camera Communication (OCC) Video Message Decoding
**Files:** `tune.py`, `EXPERIMENT_LOG_DAY19.MD` (all 51 runs), `tuning_results.json`, `best_config.json`.
**Tuned:** the two Day 18 shortlisted candidates only — the threshold decoder and the M2 classifier.

---

## 1. Search Strategy (fixed before running)

| | |
|---|---|
| **Search** | Full grid, small and meaningful: 45 threshold configurations (5 end margins × 3 percentile pairs × 3 sampling rules), 6 classifier configurations (3 regularisation strengths × 2 feature windows) |
| **Validation data** | Synthetic streams, seeds 30–33 — never used on Days 17–18 (train 0–3, test 10–13 / 20–23) — at noise 8 and 80, exposure 0.3, random phase, decoded at the **phase-0 convention** (the real situation) |
| **Primary metric** | Mean validation BER at phase 0 |
| **Tie-break** | Phase tolerance: width of the band around the true phase where BER ≤ 1 % |
| **Logged, not used** | Real DEV indicators (safe-bit share, phase stability) for every run. They cannot measure correctness — and §3 shows they would have chosen wrongly |
| **Test set** | The last 70 % of every real signal. Not opened. |

Every run is one row of `EXPERIMENT_LOG_DAY19.MD` with its settings, all five metrics and its runtime. Total runtime 11 s.

**Parameters deliberately not tuned, and why** *(added 2026-09-11 — the task lists smoothing and synchronisation parameters)*:

| Parameter | Not tuned because |
|---|---|
| Smoothing window | Day 12 measured every window as harmful on the signal (27 % of transitions deleted at 3 frames). Day 20 §2 then swept it on the decoder: a 3-frame window changes the tuned rule's BER by 0.1 point and destroys decoding from 5 frames. Nothing to gain |
| Number of ensemble phases (`n_phases`) | Affects only the safe-mask resolution, not the decoded bits; Day 16 §6 showed 12 vs 24 moves the mask by under 0.3 points |
| Phase | Cannot be estimated (Day 15); held as a convention. Day 20 §4 sweeps it |
| Bit period | The filename's value, unconfirmed; Day 20 §5 shows a 0.2 % change is fatal, so it is not a parameter to *tune* but a quantity to *find* (Week-4 direction) |
| Adaptive-threshold window | The adaptive threshold was dropped on Day 18 (identical to fixed, three times slower) |

---

## 2. Results

### Candidate A — threshold decoder (45 runs, E19-01 … E19-45)

The sampling rule decides everything; the other two settings barely register.

| Sampling rule | Val BER @ phase 0 | Val BER @ true phase | Phase tolerance | DEV safe bits | DEV phase stability |
|---|---|---|---|---|---|
| Most confident frame (Day 09 choice), end margin 0 | 12.05 % | 1.32 % | 0.05 bit | 43.6 % | 90.4 % |
| Most confident frame, end margin 0.5 | 10.18 % | — | 0.13 bit | 38.9 % | — |
| Average over the bit | 6.59 % | **0.86 %** | **0.32 bit** | 41.2 % | 90.1 % |
| **Nearest frame to the bit centre** | **6.19 %** | 3.26 % | 0.30 bit | 34.9 % | 88.1 % |

(percentile pair (10, 90); the (5, 95) and (25, 75) rows differ by < 0.03 points.)

- **End margin** helps only the confident rule (12.1 → 10.2 % as it grows to 0.5) and does nothing for the other two — the nearest rule never looks at the window end, and the average rule loses a frame it wanted.
- **Percentile pair** is irrelevant on a signal this clean: three pairs, same numbers to two decimals.

### Candidate B — classifier (6 runs, E19-46 … E19-51)

| C | Frames | Val BER @ phase 0 | Val BER @ true phase | Phase tolerance | DEV safe bits |
|---|---|---|---|---|---|
| 0.1 | 5 | 8.45 % | 0.63 % | 0.18 bit | 49.8 % |
| **0.1** | **7** | **7.00 %** | 0.60 % | 0.20 bit | 48.8 % |
| 1.0 | 7 | 7.18 % | — | 0.19 bit | 48.8 % |
| 10 | 7 | 7.23 % | — | 0.19 bit | 48.8 % |

A wider window helps (5 → 7 frames: 8.5 → 7.0 %); regularisation strength does not.

### Selected

**E19-02 — threshold decoder, nearest-frame rule** (`best_config.json`). Validation BER at phase 0 = 6.19 %, half the Day 09 rule's 12.05 %, with a 0.30-bit phase tolerance against 0.05. Best classifier (E19-47) is second at 7.00 %.

The average-over-bit rule (E19-03) is 0.4 points behind on the primary metric and clearly better at the true phase (0.86 % vs 3.26 %). The selection rule was fixed in advance and it picks the nearest rule; Day 21 reports both on TEST so the trade-off is visible.

---

## 3. What This Reverses, and Why

**Day 09 chose the most-confident-frame rule because it scored 0.00 % "bits near the threshold" at every phase.** That metric measured how *cleanly* each bit was read, not whether the right bit was read. At an unknown phase a 3-frame window straddles two true bits about half the time, and the cleanest frame in it belongs to the neighbour as often as not — that is the 12 %. A single sample at the assumed bit centre always lies inside exactly one true bit; with the period right, a wrong phase only shifts the whole sequence by a constant index, which the BER alignment absorbs. That is why the nearest rule halves the error and why its tolerance band is six times wider.

Day 15 found the symptom (the phase score is flat); Day 17's generator made it measurable; today's grid gives the replacement rule. The trade: the single sample is noisier when the phase *is* known (3.3 % vs 1.3 % at the true phase, mostly from the noise-80 streams). On the real videos, where the phase is not known and noise is 6–11, that is the right side of the trade.

**The real-data indicators would have chosen the wrong rule.** Safe-bit share: confident 43.6 %, nearest 34.9 %. Phase stability: 90.4 % vs 88.1 %. Both favour the Day 09 rule, which has twice the BER where a BER can be measured. "Safe" measures how little the output moves, and an output can be stably wrong. This is the concrete reason the selection rule excluded those indicators, and it should be remembered on Day 21: a lower safe share on TEST is expected and is not a regression.

---

## 4. Limits

- The validation BER is measured on the assumed 92 bps model. The real videos contain run lengths that model does not produce (Day 10). If the true rate is not 92 bps, the period error dominates every rule (Day 18 F5: zero tolerance to a 1 % rate error) and this tuning is moot.
- Two noise levels, one exposure. Exposure 0.3 was inferred on Day 13, not measured.
- 51 runs is a small grid by design; nothing in the search suggests a finer one would change the ranking — the three rules are separated by factors of two.

---

## 5. Files

| File | What it is |
|---|---|
| `tune.py` | The grid, the validation, the log writer |
| `EXPERIMENT_LOG_DAY19.MD` | One row per run, all 51, best marked; observations per group at the end |
| `tuning_results.json` | The same, machine-readable, with the selection rule and the classifier weights per run |
| `best_config.json` | The selected configuration, plus the best of each candidate |
