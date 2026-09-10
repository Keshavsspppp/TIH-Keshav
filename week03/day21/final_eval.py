#!/usr/bin/env python3
"""Day 21 - best-candidate checkpoint. Opens the TEST part (last 70% of every
real signal) for the first time, once, with the configurations frozen on Day 19.

Compared:
  baseline  Day 16 decoder as it stood  : most confident frame, end margin 0
  tuned     Day 19 selection (E19-02)   : nearest frame to the bit centre
  runner-up Day 19 E19-03               : average over the bit window

Real TEST : internal-consistency indicators (no ground truth), agreement
            between decoders, timing.
Synthetic : seeds 50-53 (unused so far), noise 8 and 80, exposure 0.3 -
            BER at true phase and phase 0, phase tolerance.
Examples  : windows where baseline and tuned disagree, shown as frames.

Outputs: final_eval.json, fig_final.png
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "day17"))
from occlib import T92, agreement, ber, bit_windows, decode, fixed_thr, indicators, load_signal_v1, random_bits, split, synth

CFG = json.loads((HERE.parent / "day19" / "best_config.json").read_text())
assert CFG["selected"]["rule"] == "nearest", "best_config.json changed since Day 19"
DECODERS = {"baseline (confident)": dict(rule="confident", end_margin=0.0),
            "tuned (nearest)": dict(rule="nearest", end_margin=0.0),
            "runner-up (average)": dict(rule="average", end_margin=0.0)}


def main():
    S = load_signal_v1()
    TEST = {k: split(s, "test") for k, s in S.items()}
    out = {"opened": "TEST = last 70% of each Signal V1 lamp, first and only opening, 2026-09-10",
           "real_test": {}, "synthetic_test": {}, "examples": {}}

    # ---- real TEST
    bits = {}
    for name, kw in DECODERS.items():
        out["real_test"][name] = {}
        for k, s in TEST.items():
            t0 = time.perf_counter(); ind = indicators(s, T92, fixed_thr, 12, kw["rule"], end_margin=kw["end_margin"])
            ind["time_s"] = round(time.perf_counter() - t0, 3)
            bits.setdefault(name, {})[k] = decode(s, fixed_thr(s), T92, 0.0, kw["rule"], kw["end_margin"])[0]
            out["real_test"][name][k] = ind
        med = {m: round(float(np.median([out["real_test"][name][k][m] for k in TEST])), 2)
               for m in ("safe_pct", "phase_stability_pct", "threshold_tolerance_pct", "median_margin_pct", "ones_pct", "flip_pct")}
        out["real_test"][name]["median"] = med
    agree = {k: round(agreement(bits["baseline (confident)"][k], bits["tuned (nearest)"][k]) * 100, 2) for k in TEST}
    out["real_test"]["agreement_baseline_vs_tuned_pct"] = agree
    out["real_test"]["agreement_baseline_vs_tuned_median"] = round(float(np.median(list(agree.values()))), 2)

    # ---- synthetic TEST
    rng = np.random.default_rng(21)
    for name, kw in DECODERS.items():
        out["synthetic_test"][name] = {}
        for nz in (8, 80):
            e0, et, tol = [], [], []
            for seed in range(50, 54):
                b = random_bits(3000, seed); ph = float(rng.uniform(0, T92))
                x = synth(b, phase=ph, exposure=0.3, noise=nz, seed=seed + 500); thr = fixed_thr(x)
                d = lambda p: decode(x, thr, T92, p, kw["rule"], kw["end_margin"])[0]
                e0.append(ber(d(0.0), b)[0]); et.append(ber(d(ph), b)[0])
                offs = np.arange(-0.5, 0.5001, 0.05)
                ok = np.array([ber(d((ph + o * T92) % T92), b)[0] <= 0.01 for o in offs])
                i = len(offs) // 2; lo = hi = i
                while lo > 0 and ok[lo - 1]: lo -= 1
                while hi < len(offs) - 1 and ok[hi + 1]: hi += 1
                tol.append(offs[hi] - offs[lo] if ok[i] else 0.0)
            out["synthetic_test"][name][f"noise {nz}"] = {
                "ber_phase0_pct": round(float(np.mean(e0)) * 100, 2), "ber_true_phase_pct": round(float(np.mean(et)) * 100, 3),
                "phase_tolerance_bits": round(float(np.mean(tol)), 2)}

    # ---- examples: where baseline and tuned disagree on real TEST (1LED), by context
    k = "1LED_92bps/lamp1"; s = TEST[k]; thr = fixed_thr(s)
    bb, bt = bits["baseline (confident)"][k], bits["tuned (nearest)"][k]; n = min(len(bb), len(bt))
    dis = np.flatnonzero(bb[:n] != bt[:n])
    lo, hi = bit_windows(len(s), T92, 0.0)
    # context: how many frames in the window are 'clean' (far from threshold)?
    span = float(np.ptp(s))
    clean = np.array([np.sum(np.abs(s[lo[i]:hi[i] + 1] - thr[0]) > 0.35 * span) for i in range(n)])
    both_levels = np.array([(np.any(s[lo[i]:hi[i] + 1] > thr[0] + 0.35 * span) and np.any(s[lo[i]:hi[i] + 1] < thr[0] - 0.35 * span)) for i in range(n)])
    out["examples"]["1LED_test"] = {
        "n_bits": int(n), "disagreements": int(len(dis)), "disagree_pct": round(float(len(dis) / n * 100), 2),
        "share_of_disagreements_where_window_holds_both_levels_pct": round(float(both_levels[dis].mean() * 100), 1),
        "share_of_all_windows_holding_both_levels_pct": round(float(both_levels.mean() * 100), 1),
        "windows": []}
    for i in dis[:6]:
        fr = s[max(0, lo[i] - 1):hi[i] + 2]
        out["examples"]["1LED_test"]["windows"].append({
            "bit_index": int(i), "frames": [round(float(v)) for v in fr],
            "window_frames_are": "[one before] + window + [one after]",
            "baseline_bit": int(bb[i]), "tuned_bit": int(bt[i]),
            "centre_sample": round(float(s[int(round(lo[i] - 0.5 + T92 / 2))]))})
    # unusual streams
    out["examples"]["unusual"] = {
        "2LEDs_L1_ones_pct": {nme: out["real_test"][nme]["2LEDs_92bps/lamp1"]["ones_pct"] for nme in DECODERS},
        "3LEDs_L3_contrast": round(float(np.percentile(TEST["3LEDs_92bps/lamp3"], 90) - np.percentile(TEST["3LEDs_92bps/lamp3"], 10))),
        "3LEDs_L3_safe_pct": {nme: out["real_test"][nme]["3LEDs_92bps/lamp3"]["safe_pct"] for nme in DECODERS},
    }
    (HERE / "final_eval.json").write_text(json.dumps(out, indent=2))

    # ---- print + figure
    for name in DECODERS:
        m = out["real_test"][name]["median"]; sy = out["synthetic_test"][name]
        print(f"{name:22s} TEST safe {m['safe_pct']:5.1f}%  stab {m['phase_stability_pct']:5.1f}%  thr-tol {m['threshold_tolerance_pct']:5.1f}%  "
              f"| synth n8 BER@0 {sy['noise 8']['ber_phase0_pct']:5.2f}% @true {sy['noise 8']['ber_true_phase_pct']:.3f}% tol {sy['noise 8']['phase_tolerance_bits']:.2f} "
              f"| n80 BER@0 {sy['noise 80']['ber_phase0_pct']:5.2f}% @true {sy['noise 80']['ber_true_phase_pct']:.2f}%")
    print("baseline vs tuned agreement on TEST (median):", out["real_test"]["agreement_baseline_vs_tuned_median"], "%")
    ex = out["examples"]["1LED_test"]
    print(f"1LED TEST: {ex['disagreements']} of {ex['n_bits']} bits differ ({ex['disagree_pct']}%); "
          f"{ex['share_of_disagreements_where_window_holds_both_levels_pct']}% of them in windows holding both levels "
          f"(such windows are {ex['share_of_all_windows_holding_both_levels_pct']}% of all)")

    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))
    ks = list(TEST); y = np.arange(len(ks)); col = {"baseline (confident)": "#B85042", "tuned (nearest)": "#1f5fa8", "runner-up (average)": "#2C6E49"}
    for j, name in enumerate(DECODERS):
        ax[0].barh(y + (j - 1) * 0.27, [out["real_test"][name][k]["threshold_tolerance_pct"] for k in ks], 0.27, color=col[name], label=name)
    ax[0].set_yticks(y); ax[0].set_yticklabels([k.replace("_92bps", "") for k in ks], fontsize=7); ax[0].invert_yaxis()
    ax[0].set_xlim(60, 101); ax[0].set_xlabel("% bits unchanged under a +/-10% threshold shift (TEST)"); ax[0].set_title("Threshold tolerance on TEST"); ax[0].legend(fontsize=6); ax[0].grid(alpha=.3, axis="x")
    for name in DECODERS:
        ax[1].bar([f"{name.split(' ')[0]}\n@0", f"{name.split(' ')[0]}\n@true"],
                  [out["synthetic_test"][name]["noise 8"]["ber_phase0_pct"], out["synthetic_test"][name]["noise 8"]["ber_true_phase_pct"]], color=col[name])
    ax[1].set_ylabel("BER %"); ax[1].set_title("Synthetic TEST, noise 8: phase 0 vs true phase"); ax[1].grid(alpha=.3, axis="y")
    w = ex["windows"][0] if ex["windows"] else None
    if w:
        fr = w["frames"]; ax[2].plot(range(len(fr)), fr, "o-", color="#37474f")
        ax[2].axhline(thr[0], color="r", ls="--", lw=1, label="threshold")
        ax[2].axvspan(0.5, len(fr) - 1.5, color="#F2A65A", alpha=.25, label="assumed bit window")
        ax[2].set_title(f"1LED TEST bit {w['bit_index']}: baseline={w['baseline_bit']}, tuned={w['tuned_bit']}", fontsize=9)
        ax[2].set_xlabel("frame (window +/- 1)"); ax[2].set_ylabel("brightness"); ax[2].legend(fontsize=7); ax[2].grid(alpha=.3)
    fig.tight_layout(); fig.savefig(HERE / "fig_final.png", dpi=110)
    print("wrote final_eval.json, fig_final.png")


if __name__ == "__main__":
    main()
