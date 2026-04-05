# 2026-04-01 wt-dev 런타임 회귀 RCA 및 워크트리 감사 로그

## 개요

이 문서는 `C:\System_Trading\STOM\STOM_V.wt-dev`에서 2026-04-01 기준으로 확인된 런타임 회귀 4건만 기록한다. 범위는 이미 검증이 끝난 wt-dev 사례로 한정하며, 다른 워크트리의 세부 판정은 본 문서 하단의 감사 매트릭스에 후속 기록 대상으로 남긴다.

이번 RCA 대상은 다음 4건이다.

1. V2.70 이후 삭제된 지수 차트 참조 잔존
2. `utility.static` 호환 심볼 `summer_time`, `get_profile_text` 누락
3. QThread 전환 이후 홈 탭 WebCrawling 전달 경로 불일치
4. 종료 경로의 `qtimer0` 잔존 참조

검증은 단위 테스트, 모듈 import 확인, 짧은 `stom.py` 기동 확인으로 수행했다.

## 문제 1. V2.70 이후 삭제된 지수 차트 참조 잔존

### 증상

- `ui/ui_mainwindow.py`에 삭제된 지수 차트 모듈 `ui.ui_draw_jisuchart` import 흔적이 남아 있으면 `ui.ui_mainwindow` import 단계에서 런타임 오류가 발생할 수 있었다.
- `ui/ui_mainwindow.py`의 `DrawRealJisuChart`, `show_jisu` 참조와 `ui/ui_process_kill.py`의 `dialog_jisu` 종료 참조는 이미 제거된 기능을 계속 가리키는 잔존 코드였다.

### 원인

- V2.70 이후 지수 차트 기능이 제거됐지만, 관련 import와 UI 종료 경로 참조가 완전히 정리되지 않은 상태로 남아 있었다.
- 삭제 대상 심볼이 여러 파일에 분산되어 있어 한 파일만 정리하면 끝나는 종류의 회귀가 아니었다.

### 해결

- `ui/ui_mainwindow.py`에서 삭제된 지수 차트 import 및 `DrawRealJisuChart`, `show_jisu` 참조를 제거했다.
- `ui/ui_process_kill.py`에서 삭제된 대화상자 `dialog_jisu` 참조를 제거했다.

### 검증

- `tests/unit/test_ui_jisu_cleanup.py`로 다음 잔존 참조 부재를 검증했다.
  - `ui.ui_draw_jisuchart`
  - `DrawRealJisuChart`
  - `show_jisu`
  - `dialog_jisu`
- `python -c "import importlib; importlib.import_module('ui.ui_mainwindow'); print('ok')"` 실행 결과 `ok`를 확인했다.

## 문제 2. `utility.static` 호환 심볼 누락

### 증상

- `ui.ui_mainwindow` import 체인이 `utility.static`의 호환 심볼 누락으로 실패했다.
- `trade.stock_korea.kiwoom_trader` import도 `summer_time`, `get_profile_text` 누락 때문에 실패했다.

### 원인

- `ui/ui_process_starter.py`는 `summer_time`을 직접 import해서 사용하고 있었다.
- `trade/stock_korea/kiwoom_trader.py`는 `get_profile_text`를 직접 import해서 사용하고 있었다.
- 그런데 `utility/static.py`에 이 두 심볼이 호환 이름으로 노출되지 않아 import 체인이 끊겼다.

### 해결

- `utility/static.py`에 `summer_time` 호환 심볼을 다시 노출했다.
- `utility/static.py`에 `get_profile_text` 함수를 복구해 kiwoom 계열 import 체인을 다시 연결했다.

### 검증

- `tests/unit/test_static_compat.py`로 `summer_time` 심볼 존재, 정수형 오프셋 유지, `get_profile_text` 심볼 존재를 검증했다.
- `python -c "import importlib; importlib.import_module('ui.ui_mainwindow'); print('ok')"` 실행 결과 `ok`를 확인했다.
- `python -c "import importlib; importlib.import_module('trade.stock_korea.kiwoom_trader'); print('ok')"` 실행 결과 `ok`를 확인했다.

## 문제 3. 홈 탭 WebCrawling 전달 경로 불일치

### 증상

- 홈 탭 라벨이 계속 `데이터 검색 중 ...` 상태에 머물렀다.
- `utility/webcrawling.py`는 QThread 기반으로 바뀌어 `signal.emit(...)`로 UI 데이터를 올리는데, `ui/ui_mainwindow.py`는 계속 `Process(target=WebCrawling, ...)` 방식에 머물러 있어 전달 경로가 맞지 않았다.

### 원인

- `utility/webcrawling.py`가 프로세스 스타일 클래스에서 `QThread` 기반 `WebCrawling`으로 바뀌었다.
- 하지만 `ui/ui_mainwindow.py`는 그 전제에 맞춰 갱신되지 않아 홈 탭 데이터 전달이 끊겼다.
- 결과적으로 홈 탭 초기 플레이스홀더 문자열만 남고 실제 데이터가 라벨까지 도달하지 못했다.

### 해결

- `ui/ui_mainwindow.py`에서 `WebCrawling(self.qlist)`를 QThread 인스턴스로 생성하고, `self.webc.signal.connect(self.windowQ.put)`로 신호를 `windowQ`에 연결한 뒤 `self.webc.start()`로 실행하는 구조로 맞췄다.
- 더 이상 `Process(target=WebCrawling, ...)` 경로를 사용하지 않도록 정리했다.
- QThread 전환에 맞춰 `utility/webcrawling.py`의 `stop()` 계약을 보강했다. `treemap` 재스케줄 timer를 추적·취소하고, HTTP 요청에 공통 timeout을 적용하고, 무기한 `wait()` 대신 bounded wait를 사용하도록 바꿨다.

### 검증

- `tests/unit/test_ui_runtime_wiring.py`로 `Process(target=WebCrawling` 문자열 부재와 `self.webc.signal.connect(self.windowQ.put)` 연결 존재를 검증했다.
- 별도 Qt 이벤트 루프에서 `WebCrawling.signal`을 실제로 연결해 실행했을 때 홈 데이터 신호가 1회 이상 발생하는 것을 확인했다.
- 짧은 `python stom.py` 실행에서 즉시 traceback 없이 기동되는 것을 확인했다.
  - 8초 관찰 결과: `RUNNING_NO_TRACEBACK`
  - 확인 후 강제 종료: `STOPPED_AFTER_CHECK`

## 문제 4. 종료 경로의 `qtimer0` 잔존 참조

### 증상

- 종료 경로에서 `ui.qtimer0`를 참조하면 `MainWindow`에 없는 속성을 읽게 되어 종료 예외가 발생할 수 있었다.

### 원인

- `ui/ui_process_kill.py`가 `ui.qtimer0`를 계속 참조하고 있었지만, 실제 `MainWindow`에는 `qtimer0`가 존재하지 않았다.
- 종료 시점에만 실행되는 코드라 평상시에는 드러나지 않다가 shutdown 경로에서만 stale reference로 표면화됐다.

### 해결

- `ui/ui_process_kill.py`에서 존재하지 않는 `ui.qtimer0` 참조를 제거하고 실제로 살아 있는 타이머 경로만 정리하도록 맞췄다.

### 검증

- `tests/unit/test_ui_runtime_wiring.py`로 `ui/ui_process_kill.py`에 `qtimer0` 문자열이 남아 있지 않음을 구조적으로 검증했다.
- 짧은 `python stom.py` 실행에서 기동 직후 추가 traceback이 없음을 확인했다. 이 검증은 종료 경로 E2E 검증이 아니라, 최소한의 구조 회귀와 기동 안정성 확인 기준으로 사용했다.

## 검증 로그

아래 명령을 wt-dev에서 직접 실행해 결과를 확인했다.

| 명령 | 결과 |
|------|------|
| `python -m pytest tests/unit/test_static_compat.py tests/unit/test_ui_jisu_cleanup.py tests/unit/test_ui_runtime_wiring.py -q` | `9 passed, 3 warnings in 12.24s` |
| `python -m pytest tests/unit/ -q` | `788 passed, 1 skipped, 10 warnings in 99.06s` |
| `python -c "import importlib; importlib.import_module('ui.ui_mainwindow'); print('ok')"` | `ok` |
| `python -c "import importlib; importlib.import_module('trade.stock_korea.kiwoom_trader'); print('ok')"` | `ok` |
| `python stom.py` 짧은 기동 확인 | 즉시 traceback 없음, 8초 관찰 중 실행 유지 후 수동 종료 |

## 워크트리 감사 매트릭스

| 워크트리 | 동일 문제 존재 여부 | 근거 | 반영 필요 여부 | 실제 반영 여부 |
|------|------|------|------|------|
| `STOM_Version_2U` | 존재 | `ui_mainwindow/ui_process_kill/webcrawling` 정적 시그니처 일치, import smoke로 재현 확인 | 필요 | 반영함 (`3578284`, `7f7d069`) |
| `STOM_Version_2U_C` | 존재 | `2U`와 동일한 정적 시그니처 일치, `database_check()` 이후 import smoke로 재현/검증 확인 | 필요 | 반영함 (`4c16eb2`, `78a0242`) |
| `research/init` | 존재 | 동일 파일 경로에서 같은 시그니처와 import 실패 재현 확인 | 필요 | 반영함 (`8602782`) |

- `STOM_Version_2U`: `summer_time`는 이미 있었지만 지수차트 잔재, `qtimer0`, `WebCrawling` wiring 불일치가 실제로 남아 있었고, 키 로딩 경로도 안전하지 않아 `wt-dev` 기준 패치를 반영했다. 반영 후 targeted 회귀 테스트 `12 passed`, import smoke `ok`를 확인했다.
- `STOM_Version_2U_C`: `2U`와 동일한 런타임 결함군이 존재했고, 직접 `ui.ui_mainwindow` import는 DB 초기화 전제 때문에 `database_check()` 이후 기준으로 검증했다. 안전한 키 정책까지 포함해 반영했고, targeted 회귀 테스트 `12 passed`, import smoke `ok`를 확인했다.
- `research/init`: 연구 브랜치라도 동일 파일 경로에서 같은 결함과 import 실패가 재현되어 미반영 근거가 없었다. 부분 패치로 꼬인 상태를 2U 통과본 기준으로 정리했고, targeted 회귀 테스트 `12 passed`, import smoke `ok`를 확인했다.
