#!/usr/bin/env python3
"""
OCC preprocessing pipeline — raw video to per-lamp brightness signal.

Runs stages 1 to 5 of the pipeline:
    read frames -> trim -> find lamps -> aggregate brightness -> optional cleaning

It does NOT decode. Bits come later. This step only produces the signal.

Usage
-----
    python occ_pipeline.py --video data/raw/1LED_92bps.mp4 \
                           --config configs/preprocess_v1.yaml \
                           --out signals/

    python occ_pipeline.py --all --config configs/preprocess_v1.yaml --out signals/

What it writes, per video, into <out>/<video_id>/ :
    lamp1.npy ...    one float32 brightness value per frame, per lamp
    meta.json        the resolved settings, the lamp boxes, timings, and a
                     fingerprint of every file, so a later run can be compared

Determinism
-----------
Same video + same config = byte-identical .npy files, every time. The one random
step is the k-means used to group pixels, so its seed is fixed and recorded. Run
with --verify to prove it: the pipeline runs twice and compares fingerprints.

Nothing in the raw folder is ever written to.
"""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import yaml

PIPELINE_VERSION = "1.0.0"


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------

def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def sha256_array(a):
    """Fingerprint of the numbers themselves, so two runs can be compared."""
    return hashlib.sha256(np.ascontiguousarray(a, dtype=np.float32).tobytes()).hexdigest()


def git_commit():
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10)
        if out.returncode:
            return None
        sha = out.stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"],
                               capture_output=True, text=True, timeout=10).stdout.strip()
        return sha + ("-dirty" if dirty else "")
    except Exception:
        return None


# ----------------------------------------------------------------------
# stage 1 — read the video
# ----------------------------------------------------------------------

def scan_frame_maxima(path):
    """One cheap pass: the brightest pixel in each frame. Used for trimming."""
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open {path}")
    m = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        m.append(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).max())
    cap.release()
    if not m:
        raise RuntimeError(f"no frames in {path}")
    return np.array(m, dtype=np.uint8)


# ----------------------------------------------------------------------
# stage 2 — trim the dark lead-in and lead-out
# ----------------------------------------------------------------------

def trim_bounds(maxima, cfg):
    """
    Start where the lamp is lit for a decent share of a whole window, NOT at the
    first bright frame. One of the supplied videos has a single flash followed by
    3.4 seconds of darkness; trimming on the first bright frame would feed that
    silence to the decoder.
    """
    fps = cfg["video"]["fps"]
    w = max(1, int(fps * cfg["trim"]["window_s"]))
    need = cfg["trim"]["min_lit_share"]
    lit = (maxima > cfg["trim"]["lit_level"]).astype(np.float32)
    if len(lit) < w:
        return 0, len(lit) - 1
    run = np.convolve(lit, np.ones(w, dtype=np.float32) / w, mode="valid")
    ok = np.flatnonzero(run >= need)
    if len(ok) == 0:
        return 0, len(lit) - 1
    # ok[0] is the START of the first window holding enough activity, which can
    # sit up to a full window BEFORE the transmission itself. Step forward to the
    # first lit frame inside that window, or we keep ~1 second of dead signal.
    win_start = int(ok[0])
    lit_idx = np.flatnonzero(lit[win_start:win_start + w])
    start = win_start + int(lit_idx[0]) if len(lit_idx) else win_start

    rev = np.convolve(lit[::-1], np.ones(w, dtype=np.float32) / w, mode="valid")
    ok_r = np.flatnonzero(rev >= need)
    if len(ok_r) == 0:
        return start, len(lit) - 1
    win_end = len(lit) - 1 - int(ok_r[0])
    lo = max(start, win_end - w + 1)
    lit_idx = np.flatnonzero(lit[lo:win_end + 1])
    end = lo + int(lit_idx[-1]) if len(lit_idx) else win_end
    return start, end


# ----------------------------------------------------------------------
# stage 3 — find one region per lamp
# ----------------------------------------------------------------------

def sample_frames(path, a, b, n):
    """Frames spread across the WHOLE active part.

    Not the first n frames: if the message opens with a long run of one bit, the
    opening frames show no change and the lamp search finds nothing.
    """
    stride = max(1, (b - a) // n)
    cap = cv2.VideoCapture(str(path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, a)
    frames, i = [], a
    while i <= b and len(frames) < n:
        ok, f = cap.read()
        if not ok:
            break
        if (i - a) % stride == 0:
            frames.append(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY))
        i += 1
    cap.release()
    return np.stack(frames)


def find_lamps(stack, cfg):
    """
    Group the changing pixels by how their brightness behaves over time.

    Pixels of one lamp blink together; pixels of different lamps do not. That is
    what separates two lamps sitting side by side, which no shape-based rule can
    do once their bright areas touch.
    """
    c = cfg["roi"]
    cv2.setRNGSeed(int(cfg["random_seed"]))       # k-means is the only random step

    f = stack.astype(np.float32)
    var = f.var(axis=0)
    thr = max(float(c["min_variance"]), c["variance_share"] * float(var.max()))
    ys, xs = np.nonzero(var >= thr)
    if len(ys) < c["min_pixels"]:
        return [], var

    sig = f[:, ys, xs].T
    sig = (sig - sig.mean(1, keepdims=True)) / (sig.std(1, keepdims=True) + 1e-6)
    sig = np.ascontiguousarray(sig, dtype=np.float32)

    chosen = None
    for k in range(1, c["max_lamps"] + 1):
        crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
                c["kmeans_iters"], 0.1)
        _, lab, cen = cv2.kmeans(sig, k, None, crit, c["kmeans_attempts"],
                                 cv2.KMEANS_PP_CENTERS)
        lab = lab.ravel()
        if np.bincount(lab, minlength=k).min() < c["min_pixels"]:
            continue
        if k == 1:
            sep = 0.0
        else:
            cc = np.corrcoef(cen)
            sep = 1.0 - float(cc[np.triu_indices(k, 1)].max())
        # keep the largest k whose groups still behave differently from each
        # other; groups that behave alike are one lamp split in two
        if k == 1 or sep > c["min_separation"]:
            chosen = (k, lab, sep)

    if chosen is None:
        return [], var
    k, lab, sep = chosen

    lamps = []
    for ci in range(k):
        m = lab == ci
        if m.sum() < c["min_pixels"]:
            continue
        py, px = ys[m], xs[m]
        x0, y0 = int(px.min()), int(py.min())
        w, h = int(px.max() - x0 + 1), int(py.max() - y0 + 1)
        lamps.append({"box": [x0, y0, w, h], "n_px": int(m.sum()),
                      "cx": float(px.mean()), "cy": float(py.mean()),
                      "fill": round(float(m.sum()) / (w * h), 3)})
    if not lamps:
        return [], var

    # A lamp is a solid disc: its pixels fill most of its own box. Leftover
    # groups are halo and glare - a few pixels smeared over a large box.
    biggest = max(L["n_px"] for L in lamps)
    lamps = [L for L in lamps
             if L["fill"] >= c["min_fill"] and L["n_px"] >= c["min_share"] * biggest]
    # stable order: top row first, then left to right
    lamps.sort(key=lambda L: (int(L["cy"] // c["row_height"]), L["cx"]))
    for i, L in enumerate(lamps):
        L["id"] = i + 1
        L["separation"] = round(sep, 3)
    return lamps, var


# ----------------------------------------------------------------------
# stage 4 — one brightness number per frame, per lamp
# ----------------------------------------------------------------------

def aggregate(path, lamps, a, b, cfg):
    """
    Read the active frames once and reduce each lamp's box to a single number.

    Default is the mean of the brightest quarter of the pixels. A plain mean over
    the whole box is diluted by dark corner pixels, and a single max is at the
    mercy of one hot pixel.
    """
    stat = cfg["intensity"]["statistic"]
    frac = cfg["intensity"]["bright_fraction"]
    cap = cv2.VideoCapture(str(path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, a)
    series = [[] for _ in lamps]
    n = 0
    while n <= (b - a):
        ok, f = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        for i, L in enumerate(lamps):
            x, y, w, h = L["box"]
            patch = g[y:y + h, x:x + w].reshape(-1)
            if stat == "bright_mean":
                keep = max(1, int(patch.size * frac))
                v = float(np.sort(patch)[-keep:].mean())
            elif stat == "mean":
                v = float(patch.mean())
            elif stat == "max":
                v = float(patch.max())
            elif stat == "percentile":
                v = float(np.percentile(patch, cfg["intensity"]["percentile"]))
            else:
                raise ValueError(f"unknown statistic: {stat}")
            series[i].append(v)
        n += 1
    cap.release()
    return [np.array(s, dtype=np.float32) for s in series]


# ----------------------------------------------------------------------
# stage 5 — optional cleaning
# ----------------------------------------------------------------------

def clean(sig, cfg):
    """
    Detrend, normalise and smooth — all OFF by default, and that is a measured
    decision, not laziness. On this dataset the lamp's on-level moves by at most
    0.13 grey levels across a whole recording, against a contrast of about 245,
    so there is nothing for detrending to remove. Smoothing would blur the very
    edges we need to read.

    The steps stay here behind flags so they can be switched on for data that
    does need them, and so their effect can be measured rather than assumed.
    """
    out = sig.astype(np.float32)
    applied = []
    c = cfg["clean"]

    if c["detrend"]["enabled"]:
        w = int(c["detrend"]["window_frames"])
        if w > 1:
            pad = np.pad(out, (w // 2, w - 1 - w // 2), mode="edge")
            base = np.convolve(pad, np.ones(w, dtype=np.float32) / w, mode="valid")
            out = out - base + float(np.mean(base))
            applied.append(f"detrend(window={w})")

    if c["normalise"]["enabled"]:
        w = int(c["normalise"]["window_frames"])
        if w > 1:
            pad = np.pad(out, (w // 2, w - 1 - w // 2), mode="edge")
            mu = np.convolve(pad, np.ones(w, dtype=np.float32) / w, mode="valid")
            sd = np.sqrt(np.convolve((pad - np.pad(mu, (w // 2, w - 1 - w // 2), mode="edge"))**2,
                                     np.ones(w, dtype=np.float32) / w, mode="valid")) + 1e-6
            out = (out - mu) / sd
            applied.append(f"normalise(window={w})")

    if c["smooth"]["enabled"]:
        w = int(c["smooth"]["window_frames"])
        if w > 1:
            pad = np.pad(out, (w // 2, w - 1 - w // 2), mode="edge")
            out = np.convolve(pad, np.ones(w, dtype=np.float32) / w, mode="valid")
            applied.append(f"smooth(window={w})")

    return out.astype(np.float32), applied


# ----------------------------------------------------------------------
# driver
# ----------------------------------------------------------------------

def process(video, cfg, out_root):
    t0 = time.time()
    video = Path(video)
    vid_id = video.stem
    out_dir = Path(out_root) / vid_id
    out_dir.mkdir(parents=True, exist_ok=True)

    maxima = scan_frame_maxima(video)
    total = len(maxima)
    a, b = trim_bounds(maxima, cfg)

    stack = sample_frames(video, a, b, cfg["roi"]["sample_frames"])
    lamps, _ = find_lamps(stack, cfg)
    if not lamps:
        raise RuntimeError(f"{vid_id}: no lamp found")

    raw = aggregate(video, lamps, a, b, cfg)

    files, applied = [], []
    for L, s in zip(lamps, raw):
        s2, applied = clean(s, cfg)
        p = out_dir / f"lamp{L['id']}.npy"
        np.save(p, s2)
        files.append({"lamp": L["id"], "file": p.name, "n_samples": int(len(s2)),
                      "box": L["box"], "n_pixels": L["n_px"], "fill": L["fill"],
                      "min": float(s2.min()), "max": float(s2.max()),
                      "mean": round(float(s2.mean()), 3),
                      "sha256": sha256_array(s2)})

    meta = {
        "pipeline_version": PIPELINE_VERSION,
        "git_commit": git_commit(),
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "video": {"id": vid_id, "path": str(video), "sha256": sha256_file(video),
                  "total_frames": int(total)},
        "trim": {"start_frame": int(a), "end_frame": int(b),
                 "kept_frames": int(b - a + 1),
                 "dropped_lead_in": int(a), "dropped_lead_out": int(total - b - 1),
                 "kept_seconds": round((b - a + 1) / cfg["video"]["fps"], 2)},
        "lamps_found": len(lamps),
        "cleaning_applied": applied if applied else ["none"],
        "signals": files,
        "config": cfg,
        "environment": {"python": platform.python_version(),
                        "opencv": cv2.__version__, "numpy": np.__version__},
        "runtime_s": round(time.time() - t0, 2),
    }
    with open(out_dir / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    return meta


def main():
    ap = argparse.ArgumentParser(description="OCC preprocessing: video -> brightness signal")
    ap.add_argument("--video", help="one video file")
    ap.add_argument("--all", action="store_true", help="every video in the raw folder")
    ap.add_argument("--raw", default="data/raw", help="raw folder (read-only)")
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", default="signals")
    ap.add_argument("--verify", action="store_true",
                    help="run twice and check the signals come out identical")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config))

    videos = ([Path(args.video)] if args.video
              else sorted(Path(args.raw).glob("*.mp4")))
    if not videos:
        sys.exit("no videos found")

    all_meta = []
    for v in videos:
        m = process(v, cfg, args.out)
        all_meta.append(m)
        print(f"{m['video']['id']:16s} {m['lamps_found']} lamp(s)  "
              f"kept {m['trim']['kept_frames']:6d}/{m['video']['total_frames']:6d} frames  "
              f"({m['trim']['kept_seconds']:6.1f}s)  {m['runtime_s']:5.1f}s")
        for s in m["signals"]:
            print(f"    lamp{s['lamp']}  box {str(s['box']):22s} "
                  f"{s['n_samples']:6d} samples  range {s['min']:5.1f}..{s['max']:5.1f}  "
                  f"{s['sha256'][:12]}")

    if args.verify:
        print("\nsecond run, checking the signals are identical...")
        ok = True
        for v, m0 in zip(videos, all_meta):
            m1 = process(v, cfg, args.out + "_verify")
            for s0, s1 in zip(m0["signals"], m1["signals"]):
                same = s0["sha256"] == s1["sha256"]
                ok &= same
                print(f"    {m0['video']['id']} lamp{s0['lamp']}: "
                      f"{'identical' if same else 'DIFFERENT'}")
        print("\nDETERMINISM CHECK:", "PASSED" if ok else "FAILED")
        if not ok:
            sys.exit(1)

    idx = Path(args.out) / "index.json"
    json.dump([{"video": m["video"]["id"], "lamps": m["lamps_found"],
                "kept_frames": m["trim"]["kept_frames"],
                "signals": [{"lamp": s["lamp"], "sha256": s["sha256"]} for s in m["signals"]]}
               for m in all_meta], open(idx, "w"), indent=2)
    print(f"\nwrote {idx}")


if __name__ == "__main__":
    main()
