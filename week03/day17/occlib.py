"""Shared pieces for Days 17-21: Signal V1 loading, the DEV/TEST split, the
threshold decoders (vectorised), the internal-consistency indicators, and a
synthetic OOK signal generator with known bits.

Everything downstream of Day 16 imports this so that every day measures the
same thing the same way.

Ground rule (unchanged since Day 07): no ground truth was supplied for the real
videos. On real signals every number here is an internal-consistency indicator.
Only the synthetic signals have a BER.
"""
import json
import time
from pathlib import Path

import numpy as np

FPS = 260.0
BPS = 92.0                 # from the FILENAME - an assumption (Days 10, 13, 16)
T92 = FPS / BPS
DEV_FRAC = 0.30            # Day 07 s6: first 30% of each signal = DEV (tuning),
                           # last 70% = TEST, opened once on Day 21
HERE = Path(__file__).resolve().parent
SIGNAL_V1 = HERE.parent.parent / "week02" / "day12" / "signal_v1"


# ----------------------------------------------------------------------
# data
# ----------------------------------------------------------------------

def load_signal_v1(root=SIGNAL_V1):
    """{'1LED_92bps/lamp1': float32 array, ...} in manifest order."""
    m = json.loads((Path(root) / "SIGNAL_V1_MANIFEST.json").read_text())
    return {f"{e['video']}/lamp{e['lamp']}": np.load(Path(root) / e["file"])
            for e in m["signals"]}


def split(s, part):
    """part = 'dev' (first 30%) | 'test' (last 70%) | 'all'."""
    k = int(len(s) * DEV_FRAC)
    return {"dev": s[:k], "test": s[k:], "all": s}[part]


# ----------------------------------------------------------------------
# thresholds and the decoder (Day 15/16 rule, vectorised)
# ----------------------------------------------------------------------

def fixed_thr(s, lo_pct=10, hi_pct=90):
    return np.full(len(s), (np.percentile(s, lo_pct) + np.percentile(s, hi_pct)) / 2, np.float32)


def adaptive_thr(s, window=2600, lo_pct=10, hi_pct=90):
    w = int(min(window, max(51, len(s) // 4)))
    step = max(1, w // 8)
    idx = np.arange(0, len(s), step)
    pad = np.pad(s, (w // 2, w // 2), mode="edge")
    lo = np.interp(np.arange(len(s)), idx, [np.percentile(pad[i:i + w], lo_pct) for i in idx])
    hi = np.interp(np.arange(len(s)), idx, [np.percentile(pad[i:i + w], hi_pct) for i in idx])
    return ((lo + hi) / 2).astype(np.float32)


def bit_windows(n, T, phase, end_margin=0.0):
    """Start/end frame index (inclusive) of every bit window.

    end_margin: frames trimmed from the END of each window. Day 15/16 used 0,
    which lets the last frame of a bit expose partly inside the NEXT bit when
    the camera's exposure is short (Day 13 inferred ~0.3 frame). Found on Day
    17 with the synthetic generator; tuned on Day 19.
    """
    nb = int((n - phase - 1) // T)
    starts = phase + np.arange(nb) * T
    hi = np.floor(starts + T - end_margin).astype(int)
    lo = np.ceil(starts).astype(int)
    return lo, np.maximum(hi, lo)


def decode(s, thr, T=T92, phase=0.0, rule="confident", end_margin=0.0):
    """One bit per period.

    rule = 'confident' : the frame furthest from the threshold (Day 09 choice)
           'nearest'   : the frame nearest the bit centre
           'average'   : mean over the frames inside the bit
    Returns bits (int8) and margin (|value - threshold| of the deciding sample).
    """
    n = len(s)
    lo, hi = bit_windows(n, T, phase, end_margin)
    nb = len(lo)
    if nb == 0:
        return np.zeros(0, np.int8), np.zeros(0, np.float32)
    d = s - thr
    if rule == "nearest":
        c = np.clip(np.round(lo - 0.5 + T / 2).astype(int), 0, n - 1)
        v = d[c]
        return (v > 0).astype(np.int8), np.abs(v).astype(np.float32)
    max_off = int(np.ceil(T)) + 1
    if rule == "average":
        tot = np.zeros(nb); cnt = np.zeros(nb)
        for j in range(max_off):
            idx = lo + j
            ok = (idx <= hi) & (idx < n)
            cl = np.clip(idx, 0, n - 1)
            tot += np.where(ok, d[cl], 0.0); cnt += ok
        v = tot / np.maximum(cnt, 1)
        return (v > 0).astype(np.int8), np.abs(v).astype(np.float32)
    best = np.zeros(nb); absb = np.full(nb, -1.0)
    for j in range(max_off):
        idx = lo + j
        ok = (idx <= hi) & (idx < n)
        cl = np.clip(idx, 0, n - 1)
        v = np.where(ok, d[cl], 0.0)
        take = ok & (np.abs(v) > absb)
        best = np.where(take, v, best); absb = np.where(take, np.abs(v), absb)
    return (best > 0).astype(np.int8), np.abs(best).astype(np.float32)


def phase_ensemble(s, thr, T=T92, n_phases=12, rule="confident", end_margin=0.0):
    """Decode at n evenly spaced phases. Returns the stack (n_phases x n_bits),
    the phase-0 bits and the 'safe' mask (bit identical at every phase)."""
    stack = [decode(s, thr, T, ph, rule, end_margin)[0]
             for ph in np.linspace(0, T, n_phases, endpoint=False)]
    n = min(len(b) for b in stack)
    M = np.stack([b[:n] for b in stack])
    votes = M.mean(0)
    return M, stack[0][:n], (votes == 0) | (votes == 1)


# ----------------------------------------------------------------------
# internal-consistency indicators (real data) - NOT correctness
# ----------------------------------------------------------------------

def agreement(a, b, max_offset=1):
    """Share of identical bits, best over a small index offset."""
    best = 0.0
    for off in range(-max_offset, max_offset + 1):
        x = a[max(0, off):]; y = b[max(0, -off):]
        m = min(len(x), len(y))
        if m:
            best = max(best, float(np.mean(x[:m] == y[:m])))
    return best


def indicators(s, T=T92, thr_fn=fixed_thr, n_phases=12, rule="confident", thr_shift=0.10,
               end_margin=0.0, bits=None):
    """bits: optionally supply the phase-0 bit sequence of another decoder (e.g.
    the ML one) to score its phase/threshold stability with the same machinery."""
    thr = thr_fn(s)
    span = float(np.ptp(s))
    M, b0, safe = phase_ensemble(s, thr, T, n_phases, rule, end_margin)
    _, margin = decode(s, thr, T, 0.0, rule, end_margin)
    n = len(b0)
    if bits is not None:
        b0 = bits[:n]; n = len(b0)
    # phase stability: bits unchanged under a +/-0.15-bit shift (Day 15 measure).
    # A negative shift wraps to phase T-0.15T, which moves every index by one,
    # so the comparison allows a +/-1 bit alignment.
    agr = []
    for d in (-0.15, 0.15):
        b2, _ = decode(s, thr, T, (d * T) % T, rule, end_margin)
        agr.append(agreement(b0, b2))
    # threshold tolerance: bits unchanged when the threshold moves +/-10% of span
    tt = []
    for d in (-thr_shift, thr_shift):
        b2, _ = decode(s, thr + d * span, T, 0.0, rule, end_margin)
        tt.append(agreement(b0, b2))
    return {
        "n_bits": int(n),
        "safe_pct": round(float(safe.mean() * 100), 2),
        "phase_stability_pct": round(float(np.mean(agr) * 100), 2),
        "threshold_tolerance_pct": round(float(np.mean(tt) * 100), 2),
        "median_margin_pct": round(float(np.median(margin[:n]) / span * 100), 2),
        "ones_pct": round(float(b0.mean() * 100), 2),
        "flip_pct": round(float(np.mean(np.diff(b0) != 0) * 100), 2),
    }


# ----------------------------------------------------------------------
# synthetic OOK signal with known bits (the only place a BER exists)
# ----------------------------------------------------------------------

def random_bits(n, seed):
    return np.random.default_rng(seed).integers(0, 2, n).astype(np.int8)


def synth(bits, T=T92, phase=0.0, exposure=0.3, hi=245.0, lo=1.0, noise=8.0, seed=0, sub=16):
    """Per-frame brightness a camera would record from an OOK lamp.

    Each frame integrates the light over an exposure window of `exposure`
    frames (Day 13 inferred about 0.3 for the real camera). Level, contrast and
    noise default to what Day 10 measured (0 / ~245, noise 6-11).

    LIMITATION: this is the *assumed* model - a clean bit clock at period T.
    The real videos contain run lengths this model cannot produce (Day 10), so
    a BER measured here says how well a method decodes the model, not the
    videos.
    """
    rng = np.random.default_rng(seed)
    n = int(np.floor((len(bits) * T + phase)))
    k = np.arange(n)[:, None] + (np.arange(sub) + 0.5)[None, :] / sub * exposure
    idx = np.clip(np.floor((k - phase) / T).astype(int), 0, len(bits) - 1)
    x = np.where(bits[idx] == 1, hi, lo).mean(1)
    return (x + rng.normal(0, noise, n)).astype(np.float32)


def ber(pred, ref, max_offset=3):
    """Lowest BER over both polarities and small alignment offsets (Day 05 s4.2).
    Returns (ber, polarity, offset)."""
    best = (1.0, 1, 0)
    for pol in (1, 0):
        p = pred if pol else 1 - pred
        for off in range(-max_offset, max_offset + 1):
            a = p[max(0, off):]; r = ref[max(0, -off):]
            m = min(len(a), len(r))
            if m < len(ref) // 2:
                continue
            e = float(np.mean(a[:m] != r[:m]))
            if e < best[0]:
                best = (e, pol, off)
    return best


def timed(fn, *a, **k):
    t0 = time.perf_counter(); out = fn(*a, **k); return out, time.perf_counter() - t0


if __name__ == "__main__":
    # self-check: a clean synthetic stream decodes exactly at the true phase,
    # and the ensemble/safe machinery agrees with Day 16 on the real data
    b = random_bits(2000, 0)
    x = synth(b, phase=0.7, noise=8)
    d, _ = decode(x, fixed_thr(x), T92, 0.7, end_margin=0.3)
    assert ber(d, b)[0] == 0.0, ber(d, b)
    S = load_signal_v1()
    s = S["1LED_92bps/lamp1"]
    _, b0, safe = phase_ensemble(s, fixed_thr(s))
    assert abs(safe.mean() * 100 - 40.82) < 0.05, safe.mean()
    print("occlib self-check passed:", len(S), "signals;", f"1LED safe {safe.mean()*100:.2f}%")
