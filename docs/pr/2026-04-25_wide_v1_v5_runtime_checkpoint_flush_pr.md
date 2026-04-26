# Wide v1 v5 runtime checkpoint flush PR

## 배경

`candidate_count=10` v5 재실행은 최종 actual row-set 대표 10개 확보가 목적이다. v5 내부에서는 대표 10개를 얻기 위해 후보 실행 수가 10개보다 많아질 수 있으며, 현재 로직 기준 `planned_v5_execution_count(requested_count=10, eligible_count>=20)`이면 최대 20개까지 실행한다.

중단된 실행에서는 `cand001`부터 `cand016`까지 진행됐고, 각 후보가 대략 2.5~3.2분 소요됐다. 따라서 해당 설정의 현실적 총 소요 시간은 약 45~65분이다. 문제는 실행 시간이 아니라, runtime JSON이 최종 종료 시점에만 기록되어 장시간 실행 중 현재 후보와 checkpoint를 확인할 수 없었다는 점이다.

## 변경 내용

- `run_research_iteration()`에서 주요 checkpoint마다 `status=running` runtime JSON을 즉시 flush한다.
- flush 지점:
  - `iteration_started`
  - `analysis_completed`
  - `candidate_pool_selected`
  - `candidate_started`
  - `candidate_succeeded`
  - `candidate_failed`
- 실행 중 checkpoint payload는 가볍게 유지한다.
  - 포함: config, failure_policy, candidate_specs, candidates, active_candidate, checkpoint_summary
  - 제외: analysis_result, expression_result, retention_selection, retention_candidates, baseline_result
- 최종 종료 시점의 full runtime JSON 기록은 기존 구조를 유지한다.
- `runtime_timing` 요약을 추가한다.
  - `checkpoint_durations`: checkpoint 사이의 경과 시간
  - `candidate_durations`: 후보별 조건식, 생성 source/feature, 후보 CSV, 거래 수, retention, 시작/완료/소요 시간
  - 실행 중 후보는 `status=running`, `active_candidate`와 같은 조건식을 노출한다.

## 검증

- 단위 테스트:
  - `python -m pytest tests/unit/test_research_loop.py::test_run_research_iteration_flushes_runtime_output_before_candidate_execution -q`
  - 결과: `1 passed`
- 관련 회귀 테스트:
  - `python -m pytest tests/unit/test_research_runtime_output.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py tests/unit/test_research_iteration_v5.py tests/unit/test_wide_v1_v5_analysis.py -q`
  - 결과: `167 passed`
- CLI smoke:
  - `WideV1IterationV5CheckpointSmoke_20260425`
  - runtime path: `backtest/temp/wide_v1_v5_checkpoint_flush_smoke_20260425.json`
  - 결과: runtime JSON 생성 확인, 프로세스 정리 확인

## 운영 기준

full v5 재실행은 다음 기준으로 진행한다.

1. `--runtime-output backtest\temp\wide_v1_iteration_v5_recovery_20260425.json`을 반드시 지정한다.
2. 실행 후 2~5분 안에 runtime JSON이 생성되지 않으면 중단하고 CLI 진입 실패로 본다.
3. 실행 중에는 아래 명령으로 진행 상황을 확인한다.

```powershell
@'
from pathlib import Path
from cli.research_v3_decision import read_runtime_json

p = Path("backtest/temp/wide_v1_iteration_v5_recovery_20260425.json")
data = read_runtime_json(p)
print(f"status={data.get('status')}")
print(f"phase={data.get('phase')}")
print(f"last_checkpoint={(data.get('checkpoint_summary') or {}).get('last_checkpoint')}")
print(f"event_count={(data.get('checkpoint_summary') or {}).get('event_count')}")
print(f"candidate_result_count={len(data.get('candidates') or [])}")
print(f"active_candidate={(data.get('active_candidate') or {}).get('strategy_name')}")
print(f"failure_policy={data.get('failure_policy')}")
print(f"actual_rowset_selection={data.get('actual_rowset_selection')}")
'@ | python -
```

4. `candidate_count=10` full v5의 예상 시간은 45~65분으로 잡는다.
5. MVP 종료 판단은 실행 시간보다 `actual_rowset_selection` 결과를 기준으로 한다.

후보별 조건식과 소요 시간은 아래 경로에서 확인한다.

```text
runtime_timing.candidate_durations
```

예시 필드:

```text
strategy_name=WideV1IterationV5Recovery_20260425__cand001
expression=<candidate condition expression>
source=<generation source>
feature=<generation feature>
trade_count=<candidate backtest trade count>
trade_count_retention=<candidate/base trade-count ratio>
duration_seconds=<candidate elapsed seconds>
```

## 다음 단계

이 PR이 병합되면 같은 v5 full run을 다시 실행한다. 이번에는 runtime JSON으로 후보 시작/성공/실패를 확인할 수 있으므로, 멈춘 것인지 정상 진행 중인지 5분 단위로 판단할 수 있다.
