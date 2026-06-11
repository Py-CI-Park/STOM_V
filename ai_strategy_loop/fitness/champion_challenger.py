"""M4 (2026-06-11) — 챔피언-챌린저 운용 모니터링 (advisory).

프로세스가 V6 결정에서 끝나는 갭을 메운다: 승격 이후에도 챔피언(운용 중)과
챌린저(후보/구 시드)를 같은 데이터로 계속 동시 측정하고, **알파 감쇠를
월 단위로 감지**한다. 알파 감쇠는 근본 원인 보고서의 5번 원인이었으나
지금까지 감지 체계가 없었다.

사전선언 경보 규칙:
  - champion_decay: 챔피언이 연속 N개월(기본 2) 적자.
  - challenger_dominance: 챌린저가 연속 N개월(기본 2) 우세(월 손익 기준).
경보는 운용 결정(재검토/강등)의 트리거 제안일 뿐 자동 조치는 없다.
"""
from __future__ import annotations

from typing import Dict, List, Optional


def _monthly(daily: Dict[str, float]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for day, pnl in daily.items():
        key = str(day)[:6]
        out[key] = out.get(key, 0.0) + float(pnl)
    return out


def championship_report(
    champion_daily: Dict[str, float],
    challenger_daily: Dict[str, float],
    consecutive_alert: int = 2,
) -> Optional[Dict[str, object]]:
    """월별 동시 비교표 + 감쇠/역전 경보. 공통 월 2개 미만이면 None."""
    champ_m, chall_m = _monthly(champion_daily), _monthly(challenger_daily)
    months = sorted(set(champ_m) | set(chall_m))
    if len(months) < 2:
        return None
    rows: List[Dict[str, object]] = []
    champ_neg_streak = chall_win_streak = 0
    max_champ_neg = max_chall_win = 0
    for m in months:
        c = champ_m.get(m, 0.0)
        h = chall_m.get(m, 0.0)
        champ_neg_streak = champ_neg_streak + 1 if c < 0 else 0
        chall_win_streak = chall_win_streak + 1 if h > c else 0
        max_champ_neg = max(max_champ_neg, champ_neg_streak)
        max_chall_win = max(max_chall_win, chall_win_streak)
        rows.append({"month": m, "champion": round(c), "challenger": round(h),
                     "winner": "challenger" if h > c else "champion"})
    alerts: List[str] = []
    if champ_neg_streak >= consecutive_alert:
        alerts.append(
            f"champion_decay: 챔피언 연속 {champ_neg_streak}개월 적자 — 재검토 트리거"
        )
    if chall_win_streak >= consecutive_alert:
        alerts.append(
            f"challenger_dominance: 챌린저 연속 {chall_win_streak}개월 우세 — 교대 검토 트리거"
        )
    return {
        "months": rows,
        "champion_total": round(sum(champ_m.values())),
        "challenger_total": round(sum(chall_m.values())),
        "max_champion_negative_streak": max_champ_neg,
        "max_challenger_win_streak": max_chall_win,
        "alerts": alerts,
        "note": "advisory — 경보는 운용 재검토 트리거 제안일 뿐 자동 조치 없음",
    }
