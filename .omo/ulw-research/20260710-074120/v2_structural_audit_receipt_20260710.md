# V2 condition structural audit receipt — 2026-07-10

## Inputs and read mode

- V2 seed JSON SHA-256: `7525528f406138e96e99bdf54a226a521a7ac32091ab934ece57fcad432161c3`
- Human reference DB: `ai_strategy_loop/state/loop_strategies.db`, SQLite URI `mode=ro`
- Strategy DB SHA-256: `42bb7c5b3a9eee902443a173381d3f78651800f5f6f778b68b9c0542c30a4ed5`
- Human names: `Tick_B_902_905_Update_2`, `Tick_S_902_905_Update_2`
- No strategy, DB, or runtime write was performed.

## Deterministic method

- Exact uniqueness: full source string equality.
- Numeric-normalized skeleton: Python AST with numeric `Constant` nodes replaced by `0`, then `ast.dump(..., include_attributes=False)`.
- Structure counts: standard Python AST nodes (`If`, `Compare`, `BoolOp`, `Call`, `Name`).
- Depth: module root counted as depth 1.
- Body06/body08 similarity: Jaccard over stripped, whitespace-normalized, nonempty source lines.

## Results

| Metric | V2 buy | V2 sell | Human buy | Human sell |
|---|---:|---:|---:|---:|
| Exact unique | 8 | 4 | 1 reference | 1 reference |
| Numeric-normalized skeleton | 6 | 1 | — | — |
| Mean characters | 358.25 | — | 3,836 | 1,374 |
| Mean lines | 18.25 | — | 128 | 47 |
| Mean `If` | 8.125 | — | 44 | 12 |
| Mean `Compare` | 7.125 | — | 48 | 26 |
| Mean `BoolOp` | 0 | — | 7 | 8 |
| Mean `Call` | 3.375 | — | 12 | 18 |
| Mean unique names | 11.25 | — | 34 | 19 |
| Mean/root-counted AST depth | 13.875 | — | 30 | 19 |

- One sell SHA-256, `361481ae...f97f1d`, is shared by five of eight bodies.
- Body06/body08 buy-line Jaccard is `0.9166666667`.

## Interpretation boundary

This proves low structural diversity in this eight-body batch relative to the chosen gold seed. It does not prove that longer or deeper code is more profitable, nor that template similarity alone caused the negative P&L.
