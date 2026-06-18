# Research Registry - STOM Reorganization Page 5

Generated: 2026-06-18T22:45:47+09:00

This registry is an index over evidence. It does not replace raw `jsonl`, `summary.json`, official OOS records, CSVs, or update logs.

## Schema

| Field | Meaning |
|---|---|
| `machine_name` | Stable identifier used in code/evidence. |
| `display_alias` | Korean short label for dashboard/user-facing review. |
| `candidate_family` | Structural class: seed, mutation, entry filter, portfolio rule, defense baseline, shadow, etc. |
| `evidence_type` | Evidence class: official OOS, CSV reanalysis, portfolio simulation, docs-only, blocked. |
| `oos_status` | Whether official OOS exists, is pending, failed, or is shadow-only. |
| `promotion_status` | Whether promoted, queued, watchlist-only, diagnostic, or baseline. |
| `next_action` | Exact next research action. |

## Candidate Table

| Priority | Display Alias | Machine Name | Evidence Type | OOS Status | Promotion Status | Next Action |
|---:|---|---|---|---|---|---|
| 1 | 저시총 제외 방어 조합 | `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full` | CSV reanalysis | official OOS pending | queued, not promoted | Implement filter/config and run annual + 2025Q4 official OOS. |
| 2 | 11월 제외 비교용 | `r8_exclude_month_11__exit2_skip_after_prior_exit2_loss_500k_else_full` | CSV reanalysis shadow | shadow OOS pending | watchlist only, high overfit risk | Run only as same-period shadow comparison. |
| 3 | exit2 월별 ON/OFF | `exit2_full_after_prior_r8r2_loss_else_off` | portfolio rule simulation | portfolio validation pending | auxiliary rule, not a condition expression | Validate as portfolio-layer official report. |
| 4 | r8 저시총 제외 단독 | `r8_exclude_cap_lt_1500` | CSV reanalysis | official OOS pending | diagnostic candidate | Run standalone r8 low-cap pre-filter official OOS. |
| baseline | r8 기준 전략 | `r8_4` | official OOS baseline | available, Q4 failed | baseline loss source | Use as Q4 loss source for defense work. |
| baseline | exit2 방어 | `exit2_balance` | official OOS baseline | available, Q4 passed | defensive component | Use as portfolio defensive component. |
| baseline | r2full MDD 방어 | `r2full_mdd` | official OOS baseline | available, Q4 passed | defensive component | Use as recent-regime defensive component. |

## Key Metrics

| Candidate | Score | All Profit | All MDD | Recent Profit | Q4 Profit | Q4 MDD | Interpretation |
|---|---:|---:|---:|---:|---:|---:|---|
| `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full` | 90.5884 | 39,402,438 | 7.6823 | 6,941,830 | 952,502 | 11.3583 | Execution priority 1 because it avoids calendar overfit. |
| `r8_exclude_month_11__exit2_skip_after_prior_exit2_loss_500k_else_full` | 93.5087 | 46,745,487 | 10.9396 | 8,551,375 | 1,028,539 | 12.7237 | Raw score winner, but shadow only due November calendar exclusion. |
| `exit2_full_after_prior_r8r2_loss_else_off` | n/a | 35,392,509 | 8.94 | 7,039,427 | 132,648 | 18.23 | Portfolio rule, not condition expression promotion. |
| `r8_exclude_cap_lt_1500` | n/a | 9,420,419 | 7.68 | 2,705,797 | 310,886 | 9.09 | Diagnostic r8 low-cap defense candidate. |
| `r8_4` | n/a | 16,894,052 | n/a | n/a | -835,479 | 35.60 | Baseline and Q4 loss source. |
| `exit2_balance` | n/a | n/a | n/a | n/a | 640,100 | 16.43 | Q4 defensive component. |
| `r2full_mdd` | n/a | n/a | n/a | n/a | 1,516 | 17.17 | Q4 defensive component. |

## Source Files

| Source | Registry Use |
|---|---|
| `.omo/evidence/tmap-walkforward/post-q4-3h-official-oos-recommendations-20260618.json` | next official OOS queue and key metrics |
| `.omo/evidence/tmap-walkforward/post-q4-3h-candidate-scoreboard-20260618.json` | raw score ranking |
| `docs/update_log/2026-06-18_condition_research_current_state_rereview.md` | current score and direction |
| `docs/research/2026-06-18_post_q4_official_oos_next_research.md` | long-lived next OOS note |
| `docs/update_log/2026-06-18_q4_defense_prerule_halfexit_dashboard.md` | Q4 official OOS and defensive interpretation |

## Promotion Rule

No candidate in this registry is final-promoted. The first promotion gate is official OOS for `저시총 제외 방어 조합`. The `11월 제외 비교용` candidate must remain shadow-only unless a later pre-registered causal justification replaces the calendar-month exclusion.
