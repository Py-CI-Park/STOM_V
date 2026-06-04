# CLI KNOWLEDGE BASE

## OVERVIEW
`cli/` owns command parsing, backtest runner orchestration, research loops, condition generation, and ML factor-analysis helpers. It bridges the old STOM runtime and the newer research workflow.

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Backtest args | `config.py` | CLI config and parser shape. |
| Subcommands | `subcommands.py` | `formula`, `strategy`, `discovery`, preflight, etc. |
| Runner | `runner.py` | Multiprocessing queues and diagnostics. |
| Research loop | `research_loop.py` | Baseline analysis -> candidates -> iterations. |
| Condition generation | `condition_generator.py` | B_* candidate expressions; leakage guard. |
| ML factors | `ml_factor_model.py` | RF/GB feature importance and CV. |
| V3 decisions | `research_v3_decision.py`, `v3_tiebreak.py` | tie-break, row-set signatures, family control. |
| Optimizer | `research_optimizer.py` | Multi-round leaderboard/no-improvement flow. |

## CONVENTIONS
- `runner.py` must preserve `dict_set`, queue handoff, and child-process contracts expected by tests.
- Condition generation should use safe B_* features; S_* and R_* are diagnostics/results and must not leak into generated buy conditions.
- Keep CLI output contract-friendly; pre-commit checks scan `cli/` for stray debug `print()` statements.
- Prefer adding small helpers over changing broad runner behavior.

## ANTI-PATTERNS
- Do not add live broker side effects to CLI research commands.
- Do not make random splits for time-series trading research; use time-ordered validation concepts.
- Do not bypass control-score or row-set retention logic when promoting research candidates.

## COMMANDS
```powershell
pytest tests/unit/test_runner_helpers.py -q
pytest tests/unit/test_research_loop.py tests/unit/test_research_optimizer.py -q
python scripts/pre_commit_check.py
```

## LOCAL GOTCHAS
- `stom_backtest.py` may dispatch here, so CLI behavior can affect desktop-adjacent workflows.
- Research candidates are evidence inputs, not automatic production strategies.
- Keep parser defaults aligned with tests and existing batch/script callers.
