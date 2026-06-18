# Task 3 — Local Code, Dashboard, Backtest, CLI, V3K Evidence Refresh

## Summary Judgment

The current dashboard and autonomous condition-evolution process are **well developed as a research/control-plane system** for generating, testing, analyzing, and refining STOM condition candidates toward the human reference style. It is **not yet sufficient to claim automatic production of human-level or superior profitable conditions**, because the TICK T0-T4 toggles have not been run through multiyear full-universe research plus 2022/2026 OOS validation.

## Inspected Surfaces

### Portable handoff and current state
- `docs/AGENT_HANDOFF.md`: present. Establishes non-Claude, self-contained handoff, invariants, TICK T0-T4 status, ground truth, architecture map, and next work.
- `docs/update_log/2026-06-03_tick_program_complete_handoff.md`: present. Detailed TICK T0-T4 handoff.
- `docs/update_log/2026-06-02_comprehensive_review_and_redirection.md`: present. Earlier architecture/research audit and direction reset.

Classification: **present/changed** from prior report. The work now has a clearer portable handoff and a TICK-first infrastructure completion record.

### AI loop configuration and generation
- `ai_strategy_loop/config.py`: present. Confirms default-OFF toggles for classification generation, few-shot, filter gates, time-window no-op rejection, prompt logging, equity points, hypothesis tracking, segment feedback, adaptive timing, and MDD/exit feedback.
- `ai_strategy_loop/brain/prompt.py`: present. Contains prompt blocks for filter gates, classification, time dispersion, segment feedback, and related guidance.
- `ai_strategy_loop/brain/generator.py`: present. Contains pre-save validation path including filter gate and meaningful time-window checks.
- `ai_strategy_loop/brain/filter_gate.py`: present. Contains time-window measurement and no-op detection.
- `ai_strategy_loop/brain/segment_feedback.py`: present by handoff and grep evidence as T4.

Classification: **present**. Candidate generation infrastructure is strong; profitability proof remains external to generation.

### Scoring and analysis
- `ai_strategy_loop/fitness/score.py`: present. Hard gate remains protected by invariant.
- `ai_strategy_loop/fitness/edge_ratio.py`: present. `/edge_ratio` on `tickwide_t0b` returned global edge_ratio `1.4039`, win_rate `0.4828`, mae_efficiency `0.0541`.
- `ai_strategy_loop/fitness/feature_importance.py`: present. `/feature_importance` on `tickwide_t0b` returned B_* feature rankings including `B_시분초`, `B_체결강도`, `B_매수총잔량`.
- `ai_strategy_loop/fitness/adaptive_timing.py`: present as analysis-only.
- `ai_strategy_loop/fitness/backfinder_principle.py`: present by handoff; T2 smoke produced highest-cell lift `8.99`.

Classification: **present/partially validated**. Analysis tooling is adequate for research feedback. Statistical promotion controls such as PBO/DSR/CVaR remain roadmap.

### Runtime loop and state
- `ai_strategy_loop/controller/loop.py`: present. `run_loop` is the main generation/backtest/score/autopsy loop.
- `ai_strategy_loop/controller/state.py`: present. Supports `runs`, `generations`, `prompts`, and `equity_points`.
- `ai_strategy_loop/state/loop_runs.db`: read-only inspected in Task 4.
- `ai_strategy_loop/state/loop_strategies.db`: read-only inspected in Task 4.

Classification: **present/changed**. Observability has improved since the prior report.

### Dashboard
- `ai_strategy_loop/dashboard/app.py`: present. Endpoints found: `/health`, `/status`, `/config/spec`, `/runs`, `/run_state`, `/backtest_detail`, `/adaptive_timing`, `/edge_ratio`, `/feature_importance`, `/ws`, and `final_approval`.
- `ai_strategy_loop/dashboard/frontend/analysis.jsx`: present. Renders edge_ratio and feature_importance panels.
- `ai_strategy_loop/dashboard/frontend/chart.jsx`: present. Uses `/backtest_detail`.
- Live dashboard `http://127.0.0.1:8770/ui/`: HTTP 200, title `STOM AI · 조건식 자율 진화 대시보드`, body length 13,656, screenshot artifact `.omo/evidence/dashboard-ui-playwright.png`.
- Console issues: one Babel-transformer warning and one 404 resource error. These do not prevent rendering but should be cleaned up.

Classification: **present/working**. Dashboard is good for live review and analysis. It still needs a single enforceable promotion/rejection card with OOS/PBO/slippage/lineage badges.

### Backtest
- `backtest/backtest.py`: present.
- `backtest/backengine_base.py`: present.
- `backtest/rolling_walk_forward_test.py`: referenced by plan; local inspection via root did not deeply parse it in this pass.
- `backtest/optimiz.py`: referenced by plan; local inspection via root did not deeply parse it in this pass.

Classification: **present/not-deeply-reinspected**. Official engine remains protected and should not be modified.

### CLI research
- `cli/research_loop.py`, `cli/condition_generator.py`, `cli/ml_factor_model.py`, `cli/research_optimizer.py`, `cli/research_v3_decision.py`: referenced in prior report and root AGENTS. Root pass did not deeply parse every file in this turn.

Classification: **present/not-deeply-reinspected**. Prior report and handoff keep CLI as the non-LLM evidence path.

### V3K analyzers
- `research/analyzer/`, `research/deeplearning/`, `strategy/v3k_analyzer_adapter.py`: referenced by plan and prior report. Root pass did not execute analyzers.
- Root `AGENTS.md` confirms V3K gate execution remains `3/6`; later gates blocked.

Classification: **offline/advisory only**. No gate advancement.

### Human references
- `docs/reference/STOM_Good_Results/`: present. Contains report markdown and 17 screenshot PNGs plus zoom/crop artifacts.

Classification: **present**. Human-good reference corpus is available and should remain the benchmark.

## Pre-existing Dirty State

`git status --short --branch` shows modified root `AGENTS.md`, untracked `.claude/`, `.omo/`, many subdirectory `AGENTS.md`, `docs/reference/`, and temp files. These are treated as pre-existing except `.omo/` evidence and Boulder files created for this review.

## Sufficiency Answer

- **Sufficient as a research system:** yes. It can generate candidates, run official backtests, persist runs, display live dashboard data, analyze edge/feature/time/segment behavior, and feed loss segments back into prompts.
- **Sufficient as a proven human/superhuman strategy factory:** not yet. The missing proof is the next handoff step: toggles ON, multiyear research run, and 2022/2026 OOS comparison against the human reference.
