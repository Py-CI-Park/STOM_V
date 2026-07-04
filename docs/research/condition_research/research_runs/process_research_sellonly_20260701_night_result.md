# Research Result Report — process_research_sellonly_20260701_night

## Executive summary

This run validates the sell-only repair extension of process-research v2. It keeps the parent buy condition fixed and changes only the sell condition one axis at a time. Every result is research-only and cannot be exported, traded live, or final-promoted.

## Baseline

| Profit KRW | MDD % | Trades | Win % | Avg hold |
|---:|---:|---:|---:|---:|
| 518822 | 20.54 | 175 | 52.57 | 280.04 |

## Candidate official backtest results

| Candidate | Axis | Profit KRW | ΔProfit | MDD % | ΔMDD | Trades | Win % | Avg hold | Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| `prv2sell_20260701_trail01` | `trailing_giveback` | 356100 | -162722 | 24.61 | 4.07 | 177 | 54.24 | 231.02 | `success` |
| `prv2sell_20260701_stop02` | `hard_stop` | 558947 | 40125 | 19.09 | -1.45 | 175 | 52.57 | 260.74 | `success` |
| `prv2sell_20260701_hold03` | `hold_time_stop` | 202095 | -316727 | 28.45 | 7.91 | 176 | 45.45 | 180.43 | `success` |
| `prv2sell_20260701_flowma04` | `orderflow_ma_breakdown` | 96566 | -422256 | 28.1 | 7.56 | 182 | 44.51 | 168.9 | `success` |
| `prv2sell_20260701_trail05` | `additional_trailing_ladder` | 530905 | 12083 | 20.6 | 0.06 | 175 | 52.57 | 275.6 | `success` |
| `prv2sell_20260701_stop06` | `additional_hard_stop_ladder` | 554107 | 35285 | 20.04 | -0.5 | 175 | 52.57 | 278.89 | `success` |

## Interpretation rule

- Prefer candidates that lower MDD without destroying trade count and profit.
- A lower-MDD but low-profit candidate is a diagnostic branch, not a promotion candidate.
- Sell-only changes can be paired with buy-side reject filters only after standalone sell effect is confirmed.
