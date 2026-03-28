# STOM_Version_2U 해결 업데이트 안내서

- 작성일: 2026-03-02
- 대상: `STOM_Version_2U` 운영/개발 사용자
- 관련 장애: KHOpenAPI ActiveX 초기화 실패 후 `OnReceiveMsg` AttributeError 반복
- 참조 문서: `docs/update_log/2026-03-02_khopenapi_qaxwidget_traceback_rca.md`

---

## 1) 적용 전 확인사항

### 1.1 브랜치/작업 상태 확인

```bash
git rev-parse --abbrev-ref HEAD
git status --short
```

- 브랜치가 `STOM_Version_2U`인지 확인
- 미커밋 변경이 많다면 별도 스태시/브랜치로 분리 후 작업

### 1.2 증상 확인(현재 상태)

실행 로그에 다음이 반복되는지 확인합니다.

- `QAxBase::setControl: requested control KHOPENAPI.KHOpenAPICtrl.1 could not be instantiated`
- `AttributeError: 'QAxWidget' object has no attribute 'OnReceiveMsg'`

---

## 2) 권장 업데이트 순서 (실제 적용 절차)

### Step A. 인터프리터 경로 정합성 확보 (최우선)

1. `python32`가 실제 32비트 인터프리터로 동작하는지 확인
2. `python`이 64비트로 연결되어 있는 환경이라면,
   `ui/ui_mainwindow.py`의 주식 매니저 실행 경로를 `python32` 기준으로 명시하도록 업데이트

목표는 **로그인 도우미(`python32`)와 에이전트 spawn 경로가 동일 런타임 계열로 맞춰지게 하는 것**입니다.

### Step B. 방어 로직 추가(권장)

- `stock/kiwoom_agent_tick.py`에서 OCX 생성 후 이벤트 connect 전에 필수 이벤트 속성 존재 여부 검사
- 실패 시 단일 에러 메시지 출력 후 안전 종료

효과:
- 원인 미해결 시에도 무한 traceback 반복 방지
- 장애 원인 식별 시간 단축

### Step C. 재시도 루프 안정화(권장)

- `stock/kiwoom_manager.py`의 반복 재시도 루프에 백오프/횟수 제한 적용
- 로그 폭주/프로세스 난립 완화

---

## 3) 검증 절차

### 3.1 인터프리터/OCX 기본 점검

```bat
python -c "import struct; print('python bits=', struct.calcsize('P')*8)"
python32 -c "import struct; print('python32 bits=', struct.calcsize('P')*8)"
```

```bat
python -c "from PyQt5.QtWidgets import QApplication; from PyQt5.QAxContainer import QAxWidget; app=QApplication([]); ocx=QAxWidget('KHOPENAPI.KHOpenAPICtrl.1'); print('python has OnReceiveMsg=', hasattr(ocx,'OnReceiveMsg'))"
python32 -c "from PyQt5.QtWidgets import QApplication; from PyQt5.QAxContainer import QAxWidget; app=QApplication([]); ocx=QAxWidget('KHOPENAPI.KHOpenAPICtrl.1'); print('python32 has OnReceiveMsg=', hasattr(ocx,'OnReceiveMsg'))"
```

### 3.2 STOM 실행 검증

```bat
python stom.py stock
```

다음 문자열이 재발하지 않아야 정상입니다.

- `QAxBase::setControl: requested control KHOPENAPI...`
- `AttributeError: 'QAxWidget' object has no attribute 'OnReceiveMsg'`

### 3.3 소스 일관성 검증(권장)

```bash
python3 -m py_compile ui/ui_mainwindow.py stock/kiwoom_manager.py stock/kiwoom_agent_tick.py
```

---

## 4) 롤백 절차

### 4.1 미커밋 상태 롤백

```bash
git restore ui/ui_mainwindow.py stock/kiwoom_manager.py stock/kiwoom_agent_tick.py
```

### 4.2 커밋 후 롤백

```bash
git log --oneline -n 10
git revert <문제 커밋해시>
```

---

## 5) 운영 FAQ

### Q1. 왜 `deb68d3`에서는 괜찮았는데 2U에서 터지나요?

`deb68d3`는 `ui_mainwindow.pyd` 기반이고, 2U는 `ui_mainwindow.py` 기반입니다.
실행 경로의 인터프리터 선택이 환경 의존적으로 바뀌면서 잠재 리스크가 표면화될 수 있습니다.

### Q2. 최근 U1.2~U1.5 패치가 직접 원인인가요?

직접 원인으로 보기 어렵습니다.
stock 런타임 핵심 파일은 `deb68d3`와 동일하며, 최근 패치에서 변경된 파일은 주로 `ui/ui_mainwindow.py`, `utility/static.py` 계열입니다.

### Q3. 지금 당장 가장 효과적인 조치는 무엇인가요?

매니저/에이전트 실행 인터프리터를 OpenAPI 호환 런타임으로 명시 고정하는 것입니다.

---

## 6) 커밋/배포 권장 포맷

- 커밋 제목 예시:
  - `STOM V2.50.U1.6 - KHOpenAPI OnReceiveMsg 장애 RCA 및 해결 가이드 문서화`
- 커밋 본문에 아래 3개를 반드시 포함:
  1. 증상 로그 키워드
  2. 원인 판단 근거(파일/라인)
  3. 적용 및 검증 절차

