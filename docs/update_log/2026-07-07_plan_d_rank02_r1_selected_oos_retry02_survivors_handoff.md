# 2026-07-07 Plan D rank02 R1 selected OOS retry02 handoff

## 1. 이번 loop 목적

Plan D rank02 R1 selected OOS가 warm64 prepare 단계에서 두 번 멈춘 상태를 먼저 진단하고, 같은 selected 2개 후보를 공식 min OOS-style window에서 다시 평가할 수 있는지 확인했다.

이번 범위에서 portfolio, export/live/final promotion, full tick/min 288, 비선정 후보 OOS는 실행하지 않았다.

## 2. 차단 원인과 조치

이전 차단:

- `lat_plan_d_rank02_r1_selected2_oos_min_warm64_20260707`
- `lat_plan_d_rank02_r1_selected2_oos_min_warm64_retry01_20260707`

두 실행 모두 warm64 prepare 중 0 generation row 상태로 멈췄다. 후보 품질 판정 전 단계였으므로 조건식 실패가 아니라 warm prepare 실행 관리 문제로 분류했다.

조치:

- `cli/warm_session.py`에서 warm prepare 실패 시 `_collect_engine_shared_info`의 timeout 진단 정보를 보존하도록 보강했다.
- `tests/unit/test_warm_session_window.py`에 진단 보존 회귀 테스트를 추가했다.
- 기존 stale run row는 DB UPDATE/DELETE 없이 보존했다.

통과 테스트:

```text
python -m pytest tests/unit/test_warm_session_window.py -q
11 passed
```

## 3. retry02 실행 결과

실행 run id:

```text
lat_plan_d_rank02_r1_selected2_oos_min_warm64_retry02_20260707
```

프로파일:

| 항목 | 값 |
|---|---|
| lane | min |
| DB | `_database/stock_min_back.db` |
| 기간 | 2026-01-01 ~ 2026-02-27 |
| 시간 | 09:00 ~ 15:19 |
| 엔진 | warm64 |
| 후보 수 | selected 2개 |

결과:

| 후보 | profit | MDD | trades | daily | gate | 판정 |
|---|---:|---:|---:|---:|---|---|
| `plan_d_r1_rank02_r1_08_parent_buy_default_tp3_sl3_hold90` | 1,079,768 | 4.06 | 19 | 0.50 | true | survivor |
| `plan_d_r1_rank02_r1_02_l14_amt9000_rate80_hold90` | 1,124,220 | 4.12 | 18 | 0.50 | true | survivor |

요약:

- honest rows: 2/2
- status_counts: `ok=2`
- gate_passed: 2/2
- survivor: 2
- hold/no_go: 0

## 4. 산출물

| 구분 | 경로 |
|---|---|
| retry02 result | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_d_selected_oos_20260707/plan_d_rank02_r1_selected_oos_retry02_result_20260707.json` |
| local survivor list | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_d_selected_oos_20260707/plan_d_rank02_r1_selected_oos_survivors_20260707.jsonl` |
| append receipt | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_d_selected_oos_20260707/plan_d_rank02_r1_oos_append_receipt_20260707.json` |
| next seed readiness | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_d_selected_oos_20260707/plan_d_rank02_r1_next_seed_readiness_20260707.json` |
| verification receipt | `docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_d_selected_oos_20260707/plan_d_rank02_r1_selected_oos_retry02_verification_receipt_20260707.json` |
| global survivor ledger | `docs/research/condition_research/generated_conditions/oos_survivors.jsonl` |
| seed pool | `docs/research/condition_research/generated_conditions/seed_pool.jsonl` |
| passport 01 | `docs/research/condition_research/generated_conditions/plan_d_seed_pool_20260706/passports/plan_d_rank02_r1_oos_20260707_01.md` |
| passport 02 | `docs/research/condition_research/generated_conditions/plan_d_seed_pool_20260706/passports/plan_d_rank02_r1_oos_20260707_02.md` |

Append-only 등록:

- `plan_d_rank02_r1_oos_20260707_01`
- `plan_d_rank02_r1_oos_20260707_02`

## 5. 현재 판단

rank02 R1은 Plan D 다음 seed 입력으로 진행 가능하다. 단, selected 2개는 R1 full-period min replay에서 고른 후보이므로 완전 blind OOS가 아니라 fixed OOS-style robustness replay라는 caveat를 유지한다.

추천 next active seed:

```text
plan_d_rank02_r1_oos_20260707_02
```

이유:

- 두 후보 모두 survivor다.
- `_02`는 OOS 수익이 더 높다.
- `_01`은 MDD가 가장 낮아 보조 비교축으로 유지한다.

## 6. 다음 페이지 추천 명령어

다음은 선택 seed를 확정한 뒤 다음 8-slot round를 dry-run까지만 여는 범위다. 공식 replay/OOS/portfolio는 다음 판단 전까지 열지 않는다.

```text
$start-work .omo/plans/css-v7-repair-plan-c-plan-b-d-20260703.md

범위는 plan-d-rank02-r1-survivor-next-round-generate8-dryrun-no-portfolio-export까지만 진행한다.
목표는 rank02 R1 OOS survivor 중 active seed를 1개 선택하고,
Plan D 다음 8-slot 후보를 설계한 뒤 static gate와 DB registration dry-run까지만 수행하는 것이다.

반드시 먼저 읽을 문서:
- docs/update_log/2026-07-07_plan_d_rank02_r1_selected_oos_retry02_survivors_handoff.md
- docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_d_selected_oos_20260707/plan_d_rank02_r1_selected_oos_retry02_result_20260707.json
- docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_d_selected_oos_20260707/plan_d_rank02_r1_oos_append_receipt_20260707.json
- docs/research/condition_research/generated_conditions/plan_d_seed_r1_rank02_20260706/r_d_selected_oos_20260707/plan_d_rank02_r1_next_seed_readiness_20260707.json
- docs/research/condition_research/generated_conditions/seed_pool.jsonl
- docs/research/condition_research/plans/2026-07-02_plan_D_seed_research_program.md
- utility/ai_agent/strategy.txt
- utility/ai_agent/rules.txt

진행:
1. `plan_d_rank02_r1_oos_20260707_02`를 active seed 후보로 우선 검토한다.
2. `_01`은 low-MDD comparator로 유지한다.
3. seed passport, buy/sell sha, source OOS result를 재확인한다.
4. 8-slot 후보는 research lane 전용, hypothesis_seed 라벨, sanitized 이름만 사용한다.
5. strategy/rules 기준 static gate를 수행한다.
6. DB registration은 dry-run까지만 수행한다.
7. 공식 replay, OOS, portfolio, export/live/final promotion은 실행하지 않는다.
8. handoff와 다음 명령어를 작성하고 한글 커밋한다.

금지:
- 공식 replay 실행 금지
- OOS 실행 금지
- portfolio 산출 금지
- export/live/final promotion 금지
- DB UPDATE/DELETE 금지
- DB INSERT apply 금지
- git add -A 금지
- A3/promotion/export/live/final 경로 수정 금지
- dashboard 7파일, .gjc, unrelated .omo 잔재 스테이징 금지
```
