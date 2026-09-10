# Day 15 — Threshold OOK Baseline

**Project:** Optical Camera Communication (OCC) Video Message Decoding
**Built:** a threshold decoder with fixed and adaptive modes, run over all of Signal V1.
**Produced:** 46,372 preliminary bits across 10 lamps, two decoders each.

**Files:** `decoder.py`, `bits/` (the bit sequences and the report), `fig_decode.png`.

> **Note (2026-09-10, audit).** Only `decode_report.json` (in this folder, not `bits/`) was committed; the 20 `.npy` bit files were not. Re-running `decoder.py` on the regenerated `../../week02/day12/signal_v1/` reproduces the report exactly. The §2 table is computed with the phase **held at the fixed decoder's choice**, which the original `decoder.py` did not output — the JSON's `fixed_vs_adaptive_agree_pct` lets each decoder pick its own phase and reads about 60 % on three signals (§3). `decoder.py` now also writes `fixed_vs_adaptive_agree_pct_same_phase`, and the report has been regenerated with that one extra field (every other value unchanged). The Day 15 task also asked for mentor feedback; none is recorded here.

**Read this first.** The decoder works. The bits are not trustworthy, and the reason is specific and fixable-in-principle. It is set out in §3.

---

## 1. What Was Built

Two decision rules, sharing the same sampling method.

| | Fixed | Adaptive |
|---|---|---|
| Threshold | One level for the whole signal: midpoint of the 10th and 90th percentiles | Rolling midpoint over a wide window, plus a Schmitt trigger |
| Purpose | The deliberately simple baseline | Guards against a slow shift in level |
| Sampling | Within each bit, the frame furthest from the threshold | Same |

The sampling rule comes from Day 09, where it beat three alternatives.

### Preliminary bits

| Video | Lamps | Bits per lamp | Total |
|---|---|---|---|
| 1LED | 1 | 9,856 | 9,856 |
| 2LEDs | 2 | 6,084 | 12,168 |
| 3LEDs | 3 | 4,056 | 12,168 |
| 4LEDs | 4 | 3,045 | 12,180 |

**46,372 bits** from the fixed decoder, the same again from the adaptive one. All at the assumed 92 bps.

First 120 bits of `1LED` lamp 1:

```
111000111001001110111111000100111110000000010101010011010001100010100001010000011111101110001111110010000000010111011111
```

---

## 2. Indicators That Look Good

No ground truth exists for these videos, so none of this measures correctness. These are internal consistency checks.

### The threshold choice barely matters

Holding the phase fixed and swapping fixed for adaptive:

| Signal | Bits identical |
|---|---|
| 1LED L1 | 98.76% |
| 2LEDs L1 / L2 | 99.44% / 99.65% |
| 3LEDs L1–L3 | 99.11% / 98.74% / 98.92% |
| 4LEDs L1–L4 | 97.90% / 97.08% / 98.82% / 97.11% |

Median **98.79%**. On a signal this clean, the two thresholds agree on almost every bit. The adaptive version has nothing to correct, which matches Day 08: the lamp's level moves at most 0.13 grey levels across a whole recording.

### The decisions are confident

Every bit is decided by a frame sitting far from the threshold — a median margin of about half the full signal range. No bit is marginal.

### The streams look like data

| | Range across the 10 lamps | Random data would give |
|---|---|---|
| Share of ones | 39.2% to 60.0% | 50% |
| Flip rate | 43.3% to 48.8% | 50% |

Nothing degenerate: no stuck lamp, no all-ones, no obvious periodicity in the values.

---

## 3. The Indicator That Does Not

**The decoder's output is decided by a phase choice it has no basis for making.**

### How this showed up

Running fixed and adaptive across all ten signals, three came out at about 60% agreement while the rest were near 99%. The cause was not the threshold. In those three, the two decoders had picked **different phases** — 2.26 frames against 0.00, and so on. A different phase means a completely different bitstream.

### Why the phase cannot be chosen

We pick the phase by maximising confidence: the phase whose sampled frames sit furthest from the threshold. Sweeping the phase across a whole bit on `1LED`:

| Phase shift | Bits unchanged | Confidence score |
|---|---|---|
| 0.0 bit | 100% | 123.5 |
| 0.1 | 92.6% | 123.5 |
| 0.2 | 85.6% | 123.5 |
| 0.3 | 78.4% | 123.5 |
| 0.5 | 67.6% | 123.5 |
| 0.7 | 58.4% | 123.5 |

**The confidence score does not move. At all.** Meanwhile a third of the bits change.

So the criterion we use to choose the phase is completely blind to it, and the phase we end up with is set by floating-point noise. Whichever phase wins, the decoder reports full confidence.

### This is a consequence of a Day 09 decision, and I got the trade-off wrong

On Day 09 I compared four sampling rules and chose "the frame within the bit that is furthest from the threshold", because it scored 0.00% marginal bits **at every phase**. I presented that phase-insensitivity as the rule's main strength.

It is a strength for reading a bit once the boundaries are known. But it is exactly what destroys our ability to *find* the boundaries. With 2.83 frames per bit, at least one frame always falls cleanly inside the bit — so every phase looks equally good, because for every phase one clean frame exists.

The rule that made sampling robust removed the signal the phase estimate needed. I should have caught that when I wrote "it does not care where we think the bit starts" on the Day 09 slide. That sentence was the warning.

### What this means for the bits

They are internally consistent, confident, and stable against threshold choice. And they are one arbitrary phase choice away from a substantially different answer. Roughly a third of them would flip under a half-bit shift that nothing in our measurements argues against.

---

## 4. The Test for a Repeating Message

Without ground truth, one check could still have validated the clock: if the transmitter loops a message, the bitstream contains the same block twice, and the right bit rate would make that repeat sharp.

Tested across eleven candidate rates from 88 to 150 bps. *(Audit note: `decode_report.json` holds the 92 bps run only; the other rates were re-checked on 2026-09-10 and give the same picture — 7.1–8.6× on `1LED` with no rate preferred. Regenerate with `--rates 88,90,91,92,94,100,110,120,124,136,150`.)*

| Rate | Best lag | Strength against noise |
|---|---|---|
| 91 bps | 107 bits | 7.8x |
| 92 bps | 310 bits | 7.6x |
| 124 bps | 39 bits | 7.9x |
| 136 bps | 32 bits | 8.0x |

**No repeat anywhere.** On `1LED` every rate sits between 7 and 9 times the noise level (4 to 9 times across the ten lamps at 92 bps), with no peak standing out and no rate preferred. The "noise level" is the spread of the autocorrelation over all lags, which shrinks with lag, so a ratio of several times noise is what random bits give; the evidence is the absence of a spike, not the ratio. A genuine looping message would spike far above that, at one rate only.

Two readings, and we cannot yet separate them:

1. The message does not repeat within the recording.
2. Our bits are wrong, so any repeat is scrambled.

Either way, this route to validating the clock is closed.

---

## 5. For the Mentor — Confirming Direction

### What we have

A working threshold decoder, 46,372 preliminary bits, and a clear account of why they cannot be trusted.

### The question

**Should we keep building on the 92 bps assumption, or stop and wait?**

The case for continuing: the pipeline gets built and tested end to end, so when the answers arrive we only re-run. The Day 14 beat finding put a candidate near 91 bps back in play, so 92 may yet be right.

The case for stopping: every bit produced is one arbitrary phase choice from a different answer. Effort spent tuning against unverifiable output can easily make things worse while appearing to make them better — and we would not be able to tell.

### Our recommendation

Continue building, but **stop tuning**. Concretely:

- Keep the decoder and keep it simple. Do not adjust parameters to improve indicators that cannot measure correctness.
- Spend Week 3 effort on the phase problem (§6), which is a real, self-contained technical problem that does not need the faculty.
- Treat every bit sequence as provisional and label it that way in the files, which `decode_report.json` already does.

### Still blocking, now three weeks old

| # | Question | What it unblocks |
|---|---|---|
| **Q1** | The transmitted bits for one video | Everything. Correctness, BER, the ML branch, and the phase problem all at once |
| **Q2** | What sits above the raw bits | The leading hypothesis from Day 14 |
| **Q3** | Is 92 bps the payload rate or the light's switching rate | Narrows five hypotheses to one or two |

Q1 would also solve §3 outright: with known bits, the correct phase is whichever one reproduces them.

---

## 6. Next Step, and It Does Not Need the Faculty

The phase problem is self-contained, and Day 14 pointed at the tool.

The sampling rule is blind to phase because it looks at one frame per bit in isolation. But the **shared glitches** found on Day 14 are a phase measurement — they occur when a bit boundary falls at a particular place inside a frame, which is why they coincide across lamps that carry different data.

So: estimate the phase from the glitch pattern rather than from per-bit confidence. The glitches repeat every about 21 frames, and that beat is where the boundary information lives.

This is worth trying before any more decoder work, because every downstream number depends on the phase being right.

---

## 7. Files

| File | What it is |
|---|---|
| `decoder.py` | Fixed and adaptive threshold decoder, with the consistency checks built in |
| `bits/*_fixed.npy`, `bits/*_adaptive.npy` | Preliminary bit sequences, 20 files |
| `bits/decode_report.json` | Per-signal indicators: margins, stream statistics, phase stability, repetition |
| `fig_decode.png` | The three results of §2 to §4 in one figure |
