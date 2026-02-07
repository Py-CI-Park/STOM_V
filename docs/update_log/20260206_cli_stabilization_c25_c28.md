# STOM CLI 안정화 작업 로그 (C2.5 ~ C2.8)

## 1. 개요
- 작업 일시: 2026-02-06
- 대상 브랜치: `STOM_Version_2U-cli-research-test`
- 목표: 코드 리뷰 보고서(`docs/reports/2026-02-06_STOM_Version_2U_cli_research_test_code_review.md`)의 개발 안내 항목(C2.5~C2.8) 실행

## 2. 단계별 수행 결과

### 2.1 C2.5 - DB 정합성/버전 단일화
- 버전 상수 단일 소스 도입: `cli/version.py`
- `cli/main.py`, `cli/__init__.py` 버전 참조 통일
- `cli/adapters/schema_adapter.py` 도입
- `data/trade/monitor/optimize/db` 명령의 DB 테이블/컬럼 매핑 정합화
- `db info --format json` 출력 구조 정비

관련 커밋:
- `92de461` STOM V2.36.U1.5.C2.5 - CLI 스키마 정합성 및 버전 단일화 안정화

### 2.2 C2.6 - 테스트 신뢰도 복구
- `tests/test_data.py`, `tests/test_trade.py`, `tests/test_monitor.py`, `tests/test_backtest.py`, `tests/test_optimize.py` 재작성
- 느슨한 assertion(`in [0,1,2]`) 제거
- 실제 CLI 옵션(`--type`) 기준으로 테스트 정렬
- legacy 옵션 거부 케이스 명시화

관련 커밋:
- `b05352f` STOM V2.36.U1.5.C2.6 - CLI 테스트 신뢰도 강화 및 옵션 정합화

### 2.3 C2.7 - Runner Hardening
- `cli/runners/backtest_runner.py`: invalid type 조기 실패(모듈 로딩 전)
- `cli/runners/trade_runner.py`: 미구현 주문 실행 경로를 명확히 비지원 처리
- 신규 테스트:
  - `tests/test_runners.py`
  - `tests/test_schema_contract.py`

관련 커밋:
- `7e02c7a` STOM V2.36.U1.5.C2.7 - 러너 안정화 및 스키마 계약 테스트 추가

### 2.4 C2.8 - AI-Ready CLI
- `OutputAdapter` 개선:
  - JSON/CSV 출력에서 title 배너 제거(파싱 안정성 확보)
  - JSON 에러 포맷(`ok`, `error.code`, `error.message`) 표준화
- 주요 명령 에러 응답에 표준 코드 적용:
  - `data`, `monitor`, `optimize`, `backtest`, `db info`
- 문서 버전/링크 동기화:
  - `docs/AGENTS.md`
  - `docs/README.md`
  - `docs/CLI_User_Manual.md`
  - `docs/change_log/change_log.md`
  - `docs/reports/2026-02-06_STOM_Version_2U_cli_research_test_code_review.md`

## 3. 검증 로그

### 3.1 핵심 테스트
```bash
python -m pytest tests/test_data.py tests/test_trade.py tests/test_monitor.py tests/test_backtest.py tests/test_optimize.py -q
```
- 결과: `70 passed`

```bash
python -m pytest tests/test_runners.py tests/test_schema_contract.py tests/test_output_formats.py tests/test_data.py tests/test_monitor.py tests/test_optimize.py tests/test_backtest.py -q
```
- 결과: `95 passed, 1 skipped`

### 3.2 버전 및 명령 스모크
```bash
python -m cli.main --version
python -m cli.main db info --type strategy --format json
python -m cli.main data backtest-list --format json
python -m cli.main optimize list --format json
```
- 결과: 실행/출력 정상

## 4. 후속 권장 작업
1. `trade.py` 인코딩 깨짐 주석/문자열 정리(기능 영향은 없으나 유지보수성 저하 요인)
2. 러너 계층 통합 테스트를 CI 기본 파이프라인에 포함
3. JSON 출력 스키마를 문서화(`docs/CLI_User_Manual.md`에 명시적 계약 표 추가)

## 5. 후속 진행 상태 (같은 날짜 추가 반영)

### 5.1 완료 항목
1. `trade.py` 인코딩 깨짐 정리 완료
2. 러너/스키마 테스트 CI 필수 게이트 추가 완료
3. JSON 응답 계약 문서화 완료

### 5.2 반영 파일
- `cli/commands/trade.py`
- `.github/workflows/cli-tests.yml`
- `docs/CLI_User_Manual.md`

### 5.3 검증 결과
- `python -m pytest tests/test_trade.py tests/test_cli_basic.py -q` → `38 passed`
- `python -m cli.main positions list --format json` → `{"message": ...}` 구조 확인
- `python -m cli.main orders list --format json` → `{"message": ...}` 구조 확인
- `python -m cli.main trade status --format json` → 객체 구조 출력 확인

### 5.4 다음 권장 단계
1. `tests/test_trade.py`에 `positions/orders` JSON 구조 검증 케이스 추가
2. coverage job에 러너/스키마 전용 리포트 아티팩트 분리
3. JSON 스키마를 독립 문서(`docs/reports/*` 또는 `docs/contracts/*`)로 승격

## 6. C2.10 진행 상태 (추가 후속 실행)

### 6.1 완료 항목
1. `tests/test_trade.py` JSON 구조 검증 케이스 추가 완료
2. coverage job 러너/스키마 리포트 아티팩트 분리 완료
3. JSON 스키마 독립 문서 분리 완료 (`docs/contracts/CLI_JSON_Contract.md`)

### 6.2 반영 파일
- `tests/test_trade.py`
- `.github/workflows/cli-tests.yml`
- `docs/contracts/CLI_JSON_Contract.md`
- `docs/README.md`
- `docs/CLI_User_Manual.md`

### 6.3 확인 결과
- `python -m pytest tests/test_trade.py -q` 통과
- `python -m pytest tests/ -q --tb=short` 통과
- `python -m cli.main --version` 결과: `STOM, version 2.36.U1.5.C2.10`

## 7. C2.11 진행 상태 (추가 후속 실행)

### 7.1 완료 항목
1. `positions close`/`orders cancel` 실패 JSON 에러코드 계약 테스트 추가 완료
2. runner/schema 커버리지 하한선(`--cov-fail-under=35`) 적용 완료
3. JSON 계약 문서에 명령별 샘플/테스트 링크 표 추가 완료

### 7.2 반영 파일
- `cli/commands/trade.py`
- `tests/test_trade.py`
- `.github/workflows/cli-tests.yml`
- `docs/contracts/CLI_JSON_Contract.md`

### 7.3 확인 결과
- `python -m pytest tests/test_trade.py -q` 통과
- `python -m pytest tests/ -q --tb=short` 통과
- `python -m cli.main --version` 결과: `STOM, version 2.36.U1.5.C2.11`

## 8. C2.12 진행 상태 (추가 후속 실행)

### 8.1 완료 항목
1. `positions close --all`/`orders cancel --all` 성공 JSON payload 계약 테스트 추가 완료
2. jsonschema 기반 JSON 계약 자동검증 테스트 도입 완료
3. 전체 CLI coverage 하한선(`--cov-fail-under=50`) 적용 완료

### 8.2 반영 파일
- `tests/test_trade.py`
- `tests/test_json_contract_schema.py`
- `.github/workflows/cli-tests.yml`
- `requirements-test.txt`

### 8.3 확인 결과
- `python -m pytest tests/test_trade.py tests/test_json_contract_schema.py -q` 통과
- `python -m pytest tests/ -q --tb=short` 통과
- `python -m pytest tests/ -q --cov=cli --cov-report=term-missing --cov-fail-under=50` 통과
- `python -m cli.main --version` 결과: `STOM, version 2.36.U1.5.C2.12`

## 9. C2.13 진행 상태 (문서 권장 다음 단계 실행)

### 9.1 완료 항목
1. `backtest/optimize list/status` JSON schema 검증 확장 완료
2. 상태 조회 미존재 ID(`unknown_job_id`) 메시지 계약 검증 완료
3. 상태 조회 성공 스키마 검증을 DB 최신 ID 기반으로 안정화(쓰기 충돌 방지) 완료

### 9.2 반영 파일
- `tests/test_json_contract_schema.py`
- `docs/contracts/CLI_JSON_Contract.md`
- `docs/reports/2026-02-06_STOM_Version_2U_cli_research_test_code_review.md`

### 9.3 확인 결과
- `python -m pytest tests/test_json_contract_schema.py -q --tb=short` 통과
- `python -m pytest tests/ -q --cov=cli --cov-report=term-missing --cov-fail-under=50 --tb=short` 통과
- 결과: `234 passed, 1 skipped`, 커버리지 약 `54.67%`
- `python -m cli.main --version` 결과: `STOM, version 2.36.U1.5.C2.13`

## 10. C2.14 진행 상태 (커버리지 하한선 상향)

### 10.1 완료 항목
1. CI 전체 커버리지 하한선 `50 -> 55` 상향 완료
2. optimize 상태/목록/취소 성공 경로 테스트 3건 추가 완료
3. 신규 하한선 기준 전체 테스트 검증 완료

### 10.2 반영 파일
- `.github/workflows/cli-tests.yml`
- `tests/test_optimize.py`

### 10.3 확인 결과
- `python -m pytest tests/test_optimize.py -q --tb=short` 통과
- `python -m pytest tests/ -q --cov=cli --cov-report=term-missing --cov-fail-under=55 --tb=short` 통과
- 결과: `237 passed, 1 skipped`, 커버리지 약 `55.08%`
- `python -m cli.main --version` 결과: `STOM, version 2.36.U1.5.C2.14`

## 11. C2.15 진행 상태 (계약 변경 이력 관리 체계)

### 11.1 완료 항목
1. `docs/contracts/CLI_JSON_Contract.md`에 명령별 계약 변경 이력 표 추가 완료
2. 계약 변경 운영 규칙(이력 등록/호환성 표기/테스트 링크) 추가 완료
3. 계약 문서 내 CI coverage 기준 수치(55) 동기화 완료

### 11.2 반영 파일
- `docs/contracts/CLI_JSON_Contract.md`
- `docs/reports/2026-02-06_STOM_Version_2U_cli_research_test_code_review.md`

### 11.3 확인 결과
- `python -m cli.main --version` 결과: `STOM, version 2.36.U1.5.C2.15`
