"""TMAP P5 — 앵커 변이(mutator): 현재 최적 θ의 이웃 후보 θ 제안기(순수).

경향성 지도(G3)가 변수별 고원을 찾고 grid(P4)가 면을 교차검증한 뒤, 운영자가 채택한
**앵커 θ\\*** 주변을 좁게 한 칸씩 흔들어 더 나은 이웃을 찾고 싶을 때 쓴다. 이 모듈은
앵커에서 출발해, 각 슬롯의 ParamSpec.values 중 **앵커 값의 정렬상 인접(좌/우)** 후보로
한 슬롯씩만 바꾼 변이 θ를 만들어 돌려준다(제안만).

규율(P4 refine_candidates와 동일):
  - **백테/게이트 호출 없음**: 제안만 한다. 채택(재백테)은 오케스트레이터가 refine_gate
    P0b로 별도 수행한다.
  - **기존 슬롯/값만 사용**: 신규 컬럼·횡단면 항 0. 변이 θ는 template.render로 KeyError
    없이 렌더되고, 토큰셋은 기본 렌더의 부분집합이다(identity 계약 보존).
  - **순수·무예외·불변**: 잘못된 입력(빈 템플릿/비-dict anchor/알 수 없는 키/값 부재)은
    예외 대신 빈 리스트(또는 무시)로 처리하고, anchor_theta 원본은 절대 변형하지 않는다.

분석/연구 전용 — 엔진·하드게이트 무수정.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from ai_strategy_loop.tmap.template import TemplateSpec, render


def _neighbor_values(values: Sequence[Any], anchor_value: Any) -> List[Any]:
    """정렬된 후보열에서 anchor 값의 좌·우 인접 후보를 (좌, 우) 순으로 돌려준다.

    anchor 값이 values에 없으면 인접을 정의할 수 없으므로 빈 리스트(graceful skip).
    """
    try:
        idx = list(values).index(anchor_value)
    except ValueError:
        return []
    neighbors: List[Any] = []
    if idx - 1 >= 0:
        neighbors.append(values[idx - 1])  # 좌(작은 값).
    if idx + 1 < len(values):
        neighbors.append(values[idx + 1])  # 우(큰 값).
    return neighbors


def propose_mutations(
    template: TemplateSpec,
    anchor_theta: Dict[str, Any],
    *,
    max_per_param: int = 2,
    params: Optional[Sequence[str]] = None,
) -> List[Dict[str, Any]]:
    """앵커 θ에서 각 대상 슬롯의 인접 후보로 한 슬롯씩 바꾼 변이 θ들을 제안한다.

    Args:
        template: TemplateSpec(슬롯 정의·후보값·기본값).
        anchor_theta: 현재 최적 θ(dict). 빈 dict면 template.defaults()를 앵커로 본다.
            앵커에 없는 슬롯은 해당 슬롯의 기본값을 앵커 값으로 채워 인접을 계산한다.
            알 수 없는 키는 무시한다(graceful).
        max_per_param: 한 슬롯당 생성할 변이 상한(좌1·우1까지 → 기본 2). 0 이하면 빈 리스트.
        params: (선택) 변이 대상 슬롯명 목록. 미지정 시 모든 슬롯이 대상.

    Returns:
        변이 항목 리스트. 각 항목:
          {
            "label": "MUT {param}={value}",
            "theta": {...전체 θ...},   # 앵커 + 한 슬롯만 인접값으로 교체.
            "param": 슬롯명,
            "value": 인접 후보값,
            "from": 앵커에서의 그 슬롯 값,
          }
        중복 θ·앵커와 동일한 θ는 제외한다. 잘못된 입력은 빈 리스트.
    """
    # 무예외 가드: 비정상 입력은 빈 리스트.
    if not isinstance(template, TemplateSpec) or not template.params:
        return []
    if not isinstance(anchor_theta, dict):
        return []
    if max_per_param <= 0:
        return []

    defaults = template.defaults()
    valid_names = set(defaults)

    # 불변성: anchor 원본을 변형하지 않도록 복사하고, 알 수 없는 키는 버린다.
    anchor = {k: v for k, v in anchor_theta.items() if k in valid_names}
    # 유효 앵커 θ = 기본값 위에 앵커 덮어쓰기(비대상 슬롯의 운반값 기준).
    base_theta = dict(defaults)
    base_theta.update(anchor)

    if params is None:
        target = [p.name for p in template.params]
    else:
        target = [name for name in params if name in valid_names]

    out: List[Dict[str, Any]] = []
    seen: set = set()
    for name in target:
        spec = template.param(name)
        anchor_value = base_theta[name]
        neighbors = _neighbor_values(spec.values, anchor_value)
        produced = 0
        for value in neighbors:
            if produced >= max_per_param:
                break
            theta = dict(base_theta)
            theta[name] = value
            if theta == base_theta:
                continue  # 앵커와 동일한 θ는 제외(이론상 불가하나 방어).
            key = tuple(sorted(theta.items()))
            if key in seen:
                continue  # 중복 θ 제외.
            seen.add(key)
            out.append({
                "label": f"MUT {name}={value}",
                "theta": theta,
                "param": name,
                "value": value,
                "from": anchor_value,
            })
            produced += 1
    return out


def render_mutation(template: TemplateSpec, theta: Dict[str, Any]) -> Tuple[str, str]:
    """변이 θ를 (매수 코드, 매도 코드)로 렌더한다(template.render 재사용)."""
    return render(template, theta)
