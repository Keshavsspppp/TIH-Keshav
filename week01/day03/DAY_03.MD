# 1. Refined Research Question

**"How accurately and robustly can a fully offline, software-only pipeline recover a transmitted OOK binary message from unsynchronized camera video of a blinking light source, comparing classical signal-processing decoding against a lightweight ML-assisted symbol classifier, across variation in ROI selection, ambient/exposure conditions, and symbol-timing assumptions?"**

## Measurable Outputs

- **Decoded-message correctness** — % of test videos where the reconstructed message exactly matches ground truth.
- **Bit error rate (BER)** — computed wherever reference bitstreams are available.
- **Synchronization robustness** — how far symbol-timing/ROI/threshold parameters can drift before decoding fails (a tolerance range, not a single number).
- **Execution time** — per-video runtime, baseline vs. signal-processing vs. ML-assisted.
- **Sensitivity curves** — accuracy/BER plotted against ROI size/position, smoothing window, threshold choice, and timing offset, across the full video set.

---

> **Note (2026-09-10, audit):**
> - Slide 2 of `Keshav_Day03_PPT.pdf` says "Reviewed 10 closely related methods/systems and built a comparison table". Ten papers were reviewed; the comparison table (`../day02/methods.png`) holds six systems. See the note in `DAY_02.MD` §2.
> - The Day 03 task asked for mentor decisions to be recorded. No mentor notes exist in this folder; the four blockers on slide 3 were carried forward unchanged into `DAY_04.MD` §4, which is the only record of what was left open.
> - Two of the measurable outputs above (message correctness, BER) later turned out to be unmeasurable: no ground truth was supplied with the dataset (`../day07/DAY_07_FINDINGS.MD` §5.1).