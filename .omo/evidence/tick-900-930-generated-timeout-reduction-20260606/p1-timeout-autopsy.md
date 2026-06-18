# P1 - Timeout Autopsy And Diagnostic Gap

Run: `tick_p7_timecap_900_930_bounded_20260606` gen `1`

## Classification

`unknown_needs_probe`

## Code Shape

| Side | Non-comment lines | Regex if/elif | Regex assignments | AST status |
|---|---:|---:|---:|---|
| buy | 31 | 15 | 15 | `not_used_stom_syntax_regex_count_only` |
| sell | 27 | 14 | 12 | `not_used_stom_syntax_regex_count_only` |

## Notes

- buy code is inside current line/if caps by regex, so current buy-only caps do not explain the timeout alone
- stdout confirms warm backtest timeout at the bounded 180s cap and csv=no
- no single code-shape metric explains the timeout; split probes are required

## Evidence Files

- JSON: `.omo\evidence\tick-900-930-generated-timeout-reduction-20260606\p1-timeout-autopsy.json`
- Source code payload: `.omo\evidence\tick-human-like-research-criteria-dashboard-20260605\p7-strategy-code-gen1.json`
- Timeout stdout: `.omo\evidence\tick-human-like-research-criteria-dashboard-20260605\p7-timecap-900-930-result.stdout.txt`

## Cleanup

No process was spawned or killed for P1. This was read-only artifact analysis.
