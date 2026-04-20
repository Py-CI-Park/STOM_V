# 2026-04-20 CLI/GUI Tick Backtest Parity Preflight

## 목적

CLI 자동 연구 루프를 재개하기 전에 GUI/STOM Wide v1 tick 백테스트와 CLI 실행 환경의 정합성을 확인하기 위한 preflight 변경과 검증 결과를 기록한다.

## 전체 흐름

```text
[Wide v1 GUI/STOM 백테스트 성공]
        |
        v
[CLI/GUI Tick Backtest Parity Preflight]
        |
        v
[CLI baseline 1회 검증]
        |
        v
[Wide v1 Retention-Aware 후보 5개 실행]
        |
        v
[반복 개선 루프 v2]
        |
        v
[최종 promote/WFO 검증]
```

단일 라인 흐름:

```text
[Wide v1 GUI/STOM 백테스트 성공] -> [CLI/GUI Tick Backtest Parity Preflight] -> [CLI baseline 1회 검증] -> [Wide v1 Retention-Aware 후보 5개 실행] -> [반복 개선 루프 v2] -> [최종 promote/WFO 검증]
```

## 변경 사항

- `cli/runtime_preflight.py` 추가
- `runtime-preflight` CLI 명령 추가
- `cli/backtest_checkpoints.py` 추가
- `cli.runner.run_backtest()` timeout checkpoint 필드 연결
- runtime preflight, subcommand, checkpoint 테스트 추가

## 검증 결과

### focused tests: PASS

```powershell
python -m pytest tests/unit/test_runtime_preflight.py tests/unit/test_backtest_checkpoints.py tests/unit/test_subcommands.py tests/unit/test_runner_helpers.py -q
```

결과:

```text
107 passed in 7.86s
```

### full unit tests: PASS

```powershell
python -m pytest tests/unit/ -q
```

결과:

```text
1013 passed, 1 skipped, 10 warnings in 74.45s (0:01:14)
```

### verify_nonrelease_sync.py: PASS

```powershell
python scripts/verify_nonrelease_sync.py
```

결과:

```text
모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.
```

## 남은 위험

- 이 작업에서는 실제 Wide v1 `candidate_count=5` 백테스트를 실행하지 않았다.
- CLI baseline 1회 결과와 GUI 결과 비교는 후속 작업이다.
- `strategy.db`가 다시 `????` 형태로 손상되면 preflight가 반드시 차단해야 한다.
- feature worktree의 heavy tick 실행은 명시적인 runtime profile이 정해질 때까지 제한된다.

## 다음 단계

1. `wt-dev`에서 `runtime-preflight` 실행
2. `ResearchTest` wide 조건식 코드 정상성 확인
3. CLI baseline 1회 백테스트 실행
4. GUI 기준 결과와 비교
5. 통과 시 Wide v1 Retention-Aware 후보 5개 실행 재개
