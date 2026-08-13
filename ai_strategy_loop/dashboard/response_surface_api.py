"""파라미터 응답면 API (페이지 32) — 국소 파라미터 민감도.

페이지 32는 같은 연구 표본에서 이웃한 파라미터 격자점의 성적 변화를 읽는다.
따라서 이 화면은 표본 밖 생존이나 채택 여부를 판정하지 않는다.

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

_PROVENANCE_FIELDS: Final = (
    "study", "study_id", "artifact", "artifact_id", "source", "source_id",
    "split", "window", "hash", "created_at",
)


def _find(out_name: str, tag: str) -> str | None:
    """태그를 주면 그것을, 안 주면 **가장 최근 산출**을 쓴다.

    태그를 고정하면 안 되는 이유: 라벨이 넓어질 때마다 새 태그로 산출한다
    (`_wide` 355일 → `_wide832` 832일). 화면이 옛 태그를 붙들고 있으면
    백필을 끝내도 옛 표본의 그림을 계속 보여준다 — 페이지 29 에서 실제로 겪었다.
    """
    if tag:
        path = os.path.join(_LABEL_ROOT, out_name, f"_exit_response_surface{tag}.json")
        return path if os.path.exists(path) else None
    found = glob.glob(os.path.join(
        _LABEL_ROOT, out_name, "_exit_response_surface*.json"))
    return max(found, key=os.path.getmtime) if found else None


def _provenance(report: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    """Return only supplied provenance facts; malformed metadata is not guessed."""
    raw = report.get("provenance")
    if raw is not None and not isinstance(raw, dict):
        return {}, "산출 provenance 형식이 올바르지 않습니다."
    sources = (raw or {}, report)
    values: dict[str, Any] = {}
    for key in _PROVENANCE_FIELDS:
        for source in sources:
            if key in source and source[key] not in (None, ""):
                values[key] = source[key]
                break
    if not values:
        return {}, "산출 provenance가 없습니다."
    return values, None


def _unavailable(
    out_name: str,
    tag: str,
    reason: str,
    *,
    artifact: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "available": False,
        "out_name": out_name,
        "tag": tag,
        "reason": reason,
        "verdict_labels": VERDICT_LABEL,
        "cells": [],
        "reading_rules": [],
        "provenance_available": False,
    }
    if artifact is not None:
        payload["source"] = artifact
    return payload


@response_surface_router.get("/loop/response-surface")
def response_surface(out_name: str = "design_v5", tag: str = "") -> dict[str, Any]:
    path = _find(out_name, tag)
    if path is None:
        return _unavailable(
            out_name, tag,
            "응답면 산출이 없습니다 — 국소 파라미터 민감도를 계산한 산출이 필요합니다.",
        )

    artifact = os.path.basename(path)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            report = json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return _unavailable(
            out_name, tag, "응답면 산출을 읽을 수 없습니다.", artifact=artifact,
        )
    if not isinstance(report, dict):
        return _unavailable(
            out_name, tag, "응답면 산출 형식이 올바르지 않습니다.", artifact=artifact,
        )

    cells = report.get("cells") or []
    for cell in cells:
        if isinstance(cell, dict):
            cell["verdict_label"] = VERDICT_LABEL.get(cell.get("verdict"), cell.get("verdict"))

    provenance, provenance_error = _provenance(report)
    oos_verdict = report.get("oos_verdict")
    has_oos_verdict = isinstance(oos_verdict, str) and bool(oos_verdict.strip())
    report_fields = {
        key: value for key, value in report.items()
        if key not in ("cells", "ascii", "provenance", "recommendation", "oos_verdict")
    }

    payload = {
        "available": bool(cells),
        "out_name": out_name, "tag": tag,
        "source": artifact,
        "verdict_labels": VERDICT_LABEL,
        "provenance_available": provenance_error is None,
        **({"provenance": provenance} if provenance_error is None else
           {"provenance_error": provenance_error}),
        **report_fields,
        "cells": cells,
        "reading_rules": [
            "**고원**은 이웃 격자점도 같은 연구 표본에서 성적을 유지한다는 뜻입니다.",
            "**절벽**은 이웃 중 하나가 0 이하라는 뜻입니다. 지금 표본에서 아무리 높아도 "
            "국소 파라미터 변화에 민감합니다.",
            "격자 **가장자리**는 고원으로 승격하지 않습니다 — 한쪽을 못 봤을 뿐입니다.",
            "'가장 높은 셀'과 **'가장 높은 고원 셀'**의 격차는 국소 민감도의 참고값입니다.",
        ],
    }
    if has_oos_verdict:
        payload["oos_verdict"] = oos_verdict
        if "recommendation" in report:
            payload["recommendation"] = report["recommendation"]
    return payload
