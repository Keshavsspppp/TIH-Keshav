# Day 07 — Dataset Inspection

**Project:** Optical Camera Communication (OCC) Video Message Decoding

**What this covers:** keep an untouched copy of the supplied data, look at everything in it, find what is missing or broken or repeated, and produce first-look numbers and pictures — **without changing anything**.

**What is delivered:**

| File | What it does |
|---|---|
| `preserve_raw.sh` | Copies the supplied dataset into `data/raw`, fingerprints every file, and locks the folder |
| `inspect_dataset.py` | Reads every video and writes the manifest, the figures and the report |
| This file | The rules: what we check, what each number means, and what we are not allowed to do yet |

Both scripts have been **run and tested** on a made-up dataset with deliberate faults built in. What they caught is written up in §7.

---

## 1. Keep an Untouched Copy

This is the first task and the one that cannot be undone if we get it wrong.

### The rule

`data/raw/` is **read-only**. No script writes there. Not the inspection script, not the pipeline, not us by hand. Every later step reads from `data/raw/` and writes somewhere else.

### How to do it

```bash
bash preserve_raw.sh /path/to/the/supplied/dataset
```

This copies the files in, writes a `SHA256SUMS` file holding a fingerprint of every file, and then removes write permission from the whole folder.

Later, before any run that matters:

```bash
bash preserve_raw.sh --verify data/raw
```

This re-checks every file against its fingerprint and tells us if anything changed.

### The honest limit

Read-only stops ordinary accidents. It does **not** stop an admin user, who can still overwrite the files. So the fingerprint file is the real protection, not the permission bit. Two habits follow from that:

1. Run `--verify` before any run whose numbers we will report.
2. Keep a second copy of the dataset somewhere off this machine.

The script also refuses to run if `data/raw` already has files in it, so a second run cannot quietly overwrite the first copy.

---

## 2. What We Look At

Run the inspection with:

```bash
python inspect_dataset.py --raw data/raw --out reports/day07 --truth data/ground_truth
```

It reads each video **once** and collects everything in that single pass. Outputs go to `reports/day07/`:

| Output | What it holds |
|---|---|
| `MANIFEST.csv` | One row per video. The main table |
| `per_video/<id>.json` | Every number measured for that one video |
| `figures/<id>_*.png` | Four pictures per video (see §5) |
| `INSPECTION_REPORT.md` | The written report |

### Files and metadata

| Check | Why it matters |
|---|---|
| SHA-256 of each file | Lets us spot a swapped or edited file later |
| Codec, pixel format, resolution | Affects ROI size and compression damage |
| Frame rate, from two different fields | See below |
| Duration and file size | Basic sanity |

**The frame-rate check is the important one.** The tool reads the real time of each frame for the first ten seconds and measures whether those times are evenly spaced. If they are not, the video has a **variable frame rate**, which means the frames are *not* evenly spaced in time. Treating them as evenly sampled would break the timing recovery for a reason that has nothing to do with our method. Better to know this on day one than in week three.

### Frames

| Check | Why it matters |
|---|---|
| Frames counted by reading, vs the count in the file header | Headers often lie. We trust the counted number |
| All-black frames | Dropped or corrupted frames |
| How bright the light actually gets | See "clipping" in §4 |
| Where in the picture things change | This is how we find the light (§3) |

### Labels and targets

The tool looks for a truth file named after each video (`vid_003.json` or `vid_003.txt`) and reports:

- how many videos have truth at all,
- how many bits each truth holds,
- **the share of 1s versus 0s in each one.**

That last number matters more than it looks. If a video's true message is 90% ones, a decoder that always guesses "1" scores 90% and looks excellent while being useless. The report flags this automatically and says to compare against an always-guess baseline.

---

## 3. Finding the Light Without Touching Anything

The tool builds a **variance map**: for each pixel, how much does it change across the video? The blinking light changes most, so it stands out. The biggest high-change blob becomes the ROI, and the brightness inside it becomes our first-look signal.

This is only for looking. Nothing is cropped or saved as a new video.

**One design point that came out of testing, and it matters beyond this script.** The frames used for the variance map must be spread across the **whole** video, not taken from the start. If the message begins with a long run of the same bit, the opening frames show no change at all, and a variance map built from them wrongly concludes that nothing blinks. One of our test videos started with 54 ones in a row and was marked "nothing blinks" until this was fixed.

**M1 has the same weakness.** The ROI step in `DAY_06.MD` §2.2 says "over the first `K` frames". That should be changed to "over `K` frames spread across the whole clip" before it is written. This is a free bug fix, found before we wrote a line of the pipeline.

---

## 4. Checks for Broken, Missing and Repeated Data

### Missing or invalid

| Problem | How it is caught |
|---|---|
| File does not open | Video reader fails |
| Video has no frames | Counted frames is zero |
| Too short to use | Fewer than 30 frames |
| Dropped or corrupt frames | All-black frames counted |
| Header disagrees with reality | Header frame count vs counted frames |
| Frames not evenly spaced in time | Timestamp jitter above 2% |
| **Nothing actually blinks** | See below |

**"Nothing blinks" needs care**, because a video of pure noise will still give you an ROI and still split into two brightness groups — noise splits too. So the tool measures how much more the busiest pixel changes than a typical one. On a real blinking light this ratio is in the hundreds or thousands. On noise it is under 2. Anything under 3 is marked red.

### Clipping (the light is too bright)

If the light sits at the top of the brightness range, the signal is flat-topped and the exact level is lost. On/off still works, so this is a warning, not a failure — but it kills any idea of reading more than one bit per flash, and it means our brightness statistic should step away from the clipped pixels.

The tool measures the brightest level the light actually reaches. At or above 250 out of 255, it flags clipping.

### Duplicates

Two checks:

1. **Exactly the same file** — same SHA-256. Catches a copied or renamed video.
2. **The same blinking pattern** — the brightness-over-time signals of two videos match above 0.98.

The second check deliberately does **not** compare how the frames look. In this dataset every video looks the same: a small bright light on a dark background. During testing, an appearance-based check flagged completely unrelated videos as duplicates. What actually makes two OCC clips duplicates is that the light blinks the same way, so that is what we compare.

Why this matters: if the same clip ends up in both DEV and TEST, the final number is worthless.

---

## 5. First-Look Statistics and Pictures

No cleaning. These are all measurements of the raw signal.

### Four pictures per video

| Picture | What to look for |
|---|---|
| Variance map | One bright spot means one clear transmitter. Several spots mean something else in the scene is also flickering |
| Brightness over time | A square-ish up-down pattern means the blinking is being sampled well. A smooth wobble means we are undersampling it |
| Histogram | Two humps means a clean on/off split. One hump means the two levels overlap |
| Rhythm (frequency) | One sharp spike means a steady blink rate. A flat spread means no clear rhythm |

### Two numbers

**On/off split score.** How cleanly the brightness falls into two groups, measured in units of their own spread.

| Score | Reading |
|---|---|
| Above 3 | Clean. A simple threshold should work |
| 1 to 3 | Workable, but the levels overlap. This is where the adaptive method earns its place |
| Below 1 | The two levels are not separable from brightness alone |

**Strongest rhythm.** The main repeating rate in the brightness, in cycles per second, plus how far that peak stands above the rest.

Treat this as a hint only. If the light blinks faster than the camera samples, this number is an **alias** — a real reading of a false rate. It is still useful, because a strong clear peak tells us there is something periodic to recover, even when the value itself is wrong.

---

## 6. What We Do Not Do Yet

Day 07 is looking, not fixing. None of the following happens now:

- No cropping, resizing or re-encoding
- No dropping of bad frames or bad videos
- No filtering, smoothing or normalising saved to disk
- No deleting of anything, including files marked red
- No filling in of missing labels
- No choosing which videos go in DEV and which in TEST *(that comes next, but the verdicts from today are the input to it)*

A video marked red stays in the folder with its reason written down. Quietly dropping data and then reporting good numbers is the thing this whole protocol exists to prevent.
