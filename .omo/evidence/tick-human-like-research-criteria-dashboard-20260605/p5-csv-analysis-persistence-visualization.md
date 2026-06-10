# P5 CSV Analysis Persistence And Visualization Evidence

## Scope

Plan item: `P5 - CSV Analysis Persistence And Visualization`

Implemented a local research-only analysis snapshot endpoint and SQLite persistence layer:

- `ai_strategy_loop/dashboard/analysis_snapshot.py`
- `ai_strategy_loop/dashboard/research_api.py`
- `tests/unit/test_analysis_snapshot_persistence.py`

This does not write production strategy DBs, `_database/`, `backtest/graph`, export paths, or live broker paths.

## What Changed

- Added `GET /analysis_snapshot`.
- Existing read-only analysis routes remain unchanged:
  - `/variable_correlation`
  - `/edge_ratio`
  - `/feature_importance`
- `/analysis_snapshot?persist=true` writes only to local research state:
  - `ai_strategy_loop/state/research_analysis.db`
- The persisted schema has:
  - `analysis_snapshots`
  - `analysis_rows`
- Persisted row kinds include:
  - `b_variable_correlation`
  - `b_variable_range`
  - `compound_feature_interaction`
  - `time_bucket`
  - `market_cap_band`
  - `edge_global`
  - `time_bucket_edge`
  - `market_cap_edge`
  - `time_cap_edge`
  - `feature_importance`
  - `generation_metric`
  - `daily_profit_loss`
- Snapshot payload includes Korean metric explanations for:
  - `edge_ratio`
  - `payoff_ratio`
  - `daily_profit_loss`

## Live Evidence

Dashboard was already running on `http://127.0.0.1:8770`, but the process was serving old code and returned `404` for `/analysis_snapshot`.

Safe restart performed:

- Confirmed `/status` was `complete`.
- Identified exact process: `python -m ai_strategy_loop --port 8770`, PID `125024`.
- Stopped only PID `125024`; no blanket `taskkill`.
- Restarted dashboard on the same port, new PID `132616`.
- Output logs:
  - `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p5-dashboard-8770.out.log`
  - `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p5-dashboard-8770.err.log`

Health:

```text
curl.exe -sS http://127.0.0.1:8770/health
=> {"status":"ok","contract_version":2}
```

Persisted snapshot:

```text
curl.exe -sS -o .omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p5-analysis-snapshot-live.json \
  "http://127.0.0.1:8770/analysis_snapshot?run_id=tick_p2_timecap_900_920_preflight_guarded2_20260606&persist=true&method=spearman&fine_time=true"
=> HTTP_STATUS:200
```

Snapshot summary:

```json
{
  "ok": true,
  "persisted": true,
  "csv_count": 2,
  "analysis_id": 1,
  "source_count": 2,
  "pooled_trades": 6,
  "edge_ratio": 2.478806907378336,
  "daily_rows": 2,
  "row_counts": {
    "b_variable_correlation": 14,
    "b_variable_range": 14,
    "compound_feature_interaction": 20,
    "daily_profit_loss": 2,
    "edge_global": 1,
    "feature_importance": 11,
    "generation_metric": 2,
    "market_cap_band": 1,
    "market_cap_edge": 3,
    "time_bucket": 1,
    "time_bucket_edge": 2,
    "time_cap_edge": 4
  }
}
```

Correlation panel route:

```text
curl.exe -sS -o .omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p5-variable-correlation-live.json \
  "http://127.0.0.1:8770/variable_correlation?run_id=tick_p2_timecap_900_920_preflight_guarded2_20260606&method=spearman"
=> HTTP_STATUS:200
```

Correlation summary:

```text
sources=2
pooled_trades=6
feature_count=14
top feature ~= B_전일동시간비
top correlation ~= -0.942857
time segments=1
market cap segments=1
interaction candidates=20
```

Missing CSV adversarial route:

```text
curl.exe -sS "http://127.0.0.1:8770/analysis_snapshot?run_id=noSuchRun&persist=true"
=> {"ok":true,"status":"no_csv","runs":["noSuchRun"],"csv_count":0,"persisted":false,"store":null,"analysis":{}}
=> HTTP_STATUS:200
```

SQLite verification:

```text
exists True
snapshots 1
rows [
  ('b_variable_correlation', 14),
  ('b_variable_range', 14),
  ('compound_feature_interaction', 20),
  ('daily_profit_loss', 2),
  ('edge_global', 1),
  ('feature_importance', 11),
  ('generation_metric', 2),
  ('market_cap_band', 1),
  ('market_cap_edge', 3),
  ('time_bucket', 1),
  ('time_bucket_edge', 2),
  ('time_cap_edge', 4)
]
```

## Automated Verification

```text
$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_analysis_snapshot_persistence.py -q
=> 2 passed

$env:PYTHONUTF8='1'; python -m pytest tests/unit/test_analysis_snapshot_persistence.py tests/unit/test_variable_correlation.py tests/unit/test_dashboard_research_lab_frontend.py tests/unit/test_dashboard_chart_explanations.py -q
=> 19 passed

python scripts/verify_nonrelease_sync.py
=> pass

git diff --check
=> pass; line-ending warnings only

git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json _v3k_sidecar/v3k_gui_settings.json ai_strategy_loop/state/research_analysis.db
=> empty
```

## Adversarial QA

- malformed/missing input: `run_id=noSuchRun` returns `status=no_csv`, HTTP 200, no DB write.
- stale dashboard state: 8770 initially served old code; exact dashboard PID was restarted after confirming loop status was complete.
- dirty worktree: existing dirty files were preserved; edits were limited to P5 files and evidence.
- misleading success output: validated both HTTP status and SQLite row counts.
- hung/long commands: route/test calls completed inside short wall times; no broad process kill was used.
- prompt injection: not applicable; endpoint reads CSV/DB state only and does not call an LLM.
- cancel/resume: not applicable to a synchronous read/build/persist endpoint.
- flaky tests: focused deterministic `tmp_path` SQLite tests passed.
- repeated interruptions: evidence and plan state are persisted under `.omo/`.

## Acceptance Mapping

- Analysis DB writes are local research state only:
  - writes only `ai_strategy_loop/state/research_analysis.db`
  - protected-path git status stayed empty
- Missing CSV produces empty response, not crash:
  - `status=no_csv`, HTTP 200
- Dashboard explains metrics in Korean:
  - existing glossary/chart tests passed
  - snapshot payload includes Korean explanations for edge ratio, payoff ratio, and day-level P/L
- Dashboard analysis visualization:
  - existing Research Lab route tests passed
  - live `/variable_correlation` returned heatmap/range/segment/interaction data
