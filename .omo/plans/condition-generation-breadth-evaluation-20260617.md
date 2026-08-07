# 조건식 생성 범위/AND-OR 다양성 평가 계획 (2026-06-17)

## TL;DR
> **Summary**: 백테스트 결과를 분석해 AI가 넓은 범위의 조건식, 여러 시간/시총/수급 구간, AND/OR 조합, 사람이 시도할 법한 사례를 얼마나 생성하고 연구하는지 재평가한다.
> **Deliverables**:
> - `.omo/evidence/condition-generation-breadth-evaluation-20260617/generation_inventory.md`
> - `.omo/evidence/condition-generation-breadth-evaluation-20260617/breadth_score_matrix.json`
> - `.omo/evidence/condition-generation-breadth-evaluation-20260617/backtest_pattern_assessment.md`
> - `.omo/evidence/condition-generation-breadth-evaluation-20260617/verification.md`
> - `docs/update_log/2026-06-17_condition_generation_breadth_evaluation.md`
> **Scope**: Review/report only. No source code changes, no strategy generation, no DB writes, no live trading.

## Context
- User asked to evaluate the process of analyzing backtest results and generating/researching conditions with AI.
- Focus areas: broad seed/generation range, multiple bands/ranges, AND/OR mixing, human-like research cases, and whether bad conditions can improve into good ones.
- Existing 2026-06-17 score update remains the baseline; this plan adds a deeper generation-breadth lens.

## TODOs

- [x] 1. 생성 소스와 연구 기록 인벤토리 작성
  - Read current generation prompts, template files, mutator/refine/autopsy scripts, and latest update logs.
  - Acceptance: inventory lists concrete source/evidence references and separates implemented capability from inference.

- [x] 2. 조건식 범위/논리 조합 정량 평가
  - Quantify template count, tick/min split, time-window language, cap-band language, AND/OR evidence, and human-like motif coverage.
  - Acceptance: score matrix includes numeric scores, gaps, and improvement methods.

- [x] 3. 백테스트 결과와 생성 패턴 연결 평가
  - Compare generated pattern families against available discovery, anchor mutation, positive-control, and OOS evidence.
  - Acceptance: report distinguishes train-gate success from OOS proof and identifies bottlenecks.

- [x] 4. 문서 업데이트
  - Write a Korean table-heavy report under `docs/update_log`.
  - Acceptance: includes overall score, category scores, evidence table, deficiency percentage, and next development tasks.

- [x] 5. 검증 및 상태 기록
  - Run JSON parse/math checks, focused file/evidence checks, `git diff --check`, and protected-path status check.
  - Acceptance: verification file records commands/results and plan checkboxes are completed only after evidence exists.

## Final Verification Wave

- [x] F1. Plan Compliance Audit
  - Confirm all deliverables exist and all top-level checkboxes are closed.

- [x] F2. Evidence Quality Review
  - Confirm no fake OOS success claim and every score is tied to local evidence.

- [x] F3. Scope Fidelity Check
  - Confirm no source implementation, no protected DB writes, no live/runtime side effects.
