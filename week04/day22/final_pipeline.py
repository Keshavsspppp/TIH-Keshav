#!/usr/bin/env python3
"""Day 22 - the FROZEN final pipeline: raw video -> decoded bits, one command.

    python final_pipeline.py --raw ../../data/raw --out final_outputs

Stages (each timed, each deterministic):
  1 frame extraction   read every frame once, brightest pixel per frame (trim)
  2 ROI selection      behaviour clustering, one box per lamp, seeded k-means   (Day 09/11)
  3 signal extraction  mean of the brightest 25% of pixels in each box, per frame (Day 10/11)
  4 preprocessing      none - detrend/normalise/smooth OFF, measured harmful     (Day 12)
  5 synchronisation    period = 260/92 frames (ASSUMED, from the filename);
                       phase = 0 by convention (it cannot be estimated, Day 15)  (Days 13-16)
  6 symbol decision    fixed threshold (10/90 percentile midpoint), NEAREST-FRAME
                       sampling rule (Day 19 selection), 12-phase ensemble for the
                       per-bit 'safe' mask                                         (Days 16, 19)
  7 decoded output     bits, safe mask, per-lamp text files, summary JSON
  8 evaluation         internal-consistency indicators only (no ground truth)

Everything is read from FINAL_CONFIG.json next to this file. Nothing is tuned here.
After Day 22 this file and FINAL_CONFIG.json are frozen; any later change must be
documented in CHANGES_AFTER_FREEZE.MD and re-validated.

Reuses the committed Day 11 pipeline functions and the Day 17 shared library, so the
signal it extracts is byte-identical to Signal V1 and the bits are the Day 21 bits.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "week02" / "day11"))
sys.path.insert(0, str(ROOT / "week03" / "day17"))
from occ_pipeline import scan_frame_maxima, trim_bounds, sample_frames, find_lamps, aggregate, clean, sha256_file  # noqa: E402
from occlib import decode, phase_ensemble, fixed_thr, adaptive_thr, agreement  # noqa: E402

CFG = json.loads((HERE / "FINAL_CONFIG.json").read_text())


def sha(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def run_video(video, out_root):
    t = {}; t0 = time.perf_counter()
    pre = CFG["preprocessing"]
    maxima = scan_frame_maxima(video); t["1_frame_extraction_s"] = time.perf_counter() - t0
    a, b = trim_bounds(maxima, pre)
    t1 = time.perf_counter()
    stack = sample_frames(video, a, b, pre["roi"]["sample_frames"])
    lamps, _ = find_lamps(stack, pre); t["2_roi_selection_s"] = time.perf_counter() - t1
    if not lamps:
        raise RuntimeError(f"{video.stem}: no lamp found")
    t2 = time.perf_counter()
    raw = aggregate(video, lamps, a, b, pre); t["3_signal_extraction_s"] = time.perf_counter() - t2
    t3 = time.perf_counter()
    sigs = [clean(s, pre)[0] for s in raw]; t["4_preprocessing_s"] = time.perf_counter() - t3

    dec = CFG["decoder"]; T = CFG["synchronisation"]["fps"] / CFG["synchronisation"]["bits_per_second"]
    out_dir = Path(out_root) / video.stem; out_dir.mkdir(parents=True, exist_ok=True)
    per_lamp = []; t4 = time.perf_counter()
    for L, s in zip(lamps, sigs):
        thr = fixed_thr(s, *dec["threshold_percentiles"]) if dec["threshold"] == "fixed" else adaptive_thr(s)
        bits, margin = decode(s, thr, T, CFG["synchronisation"]["phase_convention"], dec["sampling_rule"], dec["end_margin"])
        M, b0, safe = phase_ensemble(s, thr, T, dec["n_phases"], dec["sampling_rule"], dec["end_margin"])
        n = min(len(bits), len(safe)); bits, safe = bits[:n], safe[:n]
        (out_dir / f"lamp{L['id']}_bits.txt").write_text("".join(map(str, bits.tolist())) + "\n")
        (out_dir / f"lamp{L['id']}_safe_bits.txt").write_text("".join("01"[int(v)] if sf else "?" for v, sf in zip(bits, safe)) + "\n")
        np.save(out_dir / f"lamp{L['id']}_signal.npy", s)
        # evaluation: indicators only
        span = float(np.ptp(s)); stab = np.mean([agreement(b0, decode(s, thr, T, (d * T) % T, dec["sampling_rule"], dec["end_margin"])[0]) for d in (-0.15, 0.15)])
        tt = np.mean([agreement(b0, decode(s, thr + d * span, T, 0.0, dec["sampling_rule"], dec["end_margin"])[0]) for d in (-0.10, 0.10)])
        per_lamp.append({"lamp": L["id"], "box": L["box"], "n_samples": int(len(s)), "signal_sha256": sha(s),
                         "n_bits": int(n), "bits_sha256": sha(bits), "safe_pct": round(float(safe.mean() * 100), 2),
                         "phase_stability_pct": round(float(stab * 100), 2), "threshold_tolerance_pct": round(float(tt * 100), 2),
                         "ones_pct": round(float(bits.mean() * 100), 2), "flip_pct": round(float(np.mean(np.diff(bits) != 0) * 100), 2),
                         "median_margin_pct_of_range": round(float(np.median(margin[:n]) / span * 100), 2)})
    t["5_6_sync_and_decision_s"] = time.perf_counter() - t4
    t["end_to_end_s"] = time.perf_counter() - t0
    summary = {"video": video.stem, "video_sha256": sha256_file(video), "frames_total": int(len(maxima)),
               "trim": {"start_frame": int(a), "end_frame": int(b), "kept_frames": int(b - a + 1)},
               "lamps_found": len(lamps), "per_lamp": per_lamp, "timing_s": {k: round(v, 3) for k, v in t.items()},
               "config_sha256": hashlib.sha256((HERE / "FINAL_CONFIG.json").read_bytes()).hexdigest(),
               "note": CFG["evaluation"]["note"]}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--raw", default=str(ROOT / "data" / "raw")); ap.add_argument("--out", default=str(HERE / "final_outputs"))
    a = ap.parse_args()
    videos = sorted(Path(a.raw).glob("*.mp4")); assert videos, f"no videos in {a.raw}"
    all_s = []
    for v in videos:
        s = run_video(v, a.out); all_s.append(s)
        print(f"{s['video']:14s} {s['lamps_found']} lamp(s)  {s['trim']['kept_frames']:6d} frames  "
              + "  ".join(f"L{p['lamp']}: {p['n_bits']} bits, safe {p['safe_pct']:.1f}%" for p in s["per_lamp"])
              + f"  | {s['timing_s']['end_to_end_s']:.1f} s")
    (Path(a.out) / "index.json").write_text(json.dumps(all_s, indent=2))
    print(f"wrote {Path(a.out) / 'index.json'}")


if __name__ == "__main__":
    main()
