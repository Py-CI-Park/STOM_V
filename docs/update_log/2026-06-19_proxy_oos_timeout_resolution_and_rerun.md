# Proxy OOS timeout resolution and rerun

Generated: 2026-06-19

## Purpose

Resolve the proxy official OOS `engine data loading timed out` blocker, rerun the same three single-condition proxy candidates, and decide whether any proxy candidate is good enough to continue toward promotion research. This remains research-only: no live/export/operating DB/V3K/KHOPENAPI path was touched.

## Cause and fix

| Item | Result |
|---|---|
| Cause | Orphaned Windows `--multiprocessing-fork` child processes remained after prior warm-run parents exited. |
| Evidence | 104 orphan fork processes in `C:/System_Trading/STOM/STOM_V.wt-dev` were found and terminated. |
| Fix | Cleaned orphan processes and added a logged rerun wrapper that kills the process tree on timeout. |
| Rerun status | Q4 stress and 2022~2026 YTD official OOS reran successfully. |

## Candidate results

| Candidate | Decision | 2022~2026 YTD profit | Max MDD | Trades | Positive periods | Q4 profit | Main failure |
|---|---|---:|---:|---:|---:|---:|---|
| P1 entry liquidity proxy | reject | 1,168,567원 | 22.14% | 167 | 3 | 99,818원 | Below profit baseline, MDD above baseline, weak period spread. |
| P2 defensive exit proxy | reject | 3,856,918원 | 15.89% | 272 | 4 | -101,992원 | Below profit baseline and Q4 loss. |
| P3 trend/vol exit proxy | reject | 6,338,838원 | 22.86% | 263 | 5 | 132,797원 | Below profit baseline and MDD above baseline. |

Baseline: official r8 low-cap profit 7,292,861원, max MDD 19.09%, trades 263, Q4 profit 310,886원.

## Conclusion

No proxy candidate passed. The timeout blocker was resolved, but the single proxy-condition route did not reproduce the combined portfolio result. Do not promote these proxy candidates. If research continues, use a separate condition-set or operational-rule plan rather than forcing the CSV portfolio behavior into one condition expression.

## Evidence

- `.omo/evidence/tmap-walkforward/proxy-oos-20260619/proxy-oos-timeout-diagnosis-20260619.json`
- `.omo/evidence/tmap-walkforward/proxy-oos-20260619/proxy-oos-rerun-summary-20260619.json`
- `.omo/evidence/tmap-walkforward/proxy-oos-20260619/proxy-oos-decision-card-rerun-20260619.json`
- `.omo/evidence/tmap-walkforward/proxy-oos-20260619/logs/rerun-manifest.json`
