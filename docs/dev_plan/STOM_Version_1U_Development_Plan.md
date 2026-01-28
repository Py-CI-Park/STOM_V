# STOM_Version_1U 개발 계획서

## 1. 프로젝트 개요

### 1.1 목적
STOM_Version_1(V1) 코드베이스를 기반으로, STOM_Version_2(V2)에서 순차적으로 개발된 36개 커밋(V2.00 ~ V2.36)의 변경사항을 **코드를 이해하고 추론하여** STOM_Version_1U 브랜치에 체계적으로 반영한다.

### 1.2 핵심 원칙
- **체리픽(cherry-pick) 금지**: 단순 커밋 복사가 아닌, 각 커밋의 의도와 코드 변경을 이해한 뒤 V1U 코드베이스에 맞게 재구현
- **순차적 개발**: V2.00부터 V2.36까지 한 단계씩 진행하며, 각 단계에서 컴파일/실행 가능한 상태 유지
- **ui_mainwindow.py 유지**: V2에서 .pyd(바이너리)로 암호화된 `ui/ui_mainwindow.py`를 V1U에서는 **소스코드(.py) 형태로 유지**하면서 동일한 기능 변경을 추론하여 반영
- **커밋 단위 검증**: 각 단계 완료 시 독립적인 커밋으로 기록

### 1.3 배경
| 항목 | 내용 |
|------|------|
| 시작 브랜치 | `STOM_Version_1U` |
| 시작 커밋 | `80ab4ec` (STOM V1) |
| 참조 브랜치 | `STOM_Version_2` |
| 참조 범위 | `b021269` (V2.00) ~ `ddfd9fb` (V2.36), 총 36개 커밋 |
| 공통 조상 | `80ab4ec` (STOM V1 = STOM_Version_1U 시작점) |
| 핵심 과제 | V2의 `ui_mainwindow.pyd` 변경사항을 V1U의 `ui_mainwindow.py`에 소스코드로 반영 |

---

## 2. 브랜치 구조

```
Initial commit (87aee04)
  │
  └── STOM V1 (80ab4ec) ─────────────────── STOM_Version_1 브랜치
        │
        ├── STOM_Version_1U 브랜치 (본 프로젝트)
        │     └── V1U.00 → V1U.01 → ... → V1U.36 (목표)
        │
        └── STOM_Version_2 브랜치 (참조)
              └── V2.00 → V2.01 → ... → V2.36
```

---

## 3. V2 커밋 이력 전체 분석

### 3.1 커밋 목록 및 주요 변경 요약

| # | 커밋 | 버전 | 날짜 | 핵심 변경 내용 | 파일 수 | pyd 크기 |
|---|------|------|------|----------------|---------|----------|
| 1 | `b021269` | V2.00 | 2025-09-12 | 키움증권 해외선물 추가, 인증시스템, ZMQ 라이브, ui_mainwindow.py→.pyd 전환 | 135 | 892,416 |
| 2 | `9d065c0` | V2.01 | 2025-09-14 | 수익율→수익률 수정, 텔레그램봇 업그레이드 | 62 | 892,416 |
| 3 | `69067bf` | V2.02 | 2025-09-15 | DataFrame→Dictionary 전환 (트레이더/전략연산) | 30 | 892,416 |
| 4 | `1a64c19` | V2.03 | 2025-09-16 | 해선 계정 하나로 통합, future 모듈 대규모 개편 | 24 | 892,416 |
| 5 | `23384a4` | V2.04 | 2025-09-17 | 주식도 계정 하나로 통합, stock/kiwoom.py 대규모 개편 | 40 | 892,416 |
| 6 | `fefe04e` | V2.05 | 2025-09-18 | 당일실현손익 거래횟수 추가, 종료속도 개선 | 33 | 892,416 |
| 7 | `18a9fb9` | V2.06 | 2025-09-19 | 테스트모드 추가, .keys() 삭제, llvmlite 버전 지정 | 50+ | 892,416 |
| 8 | `85c8541` | V2.07 | 2025-09-20 | 미체결 체잔목록 속도개선, 호가 DataFrame→Dict | 15 | 892,416 |
| 9 | `9ab6cac` | V2.08 | 2025-09-21 | 1분봉 변수이름 오류 수정 | 20 | 892,416 |
| 10 | `6bf0546` | V2.09 | 2025-09-23 | 백테엔진 공유메모리, 피클파일 분할로딩 | 31 | 892,416 |
| 11 | `b701eab` | V2.10 | 2025-09-25 | 1분봉 백테엔진 오류, 로그인서버 시간변경, 최적화 개선 | 32 | 892,416 |
| 12 | `23be27a` | V2.11 | 2025-09-26 | **UI 파일명/함수명 대규모 리네이밍**, loguru 도입 | 45+ | 892,416 |
| 13 | `acbc671` | V2.12 | 2025-09-28 | 백테엔진 멀티수=CPU코어수, 옵튜나 기준값 개선 | 20 | 892,416 |
| 14 | `a0681ec` | V2.13 | 2025-09-30 | 그리드 최적화 방법 전면 변경 | 4 | 892,416 |
| 15 | `68f55cf` | V2.14 | 2025-10-01 | 조건편집기 매수조건 변경, 집계속도 개선 | 4 | 892,416 |
| 16 | `847c8cf` | V2.15 | 2025-10-02 | 인증 강화, V2.11 구파일 삭제, 계수값 변경 | 60+ | **905,216** |
| 17 | `937baf8` | V2.16 | 2025-10-03 | 읽기전용 DB 통일, 코드테스트 속도개선 | 46+ | **905,728** |
| 18 | `244aae5` | V2.17 | 2025-10-04 | 네이버 뉴스 크롤링 오류 수정 | 17 | 905,728 |
| 19 | `27652c6` | V2.18 | 2025-10-14 | 테이블위젯 차이셀만 갱신, 백테 중복코드 삭제, 전략오류수정 | 36 | 905,728 |
| 20 | `b9a8d88` | V2.19 | 2025-10-15 | **리시버→에이전트 대규모 리네이밍**, PyQT 이벤트루프 전환 | 39 | **906,240** |
| 21 | `6a6321c` | V2.20 | 2025-10-16 | 단축키 변경, 예외처리, 트리맵 리팩토링 | 35 | **903,168** |
| 22 | `2f4fc72` | V2.21a | 2025-10-19 | 백테엔진 코드 구조 개선, 시간설정 수정 | 9 | 903,168 |
| 23 | `15ca982` | V2.21 | 2025-10-17 | 초당/분당 거래대금 개선, python 실행파일명 변경 | 25 | 903,168 |
| 24 | `4e2a9f0` | V2.22 | 2025-10-18 | 해선 오타수정, 백테 중지오류, 그리드 최적화 계수변경 | 22 | 903,168 |
| 25 | `0343ebd` | V2.23 | 2025-11-06 | .gitignore 추가, 백테엔진 간소화, 썸머타임 수정 | 37 | **847,360** |
| 26 | `81e1229` | V2.24 | 2025-11-14 | 분봉 실시간차트 데이터 오류 수정 | 21 | 847,360 |
| 27 | `487fbda` | V2.25 | 2025-11-22 | 코인 텔레그램 오류, 매매건수 0 오류 수정 | 7 | 847,360 |
| 28 | `7f9bd52` | V2.26 | 2025-12-18 | 보유수량 오류, 리시버공유 삭제, 잔고청산 오류 | 37+ | **845,824** |
| 29 | `699fae6` | V2.27 | 2025-12-19 | CheckboxChanged_19 오류, 선물 주문오류 수정 | 9 | 845,824 |
| 30 | `db1cfc7` | V2.28 | 2025-12-20 | 코인 시그널 취소 오류 수정 | 9 | 845,824 |
| 31 | `4888263` | V2.29 | 2025-12-21 | 코인 수동잔고청산 텔레그램, cell_clicked_03 칼럼 추가 | 7 | 845,824 |
| 32 | `4750170` | V2.30 | 2025-12-24 | 해선 차트 숏포지션 표시, 웹크롤링 주소 변경 | 33 | 845,824 |
| 33 | `ecae11b` | V2.31 | 2026-01-05 | 테이블위젯 갱신 오류 수정 | 3 | **846,848** |
| 34 | `d7997af` | V2.33 | 2026-01-17 | 타임프레임 실시간차트 오류, 주문설정 경고, V2.32 포함 | 7 | 846,848 |
| 35 | `ebc8812` | V2.34 | 2026-01-23 | 보유시간 조건 버튼 ':' 누락, 차트창 오류, 백테상세기록 경고, 보조지표 오류 수정 | 19 | 846,848 |
| 36 | `7ff3e03` | V2.35 | 2026-01-26 | UI 타이틀바에 데이터타입 표시 추가, 차트창 팩터 이름 오타 수정 | 3 | 846,848 |
| 37 | `ddfd9fb` | V2.36 | 2026-01-27 | 바이낸스선물 USDT 추출, 검증 MERGE값 합산 방법 변경(곱셈→덧셈), 옵튜나 부정소수점 수정 | 10 | 846,848 |

### 3.2 pyd 크기 변동 분석 (ui_mainwindow.py 코드 변경 추론)

pyd 파일 크기가 변동된 시점은 `ui_mainwindow.py` 소스에 실질적 변경이 발생한 것을 의미합니다.

| 구간 | 크기 | 변화 | 추정 원인 |
|------|------|------|-----------|
| V2.00 ~ V2.14 | 892,416 | 동일 | 초기 암호화 후 변경 없음, 주변 모듈만 변경 |
| **V2.15** | **905,216** (+12,800) | 증가 | 인증 강화 로직 추가, 인터넷 미연결 시 종료 로직 |
| **V2.16** | **905,728** (+512) | 소폭증가 | 읽기전용 DB 연결 통일, UI 자체 DB 접근 변경 |
| V2.17 ~ V2.18 | 905,728 | 동일 | 크롤링/테이블위젯 변경은 외부 모듈 |
| **V2.19** | **906,240** (+512) | 소폭증가 | 리시버→에이전트 리네이밍에 따른 import/참조 변경 |
| **V2.20** | **903,168** (-3,072) | 감소 | 단축키 변경으로 기존 핸들러 정리, 코드 간소화 |
| V2.21 ~ V2.22 | 903,168 | 동일 | 주변 모듈 변경 |
| **V2.23** | **847,360** (-55,808) | 대폭감소 | 리시버공유 클라이언트 관련 코드 대규모 삭제 추정 |
| V2.24 ~ V2.25 | 847,360 | 동일 | |
| **V2.26** | **845,824** (-1,536) | 소폭감소 | 리시버공유 모드 완전 삭제에 따른 잔여 코드 제거 |
| V2.27 ~ V2.30 | 845,824 | 동일 | |
| **V2.31** | **846,848** (+1,024) | 소폭증가 | 테이블위젯 갱신 로직 변경 (오류수정) |
| V2.33 ~ V2.36 | 846,848 | 동일 | 주변 모듈 변경, ui_mainwindow.py 자체 변경 없음 |

---

## 4. ui_mainwindow.py 변경 추론 상세 분석

### 4.1 V1 원본 구조 (80ab4ec, 1081줄)

```
파일 구조:
├── import 문 (1~76줄)
│   ├── 표준 라이브러리: zmq, socket, subprocess
│   ├── PyQt5: QCompleter, pyqtSlot, pyqtSignal, QThread
│   ├── ui.set_* 모듈: SetIcon, SetTable, SetLogTap, SetCoinBack, SetStockBack 등
│   ├── ui.ui_* 모듈: 약 40개 wildcard import
│   └── utility.* 모듈: hoga, chart, sound, query, static, setting, webcrawling, telegram_msg
│
├── LiveSender 클래스 (Thread 기반, ZMQ 소켓 전송)
├── LiveClient 클래스 (스톰 라이브 서버 연결)
├── Writer 클래스 (QThread, windowQ 처리)
├── ZmqServ 클래스 (QThread, ZMQ 서버)
├── ZmqRecv 클래스 (QThread, ZMQ 수신)
│
└── MainWindow 클래스 (QMainWindow 상속)
    ├── __init__: 초기화
    ├── Qtimer, ProcessStarter, Chart 관련 메서드
    ├── CheckboxChanged_01 ~ _19 (19개)
    ├── sbCheckboxChanged, ssCheckboxChanged, cbCheckboxChanged, csCheckboxChanged
    ├── CellClicked_01 ~ _11
    ├── ReturnPress_01 ~ _02
    ├── TextChanged_01 ~ _04
    ├── ButtonClicked 시리즈 (svc, svj, svjb, svjs, svoa, cvc, cvj, cva, cvo, ct, sj, bjs, bjc, set, cet)
    ├── BackTestengine 관련 메서드
    ├── ProcessAlive 시리즈
    ├── keyPressEvent, eventFilter, closeEvent, ProcessKill
    └── 총 약 200+ 메서드 (대부분 외부 모듈 함수 위임)
```

### 4.2 각 단계별 ui_mainwindow.py 추론 변경사항

#### Phase 1: V2.00 (대규모 변경)
**import 변경:**
- `from utility.telegram_msg import *` → (V2.01에서 `telegram_bot`으로 변경됨)
- `from ui.set_logfile import *` 관련 변경
- future 모듈 관련 import 추가 가능성

**LiveClient/LiveSender 변경:**
- 웹소켓 → ZMQ 방식 변경 (스톰 라이브 전면 개선)
- 해선 라이브 추가

**MainWindow 변경:**
- 인증 시스템 관련 코드 추가 (시리얼키 확인, 5분 후 종료)
- 타이틀 시계 거래소 기준 시간 표시
- 해외선물 관련 UI 위젯/버튼/이벤트 핸들러 추가
- strftime/strptime 전면 수정

#### Phase 2: V2.01
- `수익율` → `수익률` 문자열 수정
- 텔레그램봇 라이브러리 변경 반영

#### Phase 3: V2.02
- pyd 변경됨 → MainWindow 내부 데이터 처리가 DataFrame에서 Dict로 변경될 가능성

#### Phase 4: V2.03 ~ V2.04
- 해선/주식 계정 통합 관련 UI 코드 변경
- ProcessStarter, ProcessKill 등 프로세스 관리 변경

#### Phase 5: V2.05 ~ V2.10 (pyd 크기 동일 = 핵심 변경 없음)
- ui_mainwindow.py 자체 변경 없거나 미미
- 주변 모듈(ui_backtest_engine, ui_process_kill 등)만 변경

#### Phase 6: V2.11 (대규모 리네이밍)
**import 변경:**
```python
# 구파일명 → 신파일명
from ui.set_cbtap import ... → from ui.set_stg_coin_tap import ...
from ui.set_sbtap import ... → from ui.set_stg_stock_tap import ...
from ui.set_setuptap import ... → from ui.set_setup_tap import ...
from ui.set_ordertap import ... → from ui.set_order_tap import ...
from ui.set_mainmenu import ... → from ui.set_main_menu import ...
from ui.set_logtap import ... → from ui.set_log_tap import ...
from ui.ui_activated_b import ... → from ui.ui_activated_back import ...
from ui.ui_activated_c import ... → from ui.ui_activated_coin_stg import ...
from ui.ui_activated_s import ... → from ui.ui_activated_stock_stg import ...
from ui.ui_button_clicked_db import ... → from ui.ui_button_clicked_dialog_database import ...
from ui.ui_button_clicked_ob import ... → from ui.ui_button_clicked_order import ...
from ui.ui_button_clicked_sd import ... → from ui.ui_button_clicked_dialog_backengine import ...
from ui.ui_button_clicked_mn import ... → from ui.ui_button_clicked_shortcut import ...
from ui.ui_button_clicked_sj import ... → from ui.ui_button_clicked_settings import ...
from ui.ui_button_clicked_svc import ... → from ui.ui_button_clicked_editer_opti_stock import ...
from ui.ui_button_clicked_svj import ... → from ui.ui_button_clicked_editer_stock import ...
from ui.ui_button_clicked_cvc import ... → from ui.ui_button_clicked_editer_opti_coin import ...
from ui.ui_button_clicked_cvj import ... → from ui.ui_button_clicked_editer_coin import ...
from ui.ui_button_clicked_svjb import ... → from ui.ui_button_clicked_editer_stg_buy_stock import ...
from ui.ui_button_clicked_svjs import ... → from ui.ui_button_clicked_editer_stg_sell_stock import ...
from ui.ui_button_clicked_cvjb import ... → from ui.ui_button_clicked_editer_stg_buy_coin import ...
from ui.ui_button_clicked_cvjs import ... → from ui.ui_button_clicked_editer_stg_sell_coin import ...
from ui.ui_button_clicked_cvoa import ... → from ui.ui_button_clicked_editer_ga_coin import ...
from ui.ui_button_clicked_svoa import ... → from ui.ui_button_clicked_editer_ga_stock import ...
from ui.ui_button_clicked_ss_cs import ... → from ui.ui_button_clicked_editer_backlog import ...
from ui.ui_button_clicked_etsj import ... → from ui.ui_button_clicked_dialog_elapsed_tick_number import ...
```

**loguru 도입:**
- `import logging` 또는 `from loguru import logger` 추가 가능성

#### Phase 7: V2.15 (pyd +12,800 bytes)
- 인터넷 미연결 시 10분 후 종료 로직 추가
- 인증 관련 코드 강화
- V2.11 구파일 삭제 확인

#### Phase 8: V2.16 (pyd +512 bytes)
- 읽기전용 DB 연결 통일: `database_read_only` 모듈 import 및 사용

#### Phase 9: V2.19 (pyd +512 bytes)
**import 변경:**
```python
# 리시버 → 에이전트 리네이밍
# stock/kiwoom_receiver_* → stock/kiwoom_agent_*
# future/future_receiver_* → future/future_agent_*
# future/future_kiwoom.py → future/future_agent_tick.py
# stock/kiwoom.py → stock/kiwoom_agent_tick.py
```
- PyQT 이벤트 루프 기반 변경에 따른 프로세스 시작/관리 코드 변경

#### Phase 10: V2.20 (pyd -3,072 bytes)
- 단축키 `Ctrl+Shift+키` → `Shift+키` 변경
- `Shift+Q` 단축키 추가 (데이터 저장 및 수동 종료)
- 기존 핸들러 정리로 코드 감소

#### Phase 11: V2.23 (pyd -55,808 bytes, 대폭 감소)
- 리시버공유 클라이언트 관련 코드 대규모 삭제
- ProcessAlive 메서드 중 리시버 공유 관련 제거
- ProcessStarter/ProcessKill에서 리시버 공유 관련 코드 제거
- .gitignore 추가

#### Phase 12: V2.26 (pyd -1,536 bytes)
- 리시버 공유 모드 완전 삭제
- `coin/binance_receiver_client.py`, `coin/upbit_receiver_client.py`, `future/future_agent_client.py` 삭제에 따른 import/참조 제거

#### Phase 13: V2.31 (pyd +1,024 bytes)
- 테이블위젯 갱신 로직 변경 (관심목록 중복, 잔고목록 셀 표시 오류 수정)

---

## 5. V2 개발 카테고리 분류

### 5.1 기능 추가
| 버전 | 기능 |
|------|------|
| V2.00 | 키움증권 해외선물(CME) 지원, 인증 시스템, ZMQ 라이브 |
| V2.01 | 텔레그램봇 업그레이드, 해선 버튼 추가 |
| V2.06 | 주식/해선 테스트모드 |
| V2.09 | 백테엔진 공유메모리, 피클파일 분할로딩 |
| V2.11 | loguru 로거 도입 |
| V2.13 | 그리드 최적화 전면 개편 |
| V2.16 | 읽기전용 DB 연결 통일 |
| V2.29 | cell_clicked_03 칼럼 추가 |

### 5.2 성능 최적화
| 버전 | 최적화 대상 |
|------|-------------|
| V2.02 | DataFrame → Dictionary 전환 (트레이더/전략연산 속도 향상) |
| V2.05 | 큐 데이터 추출 속도, 종료 속도 |
| V2.06 | 호가잔량 보정 연산, 거래대금 순위 메모리 |
| V2.07 | 미체결 체잔목록, 호가 DataFrame→Dict |
| V2.09 | 백테엔진 20%+ 속도 개선 |
| V2.10 | 최적화 기준값 계산, 전략/범위 저장 |
| V2.14 | 백테스트 중간집계 속도 |
| V2.16 | 코드테스트 속도 |
| V2.18 | 테이블위젯 차이셀만 갱신 |
| V2.21 | 초당/분당 거래대금 연산 |

### 5.3 리팩토링/리네이밍
| 버전 | 대상 |
|------|------|
| V2.00 | strftime/strptime 전면 수정, 트레이더 코드 한글화 |
| V2.06 | .keys() 전면 삭제 |
| V2.11 | **UI 파일명/함수명 전체 리네이밍** |
| V2.18 | 백테스터 중복코드 삭제, 트레이더 간소화 |
| V2.19 | **리시버→에이전트 리네이밍**, PyQT 이벤트루프 전환 |
| V2.23 | 백테엔진 코드 간소화 |
| V2.26 | 리시버 공유 모드 삭제 |

### 5.4 구조 변경
| 버전 | 변경 |
|------|------|
| V2.03 | 해선 계정 하나로 통합 |
| V2.04 | 주식 계정 하나로 통합, stock/kiwoom.py 대규모 개편 |
| V2.01 | utility/telegram_msg.py → utility/telegram_bot.py |
| V2.19 | stock/kiwoom.py → stock/kiwoom_agent_tick.py 등 |

### 5.5 버그 수정
| 버전 | 수정 내용 |
|------|-----------|
| V2.01 | 수익율→수익률 |
| V2.04 | 해선 데이터 저장, 큐사이즈 표시, 실시간차트 |
| V2.05 | 해선 확장호가, 바이낸스 매도수 표시 |
| V2.06 | 예수금 조회, 집계창 |
| V2.08 | 1분봉 변수이름, 딕셔너리 수정 |
| V2.10 | 1분봉 백테엔진, 최적화 기준값, 결과 그래프 |
| V2.14 | 업비트 주문체결 |
| V2.15 | G2M 기준값 |
| V2.17 | 네이버 뉴스 크롤링 |
| V2.18 | 매수전략 보조지표 라인분리 |
| V2.19 | 실시간 데이터 수신 순서, 전략연산 |
| V2.20 | 코스닥목록, 텔레그램, 시드부족 |
| V2.21(a) | 백테엔진 시간설정 |
| V2.21 | 매도잔량/매수잔량 차트 위치, 잔고청산 |
| V2.22 | 해선 오타, 체결필드, 지수차트, 백테 중지 |
| V2.23 | 조건최적화 롱숏, 썸머타임 |
| V2.24 | 분봉 실시간차트 |
| V2.25 | 텔레그램 잔고목록, 매매건수 0 |
| V2.26 | 보유수량, 분봉 보유시간, 잔고청산 |
| V2.27 | CheckboxChanged_19, 선물 주문 |
| V2.28 | 코인 시그널 취소 |
| V2.29 | 수동잔고청산 텔레그램 |
| V2.30 | 해선 숏포지션 차트, 종목정보, 웹크롤링 주소 |
| V2.31 | 테이블위젯 갱신 |
| V2.33 | 타임프레임 실시간차트, 주문유형 경고, 포지션 키값 |
| V2.34 | 보유시간 조건 버튼, 차트창, 백테상세기록, 백테데이터 부족, 전략삭제, 보조지표 |
| V2.35 | 차트창 팩터 이름 오타 |
| V2.36 | 바이낸스선물 USDT, 옵튜나 부정소수점 |

### 5.6 기능 개선/변경
| 버전 | 개선 내용 |
|------|-----------|
| V2.35 | UI 타이틀바에 데이터타입 표시 추가 |
| V2.36 | 검증/교차검증 MERGE값 합산 방법 변경 (곱셈→덧셈, 가중치 0.7/0.3) |

---

## 6. 파일 변경 매핑 (V1 → V2.33)

### 6.1 신규 생성 파일
```
future/__init__.py
future/future_agent_min.py        (V2.00→V2.19 리네이밍)
future/future_agent_tick.py       (V2.00→V2.19 리네이밍, V2.00의 future_kiwoom.py 기원)
future/future_manager.py
future/future_strategy_min.py
future/future_strategy_tick.py
future/future_trader.py
future/login_future/manuallogin.py
future/login_future/versionupdater.py
stock/kiwoom_agent_min.py         (V2.19 리네이밍)
stock/kiwoom_agent_tick.py        (V2.19 리네이밍, stock/kiwoom.py 기원)
utility/blacklist_future.txt
utility/database_read_only.py
utility/telegram_bot.py           (V2.01, telegram_msg.py 대체)
.gitignore                        (V2.23)
```

### 6.2 삭제된 파일
```
ui/ui_mainwindow.py              → ui/ui_mainwindow.pyd (V2.00, V1U에서는 .py 유지)
ui/set_logfile.py                (V2.15에서 삭제)
stock/kiwoom.py                  → stock/kiwoom_agent_tick.py (V2.19)
stock/kiwoom_receiver_client.py  → stock/kiwoom_agent_client.py (V2.19) → 삭제(V2.26)
stock/kiwoom_receiver_min.py     → stock/kiwoom_agent_min.py (V2.19)
stock/kiwoom_receiver_tick.py    (V2.19에서 통합)
stock/login_kiwoom/autologin2.py (V2.04에서 삭제)
coin/binance_receiver_client.py  (V2.26에서 삭제)
coin/upbit_receiver_client.py    (V2.26에서 삭제)
future/future_receiver_tick.py   (V2.19에서 통합)
future/future_receiver_client.py → future/future_agent_client.py (V2.19) → 삭제(V2.26)
future/future_receiver_min.py    → future/future_agent_min.py (V2.19)
future/future_kiwoom.py          → future/future_agent_tick.py (V2.19)
utility/telegram_msg.py          → utility/telegram_bot.py (V2.01)
utility/db_update_back.py        (V2.07에서 삭제)
utility/db_update_day.py         (V2.07에서 삭제)
utility/_db_update_back_20240504.bat  (V2.07에서 삭제)
utility/_db_update_day_20240504.bat   (삭제)
```

### 6.3 리네이밍된 파일 (V2.11 중심)
```
ui/set_cbtap.py          → ui/set_stg_coin_tap.py
ui/set_sbtap.py          → ui/set_stg_stock_tap.py
ui/set_setuptap.py       → ui/set_setup_tap.py
ui/set_ordertap.py       → ui/set_order_tap.py
ui/set_mainmenu.py       → ui/set_main_menu.py
ui/set_logtap.py         → ui/set_log_tap.py
ui/ui_activated_b.py     → ui/ui_activated_back.py
ui/ui_activated_c.py     → ui/ui_activated_coin_stg.py
ui/ui_activated_s.py     → ui/ui_activated_stock_stg.py
ui/ui_button_clicked_db.py     → ui/ui_button_clicked_dialog_database.py
ui/ui_button_clicked_ob.py     → ui/ui_button_clicked_order.py
ui/ui_button_clicked_sd.py     → ui/ui_button_clicked_dialog_backengine.py
ui/ui_button_clicked_mn.py     → ui/ui_button_clicked_shortcut.py
ui/ui_button_clicked_sj.py     → ui/ui_button_clicked_settings.py
ui/ui_button_clicked_etsj.py   → ui/ui_button_clicked_dialog_elapsed_tick_number.py
ui/ui_button_clicked_ss_cs.py  → ui/ui_button_clicked_editer_backlog.py
ui/ui_button_clicked_svc.py    → ui/ui_button_clicked_editer_opti_stock.py
ui/ui_button_clicked_svj.py    → ui/ui_button_clicked_editer_stock.py
ui/ui_button_clicked_cvc.py    → ui/ui_button_clicked_editer_opti_coin.py
ui/ui_button_clicked_cvj.py    → ui/ui_button_clicked_editer_coin.py
ui/ui_button_clicked_svjb.py   → ui/ui_button_clicked_editer_stg_buy_stock.py
ui/ui_button_clicked_svjs.py   → ui/ui_button_clicked_editer_stg_sell_stock.py
ui/ui_button_clicked_cvjb.py   → ui/ui_button_clicked_editer_stg_buy_coin.py
ui/ui_button_clicked_cvjs.py   → ui/ui_button_clicked_editer_stg_sell_coin.py
ui/ui_button_clicked_cvoa.py   → ui/ui_button_clicked_editer_ga_coin.py
ui/ui_button_clicked_svoa.py   → ui/ui_button_clicked_editer_ga_stock.py
```

---

## 7. 개발 실행 계획 (단계별)

### 규칙
1. 각 단계는 해당 V2 커밋의 변경사항을 V1U에 반영
2. `ui/ui_mainwindow.py`는 소스코드(.py) 형태를 유지
3. 각 단계 완료 후 `STOM V1U.XX` 형식으로 커밋
4. 주변 파일은 V2 커밋의 diff를 참조하여 동일하게 변경
5. `ui_mainwindow.py`는 pyd 분석 불가능하므로, 주변 파일 변경과 커밋 메시지를 기반으로 추론하여 반영
6. `ui_mainwindow.pyd` 파일은 V1U에 추가하지 않음 (소스코드 유지 원칙)

### 단계 목록

#### Step 1: STOM V1U.00 (← V2.00)
**난이도: 최고 | 변경파일: 135개**
- [ ] future/ 폴더 전체 신규 생성
- [ ] 키움증권 해외선물 관련 전 모듈 추가
- [ ] 인증 시스템 코드 추가 (ui_mainwindow.py에 시리얼키 관련 로직)
- [ ] 스톰 라이브: 웹소켓 → ZMQ 변경 (LiveSender, LiveClient, ZmqServ, ZmqRecv 수정)
- [ ] strftime/strptime 전면 수정
- [ ] 트레이더 코드 한글화
- [ ] GA 최적화 방식 변경
- [ ] DB 구조 변경 (codename → stockinfo, code_info.db)
- [ ] ui_mainwindow.py: import 추가, 해선 관련 메서드 추가, 인증/라이브 변경

#### Step 2: STOM V1U.01 (← V2.01)
**난이도: 중 | 변경파일: 62개**
- [ ] 수익율 → 수익률 전체 변경
- [ ] utility/telegram_msg.py → utility/telegram_bot.py 교체
- [ ] pip_install 배치파일 수정
- [ ] ui_mainwindow.py: telegram import 변경

#### Step 3: STOM V1U.02 (← V2.02)
**난이도: 상 | 변경파일: 30개**
- [ ] 트레이더 및 전략연산: DataFrame → Dictionary 전환
- [ ] ui_mainwindow.py: 소폭 변경 (pyd 크기 동일이므로)

#### Step 4: STOM V1U.03 (← V2.03)
**난이도: 상 | 변경파일: 24개**
- [ ] future 모듈 대규모 개편 (계정 하나로 통합)
- [ ] future_kiwoom.py 대규모 확장

#### Step 5: STOM V1U.04 (← V2.04)
**난이도: 최고 | 변경파일: 40개**
- [ ] stock/kiwoom.py 대규모 개편 (계정 통합)
- [ ] stock/login_kiwoom/autologin1.py → autologin.py
- [ ] stock/login_kiwoom/autologin2.py 삭제
- [ ] 설정 UI 변경

#### Step 6: STOM V1U.05 (← V2.05)
**난이도: 중 | 변경파일: 33개**
- [ ] 당일실현손익 거래횟수 추가
- [ ] 종료 속도 개선
- [ ] 해선 호가창 오류 수정

#### Step 7: STOM V1U.06 (← V2.06)
**난이도: 중 | 변경파일: 50+개**
- [ ] 테스트모드 추가
- [ ] .keys() 전면 삭제
- [ ] llvmlite 버전 지정

#### Step 8: STOM V1U.07 (← V2.07)
**난이도: 중 | 변경파일: 15개**
- [ ] 미체결 체잔목록 속도 개선
- [ ] 호가 DataFrame → Dict
- [ ] 구 DB 업데이트 파일 삭제

#### Step 9: STOM V1U.08 (← V2.08)
**난이도: 하 | 변경파일: 20개**
- [ ] 1분봉 변수이름 오류 수정
- [ ] 딕셔너리 수정 오류 수정

#### Step 10: STOM V1U.09 (← V2.09)
**난이도: 상 | 변경파일: 31개**
- [ ] 백테엔진 공유메모리 적용
- [ ] 피클파일 분할로딩 개선
- [ ] 백테엔진 어레이 순환 속도 개선

#### Step 11: STOM V1U.10 (← V2.10)
**난이도: 상 | 변경파일: 32개**
- [ ] 다수 백테/최적화 오류 수정
- [ ] 최적화 기준값 설정 변경
- [ ] 전략/범위 저장 큐스레드 변경

#### Step 12: STOM V1U.11 (← V2.11)
**난이도: 최고 | 변경파일: 45+개**
- [ ] **UI 파일명/함수명 전체 리네이밍** (약 26개 파일)
- [ ] loguru 로거 도입
- [ ] ui_mainwindow.py: 모든 import 문 변경, 로거 관련 코드 추가

#### Step 13: STOM V1U.12 (← V2.12)
**난이도: 중 | 변경파일: 20개**
- [ ] 백테엔진 멀티수 = CPU 코어수
- [ ] 옵튜나 기준값 개선

#### Step 14: STOM V1U.13 (← V2.13)
**난이도: 중 | 변경파일: 4개**
- [ ] 그리드 최적화 전면 변경

#### Step 15: STOM V1U.14 (← V2.14)
**난이도: 하 | 변경파일: 4개**
- [ ] 조건편집기 매수조건 변경
- [ ] 집계 속도 개선

#### Step 16: STOM V1U.15 (← V2.15)
**난이도: 상 | 변경파일: 60+개**
- [ ] V2.11 구파일 완전 삭제
- [ ] 인증 강화 (인터넷 미연결 시 종료)
- [ ] ui_mainwindow.py: 인증 관련 코드 추가 (pyd +12,800)

#### Step 17: STOM V1U.16 (← V2.16)
**난이도: 중 | 변경파일: 46+개**
- [ ] 읽기전용 DB 연결 통일
- [ ] ui_mainwindow.py: DB 접근 방식 변경 (pyd +512)

#### Step 18: STOM V1U.17 (← V2.17)
**난이도: 하 | 변경파일: 17개**
- [ ] 네이버 뉴스 크롤링 오류 수정
- [ ] ui_mainwindow.py: 소폭 변경 가능

#### Step 19: STOM V1U.18 (← V2.18)
**난이도: 상 | 변경파일: 36개**
- [ ] 테이블위젯 차이셀만 갱신
- [ ] 백테스터 중복코드 삭제
- [ ] 전략 보조지표 오류 수정

#### Step 20: STOM V1U.19 (← V2.19)
**난이도: 최고 | 변경파일: 39개**
- [ ] **리시버→에이전트 대규모 리네이밍**
- [ ] PyQT 이벤트루프 전환
- [ ] ui_mainwindow.py: import/프로세스 관리 코드 변경 (pyd +512)

#### Step 21: STOM V1U.20 (← V2.20)
**난이도: 중 | 변경파일: 35개**
- [ ] 단축키 변경 (Ctrl+Shift → Shift)
- [ ] Shift+Q 추가
- [ ] ui_mainwindow.py: 키이벤트 핸들러 변경 (pyd -3,072)

#### Step 22: STOM V1U.21a (← V2.21 첫 번째)
**난이도: 하 | 변경파일: 9개**
- [ ] 백테엔진 코드 구조 개선
- [ ] 시간설정 수정

#### Step 23: STOM V1U.21 (← V2.21 두 번째)
**난이도: 중 | 변경파일: 25개**
- [ ] 초당/분당 거래대금 연산 개선
- [ ] python 실행파일명 변경
- [ ] 잔고청산 오류 수정

#### Step 24: STOM V1U.22 (← V2.22)
**난이도: 중 | 변경파일: 22개**
- [ ] 해선 오타/오류 수정
- [ ] 그리드 최적화 계수 변경

#### Step 25: STOM V1U.23 (← V2.23)
**난이도: 상 | 변경파일: 37개**
- [ ] .gitignore 추가
- [ ] 백테엔진 대폭 간소화
- [ ] 리시버공유 관련 코드 정리 시작
- [ ] ui_mainwindow.py: 대폭 축소 (pyd -55,808)

#### Step 26: STOM V1U.24 (← V2.24)
**난이도: 중 | 변경파일: 21개**
- [ ] 분봉 실시간차트 데이터 오류 수정

#### Step 27: STOM V1U.25 (← V2.25)
**난이도: 하 | 변경파일: 7개**
- [ ] 코인 텔레그램 오류, 매매건수 0 오류 수정

#### Step 28: STOM V1U.26 (← V2.26)
**난이도: 상 | 변경파일: 37+개**
- [ ] 리시버 공유 모드 완전 삭제
- [ ] receiver_client 파일들 삭제
- [ ] ui_mainwindow.py: 리시버공유 관련 코드 제거 (pyd -1,536)

#### Step 29: STOM V1U.27 (← V2.27)
**난이도: 하 | 변경파일: 9개**
- [ ] CheckboxChanged_19 오류 수정
- [ ] 선물 주문 오류 수정

#### Step 30: STOM V1U.28 (← V2.28)
**난이도: 하 | 변경파일: 9개**
- [ ] 코인 시그널 취소 오류 수정

#### Step 31: STOM V1U.29 (← V2.29)
**난이도: 하 | 변경파일: 7개**
- [ ] cell_clicked_03 칼럼 추가
- [ ] 코인 수동잔고청산 텔레그램 수정

#### Step 32: STOM V1U.30 (← V2.30)
**난이도: 중 | 변경파일: 33개**
- [ ] 해선 차트 숏포지션 표시 수정
- [ ] 웹크롤링 주소 변경

#### Step 33: STOM V1U.31 (← V2.31)
**난이도: 하 | 변경파일: 3개**
- [ ] 테이블위젯 갱신 오류 수정
- [ ] ui_mainwindow.py: 소폭 변경 (pyd +1,024)

#### Step 34: STOM V1U.33 (← V2.33, V2.32 포함)
**난이도: 하 | 변경파일: 7개**
- [ ] 타임프레임 실시간차트 팩터인덱스 오류 수정
- [ ] 주문유형 경고 추가
- [ ] 전략종료시간 초단위 경고

#### Step 35: STOM V1U.34 (← V2.34)
**난이도: 중 | 변경파일: 19개**
- [ ] 보유시간 조건 버튼 ':' 누락 수정
- [ ] 스톰 구동 후 타임프레임 설정 변경 시 차트창 오류 수정
- [ ] 백테상세기록 테이블에서 다른 데이터타입 클릭 시 차트 미표시 및 경고창 추가
- [ ] 백테스트 시작 데이터 부족 확인 시 학습/검증기간 합계 확인 오류 수정
- [ ] 디비관리창 전략 삭제 시 갱신 오류 수정
- [ ] 분봉 매수전략에서 보조지표 설정 삽입 시 전략저장 오류 수정
- [ ] 차트 팩터에서 매수전략용 보조지표 세부설정 미반영 오류 수정

#### Step 36: STOM V1U.35 (← V2.35)
**난이도: 하 | 변경파일: 3개**
- [ ] UI 타이틀바에 데이터타입 표시 추가
- [ ] 차트창 팩터 이름 변경 시 오타 수정

#### Step 37: STOM V1U.36 (← V2.36)
**난이도: 중 | 변경파일: 10개**
- [ ] 바이낸스선물 웹소켓 유저데이터 수신 처리 변경 (USDT만 추출)
- [ ] 검증 및 교차검증 최적화 MERGE값 합산 방법 변경
  - 기존: 학습기간 × 검증기간 (곱셈)
  - 변경: (학습기간 × 0.7) + (검증기간 × 0.3) (덧셈, 가중치 적용)
  - 최근 데이터 가중치 적용 시: 검증기간에만 1.3~0.7 가중치
- [ ] 옵튜나 최적화 변수값 소숫점 부정소수점 문제 수정

---

## 8. 개발 방법론

### 8.1 각 단계의 작업 프로세스

```
1. V2 커밋의 diff 확인
   git show --stat <V2_commit>
   git diff <이전_V2_commit>..<현재_V2_commit> -- <파일>

2. 주변 파일 변경사항 분석
   - 새로 추가된 import/export 확인
   - 함수 시그니처 변경 확인
   - 파일 리네이밍 확인

3. ui_mainwindow.py 변경 추론
   - pyd 크기 변화 확인 (변경 유무 판단)
   - 주변 파일의 import 변경으로 ui_mainwindow.py 의 import도 변경 필요 여부 판단
   - 커밋 메시지의 UI 관련 변경사항으로 메서드 추가/변경 추론
   - V1의 ui_mainwindow.py 코드 패턴을 기반으로 신규 코드 작성

4. 변경 적용
   - 주변 파일: V2 diff를 V1U에 적용
   - ui_mainwindow.py: 추론한 변경사항을 소스코드로 작성

5. 검증 (가능한 범위)
   - import 문 유효성 확인
   - 참조하는 함수/변수 존재 여부 확인
   - 클래스 구조 일관성 확인

6. 커밋
   git commit -m "STOM V1U.XX - <변경 요약>"
```

### 8.2 ui_mainwindow.py 추론 원칙

1. **import 변경은 확정적**: 주변 파일이 리네이밍되면 import도 반드시 변경
2. **메서드 위임 패턴 유지**: V1의 `def XXX(self): xxx(self)` 패턴은 V1U에서도 유지
3. **pyd 크기 변화 = 코드 변경**: 크기가 동일하면 ui_mainwindow.py 변경 없음으로 판단
4. **커밋 메시지 기반 추론**: "UI 관련", "단축키", "프로세스", "인증" 키워드에 주목
5. **주변 파일의 함수 시그니처 변경 추적**: 호출측과 피호출측의 일관성 유지

### 8.3 위험 관리

| 위험 | 대응 |
|------|------|
| pyd 내부 로직 추론 불가 | 커밋 메시지 + 주변 파일 변경으로 최대한 추론, 불확실한 부분은 TODO 주석 |
| 단계 간 의존성 | 반드시 순차적 진행, 이전 단계 완료 확인 후 다음 단계 |
| 대규모 리네이밍 충돌 | V2.11(UI 리네이밍), V2.19(에이전트 리네이밍) 단계에서 특별 주의 |
| 인증 시스템 보안 | V2.00의 인증 코드는 커밋 메시지 기반으로 기본 구조만 구현 |

---

## 9. 참조 정보

### 9.1 V1 ui_mainwindow.py 클래스/메서드 전체 목록

```
Classes:
  - LiveSender(Thread)     : 스톰 라이브 소켓 전송
  - LiveClient             : 스톰 라이브 서버 연결
  - Writer(QThread)        : windowQ 처리
  - ZmqServ(QThread)       : ZMQ 서버
  - ZmqRecv(QThread)       : ZMQ 수신
  - MainWindow(QMainWindow): 메인 윈도우

MainWindow Methods (200+):
  - 초기화/타이머: __init__, Qtimer1Start, ProcessStarter, ChartCountChange, UpdateProgressBar
  - 이미지/CPU: UpdateImage, UpdateSQsize, UpdateCpuper, UpdateDictSet
  - 차트: ChartClear, ExtendWindow, CalendarClicked, AutoBackSchedule
  - 비디오/스크린샷: VideoWidgetClose, StomliveScreenshot, ChartScreenShot, ChartScreenShot2
  - 체크박스: CheckboxChanged_01~19, sb/ss/cb/csCheckboxChanged
  - 셀클릭: CellClicked_01~11
  - 텍스트: ReturnPress_01~02, TextChanged_01~04
  - 버튼: ButtonClicked 시리즈 (약 80+개)
  - 백테스트: BackTestengineShow, StartBacktestEngine, BackCodeTest1~3, ClearBacktestQ, BacktestProcessKill
  - 프로세스: StomLiveProcessAlive, CoinReceiverProcessAlive, CoinTraderProcessAlive 등
  - 이벤트: keyPressEvent, eventFilter, closeEvent, ProcessKill
```

### 9.2 커밋 해시 참조표

| 버전 | 커밋 해시 (full) |
|------|------------------|
| V2.00 | `b021269164a44e2d6745b39f098837043f9b7c4d` |
| V2.01 | `9d065c024e993f5cb9bdfeb34442c997795bb30a` |
| V2.02 | `69067bf8413b41b54497a57b85bf252a37242ea0` |
| V2.03 | `1a64c19ab4f96694856a3f5d0d7d2099750e66b7` |
| V2.04 | `23384a486607175ff33c92baf6704b6f757dd863` |
| V2.05 | `fefe04e80aa24e4755c528387a59b350cc1911c4` |
| V2.06 | `18a9fb9372c96eecff1913114fd99918646999e8` |
| V2.07 | `85c854159c3f430255e234a8f824816422858a16` |
| V2.08 | `9ab6caca4a7117b9e1960bbfce4f10f8b34f7ad6` |
| V2.09 | `6bf0546fd8442a9e0c2e833795228aef430ad497` |
| V2.10 | `b701eab846f1dd719d6d5f6073dd4858d607a3a5` |
| V2.11 | `23be27aacac91aaf7210de9c64eb8628c65a7803` |
| V2.12 | `acbc6719804319be049187bdb9981fac69054379` |
| V2.13 | `a0681ec571899ac8654498aee6c7b39e0425a750` |
| V2.14 | `68f55cf68516a0418230a30a5fe18fb5e1664029` |
| V2.15 | `847c8cfb718889eaac52984cbb25da1f7857a07f` |
| V2.16 | `937baf83782d3f2bc22a39ff4fe58ec01e9ce5a1` |
| V2.17 | `244aae5a3876be84983980e21a2e3458c9f0a1a2` |
| V2.18 | `27652c6704e21c55a4cfe4f1bb2fe8ed01a97613` |
| V2.19 | `b9a8d88da1b0d87dd010a43e80db15d65bda4ac5` |
| V2.20 | `6a6321c1fff198e186a5a51f1bcf8102418d7b43` |
| V2.21a | `2f4fc7288e6ad3d84925f8ead6a81255727f1ae3` |
| V2.21 | `15ca982210ead21fd88fd84b9a955b9b68cbf861` |
| V2.22 | `4e2a9f0654a267daf981134b059c99ff9264c337` |
| V2.23 | `0343ebd2b7c58974b5866072324cfa48d8b75c82` |
| V2.24 | `81e1229811029bfd7846b16152cc9567e963f2ab` |
| V2.25 | `487fbda7923111a9447dbb593adfe6f0a094f25b` |
| V2.26 | `7f9bd52472b3ba00d2a49c62c885cd3c935013fa` |
| V2.27 | `699fae65171cd9b64dd48ba4260c97acacb5755f` |
| V2.28 | `db1cfc76829de7500cc32e643805de73c3e452c1` |
| V2.29 | `48882639c2d88c765565a65a806258de49df320a` |
| V2.30 | `4750170d1c3abe9c8825deab730cc89bad283a02` |
| V2.31 | `ecae11b395593ba4e6089a6d806c6d96eb7c03ad` |
| V2.33 | `d7997af87f93bd320bcdf41664c05daa0d732601` |
| V2.34 | `ebc8812e1fb9272e4bc9fc86cf18290cc59ab5b5` |
| V2.35 | `7ff3e033b55cac5e0297de10c558f6aaa22ae9a6` |
| V2.36 | `ddfd9fbdc68bdb78da495f3eccec7273130ac4cc` |

---

## 10. 요약

이 문서는 STOM_Version_1U 브랜치에서 V2의 36개 커밋을 **이해 기반으로 재구현**하기 위한 완전한 개발 계획서입니다.

핵심 차별점:
- **체리픽이 아닌 코드 이해 기반 개발**: 각 V2 커밋의 목적과 구현을 분석하여 V1U에 맞게 재작성
- **ui_mainwindow.py 소스코드 유지**: V2에서 .pyd로 암호화된 파일을 V1U에서는 .py로 유지하며 기능 동등성 확보
- **pyd 크기 변동 기반 추론**: 바이너리 분석 대신 파일 크기 변화와 주변 맥락으로 내부 변경 추론
- **37단계 순차 개발**: 각 단계마다 독립적으로 검증 가능한 커밋 생성
