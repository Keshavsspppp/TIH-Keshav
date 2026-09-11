#!/usr/bin/env python3
"""Day 08 - video quality audit: one full pass over every frame of every video.

Reproduces the numbers in DAY_08.MD s2 (the code that produced that table was
never committed; this script was written on 2026-09-11 from the definitions
below and checked against the table - see the note under it in DAY_08.MD).

Definitions, so every number is checkable:
  bright pixel        grey value > 180
  lit frame           more than 20 bright pixels
  transmission span   first lit frame .. last lit frame (frames outside = dark lead-in/out)
  lamp size           bright-pixel count per lit frame; median and IQR over the span
  on level            mean of the bright pixels in a lit frame; median and 5-95th
  ambient             mean of the non-bright pixels in a frame; median over the clip
  ambient range       max - min of the per-second means
  camera drift        centre of all bright pixels, averaged in 20 blocks over the
                      lit frames; max - min of the block means (x and y). On the
                      multi-lamp videos this jumps between lamps - not motion
  longest unlit gap   longest run of frames with no lit lamp inside the span

Reads every frame; never writes to the raw folder. ~90 s for the four videos.
Usage: python audit_videos.py --raw ../../data/raw
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

FPS = 260.0


def audit(path):
    cap = cv2.VideoCapture(str(path))
    hdr = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fmax, amb, cx, cy, lit_idx, size, on = [], [], [], [], [], [], []
    prev = None; dup = black = n = 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        if prev is not None and np.array_equal(g, prev):
            dup += 1
        prev = g
        fm = int(g.max()); fmax.append(fm); black += fm < 1
        b = g > 180; nb = int(b.sum())
        amb.append(float(g[~b].mean()) if nb < g.size else float(g.mean()))
        if nb > 20:
            ys, xs = np.nonzero(b)
            cx.append(xs.mean()); cy.append(ys.mean()); lit_idx.append(n); size.append(nb); on.append(float(g[b].mean()))
        n += 1
    cap.release()
    lit_idx = np.array(lit_idx); amb = np.array(amb); size = np.array(size); on = np.array(on)
    first, last = int(lit_idx[0]), int(lit_idx[-1])
    span = last - first + 1
    gaps = np.diff(lit_idx); lg = int(gaps.max() - 1) if len(gaps) else 0
    blk = int(FPS); k = len(amb) // blk; per_s = amb[:k * blk].reshape(k, blk).mean(1)
    cx, cy = np.array(cx), np.array(cy); nb_ = 20; bs = max(1, len(cx) // nb_)
    bx = np.array([cx[i * bs:(i + 1) * bs].mean() for i in range(nb_)]); by = np.array([cy[i * bs:(i + 1) * bs].mean() for i in range(nb_)])
    contrast = float(np.median(on) - np.median(amb))
    return {
        "frames_header": hdr, "frames_read": n, "duplicated_frames": dup, "black_frames": black,
        "length_s": round(n / FPS, 1), "resolution": f"{w}x{h}", "fps_header": FPS,
        "dark_lead_in_frames": first, "dark_lead_out_frames": n - 1 - last,
        "transmission_s": round(span / FPS, 1), "bits_available_at_92bps": int(span / (FPS / 92)),
        "lit_share_of_span_pct": round(len(lit_idx) / span * 100, 1),
        "longest_unlit_gap_frames": lg, "longest_unlit_gap_bits": round(lg / (FPS / 92), 1),
        "longest_gap_starts_at_frame": int(lit_idx[np.argmax(gaps)]) if len(gaps) else None,
        "lamp_size_median_px": int(np.median(size)), "lamp_size_iqr_px": int(np.percentile(size, 75) - np.percentile(size, 25)),
        "on_level_median": round(float(np.median(on)), 1), "on_level_5_95": [round(float(np.percentile(on, 5)), 1), round(float(np.percentile(on, 95)), 1)],
        "ambient_median": round(float(np.median(amb)), 2), "ambient_range_per_second": round(float(per_s.max() - per_s.min()), 2),
        "contrast": round(contrast, 1), "ambient_range_pct_of_contrast": round(float(per_s.max() - per_s.min()) / contrast * 100, 2),
        "drift_x_px": round(float(bx.max() - bx.min()), 2), "drift_y_px": round(float(by.max() - by.min()), 2),
    }


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--raw", default="../../data/raw"); a = ap.parse_args()
    here = Path(__file__).resolve().parent
    out = {}
    for p in sorted(Path(a.raw).glob("*.mp4")):
        out[p.stem] = audit(p); r = out[p.stem]
        print(f"{p.stem:14s} {r['frames_read']}/{r['frames_header']} frames, dup {r['duplicated_frames']}, black {r['black_frames']}, "
              f"lead-in {r['dark_lead_in_frames']}, lead-out {r['dark_lead_out_frames']}, lit {r['lit_share_of_span_pct']}% of span, "
              f"gap {r['longest_unlit_gap_frames']} fr, on {r['on_level_median']}, ambient {r['ambient_median']} ±{r['ambient_range_per_second']}, "
              f"drift {r['drift_x_px']}/{r['drift_y_px']} px")
    (here / "audit_table.json").write_text(json.dumps(out, indent=2))
    keys = list(next(iter(out.values())))
    L = ["| | " + " | ".join(out) + " |", "|---|" + "---|" * len(out)]
    for k in keys:
        L.append(f"| {k} | " + " | ".join(str(out[v][k]) for v in out) + " |")
    (here / "audit_table.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("wrote audit_table.json, audit_table.md")


if __name__ == "__main__":
    main()
