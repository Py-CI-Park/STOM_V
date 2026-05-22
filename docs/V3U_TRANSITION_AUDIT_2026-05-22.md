# V3U 중간 점검 종합 보고서 (3U_C 생성 전)

- 작성일: 2026-05-22
- 작성 시점: 사이클 6 종료 후, `STOM_Version_3U_C` 생성 결정 직전
- 대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-3u`
- 대상 branch: `STOM_Version_3U`
- HEAD: `e6362231 V3U 사이클 6 시각 검증 결과를 고정한다 — 결함 0건, A1·A2 가치 입증`
- Remote: `Py-CI-Park/STOM_V` (20 commits synced)
- 본 문서 목적: V3U lane의 정규 업데이트 반영 현황 + 미완 사항 + 다른 워크트리 영향 + 3U_C 진행 plan + 2U_C 컨셉 흡수 가능성을 종합 점검하고 다음 결정 시점을 명확히 한다.

---

## Executive Summary

V3U lane은 V3 official source 0줄 수정 invariant를 유지하며 18건 결함을 reactive·proactive로 모두 해소했고, 45개 자동 회귀 테스트 + 4단계 워크플로우 + 두 진실 원천 문서(INFERENCE_LESSONS·NEXT_STEPS) + attr inventory diff 자동 도구로 차후 V3.X 흡수 안전망을 완비했다. 사이클 6 시각 검증에서 결함 보고 0건을 달성해 A1·A2 사전 정찰 패턴의 가치가 정량 입증됐다.

**핵심 미완 사항 3가지**:
1. **A3·A4 자율 작업 미적용** (contract verifier UX 분리, 추가 worker 사전 정찰)
2. **3순위(D1 DB 마이그레이션) + 4순위(C1~C4·B3 실거래) 사용자 환경 검증 잔여**
3. **V3 upstream V3.0 reconcile 결정 (E1·E2)** — V2.79 웨이브 정책으로 보류 중

**다른 워크트리 영향**:
- V2(`STOM_V`), 2U(`wt-2u`): 영향 0 (별도 lane)
- 2U_C(`wt-dev`): V3K(V3 Kiwoom) 작업 진행 중 — V3U의 lessons·도구 패턴 흡수 가능
- V3(`wt-3`): V3 source 0줄 수정이라 영향 0, upstream V3.0 reconcile만 결정 필요

**3U_C 진행 가능성**: 1·2순위 시각 검증 완료로 선행 Directive 조건 충족. 2U_C가 검증한 컨셉(사이드카 승인, ralplan 합의 plan, T-step evidence, Phase 게이트)을 V3U 위에 V3.X-LS API lane용으로 흡수 가능.

---

## 1. V3U lane 현재 상태 종합 인벤토리

### 1.1 Branch / Remote 상태

```text
Branch: STOM_Version_3U
HEAD:   e6362231 V3U 사이클 6 시각 검증 결과를 고정한다 — 결함 0건, A1·A2 가치 입증
Remote: origin/STOM_Version_3U (sync: 20 commits 모두 push)
Base:   STOM_Version_3 @ 7faec937 STOM V3.18 (V3 official)
Diff:   35 파일 (V3 official 디렉토리 0줄, V3U 전용 추가)
```

### 1.2 커밋 매트릭스 (V3U 전용 누적 20건)

| 분류 | 커밋 수 | 핵심 |
|---|---|---|
| pyd-free 본체 도입 (사이클 0) | 5 | c04faec0~e01a96bf, ui/main_window.py 587줄 추론 + 감사 + 핸드오프 |
| 자동 검증 시스템 Phase 1~6 (사이클 1) | 6 | 1c794774~f7efe481, 31 pytest + verifier 통합 + 거버넌스 |
| 시각 검증 reactive 결함 fix (사이클 2~3) | 3 | 72308bca·b72f0162·25f61980, 결함 #1~9 |
| closeEvent + process_kill (사이클 3) | 1 | 383a2fbe, 결함 #10 |
| §5-1·§5-2 시스템화 (사이클 4) | 2 | 1116540a·0d6eb498, attr inventory diff + NEXT_STEPS 신규 |
| A1 사전 정찰 + reactive #13 (사이클 5) | 2 | c1554a36·9422b293, 결함 #11·#12·#13 |
| A2 CRITICAL 정리 (사이클 6) | 3 | 0eba2a71·d1014fe8·e6362231, 결함 #14a~e + baseline 0 + 사이클 6 결과 |
| **합계** | **20** | 결함 18건 fix + 자동 도구 1 + 거버넌스 5문서 |

### 1.3 산출 코드 인벤토리

```text
ui/main_window.py                              V3U pyd-free MainWindow 본체
  ├─ MainWindow 클래스 (앞 110줄)
  ├─ _init_queues (V3 컨벤션 12 명명큐 + qlist 13개 + 추가 3개)
  ├─ _init_runtime_state (state attrs + dbreader + lists)
  ├─ _load_user_settings
  ├─ _init_market_state
  ├─ _build_v3_widgets (V3 widget builder lazy import)
  ├─ _init_update_and_chart_helpers (UpdateCrawlingData/Telegram/Tablewidget/Textedit + DrawHomeChart alias)
  ├─ _init_timers (qtimer1·2·3 모두 자동 start)
  ├─ _init_workers (WebCrawling + TelegramBot + _NullProcess placeholders + signal connect)
  ├─ _NullWorker (QThread 호환 placeholder)
  ├─ _NullProcess (multiprocessing.Process 호환 placeholder)
  ├─ process_kill (timer + telegram + webc graceful cleanup)
  ├─ closeEvent (V3 close_event 위임)
  ├─ setting_serial_save / web_dashboard_log stub methods
  └─ 50+ V3 expected method wrapper (Qtimer1Start, ProcessStarter, etc.)

scripts/
  ├─ v3u_gui_contract_manifest.py        (사이클 0)
  ├─ v3u_smoke_offline_gui.py            (사이클 0)
  ├─ verify_v3u_pyd_gui_contract.py      (사이클 0 + Phase 5 pytest 게이트 통합)
  └─ v3u_attr_inventory_diff.py          (사이클 4, §5-1·§5-2 통합 도구)

tests/v3u/
  ├─ conftest.py                          (qapp/main_window/dict_findex_min/tick/synthetic_ohlcv + STOM_V3U_DISABLE_WEBC)
  ├─ fixtures/
  │   ├─ synthetic_ohlcv.py               (결정적 OHLCV 생성)
  │   ├─ dict_findex_v318.json            (V3.18 키 스냅샷)
  │   └─ mock_exchange.py                 (LS/Binance/Upbit mock 응답)
  ├─ test_smoke.py                        (smoke 5 + runtime state + qtimer + helper attr + signal + process_kill + telegram + webc)
  ├─ test_widgets.py                      (위젯 시그널·차트 helper·아이콘)
  ├─ test_lifecycle.py                    (백테 + 분석기)
  ├─ test_data_layer.py                   (잔고·18거래소·DB)
  ├─ test_units.py                        (AnalyzerRisk·prange·settings)
  ├─ test_rest_api_contract.py            (LS/Binance/Upbit 정적 + mock)
  └─ test_attr_inventory_drift.py         (CRITICAL=0 strict 회귀 차단)

requirements-dev.txt                       (pytest·pytest-qt·pytest-timeout·pytest-mock)
pytest.ini                                 (testpaths=tests/v3u, qt_api=pyqt5, 5 markers)
```

### 1.4 거버넌스 문서 (8문서)

| 문서 | 역할 | 상태 |
|---|---|---|
| `docs/V3U_PYD_REMOVAL_PLAN.md` | pyd 제거 계획 + §11 자동 검증 extension | 안정 (사이클 1 기준) |
| `docs/V3U_TEST_AUTOMATION_GUIDE.md` | 운영 매뉴얼 | 안정 (사이클 1 기준) |
| `docs/V3U_INFERENCE_LESSONS.md` | **과거 진실 원천** — 결함 #1~18 + §3 근본원인 + §5 재발방지 + §7 통계 | 매 사이클 §6/§7 갱신 (4단계 워크플로우) |
| `docs/V3U_NEXT_STEPS.md` | **미래 진실 원천** — 옵션 카탈로그 + 우선순위 + 선택 이력 | 매 사이클 §5 갱신 |
| `docs/WORKTREE_STRATEGY.md` | V2 + V3 Lane Branch Parity Invariants 양쪽 명문화 | 안정 (사이클 1) |
| `docs/UPSTREAM_SYNC_STRATEGY.md` | V2 + V3 Wave Source Of Truth + V3 Ingress Policy | 안정 (사이클 1) |
| `docs/CARRY_FORWARD_REGISTRY.md` | V2 + V3U custom allowlist rule + V3 lane carry-forward placeholder | 안정 (사이클 1) — **3U_C 항목은 미작성** |
| `CLAUDE.md` | V3U Test Automation Gate + 결함 발견·수정 4단계 워크플로우 + 사이클 종료 의무 | 안정 (사이클 1·5) |

### 1.5 통계 누적 (사이클 6 종료, 2026-05-21)

| 측정 | 값 |
|---|---|
| 총 결함 발견·수정 | 18 (사이클 1: 9, 사이클 3: 1, 사이클 5: 3, 사이클 6: 5) |
| 자동 회귀 테스트 케이스 | 45 |
| 신규 자동 도구 | 1 (`scripts/v3u_attr_inventory_diff.py`) |
| 사용자 시각 검증 사이클 | 6회 (사이클 6 결함 0건) |
| CRITICAL drift baseline | **0** (strict 모드) |
| V3 official source 수정 | **0줄** (invariant 유지) |
| 한글 커밋 (V3U lane) | 20건 |
| Remote sync | 20 commits push 완료 |

---

## 2. V3U lane에서 추가 업데이트할 항목 (자율 + 사용자)

### 2.1 자율 가능 (Claude 단독)

#### A3: contract verifier UX 분리 (30분, ROI medium)
**현재**: `verify_v3u_pyd_gui_contract.py`가 pytest gate를 subprocess로 호출하지만 출력 라인은 1개 (`pytest gate: passed/failed`).

**개선**:
- `attr_inventory_diff.py` 결과를 별도 단계로 분리 출력
- 각 단계 PASS/FAIL을 명시적으로 라인별로 표시
- V3 흡수 시 fail 단계 즉시 파악 가능

**산출**: `verify_v3u_pyd_gui_contract.py` 갱신, V3U_TEST_AUTOMATION_GUIDE.md §4 갱신.

#### A4: 추가 worker 사전 정찰 (30~60분, ROI low~medium)
**후보 worker**:
- `KimpWebSocketManager` (qlist 안 받음, codes 인자) — 김프 기능에서만 spawn
- `PyttsxSound` (소리 알림) — 사용자 소리 옵션 시
- `MonitorReceivQ`, `MonitorTraderQ` (trade/base_*) — 라이브 시작 시 base_receiver 자체가 시작
- `ui.web_dashboard` — `button_clicked_shortcut.py:253`에서 참조 (log_received signal 보유)

**평가**:
- 라이브 시작 / 김프 / 사운드 토글 / 웹대시보드 시작은 모두 사용자 액션 트리거. 부팅 시 spawn 불필요.
- 다만 `ui.web_dashboard.log_received.connect(ui.web_dashboard_log)` — `ui.web_dashboard` 인스턴스가 없으면 AttributeError. _NullWorker placeholder 부착 검토.

**산출**: `_init_workers`에 `web_dashboard` 안전 placeholder + 해당 회귀 테스트.

#### A5 (신규 후보): V3 upstream V3.0 reconcile 분석 (1~2시간)
**현재**: V3 lane 양방향 발산.
- 로컬 V3.09~V3.18 → 18개 (parkchanil)
- upstream V3.0 태그 → 20개 (업비트 웹소켓 수정 등)
- V2.79 웨이브 정책상 흡수 의무 없음

**분석 가능 작업**:
- 양방향 발산 commit별 영향 분류 (UI/거래/DB)
- V3.19 흡수 시 reconcile 시점 추천
- 보고서 산출: `docs/update_log/2026-05-22_v3_upstream_divergence_analysis.md`

**진행 여부**: 사용자가 V3 wave 시작 시점 결정 시까지 보류 가능.

#### A6 (신규 후보): attr_inventory_diff 도구 외부 적용 가능성 (1~2시간)
**현재**: V3U lane에만 적용.

**가능성**:
- 2U_C V3K lane에 동일 도구 이식 (V3K-specific attr inventory 측정)
- V2 lane은 pyd 보존이라 무관

**산출**: 2U_C 워크트리에 별도 도구 사본 또는 공유 모듈화.

### 2.2 사용자 환경 필수 (Claude 보조)

#### C1: 3순위 DB 마이그레이션 (D1) (20분 + 사용자 DB)
**조건**: 사용자가 백업 DB 파일 경로 제공.

**Claude 보조 가능**:
- dry-run 시뮬레이션 (실 DB 변경 없이 schema diff)
- `database_check.py` 결과 로그 수집
- migration 충돌 자동 감지

#### C2: 4순위 실거래 검증 (1시간+ + 사용자 자격증명)
**본질적 자동화 불가**:
- C1: LS 모의투자 주문 라이프사이클
- C2: 바이낸스 테스트넷
- C3: 업비트 실 최소금액
- C4: base_strategy 1시간 무인
- B3: LS 웹소켓 체결/호가 라이브

**release 전 사용자 본인 검증 필수.**

#### 2순위 잔여 (사이클 6에서 미확인)
**확인된 것**: 메인창 + 9탭 + 종료 라이프사이클.
**미확인**: 백테스트 1회 완주, 차트 zoom/pan, 변손익분석 옵션 ON 1 사이클.

**다음 시각 검증 사이클 권장 시나리오**:
1. 백테 라이브 탭 → 시작 버튼 클릭 → 엔진 spawn → 합성 데이터 1 사이클 완주
2. 실시간 차트 또는 백테 차트에서 zoom/pan
3. 백테 설정에서 변손익분석 옵션 ON → 백테 시작 → 완주 후 결과 확인

### 2.3 정책 판단 (사용자만)

| 항목 | 현재 상태 | 결정 필요 시점 |
|---|---|---|
| D1: `STOM_Version_3U_C` 생성 | 선행 Directive(`4aef1cce`)로 보류, 1·2순위 PASS로 조건 충족 | **지금 결정 가능** |
| D2: V3 upstream V3.0 reconcile | V2.79 웨이브 정책상 의무 없음 | V3 wave 시작 시 |
| D3: V3.19 흡수 시점 | V3 upstream 새 버전 미발표 | upstream 발표 시 |

---

## 3. V3U lane에서 놓친 부분 (잠재 미완)

### 3.1 명백한 미완 (이미 §2에 명시)
- A3·A4 자율 작업
- 2순위 백테/차트/변손익분석 시각 검증
- 3·4순위 사용자 환경 검증
- V3 upstream reconcile

### 3.2 알려지지 않은 잠재 결함 (위험 평가)

#### 카테고리 B 잔여 위험 (worker 누락)
**검증된 안전**:
- WebCrawling: 시작 + signal connect + cleanup OK
- TelegramBot: 시작 + cleanup OK
- proc_chqs/proc_tele: _NullProcess placeholder
- 백테 26개 process attr: None으로 정상 초기화

**잠재 위험**:
- `ui.web_dashboard` 인스턴스 부재 — `button_clicked_shortcut.py:253`에서 사용자 단축키 입력 시 AttributeError 가능
- `ui.proc_receiver`, `ui.proc_trader`, `ui.proc_strategys`, `ui.proc_coin_kimp` — `process_alive.py`에서 `is not None and is_alive()` 패턴이라 안전. 단 다른 site에서 None 체크 없는지 추가 grep 필요.

**조치**: A4 진행 시 함께 정리.

#### 카테고리 C 잔여 위험 (signal connect 누락)
**검증된 안전**:
- WebCrawling.signal → update_crawling_data

**미검증**:
- TelegramBot은 pyqtSignal 없음 → connect 불필요
- KimpWebSocketManager.signal1·signal2 — 사용자 김프 기능 활성 시 base_receiver가 connect
- base_receiver.signal1·2, base_trader.signal1~4 — 라이브 시작 시 user code에서 connect

**조치**: 라이브 시작·김프 활성 시점에 별도 사이클로 검증.

#### 카테고리 D 잔여 위험 (helper 이름 mismatch)
**검증된 안전**: attr inventory diff CRITICAL = 0.

**도구 한계**:
- `attr_inventory_diff`가 잡지 못하는 케이스:
  - 외부 코드에서 `getattr(ui, X, default)` 동적 access
  - `ui.X[N]` 인덱스 access (list/dict이 비어있어 IndexError/KeyError)
  - 메서드 시그니처 차이 (attr 존재해도 인자 mismatch)

**조치**: 사용자 시각 검증으로만 발견 가능. 4단계 워크플로우 reactive 적용.

### 3.3 자동 검증 시스템 자체 미완

#### A) 시각 회귀 감지 부재
**현재**: 위젯 깨짐을 자동으로 못 잡음 (offscreen 픽셀 비교 없음).
**개선**: 옵션 D — Pillow + imagehash 기반 스크린샷 회귀. 별도 ralplan으로 분리됨.

#### B) Multi-version V3 호환 검증 부재
**현재**: V3.18 fixture만 동결.
**위험**: V3.19 흡수 시 dict_findex 키 추가/삭제 가능 → 합성 데이터 schema drift.
**개선**: `dict_findex_v318.json`에 schema validation 추가, V3 upstream 흡수 시 자동 diff.

#### C) AI 자동 시나리오 생성 부재
**현재**: 회귀 테스트는 사람이 작성.
**개선**: 옵션 E — `ui/event_click/` 자동 분석 후 시나리오 자동 생성. 별도 ralplan.

#### D) CI 통합 부재
**현재**: 로컬 pytest 수동 실행.
**개선**: GitHub Actions 또는 pre-commit hook. 별도 ralplan.

---

## 4. 다른 워크트리 영향 매트릭스

### 4.1 워크트리 7개 상태 (2026-05-22 시점)

| Worktree | Branch | HEAD | 역할 | V3U fix 영향 |
|---|---|---|---|---|
| `STOM_V/` | STOM_Version_2 | `adfe80c7 V3K safe-staged 설계 기준` | V2 release-ingress | ❌ 없음 (별도 lane) |
| `wt-2u/` | STOM_Version_2U | `3b7a3aeb 파이썬 3.13 기준 2U pyd-free 긴급 정렬` | V2 pyd-free 추론 | ❌ 없음 (다른 pyd 대상) |
| `wt-3/` | STOM_Version_3 | `7faec937 STOM V3.18` | V3 release-ingress (보관) | ❌ 없음 (V3U는 V3 source 0줄 수정) |
| `wt-3u/` | STOM_Version_3U | `e6362231 V3U 사이클 6` (HEAD) | V3 pyd-free 추론 (활성) | ✅ 본 보고서 대상 |
| `wt-dev/` | STOM_Version_2U_C | `6e8e23d0 F1 DB cutover ralplan plan v1` | V3K 진행 중 (활성 custom) | ⚠️ 패턴 흡수 가능 (§5 참조) |

### 4.2 V3U lane 변경의 다른 워크트리 영향

#### V2 (`STOM_V`) - **영향 0**
- V3U는 V3에서 분기, V2 lane과 완전 격리
- V2 ingress 정책 위반 가능성 없음
- V2.79 wave 진행에 영향 없음

#### 2U (`wt-2u`) - **영향 0**
- V2 pyd → V2 추론 lane, V3U와 다른 pyd 대상
- 2U는 `ui/ui_mainwindow.py` (V2 `ui_mainwindow.pyd` 추론)
- V3U는 `ui/main_window.py` (V3 `main_window.pyd` 추론)
- **단**: V3U의 lessons(4단계 워크플로우, attr inventory diff 도구)는 2U에도 적용 가능. 별도 결정 필요.

#### 2U_C (`wt-dev`) - **패턴 흡수 가능, 코드 영향 0**
- 2U_C는 V3K (V3 → V2 Kiwoom 호환) 진행 중. V3U(V3 LS API pyd-free)와 다른 목적.
- V3U 자산 중 2U_C에서도 유용한 것:
  - 4단계 워크플로우 (이미 2U_C도 ralplan + audit JSON 패턴 사용 중)
  - attr inventory diff 도구 (V3K-specific attr inventory 측정에 이식 가능)
  - _NullWorker / _NullProcess placeholder 패턴
  - process_kill cleanup 패턴
- 반대로 2U_C가 V3U에 줄 수 있는 패턴은 §5에서 상세.

#### V3 (`wt-3`) - **영향 0, 단 reconcile 결정 필요**
- V3U는 V3 source 0줄 수정이라 코드 영향 없음
- V3 lane은 `7faec937 STOM V3.18` 상태로 동결
- V3 upstream `refs/tags/V3.0` 양방향 발산:
  - 로컬 V3.09~V3.18 (parkchanil 추가, 18개)
  - upstream V3.0 (~20 commits 미흡수: 업비트 웹소켓·DB PK·README 등)
- V3 wave 시작 시 reconcile 결정 필요 (V2.79 정책상 현재 의무 없음)

### 4.3 V3U 자산을 다른 워크트리에 반영하는 방법

#### 패턴 이식 우선순위

| 패턴 | 2U 이식 | 2U_C 이식 | V3 이식 |
|---|---|---|---|
| 4단계 워크플로우 + INFERENCE_LESSONS.md | ✅ 권장 | 🟢 이미 적용 중 | N/A |
| attr inventory diff 도구 | 🟡 ROI 낮음 (pyd 보존됨) | ✅ 권장 (V3K-specific) | N/A |
| NEXT_STEPS.md decision tree | ✅ 권장 | 🟢 이미 적용 중 (plans/) | N/A |
| _NullWorker/_NullProcess placeholder | 🟡 이미 fallback 있음 | ✅ 권장 | N/A |
| pytest-qt 자동 검증 시스템 | ✅ 권장 (2U 안정성↑) | ✅ 권장 (V3K Phase 검증) | N/A |
| process_kill cleanup 패턴 | 🟢 2U는 ui_process_kill.py 보유 | ✅ 권장 | N/A |

**가장 ROI 높은 이식 후보**:
- **2U_C에 attr inventory diff 이식** — V3K가 V3 함수를 V2 Kiwoom 호환으로 흡수하는 과정에서 attr 누락 감지 가능
- **2U에 4단계 워크플로우 + LESSONS.md 패턴 이식** — 2U도 pyd 추론 lane이라 같은 결함 패턴 가능

---

## 5. 3U_C 진행 plan

### 5.1 사전 조건 (모두 충족)

| 조건 | 상태 |
|---|---|
| 1순위 시각 검증 PASS | ✅ 사이클 6 |
| 2순위 시각 검증 PASS (기본) | ✅ 메인창·탭·종료 |
| V3U lane 안전망 완비 | ✅ 45 pytest + baseline 0 strict |
| V3 source 0줄 수정 invariant | ✅ 35 diff 모두 V3U 전용 경로 |
| 거버넌스 문서 5개 정합성 | ✅ cross-link 일관 |
| `STOM_Version_3U_C` 미생성 (Directive) | ✅ 유지 중 |

### 5.2 3U_C 생성 단계

#### Phase A: 거버넌스 사전 작업 (10분)
1. `docs/CARRY_FORWARD_REGISTRY.md`에 "V3U_C custom allowlist rule" 섹션 추가
   - V3U-extension인지 V3U_C-specific인지 명확히 구분
   - 허용 차이 카테고리 명시 (custom 기능별 그룹화)
2. `docs/WORKTREE_STRATEGY.md`에 "V3 Lane Branch Parity Invariants" 확장
   - V3 ← V3U ← V3U_C 3단계 verification order 명시
3. `docs/V3U_NEXT_STEPS.md` §3에 새 옵션 그룹 E (V3U_C 작업) 추가

#### Phase B: branch + worktree 생성 (5분)
```powershell
# 1. V3U HEAD에서 branch 생성
git checkout STOM_Version_3U
git checkout -b STOM_Version_3U_C

# 2. 신규 worktree 생성 (관행: wt-3uc 또는 wt-dev-3uc)
git worktree add C:/System_Trading/STOM/STOM_V.wt-3uc STOM_Version_3U_C
```

#### Phase C: 첫 custom 작업 사이클 (사용자 결정)
- 어떤 custom 기능을 가장 먼저 추가할지 결정
- 2U_C 컨셉(§6) 중 일부 또는 V3 official에 없는 신규 기능

### 5.3 3U_C 운영 모델

**진실 원천 추가**:
- `docs/V3U_C_NEXT_STEPS.md` 신규 (3U_C 전용 decision tree)
- `docs/V3U_C_INFERENCE_LESSONS.md` 신규 (3U_C 결함 기록) 또는 기존 V3U lessons 공유

**4단계 워크플로우**: 동일 적용 (발견 → V3U_C 전용 파일 수정 → 회귀 테스트 → docs 갱신)

**Verification Order**:
1. `3U vs 3`: pyd 제거 + V3U 전용 도구·테스트만 차이 (현재 안전망)
2. `3U_C vs 3U`: V3U_C custom 차이가 carry-forward registry에 모두 등록되어야 함

**검증 게이트**:
- 3U에서 만든 `verify_v3u_pyd_gui_contract.py`를 3U_C에서도 호출 (pytest 게이트 자동 포함)
- 3U_C-specific 회귀는 별도 `tests/v3uc/` 디렉토리 분리 검토

---

## 6. 2U_C 컨셉의 3U_C 흡수 가능성

### 6.1 2U_C가 검증한 컨셉 인벤토리

2U_C는 V3K(V3 → V2 키움 호환) 작업을 통해 다음 컨셉을 검증한 상태:

| 컨셉 | 2U_C 적용 위치 | V3U_C 흡수 가능성 |
|---|---|---|
| **ralplan 합의 plan 정본화** | `F1 DB cutover plan Planner v1`, `Phase H plan §K.5 amend` | ✅ V3U도 이미 ralplan 사용 — 동일 패턴 적용 |
| **Phase A~H 단계별 게이트** | V3K Phase A→B→...→H, gate audit | ✅ 3U_C custom 기능 도입 시 Phase 게이트 적용 가능 |
| **T-step (T01, T02, ...) evidence 정본화** | T01+T02 sentinel hook, T03 audit JSON schema v2, T04 host hash trail, T05 runner, T06 health smoke | ✅ 3U_C custom 기능을 T-step 단위로 분해 가능 |
| **사이드카 승인 패턴** | "Phase F/G 승인 게이트를 사이드카 설정으로 실행" | ✅ 3U_C에서 위험 작업(예: 거래 라이브 진입) 사이드카 승인 적용 |
| **audit JSON schema v2 (primary/corroborating signal 분리)** | T03 audit schema v2 | ✅ 3U_C audit에 동일 schema 적용 — primary는 자동 검증, corroborating은 시각 검증 |
| **중간 점검 v4 정본화** | `V3K 중간 점검 v4 (110 commit, 50% 마일스톤)` | ✅ 본 보고서 자체가 V3U 중간 점검 v1로 정착 — 3U_C에도 동일 운영 |
| **CARRY_FORWARD_REGISTRY 적극 활용** | V3K-specific carry-forward 항목 누적 | ✅ V3U_C custom allowlist rule + 차후 carry-forward 항목 |
| **STOM_CLI_AI_AUTOMATION_PLAN.md 패턴** | CLI AI automation의 plan 정본화 | 🟡 V3U_C가 어떤 custom 기능 도입하느냐에 따라 |

### 6.2 흡수 시 주의사항 (V3U와 2U_C lane 차이)

| 측면 | V3U lane | 2U_C (V3K) lane |
|---|---|---|
| 상위 lane | V3 (LS API) | V2 (Kiwoom) |
| 목적 | pyd-free 추론 + 안정 | V3 기능을 V2 호환 흡수 (역방향) |
| 워크 단위 | 결함 fix 사이클 | V3K Phase A~H 게이트 |
| 검증 방식 | pytest 자동 + 시각 reactive | 사이드카 승인 + mock execution + host hash trail |
| 코드 base | V3 source 0줄 수정 | 대규모 utility/* custom (1202 files) |

**3U_C는 V3U처럼 "기능 안정성"보다 "custom 기능 추가" 목적이라 2U_C 컨셉이 더 가까움.**

### 6.3 3U_C 첫 custom 작업 후보 (2U_C 패턴 적용)

#### 후보 X1: V3.X 흡수 자동화 파이프라인
- 2U_C T-step 패턴으로 V3.19 흡수 단계 분해 (T01: branch merge → T02: verifier 통과 → T03: audit 정본화 → T04: 한글 commit → T05: push)
- 각 T-step은 mock execution 후 live dry-run

#### 후보 X2: STOM_CLI 자동화 + V3U 통합
- 2U_C `STOM_CLI_AI_AUTOMATION_PLAN.md` 패턴 참고
- V3U_C에 CLI 단축키 + 자동화 시나리오 추가

#### 후보 X3: 실시간 모니터링 dashboard
- `ui.web_dashboard` 인스턴스 적극 활용
- 별도 worker로 자체 web dashboard server 운영
- 2U_C 사이드카 패턴 적용 (위험 작업 게이트)

#### 후보 X4: 고급 백테 자동화
- 2U_C V3K mapping 지도 참고
- V3U_C에 백테 결과 자동 분석 + GA + Optuna 자동 ranking

**선택은 사용자 우선순위에 따라.** 본 보고서는 옵션 매트릭스만 제시.

---

## 7. 권장 다음 단계 (우선순위)

| 우선순위 | 단계 | 주체 | 시간 |
|---|---|---|---|
| 🟢 1 | A3 + A4 자율 작업 완료 (verifier UX 분리 + web_dashboard placeholder) | Claude | 1시간 |
| 🟡 2 | 2순위 잔여 시각 검증 (백테 1회·차트·변손익분석) | 사용자 | 30분 |
| 🔵 3 | C1 DB 마이그레이션 검증 (백업 DB 경로 제공 시) | 사용자 + Claude | 20분 |
| 🟠 4 | **3U_C 생성** Phase A (거버넌스 사전 작업) + Phase B (branch + worktree) | Claude (게이트 후 사용자 승인) | 15분 |
| ⚪ 5 | 3U_C 첫 custom 작업 사이클 (X1~X4 중 선택) | 사용자 결정 → Claude 진행 | 가변 |
| 🟢 6 | (옵션) 2U_C에 attr inventory diff 이식 | Claude | 1시간 |
| 🔵 7 | (release 전) C2 모의/테스트넷 실거래 | 사용자 | 1시간+ |
| ⚪ 8 | (V3 wave 시작 시) E1·E2 V3 upstream V3.0 reconcile | 사용자 결정 | 별도 사이클 |

---

## 8. 위험 분석

### 8.1 3U_C 생성 시 즉시 위험

| 위험 | 확률 | 영향 | 완화 |
|---|---|---|---|
| 3U_C 작업이 V3U 결함을 노출 | medium | medium | 매번 verify_v3u_pyd_gui_contract.py 통합 게이트 실행 |
| 거버넌스 문서 누락으로 차후 작업자 혼란 | low | high | Phase A에서 거버넌스 사전 작업 필수 |
| custom 기능이 V3 official 위배 | low | high | V3U의 0줄 수정 invariant를 3U_C에도 강제 |
| 2U_C 패턴 잘못 흡수 | medium | low | 본 보고서 §6.2 차이점 명시 |

### 8.2 V3U lane 잔여 위험

| 위험 | 확률 | 완화 |
|---|---|---|
| 사용자 실거래 시 추가 결함 (C1~C4·B3) | medium | release 전 사용자 본인 검증 + 4단계 워크플로우 reactive |
| V3.19 흡수 시 attr inventory drift | medium | strict baseline 0이 즉시 fail 알림 |
| V3.19에서 dict_findex schema 변경 | medium | dict_findex_v318.json + factor_lists 라이브 비교 |
| webc 종료 OSError가 다른 Worker로 확산 | low | _safe_webc_run_wrapper 패턴 적용 검토 |

### 8.3 다른 워크트리 위험

| 위험 | 확률 | 완화 |
|---|---|---|
| V2 wave가 V3U에 영향 | low | 별도 lane이라 영향 0 |
| 2U_C V3K 작업이 V3U와 충돌 | low | 별도 worktree, branch 격리 |
| V3 upstream V3.0 reconcile이 V3U 깨뜨림 | medium | reconcile 사이클 별도, 자동 게이트 통과 후 흡수 |

---

## 9. 핵심 결론

1. **V3U lane은 정규 업데이트 흡수 게이트 + 결함 사이클 운영 모델이 안정화됨**. 18건 결함 누적 fix + 45 pytest + 자동 도구 1 + 거버넌스 5문서 + 4단계 워크플로우 정착.
2. **사이클 6 시각 검증 결함 0건은 A1·A2 사전 정찰 패턴의 정량 입증**. 다음 V3.X 흡수도 동일 패턴으로 사용자 부담 최소.
3. **다른 워크트리(V2·2U·V3)에 V3U 코드 영향 0**. 패턴(4단계 워크플로우, attr inventory diff)은 흡수 가치 있음.
4. **2U_C는 V3K로 발전 중**이며 그 컨셉(ralplan, Phase 게이트, T-step, audit JSON v2, 사이드카 승인)이 3U_C에 흡수 가능. 단 lane 목적 차이 주의.
5. **3U_C 생성 사전 조건 모두 충족**. Phase A 거버넌스 사전 작업 → Phase B branch 생성 → Phase C 첫 custom 작업 사이클로 진입 가능.
6. **A3·A4 자율 작업은 3U_C 생성 전·후 어느 시점이든 가능**. 본 보고서 §7 우선순위 1번 권장.

---

## 10. 부록

### 10.1 commit hash 누적 (V3U lane 20건, 2026-05-12~21)

```text
사이클 0 (pyd-free 본체, 사이클 1 이전 작업 일부 포함):
c04faec0 V3U pyd 제거 경계를 먼저 고정한다
d05c132c V3U pyd 대체 검증 발판을 먼저 세운다
3d8f9c1e V3U pyd 제거를 실제 코드 경계로 전환한다
4aef1cce V3U 최종 parity 감사 증적을 고정한다
4a4d989c V3U 인수인계 검증 체크리스트와 직접 개발 검토를 고정한다
e01a96bf V3U 확장 자동 검증 감사 증적을 고정한다

사이클 1 (자동 검증 시스템 Phase 1~6):
1c794774 V3U 자동 GUI 검증 골격을 도입한다
96787192 V3U 1순위 사용자 검증을 스모크 테스트로 자동화한다
4059ce36 V3U 2·3순위 사용자 검증을 통합 테스트로 자동화한다
fc1870fe V3U 분석기 단위 테스트와 REST API mock 계약 검증을 추가한다
b43fef6e V3U pyd contract verifier에 pytest 게이트를 통합한다
096cc1a7 V3 lane 거버넌스 규칙을 워크트리 전략 문서에 명문화한다
f7efe481 V3U 자동 검증 시스템 도입 감사와 운영 가이드를 고정한다

사이클 2 (시각 검증 reactive 결함 fix):
72308bca V3U MainWindow 누락 runtime state와 자동 타이머·콘솔 로깅을 보강한다
b72f0162 V3U 큐 컨벤션을 V3 worker 기대치로 정렬하고 WebCrawling worker를 시작한다
25f61980 V3U 홈 대시보드 데이터 핸들러를 V3 컨벤션에 맞게 결선한다

사이클 3 (#10 closeEvent + process_kill):
383a2fbe V3U closeEvent와 process_kill을 추가해 종료 시 worker cleanup을 보장한다

사이클 4 (§5-1·§5-2 시스템화 + NEXT_STEPS):
1116540a V3U attr inventory 3-way diff 자동 도구로 §5-1·§5-2 액션을 적용한다
0d6eb498 V3U next-steps decision tree 진실 원천을 만들고 사이클 종료 의무를 명문화한다

사이클 5 (A1 사전 정찰 + #13):
c1554a36 V3U A1 사전 정찰로 telegram·proc_chqs placeholder 결함 2건을 사전 차단한다
9422b293 V3U WebCrawling 종료 OSError를 안전 wrapper로 swallow한다

사이클 6 (A2 CRITICAL 0 + 시각 검증 결과):
0eba2a71 V3U A2로 CRITICAL drift 67을 0으로 정리하고 strict baseline을 적용한다
d1014fe8 V3U NEXT_STEPS 사이클 6 기록을 추가한다 (직전 commit에서 누락분 보완)
e6362231 V3U 사이클 6 시각 검증 결과를 고정한다 — 결함 0건, A1·A2 가치 입증
```

### 10.2 cross-link 문서 그래프

```text
CLAUDE.md (운영 규칙)
  ├─ V3U Test Automation Gate
  ├─ 결함 발견·수정 4단계 워크플로우 → V3U_INFERENCE_LESSONS.md §8.1
  └─ 사이클 종료 시 NEXT_STEPS 갱신 의무 → V3U_NEXT_STEPS.md

V3U_INFERENCE_LESSONS.md (과거 진실 원천)
  ├─ §6 결함 기록 (#1~18 + 사이클 6 결과)
  ├─ §7 통계 누적
  └─ §9 관련 문서 → V3U_NEXT_STEPS.md, V3U_PYD_REMOVAL_PLAN.md

V3U_NEXT_STEPS.md (미래 진실 원천)
  ├─ §3 옵션 카탈로그 A/B/C/D
  ├─ §5 선택 이력 (사이클 1~6-2)
  └─ §7 관련 문서 → V3U_INFERENCE_LESSONS.md

V3U_PYD_REMOVAL_PLAN.md (계획)
  └─ §11 자동 검증 시스템 extension

V3U_TEST_AUTOMATION_GUIDE.md (운영 매뉴얼)
  └─ §8 관련 문서 → V3U_INFERENCE_LESSONS.md (최우선 참조)

WORKTREE_STRATEGY.md (V2 + V3 lane parity)
UPSTREAM_SYNC_STRATEGY.md (V2 + V3 ingress)
CARRY_FORWARD_REGISTRY.md (V2_C + V3U custom allowlist)

V3U_TRANSITION_AUDIT_2026-05-22.md (본 문서)
  └─ 3U_C 생성 전 종합 점검
```

### 10.3 sync 가능한 자산 인벤토리 (다른 lane 이식 후보)

| 자산 | 경로 | 이식 후보 lane |
|---|---|---|
| `_NullWorker` / `_NullProcess` 클래스 | ui/main_window.py:65-117 | 2U_C 신규 worker 추가 시 |
| `_safe_webc_run_wrapper` 패턴 | ui/main_window.py:486-495 | 2U_C QThread worker cleanup |
| `attr_inventory_diff.py` 도구 | scripts/v3u_attr_inventory_diff.py | 2U_C (V3K-specific inventory), 2U |
| 4단계 워크플로우 | CLAUDE.md "결함 발견·수정 4단계" | 2U_C, 2U |
| LESSONS/NEXT_STEPS 진실 원천 패턴 | docs/V3U_INFERENCE_LESSONS.md, docs/V3U_NEXT_STEPS.md | 2U_C (이미 적용 중인 V3K_PLAN 패턴과 결합), 2U |
| pytest-qt 자동 검증 인프라 | tests/v3u/, conftest.py, pytest.ini | 2U_C (V3K-specific tests), 2U |

---

## 11. 본 보고서 갱신 의무

본 보고서는 V3U lane의 **중간 점검 v1**이다. 다음 시점에 갱신:
1. 3U_C 생성 직후 (Phase A·B 완료)
2. A3·A4 자율 작업 완료 시
3. V3.X 흡수 사이클 종료 시
4. C1·C2 사용자 검증 결과 받은 후
5. 6개월 이상 지속될 lane이라면 분기별 1회

각 갱신 시 §1.5 통계, §7 우선순위 매트릭스, §10.1 commit 누적을 함께 갱신.
