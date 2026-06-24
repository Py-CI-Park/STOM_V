"""P5 — 얇은 자율 부검 폐루프 오케스트레이터([A]→[F], 사람 개입 0).

조립만 한다(신규 알고리즘 없음): 1-D/2-D 스윕 요약(P4 tendency) → 다음 grid 축 추천
(refine_candidates) + 앵커 이웃 변이 제안(P5 mutator) → 각 후보를 **진짜 재백테 게이트
(P0b refine_gate.gate_candidate)** 로 검증해 통과분만 채택한다.

규율(불가침):
  - **모든 변이는 P0b 게이트 통과 후에만 채택**한다(게이트 우회 0 — 하드교훈 a, 사후슬라이스
    ≠ 엣지). mutator는 제안만 하고, 채택 판정의 진실원은 재백테 손익뿐이다.
  - 기존 param 좌표 스키마 안에서만 변이(신규 B_* 컬럼·횡단면 항 0). 엔진 무수정.
  - planning 코어(plan_candidates)는 순수(백테/게이트 미호출)라 결정론적으로 단위테스트된다.
    라이브 게이트는 gate_fn 주입으로 모킹해 오케스트레이션 로직만 검증한다.
"""

from __future__ import annotations

import argparse
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from ai_strategy_loop.tmap.template import (
    TemplateSpec,
    load_template,
    render,
    validate_rendered,
)


def plan_candidates(
    template: TemplateSpec,
    summary: Dict[str, Any],
    anchor_theta: Optional[Dict[str, Any]] = None,
    *,
    max_per_param: int = 2,
    params: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """스윕 요약 + 앵커에서 게이트할 후보(변이) 목록을 만든다(순수 — 백테/게이트 미호출).

    refine_candidates(P4)로 다음 2차 grid 축을 정하고, propose_mutations(P5)로 앵커 이웃
    변이를 만든 뒤, **렌더 가능 + 생성가드 통과** 후보만 {label, theta, buy_code, sell_code}로
    돌려준다. 렌더 실패/가드 실패 후보는 제외한다(주입 전 정합성 보장).

    Args:
        template: 모수화 템플릿(TemplateSpec).
        summary: summarize_tendency 출력(refine_candidates 입력).
        anchor_theta: 변이 출발점 θ(없으면 템플릿 기본값 = 시드).
        max_per_param: 한 슬롯당 변이 수(좌/우, propose_mutations에 전달).
        params: 변이 대상 슬롯 한정(None이면 전 슬롯).

    Returns:
        {"recommended_grid": (a, b)|None, "candidates": [{label, theta, buy_code, sell_code}, ...]}.
    """
    from ai_strategy_loop.tmap.mutator import propose_mutations  # noqa: PLC0415
    from ai_strategy_loop.tmap.tendency import refine_candidates  # noqa: PLC0415

    refine = refine_candidates(summary, template=template)
    mutations = propose_mutations(
        template, anchor_theta or {}, max_per_param=max_per_param, params=params,
    )
    candidates: List[Dict[str, Any]] = []
    for m in mutations:
        try:
            buy, sell = render(template, m["theta"])
        except Exception:  # noqa: BLE001 - 렌더 실패 후보는 조용히 제외(순수·무예외).
            continue
        errors = validate_rendered(buy, sell, template.timeframe)
        if errors:
            continue  # 생성가드(compile/token/scope/시간무결성) 실패 → 제외.
        candidates.append({
            "label": m["label"], "theta": m["theta"],
            "buy_code": buy, "sell_code": sell,
        })
    return {"recommended_grid": refine.get("recommended_grid"), "candidates": candidates}


# gate_fn 계약: (buy_code, sell_code, config_path, *, label, in_sample_lift) -> {"passed": bool, ...}.
GateFn = Callable[..., Dict[str, Any]]


def run_autopsy_loop(
    template: TemplateSpec,
    summary: Dict[str, Any],
    config_path: str,
    *,
    anchor_theta: Optional[Dict[str, Any]] = None,
    gate_fn: Optional[GateFn] = None,
    max_candidates: int = 8,
    in_sample_lift: Optional[float] = None,
    max_per_param: int = 2,
) -> Dict[str, Any]:
    """후보 변이를 만들어 P0b 재백테 게이트로 채택분만 골라낸다(폐루프 [A]→[F]).

    **모든 후보는 gate_fn(=P0b 재백테)을 거쳐 passed=True인 것만 adopted**에 들어간다 —
    게이트 우회 경로는 없다(하드교훈 a). gate_fn 미지정 시 refine_gate.gate_candidate(진짜
    재백테)를 쓴다. 단위테스트는 gate_fn을 모킹해 백테 없이 오케스트레이션만 검증한다.

    Returns:
        {"recommended_grid", "n_candidates", "adopted": [...], "rejected": [...]}.
        각 adopted/rejected 항목은 후보 dict + "gate"(게이트 반환) 병합.
    """
    plan = plan_candidates(
        template, summary, anchor_theta, max_per_param=max_per_param,
    )
    candidates = plan["candidates"][: max(int(max_candidates), 0)]
    if gate_fn is None:
        from ai_strategy_loop.tmap.refine_gate import gate_candidate as gate_fn  # noqa: PLC0415

    adopted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for c in candidates:
        gate = gate_fn(
            c["buy_code"], c["sell_code"], config_path,
            label=c["label"], in_sample_lift=in_sample_lift,
        )
        record = {**c, "gate": gate}
        if gate.get("passed"):
            adopted.append(record)
        else:
            rejected.append(record)
    return {
        "recommended_grid": plan["recommended_grid"],
        "n_candidates": len(candidates),
        "adopted": adopted,
        "rejected": rejected,
    }


def _anchor_from_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    """스윕 요약의 변수별 고원 중심값을 모아 앵커 θ로 만든다(없으면 빈 dict=기본값)."""
    anchor: Dict[str, Any] = {}
    for name, info in (summary.get("params") or {}).items():
        plateau = (info or {}).get("plateau") or {}
        center = plateau.get("center_value")
        if center is not None:
            anchor[name] = center
    return anchor


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI: 기존 스윕 run의 요약에서 변이 후보를 만들어 P0b 게이트로 채택분을 출력한다."""
    parser = argparse.ArgumentParser(
        prog="tmap_autopsy_loop",
        description="P5 자율 부검 폐루프 — sweep 요약→변이 제안→P0b 재백테 게이트 채택.",
    )
    parser.add_argument("--template", required=True, help="템플릿 이름 또는 JSON 경로.")
    parser.add_argument("--run-id", required=True, help="요약을 읽을 기존 스윕 run_id.")
    parser.add_argument("--config-json", required=True, help="재백테 게이트 config 경로.")
    parser.add_argument("--max-candidates", type=int, default=8)
    parser.add_argument("--max-per-param", type=int, default=2)
    args = parser.parse_args(argv)

    from ai_strategy_loop.tmap.tendency import summarize_tendency  # noqa: PLC0415

    template = load_template(args.template)
    summary = summarize_tendency(args.run_id)
    anchor = _anchor_from_summary(summary)
    result = run_autopsy_loop(
        template, summary, args.config_json,
        anchor_theta=anchor, max_candidates=args.max_candidates,
        max_per_param=args.max_per_param,
    )
    print(
        f"[AUTOPSY-LOOP] run={args.run_id} 후보 {result['n_candidates']} → "
        f"채택 {len(result['adopted'])} / 기각 {len(result['rejected'])} "
        f"(grid 추천={result['recommended_grid']})"
    )
    for a in result["adopted"]:
        prof = (a.get("gate") or {}).get("profit")
        print(f"  ✓ {a['label']} — 재백테 흑자 {prof}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
