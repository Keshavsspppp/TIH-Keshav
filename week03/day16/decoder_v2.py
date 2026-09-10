#!/usr/bin/env python3
"""
Improved OOK decoder (v2).

What changed since v1, and why.

v1 estimated the bit phase by maximising confidence. Day 15 showed that score is
completely flat across the phase - it scored 123.5 at every phase tested while a
third of the bits changed. So v1's phase was set by floating-point noise, and it
reported full confidence whichever phase it landed on.

v2 stops pretending. Three changes:

  1. The phase convention is fixed and stated (phase = 0), not "estimated".
  2. It decodes at many phases and reports, per bit, whether the answer depends
     on the phase. About 44% of bits do not, and those are usable now.
  3. Local normalisation is available and measured, not assumed.

The output is therefore a bit sequence AND a mask saying which bits are safe.
Ignoring the mask puts you back where v1 was.

Still true: no ground truth exists for these videos. Nothing here measures
correctness.
"""

import argparse
import json
from pathlib import Path

import numpy as np

FPS = 260.0
DEFAULTS = {
    "bits_per_second": 92.0,
    "phase_convention": 0.0,          # fixed, not estimated - see module docstring
    "n_phases": 12,                   # how many phases the ensemble uses
    "threshold": "fixed",             # fixed | adaptive
    "adaptive_window_frames": 2600,
    "hysteresis": 0.0,
    "local_normalise": False,         # measured, off by default
    "local_normalise_window": 261,
}


# ----------------------------------------------------------------------

def fixed_threshold(s):
    return np.full(len(s), (np.percentile(s, 10) + np.percentile(s, 90)) / 2.0, np.float32)


def adaptive_threshold(s, window_frames=2600):
    w = int(min(window_frames, max(51, len(s) // 4)))
    step = max(1, w // 8)
    idx = np.arange(0, len(s), step)
    pad = np.pad(s, (w // 2, w // 2), mode="edge")
    lo = np.interp(np.arange(len(s)), idx, [np.percentile(pad[i:i + w], 10) for i in idx])
    hi = np.interp(np.arange(len(s)), idx, [np.percentile(pad[i:i + w], 90) for i in idx])
    return ((lo + hi) / 2.0).astype(np.float32)


def local_normalise(s, window):
    """Rescale each stretch to a common range. Off by default: Day 12 measured
    that it lowers the on/off separation on this dataset rather than raising it."""
    w = int(window) | 1
    pad = np.pad(s, (w // 2, w // 2), mode="edge")
    step = max(1, w // 8)
    idx = np.arange(0, len(s), step)
    lo = np.interp(np.arange(len(s)), idx, [np.percentile(pad[i:i + w], 5) for i in idx])
    hi = np.interp(np.arange(len(s)), idx, [np.percentile(pad[i:i + w], 95) for i in idx])
    rng = np.maximum(hi - lo, 1e-6)
    return ((s - lo) / rng * 255.0).astype(np.float32)


# ----------------------------------------------------------------------

def decode_one_phase(s, thr, period, phase, hysteresis=0.0):
    """Within each bit, take the frame furthest from the threshold."""
    n_bits = int((len(s) - phase - 1) // period)
    bits = np.empty(n_bits, np.int8)
    margin = np.empty(n_bits, np.float32)
    span = float(np.ptp(s))
    state = 1 if s[0] > thr[0] else 0
    for k in range(n_bits):
        a = phase + k * period
        idx = np.arange(int(np.ceil(a)), min(int(np.floor(a + period)) + 1, len(s)))
        idx = idx[(idx >= 0) & (idx < len(s))]
        if len(idx) == 0:
            idx = np.array([min(len(s) - 1, int(round(a + period / 2)))])
        d = s[idx] - thr[idx]
        j = int(np.argmax(np.abs(d)))
        m = float(d[j])
        if hysteresis > 0:
            band = hysteresis * span
            if state == 0 and m > band:
                state = 1
            elif state == 1 and m < -band:
                state = 0
            bits[k] = state
        else:
            bits[k] = 1 if m > 0 else 0
        margin[k] = abs(m)
    return bits, margin


def decode(s, cfg):
    """
    Returns bits, a per-bit 'safe' mask, and diagnostics.

    'safe' means the bit is the same at every phase tried, so the unknown phase
    does not change it.
    """
    period = FPS / cfg["bits_per_second"]
    sig = local_normalise(s, cfg["local_normalise_window"]) if cfg["local_normalise"] else s
    thr = (adaptive_threshold(sig, cfg["adaptive_window_frames"])
           if cfg["threshold"] == "adaptive" else fixed_threshold(sig))

    stack = []
    for ph in np.linspace(0, period, cfg["n_phases"], endpoint=False):
        b, _ = decode_one_phase(sig, thr, period, ph, cfg["hysteresis"])
        stack.append(b)
    n = min(len(b) for b in stack)
    M = np.stack([b[:n] for b in stack])
    votes = M.mean(axis=0)
    safe = (votes == 0) | (votes == 1)

    bits, margin = decode_one_phase(sig, thr, period, cfg["phase_convention"], cfg["hysteresis"])
    bits, margin = bits[:n], margin[:n]
    span = float(np.ptp(sig))

    diag = {
        "n_bits": int(n),
        "safe_bits_pct": round(float(safe.mean() * 100), 2),
        "ones_pct": round(float(bits.mean() * 100), 2),
        "ones_pct_safe_only": round(float(bits[safe].mean() * 100), 2) if safe.any() else None,
        "flip_rate_pct": round(float(np.mean(np.diff(bits) != 0) * 100), 2),
        "median_margin_pct": round(float(np.median(margin) / span * 100), 2),
        "agreement_across_phases_pct": round(float(np.mean(M == (votes > 0.5)) * 100), 2),
    }
    return bits, safe, diag


# ----------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--signals", default="signal_v1")
    ap.add_argument("--out", default="bits_v2")
    ap.add_argument("--threshold", choices=["fixed", "adaptive"], default="fixed")
    ap.add_argument("--local-normalise", action="store_true")
    ap.add_argument("--rate", type=float, default=92.0)
    a = ap.parse_args()

    cfg = dict(DEFAULTS)
    cfg.update(bits_per_second=a.rate, threshold=a.threshold,
               local_normalise=a.local_normalise)

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    report = {"config": cfg, "signals": {}}

    for mp in sorted(Path(a.signals).glob("*/meta.json")):
        m = json.load(open(mp))
        for sig in m["signals"]:
            s = np.load(mp.parent / sig["file"])
            bits, safe, diag = decode(s, cfg)
            key = f"{m['video']['id']}_lamp{sig['lamp']}"
            np.save(out / f"{key}_bits.npy", bits)
            np.save(out / f"{key}_safe.npy", safe)
            report["signals"][key] = diag
            print(f"{key:26s} {diag['n_bits']:6d} bits   "
                  f"safe {diag['safe_bits_pct']:5.1f}%   "
                  f"ones {diag['ones_pct']:5.1f}%   flips {diag['flip_rate_pct']:5.1f}%")

    json.dump(report, open(out / "report.json", "w"), indent=2)
    print(f"\nwrote {out/'report.json'}")
    print("Every bit file has a matching _safe mask. Bits outside it depend on")
    print("the unknown phase and should not be relied on.")


if __name__ == "__main__":
    main()
