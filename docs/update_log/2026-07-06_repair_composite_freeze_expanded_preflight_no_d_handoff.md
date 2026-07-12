# Repair Composite Freeze Expanded Preflight No-D Handoff

작성시각: 2026-07-06T09:31:27+09:00
범위: `repair-composite-freeze-expanded-preflight-no-D`
계획서: `.omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md`

## 1. 범위와 금지 조건

이번 범위는 Plan D/P7, OOS, portfolio, full tick/min 288을 열지 않고
composite coverage 후보의 안정성을 한 번 더 확인하는 no-D 제한 실행이다.

지킨 조건:

- Plan D/P7 실행 없음
- OOS 실행 없음
- portfolio 산출 없음
- full tick 288 / full min 288 실행 없음
- strategy DB는 INSERT-only 등록만 수행
- A3/promotion/export/live/final 경로 수정 없음
- dashboard 7파일, `.gjc`, unrelated `.omo` 잔재 스테이징 없음

## 2. 산출물

| 구분 | 경로 |
| --- | --- |
| read receipt | `.omo/evidence/repair-composite-freeze-expanded-preflight-no-d-20260706/source_read_receipt.md` |
| go16 freeze ledger | `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_freeze_expanded_20260706/repair_composite_go16_freeze_ledger_20260706.jsonl` |
| go16 freeze summary | `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_freeze_expanded_20260706/repair_composite_go16_freeze_summary_20260706.json` |
| expanded design | `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_freeze_expanded_20260706/repair_composite_expanded_design_20260706.json` |
| expanded seed JSON | `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_freeze_expanded_20260706/repair_composite_expanded_candidates_20260706_seeds.json` |
| compile/token receipt | `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_freeze_expanded_20260706/repair_composite_expanded_compile_token_receipt_20260706.json` |
| DB register receipt | `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_freeze_expanded_20260706/register_repair_composite_expanded_receipt_20260706.json` |
| pair list | `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_freeze_expanded_20260706/pairs_repair_composite_expanded_48_20260706.json` |
| preflight result | `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_freeze_expanded_20260706/repair_composite_expanded_preflight_result_20260706.json` |
| preflight summary | `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_freeze_expanded_20260706/repair_composite_expanded_preflight_summary_20260706.md` |
| selected freeze ledger | `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_freeze_expanded_20260706/repair_composite_selected_freeze_ledger_20260706.jsonl` |
| selected prereg draft | `docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_freeze_expanded_20260706/repair_composite_selected_freeze_preregistration_draft_20260706.md` |

## 3. 설계 요약

직전 composite coverage preflight의 go 16개를 freeze 대상으로 고정했다.
그 뒤 기존 v2에서 compile/token을 통과했던 component block만 재사용해
16개 buy 조합과 3개 sell profile을 결합한 48쌍을 만들었다.

설계 의도:

- `cov04/cov03/cov12` 계열의 early core를 보존
- L14/L13/L1430 보강으로 daily 거래수 부족을 완화
- pure late ladder가 아니라 early core 보강 형태로 late component를 사용
- sell profile은 default 중심으로 보고, tight/loose는 비교군으로 제한

compile/token gate 결과:

| 항목 | 결과 |
| --- | ---: |
| expanded 후보 | 48 |
| buy compile/token | 48/48 |
| sell compile/token | 48/48 |
| DB inserted seeds | 48 |
| DB inserted rows | 96 |
| unsafe target names | 0 |
| conflicts | 0 |

DB backup:

`ai_strategy_loop/state/loop_strategies.db.bak.lattice_20260706T000723Z`

## 4. 공식 preflight 결과

| 항목 | 값 |
| --- | --- |
| run_id | `lat_repair_composite_expanded_48_official_full_warm64_20260706` |
| lane | min |
| DB | `_database/stock_min_back.db` |
| 기간 | 2025-04-07 ~ 2026-02-27 |
| 시간 | 09:00 ~ 15:19 |
| engine | warm64 |
| warm prepare | `status=ok`, `back_count=1379`, `elapsed=109s` |
| rows | 48/48 |
| status_counts | `{"ok": 48}` |
| gate_passed | 32 |
| decision_counts | `{"go": 32, "no_go": 16}` |

sell profile별 결과:

| sell_profile | go | no_go | 해석 |
| --- | ---: | ---: | --- |
| `sell_default_tp3_sl3_hold60` | 14 | 2 | 가장 안정적 |
| `sell_loose_tp4_sl3_hold90` | 12 | 4 | 일부 안정적, MDD 낮추는 경우 있음 |
| `sell_tight_tp3_sl2p5_hold60` | 6 | 10 | L13/L14 과밀 조합에서 손익 실패가 잦음 |

상위 go:

| 순위 | condition_id | profit | MDD | daily | trades |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `repair_v3_20260706_13_top_four_plus_l14_sell_default_tp3_sl3_hold60` | 1,887,171 | 19.25 | 1.0 | 206 |
| 2 | `repair_v3_20260706_19_profitmax_plus_l1430_sell_default_tp3_sl3_hold60` | 1,426,967 | 31.04 | 0.8 | 179 |
| 3 | `repair_v3_20260706_14_top_four_plus_l13_sell_default_tp3_sl3_hold60` | 1,393,641 | 13.34 | 1.8 | 375 |
| 4 | `repair_v3_20260706_13_top_four_plus_l14_sell_loose_tp4_sl3_hold90` | 1,340,830 | 18.56 | 0.9 | 201 |
| 5 | `repair_v3_20260706_26_daily_boost_core_l1430_sell_default_tp3_sl3_hold60` | 1,318,354 | 33.04 | 0.9 | 184 |

## 5. 판단

full chunk 개방:

`가능`, 단 broad full chunk가 아니라 narrowed composite repair로만 열어야 한다.
pure late ladder와 broad tight sell 확장은 제외하는 것이 타당하다.

OOS 준비:

`조건부 가능`. selected freeze 후보 16개를 대상으로 사용자가 OOS 실행을 명시적으로 허용하면
OOS preregistration 후 OOS를 열 수 있다. 이번 범위에서는 OOS를 실행하지 않았다.

Plan D:

`불가능`. Plan D는 OOS survivor와 seed pool이 생긴 뒤에만 가능하다.
현재는 Plan D/P7을 계속 차단한다.

핵심 원인/성과:

- 기존 lattice 576개 no_go의 핵심 원인 중 하나였던 daily 거래수 부족은 composite coverage로 상당 부분 해결됐다.
- 다만 late component만 묶은 ladder형 조합은 거래수는 늘지만 손익이 음수로 무너진다.
- 가장 효율적인 방향은 early core + L13/L14/L1430 보강, default/loose sell 중심이다.

## 6. 다음 추천 명령어

OOS를 열려면 다음 범위에서 명시적으로 OOS를 허용해야 한다.
Plan D는 여전히 금지한다.

```text
$start-work .omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md

범위는 repair-composite-selected-oos-no-D까지만 진행한다.
목표는 expanded preflight go 32개 중 selected freeze 16개를 대상으로
OOS preregistration을 확정하고, 공식 OOS만 실행해 Plan D 입력 가능 여부를 판단하는 것이다.

반드시 먼저 읽을 문서:
- docs/update_log/2026-07-06_repair_composite_freeze_expanded_preflight_no_d_handoff.md
- docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_freeze_expanded_20260706/repair_composite_expanded_preflight_result_20260706.json
- docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_freeze_expanded_20260706/repair_composite_selected_freeze_preregistration_draft_20260706.md
- docs/research/condition_research/research_runs/seed_lattice_20260702/repair_composite_freeze_expanded_20260706/repair_composite_selected_freeze_ledger_20260706.jsonl

진행:
1. selected freeze 16개 후보의 buy/sell sha, DB mapping, 성과를 재확인한다.
2. OOS preregistration을 확정한다.
3. selected 16개만 공식 OOS로 실행한다.
4. OOS 결과를 survivor/hold/no_go로 분류한다.
5. OOS survivor가 있으면 Plan D 입력 가능 여부만 판단한다.
6. portfolio와 Plan D/P7은 실행하지 않는다.
7. handoff와 다음 명령어를 작성하고 한글 커밋한다.

금지:
- Plan D/P7 실행 금지
- portfolio 산출 금지
- full tick 288 실행 금지
- full min 288 실행 금지
- selected 16개 외 OOS 실행 금지
- preregistration 없는 OOS 실행 금지
- DB UPDATE/DELETE 금지
- git add -A 금지
- A3/promotion/export/live/final 경로 수정 금지
- dashboard 7파일, .gjc, unrelated .omo 잔재 스테이징 금지

완료 후 보고:
- OOS preregistration 경로
- OOS 결과
- survivor/hold/no_go 목록
- Plan D 진행 가능/불가능 판단
- 다음 추천 명령어
```
