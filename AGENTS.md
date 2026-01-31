# AGENTS.md - STOM_Version_1U AI 개발 에이전트 가이드

> 이 문서는 STOM_Version_1U 프로젝트의 AI 에이전트(Claude 등)가 코드를 이해하고 개발 작업을 수행하기 위한 **최상위 참조 문서**입니다.
>
> **프로젝트 총괄 문서 (2/3)**: 이 문서는 `README.md`, `CLAUDE.md`와 함께 프로젝트를 총괄합니다.

---

## 0. 문서 체계 및 관리 책임

### 프로젝트 총괄 문서 (최상위 3개)

| 문서 | 역할 | 관리 대상 |
|------|------|----------|
| `README.md` | 프로젝트 소개 및 총괄 | 전체 프로젝트, docs/README.md |
| `AGENTS.md` | 아키텍처 및 개발 가이드 | 전체 프로젝트, docs/README.md |
| `CLAUDE.md` | AI 작업 지침 및 규칙 | 전체 프로젝트, docs/README.md |

### 하위 문서 (docs/)

| 문서 | 역할 | 관리 주체 |
|------|------|----------|
| `docs/README.md` | docs 폴더 문서 총괄 | **상위 3개 문서가 관리** |
| `docs/dev_plan/*.md` | 개발 계획 문서 | docs/README.md |

---

## 1. 프로젝트 정체성

| 항목 | 내용 |
|------|------|
| **프로젝트명** | STOM (System Trading Optimization Machine) |
| **현재 브랜치** | `STOM_Version_1U` |
| **기반 커밋** | `80ab4ec` (STOM V1) |
| **언어** | Python 3.11 (32bit/64bit 듀얼) |
| **프레임워크** | PyQt5 (GUI), ZMQ (프로세스간 통신) |
| **대상 거래소** | 키움증권(주식), 업비트(코인), 바이낸스(코인), 키움증권 해외선물(CME) |
| **라이선스** | 파이퀀트 강좌 수강생 전용 (상업적 이용 불가) |

### 이 프로젝트의 본질
STOM은 **틱데이터 기반 초단타 시스템 트레이딩 도구**입니다. 주식/코인/해외선물의 실시간 데이터 수집, 전략 연산, 자동 주문, 백테스트, 최적화를 하나의 PyQt5 데스크톱 애플리케이션에서 수행합니다.

---

## 2. 핵심 개발 규칙 (CRITICAL)

### 2.1 반드시 참조해야 하는 문서

**개발 작업 시 아래 문서들을 항상 참조하십시오:**

| 순서 | 문서 | 경로 | 용도 |
|------|------|------|------|
| 1 | **개발 계획서** | `docs/dev_plan/STOM_Version_1U_Development_Plan.md` | 37단계 작업 명세 |
| 2 | **문서 허브** | `docs/README.md` | 문서 체계 및 관리 규칙 |
| 3 | **AI 지침** | `CLAUDE.md` | 핵심 규칙 및 체크 프로세스 |

**개발 계획서가 프로젝트의 실행 명세서입니다.**
모든 개발 작업은 이 문서에 정의된 37단계(V1U.00 ~ V1U.36)를 순차적으로 따라야 합니다.

### 2.2 절대 규칙

| # | 규칙 | 이유 |
|---|------|------|
| 1 | **체리픽(cherry-pick) 금지** | V2 커밋을 그대로 가져오면 .pyd 바이너리가 포함되어 ui_mainwindow.py 소스가 손실됨 |
| 2 | **ui/ui_mainwindow.py는 .py 형태 유지** | V2에서 .pyd로 암호화된 것을 V1U에서는 소스코드로 유지해야 함 |
| 3 | **ui/ui_mainwindow.pyd 파일 추가 금지** | 바이너리 파일은 V1U에 존재하면 안 됨 |
| 4 | **순차 개발 필수** | V1U.00 → V1U.01 → ... → V1U.36 순서로만 진행 |
| 5 | **V2 커밋 수와 동일하게 커밋** | V2의 37개 커밋(V2.00~V2.36)과 동일한 수로 V1U도 37개 커밋 진행 |
| 6 | **각 단계 독립 커밋** | 매 단계마다 `STOM V1U.XX` 형식으로 커밋 |
| 7 | **V2 커밋 diff 참조 개발** | 각 단계에서 해당 V2 커밋의 diff를 분석하여 이해 기반으로 재구현 |
| 8 | **체크 과정 필수 포함** | 각 단계마다 검증 체크리스트 완료 후 커밋 (CLAUDE.md 참조) |

### 2.3 ui_mainwindow.py 개발 원칙

`ui/ui_mainwindow.py`는 이 프로젝트에서 가장 핵심적이면서 가장 어려운 파일입니다.

**V2에서는 이 파일이 .pyd(컴파일된 바이너리)로 배포**되어 소스코드를 직접 볼 수 없습니다.
따라서 다음 방법으로 변경사항을 추론해야 합니다:

1. **pyd 파일 크기 변동 추적**: 크기가 변하면 소스에 실질적 변경이 있음
2. **주변 파일 변경 분석**: import/export, 함수 시그니처 변경으로 ui_mainwindow.py의 변경 유추
3. **커밋 메시지 분석**: UI 관련 키워드(단축키, 인증, 프로세스 등)로 내부 변경 추론
4. **V1 코드 패턴 기반 작성**: V1의 메서드 위임 패턴(`def XXX(self): xxx(self)`)을 유지

**pyd 크기 변동 시점 (확인된 변경점):**

| 버전 | 크기 변동 | 추정 변경 |
|------|-----------|-----------|
| V2.15 | +12,800 | 인증 강화, 인터넷 미연결 종료 로직 |
| V2.16 | +512 | 읽기전용 DB 연결 통일 |
| V2.19 | +512 | 리시버→에이전트 리네이밍 반영 |
| V2.20 | -3,072 | 단축키 변경, 코드 간소화 |
| V2.23 | -55,808 | 리시버공유 관련 코드 대규모 삭제 |
| V2.26 | -1,536 | 리시버 공유 모드 완전 삭제 |
| V2.31 | +1,024 | 테이블위젯 갱신 로직 수정 |

---

## 3. 아키텍처 개요

### 3.1 진입점

```
stom.py → MainWindow (ui/ui_mainwindow.py)
         ├── auto_run=0: 수동 실행
         ├── auto_run=1: 주식 자동 실행 (stom_stock.bat)
         └── auto_run=2: 코인 자동 실행 (stom_coin.bat)
```

### 3.2 디렉토리 구조 (V1 현재 상태)

```
STOM_V/
├── stom.py                    # 진입점
├── stom.bat                   # 실행 배치 (수동)
├── stom_stock.bat             # 주식 자동실행
├── stom_coin.bat              # 코인 자동실행
├── _update.txt                # 버전 이력
├── _license.txt               # 라이선스
│
├── docs/
│   └── dev_plan/
│       └── STOM_Version_1U_Development_Plan.md  # ★ 핵심 개발 계획서
│
├── ui/                        # UI 레이어 (PyQt5)
│   ├── ui_mainwindow.py       # ★ 핵심 파일 - MainWindow 클래스
│   ├── set_*.py               # UI 위젯 설정 (탭, 메뉴, 다이얼로그 등)
│   ├── ui_activated_*.py      # 탭 활성화 이벤트
│   ├── ui_button_clicked_*.py # 버튼 클릭 이벤트
│   ├── ui_cell_clicked.py     # 셀 클릭 이벤트
│   ├── ui_checkbox_changed.py # 체크박스 이벤트
│   ├── ui_text_changed.py     # 텍스트 변경 이벤트
│   ├── ui_return_press.py     # 엔터키 이벤트
│   ├── ui_key_press_event.py  # 키보드 이벤트
│   ├── ui_event_filter.py     # 이벤트 필터
│   ├── ui_draw_chart.py       # DB 차트 그리기
│   ├── ui_draw_realchart.py   # 실시간 차트
│   ├── ui_draw_treemap.py     # 트리맵
│   ├── ui_draw_jisuchart.py   # 지수 차트
│   ├── ui_backtest_engine.py  # 백테스트 엔진 UI
│   ├── ui_process_starter.py  # 프로세스 시작
│   ├── ui_process_kill.py     # 프로세스 종료
│   ├── ui_process_alive.py    # 프로세스 생존 확인
│   ├── ui_update_tablewidget.py # 테이블위젯 갱신
│   ├── ui_update_textedit.py  # 텍스트에디트 갱신
│   ├── ui_update_progressbar.py # 프로그레스바 갱신
│   ├── ui_show_dialog.py      # 다이얼로그 표시
│   ├── ui_etc.py              # 기타 UI 함수
│   ├── ui_vars_change.py      # 변수 변경
│   ├── ui_get_label_text.py   # 라벨 텍스트
│   ├── ui_extend_window.py    # 창 확장
│   ├── ui_betting_cotrol.py   # 배팅 제어
│   ├── ui_crosshair.py        # 십자선
│   └── ui_chart_count_change.py # 차트 카운트 변경
│
├── stock/                     # 키움증권 주식 모듈
│   ├── kiwoom.py              # 키움 API 메인 (V2.19에서 kiwoom_agent_tick.py로 변경)
│   ├── kiwoom_manager.py      # 키움 매니저 (32bit 프로세스)
│   ├── kiwoom_receiver_client.py  # 리시버 공유 클라이언트
│   ├── kiwoom_receiver_min.py     # 분봉 리시버
│   ├── kiwoom_receiver_tick.py    # 틱 리시버 (V2.19에서 통합됨)
│   ├── kiwoom_rest.py             # REST API
│   ├── kiwoom_strategy_min.py     # 분봉 전략연산
│   ├── kiwoom_strategy_tick.py    # 틱 전략연산
│   ├── kiwoom_trader.py           # 트레이더
│   └── login_kiwoom/             # 키움 로그인
│       ├── autologin1.py         # 자동로그인 1
│       ├── autologin2.py         # 자동로그인 2 (V2.04에서 삭제)
│       ├── manuallogin.py        # 수동로그인
│       └── versionupdater.py     # 버전업데이터
│
├── coin/                      # 코인 모듈 (바이낸스 + 업비트)
│   ├── binance_receiver_client.py  # 바이낸스 리시버 공유 클라이언트
│   ├── binance_receiver_min.py     # 바이낸스 분봉 리시버
│   ├── binance_receiver_tick.py    # 바이낸스 틱 리시버
│   ├── binance_strategy_min.py     # 바이낸스 분봉 전략
│   ├── binance_strategy_tick.py    # 바이낸스 틱 전략
│   ├── binance_trader.py           # 바이낸스 트레이더
│   ├── binance_websocket.py        # 바이낸스 웹소켓
│   ├── upbit_receiver_client.py    # 업비트 리시버 공유 클라이언트
│   ├── upbit_receiver_min.py       # 업비트 분봉 리시버
│   ├── upbit_receiver_tick.py      # 업비트 틱 리시버
│   ├── upbit_strategy_min.py       # 업비트 분봉 전략
│   ├── upbit_strategy_tick.py      # 업비트 틱 전략
│   ├── upbit_trader.py             # 업비트 트레이더
│   ├── upbit_websocket.py          # 업비트 웹소켓
│   └── kimp_upbit_binance.py       # 김치프리미엄
│
├── backtester/                # 백테스트 엔진
│   ├── backtest.py            # 백테스트 메인
│   ├── backfinder.py          # 백파인더
│   ├── back_code_test.py      # 코드 테스트
│   ├── back_static.py         # 정적 계산
│   ├── back_subtotal.py       # 중간 집계
│   ├── backengine_kiwoom_tick.py   # 키움 틱 백테엔진
│   ├── backengine_kiwoom_tick2.py  # 키움 틱 백테엔진2
│   ├── backengine_kiwoom_min.py    # 키움 분봉 백테엔진
│   ├── backengine_kiwoom_min2.py   # 키움 분봉 백테엔진2
│   ├── backengine_binance_tick.py  # 바이낸스 틱 백테엔진
│   ├── backengine_binance_tick2.py # 바이낸스 틱 백테엔진2
│   ├── backengine_binance_min.py   # 바이낸스 분봉 백테엔진
│   ├── backengine_binance_min2.py  # 바이낸스 분봉 백테엔진2
│   ├── backengine_upbit_tick.py    # 업비트 틱 백테엔진
│   ├── backengine_upbit_tick2.py   # 업비트 틱 백테엔진2
│   ├── backengine_upbit_min.py     # 업비트 분봉 백테엔진
│   ├── backengine_upbit_min2.py    # 업비트 분봉 백테엔진2
│   ├── optimiz.py                  # 최적화 (그리드)
│   ├── optimiz_conditions.py       # 최적화 조건
│   ├── optimiz_genetic_algorithm.py # 유전 알고리즘
│   └── rolling_walk_forward_test.py # 전진분석
│
├── utility/                   # 유틸리티
│   ├── static.py              # 상수/정적 데이터 (columns, 변수명 등)
│   ├── setting.py             # 설정 관리 (DB 읽기/쓰기)
│   ├── query.py               # SQL 쿼리
│   ├── chart.py               # 차트 유틸리티
│   ├── hoga.py                # 호가 유틸리티
│   ├── database_check.py      # DB 무결성 확인
│   ├── telegram_msg.py        # 텔레그램 메시지 (V2.01에서 telegram_bot.py로 변경)
│   ├── webcrawling.py         # 웹크롤링
│   ├── sound.py               # 소리 알림
│   ├── timesync.py            # 시간 동기화
│   ├── db_distinct.py         # DB 중복제거
│   ├── db_update_back.py      # DB 업데이트 (V2.07에서 삭제)
│   ├── db_update_day.py       # DB 업데이트 (V2.07에서 삭제)
│   ├── total_code_line.py     # 코드 라인수 계산
│   └── syntax.py              # 문법 하이라이트
│
├── lecture/                   # 강의 자료
│   ├── imagefiles/            # 이미지 파일
│   ├── pycharm/               # PyCharm 설정
│   └── testcode/              # 테스트 코드
│
└── icon/                      # 아이콘 리소스
```

### 3.3 V2 개발 후 최종 구조 변경 예정 사항

V1U가 V2.36까지 개발 완료되면 다음 변경이 반영됩니다:

**신규 디렉토리/파일:**
- `future/` 폴더 전체 (해외선물 모듈)
- `utility/telegram_bot.py` (텔레그램봇 교체)
- `utility/database_read_only.py` (읽기전용 DB)
- `.gitignore`

**리네이밍 (V2.11 UI 파일명):**
- `set_cbtap.py` → `set_stg_coin_tap.py` 외 25개 파일

**리네이밍 (V2.19 에이전트):**
- `stock/kiwoom.py` → `stock/kiwoom_agent_tick.py`
- `stock/kiwoom_receiver_*` → `stock/kiwoom_agent_*`
- `future/future_kiwoom.py` → `future/future_agent_tick.py`

**삭제:**
- 리시버 공유 관련 클라이언트 파일들 (V2.26)
- 구 DB 업데이트 파일들 (V2.07)
- `stock/login_kiwoom/autologin2.py` (V2.04)

### 3.4 프로세스 아키텍처

```
[stom.py] MainWindow (64bit)
    │
    ├── [stock/kiwoom_manager.py]     키움매니저 (32bit, 키움 API)
    │   ├── 주식 에이전트 (틱/분봉 데이터 수집)
    │   └── 주식 트레이더 (주문 실행)
    │
    ├── [coin/binance_*.py]           바이낸스 모듈
    │   ├── 웹소켓 (실시간 데이터)
    │   ├── 리시버 (데이터 전처리)
    │   ├── 전략연산 (틱/분봉)
    │   └── 트레이더 (주문)
    │
    ├── [coin/upbit_*.py]             업비트 모듈
    │   ├── 웹소켓 (실시간 데이터)
    │   ├── 리시버 (데이터 전처리)
    │   ├── 전략연산 (틱/분봉)
    │   └── 트레이더 (주문)
    │
    ├── [future/*]                    해외선물 (V2.00에서 추가)
    │   ├── 에이전트 (데이터 수집)
    │   ├── 매니저 (32bit)
    │   ├── 전략연산 (틱/분봉)
    │   └── 트레이더 (주문)
    │
    └── [backtester/*]                백테스트 엔진
        ├── 멀티프로세스 백테엔진
        ├── 최적화 (그리드/GA/옵튜나)
        └── 전진분석
```

### 3.5 프로세스 간 통신

| 방식 | 용도 |
|------|------|
| `multiprocessing.Queue` | 프로세스 간 데이터 전달 |
| `ZMQ (zmq)` | 32bit ↔ 64bit 프로세스 통신, 스톰 라이브 |
| `PyQt5 Signal/Slot` | UI 스레드 간 통신 |
| `SharedMemory` | 백테엔진 데이터 공유 (V2.09) |

### 3.6 데이터베이스 구조

| DB 파일 | 용도 |
|---------|------|
| `setting.db` | 설정값 (계정, 전략, 변수, 범위 등) |
| `tradelist.db` | 거래 내역, 당일실현손익 |
| `code_info.db` | 종목정보 (V2.00에서 추가) |
| `*.db` (일자별) | 틱/분봉 데이터 저장 |

---

## 4. 코드 패턴 이해

### 4.1 MainWindow 메서드 위임 패턴

`ui_mainwindow.py`의 MainWindow 클래스는 대부분의 로직을 외부 모듈에 위임합니다:

```python
# ui/ui_mainwindow.py 패턴
class MainWindow(QMainWindow):
    def CheckboxChanged_01(self, state): checkbox_changed_01(self, state)
    def CellClicked_01(self, row, col): cell_clicked_01(self, row, col)
    def sjButtonClicked_01(self): sj_button_cicked_01(self)
    # ... 약 200개 메서드가 이 패턴
```

이 패턴을 이해해야 V2 변경사항을 올바르게 반영할 수 있습니다:
- **import 변경** = 위임 대상 모듈 파일명이 바뀜
- **메서드 추가** = 새로운 UI 이벤트 핸들러가 추가됨
- **메서드 삭제** = 해당 기능이 제거됨

### 4.2 전략연산 구조

```python
# 전략연산 프로세스 실행 흐름
MainWindow → ProcessStarter → strategy_tick/strategy_min 프로세스 생성
                                    ↓
                              데이터 수신 (Queue)
                                    ↓
                              전략 조건 판단
                                    ↓
                              시그널 생성 → Trader Queue
```

### 4.3 데이터 흐름

```
거래소 API/웹소켓 → Receiver → Queue → Strategy → Signal → Trader → 주문
                       ↓
                   DB 저장 (틱/분봉)
                       ↓
                   UI 갱신 (테이블, 차트)
```

### 4.4 변수 네이밍 컨벤션

| 접두사 | 의미 |
|--------|------|
| `self.dict_` | 딕셔너리 변수 |
| `self.list_` | 리스트 변수 |
| `self.df_` | DataFrame 변수 (V2.02에서 dict로 전환) |
| `*Q` | Queue 변수 (windowQ, stockQ, coinQ 등) |
| `columns_` | 테이블 컬럼 정의 (utility/static.py) |

### 4.5 한글 변수/함수명 사용

이 프로젝트는 다수의 한글 변수명을 사용합니다:
```python
수익률, 수익금합계, 매수금액, 매도금액, 보유수량, 거래횟수,
누적매수금액, 누적수익금, 최고기준값, 전략종료시간, ...
```

이는 의도된 설계이며 V2에서도 동일하게 유지됩니다.

---

## 5. 개발 작업 프로토콜

### 5.1 새로운 개발 단계 시작 시

```
1. docs/dev_plan/STOM_Version_1U_Development_Plan.md 의 해당 Step 확인
2. V2 커밋의 diff 분석: git show --stat <V2_commit>
3. 파일별 상세 diff 확인: git diff <이전커밋>..<현재커밋> -- <파일>
4. ui_mainwindow.py 변경 필요 여부 판단 (pyd 크기 변동 표 참조)
5. 변경 적용 (주변 파일 → ui_mainwindow.py 순서)
6. 커밋: "STOM V1U.XX - <변경 요약>"
```

### 5.2 코드 수정 시 주의사항

- **V2의 diff를 참조하되 맹목적으로 복사하지 않음**: V1U의 현재 코드 상태에 맞게 적용
- **파일 리네이밍 시**: import 문, 모든 참조 코드, 배치파일까지 함께 변경
- **함수 시그니처 변경 시**: 호출측과 피호출측 모두 확인
- **데이터 구조 변경 시**: DataFrame → Dict 전환 등은 연관 모듈 전체 확인

### 5.3 검증 체크리스트

- [ ] import 문이 존재하는 파일을 참조하는가
- [ ] 함수 시그니처가 호출측/피호출측에서 일치하는가
- [ ] ui_mainwindow.py의 메서드가 외부 모듈의 함수와 대응하는가
- [ ] 한글 변수명이 일관되게 사용되는가 (수익율 vs 수익률 주의)
- [ ] Queue 변수명이 프로세스 간에 일치하는가

---

## 6. 주요 리팩토링 이정표

### 6.1 V1U.00 (V2.00) - 해외선물 추가, 인증, 라이브 변경
- 가장 큰 변경. future/ 폴더 전체 생성, 135개 파일 변경
- ui_mainwindow.py에 인증 시스템, 해선 라이브, 해선 UI 요소 추가

### 6.2 V1U.02 (V2.02) - DataFrame → Dictionary 전환
- 트레이더와 전략연산의 핵심 데이터 구조 변경
- 성능 향상의 기반이 되는 구조적 변경

### 6.3 V1U.11 (V2.11) - UI 파일 대규모 리네이밍
- 26개 UI 파일의 이름이 약어에서 풀네임으로 변경
- ui_mainwindow.py의 모든 import 문 변경 필요

### 6.4 V1U.19 (V2.19) - 리시버→에이전트 리네이밍
- stock/kiwoom.py → stock/kiwoom_agent_tick.py
- 리시버와 키움 프로세스 통합, PyQT 이벤트루프 전환
- 프로세스 아키텍처 변경

### 6.5 V1U.23 (V2.23) - 리시버공유 코드 대폭 삭제
- ui_mainwindow.py에서 -55,808 bytes 감소
- 가장 큰 코드 삭감 단계

### 6.6 V1U.26 (V2.26) - 리시버 공유 모드 완전 삭제
- receiver_client 파일들 완전 삭제
- 아키텍처 단순화 완료

---

## 7. 커밋 규칙 (상세)

### 버전 매칭 원칙

**V1U.XX는 반드시 V2.XX와 1:1 매칭됩니다:**

| V2 커밋 | V1U 커밋 | 매칭 관계 |
|---------|----------|----------|
| V2.00 | V1U.00 | 해외선물 추가 |
| V2.01 | V1U.01 | 텔레그램봇 업그레이드 |
| V2.02 | V1U.02 | DataFrame → Dict 전환 |
| ... | ... | ... |
| V2.36 | V1U.36 | MERGE값 합산 변경 |

### 커밋 메시지 형식

커밋 메시지는 **상세하게** 작성합니다. 상세 형식은 `CLAUDE.md`의 "커밋 규칙 (상세)" 섹션을 참조하십시오.

```
STOM V1U.XX - <핵심 변경 요약>

## 대응 V2 커밋
- V2.XX (<commit_hash>)
- 원본 커밋 메시지: <V2 커밋 메시지>

## 변경 내역
1. <변경 사항 1>
   - 상세 설명
   - 영향 받는 파일: <파일 목록>

2. <변경 사항 2>
   - 상세 설명
   - 영향 받는 파일: <파일 목록>

## ui_mainwindow.py 변경 (해당 시)
- pyd 크기 변동: <이전> → <현재> (<변동량>)
- 추론 근거: <분석 내용>
- 적용 내용: <변경 내용>

## 검증 체크리스트
- [x] import 문 검증 완료
- [x] 함수 시그니처 일치 확인
- [x] 변수명 일관성 확인
- [x] Queue 변수명 일치 확인
- [x] ui_mainwindow.py 메서드-외부함수 대응 확인
```

> **참고**: 전체 커밋 메시지 예시는 `CLAUDE.md`를 참조하십시오.

---

## 8. 파일별 역할 상세

### 8.1 ui/ui_mainwindow.py (1081줄, V1 기준)

| 클래스 | 역할 |
|--------|------|
| `LiveSender(Thread)` | 스톰 라이브 서버로 실시간 데이터 전송 |
| `LiveClient` | 스톰 라이브 서버 연결 및 데이터 수신/처리 |
| `Writer(QThread)` | windowQ에서 데이터를 읽어 UI 갱신 명령 처리 |
| `ZmqServ(QThread)` | ZMQ 서버 (32bit 프로세스와 통신) |
| `ZmqRecv(QThread)` | ZMQ 수신 (외부 명령 수신) |
| `MainWindow(QMainWindow)` | 메인 윈도우 (200+ 메서드, 모두 외부 위임) |

### 8.2 utility/static.py

- 전체 프로젝트에서 사용하는 상수, 컬럼명, 시간 관련 함수 정의
- `columns_tt`, `columns_nd`, `columns_sd` 등 테이블 컬럼 상수
- `now()`, `timedelta_sec()` 등 시간 유틸리티
- V2에서 DataFrame 관련 코드가 Dict 기반으로 변경됨

### 8.3 utility/setting.py

- SQLite DB(setting.db) 기반 설정 관리
- 계정, 전략, 변수, 범위, 종목정보 등 CRUD
- V2.04에서 계정 구조 변경 (주식/해선 통합)
- V2.16에서 읽기전용 DB 연결 도입

### 8.4 backtester/optimiz.py

- 그리드 최적화 메인 로직
- V2.13에서 전면 개편 (최적값 변경 기준 계수 도입)
- V2.22에서 계수 로직 재변경

---

## 9. 에이전트 작업 시 참조 명령어

### Git 참조 명령어

```bash
# 특정 V2 커밋의 변경 파일 목록
git show --stat <V2_commit_hash>

# 특정 V2 커밋의 상세 diff
git diff <이전커밋>..<현재커밋> -- <파일경로>

# V1 원본의 특정 파일 내용 확인
git show 80ab4ec:<파일경로>

# V2 특정 버전의 파일 내용 확인
git show <V2_commit>:<파일경로>

# 두 버전 간 특정 파일 비교
git diff 80ab4ec..<V2_commit> -- <파일경로>
```

### 전체 V2 커밋 해시 (빠른 참조)

```
V2.00  b021269    V2.01  9d065c0    V2.02  69067bf    V2.03  1a64c19
V2.04  23384a4    V2.05  fefe04e    V2.06  18a9fb9    V2.07  85c8541
V2.08  9ab6cac    V2.09  6bf0546    V2.10  b701eab    V2.11  23be27a
V2.12  acbc671    V2.13  a0681ec    V2.14  68f55cf    V2.15  847c8cf
V2.16  937baf8    V2.17  244aae5    V2.18  27652c6    V2.19  b9a8d88
V2.20  6a6321c    V2.21a 2f4fc72    V2.21  15ca982    V2.22  4e2a9f0
V2.23  0343ebd    V2.24  81e1229    V2.25  487fbda    V2.26  7f9bd52
V2.27  699fae6    V2.28  db1cfc7    V2.29  4888263    V2.30  4750170
V2.31  ecae11b    V2.33  d7997af    V2.34  ebc8812    V2.35  7ff3e03
V2.36  ddfd9fb
```

---

## 10. 진행 상태 추적

개발 진행 상태는 각 단계 커밋의 존재 여부로 확인합니다:

```bash
git log --oneline STOM_Version_1U
```

현재 상태: **V1U 개발 시작 전** (80ab4ec STOM V1 기반)

다음 작업: **Step 1 - STOM V1U.00** (← V2.00, 키움증권 해외선물 추가)

### V2.34 ~ V2.36 신규 커밋 요약

| 버전 | 커밋 | 날짜 | 핵심 변경 |
|------|------|------|-----------|
| V2.34 | `ebc8812` | 2026-01-23 | 보유시간 조건, 차트창, 백테상세기록, 보조지표 오류 수정 |
| V2.35 | `7ff3e03` | 2026-01-26 | UI 타이틀바에 데이터타입 표시, 팩터 이름 오타 |
| V2.36 | `ddfd9fb` | 2026-01-27 | 바이낸스선물 USDT 추출, MERGE값 합산 방법 변경, 옵튜나 부정소수점 |

pyd 크기: 모두 846,848 (V2.33과 동일) → ui_mainwindow.py 변경 없음 추정
