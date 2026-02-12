# STOM_Version_2U-cli-research 머지 이후 종합 코드 검토 보고서 (상세 개선판)

## 1. 문서 목적
- 본 문서는 `STOM_Version_2U-cli-research` 브랜치(머지 이후 부모 브랜치 기준)의 현재 상태를 기술적으로 검토하고, 실제 운영/개발 관점에서 다음 실행 계획을 제시하기 위한 종합 보고서입니다.
- 단순 상태 요약이 아니라 다음 4가지를 동시에 다룹니다.
- 프로젝트/브랜치 목적 정리
- 현재 가능한 기능과 실제 제한사항 구분
- 정량 근거 기반 완성도 평가
- 우선순위 기반 개선 방법 + 상세 개발 안내

## 2. 검토 기준 및 범위

### 2.1 기준 시점
- 기준 날짜: 2026-02-12
- 기준 브랜치: `STOM_Version_2U-cli-research`
- 기준 버전 상수: `2.36.U1.5.C2.23` (`cli/version.py:3`)

### 2.2 검토 범위
- 코드
- CLI 엔트리/명령 (`cli/main.py`, `cli/commands/*`)
- Adapter/Runner 계층 (`cli/adapters/*`, `cli/runners/*`)
- 공용 유틸 fallback (`utility/static.py`)
- 테스트/CI
- `tests/*`, `.github/workflows/cli-tests.yml`
- 문서
- `docs/README.md`, `docs/CLI_User_Manual.md`, `docs/contracts/CLI_JSON_Contract.md`
- 누적 리뷰 문서
- `docs/reports/2026-02-06_STOM_Version_2U_cli_research_test_code_review.md`

### 2.3 검토 방법
- 정적 코드 구조 확인 (명령군/옵션/핵심 분기)
- 문서-코드-테스트 정합성 대조
- 실제 실행 검증
- `python -m pytest tests/ --collect-only -q`
- `python -m pytest tests/ -q --cov=cli --cov-report=term-missing --cov-fail-under=55`
- CLI 도움말/버전 스모크
- `python -m cli.main --version`, `--help`, 그룹별 `--help`

## 3. 최종 결론 (요약)
- 브랜치 목표였던 "GUI 의존 완화 + CLI 자동화 안정화 + JSON 계약 기반 운영"은 높은 수준으로 달성되었습니다.
- 특히 JSON 계약과 jsonschema 테스트 체계가 고정되어 자동화 친화성은 매우 우수합니다.
- 테스트/커버리지 상태도 운영 가능한 수준을 넘었습니다.
- 테스트: 289/289 passed
- 전체 CLI 커버리지: 64.57% (게이트 55% 충족)
- 다만 아래 3개는 완성도 상한을 제한하는 핵심 잔여 과제입니다.
- `db append` 실적재 미구현 (`cli/commands/db.py:137`)
- `optimize` 명령 경로의 실행 연동 비활성 경고 (`cli/commands/optimize.py:203`)
- `trade` 계열 일부 동작의 placeholder 성격 (`cli/runners/trade_runner.py:5`)

## 4. 프로젝트/브랜치 목적 분석

### 4.1 프로젝트 목적
- STOM은 시스템 트레이딩 운영 플랫폼이며, 본 브랜치는 핵심 운영 흐름을 CLI로 일관 제어해 자동화/에이전트 연동을 가능하게 하는 것을 목표로 합니다.
- CLI 엔트리에서 주요 명령군이 통합 등록됩니다.
- `strategy`, `data`, `backtest`, `trade`, `positions`, `orders`, `monitor`, `optimize`, `db` (`cli/main.py:36`~`cli/main.py:44`)

### 4.2 머지된 개발 목적
- 테스트 브랜치에서 수행된 안정화 작업(C2.17~C2.24 계열)을 부모 브랜치에 흡수하여 다음 품질 특성을 확보하는 것이 핵심 목적이었습니다.
- JSON 응답 계약의 표준화 및 회귀 방지
- CI 파이프라인의 플랫폼/의존성 안정성
- 커버리지 게이트 기반 품질 하한선 보장
- 문서 기반 운영/개발 가이드 정착

### 4.3 목적 달성 판단
- 달성도: 높음
- 잔여 이슈는 "기능이 틀렸음"보다는 "일부 기능이 의도적으로 제한/미완"에 해당합니다.

## 5. 아키텍처 관점 구조 분석

### 5.1 계층 구조
- Entry Layer: `cli/main.py`
- Command Layer: `cli/commands/*.py`
- Adapter Layer: `cli/adapters/*.py`
- Runner Layer: `cli/runners/*.py`
- Legacy/Core 연동: `backtester/*`, `_database/*`, `utility/static.py`

### 5.2 강점
- 명령군 책임 분리(전략/데이터/백테스트/트레이드/모니터/최적화/DB)
- Adapter를 통한 출력/스키마/설정 책임 분리
- JSON 계약 문서와 테스트가 연결되어 인터페이스 안정성 확보

### 5.3 주의점
- 일부 Runner는 multiprocessing + 외부 모듈 로딩과 결합되어 테스트 난이도가 높습니다.
- 실제 집행(브로커/거래소) 동작은 현재 명시적으로 제한된 경로가 존재합니다.

## 6. 기능별 상세 평가

### 6.1 전략(`strategy`)
- 제공 기능: list/show/export/save/delete/import/validate/stats
- 상태: 실사용 가능(높음)
- 근거: `cli/commands/strategy.py`
- 비고: 최근 Click 버전 차이 대응을 포함한 안정화 이력이 반영됨.

### 6.2 데이터(`data`)
- 제공 기능: backtest-list/backtest-result/trades/summary/export
- 상태: 실사용 가능(중상)
- 근거: `cli/commands/data.py`
- 비고: JSON 계약/스키마 보강 이력 반영.

### 6.3 백테스트(`backtest`)
- 제공 기능: run/status/list/cancel/delete
- 상태: 실사용 가능(중상)
- 근거: `cli/commands/backtest.py`
- 비고: 동기/비동기 모두 지원하지만 실행경로의 복잡성이 높아 runner 테스트 확장이 여전히 중요.

### 6.4 트레이드(`trade`, `positions`, `orders`)
- 제공 기능
- `trade`: start/stop/status
- `positions`: list/close
- `orders`: list/cancel
- 상태: 운영 조회/상태 기록 중심, 액션 일부 제한
- 근거
- 실제 집행 placeholder 명시: `cli/runners/trade_runner.py:5`
- 수동/운영 안내 주석: `docs/CLI_User_Manual.md:962`
- 판단: "완전 실주문 제어"가 아니라 "헤드리스 상태/요청 제어"로 해석해야 정확함.

### 6.5 모니터링(`monitor`)
- 제공 기능: live/pnl/positions
- 상태: 실사용 가능(중상)
- 근거: `cli/commands/monitor.py`
- 비고: 데이터 소스 테이블 변동 시 schema adapter/조회 로직 검증이 중요.

### 6.6 최적화(`optimize`)
- 제공 기능: grid/bayesian/ga/walkforward/backfinder/status/list/cancel/delete
- 상태: 큐 등록/조회 안정, 실행 연동 제한
- 근거
- 실행 비활성 경고: `cli/commands/optimize.py:203`
- 판단: 스케줄링 중심으로는 usable, "즉시 실행형" 완성도는 추가 개발 필요.

### 6.7 DB(`db`)
- 제공 기능: create/delete/info/vacuum/backup
- 상태: 실사용 가능(중상)
- 미완 항목
- `append` 실데이터 적재 TODO: `cli/commands/db.py:137`

## 7. 자동화/에이전트 연동 적합성 평가

### 7.1 강점
- `--format json` 계약이 문서와 테스트로 고정되어 파서 안정성이 높습니다.
- 표준 에러 payload(`ok=false`, `error.code/type/message/title`)가 명확합니다.
- 근거
- 계약 문서: `docs/contracts/CLI_JSON_Contract.md:42`
- 계약 테스트: `tests/test_json_contract_schema.py:47`

### 7.2 파서 구현 시 필수 규칙
- 종료코드와 stdout JSON을 분리 검증
- `message` 단독 객체는 정상 빈결과로 처리
- `ok=false` 객체는 실패로 처리
- 배열 응답은 데이터 목록으로 처리
- 근거: `docs/contracts/CLI_JSON_Contract.md:69`

## 8. 테스트/품질 분석

### 8.1 실측 결과 (2026-02-12)
- 테스트 수집: 289
- 테스트 실행: 289 passed
- 전체 커버리지: 64.57%
- 최소 게이트: 55% 충족

### 8.2 커버리지 상세 해석
- 우수 영역
- `cli/commands/db.py`: 88%
- `cli/commands/optimize.py`: 79%
- `cli/commands/trade.py`: 76%
- `cli/adapters/output_adapter.py`: 81%
- 보강 필요 영역
- `cli/runners/backtest_runner.py`: 36%
- `cli/runners/optimize_runner.py`: 47%
- `cli/commands/backtest.py`: 51%
- `cli/commands/data.py`: 52%

### 8.3 CI 파이프라인 성숙도
- smoke/test/coverage/lint/docker-build 분리 구성
- coverage gate 명시 (`--cov-fail-under=55`)
- runner/schema 별도 스냅샷 게이트 포함
- 근거: `.github/workflows/cli-tests.yml:162`, `.github/workflows/cli-tests.yml:165`

## 9. 위험요소 분석 (Risk Matrix)

| 위험 항목 | 영향도 | 발생 가능성 | 현재 통제 수준 | 비고 |
|---|---|---|---|---|
| `db append` 미구현 | 높음 | 높음 | 낮음 | 운영 데이터 적재 자동화 단절 |
| optimize 실행 연동 제한 | 높음 | 중간 | 중간 | 사용자 기대(실행)와 현재 동작(큐 등록) 간 갭 |
| trade 실제 집행 미완 | 중간~높음 | 중간 | 중간 | 상태 제어 중심으로 명시 필요 |
| runner 저커버리지 경로 | 중간 | 중간 | 중간 | 회귀 탐지 지연 가능 |
| 문서/버전 수치 동기화 누락 | 중간 | 중간 | 중간 | 신뢰도/온보딩 비용 증가 |

## 10. 부족 내용 (정리)

### 10.1 기능 부족
- `db append` 구현 부재
- optimize sync 실행 미연동
- trade 액션 일부는 비지원/placeholder

### 10.2 품질 부족
- runner 계층 커버리지 편차
- 문서의 최신 실행 수치 일부 불일치 가능

### 10.3 운영 부족
- "실제 집행 가능한 명령"과 "상태 기록/시뮬레이션 명령"의 구분이 문서/도움말에 더 명확히 드러날 필요

## 11. 개선 로드맵 (실행 우선순위)

### 11.1 P0 (즉시, 1~2주)
1. `db append` 구현 완료
- 파일: `cli/commands/db.py`
- 산출물
- 입력 포맷 정의(CSV/Parquet/DB dump 중 최소 1개)
- 적재 로직 + 중복 처리 + 트랜잭션 롤백
- `--dry-run`/`--apply` 모드 분리
- 테스트
- 성공/형식오류/중복/롤백 케이스 추가

2. optimize 실행 연동 보강
- 파일: `cli/commands/optimize.py`, `cli/runners/optimize_runner.py`
- 산출물
- 동기 실행 시 runner 호출 및 상태 전이 반영
- 실패 시 표준 JSON 에러 코드 통일
- 테스트
- sync path 성공/실패/timeout 계약 테스트

3. trade 책임 경계 명확화
- 파일: `cli/commands/trade.py`, `docs/CLI_User_Manual.md`
- 산출물
- 비지원 액션은 명시 에러 코드/메시지 고정
- simulated/live 모드 정의 문구 추가

### 11.2 P1 (단기, 2~4주)
1. runner 테스트 집중 강화
- 목표
- `backtest_runner` 36% -> 55%+
- `optimize_runner` 47% -> 60%+
- 방식
- multiprocess 종료/큐 timeout/DB lock/import fail 시나리오 확장

2. 문서-버전 동기화 자동검사
- 대상 파일
- `cli/version.py`
- `docs/README.md`
- `tests/README.md`
- `docs/change_log/change_log.md`
- 방식
- CI 스크립트로 버전/날짜/핵심 수치 정합성 점검

### 11.3 P2 (중기)
1. 스키마 검증 명령 도입
- 예: `stom db check-schema --format json`
- 목적: 배포 전 DB 스키마 drift 조기 탐지

2. 운영 모드 명시 체계화
- `headless/simulated/live` 모드 선언 및 명령별 지원 매트릭스 문서화

## 12. 개선 방법 (기술 구현 지침)

### 12.1 `db append` 구현 지침
- 요구사항
- 날짜(`YYYYMMDD`) 유효성
- 소스 파일 존재/형식 검증
- 대상 테이블 자동 탐지(자산유형/틱/분)
- 중복키 정책(무시/갱신) 명확화
- 구현 포인트
- sqlite transaction(`BEGIN`, `COMMIT`, `ROLLBACK`) 명시
- 실패 시 표준 JSON 에러 코드 반환
- 검증 커맨드 예
```bash
python -m pytest tests/test_db.py -q
python -m pytest tests/integration/test_data_consistency.py -q
```

### 12.2 optimize 실행 연동 지침
- 요구사항
- sync 실행 시 큐 등록만 하지 말고 runner를 통한 상태 전이 수행
- 상태값 규약 고정: `pending -> running -> completed|failed|canceled`
- 구현 포인트
- `optimize_jobs` 테이블 상태 업데이트 분기 통일
- 에러 code 표준화 (`OPT_*`)
- 검증 커맨드 예
```bash
python -m pytest tests/test_optimize.py tests/test_json_contract_schema.py -q
```

### 12.3 trade 명확화 지침
- 요구사항
- "실집행 미지원" 경로는 명시적 실패 코드로 고정
- 사용자 오해 방지 문구를 help/manual에 동시 반영
- 구현 포인트
- `positions close`, `orders cancel`의 unsupported 케이스 메시지 표준화
- 검증 커맨드 예
```bash
python -m pytest tests/test_trade.py tests/test_json_contract_schema.py -q
```

## 13. 개발 안내 (실행 절차, 상세)

### 13.1 새 기능 작업 표준 절차
1. 요구사항 확정
- 명령 목적, 입력 옵션, 성공/실패 응답 스키마를 먼저 정의

2. 코드 구현
- `cli/commands/*`에 명령 구현
- 필요 시 `cli/adapters/*`, `cli/runners/*`로 책임 분리

3. 계약 문서 갱신
- `docs/contracts/CLI_JSON_Contract.md`에 필드/호환성/테스트 링크 반영

4. 테스트 작성
- 단위(명령), 계약(jsonschema), 통합(workflow) 순으로 추가

5. 문서 동기화
- `docs/CLI_User_Manual.md`, `docs/README.md`, `tests/README.md` 업데이트

6. 검증
```bash
python -m pytest tests/ --collect-only -q
python -m pytest tests/ -q --cov=cli --cov-report=term-missing --cov-fail-under=55
python -m cli.main --help
```

7. 커밋
- `docs/AGENTS.md` 커밋 규칙 준수

### 13.2 배포 전 체크리스트
- [ ] JSON 계약 문서와 실제 출력 필드 일치
- [ ] 에러 코드 네이밍 일관 (`MODULE_ACTION_REASON`)
- [ ] CI 커버리지 게이트 통과
- [ ] 문서 버전/날짜/테스트 수치 동기화
- [ ] 비지원 기능 문구가 명시적으로 드러남

### 13.3 장애 대응 플레이북
1. 명령 재현 (`--format json`)
2. `db info`로 대상 DB/테이블 상태 확인
3. 계약 테스트 우선 실행
4. runner/adapter 단위로 원인 축소
5. 코드+테스트+문서 동시 수정

## 14. PR/머지 품질 기준 제안
- 최소 품질 게이트
- 전체 테스트 통과
- CLI 커버리지 55% 이상
- 신규/변경 명령의 JSON 계약 테스트 포함
- 문서 동기화 완료

- 권장 품질 게이트
- runner/schema 스냅샷 커버리지 50% 이상
- 비지원 기능은 에러 코드/문서에 명시

## 15. 현재 브랜치 완성도 종합 평가

### 15.1 점수
- 현재 상태: **7.9 / 10**
- 강점
- 인터페이스 일관성
- 계약 기반 자동화 안정성
- CI/테스트 체계
- 약점
- 일부 실행경로의 미완/제한 기능
- runner 커버리지 편차

### 15.2 최종 판단
- 본 브랜치는 "안정적 CLI 운영 기반"으로는 충분히 성숙했습니다.
- 다음 단계에서 `db append`, optimize sync 연동, trade 경계 명확화를 완료하면 "실행 완결형 브랜치" 수준으로 상승 가능합니다.

## 16. 실행 근거 (파일)

### 16.1 코드 근거
- `cli/main.py`
- `cli/version.py`
- `cli/commands/strategy.py`
- `cli/commands/data.py`
- `cli/commands/backtest.py`
- `cli/commands/trade.py`
- `cli/commands/monitor.py`
- `cli/commands/optimize.py`
- `cli/commands/db.py`
- `cli/adapters/output_adapter.py`
- `cli/adapters/settings_adapter.py`
- `cli/adapters/schema_adapter.py`
- `cli/runners/backtest_runner.py`
- `cli/runners/optimize_runner.py`
- `cli/runners/trade_runner.py`
- `utility/static.py`

### 16.2 문서 근거
- `docs/README.md`
- `docs/CLI_User_Manual.md`
- `docs/contracts/CLI_JSON_Contract.md`
- `docs/reports/2026-02-06_STOM_Version_2U_cli_research_test_code_review.md`
- `docs/update_log/20260206_cli_stabilization_c25_c28.md`
- `tests/README.md`

### 16.3 검증 커맨드
```bash
python -m pytest tests/ --collect-only -q
python -m pytest tests/ -q --cov=cli --cov-report=term-missing --cov-fail-under=55
python -m cli.main --version
python -m cli.main --help
```
