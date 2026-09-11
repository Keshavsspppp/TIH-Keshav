#!/usr/bin/env python3
"""Day 14 - the beat between the bit grid and the frame grid (E8, E9, H5).

Added 2026-09-11: the Day 14 findings (shared 1-frame glitches across lamps,
their ~21-frame repeat, the candidate periods) had no code in this folder -
only in OCC_Complete_Analysis.ipynb s8. This is that analysis as a script,
reading the frozen Signal V1. Numbers reproduce SYNC_HYPOTHESES.MD E8/E9.

  E8  1-frame runs on different lamps of the same video coincide (within +/-1
      frame) 2.3-3.9x more often than chance
  E9  the frames where ALL lamps of a video glitch together repeat with a
      strongest lag near 21 frames (2LEDs, 4LEDs) and 63/84 (3LEDs)
  H5  two grids drifting past each other realign every T/|T - round(T)|
      frames; the candidate periods for a ~20-21 frame beat are listed

Outputs: beat_results.json, fig_beat_check.png
"""
import itertools
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SV1 = HERE.parent / "day12" / "signal_v1"
FPS = 260.0


def load():
    m = json.loads((SV1 / "SIGNAL_V1_MANIFEST.json").read_text())
    return {f"{e['video']}/lamp{e['lamp']}": np.load(SV1 / e["file"]) for e in m["signals"]}


def short_run_starts(sig):
    t = (np.percentile(sig, 10) + np.percentile(sig, 90)) / 2
    e = np.flatnonzero(np.diff((sig > t).astype(np.int8))) + 1
    return e[:-1][np.diff(e) == 1], len(sig)


def main():
    S = load(); out = {"E8_coincidence": {}, "E9_repeat_lags": {}, "H5_candidates": []}
    for vid in ("2LEDs_92bps", "3LEDs_92bps", "4LEDs_92bps"):
        ks = [k for k in S if k.startswith(vid)]
        for a, b in itertools.combinations(ks, 2):
            si, n = short_run_starts(S[a]); sj, _ = short_run_starts(S[b])
            A = np.zeros(n, bool); A[si[si < n]] = True; B = np.zeros(n, bool); B[sj[sj < n]] = True
            aw = A | np.roll(A, 1) | np.roll(A, -1); hit = int((aw & B).sum()); exp = aw.sum() / n * B.sum()
            out["E8_coincidence"][f"{a} vs {b.split('/')[1]}"] = {"coincide": hit, "expected_by_chance": round(float(exp), 1), "ratio": round(hit / exp, 2)}
        n = min(len(S[k]) for k in ks); votes = np.zeros(n)
        for k in ks:
            sh, _ = short_run_starts(S[k]); v = np.zeros(n); v[sh[sh < n]] = 1
            votes += np.convolve(v, np.ones(3), mode="same") > 0
        tr = (votes >= len(ks)).astype(float); x = tr - tr.mean()
        ac = np.correlate(x, x, "full")[n - 1:]; ac /= ac[0]
        pk = sorted([(float(ac[k]), k) for k in range(4, 100) if ac[k] > ac[k - 1] and ac[k] >= ac[k + 1]], reverse=True)[:5]
        out["E9_repeat_lags"][vid] = {"n_all_lamp_glitches": int(tr.sum()), "strongest_lags": [(k, round(v, 3)) for v, k in pk], "ac_1_99": [round(float(v), 4) for v in ac[1:100]]}
    for T in np.arange(1.8, 3.3, 0.005):
        d = abs(T - round(T))
        if d > 1e-6 and 19.5 < T / d < 21.5:
            out["H5_candidates"].append({"period_frames": round(float(T), 3), "bps": round(FPS / T, 2), "beat_frames": round(float(T / d), 1)})
    out["H5_note"] = ("Filename's 2.826 frames would give a 16.2-frame beat. Repeat lags 21/41/61/81 are spaced 20, "
                      "so the beat is nearer 20.2; candidates unchanged within rounding: ~82, ~91, ~124, ~136 bps.")
    (HERE / "beat_results.json").write_text(json.dumps(out, indent=2))
    rs = [v["ratio"] for v in out["E8_coincidence"].values()]
    print(f"E8: coincidence {min(rs):.2f}x .. {max(rs):.2f}x chance over {len(rs)} lamp pairs")
    for vid, r in out["E9_repeat_lags"].items():
        print(f"E9: {vid} strongest lags {[k for k, _ in r['strongest_lags']]}")
    print("H5:", ", ".join(f"{c['period_frames']} fr = {c['bps']} bps" for c in out["H5_candidates"]))

    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 3.2))
    for vid, col in (("2LEDs_92bps", "#1f5fa8"), ("4LEDs_92bps", "#B85042"), ("3LEDs_92bps", "#2C6E49")):
        ax.plot(range(1, 100), out["E9_repeat_lags"][vid]["ac_1_99"], lw=1.1, color=col, label=vid.replace("_92bps", ""))
    for k in (21, 42, 63, 84): ax.axvline(k, color="k", alpha=.25, ls="--", lw=1)
    ax.set(xlabel="lag (frames)", ylabel="repeat strength", title="Shared glitches repeat on a ~20-21 frame beat (dashed: 21, 42, 63, 84)")
    ax.legend(fontsize=8); ax.grid(alpha=.3); fig.tight_layout(); fig.savefig(HERE / "fig_beat_check.png", dpi=110)
    print("wrote beat_results.json, fig_beat_check.png")


if __name__ == "__main__":
    main()
