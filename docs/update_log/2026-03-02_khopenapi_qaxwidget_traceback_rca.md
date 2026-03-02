# STOM_Version_2U 장애 분석 보고서

- 작성일: 2026-03-02
- 대상 브랜치: `STOM_Version_2U`
- 비교 기준(정상 동작 진술 기준): `STOM_Version_2` 커밋 `deb68d3e617b9786b855b9cfaff3cf81040b23d6` (STOM V2.50)
- 관련 로그 핵심:
  - `QAxBase::setControl: requested control KHOPENAPI.KHOpenAPICtrl.1 could not be instantiated`
  - `AttributeError: 'QAxWidget' object has no attribute 'OnReceiveMsg'`

---

## 1) 문제

주식 로그인/에이전트 구동 과정에서 OpenAPI ActiveX 컨트롤 초기화에 실패하고, 이후 `OnReceiveMsg` 이벤트 연결 지점에서 `AttributeError`가 반복 발생하여 매니저가 재시도 루프에 빠지는 문제가 발생함.

---

## 2) 분석

### 2.1 실패 지점(직접 원인 라인)

`stock/kiwoom_agent_tick.py`:

- `self.ocx = QAxWidget('KHOPENAPI.KHOpenAPICtrl.1')` (라인 69)
- `self.ocx.OnReceiveMsg.connect(self.OnReceiveMsg)` (라인 70)

ActiveX 로드 실패 시 `QAxWidget` 래퍼 객체에 해당 이벤트 속성이 생성되지 않아 라인 70에서 즉시 예외가 발생함.

### 2.2 코드 비교 결과 (deb68d3 vs 2U HEAD)

다음 파일은 `deb68d3`와 `STOM_Version_2U` HEAD에서 blob hash가 동일함.

- `stock/kiwoom_manager.py`
- `stock/kiwoom_agent_tick.py`
- `stock/login_kiwoom/autologin.py`
- `stock/login_kiwoom/versionupdater.py`

즉, **stock 런타임 핵심 모듈 자체는 최근 2U(U1.2~U1.5)에서 변경되지 않았음**.

### 2.3 분기점: `ui_mainwindow.pyd` → `ui_mainwindow.py` 마이그레이션

`STOM_Version_2U`는 2026-01-31 (`868c9ca`)에 `ui/ui_mainwindow.py`를 도입함.
마이그레이션 문서(`docs/update_log/2026-01-31_ui_mainwindow_migration.md`)에 따르면 V1.10 소스를 기반으로 가져왔고,
해당 경로의 매니저 실행 코드는 다음과 같이 유지됨.

```python
subprocess.Popen(f'python ./stock/kiwoom_manager.py {port_num}')
```

현재 `ui/ui_mainwindow.py`(라인 504)도 동일.

### 2.4 인터프리터 실행 경로 불일치 정황

`stock/kiwoom_manager.py`는 로그인/버전업 도우미를 `python32`로 명시 실행함.

- `python32 {LOGIN_PATH}/versionupdater.py` (라인 229)
- `python32 {LOGIN_PATH}/autologin.py` (라인 238, 241)

반면, 에이전트는 `multiprocessing.Process`로 매니저 프로세스에서 직접 spawn함.

- `self.proc_agent = Process(target=target, args=(self.qlist,), daemon=True)` (라인 275)

즉 매니저가 어떤 파이썬으로 떠 있느냐가 에이전트 비트수/런타임에도 그대로 영향을 줌.

### 2.5 V2.21 실행파일 이름 규약과의 연동 리스크

`_update.txt` (2025-10-17 V2.21)에는 다음 규약이 명시됨.

- 32비트: `python.exe -> python32.exe`
- 64비트: `python64.exe -> python.exe`

따라서 `python`(generic)로 매니저를 띄우는 경로는 환경에 따라 64비트 인터프리터로 이어질 수 있고,
이 경우 KHOpenAPI ActiveX(32비트 요구) 초기화 실패 가능성이 높아짐.

---

## 3) 원인

### 최종 원인 요약

1. **직접 원인**: KHOpenAPI ActiveX 컨트롤 인스턴스화 실패 상태에서 즉시 이벤트를 connect하여 `AttributeError` 발생.
2. **근본 원인**: 2U 경로에서 매니저 실행 인터프리터가 `python`으로 고정되어 환경 의존성이 커졌고,
   로그인 도우미(`python32`)와 에이전트(multiprocessing 상속)가 다른 런타임 경로를 타면서 비트수 불일치가 발생할 수 있는 구조.
3. **회귀 여부 판단**: U1.2~U1.5의 최근 패치가 stock 런타임 코드를 바꿔서 생긴 신규 결함이라기보다,
   기존 잠재 리스크가 2U 실행 경로에서 표면화된 사례로 판단.

---

## 4) 해결책

### 4.1 즉시 대응(P0)

- `ui/ui_mainwindow.py`의 주식 매니저 실행 경로를 환경 의존 `python`이 아니라,
  OpenAPI 호환이 보장되는 인터프리터(예: `python32`)로 명시 실행.

### 4.2 안정화 대응(P1)

- `stock/kiwoom_agent_tick.py`에서 OCX 생성 직후 이벤트 connect 전에 방어 검사 추가:
  - 필수 이벤트 속성 존재 여부 확인
  - 실패 시 명시적 단일 에러 로그 + 안전 종료(무한 traceback 방지)

### 4.3 운영 안전성 개선(P1)

- `stock/kiwoom_manager.py`의 반복 재시도 루프에 백오프/상한을 두어 장애 시 로그 폭주와 프로세스 난립을 완화.
- 별도 결함: `StockAgentProcessKill()`이 trader를 kill하는 오타성 버그는 분리 수정 권장.

---

## 5) 검증 체크리스트

1. `python32`/`python` 비트수 확인
2. 단독 OCX probe에서 `hasattr(ocx, 'OnReceiveMsg')` 결과 비교
3. `python stom.py stock` 실행 시 다음 문자열 재발 여부 확인
   - `QAxBase::setControl: requested control KHOPENAPI...`
   - `AttributeError: 'QAxWidget' object has no attribute 'OnReceiveMsg'`
4. 로그인/버전업/에이전트 시작까지 정상 진입 확인

---

## 6) 결론

`deb68d3` 대비 증상 차이는 stock 로직 자체 변경이 아니라,
`STOM_Version_2U`의 `ui_mainwindow.py` 기반 실행 경로에서 인터프리터 선택이 환경 의존적으로 동작하면서
KHOpenAPI OCX 초기화 실패 조건이 현실화된 것으로 결론지음.

