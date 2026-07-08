# Lattice Condition Generation V2 Failure Map

Created: 2026-07-08T09:58:26+09:00

## Official Result

| Item | Result |
|---|---:|
| tick rows | 288 |
| tick gate passed | 0 |
| tick negative profit | 288 |
| min rows | 288 |
| min gate passed | 0 |
| P6 go | 0 |
| P6 hold | 0 |
| P6 no_go | 576 |
| positive + MDD + daily intersection | 0 |

## Conclusion

- Tick is diagnostic only: official tick 288 produced no positive-profit row.
- Min remains the redesign lane: sparse positive and low-MDD fragments exist, but daily coverage overlap is missing.
- The original lattice shape should not be repeated as a full Cartesian mining run.
- Gate relaxation alone is insufficient because the three-way intersection remains zero.

## V2 Keep / Discard

Keep:
- min lane sparse fragments
- composite coverage repair
- seed lineage as input only
- negative and holdout controls

Discard or demote:
- tick lane as discovery lane
- single-axis lattice repetition
- threshold-only repair
- automatic Plan D R3 continuation
