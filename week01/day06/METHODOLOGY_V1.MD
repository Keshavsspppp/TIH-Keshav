# Methodology V1

**Project:** Optical Camera Communication (OCC) Video Message Decoding
**Version:** V1 — end of Day 06, before the dataset

> **Provenance (2026-09-11).** This file is cited by `DAY_06.MD`, `EXPERIMENT_PLAN_V2.MD` (§3 checklist, §6.3 split rule) and `../day07/DAY_07_FINDINGS.MD` (§3, §6), but was never committed. It has been **reconstructed** from the Day 04–06 documents it summarises — nothing here is new: every rule below is quoted or condensed from `../day04/DAY_04.MD`, `../day05/DAY_05.MD`, `DAY_06.MD` and `EXPERIMENT_PLAN_V2.MD`, with the source given per section. Section numbers match the citations. §9 records what the data did to each rule on Day 07 and after; §10 is the mentor-corrections record, which is empty because none were recorded.

---

## 1. Problem and targets

*(from `../day01/PROBLEM_STATEMENT.MD` §1–2, `../day03/DAY_03.MD`)*

A lamp blinks in on-off keying; a frame-based camera records it at a frame rate not synchronised to the bit clock. **Input:** raw video; the modelling unit is the per-frame brightness of the lamp region. **Target:** the transmitted bit sequence and the message it encodes.

Research question: *how accurately and robustly can a software-only pipeline recover the OOK message from unsynchronised video, classical signal processing against a lightweight ML symbol classifier, across variation in ROI, ambient/exposure conditions and symbol-timing assumptions?*

## 2. Literature position

*(from `../day02/DAY_02.MD`, Day 03 deck slide 3)*

Ten papers reviewed, six systems tabulated (`../day02/methods.png`). Prior OCC systems mostly assume synchronised or specialised modulation (UFSOOK, UPSOOK, rolling-shutter stripes); this project assumes generic OOK with an unknown symbol/frame-rate ratio. Ambient light, auto-exposure and distance are the dominant reported error sources, which motivates the sensitivity study (§5.3). None of the reviewed systems reports how far its settings can be off before it fails — that gap is the project's contribution.

## 3. Data-readiness checklist (E00)

*(from `EXPERIMENT_PLAN_V2.MD` E00, `../day04/DAY_04.MD` §1.2, §1.5, §2)*

Run on the day the data lands, before anything else. Every video gets a green / amber / red verdict; no video is excluded silently.

| # | Check | How | Why |
|---|---|---|---|
| 1 | Inventory | Every file listed with `video_id`, path, size | Nothing missing, nothing extra |
| 2 | SHA-256 | Fingerprint every raw file; write `SHA256SUMS` | Catch a swapped or edited file later |
| 3 | Frame rate | Read it two ways (container fields) and compare with frames ÷ duration | The sampling clock of the whole problem |
| 4 | Fixed or variable frame rate | Timestamp spacing over the first seconds; jitter > 2 % = variable | Variable spacing breaks every timing assumption |
| 5 | Real frame count | Count by reading, compare with the header | Headers lie; dropped/truncated frames shift every later bit |
| 6 | Resolution, codec, pixel format | Container | ROI pixel count; inter-frame compression can smear the signal |
| 7 | Saturation | Peak lamp level; share of pixels at 255 | Clipping destroys amplitude information |
| 8 | Stripes | Look for rolling-shutter banding across the lamp | Decides per-frame vs per-row decoding — a pipeline fork |
| 9 | Light visibility | Variance map; is there a blinking region at all, how strong | A video with nothing blinking is red |
| 10 | Movement | Does the bright region move across the clip | Decides whether ROI tracking is needed |
| 11 | Ground-truth format | Truth files present? per message / per symbol / per frame? ones share? | Decides BER, the ML branch and the majority-class baseline |
| 12 | Duplicates | Same hash; same blink pattern | A duplicate in DEV and TEST makes the final number worthless |

Output: `data/raw/MANIFEST.csv` fully filled plus the verdicts in the log. **Pass mark: every video has a verdict.**

## 4. Preprocessing pipeline

*(from `DAY_06.MD` §1)*

Eight stages, each saving its output so any one can be re-run alone: read frames → find the light (variance map → ROI → tracker) → brightness per frame → clean (detrend, normalise, smooth) → bit timing (frames per bit + start offset) → 0/1 decision → bits to message → score. `data/raw/` is read-only. Stages 1–3 are saved once per video; stages 4–8 per run.

## 5. Methods and the project's own experiment

*(from `DAY_06.MD` §2)*

- **M0 baseline** — fixed ROI, mean brightness, no cleaning, `sps = fps / symbol_rate` from config, midpoint threshold, majority vote per bit.
- **M1 main method** — variance-map ROI + CSRT tracker, brightest-*p*% mean, detrend, rolling normalise, short smooth, `sps` from autocorrelation/FFT, phase by widest on/off separation, rolling-median threshold with hysteresis, preamble search.
- **M2 ML classifier** — only if labels exist (Gate G4): window around each bit centre → logistic regression, then RBF SVM, then a small 1-D CNN; stop at the first that beats M1. Changes only the decision step.
- **5.3 Project-specific experiment** — measure how far ROI, cleaning, threshold and timing can be wrong before decoding fails; report working ranges, not one accuracy number; compare how M1 and M2 degrade.

## 6. Data roles and split strategy

*(from `DAY_06.MD` §4, `../day04/DAY_04.MD` §2.5, §3)*

### 6.1 Roles

| Role | What | Use |
|---|---|---|
| FAKE | Our own synthetic OOK videos with known bits | Unlimited; the only guaranteed ground truth |
| DEV | Real videos we may tune on | All sensitivity sweeps (E05–E11), all model selection |
| TEST | Real videos opened once, at the end | The reported numbers; every opening logged; ≤ 2 openings (E17) |

### 6.2 Leakage rules

The split unit is the video (or the session, if known), never the frame — frames are autocorrelated. No video in two roles. Same message text not in both DEV and TEST. Normalisation and threshold statistics fitted per video or on DEV only. Synchronisation derived from the signal only; truth-aided sync is an oracle bound and is labelled as one. All tuning on DEV; TEST touched once.

### 6.3 Role-assignment rule

Immediately after E00, before any tuning:

1. Group videos by capture condition (session, distance, lighting, lamp count) as far as the metadata allows.
2. Hold out **one or two videos as TEST**, chosen so that every condition present in TEST also appears in DEV; if a condition has only one video it stays in DEV, unless an unseen-condition measurement is explicitly wanted and documented.
3. Everything else is DEV; within DEV, use leave-one-video-out for any model selection that needs held-out data.
4. Write the TEST `video_id`s in `EXPERIMENT_LOG.MD` with the date. They do not change afterwards.
5. If there are too few videos for step 2 to hold, say so, report per-video results, and treat any aggregate as indicative only (`../day04/DAY_04.MD` §1.6, §3.3).

## 7. Evaluation

*(from `DAY_06.MD` §3)*

Message correctness (MCR, NED); BER where truth exists, with polarity and alignment offset reported; synchronisation robustness as ranges (start-offset and rate bands where BER ≤ 0.01); execution time per video and per frame, median of 3; sensitivity curves per swept setting. Every run writes `metrics.json`; tables are built from those files, never typed.

## 8. Constraints and scope

*(from the brief §4, §7; `DAY_06.MD` §7)*

Software-only, offline, four weeks, faculty dataset only, no hardware. Rolling-shutter stripe decoding out of scope unless the videos show stripes. The dataset blocks the *answers* (frame rate, bit rate, framing, labels, whether the lamp moves), not the *machinery* — every stage can be built and tested on FAKE data first.

## 9. What the data did to V1 (recorded after Day 07)

| Rule | Outcome | Where |
|---|---|---|
| §3 checklist | Run on Day 07. Manifest produced with a capped scan — corrected on Day 08 and in the audit | `../day07/DAY_07_FINDINGS.MD` §1 |
| §4 detrend / normalise / smooth | Nothing to remove (drift ≈ 0.1 % of contrast); all three measured harmful and switched off | Days 08, 09, 12 |
| §4 tracker; "first K frames" ROI | Camera static — tracker off. ROI must sample the whole clip | Days 07 §3, 08 §4 |
| §5 M2 | Never ran: no labels of any kind (Gate G4 failed) | `../day07/DAY_07_FINDINGS.MD` §5.1 |
| §5 Gate G3 | Unevaluable without ground truth; re-worded Day 07, never closed | `../day05/DAY_05.MD` §5 note |
| §6.3 split | **Cannot be applied**: four videos, four different setups, one per condition. Replaced by a within-video time split (first 30 % DEV, last 70 % TEST), proposed Day 07 §6, used Days 17–21 | `../day07/DAY_07_FINDINGS.MD` §6 |
| §7 BER, correctness | Unmeasurable on real data; measured on FAKE only | every later day |
| `sps` unknown | 260 fps measured; 92 bps is the filename's number and is not confirmed by the data | Days 10, 13 |

## 10. Mentor corrections and decisions (Day 06 review)

*Not recorded at the time.* No mentor feedback for the Day 06 review exists in the repository; the changes between Day 05 and Day 06 (`EXPERIMENT_PLAN_V2.MD` "What changed") were self-generated. Use `MENTOR_NOTES.MD` in this folder to record them if they can still be recovered.
