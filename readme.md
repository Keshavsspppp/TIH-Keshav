# TIH-Keshav

**T**oday **I** **L**earned — a day-by-day research log for an **Optical Camera Communication (OCC) video message decoding** project (TIH IIT Guwahati, 4-week online internship, Days 1–28).

Each `dayNN` folder is a snapshot of one day's work: notes, plans, experiment logs, figures, notebooks and scripts, written up as the project actually happened — including dead ends, revised assumptions, and open questions carried forward. Where a later day disproved an earlier one, the earlier file keeps its original text and carries a dated correction note pointing forward; nothing is rewritten after the fact.

## Problem statement

A lamp blinks in on-off keying (on = 1, off = 0). A frame-based camera records it, but the camera's frame rate is not synchronised to the transmitter's bit clock, so each video holds only an indirect, aliased trace of the bitstream — the frame-to-frame brightness of the lamp's region. **Build an offline, software-only pipeline that recovers the transmitted bits and message from such a video**, evaluated on decoded-message correctness, bit error rate where reference truth exists, synchronisation robustness and execution time, with a sensitivity study over ROI choice, smoothing, threshold and symbol timing across the supplied videos. Four videos were supplied; no ground truth, no framing description, and no confirmation of the bit rate beyond the filename.

## Project in one paragraph

A light source ("transmitter") blinks in On-Off Keying (OOK), encoding a binary message. A standard frame-based camera records this blinking as video, but its frame rate is not synchronized to the transmitter's bit clock — so each video only contains an indirect, noisy trace of the original bitstream. The goal is a fully offline, software-only pipeline that takes raw video and reconstructs the transmitted bits and the human-readable message, evaluated on bit error rate (BER), synchronization robustness and reproducibility — no camera or transmitter hardware involved.

## The dataset, in numbers

| | |
|---|---|
| Videos | `1LED_92bps`, `2LEDs_92bps`, `3LEDs_92bps`, `4LEDs_92bps` — 226 MB, in `Videos/` |
| Frame rate / format | 260 fps, steady, no duplicated frames; 640×360, mpeg4 |
| Signal | Near-binary: lamp at 0 or ~245, noise 6–11; camera static (< 1 px drift); ambient light constant to ~0.1 % of contrast |
| Lamps | Carry **different** data, share a clock |
| Bit rate | **92 bps is from the filename — an assumption.** Days 10, 13 and 16 found evidence against it; no other rate fits better |
| Ground truth | **None supplied.** No decoded bit can be checked for correctness |

## Repo structure

```
TIH-Keshav/
├── week01/
│   ├── day01/   PROBLEM_STATEMENT.MD, occ.png — problem restated, pipeline diagram, 10 questions
│   ├── day02/   DAY_02.MD, methods.png — domain concepts, 6-system comparison table, 3-method shortlist
│   ├── day03/   DAY_03.MD, Keshav_Day03_PPT.pdf, MENTOR_NOTES.MD (template) — research question, 3-slide pack
│   ├── day04/   DAY_04.MD — expected dataset schema, split rules, risk checklist (pre-dataset)
│   ├── day05/   DAY_05.MD, EXPERIMENT_PLAN.MD, EXPERIMENT_LOG.MD — pipeline design, plan, log template, folder structure
│   ├── day06/   DAY_06.MD, EXPERIMENT_PLAN_V2.MD, METHODOLOGY_V1.MD (reconstructed), MENTOR_NOTES.MD (template)
│   └── day07/   Dataset arrives — preserve_raw.sh + SHA256SUMS, inspect_dataset.py + reports/, DATASET_MANIFEST.csv,
│                DAY_07_FINDINGS.MD (with the run-length correction)
├── week02/
│   ├── day08/   DAY_08.MD quality table + risk checklist; audit_videos.py reproduces the table (audit_table.json)
│   ├── day09/   Per-lamp ROI by behaviour clustering (roi_extract.py, rois.json); ROI_CANDIDATES.MD (5-criterion
│                comparison); sampling-rule study; frozen preprocessing; 3-slide PDF; MENTOR_NOTES.MD (template)
│   ├── day10/   Day10_EDA.ipynb + its inputs (rois.json, audit_*.npz) — ROI statistics, run lengths vs 92 bps, drift
│   ├── day11/   occ_pipeline.py + configs/preprocess_v1.yaml — deterministic video → per-lamp brightness; make_frames_csv.py
│   ├── day12/   Cleaning ablation; freeze_signal.py; signal_v1/ — the frozen, fingerprinted Signal V1 (+ frames.csv); MENTOR_NOTES.MD
│   ├── day13/   Day13_Synchronisation.ipynb — three clock estimators, candidate_timing.json, hypotheses
│   └── day14/   WEEK2_PACKAGE.MD, SYNC_HYPOTHESES.MD, beat_analysis.py (E8/E9/H5), PEER_REVIEW.MD (template)
├── week03/
│   ├── day15/   decoder.py (fixed / adaptive threshold), decode_report.json, fig_decisions.png — preliminary bits, indicators
│   ├── day16/   decoder_v2.py, report.json — phase as a convention, per-bit "safe" mask (~44 % phase-independent)
│   ├── day17/   occlib.py (shared library, self-checked); ml_decoder.py — logistic-regression symbol classifier, saved models
│   ├── day18/   compare_methods.py, comparison.md — one table over all methods; 3-slide pack; shortlist
│   ├── day19/   tune.py, EXPERIMENT_LOG_DAY19.MD, best_config.json — 51-run grid, selection rule fixed in advance
│   ├── day20/   ablation.py, timing.py — sensitivity to ROI, smoothing, threshold, phase, period; execution time
│   └── day21/   final_eval.py, final_eval.json — TEST opened once; baseline vs tuned; Week-4 direction for approval
└── week04/
    ├── day22/   FROZEN: final_pipeline.py, FINAL_CONFIG.json, FROZEN_MANIFEST.json, final_outputs/, CHANGES_AFTER_FREEZE.MD
    ├── day23/   Day23_Final_Validation.ipynb — performance measurements, TEST re-run, final vs baseline, trade-off
    ├── day24/   Final technical review pack, stage-by-stage workflow, demo.sh (video → evaluation in one script)
    ├── day25/   Day25_Error_Analysis.ipynb — worst windows, failure factors, systematic vs isolated, limitations
    ├── day26/   Package map, figures/, TABLES.MD, RESULTS_SUMMARY.MD, REPORT_DRAFT.MD, OCC_Presentation.pptx
    ├── day27/   Near-final report and presentation, mentor-correction list, frozen results manifest, sign-off record
    └── day28/   Submission checklist (verified), peer mock-presentation record, final report and presentation

OCC_Complete_Analysis.ipynb   The whole project, Days 1–21, in one executed notebook (generated by build_all.py)
build_all.py                  Source of that notebook — edit this, not the .ipynb
EXPLANATION.MD                The whole project explained: what it does, what each week made, how the pipeline works, what was found
AUDIT_CHANGELOG.md            Every audit correction and regenerated file, dated (2026-09-10/11)
Videos/                       The four supplied videos (git-ignored)
data/raw/                     Locked copy made by preserve_raw.sh (git-ignored; SHA256SUMS is tracked in week01/day07/)
```

Each day folder has a `DAY_NN.MD` write-up (or a notebook) plus its artefacts. Files headed *reconstructed*, *regenerated* or *template* were added during the 2026-09-10/11 audit and say so at the top.

**What is tracked and what is ignored.** Raw video (`Videos/`, `data/`, `*.mp4`) and every regenerable run output (`signals/`, `signal_v1/` at the root, `bits/`, `bits_v2/`, `runs/`, `reports/` at the root, `var_*.npy`, `__pycache__`, `*_exec.ipynb`) are ignored — see the root `.gitignore` and the small per-folder ones in `day07`, `day09`–`day13`, `day15`, `day16`. Everything a reader needs to check a number is tracked: the frozen `week02/day12/signal_v1/` (byte-identical to the pipeline output), every configuration, every report JSON, every figure, and the Day 07 inspection `reports/`.

## How the project evolved

**Week 1 — framing the problem before seeing any data.** The brief was turned into an explicit pipeline (frames → ROI → intensity → preprocessing → symbol sync → decision → decoding → evaluation), the CV/OCC/signal-processing/ML background was mapped, and a dataset schema, split strategy and risk register were written *before* the data arrived — so inspection would be a checklist run against stated expectations. Several of those expectations (30–60 fps, drift to detrend, a by-video split, an ML branch with labels) were later reversed by the data; the Day 4–6 files say where.

**Dataset arrival (Day 7).** Four videos at 260 fps, 1–4 lamps, clean two-level signal, static camera, no dropped frames — but no ground truth, no known framing above the raw bits, and four different setups with no repeats, so no generalisation claim is possible. Day 7 also *believed* the run lengths confirmed 92 bps; Day 10 showed they do the opposite (a fifth of all runs are impossible at that rate), and Day 7 carries the correction.

**Week 2 — signal extraction and synchronisation.** Lamps are found automatically in all four videos by clustering pixels on how they blink. A deterministic pipeline produces Signal V1: ten brightness series, 131,080 samples, fingerprinted and byte-for-byte reproducible from the config. Every cleaning step (detrend, normalise, smooth) was measured and switched off — there is no drift to remove and smoothing deletes real transitions. Then the central negative result: **the level changes fit a 92 bps grid 0.3 % better than randomly chosen times, and no other rate does better.** The symbol clock is not recoverable from these videos. Day 14 found the one lead — glitches shared across lamps that repeat every ~21 frames, consistent with a clock near 91, 124 or 136 bps.

**Week 3 — decoding without a clock, and how far the settings can be wrong.**
- *Days 15–16.* A threshold decoder produces 46,372 preliminary bits at the assumed rate, but its phase estimate is blind — the score used to pick the phase is identical at every phase. Decoder v2 stops estimating, decodes at twelve phases and reports which bits do not depend on it: about 44 % of every stream.
- *Day 17.* The ML classifier (logistic regression) is built with the only labels that exist — synthetic — and separately with the threshold decoder's own safe bits. It beats the threshold where a BER can be measured, is a coin toss on the phase-dependent real bits, and inherits the phase problem. Building the synthetic generator exposed a window bug in the sampling rule (the last frame of a bit can expose inside the next bit).
- *Days 18–19.* One comparison table, four methods, timed; then a 51-run tuning grid with the selection rule fixed in advance. Result: the Day 9 "most confident frame" rule is the *worst* choice at an unknown phase (12 % BER on the model); the "nearest frame to the bit centre" rule Day 9 rejected halves that and is immune to threshold placement. The real-data consistency indicators would have picked the wrong rule — which is why they were excluded from selection.
- *Day 20.* The sensitivity study: the tuned decoder changes under 1 % of its bits for a box half or double the size, a shift of half a box, a 3-frame smoother or a ±30 % threshold move; it decodes correctly across 60 % of possible phases. **The one thing it is sensitive to is the bit period — a 0.2 % rate error is a coin toss over 3,000 bits**, and the rate is not known to within 40 %.
- *Day 21.* TEST (the last 70 % of each signal) opened once; the checkpoint and a Week-4 proposal (fix the clock via the beat or the transmitted bits, then block-wise phase decoding) await mentor approval.

**Standing result.** The pipeline is stable, deterministic, fingerprinted and insensitive to everything it controls; it produces bit streams for all four videos; and it cannot say whether a single bit is correct, because the bit clock could not be recovered and no reference was supplied. Every "confidence", "safe" or "agreement" figure in this repo is an internal-consistency indicator, never a correctness measurement, and is labelled as such.

## Setting up

One Python environment at the repository root serves every day folder — the scripts share the same seven packages and Days 17–21 import each other across folders, so do **not** create per-folder environments. From the repository root:

```bash
python -m venv .venv                # or: conda create -n occ python=3.13
.venv\Scripts\activate              # Windows;  source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
python week03/day17/occlib.py       # self-check: should print "occlib self-check passed"
```

`requirements.txt` pins the versions every committed number was produced with (Python 3.13). The environment folder (`.venv/`, `venv/`, `env/`, conda's `.conda/`) is git-ignored at the root.

## Dataset structure and usage

```
Videos/                          the four supplied videos (git-ignored, 226 MB)
  1LED_92bps.mp4  2LEDs_92bps.mp4  3LEDs_92bps.mp4  4LEDs_92bps.mp4
data/raw/                        locked copy made by preserve_raw.sh (git-ignored); SHA256SUMS tracked in week01/day07/
week02/day12/signal_v1/          the frozen per-lamp brightness series (tracked): <video>/lampN.npy, meta.json, frames.csv
```

Every script reads the videos from `data/raw/` and never writes there. Days 13–28 read the frozen `signal_v1/` and do not need the videos at all. The SHA-256 of every video is in `week01/day07/DATASET_MANIFEST.csv`; `bash week01/day07/preserve_raw.sh --verify data/raw` re-checks them. No labels, ground truth or message content exist anywhere in the repository — none were supplied.

## How to run the pipeline

```bash
bash week04/day24/demo.sh                                   # everything: video -> bits -> evaluation, about 2 minutes
bash week04/day26/example_inference.sh Videos/3LEDs_92bps.mp4   # one video -> decoded bits
python week04/day22/final_pipeline.py --raw data/raw --out my_outputs   # the frozen pipeline directly
```

## Reproducing

```bash
# Week 1-2: video -> Signal V1 (about 6 minutes)
bash week01/day07/preserve_raw.sh Videos           # copies to data/raw, fingerprints, locks; --verify to re-check
python week01/day07/inspect_dataset.py --raw data/raw --out reports/day07
python week02/day08/audit_videos.py --raw data/raw
python week02/day11/occ_pipeline.py --all --raw data/raw --config week02/day11/configs/preprocess_v1.yaml --out signals
python week02/day12/freeze_signal.py --freeze --signals signals --out signal_v1 --config week02/day11/configs/preprocess_v1.yaml
python week02/day12/freeze_signal.py --verify --out signal_v1   # must report every signal matching its fingerprint

# Week 3: decoders and experiments (about 3 minutes, read the committed signal_v1 directly)
python week03/day15/decoder.py --signals week02/day12/signal_v1 --out bits
python week03/day16/decoder_v2.py --signals week02/day12/signal_v1 --out bits_v2
python week03/day17/occlib.py                      # self-check of the shared library
python week03/day17/ml_decoder.py && python week03/day18/compare_methods.py
python week03/day19/tune.py && python week03/day20/ablation.py && python week03/day21/final_eval.py

# Optional: the per-day analysis scripts (Day 09 ROI candidates, Day 14 beat, Day 15 decisions plot, Day 20 timing)
python week02/day09/roi_candidates.py && python week02/day14/beat_analysis.py
python week03/day15/plot_decisions.py && python week03/day20/timing.py
```

Needs Python 3 with OpenCV, NumPy, SciPy, scikit-learn, Matplotlib, PyYAML and Jupyter; `ffprobe` is optional. The pipeline is deterministic: the `signal_v1/` it produces is byte-identical to the frozen copy (value and file SHA-256, checked in a clean run on 2026-09-11), and every report JSON in Weeks 2–3 regenerates identically. The per-day notebooks (`Day10_EDA`, `Day13_Synchronisation`) expect `data/raw/` and, for Day 13, a copy of `signal_v1/` in their own folder. `OCC_Complete_Analysis.ipynb` is the whole project in one file — Days 1–6 as detailed planning notes with what the data later did to each, Days 7–21 as executed code — and must be run from the repository root with `data/raw/` in place (about 10 minutes); `python build_all.py` regenerates it from the day folders.

## Expected outputs

`final_pipeline.py` writes, per video, `<out>/<video>/`:

| File | Content |
|---|---|
| `lampN_bits.txt` | the full provisional bit string at the assumed 92 bps (e.g. 9,855 bits for 1LED) |
| `lampN_safe_bits.txt` | the same string with every phase-dependent bit replaced by `?` — **the only bits that should be quoted**; about 35 % are decided |
| `lampN_signal.npy` | the brightness series (byte-identical to Signal V1) |
| `summary.json` | lamp boxes, trim points, bit counts, fingerprints, consistency indicators, per-stage timings |

The committed run is `week04/day22/final_outputs/` (46,362 bits over ten lamps). Re-running must reproduce it exactly: signals match `SIGNAL_V1_MANIFEST.json` on SHA-256, bits match `final_outputs/*/summary.json`. Expected indicators on the held-out part: phase-independent share ≈ 36 %, threshold tolerance ≈ 99.8 %, baseline–final agreement ≈ 79 %. Synthetic BER (assumed model, real noise): ≈ 5.6 % at an unknown phase, 0.00 % at the true phase.

## Limitations

1. **No real bit can be verified.** No ground truth was supplied; every real-data number is an internal-consistency indicator.
2. **The symbol clock is not recoverable from the videos**, and the 92 bps in the filenames is contradicted by the run lengths. A 0.2 % error in the assumed rate makes the output a coin toss over 3,000 bits.
3. **Two thirds of every output stream depends on the unknown phase** (marked `?`); the decoder is right for about 60 % of possible phases on the model.
4. **No message can be produced** — the framing above the raw bits is unknown (not text, not Manchester).
5. **Four recordings, one per condition.** Consistency across them is shown; generalisation beyond them is not.
6. Mentor and peer decisions were never recorded on any review day; the templates are blank.

Full list with the measurement behind each: `week04/day26/TABLES.MD` T8 and `week04/day25/DAY_25.MD`.

## Tech stack

- **Python** — OpenCV for video and frame handling, NumPy/SciPy for signal processing, scikit-learn for the symbol classifier, Matplotlib for figures, Jupyter for exploration, python-pptx for the presentation
- **Markdown + Mermaid** for write-ups and pipeline diagrams
- Reproducibility first: raw videos are SHA-256 fingerprinted, the signal set is frozen with two fingerprints per file, every run is config-driven and seeded, and every reported number is in a JSON next to the script that produced it

## Notes

- This is a personal/academic learning log, not a packaged library. Each day's scripts are self-contained; the `DAY_NN.MD` in each folder says what to run and why.
- Mentor decisions were not recorded on Days 3, 6, 9, 12, 15, 18 and 21, nor the Day 14 peer review. `MENTOR_NOTES.MD` templates (Days 3, 6, 9, 12) and `PEER_REVIEW.MD` (Day 14) carry the required fields with our side pre-filled and the decision columns blank; Days 15, 18 and 21 have blank "mentor decisions" sections in their write-ups.
- Days 15–16 decoded the full signals; the DEV/TEST split (first 30 % / last 70 % of each signal) was instituted on Day 17 and TEST was opened once, on Day 21.
- `AUDIT_CHANGELOG.md` lists every correction note, every reconstructed or regenerated file, and the clean-run verification, all dated.

## Author

Keshav Prasad ([@Keshavsspppp](https://github.com/Keshavsspppp))
