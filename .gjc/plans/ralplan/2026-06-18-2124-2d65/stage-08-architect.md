# Summary
G002 is substantively resolved for the safe official OOS command mapping. The reviewed mapping and wrapper define an evidence-local command envelope, the root path is fixed to `parents[3]`, and the runner avoids protected runtime DB writes, `materialize_candidate`, `backtest.py`, live, and V3K paths.

Recommendation: APPROVE. The only remaining note is operational bookkeeping: `.gjc/ultragoal/goals.json` still records G002 as active and G001 as review_blocked, so update the ultragoal ledger/status after accepting this review before executing P4.

# Analysis
- Spec compliance: `.omo/evidence/tmap-walkforward/post-20260618-official-oos-command-mapping-20260619.md:7-11` states P4 uses evidence-local runtime artifacts only: strategy sandbox, run-state sandbox, snapshots/current-state, and wrapper. `.omo/evidence/tmap-walkforward/run_post_q4_oos_wrapper_20260619.py:8-14` computes repo root from `.omo/evidence/tmap-walkforward` using `parents[3]` and derives all OOS state paths under `.omo/evidence/tmap-walkforward`.
- Wrapper safety: `run_post_q4_oos_wrapper_20260619.py:19` sets `STOM_CLI_DB_STRATEGY` to the evidence-local strategy sqlite, and `run_post_q4_oos_wrapper_20260619.py:23-26` patches `LoopState` run DB, snapshots, current-state, and stop-flag paths to evidence-local artifacts before `runpy.run_module` executes `ai_strategy_loop.scripts.claude_candidate_batch_eval`.
- Command envelope: `post-20260618-official-oos-command-mapping-20260619.md:30` explicitly forbids `materialize_candidate` because it writes `ai_strategy_loop/state/loop_strategies.db`; the build command at line 34 reads that DB with `mode=ro` and writes only the evidence-local sqlite and pair JSON. Lines 46-64 route Q4 and yearly official OOS through the wrapper.
- Guardrails: `post-20260618-official-oos-command-mapping-20260619.md:78-84` define stop rules for any `*.db` write, protected runtime DB writes, wrapper bypass, `backtest.py` edits, live/V3K/KHOPENAPI paths, and taxonomy loss. The reviewed commands do not invoke `backtest.py`, live trading, V3K, KHOPENAPI, or `materialize_candidate`.
- Evidence taxonomy: `post-20260618-official-oos-command-mapping-20260619.md:18-20` separates r8 filtered buy/sell as `공식 OOS`, exit2 prior-month allocation as `포트폴리오 규칙`, and the robust combined candidate as `공식 OOS + 포트폴리오 규칙 조합`. Lines 66-71 preserve the portfolio-layer report label for combined evidence.
- Pair artifact: `.omo/evidence/tmap-walkforward/pairs-post-q4-r8-lowcap-oos-20260619.json:1` contains one official-run pair, label `r8_exclude_cap_lt_1500`, buy `POSTQ4_r8_exclude_cap_lt_1500_B`, sell `POSTQ4_r8_exclude_cap_lt_1500_S`, matching the mapping and avoiding a false single-pair representation of the compound portfolio rule.
- Goal state: `.gjc/ultragoal/goals.json:20-21` still shows G002 objective and status `active`; `.gjc/ultragoal/goals.json:11` keeps G001 `review_blocked`. That is not a technical blocker in the wrapper or mapping, but it should be reconciled after approval.

# Root Cause
The prior blocker was an unsafe or ambiguous path envelope for official OOS execution, with risk that the wrapper rooted paths under `.omo` instead of the repository root and that official runner state could fall back to protected runtime DBs. The fixed wrapper root `parents[3]` plus explicit evidence-local state rebinding addresses that root cause.

# Findings
No blocking findings.

- LOW, `.gjc/ultragoal/goals.json:11,20-21`: G002 is still marked `active` and G001 remains `review_blocked` even though the reviewed artifacts now satisfy the G002 command-mapping objective. Impact: process state can confuse the next operator or cause unnecessary re-review. Fix: after accepting this review, record the review receipt in the ledger and mark G002 complete or otherwise unblock G001 before P4 setup.

# Recommendations
1. Approve G002 as resolved for architecture, product command envelope, and wrapper code safety.
2. Update ultragoal bookkeeping after approval: mark G002 complete or reviewed, attach this artifact receipt, and unblock G001 for P4 setup.
3. Execute only the documented sequence: build evidence-local sandbox and pair JSON, inspect the pair JSON, then run Q4 stress first through the wrapper and yearly coverage one period at a time.
4. Keep the stop rules strict: any protected runtime DB write, wrapper bypass, `backtest.py` edit, live/V3K/KHOPENAPI path, or taxonomy collapse should stop execution.

# Architectural Status
CLEAR

# Code Review Recommendation
APPROVE

# Trade-offs
- Evidence-local wrapper: preferred because it reuses the official batch evaluator while relocating strategy and run state to `.omo/evidence/tmap-walkforward`; tradeoff is a small adapter surface that must stay aligned with `LoopState` globals.
- Direct official runner without wrapper: rejected because `LoopState` can default to protected runtime paths.
- Editing `backtest.py` or adding condition-runner support: rejected for this blocker because it expands scope and violates the current guardrail.
- Treating the compound candidate as one plain pair: rejected because it would erase the distinction between `공식 OOS` and `포트폴리오 규칙` evidence.
