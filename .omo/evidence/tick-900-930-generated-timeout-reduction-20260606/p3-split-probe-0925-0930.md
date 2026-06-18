# P3 Split Probe 09:25..09:30 - 2026-06-06

## Scope

Research-only tick split probe for `2025-01-03`, window `09:25..09:30`, OOS disabled. This run was intended to diagnose whether the expanded `09:00..09:30` generated strategy timeout can be reduced by testing the last five-minute slice independently.

## Command

```powershell
python -m ai_strategy_loop.scripts.tick_seed_timeout_probe run-loop --config-json .omo\evidence\tick-900-930-generated-timeout-reduction-20260606\p3-split-0925-0930-config.json --run-id tick_p3_split_0925_0930_20260606 --wall-cap 600 --out .omo\evidence\tick-900-930-generated-timeout-reduction-20260606\p3-split-0925-0930-result.json
```

## Result

| Field | Value |
|---|---|
| Result JSON | `.omo/evidence/tick-900-930-generated-timeout-reduction-20260606/p3-split-0925-0930-result.json` |
| stdout | `.omo/evidence/tick-900-930-generated-timeout-reduction-20260606/p3-split-0925-0930-result.stdout.txt` |
| stderr | `.omo/evidence/tick-900-930-generated-timeout-reduction-20260606/p3-split-0925-0930-result.stderr.txt` |
| wrapper status | `ok` |
| wrapper timeout | `false` |
| elapsed | `62.052s` |
| run ID | `tick_p3_split_0925_0930_20260606` |
| OOS mode | `disabled` |

## Classification

`provider_auth_limit_no_generated`

The split probe itself ended within the `600s` wall cap and did not reproduce the prior `180s` warm backtest timeout. However, it also did not produce a generated candidate:

- Gen0 seed backtest: `status=error`, `message=backtest completed without metrics`, `csv=no`.
- Gen1 generated buy creation: failed before strategy code existed because `gpt_auth` returned HTTP 429 usage limit.
- Stderr reports `usage_limit_reached`, `plan_type=pro`, and reset timestamp `1781138513` (`2026-06-11T09:41:53` local time).

## Safety / Cleanup

- No blanket process kill was used.
- The wrapper-owned process exited normally with return code `0`.
- Dashboard health after the split probes remained `200 {"status":"ok","contract_version":2}`.
- Protected-path status command reported no protected-path changes.

## Interpretation

This is not evidence that the `09:25..09:30` generated strategy is fast, slow, profitable, or unprofitable. The generated path is currently blocked by provider quota before a generated strategy can be evaluated. Do not use this result for human-level, seed-superior, OOS, or promotion claims.
