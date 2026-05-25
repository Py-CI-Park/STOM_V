"""전략 생성 파이프라인 (US-003 Phase 1b).

파이프라인 순서 (PRE-SAVE 게이트가 통과한 코드만 저장):

    provider.chat(build_messages)
        → extract_code (응답에서 코드 블록 추출)
        → validate_strategy (compile-only 구문 검증)
        → check_tokens (import/exec/eval/open/compile/dunder 거부)
        → dedup 검사 (최근 K개 정규화 해시와 비교)
        → save_strategy_to_db (위 게이트를 모두 통과한 코드만 저장)

compile/token 실패 시 오류를 다음 프롬프트(prior_error)에 붙여 retry_max까지 재시도.
dedup은 '중복이면 재시도'(같은 전략 반복 저장 방지).

NOTE on ordering: compile + token_check + dedup이 PRE-SAVE 게이트다. dry_run/run은
이 모듈 밖(예: e2e_smoke / 루프 오케스트레이터)에서 저장된 전략을 이름으로 참조해
실행한다. 백테스트 러너(cli.runner.run_backtest)는 STOM_CLI_DB_STRATEGY DB에서
전략 이름으로 코드를 조회하므로, 반드시 save가 dry_run/run보다 먼저여야 한다.
따라서 generator의 책임은 save까지이며, 실행 단계는 호출자가 save 이후에 수행한다.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from . import token_check
from .prompt import build_messages, extract_code
from .token_check import DedupTracker
from .variable_scope import check_variable_scope

logger = logging.getLogger(__name__)

_VALID_KINDS = ("buy", "sell")


def _usage_to_dict(usage: Any) -> Dict[str, int]:
    """ChatUsage(또는 dict)를 직렬화 가능한 dict로 변환."""
    if usage is None:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    if isinstance(usage, dict):
        return {
            "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
            "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
            "total_tokens": int(usage.get("total_tokens", 0) or 0),
        }
    return {
        "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }


def generate_strategy(
    provider: Any,
    kind: str,
    name: str,
    db_path: str,
    *,
    timeframe: str = "min",
    base_code: Optional[str] = None,
    autopsy_feedback: Optional[str] = None,
    history_summary: Optional[str] = None,
    retry_max: int = 3,
    dedup: Optional[DedupTracker] = None,
) -> Dict[str, Any]:
    """LLM으로 STOM 전략을 생성하고 게이트 통과 시 DB에 저장한다.

    Args:
        provider: chat(messages, model=None, **kw) -> ChatResult 를 가진 provider.
        kind: 'buy' 또는 'sell'.
        name: 저장 전략 이름 (DB index 컬럼).
        db_path: 저장 대상 strategy DB 경로 (루프 DB / 테스트 tmp DB).
        timeframe: 'min' 또는 'tick'. 프롬프트 지침 + 변수 스코프 가드에 쓰인다.
        base_code: seed-and-refine 출발점 코드. 주어지면 build_messages가
            fresh 생성 대신 이 코드를 점진 개선하도록 프롬프트한다. None이면
            기존 fresh 생성(하위호환).
        autopsy_feedback: 직전 백테스트 부검 피드백(게이트 거리 + 변별 변수).
        history_summary: 누적 세대 이력 요약(CONVERGENCE). build_messages로 전달.
        retry_max: compile/token 실패 시 최대 시도 횟수 (>=1).
        dedup: 중복 탐지용 DedupTracker (없으면 검사 생략).

    Returns:
        성공: {status: 'ok', name, code, attempts, usage}
        실패: {status: 'error', reason, attempts}
    """
    if kind not in _VALID_KINDS:
        return {"status": "error", "reason": f"잘못된 kind: {kind!r}", "attempts": 0}
    if retry_max < 1:
        retry_max = 1

    # cli.* import는 bootstrap 이후여야 하므로 함수 내부에서 지연 import.
    from cli.strategy import validate_strategy
    from cli.strategy_generator import save_strategy_to_db

    prior_error: Optional[str] = None
    last_usage: Dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    attempts = 0

    for attempt in range(1, retry_max + 1):
        attempts = attempt
        messages = build_messages(
            kind,
            timeframe=timeframe,
            base_code=base_code,
            autopsy_feedback=autopsy_feedback,
            history_summary=history_summary,
            prior_error=prior_error,
        )

        # --- 1) LLM 호출 ---
        try:
            result = provider.chat(messages)
        except Exception as exc:  # provider 실패는 재시도하지 않고 즉시 종료.
            return {
                "status": "error",
                "reason": f"provider 호출 실패: {exc}",
                "attempts": attempts,
            }

        text = getattr(result, "text", "") or ""
        last_usage = _usage_to_dict(getattr(result, "usage", None))

        # --- 2) 코드 추출 ---
        code = extract_code(text)
        if not code:
            prior_error = "응답에서 코드 블록을 찾지 못함"
            logger.info("attempt %d: %s", attempt, prior_error)
            continue

        # --- 3) compile 검증 (cli.strategy.validate_strategy) ---
        v = validate_strategy(code)
        if v.get("status") != "ok":
            prior_error = f"구문 검증 실패: {v.get('message')}"
            logger.info("attempt %d: %s", attempt, prior_error)
            continue

        # --- 4) token_check (최소 denylist) ---
        ok, reason = token_check.check_tokens(code)
        if not ok:
            prior_error = f"금지 토큰: {reason}"
            logger.info("attempt %d: %s", attempt, prior_error)
            continue

        # --- 4b) 변수 스코프 가드 (타임프레임 인지) ---
        #   NameError-데드락의 결정론적 차단점. 타임프레임에 없는 변수를 쓰면
        #   엔진 exec(buystg)가 죽어 백테스트가 데드락한다 → 백테 이전에 거부.
        scope_ok, offending = check_variable_scope(code, timeframe, kind)
        if not scope_ok:
            hint = (
                "분당거래대금을 써라(초당거래대금 아님)"
                if timeframe == "min"
                else "초당거래대금을 써라(분당거래대금 아님)"
            )
            prior_error = (
                f"{timeframe} 타임프레임에서 사용할 수 없는 변수: "
                f"{', '.join(offending)}; 예: {hint}"
            )
            logger.info("attempt %d: %s", attempt, prior_error)
            continue

        # --- 5) dedup ---
        if dedup is not None and dedup.is_duplicate(code):
            prior_error = "직전 전략과 구조가 동일(중복). 다른 조건으로 작성하라."
            logger.info("attempt %d: %s", attempt, prior_error)
            continue

        # --- 6) save (모든 PRE-SAVE 게이트 통과 시에만) ---
        saved = save_strategy_to_db(db_path, name, code, kind)
        if saved.get("status") != "ok":
            return {
                "status": "error",
                "reason": f"DB 저장 실패: {saved.get('message')}",
                "attempts": attempts,
            }

        if dedup is not None:
            dedup.record(code)

        return {
            "status": "ok",
            "name": name,
            "code": code,
            "attempts": attempts,
            "usage": last_usage,
        }

    # retry_max 소진.
    return {
        "status": "error",
        "reason": f"재시도 소진 ({retry_max}회): {prior_error}",
        "attempts": attempts,
    }
