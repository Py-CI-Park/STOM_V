"""패치 매도식 반사실 리플레이 — 순수 스칼라 / 벡터 (엔진 미러 재사용).

봉인 근거: 2026-07-12_d5r_conditional_exit_preregistration.md §4 후보 격자.

현직 rr8_12 매도식(replay.CHAMPION_SELL_CONDS / labels_v2._eval_row_clause)을
정본으로 두고, §4 사전값 그대로 절을 국소 변형한다:

  - Family A (트레일링 완화): 현직 절5 `최고수익률 * 0.6 >= 수익률` 의 keep
    배수만 하향(0.55 / 0.50). 절 추가·삭제 없음(발동만 더 늦춤 = 승자 연장).
  - Family B (저활력 조기 절단): `if 시가총액 < 10000:` 블록 최하단에 신규
    sub-elif 추가 — `보유시간 >= T and 최고수익률 < x and 수익률 < y`. 현직
    하드/트레일/각도급락/MA 절이 먼저 평가되고 어느 것도 발동 안 한 잔여
    집합에만 도달(절 순서 보존). 어트리뷰션 태그 = B_CLAUSE_TAG.

체결·수익률 의미론은 replay.replay_champion_exit 와 100% 동일하다
(kiwoom_pgsgsp 실측식 + 매수호가 사다리 _ladder_fill + 일 마지막 행 LastSell).
identity 패치(patch=None)는 replay_champion_exit 와 바이트 동치여야 한다
(단위 테스트·L3 게이트로 봉쇄). tick DB 접근은 read-only, print 금지 — logging.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Tuple

import numpy as np

from alpha_lab.dataset.labels_v2 import DayContext, _vector_sp
from alpha_lab.distill.replay import _ladder_fill, kiwoom_pgsgsp

__all__ = [
    "B_CLAUSE_TAG",
    "ExitResult",
    "Patch",
    "PathAnalysis",
    "analyze_path",
    "eval_row_clause_patched",
    "replay_patched_pure",
    "replay_patched_vector",
    "time_stop_cut",
]

logger = logging.getLogger(__name__)

# 신규 Family B 절 어트리뷰션 태그(현직 절 0~9와 충돌 없는 값).
B_CLAUSE_TAG = 100

# 현직 절5 keep 배수(변형 대상). Family A 는 이 값만 낮춘다.
_INCUMBENT_TRAILING_KEEP = 0.6


@dataclass(frozen=True)
class Patch:
    """청산 절 국소 변형 명세(봉인 사전값).

    family:
      - None       : 현직(identity) — replay_champion_exit 와 동치.
      - 'A'        : 절5 배수 하향. mult 필수(0.55|0.50).
      - 'B'        : 신규 저활력 절. T·x·y 필수.
    """

    family: Optional[str] = None
    mult: Optional[float] = None          # Family A keep 배수.
    T: Optional[int] = None               # Family B 보유시간 하한(초).
    x: Optional[float] = None             # Family B 최고수익률 상한(미만).
    y: Optional[float] = None             # Family B 수익률 상한(미만).
    label: str = "incumbent"

    def __post_init__(self) -> None:
        if self.family is None:
            return
        if self.family == "A":
            if self.mult is None or not (0.0 < self.mult < _INCUMBENT_TRAILING_KEEP):
                raise ValueError(f"Family A mult 는 (0, 0.6) 이어야 한다: {self.mult}")
        elif self.family == "B":
            if self.T is None or self.x is None or self.y is None:
                raise ValueError("Family B 는 T·x·y 가 모두 필요하다")
        else:
            raise ValueError(f"알 수 없는 family: {self.family!r}")

    @property
    def trailing_keep(self) -> float:
        return float(self.mult) if self.family == "A" else _INCUMBENT_TRAILING_KEEP


@dataclass(frozen=True)
class ExitResult:
    """반사실 청산 1건의 결과(순수·벡터 공통 계약)."""

    status: str
    sell_time: int = 0
    sell_price: float = 0.0
    profit_pct: float = 0.0        # kiwoom_pgsgsp 수익률(%) — 원장 수익률과 동일 단위.
    profit_won: int = 0            # kiwoom_pgsgsp 수익금(원, int).
    cond: int = 0                  # 발동 절(0=LastSell, 1~9 현직, 100=Family B).
    best: float = 0.0              # 청산 시점까지 누적 최고수익률.
    worst: float = 0.0
    hold_exit: int = 0             # 청산 보유시간(초).


# ---------------------------------------------------------------------------
# 순수 스칼라 경로 — labels_v2._eval_row_clause 미러 + 패치.
# ---------------------------------------------------------------------------

def eval_row_clause_patched(
    ctx: DayContext, i: int, *, sp: float, best: float, hold: int, patch: Patch
) -> Optional[int]:
    """행 i 매도식 절 평가(패치 반영) — 발동 절 번호 또는 None.

    labels_v2._eval_row_clause 와 절·게이트·연산 순서 동일. Family A 는 절5
    배수만, Family B 는 cap<10000 블록 최하단 신규 절만 추가한다.
    """
    tick_count = i + 1
    cur = float(ctx.price[i])
    open_price = float(ctx.open_[i])
    pct = float(ctx.pct[i])
    open_vs = ((cur - open_price) / open_price) * 100 if open_price else 0.0
    hms = int(ctx.idxs[i]) % 1_000_000

    def low_price(tick: int, pre_n: int) -> float:
        if tick + pre_n <= tick_count:
            s, e = i + 1 - tick - pre_n, i + 1 - pre_n
            return float(ctx.price[s:e].min())
        return 0.0

    def ma(tick: int, pre_n: int = 0) -> float:
        if tick + pre_n <= tick_count:
            return float(ctx.ma60[i - pre_n])
        return 0.0

    def angle(pre_n: int = 0) -> float:
        if 30 + pre_n <= tick_count:
            return float(ctx.ang30[i - pre_n])
        return 0.0

    prev_price = float(ctx.prev[i])
    sell_vol = float(ctx.sellv[i])
    buy_vol = float(ctx.buyv[i])
    bid_total = float(ctx.bidtot[i])
    cap = float(ctx.cap[i])
    keep = patch.trailing_keep

    if pct > 29.5:
        return 1
    if open_vs < 0 and sp <= -2.0 and cur < low_price(60, int(hold)):
        return 2
    if hold > 60 and cur < low_price(60, int(hold)):
        return 3
    if hms < 93000:
        if sp >= 9 or sp <= -5.0:
            return 4
        if best > 3 and best * keep >= sp:          # 절5 (Family A: keep 하향).
            return 5
        if cap < 10000:
            drop = (cur / prev_price - 1) * 100 if prev_price else 0.0
            if angle() >= 10 and (sell_vol - buy_vol) >= bid_total * 0.5 and drop < -0.5:
                return 6
            if 5 <= angle() < 10 and (sell_vol - buy_vol) >= bid_total * 0.7 and drop < -0.7:
                return 7
            if 0 <= angle() < 5 and (sell_vol - buy_vol) >= bid_total * 0.8 and drop < -0.5:
                return 8
            if 4.5 < best and prev_price >= ma(60, 1) and ma(60) > cur:
                return 9
            if patch.family == "B" and hold >= patch.T \
                    and best < patch.x and sp < patch.y:   # 신규 저활력 절.
                return B_CLAUSE_TAG
    return None


def _fill_and_pack(
    ctx: DayContext, i: int, *, bg: float, qty: int, sp_row: float,
    best: float, worst: float, hold: int, cond: int,
) -> Optional[ExitResult]:
    """행 i 사다리 체결 → ExitResult (잔량 부족 시 None = 미체결 보유 지속)."""
    sell_price = _ladder_fill(
        qty,
        [float(ctx.bid1[i]), float(ctx.bid2[i]), float(ctx.bid3[i])],
        [float(ctx.rem1[i]), float(ctx.rem2[i]), float(ctx.rem3[i])],
    )
    if sell_price is None:
        return None
    _, sg, ssp = kiwoom_pgsgsp(bg, qty * sell_price)
    return ExitResult(
        status="ok", sell_time=int(ctx.idxs[i]), sell_price=float(sell_price),
        profit_pct=float(ssp), profit_won=int(sg), cond=int(cond),
        best=float(best), worst=float(worst), hold_exit=int(hold),
    )


def _last_sell(ctx: DayContext, *, bg: float, qty: int, entry_sec: int,
               best: float, worst: float) -> ExitResult:
    """일 마지막 행 LastSell — 사다리 실패 시 매수호가1 강제(엔진 미러)."""
    last = ctx.n - 1
    sell_price = _ladder_fill(
        qty,
        [float(ctx.bid1[last]), float(ctx.bid2[last]), float(ctx.bid3[last])],
        [float(ctx.rem1[last]), float(ctx.rem2[last]), float(ctx.rem3[last])],
    )
    if sell_price is None:
        sell_price = float(int(ctx.bid1[last] + 0.5))
    _, sg, ssp = kiwoom_pgsgsp(bg, qty * sell_price)
    return ExitResult(
        status="ok", sell_time=int(ctx.idxs[last]), sell_price=float(sell_price),
        profit_pct=float(ssp), profit_won=int(sg), cond=0,
        best=float(best), worst=float(worst),
        hold_exit=int(ctx.sec[last]) - int(entry_sec),
    )


def replay_patched_pure(
    ctx: DayContext, *, buy_time: int, buy_price: float, qty: int, patch: Patch
) -> ExitResult:
    """순수 스칼라 반사실 리플레이 — replay_champion_exit 미러(+패치)."""
    n = ctx.n
    pos = int(np.searchsorted(ctx.idxs, int(buy_time)))
    if pos >= n or int(ctx.idxs[pos]) != int(buy_time):
        return ExitResult(status="entry_row_missing")
    bg = qty * float(buy_price)
    entry_sec = int(ctx.sec[pos])
    best = 0.0
    worst = 0.0
    for i in range(pos + 1, n):
        if i == n - 1:
            break  # 일 마지막 행 LastSell 전용.
        _, _, sp = kiwoom_pgsgsp(bg, qty * float(ctx.price[i]))
        if sp > best:
            best = sp
        elif sp < worst:
            worst = sp
        hold = int(ctx.sec[i]) - entry_sec
        clause = eval_row_clause_patched(
            ctx, i, sp=sp, best=best, hold=hold, patch=patch
        )
        if clause is None:
            continue
        packed = _fill_and_pack(
            ctx, i, bg=bg, qty=qty, sp_row=sp, best=best, worst=worst,
            hold=hold, cond=clause,
        )
        if packed is None:
            continue  # 잔량 부족 — 미체결 보유 지속.
        return packed
    return _last_sell(ctx, bg=bg, qty=qty, entry_sec=entry_sec,
                      best=best, worst=worst)


# ---------------------------------------------------------------------------
# 벡터 경로 — labels_v2._fire_arrays 미러 + 패치.
# ---------------------------------------------------------------------------

def _patched_fire_arrays(
    ctx: DayContext, *, lo: int, hi: int, entry_pos: int, bg: float,
    qty: int, patch: Patch,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """행 구간 [lo, hi) 의 (fire, sp, best, hold) 벡터 — labels_v2._fire_arrays +패치."""
    price = ctx.price[lo:hi]
    sp = _vector_sp(bg, float(qty) * price)
    best = np.maximum.accumulate(np.maximum(sp, 0.0))
    hold = ctx.sec[lo:hi] - int(ctx.sec[entry_pos])
    abs_i = np.arange(lo, hi, dtype=np.int64)
    j = abs_i - hold
    valid_low = j >= 59
    lowv = np.where(valid_low, ctx.rmin60[np.clip(j, 0, ctx.n - 1)], 0.0)
    low_fire = price < lowv
    c2 = ctx.open_neg[lo:hi] & (sp <= -2.0) & low_fire
    c3 = (hold > 60) & low_fire
    c4 = (sp >= 9.0) | (sp <= -5.0)
    c5 = (best > 3.0) & (best * patch.trailing_keep >= sp)
    c69 = ctx.capgate[lo:hi] & (
        ctx.c6_row[lo:hi] | ctx.c7_row[lo:hi] | ctx.c8_row[lo:hi]
        | ((best > 4.5) & ctx.c9_row[lo:hi])
    )
    tail = c4 | c5 | c69
    if patch.family == "B":
        cB = ctx.capgate[lo:hi] & (hold >= int(patch.T)) \
            & (best < float(patch.x)) & (sp < float(patch.y))
        tail = tail | cB
    fire = ctx.c1_row[lo:hi] | c2 | c3 | (ctx.tgate[lo:hi] & tail)
    return fire, sp, best, hold


def replay_patched_vector(
    ctx: DayContext, *, buy_time: int, buy_price: float, qty: int, patch: Patch
) -> ExitResult:
    """벡터 반사실 리플레이 — replay_champion_exit_vector 미러(+패치).

    벡터 fire 와 스칼라 절 어트리뷰션이 어긋나면 RuntimeError(조용한 드리프트
    금지 — 신규 절 포함 판정을 스칼라로 재확인).
    """
    n = ctx.n
    pos = int(np.searchsorted(ctx.idxs, int(buy_time)))
    if pos >= n or int(ctx.idxs[pos]) != int(buy_time):
        return ExitResult(status="entry_row_missing")
    bg = qty * float(buy_price)
    entry_sec = int(ctx.sec[pos])
    lo, hi = pos + 1, n - 1  # 마지막 행 LastSell 전용.
    best_final = 0.0
    worst_final = 0.0
    if hi > lo:
        fire, sp, best, hold = _patched_fire_arrays(
            ctx, lo=lo, hi=hi, entry_pos=pos, bg=bg, qty=qty, patch=patch
        )
        worst = np.minimum.accumulate(np.minimum(sp, 0.0))
        for r in np.flatnonzero(fire):
            i = lo + int(r)
            clause = eval_row_clause_patched(
                ctx, i, sp=float(sp[r]), best=float(best[r]),
                hold=int(hold[r]), patch=patch,
            )
            if clause is None:
                raise RuntimeError(
                    f"벡터/스칼라 절 평가 불일치: row={i} idx={int(ctx.idxs[i])}"
                )
            packed = _fill_and_pack(
                ctx, i, bg=bg, qty=qty, sp_row=float(sp[r]),
                best=float(best[r]), worst=float(worst[r]),
                hold=int(hold[r]), cond=clause,
            )
            if packed is None:
                continue  # 잔량 부족 — 미체결 보유 지속.
            return packed
        best_final = float(best[-1])
        worst_final = float(worst[-1])
    return _last_sell(ctx, bg=bg, qty=qty, entry_sec=entry_sec,
                      best=best_final, worst=worst_final)


# ---------------------------------------------------------------------------
# R1 포렌식 — t=T 상태 재구성 + 순수 time_stop 절단(도움/해악 map).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PathAnalysis:
    """한 거래의 보유경로 실측 — 현직 청산 + T별 t=T 상태·순수 절단."""

    status: str
    inc_time: int = 0
    inc_hold: int = 0
    inc_pct: float = 0.0
    inc_won: int = 0
    inc_cond: int = 0
    inc_best: float = 0.0
    # T별: held(보유≥T 여부), best_T, sp_T, 절단 net(%), 절단 won.
    per_T: Optional[Dict[int, Dict[str, float]]] = None


def _cut_at(
    ctx: DayContext, *, lo_row: int, hi: int, bg: float, qty: int,
) -> Optional[Tuple[int, float, int]]:
    """행 lo_row 부터 유효 사다리 체결을 찾아 (sell_time, pct, won) 반환.

    순수 time_stop 절단 — 첫 관측 행(hold≥T)에서 체결, 잔량 부족 시 다음 행.
    """
    for i in range(lo_row, hi):
        sell_price = _ladder_fill(
            qty,
            [float(ctx.bid1[i]), float(ctx.bid2[i]), float(ctx.bid3[i])],
            [float(ctx.rem1[i]), float(ctx.rem2[i]), float(ctx.rem3[i])],
        )
        if sell_price is None:
            continue
        _, sg, ssp = kiwoom_pgsgsp(bg, qty * sell_price)
        return int(ctx.idxs[i]), float(ssp), int(sg)
    return None


def analyze_path(
    ctx: DayContext, *, buy_time: int, buy_price: float, qty: int,
    Ts: Tuple[int, ...] = (120, 180, 240),
) -> PathAnalysis:
    """현직 청산 + T별 t=T 상태(누적최고·수익률)·순수 절단 net 을 한 번에 실측.

    held(보유≥T) = 현직 청산 보유시간 ≥ T. t=T 상태는 hold≥T 인 첫 관측 행의
    (누적최고수익률, 수익률). 절단 net 은 그 행부터의 유효 사다리 체결.
    """
    inc = replay_patched_pure(
        ctx, buy_time=buy_time, buy_price=buy_price, qty=qty, patch=Patch()
    )
    if inc.status != "ok":
        return PathAnalysis(status=inc.status)
    n = ctx.n
    pos = int(np.searchsorted(ctx.idxs, int(buy_time)))
    bg = qty * float(buy_price)
    entry_sec = int(ctx.sec[pos])
    # 누적최고·수익률 궤적(첫 hold≥T 행 탐색용).
    per_T: Dict[int, Dict[str, float]] = {}
    best = 0.0
    row_state: Dict[int, Tuple[int, float, float]] = {}  # T -> (row, best_T, sp_T)
    remaining = set(int(t) for t in Ts)
    for i in range(pos + 1, n):
        _, _, sp = kiwoom_pgsgsp(bg, qty * float(ctx.price[i]))
        if sp > best:
            best = sp
        hold = int(ctx.sec[i]) - entry_sec
        for t in list(remaining):
            if hold >= t:
                row_state[t] = (i, best, sp)
                remaining.discard(t)
        if not remaining:
            break
    for t in Ts:
        t = int(t)
        held = int(inc.hold_exit >= t)
        entry = {"held": held, "best_T": float("nan"), "sp_T": float("nan"),
                 "cut_pct": float("nan"), "cut_won": float("nan"),
                 "cut_time": 0.0}
        if held and t in row_state:
            row, best_T, sp_T = row_state[t]
            entry["best_T"] = float(best_T)
            entry["sp_T"] = float(sp_T)
            cut = _cut_at(ctx, lo_row=row, hi=n, bg=bg, qty=qty)
            if cut is not None:
                entry["cut_time"] = float(cut[0])
                entry["cut_pct"] = float(cut[1])
                entry["cut_won"] = float(cut[2])
        per_T[t] = entry
    return PathAnalysis(
        status="ok", inc_time=int(inc.sell_time), inc_hold=int(inc.hold_exit),
        inc_pct=float(inc.profit_pct), inc_won=int(inc.profit_won),
        inc_cond=int(inc.cond), inc_best=float(inc.best), per_T=per_T,
    )


def time_stop_cut(
    ctx: DayContext, *, buy_time: int, buy_price: float, qty: int, T: int
) -> ExitResult:
    """순수 time_stop(보유≥T 즉시 절단) 반사실 — R1 도움/해악 대조군.

    현직 절을 전부 무시하고 hold≥T 인 첫 관측 행에서 절단한다(P5 기각
    전역 time_stop 의 재현 — Family B 겹침·kill-1 대조 기준).
    """
    n = ctx.n
    pos = int(np.searchsorted(ctx.idxs, int(buy_time)))
    if pos >= n or int(ctx.idxs[pos]) != int(buy_time):
        return ExitResult(status="entry_row_missing")
    bg = qty * float(buy_price)
    entry_sec = int(ctx.sec[pos])
    for i in range(pos + 1, n):
        hold = int(ctx.sec[i]) - entry_sec
        if hold < int(T):
            continue
        cut = _cut_at(ctx, lo_row=i, hi=n, bg=bg, qty=qty)
        if cut is None:
            break
        return ExitResult(
            status="ok", sell_time=cut[0], sell_price=0.0, profit_pct=cut[1],
            profit_won=cut[2], cond=B_CLAUSE_TAG, best=0.0, worst=0.0,
            hold_exit=int(ctx.sec[np.searchsorted(ctx.idxs, cut[0])]) - entry_sec,
        )
    return _last_sell(ctx, bg=bg, qty=qty, entry_sec=entry_sec, best=0.0, worst=0.0)
