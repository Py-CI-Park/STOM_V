## Summary
G002 is not resolved yet. The mapping and preregistration make the right product distinction between r8 official OOS and the exit2 portfolio rule, but the wrapper routes evidence paths to .omo/.omo/evidence/tmap-walkforward instead of the documented .omo/evidence/tmap-walkforward, so P4 is not safely executable as written.

## Analysis
- The preregistration establishes the required boundary: no backtest.py, no live or V3K or serial-key or protected runtime paths, no strategy.db, and distinct labels for official OOS, CSV reanalysis, and portfolio rules.
- The command mapping correctly separates the compound candidate into two evidence layers: r8_exclude_cap_lt_1500 as official OOS and exit2_skip_after_prior_exit2_loss_500k_else_full as portfolio-layer reporting. It also provides explicit P4 commands and avoids backtest.py, live or V3K, _database/strategy.db, and protected runtime DB writes in the documented command envelope.
- The pairs JSON contains only the r8 filtered official pair, POSTQ4_r8_exclude_cap_lt_1500_B and POSTQ4_r8_exclude_cap_lt_1500_S, which preserves the taxonomy instead of pretending the exit2 portfolio rule is a STOM buy or sell pair.
- The wrapper attempts to redirect strategy and run state by setting STOM_CLI_DB_STRATEGY and patching LoopState paths before running claude_candidate_batch_eval; that is the right architecture for a bounded adapter.
- The wrapper path root is wrong: from .omo/evidence/tmap-walkforward/run_post_q4_oos_wrapper_20260619.py, Path(__file__).resolve().parents[2] resolves to the repository .omo directory, and then EVID is built by appending another .omo/evidence/tmap-walkforward. This disagrees with every documented command and expected artifact path under .omo/evidence/tmap-walkforward.
- .gjc/ultragoal/goals.json still marks G002 active and G001 review_blocked. That state is appropriate while this blocker remains unresolved.

## Root Cause
The execution adapter treats .omo as the repository root and appends another .omo segment. The intended evidence-local sandbox exists under the wrapper file directory or under the repository root .omo/evidence path, but the code constructs a duplicate .omo/.omo tree.

## Findings
- HIGH — .omo/evidence/tmap-walkforward/run_post_q4_oos_wrapper_20260619.py:8-9: the wrapper calculates ROOT using Path(__file__).resolve().parents[2] and then builds EVID by appending .omo/evidence/tmap-walkforward. Impact: the official P4 commands will not use the documented strategy sandbox or run-state sandbox; they may fail to find the generated sqlite or write runtime artifacts outside the expected evidence location. Fix: derive EVID directly from Path(__file__).resolve().parent, or set repository root to parents[3], then optionally assert the strategy sqlite exists before invoking the official runner.

## Recommendations
1. Request changes before any P4 official OOS execution.
2. Fix the wrapper evidence path root so all redirected artifacts land in .omo/evidence/tmap-walkforward exactly as documented.
3. Re-review the corrected wrapper and command mapping, then mark G002 complete only after the adapter paths and explicit next commands align.
4. Keep the existing taxonomy: official OOS for the r8 filtered pair, portfolio-rule reporting for exit2 prior-month allocation, and no claim of official OOS results until commands are actually run.

## Architectural Status
BLOCK

## Code Review Recommendation
REQUEST CHANGES

## Trade-offs
- Deriving EVID from Path(__file__).resolve().parent is simplest and makes the evidence artifact self-contained even if the repository root moves.
- Deriving repository root via parents[3] preserves the current root plus .omo shape but is more brittle to directory movement.
- Adding a preflight existence assertion for the strategy sandbox would improve operator safety but does not replace fixing the root calculation.
