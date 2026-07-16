"""드롭 파라미터화 발화 미러 — labels_v2 절 평가/스캔의 절-제거 판본.

봉인(매도식 D1 §14): 원본 파일 무수정 원칙에 따라 `_eval_row_clause` ·
`_fire_arrays` 의 로직을 여기 복제하고 drop(제거 절 집합)만 추가한다.
drop 의미론 = "그 절이 매도식에서 삭제됨": 해당 분기 조건이 참이어도
발화하지 않고 **같은 행의 후속 절**부터 계속 평가한다(elif 체인에서 절을
지운 것과 동일). drop=None 이면 원본과 완전 동일해야 하며(§14-F9 원본재현
게이트가 전수 비트동일로 강제), 실현 손익은 pilot_v2 와 동일한 이중 세율
규약(발화=엔진 0.18% 의미론 · 실현=연도 세율 재계상)을 따른다.
"""
from __future__ import annotations

from typing import Dict, Iterator, Mapping, Optional, Sequence, Tuple, Union

import numpy as np

from alpha_lab.dataset import labels_v2 as lv2
from alpha_lab.stats_map import config_v2, costs_v2

# 미러 계보 — 이 하니스가 복제한 매도식 원문 sha(발화 절 1~9 + 강제캡 0).
MIRROR_OF_SELL_SHA = lv2.CHAMPION_SELL_SHA256
FIRE_CLAUSES: Tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7, 8, 9)
DROP_ALL = "all"

DropSpec = Union[None, int, str, frozenset]


def normalize_drop(drop: DropSpec) -> frozenset:
    """drop 인자 정규화 — None→빈집합, int k→{k}, 'all'→{1..9}."""
    if drop is None:
        return frozenset()
    if drop == DROP_ALL:
        return frozenset(FIRE_CLAUSES)
    if isinstance(drop, (int, np.integer)):
        k = int(drop)
        if k not in FIRE_CLAUSES:
            raise ValueError(f"drop 절 번호는 1~9: {k}")
        return frozenset({k})
    ks = frozenset(int(k) for k in drop)
    if not ks.issubset(set(FIRE_CLAUSES)):
        raise ValueError(f"drop 절 번호는 1~9: {sorted(ks)}")
    return ks


def eval_row_clause_drop(
    ctx, i: int, *, sp: float, best: float, hold: int, drop: frozenset,
) -> Optional[int]:
    """행 i 절 평가(labels_v2._eval_row_clause 미러) — drop 절은 건너뛴다.

    drop=∅ 이면 원본과 판정·순서·연산이 동일해야 한다(원본재현 게이트 대상).
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

    if pct > 29.5 and 1 not in drop:
        return 1
    if (open_vs < 0 and sp <= -2.0 and cur < low_price(60, int(hold))
            and 2 not in drop):
        return 2
    if hold > 60 and cur < low_price(60, int(hold)) and 3 not in drop:
        return 3
    if hms < 93000:
        if (sp >= 9 or sp <= -5.0) and 4 not in drop:
            return 4
        if best > 3 and best * 0.6 >= sp and 5 not in drop:
            return 5
        if cap < 10000:
            drop_pct = (cur / prev_price - 1) * 100 if prev_price else 0.0
            if (angle() >= 10 and (sell_vol - buy_vol) >= bid_total * 0.5
                    and drop_pct < -0.5 and 6 not in drop):
                return 6
            if (5 <= angle() < 10 and (sell_vol - buy_vol) >= bid_total * 0.7
                    and drop_pct < -0.7 and 7 not in drop):
                return 7
            if (0 <= angle() < 5 and (sell_vol - buy_vol) >= bid_total * 0.8
                    and drop_pct < -0.5 and 8 not in drop):
                return 8
            if (4.5 < best and prev_price >= ma(60, 1) and ma(60) > cur
                    and 9 not in drop):
                return 9
    return None


def fire_arrays_drop(
    ctx, *, lo: int, hi: int, entry_pos: int, bg: float, qty: int,
    drop: frozenset,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """labels_v2._fire_arrays 미러 — drop 절 항을 fire 합성에서 제외한다."""
    price = ctx.price[lo:hi]
    sp = lv2._vector_sp(bg, float(qty) * price)
    best = np.maximum.accumulate(np.maximum(sp, 0.0))
    hold = ctx.sec[lo:hi] - int(ctx.sec[entry_pos])
    abs_i = np.arange(lo, hi, dtype=np.int64)
    j = abs_i - hold
    valid_low = j >= 59
    lowv = np.where(valid_low, ctx.rmin60[np.clip(j, 0, ctx.n - 1)], 0.0)
    low_fire = price < lowv

    off = np.zeros(hi - lo, dtype=bool)  # 드롭된 항의 자리(항상 False).
    t1 = ctx.c1_row[lo:hi] if 1 not in drop else off
    t2 = (ctx.open_neg[lo:hi] & (sp <= -2.0) & low_fire) if 2 not in drop else off
    t3 = ((hold > 60) & low_fire) if 3 not in drop else off
    t4 = ((sp >= 9.0) | (sp <= -5.0)) if 4 not in drop else off
    t5 = ((best > 3.0) & (best * 0.6 >= sp)) if 5 not in drop else off
    t6 = ctx.c6_row[lo:hi] if 6 not in drop else off
    t7 = ctx.c7_row[lo:hi] if 7 not in drop else off
    t8 = ctx.c8_row[lo:hi] if 8 not in drop else off
    t9 = ((best > 4.5) & ctx.c9_row[lo:hi]) if 9 not in drop else off
    c69 = ctx.capgate[lo:hi] & (t6 | t7 | t8 | t9)
    fire = t1 | t2 | t3 | (ctx.tgate[lo:hi] & (t4 | t5 | c69))
    return fire, sp, best, hold


def _fire_pure_drop(
    ctx, *, lo: int, hi: int, entry_pos: int, bg: float, qty: int,
    drop: frozenset,
) -> Iterator[Tuple[int, int]]:
    """순수 스캔(폴백) — (발동 행, 절) 순서 생성. labels_v2 순수 경로 미러."""
    best = 0.0
    entry_sec = int(ctx.sec[entry_pos])
    for i in range(lo, hi):
        _, _, sp = lv2.kiwoom_pgsgsp(bg, qty * float(ctx.price[i]))
        if sp > best:
            best = sp
        hold = int(ctx.sec[i]) - entry_sec
        clause = eval_row_clause_drop(
            ctx, i, sp=sp, best=best, hold=hold, drop=drop)
        if clause is not None:
            yield i, clause


def _fire_vector_drop(
    ctx, *, lo: int, hi: int, entry_pos: int, bg: float, qty: int,
    drop: frozenset,
) -> Iterator[Tuple[int, int]]:
    """벡터 스캔 — 발동 행마다 드롭-인지 스칼라로 절 번호 어트리뷰션."""
    if hi <= lo:
        return
    fire, sp, best, hold = fire_arrays_drop(
        ctx, lo=lo, hi=hi, entry_pos=entry_pos, bg=bg, qty=qty, drop=drop)
    for r in np.flatnonzero(fire):
        i = lo + int(r)
        clause = eval_row_clause_drop(
            ctx, i, sp=float(sp[r]), best=float(best[r]), hold=int(hold[r]),
            drop=drop)
        if clause is None:
            raise RuntimeError(
                f"드롭 벡터/스칼라 절 평가 불일치: row={i} "
                f"idx={int(ctx.idxs[i])} drop={sorted(drop)}")
        yield i, clause


_SCANNERS = {"pure": _fire_pure_drop, "vector": _fire_vector_drop}


def label_drop(
    rows_by_t0: Mapping[int, Mapping],
    t0_ints: Sequence[int],
    *,
    year: int,
    drop: DropSpec = None,
    engine: str = "vector",
    nominal_betting: float = lv2.L3_NOMINAL_BETTING,
    cap_hms: int = lv2.L3_CAP_HMS,
) -> Tuple[Dict[str, np.ndarray], Dict[str, object]]:
    """한 (종목,일)의 t0 들에 드롭-변형 L3 라벨(연도 세율 실현) 산출.

    발화 흐름은 labels_v2.build_l3_labels 미러(진입 t0+1초 매도호가1+2틱,
    첫 유효 발화 or 강제캡 역탐색), 실현 net 은 pilot_v2._l3_labels 규약
    (costs_v2.adverse_fill_year + net_rate_year_vec). 반환 arrays:
    {net, exit_t, clause, labeled} — 은행 스키마 정렬(t0_ints 순).
    """
    dset = normalize_drop(drop)
    if engine not in _SCANNERS:
        raise ValueError(f"알 수 없는 engine: {engine!r}")
    scanner = _SCANNERS[engine]
    n = len(t0_ints)
    net = np.full(n, np.nan, dtype=np.float64)
    exit_t = np.zeros(n, dtype=np.int64)
    clause_a = np.full(n, -1, dtype=np.int64)
    labeled = np.zeros(n, dtype=bool)
    entry_ask_a = np.zeros(n, dtype=np.float64)
    exit_bid_a = np.zeros(n, dtype=np.float64)
    stats: Dict[str, object] = {
        "n": n, "labeled": 0, "entry_missing": 0, "entry_quote_bad": 0,
        "path_empty": 0, "no_exit_quote": 0, "bad_fire_quote_rows": 0,
        "fired": 0, "forced_cap": 0, "engine": engine,
        "drop": sorted(dset),
    }
    if n == 0:
        return ({"net": net, "exit_t": exit_t, "clause": clause_a,
                 "labeled": labeled}, stats)
    days = {int(t0) // 1_000_000 for t0 in t0_ints}
    if len(days) != 1:
        raise ValueError(f"t0_ints 는 단일 일자여야 한다: {sorted(days)}")
    day = days.pop()
    ctx = lv2.day_context_from_rows(rows_by_t0, day=day, end_hms=cap_hms)
    if ctx.n == 0:
        stats["entry_missing"] = n
        return ({"net": net, "exit_t": exit_t, "clause": clause_a,
                 "labeled": labeled}, stats)

    for ix, t0 in enumerate(t0_ints):
        entry_int = lv2._plus_seconds(int(t0), 1)
        pos = int(np.searchsorted(ctx.idxs, entry_int))
        if pos >= ctx.n or int(ctx.idxs[pos]) != entry_int:
            stats["entry_missing"] += 1  # type: ignore[operator]
            continue
        entry_ask = float(ctx.ask1[pos])
        if entry_ask <= 0.0:
            stats["entry_quote_bad"] += 1  # type: ignore[operator]
            continue
        buy_fill, _ = lv2.adverse_fill(entry_ask, entry_ask)
        qty = max(1, int(nominal_betting / buy_fill))
        bg = qty * buy_fill
        lo, hi = pos + 1, ctx.n
        if lo >= hi:
            stats["path_empty"] += 1  # type: ignore[operator]
            continue
        exit_pos: Optional[int] = None
        fired_clause = 0
        for cand, cand_clause in scanner(
                ctx, lo=lo, hi=hi, entry_pos=pos, bg=bg, qty=qty, drop=dset):
            if float(ctx.bid1[cand]) > 0.0:
                exit_pos, fired_clause = cand, int(cand_clause)
                break
            stats["bad_fire_quote_rows"] += 1  # type: ignore[operator]
        if exit_pos is None:
            back = hi - 1
            while back >= lo and float(ctx.bid1[back]) <= 0.0:
                back -= 1
            if back < lo:
                stats["no_exit_quote"] += 1  # type: ignore[operator]
                continue
            exit_pos, fired_clause = back, 0
            stats["forced_cap"] += 1  # type: ignore[operator]
        else:
            stats["fired"] += 1  # type: ignore[operator]
        exit_t[ix] = int(ctx.idxs[exit_pos])
        clause_a[ix] = fired_clause
        labeled[ix] = True
        entry_ask_a[ix] = entry_ask
        exit_bid_a[ix] = float(ctx.bid1[exit_pos])
        stats["labeled"] += 1  # type: ignore[operator]

    m = labeled
    if m.any():
        bf, sf = costs_v2.adverse_fill_year(entry_ask_a[m], exit_bid_a[m])
        tax = config_v2.year_tax_rate(int(year))
        net[m] = costs_v2.net_rate_year_vec(bf, sf, tax)
    return ({"net": net, "exit_t": exit_t, "clause": clause_a,
             "labeled": labeled}, stats)
