# Day 04 — Dataset Schema, Structure and Risk Assessment

Written **before** the faculty dataset arrives. Purpose: fix the expected structure, the metadata that must exist, the split rules, and the risks to check for — so that dataset inspection on arrival is a checklist run against a stated expectation, not an improvised look-around. Every "expected" below is a hypothesis to be confirmed or corrected on Day 05 (dataset inspection), and any mismatch is itself a finding worth recording.

---
  
# 1. Expected Files, Columns, Labels and Targets

## 1.1 Expected directory layout

The raw drop is preserved unmodified (brief, section B: *"Preserve an unchanged raw copy"*). Everything derived lives beside it, never inside it.

```
data/
  raw/                     # immutable — read-only after first copy, checksummed
    videos/                # faculty-provided OOK video files
    labels/                # ground truth, if supplied (see 1.3)
    README_from_faculty.*  # any accompanying notes/metadata sheet
  interim/                 # per-video extracted signals (see 1.4)
  processed/               # split-assigned, versioned feature/label tables
```

## 1.2 Expected raw inputs

| Item | Expected form | Why it matters | Confirm on arrival |
|---|---|---|---|
| Video files | `.mp4` / `.avi` / `.mov`, or a folder of frame images per recording | Container + codec drives whether compression distorts intensity | Yes |
| Codec | H.264 / MJPEG most likely | Inter-frame (H.264) compression can smear the temporal signal; MJPEG is intra-only and safer | Yes |
| Frame rate | 30 or 60 fps, constant | The sampling clock of the whole problem | Yes — and check for **variable** frame rate |
| Resolution | 720p–1080p | Sets ROI pixel count, hence intensity SNR | Yes |
| Duration / frame count | Tens to a few hundred frames per message | Bounds how many symbols exist per video | Yes |
| Colour | 3-channel BGR (OpenCV default) | Channel choice is a preprocessing decision; a colour-shift scheme would change everything | Yes |
| Bit depth | 8-bit per channel | Clipping/saturation behaviour at the LED core | Yes |

## 1.3 Expected labels / targets

The prediction target is stated in the brief: **the transmitted binary sequence and the decoded message**. The open question is at what granularity that truth is supplied.

| Label granularity | Form | Enables | Assumed availability |
|---|---|---|---|
| Per-message (per video) | one string + its bitstream, e.g. `video_07 → "HELLO" / 0100100001...` | Message-correctness metric; end-to-end BER after alignment | **Most likely** — assume this is the baseline case |
| Per-symbol | ordered bit list with symbol indices | Direct BER without alignment; supervised symbol classifier | Possible |
| Per-frame | a bit (or "boundary/don't-care") label for every frame index | Supervised per-frame classifier, the strongest ML case | **Unlikely** — do not design around it |
| None | videos only | Unsupervised decode only; no BER, no ML | Contingency — must have a plan (see 1.6) |

This resolves Blocker #4 from the Day 03 deck. The ML-assisted arm of the study (shortlist method 3) is feasible only at per-symbol granularity or finer; at per-message granularity it survives only if bits can be reliably back-aligned to symbol windows, which is itself a decoding assumption and must be flagged as such rather than silently used to manufacture labels.

## 1.4 Derived signal table (the actual modelling unit)

The video is the input; the *modelling* unit is the extracted 1-D intensity series. One tidy table per video in `interim/`, one row per frame:

| Column | Type | Definition | Notes |
|---|---|---|---|
| `video_id` | str | Stable key back to the raw file | Never a filename that could be renamed |
| `frame_idx` | int | 0-based, monotonic, no gaps | Gaps = dropped frames, a finding not a nuisance |
| `timestamp_s` | float | Presentation timestamp from the container | Do **not** assume `frame_idx / fps`; check against it |
| `roi_x, roi_y, roi_w, roi_h` | int | ROI box for this frame | Constant if static ROI; varying if tracked |
| `intensity_mean` | float | Mean pixel value over ROI | Primary signal |
| `intensity_max` | float | Max pixel value over ROI | Robust to ROI over-sizing, sensitive to saturation |
| `intensity_std` | float | Std over ROI | Cheap sanity/occlusion signal |
| `sat_frac` | float | Fraction of ROI pixels at 255 | Detects clipping, which destroys amplitude information |
| `roi_conf` | float | Detector/tracker confidence | For rejecting frames where the ROI was lost |

Rationale for carrying mean, max, std and `sat_frac` rather than mean alone: the sensitivity study required by the brief varies ROI choice, and these are exactly the statistics that respond differently to a badly chosen ROI. They cost nothing to compute in the same pass.

## 1.5 Per-video metadata (one row per video, `interim/video_manifest.csv`)

This manifest is the backbone of both the split design (§3) and the robustness analysis (brief, section G). Fields marked **derived** are computed by us and must never be silently confused with faculty-supplied truth.

| Field | Source | Purpose |
|---|---|---|
| `video_id`, `raw_path`, `sha256` | derived | Immutability + reproducibility |
| `fps_declared`, `fps_measured` | container / derived | A mismatch invalidates every timing assumption |
| `n_frames`, `width`, `height`, `codec`, `bitrate` | container | Quality/compression grouping |
| `symbol_rate_bps` | **faculty** | Unknown as of Day 03 — Blocker #1 |
| `fps_to_symbol_ratio` | derived | The single most important number in the project |
| `message_text`, `bitstream` | **faculty** | Ground truth |
| `n_bits` | derived | Cross-check: `n_bits` vs `n_frames / ratio` must be consistent |
| `encoding_scheme` | **faculty** | NRZ / Manchester / framed — Blocker #2 |
| `polarity` | **faculty** or derived | Is "light on" = 1 or 0? Cannot be assumed |
| `roi_mode` | derived | `static` / `moving` — Blocker #3 |
| `capture_condition` | faculty or derived | distance, ambient light, indoor/outdoor, camera motion |
| `session_id` / `capture_batch` | faculty or inferred | **Critical for splitting** — see §3 |
| `transmitter_id` | faculty or inferred | Which physical LED/device |

If `session_id` is not supplied, it must be reconstructed (file timestamps, resolution/codec fingerprints, background scene similarity) and the reconstruction documented as an assumption. Splitting without it is the single largest leakage risk in this project (§2.5).

## 1.6 Contingency if the dataset contradicts these expectations

- **No ground truth at all** → BER and message-correctness become unavailable for those videos; fall back to self-consistency metrics (decode stability across ROI/threshold perturbations, agreement between the three methods) and state plainly that absolute accuracy is unmeasured. Do not invent truth by declaring one method's output the reference.
- **Only one or two videos** → the sensitivity study becomes the primary contribution, and a held-out *test* split is not statistically meaningful; report per-video results with explicit "n is too small for generalisation claims".
- **Rolling-shutter stripe data rather than per-frame blink** → the intensity-per-frame table in §1.4 is the wrong unit; the row-level signal is. This is a pipeline fork, not a parameter change, and must be detected on Day 05, not week 3.

---

# 2. Likely Data-Quality Risks

## 2.1 Missing / invalid data

- **Dropped or duplicated frames** — codec or capture hiccups put a gap in the sampling clock; a decoder that assumes uniform spacing silently shifts every subsequent bit. Detect via non-uniform `timestamp_s` deltas, not frame count alone.
- **Variable frame rate (VFR)** — phone cameras often record VFR while declaring a constant nominal fps. This breaks `frame_idx / fps` timing outright.
- **Truncated / corrupt videos** — last frames unreadable; OpenCV returns `ret=False` mid-stream and a naive loop just stops early without complaint.
- **ROI loss** — transmitter leaves frame, is occluded, or the detector fails. Produces plausible-looking but meaningless intensity values. Needs an explicit "no valid ROI" state, not a zero.
- **Saturation / clipping** — an overexposed LED core reads 255 for both bright and brighter, collapsing amplitude. Detected by `sat_frac`; mitigated by measuring the halo rather than the core.
- **Missing metadata** — symbol rate or encoding not supplied. Not a nuisance field: without it, symbol synchronization becomes blind estimation, which materially changes the difficulty of the project and must be raised at mentor review rather than absorbed.

## 2.2 Annotation risks

- **Off-by-one / alignment ambiguity** — does the bitstream start at frame 0, at the first "on" frame, or after a preamble? An unstated convention makes BER wrong by a constant shift while looking like a decoder failure.
- **Polarity ambiguity** — an inverted bitstream gives ~100% BER while the decoder is in fact working perfectly. Always evaluate both polarities and report which was assumed.
- **Bit order** — MSB-first vs LSB-first when packing bits into characters; and the character encoding (ASCII vs 5-bit/custom) for the message.
- **Framing not documented** — preamble, start/stop bits, parity, CRC, or a DC-balanced line code (Manchester) sitting above the raw OOK. If ground truth is the *payload* and the video carries the *encoded* stream, raw bit-by-bit comparison is invalid.
- **Transcription errors in the message strings** — case, whitespace, trailing terminators. Define string comparison exactly (exact match after strip, and separately a character-level distance).

## 2.3 Imbalance

- **Class (bit) imbalance** — messages in natural text are not 50/50 in bits; a classifier can score well by exploiting the prior rather than reading the light. Always report BER against a majority-class baseline, and report 0→1 and 1→0 error rates separately.
- **Run-length imbalance** — long runs of identical bits stress clock recovery far more than alternating bits, and are rarer. Accuracy averaged over all bits hides this; stratify error by run length.
- **Condition imbalance** — most videos captured in one lighting/distance condition and a couple in others. A "robustness" claim built on two videos in the hard condition is not a robustness claim.
- **Message-length imbalance** — long videos dominate a pooled per-bit metric. Report per-video metrics and macro-average across videos, not only a pooled bit count.

## 2.4 Temporal risks

- **Within-video autocorrelation** — consecutive frames are not independent samples. Any random shuffle of frames into train/test is invalid (see §3).
- **Slow drift** — auto-exposure, auto-gain, auto-white-balance and ambient change move the DC level across a video, so a threshold fitted on early frames fails on later ones. This is the motivation for the detrending stage already in the pipeline.
- **Rolling-shutter sub-frame structure** — one frame may contain several symbols as stripes; per-frame averaging destroys them. Must be checked visually on arrival.
- **Aliasing** — if the symbol rate is near or above the Nyquist limit of the frame rate, the true sequence is not recoverable from per-frame means at all, however good the classifier. Compute `fps_to_symbol_ratio` first; it decides whether the project is a decoding problem or an aliasing problem.
- **Inter-frame gaps** — the camera does not expose continuously; symbols falling in the blanking interval are simply never observed. A known, structural cause of unrecoverable bits.

## 2.5 Leakage risks

Ordered by how likely they are to silently inflate results here:

1. **Same-video leakage** — frames or symbol windows from one video split across train and test. The model then learns that video's specific DC level, LED position and noise floor. **Split unit must be the video, never the frame or symbol.**
2. **Same-session / same-scene leakage** — different videos recorded back-to-back in the same setup share exposure, background and distance. Splitting by video but not by session still leaks the condition.
3. **Same-message leakage** — the same message text recorded several times; a classifier can memorise the bit sequence rather than decode it. Group by message content as well as by video.
4. **Tuning-on-test** — choosing ROI size, smoothing window and threshold by looking at test scores. The brief explicitly warns against this ("select the final method using validation evidence rather than test-set trial-and-error"). All sensitivity sweeps run on validation only.
5. **Preprocessing leakage** — computing normalisation statistics (mean/std, threshold, detrend baseline) over the whole dataset including test. Statistics must be fitted per-video or on train only.
6. **Ground-truth leakage through synchronization** — using the known bitstream to find symbol boundaries and then reporting BER on those boundaries. This makes any decoder look excellent. Synchronization must be derived from the signal only; if truth-aided sync is used, it is an oracle upper bound and must be labelled as one.

---

# 3. What a Correct Split Must Preserve

## 3.1 The split unit is the video (grouped), not the frame

Frames within a video are temporally correlated and share a capture setup, so an i.i.d. row-level split is invalid. The correct construction is a **grouped split** with the group key being, in decreasing order of preference: `session_id` > `video_id` > `message_text`. Where session information exists, group by session; grouping by video alone is the minimum acceptable standard and its residual leakage must be stated.

## 3.2 What must be preserved

| Property | Requirement |
|---|---|
| **Group integrity** | No video (and ideally no session) contributes to more than one split. |
| **Condition coverage** | Each split contains at least one video from each capture condition present (distance / lighting / motion). If a condition has only one video, it goes to test only if the study needs an unseen-condition measurement, and that choice is documented. |
| **Difficulty spread** | Test is not accidentally all-easy or all-hard. Stratify on the observable difficulty proxies: `fps_to_symbol_ratio`, ambient level, `sat_frac`, ROI size. |
| **Bit-class balance** | Roughly comparable 0/1 proportions across splits; report the actual proportions rather than assuming. |
| **Temporal order within a video** | Never shuffled. A video is decoded as a sequence, start to finish. |
| **Message disjointness** | The same message text does not appear in both train and test. |
| **Determinism** | Fixed seed, split assignment written to `processed/splits.csv` and version-controlled, so any result can be reproduced exactly. |
| **Honest reporting of size** | With a small video count, report per-video results and treat the aggregate as indicative, not as a generalisation estimate. |

## 3.3 Practical scheme

- **Validation** is where all tuning happens: ROI size/position, smoothing window, threshold rule, timing offset — i.e. the entire sensitivity study of the brief.
- **Test** is touched once, at the end, with the method already chosen.
- If the dataset is too small for three groups (a real possibility), use **leave-one-video-out cross-validation** over train+validation, keep one or two videos fully held out as test if at all possible, and state explicitly that the split is small-sample. LOVO is the honest choice here; it preserves group integrity and uses every video, which a 60/20/20 split of eight videos does not.
- Threshold and normalisation parameters are fitted **per video from that video's own signal**, which is both physically correct (each capture has its own DC level) and leakage-free. Any parameter shared across videos is fitted on train only.

---



# 4. Questions for the Next Mentor Review

Carried forward from Day 03 blockers, now sharpened into what would actually unblock work:

1. What is the symbol rate per video, and is `fps_to_symbol_ratio` fixed across the dataset? (Blocks C1–C3, and determines whether the problem is recoverable at all.)
2. At what granularity is ground truth supplied — message string, bitstream, or per-symbol bits? (Blocks D1 and the entire ML arm.)
3. Is there framing above the raw OOK — preamble, parity, Manchester coding? Is the supplied truth the payload or the encoded stream? (Blocks D5–D6 and makes BER either valid or meaningless.)
4. Does "light on" mean 1, and is that consistent across all videos? (Blocks D4.)
5. Were the videos captured in distinguishable sessions/conditions, and can that grouping be supplied? (Blocks F1 and the whole robustness analysis.)
6. How many videos are there, and how many have ground truth? (Decides whether a three-way split or leave-one-video-out is the honest methodology.)
