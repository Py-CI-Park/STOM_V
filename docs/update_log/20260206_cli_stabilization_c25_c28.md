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
