# V3U 확장 자동 검증 감사 (2026-05-12)

작성일: 2026-05-12
대상 worktree: C:\System_Trading\STOM\STOM_V.wt-3u
대상 branch: STOM_Version_3U
HEAD: 4a4d989c V3U 인수인계 검증 체크리스트와 직접 개발 검토를 고정한다
선행 감사: docs/update_log/2026-05-06_v3u_final_parity_audit.md
선행 체크리스트: docs/update_log/2026-05-07_v3u_handoff_verification_checklist.md

## 1. 목적

선행 체크리스트의 25개 사용자 검증 항목 중 헤드리스(`QT_QPA_PLATFORM=offscreen`) 환경에서 자동화 가능한 항목을 본 세션에서 모두 시도하여 사용자 부담을 줄이고 잔여 위험을 좁히는 것을 목표로 한다.

본 감사는 `STOM_Version_3U`의 source diff를 일체 변경하지 않으며 산출물은 `.omx/logs/v3u/automation_2026_05_12/` 하위 로그와 본 문서뿐이다.

## 2. 실행 환경

| 구성 | 값 |
|---|---|
| Python | 3.13.13 |
| PyQt5 | OK |
| psutil | 7.2.2 |
| pytest-qt | 미설치 (대체: 직접 `setCurrentIndex` 호출) |
| QPA platform | `offscreen` |
| 환경변수 | `STOM_ALLOW_MINIMAL_SETTING=1`, `PYTHONIOENCODING=utf-8` |
| Qt 속성 사전 설정 | `Qt.AA_ShareOpenGLContexts` (stom.py와 동일 시퀀스) |

`stom.py:15`에서 `QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)`을 `QApplication` 생성 전 호출한다. 본 감사도 동일 시퀀스를 따라야 `_build_v3_widgets`의 `QtWebEngineWidgets` 가드가 prod 경로에서처럼 통과한다.

## 3. 자동 검증 결과 매트릭스

| # | 항목 | 결과 | 신뢰도 | 증적 로그 |
|---|---|---|---|---|
| A1 | PyQt MainWindow 헤드리스 기동 | PASS | High | `a1_a2_with_aa_share.log`, `a1_a2_b1_combined.log` |
| A2 | guarded fallback 미발동 (AA_Share 사전 설정 시) | PASS | High | 위와 동일 |
| A3 | 9개 탭 위젯 `setCurrentIndex` 전환 | PASS | Medium | `a3_a5_b5_final.log` |
| A4 | 백테스트 프로세스 핸들 22개 + 큐 12개 + stgQs 1개 초기화 | PASS | High | `b7_a4.log`, `a4_b1_b5_b6.log` |
| A5 | 차트 도우미 객체 3개(DB/Real/Home) 인스턴스화 | PASS (객체) | Medium | `a3_a5_b5_final.log` |
| B1 | `AnalyzerRisk` 디폴트 `min_data=30` 적용 | PASS | High | `a1_a2_b1_combined.log` |
| B2 | 실시간 매매 경로(`trade/`)에 `prange` 사용 0건 | PASS | High | grep 결과 |
| B5 | 잔고 dt-guard 패턴 동작 (4 입력 → 2 unique dt → 2회 fire) | PASS | High | `a3_a5_b5_final.log` |
| B6 | `vt_analyzer.load_volatility_code_data` / `analyze_current_volatility` 일관 호출 | PASS | High | `a4_b1_b5_b6.log` |
| B7 | `AnalyzerMicrostructure(stock|coin)` 인스턴스화 + `_radar_history` 보유 | PASS | High | `b7_a4.log` |
| B8 | `ICON_PATH=./ui/_icon` + `strategy.png/strategy2.png` QPixmap 로드 (512x512) | PASS | High | `b8_icons.log` |
| C1·C2·C3 | LS/바이낸스/업비트 REST 모듈 import + 클래스 노출 | PASS (정적) | Medium | static check |
| D2 | 18개 거래소 ACCOUNT/TELE/STG/BACT 행 수 모두 18 | PASS | High | `d2_d3.log` |
| D3 | `database_check` API 노출 + 18개 BACT 자동 생성 | PASS | High | `d2_d3.log` |
| E1·E2 | 업스트림 `refs/tags/V3.0` 양방향 발산 보고 | PASS (보고만) | High | git fetch + log |

## 4. 항목별 상세

### 4.1 A1·A2 — MainWindow 기동과 fallback

* `Qt.AA_ShareOpenGLContexts` **사전 설정 필수**. 미설정 시 `_build_v3_widgets`의 `QtWebEngineWidgets` import에서 가드가 발동하며 V3U `ui/main_window.py` 358행 부근의 `try/except` fallback이 작동한다. 본 감사는 두 시나리오를 모두 재현했고, prod 경로(`stom.py`)는 사전 설정을 수행하므로 prod에서는 fallback 미발동임을 확인했다.
* `MainWindow.__init__` 후 `findChildren(QTabWidget)` 결과 3개 인스턴스 정상 생성.

### 4.2 A3 — 탭 전환

| Tab | 라벨 |
|---|---|
| 0 | 주식 라이브, 코인 라이브, 선물 라이브, 백테 라이브 |
| 1 | 일반설정, 주문설정 |
| 2 | 매수/매도전략, 최적화및GA범위, 백테스트스케쥴 |

총 9개 탭 모두 `setCurrentIndex(i)` 직후 `currentIndex()==i` 검증 PASS. 위젯 시각 표현 자체는 offscreen이므로 사용자 환경에서 별도 확인 필요.

### 4.3 A4 — 백테스트 프로세스/큐 초기화

* `_BACKTEST_PROCESS_ATTRS` 22개 모두 `None`으로 초기화 OK (spawn 직전 상태로 정상).
* 큐 12개 (`windowQ` 등) + `stgQs(1)` + `qlist(12)` 정상 생성. `multiprocessing.Queue` 생성 실패 시 `_NullQueue`로 안전 폴백 보장됨.

### 4.4 A5 — 차트 도우미 객체

`DrawDBChart`, `DrawRealChart`, `DrawHomeChart` 모두 인스턴스화 PASS. 단, `mw.canvas`는 `None` 상태 — 실제 차트 그리기는 사용자가 데이터를 로드해 호출한 시점에 트리거되므로 객체 준비는 OK이며 그리기 자체는 사용자 검증 필요.

### 4.5 B1 — 리스크분석 30개 임계값

`AnalyzerRisk.__init__(market_type, dict_findex, min_data: int = 30)` 디폴트 30 PASS. V3.18 변경 사항 그대로 반영.

### 4.6 B2 — 실시간 매매 prange 제거

`grep -rn "prange" trade/ ui/event_click/ ui/update_widget/` 결과 0건. `prange`는 `backtest/back_static_numba.py`, `strategy/analyzer_*.py` (numba JIT 가속용)에만 잔존하며 실시간 매매 경로엔 없음. CPU<90% 보장 조건 충족.

### 4.7 B5 — 잔고 변동시만 INSERT

`trade/base_receiver.py`에 `if pre_dt is None or dt > pre_dt:` 가드가 3곳 (line 237, 315, 503), `traderQ.put(('잔고갱신', ...))`이 dt 변동 시에만 발동. 4개 입력(2개 unique dt) 시뮬에서 정확히 2회만 이벤트 fire 검증 PASS.

### 4.8 B6 — 변손익분석 함수명 정합성

* 학습 데이터 로드: `self.vt_analyzer.load_volatility_code_data(code, date)` (`backtest/backengine_base.py:681`)
* 현재값 분석: `self.vt_analyzer.analyze_current_volatility(self.code, current_data)` (`backtest/backengine_base.py:813`)
* 다른 분석기 명명 컨벤션과 일관 (`load_*_code_*`, `analyze_current_*`).

### 4.9 B7 — 시장미시구조 더미 객체

`AnalyzerMicrostructure(market_type='stock'|'coin', dict_findex=...)` 양 케이스 인스턴스화 PASS. `_radar_history`, `_radar_axis_names`(8 지표), `_depth_weights` 모두 보유.

### 4.10 B8 — strategy 아이콘

* `ICON_PATH = './ui/_icon'` (`utility/settings/setting_base.py:7`)
* `strategy.png` 512x512 QPixmap 로드 PASS, isNull=False
* `strategy2.png` 512x512 QPixmap 로드 PASS, isNull=False
* `ui/create_widget/set_icon.py:23,24`에서 정확히 두 파일 참조.

### 4.11 C1·C2·C3 — REST API 정적 분석

| 모듈 | 라인 수 | 노출 클래스 |
|---|---|---|
| `trade/restapi_ls.py` | 773 | `LsRestAPI`, `LsRestData`, `LsWebSocketReceiver`, `LsWebSocketTrader` |
| `trade/restapi_binance.py` | 185 | `BinanceWebSocketReceiver`, `BinanceWebSocketTrader` |
| `trade/restapi_upbit.py` | 344 | `UpbitRestAPI`, `UpbitWebSocketReceiver`, `UpbitWebSocketTrader`, `get_symbols_info` |

3개 모듈 모두 import 성공. **실제 응답·체결·잔고 라이프사이클은 자격증명·시장시간 필요로 사용자 검증 영역이며 본 감사는 정적 노출 검증까지만 수행함.**

### 4.12 D2·D3 — 18개 거래소 + DB 자동 생성

| 데이터 | 행 수 |
|---|---|
| `ACCOUNT_DATA` | 18 |
| `TELE_DATA` | 18 |
| `STG_DATA` | 18 |
| `BACT_DATA` | 18 (index 1~18 unique) |

`database_check` 함수 노출 OK, 18개 거래소 컨텍스트 자동 생성 검증 완료. **사용자의 실 DB 마이그레이션 호환성은 사용자 백업 DB로만 검증 가능함.**

### 4.13 E1·E2 — 업스트림 V3.0 발산

`git fetch https://github.com/devstom/STOM.git refs/tags/V3.0:refs/remotes/devstom_tmp/tags/V3.0` 후 양방향 비교.

* **로컬 STOM_Version_3에는 없고 업스트림 V3.0 태그에만 있는 커밋**: 약 20개 (업비트 웹소켓 오류 수정 2건, DB PRIMARY KEY 도입, 라이선스/리드미 갱신 등)
* **로컬 STOM_Version_3에만 있고 업스트림 V3.0 태그에 없는 커밋**: 약 20개 (parkchanil 직접 추가 V3.01~V3.18 + dry-run 후보)

CLAUDE.md 정책상 V3는 V2.79 웨이브 제외 영역이므로 현재 시점 동기화 의무 없음. 향후 V3 wave 시작 시 reconcile 결정 필요.

## 5. 사용자 환경에서만 가능한 잔여 항목

| # | 항목 | 사유 |
|---|---|---|
| 시각 | 메인창/탭/위젯 레이아웃 시각 확인 | offscreen 렌더링은 사람 눈 판단 불가 |
| C1 | LS증권 모의투자 주문/체결/잔고 | 자격증명 + 영업시간 |
| C2 | 바이낸스 테스트넷 주문 라이프사이클 | 자격증명 |
| C3 | 업비트 실 최소금액 매수/매도 | 자격증명 + 실 자금 |
| C4 | base_strategy/base_trader 1시간 무인 운영 | 실시간 시장 + 자격증명 |
| B3 | LS 웹소켓 체결/호가 분리 라이브 수신 | 자격증명 + 라이브 |
| D1 | 사용자 실 DB로 V3U 첫 기동 | 사용자 DB 파일 필요 |
| F1 | `STOM_Version_3U_C` 생성 시점 결정 | 정책 판단 (선행 Directive로 차단 중) |

본 감사 후 잔여 위험은 위 8개 항목에 한정되며, 시각 확인 외 7개는 모두 사용자 자격증명/실데이터/정책 판단을 필요로 하므로 본질적으로 자동화 불가다.

## 6. 정책/안전 경계 준수

| 정책 | 상태 |
|---|---|
| V3 official source 미수정 (diff 8파일 한정) | 준수 |
| `_database/`, `_log/`, `*.db` 미추적 | 준수 |
| `STOM_Version_3U_C` 미생성 | 준수 |
| `backtest/graph/` 보호 경로 비침범 | 준수 |
| upstream V2 ingress 정책 비침범 | 준수 |
| 자격증명/실거래 API 호출 0건 | 준수 |
| 본 감사 산출물은 `docs/update_log/` + `.omx/logs/` 한정 | 준수 |

## 7. 다음 단계 제안

1. 사용자: `python stom.py` 1회 기동 + 9개 탭 시각 확인 (5분, A1·A2·A3 시각 PASS 확정)
2. 사용자: 백테스트 1회 + 차트 zoom/pan 시각 (15분, A4·A5·B6·B7 통합 시각 PASS 확정)
3. 1·2 시각 PASS 후 D1(사용자 백업 DB) 검토 (20분)
4. 4순위(C1~C4·B3) 모의·테스트넷 거래 검증 (1시간 이상, release 전)
5. 1·2 시각 PASS 후 `STOM_Version_3U_C` 생성 시점 결정 (F1)

## 8. 감사 메타

* Constraint: V3 official runtime source 변경 금지. 본 감사는 `docs/update_log/` 1개 + `.omx/logs/v3u/automation_2026_05_12/` 산출물만 추가.
* Constraint: 자격증명·실거래 API 호출 일체 금지.
* Constraint: `_database/`, `_log/`, `*.db`, `STOM_Version_3U_C` 변경 금지.
* Confidence: High (구조·계약·인스턴스화·단위 시뮬 영역). Medium (offscreen 차트·REST 정적 분석).
* Scope-risk: narrow (문서·로그 추가 한정).
* Directive: 본 문서 추가 후에도 `STOM_Version_3U_C` 생성은 사용자 시각 검증 통과 후로 보류 유지.
* Tested: 본 문서 3절 매트릭스 전 항목 헤드리스 PASS.
* Not-tested: 5절 8개 사용자 환경 항목.
