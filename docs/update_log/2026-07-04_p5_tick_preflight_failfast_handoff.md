# 2026-07-04 P5 Tick Official Preflight Fail-Fast Handoff

## 1. 결론

P5 official tick preflight 4페어는 공식 DB 전체기간 + warm64 프로파일에서 실행 증거를 확보했다. warm64 prepare 는 통과했고, 4개 preflight 페어 모두 honest `ok` row 를 기록했다. 다만 4/4 모두 `gate_passed=false` 이며 MDD/손익 훼손이 크므로 tick 288 full run 은 계속 금지한다.

추가로 `retry01` 의 4번째 페어 진행 중 warm timeout recovery/reload 대기 비용이 과도하게 커지는 운영 결함을 확인했다. 이를 위해 `claude_candidate_batch_eval` 에 `--fail-fast-timeout` 옵션을 추가했고, timeout 발생 시 error row 를 기록한 뒤 warm-pool 재로딩 장기 대기를 생략하도록 했다.

## 2. 실행 증거

| 항목 | 값 |
|---|---|
| 공식 config | `docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_config_tick_official_full_warm64_20260704.json` |
| 4페어 원장 | `docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_preflight4_official_full_warm64_20260704.json` |
| gen3 supplement 원장 | `docs/research/condition_research/research_runs/seed_lattice_20260702/pairs_tick_preflight_gen3_official_full_warm64_20260704.json` |
| receipt | `docs/research/condition_research/research_runs/seed_lattice_20260702/p5_tick_preflight_official_full_warm64_20260704_receipt.json` |
| retry01 | `lat_preflight_tick_official_full_warm64_20260704_retry01` |
| gen3 retry02 | `lat_preflight_tick_official_full_warm64_20260704_gen3_retry02` |
| warm prepare retry01 | `status=ok`, `back_count=2424`, `elapsed=295s` |
| warm prepare gen3 retry02 | `status=ok`, `back_count=2424`, `elapsed=347s` |

## 3. Preflight row 요약

| source | label | status | gate | trades | daily | MDD | profit | reason |
|---|---|---|---:|---:|---:|---:|---:|---|
| retry01 gen0 | `tick_0900_small_low:momentum_breakout` | ok | false | 1712 | 1.8 | 280.14 | -42,046,738 | `mdd 280.1 > mdd_cap 35` |
| retry01 gen1 | `tick_0910_small_low:momentum_breakout` | ok | false | 358 | 0.4 | 181.44 | -9,158,599 | `daily_avg_trades 0.4 < min_daily_trades 0.5` |
| retry01 gen2 | `tick_0920_small_low:momentum_breakout` | ok | false | 139 | 0.1 | 53.41 | -2,497,875 | `daily_avg_trades 0.1 < min_daily_trades 0.5` |
| gen3 retry02 | `tick_0925_large_high:volume_surge` | ok | false | 1742 | 1.8 | 263.65 | -39,386,976 | `mdd 263.6 > mdd_cap 35` |

## 4. 운영 결함과 수정

`retry01` 은 gen3 진행 중 오래 대기했다. 원인은 timeout 이후 warm-session recovery/reload 가 전체 DB warm64 재로딩 비용을 다시 치르는 구조다. preflight 에서는 timeout 자체가 중단 신호이므로 장기 recovery 는 불필요하다.

수정:

- `cli/warm_session.py`: `WarmBacktestSession.run(..., recover_on_timeout=True)` 파라미터 추가.
- `recover_on_timeout=False` 일 때 timeout 된 BackTest 를 kill 하고 warm pool 을 닫은 뒤 recordable error result 를 반환.
- `ai_strategy_loop/scripts/claude_candidate_batch_eval.py`: `--fail-fast-timeout` 옵션 추가.
- fail-fast timeout error 발생 시 batch 를 중단.
- 테스트: `pytest tests/unit/test_warm_session_window.py tests/unit/test_lattice_p5_batch_repair.py tests/unit/test_plan_b_p5_profile_audit.py -q` → 19 passed.

## 5. 판정

P5 tick preflight 는 실행됐지만 tick 288 full run 은 아직 진행하면 안 된다.

이유:

1. 4페어 모두 `gate_passed=false`.
2. 2개 고빈도 페어는 MDD 가 260% 이상으로 비정상적으로 크다.
3. 격자 seed 가 지도용 seed 라는 기존 결론은 유지되지만, full 288 을 바로 실행하기 전 chunk objective 를 coverage-map 중심으로 고정하고 timeout fail-fast 운영을 commit/review 해야 한다.
4. `retry01` run row 는 프로세스 kill 로 `running` 상태가 남아 있으나 공식 판단은 receipt 의 3개 completed generation row 만 사용한다. DB UPDATE/DELETE 금지 때문에 상태를 수동 보정하지 않았다.

## 6. 다음 순서

1. 이번 fail-fast 코드/문서/receipt 를 커밋한다.
2. Ultragoal G001 은 preflight evidence 로 checkpoint 한다.
3. G002 tick 288 은 아직 바로 실행하지 않는다. 먼저 chunk size/timeout/fail-fast 정책을 공식 full-run 명령에 반영하고, 첫 chunk 를 48보다 더 작은 pilot chunk 로 낮출지 결정해야 한다.
4. min/P6/P7/Plan D 는 계속 금지다.

## 7. 금지 유지

- `lat_smoke_tick_full_sanitized_20260704*` 공식 판단 사용 금지.
- tick chunk08~chunk10 재개 금지.
- tick 288 full 즉시 실행 금지.
- min은 tick 공식 export 전 실행 금지.
- P6/P7/Plan D 조기 실행 금지.
- CSS_V7 non-OPT 21건 완결 전략 재실행 금지.
- DB UPDATE/DELETE 금지.
- `git add -A` 금지.
