# STOM AI 에이전트 가이드

**프로젝트**: STOM (System Trading Operation Manager)
**버전**: V2.36.U1.5.C2.23
**최종 업데이트**: 2026-02-09

이 문서는 AI 에이전트(Claude Code, GitHub Copilot 등)가 STOM 프로젝트를 효율적으로 이해하고 작업할 수 있도록 작성되었습니다.

---

## 프로젝트 개요

STOM은 **시스템 트레이딩 운영 관리자**로, 주식/코인/선물 자동매매를 위한 Python 기반 트레이딩 시스템입니다.

### 핵심 기능

| 기능 | 설명 |
|------|------|
| **자동매매** | 주식(한국투자증권 API), 코인(업비트/바이낸스), 선물 지원 |
| **백테스트** | 16가지 분류 엔진 지원, 멀티프로세스 병렬 처리 |
| **전략 관리** | Python 기반 매수/매도 전략 작성 및 관리 |
| **최적화** | Grid Search, Optuna(베이지안), 유전 알고리즘, Walk-forward |
| **CLI 인터페이스** | AI 에이전트 자동화를 위한 명령줄 도구 |

---

## 프로젝트 구조

```
STOM_V/
├── cli/                    # CLI 인터페이스 (AI 에이전트 주요 진입점)
│   ├── main.py            # CLI 진입점 (Click 기반)
│   ├── adapters/          # 어댑터 (설정, 큐, 출력)
│   ├── commands/          # 명령어 그룹 (strategy, backtest, data 등)
│   └── runners/           # 헤드리스 러너 (백테스트, 최적화)
├── backtester/            # 백테스트 엔진
│   ├── back.py           # BackTest 메인 클래스
│   ├── back_engine.py    # BackEngine (분류별 처리)
│   └── back_sub_total.py # BackSubTotal (결과 집계)
├── ui/                    # PyQt5 GUI 모듈
│   └── ui_mainwindow.py  # 메인 윈도우
├── utility/               # 유틸리티 모듈
│   ├── setting.py        # 전역 설정 (DICT_SET, DB 경로)
│   ├── static.py         # 상수 정의
│   └── variable.py       # 공유 변수
├── stock/                 # 주식 트레이딩 로직
├── coin/                  # 코인 트레이딩 로직
├── future/                # 선물 트레이딩 로직
├── _database/             # SQLite 데이터베이스
│   ├── setting.db        # 시스템 설정
│   ├── strategy.db       # 전략 저장소
│   ├── backtest.db       # 백테스트 결과
│   └── tradelist.db      # 거래 기록
├── tests/                 # pytest 테스트 스위트
│   ├── conftest.py       # 테스트 픽스처
│   └── cli/              # CLI 테스트 (202개)
└── docs/                  # 문서
    ├── AGENTS.md         # 이 파일
    ├── CLI_User_Manual.md # CLI 매뉴얼
    └── ...
```

---

## AI 에이전트를 위한 CLI 사용법

### 기본 실행

```bash
# 프로젝트 루트에서 실행
cd C:\System_Trading\STOM\STOM_V
python -m cli.main --help
```

### 주요 명령어

| 명령어 | 용도 | 예시 |
|--------|------|------|
| `strategy list` | 전략 목록 조회 | `python -m cli.main strategy list --format json` |
| `strategy show` | 전략 상세 보기 | `python -m cli.main strategy show "전략명"` |
| `backtest run` | 백테스트 실행 | `python -m cli.main backtest run --type stock ...` |
| `backtest list` | 백테스트 목록 | `python -m cli.main backtest list --limit 10` |
| `data trades` | 거래 내역 조회 | `python -m cli.main data trades --format json` |
| `trade status` | 트레이딩 상태 | `python -m cli.main trade status` |
| `db info` | DB 정보 조회 | `python -m cli.main db info --type backtest` |

### JSON 출력 활용

AI 에이전트는 `--format json` 옵션을 사용하여 파싱 가능한 출력을 받을 수 있습니다:

```bash
python -m cli.main strategy list --format json
```

```json
{
  "strategies": [
    {"전략타입": "stock", "테이블": "stockbuy", "name": "GoldenCross", ...}
  ]
}
```

---

## 핵심 모듈 이해

### 1. 설정 시스템 (`utility/setting.py`)

```python
# 전역 설정 딕셔너리
DICT_SET = {
    'main': {...},      # 메인 설정
    'stock': {...},     # 주식 설정
    'coin': {...},      # 코인 설정
    'back': {...},      # 백테스트 설정
}

# 데이터베이스 경로
DB_SETTING = './_database/setting.db'
DB_STRATEGY = './_database/strategy.db'
DB_BACKTEST = './_database/backtest.db'
DB_TRADELIST = './_database/tradelist.db'
```

### 2. 백테스트 엔진 (`backtester/`)

**분류 엔진 (16가지)**:
- 종목코드별 분류
- 날짜별 분류 (일별/월별)
- 전략별 분류
- 복합 분류 (종목+날짜, 전략+날짜 등)

**프로세스 구조**:
```
BackTest (메인)
├── BackEngine[0..N] (워커)
└── BackSubTotal[0..M] (집계)
```

### 3. 전략 데이터베이스

**테이블 구조** (`strategy.db`):
- `stockbuy` - 주식 매수 전략
- `stocksell` - 주식 매도 전략
- `coinbuy` - 코인 매수 전략
- `coinsell` - 코인 매도 전략
- `futurebuy` - 선물 매수 전략
- `futuresell` - 선물 매도 전략

**컬럼**:
- `index` (TEXT, PK) - 전략 이름
- `코드` (TEXT) - Python 코드
- 기타 메타데이터

---

## 코드 수정 가이드

### 버전 네이밍 규칙

```
V{major}.{minor}.U{patch}.C{custom}
```

| 구분 | 설명 | 예시 |
|------|------|------|
| Major (V2) | 대규모 아키텍처 변경 | V2 → V3 |
| Minor (.36) | 기능 추가, 중요 업데이트 | V2.36 → V2.37 |
| Patch (U1) | 마이그레이션, 리팩토링 | V2.36.U1 → V2.36.U2 |
| Custom (C1) | CLI 등 특정 기능 개발 | V2.36.U1.5.C1 → C2 |

### 커밋 메시지 형식

```
STOM V{version} - {간단한 설명}

수정 내용:
- {변경 1}
- {변경 2}
...

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

### 파일 수정 시 주의사항

1. **PyQt5 의존성**: GUI 모듈(`ui/`)은 PyQt5가 필요합니다. CLI는 PyQt5 없이 동작하도록 설계되었습니다.

2. **데이터베이스 스키마**: `_database/` 내 DB 스키마 변경 시 마이그레이션 스크립트 필요

3. **멀티프로세싱**: 백테스트 엔진은 `multiprocessing` 사용. Windows에서 `if __name__ == '__main__':` 가드 필수

4. **테스트 실행**: 변경 후 반드시 테스트 실행
   ```bash
   pytest tests/ -v --tb=short
   ```

---

## 테스트 시스템

### 테스트 구조

```
tests/
├── conftest.py              # 공통 픽스처
├── cli/
│   ├── test_main.py        # 메인 CLI 테스트
│   ├── test_strategy.py    # 전략 명령 테스트
│   ├── test_backtest.py    # 백테스트 명령 테스트
│   ├── test_data.py        # 데이터 명령 테스트
│   └── ...                 # 총 202개 테스트
└── smoke/
    └── smoke_test.ps1      # 스모크 테스트
```

### 테스트 실행

```bash
# 전체 테스트
pytest tests/ -v

# 특정 모듈 테스트
pytest tests/cli/test_strategy.py -v

# 마커별 테스트
pytest tests/ -m "not slow" -v

# 커버리지 포함
pytest tests/ --cov=cli --cov-report=term-missing
```

### 테스트 픽스처

```python
# conftest.py 주요 픽스처
@pytest.fixture
def cli_runner():
    """Click CliRunner 인스턴스"""
    return CliRunner()

@pytest.fixture
def temp_db(tmp_path):
    """임시 테스트 데이터베이스"""
    ...

@pytest.fixture
def mock_settings(monkeypatch):
    """설정 모킹"""
    ...
```

---

## 문제 해결

### 자주 발생하는 오류

| 오류 | 원인 | 해결 |
|------|------|------|
| `ModuleNotFoundError: cli` | PYTHONPATH 미설정 | `set PYTHONPATH=%cd%` |
| `Database is locked` | DB 동시 접근 | `stom db vacuum --type all` |
| `Strategy not found` | 전략 미존재 | `stom strategy list` 확인 |
| `QApplication` 오류 | PyQt5 의존성 | CLI 모듈에서 Qt import 제거 |

### 디버깅 팁

1. **CLI 상세 로그**:
   ```bash
   python -m cli.main --verbose strategy list
   ```

2. **DB 직접 조회**:
   ```bash
   sqlite3 _database/strategy.db "SELECT name FROM stockbuy;"
   ```

3. **설정 확인**:
   ```bash
   python -c "from utility.setting import DICT_SET; print(DICT_SET.keys())"
   ```

---

## 관련 문서

| 문서 | 설명 |
|------|------|
| [CLI_User_Manual.md](CLI_User_Manual.md) | CLI 전체 명령어 참조 (한글) |
| [contracts/CLI_JSON_Contract.md](contracts/CLI_JSON_Contract.md) | CLI JSON 응답 계약서 |
| [change_log/change_log.md](change_log/change_log.md) | 버전 변경 이력 |
| [reports/CLI_Test_Report_V2.36.U1.5.C2.3.md](reports/CLI_Test_Report_V2.36.U1.5.C2.3.md) | 테스트 실행 보고서 |
| [reports/2026-02-06_STOM_Version_2U_cli_research_test_code_review.md](reports/2026-02-06_STOM_Version_2U_cli_research_test_code_review.md) | 브랜치 종합 코드 검토 및 실행 계획/결과 |
| [../CLAUDE.md](../CLAUDE.md) | 프로젝트 루트 가이드라인 |

---

## 빠른 참조 명령어

```bash
# 프로젝트 상태 확인
git status
python -m cli.main --version

# 전략 작업
python -m cli.main strategy list --format json
python -m cli.main strategy show "전략명" --format json

# 백테스트 실행
python -m cli.main backtest run \
  --type stock \
  --buy-strategy "매수전략" \
  --sell-strategy "매도전략" \
  --start-date 20240101 \
  --end-date 20240131 \
  --format json

# 테스트 실행
pytest tests/ -v --tb=short

# DB 관리
python -m cli.main db info --type backtest --format json
python -m cli.main db vacuum --type all --yes
```

---

**문서 작성**: Claude Opus 4.5
**최종 검토**: 2026-02-03
