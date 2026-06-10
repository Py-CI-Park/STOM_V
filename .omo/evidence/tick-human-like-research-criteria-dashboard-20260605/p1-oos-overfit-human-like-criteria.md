# P1 OOS / Overfit / Human-Like Criteria Layer

Status: `complete`

## Implemented

| Item | Result |
|---|---|
| OOS modes | `disabled`, `advisory`, `promotion_only` |
| Default research mode | `disabled` |
| Research criteria object | `research_continue`, `promotion_claim`, `reason_codes`, `recent_weighted_profit`, `equity_upward`, `win_day_ratio`, `payoff_compensation` |
| Candidate pool integration | `CandidatePoolItem.research_criteria`, `CandidateResearchPoolResult.research_oos_mode` |
| Artifact integration | `research_oos_mode` and per-item `research_criteria` serialized |
| Config/API | `LoopConfig.research_oos_mode`, `/research_criteria` |
| Dashboard | `ResearchCriteriaBanner` shown in Run Monitor |
| Live dashboard restart | old PID `108116` stopped, new PID `98272` started on `8770` |

## Policy

| Mode | Behavior |
|---|---|
| `disabled` | no OOS rejection; research-only discovery |
| `advisory` | OOS is reference only; no OOS-only research rejection |
| `promotion_only` | fixed OOS only after a frozen candidate is reviewed |

Strict promotion remains blocked in `disabled` and `advisory`.

## Verification

| Command | Result |
|---|---|
| `python -m pytest tests/unit/test_candidate_research_pool_v2.py tests/unit/test_dashboard_route_parity.py tests/unit/test_dashboard_strategy_prompt_frontend.py -q` | `19 passed` |
| `python -m pytest tests/unit/test_config.py tests/unit/test_launch_config.py tests/unit/test_state_contract.py -q` | `105 passed` |
| `python -m pytest tests/unit/test_dashboard_strategy_diff.py tests/unit/test_dashboard_strategy_prompt_frontend.py tests/unit/test_variable_correlation.py -q` | `19 passed` |
| `curl.exe -sS http://127.0.0.1:8770/health` | `{"status":"ok","contract_version":2}` |
| `curl.exe -sS "http://127.0.0.1:8770/research_criteria?mode=disabled"` | returns `label=OOS disabled`, `claim_status=research-only` |
| `curl.exe -sS -o NUL -w "%{http_code}" http://127.0.0.1:8770/ui/` | `200` |
| `python scripts/verify_nonrelease_sync.py` | pass |
| `git diff --check` | pass; line-ending warnings only |

## LOC / Architecture Note

| File | Pure LOC |
|---|---:|
| `ai_strategy_loop/fitness/research_criteria.py` | 175 |
| `ai_strategy_loop/controller/_candidate_research_pool_v2.py` | 219 |
| `ai_strategy_loop/dashboard/app.py` | 1530 |
| `ai_strategy_loop/dashboard/frontend/panels.jsx` | 892 |
| `ai_strategy_loop/dashboard/frontend/app.jsx` | 495 |

The new criteria module is within the 250 LOC ceiling. The dashboard files are inherited oversized modules. P1 kept edits minimal; later dashboard-heavy pages should split API/UI panels by responsibility before adding large new surfaces.

## Guardrails

- Official backtest engines unchanged.
- Hard gate scoring unchanged.
- `backtest/graph` unchanged.
- No production export.
- No `final_approval`.
- No live broker/KHOPENAPI/V3K action.
- No blanket `taskkill`.
