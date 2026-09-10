#!/usr/bin/env python3
"""Day 20 - project-specific robustness / ablation study.

The brief's own experiment: sensitivity to ROI choice, smoothing, threshold and
symbol timing, across all four videos. Each sweep changes ONE setting and holds
everything else at the Day 19 tuned configuration. Every sweep is run for two
decoders so their degradation can be compared (Day 05 E14):

    baseline : Day 09/16 rule  - most confident frame in the window
    tuned    : Day 19 rule     - nearest frame to the bit centre

Metrics
  synthetic (assumed 92 bps model, bits known)     : BER at the true phase and
                                                     at the phase-0 convention
  real DEV part (first 30% of each lamp, no truth) : share of bits identical to
                                                     the default setting, and
                                                     the phase-independent share
  ROI sweeps exist only for real data (a synthetic signal has no ROI).

The ROI sweep re-reads the DEV frames of each video once and aggregates every
box variant in the same pass (mean of the brightest 25% of pixels, as Signal V1).

Outputs: ablation_results.json, fig_ablation_day20.png
"""
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "day17"))
from occlib import (DEV_FRAC, T92, agreement, ber, decode, fixed_thr, load_signal_v1,
                    random_bits, split, synth)

RAW = HERE.parent.parent / "Videos"
MANIFEST = HERE.parent.parent / "week02" / "day12" / "signal_v1"
RULES = {"baseline (confident)": "confident", "tuned (nearest)": "nearest"}
ROI_SCALES = (0.5, 0.7, 0.85, 1.0, 1.25, 1.5, 2.0)
ROI_SHIFTS = (-0.5, -0.25, -0.1, 0.0, 0.1, 0.25, 0.5)
SMOOTH = (1, 3, 5, 7, 9)
THR_SHIFT = (-0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3)
PHASE = np.round(np.arange(-0.5, 0.5001, 0.05), 2)
PERIOD = (-10, -3, -2, -1, -0.5, -0.2, 0.0, 0.2, 0.5, 1, 2, 3, 10)


def dec(x, rule, T=T92, phase=0.0, thr=None):
    thr = fixed_thr(x) if thr is None else thr
    return decode(x, thr, T, phase, rule)[0]


def smooth(x, w):
    if w <= 1:
        return x
    pad = np.pad(x, (w // 2, w - 1 - w // 2), mode="edge")
    return np.convolve(pad, np.ones(w) / w, mode="valid").astype(np.float32)


def phase_indep(x, rule):
    st = [dec(x, rule, phase=ph) for ph in np.linspace(0, T92, 12, endpoint=False)]
    n = min(len(b) for b in st); M = np.stack([b[:n] for b in st]); v = M.mean(0)
    return float(np.mean((v == 0) | (v == 1)) * 100)


# ---------------------------------------------------------------- synthetic
def synth_set(seeds=range(40, 44), noise=8):
    rng = np.random.default_rng(20); out = []
    for s in seeds:
        b = random_bits(3000, s); ph = float(rng.uniform(0, T92))
        out.append((b, ph, synth(b, phase=ph, exposure=0.3, noise=noise, seed=s + 400)))
    return out


def synth_ber(SET, rule, transform=lambda x: x, T=T92, phase_off=0.0, thr_shift=0.0):
    e0, et = [], []
    for b, ph, x in SET:
        x2 = transform(x); thr = fixed_thr(x2) + thr_shift * float(np.ptp(x2))
        e0.append(ber(dec(x2, rule, T, 0.0, thr), b)[0])
        et.append(ber(dec(x2, rule, T, (ph + phase_off * T92) % T, thr), b)[0])
    return round(float(np.mean(e0)) * 100, 2), round(float(np.mean(et)) * 100, 2)


# ---------------------------------------------------------------- real ROI
def roi_variants(box):
    x, y, w, h = box; cx, cy = x + w / 2, y + h / 2; out = {}
    for sc in ROI_SCALES:
        ww, hh = max(2, int(round(w * sc))), max(2, int(round(h * sc)))
        out[f"scale {sc}"] = (int(round(cx - ww / 2)), int(round(cy - hh / 2)), ww, hh)
    for sh in ROI_SHIFTS:
        out[f"shift x {sh:+.2f}"] = (int(round(x + sh * w)), y, w, h)
    return out


def extract_variants(video, lamps, a, n_frames):
    """One pass over frames a..a+n_frames-1; returns {lamp_id: {variant: series}}."""
    cap = cv2.VideoCapture(str(video)); cap.set(cv2.CAP_PROP_POS_FRAMES, a)
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)); W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    variants = {L["lamp"]: roi_variants(L["box"]) for L in lamps}
    out = {lid: {v: [] for v in vs} for lid, vs in variants.items()}
    for _ in range(n_frames):
        ok, f = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        for lid, vs in variants.items():
            for name, (x, y, w, h) in vs.items():
                x0, y0 = max(0, x), max(0, y); x1, y1 = min(W, x + w), min(H, y + h)
                if x1 <= x0 or y1 <= y0:
                    out[lid][name].append(0.0); continue
                p = g[y0:y1, x0:x1].reshape(-1); k = max(1, p.size // 4)
                out[lid][name].append(float(np.partition(p, p.size - k)[p.size - k:].mean()))
    cap.release()
    return {lid: {v: np.array(s, np.float32) for v, s in vs.items()} for lid, vs in out.items()}


def main():
    t_start = time.time()
    S = load_signal_v1(); DEV = {k: split(s, "dev") for k, s in S.items()}
    SET8, SET80 = synth_set(noise=8), synth_set(noise=80)
    R = {"note": "Real-data columns are agreement with the default setting and phase-independent share "
                 "(no ground truth). Synthetic columns are BER on the assumed 92 bps model.", "sweeps": {}}

    # ---- default real bits per rule (reference for 'unchanged' columns)
    ref = {r: {k: dec(s, rule) for k, s in DEV.items()} for r, rule in RULES.items()}

    def real_row(r, rule, transform, T=T92, thr_shift=0.0, phase=0.0):
        agr, pi = [], []
        for k, s in DEV.items():
            x2 = transform(s); thr = fixed_thr(x2) + thr_shift * float(np.ptp(x2))
            agr.append(agreement(ref[r][k], dec(x2, rule, T, phase, thr)))
            pi.append(phase_indep(x2, rule) if (T == T92 and thr_shift == 0.0 and phase == 0.0) else np.nan)
        return round(float(np.median(agr)) * 100, 2), (round(float(np.nanmedian(pi)), 2) if not np.all(np.isnan(pi)) else None)

    # ---- 1. smoothing
    sw = {}
    for w in SMOOTH:
        sw[str(w)] = {}
        for r, rule in RULES.items():
            b8 = synth_ber(SET8, rule, lambda x, w=w: smooth(x, w)); b80 = synth_ber(SET80, rule, lambda x, w=w: smooth(x, w))
            ag, pi = real_row(r, rule, lambda x, w=w: smooth(x, w))
            sw[str(w)][r] = {"synth_ber_phase0_n8": b8[0], "synth_ber_true_n8": b8[1],
                             "synth_ber_phase0_n80": b80[0], "synth_ber_true_n80": b80[1],
                             "real_unchanged_pct": ag, "real_phase_indep_pct": pi}
    R["sweeps"]["smoothing_window_frames"] = sw
    print("smoothing done", f"{time.time()-t_start:.0f}s")

    # ---- 2. threshold shift
    st = {}
    for d in THR_SHIFT:
        st[f"{d:+.1f}"] = {}
        for r, rule in RULES.items():
            b8 = synth_ber(SET8, rule, thr_shift=d); b80 = synth_ber(SET80, rule, thr_shift=d)
            ag, _ = real_row(r, rule, lambda x: x, thr_shift=d)
            st[f"{d:+.1f}"][r] = {"synth_ber_phase0_n8": b8[0], "synth_ber_true_n8": b8[1],
                                  "synth_ber_phase0_n80": b80[0], "synth_ber_true_n80": b80[1],
                                  "real_unchanged_pct": ag}
    R["sweeps"]["threshold_shift_fraction_of_range"] = st
    print("threshold done", f"{time.time()-t_start:.0f}s")

    # ---- 3. phase offset (synthetic: from the true phase; real: from phase 0)
    pho = {}
    for o in PHASE:
        pho[f"{o:+.2f}"] = {}
        for r, rule in RULES.items():
            _, bt8 = synth_ber(SET8, rule, phase_off=o); _, bt80 = synth_ber(SET80, rule, phase_off=o)
            ag, _ = real_row(r, rule, lambda x: x, phase=(o * T92) % T92)
            pho[f"{o:+.2f}"][r] = {"synth_ber_n8": bt8, "synth_ber_n80": bt80, "real_unchanged_pct": ag}
    R["sweeps"]["phase_offset_bits"] = pho
    print("phase done", f"{time.time()-t_start:.0f}s")

    # ---- 4. period error
    pe = {}
    for e in PERIOD:
        T = T92 * (1 + e / 100); pe[f"{e:+g}"] = {}
        for r, rule in RULES.items():
            b8 = synth_ber(SET8, rule, T=T); b80 = synth_ber(SET80, rule, T=T)
            ag, _ = real_row(r, rule, lambda x: x, T=T)
            pe[f"{e:+g}"][r] = {"synth_ber_phase0_n8": b8[0], "synth_ber_true_n8": b8[1],
                                "synth_ber_phase0_n80": b80[0], "synth_ber_true_n80": b80[1],
                                "real_unchanged_pct": ag}
    R["sweeps"]["period_error_pct"] = pe
    print("period done", f"{time.time()-t_start:.0f}s")

    # ---- 5. ROI (real only)
    man = json.loads((MANIFEST / "SIGNAL_V1_MANIFEST.json").read_text())
    roi = {}
    for vid in sorted({e["video"] for e in man["signals"]}):
        lamps = [e for e in man["signals"] if e["video"] == vid]
        meta = json.loads((MANIFEST / vid / "meta.json").read_text())
        a = meta["trim"]["start_frame"]; n = int(meta["trim"]["kept_frames"] * DEV_FRAC)
        series = extract_variants(RAW / f"{vid}.mp4", lamps, a, n)
        for L in lamps:
            key = f"{vid}/lamp{L['lamp']}"; base = DEV[key][:n]
            for vname, x in series[L["lamp"]].items():
                roi.setdefault(vname, {})
                for r, rule in RULES.items():
                    d = roi[vname].setdefault(r, {"real_unchanged_pct": [], "real_phase_indep_pct": [], "gap_over_noise": []})
                    if float(np.ptp(x)) < 20:                 # box fell off the lamp
                        d["real_unchanged_pct"].append(50.0); d["real_phase_indep_pct"].append(np.nan); d["gap_over_noise"].append(0.0); continue
                    d["real_unchanged_pct"].append(agreement(dec(base, rule), dec(x, rule)) * 100)
                    d["real_phase_indep_pct"].append(phase_indep(x, rule))
                    t = (np.percentile(x, 10) + np.percentile(x, 90)) / 2; sp = np.ptp(x)
                    on, off = x[x > t + .25 * sp], x[x < t - .25 * sp]
                    d["gap_over_noise"].append(float((on.mean() - off.mean()) / max(np.sqrt((on.std()**2 + off.std()**2) / 2), 1e-9)))
        print("  ROI", vid, f"{time.time()-t_start:.0f}s")
    for vname in roi:
        for r in roi[vname]:
            roi[vname][r] = {m: round(float(np.nanmedian(v)), 2) for m, v in roi[vname][r].items()}
    R["sweeps"]["roi"] = roi
    R["runtime_s"] = round(time.time() - t_start, 1)
    (HERE / "ablation_results.json").write_text(json.dumps(R, indent=2))

    # ---- figure
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 3, figsize=(15, 7.5)); col = {"baseline (confident)": "#B85042", "tuned (nearest)": "#1f5fa8"}
    for r in RULES:
        ax[0, 0].plot(SMOOTH, [sw[str(w)][r]["synth_ber_phase0_n8"] for w in SMOOTH], "o-", color=col[r], label=f"{r}, synth BER @ phase 0")
        ax[0, 0].plot(SMOOTH, [sw[str(w)][r]["synth_ber_true_n8"] for w in SMOOTH], "s--", color=col[r], alpha=.6, label=f"{r}, synth BER @ true")
        ax[0, 1].plot(THR_SHIFT, [st[f'{d:+.1f}'][r]["synth_ber_true_n8"] for d in THR_SHIFT], "s--", color=col[r], alpha=.6)
        ax[0, 1].plot(THR_SHIFT, [st[f'{d:+.1f}'][r]["synth_ber_phase0_n8"] for d in THR_SHIFT], "o-", color=col[r])
        ax[0, 2].plot(PHASE, [pho[f'{o:+.2f}'][r]["synth_ber_n8"] for o in PHASE], "o-", color=col[r], ms=3)
        ax[1, 0].plot([e for e in PERIOD if abs(e) <= 3], [pe[f'{e:+g}'][r]["synth_ber_true_n8"] for e in PERIOD if abs(e) <= 3], "s--", color=col[r], alpha=.6)
        ax[1, 0].plot([e for e in PERIOD if abs(e) <= 3], [pe[f'{e:+g}'][r]["synth_ber_phase0_n8"] for e in PERIOD if abs(e) <= 3], "o-", color=col[r])
        ax[1, 1].plot(ROI_SCALES, [roi[f"scale {s}"][r]["real_unchanged_pct"] for s in ROI_SCALES], "o-", color=col[r], label=f"{r}, bits unchanged")
        ax[1, 2].plot(ROI_SHIFTS, [roi[f"shift x {s:+.2f}"][r]["real_unchanged_pct"] for s in ROI_SHIFTS], "o-", color=col[r])
    ax[0, 0].set(title="Smoothing (synthetic, noise 8)", xlabel="window (frames)", ylabel="BER %"); ax[0, 0].legend(fontsize=6)
    ax[0, 1].set(title="Threshold shift (synthetic, noise 8)", xlabel="shift (fraction of range)", ylabel="BER %")
    ax[0, 2].set(title="Phase offset from truth (synthetic, noise 8)", xlabel="offset (bits)", ylabel="BER %")
    ax[1, 0].set(title="Assumed-period error (synthetic, noise 8)", xlabel="period error (%)", ylabel="BER %")
    ax[1, 1].set(title="ROI scale (real DEV)", xlabel="box scale", ylabel="% bits unchanged vs default box"); ax[1, 1].legend(fontsize=7)
    ax[1, 2].set(title="ROI shift (real DEV)", xlabel="x shift (fraction of box width)", ylabel="% bits unchanged")
    for a_ in ax.ravel(): a_.grid(alpha=.3)
    fig.suptitle("Day 20 - sensitivity: baseline (Day 09 rule) vs tuned (Day 19 rule). Solid = phase 0, dashed = true phase.", fontsize=10)
    fig.tight_layout(); fig.savefig(HERE / "fig_ablation_day20.png", dpi=110)
    print("wrote ablation_results.json, fig_ablation_day20.png", f"({R['runtime_s']} s)")


if __name__ == "__main__":
    main()
