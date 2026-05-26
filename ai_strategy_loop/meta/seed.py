"""P4 — 메타 인사이트 환류: MetaInsights → 생성 프롬프트 주입용 NL 가이드.

누적 메타분석(analyze.py)이 뽑은 "통과 전략 공통 조건/개선 변경/실패 패턴"을
다음 run의 전략 생성 프롬프트에 주입할 한국어 가이드 문자열로 변환한다.

환류는 **기본 OFF**(config.meta_seed_enabled=False)다 — 하위호환. ON일 때만
build_messages의 선택 슬롯(meta_seed)에 이 텍스트가 들어가 "통과 전략은 공통적으로
X를 쓴다"를 모델에 알려준다. 신호 유효성은 A/B(주입 vs 미주입)로 검증한다(계획 P4).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .analyze import MetaInsights


def build_meta_seed_text(insights: Optional[MetaInsights], *, max_vars: int = 5) -> Optional[str]:
    """MetaInsights를 생성 프롬프트 주입용 NL 가이드로 만든다.

    통과 전략 공통 변수 + 개선을 낳은 변경 + 회피할 실패 패턴을 compact 하게 담는다.
    인사이트가 비거나(None/공통변수 없음) 의미 있는 신호가 없으면 None(주입 안 함).

    Args:
        insights: 누적 메타분석 결과. None이면 None 반환(환류 안 함).
        max_vars: 가이드에 실을 공통 변수 최대 개수.

    Returns:
        주입용 한국어 가이드 문자열, 또는 신호가 없으면 None.
    """
    if insights is None:
        return None
    common = list(insights.common_pass_vars or [])[:max_vars]
    changes = list(insights.improving_changes or [])[:3]
    fp = insights.failure_patterns or {}

    # 신호 게이트: 공통 변수도·개선 변경도 없으면 주입할 가치가 없다.
    if not common and not changes:
        return None

    lines = [
        "누적 메타분석(과거 여러 run에서 학습한 공통 신호 — 이를 활용해 더 빨리 통과하라):",
    ]
    if common:
        var_str = ", ".join(f"{var}({cnt}회)" for var, cnt in common)
        lines.append(
            f"- 게이트를 통과한 전략들은 공통적으로 다음 변수를 진입 조건에 자주 썼다: {var_str}. "
            "이 변수들을 우선 고려하라(맹목 복제 금지 — 현재 부검/이력과 조화시켜라)."
        )
    if changes:
        change_str = "; ".join(f"{phrase}" for phrase, _ in changes)
        lines.append(
            f"- 과거 점수를 올린 변경 유형: {change_str}. 유사한 방향의 개선을 고려하라."
        )
    # 실패 패턴 회피 가이드(빈도가 의미 있을 때만).
    warn_parts = []
    if int(fp.get("overtrade", 0) or 0) > 0:
        warn_parts.append("과매매(거래 과다)")
    if int(fp.get("zero_trade", 0) or 0) > 0:
        warn_parts.append("0거래(과선별)")
    if int(fp.get("high_mdd", 0) or 0) > 0:
        warn_parts.append("고MDD")
    if warn_parts:
        lines.append(
            f"- 과거 반복된 실패 패턴을 회피하라: {', '.join(warn_parts)}. "
            "거래는 합리적 빈도로, MDD는 낮게 유지하라."
        )
    return "\n".join(lines)


def to_page_data(insights: Optional[MetaInsights]) -> Dict[str, Any]:
    """MetaInsights를 대시보드 LIVE 패널용 page_data["meta"]로 직렬화한다.

    인사이트가 없으면 status='empty'. JSON-직렬화 가능한 기본 타입만 담는다.
    """
    if insights is None:
        return {"status": "empty"}
    return {
        "status": "ok",
        "total_generations": insights.total_generations,
        "passing_count": insights.passing_count,
        "common_pass_vars": [list(x) for x in (insights.common_pass_vars or [])],
        "improving_changes": [list(x) for x in (insights.improving_changes or [])],
        "failure_patterns": dict(insights.failure_patterns or {}),
        "note": insights.note,
    }
