# P2 - Prompt And Guard Refinement

## Decision

`NO_CODE_CHANGE_SPLIT_PROBE_FIRST`

## Rationale

- P1 classified the timeout as `unknown_needs_probe`.
- Generated gen1 buy code is inside current regex caps: 31 non-comment lines and 15 if/elif conditions.
- Current cap is 40 non-comment lines and 16 if nodes, so blindly lowering the guard may remove valid narrow probes without proving the timeout cause.
- The bounded stdout still shows warm timeout at 180s and `csv=no`.
- Therefore the evidence-backed next action is P3 split probes for `09:20..09:25` and `09:25..09:30`, not source-code tightening yet.

## Verification

```powershell
python -m pytest tests/unit/test_time_cap_bucket_generation.py -q
```

Result:

```text
10 passed in 8.63s
```

## Scope

- No source code changed in P2.
- Existing default-OFF time-cap behavior remains intact.
- Existing prompt/guard tests remain green.

## Cleanup

No process was spawned or killed for P2. Only a unit test process ran and exited normally.
