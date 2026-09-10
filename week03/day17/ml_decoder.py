#!/usr/bin/env python3
"""Day 17 - ML-assisted symbol decision (M2 from the Day 05 plan).

What a "symbol classifier" can and cannot be given on this project:

  * No ground truth was supplied, so there are NO labels for the real videos.
    (Day 05 s2 said M2 "runs only if we have labels"; Gate G4 failed on Day 07.)
  * The task rule "do not use confidential final-message content as labels"
    is therefore moot - we have no message content at all.

So the classifier is trained and scored two ways, and the two are never mixed:

  A. SYNTHETIC, true labels. Signals from occlib.synth (the *assumed* 92 bps
     model with the measured contrast/noise), bits known. This is the only place
     a BER exists. Threshold baseline and classifier are compared at the true
     phase (decision quality alone) and at the phase-0 convention (the realistic
     case, where both inherit the unrecoverable phase - Days 13, 15, 16).

  B. REAL, pseudo-labels. Labels are the Day 16 phase-independent ("safe")
     threshold decisions on the DEV part (first 30%) of each lamp; the model is
     trained leave-one-lamp-out and scored on the held-out lamp's DEV part.
     Day 05 s2 warned that this makes M2 "copy M1, not compete with it". It
     does. The score is AGREEMENT with the threshold decoder, not correctness.
     The TEST part (last 70%) is not touched.

Feature per bit window (phase-0 convention unless stated): the five frames at
lo-1 .. lo+3 as (value - threshold) / range, plus the fractional position of
the window start inside a frame. Model: logistic regression (sklearn). The plan
said "logistic regression, then RBF SVM, then a small CNN; stop at the first
one that beats M1" - see the report for whether anything did.

Outputs: ml_model.json (weights + feature definition), ml_report.json, fig_ml.png
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).resolve().parent))
from occlib import (T92, ber, decode, fixed_thr, load_signal_v1, phase_ensemble,
                    random_bits, split, synth, bit_windows)

HERE = Path(__file__).resolve().parent
END_MARGIN = 0.0            # Day 16 rule as-is; Day 19 tunes this


def features(s, thr, T=T92, phase=0.0, end_margin=END_MARGIN):
    n = len(s)
    lo, hi = bit_windows(n, T, phase, end_margin)
    span = float(np.ptp(s))
    d = (s - thr) / span
    cols = [d[np.clip(lo + j, 0, n - 1)] for j in range(-1, 4)]
    frac = (phase + np.arange(len(lo)) * T) % 1.0
    return np.column_stack(cols + [frac]).astype(np.float32)


def fit(X, y, C=1.0):
    return LogisticRegression(C=C, max_iter=2000).fit(X, y)


def predict(model, X):
    p = model.predict_proba(X)[:, 1]
    return (p > 0.5).astype(np.int8), p


# ----------------------------------------------------------------------
# A. synthetic, true labels
# ----------------------------------------------------------------------

def synthetic_experiment(noises=(8, 40, 80, 110), exposures=(0.3, 1.0), n_bits=3000,
                         train_seeds=range(4), test_seeds=range(10, 14)):
    rng = np.random.default_rng(17)
    X, Y = [], []
    for seed in train_seeds:
        for nz in noises:
            for ex in exposures:
                b = random_bits(n_bits, seed); ph = float(rng.uniform(0, T92))
                x = synth(b, phase=ph, exposure=ex, noise=nz, seed=seed)
                X.append(features(x, fixed_thr(x), phase=ph)); Y.append(b[:len(X[-1])])
    X = np.vstack(X); Y = np.concatenate(Y)
    t0 = time.perf_counter(); model = fit(X, Y); t_train = time.perf_counter() - t0

    rows = []
    for nz in noises:
        for ex in exposures:
            r = {"noise": nz, "exposure": ex}
            for cond, use_true in (("true_phase", True), ("phase0", False)):
                bt, bm, bt3 = [], [], []
                for seed in test_seeds:
                    b = random_bits(n_bits, seed); ph = float(rng.uniform(0, T92))
                    x = synth(b, phase=ph, exposure=ex, noise=nz, seed=seed + 100)
                    thr = fixed_thr(x); use_ph = ph if use_true else 0.0
                    d, _ = decode(x, thr, T92, use_ph, end_margin=END_MARGIN)
                    d3, _ = decode(x, thr, T92, use_ph, end_margin=0.3)   # window fix, see occlib
                    m, _ = predict(model, features(x, thr, phase=use_ph))
                    bt.append(ber(d, b)[0]); bm.append(ber(m, b)[0]); bt3.append(ber(d3, b)[0])
                r[f"ber_threshold_{cond}"] = round(float(np.mean(bt)) * 100, 3)
                r[f"ber_threshold_margin03_{cond}"] = round(float(np.mean(bt3)) * 100, 3)
                r[f"ber_ml_{cond}"] = round(float(np.mean(bm)) * 100, 3)
            rows.append(r)
    return model, rows, {"n_train_bits": int(len(Y)), "train_time_s": round(t_train, 3)}


# ----------------------------------------------------------------------
# B. real, pseudo-labels (agreement, not correctness)
# ----------------------------------------------------------------------

def real_experiment(S):
    dev = {k: split(s, "dev") for k, s in S.items()}
    feats, labels, safes, tbits = {}, {}, {}, {}
    for k, s in dev.items():
        thr = fixed_thr(s)
        M, b0, safe = phase_ensemble(s, thr, T92, 12, end_margin=END_MARGIN)
        F = features(s, thr)[:len(b0)]
        feats[k], labels[k], safes[k], tbits[k] = F, b0, safe, b0
    rows = {}
    t_pred = 0.0
    for k in dev:                                   # leave-one-lamp-out
        Xtr = np.vstack([feats[j][safes[j]] for j in dev if j != k])
        ytr = np.concatenate([labels[j][safes[j]] for j in dev if j != k])
        model = fit(Xtr, ytr)
        t0 = time.perf_counter(); pred, p = predict(model, feats[k]); t_pred += time.perf_counter() - t0
        safe = safes[k]; tb = tbits[k]
        conf = np.abs(p - 0.5) * 2
        rows[k] = {
            "n_bits_dev": int(len(tb)),
            "agree_threshold_safe_bits_pct": round(float(np.mean(pred[safe] == tb[safe]) * 100), 2),
            "agree_threshold_unsafe_bits_pct": round(float(np.mean(pred[~safe] == tb[~safe]) * 100), 2),
            "ml_confident_pct": round(float(np.mean(conf > 0.9) * 100), 2),
            "ml_confident_and_unsafe_pct": round(float(np.mean((conf > 0.9) & ~safe) * 100), 2),
            "ones_pct_ml": round(float(pred.mean() * 100), 2),
            "ones_pct_threshold": round(float(tb.mean() * 100), 2),
        }
    # final model on all DEV safe bits - the saved candidate
    Xall = np.vstack([feats[j][safes[j]] for j in dev]); yall = np.concatenate([labels[j][safes[j]] for j in dev])
    final = fit(Xall, yall)
    return rows, final, {"n_train_bits": int(len(yall)), "predict_time_s_total": round(t_pred, 4)}


def main():
    S = load_signal_v1()
    model_syn, syn_rows, syn_meta = synthetic_experiment()
    real_rows, model_real, real_meta = real_experiment(S)

    report = {
        "note": ("No ground truth exists for the real videos. Section A (synthetic) is the only BER. "
                 "Section B scores AGREEMENT with the threshold decoder on pseudo-labels, never correctness."),
        "features": "d[lo-1..lo+3] = (value - threshold)/range at the five frames from one before the "
                    "window start, plus frac(window start); phase-0 convention; end_margin=%g" % END_MARGIN,
        "model": "sklearn LogisticRegression(C=1.0)",
        "A_synthetic": {"meta": syn_meta, "rows": syn_rows},
        "B_real_pseudo_labels": {"meta": real_meta, "rows": real_rows},
    }
    (HERE / "ml_report.json").write_text(json.dumps(report, indent=2))
    for name, m in (("synthetic", model_syn), ("real_pseudo", model_real)):
        (HERE / f"ml_model_{name}.json").write_text(json.dumps({
            "features": report["features"], "model": report["model"],
            "coef": m.coef_[0].round(6).tolist(), "intercept": round(float(m.intercept_[0]), 6),
            "trained_on": name}, indent=2))

    print("A. synthetic (BER %, mean of 4 test streams)")
    print(f"{'noise':>6s} {'expo':>5s} | {'thr@true':>9s} {'thr+m.3':>8s} {'ml@true':>8s} | {'thr@ph0':>8s} {'thr+m.3':>8s} {'ml@ph0':>7s}")
    for r in syn_rows:
        print(f"{r['noise']:6d} {r['exposure']:5.1f} | {r['ber_threshold_true_phase']:9.3f} "
              f"{r['ber_threshold_margin03_true_phase']:8.3f} {r['ber_ml_true_phase']:8.3f} | "
              f"{r['ber_threshold_phase0']:8.2f} {r['ber_threshold_margin03_phase0']:8.2f} {r['ber_ml_phase0']:7.2f}")
    print("\nB. real DEV, pseudo-labels, leave-one-lamp-out (agreement with threshold, NOT correctness)")
    for k, r in real_rows.items():
        print(f"  {k:22s} safe-bits agree {r['agree_threshold_safe_bits_pct']:6.2f}%  "
              f"unsafe-bits agree {r['agree_threshold_unsafe_bits_pct']:6.2f}%  "
              f"ML confident {r['ml_confident_pct']:5.1f}%")

    # figure
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    for ex, ls in ((0.3, "-"), (1.0, "--")):
        rr = [r for r in syn_rows if r["exposure"] == ex]
        nz = [r["noise"] for r in rr]
        ax[0].plot(nz, [r["ber_threshold_true_phase"] for r in rr], "o" + ls, color="#1f5fa8", label=f"threshold, true phase, exp {ex}")
        ax[0].plot(nz, [r["ber_ml_true_phase"] for r in rr], "s" + ls, color="#2C6E49", label=f"ML, true phase, exp {ex}")
        ax[0].plot(nz, [r["ber_threshold_phase0"] for r in rr], "o:", color="#B85042", alpha=.7, label=f"threshold, phase 0, exp {ex}")
        ax[0].plot(nz, [r["ber_ml_phase0"] for r in rr], "s:", color="#F2A65A", alpha=.9, label=f"ML, phase 0, exp {ex}")
    ax[0].set_xlabel("noise (grey levels; real data is 6-11)"); ax[0].set_ylabel("BER %")
    ax[0].set_title("A. Synthetic: the phase, not the decision, is the error"); ax[0].legend(fontsize=6); ax[0].grid(alpha=.3)
    ks = list(real_rows); y = np.arange(len(ks))
    ax[1].barh(y - 0.2, [real_rows[k]["agree_threshold_safe_bits_pct"] for k in ks], 0.4, label="on phase-independent bits")
    ax[1].barh(y + 0.2, [real_rows[k]["agree_threshold_unsafe_bits_pct"] for k in ks], 0.4, label="on phase-dependent bits")
    ax[1].set_yticks(y); ax[1].set_yticklabels([k.replace("_92bps", "") for k in ks], fontsize=7); ax[1].invert_yaxis()
    ax[1].set_xlabel("% agreement with threshold decoder (NOT correctness)"); ax[1].set_xlim(50, 100)
    ax[1].set_title("B. Real DEV: ML trained on the threshold's own safe bits"); ax[1].legend(fontsize=7); ax[1].grid(alpha=.3, axis="x")
    fig.tight_layout(); fig.savefig(HERE / "fig_ml.png", dpi=110)
    print(f"\nwrote ml_report.json, ml_model_*.json, fig_ml.png")


if __name__ == "__main__":
    main()
