# Final Verification

## Work
- Work ID: `tick-research-direction-realignment-20260605`
- Final verdict: `NEEDS_MORE_EVIDENCE`
- Completed through: P0-P9, including explicit blockers for P7 and P8.

## Focused Tests
- `python -m pytest tests/unit/test_candidate_research_pool_v2.py tests/unit/test_promotion_diagnostics.py tests/unit/test_sparse_positive_prompt.py -q`
  - Result: `18 passed`
  - Evidence: `final-tests-selector-diagnostics.txt`
- `python -m pytest tests/unit/test_variable_correlation.py tests/unit/test_feature_importance.py tests/unit/test_backfinder_principle.py tests/unit/test_dispersion.py -q`
  - Result: `51 passed`
  - Evidence: `final-tests-quant-dispersion.txt`

## Guardrails
- `python scripts/verify_nonrelease_sync.py`
  - Result: passed
  - Evidence: `final-nonrelease-sync.txt`
- Protected path status:
  - Result: `clean`
  - Evidence: `final-protected-path-status.txt`
- Full `git diff --check`:
  - Result: failed because the pre-existing dirty worktree contains broad trailing-whitespace/BOM/line-ending issues in `.omo/boulder.json`, `.omo/start-work/ledger.jsonl`, and multiple already-dirty dashboard/config files.
  - Evidence: `final-git-diff-check.txt`, `final-git-diff-check-exit.txt`
- Owned-scope trailing whitespace:
  - Result: no matches from `rg -n "[ \t]+$"` over the new selector/diagnostic files, tests, this plan, and this work's evidence directory.
  - Evidence: `final-owned-trailing-whitespace-check.txt`, `final-owned-trailing-whitespace-exit.txt`

## Scope Fidelity
- Official backtest engines were not edited.
- `compute_fitness` hard pass/fail semantics were not relaxed.
- `backtest/graph/` was not edited.
- No `final_approval`, `export_winner`, production strategy DB write, live broker/KHOPENAPI action, V3K action, or blanket `taskkill` was used.
- Runtime DB writes occurred only through the P6 smoke loop run.

## Main Outcome
The research process is materially improved:

- PBO/CSCV, Deflated Sharpe, and slippage stress diagnostics now exist.
- Exploration/Research/Promotion layers are separated.
- Human-like or overfit-looking candidates can stay analyzable without becoming promotion claims.
- The first bounded smoke run produced one generated candidate and classified it correctly.

The performance goal is not proven yet:

- P6 gen0 timed out after the 300s warm backtest timeout.
- P6 gen1 was negative and not promotion-worthy.
- P7 2023-2025 training was blocked as an unbounded long run.
- P8 fixed OOS was blocked because no frozen promotion candidate exists.

## Next Command
```text
$ulw-plan TICK P7 다년 run을 재시도하기 전에 백테스트 진행률/엔진 설정/엔진 로그/timeout 관측성을 보강하고, 2023~2025 bounded training run을 완료해 exploration_pool_v2/research_pool_v2/promotion_gate_v2 후보풀을 생성하는 계획을 만들어줘. docs/AGENT_HANDOFF.md, docs/update_log/2026-06-05_direction_review_through_84acb6cb.md, .omo/evidence/tick-research-direction-realignment-20260605/p6-smoke-summary.md, p7-train-log.txt, p9-decision-card.md를 정본으로 삼고, 엔진/하드게이트/backtest_graph/protected path 무수정, final_approval/export_winner 금지 조건으로 계획해줘.
```
