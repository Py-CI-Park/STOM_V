"""D5-R 파이프라인 — RR8 가문 원장 적재 + 거래별 반사실 평가 레코드.

봉인 근거: 2026-07-12_d5r_conditional_exit_preregistration.md §4·§5.

재사용 인프라(무재구현): ledger_wiring.scan_csvs → normalize → 발견창 필터 →
replay_gate.prepare_trades(name→code, qty, 원장_*) → replay.load_day_rows/
precompute_windows → labels_v2.build_day_context. 패치 반사실은
exitlab_r.patch_exit(순수/벡터). tick DB read-only, 엔진 백테 0회.

거래별 레코드 하나가 R1(포렌식)·R3(triage)의 유일 입력이다 — 현직 청산·
T별 t=T 상태·후보별 패치 청산을 한 번에 담는다(다중 스캔 방지).
"""
from __future__ import annotations

import logging
from typing import Callable, Dict, List, Mapping, Sequence, Tuple

from alpha_lab.dataset.labels_v2 import build_day_context
from alpha_lab.distill.ledger_wiring import scan_csvs
from alpha_lab.distill.replay import (
    connect_back_ro,
    load_day_rows,
    precompute_windows,
)
from alpha_lab.distill.replay_gate import prepare_trades
from alpha_lab.exitlab_r.patch_exit import (
    B_CLAUSE_TAG,
    Patch,
    analyze_path,
    replay_patched_pure,
)
from alpha_lab.mcl.rejoin import load_stockinfo_map

__all__ = [
    "CANDIDATES",
    "DISCOVERY_END_DAY",
    "FAMILY_CSVS",
    "T_GRID",
    "build_ctx_cache_getter",
    "dedup_representative",
    "evaluate_trades",
    "load_family_trades",
]

logger = logging.getLogger(__name__)

DISCOVERY_END_DAY = 20231231  # 발견창 상한(§1 — 2024+ known 미접촉).
T_GRID: Tuple[int, ...] = (120, 180, 240)

# 발견창 배치 CSV(§0.5 W6a 상속 — 0836~0841 배치는 2025 포함이라 미접촉).
FAMILY_CSVS: Dict[str, str] = {
    "RR8_12": "backtest/csv/stock_bt_ALP_V4_RR8_12_20260707074238.csv",
    "RR8_0": "backtest/csv/stock_bt_ALP_V4_RR8_0_20260707074352.csv",
    "RR8_21": "backtest/csv/stock_bt_ALP_V4_RR8_21_20260707074459.csv",
}
GPTAUTH_CSV = "backtest/csv/stock_bt_ALP_V4_GPTAUTH_G8_20260707075127.csv"

# 후보 격자 8개 — §4 사전값 봉인(측정 후 조정 금지).
CANDIDATES: Tuple[Patch, ...] = (
    Patch(family="A", mult=0.55, label="A1"),
    Patch(family="A", mult=0.50, label="A2"),
    Patch(family="B", T=120, x=1.0, y=0.0, label="B1"),
    Patch(family="B", T=120, x=1.5, y=0.0, label="B2"),
    Patch(family="B", T=180, x=1.0, y=0.0, label="B3"),
    Patch(family="B", T=180, x=1.5, y=0.0, label="B4"),
    Patch(family="B", T=240, x=1.0, y=0.0, label="B5"),
    Patch(family="B", T=240, x=1.5, y=0.0, label="B6"),
)


def load_family_trades(
    back_db_path: str, code_info_path: str, root: str = ".",
) -> Tuple[List[dict], Dict[str, object]]:
    """RR8 가문(RR8_12/0/21) 발견창 거래 적재 — rr8_12 매도식 지배 거래만.

    prepare_trades 가 매도조건이 rr8_12 절과 일치하는 거래만 채택한다(foreign
    은 제외 카운트). 각 거래에 champ·year·dedup_key 를 부가한다. GPTAUTH 는
    §7대로 미적재(별개 매도식 — 영향거래 0). Returns (trades, report).
    """
    from pathlib import Path
    primary, _ = load_stockinfo_map(back_db_path)
    fallback, _ = load_stockinfo_map(code_info_path)
    conn = connect_back_ro(back_db_path)
    trades: List[dict] = []
    report: Dict[str, object] = {"per_champion": {}, "exclusions": {}}
    try:
        for champ, rel in FAMILY_CSVS.items():
            recs, _ = scan_csvs([str(Path(root) / rel)])
            disc = [r for r in recs if int(r["진입일자"]) <= DISCOVERY_END_DAY]
            champ_trades, excl = prepare_trades(disc, conn, primary, fallback)
            for t in champ_trades:
                t["champ"] = champ
                t["year"] = int(t["진입일자"]) // 10000
                t["dedup_key"] = (t["진입일자"], t["code6"], t["진입시각"])
                trades.append(t)
            report["per_champion"][champ] = {  # type: ignore[index]
                "discovery_rows": len(disc), "accepted": len(champ_trades),
                "exclusions": dict(excl),
            }
    finally:
        conn.close()
    report["total_accepted"] = len(trades)
    report["unique_dedup"] = len({t["dedup_key"] for t in trades})
    return trades, report


def build_ctx_cache_getter(
    back_db_path: str,
) -> Tuple[Callable[[str, int], object], Callable[[], None]]:
    """(code, day) → DayContext 캐시 게터와 닫기 함수. 연결은 read-only URI."""
    conn = connect_back_ro(back_db_path)
    cache: Dict[Tuple[str, int], object] = {}

    def get(code: str, day: int):
        key = (code, int(day))
        if key not in cache:
            idxs, arr, ci = load_day_rows(conn, code, int(day))
            pre = precompute_windows(arr, ci)
            cache[key] = build_day_context(idxs, arr, ci, pre)
        return cache[key]

    def close() -> None:
        conn.close()

    return get, close


def evaluate_trades(
    trades: Sequence[Mapping],
    get_ctx: Callable[[str, int], object],
    candidates: Sequence[Patch] = CANDIDATES,
    Ts: Tuple[int, ...] = T_GRID,
) -> List[dict]:
    """거래별 현직·t=T 상태·후보 패치 청산을 한 레코드로 실측(순수 경로).

    per_T[T] = {held, best_T, sp_T, cut_pct, cut_won}. cand[label] = {time,
    pct, won, cond, hold, affected(청산 상이), dnet_pp, dwon}. dnet 은 현직
    재현 대비(순손익 변화) — 원장이 아니라 재현 현직 기준(재현 오차 상쇄).
    """
    records: List[dict] = []
    for t in trades:
        ctx = get_ctx(t["code6"], int(t["진입일자"]))
        pa = analyze_path(
            ctx, buy_time=int(t["매수시간"]), buy_price=float(t["매수가"]),
            qty=int(t["qty"]), Ts=Ts,
        )
        if pa.status != "ok":
            records.append({**_ident(t), "status": pa.status})
            continue
        cand: Dict[str, dict] = {}
        for patch in candidates:
            ex = replay_patched_pure(
                ctx, buy_time=int(t["매수시간"]), buy_price=float(t["매수가"]),
                qty=int(t["qty"]), patch=patch,
            )
            cand[patch.label] = {
                "time": ex.sell_time, "price": ex.sell_price, "pct": ex.profit_pct,
                "won": ex.profit_won, "cond": ex.cond, "hold": ex.hold_exit,
                "affected": int(ex.sell_time != pa.inc_time),
                "dnet_pp": round(ex.profit_pct - pa.inc_pct, 6),
                "dwon": int(ex.profit_won - pa.inc_won),
                "b_fired": int(ex.cond == B_CLAUSE_TAG),
            }
        records.append({
            **_ident(t), "status": "ok",
            "inc_time": pa.inc_time, "inc_pct": pa.inc_pct, "inc_won": pa.inc_won,
            "inc_cond": pa.inc_cond, "inc_hold": pa.inc_hold, "inc_best": pa.inc_best,
            "led_pct": float(t["원장_수익률"]),
            "per_T": pa.per_T, "cand": cand,
        })
    return records


def _ident(t: Mapping) -> dict:
    return {
        "champ": t["champ"], "code6": t["code6"], "day": int(t["진입일자"]),
        "hms": t["진입시각"], "buy_time": int(t["매수시간"]), "year": int(t["year"]),
        "qty": int(t["qty"]), "buy_price": float(t["매수가"]),
        "dedup_key": tuple(t["dedup_key"]),
    }


def dedup_representative(records: Sequence[Mapping]) -> List[dict]:
    """dedup 키(일자,code6,진입시각) 별 대표 1건 — 쌍둥이 동일 경로라 first-wins.

    반환 레코드에 shared_champs(그 거래를 취한 챔피언 집합)를 부가한다.
    """
    groups: Dict[Tuple, List[Mapping]] = {}
    for r in records:
        groups.setdefault(tuple(r["dedup_key"]), []).append(r)
    out: List[dict] = []
    for key, grp in groups.items():
        rep = dict(grp[0])
        rep["shared_champs"] = sorted({g["champ"] for g in grp})
        out.append(rep)
    return out
