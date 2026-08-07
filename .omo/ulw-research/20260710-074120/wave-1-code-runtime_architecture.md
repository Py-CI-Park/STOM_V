# Wave 1: Runtime Architecture (preliminary raise)

Observer: `/root/runtime_architecture`

- Dashboard entry and loop execution are distinct: `python -m ai_strategy_loop` serves the dashboard, while `ai_strategy_loop.controller.loop` owns execution.
- Default engine is warm; cold official backtest is fallback after warm prepare failure.
- Potential documentation drift: graduation holdout is described as no-op in launch config but runtime applies it.
- Potential wiring gap: `principle_gate_enabled` exists in generator/config, but `_generate_pair` may not pass it.
- Final approval is the only located export boundary.
- Raised contradiction: promotion preset publishes `condition_generation_allowed=false`, but `run_loop` apparently never consumes capability flags.
- Raised reachability gap: strict Context Pack/candidate-pack modules may have only wrapper/test callers; the live loop remains on legacy `generate_strategy/build_messages`.
- Raised export gap: backend final approval appears to accept arbitrary nonempty names and export without tying them to a recorded hard-gate winner.
- Raised GA parity gap: GA bypasses many hill-climb flags/callbacks and lacks cold fallback/multiyear winner wiring.

## EXPAND

- LEAD: audit config-to-runtime consumption, especially principle gate and holdout — WHY: a visible/configurable feature that is not wired makes the loop look more data-driven than it is — ANGLE: enumerate references, call arguments, tests, and runtime state.
- LEAD: audit promotion capability enforcement and final export evidence binding — WHY: dashboard policy text may not be a runtime safety boundary — ANGLE: trace launch and approval endpoints without mutating production state.
- LEAD: build a producer-consumer reachability matrix for Context Pack, Analysis Card, candidate pack, feature hints, axis ledger, and hypotheses — WHY: stored evidence is not learning unless generation consumes it — ANGLE: callers plus current run configs.
- LEAD: compare GA and hill-climb parity — WHY: the nominally creative evolutionary mode may omit the strongest safety/learning paths — ANGLE: argument and scoring/persistence diff.
