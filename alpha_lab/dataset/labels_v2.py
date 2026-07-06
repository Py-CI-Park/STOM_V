"""L3_replay 라벨러 v2 — 챔피언 현직 매도식 리플레이 기반 실현 net_rate 라벨.

봉인 근거: docs/research/condition_research/research_runs/alpha_lab_v2_20260706/
preregistration_v2.json (sha dcac7492...) label_spec_v2 그대로:
  - entry  = (t0+1초) 매도호가1 + 2틱 불리 — v1 비용 모형(labels.adverse_fill,
    krx 2023 개편 공통 호가단위) 동일.
  - 경로   = t0+1 이후 관측 초들에 대해 챔피언 현직 매도식 원문
    (GATE_rr8_12..., sha256 8ef01e0e...) 전체 절 평가 —
    alpha_lab.distill.replay 의 엔진 미러(_eval_sell_clauses 의미론) 재사용.
  - exit   = 매도 발화 초 매수호가1 - 2틱. 상한 09:30:00 도달 시 강제 청산
    (그 초 매수호가1 - 2틱; 09:30:00 행 결측 시 직전 마지막 관측 초 —
    P5 force_exit 결측 규약과 일관).
  - 라벨   = L3_net(연속 net_rate, v1 비용식) + L3_pos(L3_net >= +0.01).
  - 결측   = entry 초 결측/호가<=0 → 표본 제외. 경로 결측 초는 건너뜀
    (관측 초만 평가 — 재현게이트 컨벤션).

매도식 원문 무결성: 로컬 strategy.db stocksell 'ALP_EXITCHK_A_INCUMBENT' 의
전략코드 sha256 이 봉인값과 일치해야 한다(불일치 → SellExprMismatch, blocked).
절 평가기는 P5 재현게이트(오차 중앙 0.0pp·1틱내 99.7%)로 검증된 엔진 미러의
재사용이며, sha 게이트는 그 미러의 원본 텍스트가 드리프트하지 않았음을 묶는다.

성능 경로: 순수 파이썬 스캔(_fire_candidates_pure — replay._eval_sell_clauses
미러)과 벡터화 스캔(_fire_candidates_vector)을 함께 제공한다. 벡터 경로는
등가성 게이트(run_equivalence_gate — P5 챔피언 원장 667거래에서 기존
replay_champion_exit 와 청산시각·가격 일치율 >= 99.9%) 통과 영수증이 있을
때만 사용한다(미달 시 순수 경로 — 느려도 정직).

수익률(매도식 내부 상태)의 명목 수량: 원장 실측 매수금액이 5,000,000원
군집(4,998,000/4,999,500/... — champion_ledger.jsonl 671행)이므로 명목 배팅
5,000,000원으로 qty = max(1, int(배팅/매수체결가)) 를 쓴다. tick DB 접근은
read-only URI 전용. print 금지 — logging.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from alpha_lab.dataset.labels import adverse_fill, net_rate
from alpha_lab.dataset.reader import connect_ro
from alpha_lab.dataset.schema import as_float

# 엔진 미러 재사용(봉인 신뢰 기반 P5 재현게이트). _ladder_fill 은 사설 심볼이나
# 등가성 게이트가 replay_champion_exit 와 같은 체결 규약을 써야 하므로 의도적
# 재사용이다(중복 재구현 금지 — 드리프트 방지).
from alpha_lab.distill.replay import (
    _ladder_fill,
    kiwoom_pgsgsp,
    precompute_windows,
    replay_champion_exit,
)

__all__ = [
    "CHAMPION_SELL_SHA256",
    "CHAMPION_SELL_STRATEGY_NAME",
    "EQUIVALENCE_THRESHOLD",
    "L3_CAP_HMS",
    "L3_NOMINAL_BETTING",
    "L3_POS_THRESHOLD",
    "DayContext",
    "SellExprMismatch",
    "build_day_context",
    "build_l3_labels",
    "day_context_from_rows",
    "equivalence_gate_pass",
    "load_champion_sell_expr",
    "replay_champion_exit_vector",
    "run_equivalence_gate",
    "verify_sell_expr",
]

logger = logging.getLogger(__name__)

# 봉인 상수 — preregistration_v2.json label_spec_v2 실측값 그대로.
CHAMPION_SELL_SHA256 = (
    "8ef01e0ef2087ec95ac6b358b6f5c710414f3eb4dd401b01cc8162877f911c07"
)
CHAMPION_SELL_STRATEGY_NAME = "ALP_EXITCHK_A_INCUMBENT"
L3_POS_THRESHOLD = 0.01      # L3_pos = (L3_net >= +0.01).
L3_CAP_HMS = 93000           # 09:30:00 강제 청산 상한.
L3_WINDOW_START_HMS = 90000  # 일중 tick_count 기산 시작(엔진 창 시작 미러).
L3_NOMINAL_BETTING = 5_000_000.0  # 원장 매수금액 실측 군집(≈5.0e6) — 명목 배팅.
EQUIVALENCE_THRESHOLD = 0.999     # 벡터 경로 사용 허가 임계(청산시각·가격 동시 일치).

_TS_FORMAT = "%Y%m%d%H%M%S"

# 라벨 경로가 요구하는 저장 컬럼(결측 컬럼은 as_float(None)=0.0 — 엔진
# np.nan_to_num 미러). 매도호가1 은 entry, 매수호가1 은 exit 기준가.
_LABEL_COLUMNS = (
    "현재가", "시가", "등락율", "초당매수수량", "초당매도수량",
    "시가총액", "매수총잔량", "매수호가1", "매도호가1",
)


class SellExprMismatch(Exception):
    """매도식 원문 sha256 불일치 — 라벨 산출 차단(blocked)."""


def verify_sell_expr(text: str, expected_sha: str = CHAMPION_SELL_SHA256) -> str:
    """매도식 원문 sha256 검증 — 일치 시 sha hex 반환, 불일치 시 SellExprMismatch."""
    actual = hashlib.sha256(str(text).encode("utf-8")).hexdigest()
    if actual != expected_sha:
        raise SellExprMismatch(
            f"매도식 원문 sha 불일치: 실제 {actual} != 기대 {expected_sha}"
        )
    return actual


def load_champion_sell_expr(
    strategy_db_path, name: str = CHAMPION_SELL_STRATEGY_NAME
) -> str:
    """strategy.db stocksell 에서 매도식 원문을 read-only 로 읽는다(검증은 별도).

    행 부재는 ValueError — 호출측이 blocked 로 다룬다.
    """
    conn = connect_ro(strategy_db_path)
    try:
        row = conn.execute(
            'SELECT "전략코드" FROM stocksell WHERE "index" = ?', (name,)
        ).fetchone()
    finally:
        conn.close()
    if row is None or row[0] is None:
        raise ValueError(f"stocksell 에 매도식 없음: {name!r}")
    return str(row[0])


# ---------------------------------------------------------------------------
# 일 컨텍스트 — 절 평가에 필요한 배열 + 행 정적(트레이드 무관) 사전계산.
# ---------------------------------------------------------------------------

class DayContext:
    """한 (종목, 일)의 절 평가 컨텍스트 — 배열은 전부 읽기 전용 취급."""

    __slots__ = (
        "idxs", "n", "sec", "price", "open_", "pct", "sellv", "buyv",
        "bidtot", "cap", "bid1", "ask1", "ma60", "ang30", "prev", "rmin60",
        "c1_row", "open_neg", "tgate", "capgate",
        "c6_row", "c7_row", "c8_row", "c9_row",
        "bid2", "bid3", "rem1", "rem2", "rem3",
    )


def _sec_of_day(idxs: np.ndarray) -> np.ndarray:
    """int YYYYMMDDHHMMSS → 그 날 0시 기준 초(int64) — 같은 일 내 차이 전용."""
    hms = idxs % 1_000_000
    return (hms // 10_000) * 3600 + ((hms // 100) % 100) * 60 + (hms % 100)


def build_day_context(
    idxs: np.ndarray, arr: np.ndarray, ci: Mapping[str, int],
    pre: Mapping[str, np.ndarray],
) -> DayContext:
    """replay 형식 (idxs, arr, ci, pre) → DayContext.

    행 정적 절 성분(절 1·6~9 의 트레이드 무관 부분)은 여기서 한 번만 계산한다.
    수식은 replay._eval_sell_clauses 의 스칼라 식과 동일한 연산 순서를 쓴다
    (부동소수 동등성 — 등가성 게이트로 검증).
    """
    ctx = DayContext()
    n = int(idxs.shape[0])
    ctx.idxs = np.asarray(idxs, dtype=np.int64)
    ctx.n = n
    ctx.sec = _sec_of_day(ctx.idxs)

    def col(name: str) -> np.ndarray:
        if name in ci:
            return np.ascontiguousarray(arr[:, ci[name]], dtype=np.float64)
        return np.zeros(n, dtype=np.float64)

    ctx.price = col("현재가")
    ctx.open_ = col("시가")
    ctx.pct = col("등락율")
    ctx.sellv = col("초당매도수량")
    ctx.buyv = col("초당매수수량")
    ctx.bidtot = col("매수총잔량")
    ctx.cap = col("시가총액")
    ctx.bid1 = col("매수호가1")
    ctx.ask1 = col("매도호가1")
    ctx.bid2 = col("매수호가2")
    ctx.bid3 = col("매수호가3")
    ctx.rem1 = col("매수잔량1")
    ctx.rem2 = col("매수잔량2")
    ctx.rem3 = col("매수잔량3")
    ctx.ma60 = np.asarray(pre["ma60"], dtype=np.float64)
    ctx.ang30 = np.asarray(pre["ang30"], dtype=np.float64)

    ctx.prev = np.concatenate(([0.0], ctx.price[:-1])) if n else ctx.price[:0]
    if n >= 60:
        windows = np.lib.stride_tricks.sliding_window_view(ctx.price, 60)
        rmin = np.full(n, np.inf)
        rmin[59:] = windows.min(axis=1)
    else:
        rmin = np.full(n, np.inf)
    ctx.rmin60 = rmin

    pos_i = np.arange(n)
    ang_eval = np.where(pos_i >= 29, np.nan_to_num(ctx.ang30, nan=0.0), 0.0)
    ma_eval = np.where(pos_i >= 59, np.nan_to_num(ctx.ma60, nan=0.0), 0.0)
    ma_prev_raw = np.concatenate(([0.0], np.nan_to_num(ctx.ma60, nan=0.0)[:-1])) \
        if n else ctx.ma60[:0]
    ma_prev_eval = np.where(pos_i >= 60, ma_prev_raw, 0.0)

    open_nonzero = ctx.open_ != 0.0
    open_div = np.where(open_nonzero, ctx.open_, 1.0)
    open_vs = np.where(
        open_nonzero, ((ctx.price - ctx.open_) / open_div) * 100.0, 0.0
    )
    prev_nonzero = ctx.prev != 0.0
    prev_div = np.where(prev_nonzero, ctx.prev, 1.0)
    drop = np.where(prev_nonzero, (ctx.price / prev_div - 1.0) * 100.0, 0.0)
    imb = ctx.sellv - ctx.buyv

    ctx.c1_row = ctx.pct > 29.5
    ctx.open_neg = open_vs < 0.0
    ctx.tgate = (ctx.idxs % 1_000_000) < 93000
    ctx.capgate = ctx.cap < 10000.0
    ctx.c6_row = (ang_eval >= 10.0) & (imb >= ctx.bidtot * 0.5) & (drop < -0.5)
    ctx.c7_row = (
        (ang_eval < 10.0) & (ang_eval >= 5.0)
        & (imb >= ctx.bidtot * 0.7) & (drop < -0.7)
    )
    ctx.c8_row = (
        (ang_eval < 5.0) & (ang_eval >= 0.0)
        & (imb >= ctx.bidtot * 0.8) & (drop < -0.5)
    )
    ctx.c9_row = (ctx.prev >= ma_prev_eval) & (ma_eval > ctx.price)
    return ctx


def day_context_from_rows(
    rows_by_t0: Mapping[int, Mapping],
    *,
    day: int,
    start_hms: int = L3_WINDOW_START_HMS,
    end_hms: int = L3_CAP_HMS,
) -> DayContext:
    """reader.load_stock_rows 결과(dict) → DayContext (창 [start, end] 행만).

    NULL/결측 컬럼은 as_float 로 0.0 강제(엔진 np.nan_to_num 미러). tick_count
    는 이 창의 첫 행부터 기산한다(엔진 일중 행수 미러 — 창 시작 09:00:00).
    """
    lo = int(day) * 1_000_000 + int(start_hms)
    hi = int(day) * 1_000_000 + int(end_hms)
    keys = sorted(t for t in rows_by_t0 if lo <= int(t) <= hi)
    n = len(keys)
    arr = np.zeros((n, len(_LABEL_COLUMNS)), dtype=np.float64)
    for r, t in enumerate(keys):
        row = rows_by_t0[t]
        for c, name in enumerate(_LABEL_COLUMNS):
            arr[r, c] = as_float(row.get(name))
    idxs = np.asarray(keys, dtype=np.int64)
    ci = {name: c for c, name in enumerate(_LABEL_COLUMNS)}
    pre = precompute_windows(arr, ci)
    return build_day_context(idxs, arr, ci, pre)


# ---------------------------------------------------------------------------
# 수익률 벡터화 — utility.static.GetKiwoomPgSgSp(kiwoom_pgsgsp) 미러.
# ---------------------------------------------------------------------------

def _vector_sp(bg: float, cg: np.ndarray) -> np.ndarray:
    """kiwoom_pgsgsp(bg, cg)[2] 의 벡터 등가 — 스칼라와 비트 동일 목표.

    int() 절사는 np.trunc(양수 전제 — cg>=0), round 는 np.round 후 반집합
    경계(±1e-6) 요소만 파이썬 round 로 재계산(np.round 와 CPython round 의
    십진 경계 불일치 가능성 봉쇄 — 게이트·성질 테스트로 검증).
    """
    cg = np.asarray(cg, dtype=np.float64)
    texs = np.trunc(cg * 0.0018)
    bfee = float(int(bg * 0.00015 / 10) * 10)
    sfee = np.trunc(cg * 0.00015 / 10.0) * 10.0
    pg = np.trunc(cg - texs - bfee - sfee)
    sg = np.rint(pg - bg)
    v = sg / bg * 100.0
    sp = np.round(v, 2)
    scaled = v * 100.0
    risky = np.abs(scaled - np.floor(scaled) - 0.5) < 1e-6
    if risky.any():
        sp[risky] = [round(float(x), 2) for x in v[risky]]
    return sp


# ---------------------------------------------------------------------------
# 절 평가 — 스칼라(replay._eval_sell_clauses 미러) / 벡터.
# ---------------------------------------------------------------------------

def _eval_row_clause(
    ctx: DayContext, i: int, *, sp: float, best: float, hold: int
) -> Optional[int]:
    """행 i 의 매도식 절 평가 — 발동 절 번호 또는 None.

    replay._eval_sell_clauses 와 절·게이트·연산 순서 동일(원 배열에서 직접
    계산 — 벡터 경로와 독립인 정직 폴백/어트리뷰션 경로).
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

    if pct > 29.5:
        return 1
    if open_vs < 0 and sp <= -2.0 and cur < low_price(60, int(hold)):
        return 2
    if hold > 60 and cur < low_price(60, int(hold)):
        return 3
    if hms < 93000:
        if sp >= 9 or sp <= -5.0:
            return 4
        if best > 3 and best * 0.6 >= sp:
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
    return None


def _fire_candidates_pure(
    ctx: DayContext, *, lo: int, hi: int, entry_pos: int, bg: float, qty: int
) -> Iterator[Tuple[int, int]]:
    """순수 파이썬 스캔 — (발동 행, 절) 을 순서대로 생성(폴백 경로)."""
    best = 0.0
    entry_sec = int(ctx.sec[entry_pos])
    for i in range(lo, hi):
        _, _, sp = kiwoom_pgsgsp(bg, qty * float(ctx.price[i]))
        if sp > best:
            best = sp
        hold = int(ctx.sec[i]) - entry_sec
        clause = _eval_row_clause(ctx, i, sp=sp, best=best, hold=hold)
        if clause is not None:
            yield i, clause


def _fire_arrays(
    ctx: DayContext, *, lo: int, hi: int, entry_pos: int, bg: float, qty: int
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """행 구간 [lo, hi) 의 (fire, sp, best, hold) 벡터 — lo 는 보유 첫 행 전제."""
    price = ctx.price[lo:hi]
    sp = _vector_sp(bg, float(qty) * price)
    best = np.maximum.accumulate(np.maximum(sp, 0.0))
    hold = ctx.sec[lo:hi] - int(ctx.sec[entry_pos])
    abs_i = np.arange(lo, hi, dtype=np.int64)
    j = abs_i - hold
    valid_low = j >= 59
    lowv = np.where(
        valid_low, ctx.rmin60[np.clip(j, 0, ctx.n - 1)], 0.0
    )
    low_fire = price < lowv
    c2 = ctx.open_neg[lo:hi] & (sp <= -2.0) & low_fire
    c3 = (hold > 60) & low_fire
    c4 = (sp >= 9.0) | (sp <= -5.0)
    c5 = (best > 3.0) & (best * 0.6 >= sp)
    c69 = ctx.capgate[lo:hi] & (
        ctx.c6_row[lo:hi] | ctx.c7_row[lo:hi] | ctx.c8_row[lo:hi]
        | ((best > 4.5) & ctx.c9_row[lo:hi])
    )
    fire = ctx.c1_row[lo:hi] | c2 | c3 | (ctx.tgate[lo:hi] & (c4 | c5 | c69))
    return fire, sp, best, hold


def _fire_candidates_vector(
    ctx: DayContext, *, lo: int, hi: int, entry_pos: int, bg: float, qty: int
) -> Iterator[Tuple[int, int]]:
    """벡터화 스캔 — 발동 행마다 스칼라 재평가로 절 번호를 어트리뷰션한다.

    벡터 fire 와 스칼라 판정이 어긋나면 RuntimeError(조용한 드리프트 금지).
    """
    if hi <= lo:
        return
    fire, sp, best, hold = _fire_arrays(
        ctx, lo=lo, hi=hi, entry_pos=entry_pos, bg=bg, qty=qty
    )
    for r in np.flatnonzero(fire):
        i = lo + int(r)
        clause = _eval_row_clause(
            ctx, i, sp=float(sp[r]), best=float(best[r]), hold=int(hold[r])
        )
        if clause is None:
            raise RuntimeError(
                f"벡터/스칼라 절 평가 불일치: row={i} idx={int(ctx.idxs[i])}"
            )
        yield i, clause


_FIRE_SCANNERS = {
    "pure": _fire_candidates_pure,
    "vector": _fire_candidates_vector,
}


# ---------------------------------------------------------------------------
# L3 라벨 — 봉인 label_spec_v2 구현.
# ---------------------------------------------------------------------------

def _plus_seconds(ts: int, seconds: int) -> int:
    moment = datetime.strptime(str(int(ts)), _TS_FORMAT)
    return int((moment + timedelta(seconds=seconds)).strftime(_TS_FORMAT))


def build_l3_labels(
    rows_by_t0: Mapping[int, Mapping],
    t0_grid: Sequence[int],
    sell_expr_text: str,
    *,
    engine: str = "pure",
    expected_sha: str = CHAMPION_SELL_SHA256,
    nominal_betting: float = L3_NOMINAL_BETTING,
    cap_hms: int = L3_CAP_HMS,
) -> Tuple[Dict[int, Optional[Dict[str, object]]], Dict[str, object]]:
    """한 (종목, 일)의 t0 들에 L3_replay 라벨을 계산한다.

    Args:
        rows_by_t0: reader.load_stock_rows 결과 — {int YYYYMMDDHHMMSS: 행 dict}.
        t0_grid: 라벨 대상 t0 목록(int, 같은 일자여야 함).
        sell_expr_text: 챔피언 매도식 원문 — sha 불일치 시 SellExprMismatch.
        engine: 'pure' | 'vector' — vector 는 등가성 게이트 통과 후에만 쓸 것.

    Returns:
        (labels, stats). labels[t0] = None(정직 제외) 또는
        {'L3_net': float, 'L3_pos': int, 'exit_time': int, 'clause': int(0=강제캡)}.
        stats 는 제외 사유·발화/강제캡 카운트.
    """
    verify_sell_expr(sell_expr_text, expected_sha)
    if engine not in _FIRE_SCANNERS:
        raise ValueError(f"알 수 없는 engine: {engine!r} (허용: pure|vector)")
    scanner = _FIRE_SCANNERS[engine]
    labels: Dict[int, Optional[Dict[str, object]]] = {
        int(t0): None for t0 in t0_grid
    }
    stats: Dict[str, object] = {
        "n": len(labels), "labeled": 0, "entry_missing": 0,
        "entry_quote_bad": 0, "path_empty": 0, "no_exit_quote": 0,
        "bad_fire_quote_rows": 0, "fired": 0, "forced_cap": 0,
        "engine": engine,
    }
    if not labels:
        return labels, stats
    days = {int(t0) // 1_000_000 for t0 in labels}
    if len(days) != 1:
        raise ValueError(f"t0_grid 는 단일 일자여야 한다: {sorted(days)}")
    day = days.pop()
    ctx = day_context_from_rows(rows_by_t0, day=day, end_hms=cap_hms)
    if ctx.n == 0:
        stats["entry_missing"] = len(labels)
        return labels, stats

    for t0 in sorted(labels):
        entry_int = _plus_seconds(t0, 1)
        pos = int(np.searchsorted(ctx.idxs, entry_int))
        if pos >= ctx.n or int(ctx.idxs[pos]) != entry_int:
            stats["entry_missing"] += 1
            continue
        entry_ask = float(ctx.ask1[pos])
        if entry_ask <= 0.0:
            stats["entry_quote_bad"] += 1
            continue
        buy_fill, _ = adverse_fill(entry_ask, entry_ask)
        qty = max(1, int(nominal_betting / buy_fill))
        bg = qty * buy_fill
        lo, hi = pos + 1, ctx.n
        if lo >= hi:
            stats["path_empty"] += 1
            continue
        exit_pos: Optional[int] = None
        clause = 0
        for cand, cand_clause in scanner(
            ctx, lo=lo, hi=hi, entry_pos=pos, bg=bg, qty=qty
        ):
            if float(ctx.bid1[cand]) > 0.0:
                exit_pos, clause = cand, int(cand_clause)
                break
            stats["bad_fire_quote_rows"] += 1  # type: ignore[operator]
        if exit_pos is None:
            # 강제 캡 — 마지막 관측 초부터 역방향으로 유효 호가 탐색.
            back = hi - 1
            while back >= lo and float(ctx.bid1[back]) <= 0.0:
                back -= 1
            if back < lo:
                stats["no_exit_quote"] += 1
                continue
            exit_pos, clause = back, 0
            stats["forced_cap"] += 1
        else:
            stats["fired"] += 1
        exit_bid = float(ctx.bid1[exit_pos])
        _, sell_fill = adverse_fill(entry_ask, exit_bid)
        rate = net_rate(buy_fill, sell_fill)
        labels[int(t0)] = {
            "L3_net": float(rate),
            "L3_pos": int(rate >= L3_POS_THRESHOLD),
            "exit_time": int(ctx.idxs[exit_pos]),
            "clause": clause,
        }
        stats["labeled"] += 1
    return labels, stats


# ---------------------------------------------------------------------------
# 등가성 게이트 — 벡터 경로 vs 기존 replay_champion_exit (P5 원장 667거래).
# ---------------------------------------------------------------------------

def replay_champion_exit_vector(
    ctx: DayContext, *, buy_time: int, buy_price: float, qty: int
) -> Dict[str, object]:
    """replay.replay_champion_exit 의 벡터화 등가 — 반환 계약 동일.

    사다리 3호가 체결·미체결 보유 지속·일 마지막 행 LastSell 전용 규약까지
    미러한다. 등가성 게이트가 이 함수와 스칼라 원본의 청산시각·가격 일치를
    667거래 전수로 증명한 뒤에만 벡터 라벨 경로를 허가한다.
    """
    n = ctx.n
    pos = int(np.searchsorted(ctx.idxs, int(buy_time)))
    if pos >= n or int(ctx.idxs[pos]) != int(buy_time):
        return {"status": "entry_row_missing"}
    bg = qty * float(buy_price)
    lo, hi = pos + 1, n - 1  # 마지막 행은 LastSell 전용(엔진 미러).
    best_final = 0.0
    worst_final = 0.0
    if hi > lo:
        fire, sp, best, hold = _fire_arrays(
            ctx, lo=lo, hi=hi, entry_pos=pos, bg=bg, qty=qty
        )
        worst = np.minimum.accumulate(np.minimum(sp, 0.0))
        for r in np.flatnonzero(fire):
            i = lo + int(r)
            clause = _eval_row_clause(
                ctx, i, sp=float(sp[r]), best=float(best[r]), hold=int(hold[r])
            )
            if clause is None:
                raise RuntimeError(
                    f"벡터/스칼라 절 평가 불일치: row={i} idx={int(ctx.idxs[i])}"
                )
            sell_price = _ladder_fill(
                qty,
                [float(ctx.bid1[i]), float(ctx.bid2[i]), float(ctx.bid3[i])],
                [float(ctx.rem1[i]), float(ctx.rem2[i]), float(ctx.rem3[i])],
            )
            if sell_price is None:
                continue  # 잔량 부족 — 미체결 보유 지속(엔진 Sell no-op 미러).
            _, _, sell_sp = kiwoom_pgsgsp(bg, qty * sell_price)
            return {
                "status": "ok", "sell_time": int(ctx.idxs[i]),
                "sell_price": sell_price, "profit_pct": sell_sp,
                "cond": int(clause), "best": float(best[r]),
                "worst": float(worst[r]),
            }
        best_final = float(best[-1])
        worst_final = float(worst[-1])
    last = n - 1
    sell_price = _ladder_fill(
        qty,
        [float(ctx.bid1[last]), float(ctx.bid2[last]), float(ctx.bid3[last])],
        [float(ctx.rem1[last]), float(ctx.rem2[last]), float(ctx.rem3[last])],
    )
    if sell_price is None:
        sell_price = float(int(ctx.bid1[last] + 0.5))
    _, _, sell_sp = kiwoom_pgsgsp(bg, qty * sell_price)
    return {
        "status": "ok", "sell_time": int(ctx.idxs[last]),
        "sell_price": sell_price, "profit_pct": sell_sp, "cond": 0,
        "best": best_final, "worst": worst_final,
    }


def run_equivalence_gate(
    ledger_path, back_db_path, fallback_db_path, out_path,
    *, generated: str, threshold: float = EQUIVALENCE_THRESHOLD,
) -> dict:
    """P5 챔피언 원장 전수(667거래)로 벡터 경로 등가성 영수증을 만든다.

    비교 대상: 기존 replay.replay_champion_exit(스칼라, P5 재현게이트 검증) vs
    replay_champion_exit_vector(본 모듈). 판정: 청산시각·청산가 동시 일치율
    >= threshold(0.999) 일 때만 gate_pass=True — 미달 시 벡터 경로 사용 금지.
    """
    # 무거운 배선 의존(원장/종목맵)은 게이트 실행 시에만 적재 — 순환 없음.
    from alpha_lab.distill.ledger_wiring import read_ledger
    from alpha_lab.distill.replay import connect_back_ro, load_day_rows
    from alpha_lab.distill.replay_gate import prepare_trades
    from alpha_lab.mcl.rejoin import load_stockinfo_map

    records = read_ledger(ledger_path)
    primary, _ = load_stockinfo_map(back_db_path)
    fallback, _ = load_stockinfo_map(fallback_db_path)
    conn = connect_back_ro(back_db_path)
    try:
        trades, excl = prepare_trades(records, conn, primary, fallback)
        cache: Dict[Tuple[str, int], Tuple] = {}
        results: List[dict] = []
        for tr in trades:
            key = (tr["code6"], int(tr["진입일자"]))
            if key not in cache:
                idxs, arr, ci = load_day_rows(conn, key[0], key[1])
                pre = precompute_windows(arr, ci)
                cache[key] = (idxs, arr, ci, pre,
                              build_day_context(idxs, arr, ci, pre))
            idxs, arr, ci, pre, ctx = cache[key]
            ref = replay_champion_exit(
                idxs, arr, ci, pre, buy_time=tr["매수시간"],
                buy_price=tr["매수가"], qty=tr["qty"],
            )
            vec = replay_champion_exit_vector(
                ctx, buy_time=tr["매수시간"], buy_price=tr["매수가"],
                qty=tr["qty"],
            )
            if ref["status"] != "ok" or vec["status"] != "ok":
                status = f"{ref['status']}|{vec['status']}"
                excl[status] = excl.get(status, 0) + 1
                continue
            results.append({
                "code6": tr["code6"], "진입일자": tr["진입일자"],
                "매수시간": tr["매수시간"],
                "ref_sell_time": ref["sell_time"], "vec_sell_time": vec["sell_time"],
                "ref_sell_price": ref["sell_price"], "vec_sell_price": vec["sell_price"],
                "ref_cond": ref["cond"], "vec_cond": vec["cond"],
                "time_match": int(ref["sell_time"] == vec["sell_time"]),
                "price_match": int(ref["sell_price"] == vec["sell_price"]),
                "cond_match": int(int(ref["cond"]) == int(vec["cond"])),
            })
    finally:
        conn.close()
    n = len(results)
    both = sum(1 for r in results if r["time_match"] and r["price_match"])
    mismatches = [
        r for r in results if not (r["time_match"] and r["price_match"])
    ]
    report = {
        "kind": "v2_labeler_equivalence",
        "generated": generated,
        "sealed_threshold": threshold,
        "compare_basis": "replay.replay_champion_exit (P5 재현게이트 검증 스칼라)",
        "n_ledger_rows": len(records),
        "n_trades": n,
        "exclusions": dict(sorted(excl.items())),
        "n_time_match": int(sum(r["time_match"] for r in results)),
        "n_price_match": int(sum(r["price_match"] for r in results)),
        "n_both_match": int(both),
        "cond_match_rate": (
            round(sum(r["cond_match"] for r in results) / n, 6) if n else None
        ),
        "equivalence_pct": round(100.0 * both / n, 4) if n else 0.0,
        "gate_pass": bool(n > 0 and (both / n) >= threshold),
        "mismatches": mismatches,
    }
    Path(out_path).write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
    )
    logger.info(
        "equivalence gate: n=%d both=%d pct=%.4f pass=%s",
        n, both, report["equivalence_pct"], report["gate_pass"],
    )
    return report


def equivalence_gate_pass(receipt_path) -> bool:
    """등가성 영수증의 gate_pass — 파일 부재/파손은 False(벡터 경로 불허)."""
    path = Path(receipt_path)
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return bool(
        payload.get("kind") == "v2_labeler_equivalence"
        and payload.get("gate_pass") is True
    )
