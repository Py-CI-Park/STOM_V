"""M11 (2026-06-11) — MC 분포 기반 포지션 사이징 advisory.

같은 조건식도 사이징이 파산/복리를 가른다. 블록 부트스트랩 MC의 MDD 분포
(p95 — 비관 시나리오)를 사용자의 감내 가능 낙폭 금액에 맞춰 베팅 배수를
역산한다. 선형 가정(베팅 k배 → 손익·낙폭 k배)이며, 슬리피지는 주문 크기에
비선형이므로(M3 용량 분석 전까지) 상향 권고는 보수적으로 절반만 반영한다.
판정 미사용 — 운용 결정 참고용.
"""
from __future__ import annotations

from typing import Dict, Optional


def sizing_advisory(
    mc: Dict[str, object], current_betting: float, max_dd_amount: float
) -> Optional[Dict[str, object]]:
    """베팅 배수 권고. mc는 block_bootstrap_daily 결과(mdd_p95 필요).

    scale = 감내 낙폭 / MDD p95. scale > 1(상향 여지)은 절반만 반영
    (슬리피지 비선형 보수성), scale < 1(축소 필요)은 그대로 반영.
    """
    try:
        mdd_p95 = float(mc.get("mdd_p95") or 0.0)
        if mdd_p95 <= 0 or current_betting <= 0 or max_dd_amount <= 0:
            return None
        scale = max_dd_amount / mdd_p95
        applied = 1.0 + (scale - 1.0) * 0.5 if scale > 1.0 else scale
        return {
            "mdd_p95": mdd_p95,
            "max_acceptable_dd": float(max_dd_amount),
            "raw_scale": round(scale, 3),
            "applied_scale": round(applied, 3),
            "current_betting": float(current_betting),
            "recommended_betting": round(current_betting * applied, 1),
            "note": (
                "선형 가정 + 상향분 50% 보수 반영 — 슬리피지는 주문 크기에"
                " 비선형(M3 용량 분석 전). advisory 전용, 판정 미사용"
            ),
        }
    except Exception:  # noqa: BLE001 - advisory.
        return None
