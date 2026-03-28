# 2026-03-28 research/init 운영 문서 맵

## 목적

이 문서는 `research/init` 브랜치에서 어떤 문서를 어떤 순서로 읽어야 하는지 한 페이지로 정리한 **운영 문서 맵**이다.

새 세션에서 작업을 시작할 때,
- 어떤 문서가 최상위 규칙인지
- 어떤 문서가 공식 업데이트 반영 기준인지
- 어떤 문서가 완료 상태를 설명하는지
를 빠르게 파악할 수 있도록 만든다.

---

## 1. 최상위 지침 문서

| 파일 | 역할 | 언제 먼저 읽는가 |
|---|---|---|
| `AGENTS.md` | research 브랜치 운영 규칙, canonical base, A/B/C 원칙, 공식 업데이트 반영 순서 | **항상 첫 번째** |
| `CLAUDE.md` | 작업 방법, 브랜치 목적, 공식 업데이트 추적 기준, 금지 사항 | **항상 두 번째** |

### 핵심 요약
- canonical base: `wt-dev / STOM_Version_2U_C_CLI_v267`
- 원칙 A: 공식 업데이트 흡수
- 원칙 B: 리서치 맥락에 맞게 조정
- 원칙 C: branch-specific 문서와 최소 호환 보정 유지

---

## 2. 공식 업데이트 반영 기준 문서

| 파일 | 역할 | 용도 |
|---|---|---|
| `docs/research/2026-03-28_research_init_v259_v267_sync_matrix_and_plan.md` | `V2.59 ~ V2.67` 공식 업데이트를 버전별로 해석한 매트릭스 | 버전별로 무엇을 왜 받아야 하는지 확인 |
| `docs/research/2026-03-28_research_init_official_update_playbook.md` | 공식 업데이트를 실무 묶음 단위로 반영하는 플레이북 | **실제 작업 순서 결정용 핵심 문서** |

### 언제 읽는가
- 부모 브랜치에 새 공식 버전이 반영되었을 때
- `research/init`을 다음 공식 기준선으로 업데이트할 때
- 어떤 파일을 먼저 반영할지 판단할 때

---

## 3. wt-lab 전환 / 완료 상태 문서

| 파일 | 역할 | 용도 |
|---|---|---|
| `docs/research/2026-03-28_wt_lab_home_crawler_integration_plan.md` | wt-lab 홈탭 / crawler 구조 전환 계획 | split → integrated 전환 배경 추적 |
| `docs/research/2026-03-28_research_init_v267_preparation_completion_report.md` | 이번 v267 준비 작업 완료 보고서 | 현재 브랜치가 어디까지 정리되었는지 확인 |

### 언제 읽는가
- 현재 `research/init`이 어디까지 완료되었는지 확인할 때
- 이미 반영한 범위와 의도적으로 남긴 차이를 다시 설명해야 할 때
- 후속 세션에서 “완전 동일 코드인지 / 준비 상태인지”를 구분해야 할 때

---

## 4. 권장 읽기 순서

### A. 새 세션 시작 직후
1. `AGENTS.md`
2. `CLAUDE.md`
3. `docs/research/2026-03-28_research_init_v267_preparation_completion_report.md`

### B. 공식 업데이트 반영 작업 시작 전
1. `AGENTS.md`
2. `CLAUDE.md`
3. `docs/research/2026-03-28_research_init_v259_v267_sync_matrix_and_plan.md`
4. `docs/research/2026-03-28_research_init_official_update_playbook.md`

### C. 홈탭 / crawler / runtime 관련 작업 시
1. `docs/research/2026-03-28_wt_lab_home_crawler_integration_plan.md`
2. `docs/research/2026-03-28_research_init_v267_preparation_completion_report.md`

---

## 5. 문서별 한 줄 요약

| 문서 | 한 줄 요약 |
|---|---|
| `AGENTS.md` | research 브랜치 최상위 운영 규칙 |
| `CLAUDE.md` | 작업 방법 + 공식 업데이트 추적 기준 |
| `...sync_matrix_and_plan.md` | `V2.59~V2.67` 공식 업데이트를 버전별로 어떻게 받아야 하는지 정리 |
| `...official_update_playbook.md` | 앞으로 공식 업데이트를 어떤 실무 순서로 반영할지 정리 |
| `...wt_lab_home_crawler_integration_plan.md` | 홈탭/crawler 구조 전환 계획 |
| `...v267_preparation_completion_report.md` | 현재 research/init이 어디까지 완료되었는지 설명 |

---

## 최종 안내

새 작업을 시작할 때는 아래 두 질문부터 확인하면 된다.

1. **이번 작업이 공식 업데이트 반영인가?**
   - Yes → `sync_matrix_and_plan` + `official_update_playbook` 먼저 확인
2. **이번 작업이 현재 상태 확인/후속 유지보수인가?**
   - Yes → `completion_report` 먼저 확인

그리고 어떤 경우든 시작은 항상:
- `AGENTS.md`
- `CLAUDE.md`
순서로 한다.

