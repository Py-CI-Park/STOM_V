"""파라미터 응답면 API (페이지 32) — "이 값이 고원 위인가, 절벽 끝인가".

페이지 30 이 "이 후보가 나은가", 페이지 31 이 "그 판정을 믿을 만한가"를 답한다면,
여기는 **"그 값을 채택해도 표본 밖에서 살아남는가"**를 답한다.

세 화면이 채택 결정의 세 축이다:

    30 성과   →  31 신뢰도  →  32 견고성

권한 계약: **읽기 전용.** 러너가 남긴 JSON 만 읽는다.
"""

from __future__ import annotations

import glob
import json
import os
from typing import Any, Final

from fastapi import APIRouter

response_surface_router = APIRouter()

_LABEL_ROOT: Final = os.path.join(
    os.path.dirname(__file__), "..", "state", "labels")

#: 판정별 사람 말 — 화면과 API 가 같은 문구를 쓰게 한 곳에 둔다.
VERDICT_LABEL: Final = {
    "고원": "고원 · 이웃도 버틴다",
    "경사": "경사 · 민감",
    "절벽": "절벽 · 과최적 위험",
    "음수": "음수 · 후보 아님",
    "가장자리": "가장자리 · 판정 불가",
    "빈칸": "미측정",
}


def _find(out_name: str, tag: str) -> str | None:
    path = os.path.join(_LABEL_ROOT, out_name, f"_exit_response_surface{tag}.json")
    if os.path.exists(path):
        return path
    # 태그를 모르고 들어온 경우 — 하나뿐이면 그것을 쓴다. 여럿이면 고르지 않는다.
    found = sorted(glob.glob(os.path.join(
        _LABEL_ROOT, out_name, "_exit_response_surface*.json")))
    return found[0] if len(found) == 1 else None


@response_surface_router.get("/loop/response-surface")
def response_surface(out_name: str = "design_v5", tag: str = "_wide") -> dict[str, Any]:
    path = _find(out_name, tag)
    if path is None:
        return {"available": False, "out_name": out_name, "tag": tag,
                "reason": ("응답면 산출이 없습니다 — run_reproduction_gate --grid wide "
                           "후 run_exit_response_surface 를 돌리면 생깁니다."),
                "verdict_labels": VERDICT_LABEL, "cells": [], "reading_rules": []}

    with open(path, "r", encoding="utf-8") as handle:
        report = json.load(handle)

    cells = report.get("cells") or []
    for cell in cells:
        cell["verdict_label"] = VERDICT_LABEL.get(cell.get("verdict"), cell.get("verdict"))

    return {
        "available": bool(cells),
        "out_name": out_name, "tag": tag,
        "source": os.path.basename(path),
        "verdict_labels": VERDICT_LABEL,
        **{k: v for k, v in report.items() if k not in ("cells", "ascii")},
        "cells": cells,
        "reading_rules": [
            "**고원**은 이웃 격자점도 성적을 유지한다는 뜻입니다 — 임계를 조금 빗나가도 "
            "무너지지 않습니다.",
            "**절벽**은 이웃 중 하나가 0 이하라는 뜻입니다. 지금 표본에서 아무리 높아도 "
            "표본 밖에서 사라질 자리입니다.",
            "격자 **가장자리**는 고원으로 승격하지 않습니다 — 한쪽을 못 봤을 뿐입니다.",
            "권고는 '가장 높은 셀'이 아니라 **'가장 높은 고원 셀'** 입니다. 둘의 격차가 "
            "곧 최고값을 채택했을 때 잃을 각오입니다.",
        ],
    }
