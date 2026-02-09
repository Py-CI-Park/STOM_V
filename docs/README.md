# STOM 문서 관리

**프로젝트**: STOM (System Trading Operation Manager)
**버전**: V2.36.U1.5.C2.23
**최종 업데이트**: 2026-02-09

---

## 폴더 구조

```
docs/
├── README.md                    # 문서 관리 인덱스
├── AGENTS.md                    # AI 에이전트 가이드 (신규)
├── CLI_User_Manual.md           # CLI 사용자 매뉴얼 (한글)
├── contracts/                   # CLI/자동화 계약 문서
│   └── CLI_JSON_Contract.md     # JSON 응답 표준 계약
├── change_log/
│   └── change_log.md            # 버전별 변경 이력
├── update_log/                  # 업데이트 상세 기록
│   ├── 2026-01-31_f2aa6be_review.md
│   ├── 2026-01-31_ui_mainwindow_migration.md
│   ├── 2026-01-31_analysis_v1_vs_v2.md
│   ├── 20260202_cli_interface.md
│   └── 20260206_cli_stabilization_c25_c28.md
├── research/                    # 연구 및 분석 보고서
│   ├── 2026-02-01_cli_interface_feasibility_report.md
│   └── 20260203_cli_test_environment_research.md
└── reports/                     # 기술 보고서
    ├── CLI_Implementation_Report_V2.36.U1.5.C1.1.md
    ├── CLI_Test_Report_V2.36.U1.5.C2.3.md
    └── 2026-02-06_STOM_Version_2U_cli_research_test_code_review.md
```

---

## 문서 목록

### AI 에이전트 가이드

| 문서 | 설명 |
|------|------|
| [AGENTS.md](AGENTS.md) | AI 에이전트(Claude Code 등)를 위한 프로젝트 가이드 |

### 사용자 매뉴얼

| 문서 | 설명 |
|------|------|
| [CLI_User_Manual.md](CLI_User_Manual.md) | CLI 사용자 매뉴얼 (한글, 2,096줄) - 사용자 및 AI Agent용 |
| [contracts/CLI_JSON_Contract.md](contracts/CLI_JSON_Contract.md) | CLI JSON 응답 계약서 |
| [tests/README.md](../tests/README.md) | CLI 테스트 시스템 문서 (284개 테스트) |

### change_log/ - 변경 이력

| 문서 | 설명 |
|------|------|
| [change_log.md](change_log/change_log.md) | 전체 버전 변경 이력 |

### update_log/ - 업데이트 로그

업데이트 상세 기록 및 작업 이력을 보관합니다. (YYYYMMDD_제목.md 또는 YYYY-MM-DD_제목.md 형식)

| 날짜 | 문서 | 설명 |
|------|------|------|
| 2026-02-06 | [20260206_cli_stabilization_c25_c28.md](update_log/20260206_cli_stabilization_c25_c28.md) | C2.5~C2.8 안정화/테스트/문서 동기화 작업 로그 |
| 2026-02-02 | [20260202_cli_interface.md](update_log/20260202_cli_interface.md) | CLI 인터페이스 개발 완료 보고서 |
| 2026-01-31 | [2026-01-31_ui_mainwindow_migration.md](update_log/2026-01-31_ui_mainwindow_migration.md) | ui_mainwindow.pyd → .py 마이그레이션 |
| 2026-01-31 | [2026-01-31_analysis_v1_vs_v2.md](update_log/2026-01-31_analysis_v1_vs_v2.md) | V1 vs V2 비교 분석 |
| 2026-01-31 | [2026-01-31_f2aa6be_review.md](update_log/2026-01-31_f2aa6be_review.md) | 커밋 f2aa6be 리뷰 |

### research/ - 연구 보고서

기술 타당성 분석 및 설계 연구 보고서를 보관합니다.

| 날짜 | 문서 | 설명 |
|------|------|------|
| 2026-02-03 | [20260203_cli_test_environment_research.md](research/20260203_cli_test_environment_research.md) | CLI 테스트 환경 연구 |
| 2026-02-01 | [2026-02-01_cli_interface_feasibility_report.md](research/2026-02-01_cli_interface_feasibility_report.md) | CLI 인터페이스 실현가능성 분석 |

### reports/ - 기술 보고서

종합 기술 보고서 및 구현 상세 기록을 보관합니다.

| 문서 | 설명 |
|------|------|
| [CLI_Implementation_Report_V2.36.U1.5.C1.1.md](reports/CLI_Implementation_Report_V2.36.U1.5.C1.1.md) | CLI 구현 상세 보고서 (667줄) |
| [CLI_Test_Report_V2.36.U1.5.C2.3.md](reports/CLI_Test_Report_V2.36.U1.5.C2.3.md) | CLI 테스트 실행 보고서 (202개 통과) |
| [2026-02-06_STOM_Version_2U_cli_research_test_code_review.md](reports/2026-02-06_STOM_Version_2U_cli_research_test_code_review.md) | 현재 브랜치 종합 코드 검토 + 실행 결과 반영 문서 |

---

## 문서 작성 규칙

### 파일명 규칙

```
YYYYMMDD_제목.md  또는  YYYY-MM-DD_제목.md
```

예시:
- `20260202_cli_interface.md`
- `2026-01-31_ui_mainwindow_migration.md`

### 필수 포함 내용

1. **개요**: 작업 목적 및 배경
2. **상세 내용**: 기술적 세부사항
3. **결과**: 작업 결과 및 검증
4. **참고**: 관련 파일 및 링크

---

## 최근 변경사항

### V2.36.U1.5.C2.23 (2026-02-09)

- GitHub Actions `setup-python` 캐시 경로를 명시해 CI 사전 단계 실패(`cache: pip`)를 해소
- Smoke/Test/coverage 의존성 설치에 `pytz`를 명시해 리눅스 import 실패를 방지
- Docker smoke 단계의 엔트리포인트 호출 인자를 수정(`python -m cli.main ...` -> `--version/--help`)
- `utility/static.py`를 리눅스/헤드리스 호환 fallback 구조로 보강
  - `winreg`, `PyQt5`, `psutil`, `exchange_calendars`, `cryptography`, `loguru` 미설치 환경 import 안전성 개선
  - `read_key`, `qtest_qwait`, `cme_normal_open`, `win_proc_alive`에 플랫폼별 안전 경로 추가
- `tests/test_static_cross_platform.py` 신규 추가(5건): 크로스플랫폼 fallback 동작 회귀 검증
- 목적: PR 품질 게이트(스모크/코드품질/도커 빌드) 통과를 위한 실행환경 의존성 리스크 제거

### V2.36.U1.5.C2.22 (2026-02-07)

- `tests/test_trade.py`에 DB 오류 시 JSON 에러코드 계약 테스트 4건 추가
- `tests/test_strategy_boundaries.py` 신규 추가(13건): strategy 명령 실패/경계 경로 검증 강화
- `cli/commands/strategy.py`에서 `import` JSON 파싱 시 `list` shadowing 버그 수정(`builtins.list/dict` 사용)
- `cli/commands/trade.py`의 JSON 모드 오류 종료 경로 정리(`positions list`, `orders list`)
- 전체 테스트 수: `284`, 결과: `283 passed, 1 skipped`
- 전체 CLI 커버리지: 약 `64.59%`

### V2.36.U1.5.C2.21 (2026-02-07)

- `tests/test_adapters.py` 신규 추가(13건): settings/queue adapter 저커버리지 구간 보강
- `cli/adapters/queue_adapter.py` 커버리지 `23% -> 80%` 개선
- `cli/adapters/settings_adapter.py` 커버리지 `24% -> 56%` 개선
- 전체 테스트 수: `265`, 결과: `264 passed, 1 skipped`
- 전체 CLI 커버리지: 약 `61.42%`

### V2.36.U1.5.C2.20 (2026-02-07)

- `tests/test_runners.py`에 runner 실패 시나리오 계약 테스트 2건 추가
- `windowQ.get()` timeout(Empty) 예외 처리 경로 검증 추가
- `kill_processes`의 join timeout 이후 `kill()` 강제 종료 경로 검증 추가
- 전체 테스트 수: `252`로 증가
- 전체 테스트 기준: `251 passed, 1 skipped`, 커버리지 약 `57.60%`

### V2.36.U1.5.C2.19 (2026-02-07)

- `tests/test_runners.py` 러너 경계/오류/정리 경로 테스트 7건 추가
- `backtest_runner` 커버리지 `22% -> 34%`, `optimize_runner` `39% -> 47%` 개선
- 전체 테스트 기준: `249 passed, 1 skipped`
- 전체 CLI 커버리지: 약 `57.41%`

### V2.36.U1.5.C2.18 (2026-02-07)

- `tests/README.md`를 현재 테스트 구조 기준으로 전면 동기화
- 파일별 테스트 수/총 테스트 수(243) 반영
- 테스트 실행/수집/커버리지 명령과 유지보수 규칙 최신화

### V2.36.U1.5.C2.17 (2026-02-07)

- `backtest run`, `optimize grid` 실패 JSON 계약을 jsonschema로 확장(파라미터 오류/DB 오류)
- JSON 모드 실패 시 순수 JSON payload만 출력되도록 에러 종료 경로 정리
- `tests/test_json_contract_schema.py` 실패 계약 테스트 3건 추가
- 전체 테스트 기준: `242 passed, 1 skipped`

### V2.36.U1.5.C2.16 (2026-02-07)

- `backtest run`, `optimize grid` 성공 JSON payload 스키마를 status/list와 분리해 계약 테스트 추가
- job ID 생성 포맷을 마이크로초 단위로 확장해 테스트/실행 시 ID 충돌 리스크 완화
- `tests/test_json_contract_schema.py`에 run 전용 스키마 검증 2건 추가
- 전체 테스트 기준: `239 passed, 1 skipped`

### V2.36.U1.5.C2.15 (2026-02-07)

- `docs/contracts/CLI_JSON_Contract.md`에 명령별 JSON 계약 변경 이력 표(버전/변경 필드/호환성/테스트) 추가
- 계약 변경 시 문서 갱신 규칙(계약 변경 등록/테스트 링크/호환성 표기) 운영 가이드 반영
- 코드 리뷰 보고서 및 업데이트 로그에 C2.15 진행 상태 동기화

### V2.36.U1.5.C2.14 (2026-02-07)

- `tests/test_optimize.py`에 status/list/cancel 성공 경로 분기 테스트 3건 추가
- CI 전체 coverage 하한선을 `--cov-fail-under=55`로 상향
- 전체 테스트 기준: `237 passed, 1 skipped`
- 전체 CLI 커버리지 기준치 확인: 약 55.08%

### V2.36.U1.5.C2.13 (2026-02-07)

- `tests/test_json_contract_schema.py`에 backtest/optimize `list`/`status` JSON schema 검증 확장
- 상태 조회 미존재 ID(`unknown_job_id`) 응답을 `{"message": ...}` 계약으로 검증
- 상태 조회 성공 계약은 DB 최신 작업 ID 기반으로 검증해 ID 충돌/DB lock 리스크 제거
- 전체 테스트 기준: `234 passed, 1 skipped`
- 전체 CLI 커버리지 기준치 확인: 약 54.67%

### V2.36.U1.5.C2.12 (2026-02-07)

- `positions close`/`orders cancel` 성공 JSON payload 계약 테스트 추가
- `tests/test_json_contract_schema.py` 신설로 jsonschema 기반 JSON 계약 자동검증 도입
- 전체 CLI coverage 하한선 적용: `--cov-fail-under=50`
- runner/schema coverage 하한선 유지: `--cov-fail-under=35`
- 현재 전체 CLI 커버리지 기준치 확인: 약 54%

### V2.36.U1.5.C2.11 (2026-02-06)

- `positions close`/`orders cancel`에 JSON 실패 계약(`ok=false`, 에러코드) 적용
- `tests/test_trade.py`에 실패 JSON 에러코드 계약 테스트 2건 추가
- coverage job의 runner/schema 스냅샷에 하한선(`--cov-fail-under=35`) 적용
- `docs/contracts/CLI_JSON_Contract.md`에 명령별 샘플/테스트 링크 표 추가

### V2.36.U1.5.C2.10 (2026-02-06)

- `tests/test_trade.py`에 positions/orders JSON payload 계약 검증 테스트 추가
- coverage 파이프라인에 runner/schema 전용 커버리지 스냅샷 단계 및 아티팩트 추가
- JSON 계약 문서를 독립 문서로 분리: `docs/contracts/CLI_JSON_Contract.md`
- C2.9 이후 다음 단계 1~3번 항목 실행 완료

### V2.36.U1.5.C2.9 (2026-02-06)

- `cli/commands/trade.py` 인코딩 깨짐 문자열/주석 정리 및 에러 응답 코드 정비
- `docs/CLI_User_Manual.md`에 JSON 응답 계약(성공/빈결과/에러 payload) 명시
- `.github/workflows/cli-tests.yml`에 러너/스키마 계약 테스트 필수 게이트 추가
- C2.8 후속 권장사항 중 1~3번 항목 실행 완료

### V2.36.U1.5.C2.8 (2026-02-06)

- C2.5~C2.8 실행 계획 항목 반영 완료 및 문서 동기화
- JSON/CSV 출력 파싱 안정화(타이틀 배너 제거) 및 JSON 에러 응답 표준화
- 러너 계층/스키마 계약 테스트 추가로 핵심 실행 경로 검증 강화
- 코드 리뷰 보고서(`reports/2026-02-06_...`)에 실행 결과/개발 안내 반영
- update_log 신규 문서 추가: `update_log/20260206_cli_stabilization_c25_c28.md`

### V2.36.U1.5.C2.3 (2026-02-03)

- CLI 테스트 시스템 구축 완료 (Phase 1-4)
- pytest 기반 자동화 테스트 202개 작성
- 스모크 테스트 스크립트 (Bash/PowerShell)
- GitHub Actions CI/CD 워크플로우
- 테스트 커버리지: CLI 전체 명령 대상

### V2.36.U1.5.C2.0 (2026-02-03)

- CLI 전체 기능 구현 완료 (Phase 2-6)
- 트레이딩 제어, 모니터링, 최적화, DB 관리 명령 추가
- Docker 지원 (Dockerfile, docker-compose.yml)
- CLI 사용자 매뉴얼 추가 (2,096줄)
- 구현률 100% (46/46 기능)

### V2.36.U1.5.C1.1 (2026-02-02)

- CLI 백테스트 아키텍처 완전 통합
- HeadlessBacktestRunner 재작성 (16가지 엔진 지원)
- CLI 명령어 인터페이스 개선
- 종합 기술 보고서 작성

### V2.36.U1.5.C1.0 (2026-02-02)

- CLI 인터페이스 기본 구현
- 전략 관리, 데이터 조회, 백테스트 명령어

### V2.36.U1 (2026-01-31)

- ui_mainwindow.pyd → ui_mainwindow.py 마이그레이션

---

## 빠른 링크

- **프로젝트 루트**: [STOM_V](../)
- **AI 에이전트 가이드**: [AGENTS.md](AGENTS.md) ⭐
- **CLI 사용자 매뉴얼**: [CLI_User_Manual.md](CLI_User_Manual.md) ⭐
- **변경 로그**: [change_log.md](change_log/change_log.md)
- **최신 CLI 보고서**: [CLI_Implementation_Report_V2.36.U1.5.C1.1.md](reports/CLI_Implementation_Report_V2.36.U1.5.C1.1.md)
- **CLI 테스트 보고서**: [CLI_Test_Report_V2.36.U1.5.C2.3.md](reports/CLI_Test_Report_V2.36.U1.5.C2.3.md) ⭐
- **브랜치 코드 리뷰/개선 결과**: [2026-02-06_STOM_Version_2U_cli_research_test_code_review.md](reports/2026-02-06_STOM_Version_2U_cli_research_test_code_review.md) ⭐
- **마이그레이션 기록**: [2026-01-31_ui_mainwindow_migration.md](update_log/2026-01-31_ui_mainwindow_migration.md)

---

## 문서 검색 팁

- **최신 정보 찾기**: update_log/ 폴더에서 가장 최근 날짜의 파일 확인
- **특정 기능 분석**: research/ 폴더에서 관련 보고서 검색
- **전체 버전 이력**: change_log/change_log.md 참조
- **상세 구현 정보**: reports/ 폴더의 기술 보고서 참조
