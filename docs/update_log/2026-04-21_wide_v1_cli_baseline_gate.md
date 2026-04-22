# 2026-04-21 Wide v1 CLI Baseline Gate

## 목적

runtime-preflight가 통과한 ResearchTest wide 조건식을 CLI로 1회 baseline 백테스트하고, GUI 기준 결과와 비교해 후보 5개 루프 진입 가능 여부를 판단했다.

## 전체 흐름

```text
[완료] runtime-preflight
        |
        v
[이번 작업] CLI baseline 1회 백테스트
        |
        v
[이번 작업] GUI 결과와 비교 시도
        |
        v
[판정] FAIL
```

## 실행 결과 요약

```text
preflight_status=ok
preflight_failed_checks=[]
cli_command_exit_code=124
external_timeout_ms=964079
cli_result_json_created=False
cli_status=not_available
csv_path=None
checkpoint_status=not_available
last_checkpoint=not_available
cli_back_count=not_present_no_result_json
cli_trade_count=not_present_no_result_json
decision=FAIL
```

## 판정 근거

- `runtime-preflight`는 통과했으므로 전략 DB, 설정 DB, tick DB 경로와 ResearchTest wide 조건식 자체는 CLI에서 정상 확인되었다.
- CLI baseline 명령은 `--timeout 900`을 지정했지만 외부 실행 제한 약 964초까지 정상 종료하지 못했다.
- 결과 JSON과 신규 CSV가 생성되지 않아 GUI 기준값 `back_count=1638`, `trade_count=40937`과 비교할 수 없었다.
- 실패 후 `backdata_0..31` shared memory 잔여가 확인되어 runner가 데이터 공유 단계까지는 진행했을 가능성이 있다.

## 전체 계획상 위치

```text
[완료] Wide v1 GUI/STOM 백테스트 성공
        |
        v
[완료] CLI/GUI runtime-preflight
        |
        v
[실패] CLI baseline 1회 백테스트 Gate
        |
        v
[다음] CLI baseline failure checkpoint 분석
        |
        v
[보류] Wide v1 Retention-Aware 후보 5개 실행
```

## 남은 리스크

- 후보 5개 백테스트는 아직 실행하면 안 된다.
- CLI baseline이 JSON 결과를 만들지 못했기 때문에 GUI/CLI 수치 비교는 아직 불가능하다.
- `--timeout 900`이 BackTest child process join 구간에만 적용되고, 그 이전 데이터 로딩 또는 queue 대기 hang을 잡지 못할 가능성이 있다.
- shared memory 잔여가 Windows에서 즉시 해제되지 않아 다음 실행을 방해할 수 있다.
- GUI/STOM 실행 경로와 CLI runner의 engine/data loading protocol 차이를 분석해야 한다.

## 다음 단계

```text
$brainstorming CLI baseline backtest failure checkpoint 분석 설계
```

다음 브레인스토밍에서 결정할 것:

```text
1. CLI runner가 실제로 어느 단계에서 blocking되는지 계측하는 방법
2. backQ.get() / data loading 대기 구간 timeout 추가 필요 여부
3. shared memory cleanup을 Windows에서 안정화하는 방법
4. GUI runner와 CLI runner의 실행 protocol 차이 비교
5. 짧은 smoke 기간으로 재현할지, 동일 2025 전체 조건으로 재현할지
6. baseline gate를 통과시키기 위한 최소 보강 범위
```
