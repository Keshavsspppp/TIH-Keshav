# Experiment log — Day 19 tuning

Selection rule fixed before running: primary = validation BER at phase 0 (synthetic seeds 30–33, noise 8 and 80, exposure 0.3); secondary = phase tolerance. Real DEV indicators logged, not used for selection. TEST untouched.

| Run | Candidate | Settings | Val BER @ phase 0 | Val BER @ true phase | Phase tol. (bits) | DEV safe | DEV phase stab. | s |
|---|---|---|---|---|---|---|---|---|
| E19-01 | A threshold | end_margin 0.0, pct (5, 95), confident | 12.058 % | 1.321 % | 0.05 | 43.3 % | 90.4 % | 0.14 |
| E19-02 | A threshold | end_margin 0.0, pct (5, 95), nearest **←** | 6.185 % | 3.259 % | 0.30 | 34.9 % | 88.1 % | 0.08 |
| E19-03 | A threshold | end_margin 0.0, pct (5, 95), average | 6.594 % | 0.863 % | 0.32 | 40.4 % | 90.1 % | 0.12 |
| E19-04 | A threshold | end_margin 0.0, pct (10, 90), confident | 12.050 % | 1.305 % | 0.05 | 43.6 % | 90.5 % | 0.15 |
| E19-05 | A threshold | end_margin 0.0, pct (10, 90), nearest | 6.190 % | 3.255 % | 0.30 | 34.9 % | 88.1 % | 0.09 |
| E19-06 | A threshold | end_margin 0.0, pct (10, 90), average | 6.577 % | 0.863 % | 0.32 | 41.2 % | 90.1 % | 0.14 |
| E19-07 | A threshold | end_margin 0.0, pct (25, 75), confident | 12.075 % | 1.309 % | 0.05 | 45.1 % | 90.8 % | 0.15 |
| E19-08 | A threshold | end_margin 0.0, pct (25, 75), nearest | 6.190 % | 3.251 % | 0.30 | 34.9 % | 88.1 % | 0.09 |
| E19-09 | A threshold | end_margin 0.0, pct (25, 75), average | 6.590 % | 0.867 % | 0.32 | 42.5 % | 90.5 % | 0.17 |
| E19-10 | A threshold | end_margin 0.2, pct (5, 95), confident | 11.101 % | 0.571 % | 0.08 | 39.7 % | 88.8 % | 0.17 |
| E19-11 | A threshold | end_margin 0.2, pct (5, 95), nearest | 6.185 % | 3.259 % | 0.30 | 34.9 % | 88.1 % | 0.13 |
| E19-12 | A threshold | end_margin 0.2, pct (5, 95), average | 6.962 % | 0.509 % | 0.30 | 36.3 % | 87.3 % | 0.17 |
| E19-13 | A threshold | end_margin 0.2, pct (10, 90), confident | 11.088 % | 0.563 % | 0.08 | 40.2 % | 88.8 % | 0.22 |
| E19-14 | A threshold | end_margin 0.2, pct (10, 90), nearest | 6.190 % | 3.255 % | 0.30 | 34.9 % | 88.1 % | 0.1 |
| E19-15 | A threshold | end_margin 0.2, pct (10, 90), average | 6.953 % | 0.509 % | 0.30 | 37.1 % | 87.5 % | 0.15 |
| E19-16 | A threshold | end_margin 0.2, pct (25, 75), confident | 11.117 % | 0.575 % | 0.08 | 42.3 % | 89.4 % | 0.18 |
| E19-17 | A threshold | end_margin 0.2, pct (25, 75), nearest | 6.190 % | 3.251 % | 0.30 | 34.9 % | 88.1 % | 0.09 |
| E19-18 | A threshold | end_margin 0.2, pct (25, 75), average | 6.974 % | 0.529 % | 0.30 | 39.2 % | 88.7 % | 0.17 |
| E19-19 | A threshold | end_margin 0.3, pct (5, 95), confident | 10.742 % | 0.596 % | 0.11 | 38.9 % | 88.5 % | 0.18 |
| E19-20 | A threshold | end_margin 0.3, pct (5, 95), nearest | 6.185 % | 3.259 % | 0.30 | 34.9 % | 88.1 % | 0.12 |
| E19-21 | A threshold | end_margin 0.3, pct (5, 95), average | 7.095 % | 0.546 % | 0.28 | 36.4 % | 87.0 % | 0.17 |
| E19-22 | A threshold | end_margin 0.3, pct (10, 90), confident | 10.730 % | 0.588 % | 0.11 | 39.7 % | 88.6 % | 0.15 |
| E19-23 | A threshold | end_margin 0.3, pct (10, 90), nearest | 6.190 % | 3.255 % | 0.30 | 34.9 % | 88.1 % | 0.1 |
| E19-24 | A threshold | end_margin 0.3, pct (10, 90), average | 7.082 % | 0.550 % | 0.28 | 37.2 % | 87.3 % | 0.17 |
| E19-25 | A threshold | end_margin 0.3, pct (25, 75), confident | 10.750 % | 0.609 % | 0.11 | 41.8 % | 89.4 % | 0.17 |
| E19-26 | A threshold | end_margin 0.3, pct (25, 75), nearest | 6.190 % | 3.251 % | 0.30 | 34.9 % | 88.1 % | 0.1 |
| E19-27 | A threshold | end_margin 0.3, pct (25, 75), average | 7.095 % | 0.563 % | 0.28 | 38.8 % | 88.4 % | 0.14 |
| E19-28 | A threshold | end_margin 0.4, pct (5, 95), confident | 10.413 % | 0.629 % | 0.13 | 38.2 % | 88.5 % | 0.16 |
| E19-29 | A threshold | end_margin 0.4, pct (5, 95), nearest | 6.185 % | 3.259 % | 0.30 | 34.9 % | 88.1 % | 0.1 |
| E19-30 | A threshold | end_margin 0.4, pct (5, 95), average | 7.478 % | 0.588 % | 0.27 | 35.9 % | 87.1 % | 0.17 |
| E19-31 | A threshold | end_margin 0.4, pct (10, 90), confident | 10.400 % | 0.621 % | 0.13 | 39.0 % | 88.6 % | 0.17 |
| E19-32 | A threshold | end_margin 0.4, pct (10, 90), nearest | 6.190 % | 3.255 % | 0.30 | 34.9 % | 88.1 % | 0.11 |
| E19-33 | A threshold | end_margin 0.4, pct (10, 90), average | 7.453 % | 0.588 % | 0.27 | 36.7 % | 87.3 % | 0.18 |
| E19-34 | A threshold | end_margin 0.4, pct (25, 75), confident | 10.454 % | 0.642 % | 0.12 | 41.0 % | 89.4 % | 0.19 |
| E19-35 | A threshold | end_margin 0.4, pct (25, 75), nearest | 6.190 % | 3.251 % | 0.30 | 34.9 % | 88.1 % | 0.11 |
| E19-36 | A threshold | end_margin 0.4, pct (25, 75), average | 7.499 % | 0.600 % | 0.27 | 38.6 % | 88.4 % | 0.17 |
| E19-37 | A threshold | end_margin 0.5, pct (5, 95), confident | 10.183 % | 0.654 % | 0.13 | 38.1 % | 88.2 % | 0.16 |
| E19-38 | A threshold | end_margin 0.5, pct (5, 95), nearest | 6.185 % | 3.259 % | 0.30 | 34.9 % | 88.1 % | 0.1 |
| E19-39 | A threshold | end_margin 0.5, pct (5, 95), average | 7.924 % | 0.613 % | 0.24 | 36.2 % | 87.0 % | 0.14 |
| E19-40 | A threshold | end_margin 0.5, pct (10, 90), confident | 10.175 % | 0.646 % | 0.13 | 38.9 % | 88.3 % | 0.17 |
| E19-41 | A threshold | end_margin 0.5, pct (10, 90), nearest | 6.190 % | 3.255 % | 0.30 | 34.9 % | 88.1 % | 0.12 |
| E19-42 | A threshold | end_margin 0.5, pct (10, 90), average | 7.903 % | 0.613 % | 0.24 | 36.9 % | 87.2 % | 0.17 |
| E19-43 | A threshold | end_margin 0.5, pct (25, 75), confident | 10.217 % | 0.667 % | 0.13 | 40.8 % | 89.1 % | 0.18 |
| E19-44 | A threshold | end_margin 0.5, pct (25, 75), nearest | 6.190 % | 3.251 % | 0.30 | 34.9 % | 88.1 % | 0.11 |
| E19-45 | A threshold | end_margin 0.5, pct (25, 75), average | 7.958 % | 0.625 % | 0.24 | 38.9 % | 88.1 % | 0.16 |
| E19-46 | B ML | C 0.1, 5 frames | 8.453 % | 0.625 % | 0.18 | 49.8 % | 91.5 % | 0.2 |
| E19-47 | B ML | C 0.1, 7 frames *(best B)* | 6.999 % | 0.600 % | 0.20 | 48.8 % | 92.0 % | 0.24 |
| E19-48 | B ML | C 1.0, 5 frames | 8.920 % | 0.617 % | 0.18 | 49.7 % | 91.5 % | 0.16 |
| E19-49 | B ML | C 1.0, 7 frames | 7.182 % | 0.596 % | 0.19 | 48.8 % | 92.0 % | 0.24 |
| E19-50 | B ML | C 10.0, 5 frames | 8.958 % | 0.617 % | 0.18 | 49.8 % | 91.5 % | 0.21 |
| E19-51 | B ML | C 10.0, 7 frames | 7.232 % | 0.592 % | 0.19 | 48.8 % | 91.9 % | 0.23 |

## Dataset / split used for every run

Synthetic validation streams: seeds 30–33, 3,000 bits each, noise 8 and 80, exposure 0.3, phase uniform in [0, T); never used on Days 17–18 (train seeds 0–3, test seeds 10–13 and 20–23). Real: DEV part (first 30 %) of all ten Signal V1 lamps, indicators logged only. TEST (last 70 %) not opened.

## Observations (added 2026-09-11)

| Runs | Observation |
|---|---|
| E19-01/10/19/28/37 (confident, end margin 0 → 0.5) | Each 0.1 frame of end margin removes about 0.4 points of phase-0 BER and widens the band; it cannot get the confident rule below 10 % — the window still straddles bits |
| E19-02/11/20/29/38 (nearest) | End margin has no effect at all (the rule never looks at the window end); percentile pair changes the third decimal. Best on the primary metric, worst at the true phase under noise 80 (single noisy sample) |
| E19-03/12/21/30/39 (average) | Equivalent to nearest on the primary metric within 0.4 points; better at the true phase; the end margin *hurts* it slightly because it removes a valid frame |
| all A rows, percentile pairs (5,95)/(10,90)/(25,75) | Indistinguishable — the signal is near-binary, the midpoint is the same to within a grey level |
| E19-46..51 (ML) | The 7-frame window is worth 1.5 points; C is irrelevant across two decades; the classifier never beats the nearest rule at phase 0 on this validation set |
| DEV columns, all rows | Safe share and phase stability rank the rules in the *opposite* order to the validation BER (confident highest). Recorded as the reason these columns are not selection criteria |
