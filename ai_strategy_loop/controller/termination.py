"""US-005 Phase 2b — 루프 종료 판정.

`should_terminate(cumulative, config) -> (stop, reason)`.

종료 조건 (먼저 충족되는 것 우선):
  1) target: config.target_score가 설정되어 있고 best_score >= target_score
  2) max-gen: 생성 세대 수가 config.max_generations 이상
  3) cost-cap:
       - 토큰 cap을 쓸 수 있으면(config.cost_cap_tokens 설정 + 누적 토큰 추적)
         누적 total_tokens >= cost_cap_tokens 일 때 종료
       - gpt_auth처럼 토큰 비용이 불투명한($ 구독 과금) provider는
         생성 세대 COUNT를 대리 지표로 써서 누적 호출 >= cost_cap_generations
         일 때 종료한다.

cumulative는 누적 상태를 담은 단순 dict다:
  {
    "best_score": float | None,
    "gen_count":  int,    # 지금까지 생성한 세대 수
    "tokens":     int,    # 지금까지 누적 total_tokens
  }
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def _provider_has_token_accounting(config: Any) -> bool:
    """이 provider/설정에서 토큰 기반 cap을 쓸 수 있는가.

    config.cost_cap_tokens가 명시되어 있을 때만 토큰 cap을 적용한다.
    gpt_auth는 $ 구독 과금이라 토큰 비용이 불투명하므로 기본적으로 토큰 cap을
    쓰지 않고 세대-수 cap으로 폴백한다.
    """
    cap = getattr(config, "cost_cap_tokens", None)
    return cap is not None


def should_terminate(cumulative: Dict[str, Any], config: Any) -> Tuple[bool, str]:
    """종료 여부와 사유를 반환한다.

    Args:
        cumulative: {"best_score", "gen_count", "tokens"} 누적 상태.
        config: target_score / max_generations / cost_cap_* 를 가진 설정.

    Returns:
        (stop: bool, reason: str)
    """
    best_score: Optional[float] = cumulative.get("best_score")
    gen_count: int = int(cumulative.get("gen_count", 0) or 0)
    tokens: int = int(cumulative.get("tokens", 0) or 0)

    # 1) target_score 도달 (설정된 경우)
    target = getattr(config, "target_score", None)
    if target is not None and best_score is not None and best_score >= float(target):
        return True, f"target_score 도달: best_score {best_score:.6g} >= {float(target):.6g}"

    # 2) max_generations 도달
    max_gen = int(getattr(config, "max_generations", 0) or 0)
    if max_gen > 0 and gen_count >= max_gen:
        return True, f"max_generations 도달: gen_count {gen_count} >= {max_gen}"

    # 3) cost-cap
    if _provider_has_token_accounting(config):
        token_cap = int(getattr(config, "cost_cap_tokens"))
        if token_cap > 0 and tokens >= token_cap:
            return True, f"cost_cap_tokens 도달: tokens {tokens} >= {token_cap}"
    else:
        # 토큰 비용 불투명($ 과금) → 세대-수 대리 cap.
        gen_cap = int(getattr(config, "cost_cap_generations", 0) or 0)
        if gen_cap > 0 and gen_count >= gen_cap:
            return True, (
                f"cost_cap_generations 도달: gen_count {gen_count} >= {gen_cap}"
            )

    return False, "continue"
