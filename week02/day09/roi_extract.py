"""Find one ROI per lamp, then pull one brightness series per lamp.

Key idea: the lamps carry DIFFERENT data (Day 07 measured 0.31-0.41 correlation
between them). So we group the changing pixels by how their brightness behaves
over time. Pixels belonging to the same lamp blink together; pixels from
different lamps do not. This splits touching lamps, which a shape-based method
cannot do.
"""
import cv2, numpy as np, json
from pathlib import Path
FPS, BPS = 260.0, 92.0
SPS = FPS / BPS
MIN_BLOB = 100          # pixels; rejects specks of glare (risk R3)


def sustained_start(maxes, fps=FPS, win_s=1.0, need=0.15):
    """First point where the lamp is lit for a decent share of a whole second.
    Guards against the 2LEDs false start (risk R1)."""
    w = int(fps * win_s)
    lit = (maxes > 180).astype(np.float32)
    if len(lit) < w:
        return 0
    run = np.convolve(lit, np.ones(w) / w, mode='valid')
    ok = np.flatnonzero(run >= need)
    return int(ok[0]) if len(ok) else 0


def sustained_end(maxes, fps=FPS, win_s=1.0, need=0.15):
    r = sustained_start(maxes[::-1], fps, win_s, need)
    return len(maxes) - 1 - r


def scan_maxes(path):
    cap = cv2.VideoCapture(str(path)); m = []
    while True:
        ok, f = cap.read()
        if not ok: break
        m.append(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).max())
    cap.release(); return np.array(m)


def sample_frames(path, a, b, n=600):
    """Frames spread across the WHOLE active part, not just the start (risk R4)."""
    stride = max(1, (b - a) // n)
    cap = cv2.VideoCapture(str(path)); cap.set(cv2.CAP_PROP_POS_FRAMES, a)
    fr, idx, i = [], [], a
    while i <= b and len(fr) < n:
        ok, f = cap.read()
        if not ok: break
        if (i - a) % stride == 0:
            fr.append(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)); idx.append(i)
        i += 1
    cap.release()
    return np.stack(fr), np.array(idx)


def find_lamps(stack, k_max=6):
    """Group changing pixels by their brightness-over-time behaviour."""
    n, H, W = stack.shape
    f = stack.astype(np.float32)
    var = f.var(axis=0)
    # absolute threshold: a lamp pixel swings between about 0 and 245, so its
    # variance is huge. A percentile cap would limit us to a fixed share of the
    # frame, which fails once several lamps fill more of it.
    thr = max(400.0, 0.03 * float(var.max()))
    ys, xs = np.nonzero(var >= thr)
    if len(ys) < MIN_BLOB:
        return [], var, None
    sig = f[:, ys, xs].T                       # one row per pixel
    sig = (sig - sig.mean(1, keepdims=True)) / (sig.std(1, keepdims=True) + 1e-6)

    best = None
    for k in range(1, k_max + 1):
        crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.1)
        _, lab, cen = cv2.kmeans(sig.astype(np.float32), k, None, crit, 5,
                                 cv2.KMEANS_PP_CENTERS)
        lab = lab.ravel()
        sizes = np.bincount(lab, minlength=k)
        if (sizes < MIN_BLOB).any():
            continue
        # how different are the group signals from each other?
        if k == 1:
            sep = 0.0
        else:
            cc = np.corrcoef(cen)
            sep = 1.0 - float(cc[np.triu_indices(k, 1)].max())
        # keep the LARGEST k whose groups still behave differently from each
        # other. Groups that behave alike are the same lamp split in two.
        if k == 1 or sep > 0.15:
            best = (sep, k, lab)
    if best is None:
        return [], var, None
    sep, k, lab = best

    lamps = []
    for c in range(k):
        m = lab == c
        if m.sum() < MIN_BLOB: continue
        py, px = ys[m], xs[m]
        lamps.append({'box': [int(px.min()), int(py.min()),
                              int(px.max() - px.min() + 1),
                              int(py.max() - py.min() + 1)],
                      'n_px': int(m.sum()),
                      'cx': float(px.mean()), 'cy': float(py.mean())})
    # Keep only real lamps. A lamp is a solid disc: its pixels fill most of its
    # own box. The leftover groups are halo and glare - a few pixels smeared
    # over a large box - so they have a low fill and far fewer pixels.
    if lamps:
        biggest = max(L['n_px'] for L in lamps)
        keep = []
        for L in lamps:
            x, y, w, h = L['box']
            L['fill'] = round(L['n_px'] / float(w * h), 3)
            L['share'] = round(L['n_px'] / biggest, 3)
            if L['fill'] >= 0.40 and L['share'] >= 0.25:
                keep.append(L)
        lamps = keep
    lamps.sort(key=lambda L: (L['cy'] // 60, L['cx']))
    return lamps, var, sep


results = {}
for p in sorted(Path('data/raw').glob('*.mp4')):
    name = p.stem; expected = int(name[0])
    mx = scan_maxes(p)
    a, b = sustained_start(mx), sustained_end(mx)
    stack, idx = sample_frames(p, a, b)
    lamps, var, sep = find_lamps(stack)
    print(f"=== {name}: expected {expected} lamp(s), found {len(lamps)}"
          f"  (group separation {sep:.2f})" if sep is not None else name)
    print(f"    trimmed to frames {a}..{b}  ({(b-a)/FPS:.1f}s, was 0..{len(mx)-1})")
    for i, L in enumerate(lamps):
        x, y, w, h = L['box']
        print(f"    lamp {i+1}: box ({x},{y}) {w}x{h}, {L['n_px']} changing pixels")
    results[name] = {'trim': [int(a), int(b)], 'expected': expected,
                     'lamps': lamps, 'separation': sep}
    np.save(f'var_{name}.npy', var)
    print()
json.dump(results, open('rois.json', 'w'), indent=2)
