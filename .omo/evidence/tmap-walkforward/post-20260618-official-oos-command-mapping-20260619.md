# Post-20260618 Official OOS Command Mapping

Generated: 2026-06-19

## Verdict

P4 is executable **without `backtest.py` edits and without writing protected runtime `*.db` paths** by using evidence-local runtime artifacts only:

- strategy sandbox: `.omo/evidence/tmap-walkforward/post-q4-oos-strategy-20260619.sqlite`
- run-state sandbox: `.omo/evidence/tmap-walkforward/post-q4-oos-loop-runs-20260619.sqlite`
- snapshots/current-state: `.omo/evidence/tmap-walkforward/post-q4-oos-snapshots-20260619/`, `.omo/evidence/tmap-walkforward/post-q4-oos-current-state-20260619.json`
- wrapper: `.omo/evidence/tmap-walkforward/run_post_q4_oos_wrapper_20260619.py`

The robust primary candidate remains two-layer evidence:

| Layer | Evidence type | Candidate/rule |
|---|---|---|
| r8 filtered buy/sell | `공식 OOS` | `r8_exclude_cap_lt_1500` |
| exit2 prior-month allocation | `포트폴리오 규칙` | `exit2_skip_after_prior_exit2_loss_500k_else_full` |
| robust combined candidate | `공식 OOS + 포트폴리오 규칙 조합` | `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full` |

## Why a Single Pair Command Is Not Enough

`r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full` is not a plain STOM buy/sell pair. It combines a deployable r8 entry filter with a causal prior-month portfolio rule. `claude_candidate_batch_eval` can run the r8 filtered pair as official OOS; the exit2 prior-month rule must be reported separately as a portfolio-layer rule.

## Safe Runner Envelope

### 1. Build the evidence-local `.sqlite` strategy sandbox and pair JSON

This command reads `ai_strategy_loop/state/loop_strategies.db` in read-only mode and writes only evidence-local `.sqlite`/JSON artifacts. It does **not** call `materialize_candidate` because that helper writes `ai_strategy_loop/state/loop_strategies.db`.

```powershell
$env:PYTHONUTF8='1'
python -c "from pathlib import Path; import json, sqlite3; from cli.strategy_generator import save_strategy_to_db; src='ai_strategy_loop/state/loop_strategies.db'; sandbox=Path('.omo/evidence/tmap-walkforward/post-q4-oos-strategy-20260619.sqlite'); sandbox.parent.mkdir(parents=True, exist_ok=True); con=sqlite3.connect(f'file:{src}?mode=ro', uri=True); buy=con.execute('SELECT \"전략코드\" FROM stockbuy WHERE \"index\"=?',('GATE_r8_4_strength_max_250_B',)).fetchone()[0]; sell=con.execute('SELECT \"전략코드\" FROM stocksell WHERE \"index\"=?',('GATE_r8_4_strength_max_250_S',)).fetchone()[0]; con.close(); marker='\nif 매수:\n    self.Buy()'; guard='\nif 시가총액 < 1500:\n    매수 = False\n\nif 매수:\n    self.Buy()'; assert marker in buy; buy=buy.replace(marker, guard); buy_name='POSTQ4_r8_exclude_cap_lt_1500_B'; sell_name='POSTQ4_r8_exclude_cap_lt_1500_S'; rb=save_strategy_to_db(str(sandbox), buy_name, buy, 'buy'); rs=save_strategy_to_db(str(sandbox), sell_name, sell, 'sell'); assert rb['status']=='ok' and rs['status']=='ok', (rb, rs); db=sqlite3.connect(str(sandbox)); db.execute('CREATE TABLE IF NOT EXISTS formula (\"수식명\" TEXT, \"차트표시\" TEXT, \"전략연산\" TEXT, \"팩터명\" TEXT, \"표시형태\" TEXT, \"색상\" TEXT, \"굵기\" TEXT, \"종류\" TEXT, \"수식코드\" TEXT)'); db.commit(); db.close(); out=Path('.omo/evidence/tmap-walkforward/pairs-post-q4-r8-lowcap-oos-20260619.json'); out.write_text(json.dumps([{'label':'r8_exclude_cap_lt_1500','buy':buy_name,'sell':sell_name}], ensure_ascii=False), encoding='utf-8'); print(str(sandbox)); print(str(out)); print(buy_name, sell_name)"
```

Expected artifacts:

```text
.omo/evidence/tmap-walkforward/post-q4-oos-strategy-20260619.sqlite
.omo/evidence/tmap-walkforward/pairs-post-q4-r8-lowcap-oos-20260619.json
```

### 2. Run official OOS through the evidence-local wrapper

Run one period at a time and stop on any non-zero exit. The wrapper sets `STOM_CLI_DB_STRATEGY` and patches `LoopState` output paths to evidence-local `.sqlite`/JSON paths before running `claude_candidate_batch_eval`.

Fast Q4 stress first:

```powershell
$env:PYTHONUTF8='1'
python .omo/evidence/tmap-walkforward/run_post_q4_oos_wrapper_20260619.py --pairs-json .omo/evidence/tmap-walkforward/pairs-post-q4-r8-lowcap-oos-20260619.json --config-json .omo/evidence/tmap-walkforward/oos-2025-q4-e32-config.json --run-id post_q4_r8_lowcap_oos_2025q4_20260619
```

Annual coverage:

```powershell
$env:PYTHONUTF8='1'
python .omo/evidence/tmap-walkforward/run_post_q4_oos_wrapper_20260619.py --pairs-json .omo/evidence/tmap-walkforward/pairs-post-q4-r8-lowcap-oos-20260619.json --config-json .omo/evidence/tmap-walkforward/oos-2022-e32-config.json --run-id post_q4_r8_lowcap_oos_2022_20260619
python .omo/evidence/tmap-walkforward/run_post_q4_oos_wrapper_20260619.py --pairs-json .omo/evidence/tmap-walkforward/pairs-post-q4-r8-lowcap-oos-20260619.json --config-json .omo/evidence/tmap-walkforward/oos-2023-e32-config.json --run-id post_q4_r8_lowcap_oos_2023_20260619
python .omo/evidence/tmap-walkforward/run_post_q4_oos_wrapper_20260619.py --pairs-json .omo/evidence/tmap-walkforward/pairs-post-q4-r8-lowcap-oos-20260619.json --config-json .omo/evidence/tmap-walkforward/oos-2024-e32-config.json --run-id post_q4_r8_lowcap_oos_2024_20260619
python .omo/evidence/tmap-walkforward/run_post_q4_oos_wrapper_20260619.py --pairs-json .omo/evidence/tmap-walkforward/pairs-post-q4-r8-lowcap-oos-20260619.json --config-json .omo/evidence/tmap-walkforward/oos-2025-e32-config.json --run-id post_q4_r8_lowcap_oos_2025_20260619
python .omo/evidence/tmap-walkforward/run_post_q4_oos_wrapper_20260619.py --pairs-json .omo/evidence/tmap-walkforward/pairs-post-q4-r8-lowcap-oos-20260619.json --config-json .omo/evidence/tmap-walkforward/oos-2026-e32-config.json --run-id post_q4_r8_lowcap_oos_2026_20260619
```

### 3. Portfolio-layer report

After the new r8 low-cap official outputs exist, combine them with existing official OOS outputs for `exit2_balance` and `r2full_mdd`. The combined candidate must be labeled:

```text
공식 OOS(r8 low-cap) + 포트폴리오 규칙(exit2 prior-month) + 기존 공식 OOS(exit2/r2full)
```

## Stop Rules

| Stop rule | Reason |
|---|---|
| Any command writes `*.db` | Protected runtime DB guardrail violation |
| Any command writes `_database/strategy.db`, `ai_strategy_loop/state/loop_strategies.db`, or `ai_strategy_loop/state/loop_runs.db` | Operating/runtime DB guardrail violation |
| The wrapper is not used for official OOS | LoopState would default to `ai_strategy_loop/state/loop_runs.db` |
| The materialized buy code cannot be validated by the batch engine | Avoid invalid STOM syntax |
| Any command requires `backtest.py` edits | Plan guardrail violation |
| Any command requires live/V3K/KHOPENAPI paths | Approval-gate violation |
| Output cannot distinguish `공식 OOS` from `포트폴리오 규칙` | Evidence taxonomy violation |

## Next Command

The next executable command is section 1: build the evidence-local `.sqlite` strategy sandbox and pair JSON. After inspecting that pair JSON, run section 2 Q4 stress first, then annual coverage year-by-year.
