# STOM CLI 테스트 시스템

**버전**: V2.36.U1.5.C2.21  
**최종 업데이트**: 2026-02-07  
**총 테스트 수**: 265개  
**최근 실행 결과**: 264 passed, 1 skipped

---

## 개요

STOM CLI 자동화 테스트 문서입니다.  
테스트는 `pytest`와 `Click CliRunner`를 기반으로 구성되어 있으며, 명령 계약(JSON), 통합 워크플로우, 러너/스키마 계약까지 포함합니다.

---

## 디렉터리 구조

```text
tests/
├── README.md
├── conftest.py
├── test_cli_basic.py
├── test_strategy.py
├── test_db.py
├── test_output_formats.py
├── test_backtest.py
├── test_data.py
├── test_trade.py
├── test_monitor.py
├── test_optimize.py
├── test_json_contract_schema.py
├── test_adapters.py
├── test_runners.py
├── test_schema_contract.py
├── fixtures/
│   ├── __init__.py
│   ├── sample_strategies.py
│   ├── sample_data.json
│   └── test_db_creator.py
└── integration/
    ├── __init__.py
    ├── test_workflow.py
    └── test_data_consistency.py
```

---

## 파일별 테스트 수

| 파일 | 테스트 수 |
|------|-----------|
| `tests/test_cli_basic.py` | 24 |
| `tests/test_strategy.py` | 24 |
| `tests/test_db.py` | 30 |
| `tests/test_output_formats.py` | 32 |
| `tests/test_backtest.py` | 8 |
| `tests/test_data.py` | 14 |
| `tests/test_trade.py` | 22 |
| `tests/test_monitor.py` | 14 |
| `tests/test_optimize.py` | 23 |
| `tests/test_json_contract_schema.py` | 20 |
| `tests/test_adapters.py` | 13 |
| `tests/test_runners.py` | 13 |
| `tests/test_schema_contract.py` | 5 |
| `tests/integration/test_workflow.py` | 11 |
| `tests/integration/test_data_consistency.py` | 12 |
| **합계** | **265** |

---

## 실행 명령

```bash
# 전체 테스트
python -m pytest tests/ -v --tb=short

# 요약 실행
python -m pytest tests/ -q --tb=short

# 계약(JSON schema) 검증만
python -m pytest tests/test_json_contract_schema.py -q --tb=short

# 커버리지 게이트 포함 실행
python -m pytest tests/ -q --cov=cli --cov-report=term-missing --cov-fail-under=55 --tb=short

# 수집 기준 총 테스트 수 확인
python -m pytest tests/ --collect-only -q
```

---

## 마커

| 마커 | 설명 |
|------|------|
| `smoke` | 빠른 기본 검증 |
| `integration` | 통합 시나리오 |
| `slow` | 상대적으로 오래 걸리는 테스트 |
| `requires_db` | DB 의존 테스트 |

---

## 유지보수 규칙

1. 테스트 추가/삭제 시 본 문서의 파일별 테스트 수와 총합을 반드시 동기화한다.
2. JSON 계약 변경 시 `tests/test_json_contract_schema.py`와 `docs/contracts/CLI_JSON_Contract.md`를 함께 수정한다.
3. CI 커버리지 기준 변경 시 실행 명령의 `--cov-fail-under` 수치를 즉시 갱신한다.
4. 버전 상향 커밋 시 본 문서의 버전/업데이트 날짜를 함께 갱신한다.

---

## 참고 문서

- `docs/CLI_User_Manual.md`
- `docs/contracts/CLI_JSON_Contract.md`
- `docs/reports/2026-02-06_STOM_Version_2U_cli_research_test_code_review.md`
