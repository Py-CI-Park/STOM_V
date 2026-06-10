# P4 Dashboard Live Code / Diff / Prompt / History Panel

## Verdict

Status: page-complete.

The dashboard already exposes the active buy/sell names, current strategy code,
previous diff, prompt timeline, and AI context pack near the fitness area. Live
route checks and Playwright browser smoke passed.

## Live Route Checks

Target:

```text
run_id=tick_p2_timecap_900_920_preflight_guarded2_20260606
gen_no=1
```

| Route | Result | Evidence |
|---|---|---|
| `/strategy_code?run=...&gen=1` | `200 OK` | returns buy/sell names, `code_status=ok`, and full code |
| `/strategy_diff?run_id=...&gen_no=1` | `200 OK` | returns `base_gen=0`, buy/sell diffs, and prompts |
| `/prompts?run_id=...&gen_no=1` | `200 OK` | returns 4 prompt rows: 3 buy attempts and 1 sell attempt |
| `/ai_context_pack?run_id=...&gen_no=1` | `200 OK` | returns config window, strategy names, best/winner metrics, prompt count, and forbidden-action warnings |
| `/health` | `200 OK` | `{"status":"ok","contract_version":2}` |

## Browser Smoke

Playwright command opened the real UI:

```powershell
$env:PYTHONUTF8='1'; <Playwright script> goto http://127.0.0.1:8770/ui/
```

Artifact:

```text
.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p4-ui-smoke.png
```

DOM evidence:

- Page title text includes `STOM AI · 조건식 자율 진화 대시보드`.
- Run monitor shows selected run
  `tick_p2_timecap_900_920_preflight_guarded2_20260606`.
- Active strategy panel text includes:
  - `BUY_NAME`
  - `SELL_NAME`
  - `code_status=ok`
  - `diff_status=ok`
  - `Previous Diff via /strategy_diff`
- Fitness panel appears after active strategy:
  - `적합도 추이 — FITNESS TRAJECTORY`
  - latest score `6.903`

## Existing UI Coverage

The frontend already has:

- `ActiveStrategyPanel` in `panels.jsx`, placed before `FitnessChart` in
  `app.jsx`.
- `StrategyInspectorTabs` in `strategy-inspector.jsx` with:
  - `Previous Diff`
  - `Prompt Timeline`
  - `AI Context`
  - `Current Code`
- Empty/stale route states:
  - `strategy_diff route unavailable`
  - `prompts route unavailable`
  - `no strategy code loaded`
  - prompt no-record reason text

## Verification

```powershell
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_dashboard_strategy_diff.py tests/unit/test_dashboard_profit_codeview.py tests/unit/test_dashboard_strategy_prompt_frontend.py -q
# 33 passed

$env:PYTHONUTF8='1'; python scripts/verify_nonrelease_sync.py
# pass

git diff --check
# pass; line-ending warnings only
```

## UltraQA Notes

- malformed input: dashboard tests cover missing run/gen and missing route data
  returning non-breaking payloads.
- prompt injection: routes are read-only and include forbidden-action warnings
  in AI context pack.
- cancel/resume: no runtime process spawned; only route reads and a Playwright
  browser session.
- stale state: explicit `run_id` and `gen_no` were used for all route checks.
- dirty worktree: no source edits were needed for P4.
- hung or long commands: Playwright used a 20s navigation timeout; curl/test
  commands were bounded.
- flaky tests: focused dashboard strategy suites passed.
- misleading success: UI screenshot, DOM text, and route responses were all
  checked; `/health` alone was not used as proof.
- repeated interruptions: screenshot, evidence, plan, and ledger now record the
  P4 boundary.

## Next

Proceed to P5: persist CSV-derived analysis and visualize variable/time/cap
effects for future feedback.
