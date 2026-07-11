# 2026-07-11 AI 조건식 루프 정본 재구축 핸드오프 (cold-start)

> 최신 정본 핸드오프. 새 에이전트는 이 문서만으로 cold-start 할 수 있다. 이전 핸드오프(`docs/AGENT_HANDOFF.md`, `docs/update_log/2026-07-09_condition_research_cross_agent_handoff.md`)보다 이 문서가 우선한다.

## 1. 목표 (objective)
고정 데이터 분할·공식 STOM 엔진·비용·예산 안에서 이전 조건식 실패를 분석하고, 그 근거로 구조적으로 다른 다음 조건식을 생성해, 보지 않은 기간에서도 이전 세대·동일 조건 기준선보다 안정 개선됨을 재현 가능하게 증명한다.

## 2. 권한 위계 (authority hierarchy)
1. 마스터 계획 `docs/research/condition_research/plans/2026-07-11_ai_condition_loop_canonical_rebuild_master_plan.md`
2. 정본 설계 spec `docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/lattice_v3_design_spec_20260709.md`
3. 목표/상태 권한 `docs/update_log/2026-07-11_ai_condition_loop_goal_process_reset_audit.md`
4. 하위 실행계약 `docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md`

## 3. 현재 상태 (branch / commit)
- branch: `loop/process-research-pipeline`, upstream `origin/loop/process-research-pipeline`.
- 시작 HEAD(CL-D 착수 시점): `dc5ebc9b4f1f8694a3c6870a8d80dfa7e76314e7`.
- CL-D4에서 CL-D 설계 문서를 한국어로 커밋한다. 커밋 후 최신 HEAD가 이 핸드오프가 가리키는 정본 상태다.

## 4. 완료 / 잠금 단계
- 완료(이번 실행): CL-D0, CL-D1, CL-D2, CL-D3, CL-D4. 상태 = `awaiting_CL_R01_R06_approval`.
- 잠금: CL-R01..CL-R10. 각 단계는 정확한 승인 문구가 기록되기 전에는 열리지 않는다(fail-closed).

## 5. 정확한 다음 명령 (exact next command)
- 설계 재개/검토: `docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/lattice_v3_next_command_20260709.md` 참조(design-only).
- CL-R 진행은 아래 정확 승인 문구가 필요하다:
  - `I approve CL-R01-R06 code integration only`
  - `I approve CL-R07 bounded mini-loop only`
  - `I approve CL-R08 bounded min performance only`
  - `I approve CL-R09 sealed OOS/WF only`
  - `I approve CL-R10 benchmark promotion review only`

## 6. 참조 경로 (all must resolve)
```
.omo/plans/ai-condition-loop-canonical-rebuild-20260711.md
.omo/drafts/ai-condition-loop-canonical-rebuild-20260711.md
docs/research/condition_research/plans/2026-07-11_ai_condition_loop_canonical_rebuild_master_plan.md
docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md
docs/update_log/2026-07-11_ai_condition_loop_goal_process_reset_audit.md
docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/source_read_receipt_v3_design_20260709.json
docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/lattice_v3_failure_lesson_matrix_20260709.md
docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/lattice_v3_design_spec_20260709.md
docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/lattice_v3_evaluation_protocol_20260709.md
docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/lattice_v3_next_command_20260709.md
docs/update_log/2026-07-09_lattice_v3_design_only_handoff.md
docs/AGENT_HANDOFF.md
docs/update_log/2026-07-09_condition_research_cross_agent_handoff.md
ai_strategy_loop/controller/loop.py
ai_strategy_loop/controller/state.py
ai_strategy_loop/controller/contract.py
cli/condition_generator.py
```

## 7. CL-R 미래 코드/테스트 맵 (요약; 실행은 승인 후)
- 소유권: `ai_strategy_loop/controller/loop.py::run_loop` 유일 최종 계보 소유자.
- 증거 계약/저장: `ai_strategy_loop/controller/`에 typed 증거 계약 + append-only EvidenceStore(loop_runs.db, schema v11).
- 근거/지문: `cli/condition_generator.py`, `cli/analyzer.py`, `cli/research_loop.py`에 B-only provenance + AST/rowset fingerprint.
- 대시보드: `ai_strategy_loop/dashboard/app.py` cohort 안전 비교.
- 테스트: `tests/unit/` 계약 TDD(CL-R01..R06), 격리 공식 실행(CL-R07..R10).

## 8. dirty-worktree 경고
- 시작 시점 worktree에 무관한 dirty 경로가 다수(porcelain sha256 `4b0929fe16c48b6ae443d593d2da05b938eed628e213e3ef9432a4059239bc26`, 300줄) 존재한다. `git add -A` 절대 금지. 명시 allowlist만 스테이징.

## 9. stop / recovery
- CL-D4 커밋 직후 HARD STOP. CL-R 진행 금지.
- ultragoal 상태 손상 시 현재 세션 스코프로 `gjc state clear --force --mode ultragoal --session-id <id>` 후 재시드.
- 증거 검증 재현: 각 `.omo/evidence/task-<N>-ai-condition-loop-canonical-rebuild-20260711/` 의 verifier 재실행(exit 0 기대).

## 10. 기대 효과
방향·근거·검증·중단 기준이 연결된 연구 시스템 확보. 수익 전략 탄생은 보장하지 않으며, 성능/인간비교/live 승인은 분리 보고·별도 승인 대상이다.
