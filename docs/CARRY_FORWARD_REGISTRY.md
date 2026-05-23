# Carry Forward Registry

## Purpose
Tracks known issues that were intentionally not fixed in the current official update cycle.

## Current V2.79 scope note
The active V2.79 official propagation chain is `V2 -> 2U -> 2U_C`.
Entries below that name `CLI_v267` or `research/init` are historical carry-forward records from the closed V2.74~V2.77 cycle. They are not active V2.79 propagation targets unless a separate migration or corrective-fix cycle explicitly reopens them.

## 2U_C custom allowlist rule
`STOM_Version_2U_C` is the custom update lane derived from `STOM_Version_2U`.
Custom edits are allowed in 2U_C, but any runtime difference from 2U must be recorded as an intentional 2U_C custom item in this registry or the active `docs/update_log/` status document.

This rule does not loosen the 2U rule: `STOM_Version_2U` remains the pyd-to-py inference lane and should differ from `STOM_Version_2` only by pyd-to-py inference outputs and related verification scaffolding.

## Decision schema
- Deferred because: the current wave did not touch the surface directly, or the known issue did not block official intake propagation in this cycle.
- Reclassify when: a future wave changes the surface directly, the failure reproduces during blocker audit, or the affected branch becomes the active corrective-fix target.

## Release-side upstream risks
- V2.74: empty-result MDD bootstrap failure risk
  - Deferred because: the issue was recorded as an upstream risk and was not reopened by the V2.74~V2.77 downstream propagation wave.
  - Reclassify when: a future intake or corrective fix touches MDD bootstrap behavior or reproduces the empty-result path.
- V2.74: plotting-before-persistence robustness risk
  - Deferred because: the wave did not require a plotting pipeline rewrite and the risk remained unchanged from release intake.
  - Reclassify when: plotting order, persistence sequencing, or related guard handling is touched in a future wave.
- V2.75: strategy version parsing with spaces / empty compare selection
  - Deferred because: downstream propagation did not directly modify strategy version parsing or compare-selection logic.
  - Reclassify when: version parsing, compare-selection UX, or input normalization changes in a later cycle.
- V2.75: duplicate scrollbar signal connections
  - Deferred because: the known connection-management risk stayed outside the branches touched for this wave.
  - Reclassify when: scrollbar wiring, signal lifecycle handling, or the affected UI surface is edited again.
- V2.75: lexical version ordering
  - Deferred because: no version-ordering correction was required to complete this intake wave.
  - Reclassify when: version sorting logic, compare lists, or release-selection ordering is changed.
- V2.76: sparse-parameter heatmap crash risk
  - Deferred because: the heatmap path was not the active blocker for the official wave and remained an isolated risk item.
  - Reclassify when: sparse-parameter visualization logic is touched or the crash reproduces during blocker audit.
- V2.76: cubic interpolation crash risk
  - Deferred because: interpolation behavior was not part of the branch-local corrective fixes required for this cycle.
  - Reclassify when: interpolation mode handling, heatmap rendering, or numeric-grid assumptions are changed.
- V2.77: stock strategy example-button wiring issue
  - Deferred because: the example-button path did not block propagation and was left for a dedicated follow-up cycle.
  - Reclassify when: stock strategy UI wiring, example-button handlers, or the surrounding dialog flow is modified.

## Downstream carry-forward tests
- CLI_v267: `tests/unit/test_backtest_result_expansion.py::test_total_report_writes_extended_detail_csv_and_db`
  - Deferred because: protected result data existed on the branch and the current wave prioritized keeping the downstream baseline stable.
  - Reclassify when: backtest-result expansion code is touched again or the branch enters a dedicated result-persistence follow-up cycle.
- research/init: `tests/unit/test_backtest_result_expansion.py::test_total_report_writes_extended_detail_csv_and_db`
  - Deferred because: the branch remained downstream of the official wave and this failure was not required to close the intake cycle.
  - Reclassify when: research/init changes backtest-result expansion or a later wave selects this test surface for correction.
- research/init: `tests/unit/test_exit_codes.py::TestExitCodes::test_execution_error_returns_two`
  - Deferred because: exit-code alignment was not the active branch-local fix target for the current official cycle.
  - Reclassify when: execution error handling, CLI exit semantics, or test-expectation policy changes on research/init.

## Rule
- If a future wave touches one of these surfaces directly, reclassify it through blocker audit before continuing.

## V3U custom allowlist rule

`STOM_Version_3U`는 `STOM_Version_3`(V3 official 보존 lane)에서 분기된 pyd-to-py 추론 lane이다. V2 lane의 `2U custom allowlist rule`과 동일 패턴으로 다음 차이만 허용한다.

### 허용되는 V3U 전용 차이

- `ui/main_window.py` — pyd(`ui/main_window.pyd`) 제거 후 Python 대체 본체 (V3U 전용)
- `ui/main_window.pyd` — V3U에서 삭제 (V3는 보존)
- `scripts/v3u_gui_contract_manifest.py` — V3U GUI contract inventory 도구
- `scripts/v3u_smoke_offline_gui.py` — pyd-free 구조 smoke 도구
- `scripts/verify_v3u_pyd_gui_contract.py` — pyd-free contract verifier (Phase 5에서 pytest 게이트 통합)
- `tests/v3u/**` — pytest-qt 기반 자동 GUI 검증 시스템 (Phase 1~4)
- `requirements-dev.txt` — V3U 전용 dev 의존성 (pytest, pytest-qt 등)
- `pytest.ini` — V3U 전용 pytest 설정
- `tests/__init__.py`, `tests/v3u/__init__.py`, `tests/v3u/fixtures/__init__.py` — 패키지화
- `docs/V3U_*.md` 및 `docs/update_log/*v3u*.md` — V3U 계획·감사·핸드오프·자동화 가이드

### 금지되는 차이

- V3 official runtime source 디렉토리(`backtest/`, `strategy/`, `trade/`, `utility/`, `stom.py`, `ui/create_widget/`, `ui/update_widget/`, `ui/draw_chart/`, `ui/event_click/`, `ui/etcetera/`) 0줄 수정 invariant 위반.
- V3U 전용 차이가 위 허용 목록에 없는 경로에 추가되는 경우.
- V3 lane upstream `.pyd` 보존 위반 (`STOM_Version_3`에는 `ui/main_window.pyd`가 항상 존재해야 함).

### 자동 검증 게이트

`scripts/verify_v3u_pyd_gui_contract.py`(Phase 5 통합 후)가 위 invariants를 매 V3 흡수 시 자동 검증한다. 위반 시 `ui/main_window.py` 또는 `tests/v3u/`에서만 수정한다.

## V3 lane carry-forward placeholder

본 문서 작성 시점에 V3 lane 활성 carry-forward 항목은 없다. V3 wave가 시작되면 다음 카테고리로 항목을 추가한다.

- V3 release-side upstream risks (V3.X 흡수 시 발견된 미해결 risk)
- V3U pyd 추론 carry-forward (3U vs 3 verification에서 deferred 항목)
- V3U_C custom carry-forward (3U_C 사이클 진행 중 누적)

각 항목은 V2 패턴과 동일하게 `Deferred because:` / `Reclassify when:` 두 줄로 명시한다.

## V3U_C custom allowlist rule

`STOM_Version_3U_C`는 `STOM_Version_3U`(V3 pyd-free 추론 lane)에서 분기된 custom 작업 lane이다. V2 lane의 `2U_C custom allowlist rule`과 동일 패턴으로 다음 차이만 허용한다.

### 허용되는 V3U_C 전용 차이

- 3U_C custom 기능 신규 파일 (`docs/V3U_C_*.md`, `scripts/v3uc_*.py`, `tests/v3uc/**`)
- 본 registry §"V3U_C lane carry-forward"에 등록된 차이 항목
- 3U_C에서만 사용하는 추가 worker·helper (V3U 안전망과 충돌 없는 신규 경로)
- 3U_C 진행 사이클별 audit·plan 문서

### 금지되는 차이

- V3 official source 디렉토리 0줄 수정 invariant 위반 (V3U와 동일)
- V3U 안전망(`tests/v3u/`, `scripts/v3u_*`, `ui/main_window.py`, `docs/V3U_*` 핵심)의 임의 수정 — V3U lane을 통해 backport
- V3U_C 차이가 본 rule의 허용 카테고리에 없는 경로
- V3U lane이 가진 `STOM_Version_3U` HEAD를 임의 rewind/force-push

### 3단계 Verification Order

1. `3U vs 3`: pyd 제거 + V3U 전용 추론/검증/문서 차이만 기대 (현재 안전망)
2. `3U_C vs 3U`: V3U_C custom 차이가 본 registry에 모두 등록되어야 함
3. `3U_C vs 3`: 1·2 합집합 — V3 official 0줄 + V3U 안전망 + V3U_C custom

### 자동 검증 게이트

3U_C에서도 `verify_v3u_pyd_gui_contract.py` 통합 게이트 자동 실행 (8 stage 모두 PASS).
추가 게이트:
- 3U_C vs 3U diff가 본 registry §"V3U_C lane carry-forward"의 허용 카테고리만 포함
- 신규 worker·helper는 V3U `attr_inventory_diff` 도구로 동시 검증

## V3U_C lane carry-forward (지속 갱신)

3U_C 사이클 진행 중 발견되는 custom 차이·deferred 항목·carry-forward 위험을 본 절에 누적 기록한다.

### 사이클 1 (2026-05-22): E1 V3.X 흡수 자동화 파이프라인 도입

- 추가 파일 (custom allowlist 등록):
  - `scripts/v3uc_ingest_pipeline.py` (5 T-step 흡수 도구, ~270 lines)
  - `tests/v3uc/__init__.py` + `tests/v3uc/test_ingest_pipeline.py` (4 회귀 케이스)
  - `docs/V3U_C_INGEST_PIPELINE.md` (운영 매뉴얼)
  - `docs/V3U_C_INFERENCE_LESSONS.md` (3U_C 결함 진실 원천)
  - `docs/V3U_C_NEXT_STEPS.md` (3U_C decision tree)
- carry-forward 위험: 없음 (dry-run 우선 + 단위 테스트 검증)
- 잔여 의무:
  - V3.19 발표 시 실 dry-run + live 검증 (사용자 환경)
  - T01 merge conflict 자동 resolve는 별도 사이클 (현재 fail-fast로 사용자 위임)

### 사이클 2 (2026-05-22): E5 DB 마이그레이션 호환성 진단·자동 PK 추가 도구

- 추가 파일 (custom allowlist 등록):
  - `scripts/v3uc_db_compatibility_check.py` (~300 lines, --scan/--add-pk/--analyze-extra)
  - `tests/v3uc/test_db_compatibility.py` (7 회귀 케이스, mock sqlite)
  - `docs/V3U_C_DB_MIGRATION_PLAN.md` (종합 조사 + A++ 절차 정본화)
- 동작 매트릭스:
  - `--scan` read-only: PK 매트릭스 + V3.08 호환성 + JSON 매니페스트 출력
  - `--add-pk`: 백업 보유 검증 후 CREATE+INSERT+DROP+RENAME 패턴으로 PK 자동 추가
  - `--analyze-extra`: stock 외 DB(backtest/code_info/setting) schema 분석
- carry-forward 위험: 없음 (백업 보유 검증 + mock sqlite 7건 PASS)
- 잔여 의무:
  - backtest.db / code_info.db / setting.db schema 변환 (별도 사이클)
  - 분석 시스템 학습 DB(volume_spike·pattern 등) 폴리시 자동화

### 사이클 3 (2026-05-23): E7 strategy.db V2→V3 조건식 마이그레이션

- 추가 파일 (custom allowlist 등록):
  - `scripts/v3uc_strategy_migration.py` (~220 lines, scan/migrate + --target/--dry-run/--force)
  - `tests/v3uc/test_strategy_migration.py` (5 회귀 케이스, mock sqlite)
- 동작:
  - V2 컨벤션 `stockbuy/stocksell/stockoptibuy/...` → V3 컨벤션 `stock_buy/stock_sell/stock_optibuy/...` (밑줄 추가)
  - `--target` 으로 거래소별 prefix 선택 가능 (stock/stock_etf/stock_etn/stock_usa/coin/future 등 9종)
  - 백업 보유 검증 후에만 migrate (--force 우회 가능)
- 실 마이그레이션 결과 (2026-05-23, V3U 실 strategy.db):
  - stockbuy(51) → stock_buy: 51 행 복사
  - stocksell(35) → stock_sell: 35 행 복사
  - stockoptibuy(2) → stock_optibuy
  - stockoptisell(2) → stock_optisell
  - stockoptivars(5) → stock_optivars
  - 총 95 rows 복사, 에러 0
- carry-forward 위험: 없음
- 잔여 의무:
  - 다른 거래소(coin/future/stock_etf) 데이터 있을 시 별도 --target 호출
  - stockoptigavars/stockpassticks/stockvars는 V2/V3에 둘 다 없음 (V3 신규 기능)
  - V3.19+ 흡수 시 E1과 E5 통합 검토
