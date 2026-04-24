# Wide v1 Iteration Loop v5 실행 로그

## 목적

Wide v1 v5에서 `best_feature_mix_v5`와 `candidate_count=10`을 실제 실행해, v4의 proxy row-set 선택 이후 실제 백테스트 CSV 기준 actual row-set 대표 10개를 확보할 수 있는지 검증한다.

## 고정 입력

- 실행 브랜치: `feature/wide-v1-v5-candidate-count-10-runtime-validation`
- 실행 모드: `best_feature_mix_v5`
- 요청 후보 수: `candidate_count=10`
- 후보 pool multiplier: `3`
- planned execution 목표: v5 oversampling 후 actual row-set 대표 선별
- 입력 CSV: `C:\System_Trading\STOM\STOM_V.wt-wide-v2\backtest\csv\stock_bt_WideV1IterationV2_20260423__cand005_20260423103750.csv`
- score reference CSV: `C:\System_Trading\STOM\STOM_V.wt-wide-cli-compare\backtest\csv\stock_bt_ResearchTest_Tick_B_090000_092800_Wide_20260419_20260422203947.csv`
- base buy strategy: `WideV1IterationV2_20260423__cand005`
- sell strategy: `ResearchTest_Tick_S_090000_092800_Wide_20260419`
- 기간: `20250101` - `20251231`
- 시간: `090000` - `092800`
- timeframe: `tick`
- engines: `32`
- candidate timeout: `900`

## Preflight

`runtime-preflight` 결과는 정상이다.

```text
status=ok
failed_checks=[]
validation_errors=[]
```

따라서 입력 파일, 전략 DB, setting DB, backtest DB, tick back DB 접근성은 v5 실행 전 기준으로 문제가 없었다.

## 실제 실행 결과

실행 시작 시각은 `2026-04-24 22:53:03 KST`로 확인되었다.

생성된 candidate CSV는 다음 7개다.

| candidate | CSV 생성 시각 | 크기 |
| --- | --- | ---: |
| cand001 | 2026-04-24 22:55:21 | 9,610,518 bytes |
| cand002 | 2026-04-24 22:57:36 | 8,063,448 bytes |
| cand003 | 2026-04-24 23:00:04 | 9,551,453 bytes |
| cand004 | 2026-04-24 23:02:44 | 9,828,181 bytes |
| cand005 | 2026-04-24 23:05:29 | 9,828,180 bytes |
| cand006 | 2026-04-24 23:08:03 | 8,125,600 bytes |
| cand008 | 2026-04-25 06:22:00 | 9,720,750 bytes |

`cand007` CSV는 생성되지 않았다. `cand008` 생성 이후에는 parent process와 worker process가 남아 있었지만, 10분 이상 CPU 증가와 CSV 추가 생성이 없었다.

## Runtime JSON

목표 runtime 파일은 생성되지 않았다.

```text
backtest\temp\wide_v1_iteration_v5_20260424.json
```

상태:

```text
exists=False
```

이는 actual row-set 대표 선별 결과를 신뢰 가능한 JSON 구조로 평가할 수 없다는 뜻이다.

## 프로세스 상태

v5 실행 parent process는 다음 명령으로 확인되었다.

```text
python .\stom_backtest.py discovery research WideV1IterationV5_20260424 ... --iteration-v2-mode best_feature_mix_v5
```

parent PID는 `96696`이었고, worker process들은 `parent_pid=96696`의 multiprocessing fork 형태로 남아 있었다. `cand008` 이후 worker CPU와 파일 수정 시간이 멈춘 상태였으므로, 실행을 완료로 볼 수 없다.

잔여 v5 프로세스는 정리했다. unrelated `uvicorn src.api.app:app --port 8625` 프로세스는 v5 실행 프로세스가 아니므로 건드리지 않았다.

## 판정

결정:

```text
HOLD_V5_RUNTIME_FAILURE
```

이 판정은 actual row-set 다양성이 부족하다는 의미가 아니다. actual row-set 판정에 필요한 완료 runtime JSON이 생성되지 않았으므로, v5 selector 품질을 판단할 수 없는 상태라는 의미다.

## 퀀트 관점

이 상태에서 promote나 WFO로 진행하면 안 된다. 후보 10개가 실제 trade row-set 기준으로 서로 다른 대표인지 확인되지 않았고, 일부 후보만 생성된 partial run을 성과 검증 근거로 사용할 수 없다.

현재 증거는 전략 성능 문제가 아니라 실행 안정성 문제다. 다음 단계는 조건식 생성 규칙을 더 복잡하게 만드는 것이 아니라, 장시간 후보 실행 중 timeout, worker cleanup, runtime checkpoint를 안정화하는 것이다.

## CLI 개발 관점

이번 실패는 CLI 연구 루프에 다음 보강이 필요함을 보여준다.

- candidate별 진행 상태를 runtime checkpoint로 누적 저장해야 한다.
- parent shell timeout이나 stdout capture 실패가 발생해도 중간 실행 결과를 복구할 수 있어야 한다.
- candidate timeout 발생 시 nested multiprocessing worker까지 정리되어야 한다.
- `discovery research` 결과를 stdout `Tee-Object`에만 의존하지 않고 명시적 output file로 저장할 수 있어야 한다.

## 다음 단계

다음 추천 브랜치:

```text
feature/wide-v1-v5-runtime-failure-recovery
```

다음 추천 명령:

```text
$brainstorming Wide v1 v5 runtime failure recovery 설계
```

