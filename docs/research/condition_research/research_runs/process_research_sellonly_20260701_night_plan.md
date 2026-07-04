# Research Plan — process_research_sellonly_20260701_night

## Scope

- canonical process: `process-research`
- preset: `research`
- lane: `sell-only repair`
- seed: `rr8_12_turnover_min_902=1.5`
- fixed parent buy: `GATE_rr8_12_turnover_min_902_1_5_B`
- parent sell source: `GATE_rr8_12_turnover_min_902_1_5_S`
- boundary: research-only, no export, no live, no final promotion
- slippage: 3-tick advisory only
- engine policy: 64 first; 32 fallback only on warm prepare failure, engine_data_response_timeout, no-metrics, or replay failure
- prompt policy: full parent buy/sell condition code and sha256 required, id-only forbidden

## Candidate axes

| Candidate | Axis | Expression | Hypothesis |
|---|---|---|---|
| `prv2sell_20260701_trail01` | `trailing_giveback` | `최고수익률 > 2.5 and 최고수익률 * 0.72 >= 수익률` | 기존 3.0/0.6 trailing보다 조금 더 빠르게 이익 반납을 차단해 give-back과 MDD를 줄인다. |
| `prv2sell_20260701_stop02` | `hard_stop` | `수익률 <= -3.5 and 현재가 < 현재가N(1)` | 기존 -5.0 hard stop보다 손실을 빠르게 끊되 하락 tick 확인으로 노이즈 손절을 제한한다. |
| `prv2sell_20260701_hold03` | `hold_time_stop` | `보유시간 > 45 and 수익률 < 1.0 and 현재가 < 최저현재가(int(30), int(보유시간))` | 45초 이후 이익이 충분하지 않고 단기 저점 이탈이 있으면 지지부진한 손실 확대를 차단한다. |
| `prv2sell_20260701_flowma04` | `orderflow_ma_breakdown` | `시가총액 < 10000 and (초당매도수량 - 초당매수수량) >= 매수총잔량 * 0.45 and 이동평균(60) > 현재가 and (현재가 / 현재가N(1) - 1) * 100 < -0.35` | 매도 압력과 MA 이탈이 동시에 나타나는 경우만 조기 청산해 orderflow 붕괴를 포착한다. |

## Acceptance for this research run

1. Produce Context Pack containing full STOM sources and full parent buy/sell code.
2. Produce Analysis Card v2 and candidate cards.
3. Run official backtests for baseline and sell-only candidates when environment permits.
4. Keep all candidates research-only and not promotion-ready.
5. Produce management, result, HTML/dashboard, safety, and final handoff artifacts.
