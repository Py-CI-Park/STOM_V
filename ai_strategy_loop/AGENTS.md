# AI STRATEGY LOOP KNOWLEDGE BASE

## OVERVIEW
`ai_strategy_loop/` owns autonomous STOM condition-expression generation, backtesting, scoring, runtime state, and the browser dashboard. It is research/control-plane code, not production broker runtime.

## STRUCTURE
```text
ai_strategy_loop/
??? __main__.py              # `python -m ai_strategy_loop` dashboard/service entry
??? bootstrap.py             # env isolation before imports
??? config.py                # loop settings, gates, objectives, feature flags
??? brain/                   # LLM prompt/generator/validation path
??? controller/              # loop orchestration, state DB, export contracts
??? dashboard/               # FastAPI backend + static frontend
??? fitness/                 # score and graded fitness
??? provider/                # model providers/auth wrappers
??? autopsy/, meta/          # failure analysis and meta-insight helpers
??? scripts/                 # run_loop/run_dashboard and helper scripts
??? state/                   # runtime DB/snapshots; treat as generated state
```

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Start service | `__main__.py`, `scripts/run_dashboard.py` | Starts FastAPI/uvicorn dashboard. |
| Loop execution | `controller/loop.py` | Backtest cycle, candidate generation, stop handling. |
| State schema | `controller/state.py` | `loop_runs.db`, generations, prompts, equity points. |
| Prompt design | `brain/prompt.py`, `brain/generator.py` | Seed-refine, crossover, filter gates, hypothesis feedback. |
| Scoring | `fitness/score.py` | MDD/profit/frequency/TPI and objective shaping. |
| Dashboard API | `dashboard/app.py` | REST/WebSocket, final approval, reference screenshots. |
| Frontend | `dashboard/frontend/*.jsx`, `styles.css` | No new frontend framework unless explicitly requested. |

## CONVENTIONS
- Keep generation tied to STOM syntax and official backtest evidence; do not treat LLM output as truth before validation.
- Research/profile runs should preserve prompt, hypothesis, equity, and rejection evidence when possible.
- `controller/export.py` and dashboard final approval are the export boundary; do not bypass human approval into production strategy DBs.
- Runtime files in `state/` are generated; avoid committing snapshots/DB changes unless the task explicitly requires a fixture.
- V3K features remain default-OFF unless the root approval gate allows a specific enablement.

## ANTI-PATTERNS
- Do not write operating `_database/` or live strategy wiring from this loop without the approved gate.
- Do not promote one-month or smoke-test winners as final strategies without longer validation.
- Do not introduce dependencies for the dashboard/frontend without explicit request.
- Do not use S_* or result/diagnostic leakage variables as generated buy-condition inputs.

## COMMANDS
```powershell
python -m ai_strategy_loop
pytest tests/unit/test_dashboard* -q
pytest tests/unit/test_graded_fitness.py tests/unit/test_hypothesis_loop.py -q
```
