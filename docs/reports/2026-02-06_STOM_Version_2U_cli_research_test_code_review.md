# STOM 현재 브랜치 종합 코드 검토 보고서

## 1. 메타 정보
- 검토 대상 브랜치: `STOM_Version_2U-cli-research-test`
- 검토 일시: 2026-02-06
- 검토 범위: 프로젝트 전체 코드(정적 검토) + 자동 테스트 실행 + 주요 CLI 실동작 점검
- 검토 기준: 기능 정합성, DB 스키마 정합성, 테스트 신뢰도, 운영 안정성, 유지보수성

---

## 2. 한눈에 보는 결론 (Executive Summary)
- 현재 상태는 **“CLI 명령 집합은 넓게 구현되어 있으나, 실제 DB 스키마 정합성/테스트 신뢰도 부족으로 완성도는 중간 이하”**로 판단됩니다.
- `pytest`는 통과하지만(202 pass), 다수 테스트가 `exit_code in [0,1,2]`를 허용해 **실제 기능 결함을 가립니다**.
- `data`, `trade`, `monitor` 일부는 **실 DB 컬럼/테이블과 불일치**해 정상 데이터 환경에서도 실패 또는 무의미한 결과를 반환할 가능성이 큽니다.
- 버전 표기(`C2.3` vs `C2.0` vs `C1`)와 `RuntimeWarning`이 있어 **릴리스 일관성/신뢰성**이 떨어집니다.

핵심 수치:
- Python 파일 수: **186개**
- Python 코드 라인 수: **54,209 lines**
- 테스트 결과: **202 passed, 1 skipped**
- 커버리지(`--cov=cli`): **31%**
- 문법 컴파일 체크(`compileall`): **성공**

---

## 3. 수행한 검토/테스트

### 3.1 실행 명령
- `python -m pytest tests/ -v --tb=short`
- `python -m pytest tests/ --cov=cli --cov-report=term-missing --tb=short`
- `python -m compileall cli backtester utility stock coin future ui`
- `python -m cli.main --version`
- `python -m cli.main --help`
- `python -m cli.main db info --type strategy --format json`
- `python -m cli.main data backtest-list --format json`
- `python -m cli.main backtest list --format json`
- `python -m cli.main positions list --format json`
- `python -m cli.main orders list --format json`

### 3.2 요약 결과
- 테스트: `202 passed, 1 skipped` (skip 사유: `tabulate` 미설치 시 markdown 변환 테스트 skip)
- 커버리지: CLI 총 31%
  - `cli/runners/backtest_runner.py`: 0%
  - `cli/runners/optimize_runner.py`: 0%
  - `cli/runners/trade_runner.py`: 0%
  - `cli/commands/monitor.py`: 18%
  - `cli/commands/optimize.py`: 25%
- 문법 검사: compileall 기준 치명적 문법 오류 없음
- 런타임: `python -m cli.main` 실행 시 `RuntimeWarning` 반복 발생

---

## 4. 주요 발견사항 (중요도 순)

## [Critical] 1) `data` 명령의 DB 스키마 불일치로 실기능 실패
- 근거 코드:
  - `cli/commands/data.py:48`
  - `cli/commands/data.py:50`
  - `cli/commands/data.py:129`
  - `cli/commands/data.py:133`
  - `cli/commands/data.py:205`
- 실제 확인:
  - `python -m cli.main data backtest-list --format json` 실행 시 `no such column: datetime`
- 원인:
  - `backtest_results` 스키마는 `created_at` 중심인데, 코드에서 `datetime` 기준 정렬
  - 거래 요약 쿼리에서 `profit`, `status`, `datetime` 컬럼을 가정하나 실제 `tradelist.db` 스키마와 불일치
- 영향:
  - 데이터 조회/리포트 기능 신뢰성 저하
  - 실운영에서 장애성 에러 가능

## [High] 2) `trade`/`monitor`와 실제 `tradelist.db` 테이블명 불일치
- 근거 코드:
  - `cli/commands/trade.py:369`
  - `cli/commands/trade.py:536`
  - `cli/commands/monitor.py:106`
  - `cli/runners/trade_runner.py:218`
  - `cli/runners/trade_runner.py:340`
- 실제 DB 스키마:
  - 예: `s_jangolist`, `c_jangolist`, `f_jangolist`, `s_chegeollist` ...
- 코드 가정:
  - `%position%`, `%order%`, `stockjangolist`, `chegeollist`, `jumunlist`
- 영향:
  - 정상 데이터가 있어도 포지션/주문 조회 결과가 비정상 또는 빈값으로 나올 가능성 큼

## [High] 3) `db info --format` 옵션이 사실상 동작하지 않음
- 근거 코드:
  - `cli/commands/db.py:287`
- 원인:
  - `adapter.output(df, OutputFormat(output_format))` 호출로 `OutputFormat`이 제목 파라미터로 전달됨
  - 포맷 설정 자체는 반영되지 않음
- 실제 확인:
  - `--format json` 실행 시 JSON이 아니라 테이블 포맷 출력 + 타이틀에 `OutputFormat.JSON` 표기

## [High] 4) 테스트가 결함을 가리는 구조 (신뢰도 낮음)
- 근거 코드:
  - `tests/test_trade.py:39` 등 다수
  - `tests/test_backtest.py:54` 등 다수
  - `tests/test_optimize.py:43` 등 다수
  - `tests/test_trade.py:45` (`--market` 사용)
  - `tests/test_backtest.py:46` (`--market` 사용)
  - `tests/test_optimize.py:51` (`--param`, `--train-window` 등 현재 구현과 다른 옵션 사용)
- 정량:
  - `assert result.exit_code in [0, 1, 2]`: 51건
  - `assert result.exit_code in [0, 2]`: 21건
  - `assert result.exit_code in [0, 1]`: 36건
- 영향:
  - 명령어가 실패해도 테스트 통과
  - 회귀 방지 역할 약화

## [Medium] 5) `optimize` 전략 존재 확인 로직과 실제 전략 DB 테이블명 불일치
- 근거 코드:
  - `cli/commands/optimize.py:97`
  - `cli/commands/optimize.py:105`
  - `cli/commands/optimize.py:112`
- 원인:
  - 코드에서 `stock_buy`/`coin_buy`/... 형태 가정
  - 실제 스키마는 `stockbuy`/`coinbuy`/... 형태
- 영향:
  - 전략 존재 확인 결과 신뢰도 저하(거짓 경고 발생 가능)

## [Medium] 6) 버전 표기 불일치 + 런타임 경고
- 근거 코드:
  - `cli/main.py:13` (`2.36.U1.5.C2.0`)
  - `cli/__init__.py:8` (`2.36.U1.5.C1`)
  - `docs/AGENTS.md:4` (`V2.36.U1.5.C2.3`)
  - `cli/__init__.py:11` (`from .main import main`)
- 영향:
  - 배포/문서/실행 버전 불일치
  - `python -m cli.main` 실행 시 `RuntimeWarning` 발생

## [Medium] 7) 핵심 러너 경로 테스트 공백
- 근거:
  - 커버리지 결과에서 러너 계층 0%
- 대상:
  - `cli/runners/backtest_runner.py`
  - `cli/runners/optimize_runner.py`
  - `cli/runners/trade_runner.py`
- 영향:
  - 실제 실행 플로우 안정성 검증 부족

## [Medium] 8) Placeholder 구현 구간 다수
- 근거 코드:
  - `cli/runners/trade_runner.py:102`
  - `cli/runners/trade_runner.py:108`
  - `cli/runners/trade_runner.py:147`
  - `cli/runners/trade_runner.py:315`
  - `cli/commands/optimize.py:208`
- 영향:
  - 사용자 입장에서 “실행 가능해 보이지만 실제 미구현”인 기능 존재

---

## 5. 완료 내용 (현재 잘 되어 있는 부분)
- CLI 명령 그룹 구조 자체는 폭넓게 구성됨 (`strategy`, `data`, `backtest`, `trade`, `monitor`, `optimize`, `db`)
- 자동 테스트 프레임워크(파일 구조, fixture, integration test 골격) 구축됨
- 문서 구조(`docs/`)와 운영 스크립트(`scripts/run_smoke_tests.*`) 준비됨
- 대규모 모듈 컴파일이 가능하고 즉시 파싱 에러는 없음
- 백테스트/최적화 명령의 작업 이력 저장 흐름(테이블 생성/저장)은 기본 동작 확인됨

---

## 6. 부족 내용 (완성도 관점)
- DB 스키마 계약(contract) 부재로 명령별 쿼리가 제각각 가정됨
- “통과하는 테스트”와 “동작하는 기능” 사이의 갭이 큼
- 릴리스 버전 단일 소스가 없어 문서/코드 버전이 분기됨
- 미구현 기능이 런타임에서 명확히 구분되지 않아 사용자 오해 가능
- 커버리지가 낮아 핵심 경로의 장애 조기탐지 능력이 부족

---

## 7. 개선 내용

### 7.1 즉시(우선순위 P0)
1. `data` 쿼리의 컬럼/테이블 매핑을 실제 스키마 기준으로 수정
2. `db info` 포맷 옵션 버그 수정 (`OutputAdapter` 사용 방식 정정)
3. 버전 상수 단일화(예: `cli/version.py` 1원화)
4. `cli/__init__.py`의 eager import 제거(경고 제거)

### 7.2 단기(우선순위 P1)
1. `trade`/`monitor`의 테이블명 매핑 표준화 (`s_/c_/f_` prefix 지원)
2. `optimize` 전략 검증 로직을 실제 테이블명(`stockbuy` 등) 기준으로 수정
3. 테스트를 “성공/실패 명확 검증”으로 변경 (`[0,1,2]` 허용 제거)
4. 테스트 옵션을 실제 CLI 옵션과 동기화 (`--market` → `--type` 등)

### 7.3 중기(우선순위 P2)
1. 러너 계층 통합 테스트 추가 (최소 mock 기반 end-to-end)
2. DB 스키마 검증 테스트(테이블/컬럼 존재 체크) 추가
3. Placeholder 기능에 `--experimental` 또는 명확한 비지원 오류코드 도입

---

## 8. 개선 방법 (구체 실행안)

## 방법 A: DB 스키마 어댑터 계층 도입
- `cli/adapters/schema_adapter.py` 신설
- 역할:
  - 시장별 테이블 매핑 통합
  - 표준 컬럼 alias 제공 (`체결시간` ↔ `datetime` 등)
- 기대효과:
  - 명령 모듈에서 SQL 중복/불일치 제거
  - DB 변경 시 adapter만 수정

## 방법 B: 테스트 재작성 전략
- 1차:
  - `exit_code`를 목적별로 엄격화(성공 케이스는 `== 0`)
  - 잘못된 옵션을 쓰는 테스트 케이스 정리
- 2차:
  - 명령 출력 JSON schema 검증 도입
  - 실패 케이스 메시지/에러코드 검증 추가

## 방법 C: 버전/릴리스 표준화
- `VERSION` 또는 `cli/version.py`를 단일 진실 소스로 사용
- `cli/main.py`, `cli/__init__.py`, `docs/*`는 자동 반영
- 릴리스 전 체크리스트에 “버전 일치 검사” 필수화

---

## 9. 개발 안내 (팀 운영 가이드)

### 9.1 개발 원칙
- “명령 추가”보다 “스키마 계약 + 테스트 보장”을 먼저 맞춘다.
- DB 접근은 직접 SQL 난립 대신 adapter 계층을 통해 수행한다.
- 미구현 기능은 사용자에게 성공처럼 보이게 하지 않는다.

### 9.2 권장 PR 체크리스트
1. `pytest tests/ -v --tb=short` 통과
2. `pytest tests/ --cov=cli --cov-report=term-missing`에서 커버리지 하락 없음
3. 신규/수정 명령은 성공/실패/경계값 테스트 포함
4. 문서 버전과 실행 버전 일치
5. `python -m cli.main --help` 및 해당 명령 `--help` 수동 점검

### 9.3 권장 품질 목표 (다음 마일스톤)
- 커버리지: `31% → 55%+`
- 러너 계층: `0% → 35%+`
- 느슨한 테스트(`in [0,1,2]`) 비율: 대폭 축소
- 주요 명령(`data`, `trade`, `monitor`, `db`) 스키마 불일치 0건

---

## 10. 2주 개선 로드맵 (실행 가능한 형태)

### Week 1
1. DB 스키마 매핑 어댑터 도입
2. `data`/`db info` 치명 버그 수정
3. 버전 단일화 및 `RuntimeWarning` 제거
4. 회귀 테스트 20건 보강

### Week 2
1. `trade`/`monitor` 명령의 스키마 정합성 전면 수정
2. 테스트 옵션 동기화 및 느슨한 assertion 제거
3. 러너 계층 통합 테스트 추가
4. 문서/사용자 가이드 업데이트

---

## 11. 문서 통합 기반 개발 업데이트 계획 (브랜치 목적 정렬)

본 섹션은 `docs/` 전체 문서(AGENTS/README/change_log/research/update_log/reports) 맥락을 합쳐, 현재 브랜치 목적에 맞는 실질 업데이트 계획으로 재정의한 것입니다.

### 11.1 브랜치 목적 재정의
- 1차 목적: AI 에이전트가 **안정적으로 호출 가능한 CLI** 확보
- 2차 목적: GUI 없이 서버/배치 환경에서 **일관된 결과 재현** 보장
- 3차 목적: “테스트 통과”가 아니라 “기능 신뢰성”을 보장하는 **검증 체계 고도화**
- 4차 목적: 버전/문서/명령 동작을 일치시키는 **운영 표준화**

### 11.2 버전 타깃 기반 업데이트 계획

| 버전 타깃 | 기간(권장) | 핵심 목표 | 핵심 작업 | 완료 기준(DoD) |
|------|------|------|------|------|
| **C2.5 (Stabilization-1)** | 1주 | DB 정합성 복구 | `data/trade/monitor/db`의 테이블/컬럼 매핑 통일, `db info --format` 버그 수정, `RuntimeWarning` 제거, 버전 상수 단일화 | `data backtest-list`, `positions list`, `orders list`, `db info --format json`가 정상 출력 |
| **C2.6 (Test-Reliability)** | 1주 | 테스트 신뢰도 복구 | 느슨한 assertion 제거, 테스트 옵션을 실제 CLI와 동기화, 실패 케이스 명시 검증 | `exit_code in [0,1,2]` 패턴 사실상 제거, 잘못된 옵션 테스트 정리 완료 |
| **C2.7 (Runner-Hardening)** | 1~2주 | 실행 경로 안정화 | 러너 계층(backtest/trade/optimize) 통합 테스트 추가, placeholder 기능은 명확한 비지원 응답/experimental 분리 | 러너 계층 커버리지 유의미하게 상승, 미구현 기능의 오해 소지 제거 |
| **C2.8 (AI-Ready CLI)** | 1주 | AI 자동화 친화성 강화 | JSON 출력 스키마 표준화, 에러코드/메시지 표준화, CLI 매뉴얼/AGENTS 동기화 | AI가 파싱 가능한 일관 출력 및 오류 응답 체계 확립 |

### 11.3 스트림별 상세 작업

| 스트림 | 범위 파일 | 작업 항목 | 검증 명령 |
|------|------|------|------|
| DB 스키마 계약 | `cli/commands/data.py`, `cli/commands/trade.py`, `cli/commands/monitor.py`, `cli/adapters/*` | DB alias/매핑 계층 도입, 하드코딩 쿼리 정리 | `python -m cli.main data backtest-list --format json`, `python -m cli.main positions list --format json` |
| 테스트 신뢰도 | `tests/test_*.py`, `tests/integration/*.py` | 느슨한 exit code 허용 제거, 실제 옵션 기준 재작성 | `python -m pytest tests/ -v --tb=short` |
| 러너 안정화 | `cli/runners/*.py`, `tests/integration/*` | 실행/종료/예외/자원정리 경로 검증 | `python -m pytest tests/ --cov=cli --cov-report=term-missing` |
| 버전/문서 일치 | `cli/main.py`, `cli/__init__.py`, `docs/*` | 단일 버전 소스 적용, 문서 버전 자동 동기화 규칙 적용 | `python -m cli.main --version`, 문서 버전 문자열 교차검증 |

### 11.4 문서 반영 규칙 (운영 강제)
- 코드 변경과 동시에 아래 3종 문서를 묶어 업데이트
- 1. `docs/change_log/change_log.md`: 버전/변경 항목
- 2. `docs/update_log/YYYYMMDD_*.md`: 작업 의도/구현/검증 로그
- 3. `docs/reports/*.md`: 종합 결과(테스트/품질/리스크)

문서 업데이트가 없는 기능 PR은 “완료”로 간주하지 않음.

### 11.5 이번 브랜치 즉시 실행 순서 (권장)
1. `C2.5`: DB 정합성 + 버전/경고 이슈를 먼저 처리
2. `C2.6`: 테스트 재작성으로 회귀 방지 장치 복구
3. `C2.7`: 러너 경로 통합 테스트 및 미구현 경계 명확화
4. `C2.8`: AI 파싱 안정화를 위한 JSON/에러 표준화

### 11.6 품질 게이트 (머지 기준)
- `python -m pytest tests/ -v --tb=short` 통과
- `python -m pytest tests/ --cov=cli --cov-report=term-missing`에서 이전 대비 하락 없음
- `python -m cli.main --version` 결과와 `docs` 버전 표기 일치
- 주요 명령 6개 스모크 테스트 통과:
  - `strategy list`
  - `db info --type strategy --format json`
  - `data backtest-list --format json`
  - `backtest list --format json`
  - `positions list --format json`
  - `optimize list --format json`

---

## 12. 최종 판단
- 현재 브랜치는 “기능 뼈대와 문서화는 우수하나, 실데이터 정합성과 테스트 엄격성 부족으로 완성도 고도화가 필요한 상태”입니다.
- 우선순위는 **DB 스키마 정합성 복구 + 테스트 신뢰도 복구**입니다.
- 위 P0/P1 항목을 처리하면 CLI 신뢰성은 단기간 내 체감 개선이 가능합니다.

---

## 13. 개발 업데이트 실행 결과 (2026-02-06 반영)

본 섹션은 11장 계획(C2.5~C2.8) 기준으로 실제 반영 결과를 업데이트한 내용입니다.

### 13.1 단계별 완료 현황

| 단계 | 상태 | 완료 내용 |
|------|------|------|
| C2.5 (Stabilization-1) | 완료 | `schema_adapter` 도입, `data/trade/monitor/db` 스키마 정합화, 버전 상수 단일화, `db info --format` 수정 |
| C2.6 (Test-Reliability) | 완료 | `test_data/test_trade/test_monitor/test_backtest/test_optimize` 재작성, 느슨한 exit code 허용 제거 |
| C2.7 (Runner-Hardening) | 완료 | `trade/backtest` 러너 경계 동작 명확화, `tests/test_runners.py`, `tests/test_schema_contract.py` 신규 추가 |
| C2.8 (AI-Ready CLI) | 완료 | JSON/CSV 출력 파싱 안정화, JSON 에러 응답 표준 구조 도입, 문서 버전/링크 동기화 |

### 13.2 반영 파일 요약
- 코드:
  - `cli/adapters/schema_adapter.py`
  - `cli/adapters/output_adapter.py`
  - `cli/commands/data.py`
  - `cli/commands/monitor.py`
  - `cli/commands/optimize.py`
  - `cli/commands/backtest.py`
  - `cli/commands/db.py`
  - `cli/runners/backtest_runner.py`
  - `cli/runners/trade_runner.py`
  - `cli/version.py`
- 테스트:
  - `tests/test_data.py`
  - `tests/test_trade.py`
  - `tests/test_monitor.py`
  - `tests/test_backtest.py`
  - `tests/test_optimize.py`
  - `tests/test_output_formats.py`
  - `tests/test_runners.py`
  - `tests/test_schema_contract.py`
- 문서:
  - `docs/AGENTS.md`
  - `docs/README.md`
  - `docs/CLI_User_Manual.md`
  - `docs/change_log/change_log.md`
  - `docs/update_log/20260206_cli_stabilization_c25_c28.md`

### 13.3 실행 검증 결과
- `python -m pytest tests/test_data.py tests/test_trade.py tests/test_monitor.py tests/test_backtest.py tests/test_optimize.py -q`
  - 결과: `70 passed`
- `python -m pytest tests/test_runners.py tests/test_schema_contract.py tests/test_output_formats.py tests/test_data.py tests/test_monitor.py tests/test_optimize.py tests/test_backtest.py -q`
  - 결과: `95 passed, 1 skipped`

### 13.4 개발 안내 (운영용)
1. 신규 명령/쿼리 추가 시, DB 접근은 `schema_adapter`를 경유하고 하드코딩 SQL 가정을 금지한다.
2. CLI JSON 출력은 파싱 가능해야 하며, title/배너는 JSON/CSV에서 사용하지 않는다.
3. 예외 처리 시 JSON 포맷 명령은 `OutputAdapter.format_error(..., output_format=OutputFormat.JSON, error_code=...)`를 사용한다.
4. 러너 계층 변경 시 `tests/test_runners.py`와 `tests/test_schema_contract.py`를 함께 업데이트한다.
5. 릴리스 전에는 최소 아래 4개를 품질 게이트로 고정한다.
   - `python -m cli.main --version`
   - `python -m pytest tests/ -v --tb=short`
   - `python -m cli.main db info --type strategy --format json`
   - `python -m cli.main data backtest-list --format json`

### 13.5 잔여 리스크
- `trade.py` 인코딩 깨짐 이슈는 C2.9에서 정리되어 해소됨.
- 러너 계층 커버리지는 추가되었으나, 실제 장시간 백테스트/최적화 실행 시나리오 통합 테스트는 더 보강 필요.

---

## 14. 후속 단계 진행 Status (C2.9)

### 14.1 진행 결과
- `trade.py` 인코딩 깨짐 정리: **완료**
- 러너/스키마 테스트 CI 필수화: **완료**
- JSON 응답 계약 문서화: **완료**

### 14.2 근거 파일
- `cli/commands/trade.py`
- `.github/workflows/cli-tests.yml`
- `docs/CLI_User_Manual.md` (JSON 응답 계약 섹션)

### 14.3 현재 상태 요약
- 계획했던 C2.8 후속 권장사항 1~3번은 모두 실행 완료.
- 실행 버전은 `2.36.U1.5.C2.9`로 상향.
- 테스트/명령 실행 기준 회귀 없음.

### 14.4 다음 단계(권장)
1. `tests/test_trade.py`에 `positions/orders` JSON payload 필드 검증 추가
2. coverage 파이프라인에서 runner/schema 전용 커버리지 추적 지표 추가
3. JSON 계약을 독립 계약 문서로 분리해 변경 관리 강화

---

## 15. 다음 단계 실행 Status (C2.10)

### 15.1 실행 완료 항목
1. `tests/test_trade.py` JSON payload 검증 추가: 완료
2. coverage 파이프라인 runner/schema 전용 지표 추가: 완료
3. JSON 계약 독립 문서 분리: 완료 (`docs/contracts/CLI_JSON_Contract.md`)

### 15.2 현재 상태
- C2.9에서 제시한 다음 단계 1~3번이 모두 반영됨.
- 버전은 `2.36.U1.5.C2.10`으로 상향됨.

### 15.3 다음 권장 단계
1. `tests/test_trade.py`에 `positions close`/`orders cancel` 실패 JSON 에러 코드 계약 테스트 추가
2. CI coverage 단계에서 runner/schema 커버리지 하한선(`--cov-fail-under`) 도입 검토
3. JSON 계약 문서에 실제 샘플(성공/빈결과/에러) 회귀 테스트 링크 표 추가

---

## 16. 다음 단계 실행 Status (C2.11)

### 16.1 실행 완료 항목
1. `positions close`/`orders cancel` 실패 JSON 에러 코드 계약 테스트 추가: 완료
2. runner/schema 커버리지 하한선(`--cov-fail-under=35`) 적용: 완료
3. JSON 계약 문서 샘플/테스트 링크 표 추가: 완료

### 16.2 현재 상태
- C2.10에서 제시한 다음 단계 1~3번이 모두 반영됨.
- 버전은 `2.36.U1.5.C2.11`로 상향됨.

### 16.3 다음 권장 단계
1. `tests/test_trade.py`에 성공 케이스(`positions close --all`, `orders cancel --all`) JSON payload 필드 상세 검증 추가
2. CI coverage 하한선을 전체 CLI 단계로 확장할지 기준값 정의
3. `docs/contracts/CLI_JSON_Contract.md`를 기준으로 명령별 JSON schema 자동검증(예: jsonschema) 도입 검토

---

## 17. 다음 단계 실행 Status (C2.12)

### 17.1 실행 완료 항목
1. 성공 케이스 JSON payload 검증 추가: 완료
2. 전체 CLI coverage 하한선 확장(`--cov-fail-under=50`): 완료
3. jsonschema 자동검증 도입: 완료 (`tests/test_json_contract_schema.py`)

### 17.2 현재 상태
- C2.11에서 제시한 다음 단계 1~3번이 모두 반영됨.
- 버전은 `2.36.U1.5.C2.12`로 상향됨.
- 전체 CLI 커버리지 기준은 약 54%로 하한선(50%)을 충족.

### 17.3 다음 권장 단계
1. `tests/test_json_contract_schema.py`에 optimize/backtest 상태 명령 스키마 검증 확대
2. CI에서 커버리지 하한선을 단계적으로 상향(예: 50 → 55)
3. 계약 문서(`docs/contracts/CLI_JSON_Contract.md`)를 명령별 변경 이력 표와 함께 관리

---

## 18. 다음 단계 실행 Status (C2.13)

### 18.1 실행 완료 항목
1. `tests/test_json_contract_schema.py`에 `backtest/optimize list/status` JSON schema 검증 확대: 완료
2. `unknown_job_id` 상태 조회 응답(`{"message": ...}`) 계약 검증 추가: 완료
3. 상태 조회 성공 계약 검증 안정화(DB 최신 작업 ID 기반): 완료

### 18.2 현재 상태
- C2.12에서 제시한 다음 권장 단계 1번(상태 명령 스키마 검증 확대)이 반영됨.
- 버전은 `2.36.U1.5.C2.13`으로 상향됨.
- 전체 테스트는 `234 passed, 1 skipped`로 통과.
- 전체 CLI 커버리지는 약 54.67%로 50% 하한선을 충족.

### 18.3 다음 권장 단계
1. CI 전체 coverage 하한선을 `50 -> 55`로 상향하고, 실패 시 리포팅 메시지를 표준화
2. `docs/contracts/CLI_JSON_Contract.md`에 명령별 계약 변경 이력 표(버전/변경 필드/테스트)를 추가
3. `optimize/backtest run` 성공 payload에 대한 스키마 검증을 별도 섹션으로 분리해 계약 범위를 명확화

---

## 19. 다음 단계 실행 Status (C2.14)

### 19.1 실행 완료 항목
1. CI 전체 coverage 하한선 `50 -> 55` 상향: 완료
2. optimize 성공 분기(status/list/cancel) 테스트 보강: 완료
3. 55% 기준 전체 회귀 테스트 검증: 완료

### 19.2 현재 상태
- C2.13에서 제시한 다음 권장 단계 1번(coverage 하한선 상향)이 반영됨.
- 버전은 `2.36.U1.5.C2.14`로 상향됨.
- 전체 테스트는 `237 passed, 1 skipped`로 통과.
- 전체 CLI 커버리지는 약 55.08%로 신규 하한선(55%)을 충족.

### 19.3 다음 권장 단계
1. `docs/contracts/CLI_JSON_Contract.md`에 명령별 계약 변경 이력 표 추가
2. `optimize/backtest run` 성공 payload 계약을 status/list와 분리해 문서/테스트 구조화

---

## 20. 다음 단계 실행 Status (C2.15)

### 20.1 실행 완료 항목
1. 계약 문서에 명령별 JSON 계약 변경 이력 표 추가: 완료
2. 계약 변경 운영 규칙(등록/검증/호환성/테스트 링크) 추가: 완료
3. 계약 문서의 CI coverage 기준값(55%) 정합화: 완료

### 20.2 현재 상태
- C2.14에서 제시한 다음 권장 단계 1번(계약 변경 이력 관리)이 반영됨.
- 버전은 `2.36.U1.5.C2.15`로 상향됨.
- 계약 변경 시 테스트 링크 기반 추적이 가능한 문서 상태를 확보.

### 20.3 다음 권장 단계
1. `optimize/backtest run` 성공 payload 계약을 status/list와 분리한 스키마로 정리
2. run 계약의 성공/실패 케이스를 `tests/test_json_contract_schema.py`에서 독립적으로 검증

---

## 21. 다음 단계 실행 Status (C2.16)

### 21.1 실행 완료 항목
1. `backtest run`, `optimize grid run` 성공 payload 스키마를 status/list와 분리: 완료
2. `tests/test_json_contract_schema.py`에 run 전용 성공 계약 검증 2건 추가: 완료
3. job ID 생성 포맷을 마이크로초 단위로 확장해 ID 충돌 리스크 완화: 완료

### 21.2 현재 상태
- C2.15에서 제시한 다음 권장 단계(run 계약 분리/검증)가 반영됨.
- 버전은 `2.36.U1.5.C2.16`으로 상향됨.
- 전체 테스트는 `239 passed, 1 skipped`로 통과.
- 전체 CLI 커버리지는 약 55.08%로 55% 하한선을 충족.

### 21.3 후속 권장 단계
1. run 실패 payload(파라미터 오류/DB 오류) 계약도 jsonschema로 확장
2. `tests/README.md`의 테스트 수/파일별 개수를 현재 기준으로 동기화
3. runner 계층(`cli/runners/*`) 커버리지 전용 보강 스프린트 진행

---

## 22. 다음 단계 실행 Status (C2.17)

### 22.1 실행 완료 항목
1. run 실패 payload(json 파라미터 오류/DB 오류) jsonschema 검증 확장: 완료
2. JSON 모드 실패 시 단일 에러 payload 출력(추가 텍스트 방지) 경로 정리: 완료
3. 실패 계약 코드(`BACKTEST_RUN_FAILED`, `OPT_GRID_INVALID_PARAMS`, `OPT_GRID_FAILED`) 문서 반영: 완료

### 22.2 현재 상태
- C2.16 후속 권장 단계 1번(run 실패 계약 확장)이 반영됨.
- 버전은 `2.36.U1.5.C2.17`로 상향됨.
- 전체 테스트는 `242 passed, 1 skipped`로 통과.
- 전체 CLI 커버리지는 약 55.50%로 55% 하한선을 충족.

### 22.3 다음 권장 단계
1. `tests/README.md`의 테스트 수/파일별 개수를 현재 기준(243개)으로 동기화
2. runner 계층(`cli/runners/*`) 커버리지 전용 보강 스프린트 진행

---

## 23. 다음 단계 실행 Status (C2.18)

### 23.1 실행 완료 항목
1. `tests/README.md` 테스트 수/파일별 개수 동기화: 완료
2. 테스트 실행/수집/커버리지 명령 최신화: 완료
3. 테스트 문서 유지보수 규칙 정리: 완료

### 23.2 현재 상태
- C2.17의 다음 권장 단계 1번(테스트 문서 동기화)이 반영됨.
- 버전은 `2.36.U1.5.C2.18`로 상향됨.
- 테스트 문서 기준 총 테스트 수는 `243`으로 정합화됨.

### 23.3 다음 권장 단계
1. runner 계층(`cli/runners/*`) 커버리지 전용 보강 스프린트 진행

---

## 24. 다음 단계 실행 Status (C2.19)

### 24.1 실행 완료 항목
1. runner 계층 커버리지 보강 스프린트 수행: 완료
2. `tests/test_runners.py`에 optimize/backtest 러너 경계·오류·정리 테스트 추가: 완료
3. 전체 회귀/커버리지 기준(55%) 재검증: 완료

### 24.2 현재 상태
- C2.18에서 제시한 다음 권장 단계 1번(runner 커버리지 보강)이 반영됨.
- 버전은 `2.36.U1.5.C2.19`로 상향됨.
- 전체 테스트는 `249 passed, 1 skipped`로 통과.
- 전체 CLI 커버리지는 약 57.41%로 55% 하한선을 여유 있게 충족.
- 초기 후속 권장 단계(21.3 기준) 1~3번이 모두 완료됨.

### 24.3 후속 권장 단계(신규)
1. runner 계층을 대상으로 실패 시나리오(예: queue timeout, 프로세스 join timeout) 계약 테스트 추가
2. `cli/adapters/settings_adapter.py`, `cli/adapters/queue_adapter.py` 저커버리지 구간 보강

---

## 25. 다음 단계 실행 Status (C2.20)

### 25.1 실행 완료 항목
1. runner 실패 시나리오(queue timeout, process join timeout) 계약 테스트 추가: 완료
2. `tests/test_runners.py`에 `_monitor_results` timeout 예외 경계 테스트 추가: 완료
3. `tests/test_runners.py`에 `kill_processes` join timeout 이후 `kill()` 경로 테스트 추가: 완료

### 25.2 현재 상태
- C2.19의 후속 권장 단계 1번(runner 실패 시나리오 계약 테스트)이 반영됨.
- 버전은 `2.36.U1.5.C2.20`으로 상향됨.
- 전체 테스트는 `251 passed, 1 skipped`로 통과.
- 전체 CLI 커버리지는 약 `57.60%`로 55% 하한선을 충족.
- 전체 테스트 수는 `252`로 증가했으며, 러너 전용 테스트는 `13`건으로 확장됨.

### 25.3 다음 권장 단계
1. `cli/adapters/settings_adapter.py`, `cli/adapters/queue_adapter.py` 저커버리지 구간 보강

---

## 26. 다음 단계 실행 Status (C2.21)

### 26.1 실행 완료 항목
1. `cli/adapters/settings_adapter.py`, `cli/adapters/queue_adapter.py` 저커버리지 구간 보강: 완료
2. `tests/test_adapters.py` 신규 추가(13건): 완료
3. 전체 회귀/커버리지 기준(55%) 재검증: 완료

### 26.2 현재 상태
- C2.20의 다음 권장 단계 1번(adapter 저커버리지 보강)이 반영됨.
- 버전은 `2.36.U1.5.C2.21`로 상향됨.
- 전체 테스트는 `264 passed, 1 skipped`로 통과.
- 전체 CLI 커버리지는 약 `61.42%`로 55% 하한선을 여유 있게 충족.
- adapter 커버리지 개선:
  - `cli/adapters/queue_adapter.py`: `23% -> 80%`
  - `cli/adapters/settings_adapter.py`: `24% -> 56%`
- 24.3에서 정의한 남은 단계 1~2번이 모두 완료됨.

### 26.3 다음 권장 단계(선택)
1. `cli/runners/trade_runner.py`의 미구현 주문 실행(close/cancel) 분기에 대한 명시적 에러코드 계약 테스트 추가
2. `cli/commands/strategy.py` 저커버리지 구간에 CLI 실패 경계 테스트 집중 보강

---

## 27. 다음 단계 실행 Status (C2.22)

### 27.1 실행 완료 항목
1. `trade` 명령 DB 오류 경로 JSON 에러코드 계약 테스트 추가: 완료
2. `strategy` 명령 저커버리지 구간 실패/경계 테스트 보강: 완료
3. `strategy import` JSON 파싱 실결함(`list` shadowing) 수정: 완료
4. `positions/orders list` DB 오류 JSON schema 계약 검증 추가: 완료

### 27.2 현재 상태
- 26.3에서 제시한 선택 권장 단계 1~2번이 모두 반영됨.
- 버전은 `2.36.U1.5.C2.22`로 상향됨.
- 전체 테스트는 `283 passed, 1 skipped`로 통과.
- 전체 CLI 커버리지는 약 `64.59%`로 개선됨.
- 명령 커버리지 개선:
  - `cli/commands/strategy.py`: `43% -> 69%`
  - `cli/commands/trade.py`: `71% -> 76%`
- 총 테스트 수는 `284`로 확장됨.

### 27.3 최종 종합 상태
1. 초기 잔여 단계(24.3) + 후속 선택 단계(26.3)까지 모두 실행 완료
2. 남은 과제는 신규 기능 확장이 아닌, 장기 품질 고도화(러너 실거래 연동 시나리오/strategy 심화 테스트) 단계

---

## 28. PR 품질 게이트 대응 Status (C2.23)

### 28.1 실행 배경
- 부모 브랜치 PR 생성 이후 GitHub Actions에서 품질 게이트가 `UNSTABLE`로 확인됨.
- 주요 실패 원인은 기능 결함이 아니라 **CI 설정/실행환경 의존성** 이슈였음.
  1. `setup-python`의 pip cache가 dependency path를 찾지 못해 `Smoke Test`, `Code Quality` 선행 실패
  2. 리눅스/헤드리스 환경에서 `utility/static.py`의 플랫폼 특화 import(`winreg`, `PyQt5` 등) 취약성

### 28.2 실행 완료 항목
1. `.github/workflows/cli-tests.yml`의 `setup-python`에 `cache-dependency-path` 명시: 완료
2. smoke/test/coverage job 의존성 설치에 `pytz` 명시 + test/coverage의 불필요한 `PyQt5` 제거: 완료
3. Docker smoke 호출 인자 수정(`python -m cli.main ...` -> `--version/--help`): 완료
4. `utility/static.py` 크로스플랫폼 fallback 보강: 완료
5. `tests/test_static_cross_platform.py` 신규(5건) 추가: 완료
6. Python 3.9 타입힌트 호환성 보강 + 클린 DB 환경용 테스트 테이블 선생성 보강: 완료
7. 버전 상향 및 문서 동기화(`C2.23`): 완료

### 28.3 검증 결과
- `python -m pytest tests/test_static_cross_platform.py -q --tb=short`
  - 결과: `5 passed`
- `python -m pytest tests/ --collect-only -q`
  - 결과: `289 tests collected`
- `python -m pytest tests/ -q --cov=cli --cov-report=term-missing --cov-fail-under=55 --tb=short`
  - 결과: `288 passed, 1 skipped`
  - 총 커버리지: `64.59%` (기준 55% 충족)
- `python -m cli.main --version`
  - 결과: `STOM, version 2.36.U1.5.C2.23`

### 28.4 현재 종합 판단
1. 본 브랜치는 부모 브랜치 대비 **필요했던 안정화/계약/검증 체계 강화 작업**을 완료했고, PR 품질 게이트 관점에서도 추가 보강(C2.23)까지 반영됨.
2. 따라서 부모 브랜치로의 머지는 **기술적으로 권고 가능**한 상태.
3. 단, 기능 측면의 기존 Known Gap(`db append` 실적재, 실주문 close/cancel placeholder)은 여전히 후속 개발 과제로 유지됨.

### 28.5 머지 후 후속 권장
1. `db append` 실적재 로직 구현 + 계약 테스트 추가 (P0)
2. trade runner placeholder(close/cancel) 실제 브로커 연동 또는 명시적 비지원 계약 강화 (P0/P1)
3. CI soft-fail 단계 hard-gate 전환 범위 점진 확대 (P1)

---

## 부록 A. 검토 근거 요약
- 테스트 결과: `202 passed, 1 skipped`
- 커버리지: `TOTAL 31%`
- 실행 경고: `python -m cli.main` 시 `RuntimeWarning` 확인
- 확인된 정량 리스크:
  - `bare except`: 185건
  - `except Exception as e`: 115건
  - `exec(` 사용: 289건
  - `TODO`: 6건

## 부록 B. 해석 제한
- 로컬 DB에 실거래/백테스트 데이터 행이 거의 없는 상태라, 일부 명령의 “정확한 결과값 검증”은 제한됨.
- 다만 컬럼/테이블 불일치는 쿼리 자체로 재현되어 결함 근거로 충분함.
