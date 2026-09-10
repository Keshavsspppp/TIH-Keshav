# Week 2 Package — Signal and Synchronisation

**Project:** Optical Camera Communication (OCC) Video Message Decoding
**Covers:** Days 8 to 14
**For:** the Week-2 peer signal review

**Companion:** `SYNC_HYPOTHESES.MD` (the hypothesis register), `Day13_Synchronisation.ipynb` (the sync work), `signal_v1/` (the frozen signals).

---

## 1. Where Week 2 Started and Ended

**Started with:** four videos, no idea of their quality, and a plan built around a dataset we had not seen.

**Ended with:** a frozen signal set, an approved extraction pipeline, and one large unanswered question about the clock.

| Day | Work | Outcome |
|---|---|---|
| 8 | Audited every frame of every video | Camera static, no drift, no dropped frames. One video has a false start |
| 9 | ROI and signal extraction strategy | Lamps found automatically in all four videos. Extraction rule chosen by measurement |
| 10 | Frame and intensity EDA | **Run lengths do not match 92 bps** |
| 11 | Built the pipeline | 10 signals, deterministic, reproducible from a config file |
| 12 | Reviewed and froze it | Signal V1: 131,080 samples, fingerprinted |
| 13 | Synchronisation analysis | **No clock recoverable at any rate** |
| 14 | Peer review | **Shared glitches reveal a beat — a clock may exist after all** |

---

## 2. What Is Settled

| Finding | Evidence |
|---|---|
| 260 fps, steady, no duplicated frames | Header and duration agree; zero identical consecutive frames |
| Camera is static | Lamp moved 0.8 pixels in 107 seconds |
| No ambient drift, no lamp drift | On-level moves at most 0.13 grey levels per recording |
| The signal is cleanly two-level | Gap about 245, noise 6 to 11 |
| Lamps carry different data | Correlation 0.31 to 0.41 between lamps |
| Every lamp is findable automatically | 1, 2, 3 and 4 lamps found; count never supplied |
| Cleaning steps hurt on this data | Every option lowers separation; smoothing deletes 27% of real level changes |

## 3. What Is Not Settled

| Open | Status |
|---|---|
| The symbol clock | No rate shows structure. See §5 and `SYNC_HYPOTHESES.MD` |
| What sits above the raw bits | Unknown. Not plain text, not Manchester |
| Whether any decode is correct | **No ground truth supplied.** We can measure confidence, never correctness |

---

## 4. Difficult Segments — For Discussion

Measured across 95 five-second windows in all ten signals. Two results were not what we expected.

> **Note (2026-09-10, audit):** "near the threshold" is not defined here and the code is not in the repository, so the percentages could not be reproduced exactly; with a ±25 grey-level band the ordering holds (`1LED` median 1.8 % against 0.2–0.7 % for every other lamp; `3LEDs` L3 contrast 227). The 95-window count reproduces.

### The single-lamp video is the hardest, not the easiest

| Signal | Median % of samples near the threshold | Worst window |
|---|---|---|
| **1LED** | **2.54** | **3.46** |
| 2LEDs L1 / L2 | 0.62 / 1.00 | 0.77 / 1.31 |
| 3LEDs L1–L3 | 0.73 / 0.85 / 0.77 | up to 1.46 |
| 4LEDs L1–L4 | 0.31 to 0.39 | up to 0.69 |

`1LED` is three to eight times harder than every other signal by this measure. It is also the video we have been developing against, which means our impression of difficulty has been formed on the least representative clip. Worth flagging to a peer as a methodological trap, not just a curiosity.

### The dimmest lamp is not the worst lamp

`3LEDs` lamp 3 has visibly lower contrast — 227 against 250 for the others, and it looks greyer in the frames. But its near-threshold rate (0.77%) is in line with its siblings, and its 1-frame run rate (9.6%) is the *lowest* of the multi-lamp signals.

Lower contrast did not translate into a harder signal. Worth asking a peer whether they see the same on their data.

### Specific windows to look at

| Signal | Starts at | Why |
|---|---|---|
| 1LED | 50.0 s | Worst window in the whole set: 3.46% near threshold |
| 1LED | 95.0 s | 2.92% near threshold with 9.9% 1-frame runs |
| 3LEDs L3 | 0.0 s | Lowest contrast anywhere: 227 |
| 2LEDs | frames 93 to 975 | The false start: one flash, then 3.4 seconds of dark |
| 4LEDs | frames 0 to 1816 | Longest dark lead-in |

---

## 5. The Sync Problem, Stated Plainly

This is the main thing to compare with a peer.

**What we did.** Estimated the symbol clock six ways across Days 10 and 13: spectral null, transition-grid alignment and a period sweep (Day 10); long baselines between distant level changes, best-phase grid distance at every rate, and a run-length model fit (Day 13).

**What happened.** All four failed. The decisive measurement: level changes sit at an average of 0.703 frames from the nearest 92 bps boundary. Randomly chosen times sit at 0.705. A real edge can only be out by half a frame, since that is all the rounding allows.

Widening the search to every rate from 45 to 215 bps found nothing above the noise.

**Today's development.** The odd 1-frame runs — which Day 10 proved are not threshold noise — happen at the *same moments* on different lamps, 2.3 to 3.9 times more often than chance. Since the lamps carry different data, that shared timing cannot be data. It is the bit grid and the frame grid interfering.

Those shared moments repeat every about **21 frames**, the same beat in two independent recordings, with harmonics at 41, 61 and 81.

Three bit rates would produce a 21-frame beat: about 136, about 124, and **about 91 bps** — the last within 1.2% of the filename's 92.

**What this is and is not.** It is the first evidence pointing back toward something near 92 bps. It is not a confirmation: three candidates fit the same beat equally well. It reopens a door Day 13 appeared to close.

---

## 6. Questions to Compare With a Peer

Points where an outside view would help most. Findings only — no code.

1. Do you also see level changes that cannot exist at your stated bit rate? What fraction?
2. Did any clock estimator work on your data? Which, and how sharp was the answer?
3. Do your videos show glitches that coincide across separate transmitters?
4. Did you get ground truth? If so, how did you verify a decode without it before that?
5. Is your hardest segment in the video you developed against? Ours is.
6. Did switching off smoothing and detrending help you too, or is that specific to a signal this clean?

---

## 7. Peer Review Record

To be filled in during the session. Left blank on purpose — nothing here is written in advance.

### Session details

| | |
|---|---|
| Date | |
| Peer / group | |
| Their project | |
| Format | Findings compared verbally. No code exchanged |


### Comparison notes

| Topic | Ours | Theirs |
|---|---|---|
| Clock recovered? | No — 0.3% better than random | |
| Impossible run lengths? | Yes — 22.6% of runs | |
| Ground truth available? | No | |
| Hardest segment in the development video? | Yes | |
| Cleaning steps helped? | No — all measured worse | |

### One peer insight — recorded

> *Their observation, in their words as far as possible. Not our restatement of it.*

**Insight:**

**Why it matters to us:**

**What we will do about it:**

**Whether we agree, and if not, why:**

### One hypothesis — recorded

> *Where this came from: us, them, or the conversation. Say which.*

**Hypothesis:**

**What it predicts that the alternatives do not:**

**The test that would rule it out:**

**When we will run that test:**

---

## 8. Our Own Hypothesis From Today

If the session produces nothing better, this is the one we carry forward. It came from the Day 14 analysis, not from a peer, and is labelled as such.

**H5 — a clock exists, and it beats against the frame grid.**

Transition-time alignment cannot find the clock because each edge is only timed to the nearest frame, about a fifth of a bit. But the interference between the bit grid and the frame grid *is* visible, as glitches shared across lamps that repeat every about 21 frames.

**Predicts:** a bit period of about 1.91, 2.10 or 2.86 frames. Nothing else fits a 21-frame beat in the plausible range.

**Test:** measure the beat more tightly on the longest recording (`1LED`, 107 seconds). A sharper beat length narrows the three candidates, and the survivor should hold across all four videos.

**Would be ruled out by:** the beat differing between videos, or drifting within one. Both are checkable without any new information from the faculty.

---

## 9. Still Blocking

Unchanged since Day 09, and now three weeks old.

| # | Question | Consequence of not having it |
|---|---|---|
| **Q1** | The transmitted bits for at least one video | No BER, no correctness, no ML branch. Every number stays unverified |
| **Q2** | What sits above the raw bits | The leading hypothesis (H3) cannot be tested |
| **Q3** | Is 92 bps the payload rate or the light's switching rate | Would immediately narrow five hypotheses to one or two |

Week 3 begins with decoder work. Without Q1, the decoder can be **written and tested** but its output cannot be **checked**. That distinction should be stated in the Week-3 plan rather than discovered at the end of it.

---

## 10. Package Contents

| File | What it is |
|---|---|
| `WEEK2_PACKAGE.MD` | This file |
| `SYNC_HYPOTHESES.MD` | Five hypotheses, evidence, and discriminating tests |
| `signal_v1/` | The frozen signals, manifest and settings |
| `Day13_Synchronisation.ipynb` | The sync analysis, executed |
| `Day10_EDA.ipynb` | The frame and intensity EDA, executed |
| `candidate_timing.json` | Period and phase per signal, labelled as assumed |
| `fig_beat.png` | Today's finding: the 21-frame beat and which rates produce it |
| `fig_noclock.png` | No bit rate shows clock structure |
| `fig_ablation.png` | Why every cleaning option is off |
| `occ_pipeline.py`, `preprocess_v1.yaml` | The extraction pipeline and its settings |
