"""거래 짝 뷰어 — 짝지은 검정의 **개별 거래**를 열어 본다.

## 왜 필요한가

짝지은 검정은 "+0.1587%p [−0.111, +0.428]" 같은 한 줄을 준다. 그 한 줄로는
**왜** 그런지 알 수 없다. W7 에서 실제로 막힌 지점이 그것이다:

> 시간손절을 넣으면 자본은 돌지만 건당 우위가 깎인다. 그 규칙이 자르는 거래에
> "되살아났을 거래"가 섞여 있다 — 고 추측했지만, 그 거래를 직접 본 적은 없다.

이 모듈이 그 거래를 꺼낸다. 같은 진입을 1:1 로 맞췄으므로 **차이는 순수하게
매도 규칙의 결과**다.

## 무엇을 내는가

| 층 | 내용 |
|---|---|
| 요약 | 개선/악화/동일 건수 · 차이 분포 · 기여 상위 |
| 청산 사유 | 어느 매도조건이 개선을 만들고 어느 것이 악화를 만드는가 |
| 개별 거래 | 종목·시각·보유시간·양쪽 수익률과 그 차이 |

## 규율

- **같은 진입만 짝짓는다.** 한쪽에만 있는 거래는 짝이 아니므로 따로 센다.
- 총합이 아니라 **분포**를 본다. 평균 하나로는 꼬리가 안 보인다.
"""

from __future__ import annotations

from typing import Any, Final

import numpy as np
import pandas as pd

#: 진입 하나를 가리키는 열쇠 — engine_ladder 와 같은 규약이어야 한다.
ENTRY_KEY: Final = ("매수시간", "종목명")

#: 화면에 한 번에 내보낼 거래 수 상한 — 300건을 다 뿌리면 아무도 안 읽는다.
DEFAULT_LIMIT: Final = 25


def entry_key(frame: pd.DataFrame) -> pd.Series:
    return frame[ENTRY_KEY[0]].astype(str) + "|" + frame[ENTRY_KEY[1]].astype(str)


def pair(base: pd.DataFrame, chal: pd.DataFrame) -> pd.DataFrame:
    """같은 진입끼리 1:1 로 맞춘다."""
    a, b = base.copy(), chal.copy()
    a["entry_key"], b["entry_key"] = entry_key(a), entry_key(b)
    merged = a.merge(b, on="entry_key", suffixes=("_base", "_chal"))
    merged["diff_pct"] = merged["수익률_chal"] - merged["수익률_base"]
    merged["diff_krw"] = merged["수익금_chal"] - merged["수익금_base"]
    merged["hold_diff"] = merged["보유시간_chal"] - merged["보유시간_base"]
    return merged.sort_values("diff_pct").reset_index(drop=True)


def _rows(merged: pd.DataFrame, index: Any) -> list[dict[str, Any]]:
    out = []
    for _, r in merged.loc[index].iterrows():
        out.append({
            "종목명": str(r["종목명_base"]),
            "매수시간": str(r["매수시간_base"]),
            "기준_수익률": float(r["수익률_base"]),
            "후보_수익률": float(r["수익률_chal"]),
            "차이": float(r["diff_pct"]),
            "차이금액": float(r["diff_krw"]),
            "기준_보유": float(r["보유시간_base"]),
            "후보_보유": float(r["보유시간_chal"]),
            "보유차": float(r["hold_diff"]),
            "기준_매도조건": str(r.get("매도조건_base", "")),
            "후보_매도조건": str(r.get("매도조건_chal", "")),
        })
    return out


def exit_reason_breakdown(merged: pd.DataFrame) -> list[dict[str, Any]]:
    """후보의 청산 사유별로 개선/악화가 어떻게 갈리는가.

    "이 규칙이 어디서 이기고 어디서 지는가"에 직접 답하는 표다.
    """
    if "매도조건_chal" not in merged.columns:
        return []
    rows = []
    for reason, part in merged.groupby(merged["매도조건_chal"].astype(str)):
        rows.append({
            "매도조건": reason,
            "건수": int(len(part)),
            "평균차이": float(part["diff_pct"].mean()),
            "합계차이": float(part["diff_pct"].sum()),
            "개선": int((part["diff_pct"] > 0).sum()),
            "악화": int((part["diff_pct"] < 0).sum()),
        })
    rows.sort(key=lambda r: r["합계차이"])
    return rows


def analyze(base: pd.DataFrame, chal: pd.DataFrame, *,
            limit: int = DEFAULT_LIMIT) -> dict[str, Any]:
    """짝지은 거래 한 장 — 요약 + 청산 사유 + 최악/최선 개별 거래."""
    merged = pair(base, chal)
    n = len(merged)
    if n == 0:
        return {"available": False, "reason": "짝지어지는 거래가 없다",
                "baseline_only": int(len(base)), "challenger_only": int(len(chal))}

    diff = merged["diff_pct"].to_numpy(dtype=float)
    worse = merged.index[:limit]
    better = merged.index[::-1][:limit]
    # 합계 차이에서 상위 몇 건이 차지하는 비중 — 꼬리가 결과를 지배하는지 본다.
    order = np.argsort(np.abs(diff))[::-1]
    top10 = float(np.abs(diff[order[:10]]).sum())
    total_abs = float(np.abs(diff).sum())

    return {
        "available": True,
        "pairs": n,
        "baseline_only": int(len(base) - n),
        "challenger_only": int(len(chal) - n),
        "improved": int((diff > 0).sum()),
        "worsened": int((diff < 0).sum()),
        "unchanged": int((diff == 0).sum()),
        "mean_diff_pct": float(diff.mean()),
        "median_diff_pct": float(np.median(diff)),
        "sum_diff_pct": float(diff.sum()),
        "hold_diff_mean": float(merged["hold_diff"].mean()),
        # 상위 10건이 절대 차이의 이만큼을 차지한다 — 1에 가까우면 꼬리가 지배한다.
        "top10_share": (top10 / total_abs) if total_abs else None,
        "exit_reasons": exit_reason_breakdown(merged),
        "worst": _rows(merged, worse),
        "best": _rows(merged, better),
        "note": ("같은 진입을 1:1 로 맞췄으므로 차이는 순수하게 매도 규칙의 결과다. "
                 "한쪽에만 있는 거래는 짝이 아니라 따로 센다."),
    }
