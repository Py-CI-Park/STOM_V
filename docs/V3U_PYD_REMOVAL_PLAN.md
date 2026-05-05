# STOM V3U pyd 제거 계획

- 작성일: 2026-05-05
- 대상 branch: `STOM_Version_3U`
- 대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-3u`
- 기준 V3 official: `7faec937 STOM V3.18`
- 현재 단계: pyd 제거 실행 전 계획 고정
- 이번 문서 커밋에서 하지 않는 일: `ui/main_window.pyd` 제거, pyd 대체 코드 구현, DB/runtime 변경, `STOM_Version_3U_C` 생성, `2U_C` backport

## 1. 목적

이 문서는 `STOM_Version_3U`에서 V3 official pyd를 제거하기 전에 대상, 참고 자료, 허용 차이, 구현 순서, 검증 기준을 고정한다.

V3U의 목표는 다음 한 문장으로 요약한다.

```text
STOM_Version_3U는 STOM_Version_3와 같아야 하며, 차이는 pyd 제거와 그 대체 구현 및 검증 scaffolding으로 제한한다.
```

## 2. 현재 기준선

### 2.1 V3U worktree 상태

- `STOM_Version_3U`는 `STOM_Version_3`에서 분기되었다.
- `STOM_V.wt-3u` HEAD는 `7faec937 STOM V3.18`이다.
- pyd 제거 전이므로 3U와 3의 tracked source diff는 없어야 한다.
- `_database`와 `_log`는 runtime seed이며 git commit 대상이 아니다.

### 2.2 V3 pyd target

V3 official pyd target은 다음 한 파일이다.

```text
ui/main_window.pyd
```

V3 entry point는 `stom.py`에서 다음 import를 수행한다.

```python
from ui.main_window import MainWindow
```

따라서 pyd-free 이후에도 `stom.py`가 기대하는 import contract는 유지되어야 한다.

```text
ui.main_window.MainWindow(auto_run, splash)
```

### 2.3 V2 참고 target과 차이

V2/2U의 pyd-free 참고 파일은 다음이다.

```text
C:/System_Trading/STOM/STOM_V.wt-2u/ui/ui_mainwindow.py
```

하지만 V2의 pyd 경로와 V3의 pyd 경로는 다르다.

```text
V2 pyd: ui/ui_mainwindow.pyd
V3 pyd: ui/main_window.pyd
```

따라서 2U 파일을 V3 위에 그대로 덮어쓰지 않는다. 2U 산출물은 다음 용도로만 사용한다.

- MainWindow 초기화 순서 참고
- dialog 생성/show/close 패턴 참고
- process wrapper와 process_alive 패턴 참고
- event handler 연결 패턴 참고
- 검증 도구의 contract 개념 이식

## 3. V3 UI 구조 mapping

### 3.1 V3 entry/import layer

| 역할 | V3 파일 | 3U 계획 |
| --- | --- | --- |
| application entry | `stom.py` | 원칙적으로 변경하지 않음 |
| MainWindow import target | `ui/main_window.pyd` | `ui/main_window.py` 또는 동등한 Python 대체로 전환 |
| splash/import progress | `ui/etcetera/splash_screen.py`, `ui/etcetera/import_hook.py` | existing contract 유지 |

### 3.2 V3 widget creation layer

V3는 V2의 `ui/set_*.py`와 달리 `ui/create_widget/` 아래에 widget 생성 파일이 있다.

주요 mapping:

| V3 file group | 역할 | 2U 참고 가능성 |
| --- | --- | --- |
| `ui/create_widget/set_main_menu.py` | main menu 구성 | `2U/ui/set_main_menu.py` 패턴 참고 |
| `ui/create_widget/set_table.py` | table 구성 | `2U/ui/set_table.py` 패턴 참고 |
| `ui/create_widget/set_widget.py` | 주요 widget 생성 | `2U/ui/set_widget.py` 패턴 참고 |
| `ui/create_widget/set_dialog_*.py` | dialog 생성 | `2U/ui/set_dialog_*.py` 패턴 참고 |
| `ui/create_widget/set_stg_tap.py` | V3 전략 탭 구성 | 2U의 stock/coin/unified 분리 전제 그대로 사용 금지 |
| `ui/create_widget/set_style.py` | palette/style | V3 official 유지 우선 |

### 3.3 V3 event layer

| V3 file group | 역할 | pyd 제거 시 확인할 contract |
| --- | --- | --- |
| `ui/event_click/*.py` | button/table click handler | MainWindow wrapper가 handler에 필요한 `self` attr를 제공해야 함 |
| `ui/event_activate/*.py` | combo/tab activated handler | activated alias와 연결 인자 contract 확인 |
| `ui/event_change/*.py` | checkbox/text changed handler | signal 연결과 widget attr 존재 확인 |
| `ui/event_keypress/*.py` | keypress/event filter override | QMainWindow inheritance와 eventFilter fallback 확인 |
| `ui/etcetera/process_alive.py` | process state helper | process attr 초기값과 lifecycle contract 확인 |
| `ui/etcetera/process_starter.py` | process start helper | pyd-free MainWindow에서 process queue/attr 초기화 확인 |
| `ui/update_widget/*.py` | table/progress/text update | update worker attr와 thread-safe signal 연결 확인 |
| `ui/draw_chart/*.py` | chart/dialog rendering | chart dialog attr와 canvas attr contract 확인 |

## 4. 2U 검증 도구 이식 계획

2U에는 다음 검증 도구가 존재한다.

```text
C:/System_Trading/STOM/STOM_V.wt-2u/scripts/gui_contract_manifest.py
C:/System_Trading/STOM/STOM_V.wt-2u/scripts/smoke_offline_gui.py
C:/System_Trading/STOM/STOM_V.wt-2u/scripts/verify_pyd_gui_contract.py
```

V3U에서는 그대로 복사하기 전에 다음 일반화가 필요하다.

| 2U 검증 전제 | V3U 변경 필요 |
| --- | --- |
| pyd evidence path `ui/ui_mainwindow.pyd` | `ui/main_window.pyd`로 변경 |
| Python target `ui/ui_mainwindow.py` | `ui/main_window.py` 또는 V3 wrapper path로 변경 |
| V2 `ui/set_*.py` source list | V3 `ui/create_widget/set_*.py` source list로 변경 |
| V2 activated/clicked module names | V3 `ui/event_activate`, `ui/event_click` 기준으로 변경 |
| V2 log dir `.omx/logs/v279` | V3U용 `.omx/logs/v3u` 등으로 분리 |
| V2 contract manifest | V3 widget/dialog/process attr 기준으로 재작성 |

## 5. 허용 차이 정책

### 5.1 허용되는 차이

3U와 3의 diff에서 다음은 허용된다.

- `ui/main_window.pyd` 제거
- `ui/main_window.py` 또는 pyd 대체 Python entry 추가
- MainWindow wrapper/inference 구현 추가
- pyd 대체를 위한 최소한의 import boundary 조정
- V3U 검증 스크립트 추가 또는 2U 검증 스크립트의 V3 일반화 버전 추가
- V3U pyd contract manifest 추가
- pyd-free 검증 로그를 남기기 위한 ignored `.omx` runtime 산출물

### 5.2 조건부 허용되는 차이

다음은 decision record와 검증 증거가 있을 때만 허용한다.

- V3 official non-pyd runtime file 수정
- `stom.py` import boundary 수정
- event handler 시그니처 보정
- dialog show/close helper 보정
- process lifecycle wrapper 보정

조건부 허용 차이는 반드시 다음 양식으로 기록한다.

```text
Decision:
Affected file:
Why pyd-free requires this change:
Why official V3 file cannot remain unchanged:
Verification:
Rollback:
```

### 5.3 금지되는 차이

다음은 금지한다.

- `STOM_Version_2U` 파일을 V3에 무검토 overwrite
- `STOM_Version_2U_C` custom/Kiwoom 유지 로직 유입
- LS API runtime을 우회하거나 Kiwoom 호환용으로 바꾸는 작업
- `_database`, `_log`, `*.db`, `backtest/graph/` commit
- `STOM_Version_3U_C` 생성
- V3 official update commit 수정 또는 재작성
- pyd 제거와 무관한 refactor/cleanup

## 6. pyd-free 구현 순서

### Step 1. 기준선 고정

검증:

```powershell
git -C C:/System_Trading/STOM/STOM_V.wt-3u status --short
git -C C:/System_Trading/STOM/STOM_V.wt-3u log -1 --oneline
git -C C:/System_Trading/STOM/STOM_V.wt-3u diff --name-status STOM_Version_3...STOM_Version_3U
```

완료 조건:

- 3U status clean
- 3U HEAD가 `STOM V3.18`
- pyd 제거 전 3U vs 3 diff가 없음

### Step 2. V3 pyd contract inventory 작성

확인 대상:

- `stom.py`의 `MainWindow(auto_run, splash)` 호출 contract
- `ui/main_window.pyd`가 제공해야 하는 class name
- `ui/create_widget`가 생성하는 주요 attr
- `ui/event_click`, `ui/event_activate`, `ui/event_change`, `ui/event_keypress`가 참조하는 attr
- process attr 초기값
- dialog attr와 show/close 상태
- queue/signal/thread attr

산출물 후보:

```text
scripts/v3u_gui_contract_manifest.py
.omx/logs/v3u/contract_inventory_*.json
```

### Step 3. 2U 검증 도구를 V3U용으로 일반화

권장 파일명:

```text
scripts/v3u_gui_contract_manifest.py
scripts/v3u_smoke_offline_gui.py
scripts/verify_v3u_pyd_gui_contract.py
```

주의:

- 기존 2U scripts를 그대로 overwrite하지 않는다.
- V3 official branch에는 추가하지 않는다.
- V3U에서만 검증 scaffolding으로 추가한다.

### Step 4. `ui/main_window.py` 대체 entry 작성

목표:

- `from ui.main_window import MainWindow`가 Python source로 해결되게 한다.
- `MainWindow(auto_run, splash)` 생성 contract를 유지한다.
- QMainWindow inheritance, signal/event override, widget creation, process attr 초기화 순서를 명시한다.

주의:

- 2U `ui/ui_mainwindow.py`를 그대로 복사하지 않는다.
- V3의 `ui/create_widget`, `ui/event_*`, `ui/update_widget`, `ui/draw_chart`, `ui/etcetera` 구조를 기준으로 재구성한다.

### Step 5. pyd 제거

마지막에 다음을 수행한다.

```powershell
git -C C:/System_Trading/STOM/STOM_V.wt-3u rm ui/main_window.pyd
```

전제:

- `ui/main_window.py`가 준비됨
- import/py_compile가 통과함
- 최소 contract manifest가 준비됨

### Step 6. 검증과 diff audit

필수 검증:

```powershell
git -C C:/System_Trading/STOM/STOM_V.wt-3u ls-files *.pyd
python -m py_compile ui/main_window.py
python scripts/verify_v3u_pyd_gui_contract.py --branch STOM_Version_3U --version V3.18 --upstream-ref STOM_Version_3 --manifest <manifest>
python scripts/v3u_smoke_offline_gui.py --branch STOM_Version_3U --version V3.18 --offline --log-dir .omx/logs/v3u
```

보조 검증:

```powershell
git -C C:/System_Trading/STOM/STOM_V.wt-3u diff --name-status STOM_Version_3...STOM_Version_3U
git -C C:/System_Trading/STOM/STOM_V.wt-3u status --short --ignored
```

## 7. 완료 기준

V3U pyd-free 완료는 다음을 모두 만족할 때만 선언한다.

- tracked `.pyd` 파일 0개
- `ui/main_window.py` 또는 동등한 Python entry 존재
- `from ui.main_window import MainWindow` 성공
- `python -m py_compile` 통과
- V3U GUI contract manifest 통과
- offline GUI smoke 통과 또는 환경 제약으로 인한 명확한 gap 기록
- `_database`, `_log`, `*.db`, `backtest/graph/`가 commit되지 않음
- `STOM_Version_3U_C`가 생성되지 않음
- 3U vs 3 diff가 allowed diff policy에 의해 설명됨

## 8. 주요 위험과 대응

| 위험 | 설명 | 대응 |
| --- | --- | --- |
| V2 구조 혼입 | `ui/ui_mainwindow.py`를 그대로 복사하면 V3 구조와 충돌 | V3 mapping inventory 후 필요한 패턴만 이식 |
| pyd 제거 후 import 실패 | `stom.py`가 `ui.main_window.MainWindow`를 요구 | `ui/main_window.py`를 먼저 만들고 py_compile/import 검증 |
| event attr 누락 | event handler가 pyd 내부 attr에 의존할 수 있음 | manifest로 handler 참조 attr 수집 |
| process lifecycle 누락 | receiver/trader/strategy process attr 초기화 누락 가능 | `ui/etcetera/process_alive.py`, `process_starter.py` contract 확인 |
| DB/runtime 오염 | seed DB가 git status에 나타날 수 있음 | status --ignored로 ignored 상태 확인, git add 대상 제한 |
| 과도한 refactor | pyd 제거와 무관한 cleanup이 섞임 | allowed diff policy 밖의 변경 금지 |

## 9. 이번 문서 이후 다음 단계

다음 실행 단위는 pyd-free 구현이 아니라, 먼저 V3 pyd contract inventory와 V3U 검증 스크립트 일반화다.

권장 다음 작업:

1. `ui/main_window.pyd`의 외부 contract를 inventory로 정리한다.
2. 2U의 `gui_contract_manifest.py`를 V3 구조 기준으로 새 파일에 이식한다.
3. 2U의 smoke/verify script를 V3U 전용 파일명으로 일반화한다.
4. 그 다음에 `ui/main_window.py` 대체 구현을 시작한다.

## 10. 금지 사항 재확인

이 문서 커밋 이후에도 다음은 별도 승인과 계획 전에는 수행하지 않는다.

- `ui/main_window.pyd` 제거
- pyd 대체 구현 커밋
- V3 official branch 수정
- `STOM_Version_3U_C` 생성
- 2U_C backport
- DB 파일 commit
