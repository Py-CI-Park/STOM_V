# 2026-07-04 P5 Profile Audit Official Config Handoff

## 1. 결론

P5-profile-audit 범위만 완료했다. 공식 tick/min full smoke 는 아직 실행하지 않았고,
preflight 도 실행하지 않았다. 이번 산출물은 DB 전체기간 + warm64 공식 프로파일을
정적으로 검증하고, 기존 2025Q1/warm8 산출물을 공식 판단에서 제외한 상태로
새 config와 preflight 계획을 만든 것이다.

## 2. 생성 산출물

| 산출물 | 경로 | 용도 |
|---|---|---|
| audit script | `ai_strategy_loop/scripts/plan_b_p5_profile_audit.py` | DB/pair/config 정적 감사와 공식 config 생성 |
| unit test | `tests/unit/test_plan_b_p5_profile_audit.py` | range filter, gate policy, chunk protocol, artifact write 계약 |
| profile receipt | `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_profile_audit_official_full_warm64_20260704.json` | 공식 판단용 정적 receipt |
| tick official config | `docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_tick_official_full_warm64_20260704.json` | tick DB 전체기간 + warm64 config |
| min official config | `docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_min_official_full_warm64_20260704.json` | min DB 전체기간 + warm64 config |
| tick preflight pair list | `docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_preflight4_official_full_warm64_20260704.json` | tick preflight 4쌍만, full run 아님 |
| preflight plan | `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_preflight_plan_official_full_warm64_20260704.md` | 다음 실행 절차와 중단 조건 |

## 3. 검증된 공식 DB 범위

| lane | DB | table_count | temporal_row_count | index 범위 | config 날짜 |
|---|---|---:|---:|---|---|
| tick | `_database/stock_tick_back.db` | 2,427 | 124,235,459 | `20220323090000` ~ `20260227093000` | `20220323` ~ `20260227` |
| min | `_database/stock_min_back.db` | 1,381 | 5,578,411 | `202504070900` ~ `202602271519` | `20250407` ~ `20260227` |

범위 감사는 SQLite read-only URI(`mode=ro`)로 수행했다. `index` 값은 숫자 문자열만
허용하고 tick 은 길이 14 이상, min 은 길이 12 이상만 집계했다. 따라서 기존에
관측된 비시계열 단축값(`20`)은 공식 범위에서 제외된다.

## 4. 게이트 전파 감사 결과

이전 mismatch 는 "LoopConfig 가 `0.3` 을 못 읽는 버그"가 아니라,
`_score_outcome()` / `_build_warm_btconfig()` 가 `effective_condition_discovery_runtime_config()`를
거치면서 fast-discovery 정책 하한 `min_daily_trades=0.5` 를 적용한 결과였다.

| 항목 | 이전 config | 이전 실효 | 공식 config | 공식 실효 |
|---|---:|---:|---:|---:|
| `min_daily_trades` | 0.3 | 0.5 | 0.5 | 0.5 |
| `mdd_cap` | 35 | 35 | 35 | 35 |
| preset/process | 기본 fast | fast-discovery | fast / fast-discovery | fast-discovery |

따라서 이번 수정은 코드 게이트 완화가 아니라 **config를 실효 정책 하한에 맞춘
정합성 수정**이다. 앞으로 receipt와 runtime reason 문자열이 모두
`min_daily_trades 0.5`, `mdd_cap 35` 로 맞아야 한다.

## 5. 공식 프로파일

### tick

| 항목 | 값 |
|---|---|
| pair count | 288 |
| DB 기간 | `20220323` ~ `20260227` |
| warm engine | 64 |
| runtime time window | 09:00:00 ~ 09:28:00 |
| raw DB max | 09:30:00 |
| 비고 | fast-discovery runtime 은 tick 창을 09:00~09:28로 고정한다. raw DB는 09:30까지 있으나 현재 공식 config는 runtime claim 을 09:28로 맞춘다. |

### min

| 항목 | 값 |
|---|---|
| pair count | 288 |
| DB 기간 | `20250407` ~ `20260227` |
| warm engine | 64 |
| runtime time window | 09:00 ~ 15:19 |
| 비고 | `full_session_enabled=true`, `bt_min_universe_end_time=151900` |

## 6. pair / strategy DB static gate

| 항목 | tick | min |
|---|---:|---:|
| pair_count | 288 | 288 |
| unique_label_count | 288 | 288 |
| unsafe strategy names | 0 | 0 |
| stockbuy missing | 0 / 576 | - |
| stocksell missing | 0 / 576 | - |

`ai_strategy_loop/state/loop_strategies.db`는 SELECT-only로 감사했다. sanitized name
strategy row 가 buy/sell 각각 576건 모두 존재한다.

## 7. chunk / engine restart protocol

공식 288 run 은 한 번에 돌리지 않는다.

| lane | chunk_size | chunks | engine policy |
|---|---:|---:|---|
| tick | 48 | 6 | 각 chunk 전 warm64 prepare, chunk 후 close/restart |
| min | 48 | 6 | tick 공식 export 완료 후 동일 방식 |

근거: wrong-profile partial run 에서 gen154~169 16건 연속 timeout 이 발생했고,
resume chunk 12쌍은 모두 정상 완료했다. 개별 pair 문제보다 warm pool lifetime 문제가
강하므로 공식 실행은 chunk lifetime 을 48쌍으로 제한한다.

## 8. P5 성공 기준 정정

P5 공식 run 의 성공 기준은 `gate_passed` 개수가 아니다.

- primary: coverage-map completion
- required fields: per-cell trade count, gross EV, net EV, MDD distribution
- `gate_passed_count`: advisory only
- P6 입력: `ai_strategy_loop.fitness.lift` 의 EV/lift/payoff 산출을 공식 smoke CSV에 연결

격자 seed 는 승격 후보가 아니라 지도용 seed 이므로, gate_passed=0 이 나오더라도
coverage map 이 완성되면 P5 는 다음 정제 판단으로 넘어갈 수 있다.

## 9. 금지 유지

- `lat_smoke_tick_full_sanitized_20260704*` 결과를 공식 생존/기각/P6 판단에 사용 금지.
- tick chunk08~chunk10 재개 금지.
- 이 profile-audit receipt 만으로 tick/min 288 full run 실행 금지.
- min 은 공식 tick export 완료 전 실행 금지.
- P6/P7/Plan D 실행 금지.
- CSS_V7 비-OPT 21건 완결 전략 재실행 금지.
- DB UPDATE/DELETE 금지.
- `git add -A` 금지.

## 10. 다음 해야 할 일

다음 범위는 **P5 official tick preflight only** 다. tick 288 full run 이 아니다.

```powershell
python -m ai_strategy_loop.scripts.claude_candidate_batch_eval `
  --pairs-json docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_preflight4_official_full_warm64_20260704.json `
  --config-json docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_tick_official_full_warm64_20260704.json `
  --run-id lat_preflight_tick_official_full_warm64_20260704
```

preflight 통과 조건:

1. warm64 prepare 성공.
2. 4쌍 결과가 honest `ok` / `no_trades` / `error` 로 기록되고 CSV/metrics 상태가 보존됨.
3. 실패 reason 의 실효 게이트가 `min_daily_trades 0.5`, `mdd_cap 35` 와 일치.
4. timeout streak 가 보이면 즉시 중단하고 chunk size 또는 timeout 재조정. 288 full run 금지.

preflight 통과 후에만 tick 288 공식 run 을 48쌍×6 chunk 로 진행한다. tick 공식 export가
정상 생성된 뒤에만 min preflight/min 공식 run 을 진행한다.
