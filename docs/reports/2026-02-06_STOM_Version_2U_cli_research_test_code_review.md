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

## 11. 최종 판단
- 현재 브랜치는 “기능 뼈대와 문서화는 우수하나, 실데이터 정합성과 테스트 엄격성 부족으로 완성도 고도화가 필요한 상태”입니다.
- 우선순위는 **DB 스키마 정합성 복구 + 테스트 신뢰도 복구**입니다.
- 위 P0/P1 항목을 처리하면 CLI 신뢰성은 단기간 내 체감 개선이 가능합니다.

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

