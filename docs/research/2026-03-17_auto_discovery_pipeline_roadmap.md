# STOM 자동 조건식 탐색 파이프라인 (Auto-Discovery) — 로드맵

- 작성일: 2026-03-17
- 브랜치: `STOM_Version_2U_C_CLI_v258`
- 기준 커밋: `ecbc8bc` (Phase 1 완료)

---

## 1. 프로젝트 배경과 목적

### 1.1 현재 문제

STOM의 자동 조건식 탐색 파이프라인은 **수동 멀티스텝 구조**로 운영되고 있다:

1. **수동 백테스트**: 사용자가 `stom_backtest.py --buy ... --sell ...`로 백테스트를 직접 실행
2. **CSV 경로 확인**: `backtest/csv/` 디렉토리에서 결과 CSV 파일 경로를 직접 확인
3. **수동 promote**: 확인한 CSV 경로를 `discovery promote` 명령에 15개 이상 인자와 함께 전달
4. **결과 확인**: 분석 → 조건 생성 → WFO 검증 → 승격/거절 확인

이 과정의 문제점:

| 문제 | 영향 |
|------|------|
| 수동 CSV 경로 전달 | 오타, 잘못된 파일 선택 위험 |
| 15+ 인자 반복 입력 | 인자 누락, 설정 불일치 발생 |
| 파이프라인 분절 | 백테스트 → 분석 사이 컨텍스트 단절 |
| 재현성 부재 | 동일 조건 재실행이 어려움 |
| 배치 실행 불가 | 여러 전략 조합을 순차 실행할 수 없음 |

### 1.2 최종 목표

**DB에 저장된 전략 이름만으로 전체 파이프라인을 원커맨드로 실행**하는 완전 자동화 시스템:

```bash
# 최소 명령 — 전략명 + 날짜 + WFO 윈도우만 지정
python stom_backtest.py discovery auto \
    --buy Min_B_Study --sell Min_S_Study \
    --start 20250401 --end 20250430 \
    --train-window-days 30 --test-window-days 10
```

궁극적으로 다음을 지원:

- **원커맨드 실행**: 전략명 → 백테스트 → 분석 → WFO → 승격 자동화 (Phase 1 ✅)
- **CSV 직접 투입**: 이미 보유한 CSV로 Phase A를 건너뛰고 분석 시작 (Phase 2)
- **배치 실행**: JSON 설정 파일로 여러 전략 조합 순차/병렬 실행 (Phase 3)
- **리포트 강화**: 파이프라인 단계별 상세 리포트 + 히스토리 DB (Phase 4)
- **E2E 검증**: 실제 데이터 기반 통합 테스트 (Phase 5)

---

## 2. 아키텍처 개요

### 2.1 3-Phase 파이프라인

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     AutoDiscoveryEngine.run(config)                     │
├─────────────┬─────────────────────┬─────────────────────────────────────┤
│  Phase A    │     Phase B         │          Phase C                    │
│  백테스트    │     분석+조건 생성    │          WFO 검증+승격              │
│             │                     │                                     │
│ run_backtest│ analyze_results()   │ discover_and_promote_strategy()     │
│     ↓       │ generate_conditions │      ↓                              │
│ CSV 생성    │ (다단계 재시도)       │ 임시 전략 저장 → WFO 실행           │
│     ↓       │     ↓               │      ↓                              │
│ csv_path    │ 후보 조건식          │ 평가 → 승격/거절 → 리포트           │
│   회수      │                     │                                     │
└─────────────┴─────────────────────┴─────────────────────────────────────┘
```

### 2.2 모듈 의존 관계

```
stom_backtest.py (진입점)
  └─ cli/subcommands.py        → discovery auto 파서
       └─ cli/auto_discovery.py → AutoDiscoveryConfig + AutoDiscoveryEngine
            ├─ cli/ai_controller.py   → run(), analyze_results(), generate_conditions()
            │    ├─ cli/runner.py      → run_backtest() + csv_path 반환
            │    ├─ cli/analyzer.py    → analyze_result_csv()
            │    ├─ cli/ml_factor_model.py → ML feature importance
            │    ├─ cli/condition_generator.py → 조건 코드 생성
            │    ├─ cli/wfo.py         → Walk-Forward Optimization
            │    ├─ cli/promotion.py   → 승격 기준 평가
            │    └─ cli/discovery_report.py → 리포트 생성
            └─ cli/discovery_config.py → DiscoveryConfig (Phase C용)
```

### 2.3 데이터 흐름

```
[DB 전략명]
    │
    ▼ Phase A
[runner.run_backtest()]
    │ 결과: backtest.db 저장 + backtest/csv/{name}_{strategy}_{timestamp}.csv
    │
    ▼ _find_latest_csv()
[CSV 파일 경로]
    │
    ▼ Phase B
[analyzer.analyze_result_csv()]
    │ B_* 컬럼 통계 분석 (t-test, quantile)
    │
    ▼ [ml_factor_model (선택)]
    │ ML feature importance ranking
    │
    ▼ [condition_generator]
    │ 후보 조건식 → Python 코드 생성
    │
    ▼ Phase C
[discover_and_promote_strategy()]
    │ 임시 전략 DB 저장
    │ → WFO 교차 검증 (train/test 윈도우)
    │ → 평가 (success_rate, mean_oos_metric, avg_trade_count)
    │ → 승격 or 거절
    │
    ▼
[최종 전략 DB 저장 + 리포트]
```

---

## 3. Phase 1: 자동 조건식 탐색 엔진 (Auto-Discovery) — ✅ 완료

### 3.1 구현 목적

**수동 멀티스텝 파이프라인을 원커맨드로 통합**하여:
- CSV 경로 수동 전달 제거
- 15+ 인자 반복 입력 제거
- 백테스트 → 분석 사이 컨텍스트 자동 연결

### 3.2 구현 내용

#### 3.2.1 신규 파일

**`cli/auto_discovery.py`** (~310줄)

| 구성요소 | 설명 |
|---------|------|
| `AutoDiscoveryConfig` | 전체 파이프라인 설정 dataclass. 백테스트(buy/sell strategy, date range, timeframe, engines), 분석(top_n, min_samples, quantiles, alpha), ML(feature_limit, model_type, weight), 다단계 재시도(max_rounds, relax steps), WFO(train/test window, objective), 프로모션(preset, auto_relax), 출력(report paths) 설정 통합 |
| `find_latest_csv()` | `backtest/csv/` 디렉토리에서 전략명을 포함하며 지정 타임스탬프 이후에 수정된 최신 CSV를 반환. 백테스트 자식 프로세스의 CSV 쓰기 지연을 감안해 최대 3회 재시도 (2초 간격) |
| `run_multi_round_analysis()` | Round 1은 사용자 파라미터로 분석. 유효 후보 부족 시 파라미터를 완화하며 재시도: alpha += 0.02, min_samples -= 5, quantiles -= 2, top_n -= 1. 최대 max_rounds회 반복. 각 라운드의 파라미터와 후보 수를 rounds_log에 기록 |
| `AutoDiscoveryEngine` | Phase A: `controller.run()` 실행 → `find_latest_csv()`로 CSV 회수. Phase B: `run_multi_round_analysis()`로 다단계 분석 → 조건 생성. Phase C: 기존 `discover_and_promote_strategy()` 재사용하여 WFO 검증 → 승격/거절 → 리포트 생성 |

**`tests/unit/test_auto_discovery.py`** (~280줄)

| 테스트 클래스 | 테스트 수 | 검증 내용 |
|-------------|----------|----------|
| `TestFindLatestCsv` | 6 | 디렉토리 없음, 매칭 없음, 최신 선택, 타임스탬프 필터, 재시도 |
| `TestRunMultiRoundAnalysis` | 3 | 1회 성공, 완화 재시도, 전체 실패 |
| `TestPhaseABacktest` | 3 | 성공, 백테스트 실패, CSV 미발견 |
| `TestAutoDiscoveryEngineRun` | 3 | 전체 파이프라인, Phase A 중단, Phase B 중단 |
| `TestAIControllerAutoDiscover` | 2 | kwargs 위임, config 객체 |
| `TestCliParsing` | 4 | help, 필수 인자, 기본값, 필수 누락 |

#### 3.2.2 수정 파일

**`cli/runner.py`** (+15줄)
- `import glob, time` 추가
- `_find_latest_csv(strategy_name, after_timestamp)`: 백테스트 완료 후 CSV 경로 탐색
- `run_backtest()` 시작 시 `_run_start_time = time.time()` 캡처
- 결과 dict에 `csv_path` 추가 — Phase A → Phase B 연결의 핵심 브릿지

**`cli/subcommands.py`** (+55줄)
- `discovery auto` 서브커맨드 파서: 33개 인자 (--buy, --sell, --start, --end, --train-window-days, --test-window-days 필수 + 27개 선택)
- `_handle_discovery()`에 `auto` 분기: `AutoDiscoveryConfig` 생성 → `AutoDiscoveryEngine.run()` 호출

**`cli/ai_controller.py`** (+20줄)
- `auto_discover(config=None, **kwargs)`: 프로그래밍 방식 호출 API. config 인스턴스 또는 kwargs로 `AutoDiscoveryConfig` 생성 후 `AutoDiscoveryEngine.run()` 실행

#### 3.2.3 재사용한 기존 모듈

| 모듈 | 역할 | Phase |
|------|------|-------|
| `cli/runner.py` | 백테스트 실행 + CSV 생성 | A |
| `cli/analyzer.py` | B_* 컬럼 통계 분석 (t-test, quantile) | B |
| `cli/ml_factor_model.py` | ML feature importance ranking | B |
| `cli/condition_generator.py` | 분석 결과 → Python 조건 코드 생성 | B |
| `cli/wfo.py` | Walk-Forward Optimization 실행 | C |
| `cli/promotion.py` | 승격 기준 해석 (preset → criteria) | C |
| `cli/discovery_report.py` | JSON/Markdown 리포트 생성 | C |
| `cli/discovery_config.py` | DiscoveryConfig (Phase C 전달용) | C |

### 3.3 검증 결과

| 검증 항목 | 결과 |
|-----------|------|
| `python -c "import cli.auto_discovery"` | 성공 |
| `pytest tests/unit/test_auto_discovery.py` | **21/21 passed** (0.36s) |
| `python stom_backtest.py discovery auto --help` | 정상 출력 |
| `pytest tests/unit/ -q` | **618 passed**, 1 pre-existing failure (49.96s) |

### 3.4 사용법

**CLI:**
```bash
# 최소 필수 인자
python stom_backtest.py discovery auto \
    --buy Min_B_Study --sell Min_S_Study \
    --start 20250401 --end 20250430 \
    --train-window-days 30 --test-window-days 10

# 전체 옵션
python stom_backtest.py discovery auto \
    --buy Min_B_Study --sell Min_S_Study \
    --start 20250401 --end 20250430 \
    --timeframe min --engines 4 --betting 1 \
    --top-n 5 --alpha 0.05 --min-samples 30 --quantiles 10 \
    --ml-feature-limit 10 --ml-model-type random_forest --ml-weight 0.3 \
    --max-rounds 3 \
    --train-window-days 30 --test-window-days 10 \
    --objective tpi --promotion-preset balanced \
    --auto-relax --max-relax-steps 3 \
    --output-code generated.py \
    --report-json report.json --report-md report.md
```

**프로그래밍 API:**
```python
from cli.ai_controller import AIBacktestController

controller = AIBacktestController()
result = controller.auto_discover(
    buy_strategy='Min_B_Study',
    sell_strategy='Min_S_Study',
    start_date=20250401,
    end_date=20250430,
    train_window_days=30,
    test_window_days=10,
)
print(result['status'])     # 'ok' or 'error'
print(result['promoted'])   # True or False
print(result['csv_path'])   # 백테스트 결과 CSV 경로
```

---

## 4. Phase 2: CSV 직접 지정 모드 — ✅ 완료

### 4.1 구현 목적

이미 백테스트를 실행하여 CSV가 존재하는 경우, Phase A(백테스트 실행)를 건너뛰고
바로 Phase B(분석) → Phase C(WFO 검증)로 진입할 수 있어야 한다.

**사용 시나리오:**
- 과거에 실행한 백테스트 CSV를 재분석하고 싶을 때
- 외부에서 생성한 CSV로 조건식 탐색을 실행할 때
- Phase A가 이미 성공했으나 Phase B/C 파라미터를 변경해 재실행할 때

### 4.2 구현 계획

| 파일 | 변경 | 설명 |
|------|------|------|
| `cli/auto_discovery.py` | 수정 | `AutoDiscoveryConfig.input_csv` 필드 추가. `AutoDiscoveryEngine.run()`에서 `input_csv`가 지정되면 Phase A를 건너뛰고 Phase B로 직행 |
| `cli/subcommands.py` | 수정 | `discovery auto --input` 옵션 추가. `--input` 지정 시 `--buy` 필수 해제 |
| `tests/unit/test_auto_discovery.py` | 수정 | CSV 직접 투입 경로 테스트 추가 (Phase A 스킵 검증, 유효하지 않은 CSV 에러 처리) |

**사용법 (목표):**
```bash
# 기존 CSV로 Phase B/C만 실행
python stom_backtest.py discovery auto \
    --input backtest/csv/stock_bt_Min_B_Study_20260317_120000.csv \
    --sell Min_S_Study \
    --start 20250401 --end 20250430 \
    --train-window-days 30 --test-window-days 10
```

### 4.3 구현 결과

- 커밋: `4fbd0b4`
- 변경: 3개 파일, +164줄 / -9줄
- 테스트: 27/27 passed (기존 21 + 신규 6)
- 회귀: 624 passed (pre-existing 1 failure 제외)

---

## 5. Phase 3: 배치/스케줄 실행 — ✅ 완료

### 5.1 구현 목적

여러 전략 조합을 한 번에 실행하여 최적 조합을 자동 탐색한다.

**사용 시나리오:**
- 매수 전략 5개 × 매도 전략 3개 = 15가지 조합을 자동 실행
- 동일 전략을 날짜 범위를 바꿔가며 안정성 검증
- 주기적(일/주 단위) 자동 탐색 실행

### 5.2 구현 계획

| 파일 | 변경 | 설명 |
|------|------|------|
| `cli/auto_discovery.py` | 수정 | `AutoDiscoveryBatchConfig` dataclass 추가. `run_batch(configs)` 메서드로 순차/병렬 실행 |
| `cli/subcommands.py` | 수정 | `discovery batch --config batch.json` 서브커맨드 추가 |
| `cli/ai_controller.py` | 수정 | `auto_discover_batch()` 편의 메서드 추가 |
| `tests/unit/test_auto_discovery_batch.py` | 신규 | 배치 설정 파싱, 순차 실행, 결과 집계 테스트 |

**배치 설정 JSON 예시:**
```json
{
  "common": {
    "sell_strategy": "Min_S_Study",
    "start_date": 20250401,
    "end_date": 20250430,
    "train_window_days": 30,
    "test_window_days": 10
  },
  "runs": [
    { "buy_strategy": "Min_B_Study_A", "alpha": 0.05 },
    { "buy_strategy": "Min_B_Study_B", "alpha": 0.03 },
    { "buy_strategy": "Min_B_Study_C", "top_n": 3 }
  ]
}
```

**사용법 (목표):**
```bash
python stom_backtest.py discovery batch --config batch_config.json
```

**출력 예시:**
```json
{
  "status": "ok",
  "total": 3,
  "promoted": 1,
  "results": [
    { "buy_strategy": "Min_B_Study_A", "promoted": true, "strategy_name": "Auto_A_..." },
    { "buy_strategy": "Min_B_Study_B", "promoted": false, "reason": "success_rate<0.6" },
    { "buy_strategy": "Min_B_Study_C", "promoted": false, "reason": "all_rounds_no_trades" }
  ]
}
```

### 5.3 구현 결과

- 커밋: `71dfa63`
- 변경: 4개 파일, +476줄 / -1줄
- 테스트: 19/19 passed (신규)
- 회귀: 643 passed (pre-existing 1 failure 제외)

---

## 6. Phase 4: 리포트 강화 — ✅ 완료

### 6.1 구현 목적

파이프라인 실행 결과의 투명성과 재현성을 높인다.

**현재 한계:**
- Phase B 다단계 분석 라운드별 상세 정보가 Phase C 리포트에 포함되지 않음
- Phase A/B/C 각 단계의 소요 시간 정보가 없음
- 파이프라인 실행 히스토리가 DB에 저장되지 않아 과거 실행 비교 불가

### 6.2 구현 계획

| 파일 | 변경 | 설명 |
|------|------|------|
| `cli/auto_discovery.py` | 수정 | 각 Phase에 `phase_duration` 타이밍 추가. Phase B `rounds_log`를 최종 결과에 포함 |
| `cli/discovery_report.py` | 수정 | `build_discovery_report()`에 auto-discovery 전용 섹션 추가: 파이프라인 타이밍, 다단계 분석 라운드 상세 |
| `cli/history.py` | 수정 | `save_discovery_run()` 함수 추가: auto-discovery 실행 이력을 `history.db`에 저장 |
| `cli/ai_controller.py` | 수정 | `auto_discover()` 완료 후 히스토리 자동 저장. `get_discovery_history()` 조회 메서드 추가 |
| `tests/unit/test_auto_discovery.py` | 수정 | 타이밍 필드 존재 검증, 히스토리 저장/조회 테스트 |

**리포트 강화 내용:**

```markdown
## Pipeline Timing
| Phase | 소요 시간 | 상태 |
|-------|----------|------|
| A: 백테스트 | 45.2초 | 성공 |
| B: 분석 | 3.1초 (2라운드) | 성공 |
| C: WFO+승격 | 180.5초 | 승격 |
| **합계** | **228.8초** | |

## Phase B 다단계 분석 상세
| Round | alpha | min_samples | quantiles | top_n | 후보 수 | 상태 |
|-------|-------|-------------|-----------|-------|--------|------|
| 1 | 0.05 | 30 | 10 | 5 | 0 | 재시도 |
| 2 | 0.07 | 25 | 8 | 4 | 3 | 성공 |
```

### 6.3 구현 결과

- 커밋: `63ec786`
- 변경: 5개 파일, +525줄 / -2줄
- 테스트: 13/13 passed (신규)
- 회귀: 656 passed (pre-existing 1 failure 제외)

---

## 7. Phase 5: E2E 통합 테스트 — ✅ 완료

### 7.1 구현 목적

실제 DB와 소규모 데이터셋으로 `discovery auto` 전체 파이프라인을 end-to-end 검증한다.

**현재 한계:**
- Phase 1의 테스트는 모두 mock 기반 — 실제 백테스트/분석/WFO 미실행
- 모듈 간 인터페이스 정합성은 단위 테스트로 보장 불가
- 실제 데이터의 CSV 컬럼 구조, 분석 결과 형식 등은 통합 검증 필요

### 7.2 구현 계획

| 파일 | 변경 | 설명 |
|------|------|------|
| `tests/integration/test_auto_discovery_e2e.py` | 신규 | 실제 DB 데이터로 전체 파이프라인 실행. `@pytest.mark.slow` 데코레이터로 일상 CI에서 제외 |
| `tests/fixtures/` | 신규 | E2E 테스트용 소규모 fixture 데이터 (선택) |

**테스트 시나리오:**

| 시나리오 | 내용 | 예상 시간 |
|---------|------|----------|
| 분봉 전략 E2E | `Min_B_Study` + `Min_S_Study`, 3일 범위, 엔진 2개 | ~60초 |
| Phase A 성공 → CSV 존재 확인 | 결과 CSV가 실제로 생성되는지 검증 | Phase A 내 |
| Phase B 분석 결과 형식 | 분석 결과 dict의 필수 키/값 검증 | Phase B 내 |
| Phase C WFO 실행 | WFO가 실제로 실행되고 결과를 반환하는지 검증 | ~120초 |
| 전체 파이프라인 연결 | Phase A → B → C 데이터 흐름 정합성 | ~180초 |

**주의사항:**
- 실제 DB(`backtest_stock_tick.db`, `backtest_stock_min.db`)가 필요
- 전략이 `strategy.db`에 존재해야 함
- CI 환경에서는 `@pytest.mark.slow`로 제외
- 테스트 후 생성된 임시 전략은 반드시 정리

### 7.3 구현 결과

- 커밋: `7115724`
- 변경: 1개 파일, +403줄
- 테스트: 8 passed, 1 skipped (setting.db 환경 미지원으로 Phase A 스킵)
- 회귀: 656 unit passed (pre-existing 1 failure 제외)

---

## 8. Phase별 우선순위 요약

| Phase | 제목 | 상태 | 난이도 | 작업량 | 의존성 |
|-------|------|------|--------|--------|--------|
| **1** | 자동 조건식 탐색 엔진 (원커맨드) | **✅ 완료** | 중간 | +980줄 | 없음 |
| **2** | CSV 직접 지정 모드 | **✅ 완료** | 낮음 | +164줄 | Phase 1 |
| **3** | 배치/스케줄 실행 | **✅ 완료** | 중간 | +476줄 | Phase 1 |
| **4** | 리포트 강화 + 히스토리 DB | **✅ 완료** | 낮음~중간 | +525줄 | Phase 1 |
| **5** | E2E 통합 테스트 | **✅ 완료** | 중간~높음 | +403줄 | Phase 1, 실제 DB |
| **6** | 히스토리 CLI 대시보드 | **✅ 완료** | 낮음 | +476줄 | 없음 |
| **7** | 배치 병렬 실행 | **✅ 완료** | 중간 | +284줄 | Phase 6 |
| **8** | 크로스 타임프레임 탐색 | **✅ 완료** | 중간 | +354줄 | Phase 7 |
| **9** | 조건식 진화 루프 | **✅ 완료** | 높음 | +684줄 | Phase 7 |

**권장 순서:** Phase 2 → Phase 4 → Phase 3 → Phase 5

- Phase 2는 가장 적은 작업량으로 즉시 활용 가치를 제공
- Phase 4는 파이프라인 운영 시 디버깅/분석에 필수
- Phase 3는 실무에서 전략 탐색을 본격 활용할 때 필요
- Phase 5는 안정성 보장을 위해 마지막에 수행

---

## 9. 기존 모듈 현황 참조

Phase 1이 재사용하는 기존 CLI 모듈들의 현재 상태:

| 모듈 | 줄 수 | 테스트 | 상태 |
|------|-------|--------|------|
| `cli/runner.py` | ~470 | `test_runner.py` | 안정 |
| `cli/analyzer.py` | ~250 | `test_analyzer.py` | 안정 |
| `cli/ml_factor_model.py` | ~200 | `test_ml_factor_model.py` | 안정 |
| `cli/condition_generator.py` | ~300 | `test_condition_generator.py` | 안정 |
| `cli/wfo.py` | ~250 | `test_wfo.py` | 안정 |
| `cli/promotion.py` | ~150 | `test_promotion.py` | 안정 |
| `cli/discovery_report.py` | ~200 | `test_discovery_report.py` | 안정 |
| `cli/discovery_config.py` | ~55 | (dataclass) | 안정 |
| `cli/ai_controller.py` | ~950 | (통합) | 안정 |
| `cli/subcommands.py` | ~490 | `test_subcommands.py` | 안정 |

전체 CLI 테스트: **618 passed** (2026-03-17 기준, 1 pre-existing failure 제외)
