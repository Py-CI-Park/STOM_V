"""연구 Context Pack 생산자 (T2.1, 연구 레인 전용).

artifacts/process-research-validation-20260701/run_process_research_validation.py
의 make_context_and_candidates 조립 흐름을 재사용 가능한 모듈로 승격한다.

역할:
  - brain.prompt.build_research_context_pack 의 기존 계약(전체 STOM 규칙 원천
    포함, 250k 토큰 예산 fail-closed, 권한 밀반입 차단)을 **읽기 전용 import**
    로만 소비한다 — 프롬프트 함수는 수정하지 않는다.
  - sources dict 하나로 부모 buy/sell 조건식 전문+sha256, 공식 결과 지표,
    분석 카드(autopsy/analysis_card 산출 dict 수용), coverage_gap,
    축 사전확률 라인(옵션)을 받아 Context Pack 을 만든다.
  - sources['principle_docs_enabled'] 가 True 면 brain.principles 로더의
    3계층 문서(principles/constraints_checklist/idiom_dictionary)를
    extra_context 에 포함한다 (기본 미포함 —
    ai_strategy_loop.config.LoopConfig.principle_docs_enabled 기본 False 준수).
  - produce_research_candidate_pack 은 brain.pack_producer 로 후보팩 생산을
    연결한다. 조립/생산 terminal 실패면 None 을 반환해 cli.research_loop 의
    결정론 폴백(mark_diagnostic_fallback, prompt credit 0)이 자연 발동한다.

권한 규약: 연구 레인 전용 — can_promote/export/live 권한은 어디에도 없다.
"""

from __future__ import annotations

import hashlib
from typing import Any, Callable, Mapping, Optional

from ..brain.pack_producer import produce_candidate_pack, produce_candidate_pack_result
from ..brain.prompt import MAX_RESEARCH_CONTEXT_PACK_TOKENS
from ..brain.prompt import build_research_context_pack as _build_prompt_context_pack

DEFAULT_CONTEXT_PACK_MODE = "process-research"

# 원리 계층 3문서 (T4.1 로더) — 이름/로더 매핑. 지연 import 로만 소비한다.
_PRINCIPLE_DOC_NAMES = ("principles", "constraints_checklist", "idiom_dictionary")

__all__ = [
    "DEFAULT_CONTEXT_PACK_MODE",
    "build_candidate_generation_context",
    "build_context_pack_receipt",
    "build_research_context_pack",
    "collect_principle_docs",
    "produce_research_candidate_pack",
]


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _mapping(value: Any) -> dict:
    return dict(value) if isinstance(value, Mapping) else {}


def _parent_field(sources: Mapping[str, Any], side: str, field: str) -> str:
    """parents.{side}.{field} 또는 flat parent_{side}_{field} 키에서 값을 뽑는다."""

    parents = sources.get("parents") if isinstance(sources.get("parents"), Mapping) else {}
    parent = parents.get(side) if isinstance(parents.get(side), Mapping) else {}
    return str(parent.get(field) or sources.get(f"parent_{side}_{field}") or "")


def collect_principle_docs() -> dict:
    """원리 계층 3문서를 sha256과 함께 수집한다 (호출 시점 로드, fail-closed).

    문서가 없거나 비어 있으면 brain.principles 로더가 그대로 예외를 던진다.
    문서 내용은 백테스트로 검증되지 않은 가설 체계다 — 소비자는 임계값을
    검증된 사실로 취급하면 안 된다.
    """

    from ..brain import principles

    loaders = {
        "principles": (principles.PRINCIPLES_PATH, principles.load_principles),
        "constraints_checklist": (principles.CONSTRAINTS_PATH, principles.load_constraints),
        "idiom_dictionary": (principles.IDIOMS_PATH, principles.load_idioms),
    }
    docs: dict[str, dict] = {}
    for name in _PRINCIPLE_DOC_NAMES:
        path, loader = loaders[name]
        content = loader()
        docs[name] = {
            "name": name,
            "path": path.name,
            "content": content,
            "sha256": _sha256_text(content),
            "characters": len(content),
        }
    return docs


def _build_extra_context(sources: Mapping[str, Any], analysis_card: dict, coverage_gap: dict) -> dict:
    extra_context = _mapping(sources.get("extra_context"))
    if analysis_card and "analysis_card" not in extra_context:
        extra_context = {**extra_context, "analysis_card": analysis_card}
    if coverage_gap and "coverage_gap" not in extra_context:
        extra_context = {**extra_context, "coverage_gap": coverage_gap}
    axis_prompt_lines = sources.get("axis_prompt_lines")
    if axis_prompt_lines and "axis_priors" not in extra_context:
        extra_context = {
            **extra_context,
            "axis_priors": [str(line) for line in axis_prompt_lines],
            "axis_priors_source": "axis_ledger_to_prompt_lines",
        }
    if sources.get("principle_docs_enabled") and "principle_docs" not in extra_context:
        extra_context = {**extra_context, "principle_docs": collect_principle_docs()}
    return extra_context


def build_research_context_pack(sources: Mapping[str, Any]) -> dict:
    """sources dict 하나로 연구 Context Pack 을 만든다 (fail-closed).

    필수 소스: timeframe(tick|min)과 부모 buy/sell 조건식 전문
    (parent_buy_code/parent_sell_code 또는 parents.{buy,sell}.code).
    부모 전문이 없으면 ValueError("context_pack_parent_sources_missing")
    — ID-only 전달 금지 계약(full_condition_code_required_not_id_only).
    예산 초과(250k)/규칙 원천 누락/권한 밀반입은 brain.prompt 계약이 그대로
    ValueError 로 fail-closed 한다 (이 모듈은 완화하지 않는다).
    sources['max_tokens'] 는 MAX_RESEARCH_CONTEXT_PACK_TOKENS(250k) 를 상한으로
    클램프한다 — 데이터로 fail-closed 예산을 상향할 수 없다 (하향만 허용).
    """

    if not isinstance(sources, Mapping):
        raise ValueError("context_pack_sources_not_object")
    parent_buy_code = _parent_field(sources, "buy", "code")
    parent_sell_code = _parent_field(sources, "sell", "code")
    missing_sides = [
        side
        for side, code in (("buy", parent_buy_code), ("sell", parent_sell_code))
        if not code.strip()
    ]
    if missing_sides:
        raise ValueError("context_pack_parent_sources_missing: " + ",".join(missing_sides))

    analysis_card = _mapping(sources.get("analysis_card"))
    coverage_gap = _mapping(sources.get("coverage_gap"))
    feature_importance = sources.get("feature_importance")
    if feature_importance is None and analysis_card:
        feature_importance = analysis_card.get("feature_importance")
    root_cause_summary = sources.get("root_cause_summary")
    if root_cause_summary is None and analysis_card:
        root_cause_summary = analysis_card.get("root_cause")
    candidate_hypotheses = [
        dict(item)
        for item in (sources.get("candidate_hypotheses") or [])
        if isinstance(item, Mapping)
    ]
    context_pack_id = str(sources.get("context_pack_id") or "") or None

    return _build_prompt_context_pack(
        context_pack_id=context_pack_id,
        mode=str(sources.get("mode") or DEFAULT_CONTEXT_PACK_MODE),
        timeframe=str(sources.get("timeframe") or ""),
        parent_buy_id=_parent_field(sources, "buy", "id") or None,
        parent_buy_code=parent_buy_code,
        parent_sell_id=_parent_field(sources, "sell", "id") or None,
        parent_sell_code=parent_sell_code,
        official_metrics=_mapping(sources.get("official_metrics")),
        daily_rows_summary=sources.get("daily_rows_summary"),
        regime_summaries=_mapping(sources.get("regime_summaries")),
        segment_heatmap=sources.get("segment_heatmap"),
        feature_importance=feature_importance,
        edge_ratio=_mapping(sources.get("edge_ratio")),
        mfe_mae=_mapping(sources.get("mfe_mae")),
        correlation_redundancy=sources.get("correlation_redundancy"),
        avoid_zones=sources.get("avoid_zones"),
        prefer_zones=sources.get("prefer_zones"),
        root_cause_summary=root_cause_summary,
        candidate_hypotheses=candidate_hypotheses,
        validation_provenance=_mapping(sources.get("validation_provenance")),
        extra_context=_build_extra_context(sources, analysis_card, coverage_gap),
        # 데이터가 250k fail-closed 예산을 상향하지 못하도록 상한 클램프(하향만 허용).
        max_tokens=min(
            int(sources.get("max_tokens") or MAX_RESEARCH_CONTEXT_PACK_TOKENS),
            MAX_RESEARCH_CONTEXT_PACK_TOKENS,
        ),
    )


def build_context_pack_receipt(context_pack: Mapping[str, Any]) -> dict:
    """결과 dict 에 병기할 additive 추적 필드만 뽑는다 (전문 미포함, 무예외)."""

    if not isinstance(context_pack, Mapping):
        return {
            "context_pack_id": "",
            "context_pack_sha256": "",
            "full_stom_sources_included": False,
            "prompt_budget_estimated_tokens": 0,
        }
    budget = _mapping(context_pack.get("budget"))
    stom_sources = _mapping(context_pack.get("stom_sources"))
    try:
        estimated_tokens = int(budget.get("estimated_tokens") or 0)
    except (TypeError, ValueError):
        estimated_tokens = 0
    return {
        "context_pack_id": str(context_pack.get("context_pack_id") or ""),
        "context_pack_sha256": str(budget.get("rendered_sha256") or ""),
        "full_stom_sources_included": bool(stom_sources.get("all_available_sources_included")),
        "prompt_budget_estimated_tokens": estimated_tokens,
    }


def build_candidate_generation_context(
    sources: Mapping[str, Any],
    context_pack: Optional[Mapping[str, Any]] = None,
) -> dict:
    """brain.pack_producer.produce_candidate_pack 이 기대하는 context dict.

    context_pack 이 없으면 sources 로 새로 조립한다 (fail-closed 동일).
    """

    pack = dict(context_pack) if isinstance(context_pack, Mapping) else build_research_context_pack(sources)
    pack_parents = _mapping(pack.get("parents"))
    parents = {
        side: {
            "id": str(_mapping(pack_parents.get(side)).get("id") or ""),
            "code": str(_mapping(pack_parents.get(side)).get("code") or ""),
        }
        for side in ("buy", "sell")
    }
    return {
        "kind": str(sources.get("kind") or "buy"),
        "timeframe": str(pack.get("timeframe") or sources.get("timeframe") or ""),
        "parents": parents,
        "analysis_card": _mapping(sources.get("analysis_card")),
        "coverage_gap": _mapping(sources.get("coverage_gap")),
        "novelty_context": _mapping(sources.get("novelty_context")),
        "research_context_pack": pack,
        "round_id": str(sources.get("round_id") or ""),
        "prompt_score": int(sources.get("prompt_score") or 0),
    }


def produce_research_candidate_pack(
    sources: Mapping[str, Any],
    provider: Callable[[list], str],
    *,
    lanes: Optional[Mapping[str, int]] = None,
    axis_prompt_lines: Optional[list] = None,
    context_pack: Optional[Mapping[str, Any]] = None,
    final_owner_enabled: bool = False,
    methodology_version: str = "clr04_v1",
    strict_candidate_payload_v2: bool = False,
) -> Optional[dict]:
    """Context Pack + pack_producer 로 research_candidate_pack 을 만든다.

    Context Pack 조립 실패(부모 전문 누락/예산 초과 등)나 terminal 생산 실패면
    None 을 반환한다 — analysis_result['research_candidate_pack'] 에 넣으면
    falsy 라서 cli.research_loop 의 결정론 폴백(mark_diagnostic_fallback,
    prompt credit 0)이 자연 발동한다.

    DR-04 -- `final_owner_enabled` (default False = byte-identical v1 path)
    additionally routes the pack through the canonical
    `candidate_pool.select_official_candidate` final-owner selection and
    exposes the pick as `pack['final_owner_selection']`.
    """

    try:
        context = build_candidate_generation_context(sources, context_pack=context_pack)
    except (TypeError, ValueError):
        return None
    lines = axis_prompt_lines
    if lines is None:
        raw_lines = sources.get("axis_prompt_lines") if isinstance(sources, Mapping) else None
        lines = [str(line) for line in raw_lines] if raw_lines else None
    if not final_owner_enabled:
        if strict_candidate_payload_v2:
            return produce_candidate_pack(
                context,
                provider,
                lanes=lanes,
                axis_prompt_lines=lines,
                strict_candidate_payload_v2=True,
            )
        return produce_candidate_pack(
            context,
            provider,
            lanes=lanes,
            axis_prompt_lines=lines,
        )
    result = produce_candidate_pack_result(
        context,
        provider,
        lanes=lanes,
        axis_prompt_lines=lines,
        final_owner_enabled=True,
        methodology_version=methodology_version,
        strict_candidate_payload_v2=strict_candidate_payload_v2,
    )
    return result["candidate_pack"]
