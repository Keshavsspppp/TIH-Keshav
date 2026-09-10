#!/usr/bin/env python3
"""
Threshold OOK decoder — Signal V1 to a preliminary bit sequence.

Two decision rules:
  fixed     one threshold for the whole signal (midpoint of the 10th and 90th
            percentiles). Deliberately simple. This is the baseline.
  adaptive  rolling-median threshold with a Schmitt trigger, so a slow shift in
            level cannot drag the decision off.

Both sample the same way: within each bit, take the frame whose brightness is
furthest from the threshold. Day 09 measured this against three alternatives and
it was the only one that scored 0.00% marginal bits at every phase.

IMPORTANT — no ground truth has been supplied for these videos. Nothing here can
tell you whether a bit is CORRECT. Every number this produces is an internal
consistency indicator: how confident, how stable, how self-consistent. A decoder
can score perfectly on all of them and still be wrong about every bit.

Usage:
    python decoder.py --signals signal_v1 --out bits/
    python decoder.py --signals signal_v1 --out bits/ --rates 91,92,124,136
"""

import argparse
import json
from pathlib import Path

import numpy as np

FPS = 260.0


# ----------------------------------------------------------------------
# thresholds
# ----------------------------------------------------------------------

def fixed_threshold(s):
    """One level for the whole signal."""
    return np.full(len(s), (np.percentile(s, 10) + np.percentile(s, 90)) / 2.0,
                   dtype=np.float32)


def adaptive_threshold(s, window_frames=2600):
    """
    Rolling midpoint. Uses a wide window so it tracks a slow drift in level
    without chasing the data itself.
    """
    w = int(min(window_frames, max(51, len(s) // 4)))
    if w % 2 == 0:
        w += 1
    pad = np.pad(s, (w // 2, w // 2), mode="edge")
    # rolling min and max via a coarse grid, then interpolate - cheap and smooth
    step = max(1, w // 8)
    idx = np.arange(0, len(s), step)
    los, his = [], []
    for i in idx:
        seg = pad[i:i + w]
        los.append(np.percentile(seg, 10))
        his.append(np.percentile(seg, 90))
    lo = np.interp(np.arange(len(s)), idx, los)
    hi = np.interp(np.arange(len(s)), idx, his)
    return ((lo + hi) / 2.0).astype(np.float32)


# ----------------------------------------------------------------------
# decision
# ----------------------------------------------------------------------

def decode(s, thr, period, phase, hysteresis=0.0):
    """
    One bit per period. Within each bit, use the frame whose brightness is
    furthest from the threshold, and record how far that was (the margin).
    """
    n_bits = int((len(s) - phase - 1) // period)
    bits = np.empty(n_bits, dtype=np.int8)
    margin = np.empty(n_bits, dtype=np.float32)
    span = np.ptp(s)
    state = 1 if s[0] > thr[0] else 0

    for k in range(n_bits):
        a = phase + k * period
        idx = np.arange(int(np.ceil(a)), min(int(np.floor(a + period)) + 1, len(s)))
        idx = idx[(idx >= 0) & (idx < len(s))]
        if len(idx) == 0:
            idx = np.array([min(len(s) - 1, int(round(a + period / 2)))])
        d = s[idx] - thr[idx]
        j = int(np.argmax(np.abs(d)))
        m = float(d[j])
        if hysteresis > 0:
            band = hysteresis * span
            if state == 0 and m > band:
                state = 1
            elif state == 1 and m < -band:
                state = 0
            bits[k] = state
        else:
            bits[k] = 1 if m > 0 else 0
        margin[k] = abs(m)
    return bits, margin


def best_phase(s, thr, period, steps=60):
    """Pick the phase whose sampled points sit furthest from the threshold."""
    best = None
    for ph in np.linspace(0, period, steps, endpoint=False):
        _, m = decode(s, thr, period, ph)
        sc = float(np.mean(m))
        if best is None or sc > best[0]:
            best = (sc, float(ph))
    return best[1], best[0]


# ----------------------------------------------------------------------
# internal consistency indicators (NOT correctness)
# ----------------------------------------------------------------------

def margin_stats(margin, span):
    """How far from the threshold the decisions sat. Higher is more confident."""
    return {
        "median_margin_pct_of_range": round(float(np.median(margin) / span * 100), 2),
        "worst_margin_pct_of_range": round(float(margin.min() / span * 100), 3),
        "bits_below_5pct_margin": round(float(np.mean(margin < 0.05 * span) * 100), 3),
        "bits_below_15pct_margin": round(float(np.mean(margin < 0.15 * span) * 100), 3),
    }


def stream_stats(bits):
    """Does the stream look like data? Random bits give 50% ones, 50% flips."""
    flips = np.diff(bits) != 0
    runs = np.diff(np.flatnonzero(np.concatenate(([True], flips, [True]))))
    return {
        "n_bits": int(len(bits)),
        "ones_pct": round(float(bits.mean() * 100), 2),
        "flip_rate_pct": round(float(flips.mean() * 100), 2),
        "longest_run": int(runs.max()) if len(runs) else 0,
        "mean_run_bits": round(float(runs.mean()), 3) if len(runs) else 0.0,
    }


def phase_stability(s, thr, period, phase, bits, nudge=0.15):
    """
    Shift the assumed bit start slightly and see how many bits change.
    A trustworthy decode barely moves. A fragile one rewrites itself.
    """
    out = {}
    for d in (-nudge, nudge):
        b2, _ = decode(s, thr, period, (phase + d * period) % period)
        n = min(len(bits), len(b2))
        out[f"agree_at_{d:+.2f}_bit_pct"] = round(float(np.mean(bits[:n] == b2[:n]) * 100), 2)
    return out


def self_repetition(bits, max_lag=None):
    """
    Does the bit sequence repeat itself?

    If the transmitter loops a message, the stream contains the same block twice.
    That would be visible without any ground truth, and it is the one internal
    check that could actually validate the clock: at the right bit rate the
    repeat is sharp, at a wrong one it is smeared away.
    """
    b = bits.astype(np.float64) * 2 - 1          # map to -1 / +1
    n = len(b)
    if max_lag is None:
        max_lag = n // 2
    f = np.fft.rfft(b, 2 * n)
    ac = np.fft.irfft(f * np.conj(f))[:max_lag]
    ac /= ac[0]
    lo = 16
    if max_lag <= lo + 2:
        return {"best_lag": None, "best_score": 0.0, "noise_level": 0.0, "ratio": 0.0}
    seg = ac[lo:]
    k = int(np.argmax(seg)) + lo
    noise = float(np.std(seg))
    return {
        "best_lag": int(k),
        "best_score": round(float(ac[k]), 4),
        "noise_level": round(noise, 4),
        "ratio": round(float(ac[k] / max(noise, 1e-9)), 2),
    }


# ----------------------------------------------------------------------
# driver
# ----------------------------------------------------------------------

def run_signal(s, period, hysteresis=0.05):
    span = float(np.ptp(s))
    results = {}
    for name, thr in (("fixed", fixed_threshold(s)),
                      ("adaptive", adaptive_threshold(s))):
        hy = 0.0 if name == "fixed" else hysteresis
        ph, _ = best_phase(s, thr, period)
        if name == "fixed":
            ph_fixed = ph                      # unrounded, for the same-phase check
        bits, margin = decode(s, thr, period, ph, hysteresis=hy)
        r = {"phase_frames": round(ph, 3)}
        r.update(margin_stats(margin, span))
        r.update(stream_stats(bits))
        r.update(phase_stability(s, thr, period, ph, bits))
        r["self_repetition"] = self_repetition(bits)
        results[name] = r
        results[name + "_bits"] = bits
    a, b = results["fixed_bits"], results["adaptive_bits"]
    n = min(len(a), len(b))
    results["fixed_vs_adaptive_agree_pct"] = round(float(np.mean(a[:n] == b[:n]) * 100), 3)
    # Audit addition (2026-09-10): the figure above lets each decoder pick its
    # own phase, so on three signals it reads ~60% for a reason that has nothing
    # to do with the threshold (DAY_15.MD s3). This one holds the phase fixed at
    # the fixed decoder's choice, which is the comparison DAY_15.MD s2 reports.
    b_same, _ = decode(s, adaptive_threshold(s), period, ph_fixed, hysteresis=hysteresis)
    n2 = min(len(a), len(b_same))
    results["fixed_vs_adaptive_agree_pct_same_phase"] = round(
        float(np.mean(a[:n2] == b_same[:n2]) * 100), 3)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--signals", default="signal_v1")
    ap.add_argument("--out", default="bits")
    ap.add_argument("--rates", default="92",
                    help="comma-separated bit rates to try, e.g. 91,92,124,136")
    a = ap.parse_args()

    rates = [float(x) for x in a.rates.split(",")]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    report = {}

    for meta_path in sorted(Path(a.signals).glob("*/meta.json")):
        m = json.load(open(meta_path))
        vid = m["video"]["id"]
        for sig in m["signals"]:
            s = np.load(meta_path.parent / sig["file"])
            key = f"{vid}/lamp{sig['lamp']}"
            report[key] = {}
            for rate in rates:
                period = FPS / rate
                res = run_signal(s, period)
                tag = f"{rate:g}bps"
                np.save(out / f"{vid}_lamp{sig['lamp']}_{tag}_fixed.npy",
                        res.pop("fixed_bits"))
                np.save(out / f"{vid}_lamp{sig['lamp']}_{tag}_adaptive.npy",
                        res.pop("adaptive_bits"))
                report[key][tag] = res
            print(f"{key:26s} " + "  ".join(
                f"{t}: {report[key][t]['fixed']['n_bits']}b "
                f"agree {report[key][t]['fixed_vs_adaptive_agree_pct']:.1f}%"
                for t in report[key]))

    json.dump(report, open(out / "decode_report.json", "w"), indent=2)
    print(f"\nwrote {out/'decode_report.json'}")


if __name__ == "__main__":
    main()
