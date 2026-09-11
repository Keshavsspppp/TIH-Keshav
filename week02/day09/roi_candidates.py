#!/usr/bin/env python3
"""Day 09 - compare candidate transmitter ROIs on the five criteria the task
names: signal visibility, noise level, stability, transmitter isolation,
sensitivity to ambient-light changes.

Added 2026-09-11: the original Day 09 compared detection METHODS and sampling
RULES; this compares alternative BOXES for each lamp, which is what the task
asked for. Nothing else in Day 09 changes.

Candidates per lamp:
  day07-blob   the Day 07 method: variance map over the whole clip, top 0.5%
               of pixels, biggest connected blob. On multi-lamp videos this
               merges neighbours or picks one lamp - the failure Day 07 s5.4
               reported. One box per VIDEO, scored against every lamp.
  day09-box    the Day 09 behaviour-clustering box (Signal V1 manifest)
  x0.5 / x2    the Day 09 box shrunk / grown about its centre
  shift+0.5    the Day 09 box moved right by half its width

Signal per candidate: mean of the brightest 25% of pixels in the box (as
Signal V1), over the DEV part (first 30%) of the transmission span.

Criteria (all per candidate, per lamp):
  visibility     gap = mean(on) - mean(off), on/off = samples beyond 25% of the
                 range from the mid-level; and gap / noise
  noise          rms of the on- and off-group standard deviations
  stability      |on-level second half - first half|, grey levels
  isolation      correlation with the NEIGHBOURING lamp's Signal V1 series
                 (a box that leaks a neighbour's light scores high; 1LED: n/a)
  ambient sens.  correlation with the frame's background mean (pixels <= 180)

Outputs: roi_candidates.json, ROI_CANDIDATES.MD. One video pass, ~1 min.
"""
import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
RAW = HERE.parent.parent / "data" / "raw"
SV1 = HERE.parent / "day12" / "signal_v1"
DEV_FRAC = 0.30


def day07_blob(path, n_frames=200):
    cap = cv2.VideoCapture(str(path)); total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    stride = max(1, total // n_frames); frames = []; i = 0
    while len(frames) < n_frames:
        ok, f = cap.read()
        if not ok: break
        if i % stride == 0: frames.append(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32))
        i += 1
    cap.release()
    var = np.stack(frames).var(0)
    mask = (var >= np.percentile(var, 99.5)).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, h, _ = stats[big]
    return [int(x), int(y), int(w), int(h)]


def scaled(box, s):
    x, y, w, h = box; cx, cy = x + w / 2, y + h / 2
    ww, hh = max(2, int(round(w * s))), max(2, int(round(h * s)))
    return [int(round(cx - ww / 2)), int(round(cy - hh / 2)), ww, hh]


def extract(path, boxes, a, n, W, H):
    cap = cv2.VideoCapture(str(path)); cap.set(cv2.CAP_PROP_POS_FRAMES, a)
    out = {k: [] for k in boxes}; bg = []
    for _ in range(n):
        ok, f = cap.read()
        if not ok: break
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        b = g > 180; bg.append(float(g[~b].mean()) if b.sum() < g.size else float(g.mean()))
        for k, (x, y, w, h) in boxes.items():
            x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
            p = g[y0:y1, x0:x1].reshape(-1); kk = max(1, p.size // 4)
            out[k].append(float(np.partition(p, p.size - kk)[p.size - kk:].mean()))
    cap.release()
    return {k: np.array(v, np.float32) for k, v in out.items()}, np.array(bg, np.float32)


def criteria(x, neighbour, bg):
    t = (np.percentile(x, 10) + np.percentile(x, 90)) / 2; sp = float(np.ptp(x))
    on, off = x[x > t + .25 * sp], x[x < t - .25 * sp]
    if len(on) < 10 or len(off) < 10:
        return {"gap": round(sp, 1), "noise": None, "gap_over_noise": 0.0, "on_level_drift": None,
                "corr_neighbour": None, "corr_background": round(float(np.corrcoef(x, bg)[0, 1]), 3), "note": "no two-level signal in this box"}
    noise = float(np.sqrt((on.std() ** 2 + off.std() ** 2) / 2)); h = len(on) // 2
    return {"gap": round(float(on.mean() - off.mean()), 1), "noise": round(noise, 2),
            "gap_over_noise": round(float((on.mean() - off.mean()) / max(noise, 1e-9)), 1),
            "on_level_drift": round(float(abs(on[h:].mean() - on[:h].mean())), 2),
            "corr_neighbour": None if neighbour is None else round(float(np.corrcoef(x, neighbour[:len(x)])[0, 1]), 3),
            "corr_background": round(float(np.corrcoef(x, bg)[0, 1]), 3)}


def main():
    man = json.loads((SV1 / "SIGNAL_V1_MANIFEST.json").read_text())
    result = {}
    for vid in sorted({e["video"] for e in man["signals"]}):
        lamps = [e for e in man["signals"] if e["video"] == vid]
        meta = json.loads((SV1 / vid / "meta.json").read_text())
        a, n = meta["trim"]["start_frame"], int(meta["trim"]["kept_frames"] * DEV_FRAC)
        path = RAW / f"{vid}.mp4"; cap = cv2.VideoCapture(str(path))
        W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)); cap.release()
        blob = day07_blob(path)
        boxes = {"day07-blob": blob}
        for L in lamps:
            b = L["box"]; k = f"lamp{L['lamp']}"
            boxes[f"{k}:day09-box"] = b; boxes[f"{k}:x0.5"] = scaled(b, 0.5); boxes[f"{k}:x2"] = scaled(b, 2.0)
            boxes[f"{k}:shift+0.5"] = [b[0] + b[2] // 2, b[1], b[2], b[3]]
        sig, bg = extract(path, boxes, a, n, W, H)
        sv1 = {L["lamp"]: np.load(SV1 / L["file"])[:n] for L in lamps}
        result[vid] = {"dev_frames": n, "day07_blob_box": blob, "lamps": {}}
        for L in lamps:
            lid = L["lamp"]; others = [sv1[o] for o in sv1 if o != lid]
            neigh = others[int(np.argmax([np.corrcoef(sig[f'lamp{lid}:day09-box'], o)[0, 1] for o in others]))] if others else None
            rows = {}
            for cand in ("day07-blob", "day09-box", "x0.5", "x2", "shift+0.5"):
                key = "day07-blob" if cand == "day07-blob" else f"lamp{lid}:{cand}"
                rows[cand] = {"box": boxes[key], **criteria(sig[key], neigh, bg)}
            result[vid]["lamps"][f"lamp{lid}"] = rows
        print(vid, "done; day07 blob box", blob)
    (HERE / "roi_candidates.json").write_text(json.dumps(result, indent=2))

    L = ["# Candidate ROI comparison (Day 09 task, added 2026-09-11)", "",
         "Per lamp, DEV part (first 30 % of the transmission span). Definitions in `roi_candidates.py`. "
         "`day07-blob` is one box per video (the Day 07 method), scored against every lamp of that video.", "",
         "| Video / lamp | Candidate | Box (x,y,w,h) | Visibility: gap | Noise | Gap / noise | Stability: on-level drift | Isolation: corr. with neighbour | Ambient: corr. with background |",
         "|---|---|---|---|---|---|---|---|---|"]
    for vid, r in result.items():
        for lamp, rows in r["lamps"].items():
            for cand, c in rows.items():
                L.append(f"| {vid.replace('_92bps','')} {lamp} | {cand} | {tuple(c['box'])} | {c['gap']} | {c['noise'] if c['noise'] is not None else '—'} | "
                         f"{c['gap_over_noise']} | {c['on_level_drift'] if c['on_level_drift'] is not None else '—'} | "
                         f"{c['corr_neighbour'] if c['corr_neighbour'] is not None else 'n/a'} | {c['corr_background']} |")
    (HERE / "ROI_CANDIDATES.MD").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("wrote roi_candidates.json, ROI_CANDIDATES.MD")


if __name__ == "__main__":
    main()
