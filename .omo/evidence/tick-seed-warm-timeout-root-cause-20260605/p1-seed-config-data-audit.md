# P1 Seed Code, Effective Config, And Data Coverage Audit

Status: `complete`
Raw artifact: `.omo/evidence/tick-seed-warm-timeout-root-cause-20260605/p1-seed-config-data-audit.json`

## Inputs

- Source config: `.omo/evidence/tick-p7-timeout-unblock-live-strategy-visibility-20260605/p5-seed-diag-5m-config.json`
- Seed buy: `C_T_900_920_U2_B`
- Seed sell: `C_T_900_920_U2_S`
- DB access: SQLite read-only URI against `_database/stock_tick_back.db`

## Seed Code

| Seed | Exists | SHA-256 | Lines | self.Buy | self.Sell | Buy=True | Sell=True | Time Tokens |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| `C_T_900_920_U2_B` | yes | `902cb36b87f5828548531583cd4aa16ed4a5a2a597b3db3abba217cb0f86e2e3` | 431 | yes | no | 0 | 0 | 2 |
| `C_T_900_920_U2_S` | yes | `e61d8ba393ae74de73d07e0cd291861bc3edeec1050cbc7d06a0750d67cba5c6` | 87 | no | yes | 0 | 0 | 0 |

Buy first lines:

```text
# ================================
#  공통 계산 지표
# ================================
전일종가          = 현재가 / (1 + (등락율 / 100))                      # 단위: 원
시가등락율        = ((시가 - 전일종가) / 전일종가) * 100                # 단위: 퍼센트
시가대비등락율    = ((현재가 - 시가) / 시가) * 100                      # 단위: 퍼센트
```

Sell first lines:

```text
# ================================
#  공통 계산 지표
# ================================
시가대비등락율    = ((현재가 - 시가) / 시가) * 100                      # 단위: 퍼센트
```

The raw JSON artifact contains the full first-12-line snippets for both seeds.

## Effective Warm Backtest Config

| Field | Value |
|---|---:|
| start_date | `20250101` |
| end_date | `20250103` |
| start_time | `090000` |
| end_time | `090500` |
| avg_time | `30` |
| engine_count | `8` |
| is_tick | `true` |
| betting | `5` |
| divid_mode | `종목코드별 분류` |
| backtest timeout | `600` |
| warm run timeout | `120` |

## Data Coverage

| Field | Value |
|---|---:|
| DB exists | yes |
| moneytop rows in requested range | `2100` |
| distinct codes | `205` |
| covered days | `20250102=1800`, `20250103=300` |
| first covered day | `20250102` |
| moneytop value column | `거래대금순위` |

## Decision

- `SEED_CODE_MISSING_OR_STALE` is refuted for this seed pair: both seed texts exist and contain the expected `self.Buy`/`self.Sell` calls.
- `DATA_WINDOW_EMPTY_OR_NONTRADING` is refuted for the full requested range: 2100 moneytop rows and 205 distinct codes are present.
- `2025-01-01` is not covered in this DB slice, so one-day tiny runtime variants should use the first covered day, `2025-01-02`.
- Static facts are recorded only as facts. They are not treated as overfire proof.
