#!/usr/bin/env python3
"""Day 20 - execution time per tested condition (added 2026-09-11; the task asks
for execution time to be quantified alongside BER and robustness).

Median wall time over 5 runs, single lamp (1LED DEV part, 8,356 frames), for
each sweep variant of ablation.py. ROI cost is the per-frame aggregation of one
box (brightest-25% mean via np.partition) measured over 500 frames.
Output: timing.json"""
import json, sys, time
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE.parent / "day17"))
from occlib import T92, decode, fixed_thr, load_signal_v1, split
from ablation import smooth, ROI_SCALES, SMOOTH, THR_SHIFT, PERIOD
s = split(load_signal_v1()["1LED_92bps/lamp1"], "dev"); thr = fixed_thr(s)
def med(fn, n=5):
    t = []
    for _ in range(n):
        t0 = time.perf_counter(); fn(); t.append(time.perf_counter() - t0)
    return round(float(np.median(t)) * 1000, 3)
out = {"frames": int(len(s)), "unit": "ms per decode of 8,356 frames (median of 5)", "rules": {}}
for rule in ("confident", "nearest", "average"):
    r = {"decode_default": med(lambda: decode(s, thr, T92, 0.0, rule))}
    r["smoothing"] = {str(w): med(lambda w=w: decode(smooth(s, w), thr, T92, 0.0, rule)) for w in SMOOTH}
    r["threshold_shift"] = {f"{d:+.1f}": med(lambda d=d: decode(s, thr + d * np.ptp(s), T92, 0.0, rule)) for d in THR_SHIFT}
    r["period_error_pct"] = {f"{e:+g}": med(lambda e=e: decode(s, thr, T92 * (1 + e / 100), 0.0, rule)) for e in PERIOD if abs(e) <= 3}
    r["phase_ensemble_12"] = med(lambda: [decode(s, thr, T92, ph, rule) for ph in np.linspace(0, T92, 12, endpoint=False)])
    out["rules"][rule] = r
# ROI aggregation cost per frame vs box scale (synthetic 8-bit patch of the 105x105 1LED box)
rng = np.random.default_rng(0); roi = {}
for sc in ROI_SCALES:
    side = int(105 * sc); p = rng.integers(0, 256, side * side).astype(np.uint8); k = max(1, p.size // 4)
    roi[str(sc)] = {"box_px": side * side, "us_per_frame": round(med(lambda: [np.partition(p, p.size - k)[p.size - k:].mean() for _ in range(500)]) / 500 * 1000, 2)}
out["roi_aggregation"] = roi
(HERE / "timing.json").write_text(json.dumps(out, indent=2))
for rule, r in out["rules"].items():
    print(f"{rule:10s} default {r['decode_default']:.2f} ms | smooth {r['smoothing']} | 12-phase ensemble {r['phase_ensemble_12']:.1f} ms")
print("ROI us/frame by scale:", {k: v['us_per_frame'] for k, v in roi.items()})
