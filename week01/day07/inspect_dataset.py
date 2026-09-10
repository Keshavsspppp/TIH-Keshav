#!/usr/bin/env python3
"""
Day 07 dataset inspection.

Looks at every video in the raw folder and writes down what it finds.
It NEVER changes the raw files. It only reads them.

Usage:
    python inspect_dataset.py --raw data/raw --out reports/day07
    python inspect_dataset.py --raw data/raw --out reports/day07 --truth data/ground_truth

Outputs, all inside --out:
    MANIFEST.csv            one row per video, the main table
    per_video/<id>.json     every number we measured, for that video
    figures/<id>_*.png      variance map, brightness trace, histogram, frequency
    INSPECTION_REPORT.md    the written report
"""

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

VIDEO_EXT = {".mp4", ".avi", ".mov", ".mkv", ".m4v", ".mpg", ".mpeg", ".webm"}


# ----------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------

def sha256_of_file(path, chunk=1 << 20):
    """Fingerprint of the file. Lets us spot a file being swapped later."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def run_ffprobe(path):
    """Ask ffprobe for the container metadata. Returns {} if ffprobe is missing."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries",
        "stream=codec_name,width,height,r_frame_rate,avg_frame_rate,nb_frames,pix_fmt,duration",
        "-show_entries", "format=duration,size,format_name",
        "-of", "json", str(path),
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if out.returncode != 0:
            return {}
        return json.loads(out.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {}


def parse_rate(text):
    """ffprobe gives rates like '30000/1001'. Turn that into a number."""
    if not text:
        return None
    try:
        if "/" in text:
            a, b = text.split("/")
            b = float(b)
            return float(a) / b if b else None
        return float(text)
    except ValueError:
        return None


def frame_timestamps(path, seconds=10):
    """
    Read the time of each frame for the first few seconds.
    If those times are not evenly spaced, the video has a variable frame rate,
    and we cannot treat the frames as evenly sampled in time.
    """
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-read_intervals", f"%+{seconds}",
        "-show_entries", "frame=best_effort_timestamp_time",
        "-of", "csv=p=0", str(path),
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if out.returncode != 0:
            return []
        times = []
        for line in out.stdout.splitlines():
            line = line.strip().rstrip(",")
            if not line or line == "N/A":
                continue
            try:
                times.append(float(line))
            except ValueError:
                pass
        return times
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def average_hash(gray, size=8):
    """
    A tiny fingerprint of one frame, used to spot near-duplicate videos
    (same clip re-encoded or renamed). Shrink to 8x8, compare to the mean.
    """
    small = cv2.resize(gray, (size, size), interpolation=cv2.INTER_AREA)
    return (small > small.mean()).flatten()


def hamming(a, b):
    return int(np.count_nonzero(a != b))


# ----------------------------------------------------------------------
# reading the video
# ----------------------------------------------------------------------

def scan_video(path, max_frames=None, var_frames=200):
    """
    Read the video once. Collect everything we need in that single pass.

    Returns a dict of measurements, or {'readable': False} if it will not open.
    """
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return {"readable": False}

    header_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    header_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

    # Step size so the variance-map frames are spread across the whole clip.
    total_guess = max_frames or header_frames or 0
    var_stride = max(1, -(-total_guess // var_frames)) if total_guess else 1

    global_mean = []      # average brightness of the whole frame
    frame_max = []        # brightest pixel in the frame
    sat_fraction = []     # share of pixels stuck at 255
    black_frames = 0
    var_stack = []        # a few frames kept for the variance map
    first_hash = None
    mid_hash = None

    counted = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        g = gray.astype(np.float32)

        global_mean.append(float(g.mean()))
        frame_max.append(float(g.max()))
        sat_fraction.append(float((gray >= 255).mean()))
        if g.max() < 1.0:
            black_frames += 1

        if counted == 0:
            first_hash = average_hash(gray)
        # Keep a spread of frames for the variance map, taken from across the
        # WHOLE video, not just the start. If the message opens with a long run
        # of the same bit, the first N frames show no change at all, and a
        # variance map built from them would wrongly say nothing blinks.
        if counted % var_stride == 0 and len(var_stack) < var_frames:
            var_stack.append(cv2.resize(gray, (min(320, gray.shape[1]),
                                               min(240, gray.shape[0])),
                                        interpolation=cv2.INTER_AREA).astype(np.float32))

        counted += 1
        if max_frames and counted >= max_frames:
            break
    cap.release()

    if counted == 0:
        return {"readable": False}

    # middle-frame fingerprint, for near-duplicate checking
    cap = cv2.VideoCapture(str(path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, counted // 2)
    ok, frame = cap.read()
    if ok:
        g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        mid_hash = average_hash(g)
    cap.release()

    # ---- variance map: the blinking light is the thing that changes most ----
    stack = np.stack(var_stack, axis=0)
    var_map = stack.var(axis=0)

    roi_series = None
    roi_box = None
    # How much more does the busiest pixel change than a typical pixel?
    # On a video where nothing blinks, this stays small and the "ROI" we find
    # is just noise. This number is what tells the two cases apart.
    med_var = float(np.median(var_map))
    # floor of 1.0 grey level: a real camera always has some noise, and
    # dividing by a near-zero median would give a meaningless huge number
    roi_variance_ratio = float(var_map.max() / max(med_var, 1.0))
    if var_map.max() > 0:
        # keep only the top of the variance map, then take the biggest blob
        thresh = np.percentile(var_map, 99.5)
        mask = (var_map >= max(thresh, 1e-6)).astype(np.uint8)
        n, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, 8)
        if n > 1:
            biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            x, y, w, h, _ = stats[biggest]
            # scale the box back up to full resolution
            sx = width / stack.shape[2]
            sy = height / stack.shape[1]
            roi_box = [int(x * sx), int(y * sy), max(1, int(w * sx)), max(1, int(h * sy))]
            # brightness inside that box, from the downsized stack
            roi_series = stack[:, y:y + max(1, h), x:x + max(1, w)].mean(axis=(1, 2))

    return {
        "readable": True,
        "header_frames": header_frames,
        "header_fps": header_fps,
        "counted_frames": counted,
        "width": width,
        "height": height,
        "global_mean": np.array(global_mean, dtype=np.float32),
        "frame_max": np.array(frame_max, dtype=np.float32),
        "sat_fraction": np.array(sat_fraction, dtype=np.float32),
        "black_frames": black_frames,
        "var_map": var_map,
        "roi_box": roi_box,
        "roi_variance_ratio": roi_variance_ratio,
        "var_stride": var_stride,
        "roi_series": None if roi_series is None else np.asarray(roi_series, dtype=np.float32),
        "first_hash": first_hash,
        "mid_hash": mid_hash,
        "truncated": bool(max_frames and counted >= max_frames),
    }


# ----------------------------------------------------------------------
# first-look statistics
# ----------------------------------------------------------------------

def bimodality(series):
    """
    Does the brightness split into two clear groups (an 'on' group and an
    'off' group)? We use Otsu's threshold and measure how far apart the two
    groups sit, in units of their own spread. Bigger is cleaner.
    Returns (separation, threshold) or (None, None).
    """
    if series is None or len(series) < 10:
        return None, None
    s = series.astype(np.float64)
    lo, hi = s.min(), s.max()
    if hi - lo < 1e-9:
        return 0.0, None
    # reshape to a column: OpenCV expects a 2-D single-channel image here,
    # and a flat 1-D array makes Otsu return a useless threshold of 0
    scaled = ((s - lo) / (hi - lo) * 255).astype(np.uint8).reshape(-1, 1)
    t, _ = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    thr = lo + (t / 255.0) * (hi - lo)
    low = s[s <= thr]
    high = s[s > thr]
    if len(low) < 2 or len(high) < 2:
        # Otsu gave a lopsided split. Fall back to the plain midpoint.
        thr = (lo + hi) / 2.0
        low, high = s[s <= thr], s[s > thr]
        if len(low) < 2 or len(high) < 2:
            return 0.0, float(thr)
    # floor of half a grey level, for the same reason as above
    spread = max(np.sqrt((low.std() ** 2 + high.std() ** 2) / 2), 0.5)
    return float(abs(high.mean() - low.mean()) / spread), float(thr)


def dominant_frequency(series, fps):
    """
    The strongest repeating rhythm in the brightness, in cycles per second.
    This is a hint at the blink rate. It is only a hint: if the blinking is
    faster than the camera can sample, this number will be an alias and wrong.
    """
    if series is None or len(series) < 16 or not fps:
        return None, None
    s = series.astype(np.float64)
    s = s - s.mean()
    if s.std() < 1e-9:
        return None, None
    win = np.hanning(len(s))
    spec = np.abs(np.fft.rfft(s * win))
    freqs = np.fft.rfftfreq(len(s), d=1.0 / fps)
    spec[0] = 0.0  # ignore the flat part
    k = int(np.argmax(spec))
    peak = float(spec[k])
    rest = float(np.median(spec[spec > 0])) + 1e-12
    return float(freqs[k]), float(peak / rest)


# ----------------------------------------------------------------------
# figures
# ----------------------------------------------------------------------

def make_figures(vid_id, scan, out_dir, fps):
    paths = {}
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    # 1. variance map
    vm = scan["var_map"]
    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(vm, cmap="magma")
    ax.set_title(f"{vid_id} — where the picture changes most")
    ax.axis("off")
    fig.colorbar(im, ax=ax, shrink=0.8)
    p = fig_dir / f"{vid_id}_variance_map.png"
    fig.savefig(p, dpi=110, bbox_inches="tight")
    plt.close(fig)
    paths["variance_map"] = str(p)

    # 2. brightness over time
    series = scan["roi_series"] if scan["roi_series"] is not None else scan["global_mean"]
    label = "ROI brightness" if scan["roi_series"] is not None else "whole-frame brightness"
    fig, ax = plt.subplots(figsize=(9, 3))
    n_show = min(len(series), 600)
    ax.plot(series[:n_show], linewidth=0.9)
    ax.set_title(f"{vid_id} — {label} (first {n_show} frames)")
    ax.set_xlabel("frame")
    ax.set_ylabel("brightness")
    ax.grid(alpha=0.3)
    p = fig_dir / f"{vid_id}_brightness_trace.png"
    fig.savefig(p, dpi=110, bbox_inches="tight")
    plt.close(fig)
    paths["brightness_trace"] = str(p)

    # 3. histogram — two humps would mean a clean on/off split
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.hist(series, bins=50)
    ax.set_title(f"{vid_id} — brightness histogram")
    ax.set_xlabel("brightness")
    ax.set_ylabel("count")
    p = fig_dir / f"{vid_id}_histogram.png"
    fig.savefig(p, dpi=110, bbox_inches="tight")
    plt.close(fig)
    paths["histogram"] = str(p)

    # 4. frequency view
    if fps and len(series) >= 16:
        s = series.astype(np.float64) - series.mean()
        spec = np.abs(np.fft.rfft(s * np.hanning(len(s))))
        freqs = np.fft.rfftfreq(len(s), d=1.0 / fps)
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.plot(freqs[1:], spec[1:], linewidth=0.9)
        ax.set_title(f"{vid_id} — rhythm in the brightness")
        ax.set_xlabel("cycles per second")
        ax.set_ylabel("strength")
        ax.grid(alpha=0.3)
        p = fig_dir / f"{vid_id}_spectrum.png"
        fig.savefig(p, dpi=110, bbox_inches="tight")
        plt.close(fig)
        paths["spectrum"] = str(p)

    return paths


# ----------------------------------------------------------------------
# ground truth
# ----------------------------------------------------------------------

def load_truth(truth_dir, vid_id):
    """Look for a truth file named after the video. JSON or plain text."""
    if not truth_dir:
        return None
    d = Path(truth_dir)
    for ext in (".json", ".txt"):
        p = d / f"{vid_id}{ext}"
        if p.exists():
            try:
                if ext == ".json":
                    data = json.loads(p.read_text())
                else:
                    data = {"raw": p.read_text().strip()}
                return {"path": str(p), "data": data}
            except (json.JSONDecodeError, OSError) as e:
                return {"path": str(p), "error": str(e)}
    return None


def summarise_truth(truth):
    """Count the 0s and 1s, so we can see if one value dominates."""
    if not truth or "data" not in truth:
        return {}
    d = truth["data"]
    bits = None
    for key in ("bits", "bitstream", "sequence", "raw"):
        v = d.get(key) if isinstance(d, dict) else None
        if isinstance(v, str) and set(v.strip()) <= {"0", "1"} and v.strip():
            bits = v.strip()
            break
        if isinstance(v, list) and all(x in (0, 1) for x in v):
            bits = "".join(str(x) for x in v)
            break
    out = {}
    if bits:
        ones = bits.count("1")
        out["n_bits"] = len(bits)
        out["ones"] = ones
        out["zeros"] = len(bits) - ones
        out["ones_share"] = round(ones / len(bits), 4)
    msg = d.get("message") if isinstance(d, dict) else None
    if isinstance(msg, str):
        out["message_len"] = len(msg)
    return out


# ----------------------------------------------------------------------
# verdict
# ----------------------------------------------------------------------

def verdict_for(row):
    """
    One label per video, with the reasons written out.
    green  = usable as is
    amber  = usable but with a problem to remember
    red    = cannot be used
    """
    reasons = []
    level = "green"

    if not row["readable"]:
        return "red", ["file does not open or has no frames"]

    if row["counted_frames"] < 30:
        level = "red"
        reasons.append(f"only {row['counted_frames']} frames")

    if row["black_frames"] > 0:
        level = "amber" if level == "green" else level
        reasons.append(f"{row['black_frames']} all-black frames")

    # Audit fix (2026-09-10): when the scan was capped with --max-frames the
    # counted figure is a cap, not a measurement, so it must not be compared
    # with the header. The Day 07 manifest was produced with --max-frames 8000
    # and this check wrongly flagged all four videos.
    if row.get("truncated"):
        reasons.append(
            f"scan capped at {row['counted_frames']} frames (--max-frames); "
            f"header reports {row['header_frames']}, not verified by this run")
    elif row["header_frames"] and abs(row["header_frames"] - row["counted_frames"]) > 2:
        level = "amber" if level == "green" else level
        reasons.append(
            f"header says {row['header_frames']} frames, we counted {row['counted_frames']}")

    if row.get("variable_frame_rate") is True:
        level = "amber" if level == "green" else level
        reasons.append("variable frame rate — frames are not evenly spaced in time")

    peak_level = row.get("light_peak_level")
    if peak_level is not None and peak_level >= 250:
        level = "amber" if level == "green" else level
        reasons.append(
            f"the light reaches {peak_level:.0f} out of 255, so its brightness is "
            f"clipped at the top — on/off still works, but the exact level is lost")

    if row.get("roi_found") is False:
        level = "red"
        reasons.append("no blinking region found — nothing changes over time")

    # A video of pure noise will still produce an "ROI" and a two-group split,
    # because noise splits too. These two checks are what catch that case.
    rvr = row.get("roi_variance_ratio")
    if rvr is not None and rvr < 3.0:
        level = "red"
        reasons.append(
            f"nothing in the picture blinks — the busiest pixel changes only "
            f"{rvr:.1f}x more than a typical one, so the ROI is just noise")

    peak = row.get("freq_peak_strength")
    if peak is not None and peak < 3.0 and level != "red":
        level = "amber"
        reasons.append(f"no clear repeating rhythm in the brightness (peak strength {peak})")

    if row.get("bimodality") is not None and row["bimodality"] < 1.0:
        level = "amber" if level == "green" else level
        reasons.append(f"brightness does not split cleanly into on/off (score {row['bimodality']:.2f})")

    if not row.get("has_truth"):
        level = "amber" if level == "green" else level
        reasons.append("no ground truth — BER cannot be computed for this video")

    if not reasons:
        reasons.append("no problems found")
    return level, reasons


# ----------------------------------------------------------------------
# main
# ----------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Day 07 dataset inspection (read-only).")
    ap.add_argument("--raw", required=True, help="folder holding the supplied videos")
    ap.add_argument("--out", required=True, help="folder to write the report into")
    ap.add_argument("--truth", default=None, help="optional folder with ground-truth files")
    ap.add_argument("--max-frames", type=int, default=None,
                    help="stop after this many frames per video (for a quick look)")
    args = ap.parse_args()

    raw_dir = Path(args.raw).resolve()
    out_dir = Path(args.out).resolve()

    if not raw_dir.exists():
        sys.exit(f"raw folder not found: {raw_dir}")

    # safety: never write inside the raw folder
    if out_dir == raw_dir or raw_dir in out_dir.parents:
        sys.exit("refusing to write inside the raw folder. Pick a different --out.")

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "per_video").mkdir(exist_ok=True)

    videos = sorted([p for p in raw_dir.rglob("*") if p.suffix.lower() in VIDEO_EXT])
    if not videos:
        sys.exit(f"no video files found in {raw_dir}")

    print(f"Found {len(videos)} video file(s) in {raw_dir}\n")

    rows = []
    hashes = {}
    for i, path in enumerate(videos, 1):
        vid_id = path.stem
        print(f"[{i}/{len(videos)}] {path.name}")

        row = {"video_id": vid_id, "filename": str(path.relative_to(raw_dir))}
        row["size_bytes"] = path.stat().st_size
        row["sha256"] = sha256_of_file(path)

        probe = run_ffprobe(path)
        stream = {}
        if probe.get("streams"):
            stream = probe["streams"][0]
        row["codec"] = stream.get("codec_name")
        row["pix_fmt"] = stream.get("pix_fmt")
        r_rate = parse_rate(stream.get("r_frame_rate"))
        a_rate = parse_rate(stream.get("avg_frame_rate"))
        row["r_frame_rate"] = None if r_rate is None else round(r_rate, 4)
        row["avg_frame_rate"] = None if a_rate is None else round(a_rate, 4)
        row["duration_s"] = None
        if probe.get("format", {}).get("duration"):
            try:
                row["duration_s"] = round(float(probe["format"]["duration"]), 3)
            except ValueError:
                pass

        # even spacing check
        times = frame_timestamps(path)
        if len(times) > 5:
            d = np.diff(np.array(times))
            d = d[d > 0]
            if len(d) > 3:
                jitter = float(d.std() / (d.mean() + 1e-12))
                row["timestamp_jitter"] = round(jitter, 5)
                row["variable_frame_rate"] = bool(jitter > 0.02)
            else:
                row["variable_frame_rate"] = None
        else:
            row["timestamp_jitter"] = None
            row["variable_frame_rate"] = None

        scan = scan_video(path, max_frames=args.max_frames)
        row["readable"] = scan["readable"]
        if not scan["readable"]:
            row.update({"counted_frames": 0, "black_frames": 0})
            level, reasons = verdict_for(row)
            row["verdict"], row["verdict_reasons"] = level, "; ".join(reasons)
            rows.append(row)
            print(f"    unreadable\n")
            continue

        row["width"] = scan["width"]
        row["height"] = scan["height"]
        row["header_fps"] = round(scan["header_fps"], 4) if scan["header_fps"] else None
        row["header_frames"] = scan["header_frames"]
        row["counted_frames"] = scan["counted_frames"]
        row["truncated"] = scan["truncated"]
        row["black_frames"] = scan["black_frames"]
        row["mean_saturated_share"] = float(np.mean(scan["sat_fraction"]))
        # How bright does the light actually get? If it sits at the top of the
        # range, the brightness is clipped: the signal is flat-topped and any
        # multi-level reading is impossible.
        row["light_peak_level"] = float(np.percentile(scan["frame_max"], 99))
        row["global_brightness_mean"] = float(np.mean(scan["global_mean"]))
        row["global_brightness_std"] = float(np.std(scan["global_mean"]))
        row["roi_found"] = scan["roi_box"] is not None
        row["roi_box"] = scan["roi_box"]
        row["roi_variance_ratio"] = round(scan["roi_variance_ratio"], 2)

        fps = row["avg_frame_rate"] or row["header_fps"]
        series = scan["roi_series"] if scan["roi_series"] is not None else scan["global_mean"]
        bi, thr = bimodality(series)
        row["bimodality"] = None if bi is None else round(bi, 3)
        row["otsu_threshold"] = None if thr is None else round(thr, 3)
        f0, snr = dominant_frequency(series, fps)
        row["dominant_freq_hz"] = None if f0 is None else round(f0, 3)
        row["freq_peak_strength"] = None if snr is None else round(snr, 2)

        truth = load_truth(args.truth, vid_id)
        row["has_truth"] = truth is not None and "error" not in truth
        row.update({f"truth_{k}": v for k, v in summarise_truth(truth).items()})

        series_for_dupe = (scan["roi_series"] if scan["roi_series"] is not None
                           else scan["global_mean"])
        hashes[vid_id] = (scan["first_hash"], scan["mid_hash"], row["sha256"],
                          np.asarray(series_for_dupe, dtype=np.float64))

        figs = make_figures(vid_id, scan, out_dir, fps)
        row["figures"] = figs

        level, reasons = verdict_for(row)
        row["verdict"] = level
        row["verdict_reasons"] = "; ".join(reasons)

        with open(out_dir / "per_video" / f"{vid_id}.json", "w") as f:
            json.dump({k: v for k, v in row.items()}, f, indent=2, default=str)

        rows.append(row)
        print(f"    {row['counted_frames']} frames, {row['width']}x{row['height']}, "
              f"verdict: {level}")
        print(f"    {row['verdict_reasons']}\n")

    # ---- duplicates ----
    exact = {}
    for vid, (_, _, sha, _) in hashes.items():
        exact.setdefault(sha, []).append(vid)
    exact_dupes = [v for v in exact.values() if len(v) > 1]

    # Near-duplicate check.
    #
    # We deliberately do NOT compare how the frames look. In this dataset every
    # video looks the same: a small bright light on a dark background. Comparing
    # appearance flags almost every pair as a duplicate, which is useless.
    #
    # What actually makes two OCC clips duplicates is that the light blinks the
    # same way. So we compare the brightness-over-time signals instead.
    near_dupes = []
    ids = list(hashes.keys())
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            sa, sb = hashes[ids[a]][2], hashes[ids[b]][2]
            if sa == sb:
                continue  # already caught as an exact duplicate
            x, y = hashes[ids[a]][3], hashes[ids[b]][3]
            if x is None or y is None or len(x) < 20 or len(y) < 20:
                continue
            n = min(len(x), len(y))
            if abs(len(x) - len(y)) > max(3, 0.05 * n):
                continue  # very different lengths, not the same clip
            xa, yb = x[:n], y[:n]
            if xa.std() < 1e-9 or yb.std() < 1e-9:
                continue
            corr = float(np.corrcoef(xa, yb)[0, 1])
            if corr > 0.98:
                near_dupes.append((ids[a], ids[b], round(corr, 4)))

    # ---- manifest ----
    fields = ["video_id", "filename", "sha256", "size_bytes", "codec", "pix_fmt",
              "width", "height", "r_frame_rate", "avg_frame_rate", "header_fps",
              "duration_s", "header_frames", "counted_frames", "variable_frame_rate",
              "timestamp_jitter", "black_frames", "mean_saturated_share", "light_peak_level",
              "roi_found", "roi_variance_ratio", "bimodality", "dominant_freq_hz",
              "freq_peak_strength",
              "has_truth", "truth_n_bits", "truth_ones_share",
              "verdict", "verdict_reasons"]
    with open(out_dir / "MANIFEST.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    write_report(out_dir, rows, exact_dupes, near_dupes, raw_dir)
    print(f"Wrote {out_dir/'MANIFEST.csv'}")
    print(f"Wrote {out_dir/'INSPECTION_REPORT.md'}")


def write_report(out_dir, rows, exact_dupes, near_dupes, raw_dir):
    green = [r for r in rows if r.get("verdict") == "green"]
    amber = [r for r in rows if r.get("verdict") == "amber"]
    red = [r for r in rows if r.get("verdict") == "red"]
    with_truth = [r for r in rows if r.get("has_truth")]

    L = []
    L.append("# Dataset Inspection Report — Day 07\n")
    L.append(f"**Raw folder:** `{raw_dir}`  ")
    L.append(f"**Videos found:** {len(rows)}  ")
    L.append(f"**Verdicts:** {len(green)} green, {len(amber)} amber, {len(red)} red  ")
    L.append(f"**With ground truth:** {len(with_truth)} of {len(rows)}\n")
    L.append("Nothing in the raw folder was changed. This run only read the files.\n")

    L.append("## 1. Every video at a glance\n")
    L.append("| video | frames | size | fps | truth? | on/off split | verdict |")
    L.append("|---|---|---|---|---|---|---|")
    for r in rows:
        fps = r.get("avg_frame_rate") or r.get("header_fps") or "?"
        bi = r.get("bimodality")
        bi = "—" if bi is None else f"{bi:.2f}"
        L.append(f"| {r['video_id']} | {r.get('counted_frames','—')} | "
                 f"{r.get('width','?')}x{r.get('height','?')} | {fps} | "
                 f"{'yes' if r.get('has_truth') else 'no'} | {bi} | **{r.get('verdict','?')}** |")
    L.append("")

    L.append("## 2. Problems found\n")
    any_problem = False
    for r in rows:
        if r.get("verdict") in ("amber", "red"):
            any_problem = True
            L.append(f"- **{r['video_id']}** ({r['verdict']}): {r['verdict_reasons']}")
    if not any_problem:
        L.append("No problems found in any video.")
    L.append("")

    L.append("## 3. Duplicates\n")
    if exact_dupes:
        for group in exact_dupes:
            L.append(f"- **Same file exactly** (same SHA-256): {', '.join(group)}")
    else:
        L.append("- No two files are byte-for-byte identical.")
    if near_dupes:
        for a, b, corr in near_dupes:
            L.append(f"- **The light blinks the same way**: `{a}` and `{b}` "
                     f"(brightness signals match at {corr}). Different files, but "
                     f"they may carry the same message — check before putting one "
                     f"in DEV and the other in TEST.")
    else:
        L.append("- No two videos share the same blinking pattern.")
    L.append("")
    L.append("Note: duplicates are judged by the blinking pattern, not by how the "
             "frames look. Every video in this dataset looks alike, so appearance "
             "would flag almost every pair.")
    L.append("")

    L.append("## 4. Ground-truth coverage\n")
    if not with_truth:
        L.append("No ground-truth files were found. BER cannot be computed on any video. "
                 "All BER work must move to the synthetic videos.")
    else:
        L.append(f"{len(with_truth)} of {len(rows)} videos have ground truth.\n")
        L.append("| video | bits | share of 1s |")
        L.append("|---|---|---|")
        for r in with_truth:
            L.append(f"| {r['video_id']} | {r.get('truth_n_bits','—')} | "
                     f"{r.get('truth_ones_share','—')} |")
        shares = [r.get("truth_ones_share") for r in with_truth
                  if isinstance(r.get("truth_ones_share"), float)]
        if shares:
            lo, hi = min(shares), max(shares)
            L.append("")
            if lo < 0.35 or hi > 0.65:
                L.append(f"**Watch out:** the share of 1s runs from {lo} to {hi}. "
                         "One value dominates in at least one video, so accuracy alone "
                         "would look good even for a decoder that always guesses the "
                         "same bit. Report BER against an always-guess baseline.")
            else:
                L.append(f"The share of 1s runs from {lo} to {hi}, which is reasonably even.")
    L.append("")

    L.append("## 5. First-look signal check\n")
    L.append("The **on/off split** score says how cleanly the brightness falls into two "
             "groups. Above about 2 is clean. Below 1 means the two levels overlap and "
             "a simple threshold will struggle.\n")
    L.append("The **strongest rhythm** is a hint at the blink rate. It is only a hint: "
             "if the light blinks faster than the camera samples, this number is an "
             "alias and will be wrong.\n")
    L.append("| video | on/off split | strongest rhythm (Hz) | peak strength |")
    L.append("|---|---|---|---|")
    for r in rows:
        if not r.get("readable"):
            continue
        bi = r.get("bimodality")
        f0 = r.get("dominant_freq_hz")
        sn = r.get("freq_peak_strength")
        L.append(f"| {r['video_id']} | {'—' if bi is None else f'{bi:.2f}'} | "
                 f"{'—' if f0 is None else f0} | {'—' if sn is None else sn} |")
    L.append("")

    L.append("## 6. Figures\n")
    for r in rows:
        if r.get("figures"):
            L.append(f"**{r['video_id']}**")
            for name, p in r["figures"].items():
                L.append(f"- {name}: `{Path(p).relative_to(out_dir)}`")
            L.append("")

    L.append("## 7. What to do next\n")
    L.append("- [ ] Check every amber and red video by eye before deciding to keep or drop it")
    L.append("- [ ] Copy this MANIFEST into `data/raw/MANIFEST.csv`")
    L.append("- [ ] Assign DEV and TEST roles, and write the TEST video IDs in the log "
             "**before** any tuning starts")
    L.append("- [ ] Send the open questions to the faculty (see `MENTOR_REVIEW.MD`)")
    L.append("- [ ] Do not clean, crop, re-encode or delete anything yet\n")

    (out_dir / "INSPECTION_REPORT.md").write_text("\n".join(L))


if __name__ == "__main__":
    main()
