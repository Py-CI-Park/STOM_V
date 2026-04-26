# Wide v1 post-MVP roadmap and risk backlog design

## Purpose

This design fixes the direction before continuing work on
`feature/wide-v1-post-mvp-risk-backlog`.

The project goal is not merely to run one profitable-looking backtest. The goal
is to build a reproducible condition-improvement system:

```text
base condition
-> backtest
-> result recording
-> data and quant analysis
-> improved condition generation
-> candidate backtests
-> ranking and selection
-> repeated improvement
-> final candidate
-> final WFO validation only after research selection
```

Wide v1 has reached the MVP freeze point. This branch should close Wide v1
cleanly, record remaining risks, and preserve the next development path toward
Wide v2 automatic condition optimization.

## Current state

Current branch:

```text
feature/wide-v1-post-mvp-risk-backlog
```

Baseline:

```text
STOM_Version_2U_C @ 9c4ad20d
Wide v1 MVP freeze 및 운영 재현 문서화
```

Wide v1 frozen artifacts:

```text
final_buy_strategy=WideV1Final_B_20260425
base_buy_strategy=WideV1IterationV2_20260423__cand005
sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
primary_candidate=WideV1IterationV5ObservableFull_20260425__cand017
primary_expression=66.999 <= 시가총액 < 2_580 and 등락율 > 4.83
```

Wide v1 freeze evidence:

```text
actual row-set representative candidates=10
WFO round_count=8
WFO success_rate=1.0
WFO mean_oos_metric=0.5762499999999999
WFO mean_trade_count=2131.75
WFO zero_trade_rounds=0
balanced preset=pass
conservative preset=pass
```

## Decisions already made

### WFO stays outside the fast research loop

WFO is a final validation step, not the default mechanism for every candidate
iteration.

```text
discovery research:
  fast condition research, candidate generation, candidate backtests, ranking

discovery promote / cli.wfo / auto_discovery:
  heavier final validation after a candidate has been selected
```

This keeps the improvement loop fast enough to iterate and prevents WFO runtime
from blocking early-stage candidate exploration.

### v6 is not the default next step after successful v5

The v5 branch logic was:

```text
v5 actual row-set validation succeeds
  -> promote/WFO

v5 actual row-set validation is insufficient
  -> v6 minimal candidate-generation expansion

v5 runtime fails
  -> runtime recovery
```

Wide v1 v5 succeeded and moved through promote/WFO to MVP freeze. Therefore v6
is not the correct name for the next normal development step. Further condition
improvement should start as a new Wide v2 research cycle.

### Wide v1 freeze is not a live-trading guarantee

The freeze means the research MVP candidate is reproducible and has passed the
defined Wide v1 validation gates. It does not prove live profitability.

## Scope for this branch

This branch should produce documentation only unless the implementation plan
later identifies a small correctness fix required by the documentation work.

In scope:

- Record the whole condition-improvement roadmap through final system behavior.
- Record what Wide v1 completed and what it did not complete.
- Record the post-MVP risk backlog and live-pilot checklist for the frozen v1
  candidate.
- Record the next development direction: Wide v2 automatic backtest iteration.
- Record the PR/branch sequence so future work does not mix operating validation
  with condition optimizer development.

Out of scope:

- Changing strategy logic.
- Running a new full backtest or WFO.
- Modifying `utility/strategy.db`.
- Implementing Wide v2 loop behavior.
- Refactoring `cli/research_loop.py` before a separate plan.
- Touching protected backtest result directories such as `backtest/graph/`.

## Documentation design

### Document 1: post-MVP roadmap

Create a roadmap document under `docs/research/condition_research/mvp/`.

Suggested path:

```text
docs/research/condition_research/mvp/2026-04-26_wide_v1_post_mvp_roadmap.md
```

Required content:

- Final system goal: automatic condition improvement by repeated backtest and
  quant analysis.
- Completed Wide v1 stages.
- Remaining work after Wide v1.
- WFO role: final validation only.
- Why post-MVP risk backlog comes before Wide v2.
- Why Wide v2, not v6, is the correct next research cycle.
- Branch and PR sequence from current state to final system.

### Document 2: risk backlog and live-pilot checklist

Create a focused checklist under `docs/research/condition_research/mvp/`.

Suggested path:

```text
docs/research/condition_research/mvp/2026-04-26_wide_v1_post_mvp_risk_backlog.md
```

Required content:

- What WFO pass means.
- What WFO pass does not mean.
- Live-trading risks:
  - slippage
  - quote/limit-order fill mismatch
  - broker/API runtime failure
  - network failure
  - order-size and cash guard
  - symbol concentration
  - daily stop condition
  - rollback and disable procedure
- Paper/live pilot checklist.
- Explicit stop condition: do not claim live profitability from WFO alone.

### Document 3: PR report

Create a Korean PR report under `docs/pr/`.

Suggested path:

```text
docs/pr/2026-04-26_wide_v1_post_mvp_risk_backlog_pr.md
```

Required content:

- Purpose.
- Whole development flow.
- Current branch scope.
- Changed files.
- Verification.
- Next command:

```text
$brainstorming Wide v2 백테스트 반복 기반 조건식 자동 개선 루프 설계
```

## Whole development flow

### Phase 0: Wide v1 MVP research foundation

Status: complete.

Goal:

```text
prove that the system can generate, run, compare, and validate candidate
conditions from backtest data
```

Completed:

- Backtest CSV analysis.
- Candidate expression generation.
- Candidate strategy generation.
- Candidate backtest execution.
- Multi-candidate ranking.
- Retention-aware candidate selection.
- Row-level candidate diff.
- Score baseline comparability.
- v3/v4/v5 row-set diversity checks.
- v5 actual row-set representative selection.
- Permanent final strategy recreation.
- WFO validation.
- MVP freeze.

Not completed in Wide v1:

- Fully automated multi-round condition optimization.
- Persistent leaderboard across many rounds.
- Automated stop condition after stagnation.
- Wide v2 optimizer-specific reporting.
- Live-trading risk closure.

### Phase 1: Wide v1 post-MVP closure

Status: current branch.

Goal:

```text
close Wide v1 without losing the final objective of automatic condition
improvement
```

Deliverables:

- Post-MVP roadmap.
- Risk backlog.
- Live-pilot checklist.
- PR report.

Exit criteria:

- The roadmap clearly states that Wide v2 is the next condition-improvement
  cycle.
- WFO is documented as final validation, not routine candidate generation.
- Live-trading risks are listed without claiming they are resolved.
- The next command is explicit.

### Phase 2: Wide v2 optimizer design

Status: next branch after this PR.

Recommended command:

```text
$brainstorming Wide v2 백테스트 반복 기반 조건식 자동 개선 루프 설계
```

Goal:

```text
design the automatic multi-round condition improvement system
```

Required design topics:

- How to promote `best_candidate` into the next round baseline.
- How to generate the next candidate pool from the latest best condition.
- How to preserve previous best candidates.
- How to avoid over-pruning and duplicate row-sets.
- How to persist a leaderboard.
- How to stop after no meaningful improvement.
- How to defer WFO until a final candidate is selected.

### Phase 3: Wide v2 implementation

Status: future implementation PRs.

Expected PR slices:

```text
PR A: round state and leaderboard schema
PR B: best_candidate -> next baseline promotion
PR C: multi-round runner
PR D: candidate generation strategies for tighten/loosen/add/remove/replace
PR E: stop condition and reporting
PR F: final candidate freeze candidate selection
```

Expected behavior:

```text
round 1:
  baseline -> candidates -> backtests -> ranking -> best

round 2:
  previous best -> candidates -> backtests -> ranking -> best

round N:
  repeat until improvement stops or max rounds is reached
```

### Phase 4: Final validation

Status: future.

Goal:

```text
run WFO only on the final selected optimizer candidate
```

WFO should not be used as the inner-loop optimizer because it is too slow for
routine candidate generation.

### Phase 5: Release or new research cycle

Status: future.

Branch decision:

```text
WFO pass:
  freeze candidate and record operational reproduction

WFO fail:
  analyze failure and decide whether to return to Wide v2 candidate generation
  or start a new research family
```

## Error handling and guardrails

- Keep `STOM_Version_2U_C` integration through PRs.
- Do not directly commit unrelated runtime artifacts.
- Do not overwrite WFO evidence from Wide v1 without a new branch and PR.
- Treat `backtest/graph/`, `backtest/temp/`, and `backtest/csv/` as runtime
  evidence locations unless a plan explicitly allows a curated artifact.
- Keep `discovery research` fast; do not reattach WFO to the inner research loop.
- Do not claim live-trading profitability from backtest or WFO evidence alone.

## Testing and verification plan

This branch is documentation-focused.

Minimum verification:

```text
git diff --check --ignore-cr-at-eol
```

If any code changes are introduced by a later implementation plan, run the
focused unit tests for the changed code and the standard non-release sync guard:

```text
python -m pytest tests/unit/ -q
python scripts/verify_nonrelease_sync.py
```

## Acceptance criteria

- A roadmap exists and explains the whole path from Wide v1 to final automatic
  condition improvement.
- A post-MVP risk backlog exists and does not imply that WFO equals live-profit
  proof.
- The PR report points to the correct next command for Wide v2 design.
- No runtime result data is staged.
- The final response to the user separates:
  - what Wide v1 completed
  - why post-MVP closure is still useful
  - how Wide v2 continues the real condition-improvement goal
