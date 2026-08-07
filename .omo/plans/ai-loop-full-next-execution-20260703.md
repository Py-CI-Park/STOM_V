# AI 조건식 루프 다음 실행 통합 계획

## TL;DR
> **Summary**: `2c3ac861` 핸드오프 이후 작업을 Plan A -> Plan C -> Plan B -> Plan D 순서로 실행한다. 이 `.omo` 파일은 원문 Plan 문서를 대체하지 않고, 원문을 반드시 읽게 만드는 상위 오케스트레이션 계획이다.
> **Deliverables**:
> - Plan A A1/A2 코드 커밋 2건, A3 승인 게이트 보류 기록
> - CSS_V7 25개+조합 2세트 검증 원장과 Plan D 입력용 생존 목록
> - lattice 576시드 생성/등재/스모크/coverage/정제/OOS/포트폴리오 산출물
> - Plan D 1기 seed pool, OOS survivor, KPI/result/update_log
> **Effort**: XL, 3~7일 이상
> **Parallel**: YES - 검토/기록은 병렬 가능하나 DB 쓰기, git commit, OOS 개봉은 직렬
> **Critical Path**: T0 -> T1 -> T2 -> T4 -> T5 -> T6 -> T7 -> T8 -> T9 -> T10

## Context
### Original Request
사용자는 `$ulw-plan`으로 위 단계별 상세와 이전 핸드오프 내용을 고려해 전체 진행 계획을 수립하라고 요청했다.

### Interview Summary
- 실행 순서는 핸드오프 기준 Plan A, Plan C, Plan B, Plan D다.
- 사용자 표의 "Plan B-1/B-2/B-3"은 편의상 단계명이며, 원문 Plan B 내부 번호와 다르다. 이 계획은 `Stage N`과 원문 `Plan B B1~B5`를 분리한다.
- Plan A A3는 사용자 명시 승인 전 코드 수정 금지다.
- code lane은 전체 unit gate를 쓰고, research-only lane은 원문 계획서의 자기 테스트, positive control, lineage, `git diff --check`를 쓴다.

### Metis Review (gaps addressed)
- Plan B 번호 충돌: `Stage 6`은 원문 Plan B B1.1~B1.2, `Stage 7`은 원문 B1.3, `Stage 8`은 원문 B2로 명시했다.
- Test gate 충돌: 전체 `tests/unit/`은 Plan A 코드 커밋에만 필수로 둔다. Plan C/D 연구 실행은 원문 문서대로 전체 테스트 금지, 자기 테스트/positive control/lineage 중심이다.
- INSERT-only 위험: `cli/strategy_generator.py:144`의 `save_strategy_to_db`는 기존명 UPDATE 경로가 있으므로, 모든 DB 등재는 사전 충돌 조회와 `INSERT` 전용 래퍼만 허용한다.
- Positive control 기준 파일 미확정: T0에서 직전 공식 결과 JSON을 발견해 `baseline_positive_control_source.json`에 고정하지 못하면 Plan C 이후를 중단한다.
- Dirty worktree: 기존 dashboard 7파일, `.gjc/`, `.omo/`는 보존하고 `git add -A` 금지로 처리한다.

### Read-First Source Package
이 통합 계획은 아래 문서들의 실행 결정을 요약/구조화한 **상위 실행 계획**이다. 원문 전문을 모두 복사한 문서는 아니므로, 실행 에이전트는 T0에서 이 목록을 읽고 체크해야 한다.

| 우선 | 문서 | 포함 수준 | 실행상 의미 |
|---:|---|---|---|
| 0 | `docs/update_log/2026-07-03_ai_loop_full_implementation_session_handoff.md` | 핵심 순서/불변 조건 반영, 전문 미복사 | 전체 시작점. 단, 문서 내 HEAD `12efdc23`은 현재 `2c3ac861` 핸드오프 커밋으로 보정한다. |
| 1 | `docs/research/condition_research/2026-07-02_ai_loop_full_audit_and_code_update_plan.md` | 감사 결론만 반영, 전문 미복사 | 병목이 "분석->후보 연결"이라는 배경과 Phase 0~6 설계 근거. |
| 2 | `docs/update_log/2026-07-02_ai_loop_phase_implementation_record.md` | 이월 항목/게이트 원칙 반영, 전문 미복사 | Plan A A1/A2/A3의 출처와 Phase 구현 완료 기록. |
| 3 | `docs/research/condition_research/2026-07-02_ai_loop_execution_checklist.md` | 완료 상태만 반영, 전문 미복사 | Phase 0~6 체크 완료 여부 확인용. |
| 4 | `docs/research/condition_research/plans/2026-07-02_plan_A_deferred_code_tasks.md` | 주요 실행 조건/테스트/중단 조건 반영 | T1~T3의 정본. A3는 승인 전 보류. |
| 5 | `docs/research/condition_research/plans/2026-07-02_plan_C_chart_sulsa_validation_protocol.md` | 주요 실행 단계/예산/중단 조건 반영 | T4~T5의 정본. CSS_V7 검증은 이 문서를 우선한다. |
| 6 | `docs/research/condition_research/plans/2026-07-02_plan_B_research_execution_roadmap.md` | 주요 실행 단계/예산/중단 조건 반영 | T6~T9의 정본. 이 계획의 Stage 번호와 원문 B1~B5 번호를 혼동하지 않는다. |
| 7 | `docs/research/condition_research/plans/2026-07-02_plan_D_seed_research_program.md` | 주요 실행 단계/종료 조건 반영 | T10의 정본. Plan C/B 산출물이 입력이다. |
| 8 | `docs/research/condition_research/chart_sulsa/2026-07-02_chart_sulsa_v7_condition_catalog.md` | 자산 위치만 반영, 전문 미복사 | CSS_V7 25개 목록/코드 sha/조합 2세트 확인용. |
| 9 | `docs/research/condition_research/chart_sulsa/provenance_registry.jsonl` | 출처 원장 필요성 반영 | CSS_V7 원천 문서 sha/섹션/코드 sha 역추적용. |
| 10 | `docs/research/condition_research/chart_sulsa/db_insert_receipt_20260702.json` | DB 등재 상태 반영 | `_database/strategy.db` CSS_V7 25건 등재 확인용. |

포함 기준: 이 파일 하나만으로 실행 순서와 중단 조건은 알 수 있지만, 각 Plan 문서의 상세 명령/config 전문은 원문을 읽어야 한다. 따라서 "모든 문서 내용을 계획 파일에 완전 병합"한 상태가 아니라 "모든 문서를 읽는 순서와 실행 결정을 통합"한 상태다.

### Source Authority Rule
원문 문서가 정본이다. 이 `.omo` 계획은 실행 순서, 의존성, 공통 안전장치, 증거 위치를 묶는 컨트롤 타워로만 사용한다.

| 상황 | 적용 규칙 |
|---|---|
| 원문 Plan 문서와 이 `.omo` 계획의 세부 명령/config가 다름 | 원문 Plan 문서를 우선한다. |
| 이 `.omo` 계획이 원문보다 더 엄격한 안전장치를 둠 | 더 엄격한 쪽을 따른다. 예: INSERT-only 사전 충돌 검사, OOS preregistration, path-scoped staging. |
| 핸드오프 문서의 HEAD `12efdc23` vs 현재 HEAD `2c3ac861` | 현재 HEAD `2c3ac861`을 우선한다. 핸드오프 커밋이 문서 작성 후 추가된 상태로 본다. |
| 사용자 단계명 `Plan B-1/B-2/B-3` vs 원문 B1~B5 번호 | 이 `.omo`의 Stage 번호는 일정 관리용이고, 실제 실행은 원문 Plan B 내부 번호를 따른다. |
| 전체 unit gate 범위 충돌 | Plan A 코드 커밋은 full unit gate. Plan C/B/D 연구 실행은 원문대로 자기 테스트/positive control/lineage 중심. |

각 실행자는 작업을 시작하기 전에 해당 원문 문서를 **전문 전체로 EOF까지** 직접 열어 읽고, `.omo/evidence/ai-loop-full-next-execution-20260703/source_read_receipt.md`에 "읽은 문서, read_scope=full_document, 읽은 시각, line_count, sha256, 적용한 섹션"을 남긴다. 필요한 섹션만 발췌해서 읽는 것은 불충분하다. 이 receipt가 없으면 해당 단계는 시작하지 않는다.

## Work Objectives
### Core Objective
분석 -> 후보 연결 병목을 해소한 새 루프가 실제 후보 검증/채굴/정제까지 안전하게 진행되는지 검증하고, 생존 후보를 Plan D seed program으로 넘긴다.

### Deliverables
- `.omo/evidence/ai-loop-full-next-execution-20260703/` 하위 preflight, QA, final evidence
- Plan A 실행 로그: `docs/update_log/<date>_deferred_code_tasks_execution_log.md`
- CSS_V7 검증 산출: `artifacts/chart_sulsa_validation_20260702/`, `docs/research/condition_research/chart_sulsa/css_v7_validation_ledger.jsonl`
- lattice 산출: `docs/research/condition_research/generated_conditions/lattice/`, `docs/research/condition_research/research_runs/seed_lattice_20260702/`
- Plan D 산출: `docs/research/condition_research/generated_conditions/seed_pool.jsonl`, `oos_survivors.jsonl`, result/management/update_log

### Definition of Done (verifiable conditions with commands)
- `git rev-parse --short HEAD`가 시작 기준 `2c3ac861` 이상에서 이어진다.
- Plan A A1/A2 커밋이 있으면 각각 focused pytest, `PYTHONUTF8=1 python -m pytest tests/unit/ -q`, `python scripts/verify_nonrelease_sync.py` 결과가 기록돼 있다.
- Plan C 유니크 쌍 전건이 `생존|기각|보류` 중 하나로 append-only ledger에 남아 있다.
- Plan B 스모크 결과, coverage/gaps/batch_plan, revival registry, n_trials 누계가 남아 있다.
- Plan D 1기 종료 시 상위 3개 시드 동결, 통합 평가 1회 이상, KPI 표가 result 문서에 있다.
- 보호 경로 확인: `git status --short -- backtest/graph _database_v3k_shadow _log backup`에 의도치 않은 항목이 없다.

### Must Have
- 연구-only: `can_promote/export/live=false`, `hypothesis_seed` 라벨 유지.
- DB 쓰기 전 백업, INSERT-only, 이름 충돌 시 중단.
- OOS-blind: 동결/사전등록 전 OOS 접근 금지.
- n_trials 정직 합산, revival registry append-only.
- 커밋은 경로 지정 staging + 한글 메시지. `git add -A` 금지.
- 각 단계 시작 전 원문 Plan 문서를 전문 전체로 EOF까지 읽고 `source_read_receipt.md`에 `read_scope=full_document`, `line_count`, `sha256`, 적용 섹션을 기록.

### Must NOT Have
- `backtest/graph/` 변경 금지.
- `_database/strategy.db`와 `ai_strategy_loop/state/loop_strategies.db` 기존 행 UPDATE/DELETE 금지.
- A3 승인 없는 promotion-review/승격/export/live 배선 금지.
- 기존 dashboard 7파일, `.gjc/`, 기존 `.omo` 잔재 정리/스테이징 금지.
- OOS 결과를 보고 B3/D 라운드 후보를 조정하는 행위 금지.

## Verification Strategy
> ZERO HUMAN INTERVENTION - all verification is agent-executed except A3 approval, which is a hard block.
- Test decision: tests-after. Plan A source changes require focused tests then full unit gate. Research-only stages use targeted tests, positive control, lineage, schema checks.
- QA policy: Every task has agent-executed happy/failure scenarios.
- Evidence root: `.omo/evidence/ai-loop-full-next-execution-20260703/`.

## Execution Strategy
### Parallel Execution Waves
Wave 1: T0 preflight.
Wave 2: T1 and T2 sequential source commits; T3 gate record after T2.
Wave 3: T4 Plan C preparation, T5 Plan C validation.
Wave 4: T6 Plan B seed/DB registration, T7 overnight smoke, T8 coverage.
Wave 5: T9 Plan B refinement/OOS/portfolio.
Wave 6: T10 Plan D survivor seed program.
Wave 7: Final verification wave.

### Dependency Matrix
| Task | Blocks | Blocked By |
|---|---|---|
| T0 | T1,T4,T6,T10 | none |
| T1 | T2 | T0 |
| T2 | T3,T4 | T1 |
| T3 | none | T2 |
| T4 | T5 | T0,T2 |
| T5 | T10 | T4 |
| T6 | T7 | T0,T2 |
| T7 | T8 | T6 |
| T8 | T9,T10 | T7 |
| T9 | T10 | T8 |
| T10 | Final | T5,T9 |

## TODOs
> Implementation + Test = ONE task. EVERY task has References + Acceptance Criteria + QA Scenarios.

- [x] T0. Preflight, Scope Lock, And Evidence Root

  **What to do**: Capture current state, resolve the handoff snapshot mismatch, discover the positive-control baseline file, verify required passports, and freeze protected-path/dirty-worktree assumptions before any code or DB work.

  **Must NOT do**: Do not edit source, DB, `.gjc`, dashboard bundle files, or protected runtime paths.

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: T1,T4,T6,T10 | Blocked By: none

  **References**:
  - Handoff: `docs/update_log/2026-07-03_ai_loop_full_implementation_session_handoff.md:43` - internal snapshot says `12efdc23`; current HEAD is expected to be `2c3ac861`.
  - Plan A: `docs/research/condition_research/plans/2026-07-02_plan_A_deferred_code_tasks.md:9`.
  - Plan C: `docs/research/condition_research/plans/2026-07-02_plan_C_chart_sulsa_validation_protocol.md:187`.
  - Plan B: `docs/research/condition_research/plans/2026-07-02_plan_B_research_execution_roadmap.md:397`.
  - Plan D: `docs/research/condition_research/plans/2026-07-02_plan_D_seed_research_program.md:123`.

  **Acceptance Criteria**:
  - [ ] Create `.omo/evidence/ai-loop-full-next-execution-20260703/t0-preflight.md`.
  - [ ] Create `.omo/evidence/ai-loop-full-next-execution-20260703/source_read_receipt.md` listing every read-first source document, `read_scope=full_document`, read timestamp, line_count, sha256, and sections used.
  - [ ] Record `git rev-parse --short HEAD`, `git status --short --branch`, and `git log --oneline -15`.
  - [ ] Record dirty groups and state that dashboard 7 files, `.gjc/`, and unrelated `.omo/` are out of scope.
  - [ ] Verify `docs/research/condition_research/condition_passports/rr8_12_turnover_min_902_1.5.md` exists.
  - [ ] Discover positive-control input by searching known official result artifacts; write chosen path and sha256 to `.omo/evidence/ai-loop-full-next-execution-20260703/baseline_positive_control_source.json`. If no file is defensible, stop Plan C/B/D and write blocker.
  - [ ] Record `git status --short -- backtest/graph _database_v3k_shadow _log backup`.

  **QA Scenarios**:
  ```text
  Scenario: Happy path preflight
    Tool: powershell
    Steps: run the commands above and write both markdown and JSON evidence.
    Expected: HEAD/status captured; passport exists; positive-control source chosen; protected status captured.
    Evidence: .omo/evidence/ai-loop-full-next-execution-20260703/t0-preflight.md

  Scenario: Missing positive-control source
    Tool: powershell
    Steps: search returns no defensible official result JSON.
    Expected: write blocker file and do not start Plan C/B/D validation commands.
    Evidence: .omo/evidence/ai-loop-full-next-execution-20260703/t0-positive-control-blocker.md
  ```

  **Commit**: NO | Message: n/a | Files: evidence only

- [x] T1. Plan A A1 - FailoverProvider

  **What to do**: Implement Plan A A1 exactly: add the provider failover file, minimally wire `_make_provider_with_proxy`, add tests, run focused and full gates, commit in Korean.

  **Must NOT do**: Do not modify unrelated provider, optimizer, promotion, export, live, DB, or dashboard files.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: T2 | Blocked By: T0

  **References**:
  - Plan A A1: `docs/research/condition_research/plans/2026-07-02_plan_A_deferred_code_tasks.md:66`.
  - New test required: `docs/research/condition_research/plans/2026-07-02_plan_A_deferred_code_tasks.md:133`.
  - Completion gate: `docs/research/condition_research/plans/2026-07-02_plan_A_deferred_code_tasks.md:149`.

  **Acceptance Criteria**:
  - [ ] `source_read_receipt.md` has a `read_scope=full_document` entry for `2026-07-02_plan_A_deferred_code_tasks.md`; sections A1 and common gate rules are marked as applied.
  - [ ] `PYTHONUTF8=1 python -m pytest tests/unit/test_provider_failover.py -q` passes.
  - [ ] `PYTHONUTF8=1 python -m pytest tests/unit/ -q` has only Plan A allowed baseline failures.
  - [ ] `python scripts/verify_nonrelease_sync.py` passes.
  - [ ] `docs/update_log/<date>_deferred_code_tasks_execution_log.md` records A1 commit hash and gate results.
  - [ ] Commit message is Korean and stages only A1 files.

  **QA Scenarios**:
  ```text
  Scenario: primary auth failure falls back deterministically
    Tool: pytest
    Steps: run test_provider_failover.py with fake providers where primary raises auth and secondary returns a response.
    Expected: secondary response is returned, fallback event is recorded, prompt credit rules hold.
    Evidence: .omo/evidence/ai-loop-full-next-execution-20260703/t1-provider-failover.txt

  Scenario: non-auth failure does not silently consume generations
    Tool: pytest
    Steps: fake primary raises non-auth error.
    Expected: error propagates or fail-closed behavior matches Plan A; no hidden fallback.
    Evidence: .omo/evidence/ai-loop-full-next-execution-20260703/t1-provider-failover-error.txt
  ```

  **Commit**: YES | Message: `조건식 연구 provider 장애 폴백 추가` | Files: Plan A A1 exact files

- [x] T2. Plan A A2 - Provider Upper Entrypoints

  **What to do**: Implement Plan A A2 exactly: provider factory resolution, `cli/ai_controller.py` entrypoint handoff, `cli/research_optimizer.py` runner handoff, tests, gates, Korean commit.

  **Must NOT do**: Do not change `allowed_fields` filtering semantics except the planned reserved-key `pop` style. Do not call promotion-review logic.

  **Parallelization**: Can Parallel: NO | Wave 2 | Blocks: T3,T4,T6 | Blocked By: T1

  **References**:
  - Plan A A2: `docs/research/condition_research/plans/2026-07-02_plan_A_deferred_code_tasks.md:160`.
  - Entrypoints: `docs/research/condition_research/plans/2026-07-02_plan_A_deferred_code_tasks.md:199`.
  - Tests: `docs/research/condition_research/plans/2026-07-02_plan_A_deferred_code_tasks.md:217`.

  **Acceptance Criteria**:
  - [x] `source_read_receipt.md` has a `read_scope=full_document` entry for `2026-07-02_plan_A_deferred_code_tasks.md`; sections A2 and common gate rules are marked as applied.
  - [x] `PYTHONUTF8=1 python -m pytest tests/unit/test_research_provider_entrypoints.py -q` passes.
  - [x] Relevant existing tests pass: `PYTHONUTF8=1 python -m pytest tests/unit/test_research_loop*.py tests/unit/test_research_optimizer*.py -q`.
  - [x] `PYTHONUTF8=1 python -m pytest tests/unit/ -q` has only allowed baseline failures.
  - [x] `python scripts/verify_nonrelease_sync.py` passes.
  - [x] A2 commit is separate from A1.

  **QA Scenarios**:
  ```text
  Scenario: controller passes provider without enabling candidate pack by default
    Tool: pytest
    Steps: inject provider in config, keep llm_candidate_pack_enabled=False.
    Expected: provider is accepted but pack generation is not attempted.
    Evidence: .omo/evidence/ai-loop-full-next-execution-20260703/t2-provider-entrypoints.txt

  Scenario: reserved provider key does not leak into ResearchLoopConfig
    Tool: pytest
    Steps: pass provider factory metadata through ai_controller and optimizer path.
    Expected: config construction succeeds and reserved keys are consumed before dataclass construction.
    Evidence: .omo/evidence/ai-loop-full-next-execution-20260703/t2-provider-entrypoints-error.txt
  ```

  **Commit**: YES | Message: `조건식 연구 provider 상위 진입점 연결` | Files: Plan A A2 exact files

- [x] T3. Plan A A3 Approval Gate Record

  **What to do**: Record that A3 is blocked until explicit user approval. If approval is absent, write an update_log note or append to the Plan A execution log stating no promotion-review code was touched.

  **Must NOT do**: Do not edit `promotion_preconditions`, `condition_discovery`, export, live, or final promotion paths.

  **Parallelization**: Can Parallel: YES | Wave 2 | Blocks: none | Blocked By: T2

  **References**:
  - A3 approval gate: `docs/research/condition_research/plans/2026-07-02_plan_A_deferred_code_tasks.md:247`.
  - Approval-before-code rule: `docs/research/condition_research/plans/2026-07-02_plan_A_deferred_code_tasks.md:251`.

  **Acceptance Criteria**:
  - [x] `source_read_receipt.md` has a `read_scope=full_document` entry for `2026-07-02_plan_A_deferred_code_tasks.md`; section A3 is marked as applied.
  - [x] `git diff --name-only` contains no promotion/export/live path from A3.
  - [x] Execution log says A3 status is `blocked_pending_user_approval`.
  - [x] `rg -n "can_promote=True|can_export=True|final promotion|export" ai_strategy_loop cli docs/update_log/<date>_deferred_code_tasks_execution_log.md` shows no new enabling path.

  **QA Scenarios**:
  ```text
  Scenario: no approval present
    Tool: powershell
    Steps: inspect conversation and execution log.
    Expected: A3 is marked blocked and no code files were touched.
    Evidence: .omo/evidence/ai-loop-full-next-execution-20260703/t3-a3-gate.txt

  Scenario: accidental A3 path touched
    Tool: powershell
    Steps: run git diff --name-only and rg for promotion/export enabling terms.
    Expected: any hit outside documentation causes immediate stop and rollback request, not commit.
    Evidence: .omo/evidence/ai-loop-full-next-execution-20260703/t3-a3-gate-error.txt
  ```

  **Commit**: OPTIONAL | Message: `승격 게이트 보류 상태 기록` | Files: update_log only

- [ ] T4. Plan C Static Gate, Pair List, And Loop DB Mirror

  **What to do**: Run CSS_V7 static rechecks, create unique pair list with combo priority, mirror CSS_V7 rows into `ai_strategy_loop/state/loop_strategies.db` using INSERT-only guarded logic, and record rollback data.

  **Must NOT do**: Do not update existing strategy rows. Do not use `save_strategy_to_db` without a preceding no-row collision check and abort-on-exists behavior.

  **Parallelization**: Can Parallel: NO | Wave 3 | Blocks: T5 | Blocked By: T0,T2

  **References**:
  - Plan C input assets: `docs/research/condition_research/plans/2026-07-02_plan_C_chart_sulsa_validation_protocol.md:16`.
  - Unique pairs: `docs/research/condition_research/plans/2026-07-02_plan_C_chart_sulsa_validation_protocol.md:35`.
  - Mirror INSERT: `docs/research/condition_research/plans/2026-07-02_plan_C_chart_sulsa_validation_protocol.md:76`.
  - UPDATE risk: `cli/strategy_generator.py:144`.

  **Acceptance Criteria**:
  - [ ] `source_read_receipt.md` has a `read_scope=full_document` entry for `2026-07-02_plan_C_chart_sulsa_validation_protocol.md`; sections 0~4 are marked as applied.
  - [ ] Static check reports `bad=0` for provenance vs `_database/strategy.db`.
  - [ ] `artifacts/chart_sulsa_validation_20260702/pairs_unique.json` exists and has combo priorities for the 2 recommended combos.
  - [ ] Loop DB backup exists before `--apply`.
  - [ ] Dry-run reports collision count 0; `--apply` reports only created/inserted rows.
  - [ ] `mirror_insert_receipt.json` records backup path, row counts, sha256 recheck, and restore command.
  - [ ] Duplicate-name dry-run scenario proves the script aborts before UPDATE.

  **QA Scenarios**:
  ```text
  Scenario: valid mirror insert
    Tool: powershell/python
    Steps: run static checks, dry-run, backup, apply, and post-apply sha recheck.
    Expected: 25 CSS_V7 rows available in loop DB, no updates, receipt written.
    Evidence: artifacts/chart_sulsa_validation_20260702/mirror_insert_receipt.json

  Scenario: duplicate name abort
    Tool: python
    Steps: run mirror script against a copied DB containing a pre-existing CSS_V7 name.
    Expected: non-zero/abort report, no UPDATE, original code unchanged.
    Evidence: .omo/evidence/ai-loop-full-next-execution-20260703/t4-mirror-duplicate-abort.json
  ```

  **Commit**: NO for DB; OPTIONAL for new research scripts/docs with Korean message and explicit paths only

- [ ] T5. Plan C CSS_V7 Validation And Plan D Export

  **What to do**: Execute Plan C combo-first validation: positive control, smoke, train, OOS/WF, slippage advisory, ledger append, survivor export.

  **Must NOT do**: Do not run full unit tests for this research-only stage. Do not delete rejected seeds; register them for revival. Do not promote/export/live anything.

  **Parallelization**: Can Parallel: PARTIAL | Wave 3 | Blocks: T10 | Blocked By: T4

  **References**:
  - Plan C execution tool/profile: `docs/research/condition_research/plans/2026-07-02_plan_C_chart_sulsa_validation_protocol.md:86`.
  - Smoke/train/OOS: `docs/research/condition_research/plans/2026-07-02_plan_C_chart_sulsa_validation_protocol.md:105`.
  - Evaluation order/budget: `docs/research/condition_research/plans/2026-07-02_plan_C_chart_sulsa_validation_protocol.md:150`.
  - Termination: `docs/research/condition_research/plans/2026-07-02_plan_C_chart_sulsa_validation_protocol.md:187`.

  **Acceptance Criteria**:
  - [ ] `source_read_receipt.md` has a `read_scope=full_document` entry for `2026-07-02_plan_C_chart_sulsa_validation_protocol.md`; sections 5~12 are marked as applied.
  - [ ] Positive control receipt says `gate_healthy`; otherwise stop.
  - [ ] Combos run first, then MASTER/OPT, then remaining pattern pairs.
  - [ ] `docs/research/condition_research/chart_sulsa/css_v7_validation_ledger.jsonl` has append-only events for `smoke|train|oos|wf|slippage|oos_usage`.
  - [ ] Every unique pair has final status `생존|기각|보류`.
  - [ ] rejected/no_go pairs are in `css_v7_revival_registry.jsonl`.
  - [ ] Survivor export is in Plan D seed-pool input format.
  - [ ] `python scripts/check_research_evidence_lineage.py --report artifacts/chart_sulsa_validation_20260702/lineage_report.json` runs and result is attached.

  **QA Scenarios**:
  ```text
  Scenario: combo-first validation completes
    Tool: powershell/python
    Steps: run positive control, batch runner per Plan C, ledger append, lineage check.
    Expected: final ledger covers all pairs and survivor export exists.
    Evidence: docs/research/condition_research/chart_sulsa/css_v7_validation_ledger.jsonl

  Scenario: positive control unhealthy
    Tool: powershell/python
    Steps: run scripts/run_positive_control.py using T0 baseline source.
    Expected: if not gate_healthy, write blocker and do not run smoke/train/OOS.
    Evidence: artifacts/chart_sulsa_validation_20260702/positive_control_receipt.json
  ```

  **Commit**: OPTIONAL | Message: `CSS_V7 조건식 검증 결과 기록` | Files: research result docs/ledgers only, DB excluded unless explicitly intended

- [ ] T6. Stage 6 / Plan B B1.1-B1.2 - 576 Seed Generation And Loop DB Registration

  **What to do**: Build lattice seeds, passports, provenance, register seed pairs into `ai_strategy_loop/state/loop_strategies.db` only, with INSERT-only and backup/rollback.

  **Must NOT do**: Do not register lattice seeds into live `_database/strategy.db`. Do not use UPDATE path. Do not run smoke batch in this task.

  **Parallelization**: Can Parallel: NO | Wave 4 | Blocks: T7 | Blocked By: T0,T2

  **References**:
  - Plan B B1.1: `docs/research/condition_research/plans/2026-07-02_plan_B_research_execution_roadmap.md:37`.
  - Plan B B1.2 loop DB target: `docs/research/condition_research/plans/2026-07-02_plan_B_research_execution_roadmap.md:58`.
  - Completion: `docs/research/condition_research/plans/2026-07-02_plan_B_research_execution_roadmap.md:82`.

  **Acceptance Criteria**:
  - [ ] `source_read_receipt.md` has a `read_scope=full_document` entry for `2026-07-02_plan_B_research_execution_roadmap.md`; sections B1.1~B1.2 are marked as applied.
  - [ ] `PYTHONUTF8=1 python -m cli.seed_lattice build --out-dir docs/research/condition_research/generated_conditions/lattice` reports `"seed_count": 576`.
  - [ ] 576 passport files are present unless lane/family filter is explicitly documented.
  - [ ] Registration dry-run collision count is 0.
  - [ ] Loop DB backup exists before apply.
  - [ ] pairs JSON and provenance JSONL line counts match seed count.
  - [ ] Duplicate-name test proves abort-before-update.

  **QA Scenarios**:
  ```text
  Scenario: full 576 seed generation and registration
    Tool: powershell/python
    Steps: build seeds, dry-run register, backup loop DB, apply register, count rows.
    Expected: 576 pair mappings exist, provenance complete, no UPDATE actions.
    Evidence: docs/research/condition_research/research_runs/seed_lattice_20260702/register_lattice_receipt.json

  Scenario: DB name collision
    Tool: python
    Steps: run registration against copied DB with one pre-existing LAT_* name.
    Expected: abort with collision report, no row update.
    Evidence: .omo/evidence/ai-loop-full-next-execution-20260703/t6-lattice-collision.json
  ```

  **Commit**: OPTIONAL | Message: `격자 시드 생성과 연구 DB 등재 기록` | Files: generated condition docs, scripts, receipts only as intended

- [ ] T7. Stage 7 / Plan B B1.3 - Overnight Smoke Batch

  **What to do**: Run 576-pair smoke in the defined order: tick first, then min. Create resume manifest, checkpoint cadence, process hygiene receipt, and smoke result exports.

  **Must NOT do**: Do not start min before tick result extraction finishes. Do not kill processes without dry-run inventory and PID exclusion review.

  **Parallelization**: Can Parallel: LIMITED | Wave 4 | Blocks: T8 | Blocked By: T6

  **References**:
  - Plan B smoke command: `docs/research/condition_research/plans/2026-07-02_plan_B_research_execution_roadmap.md:86`.
  - Tick before min: `docs/research/condition_research/plans/2026-07-02_plan_B_research_execution_roadmap.md:129`.
  - Process cleanup: `docs/research/condition_research/plans/2026-07-02_plan_B_research_execution_roadmap.md:146`.
  - Completion/estimate: `docs/research/condition_research/plans/2026-07-02_plan_B_research_execution_roadmap.md:165`.

  **Acceptance Criteria**:
  - [ ] `source_read_receipt.md` has a `read_scope=full_document` entry for `2026-07-02_plan_B_research_execution_roadmap.md`; sections B1.3 and B1.5 are marked as applied.
  - [ ] Write `docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_resume_manifest.json` with run ids, pairs path, config path, start time, checkpoint interval 30 minutes, max shift target 8 hours per lane.
  - [ ] tick smoke run completes or records honest per-pair errors; first 10-pair timing estimate is recorded.
  - [ ] `smoke_results_tick.json` is exported.
  - [ ] min smoke starts only after tick export exists; `smoke_results_min.json` exported.
  - [ ] Any cleanup uses dry-run inventory first and records excluded PIDs.

  **QA Scenarios**:
  ```text
  Scenario: tick then min overnight smoke
    Tool: powershell
    Steps: run claude_candidate_batch_eval for tick, export results, then run min and export.
    Expected: both result JSONs exist and all pairs have ok or honest error status.
    Evidence: docs/research/condition_research/research_runs/seed_lattice_20260702/smoke_batch_receipt.json

  Scenario: abnormal exit recovery
    Tool: powershell
    Steps: run cleanup_orphan_backtest_procs.py dry-run, verify no protected PID, then resume from manifest.
    Expected: no unrelated process killed; resume manifest records next unprocessed pair/family.
    Evidence: docs/research/condition_research/research_runs/seed_lattice_20260702/orphan_cleanup_receipt.json
  ```

  **Commit**: NO during running batch; OPTIONAL after completion with Korean result log

- [ ] T8. Stage 8 / Plan B B2 - Coverage And Smoke-Plan

  **What to do**: Run coverage and smoke-plan for tick/min using smoke results, register no_go seeds into revival, and produce go-cell plan for refinement.

  **Must NOT do**: Do not discard no_go seeds. Do not manually edit existing ledger rows.

  **Parallelization**: Can Parallel: YES by lane | Wave 4 | Blocks: T9,T10 | Blocked By: T7

  **References**:
  - Plan B B2 commands: `docs/research/condition_research/plans/2026-07-02_plan_B_research_execution_roadmap.md:180`.
  - go/no-go: `docs/research/condition_research/plans/2026-07-02_plan_B_research_execution_roadmap.md:201`.
  - revival/n_trials: `docs/research/condition_research/plans/2026-07-02_plan_B_research_execution_roadmap.md:211`.
  - Completion: `docs/research/condition_research/plans/2026-07-02_plan_B_research_execution_roadmap.md:223`.

  **Acceptance Criteria**:
  - [ ] `source_read_receipt.md` has a `read_scope=full_document` entry for `2026-07-02_plan_B_research_execution_roadmap.md`; section B2 is marked as applied.
  - [ ] tick and min each produce coverage, gaps, and batch_plan JSON.
  - [ ] no_go seeds are all appended to `revival_registry.jsonl`.
  - [ ] n_trials attempt counts from smoke are included in batch_plan and update_log.
  - [ ] cell reverse mapping failure is <=10%; otherwise return to T6.

  **QA Scenarios**:
  ```text
  Scenario: coverage succeeds for both lanes
    Tool: powershell
    Steps: run cli.seed_lattice coverage and smoke-plan for tick and min.
    Expected: 3 JSON outputs per lane and go/no_go counts recorded.
    Evidence: docs/research/condition_research/research_runs/seed_lattice_20260702/batch_plan_tick.json

  Scenario: label reverse mapping failure
    Tool: python
    Steps: validate smoke result labels can map to cell_id.
    Expected: if >10% fail, stop and write B1 label-regression blocker.
    Evidence: .omo/evidence/ai-loop-full-next-execution-20260703/t8-label-mapping-blocker.json
  ```

  **Commit**: OPTIONAL | Message: `격자 스모크 예산 판정 결과 기록` | Files: research outputs/update_log

- [ ] T9. Stage 9 / Plan B B3-B5 - Refinement, Frozen OOS, Portfolio

  **What to do**: For go cells, run B3 refinement rounds with feedback config, freeze candidates before OOS, run B4 OOS/WF only after preregistration, then run B5 portfolio assembly when 2+ OOS survivors exist.

  **Must NOT do**: Do not access OOS before freeze/preregistration. Do not use promotion-review. Do not compare portfolio frame numbers as if they were single-strategy frame numbers.

  **Parallelization**: Can Parallel: LIMITED by frozen candidate, but DB/OOS ledger writes are serial | Wave 5 | Blocks: T10 | Blocked By: T8

  **References**:
  - B3 config: `docs/research/condition_research/plans/2026-07-02_plan_B_research_execution_roadmap.md:234`.
  - B3 outputs/rules: `docs/research/condition_research/plans/2026-07-02_plan_B_research_execution_roadmap.md:305`.
  - B4 OOS freeze: `docs/research/condition_research/plans/2026-07-02_plan_B_research_execution_roadmap.md:336`.
  - B5 portfolio: `docs/research/condition_research/plans/2026-07-02_plan_B_research_execution_roadmap.md:378`.

  **Acceptance Criteria**:
  - [ ] `source_read_receipt.md` has a `read_scope=full_document` entry for `2026-07-02_plan_B_research_execution_roadmap.md`; sections B3~B5 are marked as applied.
  - [ ] Every refinement round has Analysis Card, axis ledger append, candidate pack, strict validation receipt, official replay receipt, cross-comparison matrix.
  - [ ] Two consecutive no-improve rounds close the cell and move to next go cell.
  - [ ] Each OOS command has a prior `frozen_candidate_preregistration_<id>.md` with code sha, n_trials, windows, and run ids.
  - [ ] OOS usage is appended and counted.
  - [ ] If 2+ survivors exist, portfolio JSON and measurement-frame labels are produced.
  - [ ] `scripts/run_positive_control.py` and `scripts/check_research_evidence_lineage.py` receipts are healthy/consistent at stage end.

  **QA Scenarios**:
  ```text
  Scenario: one go cell refinement reaches freeze or no-improve closure
    Tool: powershell/python
    Steps: run B3 config for selected go cell, collect required 8 outputs, apply B3 decision rules.
    Expected: candidate is advanced/frozen or cell is closed with no-improve evidence.
    Evidence: docs/research/condition_research/research_runs/seed_lattice_20260702/round_matrix/

  Scenario: OOS command attempted without preregistration
    Tool: powershell
    Steps: before any OOS command, check preregistration file exists for candidate.
    Expected: missing file blocks execution and writes blocker.
    Evidence: .omo/evidence/ai-loop-full-next-execution-20260703/t9-oos-prereg-blocker.md
  ```

  **Commit**: OPTIONAL | Message: `격자 정제와 OOS 포트폴리오 결과 기록` | Files: research docs/ledgers/update_log

- [ ] T10. Plan D Survivor Seed Research Program

  **What to do**: Build append-only seed pool from Plan C survivors, Plan B go/OOS survivors, and verified `rr8_12_turnover_min_902_1.5` seed; run one active seed at a time until top 3 seeds freeze, then run integration evaluation and KPI/result docs.

  **Must NOT do**: Do not start Plan D before T5 and T9 have produced inputs or explicit blockers. Do not run multiple active seeds concurrently. Do not let discovery agent judge its own candidates.

  **Parallelization**: Can Parallel: YES by role, not by active seed | Wave 6 | Blocks: Final | Blocked By: T5,T9

  **References**:
  - Plan D purpose: `docs/research/condition_research/plans/2026-07-02_plan_D_seed_research_program.md:1`.
  - Seed pool: `docs/research/condition_research/plans/2026-07-02_plan_D_seed_research_program.md:39`.
  - Rounds: `docs/research/condition_research/plans/2026-07-02_plan_D_seed_research_program.md:56`.
  - Portfolio/KPI: `docs/research/condition_research/plans/2026-07-02_plan_D_seed_research_program.md:100`.
  - Role split: `docs/research/condition_research/plans/2026-07-02_plan_D_seed_research_program.md:137`.

  **Acceptance Criteria**:
  - [ ] `source_read_receipt.md` has a `read_scope=full_document` entry for `2026-07-02_plan_D_seed_research_program.md`; sections 0~8 are marked as applied.
  - [ ] `seed_pool.jsonl` exists and is append-only with Plan C, verified, and lattice sources.
  - [ ] Each seed has passport path and buy/sell sha recheck.
  - [ ] Active seed count is exactly 1 at any moment.
  - [ ] Each round records R-a/R-b/R-c/R-d outputs.
  - [ ] Frozen seeds only then get OOS; OOS survivors append to `oos_survivors.jsonl`.
  - [ ] Program cycle ends after top 3 priority seeds are frozen, integration evaluation runs at least once, and KPI table is in result doc.
  - [ ] Stop if positive control fails, seed pool is exhausted, or 3 seeds in a row show all-round no-improve.

  **QA Scenarios**:
  ```text
  Scenario: first program cycle completes
    Tool: powershell/python
    Steps: build seed_pool, run serial seed rounds, freeze top 3, run integration, write KPI result.
    Expected: result doc has frozen seed statuses, OOS survivor count, portfolio TPI/MDD gap tracking.
    Evidence: docs/research/condition_research/research_runs/<plan_d_run_id>_result.md

  Scenario: three consecutive seeds no-improve
    Tool: python
    Steps: inspect seed_pool and round ledgers for 3 consecutive all-round no-improve.
    Expected: stop program and write process rereview report, no further candidate generation.
    Evidence: .omo/evidence/ai-loop-full-next-execution-20260703/t10-three-seed-stop.md
  ```

  **Commit**: OPTIONAL | Message: `생존 시드 연구 프로그램 결과 기록` | Files: Plan D docs/ledgers/update_log

## Final Verification Wave
> ALL must APPROVE. Present consolidated results to user and get explicit okay before marking the whole program complete.

- [ ] F1. Plan Compliance Audit
  - Check every T0-T10 acceptance item has evidence or an explicit blocker.
  - Command: `rg -n "blocked|ERROR|fail|gate_healthy|final_status|oos_usage" .omo/evidence/ai-loop-full-next-execution-20260703 docs/research/condition_research docs/update_log`.

- [ ] F2. Code Quality Review
  - For Plan A code commits only, review diffs and gates.
  - Commands: `git show --stat --oneline <A1_commit> <A2_commit>`, `PYTHONUTF8=1 python -m pytest tests/unit/ -q`, `python scripts/verify_nonrelease_sync.py`.

- [ ] F3. Real QA / Research Evidence Review
  - Verify positive control, lineage, schema counts, DB backups, restore commands, and protected paths.
  - Commands: `python scripts/check_research_evidence_lineage.py --report .omo/evidence/ai-loop-full-next-execution-20260703/final_lineage_report.json`, `git diff --check`.

- [ ] F4. Scope Fidelity Check
  - Confirm no export/live/final promotion, no `backtest/graph`, no unintended dirty cleanup, no `git add -A`.
  - Commands: `git status --short -- backtest/graph _database_v3k_shadow _log backup`, `rg -n "can_promote=True|can_export=True|live=True|final_approval|export" ai_strategy_loop cli docs/research/condition_research docs/update_log`.

## Commit Strategy
- Plan A A1 and A2: required separate Korean commits after full gates.
- A3: no code commit unless explicit user approval appears. Without approval, documentation-only blocked status is allowed.
- Plan C/B/D research outputs: commit only curated docs, ledgers, receipts, and scripts that are intentionally source artifacts. Do not commit `.gjc/`, broad `.omo/`, runtime DB backups, dashboard 7-file residue, or protected paths unless a later explicit decision changes scope.
- Always stage paths explicitly, for example `git add docs/update_log/... tests/unit/test_provider_failover.py ai_strategy_loop/...`.
- Never use `git add -A`. If `index.lock` occurs, verify no git.exe process owns it, remove stale zero-byte lock only, then retry serially.

## Success Criteria
- Plan A A1/A2 stabilize provider flow and pass required gates without expanding promotion/export/live authority.
- CSS_V7 candidates are fully classified and exported for Plan D if survivors exist.
- Lattice 576 seeds are generated, registered, smoke-screened, coverage-ranked, and refined under OOS-blind discipline.
- Plan D program creates a durable seed pool and either produces OOS survivors/portfolio gap tracking or a clear no-improve stop report.
- The final user-facing summary can state what was run, what survived, what was rejected/blocked, total elapsed time, exact evidence paths, and next recommended action.
