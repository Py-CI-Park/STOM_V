"""매도 축 종합 API (페이지 28) — 지도·워크포워드·엔진을 **한 자로** 읽는다.

배경: W3/W4 에서 같은 규칙이 세 곳에서 다른 숫자로 나온다.

  · 재현 게이트   — 챔피언 진입 위 지도 기대값 (건당 %)
  · 워크포워드    — 표본 밖 일평균 (일평균 %)
  · 엔진 실측     — 자본 경로·체결까지 반영한 심판값 (건당 %)

세 값이 다른 것은 잘못이 아니라 **자가 다른 것**이다. 그런데 화면이 없으면
사람도 AI 도 세 숫자를 머릿속에서 섞어 읽는다 — QSP10~13 이 반복해서 당한
"지도에서 좋았는데 엔진에서 뒤집혔다"가 바로 그 혼동에서 왔다.

이 API 는 세 출처를 규칙 이름으로 **조인**해서, 같은 규칙의 세 숫자를 한 줄에
놓는다. 값을 만들지 않는다 — 없는 것은 없다고 답한다.

판독 규율(응답에 그대로 실어 보낸다):
  · 상한(upper_bound) 셀은 미래를 참조한다 → **천장**으로만 읽는다.
  · 지도와 엔진의 단위가 다르면(건당 vs 일평균) 나란히 놓되 나눗셈하지 않는다.
  · 엔진이 없으면 전이율도 없다. 추정치를 채워 넣지 않는다.
"""

from __future__ import annotations

import json
import os
from typing import Any, Final

from fastapi import APIRouter

exit_axis_router = APIRouter()

_LABEL_ROOT: Final = os.path.join(os.path.dirname(__file__), "..", "state", "labels")

#: 판정 근거가 되는 정확도 등급 — 상한은 제외한다(헌법 5항).
JUDGEABLE: Final = ("exact", "lower_bound")

_GATE: Final = "_reproduction_gate.json"
_WALKFORWARD: Final = "_exit_walkforward.json"
_ENGINE: Final = "_p5_engine_report.json"
_LADDER_GLOB: Final = "_exit_ladder_*.json"
_ENGINE_LADDER: Final = "_engine_ladder.json"


def _read(out_name: str, filename: str) -> dict[str, Any] | None:
    path = os.path.join(_LABEL_ROOT, out_name, filename)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _engine_by_rule(engine: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """엔진 리포트를 규칙 이름으로 색인한다. 기준선은 규칙 축이 아니라 따로 뺀다."""
    if not engine:
        return {}
    indexed: dict[str, dict[str, Any]] = {}
    for outcome in engine.get("outcomes") or []:
        if not isinstance(outcome, dict) or outcome.get("arm") == "baseline":
            continue
        rule = outcome.get("rule")
        if rule:
            indexed[str(rule)] = outcome
    return indexed


def _ladders(out_name: str) -> dict[str, dict[str, Any]]:
    """규칙 이름 → 사다리 판정.

    사다리는 엔진 승격 **전에** 거르는 단계다. 엔진 수치가 좋아도 사다리가 FAIL
    이면 승격 대상이 아니므로, 표에서 엔진 값 옆에 나란히 보여야 한다
    (실측 2026-08-07: 엔진 A/B 3종 전부 통과했는데 국면 절단에서 전부 탈락).
    """
    import glob  # noqa: PLC0415

    found: dict[str, dict[str, Any]] = {}
    pattern = os.path.join(_LABEL_ROOT, out_name, _LADDER_GLOB)
    for path in sorted(glob.glob(pattern)):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError):
            continue
        rule = (payload or {}).get("rule")
        if rule:
            found[str(rule)] = payload
    return found


def _engine_ladders(out_name: str) -> dict[str, dict[str, Any]]:
    """규칙 이름 → 엔진 축 사다리 판정 (`run_engine_ladder` 산출).

    **지도 축 사다리보다 이쪽이 우선한다.** 지도는 엔진이 체결하지 않는 진입까지
    세기 때문에 국면 판정이 어긋난다(2026-08-07 정정: 지도 2/4 vs 엔진 4/4).
    """
    payload = _read(out_name, _ENGINE_LADDER)
    if not payload:
        return {}
    return {str(r.get("challenger")): r for r in payload.get("results") or []
            if r.get("challenger")}


def _chosen_counts(walkforward: dict[str, Any] | None) -> dict[str, int]:
    """폴드가 각 규칙을 몇 번 골랐는가 — 안정성의 가장 단순한 지표."""
    counts: dict[str, int] = {}
    for fold in (walkforward or {}).get("folds") or []:
        chosen = fold.get("chosen")
        if chosen:
            counts[str(chosen)] = counts.get(str(chosen), 0) + 1
    return counts


@exit_axis_router.get("/bt/exit-axis")
def exit_axis(out_name: str = "design_v4") -> dict[str, Any]:
    """세 출처를 규칙 이름으로 조인한 종합 표."""
    gate = _read(out_name, _GATE)
    walkforward = _read(out_name, _WALKFORWARD)
    engine = _read(out_name, _ENGINE)

    engine_rules = _engine_by_rule(engine)
    chosen = _chosen_counts(walkforward)
    ladders = _ladders(out_name)
    engine_ladders = _engine_ladders(out_name)
    reproducing = set((gate or {}).get("reproducing") or [])

    rows: list[dict[str, Any]] = []
    for cell in (gate or {}).get("cells") or []:
        if not isinstance(cell, dict):
            continue
        rule = str(cell.get("rule") or "")
        engine_row = engine_rules.get(rule)
        engine_metrics = (engine_row or {}).get("engine") or {}
        ladder = ladders.get(rule)
        engine_ladder = engine_ladders.get(rule)
        paired = (engine_ladder or {}).get("paired") or {}
        engine_regime = (engine_ladder or {}).get("regime") or {}
        rows.append({
            # ── 엔진 축 판정(정본). 지도 축보다 이쪽을 먼저 읽는다.
            "engine_ladder_verdict": (engine_ladder or {}).get("verdict"),
            "engine_ladder_meaning": (engine_ladder or {}).get("verdict_meaning"),
            "engine_regime_positive": engine_regime.get("challenger_positive"),
            "engine_regime_baseline": engine_regime.get("baseline_positive"),
            "engine_regime_segments": engine_regime.get("challenger_segments"),
            "paired_mean_diff_pct": paired.get("mean_diff_pct"),
            "paired_ci95": paired.get("ci95"),
            "paired_significant": paired.get("significant"),
            "paired_pairs": paired.get("pairs"),
            "paired_required_pairs": paired.get("required_pairs"),
            "paired_improved": paired.get("improved_trades"),
            "paired_worsened": paired.get("worsened_trades"),
            # 사다리 — 엔진보다 **앞선** 관문이다. FAIL 이면 엔진 수치와 무관하게
            #   승격 대상이 아니다.
            "ladder_verdict": (ladder or {}).get("verdict"),
            "ladder_rungs": {
                "plateau": ((ladder or {}).get("plateau") or {}).get("verdict"),
                "cost_stress": ((ladder or {}).get("cost_stress") or {}).get("verdict"),
                "regime": ((ladder or {}).get("regime") or {}).get("verdict"),
            } if ladder else None,
            "ladder_regime_segments": ((ladder or {}).get("regime") or {}).get("segments"),
            "rule": rule,
            "family": cell.get("family"),
            "exactness": cell.get("exactness"),
            "judgeable": cell.get("exactness") in JUDGEABLE,
            "reproduces_champion": rule in reproducing,
            # 지도 축 — 챔피언 진입 위에서 잰 값.
            "map_expectancy_pct": cell.get("expectancy_pct"),
            "map_day_mean_pct": cell.get("day_mean_pct"),
            "map_day_positive_ratio": cell.get("day_positive_ratio"),
            "map_n": cell.get("n"),
            # 워크포워드 축 — 폴드가 이 규칙을 몇 번 골랐나.
            "walkforward_chosen_count": chosen.get(rule, 0),
            # 엔진 축 — 없으면 없다고 답한다.
            "engine_avg_profit_pct": engine_metrics.get("avg_profit_pct"),
            "engine_trades": engine_metrics.get("trade_count"),
            "engine_cagr": engine_metrics.get("cagr"),
            "engine_mdd_pct": engine_metrics.get("mdd_pct"),
            "transfer_ratio": (engine_row or {}).get("transfer_ratio"),
            "engine_job_id": (engine_row or {}).get("job_id"),
        })

    rows.sort(key=lambda r: (r["map_expectancy_pct"] is None, -(r["map_expectancy_pct"] or 0)))

    baseline = next(
        (o for o in (engine or {}).get("outcomes") or []
         if isinstance(o, dict) and o.get("arm") == "baseline"),
        None,
    )
    # 도전자 대비 기준선 — 같은 런에서 잰 값끼리만 뺀다(다른 런은 비교가 아니다).
    base_pct = ((baseline or {}).get("engine") or {}).get("avg_profit_pct")
    for row in rows:
        engine_pct = row["engine_avg_profit_pct"]
        row["engine_delta_vs_baseline_pct"] = (
            float(engine_pct) - float(base_pct)
            if engine_pct is not None and base_pct is not None else None
        )

    return {
        "available": bool(rows),
        "authority": "diagnostic",
        "out_name": out_name,
        "sources": {
            "reproduction_gate": gate is not None,
            "walkforward": walkforward is not None,
            "engine": engine is not None,
            "ladder": bool(ladders),
            "engine_ladder": bool(engine_ladders),
        },
        "gate": {
            "verdict": (gate or {}).get("verdict"),
            "entry_seconds": (gate or {}).get("entry_seconds"),
            "entry_positions": (gate or {}).get("entry_positions"),
            "champion_engine": (gate or {}).get("champion_engine"),
            "reproduction_ratio": (gate or {}).get("reproduction_ratio"),
        } if gate else None,
        "walkforward": {
            "verdict": walkforward.get("verdict"),
            "candidates": walkforward.get("candidates"),
            "folds": walkforward.get("folds"),
            "mean_valid_day_mean_pct": walkforward.get("mean_valid_day_mean_pct"),
            "positive_folds": walkforward.get("positive_folds"),
            "mean_train_valid_gap_pct": walkforward.get("mean_train_valid_gap_pct"),
            "selection_bias_pct_large_scale": walkforward.get("selection_bias_pct_large_scale"),
        } if walkforward else None,
        "engine_baseline": {
            "rule": (baseline or {}).get("rule"),
            "job_id": (baseline or {}).get("job_id"),
            "design": (engine or {}).get("design"),
            **(((baseline or {}).get("engine")) or {}),
        } if baseline else None,
        "rows": rows,
        "reading_rules": [
            "상한(upper_bound) 셀은 미래를 참조합니다 — 천장으로만 읽습니다.",
            "지도는 건당 %, 워크포워드는 일평균 % 입니다. 나란히 두되 나누지 않습니다.",
            "엔진 값이 없으면 전이율도 없습니다 — 추정치를 채우지 않습니다.",
            "기준선 대비 Δ는 같은 런에서 잰 값끼리만 뺍니다.",
            "사다리는 **엔진 축**을 봅니다. 지도 축 사다리는 엔진이 체결하지 않는 "
            "진입까지 세어 국면 판정이 어긋납니다(2026-08-07 정정: 지도 2/4 vs 엔진 4/4).",
            "합격선은 절대 기준이 아니라 **챔피언**입니다. 챔피언이 3/4 면 3/4 가 "
            "기준이며, 4/4 를 요구하면 챔피언도 탈락합니다.",
            "PROMISING 은 합격이 아닙니다 — 방향은 맞지만 표본이 얇아 확정하지 "
            "못했다는 뜻입니다. 표본을 늘려 재판정해야 합니다.",
        ],
    }
