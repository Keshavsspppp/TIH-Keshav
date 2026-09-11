# Synchronisation Hypotheses

**Project:** Optical Camera Communication (OCC) Video Message Decoding
**Version:** as of Day 14 (end of Week 2)

Why this file exists: Day 13 found that the level changes in the video line up with a 92 bits-per-second grid **no better than randomly chosen times would**. That leaves several explanations open. This is the register of them — what each predicts, what would rule it out, and where each stands.

---

## The evidence any hypothesis has to fit

| # | Observation | Where from |
|---|---|---|
| E1 | Frame rate is 260 fps, steady, no duplicated frames | Day 07, Day 13 |
| E2 | The signal is cleanly two-level: gap about 245, noise 6 to 11 | Day 10 |
| E3 | Runs of 1 and 4 frames are 22.6% of the data. Both are impossible at 92 bps | Day 10 |
| E4 | Hysteresis to 35% of the signal range removes none of them, so they are not threshold noise | Day 10 |
| E5 | Level changes fit a 92 bps grid 0.3% better than random times. No other rate does better | Day 13 |
| E6 | Fitting run lengths prefers a period near 1.9 frames (about 137 bps) | Day 13 |
| E7 | About 5% of frames sit part-way between on and off, implying an exposure near 30% of a frame | Day 13 |
| E8 | **The 1-frame runs happen at the same moments on different lamps — 2.3 to 3.9 times more often than chance** | **Day 14** |
| E9 | **Those shared moments repeat every about 21 frames, with the same beat in two independent recordings** | **Day 14** |

E8 and E9 are new today and they change the picture. See §6.

> **Note (2026-09-10, audit).** E8 and E9 re-verified on the regenerated Signal V1: coincidence 2.28–3.85× chance across all ten lamp pairs; strongest repeat lags 21 / 81 / 41 / 61 in `2LEDs` and `4LEDs`, 63 / 84 in `3LEDs`. The code that produced them on Day 14 was not in this folder; `beat_analysis.py` (added 2026-09-11) reproduces E8, E9 and the H5 candidates from Signal V1 and writes `beat_results.json` / `fig_beat_check.png`; the same analysis is in `../../OCC_Complete_Analysis.ipynb` §8. The lamp correlation in H5 ("0.31 to 0.41") is the Day 07 figure; on Signal V1 it is 0.36–0.44. Question numbering: Day 07 used Q1–Q8 and Day 09 renumbered to Q1–Q4; from Day 10 on, Q1 = transmitted bits, Q2 = framing, Q3 = payload-vs-switching rate, and "Q5" below (exposure time) is a new question, not Day 07's Q5.

---

## H1 — The bit rate is simply not 92 bps

**Claim:** the filename is wrong or refers to something else, and the true rate is higher — around 124 to 137 bps.

| | |
|---|---|
| Fits | E3, E6 |
| Against | E5. If the rate were 137 bps, a 137 bps grid should show clock structure. It does not |
| Status | **Weakened.** It moves the problem rather than solving it |
| Test | Ask the faculty for the rate (Q3) |

---

## H2 — The light switches faster than the camera can follow

**Claim:** the true period is under two frames, so what we record is aliasing. The level changes we see are not the real edges.

| | |
|---|---|
| Fits | E3, E5, E6 — explains all three at once, since aliased edges would look unrelated to any grid |
| Against | The videos were shot at 260 fps. Someone chose that deliberately, presumably so the camera *could* follow. Also E9: aliasing would not produce a stable, repeatable beat |
| Status | **Weakened by E9** |
| If true | Reliable decoding from these videos is impossible, and that is the finding |
| Test | The exposure estimate (E7) plus the beat (E9) both constrain the period. Faculty answer to Q3 settles it |

---

## H3 — A line code or a carrier sits on top of the data

**Claim:** 92 bps is the payload rate. The lamp is driven faster — a flicker-free carrier, or a DC-balanced line code — and the payload comes out only after that layer is undone.

| | |
|---|---|
| Fits | E3, E5, E6, and it is normal practice in this field. Our own Day 02 review describes undersampled schemes that drive a fast carrier precisely so the light does not visibly flicker |
| Against | Nothing measured yet |
| Ruled out so far | **Manchester.** Bit pairs alternate 47% of the time; Manchester requires 100% |
| Status | **Still the leading explanation** |
| Test | Ask what sits above the raw bits (Q2). If a code is named, apply it and re-test |

---

## H4 — Our level-change detection is wrong

**Claim:** the anomalies are an artefact of how we threshold.

| | |
|---|---|
| Against | E4 (hysteresis changes nothing), and all ten signals behave the same way |
| Status | **Largely ruled out**, though E8 shows the short runs *are* an artefact of sampling — just a real and informative one, not a detection error |

---

## H5 — There is a clock, and it beats against the frame grid *(new, Day 14)*

**Claim:** a fixed symbol clock does exist. Transition-time alignment cannot see it, because each edge is only timed to the nearest frame — about a fifth of a bit. But the *interference pattern* between the bit grid and the frame grid is visible, and that is what the shared 1-frame runs are.

### Why this came up

A 1-frame run means the sampled level flipped for exactly one frame. Whether that happens depends on where a bit boundary falls inside a frame — which is shared by every lamp, because they all run off the same transmitter clock. The lamps carry **different data** (correlation 0.31 to 0.41, Day 07), so if these glitches were data, they would not coincide.

They coincide 2.3 to 3.9 times more than chance (E8).

### What the beat says

The shared glitches repeat every about **21 frames**, with harmonics at 41, 61 and 81. The same 21-frame beat appears in `2LEDs` and `4LEDs` — separate recordings — and in `3LEDs` as 63 and 84, which are multiples of it.

Two grids drifting past each other realign every `T / |T − nearest whole number|` frames. Setting that to 21 gives four candidate periods (two of them within 0.2 % of each other):

| Period (frames) | Bit rate | Beat |
|---|---|---|
| 1.910 | 136.1 bps | 21.2 frames |
| 2.100 | 123.8 bps | 21.0 frames |
| **2.860** | **90.9 bps** | **20.4 frames** |
| **2.865** | **90.8 bps** | **21.2 frames** |

**The third and fourth land within 1.2% of the filename's 92 bps.**

> **Note (2026-09-10, audit).** The repeat lags are 21, 41, 61, 81 — spaced **20** apart, so the beat is nearer 20.2 frames than 21; that moves the candidates to about 1.905 / 2.105 / 2.85 frames (136 / 124 / 91 bps) and does not change the conclusion. A fifth candidate sits on the other side of the 3-frame pole (`T ≈ 3.15`, about 82 bps; visible in `fig_beat.png`, right panel). The filename's 2.826 frames would give a 16-frame beat, which is not what is observed.

| | |
|---|---|
| Fits | E8, E9, and it is compatible with H3 |
| Against | It does not uniquely pick a period — three candidates fit the same beat |
| Status | **New, and the most promising line** |
| Test | Measure the beat more precisely on the longest recording. A tighter beat length narrows the candidates. Then check whether the surviving one is consistent across all four videos |

### What it does not mean

This is **not** a confirmation of 92 bps. It says a periodic structure exists that is consistent with a clock near 91 bps — and equally consistent with 124 or 136 bps. It reopens a door Day 13 appeared to close. It does not walk through it.

---

## Where this leaves us

| Hypothesis | Status after Day 14 |
|---|---|
| H1 — wrong rate | Weakened |
| H2 — faster than the camera | Weakened by the stable beat |
| H3 — line code or carrier | Leading |
| H4 — our detection is wrong | Largely ruled out |
| **H5 — clock exists, beats against the frame grid** | **New, most promising** |

H3 and H5 sit together comfortably: a carrier or line code would run at a rate we have not identified, and that rate would beat against the frame grid exactly as observed.

## What would settle it

| # | Question | Settles |
|---|---|---|
| **Q1** | The transmitted bits for one video | Everything. Any candidate clock could be tested directly |
| **Q2** | What sits above the raw bits — preamble, line code, carrier | H3 |
| **Q3** | Is 92 bps the payload rate or the light's switching rate | H1 versus H2 versus H3 |
| Q5 | The camera's exposure time | Sharpens E7, which constrains the period |
