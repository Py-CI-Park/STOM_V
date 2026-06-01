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
from typing import Any, Callable, Dict, Optional, Tuple

from . import token_check
from .liquidity_gate import has_liquidity_gate
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
    crossover_parents: Optional[Tuple[str, str]] = None,
    autopsy_feedback: Optional[str] = None,
    history_summary: Optional[str] = None,
    meta_seed: Optional[str] = None,
    retry_max: int = 3,
    dedup: Optional[DedupTracker] = None,
    dispersion_prompt_enabled: bool = False,
    target_daily_trades: Optional[float] = None,
    require_liquidity_gate: bool = False,
    mdd_control_enabled: bool = False,
    encourage_time_dispersion: bool = False,
    require_filter_gates: bool = False,
    min_filter_categories: int = 5,
    on_prompt: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """LLM으로 STOM 전략을 생성하고 게이트 통과 시 DB에 저장한다.

    Args:
        provider: chat(messages, model=None, **kw) -> ChatResult 를 가진 provider.
        kind: 'buy' 또는 'sell'.
        name: 저장 전략 이름 (DB index 컬럼).
        db_path: 저장 대상 strategy DB 경로 (루프 DB / 테스트 tmp DB).
        timeframe: 'min' 또는 'tick'. 프롬프트 지침 + 변수 스코프 가드에 쓰인다.
        base_code: seed-and-refine 출발점 코드(단일 부모 mutation). 주어지면
            build_messages가 fresh 생성 대신 이 코드를 점진 개선하도록 프롬프트한다.
            None이면 기존 fresh 생성(하위호환).
        crossover_parents: (부모A, 부모B) 두 전략 코드 (P2 GA crossover). 주어지면
            build_messages가 두 전략의 강점을 결합하도록 프롬프트한다. base_code와
            상호 배타(crossover_parents가 우선). None이면 기존 경로.
        autopsy_feedback: 직전 백테스트 부검 피드백(게이트 거리 + 변별 변수).
        history_summary: 누적 세대 이력 요약(CONVERGENCE). build_messages로 전달.
        meta_seed: 누적 메타분석 환류 가이드(P4). build_messages로 전달(기본 None=주입 안 함).
        retry_max: compile/token 실패 시 최대 시도 횟수 (>=1).
        dedup: 중복 탐지용 DedupTracker (없으면 검사 생략).
        dispersion_prompt_enabled: build_messages로 전달(매수 분산매매 프롬프트 토글).
            기본 False=하위호환(기존 프롬프트 byte-동일).
        target_daily_trades: build_messages로 전달(프롬프트 산식 노출용 목표 일평균).
            기본 None=하위호환(산식 미노출).
        require_liquidity_gate: True면 매수(kind=='buy') 코드가 거래대금 유동성
            게이트(거래대금 계열 변수 + 비교 조건)를 포함하는지 검증하고, 없으면
            prior_error 설정 후 재시도한다(reject→재생성). 매도(sell)에는 미적용.
            기본 False면 이 검사는 평가조차 안 돼 동작이 기존과 byte-동일(하위호환).
        mdd_control_enabled: build_messages로 전달(매도 MDD 억제 프롬프트 토글).
            build_messages가 kind=='sell'일 때만 반영하므로 매수 경로엔 무영향.
            기본 False=하위호환(기존 프롬프트 byte-동일).
        encourage_time_dispersion: build_messages로 전달(매수 진입 시간 분산 넛지
            프롬프트 토글, Phase C-3). build_messages가 kind=='buy'일 때만 반영하므로
            매도 경로엔 무영향. 시간 분산은 정적 탐지 불가라 reject 게이트가 아닌
            프롬프트 넛지 전용이다. 기본 False=하위호환(기존 프롬프트 byte-동일).
        require_filter_gates: True면 매수(kind=='buy') 코드가 서로 다른 필터 범주를
            min_filter_categories개 이상 비교 조건으로 결합했는지 검증하고, 부족하면
            prior_error 설정 후 재시도한다(reject→재생성). 과발화 방지용 구조적 게이트
            (품질 판정 아님 — "충분히 게이트됐는가?"). 동시에 build_messages로 전달돼
            매수 프롬프트에 시드 게이팅 가이드를 주입한다. 매도(sell)에는 미적용.
            기본 False면 이 검사·프롬프트가 평가조차 안 돼 동작이 기존과 byte-동일하다.
        min_filter_categories: require_filter_gates=True일 때 요구하는 최소 필터 범주 수.
            시드는 9개 범주를 충족한다. require_filter_gates=False면 미사용(무영향).
        on_prompt: LLM 호출이 성공한 직후 그 프롬프트 레코드(dict)를 받는 선택적
            콜백(P1c 프롬프트 영속화). None이면 호출되지 않아 동작이 byte-identical
            하다(로깅 안 함=기존과 동일). 예외는 콜백 내부에서 흡수해 루프를 막지 않는다.

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
            crossover_parents=crossover_parents,
            autopsy_feedback=autopsy_feedback,
            history_summary=history_summary,
            meta_seed=meta_seed,
            prior_error=prior_error,
            dispersion_prompt_enabled=dispersion_prompt_enabled,
            target_daily_trades=target_daily_trades,
            mdd_control_enabled=mdd_control_enabled,
            encourage_time_dispersion=encourage_time_dispersion,
            require_filter_gates=require_filter_gates,
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

        # --- 1b) 프롬프트 영속화 콜백 (P1c) — LLM 호출 성공 직후, 가공 전 시점 ---
        #   on_prompt가 None(기본)이면 이 블록은 호출조차 안 돼 동작이 byte-identical
        #   하다(로깅 안 함=기존과 동일). prior_error는 **이번 attempt에 입력된** 값을
        #   로깅한다(루프 끝에서 갱신되기 전 시점이라 이번 호출의 입력 컨텍스트가 맞음).
        #   콜백 예외는 흡수한다 — 로깅 실패가 생성/루프를 막아선 안 된다.
        if on_prompt is not None:
            try:
                sys_text = next(
                    (m.get("content", "") for m in messages if m.get("role") == "system"), ""
                )
                usr_text = next(
                    (m.get("content", "") for m in messages if m.get("role") == "user"), ""
                )
                on_prompt({
                    "kind": kind, "attempt": attempt,
                    "system_text": sys_text, "user_text": usr_text,
                    "injected_features": {
                        "timeframe": timeframe,
                        "has_base_code": base_code is not None,
                        "has_crossover": crossover_parents is not None,
                        "has_meta_seed": meta_seed is not None,
                        "dispersion_prompt_enabled": dispersion_prompt_enabled,
                        "require_liquidity_gate": require_liquidity_gate,
                        "mdd_control_enabled": mdd_control_enabled,
                        "encourage_time_dispersion": encourage_time_dispersion,
                        "require_filter_gates": require_filter_gates,
                        "target_daily_trades": target_daily_trades,
                        "min_filter_categories": min_filter_categories,
                    },
                    "prior_error": prior_error,
                    "model": getattr(result, "model", None),
                    "usage": last_usage,
                    "response_text": getattr(result, "text", "") or "",
                })
            except Exception as _e:
                logger.info("prompt 로깅 실패(무시): %s", _e)

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

        # --- 4c) 거래대금 유동성 게이트 (Track B 2차; 매수 전용, 기본 OFF) ---
        #   R7 실측: refine가 빈도를 올릴 때 LLM이 흑자의 핵심인 거래대금 유동성
        #   게이트를 삭제해 흑자가 깨진다. require_liquidity_gate=True면 매수 코드에
        #   거래대금 비교 조건이 없을 때 reject→재시도한다. OFF면 단락되어 무영향.
        if require_liquidity_gate and kind == "buy" and not has_liquidity_gate(code):
            prior_error = (
                "흑자에 필수인 거래대금 유동성 게이트를 매수 조건에 반드시 포함하라 — "
                "예) 당일거래대금 > 임계값, 그리고 당일거래대금각도 같은 거래대금 가속 "
                "윈도우. 이 게이트를 빼면 진입 품질이 무너져 손실이 난다."
            )
            logger.info("attempt %d: 거래대금 게이트 누락", attempt)
            continue

        # --- 4d) 필터 범주 게이트 (생성 품질 (A); 매수 전용, 기본 OFF) — 과발화 방지 ---
        #   §3.22: refine가 진입 필터를 느슨하게/적게 만들어 과발화한다(매수=True·단일
        #   조건 → 750+ 거래·OOM). 시드는 ~9개 필터 범주를 AND로 결합한다. 품질 판정은
        #   불가(R7.4)지만 "충분히 게이트됐는가?"라는 구조적(범주 수) 검사는 가능하다.
        #   require_filter_gates=True면 매수 코드의 서로 다른 필터 범주 수가
        #   min_filter_categories 미만일 때 reject→재시도한다. OFF면 단락되어 무영향.
        if require_filter_gates and kind == "buy":
            from ai_strategy_loop.brain.filter_gate import count_filter_categories  # noqa: PLC0415
            _ncat = count_filter_categories(code)
            if _ncat < min_filter_categories:
                prior_error = (
                    f"매수 조건이 과발화 위험 — 서로 다른 필터 범주를 최소 {min_filter_categories}개 "
                    f"AND로 결합하라(현재 {_ncat}개). 시가총액·가격/등락율 밴드·당일거래대금 바닥+각도·"
                    f"체결강도·호가압력·시초 시간창 중에서 조합하라."
                )
                logger.info("attempt %d: 필터 범주 부족 (%d/%d)", attempt, _ncat, min_filter_categories)
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
