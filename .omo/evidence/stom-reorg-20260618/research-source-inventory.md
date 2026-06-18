# Research Source Inventory - STOM Reorganization Page 4

Captured: 2026-06-18T22:45:47+09:00  
Scope: current-state baseline for condition research, OOS proof, portfolio defense, and dashboard research records.

## Baseline Conclusion

The current default research direction is **seed bank + official OOS + branch attribution + evidence lineage**, not cold mass generation. Cold generation can still explore structure, but current decision work must prioritize validated seeds/candidates, official OOS separation, and traceable evidence.

## Canonical Source Table

| Source | Role | Canonical Status | Key Facts | Current Action |
|---|---|---|---|---|
| `docs/update_log/2026-06-18_condition_research_current_state_rereview.md` | Latest overall score and direction | canonical current-state report | Overall 72, AI generation 67, OOS/portfolio 76, promotion readiness 56. Cold generation remains weak; seed/validated-candidate mutation plus official OOS is the realistic path. | Use as top-level state baseline. |
| `docs/research/condition_research/2026-06-18_current_state_rereview_summary.md` | Long-lived research summary | canonical long-term summary | Repeats the 72/67/76/56 score set; records next OOS priorities and long-lived gaps. | Use in dashboard/research docs index. |
| `docs/update_log/2026-06-18_post_20260618_research_dashboard_handoff.md` | Session handoff | canonical next-step handoff | Next official OOS candidate is `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full`; dashboard needs aliases, latest update_log exposure, clearer evidence labels. | Use for next execution queue. |
| `docs/research/2026-06-18_post_q4_official_oos_next_research.md` | Long-lived next OOS research note | canonical research note | Confirms CSV reanalysis is not final official OOS; robust low-cap candidate is execution priority 1. | Use as stable research reference. |
| `docs/update_log/2026-06-18_post_q4_3h_bulk_research.md` | Bulk CSV reanalysis log | canonical for candidate narrowing | annual 15 CSV + Q4 3 CSV; 64 combined candidates; robust primary selected despite raw score winner being a calendar exclusion. | Feed registry candidates. |
| `.omo/evidence/tmap-walkforward/post-q4-3h-official-oos-recommendations-20260618.json` | Machine-readable next OOS queue | canonical machine queue | Priority 1 robust primary score 90.5884, all profit 39,402,438, all MDD 7.6823, Q4 profit 952,502, Q4 MDD 11.3583. | Use as registry source of truth for next queue. |
| `.omo/evidence/tmap-walkforward/post-q4-3h-candidate-scoreboard-20260618.json` | Candidate score table | canonical scoring artifact | Raw score winner is `r8_exclude_month_11__...` at score 93.5087 but high overfit risk; robust primary is rank 3 at score 90.5884. | Keep raw ranking separate from promotion ranking. |
| `docs/update_log/2026-06-18_dashboard_research_records_oos_followup.md` | Dashboard records + OOS followup | canonical dashboard/OOS bridge | Research Records API/panel completed; GUI parity API/panel completed; 2022/2026 OOS runs for `exit2_balance` and `r2full_mdd` completed and gate passed. | Use as dashboard evidence source. |
| `.omo/evidence/tmap-walkforward/dashboard-research-records-check-20260618.json` | Dashboard API verification artifact | canonical dashboard check | `/research_records` and detail returned 200; campaign visible at rank 1; campaign_count 15 in captured check. | Use as dashboard visibility proof. |
| `docs/update_log/2026-06-18_oos_2023_2025_combo_experiment_log.md` | 2023-2025 OOS combo log | canonical OOS expansion report | 2023-2025 additional OOS 9/9 complete and gate passed; `r8_4 + exit2` total-profit leaning, `r8_4 + r2full` recent-stability leaning. | Feed portfolio classification. |
| `.omo/evidence/tmap-walkforward/oos-2023-2025-r8-exit2-r2full-20260618.json` | Official OOS run record JSON | canonical raw OOS index | 9 fixed-candidate e32 warm-engine runs for 2023-2025. | Do not summarize without source link. |
| `.omo/evidence/tmap-walkforward/portfolio-r8-exit2-r2full-20260618.json` | Portfolio aggregation evidence | canonical derived portfolio artifact | 2-strategy/3-strategy annual portfolio comparisons over official OOS CSVs. | Derived evidence; keep raw CSV/run references. |
| `docs/update_log/2026-06-18_q4_defense_prerule_halfexit_dashboard.md` | Q4 official OOS + defense report | canonical Q4 stress report | Q4 `r8_4` failed: -835,479, MDD 35.60. `exit2_balance`: +640,100, MDD 16.43. `r2full_mdd`: +1,516, MDD 17.17. | Use for stop conditions and stress labels. |
| `.omo/evidence/tmap-walkforward/q4-defense-prerule-halfexit-dashboard-20260618_summary.json` | Q4 dashboard summary | canonical dashboard summary | Best overall in Q4 dashboard card: `r2full_mdd + exit2_balance`, profit 641,616, MDD 12.522, trades 48. | Dashboard summary only; not standalone promotion evidence. |
| `docs/update_log/2026-06-18_post_q4_defense_next4.md` | Follow-up rule analysis | canonical design-stage report | `exit2_skip_after_prior_exit2_loss_500k_else_full` best overall; r8 Q4 loss concentrated in 2025-11, 09:00-09:04, market cap `<1500`, low-break exits. | Use to justify low-cap defense candidate. |
| `.omo/evidence/tmap-walkforward/post-q4-next4-20260618_summary.json` | Follow-up dashboard summary | canonical summary of four steps | best_overall label `exit2_skip_after_prior_exit2_loss_500k_else_full`, profit 46,159,506, MDD 10.9396, trades 1359. | Derived rule summary; link to raw artifacts. |
| `docs/update_log/2026-06-17_condition_generation_breadth_evaluation.md` | Prior breadth evaluation | historical but important | Average 66; OOS and lineage identified as next bottlenecks; evidence summary drift explicitly noted. | Mark drift risk source. |
| `docs/update_log/2026-06-17_condition_self_improvement_score_update.md` | Prior process score update | historical but important | Overall process improved from 56% to 68%; new candidate OOS pass count still 0; summary drift and OOS promotion workflow gaps remain. | Use as before-state. |
| `docs/research/condition_research/README.md` | Research folder index | canonical folder guide | Points to 2026-06-18 current-state summary as latest condition research baseline. | Keep updated as long-term index. |
| `ai_strategy_loop/dashboard/research_records.py` | Dashboard evidence parser | canonical implementation reference | `list_research_records()` reads `*_summary.json`, `*.jsonl`, `*_pairs.json`, and logs from `.omo/evidence/tmap-walkforward`. | Use to align registry/evidence file classes. |

## Current Candidate Baseline

| Priority | Display Alias | Machine Name | Evidence Type | OOS Status | Promotion Status | Notes |
|---:|---|---|---|---|---|---|
| 1 | 저시총 제외 방어 조합 | `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full` | CSV reanalysis candidate | official OOS pending | queued, not promoted | Score 90.5884; selected over raw winner because it avoids calendar exclusion overfit. |
| 2 | 11월 제외 비교용 | `r8_exclude_month_11__exit2_skip_after_prior_exit2_loss_500k_else_full` | shadow comparison | shadow OOS pending | watchlist only | Raw score 93.5087 but calendar-month exclusion is high overfit risk. |
| 3 | exit2 월별 ON/OFF | `exit2_full_after_prior_r8r2_loss_else_off` | portfolio rule | report/OOS style validation pending | auxiliary rule | Not a condition expression change; label separately. |
| 4 | r8 저시총 제외 단독 | `r8_exclude_cap_lt_1500` | entry filter candidate | official OOS pending | cause isolation | Tests r8 low-cap defense alone. |
| baseline | r8 기준 전략 | `r8_4` | official OOS baseline | Q4 failed, annual positive | baseline, not promoted alone | Q4 -835,479 and MDD 35.60; loss source for defense work. |
| baseline | exit2 방어 | `exit2_balance` | official OOS baseline | Q4 passed | defensive component | Q4 +640,100 and MDD 16.43. |
| baseline | r2full MDD 방어 | `r2full_mdd` | official OOS baseline | Q4 passed | defensive component | Q4 +1,516 and MDD 17.17. |

## Conflicts, Drift, and Cautions

| Item | Type | Handling |
|---|---|---|
| `r8_exclude_month_11__...` is rank 1 by raw score but not execution priority 1 | conflict between score rank and promotion rank | Keep both facts. Registry must show raw score winner as shadow, not promoted. |
| Earlier planning said merge count 59; Page 2 command found 73 merge commits | drift in branch-count estimate | Use Page 2 command output as current branch map. |
| Prior score reports use 56%, 66%, 68%, then 72/67/76/56 | historical scoring drift by date/scope | Do not overwrite; mark 2026-06-18 rereview as canonical current baseline. |
| `summary.json` files can drift from `jsonl` rows | evidence drift risk | Page 7 defines raw-vs-summary checks before promotion claims. |
| CSV reanalysis is not official OOS | evidence-type ambiguity | Label as `csv_reanalysis` until official engine run completes. |
| 2026 short period annualized returns can be overstated | metric interpretation risk | Registry must retain period fields and warning. |

## Page 4 QA

Required key facts present: 72, 67, 76, 56, `r8_exclude_cap_lt_1500`.

Cleanup receipt:
- No recomputation, no OOS run, no branch mutation, no staging, no protected path access beyond read-only evidence inspection.
