# Lattice V2 Closeout Or New Design Review

## Executive Summary

| Item | Result |
|---|---|
| Final decision | `archive_v2_branch_and_stop` |
| Replay/OOS/Plan D executed | No |
| DB write executed | No |
| Corrected prior audit issue | Yes, sell/risk threshold extraction was recomputed from source `sell_code` |
| v2 branch continuation | Not recommended |
| New design | Do not open automatically; write a separate v3 design-only plan only if the user chooses it |

## What Was Checked

| Check | Result |
|---|---|
| Source package read to EOF | Complete; receipt recorded |
| v2 limited replay row count | 8 rows |
| OK/error split | 7 OK, 1 error/no_metrics |
| Survivor/hold/no_go | 0 / 0 / 8 |
| OK-row profit | all 7 negative |
| OK-row MDD | all 7 above cap 35 |
| Parsed CSV loss pattern | 7/7 broad-based loss |
| Prior sell/risk table | Superseded due threshold extraction bug |

## Corrected Sell/Risk Finding

The previous report displayed stop/take-profit values such as `90` and `120`. Those values are hold-time thresholds, not stop/take-profit thresholds. The corrected extraction separates:

- stop loss: negative `<=` return thresholds such as `-3` or `-2`
- take profit: small positive `>=` return thresholds such as `1`, `2`, `3`, or `4`
- hold-time stop: `30`, `60`, `90`, or `120` minute thresholds
- late-session exit: time thresholds such as `145500`

This correction improves the diagnosis but does not rescue the v2 branch, because the replay metrics remain materially negative.

## Why The Branch Should Stop

| Reason | Explanation |
|---|---|
| Not a gate-only failure | Profit is negative and MDD is far above cap, so relaxing gates would accept losing strategies. |
| Not a profile-management issue | Replay constraints show no OOS/Plan D/portfolio/full 288 leakage and 8 limited rows were produced. |
| Not a single-outlier issue | Parsed CSVs classify losses as broad-based. |
| Not fixed by risk clause reporting | Corrected thresholds do not change trade outcomes. |
| No survivor input for Plan D | `survivor_count=0` and `hold_count=0`, so Plan D input is blocked. |

## What Remains Useful

| Reusable Asset | Use |
|---|---|
| Official 576 lattice results | Negative baseline and feature/failure distribution reference |
| Repair composite survivors | Evidence that composite/seed-based narrowing can produce bounded signals |
| Plan D rank research | Seed passport and overfit-risk lessons |
| v2 body static/dry-run artifacts | Syntax/registration hygiene reference |
| v2 limited replay output | Stop condition for this branch |

## Final Recommendation

Close the current v2 body branch. Do not run more replay/OOS/Plan D from these 8 bodies. If further research is desired, open a separate v3 design-only planning page that starts from structural design requirements, not from automatic mutation of this failed v2 branch.
