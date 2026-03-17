# STOM 자동 조건식 탐색 파이프라인 — Phase 6~9 개발 계획서

- 작성일: 2026-03-17
- 브랜치: `feature/discovery-monitoring-batch-v2`
- 기준 커밋: `48c2f34` (Phase 1~5 머지 후)
- 상위 브랜치: `STOM_Version_2U_C_CLI_v258`

---

## 1. 배경

### 1.1 완료된 기반 (Phase 1~5)

`feature/auto-discovery-pipeline` 브랜치에서 다음 5개 Phase가 완료되어
`STOM_Version_2U_C_CLI_v258`에 머지되었다:

| Phase | 기능 | 커밋 | 변경량 |
|-------|------|------|--------|
| 1 | 자동 조건식 탐색 엔진 (원커맨드) | `ecbc8bc` | +980줄 |
| 2 | CSV 직접 지정 모드 (--input) | `4fbd0b4` | +164줄 |
| 3 | 배치 순차 실행 (discovery batch) | `71dfa63` | +476줄 |
| 4 | 리포트 강화 + 히스토리 DB | `63ec786` | +525줄 |
| 5 | E2E 통합 테스트 | `7115724` | +403줄 |

**총계**: 11파일, +3,007줄, 656 unit + 9 integration tests

### 1.2 현재 아키텍처

```
stom_backtest.py
  └─ cli/subcommands.py
       ├─ discovery auto     → AutoDiscoveryEngine (Phase A/B/C)
       ├─ discovery batch    → run_batch() (순차 실행)
       ├─ discovery analyze  → analyzer
       ├─ discovery promote  → discover_and_promote_strategy()
       └─ (예정) history, compare, evolve

  └─ cli/ai_controller.py (프로그래밍 API)
       ├─ auto_discover()          → 단일 파이프라인
       ├─ auto_discover_batch()    → 배치 순차 실행
       └─ get_discovery_history()  → 히스토리 조회
```

### 1.3 해결되지 않은 문제

| 문제 | Phase |
|------|-------|
| 히스토리를 Python API로만 조회 가능, CLI 미지원 | 6 |
| 배치 실행이 순차만 지원 (15건 × 3분 = 45분) | 7 |
| 단일 타임프레임에서만 탐색 가능 (tick 또는 min) | 8 |
| 승격 실패 시 수동 파라미터 재조정 필요 | 9 |

---

## 2. 개발 의존 관계

```
Phase 6 (히스토리 CLI) ────── 독립, 가장 먼저 착수
    │
    ├── table_formatter.py 제공
    │
Phase 7 (배치 병렬) ──────── Phase 6의 table_formatter 재사용
    │
    ├── _run_single_pipeline() + parallel 기반 제공
    │
    ├── Phase 8 (크로스 타임프레임) ── Phase 7의 parallel batch 활용
    │
    └── Phase 9 (진화 루프) ────────── Phase 7의 parallel 실행 활용
```

**권장 순서**: Phase 6 → Phase 7 → Phase 8 → Phase 9

---

## 3. Phase 6: 히스토리 CLI 대시보드

### 3.1 목적

`discovery_runs` 히스토리를 **CLI에서 직접 조회/비교**할 수 있게 한다.
현재는 Python API(`controller.get_discovery_history()`)로만 가능하여,
운영 중 과거 실행 결과를 확인하려면 별도 스크립트를 작성해야 한다.

### 3.2 사용 시나리오

- 최근 20건의 탐색 실행 이력을 터미널에서 빠르게 확인
- 승격된 결과만 필터링하여 성공적인 전략 파라미터 분석
- 2~3개 실행 결과를 나란히 비교하여 어떤 파라미터가 더 효과적인지 판단

### 3.3 CLI 명령어 설계

```bash
# 최근 히스토리 조회 (기본 20건, 터미널 테이블)
python stom_backtest.py discovery history

# 승격된 결과만 표시
python stom_backtest.py discovery history --promoted-only

# 최대 5건, JSON 형식 출력
python stom_backtest.py discovery history --limit 5 --json

# 실행 결과 비교 (ID 지정)
python stom_backtest.py discovery compare --ids 1,2,3

# 비교 결과를 JSON으로
python stom_backtest.py discovery compare --ids 1,2,3 --json
```

### 3.4 구현 상세

#### Step 6.1: `cli/table_formatter.py` 신규 (~40줄)

터미널 테이블 포맷터. 외부 의존성 없이 순수 Python으로 구현.

```python
def format_table(rows: list[dict], columns: list[tuple[str, str, int]],
                 max_width: int = 120) -> str:
    """딕트 리스트를 터미널 테이블 문자열로 포맷한다.

    Args:
        rows: 데이터 딕트 리스트.
        columns: [(key, header_label, min_width), ...] 튜플 리스트.
        max_width: 전체 테이블 최대 폭.

    Returns:
        정렬된 멀티라인 문자열 (print() 가능).
    """
```

기능:
- 컬럼별 최소 폭 보장
- 긴 값은 `...`으로 truncation
- 헤더/구분선/데이터 행 출력
- 빈 rows일 때 "(결과 없음)" 출력

#### Step 6.2: `cli/history.py` 수정 (~45줄)

기존 `compare_runs()` 패턴(라인 234-283)을 `discovery_runs` 테이블에 적용.

```python
_DISCOVERY_METRICS = frozenset({
    'pipeline_duration', 'phase_a_duration', 'phase_b_duration',
    'phase_c_duration', 'phase_b_rounds',
})

def compare_discovery_runs(discovery_ids: list[int], db_path: str = None) -> dict:
    """여러 discovery 실행을 조회하여 비교한다.

    Returns:
        {
            'runs': [row_dict, ...],
            'best': {
                'pipeline_duration': shortest_id,
                'promoted': first_promoted_id,
                ...
            }
        }
    """
```

SQL: `SELECT * FROM discovery_runs WHERE discovery_id IN (?,?,?) ORDER BY discovery_id`
Best 판정: `pipeline_duration` 최소, `promoted=1` 우선, `phase_b_rounds` 최대(더 철저한 분석).

#### Step 6.3: `cli/subcommands.py` 수정 (~95줄)

파서 추가:
```python
# discovery history
disc_history = disc_sub.add_parser('history', help='탐색 실행 히스토리 조회')
disc_history.add_argument('--promoted-only', action='store_true', default=False)
disc_history.add_argument('--limit', '-n', type=int, default=20)
disc_history.add_argument('--json', action='store_true', default=False, dest='output_json')

# discovery compare
disc_compare = disc_sub.add_parser('compare', help='탐색 실행 결과 비교')
disc_compare.add_argument('--ids', required=True, help='쉼표 구분 discovery_id 목록')
disc_compare.add_argument('--json', action='store_true', default=False, dest='output_json')
```

핸들러:
- `history`: `get_discovery_history()` → `format_table()` 또는 JSON
  - 테이블 컬럼: ID, Timestamp, Buy Strategy, Status, Promoted, Duration(s), Strategy Name
- `compare`: `compare_discovery_runs(ids)` → 비교 테이블 + best 표시

#### Step 6.4: `cli/ai_controller.py` 수정 (~15줄)

```python
def compare_discovery_history(self, discovery_ids: list[int]) -> dict:
    """여러 discovery 실행 결과를 비교한다."""
```

#### Step 6.5: `tests/unit/test_discovery_history_cli.py` 신규 (~180줄)

| 클래스 | 테스트 수 | 검증 내용 |
|--------|----------|----------|
| `TestFormatTable` | 3 | 기본 렌더링, truncation, 빈 rows |
| `TestCompareDiscoveryRuns` | 3 | 비교 로직, 빈 IDs, best 감지 |
| `TestHistoryCliParsing` | 4 | arg 파싱, --promoted-only, --limit, --json |
| `TestCompareCliParsing` | 2 | --ids 파싱, 형식 검증 |
| `TestHistoryCliExecution` | 3 | mock controller, 테이블 출력, JSON 모드 |

### 3.5 예상 작업량

~375줄 (소스 ~195 + 테스트 ~180). 난이도 낮음. 테스트 ~15개.

---

## 4. Phase 7: 배치 병렬 실행

### 4.1 목적

`discovery batch --parallel N` 옵션으로 N개 파이프라인을 **동시 실행**하여
배치 탐색 속도를 최대 N배 향상한다.

현재 15건 순차 실행 × 평균 3분 = 45분 → 병렬 3개 시 15분.

### 4.2 사용 시나리오

```bash
# 기존 순차 실행 (호환성 유지)
python stom_backtest.py discovery batch --config batch.json

# 3개 파이프라인 병렬 실행
python stom_backtest.py discovery batch --config batch.json --parallel 3

# 프로그래밍 API
controller.auto_discover_batch(batch_path='batch.json', parallel=3)
```

### 4.3 설계 핵심

#### 엔진 수 분배
각 병렬 파이프라인이 사용할 엔진 수 = `base_engine_count // parallel_count`:
- `engine_count=8, parallel=2` → 파이프라인당 4개 엔진
- `engine_count=4, parallel=3` → 파이프라인당 1개 엔진 (최소 1)

#### SQLite 동시 접근
병렬 파이프라인이 동일 DB(backtest.db, strategy.db)에 동시 쓰기할 수 있으므로
**WAL(Write-Ahead Logging) 모드**를 활성화:
```python
con.execute("PRAGMA journal_mode=WAL")
```
WAL 모드는 동시 읽기를 허용하고, 쓰기는 자동 직렬화한다.

#### Windows spawn 대응
`ProcessPoolExecutor`의 자식 프로세스는 Windows에서 새 Python 인터프리터를 생성하므로:
- `controller` 객체를 전달하지 않음 (pickling 불가)
- 각 자식 프로세스가 `AIBacktestController()`를 내부 생성
- `_STOM_CLI_DICT_SET` 환경 변수가 손자 프로세스까지 자동 전파

### 4.4 구현 상세

#### Step 7.1: `_run_single_pipeline()` 추출 (~35줄)

기존 `run_batch()` 루프 본문을 독립 함수로 분리:

```python
def _run_single_pipeline(common: dict, run_override: dict, idx: int,
                          engine_count_override: int = None) -> dict:
    """단일 파이프라인 실행 (병렬 호출 가능한 picklable 단위).

    controller를 내부에서 생성하여 Windows spawn 호환성 확보.
    engine_count_override가 지정되면 AutoDiscoveryConfig.engine_count를 오버라이드.
    """
```

#### Step 7.2: `run_batch()` 수정 (~50줄)

```python
def run_batch(batch_path=None, common=None, runs=None,
              controller=None, parallel: int = 0) -> dict:
```

- `parallel == 0`: 기존 순차 루프 (변경 없음)
- `parallel > 0`:
  1. `engine_count_per = max(1, common.get('engine_count', 4) // parallel)`
  2. `ProcessPoolExecutor(max_workers=parallel)` 생성
  3. `submit(_run_single_pipeline, common, run, idx, engine_count_per)` for each run
  4. `as_completed()` 로 결과 수집
  5. 인덱스 순서로 정렬 후 반환

#### Step 7.3~7.4: CLI + dispatch (~20줄)

`--parallel / -p` 옵션 추가 및 dispatch chain 연결.

#### Step 7.5: 테스트 확장 (~120줄)

`TestRunBatchParallel` 클래스 6개 테스트.

### 4.5 리스크 및 대응

| 리스크 | 심각도 | 대응 방법 |
|--------|--------|-----------|
| SQLite 쓰기 경합 (backtest.db, strategy.db) | 높음 | WAL 모드 활성화. 파이프라인별 임시 전략명이 이미 고유(`__AUTO_TMP__` + timestamp) |
| DICT_SET 중첩 전파 (ProcessPool → engine Process) | 중간 | `os.environ['_STOM_CLI_DICT_SET']` 방식이 이미 모든 자손에 자동 상속 |
| controller pickling 실패 | 낮음 | controller 미전달, 자식 프로세스 내부 생성 |
| 메모리/CPU 과부하 | 낮음 | parallel 수를 사용자가 명시적으로 지정 |

### 4.6 예상 작업량

~220줄 (소스 ~100 + 테스트 ~120). 난이도 중간. 테스트 ~6개.

---

## 5. Phase 8: 크로스 타임프레임 탐색

### 5.1 목적

동일 전략을 **tick/min 양쪽 타임프레임에서 자동 실행**하고 결과를 교차 비교한다.
전략의 타임프레임 간 안정성을 검증하여 더 견고한 전략 선별을 가능케 한다.

### 5.2 사용 시나리오

```bash
# 배치 설정 JSON에 timeframes 배열 추가
{
  "common": {
    "sell_strategy": "Min_S_Study",
    "start_date": 20250401, "end_date": 20250430,
    "train_window_days": 30, "test_window_days": 10
  },
  "timeframes": ["tick", "min"],
  "runs": [
    { "buy_strategy": "Min_B_Study_A" },
    { "buy_strategy": "Min_B_Study_B" }
  ]
}
```

위 설정 시 4건 실행됨: A-tick, A-min, B-tick, B-min.
결과 리포트에 동일 전략의 tick/min 성능 비교 테이블 포함.

### 5.3 아키텍처 제약

- 각 타임프레임은 **다른 DB 파일** 사용: `stock_tick_back.db` vs `stock_min_back.db`
- 각 타임프레임은 **다른 엔진 클래스** 사용: `BackEngineKiwoomTick` vs `BackEngineKiwoomMin`
- **단일 run 내에서 혼합 불가** — 반드시 별도 run으로 분리 실행

따라서 `_expand_timeframes()`가 각 run을 타임프레임별로 복제하는 방식으로 구현.

### 5.4 구현 상세

#### Step 8.1: timeframe 확장 함수 (~25줄)

```python
def _expand_timeframes(common: dict, runs: list, timeframes: list) -> list:
    """timeframes 배열이 있으면 각 run을 tick/min별로 복제한다.

    Returns:
        확장된 runs 리스트. 각 run에 is_tick 필드와 _timeframe_label 추가.
    """
```

`load_batch_config()` 수정: `timeframes` 필드 추출.

#### Step 8.2: `run_batch()` 수정 (~20줄)

`timeframes` 파라미터 추가. batch_path 로드 시 자동 추출.

#### Step 8.3: 크로스 비교 리포트 (~50줄)

```python
def build_cross_timeframe_report(batch_result: dict) -> dict:
    """동일 buy_strategy의 tick/min 결과를 짝지어 비교 리포트 생성.

    Returns: {'pairs': [{'buy_strategy': str, 'tick': summary, 'min': summary}, ...]}
    """

def render_cross_timeframe_markdown(report: dict) -> str:
    """Markdown 비교 테이블 렌더링."""
```

#### Step 8.4: 타임프레임 호환성 검증 (~15줄)

```python
def _validate_timeframe_compat(config: AutoDiscoveryConfig) -> str | None:
    """is_tick에 맞는 DB 파일 존재 확인. 오류 시 문자열 반환."""
```

DB 파일 미존재 시 해당 타임프레임 run을 skip 처리.

#### Step 8.5: `tests/unit/test_cross_timeframe.py` 신규 (~130줄)

| 클래스 | 테스트 수 | 검증 내용 |
|--------|----------|----------|
| `TestExpandTimeframes` | 3 | 확장 로직, 빈 timeframes, 단일 timeframe |
| `TestCrossTimeframeBatchConfig` | 2 | JSON 로딩 + timeframes 필드 |
| `TestCrossTimeframeReport` | 3 | 페어 매칭, Markdown 렌더링, 미페어 처리 |
| `TestCrossTimeframeBatch` | 3 | mock 배치 + timeframes 확장 검증 |

### 5.5 예상 작업량

~240줄 (소스 ~110 + 테스트 ~130). 난이도 중간. 테스트 ~11개.

---

## 6. Phase 9: 조건식 진화 루프

### 6.1 목적

승격 실패 시 분석 파라미터를 **자동 변형(mutation)하여 재시도**하는 진화 루프.
수동 파라미터 튜닝 → 자동 파라미터 공간 탐색으로 전환.

### 6.2 사용 시나리오

```bash
# 기본 설정을 JSON으로 제공, 진화 루프로 파라미터 자동 탐색
python stom_backtest.py discovery evolve \
    --config base_config.json \
    --max-generations 5 \
    --population-size 4 \
    --objective tpi \
    --stagnation-limit 2 \
    --parallel 2 \
    --seed 42
```

```python
# 프로그래밍 API
result = controller.auto_discover_evolve(
    evo_config=AutoEvolutionConfig(
        base_config=my_config,
        max_generations=5,
        population_size=4,
        objective='tpi',
    ),
    parallel=2,
)
```

### 6.3 진화 알고리즘 설계

```
[세대 1] base_config에서 N개 변이 생성
    │
    ├─ 변이 1: alpha=0.07, top_n=4, ml_weight=0.2
    ├─ 변이 2: alpha=0.03, top_n=6, ml_weight=0.5
    ├─ 변이 3: alpha=0.05, top_n=3, ml_weight=0.1
    └─ 변이 4: alpha=0.09, top_n=5, ml_weight=0.4
    │
    ▼ 각 변이로 AutoDiscoveryEngine.run() 실행
    │
    ▼ 최고 결과 선택 (promoted 우선 → objective 기준)
    │
    ├─ promoted=True → 즉시 반환 (성공!)
    ├─ 개선 있음 → best 갱신, 다음 세대로
    └─ 개선 없음 → stagnation_count++
         ├─ stagnation_limit 도달 → 중단 ('stagnated')
         └─ 미도달 → 다음 세대로

[세대 2] 이전 세대 best에서 N개 변이 생성 → 반복...
```

### 6.4 변이 대상 파라미터

| 파라미터 | 기본 범위 | 변이 방식 |
|---------|----------|-----------|
| `alpha` | 0.01 ~ 0.20 | 가우시안 노이즈 + 범위 클리핑 |
| `top_n` | 1 ~ 10 | 정수 가우시안 + 범위 클리핑 |
| `min_samples` | 5 ~ 100 | 정수 가우시안 + 범위 클리핑 |
| `quantiles` | 3 ~ 20 | 정수 가우시안 + 범위 클리핑 |
| `ml_weight` | 0.0 ~ 1.0 | 가우시안 노이즈 + 범위 클리핑 |
| `ml_feature_limit` | 0 ~ 30 | 정수 가우시안 + 범위 클리핑 |

`mutation_strength` (기본 0.3)가 노이즈 크기를 제어:
`noise = rng.gauss(0, mutation_strength * (max - min))`

### 6.5 구현 상세

#### Step 9.1: `AutoEvolutionConfig` dataclass (~30줄)

```python
@dataclass
class AutoEvolutionConfig:
    base_config: AutoDiscoveryConfig       # 기본 설정 (변이의 시작점)
    max_generations: int = 5               # 최대 세대 수
    population_size: int = 4               # 세대당 변이 수
    objective: str = 'tpi'                 # 선택 기준 지표
    stagnation_limit: int = 2              # 개선 없는 세대 허용 수
    mutation_strength: float = 0.3         # 변이 강도 (0.0~1.0)
    alpha_range: tuple = (0.01, 0.20)
    top_n_range: tuple = (1, 10)
    min_samples_range: tuple = (5, 100)
    quantiles_range: tuple = (3, 20)
    ml_weight_range: tuple = (0.0, 1.0)
    ml_feature_limit_range: tuple = (0, 30)
```

#### Step 9.2: 변이/선택 함수 (~60줄)

```python
def _mutate_config(config, evo_config, rng=None) -> AutoDiscoveryConfig:
    """mutable 파라미터를 가우시안 노이즈로 변이. 범위 클리핑. 불변성 보존."""

def _select_best(results, objective) -> dict | None:
    """promoted 우선 → objective metric 기준 최고 선택."""

def _create_population(base_config, evo_config, rng=None) -> list[AutoDiscoveryConfig]:
    """population_size개의 변이 config 생성."""
```

#### Step 9.3: `auto_discover_evolve()` 메인 루프 (~80줄)

```python
def auto_discover_evolve(evo_config, controller=None, parallel=0) -> dict:
    """조건식 진화 루프 실행.

    Returns:
        {
            'status': 'ok' | 'stagnated' | 'exhausted',
            'promoted': bool,
            'best_result': dict,
            'best_config': dict,  # asdict() 형태
            'generations': [
                {'generation': int, 'population': [...], 'results': [...], 'best_objective': float},
            ],
            'total_runs': int,
            'total_duration': float,
        }
    """
```

#### Step 9.4: `discovery evolve` CLI 서브커맨드 (~70줄)

```
discovery evolve --config base.json
    --max-generations 5 --population-size 4
    --objective tpi --stagnation-limit 2
    --mutation-strength 0.3 --parallel 2 --seed 42
```

`--config`에 기존 batch JSON 형식 사용: `common` + `runs[0]`을 base_config로 변환.

#### Step 9.5: AI controller facade (~20줄)

```python
def auto_discover_evolve(self, evo_config=None, parallel=0, **kwargs) -> dict:
```

#### Step 9.6: `tests/unit/test_auto_discovery_evolve.py` 신규 (~200줄)

| 클래스 | 테스트 수 | 검증 내용 |
|--------|----------|----------|
| `TestAutoEvolutionConfig` | 2 | 기본값, 필드 존재 |
| `TestMutateConfig` | 4 | 범위 내, 불변성, seed 재현성, 다양성 |
| `TestSelectBest` | 3 | promoted 우선, objective 정렬, 빈 결과 |
| `TestCreatePopulation` | 2 | 크기 검증, base와 다름 |
| `TestAutoDiscoverEvolve` | 5 | 첫 승격 중단, stagnation, 전 세대 소진, 개선 추적, seed 재현 |
| `TestEvolveCliParsing` | 3 | arg 파싱, 기본값, 필수 인자 |

### 6.6 리스크 및 대응

| 리스크 | 심각도 | 대응 |
|--------|--------|------|
| 실행 비용 (5세대 × 4변이 = 20 파이프라인) | 중간 | stagnation_limit으로 조기 종료, parallel로 속도 향상 |
| 파라미터 범위 edge case | 낮음 | max(min, ...)로 항상 유효 범위 보장 |
| 재현성 | 낮음 | `--seed` 옵션으로 random.Random(seed) 사용 |
| 메모리 (세대별 결과 누적) | 낮음 | 결과 summary만 저장, 전체 result는 미보관 |

### 6.7 예상 작업량

~460줄 (소스 ~260 + 테스트 ~200). 난이도 높음. 테스트 ~19개.

---

## 7. 총괄 요약

### 7.1 Phase별 비교

| Phase | 기능 | 난이도 | 작업량 | 테스트 | 의존성 |
|-------|------|--------|--------|--------|--------|
| **6** | 히스토리 CLI 대시보드 | 낮음 | ~375줄 | ~15개 | 없음 |
| **7** | 배치 병렬 실행 | 중간 | ~220줄 | ~6개 | Phase 6 |
| **8** | 크로스 타임프레임 탐색 | 중간 | ~240줄 | ~11개 | Phase 7 |
| **9** | 조건식 진화 루프 | 높음 | ~460줄 | ~19개 | Phase 7 |
| **합계** | | | **~1,295줄** | **~51개** | |

### 7.2 변경 파일 총괄

| 파일 | Phase 6 | Phase 7 | Phase 8 | Phase 9 |
|------|---------|---------|---------|---------|
| `cli/table_formatter.py` | **신규** | — | — | — |
| `cli/auto_discovery.py` | — | 수정 | 수정 | 수정 |
| `cli/subcommands.py` | 수정 | 수정 | — | 수정 |
| `cli/history.py` | 수정 | — | — | — |
| `cli/ai_controller.py` | 수정 | 수정 | — | 수정 |
| `cli/discovery_report.py` | — | — | 수정 | — |
| `tests/unit/test_discovery_history_cli.py` | **신규** | — | — | — |
| `tests/unit/test_auto_discovery_batch.py` | — | 수정 | — | — |
| `tests/unit/test_cross_timeframe.py` | — | — | **신규** | — |
| `tests/unit/test_auto_discovery_evolve.py` | — | — | — | **신규** |

### 7.3 완료 후 기대 효과

| 현재 (Phase 5 완료) | Phase 9 완료 후 |
|---------------------|----------------|
| 히스토리 Python API만 | CLI에서 직접 조회/비교 |
| 배치 순차 실행 (45분) | 병렬 실행으로 15분 |
| 단일 타임프레임 | tick/min 교차 검증 |
| 승격 실패 → 수동 재조정 | 자동 파라미터 진화 탐색 |
| 656 unit tests | **~707 unit tests** |

### 7.4 검증 방법

각 Phase 완료 시:
1. `python -c "import cli.auto_discovery"` — import 성공
2. `pytest tests/unit/{해당_테스트}.py -v` — 신규 테스트 전체 pass
3. `python stom_backtest.py discovery {command} --help` — CLI 도움말 정상
4. `pytest tests/unit/ -q` — 전체 회귀 테스트 pass 유지
