# Post-20260618 Official OOS Preregistration

Generated: 2026-06-19

## Scope

This preregistration covers the first safe execution slice after running:

```powershell
gjc ultragoal create-goals --brief-file .omo/plans/post-20260618-official-oos-dashboard-cleanup.md
gjc ultragoal complete-goals
```

The active durable goal is the post-20260618 official OOS/dashboard cleanup plan. This preregistration closes the pre-run context checks and fixes the first official OOS candidate before any OOS command is executed.

## Preflight Evidence

| Check | Result | Evidence |
|---|---|---|
| Recommendation JSON parses | pass | `.omo/evidence/tmap-walkforward/post-q4-3h-official-oos-recommendations-20260618.json` parsed successfully |
| Candidate scoreboard parses | pass | `.omo/evidence/tmap-walkforward/post-q4-3h-candidate-scoreboard-20260618.json` parsed successfully |
| Research Records campaign visible | pass | `post-q4-3h-bulk-research-20260618` visible, rank 1, count 17, detail available |
| Protected path status | pass | `git status --short -- _database _database_v3k_shadow _log backup '*.db' backtest/graph .omx/reports 'v3k_settings*.json' _v3k_sidecar/v3k_gui_settings.json` returned no output |
| Monolithic ultragoal split attempt | not applied | `gjc ultragoal steer --kind split_subgoal` rejected because active goals cannot be split; continue under active G001 |

## Primary Candidate

| Field | Value |
|---|---|
| Friendly alias | 저시총 제외 방어 조합 |
| Machine name | `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full` |
| Evidence type to produce | `공식 OOS` |
| Selection reason | Lower overfit risk than calendar-month winner; entry filter + causal prior-month portfolio rule |
| Preselection rank | 3 |
| Preselection score | 90.5884 |
| CSV reanalysis all-period profit | 39,402,438 KRW |
| CSV reanalysis all-period MDD | 7.6823% |
| CSV reanalysis Q4 profit | 952,502 KRW |
| CSV reanalysis Q4 MDD | 11.3583% |
| Status before this preregistration | CSV reanalysis only, not official OOS |

## Shadow Candidate

| Field | Value |
|---|---|
| Friendly alias | 11월 제외 비교용 후보 |
| Machine name | `r8_exclude_month_11__exit2_skip_after_prior_exit2_loss_500k_else_full` |
| Evidence type to produce | `공식 OOS shadow comparison` |
| Selection rule | Compare only after robust primary evidence; never promote directly from calendar-month exclusion |
| Risk | High overfit risk from calendar-month rule |

## Execution Boundary

| Allowed | Forbidden |
|---|---|
| Official engine run only after candidate strategy/config is explicitly prepared | Do not modify `backtest.py` |
| Write raw OOS log/summary under `.omo/evidence/tmap-walkforward/` | Do not touch live trading, V3K, serial-key behavior, `strategy.db`, export/final approval |
| Label outputs as `공식 OOS`, `CSV 재분석`, `포트폴리오 규칙`, or `설계/보류` | Do not call CSV reanalysis official OOS |
| Use friendly Korean aliases in reports | Do not promote the 11월 제외 shadow candidate directly |

## Command Envelope

The exact P4 official OOS command is intentionally not executed by this preregistration. Before P4 starts, the runner must resolve how the compound candidate maps to official engine inputs without `backtest.py` changes:

1. `r8_exclude_cap_lt_1500` is an entry filter over the existing `r8_4` family.
2. `exit2_skip_after_prior_exit2_loss_500k_else_full` is a causal prior-month portfolio-layer rule, not a plain buy/sell pair.
3. The next command must therefore either use an existing approved condition/runner config path for this compound candidate or first produce a bounded execution adapter/config artifact that remains outside `backtest.py`, live/V3K, and protected DB writes.

Stop before official OOS if the command would require manual `*.db` writes, `backtest.py` edits, live/V3K paths, or unclear evidence-type labeling.

## Next Step

Proceed to P4 only after the official run command/config is explicit and reviewable. If command mapping is still unclear, create a short execution-adapter discovery note before running OOS.
