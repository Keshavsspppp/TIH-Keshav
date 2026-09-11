#!/usr/bin/env python3
"""Day 15 - draw the threshold and the decoded decisions over the signal.

Added 2026-09-11: the Day 15 task asked for the threshold and decoded
decisions to be visualised over the signal; fig_decode.png showed the phase
sweep, the agreement bars and the autocorrelation instead. This draws, for a
150-frame stretch of each lamp: the brightness, the fixed and adaptive
thresholds, the assumed bit windows at the decoder's own phase, the frame each
window's decision was taken from, and the decided bit. Uses decoder.py as it
stood on Day 15 (own-phase estimate, most-confident-frame rule).

Output: fig_decisions.png
"""
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from decoder import FPS, adaptive_threshold, best_phase, fixed_threshold

SV1 = HERE.parent.parent / "week02" / "day12" / "signal_v1"
T = FPS / 92.0
START, N = 1000, 150          # frames shown (well inside the transmission)


def main():
    man = json.loads((SV1 / "SIGNAL_V1_MANIFEST.json").read_text())
    entries = man["signals"]
    fig, axes = plt.subplots(len(entries), 1, figsize=(14, 2.1 * len(entries)), sharex=True)
    for ax, e in zip(axes, entries):
        s = np.load(SV1 / e["file"])
        tf, ta = fixed_threshold(s), adaptive_threshold(s)
        ph, _ = best_phase(s, tf, T)
        seg = np.arange(START, START + N)
        ax.plot(seg, s[seg], "-o", ms=2.5, lw=.9, color="#37474f", label="brightness")
        ax.plot(seg, tf[seg], "--", lw=1, color="#c62828", label="fixed threshold")
        ax.plot(seg, ta[seg], ":", lw=1.2, color="#ef6c00", label="adaptive threshold")
        k0 = int(np.ceil((START - ph) / T)); k1 = int((START + N - ph) // T)
        for k in range(k0, k1 + 1):
            a = ph + k * T
            idx = np.arange(int(np.ceil(a)), min(int(np.floor(a + T)) + 1, len(s)))
            if len(idx) == 0: continue
            d = s[idx] - tf[idx]; j = idx[int(np.argmax(np.abs(d)))]; bit = int(d[int(np.argmax(np.abs(d)))] > 0)
            ax.axvline(a, color="#2C6E49", alpha=.35, lw=.8)
            ax.plot([j], [s[j]], "s", ms=6, mfc="none", mec="#1f5fa8", mew=1.4)
            ax.text(a + T / 2, 262, str(bit), ha="center", va="bottom", fontsize=7, color="#1f5fa8")
        ax.set_ylim(-15, 290); ax.set_ylabel(e["video"].replace("_92bps", "") + f" L{e['lamp']}", fontsize=8)
        ax.text(0.005, 0.85, f"phase {ph:.2f} fr (own estimate - see DAY_15 s3)", transform=ax.transAxes, fontsize=7)
        ax.grid(alpha=.25); ax.tick_params(labelsize=7)
    axes[0].legend(fontsize=7, ncol=3, loc="lower right")
    axes[0].set_title("Day 15 decoder over the signal: green = assumed bit windows (92 bps), square = frame the decision was taken from, digit = decided bit", fontsize=9)
    axes[-1].set_xlabel("frame (Signal V1 sample index)")
    fig.tight_layout(); fig.savefig(HERE / "fig_decisions.png", dpi=110); print("wrote fig_decisions.png")


if __name__ == "__main__":
    main()
