# 1. Problem Statement, Rewritten

This is an **Optical Camera Communication (OCC) decoding problem**: a light source (the "transmitter") blinks according to an On-Off Keying (OOK) scheme, where "on" and "off" intervals encode binary 1s and 0s. A standard rolling-shutter or frame-based camera records this blinking as a video. Because the camera samples the light at its own frame rate (not synchronized to the transmitter's bit clock), the recorded video only contains an *indirect*, noisy, and possibly aliased trace of the original bitstream — visible as frame-to-frame brightness variation in the region where the transmitter appears.

The task is to build a fully offline, software-only pipeline that takes these raw videos and reconstructs the original binary sequence and the human-readable message it encodes — without touching any camera or transmitter hardware. The work is explicitly scoped as a signal-processing / computer-vision / light ML problem, not a hardware or embedded systems project: everything happens after the video already exists.

# 2. Inputs and Target Output

## Inputs

- Raw video files (frame sequences) containing a visible OOK transmitter, provided by faculty before end of Week 1.
- Implicitly, per-video metadata may accompany these (frame rate, resolution, possibly transmitter location or symbol rate — to be confirmed).
- The "signal" of interest is not the video itself but the **derived scalar time series**: per-frame light intensity in the transmitter's region of interest (ROI), sampled at the camera's frame rate.

## Target Output

- The **decoded binary sequence** (the demodulated bitstream, recovering the original OOK symbols).
- The **decoded message** (whatever human-readable or structured content those bits represent, after any framing/parity/encoding is stripped).
- Supporting outputs for evaluation: bit error rate (BER) where ground truth exists, synchronization robustness, and runtime.

# 3. End-to-End Pipeline

I've laid it out as a diagram above; the stages in prose:

1. **Video Input** — ingest raw OOK video files.
2. **Frame Extraction** — decode video into a per-frame image sequence (OpenCV).
3. **Transmitter Localization** — detect/select and track the ROI containing the transmitting light source across frames (may drift, especially with a handheld camera).
4. **Intensity Signal Extraction** — reduce each frame's ROI to a scalar (mean/max pixel intensity or a chosen channel/statistic), producing a 1-D time series.
5. **Signal Preprocessing** — denoise (e.g., smoothing/filtering), normalize for ambient light and exposure changes, detrend for slow drift.
6. **Symbol Synchronization** — recover the transmitter's bit clock/symbol boundaries from the sampled signal, since camera frame rate and transmitter symbol rate are generally not aligned (this is likely the hardest step given rolling-shutter / undersampling effects).
7. **Threshold / Classification** — convert each symbol interval into a 0/1 decision, via a fixed threshold baseline, an adaptive threshold, a classical signal-processing method, or a lightweight ML classifier (where labels exist).
8. **Decoding and Evaluation** — reassemble bits into frames/packets (handling preambles, parity, or framing if present), decode to the final message, and compute decoded-message correctness, BER (if ground truth available), synchronization robustness, and execution time.

# 4. Success Criteria

As stated in the brief, translated into concrete terms:

- **Decoded-message correctness**: exact or near-exact match between reconstructed message and ground truth, across the provided video set.
- **Bit error rate (BER)**: low BER against reference truth where available.
- **Synchronization robustness**: symbol timing recovery holds up despite frame-rate/symbol-rate mismatch, jitter, or partial occlusion/motion.
- **Sensitivity/robustness**: performance doesn't collapse under reasonable variation in ROI selection, smoothing parameters, threshold choice, and timing assumptions — documented, not just hoped for.
- **Execution time**: pipeline runs end-to-end on a video in reasonable, reported time (useful for baseline-vs-advanced comparisons).
- **Reproducibility**: pipeline is independently re-runnable from raw video to decoded message, with versioned intermediate data and a documented experiment log.

# 5. Clarifying Questions / Assumptions Needing Confirmation

1. **Frame Rate vs. Symbol Rate**: What is the camera's frame rate, and what is the transmitter's OOK symbol rate (bits/sec)? Is the ratio fixed and known, or does it vary per video/dataset?

2. **Ground Truth Availability**: For how many videos is the true transmitted bitstream/message actually provided, versus needing to be inferred? BER can only be computed where reference truth exists — how much of the dataset supports this?

3. **ROI Specification**: Is the transmitter's location fixed per video (static frame), or does it move (handheld camera / moving transmitter), requiring active tracking rather than one-time selection?

4. **Framing/Protocol Structure**: Is there a known packet structure (preamble, start/stop bits, parity/CRC, Manchester or NRZ-style encoding) layered on top of raw OOK, or is it a plain, unframed bitstream?

5. **Encoding Scheme Details**: Is it strictly OOK (binary on/off), or could there be multi-level intensity modulation in some videos? Is a "1" represented by "on" or could polarity vary by dataset?

6. **Rolling Shutter vs. Global Shutter**: Were the videos captured with rolling-shutter cameras (which can produce banding patterns encoding *sub-frame* information), or global-shutter (one intensity sample per frame, coarser)? This materially changes the achievable bit rate and recovery method.

7. **Dataset Diversity and Difficulty Axes**: Do videos vary systematically along axes like distance, ambient lighting, resolution, compression (codec/bitrate), or camera motion? Should these be treated as labeled subgroups for the required robustness/failure analysis?

8. **Labels for the ML-Assisted Classifier**: What form do labels take when "labels permit" an ML symbol classifier — per-frame bit labels, per-video message strings, or something else? This determines whether a supervised classifier is even feasible.

9. **File Formats and Codecs**: What video container/codec is used (e.g., MP4/H.264), and could compression artifacts (temporal/quantization) distort the intensity signal in ways that need explicit correction?

10. **Deliverable Format for "Decoded Message"**: Is the message plain text, a fixed-length code, or something requiring a defined character encoding after bit reconstruction — and is there a specified end-of-message marker?