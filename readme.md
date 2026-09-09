# TIH-Keshav

**T**oday **I** **L**earned — a day-by-day research log for an **Optical Camera Communication (OCC) video message decoding** project.

Each `dayNN` folder is a snapshot of one day's work: notes, plans, experiment logs, figures, notebooks and scripts, written up as the project actually happened — including dead ends, revised assumptions, and open questions carried forward to the next day.

## Project in one paragraph

A light source ("transmitter") blinks in On-Off Keying (OOK), encoding a binary message. A standard frame-based camera records this blinking as video, but its frame rate is not synchronized to the transmitter's bit clock — so each video only contains an indirect, noisy trace of the original bitstream. The goal is a fully offline, software-only pipeline that takes raw video and reconstructs the transmitted bits and the human-readable message, evaluated on bit error rate (BER), synchronization robustness, and reproducibility — no camera or transmitter hardware involved.

## Repo structure

```
TIH-Keshav/
├── week01/
│   ├── day01/   Problem statement, rewritten from the faculty brief
│   ├── day02/   Domain concepts (CV, OCC/VLC, signal processing, ML) + candidate methods
│   ├── day03/   Method shortlist presentation
│   ├── day04/   Expected dataset schema, splitting strategy, risk assessment (written pre-dataset)
│   ├── day05/   Pipeline design, experiment plan and log templates (still pre-dataset)
│   ├── day06/   Reproducible workflow package (v2 of the Day 05 deliverables)
│   └── day07/   Real dataset arrives — inspection, fingerprinting, first findings
└── week02/
    ├── day08/   Full audit of every frame in every video
    ├── day09/   Automatic ROI (lamp) localization and signal extraction strategy
    ├── day10/   Exploratory data analysis on frame intensity and run lengths
    ├── day11/   End-to-end, config-driven signal extraction pipeline
    ├── day12/   Signal V1 — reviewed, frozen and fingerprinted
    ├── day13/   Symbol/clock synchronization analysis
    └── day14/   Week 2 wrap-up and peer review package
```

Each day folder typically contains a `DAY_NN.MD` write-up plus supporting artifacts (plots, notebooks, scripts, manifests).

## How the project evolved

**Week 1 — framing the problem before seeing any data.** The brief was reverse-engineered into an explicit pipeline (frame extraction → ROI tracking → intensity extraction → preprocessing → symbol sync → thresholding/classification → decoding → evaluation), the relevant CV/OCC/signal-processing/ML background was mapped out, and a full dataset schema, split strategy (grouped by video/session, never by frame, to avoid leakage) and risk register were written down *before* the faculty dataset arrived — so that when it did arrive, inspection was a checklist run against stated expectations rather than an improvised look-around.

**Dataset arrival (Day 07).** Four videos, ~226 MB total, shot at **260 fps** (not the assumed 30–60 fps) with 1–4 LEDs blinking at 92 bps each. Clean two-level signal, static camera, no dropped frames — but no ground truth, and framing/encoding above the raw OOK bits unknown.

**Week 2 — signal extraction and synchronization.** Automatic lamp/ROI localization worked across all four videos; a deterministic, config-driven extraction pipeline produced a reproducible, fingerprinted signal set ("Signal V1," 131,080 samples). Exploratory analysis showed run lengths didn't cleanly match the expected 92 bps, and the initial synchronization pass found no recoverable clock at any tested rate — until shared glitches across lamps in the peer-review stage suggested a common clock might exist after all, an open thread carried into later work.

## Tech stack

- **Python** — OpenCV (`cv2`) for video/frame handling, NumPy for signal processing, Matplotlib for figures, Jupyter notebooks for exploratory analysis
- **Markdown + Mermaid** for write-ups and pipeline diagrams
- Config-driven, reproducibility-first tooling: raw data is hashed and locked read-only (`preserve_raw.sh`), and pipeline runs are versioned via manifest/config files

## Notes

- This is a personal/academic learning log, not a packaged library — there's no single install/run entry point across the whole repo. Each day's scripts and notebooks are self-contained; see the `DAY_NN.MD` in that folder for context on what to run and why.
- Ground truth for the supplied videos is limited, so several days explicitly separate *measured/self-consistency* results from *validated-against-truth* results — this distinction is called out wherever it matters.

## Author

Keshav Prasad ([@Keshavsspppp](https://github.com/Keshavsspppp))