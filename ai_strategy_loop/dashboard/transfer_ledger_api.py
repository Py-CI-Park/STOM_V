"""전이율 누적 원장 API (페이지 12 강화) — 지도 추정 vs 엔진 실측.

배경(QSP10 계획서 §3의 미구현분 회수): 지도는 탐색용 추정이고 엔진이 심판이다.
그 둘의 비율(전이율)을 누적해야 "지도가 +0.35% 라 할 때 실제로는 얼마인가"를
사후가 아니라 **사전에** 읽을 수 있다. QSP12 실측 전이율은 0.10~0.34 였다.

핵심 계약:
  - 원장은 P5 실행기가 남긴 리포트(`_p5*_report.json`)를 읽어 만든다 — 별도
    입력이 없다(기록되지 않은 후보는 원장에 없다).
  - **전이율은 부호가 같을 때만 감쇠 계수로 쓴다.** 부호가 뒤집힌 건(예: 지도
    양수 → 엔진 음수)은 계수가 아니라 **경고**다. QSP12 1차가 −1.18 이었다.
  - 보수 계수 = 부호 일치 건들의 중앙값(평균은 이상치에 끌린다).
"""

from __future__ import annotations

import glob
import json
import os
import statistics
from typing import Any, Final

from fastapi import APIRouter

transfer_ledger_router = APIRouter()

_LABEL_ROOT: Final = os.path.join(os.path.dirname(__file__), "..", "state", "labels")

#: 계수를 신뢰하기 위한 최소 표본 — 이보다 적으면 '축적 중'으로 표시한다.
MIN_RECORDS_FOR_COEFFICIENT: Final = 3


def _reports() -> list[tuple[str, dict[str, Any]]]:
    """P5 실행기 리포트를 모은다. 없으면 빈 목록(조작하지 않는다)."""
    found: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(glob.glob(os.path.join(_LABEL_ROOT, "*", "_p5*_report.json"))):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError):
            continue
        if isinstance(payload, dict):
            found.append((path, payload))
    return found


def _record(lane: str, source: str, outcome: dict[str, Any]) -> dict[str, Any] | None:
    predicted = outcome.get("predicted") or {}
    engine = outcome.get("engine") or {}
    map_pct = predicted.get("expectancy_pct")
    engine_pct = engine.get("avg_profit_pct")
    if map_pct is None or engine_pct is None:
        return None

    ratio = outcome.get("transfer_ratio")
    if ratio is None and map_pct:
        ratio = float(engine_pct) / float(map_pct)
    sign_flip = bool(map_pct) and bool(engine_pct) and (float(map_pct) * float(engine_pct) < 0)

    return {
        "name": outcome.get("name"),
        "rule": outcome.get("rule"),
        "job_id": outcome.get("job_id"),
        "lane": lane,
        "source": os.path.basename(source),
        "map_expectancy_pct": float(map_pct),
        "engine_avg_profit_pct": float(engine_pct),
        "map_trades": predicted.get("rows"),
        "engine_trades": engine.get("trade_count"),
        "trade_ratio": (float(engine["trade_count"]) / float(predicted["rows"]))
                       if predicted.get("rows") and engine.get("trade_count") else None,
        "transfer_ratio": float(ratio) if ratio is not None else None,
        # 부호 반전은 감쇠가 아니라 구조 불일치 신호다(진입 단위 결함이 그랬다).
        "sign_flip": sign_flip,
        "engine_total_profit_krw": engine.get("total_profit_krw"),
        "engine_cagr": engine.get("cagr"),
        "engine_mdd_pct": engine.get("mdd_pct"),
    }


@transfer_ledger_router.get("/bt/transfer-ledger")
def transfer_ledger() -> dict[str, Any]:
    """누적 원장 + 보수 계수. 기록이 없으면 정직하게 비어 있다고 답한다."""
    records: list[dict[str, Any]] = []
    for path, payload in _reports():
        lane = str(payload.get("lane") or "")
        outcomes = payload.get("outcomes")
        if not isinstance(outcomes, list):
            continue
        for outcome in outcomes:
            if not isinstance(outcome, dict):
                continue
            row = _record(lane, path, outcome)
            if row is not None:
                records.append(row)

    aligned = [r["transfer_ratio"] for r in records
               if r["transfer_ratio"] is not None and not r["sign_flip"] and r["transfer_ratio"] > 0]
    flips = [r for r in records if r["sign_flip"]]

    coefficient = statistics.median(aligned) if aligned else None
    return {
        "available": bool(records),
        "authority": "diagnostic",
        "records": records,
        "record_count": len(records),
        "sign_flip_count": len(flips),
        "aligned_count": len(aligned),
        "minimum_for_coefficient": MIN_RECORDS_FOR_COEFFICIENT,
        "status": "ready" if len(aligned) >= MIN_RECORDS_FOR_COEFFICIENT else "accumulating",
        # 보수 계수 — 부호 일치 건의 중앙값. 평균은 이상치에 끌리므로 쓰지 않는다.
        "conservative_coefficient": coefficient,
        "coefficient_basis": "median of sign-aligned transfer ratios",
        "note": ("전이율은 부호가 같을 때만 감쇠 계수다. 부호 반전 건은 계수가 아니라 "
                 "구조 불일치 경고로 읽는다(QSP12 진입 단위 결함이 −1.18 이었다)."),
    }


@transfer_ledger_router.get("/bt/transfer-ledger/estimate")
def transfer_estimate(map_expectancy_pct: float) -> dict[str, Any]:
    """지도 추정치를 원장 계수로 환산한다 — '엔진에서 얼마쯤 나올까'의 사전 답."""
    ledger = transfer_ledger()
    coefficient = ledger.get("conservative_coefficient")
    # 표본 미달 계수는 내주지 않는다 — 1~2건에서 나온 비율을 예측에 쓰면
    #   "계수가 있다"는 사실만으로 근거 없는 확신이 생긴다(원장의 존재 이유와 반대).
    if coefficient is None or ledger.get("status") != "ready":
        return {"available": False, "reason": "insufficient_records",
                "minimum_for_coefficient": MIN_RECORDS_FOR_COEFFICIENT,
                "aligned_count": ledger.get("aligned_count", 0),
                "record_count": ledger.get("record_count", 0)}
    return {
        "available": True,
        "authority": "diagnostic",
        "map_expectancy_pct": map_expectancy_pct,
        "coefficient": coefficient,
        "engine_estimate_pct": map_expectancy_pct * coefficient,
        "status": ledger["status"],
        "note": "추정일 뿐이며 공식 판정은 엔진 실측에서만 한다.",
    }
