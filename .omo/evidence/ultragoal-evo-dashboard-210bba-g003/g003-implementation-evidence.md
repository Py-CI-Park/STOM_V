# G003 Implementation Evidence

## Scope

Implemented advisory 100-point scoring helpers in `ai_strategy_loop/controller/advisory_scores.py` with tests in `tests/unit/test_advisory_scores.py`.

## Delivered contract

| Item | Result |
|---|---|
| `performance_score_100` | Bounded 0-100, reasoned components: profit, MDD, Calmar, uptrend R², trade frequency, exit quality, multi-period stability. |
| `condition_quality_score_100` | Bounded 0-100, reasoned components: syntax safety, variable diversity, market niche, composition creativity, overfire guard, execution cost, exit structure. |
| Authority guard | Scores cannot promote, export, select winner, or bypass hard gates/evidence/human approval. |
| Boundary | No live/export/operating DB/V3K/KHOPENAPI/Transformer work. |

## Verification

| Command | Result |
|---|---|
| `python -m pytest tests/unit/test_advisory_scores.py tests/unit/test_condition_discovery_policy.py tests/unit/test_launch_config.py -q` | `30 passed in 1.62s` |
| `python -m pytest tests/unit/dashboard/test_dashboard_telemetry.py tests/unit/test_advisory_scores.py tests/unit/test_condition_discovery_policy.py tests/unit/test_launch_config.py -q` | `35 passed in 13.75s` |
| `git diff --check` | clean |

## QA blocker fix

The first QA review found advisory-score robustness issues: invalid stability metrics could raise, and `give_back_rate=0.0` was treated as missing. The implementation now skips invalid numeric fields, falls back to `yearly_positive_ratio`, and treats zero give-back as valid perfect give-back evidence. Tests cover the regression.

Post-fix verification: `python -m pytest tests/unit/dashboard/test_dashboard_telemetry.py tests/unit/test_advisory_scores.py tests/unit/test_condition_discovery_policy.py tests/unit/test_launch_config.py -q` → `36 passed in 10.96s`; `git diff --check` clean.

## Non-finite robustness fix

The second review found that `nan`/`inf` values could propagate through advisory scores. `_num` and `_clamp` now reject non-finite values, invalid `give_back_rate` is treated as absent, and valid `give_back_rate=0.0` remains credited. Tests cover `nan` stability fallback and invalid give-back behavior.

Post-fix verification: `python -m pytest tests/unit/dashboard/test_dashboard_telemetry.py tests/unit/test_advisory_scores.py tests/unit/test_condition_discovery_policy.py tests/unit/test_launch_config.py -q` → `37 passed in 10.81s`; `git diff --check` clean.
