# STOM Change Log

## 버전 기록

### V2.36.U1.5.C2.12 (2026-02-07) - 성공 JSON 계약/자동검증/전체 커버리지 하한선 적용

#### 개요
C2.11 후속으로 성공 경로 JSON 계약 검증을 보강하고, jsonschema 기반 자동 검증 및 전체 CLI 커버리지 하한선을 적용.

#### 주요 변경 사항
- `tests/test_trade.py`
  - 성공 계약 테스트 추가:
    - `positions close --all --format json`
    - `orders cancel --all --format json`
- `tests/test_json_contract_schema.py` 신규
  - jsonschema 기반 계약 자동검증 테스트 9건 추가
  - 대상: `trade status`, `positions list`, `orders list`, `data backtest-list`, `db info`, close/cancel 성공/실패
- `.github/workflows/cli-tests.yml`
  - 전체 coverage 단계에 `--cov-fail-under=50` 적용
  - runner/schema coverage 단계는 `--cov-fail-under=35` 유지
- `requirements-test.txt`
  - `jsonschema>=4.20.0` 명시
- 버전 상향
  - `2.36.U1.5.C2.12`

#### 검증
- `python -m pytest tests/test_trade.py tests/test_json_contract_schema.py -q`
- `python -m pytest tests/ -q --tb=short`
- `python -m pytest tests/ -q --cov=cli --cov-report=term-missing --cov-fail-under=50`
  - 총 커버리지: 약 54%

---

### V2.36.U1.5.C2.11 (2026-02-06) - 실패 JSON 계약 강화 및 커버리지 하한선 적용

#### 개요
C2.10 후속으로 `positions close`/`orders cancel` 실패 경로의 JSON 계약을 강화하고, runner/schema 전용 커버리지 스냅샷에 하한선을 적용.

#### 주요 변경 사항
- `cli/commands/trade.py`
  - `positions close`, `orders cancel`에 `--format` 옵션 추가
  - 필수 인자 누락 시 JSON 표준 에러(`ok=false`) + 에러코드 반환
  - 신규 에러코드:
    - `POSITIONS_CLOSE_INVALID_ARGS`
    - `ORDERS_CANCEL_INVALID_ARGS`
- `tests/test_trade.py`
  - 실패 JSON 에러코드 계약 테스트 2건 추가
- `.github/workflows/cli-tests.yml`
  - runner/schema focused coverage 단계에 `--cov-fail-under=35` 적용
- `docs/contracts/CLI_JSON_Contract.md`
  - 명령별 샘플 응답 및 테스트 링크 표 추가
- 버전 상향
  - `2.36.U1.5.C2.11`

#### 검증
- `python -m pytest tests/test_trade.py -q`
- `python -m pytest tests/ -q --tb=short`
- `python -m cli.main --version`

---

### V2.36.U1.5.C2.10 (2026-02-06) - C2.9 후속 단계(테스트/커버리지/계약 분리)

#### 개요
C2.9 완료 후 정의된 다음 단계 3개 항목을 실행해 JSON 계약 검증과 CI 가시성을 강화.

#### 주요 변경 사항
- `tests/test_trade.py`
  - `positions/orders`의 JSON payload 계약(배열 또는 message 객체) 검증 테스트 추가
  - `trade status --format json` 필수 필드(`trading_status`, `configuration`) 검증 추가
- `.github/workflows/cli-tests.yml`
  - coverage job에 runner/schema 전용 커버리지 스냅샷 단계 추가
  - `runner_schema_coverage.xml`, `runner_schema_coverage.txt` 아티팩트 업로드 단계 추가
- 독립 계약 문서 추가
  - `docs/contracts/CLI_JSON_Contract.md`
  - JSON 성공/빈결과/에러 표준 페이로드 및 명령별 필드 계약 정의
- 버전 상향
  - `2.36.U1.5.C2.10`

#### 검증
- `python -m pytest tests/test_trade.py tests/test_output_formats.py tests/test_data.py tests/test_monitor.py -q`
- `python -m pytest tests/ -q --tb=short`
- `python -m cli.main --version`

---

### V2.36.U1.5.C2.9 (2026-02-06) - C2.8 후속 실행(문서/CI/인코딩 정리)

#### 개요
C2.8 이후 정의한 후속 권장사항을 기반으로 운영 안정성 항목 3가지를 추가 반영.

#### 주요 변경 사항
- `cli/commands/trade.py`
  - 깨진 인코딩 문자열/주석/도움말 텍스트를 정리해 유지보수 가독성 개선
  - `trade/positions/orders` 명령 에러 응답 코드 정비
- `docs/CLI_User_Manual.md`
  - `JSON 응답 계약 (AI 파싱 기준)` 섹션 추가
  - 빈 결과(`{"message": ...}`), 표준 에러(`ok/error`) 구조 명시
  - 명령별 JSON 필드 계약 표 추가
- `.github/workflows/cli-tests.yml`
  - `tests/test_runners.py`, `tests/test_schema_contract.py`를 필수 CI 게이트로 추가

#### 검증
- `python -m pytest tests/test_trade.py tests/test_cli_basic.py -q`
  - `38 passed`
- `python -m cli.main positions list --format json`
- `python -m cli.main orders list --format json`
- `python -m cli.main trade status --format json`
- `python -m cli.main --version`
  - `STOM, version 2.36.U1.5.C2.9`

---

### V2.36.U1.5.C2.8 (2026-02-06) - AI-Ready 출력/문서 표준화

#### 개요
C2.5~C2.8 실행 항목을 기준으로 AI 파싱 안정성을 높이기 위한 출력/에러 표준화와 문서 동기화를 완료.

#### 주요 변경 사항
- `OutputAdapter` 개선
  - JSON/CSV 출력 시 title 배너를 제거해 파싱 가능한 출력 유지
  - JSON 에러 응답 표준 구조(`ok`, `error.code`, `error.message`) 지원
- 주요 명령(`data`, `monitor`, `optimize`, `backtest`, `db info`)에서 JSON 에러 포맷 연동
- 문서 동기화
  - `docs/AGENTS.md`, `docs/README.md`, `docs/CLI_User_Manual.md` 버전/링크 최신화
  - `docs/reports/2026-02-06_STOM_Version_2U_cli_research_test_code_review.md` 실행 결과 반영
  - `docs/update_log/20260206_cli_stabilization_c25_c28.md` 신규 추가

#### 테스트
- `python -m pytest tests/test_output_formats.py tests/test_data.py tests/test_monitor.py tests/test_optimize.py tests/test_backtest.py tests/test_runners.py tests/test_schema_contract.py -q`
- 결과: `95 passed, 1 skipped`

---

### V2.36.U1.5.C2.7 (2026-02-06) - 러너 안정화 및 계약 테스트

#### 주요 변경 사항
- `cli/runners/backtest_runner.py`
  - 잘못된 `backtest_type` 입력 시 백테스트 모듈 로딩 전에 즉시 실패하도록 경로 정리
- `cli/runners/trade_runner.py`
  - 미구현 주문 실행(`close_position`, `cancel_order`)이 성공처럼 보이지 않도록 경계 동작 명확화
- 테스트 추가
  - `tests/test_runners.py`: trade/optimize/backtest 러너 핵심 경로 검증
  - `tests/test_schema_contract.py`: schema adapter 테이블/컬럼 계약 검증

#### 테스트
- `python -m pytest tests/test_runners.py tests/test_schema_contract.py -q`
- 결과: `9 passed`

---

### V2.36.U1.5.C2.6 (2026-02-06) - CLI 테스트 신뢰도 복구

#### 주요 변경 사항
- 대상 테스트 재작성:
  - `tests/test_data.py`
  - `tests/test_trade.py`
  - `tests/test_monitor.py`
  - `tests/test_backtest.py`
  - `tests/test_optimize.py`
- `exit_code in [0, 1, 2]` 형태의 느슨한 검증 제거
- 실제 CLI 옵션(`--type` 중심) 기준으로 테스트 동기화
- legacy 옵션 거부 동작 검증 추가

#### 테스트
- `python -m pytest tests/test_data.py tests/test_trade.py tests/test_monitor.py tests/test_backtest.py tests/test_optimize.py -q`
- 결과: `70 passed`

---

### V2.36.U1.5.C2.5 (2026-02-06) - DB 스키마 정합성 및 버전 단일화

#### 주요 변경 사항
- 버전 상수 단일화
  - `cli/version.py` 신설
  - `cli/main.py`, `cli/__init__.py`에서 공통 버전 사용
- 스키마 어댑터 도입
  - `cli/adapters/schema_adapter.py` 신설
  - `data/trade/monitor/optimize` 명령의 테이블/컬럼 매핑 정합화
- `db info --format` 버그 수정
  - `--format json`에서 실제 JSON 구조 출력 보장
- `RuntimeWarning` 유발 구조(eager import) 제거

---

### V2.36.U1.5.C2.3 (2026-02-03) - CLI 테스트 시스템 구축 완료

#### 개요
CLI 인터페이스 자동화 테스트 시스템 완전 구축. pytest와 Click.CliRunner 기반 202개 테스트 작성.

#### Phase 1: 테스트 인프라
- `tests/` 디렉토리 구조 생성
- `pytest.ini` 설정 파일 (마커 정의, 기본 옵션)
- `requirements-test.txt` 테스트 의존성 파일
- `tests/conftest.py` 공용 픽스처 및 헬퍼 함수

#### Phase 2: 단위 테스트 (179개)
- `test_cli_basic.py`: 기본 CLI 명령 테스트 (24개)
- `test_strategy.py`: 전략 관리 명령 테스트 (26개)
- `test_db.py`: 데이터베이스 관리 명령 테스트 (27개)
- `test_output_formats.py`: 출력 포맷 테스트 (28개)
- `test_backtest.py`: 백테스트 명령 테스트 (12개)
- `test_data.py`: 데이터 조회 테스트 (14개)
- `test_trade.py`: 트레이딩 제어 테스트 (15개)
- `test_monitor.py`: 모니터링 테스트 (17개)
- `test_optimize.py`: 최적화 테스트 (16개)

#### Phase 3: 테스트 데이터 픽스처
- `fixtures/sample_strategies.py`: 샘플 전략 코드
- `fixtures/sample_data.json`: JSON 형식 테스트 데이터
- `fixtures/test_db_creator.py`: 테스트 DB 생성 유틸리티

#### Phase 4: CI/CD 통합
- `.github/workflows/cli-tests.yml`: GitHub Actions 워크플로우
- Python 3.9, 3.10, 3.11 매트릭스 테스트
- 스모크 테스트, 단위 테스트, 통합 테스트
- 코드 커버리지 리포트

#### Phase 5: 통합 테스트 (23개)
- `integration/test_workflow.py`: 워크플로우 통합 테스트 (17개)
- `integration/test_data_consistency.py`: 데이터 일관성 테스트 (6개)

#### 스모크 테스트 스크립트
- `scripts/run_smoke_tests.sh` (Bash)
- `scripts/run_smoke_tests.ps1` (PowerShell)

#### 파일 변경 요약

| 파일 | 상태 | 라인 수 |
|------|------|---------|
| tests/conftest.py | 신규 | +195 |
| tests/test_cli_basic.py | 신규 | +186 |
| tests/test_strategy.py | 신규 | +315 |
| tests/test_db.py | 신규 | +298 |
| tests/test_output_formats.py | 신규 | +263 |
| tests/test_backtest.py | 신규 | +105 |
| tests/test_data.py | 신규 | +117 |
| tests/test_trade.py | 신규 | +126 |
| tests/test_monitor.py | 신규 | +140 |
| tests/test_optimize.py | 신규 | +178 |
| tests/integration/*.py | 신규 | +450 |
| tests/fixtures/*.py | 신규 | +380 |
| tests/README.md | 신규 | +260 |
| pytest.ini | 신규 | +45 |
| requirements-test.txt | 신규 | +25 |
| scripts/run_smoke_tests.* | 신규 | +200 |
| .github/workflows/cli-tests.yml | 신규 | +115 |
| **총계** | | **+3,398** |

---

### V2.36.U1.5.C2.0 (2026-02-03) - CLI 전체 기능 구현 완료

#### 개요
Phase 2-6 CLI 개발 완료. GUI의 모든 주요 기능을 CLI로 사용 가능.

#### Phase 2: 트레이딩 제어
- `cli/commands/trade.py` 신규 (689줄)
  - `stom trade start/stop/status` - 자동 매매 제어
  - `stom positions list/close` - 포지션 관리
  - `stom orders list/cancel` - 주문 관리
- `cli/runners/trade_runner.py` 신규 (496줄)
  - HeadlessTradeRunner 클래스

#### Phase 3: 실시간 모니터링
- `cli/commands/monitor.py` 신규 (439줄)
  - `stom monitor live` - 실시간 가격 스트림
  - `stom monitor pnl` - 손익 모니터링
  - `stom monitor positions` - 포지션 변동 알림

#### Phase 4: 최적화 기능
- `cli/commands/optimize.py` 신규 (823줄)
  - `stom optimize grid` - 그리드 서치
  - `stom optimize bayesian` - Optuna 베이지안
  - `stom optimize ga` - 유전 알고리즘
  - `stom optimize walkforward` - 워크포워드 분석
  - `stom optimize backfinder` - 변수 탐색
- `cli/runners/optimize_runner.py` 신규 (699줄)
  - HeadlessOptimizeRunner 클래스

#### Phase 5: 데이터 관리
- `cli/commands/db.py` 신규 (458줄)
  - `stom db create/append/delete` - DB 관리
  - `stom db info/vacuum/backup` - 유틸리티
- `cli/commands/strategy.py` 확장 (+200줄)
  - `stom strategy save/delete/import/validate` 추가

#### Phase 6: Docker 지원
- `Dockerfile` 신규 - CLI 전용 이미지
- `docker-compose.yml` 신규 - 서비스 구성
- `.dockerignore` 신규
- `requirements-cli.txt` 신규

#### 파일 변경 요약

| 파일 | 상태 | 라인 수 |
|------|------|---------|
| cli/commands/trade.py | 신규 | +689 |
| cli/commands/monitor.py | 신규 | +439 |
| cli/commands/optimize.py | 신규 | +823 |
| cli/commands/db.py | 신규 | +458 |
| cli/commands/strategy.py | 확장 | +200 |
| cli/runners/trade_runner.py | 신규 | +496 |
| cli/runners/optimize_runner.py | 신규 | +699 |
| cli/main.py | 수정 | +20 |
| Dockerfile | 신규 | +29 |
| docker-compose.yml | 신규 | +45 |
| .dockerignore | 신규 | +15 |
| requirements-cli.txt | 신규 | +26 |
| **총계** | | **+3,939** |

---

### V2.36.U1.5.C1.1 (2026-02-02) - CLI 백테스트 아키텍처 통합

#### 주요 변경 사항

**1. HeadlessBacktestRunner 완전 재작성 (backtest_runner.py)**
- 실제 BackTest 클래스와 동일한 아키텍처 구현
- 6개 큐 생성: windowQ, soundQ, totalQ, backQ, liveQ, teleQ
- 20개 BackSubTotal 프로세스 관리
- N개 BackEngine 프로세스 관리 (multi 설정값)
- 16가지 BackEngine 유형 지원:
  - 키움증권: Tick/Min × 주문관리 적용/미적용
  - 해외선물: Tick/Min × 주문관리 적용/미적용
  - 업비트: Tick/Min × 주문관리 적용/미적용
  - 바이낸스: Tick/Min × 주문관리 적용/미적용
- 13-튜플 파라미터 형식 준수 (betting, avgtime, startday, endday, starttime, endtime, buystg_name, sellstg_name, dict_cn, back_count, bl, schedul, back_club)
- 지연 로딩(Lazy Import)으로 레지스트리 접근 문제 해결

**2. CLI 백테스트 명령어 인터페이스 개선 (backtest.py)**
- `--buy-strategy`, `--sell-strategy` 분리 (기존 `--strategy` 대체)
- `--betting` 옵션 추가 (배팅금액: 주식 백만원, 선물 계약, 코인 USDT)
- `--avgtime` 옵션 추가 (평균값계산틱수, 기본값: 20)
- `--multi` 옵션 추가 (멀티프로세스 수, 기본값: 1)
- `--divid-mode` 옵션 추가 (분류방법: 종목코드별/일자별/한종목)
- `--blacklist/--no-blacklist` 플래그 추가

**3. 지연 로딩 적용 (runners/__init__.py)**
- `__getattr__` 방식으로 HeadlessBacktestRunner 지연 로딩
- import 시점의 레지스트리 접근 문제 해결
- Windows 권한 오류 방지

**4. 종합 보고서 작성**
- `docs/reports/CLI_Implementation_Report_V2.36.U1.5.C1.1.md` 생성
- 아키텍처 분석, 구현 상세, 사용 예시, Architect 검증 결과 포함
- 667줄 상세 기술 문서

#### 사용 예시

```bash
# 주식 백테스트 실행
python -m cli.main backtest run \
    --type stock \
    --buy-strategy "골든크로스" \
    --sell-strategy "손절매5%" \
    --start-date 20240101 \
    --end-date 20240131 \
    --betting 10 \
    --multi 4

# 코인 백테스트 실행
python -m cli.main backtest run \
    --type coin \
    --buy-strategy "RSI과매도" \
    --sell-strategy "RSI과매수" \
    --start-date 20240101 \
    --end-date 20240131 \
    --betting 100
```

#### 파일 변경

| 파일 | 변경 | 라인 수 |
|------|------|---------|
| cli/runners/backtest_runner.py | 재작성 | +676 |
| cli/commands/backtest.py | 수정 | +161 |
| cli/runners/__init__.py | 수정 | +14 |
| docs/reports/CLI_Implementation_Report_V2.36.U1.5.C1.1.md | 신규 | +667 |

---

### V2.36.U1.5.C1.1-patch1 (2026-02-02) - CLI 인터페이스 버그 수정

#### 수정 사항

**1. 백테스트 러너 통합**
- `backtest run` 커맨드가 `HeadlessBacktestRunner`와 연결되어 동기 실행 지원
- `--async` 플래그 없이 실행 시 즉시 백테스트 실행
- 실행 상태 (running → completed/failed) 자동 업데이트

**2. SQL Injection 취약점 수정**
- `strategy.py`: 테이블명 검증 추가 (whitelist 방식)
- `strategy.py`: SQL 식별자 인용 적용

**3. 중복 DataFrame 읽기 수정**
- `data.py`: export 함수에서 backtest 타입 중복 읽기 제거

**4. Import 오류 수정**
- `backtest_runner.py`: `QueueAdapter` → `CLIQueueAdapter` 수정
- `backtest_runner.py`: `CLIOutputAdapter` → `OutputAdapter` 수정

---

### V2.36.U1.5.C1.0 (2026-02-02) - CLI 인터페이스 개발

#### 개요
PyQt5 없이 STOM을 CLI(Command Line Interface)로 제어할 수 있는 인터페이스 개발 완료. 서버 환경, Docker 컨테이너, 자동화 스크립트 등 GUI가 불가능한 환경에서 STOM 활용 가능.

#### 신규 추가된 모듈

**1. CLI 패키지 구조**
```
cli/
├── __init__.py              # CLI 패키지 초기화
├── main.py                  # Click 기반 메인 진입점
├── adapters/                # PyQt5 → CLI 어댑터들
│   ├── settings_adapter.py  # 설정 로드 어댑터
│   ├── queue_adapter.py     # 큐 통신 어댑터
│   └── output_adapter.py    # 출력 포매팅 어댑터
├── commands/                # CLI 커맨드 그룹
│   ├── strategy.py          # 전략 관리 커맨드
│   ├── data.py              # 데이터 조회 커맨드
│   └── backtest.py          # 백테스트 커맨드
└── runners/                 # 헤드리스 실행기
    └── backtest_runner.py   # 백테스트 헤드리스 러너
```

**2. settings_adapter.py - PyQt5 없이 설정 로드**
- `load_settings_without_qt()`: setting.db에서 DICT_SET 로드
- `get_database_paths()`: 17개 데이터베이스 경로 반환
- `get_blacklists()`: 주식/선물/코인 블랙리스트 로드
- 암호화된 계정 정보 복호화 지원 (최대 8개 증권사, 2개 코인 API)
- 주문 관리 설정 완전 지원 (매수/매도 분할, 취소, 금지 조건)

**3. CLI 커맨드 구현**

전략 관리:
- `stom strategy list`: 전략 목록 조회
- `stom strategy show <name>`: 전략 상세 조회
- `stom strategy export <name> <file>`: 전략 내보내기
- `stom strategy stats`: 전략 통계

데이터 조회:
- `stom data trades`: 거래 내역 조회
- `stom data summary`: 거래 요약
- `stom data export`: 데이터 내보내기
- `stom data backtest-list`: 백테스트 목록
- `stom data backtest-result <id>`: 백테스트 결과

백테스트 실행:
- `stom backtest run --strategy <name> --type stock|coin|future`: 백테스트 실행
- `stom backtest list`: 백테스트 목록
- `stom backtest status <id>`: 상태 조회
- `stom backtest cancel <id>`: 취소
- `stom backtest delete <id>`: 결과 삭제

**4. backtest_runner.py - 헤드리스 백테스트**
- PyQt5 없이 백테스트 엔진 실행
- 멀티프로세스 기반 비동기 실행 지원
- BacktestStock, BacktestCoin 엔진 지원

#### 기술 스택
- CLI 프레임워크: Click 8.x
- 테이블 출력: tabulate
- 진행률 표시: tqdm
- 데이터 처리: pandas, sqlite3
- 프로세스 통신: multiprocessing.Queue

#### 사용 예시
```bash
# 버전 확인
python -m cli.main --version

# 주식 전략 목록 조회
python -m cli.main strategy list --type stock

# 백테스트 실행
python -m cli.main backtest run --strategy "전략1" --type stock --start-date 2024-01-01 --end-date 2024-12-31

# 거래 내역 조회
python -m cli.main data trades --type stock --date 2024-12-31 --format json
```

#### 신규 파일
| 파일 | 라인 수 | 설명 |
|------|---------|------|
| `cli/__init__.py` | 11 | CLI 패키지 초기화 |
| `cli/main.py` | 29 | Click 기반 메인 진입점 |
| `cli/adapters/__init__.py` | 10 | 어댑터 패키지 |
| `cli/adapters/settings_adapter.py` | 330 | 설정 로드 어댑터 |
| `cli/adapters/queue_adapter.py` | 45 | 큐 통신 헬퍼 |
| `cli/adapters/output_adapter.py` | 103 | 출력 포매팅 |
| `cli/commands/__init__.py` | 10 | 커맨드 패키지 |
| `cli/commands/strategy.py` | 112 | 전략 관리 커맨드 |
| `cli/commands/data.py` | 165 | 데이터 조회 커맨드 |
| `cli/commands/backtest.py` | 136 | 백테스트 커맨드 |
| `cli/runners/__init__.py` | 10 | 러너 패키지 |
| `cli/runners/backtest_runner.py` | 191 | 백테스트 헤드리스 러너 |

**총 12개 파일, 약 1,152 라인**

#### 활용 사례
1. **서버 환경**: GUI 없는 Linux 서버에서 백테스트 실행
2. **자동화**: Bash/PowerShell 스크립트로 배치 작업
3. **CI/CD**: GitHub Actions, Jenkins 등에서 전략 검증
4. **Docker**: 컨테이너 기반 배포 및 스케일링
5. **원격 접속**: SSH를 통한 원격 제어

#### 향후 계획
- Phase 2: 실거래 제어 (trade start/stop/status)
- Phase 3: 실시간 모니터링 (WebSocket)
- Phase 4: 스케줄링 (Cron)
- Phase 5: Docker 지원

#### 상세 문서
- 전체 개발 보고서: `docs/update_log/20260202_cli_interface.md`

---

### V2.36.U1.5 (2026-02-01) - 시리얼키 기능 제거

#### 변경 사항

**1. 시리얼키 GUI 요소 제거**
- 파일: `ui/set_setup_tap.py`
- 제거된 위젯:
  - `sj_etc_labelll_02` (시리얼키 라벨)
  - `sj_etc_liEditt_01` (시리얼키 입력필드)
  - `sj_etc_daEditt_01` (만료날짜 DateEdit)

**2. 시리얼키 로드/저장 코드 제거**
- 파일: `ui/ui_button_clicked_settings.py`
  - `setting_load_08()`: 시리얼키 로드 코드 제거
  - `setting_save_08()`: 시리얼키 저장 및 암호화 코드 제거
  - `setting_acc_view()`: 시리얼키 필드 EchoMode 토글 제거
- 파일: `ui/ui_return_press.py`
  - `return_press_setting_pass()`: 시리얼키 필드 EchoMode 설정 제거

**3. 시리얼키 dict_set 항목 제거**
- 파일: `utility/setting.py`
- 제거: `'시리얼키': de_text(EN_KEY, df_e['시리얼키'][0])` 항목

**4. 시리얼키 DB 스키마 변경**
- 파일: `utility/database_check.py`
- 변경: `etc` 테이블에서 `시리얼키` 컬럼 정의 제거
- 참고: 기존 DB의 시리얼키 컬럼은 유지되며 무시됨 (하위 호환성)

#### 변경 이유
- .pyd → .py 마이그레이션 완료로 시리얼키 보호 불필요
- 오픈소스 운영 방침에 따른 인증 기능 제거

#### 유지되는 기능
- 암호화 인프라 (`en_text()`, `de_text()`, `read_key()`, `write_key()`)
- 계정, API 키, 텔레그램 토큰 등 민감 정보 암호화
- STOM Live 체크박스 및 관련 코드 (비활성화 상태 유지)

#### 수정된 파일
| 파일 | 수정 내용 |
|------|----------|
| `ui/set_setup_tap.py` | 시리얼키 라벨, 입력필드, 만료날짜 위젯 제거 |
| `ui/ui_button_clicked_settings.py` | 시리얼키 로드/저장/암호화 코드 제거 |
| `ui/ui_return_press.py` | 시리얼키 필드 EchoMode 설정 제거 |
| `utility/setting.py` | dict_set에서 시리얼키 항목 제거 |
| `utility/database_check.py` | DB 스키마에서 시리얼키 컬럼 제거 |

---

### V2.36.U1.4 (2026-02-01) - codename 테이블 에러 핸들링 개선

#### 수정된 버그

**1. DatabaseError: no such table: codename**
- 위치: `ui/ui_mainwindow.py:317-319`
- 원인: 주식 로그인 전 `codename` 테이블이 존재하지 않음
- 해결:
  - 중첩 try/except로 양쪽 DB 모두 실패 시 처리
  - 빈 DataFrame으로 초기화하여 프로그램 계속 실행 가능
  - 사용자에게 경고 메시지 출력

---

### V2.36.U1.3 (2026-02-01) - ElapsedTickNumber 메서드 추가

#### 수정된 버그

**1. AttributeError: 'MainWindow' object has no attribute 'SettingStockElapsedTickNumberSample'**
- 위치: `ui/set_dialog_etc.py:373`
- 원인: 메서드명 불일치 (setButtonClicked_01 vs SettingStockElapsedTickNumberSample)
- 해결: `ui/ui_mainwindow.py`에 명시적 메서드 추가
  - `SettingStockElapsedTickNumberSample()`
  - `SettingStockElapsedTickNumberLoad()`
  - `SettingStockElapsedTickNumberSave()`
  - `SettingCoinElapsedTickNumberSample()`
  - `SettingCoinElapsedTickNumberLoad()`
  - `SettingCoinElapsedTickNumberSave()`
- Legacy alias 유지 (setButtonClicked_*, cetButtonClicked_*)

#### 문서 추가
- CLAUDE.md: 프로젝트 가이드라인 및 버전 네이밍 규칙 추가

---

### V2.36.U1.2 (2026-02-01) - 런타임 에러 수정

#### 수정된 버그

**1. NameError: 'int_hms' is not defined**
- 위치: `ui/ui_mainwindow.py:298`
- 원인: `int_hms()` 함수가 utility/static.py에 정의되지 않음
- 해결: `utility/static.py`에 `int_hms()` 함수 추가
  ```python
  def int_hms(std_time=None):
      if std_time is not None:
          return int(strf_time('%H%M%S', std_time))
      else:
          return int(strf_time('%H%M%S'))
  ```

**2. AttributeError: 'NoneType' object has no attribute 'read_sql'**
- 위치: `ui/ui_activated_*.py` 모듈들
- 원인: `self.dbreader`가 `None`으로 초기화되어 있음
- 해결:
  - `DatabaseReadOnly` import 추가
  - `self.dbreader = DatabaseReadOnly()`로 초기화

**3. AttributeError: 'MainWindow' object has no attribute 'ManualSaveAndExit'**
- 위치: `ui/set_main_menu.py:71`
- 원인: `ManualSaveAndExit()` 메서드가 정의되지 않음
- 해결: `ui/ui_mainwindow.py`에 메서드 추가
  ```python
  def ManualSaveAndExit(self):
      self.SettingAllSave()
      self.close()
  ```

#### 검증 결과
- 구문 검사: 통과
- int_hms() 함수 테스트: 정상 동작 (예: 181039 반환)

#### 문서 업데이트
- docs/update_log/2026-01-31_analysis_v1_vs_v2.md: 종합 마이그레이션 분석 보고서 업데이트

---

### V2.36.U1 (2026-01-31) - ui_mainwindow.pyd → ui_mainwindow.py 마이그레이션

#### 변경 사항

**1. ui/ui_mainwindow.py 생성**
- V1.10 원본 소스(commit 80ab4ec)를 기반으로 V2.36 모듈 구조에 맞게 업데이트
- 13개 모듈명 변경 반영
- 13개 신규 editer 모듈 import 추가
- STOM Live 인증 시스템 비활성화

**2. 누락된 메서드 54개 추가**
- Settings Load/Save: SettingLoad_01~08, SettingSave_01~08 (16개)
- Settings Management: SettingAllLoad, SettingAllApp, SettingAllDel, SettingAllSave, SettingAccView (5개)
- Order Settings: SettingOrderLoad_01~04, SettingOrderSave_01~04 (8개)
- Weight Control: SettingStockWeightControl, SettingCoinWeightControl 및 Load/Save/Changed (8개)
- Elapsed Tick Number: SettingStockElapsedTickNumber, SettingCoinElapsedTickNumber (2개)
- Indicator Settings: IndicatorSettingBasic, IndicatorSettingLoad, IndicatorSettingSave, GetIndicatorDetail (4개)
- Scheduler: StopScheduler (1개)
- Activated: dActivated_02 (1개)

**3. utility/telegram_msg.py 생성**
- TelegramMsg 함수 정의 (TelegramBot 래퍼)
- Process target으로 사용 가능한 구조

**4. .gitignore 업데이트**
- *.pyd.backup 추가

**5. 문서 추가**
- docs/README.md
- docs/update_log/2026-01-31_ui_mainwindow_migration.md
- docs/update_log/2026-01-31_f2aa6be_review.md

#### 삭제된 파일
- ui/ui_mainwindow.pyd (백업: ui_mainwindow.pyd.backup)

#### 영향받는 모듈
- ui/set_setup_tap.py - SettingLoad_*, SettingSave_* 메서드 사용
- ui/set_dialog_chart.py - IndicatorSetting* 메서드 사용
- ui/set_dialog_etc.py - WeightControl, ElapsedTickNumber 메서드 사용
- ui/set_order_tap.py - SettingOrderLoad_*, SettingOrderSave_* 메서드 사용
- ui/ui_button_clicked_dialog_backengine.py - StopScheduler 메서드 사용

#### 검증 결과
- 구문 검사 (py_compile): 통과
- Import 구조: V2.36 모듈 구조 반영 완료
- 메서드 정의: 모든 참조 메서드 존재 확인

---

### V2.36 (이전)
- ui_mainwindow.pyd 컴파일 버전 사용
