"""p5 프롬프트 배선 — 잠들어 있던 최상급 자산을 실제 메시지 빌더로.

배경(감사 결함 #3): `brain/prompts/p5_*.md` 두 자산은 부검 숫자 주입·성공/실패
사례·"한 번에 한 절" 원칙을 갖춘 모범 프롬프트인데, 파일 머리에 "기본 OFF —
어떤 경로에도 자동 주입되지 않는다"라고 적힌 채 **한 번도 배선된 적이 없었다**.

이 모듈이 그 공백을 메운다.

두 종류:
  - `build_single_edit_messages` — 검증된 전략의 **한 곳만** 고친다.
    변경↔결과의 인과 귀속이 성립하는 유일한 형태(다중 수정은 귀속 불가).
  - `build_template_hypothesis_messages` — 숫자를 비운 **구조 가설**을 만든다.
    숫자는 지도/최적화기가 측정한다(구조=논리, 숫자=기계 분업).

계약:
  - 자산 마크다운의 시스템 프롬프트 본문을 **원문 그대로** 싣는다(사본 표류 금지).
  - 부검 근거가 없으면 자리표시자를 채우지 않고 **명시적으로 없음을 적는다** —
    "예) 손실 거래의 73%…" 같은 예시가 실제 근거로 오인되면 안 된다.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

_PROMPT_DIR = Path(__file__).resolve().parent / "prompts"

SINGLE_EDIT_ASSET = "p5_single_edit_mutation.md"
TEMPLATE_HYPOTHESIS_ASSET = "p5_template_hypothesis.md"

#: 자산에서 시스템 프롬프트 본문(첫 코드펜스)을 뽑는 정규식.
_FENCE_RE = re.compile(r"```\s*\n(.*?)```", re.DOTALL)

_NO_EVIDENCE = "(근거 없음 — 이번 세대에는 제시된 수치가 없다. 추측으로 채우지 마라.)"


def load_asset_body(asset: str) -> str:
    """자산 마크다운에서 시스템 프롬프트 본문을 원문 그대로 읽는다."""
    path = _PROMPT_DIR / asset
    text = path.read_text(encoding="utf-8")
    match = _FENCE_RE.search(text)
    if not match:
        raise ValueError(f"프롬프트 자산에 코드펜스 본문이 없다: {path}")
    return match.group(1).strip()


# ---------------------------------------------------------------------------
# 부검 카드 → 프롬프트 근거 문단
# ---------------------------------------------------------------------------

def autopsy_summary_from_card(card: Optional[Mapping[str, Any]]) -> str:
    """Analysis Card v2 를 프롬프트용 근거 문단으로 압축한다.

    카드의 정직 라벨(status)을 존중한다 — insufficient_data 섹션은 인용하지 않는다.
    """
    if not isinstance(card, Mapping):
        return _NO_EVIDENCE

    lines: List[str] = []

    root = card.get("root_cause")
    if isinstance(root, Mapping) and root.get("status") == "ok":
        items = root.get("items") or root.get("causes") or []
        for item in list(items)[:3]:
            if not isinstance(item, Mapping):
                continue
            title = item.get("title") or item.get("kind") or "근본원인"
            detail = item.get("detail") or ""
            evidence = item.get("evidence")
            piece = f"- 근본원인: {title}"
            if detail:
                piece += f" — {detail}"
            if evidence:
                piece += f" (근거 {evidence})"
            lines.append(piece)

    edge = card.get("edge_ratio")
    mfe_mae = card.get("mfe_mae")
    if isinstance(mfe_mae, Mapping) and mfe_mae.get("status") == "ok":
        value = None
        if isinstance(edge, Mapping):
            value = edge.get("value", edge.get("edge_ratio"))
        lines.append(
            f"- 경로: 평균 MFE {mfe_mae.get('mean_mfe')} / 평균 MAE {mfe_mae.get('mean_mae')}"
            + (f" · 엣지비 {value}" if value is not None else "")
        )

    features = card.get("feature_importance")
    if isinstance(features, Mapping) and features.get("status") == "ok":
        rows = features.get("features") or features.get("items") or []
        for row in list(rows)[:4]:
            if not isinstance(row, Mapping):
                continue
            lines.append(
                f"- 판별 지표: {row.get('feature') or row.get('name')} "
                f"승자 {row.get('winner_mean')} vs 패자 {row.get('loser_mean')} "
                f"(d={row.get('cohens_d')}, q={row.get('q_value', row.get('qvalue'))})"
            )

    avoid = card.get("avoid_zones")
    if isinstance(avoid, Mapping) and avoid.get("status") == "ok":
        zones = avoid.get("zones") or avoid.get("items") or []
        for zone in list(zones)[:3]:
            if not isinstance(zone, Mapping):
                continue
            lines.append(
                f"- 손실 집중 구역: {zone.get('segment') or zone.get('cell') or zone.get('label')} "
                f"(표본 {zone.get('n') or zone.get('samples')}, "
                f"평균 {zone.get('mean_return', zone.get('mean'))}%)"
            )

    return "\n".join(lines) if lines else _NO_EVIDENCE


def mutation_axes_from_card(card: Optional[Mapping[str, Any]]) -> List[str]:
    """카드가 제시한 변이축(다음 수정 후보) 목록."""
    if not isinstance(card, Mapping):
        return []
    axis = card.get("mutation_axis")
    if not isinstance(axis, Mapping) or axis.get("status") != "ok":
        return []
    items = axis.get("items") or axis.get("axes") or []
    out: List[str] = []
    for item in items:
        if isinstance(item, Mapping):
            label = item.get("axis") or item.get("kind") or ""
            detail = item.get("detail") or item.get("hint") or ""
            out.append(f"{label}: {detail}".strip(": ").strip())
        elif isinstance(item, str):
            out.append(item)
    return out


# ---------------------------------------------------------------------------
# 메시지 빌더
# ---------------------------------------------------------------------------

def build_single_edit_messages(
    *,
    base_code: str,
    card: Optional[Mapping[str, Any]] = None,
    autopsy_summary: Optional[str] = None,
    counterfactual_suggestions: Optional[Sequence[str]] = None,
    revision_budget_left: Optional[int] = None,
    kind: str = "buy",
) -> List[Dict[str, str]]:
    """단일 변경 변이 메시지 — 절개는 한 곳만.

    Args:
        base_code: 고칠 대상 전략 원문(반드시 있어야 한다 — 백지 생성이 아니다).
        card: Analysis Card v2. 근거 문단과 변이축을 여기서 뽑는다.
        autopsy_summary: 카드 대신 직접 넣는 근거 문단(있으면 우선).
        counterfactual_suggestions: 백테 0회로 사전 검증된 필터 제안.
        revision_budget_left: 남은 수정 예산(가설 원장). 표기하면 모델이
            "아무거나 한 번 더" 하는 것을 억제한다.
    """
    if not base_code or not base_code.strip():
        raise ValueError("단일 변경 변이는 base_code 가 반드시 필요하다(백지 생성 금지)")

    body = load_asset_body(SINGLE_EDIT_ASSET)
    summary = autopsy_summary or autopsy_summary_from_card(card)
    suggestions = (
        "\n".join(f"- {s}" for s in counterfactual_suggestions)
        if counterfactual_suggestions
        else "(사전 검증된 제안 없음)"
    )
    system = (
        body.replace("{autopsy_summary}", summary)
        .replace("{counterfactual_suggestions}", suggestions)
    )

    axes = mutation_axes_from_card(card)
    user_parts = [f"[대상 코드 — {kind}]", "```python", base_code.strip(), "```"]
    if axes:
        user_parts += ["", "[카드가 제시한 변이축 — 이 중 하나만 골라라]"]
        user_parts += [f"- {a}" for a in axes]
    if revision_budget_left is not None:
        user_parts += [
            "",
            f"[예산] 이 아이디어에 남은 수정 횟수: {revision_budget_left}회. "
            "예산을 다 쓰면 가설은 폐기되고 기록된다 — 근거 없는 수정에 쓰지 마라.",
        ]
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n".join(user_parts)},
    ]


def build_template_hypothesis_messages(
    *,
    principle_text: str,
    timeframe: str = "tick",
    ext_end: int = 93000,
    seed_hints: Optional[Sequence[str]] = None,
) -> List[Dict[str, str]]:
    """구조 가설 메시지 — 숫자는 비우고 구조와 탐색 범위만 설계하게 한다.

    Args:
        principle_text: 이번 라운드가 시험할 원리(사람 아이디어 또는 채굴 시드).
        seed_hints: 백파인더 채굴 등 in-sample 시드 재료(심판 아님, 시드 전용).
    """
    if not principle_text or not principle_text.strip():
        raise ValueError("구조 가설은 시험할 원리(principle_text)가 필요하다")

    body = load_asset_body(TEMPLATE_HYPOTHESIS_ASSET)
    system = (
        body.replace("{principle_text}", principle_text.strip())
        .replace("{ext_end}", str(ext_end))
    )

    user_parts = [f"[타임프레임] {timeframe}", "", f"[시험할 원리] {principle_text.strip()}"]
    if seed_hints:
        user_parts += [
            "",
            "[시드 재료 — 채굴 결과(설계 구간 in-sample). 심판 근거가 아니라 출발점이다]",
        ]
        user_parts += [f"- {h}" for h in seed_hints]
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n".join(user_parts)},
    ]


def describe_messages(messages: Sequence[Mapping[str, str]]) -> str:
    """스풀 요청을 사람이 훑어볼 수 있게 요약(디버깅·감사용)."""
    return json.dumps(
        [{"role": m.get("role"), "chars": len(m.get("content") or "")} for m in messages],
        ensure_ascii=False,
    )
