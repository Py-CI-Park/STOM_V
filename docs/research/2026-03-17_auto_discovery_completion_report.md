# STOM 자동 조건식 탐색 파이프라인 (Auto-Discovery) — 완료 보고서

- 작성일: 2026-03-17
- 브랜치: `STOM_Version_2U_C_CLI_v258`
- 기간: 2026-03-17 (단일 세션)
- 기준 커밋: `9abe97a` (작업 전) → `c5eb35a` (작업 후)

---

## 1. 프로젝트 개요

### 1.1 목적

STOM 백테스트 시스템의 **자동 조건식 탐색 파이프라인**을 구현하여,
DB에 저장된 전략 이름만으로 전체 파이프라인(백테스트 → 분석 → 조건 생성 → WFO 검증 → 승격)을
원커맨드로 실행할 수 있게 한다.

### 1.2 해결한 문제

| 기존 문제 | 해결 방법 |
|-----------|-----------|
| CSV 경로 수동 전달 (오타/잘못된 파일 위험) | Phase A에서 자동 CSV 경로 회수 (`_find_latest_csv`) |
| 15+ 인자 반복 입력 | `AutoDiscoveryConfig` dataclass로 설정 통합 |
| 백테스트 → 분석 사이 컨텍스트 단절 | 3-Phase 엔진이 데이터 흐름 자동 연결 |
| 재현성 부재 | 히스토리 DB에 모든 실행 결과 자동 저장 |
| 배치 실행 불가 | `discovery batch --config` 명령으로 다중 전략 순차 실행 |
| 파이프라인 디버깅 어려움 | Phase별 타이밍 + 다단계 분석 라운드 상세 리포트 |

### 1.3 총 작업량

| 항목 | 수치 |
|------|------|
| 총 커밋 수 | 10개 (5 feat + 5 docs) |
| 신규 파일 | 5개 (소스 1 + 테스트 4) |
| 수정 파일 | 6개 |
| 총 추가 라인 | **+3,007줄** |
| 신규 테스트 | **67개** (unit 59 + integration 8) |

---

## 2. Phase별 구현 상세

### 2.1 Phase 1: 자동 조건식 탐색 엔진 (원커맨드)

**커밋**: `ecbc8bc` | **변경**: 5파일, +980줄

**목적**: DB 전략명만으로 백테스트 → 분석 → WFO 검증 → 승격 파이프라인을 원커맨드 실행

**구현 내용**:

| 파일 | 유형 | 핵심 내용 |
|------|------|-----------|
| `cli/auto_discovery.py` | 신규 | `AutoDiscoveryConfig` (40+ 필드 dataclass), `find_latest_csv()` (재시도 포함 CSV 탐색), `run_multi_round_analysis()` (파라미터 완화 재시도), `AutoDiscoveryEngine` (Phase A/B/C 3단계 엔진) |
| `cli/runner.py` | 수정 | `_find_latest_csv()` 헬퍼, `_run_start_time` 캡처, 결과에 `csv_path` 추가 |
| `cli/subcommands.py` | 수정 | `discovery auto` 서브커맨드 파서 (33개 인자) |
| `cli/ai_controller.py` | 수정 | `auto_discover(config=None, **kwargs)` 편의 메서드 |
| `tests/unit/test_auto_discovery.py` | 신규 | 21개 테스트 (6개 클래스) |

**사용법**:
```bash
python stom_backtest.py discovery auto \
    --buy Min_B_Study --sell Min_S_Study \
    --start 20250401 --end 20250430 \
    --train-window-days 30 --test-window-days 10
```

**검증**: 21/21 passed, 618 unit regression passed

---

### 2.2 Phase 2: CSV 직접 지정 모드

**커밋**: `4fbd0b4` | **변경**: 3파일, +164줄

**목적**: 이미 보유한 CSV로 Phase A(백테스트)를 건너뛰고 Phase B/C 직행

**구현 내용**:

| 파일 | 변경 | 핵심 내용 |
|------|------|-----------|
| `cli/auto_discovery.py` | 수정 | `input_csv` 필드 추가, `run()`에서 input_csv 분기 (존재 확인 → Phase A 스킵) |
| `cli/subcommands.py` | 수정 | `--input / -i` 옵션 추가, `--buy` 조건부 필수 해제, 검증 로직 |
| `tests/unit/test_auto_discovery.py` | 수정 | 6개 테스트 추가 (`TestInputCsvSkipPhaseA` + CLI 파싱) |

**사용법**:
```bash
python stom_backtest.py discovery auto \
    --input backtest/csv/stock_bt_Min_B_Study_20260317.csv \
    --sell Min_S_Study \
    --start 20250401 --end 20250430 \
    --train-window-days 30 --test-window-days 10
```

**검증**: 27/27 passed, 624 unit regression passed

---

### 2.3 Phase 3: 배치 실행 모드

**커밋**: `71dfa63` | **변경**: 4파일, +476줄

**목적**: JSON 설정 파일로 여러 전략 조합을 순차 실행하여 최적 조합 탐색

**구현 내용**:

| 파일 | 유형 | 핵심 내용 |
|------|------|-----------|
| `cli/auto_discovery.py` | 수정 | `load_batch_config()` (JSON 파싱), `_merge_batch_run()` (common+override 병합), `run_batch()` (순차 실행 + 결과 집계) |
| `cli/subcommands.py` | 수정 | `discovery batch --config / -c` 서브커맨드 |
| `cli/ai_controller.py` | 수정 | `auto_discover_batch()` 편의 메서드 |
| `tests/unit/test_auto_discovery_batch.py` | 신규 | 19개 테스트 (5개 클래스) |

**배치 설정 JSON 형식**:
```json
{
  "common": {
    "sell_strategy": "Min_S_Study",
    "start_date": 20250401, "end_date": 20250430,
    "train_window_days": 30, "test_window_days": 10
  },
  "runs": [
    { "buy_strategy": "Min_B_Study_A", "alpha": 0.05 },
    { "buy_strategy": "Min_B_Study_B", "top_n": 3 }
  ]
}
```

**사용법**:
```bash
python stom_backtest.py discovery batch --config batch_config.json
```

**검증**: 19/19 passed, 643 unit regression passed

---

### 2.4 Phase 4: 리포트 강화 + 히스토리 DB

**커밋**: `63ec786` | **변경**: 5파일, +525줄

**목적**: 파이프라인 운영 가시성 확보 — Phase별 타이밍, 분석 라운드 상세, 실행 이력 DB

**구현 내용**:

| 파일 | 변경 | 핵심 내용 |
|------|------|-----------|
| `cli/auto_discovery.py` | 수정 | Phase A/B/C 각각 `phase_duration` 타이밍 추가, `pipeline_timing` dict (phase_a/b/c/total) |
| `cli/discovery_report.py` | 수정 | `pipeline_timing` + `analysis_rounds_log` 필드, Markdown에 `## Pipeline Timing` 테이블 + `## Analysis Rounds Log` 테이블 |
| `cli/history.py` | 수정 | `discovery_runs` 테이블 (17컬럼), `save_discovery_run()`, `get_discovery_runs(promoted_only)` |
| `cli/ai_controller.py` | 수정 | `auto_discover()`에 히스토리 자동 저장, `get_discovery_history()` 조회 |
| `tests/unit/test_phase4_report_history.py` | 신규 | 13개 테스트 (4개 클래스) |

**리포트 예시 (Markdown)**:
```
## Pipeline Timing
| Phase | Duration (s) |
|-------|-------------|
| A: Backtest | 45.2 |
| B: Analysis | 3.1 |
| C: WFO+Promote | 180.5 |
| **Total** | **228.8** |

## Analysis Rounds Log
| Round | alpha | min_samples | quantiles | top_n | candidates | status |
|-------|-------|-------------|-----------|-------|------------|--------|
| 1 | 0.05 | 30 | 10 | 5 | 0 | ok |
| 2 | 0.07 | 25 | 8 | 4 | 3 | ok |
```

**검증**: 13/13 passed, 656 unit regression passed

---

### 2.5 Phase 5: E2E 통합 테스트

**커밋**: `7115724` | **변경**: 1파일, +403줄

**목적**: 실제 DB + 데이터로 전체 파이프라인 end-to-end 동작 검증

**구현 내용**:

| 테스트 클래스 | 테스트 수 | 유형 | 검증 내용 |
|-------------|----------|------|-----------|
| `TestDiscoveryAutoCliHelp` | 3 | 빠른 | CLI help 출력, 인자 누락 에러 |
| `TestPhaseABacktestE2E` | 1 | @slow | 실제 DB로 백테스트 → csv_path 반환 (setting.db 미지원 시 스킵) |
| `TestPhaseBAnalysisE2E` | 1 | @slow | 실제 CSV로 분석 → feature_columns 키 존재 |
| `TestPipelineStructureE2E` | 2 | 빠른 | 전체 파이프라인 필수 키 검증, input_csv 스킵 구조 |
| `TestBatchE2E` | 1 | 빠른 | JSON 배치 3건 실행 → promoted/rejected 카운트 |
| `TestHistoryE2E` | 1 | 빠른 | save→get 라운드트립 + JSON 역직렬화 |

**설계 원칙**:
- `@pytest.mark.slow`로 느린 테스트 분리 (CI: `pytest -m "not slow"`)
- DB/환경 미존재 시 `pytest.skip()`으로 우아한 스킵
- `STOM_ALLOW_MINIMAL_SETTING=1` autouse fixture로 암호화 키 우회

**검증**: 8 passed, 1 skipped, 656 unit regression passed

---

## 3. 테스트 종합

### 3.1 신규 테스트 총괄

| 테스트 파일 | 테스트 수 | 범위 |
|------------|----------|------|
| `tests/unit/test_auto_discovery.py` | 27 | Phase 1+2: 엔진, CSV 탐색, 분석 재시도, CLI 파싱, input_csv 스킵 |
| `tests/unit/test_auto_discovery_batch.py` | 19 | Phase 3: 배치 설정, 병합, 순차 실행, CLI 파싱 |
| `tests/unit/test_phase4_report_history.py` | 13 | Phase 4: 타이밍, 리포트, 히스토리 DB |
| `tests/integration/test_auto_discovery_e2e.py` | 8+1skip | Phase 5: CLI E2E, 파이프라인 구조, 실제 DB |
| **합계** | **67+1skip** | |

### 3.2 회귀 테스트

| 시점 | 단위 테스트 결과 | 비고 |
|------|----------------|------|
| Phase 1 완료 | 618 passed | 기준선 |
| Phase 2 완료 | 624 passed (+6) | |
| Phase 3 완료 | 643 passed (+19) | |
| Phase 4 완료 | 656 passed (+13) | |
| Phase 5 완료 | 656 passed (유지) | E2E는 integration/ |

- 전 Phase에서 기존 테스트 회귀 없음
- pre-existing failure 1건 (`test_exit_codes.py`) — 이번 작업과 무관

### 3.3 테스트 실행 방법

```bash
# 전체 단위 테스트 (약 50초)
pytest tests/unit/ -q

# Auto-Discovery 관련 테스트만 (약 10초)
pytest tests/unit/test_auto_discovery.py tests/unit/test_auto_discovery_batch.py tests/unit/test_phase4_report_history.py -v

# E2E 통합 테스트 — 빠른 것만 (약 7초)
pytest tests/integration/test_auto_discovery_e2e.py -m "not slow" -v

# E2E 통합 테스트 — 실제 DB 포함 (수십 초~수 분)
pytest tests/integration/test_auto_discovery_e2e.py -v
```

---

## 4. 아키텍처 최종 구조

### 4.1 모듈 의존 관계

```
stom_backtest.py (진입점)
  └─ cli/subcommands.py
       ├─ discovery auto → cli/auto_discovery.py
       │    ├─ AutoDiscoveryConfig (dataclass, 45+ 필드)
       │    ├─ AutoDiscoveryEngine (Phase A/B/C)
       │    ├─ find_latest_csv() (재시도 포함)
       │    ├─ run_multi_round_analysis() (다단계 완화)
       │    ├─ run_batch() (순차 배치 실행)
       │    └─ load_batch_config() (JSON 파싱)
       └─ discovery batch → cli/auto_discovery.run_batch()

  └─ cli/ai_controller.py (프로그래밍 API)
       ├─ auto_discover()      → AutoDiscoveryEngine.run() + 히스토리 저장
       ├─ auto_discover_batch() → run_batch()
       └─ get_discovery_history() → history.get_discovery_runs()
```

### 4.2 데이터 흐름

```
[입력]                        [Phase A]                [Phase B]              [Phase C]
DB 전략명 ──────────────→ run_backtest() ─────→ analyze_results() ───→ discover_and_promote_strategy()
  또는                        │                   generate_conditions()      │
기존 CSV (--input) ─────→ (스킵) ─────────→ run_multi_round_analysis() → WFO 검증 → 승격/거절
                                                    │                          │
                                              다단계 재시도               pipeline_timing
                                              rounds_log                 히스토리 DB 저장
                                                                         리포트 생성
```

### 4.3 소스 파일 크기

| 파일 | 줄 수 | 역할 |
|------|-------|------|
| `cli/auto_discovery.py` | 561 | 핵심 엔진 + 배치 실행 |
| `cli/ai_controller.py` | 993 | 통합 파사드 (기존 + auto_discover) |
| `cli/subcommands.py` | 532 | CLI 파서 (기존 + auto/batch) |
| `cli/runner.py` | 473 | 백테스트 실행기 (기존 + csv_path) |
| `cli/history.py` | 450 | 히스토리 DB (기존 + discovery_runs) |
| `cli/discovery_report.py` | 164 | 리포트 생성 (기존 + timing/rounds) |

---

## 5. 커밋 이력

| # | 커밋 | 유형 | 설명 | 변경량 |
|---|------|------|------|--------|
| 1 | `ecbc8bc` | feat | Phase 1: 자동 조건식 탐색 엔진 | +980 |
| 2 | `9f00684` | docs | Phase 1~5 로드맵 문서 | +459 |
| 3 | `4fbd0b4` | feat | Phase 2: CSV 직접 지정 모드 | +164 |
| 4 | `af5e67b` | docs | Phase 2 완료 업데이트 | +7 |
| 5 | `71dfa63` | feat | Phase 3: 배치 실행 모드 | +476 |
| 6 | `5178b4d` | docs | Phase 3 완료 업데이트 | +7 |
| 7 | `63ec786` | feat | Phase 4: 리포트 강화 + 히스토리 DB | +525 |
| 8 | `5f5f88f` | docs | Phase 4 완료 업데이트 | +7 |
| 9 | `7115724` | feat | Phase 5: E2E 통합 테스트 | +403 |
| 10 | `c5eb35a` | docs | 로드맵 100% 달성 | +7 |

---

## 6. 알려진 제한 사항

| 항목 | 설명 | 영향 |
|------|------|------|
| Phase A E2E 테스트 스킵 | `setting.db` 암호화 키 불일치로 실제 백테스트 E2E 테스트가 스킵됨 | 실제 백테스트 실행은 GUI 환경 또는 올바른 setting.db에서만 가능 |
| 배치 순차 실행 | `run_batch()`가 순차 실행만 지원. 병렬 실행 미구현 | 대량 배치 시 시간 소요 |
| WFO 의존성 | Phase C가 기존 `discover_and_promote_strategy()` 재사용. 해당 모듈의 제약을 그대로 상속 | WFO 자체 개선은 별도 작업 필요 |
| pre-existing test failure | `test_exit_codes.py::test_execution_error_returns_two` 1건 | 이번 작업과 무관, 별도 수정 필요 |

---

## 7. 관련 문서

| 문서 | 경로 |
|------|------|
| 로드맵 (Phase별 상세) | `docs/research/2026-03-17_auto_discovery_pipeline_roadmap.md` |
| 자동 조건식 탐색 연구 | `docs/research/auto_condition_discovery_research.md` |
| 구현 체크리스트 (초기) | `docs/research/2026-03-10_auto_condition_discovery_implementation_checklist.md` |
| CLI AI 자동화 계획서 | `docs/STOM_CLI_AI_AUTOMATION_PLAN.md` |
