# TRADE KNOWLEDGE BASE

## OVERVIEW
`trade/` contains live broker runtime boundaries for Kiwoom stock trading and coin/futures exchanges. This area can create real trading side effects; keep changes narrowly scoped and gate-aware.

## STRUCTURE
```text
trade/
??? base_strategy.py
??? stock_korea/             # Kiwoom manager/receiver/trader/runtime
??? upbit/                   # Upbit receiver/strategy/trader
??? binance/                 # Binance receiver/strategy/trader
??? future_oversea/          # overseas futures runtime
```

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Shared strategy runtime | `base_strategy.py` | common strategy behavior. |
| Kiwoom manager | `stock_korea/kiwoom_manager.py` | process orchestration boundary. |
| Kiwoom trader | `stock_korea/trader_kiwoom.py` | live order/runtime boundary. |
| Binance runtime | `binance/*_tick.py`, `binance_trader.py` | receiver/strategy/trader split. |
| Upbit runtime | `upbit/*_tick.py`, `upbit_trader.py` | receiver/strategy/trader split. |

## CONVENTIONS
- Kiwoom is retained for V3K; LS Securities direct REST/TR/REAL broker dependency is excluded.
- Keep live runtime changes separate from backtest/research changes.
- Treat KHOPENAPI connect/login and order/exit wiring as approval-gated side effects.
- Preserve process/queue message contracts used by UI and backtest surfaces.

## ANTI-PATTERNS
- Do not add live order/exit rule consumption before the exact Gate 6 approval.
- Do not perform KHOPENAPI login/connect in this environment without compatible sentinel evidence and gate approval.
- Do not reintroduce serial-key behavior.

## LOCAL GOTCHAS
- Broker runtime files may start processes or network/session paths; inspect entry guards before running.
- Keep stock/coin/futures broker assumptions separated.
- Prefer read-only analysis unless the task explicitly asks for runtime changes.
