# Post-20260618 Robust Candidate Decision Card

Generated: 2026-06-19

## Decision

| Field | Value |
|---|---|
| Candidate | `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full` |
| Alias | 저시총 제외 방어 조합 |
| Status | `oos_passed` |
| Evidence label | 공식 OOS(r8 low-cap) + 포트폴리오 규칙(exit2 prior-month) 조합 |

## Official OOS — r8 low-cap entry filter only

| Slice | Profit | MDD | Trades | Gate |
|---|---:|---:|---:|---|
| 2025 Q4 stress | 310,886 | 9.25% | 19 | True |
| 2022-2026 annual total | 7,292,861 | max 19.09% | 263 | True |

## Portfolio rule layer — separate evidence

| Layer | Profit | MDD | Trades |
|---|---:|---:|---:|
| baseline r8_4 + exit2_balance | 31,505,991 | 9.3902% | 917 |
| prior-month -500k exclusion | 31,702,635 | 9.2726% | 843 |
| delta | 196,644 | -0.1176pp | — |

The exit2 prior-month rule is a portfolio allocation rule, not a plain official buy/sell OOS result.

## Follow-up separation

- `r8_exclude_month_11__exit2_skip_after_prior_exit2_loss_500k_else_full` remains a CSV shadow/high-overfit comparison only.
- The r8 low-cap official run is the standalone attribution check for the entry filter.
- No live/export/final approval/strategy DB action is taken.
