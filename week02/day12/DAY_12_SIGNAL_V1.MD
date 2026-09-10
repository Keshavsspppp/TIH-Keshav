# Day 12 — Signal Pipeline Review and Signal V1 Freeze

**Project:** Optical Camera Communication (OCC) Video Message Decoding
**Purpose:** present the extraction pipeline, defend the cleaning decisions with measurements, and freeze the signal set that every later step will read.

**Deliverables:** `signal_v1/` (the frozen set), `freeze_signal.py` (freeze and verify), `fig_ablation.png` (the evidence), this document.

---

## 1. What Is Being Reviewed

Raw video goes in, one brightness value per frame per lamp comes out.

| Stage | Decision | Where it came from |
|---|---|---|
| Trim | Start on sustained activity, not the first bright frame | Day 08 found a false start in `2LEDs` |
| Find lamps | Group pixels by how they blink, not by shape | Day 09; shape cannot split touching lamps |
| Aggregate | Mean of the brightest 25% of pixels in each box | Day 10 compared eight statistics |
| Detrend | **Off** | §3 |
| Normalise | **Off** | §3 |
| Smooth | **Off** | §3 |

### What came out

| Video | Lamps | Frames kept | Seconds | Samples per lamp |
|---|---|---|---|---|
| 1LED | 1 | 27,856 of 30,058 | 107.1 | 27,856 |
| 2LEDs | 2 | 17,195 of 21,157 | 66.1 | 17,195 |
| 3LEDs | 3 | 11,466 of 13,057 | 44.1 | 11,466 |
| 4LEDs | 4 | 8,609 of 11,033 | 33.1 | 8,609 |

**10 signals, 131,080 samples.** Every one spans about 1 to 253 in brightness, so the on/off gap survives the whole pipeline. Runtime is about 130 seconds for all four videos.

Every lamp was found automatically. The lamp count was never given to the detector.

---

## 2. Defending the Cleaning Choices

The original plan (Day 05) had detrending and rolling normalisation as central parts of the main method. They are now switched off. That is a reversal, so it needs evidence rather than an argument.

**The test:** run every cleaning option over all 10 signals and measure what changes. See `fig_ablation.png`.

| Configuration | gap / noise | Transitions kept | Bits unchanged |
|---|---|---|---|
| **Frozen (all off)** | **58.5** | **100%** | — |
| Smooth, window 3 | 31.9 | 73.1% | 81.4% |
| Smooth, window 5 | 11.4 | 43.3% | 74.5% |
| Detrend, window 261 | 25.1 | 100.0% | 77.9% |
| Detrend, window 29 | 12.7 | 100.1% *(adds a few spurious crossings)* | 75.7% |
| Normalise, window 261 | 24.8 | 100.0% | 77.6% |
| All three together | 21.4 | 73.1% | 78.0% |

> **Note (2026-09-10, audit).** All seven rows reproduce exactly on the regenerated Signal V1. "gap / noise" here is `(mean on − mean off) / rms(std on, std off)` with on/off taken as samples more than 25 % of the range from the mid-level, over all ten signals; it is **not** the Day 10 §2 figure (24–33), which used a ±60 grey-level cut on 4,000 frames of one lamp. `ablation.json` was not committed; the numbers are recomputable from the notebook cell in `../../OCC_Complete_Analysis.ipynb` §6.

Three things stand out.

### Every option halves the separation

The frozen signal separates on from off by 58.5 times its own noise. **Every** cleaning option drops that to between 11 and 32. Not one improves it.

For detrending and normalising the reason is that they are solving a problem this dataset does not have. Subtracting a moving average from a near-square wave adds ripple; dividing by a rolling standard deviation amplifies whatever noise sits in the flat stretches. With no drift to remove, both operations are pure cost.

### Smoothing deletes real level changes

Smoothing with a 3-frame window destroys **27% of the transitions**. With a 5-frame window it destroys **57%**.

These are not noise glitches. Day 10 already proved that: pushing hysteresis out to 35% of the signal range removed none of the short runs. They are real level changes in the data, and smoothing erases them.

The reason is arithmetic. One bit lasts under 3 frames, so a 3-frame smoothing window is wider than a bit. It averages each bit together with its neighbours. The bottom panel of `fig_ablation.png` shows the result: where the raw signal sits cleanly at 0 or 250, the window-5 trace wanders around the threshold.

### One bit in five changes

Every option changes 19% to 26% of the decoded bits. These steps are not harmless defaults that we could leave on for safety. They change the answer.

**Honest limit on all of this.** Without ground truth we cannot say the frozen signal gives the *right* bits. What we can say is that it separates the two levels most cleanly, keeps every transition present in the video, and adds nothing of its own. Every alternative scores worse on all three, so none of them has a case.

### What we are not claiming

Detrending and normalising are not wrong in general. They are wrong **here**, because Day 08 measured the lamp's on-level moving by at most 0.13 grey levels across a whole recording, against a contrast of about 245, and ambient background varying by roughly 0.1% of that contrast.

All three steps stay in the code behind config flags. Turning one on changes the output and is recorded in `meta.json` — we verified that. Their value gets demonstrated on synthetic videos where we control the drift ourselves, and that result will be labelled as synthetic.

---

## 3. Signal V1 — Frozen

```bash
python freeze_signal.py --freeze --signals signals --out signal_v1
python freeze_signal.py --verify --out signal_v1     # before any run that matters
```

| | |
|---|---|
| Version | 1.0 |
| Videos | 4 |
| Signals | 10 |
| Samples | 131,080 |
| Settings | `preprocess_v1.yaml`, copied into the freeze and fingerprinted |
| Protection | Files made read-only; SHA-256 of every file and of the settings |

### What freezing means

Every later step reads `signal_v1/`. The files do not change. If the decoder gives a different answer next month, we need to know it was not because the signal quietly moved underneath it.

Two fingerprints are stored per signal: one of the numbers themselves, and one of the file on disk. The first survives a re-save; the second catches any edit at all.

### Checks run today

| Check | Result |
|---|---|
| Freeze, then verify | 10 of 10 match |
| Settings file unchanged | Confirmed |
| **Deliberate tamper** — changed one sample in one file | **Detected**, named the file, exit code 1 |
| Freeze twice | Refused, so a re-freeze cannot silently overwrite |

The tamper test matters. A verifier that always passes is not a verifier. (The file was restored afterwards, and the freeze re-verified.)

### The honest limit

Read-only stops ordinary accidents. It does not stop an admin user, who can still overwrite the files. The fingerprints are the real protection, which is why `--verify` should run before any run whose numbers get reported.

---

## 4. What We Ask You to Approve

1. **The extraction pipeline** — trim, find lamps by behaviour, aggregate the brightest 25% (§1).
2. **Cleaning off** — detrend, normalise and smooth all disabled for this dataset, on the evidence in §2.
3. **Signal V1 as frozen** — 10 signals, 131,080 samples, fingerprinted, read-only.

Once approved, decoder work runs against `signal_v1/` and never touches a video again.

> **Note (2026-09-10, audit).** No mentor approval or corrections are recorded for this review (the Day 12 task asked for both). `signal_v1/` was not committed originally; it has been regenerated from `../../Videos/` with `../day11/occ_pipeline.py` and `freeze_signal.py` and added to this folder. Every `.npy` is byte-identical to the frozen original (`file_sha256` matches the manifest for all ten). `freeze_signal.py --verify --out signal_v1` reports the settings file as changed, because the reconstructed `preprocess_v1.yaml` cannot match the original file's hash — the signals themselves pass.

---

## 5. What Signal V1 Does Not Settle

Freezing the signal does not settle the format. The blockers from Days 09 and 10 are unchanged:

| # | Question | Why it still blocks |
|---|---|---|
| **Q1** | Can we have the transmitted bits for at least one video? | Without them, no BER, no correctness check, and the ML branch cannot run. We can measure how *confident* a decode is, never whether it is *right* |
| **Q2** | What format sits above the raw bits? | Day 10 found run lengths of 1 and 4 frames making up 22.6% of the data. Both are impossible at 92 bps. Something sits between the bits and the light |
| **Q3** | Is 92 bps the payload rate or the light's switching rate? | Three estimators failed to recover the rate from the video, so it rests entirely on the filename — and the data argues against it |

Signal V1 is deliberately format-neutral. It is brightness against frame number and nothing more, so **whatever the answers turn out to be, the signal does not need re-extracting.** That is the main reason to freeze at this line rather than further along.

---

## 6. Files

| File | What it is |
|---|---|
| `signal_v1/` | The frozen set: signals, per-video meta, manifest, settings copy |
| `signal_v1/SIGNAL_V1_MANIFEST.json` | Every signal with two fingerprints, plus the settings fingerprint |
| `freeze_signal.py` | Freeze and verify. `--verify` before any reported run |
| `occ_pipeline.py` | The pipeline that produced it |
| `preprocess_v1.yaml` | Every setting, with the reason next to it |
| `fig_ablation.png` | The cleaning evidence: separation, transitions kept, and what smoothing does |
| `ablation.json` | The numbers behind that figure |
