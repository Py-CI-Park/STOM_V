# CLI 테스트 환경 연구 보고서

**작성일**: 2026-02-03
**버전**: V2.36.U1.5.C2.0
**대상**: STOM CLI 인터페이스 (Python 기반)
**목적**: CLI 테스트 시스템 현황 분석 및 구축 방안 제시

---

## 1. 현재 테스트 환경 현황

### 1.1 테스트 인프라 상태

| 구성 요소 | 상태 | 상세 |
|----------|------|------|
| pytest | ✅ 설치됨 | 8.4.1 버전 |
| Click | ✅ 설치됨 | 8.x 버전 (CLI 프레임워크) |
| 테스트 디렉토리 | ❌ 없음 | `tests/` 디렉토리 미존재 |
| 테스트 파일 | ❌ 없음 | CLI 전용 테스트 파일 없음 |
| conftest.py | ❌ 없음 | pytest 픽스처 설정 파일 없음 |
| CI/CD 통합 | ❌ 없음 | GitHub Actions 등 자동 테스트 미구성 |

### 1.2 데이터베이스 현황 분석

#### 1.2.1 데이터베이스 파일 목록

```
_database/
├── strategy.db        (212K) ✅ 활성
├── setting.db         (112K) ✅ 활성
├── tradelist.db       (124K) ✅ 활성
├── code_info.db       (20K)  ✅ 활성
├── backtest.db        (0B)   ⚠️ 빈 파일
├── stock_tick_back.db (0B)   ⚠️ 빈 파일
└── coin_tick.db       (0B)   ⚠️ 빈 파일
```

#### 1.2.2 strategy.db 스키마 분석

```
총 테이블: 25개
테이블 목록 및 현황:

주식 관련:
  ✅ stockbuy           (0 행) - 주식 매수 전략
  ✅ stocksell          (0 행) - 주식 매도 전략
  ✅ stockoptibuy       (0 행) - 주식 최적화 매수
  ✅ stockoptisell      (0 행) - 주식 최적화 매도
  ✅ stockoptivars      (0 행) - 주식 최적화 변수
  ✅ stockvars          (0 행) - 주식 변수 설정
  ✅ stockbuyconds      (0 행) - 주식 매수 조건
  ✅ stocksellconds     (0 행) - 주식 매도 조건

암호화폐 관련:
  ✅ coinbuy            (0 행) - 암호화폐 매수 전략
  ✅ coinsell           (0 행) - 암호화폐 매도 전략
  ✅ coinoptibuy        (0 행) - 암호화폐 최적화 매수
  ✅ coinoptisell       (0 행) - 암호화폐 최적화 매도
  ✅ coinoptivars       (0 행) - 암호화폐 최적화 변수
  ✅ coinvars           (0 행) - 암호화폐 변수 설정
  ✅ coinbuyconds       (0 행) - 암호화폐 매수 조건
  ✅ coinsellconds      (0 행) - 암호화폐 매도 조건

선물 관련:
  ✅ futurebuy          (0 행) - 선물 매수 전략
  ✅ futuresell         (0 행) - 선물 매도 전략
  ✅ futureoptibuy      (0 행) - 선물 최적화 매수
  ✅ futureoptisell     (0 행) - 선물 최적화 매도
  ✅ futureoptivars     (0 행) - 선물 최적화 변수
  ✅ futurevars         (0 행) - 선물 변수 설정
  ✅ futurebuyconds     (0 행) - 선물 매수 조건
  ✅ futuresellconds    (0 행) - 선물 매도 조건

기타:
  ✅ schedule           (0 행) - 스케줄 설정
```

#### 1.2.3 데이터 상태 평가

| 데이터베이스 | 스키마 | 데이터 | 평가 |
|------------|--------|--------|------|
| strategy.db | ✅ 정상 | ❌ 없음 | 스키마 준비됨, 테스트 데이터 필요 |
| setting.db | ✅ 정상 | ✅ 있음 | 운영 데이터 포함 |
| tradelist.db | ✅ 정상 | ✅ 있음 | 운영 데이터 포함 |
| backtest.db | ❌ 빈 파일 | ❌ 없음 | 스키마 초기화 필요 |
| stock_tick_back.db | ❌ 빈 파일 | ❌ 없음 | 초기화 필요 |
| coin_tick.db | ❌ 빈 파일 | ❌ 없음 | 초기화 필요 |

### 1.3 CLI 명령 테스트 결과

#### 1.3.1 기본 명령 테스트

```bash
# 1. 버전 및 도움말
$ python -m cli.main --help
✅ 정상 작동
   - 모든 서브커맨드 표시됨
   - 한글 출력 정상

$ python -m cli.main --version
✅ 정상 작동
   - 버전: 2.36.U1.5.C2.0
```

#### 1.3.2 전략 명령 테스트

```bash
# 2. 전략 통계
$ python -m cli.main strategy stats
✅ 정상 작동
   - 총 전략 수: 25개
   - 모든 테이블 조회 성공
   - 각 테이블 행 수 표시됨 (현재 모두 0)

# 3. 전략 목록
$ python -m cli.main strategy list
✅ 정상 작동
   - 빈 결과 반환 (데이터 없음)
   - 오류 없음

# 4. 전략 목록 JSON 포맷
$ python -m cli.main strategy list --format json
✅ 정상 작동
   - JSON 포맷 출력
```

#### 1.3.3 데이터베이스 명령 테스트

```bash
# 5. 데이터베이스 정보 조회
$ python -m cli.main db info --type strategy
✅ 정상 작동
   - 파일 크기: 0.21 MB
   - 수정 시간: 2026-02-01 17:54:04
   - 테이블 수: 25
   - 총 행 수: 0
   - 테이블별 정보 표시됨

# 6. 다른 데이터베이스 정보
$ python -m cli.main db info --type backtest
⚠️ 경고 (정상 동작)
   - backtest.db는 0B (빈 파일)
   - 스키마 미초기화
```

### 1.4 CLI 아키텍처 분석

#### 1.4.1 모듈 구조

```
cli/
├── main.py                 # Click 메인 그룹 정의
├── commands/
│   ├── strategy.py         # 전략 관리 (list, show, export, save, delete, import, validate)
│   ├── db.py               # DB 관리 (create, append, delete, info, vacuum, backup)
│   ├── backtest.py         # 백테스트 (run, list, status, cancel)
│   ├── data.py             # 데이터 조회 (trades, summary, export)
│   ├── trade.py            # 트레이딩 제어 (start, stop, status)
│   ├── monitor.py          # 모니터링 (live, pnl, positions)
│   └── optimize.py         # 최적화 (grid, bayesian, ga, walkforward, backfinder)
└── adapters/
    └── output_adapter.py   # 출력 포맷 (table, json, csv)
```

#### 1.4.2 주요 특징

- **Click 기반**: Click 라이브러리를 사용한 전문적인 CLI 설계
- **출력 포맷 지원**: table, json, csv 포맷 지원
- **에러 처리**: 구조화된 에러 처리 및 로깅
- **SQL Injection 방지**: 동적 테이블명에 대한 보안 대책 적용
- **한글 지원**: UTF-8 인코딩으로 완전한 한글 지원

---

## 2. 발견된 문제점 및 제한사항

### 2.1 수정 완료된 사항

#### ✅ OutputAdapter 인스턴스 vs 정적 메서드 불일치
- **문제**: OutputAdapter 사용 패턴 불일치 (35개 위치)
- **수정 상태**: 완료
- **영향**: CLI 명령이 정상 작동

### 2.2 현재 미해결 사항

#### ❌ 테스트 자동화 프레임워크 없음
- 테스트 파일 디렉토리 미존재
- 기본 smoke test도 없음
- pytest 설치되어 있지만 활용 안 됨

#### ❌ 테스트 데이터 부재
- strategy.db: 25개 테이블이 모두 비어 있음
- 테스트 실행 시 의미 있는 결과 검증 불가
- 예시 데이터 파일 없음

#### ❌ 백테스트 데이터베이스 미초기화
- backtest.db가 0B 빈 파일
- `db create --type backtest` 명령으로 초기화 가능하지만 실행 안 됨
- 스키마 검증 테스트 불가

#### ❌ 통합 테스트 불가
- 각 명령이 독립적으로 작동하는지 확인했지만
- 명령 간 상호작용 테스트 없음
- 데이터 일관성 검증 불가

#### ❌ 성능 테스트 없음
- 대용량 데이터 처리 테스트 미실시
- 응답 시간 기준 없음
- 메모리 사용량 모니터링 미실시

### 2.3 제한사항

#### 데이터베이스 스키마
```python
# strategy.py의 테이블 스키마 (기본)
CREATE TABLE {table_name} (
    name TEXT PRIMARY KEY,
    code TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

스키마가 매우 단순함. 실제 사용에 필요한 메타데이터 필드 부재:
- 전략 설명 (description)
- 파라미터 정보 (parameters)
- 성과 지표 (performance metrics)

---

## 3. CLI 명령 상세 분석

### 3.1 전략 관리 명령

#### 3.1.1 `strategy list` - 전략 목록 조회

```bash
# 기본 사용
python -m cli.main strategy list

# 필터링
python -m cli.main strategy list --type stock

# 포맷 지정
python -m cli.main strategy list --format json
python -m cli.main strategy list --format csv
```

**구현 방식**:
- sqlite_master 테이블에서 모든 테이블 조회
- 각 테이블에서 데이터 읽음
- 타입 필터링 (테이블명 기반)
- 출력 어댑터로 포맷팅

**테스트 결과**: ✅ 정상 작동 (데이터 없음)

#### 3.1.2 `strategy stats` - 전략 통계

```bash
python -m cli.main strategy stats
python -m cli.main strategy stats --format json
```

**결과 예시**:
```
============================================================
전략 통계
============================================================

총 전략 수: 25

전략별 항목 수:
  coinbuy: 0
  coinsell: 0
  ...
  stockvars: 0
  schedule: 0
```

**테스트 결과**: ✅ 정상 작동

#### 3.1.3 `strategy save` - 전략 저장

```bash
# 인라인 코드로 저장
python -m cli.main strategy save \
    --name "MyStrategy" \
    --type stock \
    --buy \
    --code "def signal(): return True"

# 파일에서 저장
python -m cli.main strategy save \
    --name "MyStrategy" \
    --type stock \
    --buy \
    --file strategy_code.py
```

**구현**:
- 테이블 자동 생성
- INSERT 또는 UPDATE 처리
- 타임스탬프 자동 관리

**테스트 예상**: ⚠️ 테스트 필요 (데이터 없어서 미검증)

#### 3.1.4 `strategy validate` - 전략 코드 유효성 검사

```bash
python -m cli.main strategy validate \
    --name "MyStrategy" \
    --type stock
```

**검사 항목**:
- Python 구문 검사 (compile 함수 사용)
- 함수 정의 확인
- 코드 길이 검사

**테스트 예상**: ⚠️ 테스트 데이터 필요

### 3.2 데이터베이스 관리 명령

#### 3.2.1 `db info` - 데이터베이스 정보 조회

```bash
# 전략 DB
python -m cli.main db info --type strategy

# 백테스트 DB
python -m cli.main db info --type backtest

# 모든 지원 타입
# backtest, tradelist, strategy, setting, stock_tick, stock_min, coin_tick, coin_min
```

**출력 정보**:
- 파일 크기 (MB)
- 마지막 수정 시간
- 테이블 수
- 총 행 수
- 테이블별 상세 정보

**테스트 결과**: ✅ 정상 작동

#### 3.2.2 `db create` - 데이터베이스 생성

```bash
# 백테스트 DB 생성
python -m cli.main db create --type backtest

# 강제 덮어쓰기
python -m cli.main db create --type backtest --force
```

**스키마**:
```python
# backtest 스키마
CREATE TABLE backtest_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_name TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    total_return REAL,
    sharpe_ratio REAL,
    max_drawdown REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

# tradelist 스키마
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    trade_time TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**테스트 예상**: ⚠️ 테스트 필요

#### 3.2.3 `db vacuum` - 데이터베이스 최적화

```bash
# 특정 DB 최적화
python -m cli.main db vacuum --type strategy

# 모든 DB 최적화
python -m cli.main db vacuum --type all

# 확인 프롬프트 스킵
python -m cli.main db vacuum --type all --yes
```

**기능**: SQLite VACUUM 명령으로 파일 크기 최적화

**테스트 결과**: ✅ 정상 작동

#### 3.2.4 `db backup` - 데이터베이스 백업

```bash
# 백업 생성
python -m cli.main db backup --output ./backups

# 압축 포함
python -m cli.main db backup --output ./backups --compress
```

**기능**:
- 모든 DB 파일 타임스탐프 디렉토리에 복사
- manifest.txt 생성
- 선택적 ZIP 압축

**테스트 결과**: ⚠️ 테스트 필요

---

## 4. 테스트 시스템 구축 방안

### 4.1 Phase 1: 기본 테스트 인프라 (필수, 우선순위 1)

#### 4.1.1 디렉토리 구조

```
tests/
├── __init__.py
├── conftest.py                 # pytest 공용 픽스처 및 설정
├── test_cli_basic.py           # 기본 CLI 테스트
├── test_cli_strategy.py        # 전략 명령 테스트
├── test_cli_db.py              # DB 명령 테스트
├── test_cli_backtest.py        # 백테스트 명령 테스트
├── test_cli_output_formats.py  # 출력 포맷 테스트
├── fixtures/
│   ├── sample_strategies.json
│   ├── sample_strategies.csv
│   └── test_config.json
└── integration/
    ├── test_workflow_create_and_list.py
    └── test_workflow_save_and_validate.py
```

#### 4.1.2 conftest.py 예시

```python
# tests/conftest.py
import pytest
import os
import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner
from cli.main import main


@pytest.fixture(scope="session")
def test_db_dir():
    """테스트용 임시 DB 디렉토리 생성"""
    tmp_dir = tempfile.mkdtemp(prefix="stom_test_")
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def cli_runner():
    """Click CLI 테스트 러너"""
    return CliRunner()


@pytest.fixture
def cli_isolated_filesystem(cli_runner):
    """격리된 파일시스템 환경"""
    with cli_runner.isolated_filesystem():
        yield cli_runner


@pytest.fixture
def sample_strategy_code():
    """샘플 전략 코드"""
    return """
def signal(price, moving_avg):
    if price > moving_avg:
        return 'BUY'
    elif price < moving_avg:
        return 'SELL'
    return 'HOLD'

def risk_management(position_size, stop_loss):
    return position_size * (1 - stop_loss)
"""


@pytest.fixture
def mock_databases(tmp_path):
    """테스트용 모의 데이터베이스 생성"""
    db_dir = tmp_path / "_database"
    db_dir.mkdir()

    # 빈 데이터베이스 파일 생성
    for db_name in ['strategy.db', 'backtest.db', 'tradelist.db']:
        (db_dir / db_name).touch()

    return db_dir
```

#### 4.1.3 기본 테스트 예시

```python
# tests/test_cli_basic.py
import pytest
from click.testing import CliRunner
from cli.main import main


class TestCLIBasic:
    """기본 CLI 테스트"""

    def test_help_command(self):
        """--help 명령 테스트"""
        runner = CliRunner()
        result = runner.invoke(main, ['--help'])

        assert result.exit_code == 0
        assert 'STOM' in result.output
        assert 'strategy' in result.output
        assert 'db' in result.output
        assert 'backtest' in result.output

    def test_version_command(self):
        """--version 명령 테스트"""
        runner = CliRunner()
        result = runner.invoke(main, ['--version'])

        assert result.exit_code == 0
        assert '2.36.U1.5' in result.output

    def test_invalid_command(self):
        """존재하지 않는 명령 테스트"""
        runner = CliRunner()
        result = runner.invoke(main, ['invalid-command'])

        assert result.exit_code != 0
        assert 'Error' in result.output or 'No such command' in result.output


class TestStrategyCommands:
    """전략 명령 테스트"""

    def test_strategy_help(self):
        """strategy --help 테스트"""
        runner = CliRunner()
        result = runner.invoke(main, ['strategy', '--help'])

        assert result.exit_code == 0
        assert 'list' in result.output
        assert 'save' in result.output
        assert 'validate' in result.output

    def test_strategy_stats(self):
        """strategy stats 테스트"""
        runner = CliRunner()
        result = runner.invoke(main, ['strategy', 'stats'])

        assert result.exit_code == 0
        assert '전략' in result.output or 'Strategies' in result.output

    def test_strategy_list(self):
        """strategy list 테스트"""
        runner = CliRunner()
        result = runner.invoke(main, ['strategy', 'list'])

        # 데이터가 없어도 오류 없이 실행되어야 함
        assert result.exit_code == 0

    def test_strategy_list_json_format(self):
        """strategy list --format json 테스트"""
        runner = CliRunner()
        result = runner.invoke(main, ['strategy', 'list', '--format', 'json'])

        assert result.exit_code == 0
        # JSON 포맷 확인


class TestDBCommands:
    """DB 명령 테스트"""

    def test_db_help(self):
        """db --help 테스트"""
        runner = CliRunner()
        result = runner.invoke(main, ['db', '--help'])

        assert result.exit_code == 0
        assert 'info' in result.output
        assert 'backup' in result.output

    def test_db_info_strategy(self):
        """db info --type strategy 테스트"""
        runner = CliRunner()
        result = runner.invoke(main, ['db', 'info', '--type', 'strategy'])

        assert result.exit_code == 0
        assert 'strategy.db' in result.output or 'Database' in result.output
```

### 4.2 Phase 2: 테스트 데이터 생성 (필수, 우선순위 2)

#### 4.2.1 테스트 데이터 픽스처

```python
# tests/fixtures/create_test_data.py
import sqlite3
import json
from pathlib import Path


def create_test_strategy_data(db_path):
    """테스트용 전략 데이터 생성"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 테이블 생성 및 데이터 삽입
    test_strategies = [
        ("stockbuy", "ma_crossover", "def signal(): return price > ma(20)"),
        ("stockbuy", "rsi_oversold", "def signal(): return rsi() < 30"),
        ("coinsell", "ma_sell", "def signal(): return price < ma(50)"),
        ("coinsell", "profit_taking", "def signal(): return profit > threshold"),
    ]

    for table, name, code in test_strategies:
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                name TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute(f"INSERT INTO {table} (name, code) VALUES (?, ?)",
                      (name, code))

    conn.commit()
    conn.close()


def create_test_backtest_results(db_path):
    """테스트용 백테스트 결과 생성"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS backtest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_name TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            total_return REAL,
            sharpe_ratio REAL,
            max_drawdown REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    test_results = [
        ("ma_crossover", "20260101", "20260131", 0.15, 1.5, -0.08),
        ("rsi_oversold", "20260101", "20260131", 0.08, 0.9, -0.12),
    ]

    for strategy, start, end, ret, sharpe, dd in test_results:
        cursor.execute("""
            INSERT INTO backtest_results
            (strategy_name, start_date, end_date, total_return, sharpe_ratio, max_drawdown)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (strategy, start, end, ret, sharpe, dd))

    conn.commit()
    conn.close()
```

#### 4.2.2 JSON 형식 테스트 데이터

```json
[
  {
    "name": "ma_crossover",
    "type": "stock",
    "buy_sell": "buy",
    "code": "def signal(price, ma20, ma50):\n    return 'BUY' if price > ma20 else 'SELL'"
  },
  {
    "name": "rsi_oversold",
    "type": "stock",
    "buy_sell": "buy",
    "code": "def signal(rsi):\n    return 'BUY' if rsi < 30 else 'HOLD'"
  }
]
```

### 4.3 Phase 3: 통합 테스트 (우선순위 3)

```python
# tests/integration/test_workflow_create_and_list.py
import pytest
from click.testing import CliRunner
from cli.main import main


class TestCreateAndListWorkflow:
    """전략 생성 및 조회 통합 테스트"""

    def test_save_and_list_workflow(self):
        """전략을 저장한 후 조회하는 워크플로우"""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # 1. 전략 저장
            save_result = runner.invoke(main, [
                'strategy', 'save',
                '--name', 'test_ma',
                '--type', 'stock',
                '--buy',
                '--code', 'def signal(): return True'
            ])
            assert save_result.exit_code == 0

            # 2. 전략 목록 조회
            list_result = runner.invoke(main, ['strategy', 'list'])
            assert list_result.exit_code == 0
            assert 'test_ma' in list_result.output

            # 3. 전략 통계 확인
            stats_result = runner.invoke(main, ['strategy', 'stats'])
            assert stats_result.exit_code == 0
            assert '1' in stats_result.output  # 최소 1개 전략
```

### 4.4 테스트 프레임워크 선택 근거

#### Click.CliRunner 선택 이유

```python
# Click의 공식 테스트 도구 사용
from click.testing import CliRunner

def test_example():
    runner = CliRunner()
    result = runner.invoke(main, ['command', 'arg'])

    # 장점:
    # 1. CLI 명령 격리 실행
    result.exit_code      # 종료 코드
    result.output         # 표준 출력
    result.exception      # 발생한 예외

    # 2. 파일시스템 격리
    with runner.isolated_filesystem():
        # 임시 파일시스템에서 테스트
        pass

    # 3. 환경 변수 모킹
    result = runner.invoke(main, ['cmd'], env={'VAR': 'value'})
```

**주요 장점**:
- Click 공식 테스트 도구
- 격리된 환경에서 안전한 테스트
- 파일시스템 격리 지원
- 환경 변수 제어 가능
- Subprocess 오버헤드 없음

---

## 5. 즉시 실행 가능한 테스트

### 5.1 Smoke Test 스크립트

```bash
#!/bin/bash
# run_smoke_tests.sh

echo "=== STOM CLI Smoke Tests ==="
echo

# 1. 버전 확인
echo "1. Testing --version..."
python -m cli.main --version
if [ $? -eq 0 ]; then echo "✓ PASS"; else echo "✗ FAIL"; fi
echo

# 2. 도움말 확인
echo "2. Testing --help..."
python -m cli.main --help > /dev/null
if [ $? -eq 0 ]; then echo "✓ PASS"; else echo "✗ FAIL"; fi
echo

# 3. 전략 통계
echo "3. Testing strategy stats..."
python -m cli.main strategy stats > /dev/null
if [ $? -eq 0 ]; then echo "✓ PASS"; else echo "✗ FAIL"; fi
echo

# 4. 전략 목록
echo "4. Testing strategy list..."
python -m cli.main strategy list > /dev/null
if [ $? -eq 0 ]; then echo "✓ PASS"; else echo "✗ FAIL"; fi
echo

# 5. 전략 목록 JSON
echo "5. Testing strategy list --format json..."
python -m cli.main strategy list --format json > /dev/null
if [ $? -eq 0 ]; then echo "✓ PASS"; else echo "✗ FAIL"; fi
echo

# 6. DB 정보
echo "6. Testing db info --type strategy..."
python -m cli.main db info --type strategy > /dev/null
if [ $? -eq 0 ]; then echo "✓ PASS"; else echo "✗ FAIL"; fi
echo

echo "=== Smoke Tests Complete ==="
```

### 5.2 JSON 출력 검증 스크립트

```python
#!/usr/bin/env python
# scripts/verify_json_output.py

import subprocess
import json
import sys


def test_json_output(command):
    """JSON 출력 검증"""
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"✗ Command failed: {command}")
            print(result.stderr)
            return False

        # JSON 파싱 시도
        json.loads(result.stdout)
        print(f"✓ Valid JSON: {command}")
        return True
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON: {command}")
        print(f"  Error: {e}")
        return False


# 테스트 명령어 목록
commands = [
    ['python', '-m', 'cli.main', 'strategy', 'list', '--format', 'json'],
    ['python', '-m', 'cli.main', 'strategy', 'stats', '--format', 'json'],
    ['python', '-m', 'cli.main', 'db', 'info', '--type', 'strategy', '--format', 'json'],
]

passed = sum(test_json_output(cmd) for cmd in commands)
total = len(commands)

print(f"\nResult: {passed}/{total} tests passed")
sys.exit(0 if passed == total else 1)
```

### 5.3 현재 즉시 실행 가능한 명령

```bash
# 1. 기본 기능 확인
python -m cli.main --help
python -m cli.main --version

# 2. 전략 관련
python -m cli.main strategy stats
python -m cli.main strategy list
python -m cli.main strategy list --format json

# 3. DB 관련
python -m cli.main db info --type strategy
python -m cli.main db info --type setting
python -m cli.main db info --type tradelist

# 4. 백업
python -m cli.main db backup --output ./backup_test

# 5. 최적화 (읽기 전용)
python -m cli.main db vacuum --type strategy --yes
```

---

## 6. 테스트 자동화 CI/CD 통합

### 6.1 GitHub Actions 워크플로우 예시

```yaml
# .github/workflows/cli-tests.yml
name: STOM CLI Tests

on:
  push:
    branches: [ main, STOM_Version_2U-cli-research ]
    paths:
      - 'cli/**'
      - 'tests/**'
  pull_request:
    branches: [ main ]
    paths:
      - 'cli/**'
      - 'tests/**'

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install pytest click pandas

    - name: Run smoke tests
      run: |
        python -m cli.main --version
        python -m cli.main strategy stats

    - name: Run pytest tests
      run: |
        pytest tests/ -v --cov=cli --cov-report=xml

    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
```

### 6.2 테스트 커버리지 목표

| 영역 | 현재 | 목표 | 시간 |
|------|------|------|------|
| strategy 명령 | 0% | 85% | 2-3주 |
| db 명령 | 0% | 80% | 1-2주 |
| output_adapter | 0% | 90% | 1주 |
| 통합 테스트 | 0% | 70% | 2주 |
| **전체** | **0%** | **80%** | **4-5주** |

---

## 7. 결론 및 권장 사항

### 7.1 현재 상태 평가

| 항목 | 상태 | 평가 |
|------|------|------|
| CLI 코드 완성도 | ✅ 95% | 명령 구현 완료, 기능 검증 필요 |
| 테스트 인프라 | ❌ 0% | 완전히 구축 필요 |
| 테스트 데이터 | ❌ 0% | 생성 필요 |
| 문서화 | ⚠️ 50% | CLI --help는 있음, 사용 가이드 필요 |
| 버그 | ✅ 발견된 버그 모두 수정 완료 | OutputAdapter 불일치 35개 위치 수정 |

### 7.2 권장 우선순위

#### 🔴 즉시 실행 (1주 이내)

1. **Smoke Test 스크립트 작성**
   - 기본 명령 10-15개 테스트
   - 파일: `scripts/run_smoke_tests.sh`
   - 시간: 2-3일

2. **테스트 디렉토리 구조 생성**
   - `tests/`, `tests/fixtures/`, `tests/integration/` 생성
   - conftest.py 작성
   - 시간: 1-2일

#### 🟠 단기 (1-2주)

3. **기본 단위 테스트 작성**
   - Phase 1: 기본 테스트 인프라
   - 대상: 전략 명령, DB 명령
   - 목표: 50% 커버리지
   - 파일: `tests/test_cli_*.py`
   - 시간: 1주

4. **테스트 데이터 생성**
   - JSON, CSV 샘플 데이터
   - 모의 DB 생성 함수
   - 시간: 3-4일

#### 🟡 중기 (2-4주)

5. **통합 테스트 작성**
   - Phase 2: 워크플로우 테스트
   - 데이터 일관성 검증
   - 시간: 1-2주

6. **성능/스트레스 테스트**
   - 대용량 데이터 처리
   - 응답 시간 벤치마크
   - 시간: 1주

#### 🟢 장기 (1개월)

7. **CI/CD 통합**
   - GitHub Actions 설정
   - 자동 테스트 실행
   - 커버리지 리포트
   - 시간: 1주

### 7.3 예상 작업량

| Phase | 항목 | 예상 줄 수 | 예상 시간 |
|-------|------|-----------|----------|
| 1 | 테스트 인프라 | 400-500줄 | 1주 |
| 2 | 테스트 데이터 | 200-300줄 | 3-4일 |
| 3 | CI/CD | 100-150줄 | 2-3일 |
| 추가 | 문서, Smoke Test | 150-200줄 | 3-4일 |
| **합계** | | **850-1,150줄** | **4-5주** |

### 7.4 성공 지표

```
테스트 구축 완료 기준:
✅ pytest 테스트 50+개 작성
✅ 코드 커버리지 80% 이상
✅ CI/CD 파이프라인 자동 실행
✅ 모든 CLI 명령 최소 1개 테스트 커버
✅ 통합 테스트 10+개 작성
✅ 문서화된 테스트 가이드
```

### 7.5 다음 단계

1. **즉시**: 이 보고서 검토 및 승인
2. **1-2주**: Phase 1 테스트 인프라 구축
3. **2-3주**: Phase 2 테스트 데이터 및 기본 테스트 작성
4. **3-4주**: Phase 3 CI/CD 통합

---

## 부록

### A. 테스트 명령어 레퍼런스

```bash
# 모든 테스트 실행
pytest tests/ -v

# 특정 테스트 파일만
pytest tests/test_cli_basic.py -v

# 커버리지 보고서 생성
pytest tests/ --cov=cli --cov-report=html

# 특정 마커 테스트만
pytest tests/ -m "not slow" -v

# 상세 출력
pytest tests/ -vv -s
```

### B. 샘플 전략 코드 (테스트용)

```python
# tests/fixtures/sample_strategies.py

# 전략 1: 이동평균선 교차
STRATEGY_MA_CROSSOVER = """
def signal(price, ma_short, ma_long):
    if ma_short > ma_long:
        return 'BUY'
    elif ma_short < ma_long:
        return 'SELL'
    return 'HOLD'
"""

# 전략 2: RSI 과매도
STRATEGY_RSI_OVERSOLD = """
def signal(rsi, threshold=30):
    if rsi < threshold:
        return 'BUY'
    elif rsi > 100 - threshold:
        return 'SELL'
    return 'HOLD'
"""

# 전략 3: 단순 매매
STRATEGY_SIMPLE = """
def signal():
    return 'BUY'
"""
```

### C. 테스트 데이터베이스 초기화 스크립트

```bash
#!/bin/bash
# scripts/setup_test_databases.sh

mkdir -p tests/data
cd tests/data

# 전략 DB 초기화
python << 'EOF'
import sqlite3
conn = sqlite3.connect('strategy.db')
cursor = conn.cursor()

# 테이블 생성
for table_name in ['stockbuy', 'stocksell', 'coinbuy', 'coinsell']:
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            name TEXT PRIMARY KEY,
            code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

# 테스트 데이터 삽입
cursor.execute("INSERT INTO stockbuy VALUES ('test_ma', 'def signal(): pass')")
cursor.execute("INSERT INTO coinbuy VALUES ('test_rsi', 'def signal(): pass')")

conn.commit()
conn.close()
print("Strategy database initialized")
EOF

echo "Test databases setup complete"
```

---

**문서 버전**: 1.0
**최종 작성**: 2026-02-03
**작성자**: Claude Opus 4.5
**다음 검토 예정일**: 2026-02-10 (Phase 1 완료 후)
