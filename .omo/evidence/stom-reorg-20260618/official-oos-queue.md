# Official OOS Queue And Promotion Workflow

Generated: 2026-06-18T23:19:07+09:00  
Plan page: 13  
Status: queue and promotion workflow only. No official OOS run was executed in this task.

## Guardrails

- CSV reanalysis is not official OOS.
- Portfolio-layer simulation is not condition-expression official OOS.
- Promotion states are limited to `candidate`, `oos_passed`, `deferred`, and `rejected`.
- Forbidden: live promotion, final approval/export winner, live order wiring, `strategy.db` writes, protected runtime DB writes, V3K gate 4~6 actions.
- If official OOS is executed later, the registry, dashboard records, raw evidence, summary evidence, and promotion/defer card must be updated in the same change set.

## Source Evidence

| Source | Key fact |
|---|---|
| `docs/update_log/2026-06-18_condition_research_current_state_rereview.md` | Next action is not mass generation; it is official OOS for the robust candidate. |
| `docs/update_log/2026-06-18_post_20260618_research_dashboard_handoff.md` | First candidate is `저시총 제외 방어 조합`; 11월 제외 is shadow comparison only. |
| `.omo/plans/post-20260618-official-oos-dashboard-cleanup.md` | Deferred plan defines official OOS sequence and dashboard cleanup follow-up. |
| `.omo/evidence/stom-reorg-20260618/research-registry.json` | Current promotion status remains pre-official-OOS candidate/deferred, not live. |

## Candidate Queue

| Order | Friendly name | Internal name/rule | Evidence type to produce | Expected time | Current status | Stop rule |
|---:|---|---|---|---:|---|---|
| 1 | 저시총 제외 방어 조합 | `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full` | official OOS | 45m | `candidate` | Stop after official engine result and promotion/defer card. Do not continue to shadow if protected paths or process cleanup fail. |
| 2 | 11월 제외 비교용 후보 | `r8_exclude_month_11__exit2_skip_after_prior_exit2_loss_500k_else_full` | official OOS shadow comparison | 35m | `deferred` / shadow only | Stop if it wins only through calendar-month exclusion without robust explanation; never promote directly. |
| 3 | exit2 월별 ON/OFF 규칙 | `exit2_full_after_prior_r8r2_loss_else_off` | portfolio-layer rule report | 25m | `deferred` support rule | Stop after labeling as portfolio rule, not condition-expression OOS. |
| 4 | r8 저시총 제외 단독 | `r8_exclude_cap_lt_1500` | official OOS isolation test | 40m | `candidate` cause-isolation | Stop after isolating whether r8 low-cap filter caused Q4 improvement. |

## Pre-Execution Checklist

Before running any official OOS:

1. Re-read AGENTS/V3K guardrails and protected path list.
2. Confirm pre-selection artifacts parse:
   - `.omo/evidence/tmap-walkforward/post-q4-3h-official-oos-recommendations-20260618.json`
   - `.omo/evidence/tmap-walkforward/post-q4-3h-candidate-scoreboard-20260618.json`
3. Record `git status --short --branch`.
4. Record protected path status with recursive DB pathspec.
5. Write preregistration: candidate, exact config, engine command, expected outputs, stop criteria.
6. Confirm no live/runtime DB, `strategy.db`, V3K, KHOPENAPI, or order path is involved.

## Expected Command Pattern

The exact official command must be filled from the later OOS execution plan after artifact validation. Required command envelope:

```powershell
# preregister candidate and evidence output path first
# execute official engine only, not CSV-only reanalysis
# write raw JSON/CSV/log and summary card under .omo/evidence/tmap-walkforward/
# update .omo/evidence/stom-reorg-20260618/research-registry.* or dashboard records in same change set
```

## Required Evidence Outputs

| Output | Required content |
|---|---|
| Preregistration | Candidate, exact input artifacts, official command, run window, stop rule. |
| Raw official result | Full official OOS output path, log, status, elapsed time. |
| Summary card | Profit, MDD, trades, gate status, OOS period, caveats. |
| Registry update | `machine_name`, `display_alias`, `evidence_type`, `oos_status`, `promotion_status`, `next_action`. |
| Dashboard record | Research Records campaign visibility and detail endpoint proof. |
| Decision card | One of `oos_passed`, `deferred`, `rejected`; never live. |

## Promotion Rules

| Result | Status | Next action |
|---|---|---|
| Official OOS passes robustly, with acceptable MDD and no calendar overfit | `oos_passed` | Queue portfolio/branch attribution review; still no live export. |
| Passes only under suspicious calendar/month exclusion | `deferred` | Keep as shadow evidence; require alternative explanation. |
| Fails official OOS or increases MDD materially | `rejected` | Record failure and feed seed-bank negative examples. |
| Execution incomplete, missing artifact, or cleanup failed | `deferred` | Repair evidence before interpreting result. |

## QA Checks For This Queue

- Search terms present: `저시총 제외 방어 조합`, `official`, `stop`.
- Promotion boundary present: `live` and `strategy.db` appear only as forbidden contexts.
- No OOS run, branch mutation, stage, commit, push, or PR creation was performed in this page.
