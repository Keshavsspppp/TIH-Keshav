# Experiment Log

**Project:** OCC Video Message Decoding
**Owner:** Keshav

**Rules:** only add, never change. Do not edit or delete an old entry. If an old result turns out to be wrong, write a new entry that replaces it and link the two. A failed result gets written up in the same detail as a good one.

---

## Machine Details

Write this once. Update it only when something changes. None of the speed numbers in this log mean anything without it.

| Field | Value |
|---|---|
| Machine | `TBD` (CPU, cores, RAM) |
| GPU | `TBD` / none |
| OS | `TBD` |
| Python | `TBD` |
| OpenCV | `TBD` |
| NumPy / SciPy | `TBD` |
| scikit-learn | `TBD` |
| Repo | `TBD` (remote URL) |
| Last change to this table | `YYYY-MM-DD` — reason |

---

## Video List

One row per video, filled in as soon as the data arrives. The `sha256` is what lets us catch a file being quietly swapped.

| video_id | filename | sha256 (first 12) | fps | resolution | length | truth? | truth type | source | notes |
|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | |

---

## Experiment Index

The quick overview table. One row per experiment, updated as each one finishes.

| Exp ID | Date | Method | Runs | Status | Main result | Entry |
|---|---|---|---|---|---|---|
| E01 | | — | | planned | | [#E01](#e01) |
| E02 | | — | | planned | | [#E02](#e02) |
| E03 | | M0 | | planned | | [#E03](#e03) |
| E04 | | M0 | | waiting for dataset | | [#E04](#e04) |
| E05 | | M1 | | planned | | [#E05](#e05) |
| E06 | | M1 | | planned | | [#E06](#e06) |
| E07 | | M1 | | planned | | [#E07](#e07) |
| E08 | | M1 | | planned | | [#E08](#e08) |
| E09 | | M1 | | planned | | [#E09](#e09) |
| E10 | | M1 | | planned | | [#E10](#e10) |
| E11 | | M1 | | planned | | [#E11](#e11) |
| E12 | | — | | waiting for G4 | | [#E12](#e12) |
| E13 | | M2 | | waiting for G4 | | [#E13](#e13) |
| E14 | | M2 | | waiting for G4 | | [#E14](#e14) |
| E15 | | all | | planned | | [#E15](#e15) |
| E16 | | all | | planned | | [#E16](#e16) |

Status words to use: `planned` · `waiting` · `running` · `done` · `replaced` · `dropped`.

---

## Entry Template

Copy this block for every experiment. Fill the top half **before** running. Fill the bottom half after.

<details>
<summary>Click to open the template</summary>

```markdown
## E<nn> — <short title>

**Started:** YYYY-MM-DD
**Finished:** YYYY-MM-DD
**Status:** planned | running | done | replaced | dropped
**Method:** M0 | M1 | M2 | none
**Git commit:** `<short sha>` (clean / dirty)
**Config(s):** `configs/…`
**Run IDs:** `runs/2026-…`, `runs/2026-…`
**Data:** fake | faculty | both — video IDs: …

### Question
One sentence. What am I trying to find out?

### Guess (write this before running)
What I think will happen, and why. If I have no idea, say so — that is fine for a
first look, but it has to be written down.

### Pass mark (write this before running)
The exact number or condition that decides if this worked.

### Setup
Only what changed since the last run. Not the whole config.

### Command
```bash
python -m occ.cli … --config … --run-id …
```

### Results
| Video / setting | MCR | BER | NED | sps_hat | time (s) |
|---|---|---|---|---|---|
| | | | | | |

Plots: `runs/<run_id>/figures/…`

### What I saw
What actually happened, including anything surprising. Facts only, no opinions.

### What I think it means
My reading of the results. Kept separate from "what I saw" on purpose — so if my
reading turns out to be wrong later, the facts are still usable.

### What could make this wrong
Reasons this result might be misleading. For example: too few videos, fake data
only, settings tuned on the same data they were tested on, or a large line-up
offset that makes the BER unreliable.

### What I do next
What this changes in the plan. Which experiment comes next, and why.

### Links
Replaces: — | Replaced by: — | Related: —
```

</details>

---

## Example Entry

This shows the level of detail to aim for. The numbers are made up, not real results.

<a id="e03-example"></a>

## E03-EXAMPLE — M0 fixed threshold on clean fake video

**Started:** 2026-09-15
**Finished:** 2026-09-15
**Status:** done
**Method:** M0
**Git commit:** `a1b2c3d` (clean)
**Config(s):** `configs/m0_fixed_threshold.yaml`
**Run IDs:** `runs/2026-09-15T10-04-11_a1b2c3d` … (12 runs)
**Data:** fake — `syn_sps8_n0_d0`, `syn_sps4_n0_d0`, `syn_sps3p7_n0_d0`, × 4 noise levels

### Question
Does the simple fixed-threshold method decode correctly in ideal conditions, and where does it first break?

### Guess
Almost perfect when `sps` is a whole number and there is no noise. It should break badly at `sps = 3.7`, because the assumed bit boundaries slowly slide out of place as the clip goes on.

### Pass mark
BER below 0.01 at `sps = 8, σ = 0`. If it fails there, the problem is our code, not the method.

### Setup
First M0 run against the E01 generator. ROI hard-coded to the known light position. No cleaning. `sps` taken from the generator settings instead of being estimated.

### Command
```bash
python -m occ.cli sweep --config configs/m0_fixed_threshold.yaml \
  --video-set synthetic --grid sps,noise
```

### Results
| Setting | MCR | BER | NED | time (s) |
|---|---|---|---|---|
| sps=8, σ=0 | 1.00 | 0.000 | 0.00 | 4.1 |
| sps=8, σ=10 | 1.00 | 0.004 | 0.00 | 4.2 |
| sps=4, σ=0 | 1.00 | 0.000 | 0.00 | 4.0 |
| sps=3.7, σ=0 | 0.00 | 0.31 | 0.62 | 4.1 |

### What I saw
Clean whole-number `sps` cases decode exactly. At `sps = 3.7`, the first 40 bits or so are right and everything after that gets worse and worse. The BER-against-bit-number curve rises steadily instead of jumping suddenly.

### What I think it means
Our code is fine, and the failure is the one we expected. The steady rise (rather than a sudden jump) suggests the error builds up slowly from phase drift. That supports spending M1's effort on phase estimation, since a per-bit phase correction should get most of the lost tail back.

### What could make this wrong
Fake data only, fixed ROI, no light drift, no compression. None of this tells us anything about the real videos yet. Also, the 0.31 BER at `sps = 3.7` was measured on two streams of the same length. If real drift adds or drops bits, the same failure would show up as a different number.

### What I do next
Gate G2 passed. Move on to E05 (turning M1's parts on one by one), starting with the phase search. Do not touch the ML branch until E05 is finished.

### Links
Replaces: — | Replaced by: — | Related: E01, E05

---

## Weekly Summary

One short block per week, written from the finished entries above. This is what feeds the weekly slides. **No number should go on a slide unless it appears in a log entry first.**

### Week N — YYYY-MM-DD to YYYY-MM-DD

- **Experiments finished:**
- **Main numbers:**
- **What I understand better now:**
- **What is blocking me, and who can unblock it:**
- **What I commit to next week:**

---

## Questions for Faculty

Kept here so the questions build up in one place between meetings, instead of being remembered at the last minute.

| # | Question | Asked on | Answer | Affects |
|---|---|---|---|---|
| 1 | What is the camera frame rate and the transmitter symbol rate? Same for all videos or different? | | | M0 `sps`, M1 search range |
| 2 | How many videos come with the true bits or the true message? | | | All BER results, Gate G4 |
| 3 | Does the light stay still in the frame, or does it move? | | | Tracking in M1, E06 |
| 4 | Is there any packet structure on top of the raw bits (preamble, parity, line coding)? | | | `decode/framing.py`, message decoding |
| 5 | Rolling shutter or global shutter? Do the frames show stripes? | | | Whether we can decode inside a single frame at all |
| 6 | If an ML classifier is expected, what level are the labels — per bit, per frame, or per message? | | | Gate G4, E12, E13 |
| 7 | What codec is used, and was the video re-encoded after recording? | | | E11 compression sweep |
