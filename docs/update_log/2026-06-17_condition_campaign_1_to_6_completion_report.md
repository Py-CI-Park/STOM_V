# 2026-06-17 condition campaign 1-6 completion report

## Scope
- User-approved direct execution of steps 1-6.
- Evidence-only research/backtest run. No live trading, DB promotion, V3K gate approval, or runtime write was performed.
- Annual figures below use the same simple train-period convention used in the prior comparison notes: train profit / 3 years. They are not compounded CAGR.

## Completed workflow
| Step | Work | Status | Evidence |
|---:|---|---|---|
| 1 | Check existing warm/overnight candidate processes | Done | No blocking prior `overnight_anchor` or `candidate_batch_eval` process found before execution. |
| 2 | Run `r8_4` OOS 2022/2026 validation | Done | `ovn_r8_oos_2022_20260617`, `ovn_r8_oos_2026_20260617` both passed gate. |
| 3 | Compare THETA/T2C3/portfolio/r8_4 | Done | `2026-06-17_ovn_r8_oos_verification_and_freeze.md`. |
| 4 | Freeze/document `r8_4` if OOS passed | Done | `r8_4_strength_max=250` fixed as train-best and OOS-surviving candidate. |
| 5 | Run `r2full` multistart | Done | `.omo/evidence/tmap-walkforward/ovn_r2full.jsonl`, `ovn_r2full_summary.json`. |
| 6 | Run `exit2` multistart | Done | `.omo/evidence/tmap-walkforward/ovn_exit2.jsonl`, `ovn_exit2_summary.json`. |

## Best candidates
| Candidate | Role | Profit | Annual profit estimate | Annual return on 5M | Annual return on 10M | MDD | Trades | Daily | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `r8_4_strength_max=250` | Train profit leader, OOS-surviving baseline | 13,928,386 | 4,642,795 | 92.9% | 46.4% | 9.62 | 460 | 0.60 | True |
| `r6_4_be_trigger=4` (`exit2`) | Exit2 train profit leader | 11,981,189 | 3,993,730 | 79.9% | 39.9% | 10.24 | 299 | 0.40 | True |
| `r4_7_be_floor=0.5` (`exit2`) | Exit2 balance leader | 11,945,251 | 3,981,750 | 79.6% | 39.8% | 9.05 | 299 | 0.40 | True |
| `r3_6_ogap_lo_b=2.0` (`r2full`) | r2full profit leader | 11,495,457 | 3,831,819 | 76.6% | 38.3% | 6.45 | 346 | 0.50 | True |
| `r11_5_ogap_lo_b=2.0` / `r4_9_burst_b=1.5` (`r2full`) | r2full MDD leader | 11,255,475 | 3,751,825 | 75.0% | 37.5% | 5.87 | 361 | 0.50 | True |

## r8_4 OOS check
| Window | Profit | MDD | Trades | Daily | Payoff | Gate |
|---|---:|---:|---:|---:|---:|---|
| OOS 2022 | 2,201,399 | 10.10 | 75 | 0.40 | 1.3545 | True |
| OOS 2026 Jan-Feb | 764,267 | 10.06 | 15 | 0.40 | 1.3688 | True |
| Combined OOS | 2,965,666 | n/a | 90 | n/a | n/a | True |

Combined OOS simple annual estimate for `r8_4` is 2,541,999, or about 50.8% per year on 5M and 25.4% per year on 10M, using the previous comparison convention.

## Interpretation
| Question | Answer |
|---|---|
| Did any run beat `r8_4` train profit? | No. `r8_4` remains the train profit leader at 13,928,386. |
| Did `r2full` help? | Yes. It found lower-MDD alternatives: profit 11,255,475 with MDD 5.87, and profit 11,495,457 with MDD 6.45. |
| Did `exit2` help? | Yes. It found a middle candidate: profit 11,945,251 with MDD 9.05, and a higher-profit exit candidate at 11,981,189 with MDD 10.24. |
| Which candidate is most proven now? | `r8_4`, because it has both train and OOS 2022/2026 gate-pass evidence. |
| Which candidate is safest by MDD in train? | `r2full` MDD leader, profit 11,255,475 with MDD 5.87. |
| Which candidate is the best next OOS target? | `exit2` balance leader `r4_7_be_floor=0.5`, then `r2full` MDD leader. |

## Next work
| Priority | Work | Why | Expected time |
|---:|---|---|---:|
| 1 | Run OOS 2022/2026 for `exit2` balance leader | Confirms whether the new balanced exit candidate generalizes outside train. | 4-6 minutes per window |
| 2 | Run OOS 2022/2026 for `r2full` MDD leader | Confirms whether the low-MDD candidate survives outside train. | 4-6 minutes per window |
| 3 | Build final portfolio comparison: `r8_4`, `exit2 balance`, `r2full MDD` | Shows whether combining candidates improves stability. | 30-60 minutes |
| 4 | Promote only after OOS pass | Avoids selecting train-only overfit candidates. | After OOS evidence |

## Files
| File | Purpose |
|---|---|
| `.omo/evidence/tmap-walkforward/pairs-ovn-r8-oos.json` | OOS pair input for `r8_4`. |
| `.omo/evidence/tmap-walkforward/ovn_r2full.jsonl` | Full `r2full` candidate evidence. |
| `.omo/evidence/tmap-walkforward/ovn_r2full_summary.json` | `r2full` summary. |
| `.omo/evidence/tmap-walkforward/ovn_exit2.jsonl` | Full `exit2` candidate evidence. |
| `.omo/evidence/tmap-walkforward/ovn_exit2_summary.json` | `exit2` summary. |
| `docs/update_log/2026-06-17_ovn_r8_oos_verification_and_freeze.md` | `r8_4` OOS and freeze note. |
