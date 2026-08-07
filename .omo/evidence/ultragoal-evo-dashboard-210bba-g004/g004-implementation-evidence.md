# G004 Implementation Evidence

## Scope

Implemented read-only condition-discovery feedback helpers in `ai_strategy_loop/controller/condition_discovery_feedback.py` with tests in `tests/unit/test_condition_discovery_feedback.py`.

## Delivered contract

| Item | Result |
|---|---|
| Prompt/equity persistence state | Preset-aware required/optional status rows with blockers. |
| Autopsy hypotheses | Advisory hypotheses normalized with id/status/source/provenance. |
| Human DB pattern cards | Creativity-only composition cards with threshold stripping and hashes. |
| Anti-copy | Full expression copy, threshold copy, and performance truth import detection. |
| Authority | No promotion/export/winner/live authority; no operating DB access. |

## Verification

| Command | Result |
|---|---|
| `python -m pytest tests/unit/test_condition_discovery_feedback.py tests/unit/test_advisory_scores.py tests/unit/test_condition_discovery_policy.py tests/unit/test_launch_config.py -q` | `38 passed in 1.54s` |
| `python -m pytest tests/unit/dashboard/test_dashboard_telemetry.py tests/unit/test_condition_discovery_feedback.py tests/unit/test_advisory_scores.py tests/unit/test_condition_discovery_policy.py tests/unit/test_launch_config.py -q` | `43 passed in 11.52s` |
| `git diff --check` | clean |

## Anti-copy robustness fix

The first G004 reviews found threshold leaks and weak copy detection. The implementation now strips no-space numeric thresholds, publishes sanitized `pattern_summary`, normalizes expression hashes across operator/whitespace formatting, and stores canonical per-threshold hashes so partial/reordered/equivalent threshold copies are blocked. Tests cover these adversarial cases.

Post-fix verification: `python -m pytest tests/unit/dashboard/test_dashboard_telemetry.py tests/unit/test_condition_discovery_feedback.py tests/unit/test_advisory_scores.py tests/unit/test_condition_discovery_policy.py tests/unit/test_launch_config.py -q` → `44 passed in 12.14s`; `git diff --check` clean.

## Numeric literal robustness fix

The final QA review found exponent/leading-dot numeric literal bypasses. The threshold regex now handles integers, decimals, leading-dot decimals, and exponent notation; tests cover exponent-equivalent threshold copy and leading-dot threshold stripping.

Post-fix verification: `python -m pytest tests/unit/dashboard/test_dashboard_telemetry.py tests/unit/test_condition_discovery_feedback.py tests/unit/test_advisory_scores.py tests/unit/test_condition_discovery_policy.py tests/unit/test_launch_config.py -q` → `44 passed in 12.76s`; `git diff --check` clean.
