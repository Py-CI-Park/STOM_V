"""C8/N1 (2026-06-11) — 체결가능성(fill-feasibility) advisory: 추격 체결 의존도.

슬리피지 도구(V5)는 '가격'만 불리하게 조정한다 — 시초 변동성 구간의 진짜
위험은 "그 가격에 체결 자체가 안 되는 것"이다. 추가 백테 없이 per-trade
CSV의 `R_매수후최저수익률`로 근사한다:

  매수후최저수익률 >= 0  →  진입 후 가격이 매수가 이하로 한 번도 안 돌아옴
    = 지정가(매수가)로는 잔량 소진 시 미체결 가능성이 큰 **추격 체결 의존 거래**.
  매수후최저수익률 < 0   →  매수가 이하 재방문 — 지정가 체결 개연성이 높음.

fragile_profit_share(추격 의존 거래의 수익 비중)가 높을수록 백테 수익이
체결 낙관 가정에 기대고 있다는 뜻이다. advisory 전용 — 판정 미사용.
근사의 한계(틱 내 큐 위치·잔량은 모름)는 결과에 명시한다.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

REQUIRED = ("수익금", "R_매수후최저수익률")


def fill_fragility(csv_path: str, epsilon: float = 0.0) -> Optional[Dict[str, object]]:
    """추격 체결 의존 거래의 건수/수익 비중. 컬럼 부재·실패는 None.

    epsilon: 최저수익률이 이 값(%) 이상이면 '재방문 없음'으로 본다(기본 0).
    """
    try:
        import pandas as pd  # noqa: PLC0415

        path = Path(csv_path)
        if not path.is_file():
            return None
        df = pd.read_csv(path, encoding="utf-8-sig")
        if any(c not in df.columns for c in REQUIRED):
            return None
        low = df["R_매수후최저수익률"].astype(float)
        profit = df["수익금"].astype(float)
        fragile = low >= epsilon
        n = len(df)
        if n == 0:
            return None
        total_profit = float(profit.sum())
        fragile_profit = float(profit[fragile].sum())
        return {
            "n_trades": n,
            "fragile_trades": int(fragile.sum()),
            "fragile_trade_ratio": round(float(fragile.sum()) / n, 4),
            "total_profit": total_profit,
            "fragile_profit": fragile_profit,
            "fragile_profit_share": (
                round(fragile_profit / total_profit, 4) if total_profit else None
            ),
            "robust_profit": round(total_profit - fragile_profit, 2),
            "note": (
                "근사 — 매수가 이하 재방문 여부만 본다(틱 내 큐 위치·호가 잔량은"
                " 미관측). fragile 비중이 높으면 지정가 운용 시 수익이 줄고"
                " 시장가 운용 시 슬리피지(V5)가 커진다. advisory 전용"
            ),
        }
    except Exception:  # noqa: BLE001 - advisory.
        return None
