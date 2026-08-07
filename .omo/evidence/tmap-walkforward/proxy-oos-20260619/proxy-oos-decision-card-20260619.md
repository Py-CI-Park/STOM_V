# Proxy OOS Decision Card (2026-06-19)

## Decision

`evidence_blocker`

공식 OOS가 후보별 성과 증거를 만들기 전에 Q4 stress prepare 단계에서 warm-engine data loading timeout으로 중단되었습니다. 따라서 proxy 후보는 `pass`도 `reject`도 아니며, 공식 trade-detail/CSV evidence 누락 때문에 `evidence_blocker`입니다.

## Candidates

| Candidate | Buy | Sell | Decision |
|---|---|---|---|
| P1_entry_liquidity_proxy | `PROXY_P1_entry_liquidity_B` | `PROXY_P1_entry_liquidity_S` | `evidence_blocker` |
| P2_defensive_exit_proxy | `PROXY_P2_defensive_exit_B` | `PROXY_P2_defensive_exit_S` | `evidence_blocker` |
| P3_trend_vol_exit_proxy | `PROXY_P3_trend_vol_exit_B` | `PROXY_P3_trend_vol_exit_S` | `evidence_blocker` |

## OOS attempts

| Run | Config | Result |
|---|---|---|
| `proxy_oos_q4_20260619` | baseline e32 Q4 config | tool timeout after 2400s before prepare completion; DB row marked `timeout_aborted` |
| `proxy_oos_q4_e8_20260619` | proxy e8 Q4 config | return code 2; `engine data loading timed out` after 1810s |

## What was proven

- 후보 조건식 3쌍은 evidence-local strategy sqlite에 저장되었습니다.
- `stom_backtest.py --dry-run` 기준 3쌍 모두 전략명/config validation은 통과했습니다.
- 공식 OOS 성과표, 거래수, MDD, top-trade concentration은 생성되지 않았습니다.

## What was not proven

- 어떤 proxy 후보도 공식 OOS `pass`가 아닙니다.
- 어떤 proxy 후보도 성과 기준 미달로 `reject`된 것도 아닙니다.
- warm-engine data loading blocker가 먼저 발생했기 때문에 성과 판단은 보류입니다.

## Next recommendation

공식 warm-engine data loading timeout을 해결하거나 같은 run root를 OOS 가능 환경에서 재실행한 뒤, Q4 stress부터 다시 시작해야 합니다. Q4가 통과해야 2022~2026 YTD 연도별 OOS로 넘어갑니다.
