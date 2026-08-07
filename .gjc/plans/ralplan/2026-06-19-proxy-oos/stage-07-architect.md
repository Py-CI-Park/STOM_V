## Summary
G007 final changes are architecturally acceptable. The condition-discovery preset now has a single effective runtime policy applied before backtest and scoring, the seed_db pattern-card guard is enforced pre-save, page-data projection fails closed, and the frontend no longer mounts the legacy lab/research surface inside the Lab/Wiki page while preserving merged heatmap+edge and process defaults.

No blocking issues were found. Tests/builds/linters were not run in this review per assignment; evidence below is from inspected source and test files only, with the provided leader contract noting prior successful verification.

## Analysis
### Spec compliance
- Runtime policy: `effective_condition_discovery_runtime_config` clones config and applies staged MDD, min daily trades, OOS mode, and tick/MIN window overrides (`ai_strategy_loop/controller/condition_discovery.py:259-305`). Backtest subprocess args consume the effective `bt_universe_start_time`/`bt_universe_end_time` after `run_backtest_for` applies the effective config (`ai_strategy_loop/controller/loop.py:254`, `ai_strategy_loop/controller/loop.py:303-304`, `ai_strategy_loop/controller/loop.py:339-340`). Warm backtest config and top-level `run_loop` also re-apply the effective policy (`ai_strategy_loop/controller/loop.py:394`, `ai_strategy_loop/controller/loop.py:1080`). Scoring applies the same effective config before `compute_fitness` and `compute_graded_fitness` (`ai_strategy_loop/controller/loop.py:2364-2407`). Existing unit coverage asserts promotion MIN maps 35% configured MDD to 15%, `promotion_only` OOS, and full-session window without mutating the raw config (`tests/unit/test_condition_discovery_policy.py:63-78`).
- Pattern-card anti-copy: seed_db few-shot examples are converted to cards only when `few_shot_enabled` and `few_shot_source == "seed_db"` (`ai_strategy_loop/controller/loop.py:728-740`) and passed into `generate_strategy` (`ai_strategy_loop/controller/loop.py:787-788`). The generator validates pattern cards before `save_strategy_to_db` and retries on full-expression/threshold/performance blockers, failing closed if the guard itself errors (`ai_strategy_loop/brain/generator.py:422-448`). The feedback helper records stripped thresholds and expression/threshold hashes, then reports `full_expression_copy`, `threshold_copy`, or `performance_truth_import` blockers (`ai_strategy_loop/controller/condition_discovery_feedback.py:155-205`). Unit coverage confirms a copied first response is rejected and only the second strategy is saved (`tests/unit/test_generator_guardrail.py:151-188`).
- Page-data projection: `_publish_live` adds condition-discovery sections when absent and catches projection errors with explicit `condition_discovery` error authority, advisory score authority flags all false, and `condition_feedback.pattern_cards.status == "unavailable"` (`ai_strategy_loop/controller/loop.py:1001-1028`). Normal feedback page-data reports pattern cards as `ok` only when cards exist and `empty` otherwise, avoiding claims that unavailable guards are active (`ai_strategy_loop/controller/condition_discovery_feedback.py:222-234`). Unit coverage checks both default `empty` and fail-closed `unavailable` paths (`tests/unit/test_publish_live_page_data.py:63-101`).
- Frontend surface: `app.jsx` routes the Lab/Wiki subtab to `LabPage`, while the normal overview keeps `ResearchLabPanel` in one research section (`ai_strategy_loop/dashboard/frontend/app.jsx:392-424`). `LabPage` deliberately records the legacy lab panel as `available-not-mounted` and mounts Wiki/AI context panels instead of nesting the lab panel (`ai_strategy_loop/dashboard/frontend/dashboard-pages.jsx:163-195`). The merged heatmap+edge panel remains in `rl-panel.jsx` (`ai_strategy_loop/dashboard/frontend/rl-panel.jsx:178-180`). Process defaults remain through `PROCESS_DEFAULT_ROWS` and the defaults table (`ai_strategy_loop/dashboard/frontend/phase-detail.jsx:533-904`).

### Architecture
The policy implementation is correctly centralized as a config overlay instead of duplicating preset checks across backtest, warm session, loop orchestration, scoring, and page-data projection. The pattern-card anti-copy guard sits in the generator pre-save sequence, which is the right boundary because it blocks persistence before DB writes while keeping prompt examples advisory. Dashboard failures are fail-closed and observable rather than silently falling back to active-looking guards.

### Code quality/security/performance
The code favors explicit gates and preserves failure evidence. The only watch item is performance overhead from rebuilding seed_db pattern-card page-data on live publishes (`ai_strategy_loop/controller/loop.py:575-599`, `ai_strategy_loop/controller/loop.py:2062-2068`); this is acceptable for final G007 because it does not change correctness and is bounded by `few_shot_k <= 5`, but caching could be considered if status publishes become hot.

## Root Cause
Prior blockers came from governance existing mainly as dashboard/prompt declarations: policy values could diverge from runtime scoring/backtest config, pattern-card anti-copy could be perceived as advisory rather than pre-save enforcement, and dashboard projection errors could leave ambiguous active-looking state. The final fix moves those concerns to the authoritative runtime/generator/page-data boundaries.

## Findings
No blocking findings.

LOW / WATCH — `ai_strategy_loop/controller/loop.py:575-599`, `ai_strategy_loop/controller/loop.py:2062-2068`: seed_db pattern-card page-data may rebuild examples on repeated live publishes. Impact is bounded and not correctness-affecting; cache per run/config only if profiling shows publish overhead.

## Recommendations
1. Approve G007 final changes.
2. Keep the focused governance/generator/page-data tests as regression coverage; they map directly to the prior blockers.
3. Consider a later non-blocking cache for seed_db pattern-card page-data if live publish frequency or exemplar lookup cost becomes visible.

## Architectural Status
CLEAR

## Product Status
CLEAR

## Code Status
CLEAR

## Code Review Recommendation
APPROVE

## Trade-offs
- Central effective config overlay vs scattered preset checks: chosen overlay keeps one policy source and reduces drift; repeated calls are idempotent and acceptable.
- Fail-closed page-data vs best-effort dashboard fallback: chosen fail-closed behavior avoids falsely advertising guards or advisory authority.
- Pre-save anti-copy guard vs prompt-only instruction: chosen pre-save guard enforces the contract at the DB persistence boundary.
- Preserve overview quick links/process defaults vs removing all explanatory UI: current changes remove nested Lab/Wiki duplication while preserving intended overview/process affordances.
