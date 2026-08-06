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


#: 무엇을 바꿔 가며 잰 전이율인가 — 이 축이 다르면 계수를 섞으면 안 된다.
#:
#: 실측(2026-08-06): 진입까지 바꾼 후보는 전이율 0.105~0.343(지도가 과대평가),
#: 진입을 고정하고 청산만 바꾼 후보는 2.25~4.22(지도가 **과소**평가)로 나왔다.
#: 둘의 중앙값 하나를 "보수 계수"라고 부르면 어느 쪽에도 맞지 않는다.
AXIS_EXIT_ONLY: Final = "exit_only"
AXIS_ENTRY_AND_EXIT: Final = "entry_and_exit"


def _axis(outcome: dict[str, Any]) -> str:
    """이 기록이 무엇을 바꿔 가며 잰 것인가.

    진입 고정 A/B 러너(`run_engine_measure`)는 `arm` 을 남긴다. 그 표식이 없으면
    진입까지 함께 바뀐 후보다(QSP10 P5 계열).
    """
    return AXIS_EXIT_ONLY if outcome.get("arm") else AXIS_ENTRY_AND_EXIT


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
        "axis": _axis(outcome),
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

    def _aligned(rows: list[dict[str, Any]]) -> list[float]:
        return [r["transfer_ratio"] for r in rows
                if r["transfer_ratio"] is not None and not r["sign_flip"]
                and r["transfer_ratio"] > 0]

    aligned = _aligned(records)
    flips = [r for r in records if r["sign_flip"]]

    # 축별 계수 — 진입까지 바꾼 기록과 청산만 바꾼 기록을 섞지 않는다.
    by_axis: dict[str, dict[str, Any]] = {}
    for axis in (AXIS_EXIT_ONLY, AXIS_ENTRY_AND_EXIT):
        rows = [r for r in records if r["axis"] == axis]
        values = _aligned(rows)
        by_axis[axis] = {
            "record_count": len(rows),
            "aligned_count": len(values),
            "coefficient": statistics.median(values) if values else None,
            "status": "ready" if len(values) >= MIN_RECORDS_FOR_COEFFICIENT else "accumulating",
        }

    coefficient = statistics.median(aligned) if aligned else None
    # 두 축이 모두 표본을 가지면 섞인 계수는 어느 쪽에도 맞지 않는다.
    mixed = all(by_axis[a]["aligned_count"] > 0 for a in by_axis)
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
        "by_axis": by_axis,
        "axis_mixed": mixed,
        "note": ("전이율은 부호가 같을 때만 감쇠 계수다. 부호 반전 건은 계수가 아니라 "
                 "구조 불일치 경고로 읽는다(QSP12 진입 단위 결함이 −1.18 이었다)."),
        "axis_note": ("진입까지 바꾼 후보(0.105~0.343)와 진입 고정·청산만 바꾼 후보"
                      "(2.25~4.22)는 전이 방향이 반대다. 섞은 중앙값은 어느 쪽에도 "
                      "맞지 않으므로 축을 골라 읽는다."),
    }


@transfer_ledger_router.get("/bt/transfer-ledger/estimate")
def transfer_estimate(map_expectancy_pct: float, axis: str = "") -> dict[str, Any]:
    """지도 추정치를 원장 계수로 환산한다 — '엔진에서 얼마쯤 나올까'의 사전 답.

    `axis` 를 주면 그 축의 계수만 쓴다. 안 주면 섞인 계수를 쓰되, 두 축이 모두
    표본을 가지고 있으면 **섞였다는 사실을 함께 돌려준다** — 조용히 섞인 값을
    내주면 그 값이 어느 쪽에도 안 맞는다는 것을 아무도 모른다.
    """
    ledger = transfer_ledger()
    if axis:
        bucket = (ledger.get("by_axis") or {}).get(axis)
        if bucket is None:
            return {"available": False, "reason": "unknown_axis", "axis": axis}
        if bucket["coefficient"] is None or bucket["status"] != "ready":
            return {"available": False, "reason": "insufficient_records", "axis": axis,
                    "minimum_for_coefficient": MIN_RECORDS_FOR_COEFFICIENT,
                    "aligned_count": bucket["aligned_count"],
                    "record_count": bucket["record_count"]}
        return {
            "available": True, "authority": "diagnostic", "axis": axis,
            "map_expectancy_pct": map_expectancy_pct,
            "coefficient": bucket["coefficient"],
            "engine_estimate_pct": map_expectancy_pct * bucket["coefficient"],
            "status": bucket["status"], "axis_mixed": False,
            "note": "추정일 뿐이며 공식 판정은 엔진 실측에서만 한다.",
        }

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
        "axis_mixed": ledger.get("axis_mixed", False),
        "by_axis": ledger.get("by_axis"),
        "note": "추정일 뿐이며 공식 판정은 엔진 실측에서만 한다.",
    }
