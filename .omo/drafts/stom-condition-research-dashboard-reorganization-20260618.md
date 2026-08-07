# Draft: STOM Condition Research Dashboard Reorganization 20260618

## Requirements (confirmed)
- 최근 커밋 2개까지 포함해 지금까지 작업을 체계적으로 정리한다.
- `STOM_Version_2U_C-ai-strategy-loop` 이후 파생 작업을 PR/브랜치 단위로 다시 설명 가능한 구조로 정리한다.
- 지금까지 조건식 연구 내용을 체계적으로 정리한다.
- 앞으로 연구를 진행할 때 연구 내용이 관리되고, 그 관리 자체가 연구 성능을 발전시키는 프로세스를 설계한다.
- 대시보드 전체를 전수 검사해 중복 기능, 기능별 분류, 비효율성, 조건식 연구 네이밍 규칙, 시각 기능, 에러를 찾는다.
- 위 작업을 페이지별 상세 계획으로 만들고, 이후 누락 없이 실행할 수 있게 한다.

## Technical Decisions
- 단일 계획 파일로 작성한다: `.omo/plans/stom-condition-research-dashboard-reorganization-20260618.md`.
- 구현은 하지 않는다. 계획 산출물과 조사만 작성한다.
- 현재 `wt-dev`의 미커밋 변경은 보호한다. 정리 작업은 먼저 inventory와 split plan을 만든 뒤에만 커밋/PR 대상으로 삼는다.
- `STOM_Version_2U_C-ai-strategy-loop`는 로컬 AI 진화 대시보드 anchor다. 강제 이동/리셋/직접 덮어쓰기는 금지하고, 현재 HEAD를 이 anchor로 끌어올릴 때는 PR merge만 사용한다.
- 재시작 목표 모델은 `base: STOM_Version_2U_C-ai-strategy-loop`, `compare: lazycodex/tick-sparse-positive-generation-improvement-20260604` PR로 anchor를 최신화한 뒤, 갱신된 anchor에서 새 개발 브랜치를 만드는 것이다.
- 연구 시스템 방향은 최신 점검 문서의 결론을 따른다: 대량 cold 생성보다 seed bank + 공식 OOS + branch attribution + evidence lineage.

## Research Findings
- 최근 2커밋:
  - `81fbcfe03` 조건식 연구 현황 재검토 문서화.
  - `067ef1841` 공식 OOS 후속 연구 기록 추가.
- 현재 브랜치는 `origin/lazycodex/tick-sparse-positive-generation-improvement-20260604` 대비 36 commits ahead이며 미커밋/미추적 변경이 많다.
- `STOM_Version_2U_C-ai-strategy-loop` 이후 parent 원격까지 +319 commits, first-parent 186 commits, merge commits 59개가 누적됐다.
- 직접 anchor 기준으로는 `STOM_Version_2U_C-ai-strategy-loop..HEAD`가 +355 commits이고 역방향은 0 commits다.
- `git ls-remote` 기준 `origin/STOM_Version_2U_C-ai-strategy-loop`는 없다. PR base로 쓰려면 먼저 anchor를 원격에 push해야 한다.
- `wt-webbt`는 `feature/webbt-followup-gates-20260618` at `19d82beb`로 clean이며 upstream이 없다. 추후 파일 분리 대시보드 PR용 보조 워크트리로 남긴다.
- 최신 재검토 문서 점수: 전체 연구 프로세스 72점, 조건식 생성 AI 자체 67점, 검증/OOS/포트폴리오 76점, 최종 승격 준비도 56점.
- 최신 문서가 남긴 우선 부족분: robust 공식 OOS, evidence lineage, branch attribution, human-case corpus, latest update_log dashboard 노출, backtest.py 계약 안정화.
- 대시보드에는 `ResearchRecordsPanel`, `EvolutionGuiParityPanel`, `/research_records`, `/evolution_gui_parity`가 이미 추가되어 있다.
- 대시보드 전수검사에 필요한 기존 가드가 있다: `track-z-harness`, `check-missing-imports`, duplicate globals, per-tab sweep, frontend bundle model.
- `docs/update_log/2026-06-18_post_20260618_research_dashboard_handoff.md`는 다음 공식 OOS 1순위를 `저시총 제외 방어 조합`으로 고정했다.
- 같은 핸드오프는 대시보드 부족분을 후보 별칭, 최신 update_log 자동 노출, 요일/시간별 그래프 확인, 증거 종류 라벨 명확화로 정리했다.
- `CODEX_DEV_HANDOFF.md`는 대시보드 개발을 `wt-webbt`에서 격리하고, `wt-dev` 연구 파일을 건드리지 않는 운영 모델을 고정한다.
- `PROG_P7_FIELD_DIFF.md`는 HoF 두 패널을 병합하지 않는 결정을 이미 내렸다. 계획에서는 “중복 제거 후보”가 아니라 “발산 기능 보존 + 라벨/분류 명확화”로 다룬다.
- 현재 하위 에이전트 도구가 노출되지 않아 Metis 호출을 실제로 수행할 수 없다. 계획에는 Metis 대체 gap review와 High Accuracy Review 선택지를 남긴다.

## Open Questions
- 기본값: 첫 실행 목표는 `정리/거버넌스 + 연구 inventory`로 둔 뒤, 공식 OOS는 누락/네이밍/대시보드 라벨 기준을 고정한 다음 실행한다.
- 기본값: PR 재구성은 `STOM_Version_2U_C-ai-strategy-loop` catch-up PR을 기본 경로로 삼되, +355 commits PR이 너무 크면 wave별 integration/replay 브랜치로 쪼갠다. 실제 push/PR/merge는 사용자가 실행을 명시하면 진행한다.
- 기본값: 대시보드 전수검사 결과는 markdown inventory와 JSON audit artifact를 모두 남긴다. 자동 audit script는 반복 가치가 확인된 항목만 만든다.

## Scope Boundaries
- INCLUDE: 브랜치/커밋/PR 재정리 계획, 연구 기록 체계화, 연구 관리 프로세스, 대시보드 전수검사, 네이밍 규칙, 계획 페이지 작성.
- EXCLUDE: 실거래 연결, KHOPENAPI 로그인, V3K gate 4~6 진행, `_database/` 운영 쓰기, `backtest.py` 즉시 수정, 대시보드 기능 구현 실행.
