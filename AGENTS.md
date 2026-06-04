# PROJECT KNOWLEDGE BASE

**Generated:** 2026-06-03
**Commit:** a4b8de59
**Branch:** STOM_Version_2U_C-ai-strategy-loop
**Mode:** init-deep update; deeper AGENTS.md files override this file inside their directories.

## OVERVIEW
STOM is a Python/PyQt trading workstation with live broker runtimes, official backtest engines, CLI research tools, and an AI condition-expression evolution dashboard. This checkout is the active `STOM_Version_2U_C` lane; preserve Kiwoom runtime and the 2U_C nonrelease contract.

## STRUCTURE
```text
STOM_V.wt-dev/
??? stom.py                  # PyQt desktop launcher -> ui.ui_mainwindow.MainWindow
??? stom_backtest.py          # top-level backtest / CLI launch surface
??? ui/                       # MainWindow, pyd-derived wrappers, charts, dialogs
??? backtest/                 # official STOM backtest engines and optimizers
??? cli/                      # backtest runner, research loop, condition generation
??? ai_strategy_loop/         # autonomous condition evolution service/dashboard
??? trade/                    # Kiwoom/Upbit/Binance live runtime boundaries
??? research/                 # V3K analyzers, risk, microstructure, deep-learning assets
??? strategy/                 # strategy adapters and V3K analyzer bridge
??? scripts/                  # audits, verification, gated sidecar writers
??? tests/                    # unit/integration contract coverage
??? docs/                     # update logs, research notes, gate records, references
??? utility/ai_agent/         # STOM strategy-generation source text/rules
```

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Desktop startup | `stom.py`, `ui/ui_mainwindow.py` | MainWindow is the central GUI contract. |
| pyd GUI parity | `ui/ui_activated_*.py`, `scripts/verify_pyd_gui_contract.py` | Treat pyd behavior as Python wrapper contracts. |
| Backtest runtime | `stom_backtest.py`, `cli/runner.py`, `backtest/backtest.py` | Preserve queue/argv/process contracts. |
| AI condition loop | `ai_strategy_loop/controller/loop.py`, `ai_strategy_loop/dashboard/app.py` | Runtime state is under `ai_strategy_loop/state/`. |
| Condition research | `cli/research_loop.py`, `cli/condition_generator.py`, `cli/ml_factor_model.py` | B_* inputs only for generation; avoid leakage from result variables. |
| V3K gate context | `docs/update_log/2026-05-14_*`, `docs/CARRY_FORWARD_REGISTRY.md` | Read before any V3K work. |
| Nonrelease verification | `scripts/verify_nonrelease_sync.py` | Use this lane's verifier, not release sync. |
| Strategy text generation | `utility/ai_agent/strategy.txt`, `utility/ai_agent/rules.txt` | Read both before generating STOM syntax. |

## CODE MAP
| Surface | Type | Location | Role |
|---|---|---|---|
| `MainWindow` | class | `ui/ui_mainwindow.py` | Desktop app coordination and wrapper import surface. |
| `BackTest` | class | `backtest/backtest.py` | Official backtest child/process orchestration. |
| `run_backtest` | function | `cli/runner.py` | CLI queue/process setup and diagnostics. |
| `run_loop` | function/module | `ai_strategy_loop/controller/loop.py` | Strategy-loop generation/backtest cycle. |
| `app` | FastAPI app | `ai_strategy_loop/dashboard/app.py` | Dashboard API, WebSocket, static frontend. |
| V3K audits | scripts | `scripts/audit_v3k_*.py` | Gate/status verification; do not confuse with writers. |

## BRANCH ROLE
- Active checkout: `C:/System_Trading/STOM/STOM_V.wt-dev` -> `STOM_Version_2U_C`.
- Active propagation chain: `V2 -> 2U -> 2U_C`.
- `STOM_V.wt-2uc/` is retired/archive for this layout; do not recreate it or check out `STOM_Version_2U_C` there unless explicitly reopened.
- Sync upstream changes by cherry-pick, not overlay merge.
- Preserve CLI/runtime customizations already absorbed into this single baseline branch.

## SERIAL / PYD POLICY
- Do not add serial-key code in this branch family.
- V2 upstream may contain serial-key behavior in pyd files; 2U/2U_C intentionally remove it.
- Do not infer serial-key behavior back into 2U_C from upstream pyds.
- No tracked `.pyd` files are expected here; use Python wrappers and MainWindow parity checks.
- `sactivated_*` / `cactivated_*` aliases should resolve through shared `activated_XX(self, 'stock'/'coin')`-style wrappers, not unresolved legacy calls.

## V3K GATE STATE
- V3K means V3 features + Kiwoom retained; LS Securities REST/TR/REAL direct broker dependency is excluded.
- Actual gate execution is `3/6`.
- Gate 1 `gui-sidecar-write-await-user-approval`: completed as default-OFF local sidecar seed.
- Gate 2 `phase-f-f4-on-await-user-approval`: completed as Phase F analyzer-strategy sidecar enable.
- Gate 3 `phase-g-g3-on-await-user-approval`: completed as Phase G microstructure-engine sidecar enable.
- Gate 4 `phase-h-h2-h3-live-dryrun-await-user-approval`: approval phrase exists but execution is blocked here because KHOPENAPI-compatible evidence is absent. Exact phrase: `I approve phase-h-h2-h3-live-dryrun-await-user-approval only`.
- Gates 5 and 6 remain out-of-order blocked while Gate 4 is incomplete.
- Do not create USER_ACK, enable registry headings, operating `_database/` writes, DB cutover, KHOPENAPI connect/login, or live order/exit wiring without the exact approved later-gate phrase and required evidence.
- Feature flags must remain default-OFF.
- Do not call `update_goal(status="complete")` until all six V3K approval gates have concrete evidence.

## V3K READ-FIRST DOCS
Before V3K work in this checkout, read:
1. `docs/update_log/2026-05-08_v3k_full_feature_migration_goal_reset.md`
2. `docs/update_log/2026-05-08_v3_2uc_unmet_features_audit_and_research.md`
3. `docs/CARRY_FORWARD_REGISTRY.md`
4. `docs/update_log/2026-05-14_v3k_goal_completion_audit_checklist.md`
5. `docs/update_log/2026-05-14_v3k_gui_sidecar_gate1_execution.md`
6. `docs/update_log/2026-05-14_v3k_phase_f_gate2_execution.md`
7. `docs/update_log/2026-05-14_v3k_phase_g_gate3_execution.md`
8. `docs/update_log/2026-05-14_v3k_phase_h_gate4_blocked_environment.md`
9. `docs/update_log/2026-05-14_v3k_gate5_gate6_review_only_blocked.md`
10. `docs/update_log/2026-05-14_v3k_gate_approval_phrase_intake_guard.md`

## PROTECTED / RUNTIME PATHS
Do not treat these as source edits or disposable scratch:
`_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`, `backtest/graph/`, `.omx/reports/`, `v3k_settings*.json`, `_v3k_sidecar/v3k_gui_settings.json`.

## COMMANDS
```powershell
pytest tests/unit/ -q
python scripts/verify_nonrelease_sync.py
python scripts/verify_pyd_gui_contract.py
python scripts/smoke_offline_gui.py
python scripts/audit_v3k_gate5_gate6_review_only_blocked.py
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

## COMMIT / REVIEW RULES
- Stage files explicitly; do not use `git add -A`.
- Keep changes small, reviewable, and reversible.
- Commit messages must use Korean titles and Korean markdown bodies.
- After upstream sync or branch propagation, run `pytest tests/unit/ -q`; if nonrelease paths are touched, also run `python scripts/verify_nonrelease_sync.py`.

## STRATEGY GENERATION NOTES
If the task concerns trading-condition generation, read `utility/ai_agent/strategy.txt` and `utility/ai_agent/rules.txt` first, generate STOM syntax in the branch-local text format, and save generated strategies under `utility/ai_agent/`.
