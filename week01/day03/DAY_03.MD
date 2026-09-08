# 1. Refined Research Question

**"How accurately and robustly can a fully offline, software-only pipeline recover a transmitted OOK binary message from unsynchronized camera video of a blinking light source, comparing classical signal-processing decoding against a lightweight ML-assisted symbol classifier, across variation in ROI selection, ambient/exposure conditions, and symbol-timing assumptions?"**

## Measurable Outputs

- **Decoded-message correctness** — % of test videos where the reconstructed message exactly matches ground truth.
- **Bit error rate (BER)** — computed wherever reference bitstreams are available.
- **Synchronization robustness** — how far symbol-timing/ROI/threshold parameters can drift before decoding fails (a tolerance range, not a single number).
- **Execution time** — per-video runtime, baseline vs. signal-processing vs. ML-assisted.
- **Sensitivity curves** — accuracy/BER plotted against ROI size/position, smoothing window, threshold choice, and timing offset, across the full video set.