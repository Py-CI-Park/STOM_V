"""M10 (2026-06-11) — 일중 서킷브레이커 반사실 검증 (백테 0회, advisory).

운용 규칙 "당일 손실 거래 N건 도달 시 당일 잔여 거래 중단"을 기존 per-trade
CSV 재계산만으로 사전 평가한다(반사실 필터 도구와 같은 패턴). 시간 순서를
보존하므로 경로의존이 없다 — 제거되는 건 항상 '그날의 나중 거래'뿐이다.

주의(정직): 이 반사실은 인샘플이다. 채택하려면 운용 규칙으로 사전선언 후
OOS/실측에서 재확인해야 한다. 어떤 게이트/선택도 바꾸지 않는다.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional


def daily_stop_counterfactual(csv_path: str, max_daily_losses: int) -> Optional[Dict[str, object]]:
    """손실 N건 도달 시 당일 중단 규칙의 반사실 손익. 실패는 None."""
    if max_daily_losses < 1:
        return None
    try:
        import pandas as pd  # noqa: PLC0415

        path = Path(csv_path)
        if not path.is_file():
            return None
        df = pd.read_csv(path, encoding="utf-8-sig")
        if "매수시간" not in df.columns or "수익금" not in df.columns:
            return None
        df = df.sort_values("매수시간")
        df["_day"] = df["매수시간"].astype(str).str[:8]

        kept_profit, removed, days_triggered = 0.0, 0, 0
        for _day, g in df.groupby("_day", sort=True):
            losses = 0
            stopped = False
            for profit in g["수익금"].astype(float):
                if stopped:
                    removed += 1
                    continue
                kept_profit += profit
                if profit < 0:
                    losses += 1
                    if losses >= max_daily_losses:
                        stopped = True
            if stopped:
                days_triggered += 1
        base_profit = float(df["수익금"].sum())
        return {
            "rule": f"당일 손실 {max_daily_losses}건 도달 시 잔여 거래 중단",
            "base_profit": base_profit,
            "kept_profit": round(kept_profit, 2),
            "profit_ratio": round(kept_profit / base_profit, 4) if base_profit else None,
            "trades_removed": removed,
            "days_triggered": days_triggered,
            "note": "인샘플 반사실 advisory — 채택 시 사전선언 후 OOS 재확인 필수",
        }
    except Exception:  # noqa: BLE001 - advisory.
        return None


def suggest_daily_stop(csv_path: str, candidates=(2, 3, 4, 5)) -> List[Dict[str, object]]:
    """총손익이 깎이지 않는(profit_ratio >= 1.0) 중단 규칙만 제안한다."""
    out = []
    for n in candidates:
        r = daily_stop_counterfactual(csv_path, n)
        if r and r.get("profit_ratio") is not None and r["profit_ratio"] >= 1.0:
            out.append(r)
    return sorted(out, key=lambda r: -(r.get("profit_ratio") or 0.0))
