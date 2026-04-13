# 2026-04-13 백테스트 공유메모리 수명 복구

## 증상

- GUI 백테스트 실행 직후 여러 worker에서 공유메모리 조회 실패가 발생했다.
- 대표 오류:
  - `FileNotFoundError: [WinError 2] 지정된 파일을 찾을 수 없습니다: 'backdata_4'`
  - `FileNotFoundError: [WinError 2] 지정된 파일을 찾을 수 없습니다: 'backdata_15'`
  - `FileNotFoundError: [WinError 2] 지정된 파일을 찾을 수 없습니다: 'backdata_19'`
- 오류 위치는 `BackEngineBase.GetArrayData()`의 `shared_memory.SharedMemory(name=shared_info['shm_name'])` 호출이었다.

## 원인

- `STOM_Version_2U_C`의 shared memory cleanup hardening이 정상 백테스트 1회 완료 시 worker의 `CleanupSharedMemory()`를 호출했다.
- `backdata_N`은 개별 worker가 생성하지만, 실행 중에는 모든 worker가 전체 `shared_info` 목록을 나눠 처리한다.
- 먼저 끝난 worker가 자기 segment를 unlink하면, 나중에 해당 segment의 `shared_info`를 잡은 다른 worker가 `FileNotFoundError`를 낸다.
- 공식 `STOM_Version_2`와 `STOM_Version_2U`는 정상 백테스트 완료 시 shared memory를 즉시 unlink하지 않는다.

## 해결

- `BackTest()` 정상 완료에서는 공유메모리를 삭제하지 않게 했다.
- `BackStop()`의 명시적 엔진 중지 cleanup은 유지했다.
- CLI는 one-shot 실행 후 parent process가 `shared_info` 기준으로 unique `shm_name`을 정리하도록 했다.
- CLI cleanup은 중복 `shm_name`을 한 번만 unlink하고, 이미 사라진 segment는 `FileNotFoundError`로 무시한다.

## 브랜치 반영

| 브랜치 | 판단 | 반영 |
| --- | --- | --- |
| `STOM_Version_2` | 공식 수명 계약 정상 | 미반영 |
| `STOM_Version_2U` | 공식 수명 계약 정상 | 미반영 |
| `STOM_Version_2U_C` | shared memory 조기 삭제 문제 존재 | 반영 |
| `research/init` | 하위 전파 대상 | 전파 예정 |
| `integration/adopt-cli-v267-into-2uc` | 비활성 보관 브랜치 | 제외 |

## 검증

- `python -m pytest tests/unit/test_backengine_shared_memory_cleanup.py -q` -> `3 passed`.
- `python -m pytest tests/unit/test_runner_helpers.py -q` -> `30 passed`.
- `python -m pytest tests/unit/test_backengine_shared_memory_cleanup.py tests/unit/test_runner_helpers.py -q` -> `33 passed`.
- `python -m pytest tests/unit/ -q` -> `840 passed, 1 skipped, 10 warnings`.
- `python scripts/verify_nonrelease_sync.py` -> passed all guardrails.
- CLI long-window minute backtest:
  - Command: `python stom_backtest.py --buy Min_B_Study_251227 --sell Min_S_Study_251227 --start 20250401 --end 20251231 --timeframe min --avg-time 30 --engines 20 --start-time 090000 --end-time 151800 --timeout 1200 --format json --quiet`
  - Result: success, `trade_count=6323`, `win_rate=29.97`, `avg_profit_pct=-0.82`, `total_profit_pct=-192.53`, `total_profit_krw=-51505189`.
- Process check after CLI run found no new multiprocessing-fork children from the completed CLI run. Two older unrelated Python multiprocessing children were already present before the run and remained outside this verification scope.

## GUI 재검증 상태

- 이전 GUI 재현은 `backdata_N` shared memory가 실행 중 삭제되는 문제를 확인했다.
- 코드 수정 후 GUI 재실행은 사용자 재검증 대기 상태다.
- 기대 결과:
  - `backdata_N` `FileNotFoundError`가 발생하지 않아야 한다.
  - `09:00~15:18`, 분봉, 평균틱수 `30`, 멀티 `20`, `Min_B_Study_251227` / `Min_S_Study_251227` 조건에서 no-buy 메시지로 붕괴하지 않아야 한다.
  - CLI 기준 `trade_count=6323`과 비교 가능한 결과가 나와야 한다.
