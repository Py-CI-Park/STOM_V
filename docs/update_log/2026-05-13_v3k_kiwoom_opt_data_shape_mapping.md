# V3K Phase G — Kiwoom OPT* data-shape mapping

| 항목 | 값 |
| --- | --- |
| 작성일 | 2026-05-13 KST |
| 대상 | Phase G G-1 / T02 |
| source | V3 `strategy/analyzer_microstructure.py` logical fields |
| target | 2U_C Kiwoom 유지 field names in `utility/setting_base.py` |
| 결론 | 2U_C 기존 field name을 그대로 사용하고, engine은 caller-owned mapping만 받는다. |

---

## 1. Mapping 원칙

- engine은 Kiwoom API를 직접 호출하지 않는다.
- engine은 운영 DB를 열지 않는다.
- engine은 `dict_findex` 또는 caller-owned row/mapping에서 값을 읽을 수 있는 순수 계산 계층으로 둔다.
- tick/minute 차이는 `초당*` 우선, 없으면 `분당*` fallback으로 처리한다.
- 없는 field는 0.0 fallback을 허용하되, Page G-2 parity에서 영향이 크면 mapping을 보정한다.

---

## 2. Field mapping

| V3 logical field | 2U_C/Kiwoom 유지 field | fallback | 비고 |
| --- | --- | --- | --- |
| `current_price` | `현재가` | 0.0 | 가격·depth value 계산 기준 |
| `buy_volume` | `초당매수수량` | `분당매수수량`, 0.0 | tick 우선 |
| `sell_volume` | `초당매도수량` | `분당매도수량`, 0.0 | tick 우선 |
| `ask_price_1..5` | `매도호가1..5` | 0.0 | 5단계 호가 |
| `bid_price_1..5` | `매수호가1..5` | 0.0 | 5단계 호가 |
| `ask_quantity_1..5` | `매도잔량1..5` | 0.0 | V3 ask qty |
| `bid_quantity_1..5` | `매수잔량1..5` | 0.0 | V3 bid qty |
| `depth_ratio` | 계산값 | 1.0 | `sum(매수잔량) / sum(매도잔량)` |
| `imbalance` | 계산값 | 0.0 | `(bid_qty - ask_qty) / total_qty` |
| `weighted_depth_ratio` | 계산값 | 1.0 | 1~5호가 가중치 `(0.35,0.25,0.20,0.12,0.08)` |

---

## 3. Output contract

`strategy/v3k_microstructure_engine.py`는 다음 5개 값을 반환한다.

| output | 의미 | G-1 상태 |
| --- | --- | --- |
| `미시구조신호` | buy=1, sell=-1, hold=0 | unit smoke only |
| `미시구조신뢰도` | 0~1 confidence | unit smoke only |
| `미시구조리스크` | 0~1 risk | unit smoke only |
| `호가불균형` | bid/ask imbalance | unit smoke only |
| `가중호가비율` | weighted bid/ask depth ratio | unit smoke only |

---

## 4. 미결정/후속 검증

- G-2 parity에서 V3 baseline과 ±15% 이상 차이가 나면 mapping을 수정한다.
- G-2 benchmark에서 ±20% 성능 한계를 넘으면 계산식을 단순화하거나 cache 전략을 검토한다.
- G-3 ON 전까지 이 output은 live order/exit rule에 연결하지 않는다.
