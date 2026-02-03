# STOM CLI 테스트 시스템

**버전**: V2.36.U1.5.C2.2
**최종 업데이트**: 2026-02-03
**총 테스트 수**: 202개

---

## 개요

STOM CLI 인터페이스의 자동화된 테스트 시스템입니다. pytest와 Click.CliRunner를 사용하여 모든 CLI 명령을 검증합니다.

---

## 디렉토리 구조

```
tests/
├── README.md                          # 이 문서
├── conftest.py                        # pytest 공용 픽스처
├── test_cli_basic.py                  # 기본 CLI 테스트 (24개)
├── test_strategy.py                   # 전략 명령 테스트 (26개)
├── test_db.py                         # DB 명령 테스트 (27개)
├── test_output_formats.py             # 출력 포맷 테스트 (28개)
├── test_backtest.py                   # 백테스트 명령 테스트 (12개)
├── test_data.py                       # 데이터 조회 테스트 (14개)
├── test_trade.py                      # 트레이딩 제어 테스트 (15개)
├── test_monitor.py                    # 모니터링 테스트 (17개)
├── test_optimize.py                   # 최적화 테스트 (16개)
├── fixtures/
│   ├── __init__.py
│   ├── sample_strategies.py           # 샘플 전략 코드
│   ├── sample_data.json               # JSON 테스트 데이터
│   └── test_db_creator.py             # 테스트 DB 생성 유틸리티
└── integration/
    ├── __init__.py
    ├── test_workflow.py               # 워크플로우 통합 테스트 (17개)
    └── test_data_consistency.py       # 데이터 일관성 테스트 (6개)
```

---

## 테스트 실행

### 전체 테스트 실행

```bash
# 프로젝트 루트에서 실행
cd C:\System_Trading\STOM\STOM_V

# 모든 테스트 실행
python -m pytest tests/ -v

# 빠른 실행 (요약만)
python -m pytest tests/ -q
```

### 특정 테스트 실행

```bash
# 스모크 테스트만
python -m pytest tests/ -m smoke -v

# 단위 테스트만 (통합 테스트 제외)
python -m pytest tests/ --ignore=tests/integration -v

# 통합 테스트만
python -m pytest tests/integration/ -v

# 특정 파일만
python -m pytest tests/test_cli_basic.py -v

# 특정 클래스만
python -m pytest tests/test_strategy.py::TestStrategyList -v

# 특정 테스트 함수만
python -m pytest tests/test_cli_basic.py::TestCLIHelp::test_main_help -v
```

### 커버리지 포함

```bash
# 커버리지 리포트 생성
python -m pytest tests/ --cov=cli --cov-report=html

# HTML 리포트 열기
start htmlcov/index.html
```

---

## 테스트 마커

| 마커 | 설명 | 사용법 |
|------|------|--------|
| `@pytest.mark.smoke` | 스모크 테스트 (빠른 기본 검증) | `pytest -m smoke` |
| `@pytest.mark.unit` | 단위 테스트 | `pytest -m unit` |
| `@pytest.mark.integration` | 통합 테스트 | `pytest -m integration` |
| `@pytest.mark.slow` | 느린 테스트 | `pytest -m "not slow"` |
| `@pytest.mark.requires_db` | DB 필요 테스트 | `pytest -m requires_db` |

---

## 스모크 테스트

빠른 기본 검증을 위한 스모크 테스트 스크립트:

### Windows (PowerShell)

```powershell
.\scripts\run_smoke_tests.ps1
```

### Linux/macOS (Bash)

```bash
bash scripts/run_smoke_tests.sh
```

---

## 테스트 픽스처

### conftest.py 주요 픽스처

| 픽스처 | 설명 |
|--------|------|
| `cli_runner` | Click CLI 테스트 러너 |
| `cli_runner_isolated` | 격리된 파일시스템 러너 |
| `temp_db_dir` | 임시 DB 디렉토리 |
| `mock_strategy_db` | 테스트용 전략 DB |
| `mock_strategy_db_with_data` | 데이터 포함 전략 DB |
| `mock_backtest_db` | 테스트용 백테스트 DB |
| `sample_strategy_code` | 샘플 전략 코드 |
| `backup_dir` | 백업 테스트 디렉토리 |

### 사용 예시

```python
def test_example(cli_runner, mock_strategy_db_with_data):
    """픽스처 사용 예시"""
    result = cli_runner.invoke(main, ['strategy', 'list'])
    assert result.exit_code == 0
```

---

## 테스트 작성 가이드

### 기본 구조

```python
import pytest
from click.testing import CliRunner
from cli.main import main

class TestCommandName:
    """명령 테스트 클래스"""

    @pytest.mark.smoke
    def test_command_basic(self, cli_runner: CliRunner):
        """기본 동작 테스트"""
        result = cli_runner.invoke(main, ['command', 'subcommand'])
        assert result.exit_code == 0

    def test_command_with_options(self, cli_runner: CliRunner):
        """옵션 테스트"""
        result = cli_runner.invoke(main, [
            'command', 'subcommand',
            '--option', 'value'
        ])
        assert result.exit_code in [0, 1]
```

### Exit Code 규칙

| Exit Code | 의미 |
|-----------|------|
| 0 | 성공 |
| 1 | 일반 에러 (데이터 없음, 실행 실패 등) |
| 2 | Click 옵션 오류 (잘못된 옵션, 누락 등) |

### 테스트 네이밍

- 파일: `test_{command}.py`
- 클래스: `Test{Command}{Feature}`
- 함수: `test_{feature}_{scenario}`

---

## CI/CD 통합

GitHub Actions 워크플로우가 자동으로 테스트를 실행합니다.

### 트리거

- `cli/` 또는 `tests/` 디렉토리 변경 시
- main 브랜치 push
- Pull Request

### 테스트 매트릭스

- Python 3.9, 3.10, 3.11
- Ubuntu, Windows

### 워크플로우 단계

1. 스모크 테스트 (빠른 검증)
2. 단위 테스트 (매트릭스)
3. 통합 테스트
4. 커버리지 리포트

---

## 문제 해결

### 자주 발생하는 문제

#### 1. ModuleNotFoundError: No module named 'tabulate'

마크다운 출력 테스트에 필요합니다:
```bash
pip install tabulate
```

#### 2. PyQt5 관련 오류

GUI 의존성 문제:
```bash
pip install PyQt5
```

#### 3. 테스트 데이터베이스 접근 오류

`_database/` 디렉토리가 필요합니다:
```bash
mkdir _database
```

---

## 테스트 현황

| 카테고리 | 테스트 수 | 상태 |
|----------|----------|------|
| 기본 CLI | 24 | ✅ 통과 |
| 전략 명령 | 26 | ✅ 통과 |
| DB 명령 | 27 | ✅ 통과 |
| 출력 포맷 | 28 | ✅ 통과 (1 스킵) |
| 백테스트 | 12 | ✅ 통과 |
| 데이터 조회 | 14 | ✅ 통과 |
| 트레이딩 | 15 | ✅ 통과 |
| 모니터링 | 17 | ✅ 통과 |
| 최적화 | 16 | ✅ 통과 |
| 통합 (워크플로우) | 17 | ✅ 통과 |
| 통합 (데이터) | 6 | ✅ 통과 |
| **총계** | **202** | **✅ 통과** |

---

## 관련 문서

- [CLI 사용자 매뉴얼](../docs/CLI_User_Manual.md)
- [테스트 환경 연구 보고서](../docs/research/20260203_cli_test_environment_research.md)
- [CLI 구현 보고서](../docs/reports/CLI_Implementation_Report_V2.36.U1.5.C1.1.md)
