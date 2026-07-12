# 2026-07-07 Plan D rank02 R2 selected OOS handoff

## Scope

- Plan: `.omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md`
- Scope: `plan-d-rank02-r2-selected-oos-prereg-no-portfolio-export`
- Run ID: `lat_plan_d_rank02_r2_selected3_oos_min_warm64_20260707`
- Boundary: portfolio/export/live/final not executed

## Purpose

R2 full-period limited replay에서 improved로 분류된 3개 후보를 freeze/preregistration으로 고정한 뒤, selected 3개만 2026-01-01~2026-02-27 min warm64 OOS-style replay로 확인했다. 목적은 Plan D 다음 라운드를 열어도 되는지 판단하는 것이다.

## Result

| Item | Value |
|---|---:|
| selected pairs | 3 |
| warm prepare | ok |
| back_count | 480 |
| honest rows | 3/3 |
| status ok | 3 |
| gate passed | 3 |
| survivor | 3 |
| hold | 0 |
| no_go | 0 |

| Label | Decision | Profit | MDD | Trades | Daily | Score |
|---|---|---:|---:|---:|---:|---:|
| `plan_d_r1_rank02_r2_06_active_buy_default_tp3_sl3_hold90` | survivor | 1,079,768 | 4.06 | 19 | 0.50 | 10.302049 |
| `plan_d_r1_rank02_r2_07_active_buy_tight_tp3_sl2p5_hold90` | survivor | 486,942 | 9.09 | 20 | 0.50 | 1.035885 |
| `plan_d_r1_rank02_r2_01_l14_amt8000_rate80_hold90` | survivor | 1,124,220 | 4.12 | 18 | 0.50 | 10.202250 |

## Append-Only Intake

| Target | Added |
|---|---:|
| `docs/research/condition_research/generated_conditions/oos_survivors.jsonl` | 3 |
| `docs/research/condition_research/generated_conditions/seed_pool.jsonl` | 3 |
| passports | 3 |

New seed IDs:

- `plan_d_rank02_r2_oos_20260707_01`
- `plan_d_rank02_r2_oos_20260707_02`
- `plan_d_rank02_r2_oos_20260707_03`

Recommended active seed for the next round is `plan_d_rank02_r2_oos_20260707_01` by score/low-MDD robustness. Profit comparator is `plan_d_rank02_r2_oos_20260707_03`.

## Evidence

| Artifact | Path |
|---|---|
| confirmed pairs | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_g_r2_selected_oos_20260707/pairs_plan_d_rank02_r2_selected3_oos_20260707.json` |
| confirmed freeze ledger | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_g_r2_selected_oos_20260707/plan_d_rank02_r2_selected_freeze_ledger_20260707.jsonl` |
| preregistration | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_g_r2_selected_oos_20260707/plan_d_rank02_r2_selected_oos_preregistration_20260707.md` |
| config | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_g_r2_selected_oos_20260707/oos_config_min_plan_d_rank02_r2_selected3_20260707.json` |
| result | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_g_r2_selected_oos_20260707/plan_d_rank02_r2_selected_oos_result_20260707.json` |
| survivor local ledger | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_g_r2_selected_oos_20260707/plan_d_rank02_r2_selected_oos_survivors_20260707.jsonl` |
| append receipt | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_g_r2_selected_oos_20260707/plan_d_rank02_r2_oos_append_receipt_20260707.json` |
| next readiness | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_g_r2_selected_oos_20260707/plan_d_rank02_r2_next_seed_readiness_20260707.json` |
| raw log | `artifacts/plan_d_rank02_r2_selected3_oos_min_warm64_20260707.log` |

## Guardrails Observed

| Guardrail | Result |
|---|---|
| preregistration before OOS | yes |
| selected-only OOS | yes, 3/3 only |
| DB UPDATE/DELETE | not used |
| DB INSERT apply | not used in this scope |
| portfolio/export/live/final | not executed |
| full tick/min 288 | not executed |

## Caveat

이 OOS는 완전한 blind OOS가 아니다. R2 후보는 2026-01-01~2026-02-27을 포함한 full-period min replay에서 선택되었으므로, 이번 실행은 고정 후보의 OOS-style robustness replay로 해석해야 한다.

## Next Command

```text
$start-work .omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md

범위는 plan-d-rank02-r3-generate8-dryrun-no-portfolio-export까지만 진행한다.
목표는 active seed `plan_d_rank02_r2_oos_20260707_01`을 바탕으로 R3 8-slot 후보를 설계하고,
static gate와 DB registration dry-run까지만 수행해 다음 limited replay 개방 여부를 판단하는 것이다.

반드시 먼저 읽을 문서:
- docs/update_log/2026-07-07_plan_d_rank02_r2_selected_oos_handoff.md
- docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_g_r2_selected_oos_20260707/plan_d_rank02_r2_selected_oos_result_20260707.json
- docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_g_r2_selected_oos_20260707/plan_d_rank02_r2_next_seed_readiness_20260707.json
- docs/research/condition_research/generated_conditions/seed_pool.jsonl
- utility/ai_agent/strategy.txt
- utility/ai_agent/rules.txt

진행:
1. active seed와 profit comparator를 재확인한다.
2. R3 8-slot 후보를 research lane 전용/hypothesis_seed/sanitized 이름으로 설계한다.
3. strategy/rules 기준 static gate를 수행한다.
4. DB registration은 dry-run까지만 수행한다.
5. 공식 replay, OOS, portfolio, export/live/final은 실행하지 않는다.
6. handoff와 다음 명령어를 작성하고 한글 커밋한다.

금지:
- 공식 replay 실행 금지
- OOS 실행 금지
- portfolio 산출 금지
- export/live/final promotion 금지
- DB INSERT apply 금지
- DB UPDATE/DELETE 금지
- git add -A 금지
- dashboard 7파일, .gjc, unrelated .omo 잔재 스테이징 금지
```
