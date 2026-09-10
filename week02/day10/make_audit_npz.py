"""Rebuild audit_<video>.npz for Day10_EDA.ipynb section 5.

Audit note (2026-09-10): the original Day 08 audit code that produced these files
is not in the repository. This script recreates the two arrays the notebook reads,
with the definition stated here so the numbers are checkable:

  amb     one value per frame: mean of all pixels NOT brighter than 180
  on_lvl  one value per LIT frame (more than 20 pixels above 180): mean of those
          bright pixels, i.e. the lamp's "on" level

Run from a folder holding data/raw/*.mp4 (the four supplied videos).
"""
import cv2, numpy as np
from pathlib import Path
for p in sorted(Path('data/raw').glob('*.mp4')):
    cap = cv2.VideoCapture(str(p)); amb, on = [], []
    while True:
        ok, f = cap.read()
        if not ok: break
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY); b = g > 180
        amb.append(float(g[~b].mean()) if b.sum() < g.size else float(g.mean()))
        if b.sum() > 20: on.append(float(g[b].mean()))
    cap.release()
    np.savez(f'audit_{p.stem}.npz', amb=np.array(amb, np.float32), on_lvl=np.array(on, np.float32))
    h = len(on) // 2
    print(f"{p.stem:14s} frames {len(amb):6d} lit {len(on):6d}  on-level first half {np.mean(on[:h]):6.1f} | second {np.mean(on[h:]):6.1f}")
