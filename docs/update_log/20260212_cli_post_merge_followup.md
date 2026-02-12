# STOM CLI 머지 후 후속 개발 로그 (2026-02-12)

## 1. 개요
- 작업 브랜치: `STOM_Version_2U-cli-research-dev-update-20260212`
- 기준 문서: `docs/reports/2026-02-06_STOM_Version_2U_cli_research_test_code_review.md` (28.5 후속 권장)
- 목표: 머지 후 잔여 P0/P1 과제(실적재/동기실행/계약 경계/필수 게이트) 실행

## 2. 단계별 수행

### 2.1 1단계 - `db append` 실적재 구현
- 반영 파일:
  - `cli/commands/db.py`
  - `tests/test_db.py`
- 주요 반영:
  - `--apply` 실적재 모드 도입(기본 dry-run 유지)
  - `csv/json/jsonl/parquet` 소스 지원 + 디렉터리 재귀 수집
  - 날짜 필터(`YYYYMMDD`) + 테이블 자동 생성/컬럼 확장
  - row hash(`sha256`) 기반 `INSERT OR IGNORE` 중복 방지
- 검증:
  - `python -m py_compile cli/commands/db.py`
  - `python -m pytest tests/test_db.py -q --tb=short` -> `33 passed`
- 커밋: `4ce55a3`

### 2.2 2단계 - optimize 동기 실행 연동
- 반영 파일:
  - `cli/commands/optimize.py`
  - `tests/test_optimize.py`
- 주요 반영:
  - `grid/bayesian/ga/walkforward/backfinder` 동기 실행 러너 연동
  - 상태 전이(`pending -> running -> completed/failed`) 기록
  - JSON 실패 에러코드(`OPT_*_SYNC_FAILED`) 표준화
  - `bayesian` 예외 처리 중복 정리
- 검증:
  - `python -m py_compile cli/commands/optimize.py`
  - `python -m pytest tests/test_optimize.py -q --tb=short` -> `26 passed`
  - `python -m pytest tests/test_json_contract_schema.py -q --tb=short` -> `22 passed`
- 커밋: `9dbae7b`

### 2.3 3단계 - trade close/cancel 계약 경계 명확화
- 반영 파일:
  - `cli/commands/trade.py`
  - `tests/test_trade.py`
  - `tests/test_json_contract_schema.py`
  - `docs/contracts/CLI_JSON_Contract.md`
- 주요 반영:
  - 성공 payload 확장(`request_id`, `created_at`, `execution_mode`, `broker_execution`, `requires_external_executor`)
  - CLI 출력/로그에 “요청 기록 전용, 실주문 미실행” 경계 명시
  - 계약 문서/스키마 자동검증 동기화
- 검증:
  - `python -m py_compile cli/commands/trade.py cli/runners/trade_runner.py`
  - `python -m pytest tests/test_trade.py -q --tb=short` -> `26 passed`
  - `python -m pytest tests/test_json_contract_schema.py -q --tb=short` -> `22 passed`
- 커밋: `64254ba`

### 2.4 4단계 - trade runner 경계 테스트 보강
- 반영 파일:
  - `tests/test_runners.py`
- 주요 반영:
  - `close_all/cancel_all` 미구현 경계(False 반환) 검증
  - 포지션 키 컬럼 누락/주문 ID 컬럼 누락 분기 검증
- 검증:
  - `python -m pytest tests/test_runners.py -q --tb=short` -> `17 passed`
  - `python -m pytest tests/test_runners.py tests/test_schema_contract.py -q --tb=short` -> `22 passed`
- 커밋: `7cb79c6`

### 2.5 5단계 - CI required gate 강화 + 문서 동기화
- 반영 파일:
  - `.github/workflows/cli-tests.yml`
  - `docs/reports/2026-02-06_STOM_Version_2U_cli_research_test_code_review.md`
  - `docs/change_log/change_log.md`
  - `docs/update_log/20260212_cli_post_merge_followup.md`
- 주요 반영:
  - `contract-gate` job 신규 추가
  - contract/schema/runner 스위트를 필수 게이트로 승격
  - 보고서/변경이력/업데이트 로그 동기화

## 3. 통합 검증
```bash
python -m pytest tests/test_db.py tests/test_optimize.py tests/test_trade.py tests/test_runners.py tests/test_json_contract_schema.py -q --tb=short
```
- 결과: `124 passed`

## 4. 남은 과제
1. `trade_runner` 실브로커 close/cancel 연동 또는 별도 실행기 분리
2. lint soft-fail 단계의 점진 hard-gate 전환(범위 기반)
3. CI 매트릭스 실행 시간 최적화

## 5. 운영 가이드
1. `db append`는 dry-run 확인 후 `--apply`를 사용한다.
2. optimize는 즉시 결과가 필요하면 동기, 배치/대량 작업은 `--async`를 사용한다.
3. `positions close`/`orders cancel`는 `execution_mode`를 확인해 요청기록 전용 응답인지 판별한다.
