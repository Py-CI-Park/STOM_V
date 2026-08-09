"""매도축 응답면 — "지금 값이 고원 위인가, 절벽 끝인가".

## 왜 이것이 최적화의 본체인가

마스터 로드맵 §2.4 의 규율: **최적화는 "더 좋은 값 찾기"가 아니라 "지금 값이 고원
위에 있는지 확인하기"로 쓴다.** 이유는 산수다. 매도축만 46,875 조합이고 전수는
1년이 걸린다. Optuna 로 수천 번 뽑아 최고값을 채택하면 QSP1~13 이 반복한 함정
(선택 편의 0.6225%p, 후보 2배 → 편의 1.9배)에 그대로 빠진다.

절벽 위의 최고점은 표본 밖에서 사라진다. 고원 위의 두 번째 값이 살아남는다.

## 비유

산등성이에서 야영지를 고르는 것과 같다. 가장 높은 곳은 칼날 능선일 수 있다 —
한 걸음만 어긋나도 굴러떨어진다. 조금 낮아도 평평한 곳에 텐트를 친다.
이웃 격자점의 성적이 **이웃 값**이고, 그것이 유지되면 평평한 것이다.

## 판정

| 판정 | 조건 | 뜻 |
|---|---|---|
| **고원** | 이웃 최소가 중심의 `retain` 배 이상이고 양수 | 채택 가능 |
| **경사** | 이웃 최소가 양수지만 `retain` 배 미만 | 민감 — 채택 시 위험 명시 |
| **절벽** | 이웃 중 하나라도 0 이하 | 과최적 — 채택 금지 |
| **음수** | 중심 자체가 0 이하 | 후보 아님 |
| **가장자리** | 이웃이 2개 미만 | 판정 불가 — 격자를 넓혀야 한다 |

가장자리를 "고원"으로 분류하지 않는 것이 중요하다. 격자 모서리는 한쪽을 못 보고
있을 뿐이지 평평한 것이 아니다.
"""

from __future__ import annotations

import re
from typing import Any, Final, Sequence

#: `trailing(arm+3/give1.5)` 형태만 응답면 축으로 쓴다.
_TRAILING: Final = re.compile(r"^trailing\(arm\+([0-9.]+)/give([0-9.]+)\)$")

#: 이웃이 중심의 이 배수 이상 성적을 유지하면 평평하다고 본다.
DEFAULT_RETAIN: Final = 0.5

#: 이웃이 이보다 적으면 판정하지 않는다(격자 모서리).
MIN_NEIGHBOURS: Final = 2


def parse_trailing(label: str) -> tuple[float, float] | None:
    match = _TRAILING.match(str(label))
    if match is None:
        return None
    return float(match.group(1)), float(match.group(2))


def build_surface(cells: Sequence[dict[str, Any]], *,
                  metric: str = "expectancy_pct") -> dict[str, Any]:
    """셀 목록 → (무장 × 되돌림) 격자. 트레일링이 아닌 셀은 조용히 빠진다."""
    points: dict[tuple[float, float], float] = {}
    for cell in cells:
        axis = parse_trailing(cell.get("rule", ""))
        value = cell.get(metric)
        if axis is None or value is None:
            continue
        points[axis] = float(value)

    arms = sorted({a for a, _ in points})
    gives = sorted({g for _, g in points})
    matrix = [[points.get((a, g)) for g in gives] for a in arms]
    return {"arms": arms, "gives": gives, "matrix": matrix,
            "points": points, "metric": metric, "cells": len(points)}


def _neighbour_values(matrix: list[list[float | None]], row: int, col: int) -> list[float]:
    out: list[float] = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        r, c = row + dr, col + dc
        if 0 <= r < len(matrix) and 0 <= c < len(matrix[0]):
            value = matrix[r][c]
            if value is not None:
                out.append(float(value))
    return out


def classify(center: float | None, neighbours: Sequence[float], *,
             retain: float = DEFAULT_RETAIN) -> str:
    if center is None:
        return "빈칸"
    if center <= 0:
        return "음수"
    if len(neighbours) < MIN_NEIGHBOURS:
        # 모서리는 한쪽을 못 볼 뿐 평평한 것이 아니다 — 고원으로 승격시키지 않는다.
        return "가장자리"
    worst = min(neighbours)
    if worst <= 0:
        return "절벽"
    return "고원" if worst >= center * retain else "경사"


def analyze(cells: Sequence[dict[str, Any]], *, metric: str = "expectancy_pct",
            retain: float = DEFAULT_RETAIN) -> dict[str, Any]:
    """응답면 전체 판정 + 채택 권고.

    권고는 "가장 높은 셀"이 아니라 **가장 높은 고원 셀**이다. 둘이 다르면 그
    사실 자체를 보고한다 — 그 격차가 과최적의 크기다.
    """
    surface = build_surface(cells, metric=metric)
    arms, gives, matrix = surface["arms"], surface["gives"], surface["matrix"]
    if not arms or not gives:
        return {"available": False, "reason": "트레일링 셀이 없다", **surface}

    graded: list[dict[str, Any]] = []
    for i, arm in enumerate(arms):
        for j, give in enumerate(gives):
            center = matrix[i][j]
            if center is None:
                continue
            around = _neighbour_values(matrix, i, j)
            verdict = classify(center, around, retain=retain)
            graded.append({
                "arm": arm, "give": give,
                "rule": f"trailing(arm+{arm:g}/give{give:g})",
                metric: center,
                "neighbours": len(around),
                "neighbour_min": min(around) if around else None,
                "retention": (min(around) / center) if (around and center > 0) else None,
                "verdict": verdict,
            })

    best = max(graded, key=lambda c: c[metric], default=None)
    plateau = [c for c in graded if c["verdict"] == "고원"]
    best_plateau = max(plateau, key=lambda c: c[metric], default=None)
    # 최고점이 절벽이면 그 격차가 곧 "최고값을 채택했을 때 잃을 각오"다.
    overfit_gap = (best[metric] - best_plateau[metric]) \
        if (best and best_plateau and best is not best_plateau) else None

    counts: dict[str, int] = {}
    for cell in graded:
        counts[cell["verdict"]] = counts.get(cell["verdict"], 0) + 1

    return {
        "available": True,
        "metric": metric, "retain": retain,
        "arms": arms, "gives": gives, "matrix": matrix,
        "cells": graded, "verdict_counts": counts,
        "best": best,
        "best_plateau": best_plateau,
        "best_is_plateau": bool(best and best.get("verdict") == "고원"),
        "overfit_gap": overfit_gap,
        "recommendation": (
            "최고점이 고원 위다 — 채택 가능." if (best and best.get("verdict") == "고원")
            else ("최고점이 고원이 아니다. 채택하려면 고원 최고 셀을 쓴다."
                  if best_plateau else
                  "고원 셀이 하나도 없다 — 이 축에서 채택할 값이 없다.")),
        "note": ("판정은 이웃 4칸 기준이다. 격자 모서리는 '가장자리'로 남기고 "
                 "고원으로 승격시키지 않는다 — 한쪽을 못 봤을 뿐이다."),
    }


def render_ascii(report: dict[str, Any], *, width: int = 9) -> str:
    """터미널용 히트맵 — 눈으로 고원/절벽을 바로 본다."""
    if not report.get("available"):
        return "(응답면 없음)"
    mark = {"고원": "O", "경사": "/", "절벽": "!", "음수": "-", "가장자리": ".", "빈칸": " "}
    by_axis = {(c["arm"], c["give"]): c for c in report["cells"]}
    metric = report["metric"]

    head = "무장\\되돌림 " + "".join(f"{g:>{width}g}" for g in report["gives"])
    lines = [head, "-" * len(head)]
    for arm in report["arms"]:
        row = [f"{arm:>10g}  "]
        for give in report["gives"]:
            cell = by_axis.get((arm, give))
            if cell is None:
                row.append(" " * width)
                continue
            row.append(f"{cell[metric]:>{width - 1}.2f}{mark[cell['verdict']]}")
        lines.append("".join(row))
    lines.append("")
    lines.append("범례  O 고원 · / 경사 · ! 절벽 · - 음수 · . 가장자리")
    return "\n".join(lines)
