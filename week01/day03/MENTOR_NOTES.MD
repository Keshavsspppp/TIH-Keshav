# Mentor Notes — Day 03 Review

**Status: not recorded at the time.** The Day 03 task asked for the four items below to be confirmed with the mentor and for every decision, correction and updated assumption to be written down. No such record exists in the repository. This template was added on 2026-09-11 so the record can still be made from personal notes; nothing has been filled in on the author's behalf.

| | |
|---|---|
| Date of review | |
| Mentor | |
| Supervisor | |

## Items to confirm

| Item | Proposed on Day 03 | Mentor decision | Correction / updated assumption |
|---|---|---|---|
| Target definition | Transmitted bit sequence + decoded message (`DAY_03.MD`) | | |
| Dataset structure | Unknown until arrival; expected schema in `../day04/DAY_04.MD` §1 | | |
| Evaluation metrics | Message correctness, BER, sync robustness, runtime, sensitivity curves | | |
| Project scope | Software-only, offline; classical SP vs light ML; stripe decoding out unless present | | |

## Blockers raised (slide 3) and what was said about them

| # | Blocker | Mentor response |
|---|---|---|
| 1 | Dataset not yet received — frame rate, symbol rate, resolution, labels unconfirmed | |
| 2 | Unknown packet / framing structure above the raw bits | |
| 3 | ROI behaviour — static or moving | |
| 4 | ML label granularity | |

## Other feedback

## What changed in the plan as a result

*(What actually happened, for reference: the four blockers were carried forward unchanged into `../day04/DAY_04.MD` §4 and were all answered by the data on Day 07 — 260 fps, no labels at any granularity, framing unknown, camera static.)*
