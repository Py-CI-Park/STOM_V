# P9 Decision Card

## Executive Verdict
`NEEDS_MORE_EVIDENCE`

The direction is improved: overfit-looking or near-miss candidates are no longer killed at the exploration stage, while strict proof remains required for promotion.

The performance claim is not achieved yet: no frozen 2023-2025 promotion candidate exists, and fixed 2022/2026 OOS was not run.

## Direction Review Incorporated
- Strict selectors are no longer the Exploration Pool filter.
- PBO/CSCV, Deflated Sharpe, and slippage stress are implemented as read-only diagnostics.
- PBO/DSR/slippage are labels in Exploration/Research Pool and blockers in Promotion Gate.
- Human-reference morphology is a research prior, not proof.

## Exploration Pool Summary
- P6 smoke produced one classifiable AI candidate.
- It was retained for research despite failing promotion.
- This confirms the new pool structure can preserve analyzable failures rather than deleting them too early.

## Research Pool Summary
- P6 Research Pool count: `1`.
- Candidate gen1 is a negative research sample: profit `-4,343,533`, MDD `22.96`, trades `269`.
- P7 did not produce a 2023-2025 Research Pool because the bounded long run was not started after P6 timeout evidence.

## Promotion Gate Summary
- Promotion candidate: none.
- Promotion blockers include no frozen 2023-2025 candidate, no fixed 2022/2026 OOS, and no pass through PBO/DSR/slippage on a frozen candidate.

## Near-Miss And Overfit-Looking Candidates
- No fresh positive near-miss candidate was produced in P6.
- gen1 is retained but is not near-miss quality because aggregate profit is negative and MDD is too high.

## Human Morphology Evidence
- Human-like graph similarity is now documented as a Research Pool ranking signal.
- It cannot override fixed OOS, trade sufficiency, slippage stress, PBO, or DSR.

## PBO / DSR / Slippage Status
- Implemented and tested:
  - `tests/unit/test_promotion_diagnostics.py`: `6 passed`
  - Selector/artifact preservation: `tests/unit/test_candidate_research_pool_v2.py`
- No promotion candidate exists to evaluate with these diagnostics yet.

## Max-Hold Audit
- `max_hold_count` is classified as `display_only`.
- It can annotate Research Pool candidates but must not block Promotion Gate by itself.

## OOS Evidence Or OOS Blocker
- Fixed OOS was blocked.
- Reason: no frozen `promotion_candidate` from P7.
- This prevents OOS-after-the-fact reselection.

## Seed Comparison
No seed-vs-AI fixed OOS comparison was run in this plan.

## Replacement Vs Complement Recommendation
Do not claim AI-alone replacement yet.

Near-term direction should be seed+AI complement and bounded research-pool generation:

- Keep the human seed/reference as the comparator and few-shot prior.
- Use AI/computing power to explore broader candidate spaces.
- Freeze candidates before OOS.
- Only then compare against seed/human reference.

## N2 Regime-Expert Feasibility
Promising, but premature for implementation in this plan. It should follow after one bounded 2023-2025 pool run exists.

## N3 Walk-Forward Feasibility
Also promising. Recent-year weighting and changing market regimes support it, but it needs a separate plan after P7 can finish with progress/logging evidence.

## Forbidden Actions Check
- `final_approval`: not used.
- `export_winner`: not used.
- Production strategy DB write: not used.
- Live broker/KHOPENAPI/V3K action: not used.
- Blanket `taskkill`: not used.
- Official backtest engines and hard-gate semantics: not edited.

## Final Verdict
`NEEDS_MORE_EVIDENCE`

The research process is better aligned with the user's goal, but the system has not yet demonstrated human-level or seed-superior condition development.

## Next Recommended Command
```text
$ulw-plan TICK P7 다년 run을 재시도하기 전에 백테스트 진행률/엔진 설정/엔진 로그/timeout 관측성을 보강하고, 2023~2025 bounded training run을 완료해 exploration_pool_v2/research_pool_v2/promotion_gate_v2 후보풀을 생성하는 계획을 만들어줘. docs/AGENT_HANDOFF.md, docs/update_log/2026-06-05_direction_review_through_84acb6cb.md, .omo/evidence/tick-research-direction-realignment-20260605/p6-smoke-summary.md, p7-train-log.txt, p9-decision-card.md를 정본으로 삼고, 엔진/하드게이트/backtest_graph/protected path 무수정, final_approval/export_winner 금지 조건으로 계획해줘.
```
