#!/usr/bin/env python3
"""Day 11 - frame/timestamp metadata for every Signal V1 sample (added 2026-09-11).

The task asked for frame/timestamp information to be saved with the signal. The
pipeline recorded only the trim start/end frames in meta.json; the per-sample
mapping is arithmetic (video_frame = start_frame + i, t = frame / 260) but was
not written out. This writes ../day12/signal_v1/<video>/frames.csv with columns
sample_index, video_frame_index, time_s_from_video_start, time_s_from_trim_start.
All lamps of a video share the same frames. The fingerprinted .npy files are
not touched. Timestamps assume the measured constant 260 fps (Days 07, 08, 13).
"""
import csv, json
from pathlib import Path
FPS = 260.0
for meta_p in sorted((Path(__file__).resolve().parent.parent / "day12" / "signal_v1").glob("*/meta.json")):
    m = json.load(open(meta_p)); a = m["trim"]["start_frame"]; n = m["trim"]["kept_frames"]
    with open(meta_p.parent / "frames.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["sample_index", "video_frame_index", "time_s_from_video_start", "time_s_from_trim_start"])
        for i in range(n):
            w.writerow([i, a + i, f"{(a + i) / FPS:.6f}", f"{i / FPS:.6f}"])
    print(meta_p.parent.name, n, "rows")
