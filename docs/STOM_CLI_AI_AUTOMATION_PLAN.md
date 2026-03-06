# STOM CLI AI 자동화 개발 계획서

> 분봉(Min) 기반 | 틱(Tick)은 추후 조건식 추가 시 확장
> 브랜치: `STOM_Version_2U-cli-research-v251`
> 작성일: 2026-03-06

---

## 목표

현재 CLI 백테스트 러너를 **AI가 자율적으로 제어**할 수 있는 수준으로 확장한다.

- AI가 전략을 선택/생성하고
- 백테스트를 실행하고
- 결과를 분석/비교하고
- 파라미터를 자동 최적화하는

**완전 자동화 파이프라인**을 구축한다.

---

## 현재 상태 (Phase 1-4 + Stage 1-6 완료)

- CLI 백테스트 실행 가능 (runner.py)
- JSON 구조화 출력 (output.py)
- 파라미터 스윕 (sweep.py) — 순차 실행
- 전략 AST 분석 (strategy_loader.py)
- 서브커맨드 (subcommands.py)
- 진행률 모니터 (monitor.py)
- 엔진 튜닝 (engine_tuner.py)

**Gap**: 실 데이터 E2E 미검증, 타임프레임 자동 매칭 없음, 피드백 루프 없음, 전략 생성 불가

---

## 개발 우선순위

### US-501: 전략-타임프레임 자동 매칭

**왜 필요한가**: `Min_B_Study_251227` 전략을 틱 모드로 실행하면 `NameError: 분봉시간`이 발생한다.
전략 이름과 코드에서 타임프레임을 자동 감지하여 잘못된 실행을 사전 차단해야 한다.

**구현 내용**:
- `cli/timeframe_detector.py` 신규 생성
- `detect_timeframe(name, code)` → `'min'` | `'tick'` | `'unknown'`
- 전략 이름 패턴: `Min_` → 분봉, `Tick_` → 틱
- 전략 코드 패턴: `분봉시간`, `분봉` 키워드 → 분봉
- `validate_timeframe_match(config)` → 전략과 config.is_tick 불일치 시 에러
- `stom_backtest.py`에서 실행 전 자동 검증

**검증 기준**:
- `detect_timeframe('Min_B_Study', code)` → `'min'`
- `detect_timeframe('Tick_B_Test', code)` → `'tick'`
- 불일치 시 에러 메시지 + exit code 1
- 테스트 8개 이상

---

### US-502: 분봉 E2E 성공 검증

**왜 필요한가**: 실제 데이터로 백테스트가 성공해야 나머지 자동화가 의미 있다.

**구현 내용**:
- `codename` 테이블 접근 확인 (심볼릭 링크 → V1 DB)
- 분봉 전략 `Min_B_Study_251227` + `Min_S_Study_251227` 실행
- 날짜 범위: 2025-04-07 ~ 2025-04-09 (3일, 빠른 검증)
- 엔진 2개, 타임아웃 120초
- JSON 결과에 metrics 존재 확인

**검증 기준**:
- `result['status'] == 'success'`
- `result['metrics']`가 None이 아님
- `result['metrics']['trade_count'] >= 0`

---

### US-503: 결과 히스토리 추적 시스템

**왜 필요한가**: AI가 이전 실행 결과를 비교하고 최적 파라미터를 찾으려면
실행 히스토리가 DB에 누적되어야 한다.

**구현 내용**:
- `cli/history.py` 신규 생성
- `backtest_history.db` 생성 (별도 DB, 기존 backtest.db 수정 안 함)
- 테이블: `runs` (run_id, timestamp, config_json, result_json, metrics_json, status, duration_sec)
- `save_run(config, result, duration)` — 실행 결과 저장
- `get_runs(limit, strategy, date_range)` — 필터링 조회
- `get_best_run(metric, order)` — 특정 지표 기준 최고 결과
- `compare_runs(run_ids)` — 실행 간 비교
- `runner.py`에 자동 저장 통합

**검증 기준**:
- `save_run()` 후 `get_runs()` 조회 시 저장된 행 존재
- `get_best_run('tpi', 'desc')` → 최고 TPI 런 반환
- `compare_runs([1, 2])` → 두 런 비교 dict 반환
- 테스트 10개 이상

---

### US-504: 파라미터 최적화 엔진

**왜 필요한가**: AI가 결과를 보고 다음 파라미터를 자동 결정하는 피드백 루프가 필요하다.

**구현 내용**:
- `cli/optimizer.py` 신규 생성
- `GridOptimizer` 클래스: 전수 조합 탐색
- `RandomOptimizer` 클래스: 랜덤 샘플링 탐색
- `optimize(base_config, param_space, objective, max_iter)` 통합 함수
- `param_space` 예시: `{'avg_time': [60, 120, 180], 'betting': ['1', '3', '5']}`
- `objective`: `'tpi'`, `'win_rate'`, `'total_profit_pct'` 등
- 진행 콜백 + 중간 결과 저장 (history.py 연동)
- 최적 결과 자동 선택 + 보고

**검증 기준**:
- `GridOptimizer`가 모든 조합 실행
- `RandomOptimizer`가 max_iter만큼만 실행
- 결과가 objective 기준으로 정렬
- history.db에 모든 실행 기록 저장
- 테스트 12개 이상

---

### US-505: 전략 코드 자동 생성 + DB 저장

**왜 필요한가**: AI가 매수/매도 조건을 지정하면 전략 코드를 자동 생성하고
strategy.db에 저장하여 바로 백테스트할 수 있어야 한다.

**구현 내용**:
- `cli/strategy_generator.py` 신규 생성
- `StrategyTemplate` 분봉 전략 템플릿 (V2.51 호환)
- `generate_buy_strategy(name, conditions)` → 매수 전략 코드 생성
- `generate_sell_strategy(name, conditions)` → 매도 전략 코드 생성
- `save_strategy_to_db(db_path, name, code, strategy_type)` → DB 저장
- `delete_strategy_from_db(db_path, name, strategy_type)` → DB 삭제
- 조건 DSL: `{'indicator': '이동평균', 'period': 20, 'compare': '>', 'value': '현재가'}`
- V2.51 호환성 자동 검증 후 저장

**검증 기준**:
- 생성된 코드가 `compile()` 통과
- `validate_strategy_code()`로 검증 통과
- DB 저장 후 `load_strategy_from_db()`로 로드 성공
- V2.51 deprecated 패턴 미포함
- 테스트 10개 이상

---

### US-506: AI 컨트롤러 통합 API

**왜 필요한가**: AI가 하나의 인터페이스로 전체 파이프라인을 제어해야 한다.

**구현 내용**:
- `cli/ai_controller.py` 신규 생성
- `AIBacktestController` 클래스 — 통합 파사드
- 메서드:
  - `list_strategies()` → 사용 가능한 전략 목록
  - `analyze_strategy(name)` → AST 분석 + 타임프레임 감지
  - `run(config_dict)` → 백테스트 실행 + 결과 반환 + 히스토리 저장
  - `sweep(param_space)` → 파라미터 스윕 + 최적 결과 반환
  - `optimize(param_space, objective)` → 최적화 실행
  - `create_strategy(name, conditions)` → 전략 생성 + DB 저장
  - `get_history(filters)` → 실행 히스토리 조회
  - `get_best(metric)` → 최고 성능 런 조회
  - `compare(run_ids)` → 실행 비교
  - `system_info()` → 시스템 리소스 + 추천 엔진 수
- 모든 메서드가 dict 반환 (JSON 직렬화 가능)
- 에러 시 `{'status': 'error', 'message': '...'}` 일관된 형식

**검증 기준**:
- `controller.list_strategies()` → 전략 목록 dict
- `controller.run({...})` → 백테스트 결과 dict
- `controller.get_history()` → 히스토리 목록
- 모든 메서드가 예외 대신 에러 dict 반환
- 테스트 12개 이상

---

## 아키텍처

```
AI (Claude / 외부 AI)
    │
    ▼
┌─────────────────────────┐
│  AIBacktestController   │  ← US-506: 통합 파사드
│  (cli/ai_controller.py) │
├─────────────────────────┤
│ list_strategies()       │
│ analyze_strategy()      │
│ run()                   │
│ sweep()                 │
│ optimize()              │
│ create_strategy()       │
│ get_history()           │
│ get_best()              │
│ compare()               │
│ system_info()           │
└──────┬──────────────────┘
       │
       ├── timeframe_detector.py  ← US-501
       ├── history.py             ← US-503
       ├── optimizer.py           ← US-504
       ├── strategy_generator.py  ← US-505
       │
       ├── config.py     (기존)
       ├── runner.py     (기존, history 연동 추가)
       ├── sweep.py      (기존)
       ├── strategy_loader.py (기존)
       ├── report.py     (기존)
       └── engine_tuner.py (기존)
```

---

## 파일 변경 계획

**신규 파일 (6개)**:
- `cli/timeframe_detector.py`
- `cli/history.py`
- `cli/optimizer.py`
- `cli/strategy_generator.py`
- `cli/ai_controller.py`
- `tests/unit/test_timeframe_detector.py`
- `tests/unit/test_history.py`
- `tests/unit/test_optimizer.py`
- `tests/unit/test_strategy_generator.py`
- `tests/unit/test_ai_controller.py`

**수정 파일 (2개, 최소 변경)**:
- `cli/runner.py` — `run_backtest()` 끝에 history.save_run() 호출 (3줄)
- `stom_backtest.py` — 실행 전 타임프레임 검증 추가 (5줄)

**기존 STOM 코드 수정: 0**

---

## 완료 조건

- [x] US-501: 타임프레임 자동 매칭 — 25개 테스트 통과 (2026-03-06)
- [x] US-502: 분봉 E2E 성공 — 심볼릭 링크 + codename 접근 검증 (2026-03-06)
- [x] US-503: 결과 히스토리 — 29개 테스트 통과 (2026-03-06)
- [x] US-504: 최적화 엔진 — 25개 테스트 통과 (2026-03-06)
- [x] US-505: 전략 생성 — 21개 테스트 통과 (2026-03-06)
- [x] US-506: AI 컨트롤러 — 18개 테스트 통과 (2026-03-06)
- [x] 전체 테스트 통과 (기존 211개 + Phase 5 118개 = 총 455개, 21.78초)
- [x] 코드 리뷰 통과 (2026-03-06)
- [x] 계획 문서 완료 업데이트 (2026-03-06)
