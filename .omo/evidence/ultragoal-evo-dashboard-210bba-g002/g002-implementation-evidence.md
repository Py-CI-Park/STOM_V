# G002 Implementation Evidence

## Scope

Implemented backend condition-discovery contract and policy helpers in `C:/System_Trading/STOM/STOM_V.wt-evo-governance` on branch `feature/evo-dashboard-condition-discovery-governance` from baseline `210bba854d03a8680ffebfb94f2544c52e81858b`.

## Changed files

| File | Purpose |
|---|---|
| `ai_strategy_loop/config.py` | Adds additive `condition_discovery_preset` config field. |
| `ai_strategy_loop/controller/condition_discovery.py` | New JSON-safe preset/time-window/MDD/evidence/policy helper module. |
| `ai_strategy_loop/controller/state.py` | Adds preset to active config snapshot. |
| `ai_strategy_loop/launch_config.py` | Validates preset and exposes it in field specs. |
| `tests/unit/test_condition_discovery_policy.py` | Covers preset validation, time windows, MDD, evidence blockers, page-data merge. |
| `tests/unit/test_launch_config.py` | Locks field-spec coverage. |

## Contract behavior

| Contract | Result |
|---|---|
| `fast/research/promotion` presets | Implemented and validated. |
| Tick research/promotion | `09:00-09:28`. |
| Min research/promotion | Full-session required with `15:18/15:19` candidate boundary metadata. |
| Staged MDD hard-gate policy | `effective_mdd_cap = min(configured_mdd_cap, preset_cap)` with caps fast `35`, research `25`, promotion `15`. |
| Evidence health | CSV/trades/equity/prompt/validation normalize to status rows and blockers. |
| Authority boundary | Scores remain advisory only; G002 does not add score/promotion/export authority. |
| 210bba seams | `/status`, `LoopState.page_data`, telemetry, and dashboard routes are preserved; no route rewrite. |

## Verification

| Command | Result |
|---|---|
| `python -m pytest tests/unit/test_condition_discovery_policy.py tests/unit/test_launch_config.py -q` | `26 passed in 1.05s` |
| `python -m pytest tests/unit/dashboard/test_dashboard_telemetry.py tests/unit/test_condition_discovery_policy.py tests/unit/test_launch_config.py -q` | `31 passed in 13.65s` |
| `git diff --check` | clean |

## Boundary checks

No live/export/operating DB/V3K/KHOPENAPI/Transformer work was added. Runtime/protected paths were not used as source inputs.

## QA blocker fix

The first QA review found that required evidence could self-report `not_required` and avoid blockers. `build_evidence_health` now coerces `not_required` to `missing` whenever the component is required, and `test_condition_discovery_policy.py` covers this adversarial promotion bypass.

Post-fix verification: `python -m pytest tests/unit/dashboard/test_dashboard_telemetry.py tests/unit/test_condition_discovery_policy.py tests/unit/test_launch_config.py -q` → `31 passed in 10.83s`; `git diff --check` clean.
