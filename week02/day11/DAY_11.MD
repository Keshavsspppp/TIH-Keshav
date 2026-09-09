# Day 11 — Preprocessing Pipeline

**Project:** Optical Camera Communication (OCC) Video Message Decoding
**What was built:** the working pipeline from raw video to a saved brightness signal.
**Status:** run over all four videos. Determinism checked and passing.

**Files:** `occ_pipeline.py` (the code), `configs/preprocess_v1.yaml` (the settings), `signals/` (the output), `fig_signals.png` (what came out).

This step does **not** decode anything. It produces the signal that the decoder will read. Bits come later.

---

## 1. How to Run It

```bash
# one video
python occ_pipeline.py --video data/raw/1LED_92bps.mp4 \
                       --config configs/preprocess_v1.yaml --out signals/

# all four
python occ_pipeline.py --all --config configs/preprocess_v1.yaml --out signals/

# run twice and check the output is identical
python occ_pipeline.py --all --config configs/preprocess_v1.yaml --out signals/ --verify
```

Nothing is written to `data/raw/`. The pipeline only reads it.

---

## 2. The Five Stages

| Stage | What it does | Setting |
|---|---|---|
| 1 | Read every frame, note the brightest pixel in each | — |
| 2 | **Trim** the dark lead-in and lead-out | `trim.*` |
| 3 | **Find one region per lamp** by grouping pixels on how they blink | `roi.*` |
| 4 | **Aggregate** each lamp's box to one number per frame | `intensity.*` |
| 5 | **Clean** — detrend, normalise, smooth (all off) | `clean.*` |

### Stage 2 — Trim

Start where the lamp is lit for at least 15% of a one-second window, **not** at the first bright frame. `2LEDs_92bps` has a single flash at frame 93 followed by 3.4 seconds of darkness; trimming on the first bright frame would feed that silence to the decoder.

### Stage 3 — Find the lamps

Group the changing pixels by how their brightness behaves over time. Pixels of one lamp blink together; pixels of different lamps do not. That is what separates two lamps sitting side by side, which no shape-based rule can do once their bright areas touch.

Then drop groups that are not solid discs (fill below 40% of their box, or fewer than a quarter of the biggest group's pixels). Those are halo and glare.

### Stage 4 — Aggregate

Mean of the brightest 25% of the pixels in each box. Day 10 compared eight options: a plain mean over the whole box is diluted by dark corner pixels, and a single `max` is at the mercy of one hot pixel. This one sits near the top and averages over many pixels.

### Stage 5 — Clean

**All three steps are off**, and that is a measured decision.

| Step | Off because |
|---|---|
| Detrend | The lamp's on-level moves by at most 0.13 grey levels across a whole recording, against a contrast of about 245. There is nothing to remove |
| Normalise | Ambient background varies by about 0.1% of the contrast |
| Smooth | The signal is already near-binary. Smoothing would blur the edges we need to read |

The code for all three is written and works — it sits behind config flags. Switching smoothing on changes the output and the change is recorded in `meta.json` as `smooth(window=3)`. They are off for *this* dataset, not deleted.

---

## 3. What Came Out

| Video | Lamps | Frames kept | Seconds | Samples per lamp |
|---|---|---|---|---|
| 1LED | 1 | 27,856 of 30,058 | 107.1 | 27,856 |
| 2LEDs | 2 | 17,195 of 21,157 | 66.1 | 17,195 |
| 3LEDs | 3 | 11,466 of 13,057 | 44.1 | 11,466 |
| 4LEDs | 4 | 8,609 of 11,033 | 33.1 | 8,609 |

**10 signals, 130,000 samples in total**, in about 130 seconds of runtime.

Every signal spans 1 to 253 in brightness, so the on/off gap survives the whole pipeline. See `fig_signals.png`.

### A bug the plot caught

The first version of the figure showed roughly 200 flat frames at the start of **every** signal — about 0.8 seconds of dead lead-in that the trim was supposed to remove.

The cause: the trim found the first one-second window containing enough activity and started there. But that window *begins* up to a second before the transmission does. It was returning the start of the window instead of the start of the signal.

Fixed by stepping forward to the first lit frame inside that window. All ten signals now begin on the first lit frame, with zero dead frames.

This was only visible by plotting the output. The numbers looked fine — the trim was cutting thousands of frames and reporting sensible durations.

---

## 4. Determinism

Required, and checked three ways.

| Check | Result |
|---|---|
| Same config, two runs in one process | 10 of 10 signals byte-identical |
| Same config, two **separate** process runs | 10 of 10 signals byte-identical |
| Changed config (smoothing on) | Output changes, and the change is recorded |

The last one matters as much as the first two. A pipeline that gives identical output no matter what you ask it to do is not deterministic — it is ignoring its settings.

### The one random step

Finding the lamps uses k-means, which starts from randomly chosen centres. Left alone it can give slightly different groups each run, and therefore different boxes and different signals.

Fixed by seeding OpenCV's generator from `random_seed` in the config before every call. The seed is recorded in `meta.json`, so a run can be reproduced from the file alone.

### What each run records

`signals/<video_id>/meta.json` holds:

- the full resolved config, not a reference to it
- the video's SHA-256, so a swapped file is detectable
- a SHA-256 of each signal's numbers
- trim points, lamp boxes, pixel counts, fill ratios
- pipeline version, git commit (flagged `-dirty` on uncommitted code)
- Python, OpenCV and NumPy versions
- runtime

That is enough to answer "where did this signal come from?" without guessing.

---

## 5. Where This Leaves Us

**Done:** every video reduced to per-lamp brightness signals, saved, fingerprinted, reproducible from a config file.

**Deliberately not done:** no bits. Day 10 found that the run lengths in the video do not match a plain 92 bits-per-second stream — runs of 1 and 4 frames make up 22.6% of the data and should be impossible at that rate. Decoding now would produce a bitstream we have no way to check and reason to doubt.

The config records `bits_per_second: 92.0` with a comment pointing at that finding, so the decoding step inherits the doubt rather than treating the number as settled.

**Still blocking (unchanged from Day 09 and 10):**

1. The transmitted bits, for at least one video.
2. The format above the raw bits — preamble, line coding, anything.
3. Whether 92 bps is the payload rate or the light's switching rate.

**Next, once those are answered:** the signals are already saved, so the decoder can be developed and re-run against them without touching a video again. That is the point of splitting the pipeline here.

---

## 6. Files

| File | What it is |
|---|---|
| `occ_pipeline.py` | The pipeline. Five stages, one CLI, `--verify` for the determinism check |
| `configs/preprocess_v1.yaml` | Every setting, with the reason for each written next to it |
| `signals/<video>/lamp*.npy` | One float32 brightness value per frame, per lamp |
| `signals/<video>/meta.json` | Resolved config, boxes, trims, fingerprints, versions |
| `signals/index.json` | One line per video: lamp count, frames kept, signal fingerprints |
| `fig_signals.png` | The first two seconds of all ten signals |
