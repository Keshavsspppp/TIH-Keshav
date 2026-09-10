# Day 09 — ROI and Signal Plan (for approval)

**Project:** Optical Camera Communication (OCC) Video Message Decoding
**Goes with:** `Day09_progress_pack.pptx` (3 slides)
**Status:** preprocessing **frozen** as of today, pending the two answers in §7.

Everything below was measured on the four supplied videos, not assumed.

---

## 1. Transmitter Detection — Confirmed Strategy

### The problem we had

On Day 07 the ROI finder failed on three of the four videos. It merged the two lamps in `2LEDs` into one box, and picked 2-pixel specks of glare in `3LEDs` and `4LEDs`.

### What fixed it

The old method looked at **shape**: find bright changing areas, take the biggest blobs. That cannot separate two lamps sitting next to each other, because their bright regions touch.

The new method looks at **behaviour**: group the changing pixels by how their brightness moves over time. Pixels belonging to one lamp blink together. Pixels of different lamps do not — Day 07 measured their correlation at only 0.31 to 0.41.

So the thing that makes the lamps hard to separate by shape is exactly the thing that separates them by behaviour.

### The steps

| Step | What it does | Why |
|---|---|---|
| 1 | Sample about 600 frames spread across the whole active part | Fixes risk R4 — looking only at the start missed the signal in `4LEDs` entirely |
| 2 | Keep pixels whose brightness varies a lot, using an **absolute** cut (`var ≥ max(400, 3% of the highest)`) | A percentile cut caps you at a fixed share of the frame, which fails once four lamps fill more of it |
| 3 | Group those pixels by their brightness-over-time behaviour (k-means on normalised signals) | This is the step that splits touching lamps |
| 4 | Choose the number of groups: keep the largest count whose group signals still differ (max correlation below 0.85) | Groups that behave alike are one lamp split in two |
| 5 | Drop groups that are not solid discs — fill below 40% of their box, or fewer than 25% of the largest group's pixels | Removes halo and glare. Fixes risks R2 and R3 |

### Result

| Video | Lamps expected | Lamps found | Boxes |
|---|---|---|---|
| 1LED | 1 | **1** | (294,117) 105×105 |
| 2LEDs | 2 | **2** | (319,23) 74×82 · (418,25) 73×81 |
| 3LEDs | 3 | **3** | (410,41) · (481,42) · (554,46), about 48×48 each |
| 4LEDs | 4 | **4** | 2×2 grid, about 66×66 each |

**The lamp count was never given to the detector.** It is worked out from the data and matches the filename in all four videos. The faint glare smudge in `1LED` is correctly ignored.

> **Note (2026-09-10, audit):** re-run of `roi_extract.py` on `../../Videos/` finds the same 1/2/3/4 lamps and the same boxes (regenerated `rois.json` added to this folder). The boxes finally used by Signal V1 differ by ≤ 1 px (`../day12/SIGNAL_V1_MANIFEST.json`), because `roi_extract.py` does not seed k-means — fixed in `../day11/occ_pipeline.py`. The "0.31 to 0.41" correlation quoted above is the Day 07 figure; on the final per-lamp signals it is 0.36–0.44 (`../../week01/day07/DAY_07_FINDINGS.MD` §4 correction).

### Trimming

Trim on **sustained activity** — the first point where the lamp is lit for at least 15% of a one-second window — not on the first bright frame.

This matters for `2LEDs`, which has a brief flash at frame 93 followed by 3.4 seconds of darkness before the real transmission. Trimming naively would have fed that silence into the timing recovery. The new rule starts it at frame 778 instead of 93.

> **Corrected on Day 11 (2026-09-10, audit note).** 778 is the *start of the first one-second window* that holds enough activity, not the first lit frame — so this rule still fed about 200 dark frames (0.8 s) to every signal. `../day11/occ_pipeline.py` steps forward to the first lit frame inside that window; the trim points Signal V1 actually uses are 217 / 975 / 965 / 1816 (`../day11/DAY_11.MD` §3). The Day 10 notebook was run with the 778-style trims from `rois.json`.

---

## 2. Signal Extraction — The Measurement That Decided It

### The problem

2.83 frames per bit means roughly **one frame in three straddles a bit boundary**. Those frames are partly lit, so their brightness lands somewhere in the middle. Read one as a bit and it could go either way.

So the question is: given the frames covering one bit, which value do we use?

### Four rules, tested at every possible bit phase

We measured the share of bits whose value lands too close to the threshold to trust (within 25 grey levels of it). Lower is better.

| Rule | Best | Worst | Verdict |
|---|---|---|---|
| **Most confident frame inside the bit** | **0.00%** | **0.00%** | **Chosen** |
| Nearest frame to the bit centre | 1.13% | 2.22% | Good, simpler |
| Interpolated value at the bit centre | 5.94% | 7.45% | Interpolation *creates* middle values |
| Averaged across the whole bit | 18.28% | 20.89% | Worst |

### Why averaging is the worst, and why that surprised us

Averaging over the bit is the textbook matched-filter answer, and it is what we would have written if we had not tested it. It fails here because it deliberately includes the straddling frames — the exact frames that carry the ambiguous values. It drags every bit toward the middle.

### Why the winner works

With 2.83 frames per bit, **at least one frame per bit falls entirely inside that bit** and is therefore fully on or fully off. Which frame that is changes from bit to bit, because 2.83 is not a whole number. So instead of fixing a position, we take the frame within the bit whose brightness is furthest from the threshold.

This is why it scores 0.00% at **every** phase we tested. It does not need to know where the bit starts.

> **Forward reference (2026-09-10, audit note).** Day 15 found the other side of this property: because the score is identical at every phase, it carries **no information about the phase**, so the decoder cannot estimate where bits start — the phase it reports is set by floating-point noise, and a third of the bits change under a half-bit shift (`../../week03/day15/DAY_15.MD` §3). Day 16 measured that only about 44 % of each bit stream is decided regardless of phase (`../../week03/day16/DAY_16.MD` §3). The robustness claimed here is real for *reading* a bit once its boundaries are known; it is what removed the signal needed to *find* the boundaries.

### The honest caveat

This rule picks the frame that most agrees with a decision the threshold has already made. It cannot turn a correct bit into a wrong one, but if the threshold itself is badly placed, this rule will confidently follow it there.

So it must be tested against threshold error, not just phase error. That test is added to the plan as experiment **E09b**, and the result goes in the report whichever way it comes out.

### What the eye diagram actually shows

Worth stating plainly, because slide 2 shows it and it is easy to misread: **the eye is not cleanly open.** Transitions land at every position inside the bit, because 2.83 is not a whole number. There is no fixed sampling point that is always safe.

That picture is the justification for the chosen rule, not a decoration.

---

## 3. Frozen Preprocessing

Locked as of today. Any change from here needs a log entry and a re-run of everything downstream.

| # | Step | Setting | Why |
|---|---|---|---|
| 1 | **Trim** | Sustained activity, 1-second window, 15% lit | The `2LEDs` false start |
| 2 | **Locate lamps** | Behaviour clustering, one ROI per lamp, fill ≥ 0.40, share ≥ 0.25 | §1 |
| 3 | **Brightness** | Mean of the brightest **half** of the pixels in each ROI | Avoids diluting with dark corner pixels; steps away from the clipped centre |
| 4 | **Detrend** | **OFF** by default | Ambient varies by about 0.1% of contrast (Day 08). There is nothing to remove |
| 5 | **Normalise** | **OFF** by default | Same reason |
| 6 | **Smoothing** | **OFF** | The signal is already near-binary. Smoothing would blur the edges we are reading |
| 7 | **Sample** | Most confident frame inside each bit | §2 |

Steps 4, 5 and 6 stay in the code behind config flags. They are switched off because this dataset does not need them, not because they are wrong. Their value is shown on the synthetic videos in experiment E11, and that result is reported as a synthetic result.

**This is a real change of position.** The original plan had detrending and normalising as central parts of M1. The measurements say otherwise for this dataset, and we would rather change the plan than run steps that do nothing so the plan looks unchanged.

---

## 4. Synchronisation Approach

| Question | Answer | Confidence |
|---|---|---|
| Bit rate | 260 fps ÷ 92 bps = **2.826 frames per bit** | Confirmed from run lengths (Day 07) |
| How we find the phase | Search all offsets from 0 to one bit, keep the one with the widest separation between the two brightness groups | Standard, and cheap |
| How much does the phase matter | With the chosen extraction rule, **almost nothing** — 0.00% at every phase tested | Measured |
| Long clips | Re-estimate the phase in blocks rather than once per video | Not yet tested; `1LED` runs 28,000 frames, so a small frame-rate error would build up |

The phase search still runs, even though the chosen rule barely needs it. It costs little, and the phase estimate is itself a reportable number: if it drifts across a clip, that tells us the real frame rate is not exactly 260.

> **Correction (2026-09-10, audit; the table above is kept as the record).** Row 1 — "Confirmed from run lengths (Day 07)" is wrong. The Day 07 run-length table omitted the 1-, 4- and 7-frame runs that cannot exist at 2.826 frames per bit; they are about 22 % of the runs in `1LED` (`../day10/Day10_EDA.ipynb` §4), and no bit rate shows clock structure (`../day13/Day13_Synchronisation.ipynb`). **92 bps is an assumption from the filename, not a measurement.** Row 3 — "almost nothing" is true for the confidence score and is precisely the problem: the score cannot see the phase at all (see the §2 note). The same "bit rate is known" wording appears on slide 4 of `DAY09_KeshavPrasad_PPT.pptx.pdf`, which is not edited.

---

## 5. Evaluation Approach

| Metric | How | Available now? |
|---|---|---|
| Message correctness | Exact match against ground truth | **No — no ground truth** |
| BER | Wrong bits ÷ total bits, with the alignment offset reported | **No — no ground truth** |
| Normalised edit distance | Reported next to every BER | **No** |
| **Bits near the threshold** | Share of bits read too close to the threshold to trust | **Yes — this is what we used today** |
| Phase tolerance | Range of bit-start offsets where quality holds | **Yes** |
| Threshold tolerance | Range of threshold values where quality holds | **Yes** (E09b) |
| ROI tolerance | Range of box sizes and offsets where quality holds | **Yes** |
| Runtime | Seconds per video, ms per frame | **Yes** |

**The important line here:** without ground truth we cannot say whether a decode is *correct*. But we can say how *confident* it is, and how far the settings can drift before that confidence collapses.

"Bits near the threshold" is a stand-in, not a replacement. It measures how cleanly the bits separate, not whether they are right. A decoder with a wrong threshold could score 0.00% and be wrong on every bit. We use it because it is the strongest measure available today, and we label it as a proxy every time it appears.

---

## 6. What We Ask You to Approve

1. **The ROI strategy** — behaviour clustering rather than shape, one box per lamp (§1).
2. **The extraction rule** — most confident frame inside each bit (§2).
3. **The frozen preprocessing** — including detrending, normalising and smoothing switched **off** for this dataset (§3).
4. **The within-video split** — tune on the first 30% of each video, report on the last 70%, because four videos of four different setups cannot support a video-level split.

---

## 7. What Blocks Us

| # | Question | What it blocks |
|---|---|---|
| **Q1** | Can we have the transmitted bits or messages? | Every correctness number, BER, and the whole ML branch. Right now we can only measure confidence, not correctness |
| **Q2** | What framing sits above the raw bits — preamble, parity, line coding? | We recovered 2,123 bits that are not plain text and not Manchester. We cannot go further without the format |
| Q3 | Is 92 bps per lamp, or shared across all lamps? | Whether `4LEDs` is 368 bps total or 23 bps each |
| Q4 | Is "1" the lamp on, or off? | A wrong guess inverts every bit |

---

## 8. Next Steps Once Approved

1. Run the frozen pipeline across all four videos and all lamps; save per-lamp bitstreams.
2. Run the threshold-tolerance test (E09b) — the one open risk in the chosen extraction rule.
3. Check whether the bit phase drifts across a 28,000-frame clip.
4. Run the ROI tolerance sweep (E07): how far can the box move and shrink before quality drops?
5. Once ground truth arrives, turn every "bits near the threshold" number into a real BER.

---

## 9. Files

| File | What it is |
|---|---|
| `Day09_progress_pack.pptx` | The 3-slide pack |
| `roi_extract.py` | Trimming and per-lamp ROI detection |
| `fig_roi.png` | All four videos with the detected boxes drawn |
| `fig_phase.png` | The four extraction rules across every bit phase |
| `fig_eye_only.png` | Eye diagram for one bit |
| `rois.json` | Trim points and lamp boxes for all four videos — **regenerated 2026-09-10** from `../../Videos/` with `roi_extract.py` (the original was not committed; trims match the Day 10 notebook to within 3 frames) |

> **Note (2026-09-10, audit):** `Day09_progress_pack.pptx` is in this folder as `DAY09_KeshavPrasad_PPT.pptx.pdf` (its title slide still reads "DAY 03 REVIEW"). `fig_eye_only.png` is not in the repository. `roi_extract.py` reads `data/raw/*.mp4`; copy or link `../../Videos/` there to run it.
