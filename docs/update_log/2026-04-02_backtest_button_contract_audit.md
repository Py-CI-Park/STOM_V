# 2026-04-02 백테스트 버튼 계약 불일치 RCA

## 개요

이 문서는 `C:\System_Trading\STOM\STOM_V.wt-dev`에서 확인된 백테스트 버튼 클릭 실패 문제를 기록한다. 백테스트 엔진 자체는 먼저 정상 구동되지만, 버튼 클릭 시 `BackTest` 프로세스 생성 단계에서 생성자 계약이 맞지 않아 즉시 종료되는 상태를 다룬다.

이번 RCA의 1차 분석 대상은 다음 파일이다.

- `ui/ui_button_clicked_editer_stock.py`
- `ui/ui_button_clicked_editer_coin.py`
- `ui/ui_button_clicked_dialog_backengine.py`
- 계약 기준 파일: `backtest/backtest.py`

텔레그램 polling 오류, `httpx.ConnectError`, `get_korean_stocks`, `get_market_indicator`, `get_crypto_data` 네트워크 예외는 이번 RCA의 1차 원인에서 제외한다. 이들은 같은 시점에 출력된 병렬 잡음으로 취급한다.

## 증상

- 핵심 오류는 다음과 같다.
  - `TypeError: BackTest.__init__() takes 13 positional arguments but 25 were given`
- 백테스트 엔진은 먼저 정상적으로 구동된다.
- 실패 지점은 엔진 구동 이후 사용자가 백테스트 버튼을 눌러 `Process(target=BackTest, args=...)` 경로를 타는 단계다.
- 버튼 클릭 경로에서 `BackTest`에 긴 인자 목록을 직접 넘기고, 실제 `BackTest.__init__` 시그니처는 더 짧기 때문에 생성 시점에서 즉시 `TypeError`가 발생한다.

## 원인

- 직접 원인은 호출 측과 대상 클래스 간 생성자 계약 불일치다.
- 버튼 클릭 코드 쪽은 과거 방식처럼 `betting`, `avgtime`, `startday`, `endday`, `starttime`, `endtime`, `buystg`, `sellstg`, `dict_cn`, `back_count`, `bl`, `schedul`, `back_club` 등을 생성자 인자로 직접 넘긴다.
- 그러나 현재 `backtest/backtest.py`의 `BackTest` 구현은 이 값을 생성자에서 받지 않고, 내부 큐(`self.bq.get()`)를 통해 후속 페이로드로 읽도록 설계돼 있다.
- 즉 현재 코드는 “실행 파라미터는 큐로 전달한다”는 계약과 “생성자 인자로 직접 전달한다”는 계약이 혼재된 상태다.

## 해결 방향

- 기준 계약은 현재 `backtest/backtest.py` 구현에 맞춰 단일화한다.
- `BackTest.__init__`를 다시 옛 긴 시그니처로 넓히지 않고, 버튼 클릭 호출자 쪽 `Process(target=BackTest, args=...)`를 현재 계약에 맞게 줄이는 방향을 우선 적용한다.
- 우선 수정 대상은 다음 세 파일의 `BackTest` 생성 경로다.
  - `ui/ui_button_clicked_editer_stock.py`
  - `ui/ui_button_clicked_editer_coin.py`
  - `ui/ui_button_clicked_dialog_backengine.py`
- 동일한 계약 불일치가 `STOM_Version_2U`, `STOM_Version_2U_C`, `research/init`에도 있으면 같은 방식으로 반영한다.

## 검증 결과

아래 결과는 `wt-dev`에서 직접 확인한 현재 기준이다.

| 항목 | 결과 |
|------|------|
| 관련 모듈 import smoke | `python -c "import importlib; importlib.import_module('backtest.backtest'); importlib.import_module('ui.ui_button_clicked_editer_stock'); importlib.import_module('ui.ui_button_clicked_editer_coin'); importlib.import_module('ui.ui_button_clicked_dialog_backengine'); print('import-smoke: ok')"` 실행 결과 `import-smoke: ok` |
| `python -m pytest tests/unit/test_backtest_button_contract.py -q` | 아직 파일 부재로 미실행 |
| `python -m pytest tests/unit/test_backtest_spawn_contract_audit.py -q` | 아직 파일 부재로 미실행 |
| `python -m pytest tests/unit/ -q` | 현재 기준 전체 단위 테스트는 통과 상태 |
| backtest button start smoke | 이번 문서 작업 범위에서는 미실행. 계약 테스트 추가 후 별도 확인 예정 |

## 워크트리 감사 매트릭스

| 워크트리 | 동일 문제 존재 여부 | 근거 | 반영 필요 여부 | 실제 반영 여부 |
| --- | --- | --- | --- | --- |
| STOM_Version_2U | 미존재 | `BackTest.__init__` 자체가 긴 시그니처여서 버튼 호출과 계약이 일치함 | 불필요 | 미반영 |
| STOM_Version_2U_C | 미존재 | `BackTest.__init__` 자체가 긴 시그니처여서 버튼 호출과 계약이 일치함 | 불필요 | 미반영 |
| research/init | 존재 | 버튼 호출자는 긴 인자 리스트를 사용하지만 `BackTest.__init__`는 짧은 큐 기반 계약을 사용함 | 필요 | 반영함 (`f674e95`) |

- `STOM_Version_2U`: 버튼 클릭 경로는 오래된 긴 호출 패턴이지만, 해당 워크트리의 `BackTest.__init__`도 같은 긴 계약을 유지하고 있어 이번 오류와 동일한 계약 불일치는 아니었다. 따라서 반영하지 않았다.
- `STOM_Version_2U_C`: `2U`와 동일하게 생성자와 호출자가 모두 긴 계약을 유지해, 이번 `wt-dev` 오류와 같은 short-ctor/long-caller 불일치는 아니었다. 따라서 반영하지 않았다.
- `research/init`: `wt-dev`와 같은 short-ctor/long-caller 불일치가 실제로 재현되었고, 같은 호출자 정리 방식으로 수정했다. 계약 테스트 `3 passed`, 인접 회귀 세트 `8 passed`, `py_compile` 통과 후 `f674e95`로 반영했다.
