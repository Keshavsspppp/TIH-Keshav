# Day 16 — Improved Synchronisation and Decoding

**Project:** Optical Camera Communication (OCC) Video Message Decoding
**Built:** decoder v2, run over all of Signal V1.
**Files:** `decoder_v2.py`, `bits_v2/`, `fig_decode_v2.png`, parameter log in §6.

**Summary.** Two attempts to recover the bit phase failed. A third approach — stop estimating the phase and instead measure which bits do not depend on it — worked, and gives a usable result: **about 44% of every stream is decided regardless of the phase.** The rest is not knowable until the phase is.

> **Correction (2026-09-10, audit).** The body of this file describes **one** failed attempt (§2, sub-frame timing) and **one** approach that worked (§3, the phase-independent mask), not two failures and a third approach; §7 repeats the same miscount. Read "two attempts" as "one". `report.json` and the §4 and §5 tables reproduce exactly on the regenerated Signal V1 (`../../week02/day12/signal_v1/`). `bits_v2/` was not committed; `decoder_v2.py` regenerates it in about 10 s. Two further notes are placed at §3 and §5.

---

## 1. What Day 15 Left

The v1 decoder chose the bit phase by maximising confidence. That score turned out to be flat: 123.5 at every phase, while a third of the bits changed. The phase was being set by floating-point noise, and the decoder reported full confidence whichever one it landed on.

So Day 16 had one job: get the phase, or work without it.

---

## 2. Attempt One — Sub-Frame Transition Timing (failed)

Day 13 timed each level change to the nearest whole frame, about a fifth of a bit, and every clock estimator drowned in that error.

But a frame whose exposure straddles a switch comes out part-way between on and off, and *how far* says where inside the frame the switch happened. That information was being thrown away. Interpolating the threshold crossing between the two frames either side should recover it.

**It did not help.**

| Edge timing | Best rate found | How much better than random | At 92 bps |
|---|---|---|---|
| Whole-frame | 173.3 bps | 15.5% | 0.2% |
| **Sub-frame** | 127.6 bps | 14.2% | 0.3% |

The reason is in the data: the interpolated positions within a frame come out at the 25th, 50th and 75th percentile as 0.5, 0.5, 0.5. **Most transitions have no intermediate frame at all** — the signal jumps straight between full levels, so there is nothing to interpolate. Only about 5% of frames sit part-way, which matches the short exposure estimated on Day 13.

The idea was sound. The data does not contain what it needed.

---

## 3. Attempt Two — Which Bits Do Not Care About the Phase (worked)

If the phase cannot be found, the next question is which answers do not depend on it.

Decode at 12 evenly spaced phases and compare. A bit that comes out the same every time is safe whatever the true phase is.

| Signal | Bits | Phase-independent |
|---|---|---|
| 1LED L1 | 9,855 | 40.8% |
| 2LEDs L1 / L2 | 6,083 | 47.4% / 43.1% |
| 3LEDs L1–L3 | 4,055 | 43.8% / 43.8% / 40.8% |
| 4LEDs L1–L4 | 3,044 | 45.7% / 45.5% / 46.9% / 44.8% |

**Median 44.3%.** Remarkably consistent across every signal, which suggests it is a property of the sampling geometry rather than of any one recording.

### Where the safe bits are

| Bit sits inside a run of | Phase-independent |
|---|---|
| 1 bit | 28.6% |
| 2 bits | 35.3% |
| 3 bits | 38.9% |
| 4 bits | 43.2% |

Exactly as expected: a bit surrounded by identical neighbours survives a shifted window, because the window still lands inside the same run. An isolated bit does not.

> **Note (2026-09-10, audit).** The table above is reproduced only when run length is measured on the **majority-vote** bits across the 12 phases, which is not the sequence `decoder_v2.py` writes. On the phase-0 bits it does write (`1LED`, same mask) the figures are **7.8 % / 42.4 % / 47.4 % / 57.9 %** for runs of 1 / 2 / 3 / 4 (pooled over all ten lamps: 8.0 / 42.7 / 51.2 / 59.9 %). The conclusion is the same and stronger on the real output — an isolated bit almost never survives.

### What v2 does with this

v2 outputs a bit sequence **and a mask** saying which bits are safe. It also stops describing the phase as "estimated": the convention is fixed at zero and stated as a convention. Ignoring the mask puts you back where v1 was.

---

## 4. Adaptive Threshold and Local Normalisation

Tested in the decoding stage, not just on the signal.

| Variant | Safe bits | Ones | Margin | Bits same as default |
|---|---|---|---|---|
| Fixed threshold (default) | 40.8% | 45.2% | 49.3% | — |
| Adaptive threshold | 41.0% | 45.8% | 49.3% | 98.86% |
| Fixed + local normalisation | 40.9% | 45.6% | 49.4% | 98.13% |
| Adaptive + local normalisation | 41.1% | 46.2% | 49.4% | 97.87% |
| Fixed + 5% hysteresis | 40.8% | 45.2% | 49.3% | 100.00% |

**None of them changes anything that matters.** Safe bits move by 0.3 percentage points across every variant, and the streams agree with the default on 98% or more of bits. Hysteresis changes literally nothing, because no bit is ever close enough to the threshold for it to act.

This matches Day 12, where the same options measured worse on the signal itself. They stay available behind flags and off by default. The default stays **fixed threshold, no normalisation**, on the grounds that it is the simplest thing that performs identically.

---

## 5. Comparing the Decoded Streams

The lamps carry different data, so the bit values cannot be compared directly. What can be compared is structure.

| Signal | Bits | Safe | Ones (all) | Ones (safe only) | Flips |
|---|---|---|---|---|---|
| 1LED L1 | 9,855 | 40.8% | 45.2% | 41.0% | 48.4% |
| 2LEDs L1 | 6,083 | 47.4% | 60.0% | 64.2% | 43.3% |
| 2LEDs L2 | 6,083 | 43.1% | 40.7% | 36.3% | 44.9% |
| 3LEDs L1 | 4,055 | 43.8% | 39.2% | 35.2% | 44.3% |
| 3LEDs L2 | 4,055 | 43.8% | 40.0% | 35.6% | 44.1% |
| 3LEDs L3 | 4,055 | 40.8% | 41.6% | 35.4% | 48.1% |
| 4LEDs L1–L4 | 3,044 | 44.8–46.9% | 47.7–54.4% | 47.7–57.9% | 46.2–48.0% |

Flip rates cluster tightly at 43–48% against 50% for random data. Nothing degenerate anywhere.

The share of ones spreads from 39.2% to 60.0%, and **wider** on the safe bits alone (35.2% to 64.2%). If these were balanced data streams we would expect the opposite — the safe subset should be no more skewed than the whole. That the skew grows is a hint that the safe subset is not a fair sample of the stream, which is worth remembering before drawing any conclusion from it.

### Do any lamps carry the same data?

Cross-correlated every pair of decoded streams at every lag.

| Pairing | Mean correlation |
|---|---|
| Lamps in the **same** video | **+0.258** |
| Lamps in **different** videos | +0.056 |
| Same streams, one shuffled (control) | +0.003 |

> **Note (2026-09-10, audit).** These are lag-0 values (the text says "at every lag"; searching ±50 bits moves no `4LEDs` pair, moves two `3LEDs` pairs by under 0.02, and turns the `2LEDs` pair into −0.12 at lag +1). The within-video mean hides a wide spread: the `2LEDs` pair is **+0.012** at lag 0 — effectively none — while `3LEDs` L1–L2 is +0.370 and the `4LEDs` pairs sit at +0.26 to +0.38. So "lamps in one recording share a substantial component" holds for `3LEDs` and `4LEDs`, not for `2LEDs`.

**A correction to my first reading of this.** I initially flagged several across-video pairs at about +0.25 as suspicious. They were outliers among 35 pairs, picked out by a cut-off I chose after seeing the numbers. The proper comparison is the group means, and across videos it is +0.056 — close to the +0.003 shuffled control. Separate recordings share essentially nothing, as they should.

The real result is the within-video figure of +0.258. Lamps in one recording share a substantial component while carrying different messages. That is the same shared structure Day 14 found in the glitch timing, now visible in the decoded bits: one transmitter clock driving every lamp, leaving a common fingerprint on all of them.

> **Softened (2026-09-10, audit).** The clock is the leading explanation, consistent with Day 14's E8/E9, but it is an interpretation: a shared preamble or framing (the explanation offered on Day 07 §4 for the raw-signal correlation of 0.36–0.44) would leave the same fingerprint and has not been ruled out. Neither reading is testable without the transmitted bits (Q1).

It also means our decoded bits contain a component that comes from the sampling rather than the data. Any later analysis that treats the lamps as independent streams would be wrong.

---

## 6. Parameter Log

Every setting in decoder v2, its value, and why.

| Parameter | Value | Basis |
|---|---|---|
| `bits_per_second` | 92.0 | **Assumed**, from the filename. Days 10 and 13 both found evidence against it |
| `phase_convention` | 0.0 | A stated convention, not an estimate. Day 15 showed the phase cannot be estimated from confidence |
| `n_phases` | 12 | Enough to resolve the safe/unsafe split; 24 changed the figure by under 0.3 points |
| `threshold` | `fixed` | §4: adaptive is identical on 98.9% of bits and no better on any indicator |
| `adaptive_window_frames` | 2600 (10 s) | Wide enough to track drift without chasing the data. Unused by default |
| `hysteresis` | 0.0 | §4: changes literally zero bits. No bit is close enough to the threshold |
| `local_normalise` | `false` | §4 here and Day 12 ablation: lowers separation, changes 1.9% of bits, improves nothing |
| `local_normalise_window` | 261 (1 s) | Only used if the option is switched on |
| Sampling rule | frame furthest from threshold, within each bit | Day 09, chosen over three alternatives |

**Changes from v1:** phase is a convention rather than an estimate; the ensemble and safe mask are new; the sub-frame edge experiment was tried and rejected (§2).

---

## 7. Where This Leaves Us

**Improved:** the decoder no longer claims a confidence it does not have. It reports what is decided and what is not, and 44% of every stream is now usable in a way it was not on Day 15.

**Not improved:** the symbol timing itself. One approach failed (§2; see the correction at the top). Sub-frame interpolation failed because the data lacks intermediate frames; everything else fails for the reason Day 13 established — the transitions carry no grid structure to lock onto.

**Still true:** no ground truth. Nothing here measures whether a bit is right. A stream can be 100% phase-independent and still wrong about every bit if the period is wrong.

**The honest state:** we have a decoder that is stable, deterministic, and clear about its own limits, producing bits we cannot check, at a bit rate the data argues against.

### Next

Day 14's beat is still the untried lead. The shared glitches occur when a bit boundary falls at a particular point inside a frame, which is precisely phase information, and they repeat every about 21 frames. That was the plan coming out of Day 15 and it has not been attempted yet — the sub-frame approach tried today was cheaper and turned out to be a dead end.

That is the one remaining route to the phase that does not need the faculty. Q1 (the transmitted bits for a single video) would settle it immediately, and is now three weeks old.
