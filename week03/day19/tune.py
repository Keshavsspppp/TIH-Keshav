#!/usr/bin/env python3
"""Day 19 - controlled parameter experiments on the two Day 18 shortlisted
candidates.

Search strategy (fixed before running, Day 18 s3):
  * full grid over a small, meaningful set of settings per candidate
  * VALIDATION = synthetic streams with seeds 30-33 (never used on Day 17/18,
    which used 0-3 train, 10-13 / 20-23 test) at noise 8 and 80, exposure 0.3,
    random phase, decoded at the phase-0 convention (the realistic case)
  * PRIMARY selection metric  : mean validation BER at phase 0
  * SECONDARY (tie-break)     : phase tolerance (band with BER <= 1% at true phase)
  * real DEV indicators are logged for every run but NOT used to select -
    they cannot measure correctness (no ground truth)
  * TEST (last 70% of each real signal) is not touched

Candidate A - threshold decoder:
    end_margin   in {0.0, 0.2, 0.3, 0.4, 0.5}   frames trimmed from window end
    percentiles  in {(5,95), (10,90), (25,75)}   threshold = midpoint of these
    rule         in {confident, nearest, average}
Candidate B - logistic classifier (M2):
    C            in {0.1, 1, 10}
    frames       in {5, 7}                       window of frames as features
    (trained on synthetic seeds 0-3 as on Day 17)

Every run is one row in EXPERIMENT_LOG_DAY19.MD and tuning_results.json.
The winner is written to best_config.json.
"""
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "day17"))
from occlib import T92, agreement, ber, bit_windows, decode, load_signal_v1, random_bits, split, synth

VAL_SEEDS, NOISES, EXPO = range(30, 34), (8, 80), 0.3


def thr_of(s, p):
    return np.full(len(s), (np.percentile(s, p[0]) + np.percentile(s, p[1])) / 2, np.float32)


def features_k(s, thr, T, phase, k):
    n = len(s); lo, _ = bit_windows(n, T, phase)
    d = (s - thr) / float(np.ptp(s))
    before = 1 if k == 5 else 2
    cols = [d[np.clip(lo + j, 0, n - 1)] for j in range(-before, k - before)]
    return np.column_stack(cols + [(phase + np.arange(len(lo)) * T) % 1.0]).astype(np.float32)


def train_ml(C, k):
    rng = np.random.default_rng(17); X, Y = [], []
    for seed in range(4):
        for nz in (8, 40, 80, 110):
            for ex in (0.3, 1.0):
                b = random_bits(3000, seed); ph = float(rng.uniform(0, T92))
                x = synth(b, phase=ph, exposure=ex, noise=nz, seed=seed)
                X.append(features_k(x, thr_of(x, (10, 90)), T92, ph, k)); Y.append(b[:len(X[-1])])
    m = LogisticRegression(C=C, max_iter=3000).fit(np.vstack(X), np.concatenate(Y))
    return m.coef_[0], float(m.intercept_[0])


def validate(dec, thr_fn):
    """dec(x, thr, phase) -> bits. Returns primary/secondary metrics."""
    rng = np.random.default_rng(19); b0, bt, tol = [], [], []
    for nz in NOISES:
        for seed in VAL_SEEDS:
            b = random_bits(3000, seed); ph = float(rng.uniform(0, T92))
            x = synth(b, phase=ph, exposure=EXPO, noise=nz, seed=seed + 300); thr = thr_fn(x)
            b0.append(ber(dec(x, thr, 0.0), b)[0]); bt.append(ber(dec(x, thr, ph), b)[0])
            offs = np.arange(-0.5, 0.5001, 0.05)
            ok = np.array([ber(dec(x, thr, (ph + o * T92) % T92), b)[0] <= 0.01 for o in offs])
            i = len(offs) // 2; lo = hi = i
            while lo > 0 and ok[lo - 1]: lo -= 1
            while hi < len(offs) - 1 and ok[hi + 1]: hi += 1
            tol.append(offs[hi] - offs[lo] if ok[i] else 0.0)
    return {"val_ber_phase0_pct": round(float(np.mean(b0)) * 100, 3),
            "val_ber_true_phase_pct": round(float(np.mean(bt)) * 100, 3),
            "val_phase_tolerance_bits": round(float(np.mean(tol)), 3)}


def real_dev(dec, thr_fn, DEV):
    safe, ps = [], []
    for s in DEV.values():
        thr = thr_fn(s)
        stack = [dec(s, thr, ph) for ph in np.linspace(0, T92, 12, endpoint=False)]
        n = min(len(b) for b in stack); M = np.stack([b[:n] for b in stack]); v = M.mean(0)
        safe.append(float(np.mean((v == 0) | (v == 1))))
        ps.append(np.mean([agreement(M[0], dec(s, thr, (d * T92) % T92)) for d in (-0.15, 0.15)]))
    return {"dev_safe_pct": round(float(np.median(safe)) * 100, 2),
            "dev_phase_stability_pct": round(float(np.median(ps)) * 100, 2)}


def main():
    S = load_signal_v1(); DEV = {k: split(s, "dev") for k, s in S.items()}
    rows = []
    # ---- candidate A ----
    for em, p, rule in itertools.product((0.0, 0.2, 0.3, 0.4, 0.5), ((5, 95), (10, 90), (25, 75)),
                                         ("confident", "nearest", "average")):
        dec = lambda x, t, ph, em=em, rule=rule: decode(x, t, T92, ph, rule, em)[0]
        thr_fn = lambda x, p=p: thr_of(x, p)
        t0 = time.perf_counter(); r = validate(dec, thr_fn); r.update(real_dev(dec, thr_fn, DEV))
        r.update(candidate="A threshold", end_margin=em, percentiles=list(p), rule=rule,
                 run_s=round(time.perf_counter() - t0, 2))
        rows.append(r); print(f"A em={em} p={p} {rule:9s}  ber0 {r['val_ber_phase0_pct']:6.3f}  "
                              f"tol {r['val_phase_tolerance_bits']:.2f}  safe {r['dev_safe_pct']:5.1f}")
    # ---- candidate B ----
    for C, k in itertools.product((0.1, 1.0, 10.0), (5, 7)):
        w, b0 = train_ml(C, k)
        dec = lambda x, t, ph, w=w, b0=b0, k=k: (features_k(x, t, T92, ph, k) @ w + b0 > 0).astype(np.int8)
        thr_fn = lambda x: thr_of(x, (10, 90))
        t0 = time.perf_counter(); r = validate(dec, thr_fn); r.update(real_dev(dec, thr_fn, DEV))
        r.update(candidate="B ML", C=C, frames=k, coef=[round(float(v), 6) for v in w], intercept=round(b0, 6),
                 run_s=round(time.perf_counter() - t0, 2))
        rows.append(r); print(f"B C={C} k={k}  ber0 {r['val_ber_phase0_pct']:6.3f}  "
                              f"tol {r['val_phase_tolerance_bits']:.2f}  safe {r['dev_safe_pct']:5.1f}")

    for i, r in enumerate(rows): r["run_id"] = f"E19-{i+1:02d}"
    order = sorted(rows, key=lambda r: (r["val_ber_phase0_pct"], -r["val_phase_tolerance_bits"]))
    best = order[0]
    bestA = next(r for r in order if r["candidate"].startswith("A"))
    bestB = next(r for r in order if r["candidate"].startswith("B"))
    (HERE / "tuning_results.json").write_text(json.dumps({"selection_rule": __doc__.split("Search strategy")[1].split("Candidate A")[0].strip(),
                                                          "runs": rows}, indent=2))
    (HERE / "best_config.json").write_text(json.dumps({
        "selected": best, "best_threshold": bestA, "best_ml": bestB,
        "note": "Selected on synthetic validation BER at phase 0, tie-break phase tolerance. "
                "Real DEV indicators were logged, not used. TEST untouched. No ground truth: "
                "'best' means best on the assumed model."}, indent=2))

    L = ["# Experiment log — Day 19 tuning", "",
         "Selection rule fixed before running: primary = validation BER at phase 0 (synthetic seeds 30–33, noise 8 and 80, exposure 0.3); secondary = phase tolerance. Real DEV indicators logged, not used for selection. TEST untouched.", "",
         "| Run | Candidate | Settings | Val BER @ phase 0 | Val BER @ true phase | Phase tol. (bits) | DEV safe | DEV phase stab. | s |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        st = (f"end_margin {r['end_margin']}, pct {tuple(r['percentiles'])}, {r['rule']}" if r["candidate"].startswith("A")
              else f"C {r['C']}, {r['frames']} frames")
        mark = " **←**" if r is best else (" *(best B)*" if r is bestB and r is not best else (" *(best A)*" if r is bestA and r is not best else ""))
        L.append(f"| {r['run_id']} | {r['candidate']} | {st}{mark} | {r['val_ber_phase0_pct']:.3f} % | "
                 f"{r['val_ber_true_phase_pct']:.3f} % | {r['val_phase_tolerance_bits']:.2f} | "
                 f"{r['dev_safe_pct']:.1f} % | {r['dev_phase_stability_pct']:.1f} % | {r['run_s']} |")
    (HERE / "EXPERIMENT_LOG_DAY19.MD").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nbest overall: {best['run_id']} {best['candidate']}  ber0 {best['val_ber_phase0_pct']}%")
    print(f"best A: {bestA['run_id']} em={bestA['end_margin']} p={bestA['percentiles']} {bestA['rule']}  ber0 {bestA['val_ber_phase0_pct']}%")
    print(f"best B: {bestB['run_id']} C={bestB['C']} k={bestB['frames']}  ber0 {bestB['val_ber_phase0_pct']}%")


if __name__ == "__main__":
    main()
