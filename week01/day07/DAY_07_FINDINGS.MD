# Day 07 — Findings on the Supplied Dataset

**Project:** Optical Camera Communication (OCC) Video Message Decoding
**Dataset received:** 4 videos, 226 MB total
**Inspection run:** E00, complete. Raw copy preserved and fingerprinted.

**Short version:** the data is much better than we planned for, and much smaller. The signal is almost perfectly clean and every video is decodable in principle. But there is no ground truth, the bits are not plain text, and four videos of four different setups is not enough to claim that anything generalises. Three things in the methodology need changing because of what we found.

---

## 1. What We Received

| Video | Frames | Length | Size | Bits available |
|---|---|---|---|---|
| `1LED_92bps.mp4` | 30,058 | 115.6 s | 102 MB | about 9,900 |
| `2LEDs_92bps.mp4` | 21,157 | 81.4 s | 62 MB | about 6,400 per LED |
| `3LEDs_92bps.mp4` | 13,057 | 50.2 s | 34 MB | about 4,100 per LED |
| `4LEDs_92bps.mp4` | 11,033 | 42.4 s | 38 MB | about 3,000 per LED |

All four: 640×360, `mpeg4` codec, `yuv420p`, **260 frames per second**, fixed frame rate (timing jitter 0.00009, so the frames are evenly spaced — good).

The raw copy is in `data/raw/`, read-only, with a `SHA256SUMS` file. Fingerprints are in `DATASET_MANIFEST.csv`.

> **Correction (2026-09-10, audit).** `DATASET_MANIFEST.csv` was produced with `inspect_dataset.py --max-frames 8000`, so its `counted_frames` column reads 8000 for every video and its `verdict_reasons` say "header says 30058 frames, we counted 8000". That is a tool artefact, not a discrepancy: the scan was capped and the verdict code did not know it. A full read on Day 08 (`../../week02/day08/DAY_08.MD` §3) found header and counted frames identical for all four videos. The verdict code has been fixed to report a capped scan as such, and `DATASET_MANIFEST_fullscan.csv` (uncapped re-run, 2026-09-10, on a machine without `ffprobe`, so the container-metadata columns are blank) is added alongside. The frame counts in the table above are the header values and are correct.

---

## 2. The Big One: 260 fps, Not 30

Our whole plan assumed a normal camera at 30 or 60 fps. These were shot at **260 fps**.

This matters more than anything else in this report:

```
frames per bit  =  260 fps ÷ 92 bits per second  =  2.83
```

**2.83 samples per bit is above the sampling limit of 2.** So the message can be recovered from plain per-frame brightness. We do **not** need rolling-shutter stripe decoding, and we do not need any of the undersampled schemes (UFSOOK, UPSOOK) from the literature review.

At 30 fps this would have been 0.33 samples per bit — hopeless without stripe decoding. Presumably the faculty picked a high-speed camera so the problem stays solvable in software. Worth saying in the Week 2 slides, because it explains why our approach is the right one.

**And 2.83 is not a whole number**, which is exactly the hard case we designed the synthetic generator around (`sps = 3.7` in E01). That design choice now looks correct rather than lucky.

### Confirmed from the data, not just from the filename

We measured how long the light stays at one level. If one bit lasts 2.83 frames, runs should cluster at 3 frames, with weaker groups near 6 (two same bits in a row) and 8–9 (three in a row).

That is exactly what we see in all four videos:

| Run length | 1LED | 2LEDs | 3LEDs | 4LEDs |
|---|---|---|---|---|
| 2–3 frames (1 bit) | 258 | 129 | 240 | 222 |
| 5–6 frames (2 bits) | 56 | 32 | 49 | 48 |
| 8–9 frames (3 bits) | 12 | 6 | 10 | 16 |

So "92bps" in the filename is real, and the frame rate in the file header is real. The two agree with the pixels.

> **Correction (2026-09-10, audit). The paragraph above is wrong and is kept as the record of what was believed on Day 07.** The table only bins runs of 2–3, 5–6 and 8–9 frames. It leaves out runs of 1, 4 and 7 frames, which are the runs that *cannot* occur if one bit lasts 2.826 frames. On the full `1LED` signal, 1-frame runs are 9.0 % of all runs and 4-frame runs are 13.7 % (22.7 % together; 25–27 % on the nine multi-lamp signals), and hysteresis does not remove them (`../../week02/day10/Day10_EDA.ipynb` §3–4). The level changes fit a 92 bps grid only 0.3 % better than randomly chosen times, and no other rate does better (`../../week02/day13/Day13_Synchronisation.ipynb` §3). `signal_check.png` above already shows level changes that do not sit on the green 2.83-frame grid. **The frame rate (260 fps) is measured. The bit rate (92 bps) is taken from the filename and is not confirmed by the data; from Day 10 on it is treated as an assumption.** Everything in this file that says "2.83 frames per bit" should be read with that caveat, including §7 row 1 and §9.

---

## 3. The Signal Is Very Clean

See `signal_check.png`.

The LED brightness sits at either **0** or **about 245**, with a wide empty gap between. The histogram has two tall spikes and almost nothing in between. The only middle values are single frames that straddle a bit boundary — expected, because 2.83 is not a whole number.

**What this means for our plan.** We expected the fixed-threshold baseline (M0) to be weak, and built M1 to fix ambient drift and exposure changes. On data this clean, **M0 may already work well.** A simple threshold at 124 separates the two levels with room to spare.

That is not bad news, but it does change the story:

- If M0 already decodes correctly, "M1 beats M0" will be a small or zero improvement, and Gate G3 as written may never pass.
- The interesting result is no longer "can we decode it". It is **how far can the settings be wrong before it stops working** — which is exactly the sensitivity study we already chose as our contribution.

So the project's contribution is now *more* important, not less. If everything decodes perfectly at the best settings, the tolerance ranges are the only thing left worth measuring. We should say this plainly rather than hunting for an accuracy gap that is not there.

---

## 4. The Multiple LEDs Carry Different Data

This was worth checking and the answer is not what the pictures suggest. In `leds_on.png` all the lamps look like they light up together, which would mean they repeat the same signal.

They do not. We compared their brightness signals over time:

| Video | LED 1 vs LED 2 |
|---|---|
| 3LEDs | +0.41 |
| 4LEDs | +0.31 |

If they carried the same bits, this would be close to +1.00. At 0.3 to 0.4 they are clearly **different data streams sharing some structure** — most likely a shared preamble or frame timing, which would explain why the correlation is well above zero but nowhere near one.

> **Correction (2026-09-10, audit).** These two numbers came from the Day 07 ROI finder, which §5.4 below says mis-located lamps in `3LEDs` and `4LEDs`. On the per-lamp signals of Signal V1 (Day 12) the whole-clip correlations are 0.39 (`2LEDs`), 0.38–0.41 (`3LEDs`) and **0.36–0.44** (`4LEDs`; lamp 1 vs lamp 2 is 0.435, not 0.31). The conclusion — different data, shared structure — stands. Later documents that quote "0.31 to 0.41" (Day 09, Day 14) inherit the Day 07 value. Day 14 and Day 16 attribute the shared structure to a common transmitter clock; the shared-preamble explanation offered here has not been ruled out.

**So more LEDs means more bits per second, not a stronger single signal.** The four videos are a throughput ladder: 92 bps, then 184, 276, 368. Each LED needs its own ROI, its own timing and its own decode, and the streams get combined at the end.

This needs confirming with the faculty (question Q4 below), because it changes what "decoded message" even means for the multi-LED videos.

---

## 5. Problems Found

### 5.1 No ground truth at all — the biggest gap

No bit files, no message files, nothing. As things stand:

- **BER cannot be computed on any real video.**
- Message correctness cannot be checked either, because we do not know what the message is meant to say.
- The ML branch (M2) is impossible — Gate G4 fails outright.

This is the single most important thing to ask for. Without it, every real-data number we produce is unverifiable.

### 5.2 The bits are not plain text

We ran a first decode on `1LED_92bps` and recovered 2,123 bits. Then we checked what they might be:

| Test | Result |
|---|---|
| Read as 8-bit characters, all 4 alignments (normal/inverted, either bit order) | 41–44% printable — that is what random bytes give. Not text |
| Manchester coding | 54% of bit pairs alternate. Manchester would give 100%. Not Manchester |
| Repeating packet structure in the bits | Weak. Best repeat scores only 0.31 |

So there is **some framing or coding on top of the raw bits that we do not know about**. This is not a failure — it is exactly the "unknown packet structure" blocker from Week 1, now confirmed as real rather than hypothetical. It needs an answer from the faculty (Q2).

> **Note (2026-09-10, audit):** the code for this first decode (2,123 bits, the printable-character test, the 54 % Manchester figure) is not in the repository, so these three numbers cannot be reproduced. On the Signal V1 bits at 92 bps the Manchester alternation is about 48 % (Day 10 and Day 13 quote 47 %). The conclusion — not text, not Manchester — is unchanged.

It is also possible our timing is slightly off and the bits are simply wrong. We cannot tell these two cases apart without ground truth. That is precisely why 5.1 matters so much.

### 5.3 Dark lead-in and lead-out in every video

Every video has dead time at the start and end where nothing transmits:

| Video | Dark at start | Active | Dark at end |
|---|---|---|---|
| 1LED | 217 frames | 217 → 28,072 | 1,985 frames |
| 2LEDs | 93 | 93 → 18,169 | 2,987 |
| 3LEDs | 965 | 965 → 12,430 | 626 |
| **4LEDs** | **1,816** | 1,816 → 10,424 | 608 |

This is not a defect, but it must be trimmed before decoding or the timing recovery will lock onto silence.

It also caught us out: our first analysis pass read the first 1,500 frames of each video and reported that `4LEDs` had **no blinking at all** — because in those frames there genuinely is none. Anything that looks at only the start of a file will get this wrong.

### 5.4 The automatic ROI finder is not good enough yet

It found the light correctly in `1LED`. On the others it struggled:

- **2LEDs:** merged both lamps into one box. They are close together, so their high-change regions touch.
- **3LEDs and 4LEDs:** found 2 real lamps plus a 2–3 pixel speck of glare, and missed the rest.

The variance map is the right idea — it locks onto the lamps immediately and ignores the dark room. But the step that turns the map into separate boxes needs work: it should split touching blobs and reject specks. This is a real work item for M1, now with concrete failing cases to test against.

### 5.5 All LEDs are clipped

Every lamp reaches 255 out of 255. The brightness is flat-topped at the top of the range.

For on/off this is harmless, and arguably helps — it widens the gap between the two levels. It does mean any multi-level reading is impossible, and our brightness statistic should use pixels away from the clipped core.

---

## 6. Four Videos: What We Can and Cannot Claim

This is the part most likely to be challenged, so it should be faced directly.

We have four videos. They are **not four samples of the same thing** — they are four different setups (1, 2, 3 and 4 LEDs). So we effectively have **one video per condition**.

What follows from that:

- The DEV/TEST split from `METHODOLOGY_V1.MD` §6.3 cannot work as written. Holding one video back means losing a whole condition, and testing on a condition we never tuned on tells us nothing useful either way.
- We **cannot** claim our method generalises across conditions. With one video per condition there is no way to separate "our method works" from "our settings happen to suit this clip".

**Proposed replacement split, for the mentor to approve:**

| Role | What we use |
|---|---|
| **Tuning** | The first 30% of each video |
| **Reporting** | The remaining 70% of each video, never looked at while tuning |
| **Fake data** | Still used for controlled noise, drift and compression tests |

Splitting by time within a video is weaker than splitting by video, and we should say so. But it is honest, it is checkable, and it is better than tuning and reporting on the same frames.

The good news: each video holds thousands of bits, so a 70% held-out portion still gives 2,000 to 7,000 bits per video. That is plenty for a meaningful BER — **if we ever get ground truth**.

---

## 7. What Must Change in the Methodology

| # | Change | Where |
|---|---|---|
| 1 | Frame rate is 260 fps and `sps` is 2.83, not unknown. Rolling-shutter decoding is out of scope for good — the reason is now a fact, not an assumption | `METHODOLOGY_V1.MD` §3, `DAY_06.MD` §2 |
| 2 | The ROI finder must sample frames from across the whole video, and must handle touching lamps and reject specks | `DAY_06.MD` §2.2 |
| 3 | Add a trimming step before decoding, to cut the dark lead-in and lead-out | Pipeline stage 3 |
| 4 | Replace the DEV/TEST split with the within-video time split in §6 above | `METHODOLOGY_V1.MD` §6 |
| 5 | Gate G3 ("M1 beats M0") probably cannot pass on data this clean. Re-word it: M1 must match M0 on accuracy and beat it on tolerance range | `DAY_06.MD` §5 |
| 6 | Mark M2 as not runnable, with the reason: no labels supplied | `EXPERIMENT_PLAN_V2.MD` Phase E |
| 7 | Each LED needs its own ROI, timing and decode, then the streams get combined | Pipeline stages 3–7 |

> **Note (2026-09-10, audit):** row 1 — `sps = 2.83` is *not* a fact; see the §2 correction. Row 4 — adopted (Day 08 R9, Day 09 §6), never exercised. Row 5 — the re-wording of G3 was never formally adopted or closed; see `../day05/DAY_05.MD` §5 note. `METHODOLOGY_V1.MD` is not in the repository.

---

## 8. Questions for the Faculty

In priority order. The first three are blocking.

| # | Question | Why it blocks |
|---|---|---|
| **Q1** | **Can we have the transmitted bits or messages for these four videos?** | Without them, no BER, no correctness check, and no ML branch. Everything on real data becomes unverifiable |
| **Q2** | **What sits on top of the raw bits?** Any preamble, start/stop bits, parity, CRC, or line coding? | We recovered 2,123 bits that are not plain text and not Manchester. We cannot go further without knowing the format |
| **Q3** | **Is 92 bps per LED, or 92 bps shared across all the LEDs?** | Decides whether the 4-LED video is 368 bps total or 23 bps each |
| Q4 | Do the LEDs carry different data? Our measurement says yes (correlation 0.31–0.41), but please confirm | Decides whether we decode each LED separately or combine them first |
| Q5 | Is 260 fps exact, or nominal? A small error compounds over 30,000 frames | Affects long-clip timing drift |
| Q6 | Are more videos coming, especially repeats of the same setup? | Four videos of four setups means we cannot claim generalisation (§6) |
| Q7 | Is "1" the light being on, or off? | A wrong guess inverts every bit |
| Q8 | Is the message the same in all four videos, or different? | Changes how we compare them |

---

## 9. Where We Stand

**Good:**

- The dataset is real, clean, and technically decodable. 2.83 frames per bit, above the sampling limit.
- The signal is close to perfectly binary, with a wide gap between on and off.
- Every video has thousands of bits — no shortage of data within each clip.
- Fixed frame rate, no dropped frames, no black frames, no duplicate files.
- Our synthetic generator's awkward `sps = 3.7` case turned out to match the real problem.

**Bad:**

- No ground truth. This blocks BER, correctness and the entire ML branch.
- The bit format is unknown, and we cannot work it out without ground truth.
- Four videos of four different setups. We cannot claim generalisation, and we should not pretend otherwise.

**Next, once Q1 to Q3 are answered:**

1. Trim the dark lead-in and lead-out.
2. Fix the ROI finder for touching lamps.
3. Run M0 and M1 across all four videos with the within-video time split.
4. Start the sensitivity sweeps — which, given how clean the data is, are now the main result rather than a side study.

---

## 10. Files

| File | What it is |
|---|---|
| `DATASET_MANIFEST.csv` | One row per video: fingerprint, format, frame rate, verdict |
| `signal_check.png` | LED brightness against the 2.83-frame bit grid, plus the histogram |
| `leds_on.png` | Frames from each video with the lamps lit |
| `inspect_dataset.py` | The inspection tool (from Day 07) |
| `preserve_raw.sh` | The raw-copy tool (from Day 07) |
