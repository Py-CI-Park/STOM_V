# Proxy OOS Candidate Design (2026-06-19)

Scope: run-owned proxy official OOS candidates derived from `POSTQ4_r8_exclude_cap_lt_1500` baseline.

Evidence taxonomy: these are candidate condition pairs for official OOS; they do not encode CSV switching, prior-month strategy PnL state, live/export behavior, or operating DB mutation.

| Candidate | Buy | Sell | Intent | Leakage review |
|---|---|---|---|---|
| P1_entry_liquidity_proxy | `PROXY_P1_entry_liquidity_B` | `PROXY_P1_entry_liquidity_S` | entry-pure: r8 저시총 제외를 유지하면서 1500~3000억 구간의 유동성/회전율/체결강도 과열 필터를 추가한다. | Uses only tick/current position variables listed in `utility/ai_agent/strategy.txt`; no future/result label, CSV selection, or prior-month strategy-PnL state. |
| P2_defensive_exit_proxy | `PROXY_P2_defensive_exit_B` | `PROXY_P2_defensive_exit_S` | exit-behavior: prior-month PnL state 없이 손실 차단과 최고수익률 반납 제한으로 exit2 방어 성향을 근사한다. | Uses only tick/current position variables listed in `utility/ai_agent/strategy.txt`; no future/result label, CSV selection, or prior-month strategy-PnL state. |
| P3_trend_vol_exit_proxy | `PROXY_P3_trend_vol_exit_B` | `PROXY_P3_trend_vol_exit_S` | exit-behavior: 더 큰 수익 구간은 보유하고 변동성/추세 이탈 손실은 제한해 r2full 참여 성향을 근사한다. | Uses only tick/current position variables listed in `utility/ai_agent/strategy.txt`; no future/result label, CSV selection, or prior-month strategy-PnL state. |

## Run-owned mutable paths

- strategy sqlite: `.omo/evidence/tmap-walkforward/proxy-oos-20260619/proxy-oos-strategy-20260619.sqlite`
- loop runs sqlite: `.omo/evidence/tmap-walkforward/proxy-oos-20260619/proxy-oos-loop-runs-20260619.sqlite`
- snapshots: `.omo/evidence/tmap-walkforward/proxy-oos-20260619/snapshots`
- current state: `.omo/evidence/tmap-walkforward/proxy-oos-20260619/current-state.json`
- stop flag: `.omo/evidence/tmap-walkforward/proxy-oos-20260619/STOP`
- pairs json: `.omo/evidence/tmap-walkforward/proxy-oos-20260619/pairs-proxy-oos-20260619.json`
