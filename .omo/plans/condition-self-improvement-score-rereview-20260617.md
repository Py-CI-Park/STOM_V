# 조건식 자기개선 프로세스 재점수화 및 문서 업데이트 계획 (2026-06-17)

## TL;DR
> **Summary**: 2026-06-15 보고서 이후 추가된 코드, 연구 기록, evidence, 테스트를 다시 검토해 자기개선 프로세스 완성도 점수와 개선책을 갱신한다.
> **Deliverables**:
> - `docs/update_log/2026-06-17_condition_self_improvement_score_update.md`
> - `.omo/evidence/condition-self-improvement-score-rereview-20260617/source_delta.md`
> - `.omo/evidence/condition-self-improvement-score-rereview-20260617/score_matrix.json`
> - `.omo/evidence/condition-self-improvement-score-rereview-20260617/improvement_plan.md`
> - `.omo/evidence/condition-self-improvement-score-rereview-20260617/verification.md`
> **Effort**: Medium
> **Parallel**: YES - 2 waves
> **Critical Path**: Task 1 -> Tasks 2-4 -> Task 5 -> Final Verification

## Context
### Original Request
- "지금까지 개발한 내용 연구 내용 모두 검토해서 다시 점수 체크및 개선책 마련 및 문서 업데이트 $start-work"

### Scope
- Include latest local code changes, docs under `docs/update_log`, evidence under `.omo/evidence/tmap-walkforward`, and existing score reports.
- Exclude source implementation, DB writes, strategy generation, live trading, V3K gate updates, and long backtests.

### Guardrails
- Scores are diagnostic only. Real success remains OOS/WF PROMISING count.
- Preserve dirty worktree and never revert unrelated user/previous work.
- Distinguish evidence from inference in docs.

## TODOs

- [x] 1. 최신 변경/연구/evidence 인벤토리 작성
  - Read latest docs, score reports, tmap evidence summaries, and relevant changed/untracked source filenames.
  - Write `source_delta.md` with what changed since the 2026-06-15 report.
  - Acceptance: at least 15 concrete source/evidence references, including 2026-06-17 docs and new P4/P5 files if present.

- [x] 2. 점수 매트릭스 재산정
  - Re-score the same axes from the 2026-06-15 report, adding new axes only if required by new evidence.
  - Write `score_matrix.json` with previous score, new score, delta, gap, evidence, and improvement.
  - Acceptance: JSON parses; score/gap math valid; overall previous/current/delta included.

- [x] 3. 개선책 및 우선순위 갱신
  - Write `improvement_plan.md` with revised P0-P5 priorities, what improved, what remains weak, and what to implement next.
  - Acceptance: includes seed coverage, typed feedback/action ledger, buy/sell feedback, mutation/grid, dashboard/runbook, and OOS proof sections.

- [x] 4. 문서 업데이트
  - Write `docs/update_log/2026-06-17_condition_self_improvement_score_update.md`.
  - Acceptance: Korean, table-heavy, includes current score, prior score, delta, top deficits, and next `$start-work` recommendation.

- [x] 5. 검증 및 상태 기록
  - Run JSON parse, score math check, focused tests for cited new/current modules where available, `git diff --check`, protected path status.
  - Write `verification.md`.
  - Acceptance: commands/results recorded; pre-existing dirty files separated from this work's files.

## Final Verification Wave

- [x] F1. Plan Compliance Audit
  - All deliverables exist and top-level plan boxes closed.

- [x] F2. Evidence Quality Review
  - Every score change is tied to source/evidence. No fake OOS success claim.

- [x] F3. Real QA
  - JSON parse, focused pytest, `git diff --check`, protected path status completed.

- [x] F4. Scope Fidelity Check
  - No source implementation, no protected DB writes, no long backtests, no strategy generation.
