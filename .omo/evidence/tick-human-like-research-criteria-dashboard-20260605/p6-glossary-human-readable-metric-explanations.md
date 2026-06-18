# P6 - Glossary And Human-Readable Metric Explanations

## Scope

P6 adds user-visible explanations for advanced dashboard metrics and proof-state terms:

- OOS
- overfit
- MDD
- payoff
- edge ratio
- MFE/MAE
- slippage
- PBO
- DSR
- win-day ratio
- recent-weighted score

The glossary explicitly separates research continuation from production or human-level proof.

## Changes

- Added `ai_strategy_loop/dashboard/frontend/glossary.jsx`.
- Loaded `glossary.jsx` before `app.jsx` in `ai_strategy_loop/dashboard/frontend/index.html`.
- Rendered `<ResearchGlossaryPanel />` directly under `ResearchCriteriaBanner` in the run monitor.
- Added glossary layout CSS in `ai_strategy_loop/dashboard/frontend/styles.css`.
- Expanded `docs/research/condition_research/wiki/metrics_glossary.md`.
- Added static frontend contract test `tests/unit/test_dashboard_research_glossary_frontend.py`.
- Expanded wiki contract terms in `tests/unit/test_research_wiki_docs.py`.

## Red / Green Evidence

Initial red command:

```powershell
python -m pytest tests/unit/test_dashboard_research_glossary_frontend.py tests/unit/test_research_wiki_docs.py -q
```

Initial result:

- `glossary.jsx` missing.
- `index.html` did not load `glossary.jsx`.
- wiki lacked `MDD`, `MFE/MAE`, `slippage`, `win-day ratio`, and `recent-weighted score`.

Green commands:

```powershell
python -m pytest tests/unit/test_dashboard_research_glossary_frontend.py tests/unit/test_research_wiki_docs.py -q
python -m pytest tests/unit/test_dashboard_research_glossary_frontend.py tests/unit/test_research_wiki_docs.py tests/unit/test_dashboard_chart_explanations.py tests/unit/test_dashboard_research_lab_frontend.py -q
```

Green results:

- `5 passed in 5.65s`
- `14 passed in 7.41s`

## Manual QA

Dashboard URL:

```text
http://127.0.0.1:8770/ui/
```

HTTP artifacts:

- `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p6-ui-index.http.txt`
- `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p6-glossary-js.http.txt`
- `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p6-glossary-malformed-query.http.txt`
- `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p6-glossary-missing-static.http.txt`

Browser artifact:

- `.omo/evidence/tick-human-like-research-criteria-dashboard-20260605/p6-research-glossary-panel.png`

Playwright DOM text confirmed the rendered panel includes:

- `METRIC GLOSSARY`
- `research signal, not production proof`
- `human-level claim blocked`
- OOS, overfit, MDD, payoff, edge ratio, and MFE/MAE cards in collapsed state.

## Safety Verification

```powershell
python scripts\verify_nonrelease_sync.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json _v3k_sidecar/v3k_gui_settings.json ai_strategy_loop/state/research_analysis.db
```

Results:

- `verify_nonrelease_sync.py`: pass.
- `git diff --check`: pass, line-ending warnings only.
- Protected path status: empty.

Code size check:

- `ai_strategy_loop/dashboard/frontend/glossary.jsx`: 76 pure LOC.
- `tests/unit/test_dashboard_research_glossary_frontend.py`: 36 pure LOC.
- `tests/unit/test_research_wiki_docs.py`: 72 pure LOC.

## Adversarial QA

- malformed input: `/ui/glossary.jsx?bad=%25FF` returns the same glossary file; missing static `/ui/not-a-real-glossary.jsx` returns bounded 404.
- prompt injection: glossary is static/read-only and does not call LLM, strategy export, final approval, live broker, or V3K actions.
- cancel/resume: no runtime research process spawned; plan/evidence/ledger capture the completion boundary.
- stale state: live `8770` served updated `/ui/` and `/ui/glossary.jsx` without requiring another process restart.
- dirty worktree: broad existing dirty tree preserved; no unrelated files reverted.
- hung or long commands: curl, pytest, and Playwright all ran with bounded timeouts.
- flaky tests: static contract tests and wiki tests reran green after red/green implementation.
- misleading success: completion required HTTP, DOM, screenshot, tests, and wiki updates, not health alone.
- repeated interruptions: plan checkbox and ledger entry make the next resume start at P7.

## Status

P6 complete. This improves user understanding and dashboard observability. It does not claim human-level or production readiness.
