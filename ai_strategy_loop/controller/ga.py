"""P2 — GA(population 기반 진화) 루프 (자기완결 격리).

기존 hill-climb(best 1개 refine)은 greedy라 local optimum에 갇히고 다양성이
없어 불안정하다. `run_ga_loop`은 그 대안으로 **population 기반 진화**를 돈다:

  세대마다:
    1. population(K개 개체)을 warm_session.run으로 **직렬 평가**(K회) →
       compute_graded_fitness로 점수. 타임아웃/실패 개체는 graded 0으로 기록한다
       (robustness — 루프는 절대 크래시/행 안 함; loop._warm_to_outcome 재사용).
    2. graded 상위로 선택. 상위 ga_elite개는 **무변이 보존**(elitism).
    3. 다음 세대 생성:
         - crossover: 상위 부모 2개 코드를 LLM이 결합(build_messages crossover_parents).
         - mutation : 부모 1개 base_code refine(기존 generate_strategy 경로 재사용).
       자식이 가드(compile/token/scope/dedup) 재시도 소진(status error)이면
       → **elite 복제 또는 다른 부모 재변이로 population을 정확히 K 유지**(가드실패 fill).
    4. best/winner 추적(graded/하드게이트), 종료 판정(loop.should_terminate 재사용),
       state record + page_data['population'] 발행.

**run_loop에는 단일 분기만** 둔다(`evolution_mode=='ga'`면 여기로 위임). hillclimb
경로/_generate_pair/기존 테스트는 절대 건드리지 않는다.

세대당 wall-clock ≈ K×(warm run~50s). population을 작게 두는 이유다.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from ai_strategy_loop import bootstrap
from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.controller.history import GenRecord, build_history_summary
from ai_strategy_loop.controller.state import LoopState
from ai_strategy_loop.controller.termination import should_terminate

logger = logging.getLogger(__name__)


# =====================================================================
# 개체(Individual) — population의 한 원소.
# =====================================================================
class Individual:
    """population 한 개체. buy/sell 전략 이름 + 코드 + 평가 결과를 담는다.

    graded는 평가 전 None, 평가 후 graded 점수(float). 평가 실패(타임아웃/예외)는
    graded=0.0 + ok=False로 기록해 selection에서 자연히 하위로 밀린다(robustness).
    """

    __slots__ = (
        "buy_name", "sell_name", "buy_code", "sell_code",
        "graded", "gate_passed", "hard_score",
        "trade_count", "mdd", "profit", "gate_distance", "ok", "reason",
        "origin",
    )

    def __init__(self, buy_name: str, sell_name: str,
                 buy_code: Optional[str] = None, sell_code: Optional[str] = None,
                 origin: str = "init"):
        self.buy_name = buy_name
        self.sell_name = sell_name
        self.buy_code = buy_code
        self.sell_code = sell_code
        # 평가 결과(평가 전 기본값).
        self.graded: float = 0.0
        self.gate_passed: bool = False
        self.hard_score: Optional[float] = None
        self.trade_count: int = 0
        self.mdd: float = 0.0
        self.profit: float = 0.0
        self.gate_distance: str = ""
        self.ok: bool = False
        self.reason: str = ""
        # 계보 표시(init|seed|elite|crossover|mutation|fill). page_data/로그용.
        self.origin: str = origin


# =====================================================================
# 전략 생성 헬퍼 (mutation / crossover / fresh) — generate_strategy 재사용.
# =====================================================================
def _gen_one(provider, config: LoopConfig, kind: str, name: str,
             *, base_code: Optional[str] = None,
             crossover_parents: Optional[Tuple[str, str]] = None,
             autopsy_feedback: Optional[str] = None,
             history_summary: Optional[str] = None,
             dedup=None) -> Dict[str, Any]:
    """buy 또는 sell 한 쪽을 생성/저장한다(generate_strategy 얇은 래퍼).

    base_code(mutation) 또는 crossover_parents(crossover) 또는 둘 다 None(fresh)을
    그대로 generate_strategy에 전달한다. 가드(compile/token/scope/dedup) 재시도
    소진 시 {status:error}를 그대로 돌려준다(호출부가 fill 정책으로 처리).
    """
    from ai_strategy_loop.brain import generate_strategy  # noqa: PLC0415

    db = str(bootstrap.LOOP_DB_STRATEGY)
    return generate_strategy(
        provider, kind, name, db,
        timeframe=config.bt_timeframe,
        base_code=base_code,
        crossover_parents=crossover_parents,
        autopsy_feedback=autopsy_feedback,
        history_summary=history_summary,
        retry_max=config.max_retries + 1,
        dedup=dedup,
    )


def _make_child(provider, config: LoopConfig, rid: str, gen_no: int, slot: int,
                *, mode: str, parents: List[Individual],
                history_summary: Optional[str], dedup) -> Optional[Individual]:
    """자식 개체 1개를 생성한다(buy+sell 둘 다 저장 성공해야 개체 성립).

    mode:
      'crossover' — parents[0], parents[1]의 코드를 LLM이 결합(부모 2개 필요).
      'mutation'  — parents[0]의 코드를 base_code로 점진 개선(부모 1개).
      'fresh'     — 출발점 없이 새로 생성(부모 없음).

    어느 한 쪽(buy/sell)이라도 가드 재시도 소진(status error)이면 None을 반환한다
    (호출부가 fill 정책으로 K를 유지한다). 둘 다 성공하면 Individual을 돌려준다.
    """
    buy_name = f"AILOOP_{rid}_g{gen_no}_p{slot}_buy"
    sell_name = f"AILOOP_{rid}_g{gen_no}_p{slot}_sell"

    buy_kwargs: Dict[str, Any] = {"history_summary": history_summary, "dedup": dedup}
    sell_kwargs: Dict[str, Any] = {"history_summary": history_summary, "dedup": dedup}
    if mode == "crossover" and len(parents) >= 2:
        buy_kwargs["crossover_parents"] = (parents[0].buy_code or "", parents[1].buy_code or "")
        sell_kwargs["crossover_parents"] = (parents[0].sell_code or "", parents[1].sell_code or "")
    elif mode == "mutation" and parents:
        buy_kwargs["base_code"] = parents[0].buy_code
        sell_kwargs["base_code"] = parents[0].sell_code
    # 'fresh'면 base/crossover 모두 없음(자연 fresh 생성).

    buy_res = _gen_one(provider, config, "buy", buy_name, **buy_kwargs)
    if buy_res.get("status") != "ok":
        logger.info("GA child buy 가드실패(slot=%d, mode=%s): %s", slot, mode, buy_res.get("reason"))
        return None
    sell_res = _gen_one(provider, config, "sell", sell_name, **sell_kwargs)
    if sell_res.get("status") != "ok":
        logger.info("GA child sell 가드실패(slot=%d, mode=%s): %s", slot, mode, sell_res.get("reason"))
        return None

    return Individual(
        buy_name, sell_name,
        buy_code=buy_res.get("code"), sell_code=sell_res.get("code"),
        origin=mode,
    )


def _clone_elite(elite: Individual) -> Individual:
    """elite 개체를 다음 세대로 무변이 복제한다(elitism + fill 폴백).

    같은 전략 이름/코드를 재사용한다(이미 DB에 저장돼 있으므로 재생성 불필요).
    평가 결과는 다음 세대에서 다시 채워지므로 origin만 'elite'로 표시한다.
    """
    return Individual(
        elite.buy_name, elite.sell_name,
        buy_code=elite.buy_code, sell_code=elite.sell_code,
        origin="elite",
    )


# =====================================================================
# 초기 population.
# =====================================================================
def _seed_individual(rid: str, seed_buy: str, seed_sell: str,
                     buy_code: Optional[str], sell_code: Optional[str]) -> Individual:
    """시드 전략을 0번 개체로 만든다(이미 DB에 있는 이름 그대로 사용)."""
    return Individual(seed_buy, seed_sell, buy_code=buy_code, sell_code=sell_code,
                      origin="seed")


def _build_initial_population(
    provider, config: LoopConfig, rid: str, k: int,
    *, seed_buy: Optional[str], seed_sell: Optional[str], dedup,
) -> List[Individual]:
    """초기 population(K개)을 만든다.

    - 시드가 있으면: 0번은 시드 그대로, 1..K-1은 시드 변이(mutation)로 채운다.
      (변이 가드실패 개체는 건너뛰고, 부족분은 fresh로 보충해 K에 최대한 근접시킨다.)
    - 시드가 없으면: 전부 fresh 생성으로 채운다.

    어떤 개체도 못 만들면(전부 가드실패) 빈 리스트가 될 수 있으나, 호출부
    run_ga_loop이 빈 population을 종료 사유로 안전 처리한다.
    """
    pop: List[Individual] = []
    has_seed = bool(seed_buy and seed_sell)

    if has_seed:
        seed_buy_code = _read_code(seed_buy, "buy")
        seed_sell_code = _read_code(seed_sell, "sell")
        seed = _seed_individual(rid, seed_buy, seed_sell, seed_buy_code, seed_sell_code)
        pop.append(seed)
        # 1..K-1: 시드 변이.
        for slot in range(1, k):
            child = _make_child(
                provider, config, rid, 0, slot,
                mode="mutation", parents=[seed],
                history_summary=None, dedup=dedup,
            )
            if child is not None:
                pop.append(child)
    else:
        for slot in range(k):
            child = _make_child(
                provider, config, rid, 0, slot,
                mode="fresh", parents=[],
                history_summary=None, dedup=dedup,
            )
            if child is not None:
                pop.append(child)

    # 부족분 fresh 보충(시드 변이가 가드실패로 빠진 경우).
    attempts = 0
    while len(pop) < k and attempts < k:
        attempts += 1
        child = _make_child(
            provider, config, rid, 0, len(pop) + 100 + attempts,
            mode="fresh", parents=[],
            history_summary=None, dedup=dedup,
        )
        if child is not None:
            pop.append(child)

    return pop


def _read_code(name: Optional[str], kind: str) -> Optional[str]:
    """루프 DB에서 전략 코드를 읽는다(loop._read_strategy_code 재사용)."""
    from ai_strategy_loop.controller.loop import _read_strategy_code  # noqa: PLC0415

    return _read_strategy_code(name, kind)


# =====================================================================
# 평가 (warm_session 직렬 K회) + 점수.
# =====================================================================
def _evaluate_individual(ind: Individual, config: LoopConfig, warm_session) -> None:
    """개체 1개를 백테 1회로 평가해 graded/하드게이트/거래·MDD·수익을 채운다.

    warm_session.run(buy,sell) → _warm_to_outcome → _score_outcome 흐름을 그대로
    재사용한다(loop와 동일 계약). 타임아웃/실패/점수실패는 graded=0.0 + ok=False로
    표준화한다(robustness — 절대 raise 안 함). warm_session 내부가 타임아웃 시
    _reset_engines+_reload_data로 복구하므로 다음 개체 평가는 영향받지 않는다.
    """
    from ai_strategy_loop.controller.loop import _score_outcome, _warm_to_outcome  # noqa: PLC0415

    try:
        outcome = _warm_to_outcome(warm_session.run(ind.buy_name, ind.sell_name))
    except Exception as exc:  # noqa: BLE001 - 어떤 예외든 흡수, 개체만 0점 처리.
        ind.graded = 0.0
        ind.ok = False
        ind.reason = f"backtest raised: {exc}"
        return

    if not outcome.ok:
        ind.graded = 0.0
        ind.ok = False
        ind.reason = f"backtest failed/timeout: {outcome.reason}"
        return

    fit, graded, err = _score_outcome(outcome, config)
    if fit is None or graded is None:
        ind.graded = 0.0
        ind.ok = False
        ind.reason = f"fitness failed: {err}"
        return

    ind.graded = float(graded.graded)
    ind.gate_passed = bool(fit.gate_passed)
    ind.hard_score = float(fit.score)
    ind.trade_count = int(fit.trade_count)
    ind.mdd = float(graded.mdd)
    ind.profit = float(graded.total_profit)
    ind.gate_distance = str(graded.gate_distance)
    ind.ok = True
    ind.reason = str(fit.reason)


def _evaluate_population(pop: List[Individual], config: LoopConfig, warm_session) -> None:
    """population 전체를 **직렬**로 평가한다(K회 warm run; 병렬 불가)."""
    for ind in pop:
        _evaluate_individual(ind, config, warm_session)


# =====================================================================
# 선택 + 다음 세대 생성.
# =====================================================================
def _select_sorted(pop: List[Individual]) -> List[Individual]:
    """graded 내림차순으로 정렬한 새 리스트를 반환한다(선택 그래디언트).

    동점이면 게이트 통과 → 거래수 적은 순(과매매 회피)으로 tie-break한다.
    """
    return sorted(
        pop,
        key=lambda i: (i.graded, 1 if i.gate_passed else 0, -i.trade_count),
        reverse=True,
    )


def _breed_next_population(
    provider, config: LoopConfig, rid: str, next_gen: int,
    ranked: List[Individual], k: int, elite_n: int,
    *, history_summary: Optional[str], dedup,
) -> Tuple[List[Individual], int]:
    """다음 세대 population(정확히 K개)을 만든다.

    1. elitism: 상위 elite_n개를 무변이 복제(_clone_elite).
    2. 나머지 K-elite_n개: ga_crossover_rate 비율로 crossover, 나머지는 mutation.
       부모는 상위 개체(ranked)에서 고른다.
    3. **가드실패 fill 정책(필수)**: 자식이 가드 재시도 소진(None)이면
       → 최우수 elite 복제 또는 다른 부모 재변이로 채워 **정확히 K를 유지**한다.

    Returns:
        (next_population, guardfail_count) — guardfail_count는 가드실패 자식 수.
    """
    if not ranked:
        return [], 0

    elite_n = max(0, min(elite_n, k, len(ranked)))
    next_pop: List[Individual] = [_clone_elite(e) for e in ranked[:elite_n]]

    crossover_rate = float(getattr(config, "ga_crossover_rate", 0.5) or 0.0)
    n_children = k - elite_n
    # crossover 자식 수(결정론적): rate 비율. 부모가 2개 미만이면 crossover 불가 → 0.
    can_crossover = len(ranked) >= 2
    n_crossover = int(round(n_children * crossover_rate)) if can_crossover else 0
    n_crossover = max(0, min(n_crossover, n_children))

    guardfail = 0
    slot = 0
    for child_idx in range(n_children):
        mode = "crossover" if child_idx < n_crossover else "mutation"
        parents = _pick_parents(ranked, mode)
        child = _make_child(
            provider, config, rid, next_gen, slot,
            mode=mode, parents=parents,
            history_summary=history_summary, dedup=dedup,
        )
        slot += 1
        if child is None:
            # 가드실패 → fill: 다른 부모 재변이를 한 번 시도, 그래도 실패면 elite 복제.
            guardfail += 1
            child = _fill_one(
                provider, config, rid, next_gen, slot, ranked, dedup, history_summary,
            )
            slot += 1
            if child is None:
                child = _clone_elite(ranked[0])
        next_pop.append(child)

    # 안전장치: 라운딩/예외로 K에 못 미치면 elite 복제로 정확히 K 채운다.
    while len(next_pop) < k:
        next_pop.append(_clone_elite(ranked[0]))
    # 초과(이론상 없음)면 잘라 정확히 K 유지.
    return next_pop[:k], guardfail


def _pick_parents(ranked: List[Individual], mode: str) -> List[Individual]:
    """mode에 맞는 부모를 ranked 상위에서 고른다.

    crossover면 상위 2개, mutation/fresh면 상위 1개. ranked가 부족하면 있는 만큼.
    """
    if mode == "crossover":
        return ranked[:2] if len(ranked) >= 2 else ranked[:1]
    return ranked[:1]


def _fill_one(provider, config: LoopConfig, rid: str, next_gen: int, slot: int,
              ranked: List[Individual], dedup, history_summary) -> Optional[Individual]:
    """가드실패 fill: 다른 부모(2순위)로 mutation 재시도 1회. 실패면 None.

    호출부가 None이면 최우수 elite 복제로 폴백해 K를 유지한다.
    """
    alt_parent = ranked[1] if len(ranked) >= 2 else ranked[0]
    return _make_child(
        provider, config, rid, next_gen, slot,
        mode="mutation", parents=[alt_parent],
        history_summary=history_summary, dedup=dedup,
    )


# =====================================================================
# page_data 직렬화 + 이력.
# =====================================================================
def _population_page_data(pop: List[Individual], gen_no: int, guardfail: int) -> Dict[str, Any]:
    """population을 LIVE 패널용 page_data['population']로 직렬화한다.

    개체별 graded/거래/MDD/수익/gate + 계보(origin) + 가드실패 카운트를 담는다.
    """
    ranked = _select_sorted(pop)
    members = [
        {
            "buy_name": ind.buy_name,
            "sell_name": ind.sell_name,
            "graded": round(float(ind.graded), 6),
            "gate_passed": bool(ind.gate_passed),
            "trade_count": int(ind.trade_count),
            "mdd": round(float(ind.mdd), 4),
            "profit": round(float(ind.profit), 2),
            "origin": ind.origin,
            "ok": bool(ind.ok),
            "gate_distance": ind.gate_distance,
        }
        for ind in ranked
    ]
    graded_vals = [float(i.graded) for i in pop]
    return {
        "status": "ok",
        "gen_no": gen_no,
        "k": len(pop),
        "guardfail_count": int(guardfail),
        "best_graded": round(max(graded_vals), 6) if graded_vals else 0.0,
        "gate_passed_count": sum(1 for i in pop if i.gate_passed),
        "members": members,
    }


def _record_and_history(
    st: LoopState, rid: str, gen_no: int, ind: Individual,
    history_records: List[GenRecord],
) -> None:
    """대표 개체(best) 1개를 generations DB에 기록하고 이력에 추가한다.

    GA는 세대당 K개를 평가하지만, generations 테이블은 (run_id, gen_no) 1행
    스키마라 세대 best 개체를 대표로 기록한다(대시보드 세대 행/요약 호환).
    """
    st.record_generation(
        rid, gen_no,
        buy_name=ind.buy_name, sell_name=ind.sell_name,
        status="ok" if ind.ok else "error",
        score=float(ind.graded),
        gate_passed=bool(ind.gate_passed),
        reason=ind.reason or ind.gate_distance,
        trade_count=int(ind.trade_count),
        mdd=float(ind.mdd), profit=float(ind.profit),
        strategy_gist=_gist(ind.buy_name),
    )
    history_records.append(GenRecord(
        gen_no=gen_no, graded_score=float(ind.graded),
        gate_passed=bool(ind.gate_passed), gate_reason=ind.gate_distance,
        trade_count=int(ind.trade_count), mdd=float(ind.mdd),
        profit=float(ind.profit), gist=_gist(ind.buy_name),
    ))


def _gist(name: str) -> str:
    from ai_strategy_loop.controller.loop import _strategy_gist  # noqa: PLC0415

    try:
        return _strategy_gist(name)
    except Exception:  # noqa: BLE001 - gist는 보조이므로 실패해도 빈 문자열.
        return ""


def _publish(st: LoopState, rid: str, config: LoopConfig, **kwargs) -> None:
    """loop._publish_live 재사용(라이브 발행). 발행 실패는 루프를 막지 않는다."""
    from ai_strategy_loop.controller.loop import _publish_live  # noqa: PLC0415

    try:
        _publish_live(st, rid, config, **kwargs)
    except Exception:  # noqa: BLE001 - 라이브 발행은 정확성 경로가 아니다.
        pass


# =====================================================================
# 메인: run_ga_loop (run_loop이 단일 분기로 위임).
# =====================================================================
def run_ga_loop(
    config: LoopConfig,
    warm_session,
    provider,
    state: LoopState,
    rid: str,
    *,
    seed_buy: Optional[str] = None,
    seed_sell: Optional[str] = None,
) -> Dict[str, Any]:
    """GA(population 기반 진화) 루프를 끝까지 돌리고 요약을 반환한다.

    run_loop이 워밍업(warm_session.prepare) 직후 evolution_mode=='ga'일 때 위임한다.
    warm_session/provider/state/rid는 run_loop이 이미 준비한 것을 받는다(자기완결이되
    워밍업·provider·state 생명주기는 run_loop이 소유; close/proxy/clear는 run_loop finally).

    Args:
        config: LoopConfig (ga_population/ga_elite/ga_crossover_rate 포함).
        warm_session: prepare 완료된 WarmBacktestSession (None이면 평가 불가 → 즉시 종료).
        provider: chat()를 가진 LLM provider.
        state: run_loop이 만든 LoopState(이미 resume_or_start 됨).
        rid: run_id.
        seed_buy/seed_sell: 초기 population 시드(있으면 시드+변이, 없으면 cold 생성).

    Returns:
        run_loop과 동일한 요약 dict(run_id/generations/best_*/winner_*/stop_reason).
    """
    from ai_strategy_loop.brain.token_check import DedupTracker  # noqa: PLC0415

    st = state
    k = max(1, int(getattr(config, "ga_population", 6) or 6))
    elite_n = max(0, int(getattr(config, "ga_elite", 2) or 0))

    best_gen = -1
    best_score: Optional[float] = None
    best_buy: Optional[str] = None
    best_sell: Optional[str] = None
    winner_gen = -1
    winner_score: Optional[float] = None
    winner_buy: Optional[str] = None
    winner_sell: Optional[str] = None
    stop_reason = "continue"
    cumulative_tokens = 0  # GA는 토큰 합산을 추적하지 않음(gpt_auth 세대-수 cap 경로).
    history_records: List[GenRecord] = []
    dedup = DedupTracker(k=max(5, k))

    if warm_session is None:
        # warm 평가 불가 → GA는 직렬 평가 모델이므로 cold 폴백 없이 즉시 종료.
        #   (cold 경로는 hillclimb이 담당; GA는 warm 세션 가정.)
        summary = _summary(rid, 0, best_gen, best_score, best_buy, best_sell,
                           winner_gen, winner_score, winner_buy, winner_sell,
                           "ga_no_warm_session")
        return summary

    _publish(st, rid, config, status="running", current_gen=0,
             cumulative_tokens=cumulative_tokens, phase="ga_init",
             message=f"GA 초기 population 생성 시작 (K={k})")

    # --- 초기 population ---
    pop = _build_initial_population(
        provider, config, rid, k,
        seed_buy=seed_buy, seed_sell=seed_sell, dedup=dedup,
    )
    if not pop:
        summary = _summary(rid, 0, best_gen, best_score, best_buy, best_sell,
                           winner_gen, winner_score, winner_buy, winner_sell,
                           "ga_initial_population_empty")
        st.finish_run(rid, status="complete")
        return summary

    gen_no = 0
    guardfail = 0
    while True:
        # --- 종료 판정(loop.should_terminate 재사용) ---
        from ai_strategy_loop.controller.state import stop_requested  # noqa: PLC0415

        if stop_requested():
            stop_reason = "stop_requested"
            break
        stop, reason = should_terminate(
            {
                "best_score": winner_score,
                "gen_count": st.get_cumulative_generation_count(rid),
                "tokens": cumulative_tokens,
            },
            config,
        )
        if stop:
            stop_reason = reason
            break

        print(f"\n[GA] === generation {gen_no} (run={rid}, K={len(pop)}) ===", flush=True)
        bootstrap.ensure_loop_db_engine_compat()

        # --- 평가(직렬 K회) ---
        _publish(st, rid, config, status="running", current_gen=gen_no,
                 cumulative_tokens=cumulative_tokens, phase="ga_evaluate_start",
                 message=f"GA gen {gen_no} 평가 시작 (K={len(pop)})",
                 best_gen=best_gen, best_score=best_score,
                 best_buy=best_buy, best_sell=best_sell,
                 winner_gen=winner_gen, winner_score=winner_score,
                 winner_buy=winner_buy, winner_sell=winner_sell)
        t0 = time.time()
        _evaluate_population(pop, config, warm_session)
        elapsed = time.time() - t0
        print(f"[GA] gen {gen_no} 평가 완료 elapsed={elapsed:.1f}s", flush=True)

        # --- 선택 + best/winner 추적 ---
        ranked = _select_sorted(pop)
        gen_best = ranked[0]
        if best_score is None or gen_best.graded > best_score:
            best_score = gen_best.graded
            best_gen = gen_no
            best_buy = gen_best.buy_name
            best_sell = gen_best.sell_name
            st.update_best(rid, best_gen, best_score)
        # winner: 하드 게이트 통과 개체 중 하드 점수 최고.
        for ind in ranked:
            if ind.gate_passed and ind.hard_score is not None and (
                winner_score is None or ind.hard_score > winner_score
            ):
                winner_score = ind.hard_score
                winner_gen = gen_no
                winner_buy = ind.buy_name
                winner_sell = ind.sell_name

        # --- 기록(대표 개체) + 이력 + page_data 발행 ---
        _record_and_history(st, rid, gen_no, gen_best, history_records)
        page_data = {"population": _population_page_data(pop, gen_no, guardfail)}
        _publish(st, rid, config, status="running", current_gen=gen_no,
                 cumulative_tokens=cumulative_tokens, phase="ga_generation_done",
                 message=f"GA gen {gen_no} recorded (best graded={gen_best.graded:.4g})",
                 best_gen=best_gen, best_score=best_score,
                 best_buy=best_buy, best_sell=best_sell,
                 winner_gen=winner_gen, winner_score=winner_score,
                 winner_buy=winner_buy, winner_sell=winner_sell,
                 page_data=page_data)

        # --- 다음 세대 생성(elitism + crossover + mutation + 가드실패 fill) ---
        history_summary = build_history_summary(history_records)
        next_pop, guardfail = _breed_next_population(
            provider, config, rid, gen_no + 1, ranked, k, elite_n,
            history_summary=history_summary, dedup=dedup,
        )
        if not next_pop:
            stop_reason = "ga_breed_empty"
            break
        pop = next_pop
        gen_no += 1

    st.finish_run(rid, status="complete")
    _publish(st, rid, config, status="complete", current_gen=gen_no,
             cumulative_tokens=cumulative_tokens, phase="complete",
             message=f"GA loop complete: {stop_reason}",
             best_gen=best_gen, best_score=best_score,
             best_buy=best_buy, best_sell=best_sell,
             winner_gen=winner_gen, winner_score=winner_score,
             winner_buy=winner_buy, winner_sell=winner_sell)

    return _summary(
        rid, st.get_cumulative_generation_count(rid),
        best_gen, best_score, best_buy, best_sell,
        winner_gen, winner_score, winner_buy, winner_sell, stop_reason,
    )


def _summary(rid, generations, best_gen, best_score, best_buy, best_sell,
             winner_gen, winner_score, winner_buy, winner_sell, stop_reason) -> Dict[str, Any]:
    """run_loop과 동일한 요약 dict를 구성한다(상위 호출부 호환)."""
    return {
        "run_id": rid,
        "generations": generations,
        "best_gen": best_gen,
        "best_score": best_score,
        "best_buy": best_buy,
        "best_sell": best_sell,
        "winner_gen": winner_gen,
        "winner_score": winner_score,
        "winner_buy": winner_buy,
        "winner_sell": winner_sell,
        "stop_reason": stop_reason,
    }
