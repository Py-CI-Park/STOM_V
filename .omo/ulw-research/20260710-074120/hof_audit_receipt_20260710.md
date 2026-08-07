# Hall-of-Fame read-only audit receipt — 2026-07-10

## Scope

- Source DB: `ai_strategy_loop/state/loop_runs.db`
- Open mode: SQLite URI `mode=ro`; no dashboard import, DDL, WAL, export, or write
- DB SHA-256 at observation: `935cd8911b7ecc3ab5dc8ba19c1df9cb73411f6af7604100753c3ede6120b51d`
- DB size at observation: `14,082,048` bytes
- Source projection: `ai_strategy_loop/dashboard/app.py::_hall_of_fame_payload`
- Audit limit: all eligible rows, equivalent to `ai_limit=1_000_000`; the public/default projection limit is 30

## Reproduction rule

1. Read every `generations` row and each matching `runs.config_json`.
2. Retain `gate_passed=1`, `profit>0`, and `total_profit_pct>0`.
3. Compute window years as `(bt_full_end - bt_full_start).days / 365.25`.
4. Mark `<0.25` years as short-window; missing/invalid windows separately.
5. Apply current source classification: a nonempty `buy_name` not beginning with `AILOOP` is `seed`; otherwise `ai`.
6. Sort by score, run id, generation exactly as the dashboard does; use no cap for the audit counts.

## Reproduced counts

| Metric | Value |
|---|---:|
| All generation rows | 5,124 |
| HOF-eligible rows at uncapped audit limit | 1,578 |
| Classified `seed` | 1,520 |
| Classified `ai` | 58 |
| Unique buy names | 1,254 |
| Window `<0.25` year | 147 |
| Missing/invalid window | 8 |

Top name prefixes among eligible rows:

| Prefix | Rows |
|---|---:|
| `GATE` | 889 |
| `TMAP` | 319 |
| `LAT` | 182 |
| `AILOOP` | 58 |
| `Tick` | 55 |

The current prefix rule therefore labels many generated/research artifacts as `seed`; it does not prove human authorship.

## Longer-window AILOOP examples

The following are record-level examples, not a matched cohort or an unbiased system benchmark.

| Run / generation | Window | Annual simple return | MDD | Daily avg | Trades |
|---|---:|---:|---:|---:|---:|
| `multiseed_train_20260611/g8` | 2.998y | 25.43% | 12.19 | 0.3 | 201 |
| `multiseed_train_20260611/g12` | 2.998y | 36.77% | 18.47 | 0.4 | 310 |
| `multiseed_train_20260611/g16` | 2.998y | 40.27% | 19.84 | 0.4 | 311 |
| `multiseed_train_20260611/g14` | 2.998y | 21.43% | 12.37 | 0.3 | 206 |
| `human_fullperiod_seed_replay_20260628/g3` | 0.997y | 17.78% | 15.14 | 2.3 | 550 |

There are duplicate strategy names across run ids, including the full-period replay row and its source run. These rows must not be treated as independent discoveries without artifact-hash deduplication.

## Interpretation boundary

This receipt reproduces the dashboard-record distribution and its classification flaw. It does not establish a causal human-versus-AI alpha gap because the human reference set lacks the same trial denominator, engine replay, dates, costs, capital, and search budget.
