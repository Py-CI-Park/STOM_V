# P3 Main Page Active Strategy Smoke

Status: `done`

## Main Page Visibility

The dashboard main page now includes an always-visible `ActiveStrategyPanel` in the `Run Monitor` section, directly after `CurrentGenPanel`.

Displayed fields:

- source: `winner`, `best`, `latest_generation`, `streaming_partial`, or `no_strategy`
- run ID
- generation number
- buy strategy name
- sell strategy name
- `code_status`
- `diff_status`
- bounded code preview
- button to open the existing full CodeViewer modal
- previous diff linkage through `/strategy_diff`

## Layout Guard

The code preview is height-bounded with `maxHeight: 170` and `overflow: auto`, so large strategy code cannot push the full page out of shape.

## Verification

```powershell
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_dashboard_strategy_prompt_frontend.py -q
```

Covered by the combined P1-P4 run: `18 passed in 9.29s`.

Manual HTTP smoke:

- Artifact: `p1-p4-curl-smoke.txt`
- Fresh owned server served `/ui/` with HTTP 200.

