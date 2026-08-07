"""엔진 축 검증 사다리 — **실제 체결된 거래**로만 후보를 심판한다.

## 왜 다시 만드는가 (2026-08-07 정정)

`run_exit_ladder` 는 사다리를 **지도(map) 축**에서 돌렸다. 그런데 지도는 챔피언 진입
344건을 전부 세는 반면 엔진은 자본 한도 때문에 155~161건만 체결한다. 지도가 세는
나머지 187건은 **엔진이 사지도 않는 거래**다. 그 187건이 국면 구간 2·4 를 음수로
끌어내려, 엔진에서 멀쩡한 후보가 사다리에서 탈락했다.

실측 대조:

| 축 | 챔피언 | trailing(5/2) |
|---|---|---|
| 지도 | (미측정) | 2/4 → FAIL |
| **엔진 실거래** | **3/4** | **4/4** |

두 번째 교훈이 더 크다. **챔피언 자신이 3/4다.** "4/4 양수"를 합격선으로 쓰면
챔피언도 탈락한다. 합격선을 챔피언 위에 그어 놓고 "아무도 못 넘는다"고 보고한
셈이었다.

## 이 모듈의 규칙

1. **심판은 엔진 체결 기록**이다. 지도는 탐색용이지 심판이 아니다.
2. **합격선은 챔피언이다.** 절대 기준(4/4 같은)이 아니라 "챔피언 이상"으로 잰다.
   챔피언이 떨어지는 기준은 후보가 아니라 **기준이 틀린 것**이다.
3. **짝지은 비교**를 쓴다. 두 팔이 같은 진입을 공유하므로 거래를 1:1 로 맞추면
   진입에서 오는 분산이 통째로 빠진다(필요 표본 1,421건 → 475건).
4. **자본을 밝힌다.** 총수익금만 보면 자본을 더 쓴 쪽이 항상 이긴다. 필요자금·
   총수익률·CAGR 을 함께 싣는다.
5. **표본이 모자라면 모자란다고 말한다.** 유의하지 않은 우위를 우위라고 하지 않는다.
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from typing import Any, Final, Sequence

import numpy as np
import pandas as pd

#: 국면 절단 조각 수.
REGIME_SEGMENTS: Final = 4

#: 유의 수준(양측)과 검정력 — 필요 표본 산출용.
Z_ALPHA: Final = 1.96
Z_POWER: Final = 0.84


@dataclass(frozen=True)
class Arm:
    """엔진에 올린 팔 하나 — 거래 기록과 자본 지표."""

    name: str
    trades: pd.DataFrame          # 매수시간·종목명·수익률·수익금
    seed_capital: float | None = None
    cagr: float | None = None
    mdd_pct: float | None = None
    total_profit_pct: float | None = None


def load_arm(db_path: str, table: str, name: str, **metrics: Any) -> Arm:
    """백테스트 결과 테이블 한 개를 팔로 읽는다."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        frame = pd.read_sql(f'SELECT 매수시간, 종목명, 수익률, 수익금 FROM "{table}"', con)
    finally:
        con.close()
    frame["일자"] = frame["매수시간"].astype(str).str[:8].astype(int)
    # 진입 하나를 가리키는 열쇠 — 같은 초에 같은 종목을 두 번 사지 않는다.
    frame["entry_key"] = frame["매수시간"].astype(str) + "|" + frame["종목명"].astype(str)
    return Arm(name=name, trades=frame.sort_values("매수시간").reset_index(drop=True),
               **metrics)


def regime_split(arm: Arm, *, segments: int = REGIME_SEGMENTS,
                 days: Sequence[int] | None = None) -> list[dict[str, Any]]:
    """거래일을 균등 분할해 구간별 건당 수익률을 낸다.

    `days` 를 주면 그 날짜 축으로 자른다 — 두 팔을 **같은 경계**로 갈라야 비교가
    성립한다(각자 자기 거래일로 자르면 경계가 어긋난다).
    """
    frame = arm.trades
    axis = sorted(set(days) if days is not None else set(frame["일자"]))
    if not axis:
        return []
    edges = np.linspace(0, len(axis), segments + 1).astype(int)
    out: list[dict[str, Any]] = []
    for index in range(segments):
        lo, hi = edges[index], min(edges[index + 1], len(axis)) - 1
        if hi < lo:
            continue
        start, end = axis[lo], axis[hi]
        part = frame[(frame["일자"] >= start) & (frame["일자"] <= end)]
        out.append({
            "segment": index + 1, "day_from": int(start), "day_to": int(end),
            "trades": int(len(part)),
            "mean_pct": float(part["수익률"].mean()) if len(part) else float("nan"),
            "profit_krw": float(part["수익금"].sum()) if len(part) else 0.0,
        })
    return out


def positive_segments(segments: Sequence[dict[str, Any]]) -> int:
    return sum(1 for s in segments if s["mean_pct"] > 0)


def paired_test(baseline: Arm, challenger: Arm) -> dict[str, Any]:
    """같은 진입을 공유하는 두 팔의 **짝지은** 비교.

    진입이 같으므로 거래를 1:1 로 맞추면 "어느 종목을 샀는가"에서 오는 분산이
    통째로 빠진다. 그래야 매도 규칙의 효과만 남는다.
    """
    merged = baseline.trades.merge(
        challenger.trades, on="entry_key", suffixes=("_base", "_chal"))
    n = len(merged)
    if n < 2:
        return {"available": False, "reason": "insufficient_paired_trades", "pairs": n}

    diff = (merged["수익률_chal"] - merged["수익률_base"]).to_numpy(dtype=float)
    money = (merged["수익금_chal"] - merged["수익금_base"]).to_numpy(dtype=float)
    mean = float(diff.mean())
    sd = float(diff.std(ddof=1))
    se = sd / math.sqrt(n)
    lo, hi = mean - Z_ALPHA * se, mean + Z_ALPHA * se
    # 이 크기의 차이를 확정하려면 표본이 몇 개 필요한가(검정력 80%).
    required = ((Z_ALPHA + Z_POWER) * sd / mean) ** 2 if mean else float("inf")

    return {
        "available": True,
        "pairs": n,
        "mean_diff_pct": mean,
        "sd": sd,
        "t_stat": mean / se if se else float("nan"),
        "ci95": [lo, hi],
        # 신뢰구간이 0 을 넘지 않을 때만 유의하다. 넘으면 "아직 모른다"가 정답이다.
        "significant": bool(lo > 0),
        "improved_trades": int((diff > 0).sum()),
        "worsened_trades": int((diff < 0).sum()),
        "unchanged_trades": int((diff == 0).sum()),
        "money_diff_krw": float(money.sum()),
        "required_pairs": float(required),
        "sample_shortfall_ratio": float(required / n) if required != float("inf") else None,
    }


def capital_view(baseline: Arm, challenger: Arm) -> dict[str, Any]:
    """자본을 감안한 대조 — 총액만 보면 자본을 더 쓴 쪽이 항상 이긴다."""
    def calmar(arm: Arm) -> float | None:
        if arm.cagr is None or not arm.mdd_pct:
            return None
        return float(arm.cagr) / float(arm.mdd_pct)

    rows = []
    for label, key, higher_better in (
        ("총수익금(원)", "profit", True),
        ("필요자금(원)", "seed_capital", False),
        ("총수익률(%)", "total_profit_pct", True),
        ("CAGR(%)", "cagr", True),
        ("MDD(%)", "mdd_pct", False),
        ("Calmar", "calmar", True),
    ):
        def pick(arm: Arm):
            if key == "profit":
                return float(arm.trades["수익금"].sum())
            if key == "calmar":
                return calmar(arm)
            return getattr(arm, key)

        base_value, chal_value = pick(baseline), pick(challenger)
        winner = None
        if base_value is not None and chal_value is not None:
            better = chal_value > base_value if higher_better else chal_value < base_value
            winner = challenger.name if better else baseline.name
        rows.append({"metric": label, "baseline": base_value,
                     "challenger": chal_value, "winner": winner})
    return {"rows": rows,
            "note": ("총수익금만 보면 자본을 더 쓴 쪽이 이긴다. 자본 대비 지표"
                     "(총수익률·CAGR)와 위험 대비 지표(Calmar)를 함께 읽는다.")}


def judge(baseline: Arm, challenger: Arm, *,
          segments: int = REGIME_SEGMENTS) -> dict[str, Any]:
    """챔피언을 합격선으로 삼아 도전자를 심판한다.

    절대 기준(예: 4/4 양수)을 쓰지 않는다 — 챔피언이 3/4 라면 3/4 가 합격선이다.
    """
    days = sorted(set(baseline.trades["일자"]) | set(challenger.trades["일자"]))
    base_segments = regime_split(baseline, segments=segments, days=days)
    chal_segments = regime_split(challenger, segments=segments, days=days)
    base_positive = positive_segments(base_segments)
    chal_positive = positive_segments(chal_segments)

    paired = paired_test(baseline, challenger)
    capital = capital_view(baseline, challenger)

    consistency_pass = chal_positive >= base_positive
    # 합격선이 챔피언이므로 **동률도 미달이 아니다**(`>` 가 아니라 `>=`).
    #   실측: `>` 로 두면 챔피언을 자기 자신과 비교했을 때 REJECT 가 나온다 —
    #   바로 이 라운드에서 고치려던 "챔피언도 떨어지는 기준"을 그대로 반복하는 셈이다.
    profit_pass = bool(paired.get("available")) and paired["mean_diff_pct"] >= 0
    proven = bool(paired.get("significant"))

    # **자본 대비**로도 챔피언 이상인가. 총수익률 = 총수익금 / 필요자금 이므로
    #   자본을 2배 쓰고 수익이 1.8배면 이 값이 떨어진다. 건당 수익률만 보면
    #   그 사실이 통째로 가려진다(실측: B1 은 건당 +0.06%p 인데 총수익률은 −36%p).
    base_tpp, chal_tpp = baseline.total_profit_pct, challenger.total_profit_pct
    capital_known = base_tpp is not None and chal_tpp is not None
    capital_pass = (not capital_known) or float(chal_tpp) >= float(base_tpp)

    if not (consistency_pass and profit_pass):
        verdict = "REJECT"
    elif not capital_pass:
        # 어떤 축은 낫고 어떤 축은 못하다 — 합격도 폐기도 아니고 **혼합**이다.
        #   사람이 무엇을 중시하는지(총수익률 vs 위험)에 따라 갈리므로 자동 판정하지 않는다.
        verdict = "MIXED"
    elif proven:
        verdict = "PASS"
    else:
        # 방향은 맞는데 표본이 얇다 — 폐기도 승격도 아니다.
        verdict = "PROMISING"

    return {
        "baseline": baseline.name,
        "challenger": challenger.name,
        "regime": {
            "segments": segments,
            "baseline_positive": base_positive,
            "challenger_positive": chal_positive,
            "baseline_segments": base_segments,
            "challenger_segments": chal_segments,
            "pass": consistency_pass,
            "note": ("합격선은 챔피언이다. 챔피언이 3/4 면 3/4 가 기준이며, "
                     "절대 4/4 를 요구하면 챔피언도 탈락한다."),
        },
        "paired": paired,
        "capital": capital,
        "capital_efficiency": {
            "baseline_total_profit_pct": base_tpp,
            "challenger_total_profit_pct": chal_tpp,
            "pass": capital_pass,
            "known": capital_known,
            "note": ("총수익률 = 총수익금 / 필요자금. 자본을 더 쓰고 총액만 늘린 후보는 "
                     "여기서 걸린다."),
        },
        "verdict": verdict,
        "verdict_meaning": {
            "PASS": "챔피언 이상이고 통계적으로도 확정됐다 — 사람 보고 대상.",
            "PROMISING": "챔피언 이상이지만 표본이 얇아 확정 못했다 — 표본을 늘려 재판정.",
            "MIXED": ("건당·일관성은 챔피언 이상이지만 **자본 대비 수익률이 낮다**. "
                      "무엇을 중시하는지에 따라 갈리므로 자동 판정하지 않는다."),
            "REJECT": "챔피언에 못 미친다 — 폐기.",
        }[verdict],
    }
