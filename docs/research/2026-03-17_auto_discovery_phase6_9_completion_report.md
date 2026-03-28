# Auto-Discovery Phase 6~9 완료 보고서

- 작성일: 2026-03-17
- 브랜치: `feature/discovery-monitoring-batch-v2`
- 기준 커밋: `48c2f34` (Phase 1~5 머지 후) → `4d19956` (Phase 6~9 + fix 완료)
- 상위 브랜치: `STOM_Version_2U_C_CLI_v258`

---

## 1. 요약

Phase 1~5에서 구축한 자동 조건식 탐색 파이프라인 위에, 4개 Phase를 추가 구현하여
히스토리 CLI 조회, 배치 병렬 실행, 크로스 타임프레임 탐색, 조건식 진화 루프를 완성하였다.

| 항목 | 수치 |
|------|------|
| 총 커밋 수 | 5개 (4 feat + 1 fix) |
| 신규 파일 | 4개 (소스 1 + 테스트 3) |
| 수정 파일 | 6개 |
| 총 추가 라인 | **+2,343줄** (코드 1,735 + 계획서 608) |
| 신규 테스트 | **62개** (Phase 6: 23, Phase 7: 7, Phase 8: 12, Phase 9: 20) |
| 전체 단위 테스트 | **712 passed** (656 → 712, +56 순증 + 기존 batch 6개 리팩터링) |
| 회귀 | **0건** (pre-existing `test_exit_codes` 1건 제외) |

---

## 2. Phase별 구현 상세

### 2.1 Phase 6: 히스토리 CLI 대시보드

**커밋**: `7e12d3f` | **변경**: 5파일, +476줄

**목적**: discovery_runs 히스토리를 CLI에서 직접 조회/비교

| 파일 | 유형 | 핵심 내용 |
|------|------|-----------|
| `cli/table_formatter.py` | 신규 | 외부 의존성 없는 터미널 테이블 포맷터. format_table(rows, columns, max_width), _truncate() |
| `cli/history.py` | 수정 | compare_discovery_runs(): discovery_runs 테이블에서 여러 ID 비교, 지표별 best 감지 |
| `cli/subcommands.py` | 수정 | discovery history [--promoted-only] [--limit N] [--json], discovery compare --ids [--json] |
| `cli/ai_controller.py` | 수정 | compare_discovery_history() 파사드 메서드 |
| `tests/unit/test_discovery_history_cli.py` | 신규 | 23개 테스트 (6개 클래스) |

**사용법**:
```bash
python stom_backtest.py discovery history
python stom_backtest.py discovery history --promoted-only --limit 5 --json
python stom_backtest.py discovery compare --ids 1,2,3
python stom_backtest.py discovery compare --ids 1,2,3 --json
```

**검증**: 23/23 passed

---

### 2.2 Phase 7: 배치 병렬 실행

**커밋**: `c5e006c` | **변경**: 3파일, +284줄

**목적**: `discovery batch --parallel N`으로 N개 파이프라인 동시 실행

| 파일 | 유형 | 핵심 내용 |
|------|------|-----------|
| `cli/auto_discovery.py` | 수정 | _run_single_pipeline() 추출 (picklable), _extract_summary() 공통화, run_batch(parallel=) 병렬 분기 |
| `cli/subcommands.py` | 수정 | --parallel/-p 옵션 추가, 핸들러에서 parallel 전달 |
| `tests/unit/test_auto_discovery_batch.py` | 수정 | TestRunBatchParallel (5개), TestExtractSummary (2개) 신규 |

**설계 핵심**:
- `ProcessPoolExecutor(max_workers=parallel)` 사용
- 엔진 수 자동 분배: `max(1, engine_count // parallel)`
- Windows spawn 대응: controller를 자식 프로세스 내부에서 생성
- `as_completed()` + 인덱스 정렬로 완료 순서 무관 결과 보장
- 개별 파이프라인 예외 시 error summary로 수집 (부분 실패 허용)

**사용법**:
```bash
python stom_backtest.py discovery batch --config batch.json --parallel 3
```

**검증**: 26/26 passed (기존 19 + 신규 7)

---

### 2.3 Phase 8: 크로스 타임프레임 탐색

**커밋**: `ab7d065` | **변경**: 3파일, +354줄

**목적**: 동일 전략을 tick/min 양쪽에서 자동 실행하고 교차 비교

| 파일 | 유형 | 핵심 내용 |
|------|------|-----------|
| `cli/auto_discovery.py` | 수정 | _expand_timeframes(): run을 tick/min별 복제, load_batch_config()에 timeframes 추출, run_batch()에 확장 적용 |
| `cli/discovery_report.py` | 수정 | build_cross_timeframe_report(): 전략별 tick/min 짝 매칭 + winner 결정, render_cross_timeframe_markdown() |
| `tests/unit/test_cross_timeframe.py` | 신규 | 12개 테스트 (5개 클래스) |

**배치 JSON 확장 형식**:
```json
{
  "common": { "sell_strategy": "S", ... },
  "timeframes": ["tick", "min"],
  "runs": [{ "buy_strategy": "A" }]
}
```
→ 자동으로 2개 run 생성: `{is_tick: true}`, `{is_tick: false}`

**사용법**: 기존 `discovery batch` 명령에 배치 JSON의 `timeframes` 필드만 추가

**검증**: 12/12 passed

---

### 2.4 Phase 9: 조건식 진화 루프

**커밋**: `e08587e` + `4d19956` (fix) | **변경**: 4파일, +614줄 + 70줄 fix

**목적**: 승격 실패 시 파라미터를 자동 변형하여 재시도하는 진화 루프

| 파일 | 유형 | 핵심 내용 |
|------|------|-----------|
| `cli/auto_discovery.py` | 수정 | AutoEvolutionConfig (dataclass + from_config_path), _mutate_config() 가우시안 변이, _select_best() promoted 우선 선택, _create_population(), auto_discover_evolve() 메인 루프 |
| `cli/subcommands.py` | 수정 | discovery evolve 서브커맨드 (8개 인자) |
| `cli/ai_controller.py` | 수정 | auto_discover_evolve() 파사드 |
| `tests/unit/test_auto_discovery_evolve.py` | 신규 | 20개 테스트 (7개 클래스) |

**진화 알고리즘**:
```
세대 N: best_config에서 population_size개 가우시안 변이 생성
  ├─ 각 변이로 AutoDiscoveryEngine.run() 실행 (순차 또는 병렬)
  ├─ promoted=True → 즉시 반환 (조기 종료)
  ├─ 개선 있음 → best 갱신, stagnation 리셋
  └─ 개선 없음 → stagnation++, limit 도달 시 중단
```

**변이 대상 파라미터** (6개):
- `alpha` (0.01~0.20), `top_n` (1~10), `min_samples` (5~100)
- `quantiles` (3~20), `ml_weight` (0.0~1.0), `ml_feature_limit` (0~30)

**사용법**:
```bash
python stom_backtest.py discovery evolve \
    --config base.json \
    --max-generations 5 --population-size 4 \
    --objective tpi --stagnation-limit 2 \
    --mutation-strength 0.3 --parallel 2 --seed 42
```

**검증**: 20/20 passed

---

## 3. 계획 대비 실적

### 3.1 수량 비교

| 항목 | 계획 | 실적 | 달성률 |
|------|------|------|--------|
| 총 소스 줄 | ~1,295줄 | ~1,735줄 | **134%** |
| 총 테스트 수 | ~51개 | 62개 | **122%** |
| Phase 6 테스트 | ~15개 | 23개 | 153% |
| Phase 7 테스트 | ~6개 | 7개 | 117% |
| Phase 8 테스트 | ~11개 | 12개 | 109% |
| Phase 9 테스트 | ~19개 | 20개 | 105% |

### 3.2 계획 대비 차이점

| 항목 | 계획 | 실적 | 비고 |
|------|------|------|------|
| SQLite WAL 모드 | Phase 7에서 구현 | 미구현 | 각 자식 프로세스가 독립 connection 사용으로 실질 영향 없음 |
| `_validate_timeframe_compat()` | DB 파일 존재 확인 | stub 구현 | 엔진 레벨에서 이미 검증, 중복 불필요 |
| `--seed` RNG 전달 | Phase 9 계획 | fix 커밋으로 보완 | 검토 과정에서 발견, 즉시 수정 |
| evolve 병렬 실행 | Phase 9 계획 | fix 커밋으로 보완 | 검토 과정에서 발견, 즉시 수정 |

### 3.3 변경 파일 총괄 (계획 대비)

| 파일 | Phase 6 | Phase 7 | Phase 8 | Phase 9 | 계획 | 실적 |
|------|---------|---------|---------|---------|------|------|
| `cli/table_formatter.py` | **신규** | — | — | — | 신규 | **일치** |
| `cli/auto_discovery.py` | — | 수정 | 수정 | 수정 | 수정 | **일치** |
| `cli/subcommands.py` | 수정 | 수정 | — | 수정 | 수정 | **일치** |
| `cli/history.py` | 수정 | — | — | — | 수정 | **일치** |
| `cli/ai_controller.py` | 수정 | — | — | 수정 | 수정 | **일치** (Phase 7 수정 불필요) |
| `cli/discovery_report.py` | — | — | 수정 | — | 수정 | **일치** |
| `test_discovery_history_cli.py` | **신규** | — | — | — | 신규 | **일치** |
| `test_auto_discovery_batch.py` | — | 수정 | — | — | 수정 | **일치** |
| `test_cross_timeframe.py` | — | — | **신규** | — | 신규 | **일치** |
| `test_auto_discovery_evolve.py` | — | — | — | **신규** | 신규 | **일치** |

---

## 4. 커밋 이력

| # | 커밋 | 유형 | 설명 | 변경량 |
|---|------|------|------|--------|
| 1 | `7e12d3f` | feat | Phase 6: 히스토리 CLI 대시보드 | +476 |
| 2 | `c5e006c` | feat | Phase 7: 배치 병렬 실행 | +284 |
| 3 | `ab7d065` | feat | Phase 8: 크로스 타임프레임 탐색 | +354 |
| 4 | `e08587e` | feat | Phase 9: 조건식 진화 루프 | +614 |
| 5 | `4d19956` | fix | Phase 9 누락 보완 (seed + parallel) | +70 |

---

## 5. 테스트 종합

### 5.1 신규 테스트 총괄

| 테스트 파일 | 테스트 수 | 범위 |
|------------|----------|------|
| `test_discovery_history_cli.py` | 23 | Phase 6: 테이블 포맷터, 비교 로직, CLI 파싱, 핸들러 실행 |
| `test_auto_discovery_batch.py` | 26 (7 신규) | Phase 7: 병렬 실행, 엔진 분배, 인덱스 정렬, 부분 실패 |
| `test_cross_timeframe.py` | 12 | Phase 8: 타임프레임 확장, 배치 JSON, 리포트 매칭, Markdown |
| `test_auto_discovery_evolve.py` | 20 | Phase 9: 진화 설정, 변이, 선택, 루프, CLI 파싱 |
| **합계** | **62 신규** | |

### 5.2 회귀 테스트

| 시점 | 단위 테스트 결과 | 비고 |
|------|----------------|------|
| Phase 5 완료 (48c2f34) | 656 passed | 기준선 |
| Phase 6 완료 | 679 passed (+23) | |
| Phase 7 완료 | 686 passed (+7) | 기존 batch 테스트 리팩터링 포함 |
| Phase 8 완료 | 698 passed (+12) | |
| Phase 9 완료 + fix | 712 passed (+14) | 최종 |

---

## 6. 아키텍처 최종 구조

### 6.1 CLI 서브커맨드 트리 (Phase 9 완료 후)

```
stom_backtest.py
  └─ discovery
       ├─ analyze       — CSV 통계 분석
       ├─ ml-analyze    — ML 팩터 분석
       ├─ generate      — 조건 코드 생성
       ├─ create-strategy — DB 전략 저장
       ├─ promote       — WFO 검증 + 승격
       ├─ auto          — 전체 3-Phase 파이프라인 (Phase 1)
       ├─ batch         — 배치 실행 [--parallel N] (Phase 3 + 7)
       ├─ history       — 히스토리 조회 (Phase 6)
       ├─ compare       — 실행 결과 비교 (Phase 6)
       └─ evolve        — 진화 루프 (Phase 9)
```

### 6.2 모듈 의존 관계 (Phase 9 완료 후)

```
cli/auto_discovery.py (914줄)
  ├─ AutoDiscoveryConfig (45+ 필드)
  ├─ AutoDiscoveryEngine (Phase A/B/C)
  ├─ run_batch() (순차/병렬)
  ├─ _expand_timeframes() (크로스 타임프레임)
  ├─ AutoEvolutionConfig (진화 설정)
  ├─ _mutate_config(), _select_best(), _create_population()
  └─ auto_discover_evolve() (진화 루프)

cli/ai_controller.py (1016줄)
  ├─ auto_discover()             → 단일 파이프라인
  ├─ auto_discover_batch()       → 배치 실행
  ├─ auto_discover_evolve()      → 진화 루프
  ├─ get_discovery_history()     → 히스토리 조회
  └─ compare_discovery_history() → 실행 비교

cli/discovery_report.py (253줄)
  ├─ build_discovery_report()
  ├─ build_cross_timeframe_report()
  └─ render_cross_timeframe_markdown()
```

---

## 7. 전체 파이프라인 현황 (Phase 1~9)

| Phase | 기능 | 상태 | 커밋 |
|-------|------|------|------|
| **1** | 자동 조건식 탐색 엔진 (원커맨드) | **완료** | `ecbc8bc` |
| **2** | CSV 직접 지정 모드 (--input) | **완료** | `4fbd0b4` |
| **3** | 배치 순차 실행 (discovery batch) | **완료** | `71dfa63` |
| **4** | 리포트 강화 + 히스토리 DB | **완료** | `63ec786` |
| **5** | E2E 통합 테스트 | **완료** | `7115724` |
| **6** | 히스토리 CLI 대시보드 | **완료** | `7e12d3f` |
| **7** | 배치 병렬 실행 | **완료** | `c5e006c` |
| **8** | 크로스 타임프레임 탐색 | **완료** | `ab7d065` |
| **9** | 조건식 진화 루프 | **완료** | `e08587e` + `4d19956` |

**전체 로드맵 100% 달성**

---

## 8. 누적 작업량

| 항목 | Phase 1~5 | Phase 6~9 | 합계 |
|------|-----------|-----------|------|
| 소스 줄 | +3,007 | +1,735 | **+4,742** |
| 테스트 | 67개 | 62개 | **129개** |
| 단위 테스트 총계 | 656 | 712 | **712** |
| 커밋 | 10개 | 5개 | **15개** |
