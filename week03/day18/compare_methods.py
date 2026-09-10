#!/usr/bin/env python3
"""Day 18 - one comparison over every decoding method built so far.

Methods (all at the Day 16 phase-0 convention; Day 15 showed an "estimated"
phase is floating-point noise, so estimating it would only add randomness):

  M0   fixed threshold, most-confident frame, Day 16 window          (Days 15/16)
  M1   adaptive threshold (rolling 10-s midpoint), same rule          (Days 15/16)
  M0+  M0 with the 0.3-frame end margin found on Day 17
  M2   logistic-regression symbol classifier, trained on SYNTHETIC
       signals only (so no real-data leakage), six features           (Day 17)

Metrics, in the brief's four groups:
  decoded-message correctness  - not measurable: no ground truth (all days)
  BER                          - synthetic only (true bits known)
  synchronization robustness   - synthetic: phase tolerance and period tolerance
                                 (width of the band where BER <= 1%);
                                 real DEV: phase-independent share, phase
                                 stability, threshold tolerance (indicators)
  execution time               - seconds per real signal, ms per 1,000 frames

Real data = DEV part (first 30%) of each Signal V1 lamp. TEST untouched.
Outputs: comparison.json, comparison.md
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "day17"))
from occlib import (T92, adaptive_thr, agreement, ber, decode, fixed_thr, load_signal_v1,
                    random_bits, split, synth)
from ml_decoder import features

ML = json.loads((HERE.parent / "day17" / "ml_model_synthetic.json").read_text())
W, B0 = np.array(ML["coef"]), ML["intercept"]


def ml_bits(s, thr, phase):
    z = features(s, thr, T92, phase) @ W + B0
    return (z > 0).astype(np.int8)


METHODS = {
    "M0 fixed threshold":        (fixed_thr,    lambda s, t, ph: decode(s, t, T92, ph)[0]),
    "M1 adaptive threshold":     (adaptive_thr, lambda s, t, ph: decode(s, t, T92, ph)[0]),
    "M0 + end margin 0.3":       (fixed_thr,    lambda s, t, ph: decode(s, t, T92, ph, end_margin=0.3)[0]),
    "M2 ML classifier (synth-trained)": (fixed_thr, ml_bits),
}


def real_stats(s, thr_fn, dec, ref_bits=None):
    t0 = time.perf_counter()
    thr = thr_fn(s)
    stack = [dec(s, thr, ph) for ph in np.linspace(0, T92, 12, endpoint=False)]
    dt = time.perf_counter() - t0
    n = min(len(b) for b in stack); M = np.stack([b[:n] for b in stack]); b0 = M[0]
    votes = M.mean(0); safe = (votes == 0) | (votes == 1)
    span = float(np.ptp(s))
    ps = np.mean([agreement(b0, dec(s, thr, (d * T92) % T92)) for d in (-0.15, 0.15)])
    tt = np.mean([agreement(b0, dec(s, thr + d * span, 0.0)) for d in (-0.10, 0.10)])
    out = {"n_bits": int(n), "safe_pct": round(float(safe.mean() * 100), 2),
           "phase_stability_pct": round(float(ps * 100), 2),
           "threshold_tolerance_pct": round(float(tt * 100), 2),
           "ones_pct": round(float(b0.mean() * 100), 2),
           "time_s": round(dt / 12, 4), "ms_per_1000_frames": round(dt / 12 / len(s) * 1e6, 2)}
    if ref_bits is not None:
        out["agree_with_M0_pct"] = round(agreement(b0, ref_bits) * 100, 2)
    return out, b0


def synth_stats(dec, thr_fn, noise, exposure, seeds=range(20, 24), n_bits=3000):
    rng = np.random.default_rng(18)
    b_true, b_ph0, ph_tol, per_tol = [], [], [], []
    for seed in seeds:
        b = random_bits(n_bits, seed); ph = float(rng.uniform(0, T92))
        x = synth(b, phase=ph, exposure=exposure, noise=noise, seed=seed + 200); thr = thr_fn(x)
        b_true.append(ber(dec(x, thr, ph), b)[0]); b_ph0.append(ber(dec(x, thr, 0.0), b)[0])
        # phase tolerance: contiguous band around the true phase with BER <= 1%
        offs = np.arange(-0.5, 0.5001, 0.05)
        e = np.array([ber(dec(x, thr, (ph + o * T92) % T92), b)[0] for o in offs])
        ok = e <= 0.01; i0 = len(offs) // 2
        lo = i0
        while lo > 0 and ok[lo - 1]: lo -= 1
        hi = i0
        while hi < len(offs) - 1 and ok[hi + 1]: hi += 1
        ph_tol.append((offs[hi] - offs[lo]) if ok[i0] else 0.0)
        # period tolerance: assumed period off by e%, true phase, 500-bit stretch
        pers = np.arange(-0.10, 0.1001, 0.01); e2 = []
        for pe in pers:
            Tt = T92 * (1 + pe)
            d = decode(x[:int(500 * T92)], thr[:int(500 * T92)], Tt, ph)[0] if dec is not ml_bits else \
                (features(x[:int(500 * T92)], thr[:int(500 * T92)], Tt, ph) @ W + B0 > 0).astype(np.int8)
            e2.append(ber(d, b[:len(d)])[0])
        e2 = np.array(e2); ok = e2 <= 0.01; i0 = len(pers) // 2
        lo = i0
        while lo > 0 and ok[lo - 1]: lo -= 1
        hi = i0
        while hi < len(pers) - 1 and ok[hi + 1]: hi += 1
        per_tol.append((pers[hi] - pers[lo]) * 100 if ok[i0] else 0.0)
    return {"ber_true_phase_pct": round(float(np.mean(b_true)) * 100, 3),
            "ber_phase0_pct": round(float(np.mean(b_ph0)) * 100, 2),
            "phase_tolerance_bits": round(float(np.mean(ph_tol)), 2),
            "period_tolerance_pct": round(float(np.mean(per_tol)), 1)}


def main():
    S = load_signal_v1()
    dev = {k: split(s, "dev") for k, s in S.items()}
    result = {"methods": {}}
    ref = {}
    for name, (thr_fn, dec) in METHODS.items():
        per = {}
        for k, s in dev.items():
            st, b0 = real_stats(s, thr_fn, dec, ref.get(k))
            per[k] = st
            if name == "M0 fixed threshold":
                ref[k] = b0
        med = {m: round(float(np.median([per[k][m] for k in per])), 2)
               for m in ("safe_pct", "phase_stability_pct", "threshold_tolerance_pct", "ms_per_1000_frames")}
        med["time_s_all_dev"] = round(float(sum(per[k]["time_s"] for k in per)), 3)
        if name != "M0 fixed threshold":
            med["agree_with_M0_pct"] = round(float(np.median([per[k]["agree_with_M0_pct"] for k in per])), 2)
        syn = {"realistic (noise 8, exposure 0.3)": synth_stats(dec, thr_fn, 8, 0.3),
               "hard (noise 80, exposure 0.3)": synth_stats(dec, thr_fn, 80, 0.3)}
        result["methods"][name] = {"real_dev_median": med, "real_dev_per_lamp": per, "synthetic": syn}
        print(f"{name:34s} safe {med['safe_pct']:5.1f}%  phase-stab {med['phase_stability_pct']:5.1f}%  "
              f"thr-tol {med['threshold_tolerance_pct']:5.1f}%  {med['ms_per_1000_frames']:5.1f} ms/kframe | "
              f"synth BER true {syn['realistic (noise 8, exposure 0.3)']['ber_true_phase_pct']:.3f}% "
              f"ph0 {syn['realistic (noise 8, exposure 0.3)']['ber_phase0_pct']:.1f}%  "
              f"phase-tol {syn['realistic (noise 8, exposure 0.3)']['phase_tolerance_bits']:.2f} bit  "
              f"period-tol {syn['realistic (noise 8, exposure 0.3)']['period_tolerance_pct']:.0f}%")
    result["note"] = ("Decoded-message correctness and real-data BER are not measurable: no ground truth. "
                      "Real-data columns are internal-consistency indicators on the DEV part (first 30%). "
                      "Synthetic columns use the assumed 92 bps model. TEST (last 70%) untouched.")
    (HERE / "comparison.json").write_text(json.dumps(result, indent=2))

    # markdown table
    L = ["| Method | Msg correct | BER (real) | BER synth @true / @phase 0 | Phase tol. (bits) | Period tol. (%) | Safe bits (real) | Phase stab. (real) | Thr. tol. (real) | Agree w/ M0 | ms / 1000 fr |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, r in result["methods"].items():
        m = r["real_dev_median"]; sy = r["synthetic"]["realistic (noise 8, exposure 0.3)"]
        L.append(f"| {name} | n/a | n/a | {sy['ber_true_phase_pct']:.3f} % / {sy['ber_phase0_pct']:.1f} % | "
                 f"{sy['phase_tolerance_bits']:.2f} | {sy['period_tolerance_pct']:.0f} | {m['safe_pct']:.1f} % | "
                 f"{m['phase_stability_pct']:.1f} % | {m['threshold_tolerance_pct']:.1f} % | "
                 f"{m.get('agree_with_M0_pct', 100.0):.1f} % | {m['ms_per_1000_frames']:.1f} |")
    L.append("")
    L.append("Hard synthetic case (noise 80, exposure 0.3): " + "; ".join(
        f"{n}: BER {r['synthetic']['hard (noise 80, exposure 0.3)']['ber_true_phase_pct']:.2f} % @true, "
        f"{r['synthetic']['hard (noise 80, exposure 0.3)']['ber_phase0_pct']:.1f} % @phase 0"
        for n, r in result["methods"].items()))
    (HERE / "comparison.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\nwrote comparison.json, comparison.md")


if __name__ == "__main__":
    main()
