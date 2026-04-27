# Wide v2 backtest iteration auto-improvement loop design

## Purpose

Wide v2의 목적은 Wide v1에서 만든 단일 라운드 후보 생성/백테스트/ranking 기반을 확장해, 조건식 개선이 실제로 닫힌 반복 루프로 동작하게 만드는 것이다.

최종 목표는 다음 흐름을 재현 가능한 CLI 연구 시스템으로 만드는 것이다.

```text
기준 조건식
-> 백테스트
-> 결과 기록
-> 데이터/퀀트 분석
-> 개선 후보 조건식 생성
-> 후보별 백테스트
-> best_candidate 선택
-> best_candidate를 다음 라운드 baseline으로 승격
-> 반복
-> 전체 leaderboard 기준 최종 후보 선택
-> 최종 후보만 WFO 검증
```

Wide v2는 실거래 운영 PR이 아니다. 또한 WFO를 inner loop로 다시 붙이는 PR도 아니다. Wide v2는 백테스트 반복 기반 조건식 자동 개선 루프를 먼저 설계하고, 마지막 검증 단계로 WFO를 분리한다.

## Background

Wide v1에서 완료된 범위:

```text
1. 백테스트 CSV 분석
2. 후보 조건식 생성
3. 후보 N개 백테스트
4. 후보 ranking
5. retention-aware selection
6. row-level 후보 차이 분석
7. score baseline 비교 가능성 보강
8. v3/v4/v5 후보 생성 및 row-set diversity gate
9. v5 actual row-set 대표 후보 선택
10. cand017 -> WideV1Final_B_20260425 영구 전략 재생성
11. WFO 검증
12. MVP freeze
13. post-MVP risk backlog 및 Wide v2 방향성 문서화
```

Wide v1에서 아직 완성하지 않은 범위:

```text
1. best_candidate를 다음 라운드 baseline으로 자동 승격
2. 여러 라운드 자동 반복
3. 라운드별 leaderboard 누적
4. 개선 정체 시 stop condition
5. final_best_candidate와 round_best_candidate 분리
6. Wide v2 전용 summary/report
```

현재 기준 브랜치:

```text
STOM_Version_2U_C @ c428d657
Wide v1 post-MVP risk backlog 및 향후 조건식 개선 로드맵
```

## Design choice

### Chosen approach: existing research loop reuse with a minimal optimizer coordinator

Wide v2 MVP는 기존 `discovery research`와 `run_research_iteration()`을 재사용하고, 그 위에 multi-round coordinator를 얹는다.

```text
Wide v2 optimizer coordinator
  -> round config 생성
  -> 기존 run_research_iteration() 호출
  -> round best 추출
  -> leaderboard 누적
  -> stop condition 평가
  -> 다음 round 또는 종료
```

이 방식을 선택한 이유:

- Wide v1에서 이미 검증한 후보 생성, 백테스트, ranking, runtime output, row-set 검증 경로를 재사용한다.
- 새 엔진을 처음부터 만들지 않으므로 실제 MVP 구현 범위가 작다.
- 조건식 자동 개선의 핵심인 "best -> next baseline -> next candidates" 루프를 가장 빨리 검증할 수 있다.
- WFO와 실거래 운영 검증을 섞지 않고, 연구 루프를 빠르게 유지한다.

### Rejected approach: full optimizer engine rebuild

`cli/research_optimizer.py`를 완전 독립 엔진으로 만들고 기존 v1 구조를 대체하는 방식은 이번 MVP에서 제외한다.

거절 이유:

- 구현량이 커진다.
- v1에서 이미 검증한 `research_loop.py` 계약을 다시 검증해야 한다.
- 현재 목표는 구조 재작성보다 자동 반복 개선 루프의 실제 동작 증명이다.

### Rejected approach: generic experiment framework

조건식/백테스트/검증을 일반 experiment framework로 추상화하는 방식도 이번 MVP에서 제외한다.

거절 이유:

- 장기 확장성은 좋지만 현재 목표보다 크다.
- 후보 조건식 자동 개선이라는 구체 목표가 흐려질 수 있다.
- 구현 완료까지 시간이 늘어난다.

## MVP scope

Wide v2 MVP에 포함한다:

```text
1. 2~3라운드 자동 반복
2. 라운드별 best_candidate 선택
3. best_candidate를 다음 round baseline/seed로 승격
4. 라운드별 후보 결과 leaderboard 누적
5. stop condition
6. JSON/Markdown summary
7. 최종 WFO 후보 handoff 정보
```

Wide v2 MVP에서 제외한다:

```text
1. 매 후보 또는 매 라운드 WFO 실행
2. 실거래 또는 paper trading
3. strategy.db에 중간 후보 영구 누적
4. 기존 Wide v1 freeze 결과 덮어쓰기
5. 대규모 cli 구조 리팩토링
6. 새 백테스트 엔진 구현
7. 모든 조건 변형 전략의 완전 자동 최적화
```

## User-facing CLI shape

Wide v2는 새 subcommand 또는 기존 `discovery research`의 별도 action으로 노출한다. 구현 계획에서 둘 중 하나를 확정한다.

권장 CLI 방향:

```powershell
python .\stom_backtest.py discovery optimize-wide-v2 `
  --name WideV2AutoLoop_20260426 `
  --base-buy-strategy WideV1Final_B_20260425 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --timeframe tick `
  --candidate-count 10 `
  --max-rounds 3 `
  --min-improvement 0.01 `
  --stop-after-no-improvement 2 `
  --runtime-output backtest\temp\wide_v2_auto_loop_20260426.json `
  --leaderboard-output backtest\temp\wide_v2_auto_loop_20260426_leaderboard.json `
  --report-path docs\research\condition_research\pilot_logs\2026-04-26_wide_v2_auto_loop_summary.md
```

대안 CLI:

```powershell
python .\stom_backtest.py discovery research WideV2AutoLoop_20260426 `
  --optimizer-mode wide_v2 `
  --max-rounds 3 `
  --candidate-count 10 `
  ...
```

MVP에서는 discoverability를 위해 새 action인 `discovery optimize-wide-v2`가 더 명확하다. 다만 구현 계획에서 `cli/subcommands.py`의 기존 parser 구조를 검토한 뒤 최종 선택한다.

## Architecture

### Existing modules to reuse

```text
cli/research_loop.py
  - ResearchLoopConfig
  - run_research_iteration()
  - candidate execution
  - ranking
  - cleanup
  - runtime output integration

cli/research_iteration_v2.py
cli/research_iteration_v3.py
cli/research_iteration_v4.py
cli/research_iteration_v5.py
  - 후보 생성 helper
  - row-set diversity helper
  - actual row-set representative selection

cli/research_report.py
  - 기존 Markdown report 구조 참고

cli/research_runtime_output.py
  - runtime JSON 기록 방식 참고

cli/subcommands.py
  - CLI parser와 action routing
```

### New modules

```text
cli/research_optimizer.py
  - Wide v2 multi-round coordinator
  - round 실행 순서 제어
  - run_research_iteration() 호출
  - stop condition 판단
  - final_best_candidate 선택

cli/research_optimizer_state.py
  - WideV2OptimizerConfig
  - WideV2RoundState
  - WideV2LeaderboardEntry
  - WideV2OptimizerResult
  - JSON-safe serialization helper

cli/research_optimizer_report.py
  - optimizer summary Markdown 생성
  - leaderboard Markdown 생성
  - WFO handoff section 생성
```

새 모듈은 coordinator/state/report 세 책임으로 나눈다. `research_loop.py`가 이미 크기 때문에 Wide v2 MVP에서 해당 파일을 크게 키우지 않는다.

## Core concepts

### round_best_candidate

한 라운드 안에서 가장 좋은 후보다.

```text
round_best_candidate:
  round_index
  strategy_name
  expression
  promotion_score
  adjusted_score
  trade_count
  retention
  actual_rowset_selected
```

용도:

- 다음 라운드 seed 후보
- 해당 라운드의 진행 결과 기록

### global_best_candidate

전체 라운드 후보 중 가장 좋은 후보다.

```text
global_best_candidate:
  best candidate across all rounds
```

용도:

- 최종 후보 선정
- WFO handoff 대상

마지막 라운드 best가 항상 global best는 아니다. 전체 leaderboard에서 선택해야 한다.

### wfo_candidate

Wide v2 loop가 최종적으로 WFO에 넘길 후보 정보다.

```text
wfo_candidate:
  strategy_name
  expression
  source_round
  source_candidate
  reason_selected
  next_command
```

Wide v2 loop 안에서는 WFO를 실행하지 않는다.

## Data flow

```text
initial input
  base_buy_strategy=WideV1Final_B_20260425
  sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
  date range
  candidate_count
  max_rounds
  stop condition

round 1
  build ResearchLoopConfig
  run_research_iteration(config)
  collect candidates
  select round_best_candidate
  append leaderboard entries
  evaluate stop condition

round 2
  previous round_best_candidate becomes seed
  build next ResearchLoopConfig
  run_research_iteration(config)
  collect candidates
  update leaderboard
  evaluate stop condition

round N
  repeat until max_rounds or stop condition

final
  compute global_best_candidate
  write optimizer summary
  write leaderboard
  emit WFO handoff candidate
```

## Round config generation

Each round constructs a `ResearchLoopConfig` from the optimizer config plus previous round output.

Round 1:

```text
base_buy_strategy = user-provided baseline
iteration_v2_best_candidate = optional seed strategy name
iteration_v2_best_expression = optional seed expression
iteration_v2_mode = best_feature_mix_v5 or chosen existing mode
```

Round 2+:

```text
iteration_v2_best_candidate = previous round best strategy_name
iteration_v2_best_expression = previous round best expression
score_reference_csv = previous round baseline/reference CSV if available
candidate_name_prefix = <run_name>__roundNNN
runtime_output_path = backtest/temp/<run_id>_roundNNN.json
```

The implementation plan must define the exact seed mapping from a `best_candidate` dict to `ResearchLoopConfig`. If an expression cannot be parsed into the existing v2/v3/v4/v5 helpers, the round must stop with `stop_reason=invalid_seed_expression` rather than guessing.

## Candidate improvement policy

Wide v2 MVP prioritizes controlled transformations:

```text
1. tighten
2. add
3. replace
```

Limited transformations:

```text
4. loosen
5. remove
```

`loosen` and `remove` can increase trade count but may degrade quality. They may be included as fallback candidate families but must not dominate the candidate pool in the MVP.

Candidate rules:

- Use only buy-time-available `B_*` features for generated conditions.
- Exclude identical expressions.
- Penalize very low trade retention.
- Keep actual row-set duplicate checks.
- Prefer candidates with enough trades and stable distribution.
- Do not treat `best_candidate` as final adoption.

## Leaderboard schema

The leaderboard must be JSON-safe and stable across runs.

Required fields:

```text
run_id
round_index
candidate_index
strategy_name
expression
source_baseline
source_candidate
candidate_type
status
promotion_passed
promotion_score
adjusted_score
score_basis
trade_count
trade_count_retention
date_concentration
symbol_concentration
actual_rowset_selected
selected_as_round_best
selected_as_global_best
runtime_json_path
candidate_csv_path
failure_phase
failure_message
```

Optional fields:

```text
rank
rank_score
retention_penalty
reference_promotion_score
incremental_promotion_score
row_set_identity_status
duplicate_actual_rowset_count
cleanup_reason
```

## Stop conditions

The optimizer stops when any of these conditions is met:

```text
max_rounds_reached
no_improvement
no_improvement_streak_reached
insufficient_candidates
duplicate_rowset_only
invalid_seed_expression
runtime_failure
```

Default MVP values:

```text
max_rounds=3
min_improvement=0.01
stop_after_no_improvement=2
candidate_count=10
max_consecutive_candidate_failures=3
```

Improvement is measured against the current global best, not just previous round best.

```text
improvement = current_round_best_score - previous_global_best_score
```

If score fields are missing or non-finite, the candidate cannot count as improvement.

## Output files

Runtime artifacts:

```text
backtest/temp/wide_v2_<run_id>_round001.json
backtest/temp/wide_v2_<run_id>_round002.json
backtest/temp/wide_v2_<run_id>_round003.json
backtest/temp/wide_v2_<run_id>_leaderboard.json
backtest/temp/wide_v2_<run_id>_summary.json
```

Committed summaries:

```text
docs/research/condition_research/pilot_logs/YYYY-MM-DD_wide_v2_<run_id>_summary.md
docs/research/condition_research/pilot_logs/YYYY-MM-DD_wide_v2_<run_id>_leaderboard.md
```

Runtime JSON under `backtest/temp` is evidence and should not be committed by default. Curated Markdown summaries under `docs/` may be committed when they are part of the PR report.

## Markdown report content

The Wide v2 summary report must include:

```text
1. run configuration
2. initial baseline
3. round count
4. round-by-round summary
5. round best candidates
6. global leaderboard top candidates
7. final_best_candidate
8. stop_reason
9. WFO handoff candidate
10. next command for WFO validation plan
```

The report must explicitly state:

```text
WFO was not run inside the optimizer loop.
The final candidate is a WFO candidate, not a live-trading approval.
```

## Error handling

### Invalid seed expression

If previous best expression cannot be parsed by existing candidate generation helpers:

```text
status=error
stop_reason=invalid_seed_expression
failed_round=<round_index>
```

The optimizer must keep the previous global best and write a summary.

### Candidate shortfall

If a round cannot generate or select enough candidates:

```text
stop_reason=insufficient_candidates
requested_candidate_count=<n>
selected_candidate_count=<m>
```

### Runtime failure

If `run_research_iteration()` returns an error:

```text
stop_reason=runtime_failure
failure_phase=<phase>
failure_message=<message>
```

The optimizer must write any completed round state before returning.

### No improvement

If current round best does not improve over global best by `min_improvement`:

```text
round_improved=false
no_improvement_streak += 1
```

Stop when `no_improvement_streak >= stop_after_no_improvement`.

## Testing strategy

Unit tests:

```text
tests/unit/test_research_optimizer_state.py
  - config defaults
  - leaderboard entry serialization
  - global best selection
  - JSON-safe non-finite normalization

tests/unit/test_research_optimizer.py
  - 2-round happy path with mocked run_research_iteration
  - previous best becomes next round seed
  - max_rounds stop
  - no_improvement stop
  - invalid_seed_expression stop
  - runtime_failure stop preserves completed rounds

tests/unit/test_research_optimizer_report.py
  - summary contains round table
  - leaderboard contains global best
  - report states WFO not run
  - report includes WFO handoff candidate

tests/unit/test_subcommands.py
  - CLI parses optimize-wide-v2 options
  - handler passes config fields to optimizer
```

Smoke test after implementation:

```powershell
python .\stom_backtest.py discovery optimize-wide-v2 `
  --name WideV2Smoke_YYYYMMDD `
  --base-buy-strategy WideV1Final_B_20260425 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --candidate-count 2 `
  --max-rounds 2 `
  --candidate-timeout 900 `
  --runtime-output backtest\temp\wide_v2_smoke_YYYYMMDD.json
```

Full research run after smoke:

```powershell
python .\stom_backtest.py discovery optimize-wide-v2 `
  --name WideV2AutoLoop_YYYYMMDD `
  --base-buy-strategy WideV1Final_B_20260425 `
  --sell ResearchTest_Tick_S_090000_092800_Wide_20260419 `
  --start 20250101 `
  --end 20251231 `
  --candidate-count 10 `
  --max-rounds 3 `
  --candidate-timeout 1800 `
  --runtime-output backtest\temp\wide_v2_auto_loop_YYYYMMDD.json
```

## Verification commands for implementation PRs

Focused tests:

```powershell
python -m pytest tests/unit/test_research_optimizer_state.py tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_subcommands.py -q
```

Research regression tests:

```powershell
python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q
```

Repository checks:

```powershell
python scripts/verify_nonrelease_sync.py
git diff --check --ignore-cr-at-eol
```

## Implementation decomposition

The implementation should be split into multiple PRs.

### PR 1: optimizer state and leaderboard

Deliverables:

- `cli/research_optimizer_state.py`
- state dataclasses or TypedDict-compatible helpers
- leaderboard entry construction
- global best selection
- JSON-safe serialization
- unit tests

### PR 2: optimizer coordinator

Deliverables:

- `cli/research_optimizer.py`
- multi-round runner
- mocked `run_research_iteration()` tests
- stop condition handling
- round seed propagation

### PR 3: reporting

Deliverables:

- `cli/research_optimizer_report.py`
- Markdown summary
- leaderboard report
- WFO handoff section
- report tests

### PR 4: CLI connection

Deliverables:

- `stom_backtest.py`/`cli/subcommands.py` route
- `discovery optimize-wide-v2` parser
- handler tests
- smoke command documentation

### PR 5: actual smoke and research run

Deliverables:

- smoke runtime evidence under `backtest/temp` not committed by default
- curated summary under `docs/research/condition_research/pilot_logs/`
- PR report with next WFO validation plan if final candidate is selected

## Acceptance criteria

Wide v2 design is complete when:

- The spec clearly states that WFO is final validation only.
- The MVP scope is limited to 2~3 round automatic backtest iteration.
- The design reuses existing `run_research_iteration()` rather than replacing the research system.
- The design defines round state, leaderboard, stop conditions, and WFO handoff.
- The design includes explicit non-goals and protected paths.
- The implementation decomposition is small enough for PR-by-PR execution.

## Non-goals and guardrails

- Do not run WFO inside the optimizer loop.
- Do not claim live-trading profitability.
- Do not modify `utility/strategy.db` as a tracked artifact.
- Do not commit raw `backtest/temp` runtime JSON by default.
- Do not overwrite Wide v1 freeze reports or WFO evidence.
- Do not commit directly to `STOM_Version_2U_C`; use feature branches and PRs.
- Do not perform broad `cli/` refactoring in the first Wide v2 MVP PR.
