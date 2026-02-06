# STOM 문서 관리

**프로젝트**: STOM (System Trading Operation Manager)
**버전**: V2.36.U1.5.C2.8
**최종 업데이트**: 2026-02-06

---

## 폴더 구조

```
docs/
├── README.md                    # 문서 관리 인덱스
├── AGENTS.md                    # AI 에이전트 가이드 (신규)
├── CLI_User_Manual.md           # CLI 사용자 매뉴얼 (한글)
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
| [tests/README.md](../tests/README.md) | CLI 테스트 시스템 문서 (202개 테스트) |

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
