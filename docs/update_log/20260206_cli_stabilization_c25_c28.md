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

## 12. C2.16 진행 상태 (run 계약 분리 및 검증 강화)

### 12.1 완료 항목
1. `backtest run`, `optimize grid run` 성공 payload를 run 전용 스키마로 분리 완료
2. run 성공 jsonschema 검증 테스트 2건 추가 완료
3. backtest/optimize job ID 생성 포맷 마이크로초 단위 확장 완료

### 12.2 반영 파일
- `tests/test_json_contract_schema.py`
- `cli/commands/backtest.py`
- `cli/commands/optimize.py`
- `docs/contracts/CLI_JSON_Contract.md`

### 12.3 확인 결과
- `python -m pytest tests/test_json_contract_schema.py tests/test_optimize.py tests/test_backtest.py -q --tb=short` 통과
- `python -m pytest tests/ -q --cov=cli --cov-report=term-missing --cov-fail-under=55 --tb=short` 통과
- 결과: `239 passed, 1 skipped`, 커버리지 약 `55.08%`
- `python -m cli.main --version` 결과: `STOM, version 2.36.U1.5.C2.16`

## 13. C2.17 진행 상태 (run 실패 계약 확장)

### 13.1 완료 항목
1. run 실패 계약(json 파라미터 오류/DB 오류) jsonschema 검증 추가 완료
2. JSON 모드 실패 시 단일 JSON payload만 출력하도록 종료 경로 정리 완료
3. 실패 에러코드 계약 문서화(`BACKTEST_RUN_FAILED`, `OPT_GRID_INVALID_PARAMS`, `OPT_GRID_FAILED`) 완료

### 13.2 반영 파일
- `tests/test_json_contract_schema.py`
- `cli/commands/backtest.py`
- `cli/commands/optimize.py`
- `docs/contracts/CLI_JSON_Contract.md`

### 13.3 확인 결과
- `python -m pytest tests/test_json_contract_schema.py -q --tb=short` 통과
- `python -m pytest tests/ -q --cov=cli --cov-report=term-missing --cov-fail-under=55 --tb=short` 통과
- 결과: `242 passed, 1 skipped`, 커버리지 약 `55.50%`
- `python -m cli.main --version` 결과: `STOM, version 2.36.U1.5.C2.17`

## 14. C2.18 진행 상태 (테스트 문서 정합성 동기화)

### 14.1 완료 항목
1. `tests/README.md`를 현재 테스트 구조 기준으로 전면 갱신 완료
2. 파일별 테스트 수/총 테스트 수(243) 반영 완료
3. 테스트 실행/수집/커버리지 명령 및 유지보수 규칙 최신화 완료

### 14.2 반영 파일
- `tests/README.md`
- `docs/README.md`

### 14.3 확인 결과
- `python -m pytest tests/ --collect-only -q` 실행 결과 `243 tests collected` 확인
- `python -m cli.main --version` 결과: `STOM, version 2.36.U1.5.C2.18`

## 15. C2.19 진행 상태 (runner 커버리지 보강)

### 15.1 완료 항목
1. `tests/test_runners.py`에 runner 경계/오류/정리 분기 테스트 7건 추가 완료
2. backtest/optimize runner 커버리지 개선 완료
3. 전체 회귀/커버리지 기준(55%) 재검증 완료

### 15.2 반영 파일
- `tests/test_runners.py`

### 15.3 확인 결과
- `python -m pytest tests/test_runners.py -q --tb=short` 통과 (`11 passed`)
- `python -m pytest tests/ -q --cov=cli --cov-report=term-missing --cov-fail-under=55 --tb=short` 통과
- 결과: `249 passed, 1 skipped`, 커버리지 약 `57.41%`
- `python -m cli.main --version` 결과: `STOM, version 2.36.U1.5.C2.19`

## 16. C2.20 진행 상태 (runner 실패 시나리오 계약 테스트)

### 16.1 완료 항목
1. `tests/test_runners.py`에 queue timeout 경계 테스트 추가 완료
2. `tests/test_runners.py`에 process join timeout 후 `kill()` 강제 종료 테스트 추가 완료
3. 러너 실패 시나리오 계약 테스트 범위 확장 완료

### 16.2 반영 파일
- `tests/test_runners.py`

### 16.3 확인 결과
- `python -m pytest tests/test_runners.py -q --tb=short` 통과 (`13 passed`)
- `python -m pytest tests/ --collect-only -q` 결과 `252 tests collected`
- `python -m pytest tests/ -q --cov=cli --cov-report=term-missing --cov-fail-under=55 --tb=short` 통과
- 결과: `251 passed, 1 skipped`, 커버리지 약 `57.60%`
- `python -m cli.main --version` 결과: `STOM, version 2.36.U1.5.C2.20`

## 17. C2.21 진행 상태 (adapter 저커버리지 보강)

### 17.1 완료 항목
1. `tests/test_adapters.py` 신규 추가(13건) 완료
2. `settings_adapter`/`queue_adapter` 핵심 경계·정상 경로 테스트 보강 완료
3. 전체 회귀/커버리지 기준(55%) 재검증 완료

### 17.2 반영 파일
- `tests/test_adapters.py`

### 17.3 확인 결과
- `python -m pytest tests/test_adapters.py -q --tb=short` 통과 (`13 passed`)
- `python -m pytest tests/ --collect-only -q` 결과 `265 tests collected`
- `python -m pytest tests/ -q --cov=cli --cov-report=term-missing --cov-fail-under=55 --tb=short` 통과
- 결과: `264 passed, 1 skipped`, 커버리지 약 `61.42%`
- 어댑터 커버리지 개선
  - `cli/adapters/queue_adapter.py`: `23% -> 80%`
  - `cli/adapters/settings_adapter.py`: `24% -> 56%`
- `python -m cli.main --version` 결과: `STOM, version 2.36.U1.5.C2.21`

## 18. C2.22 진행 상태 (trade JSON 계약 + strategy 경계 보강)

### 18.1 완료 항목
1. `tests/test_trade.py` DB 오류 JSON 계약 테스트 4건 추가 완료
2. `tests/test_strategy_boundaries.py` 신규(13건) 추가 완료
3. `tests/test_json_contract_schema.py` DB 오류 JSON 스키마 검증 2건 추가 완료
4. `strategy import`의 `list` shadowing 결함 수정 완료
5. 전체 회귀/커버리지 기준(55%) 재검증 완료

### 18.2 반영 파일
- `cli/commands/trade.py`
- `cli/commands/strategy.py`
- `tests/test_trade.py`
- `tests/test_strategy_boundaries.py`
- `tests/test_json_contract_schema.py`

### 18.3 확인 결과
- `python -m pytest tests/test_trade.py -q --tb=short` 통과 (`26 passed`)
- `python -m pytest tests/test_strategy_boundaries.py -q --tb=short` 통과 (`13 passed`)
- `python -m pytest tests/ --collect-only -q` 결과 `284 tests collected`
- `python -m pytest tests/ -q --cov=cli --cov-report=term-missing --cov-fail-under=55 --tb=short` 통과
- 결과: `283 passed, 1 skipped`, 커버리지 약 `64.59%`
- 커버리지 개선
  - `cli/commands/strategy.py`: `43% -> 69%`
  - `cli/commands/trade.py`: `71% -> 76%`
- `python -m cli.main --version` 결과: `STOM, version 2.36.U1.5.C2.22`

## 19. C2.23 진행 상태 (CI 캐시 오류 + 크로스플랫폼 fallback 안정화)

### 19.1 완료 항목
1. `setup-python` pip cache 실패 대응을 위한 `cache-dependency-path` 설정 추가 완료
2. smoke/test/coverage job 의존성에 `pytz` 명시 및 test/coverage의 불필요한 `PyQt5` 제거 완료
3. Docker smoke 명령을 엔트리포인트 방식(`--version`, `--help`)으로 수정 완료
4. `utility/static.py` 플랫폼 의존 import fallback 보강 완료
5. `tests/test_static_cross_platform.py` 신규(5건) 추가 완료
6. Python 3.9 타입힌트 호환성 보강 + 클린 DB 환경 테이블 선생성 테스트 보강 완료
7. `strategy import` 서브커맨드 명시 등록(`name='import'`)으로 Click 버전 호환성 보강 완료
8. 버전/문서 동기화 완료 (`2.36.U1.5.C2.23`)

### 19.2 반영 파일
- `.github/workflows/cli-tests.yml`
- `utility/static.py`
- `tests/test_static_cross_platform.py`
- `cli/version.py`
- `docs/change_log/change_log.md`
- `docs/reports/2026-02-06_STOM_Version_2U_cli_research_test_code_review.md`
- `docs/README.md`
- `docs/AGENTS.md`
- `docs/CLI_User_Manual.md`
- `tests/README.md`

### 19.3 확인 결과
- `python -m pytest tests/test_static_cross_platform.py -q --tb=short` 통과 (`5 passed`)
- `python -m pytest tests/ --collect-only -q` 결과 `289 tests collected`
- `python -m pytest tests/ -q --cov=cli --cov-report=term-missing --cov-fail-under=55 --tb=short` 통과
- 결과: `288 passed, 1 skipped`, 커버리지 약 `64.59%`
- `python -m cli.main --version` 결과: `STOM, version 2.36.U1.5.C2.23`
