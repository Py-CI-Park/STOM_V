"""alpha_lab.distill.replay 단위 테스트 — P5 청산 축(재현게이트 + 격자 시뮬).

실DB 불필요(합성 sqlite/배열). 실행:
    python -m pytest tests/unit/test_alpha_replay.py -q

검증 대상 의미론은 전부 실측 미러다:
  - kiwoom_pgsgsp: utility.static.GetKiwoomPgSgSp(원장 671행 전수 재현 확인식)
  - 매도식 재실행: backtest/backengine_kiwoom_tick.py Strategy() 흐름
    (일 마지막 행 LastSell 전용·사다리 3호가 체결·tick_count 게이트)
  - 격자 시뮬: p5_preregistration_v1.json exit_grid/policy_semantics 봉인.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pytest

from alpha_lab.dataset.labels import adverse_fill, net_rate
from alpha_lab.distill.replay import (
    CHAMPION_SELL_CONDS,
    EXIT_GRID_AXES,
    connect_back_ro,
    exit_grid_policies,
    hoga_unit,
    kiwoom_pgsgsp,
    load_day_rows,
    precompute_windows,
    replay_champion_exit,
    replay_path,
    simulate_exit,
    tick_distance,
)

_LEDGER = (
    Path(__file__).resolve().parents[2]
    / "docs/research/condition_research/research_runs/alpha_lab_20260705"
    / "distill/champion_ledger.jsonl"
)

# ---------------------------------------------------------------------------
# 수익률 규약(엔진 미러)
# ---------------------------------------------------------------------------

def test_kiwoom_pgsgsp_matches_ledger_observed_case():
    # 원장 1행 실측: 매수가 6650×753, 매도가 7050 → 매도금액 5297555 · 수익금
    # 290105 · 수익률 5.79 (champion_ledger.jsonl 첫 행).
    pg, sg, sp = kiwoom_pgsgsp(753 * 6650, 753 * 7050)
    assert (pg, sg, sp) == (5297555, 290105, 5.79)


def test_kiwoom_pgsgsp_parity_with_engine_source():
    static = pytest.importorskip("utility.static")
    for bg, cg in ((1_000_000, 940_000), (5_007_450, 5_308_650), (123_456, 130_001)):
        assert kiwoom_pgsgsp(bg, cg) == static.GetKiwoomPgSgSp(bg, cg)


# ---------------------------------------------------------------------------
# 호가단위·틱 거리
# ---------------------------------------------------------------------------

def test_hoga_unit_regime_split_2023():
    assert hoga_unit(15000, 20220601) == 50    # 개편 전: 1만~5만 = 50원
    assert hoga_unit(15000, 20250103) == 10    # 개편 후: 5천~2만 = 10원
    assert hoga_unit(1999, 20250103) == 1
    assert hoga_unit(2000, 20250103) == 5


def test_tick_distance_exact_and_band_cross():
    assert tick_distance(7050, 7050, 20250103) == 0.0
    assert tick_distance(6650, 6660, 20250103) == 1.0
    # 1998 → 2005 (개편 후): 1998+1=1999, +1=2000, +5=2005 → 3틱.
    assert tick_distance(1998, 2005, 20250103) == 3.0
    # 격자 밖 VWAP 가격은 소수 틱으로 계량(반올림 없음 — 보수).
    assert tick_distance(7047, 7050, 20250103) == pytest.approx(0.3)


# ---------------------------------------------------------------------------
# 봉인 격자 정의
# ---------------------------------------------------------------------------

def test_exit_grid_policies_are_sealed_192():
    policies = exit_grid_policies()
    assert len(policies) == 192
    assert {p["hard_stop_pct"] for p in policies} == set(EXIT_GRID_AXES["hard_stop_pct"])
    assert {p["trailing_pct"] for p in policies} == set(EXIT_GRID_AXES["trailing_pct"])
    assert {p["time_stop_sec"] for p in policies} == set(EXIT_GRID_AXES["time_stop_sec"])
    assert {p["profit_cap_pct"] for p in policies} == set(EXIT_GRID_AXES["profit_cap_pct"])
    for p in policies:
        assert (p["trailing_arm_pct"] == 3.0) == (p["trailing_pct"] is not None)
    # 데카르트 곱 전수 — 중복 없음.
    keys = {(p["hard_stop_pct"], p["trailing_pct"], p["time_stop_sec"],
             p["profit_cap_pct"]) for p in policies}
    assert len(keys) == 192


# ---------------------------------------------------------------------------
# replay_path — 관측 초 경로
# ---------------------------------------------------------------------------

def _make_tick_db(tmp_path, rows):
    db = tmp_path / "tick.db"
    conn = sqlite3.connect(db)
    conn.execute('CREATE TABLE "123456" ("index" INTEGER PRIMARY KEY, "매수호가1" REAL)')
    conn.executemany('INSERT INTO "123456" VALUES (?, ?)', rows)
    conn.commit()
    conn.close()
    return db


def test_replay_path_offsets_missing_and_horizon(tmp_path):
    rows = [
        (20250103090059, 10000.0),   # 매수시간 행(경로 제외 — index > 매수시간만)
        (20250103090100, 10010.0),   # +1초(분 롤오버)
        (20250103090102, 10020.0),   # +3초(결측 초 090101 미보간)
        (20250103090103, None),      # NULL 매수호가 → 관측 불능 제외
        (20250103090104, 0.0),       # 0 매수호가 → 제외
        (20250103092900, 10030.0),   # force_exit 경계(포함)
        (20250103092901, 10040.0),   # 경계 밖 → 제외
    ]
    db = _make_tick_db(tmp_path, rows)
    conn = connect_back_ro(db)
    try:
        trade = {"code6": "123456", "진입일자": "20250103", "매수시간": 20250103090059}
        path = replay_path(trade, conn)
    finally:
        conn.close()
    assert path == [(1, 10010.0), (3, 10020.0), (1681, 10030.0)]


def test_replay_path_rejects_bad_code(tmp_path):
    db = _make_tick_db(tmp_path, [(20250103090100, 100.0)])
    conn = connect_back_ro(db)
    try:
        with pytest.raises(ValueError):
            replay_path({"code6": "12x456", "진입일자": "20250103",
                         "매수시간": 20250103090059}, conn)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# simulate_exit — 봉인 정책 의미론
# ---------------------------------------------------------------------------

_ENTRY = 10000.0


def _mark(bid):
    return net_rate(_ENTRY, bid) * 100.0


def test_simulate_exit_hard_stop_fills_next_observed_sec():
    # 9700원 mark ≈ -3.2%, 9500원 mark ≈ -5.2% ≤ -5 → 발동, 다음 관측 초 체결.
    assert _mark(9500.0) <= -5.0 < _mark(9700.0)
    path = [(1, 9700.0), (2, 9500.0), (4, 9550.0), (5, 9600.0)]
    out = simulate_exit(path, {"hard_stop_pct": -5.0}, entry_price=_ENTRY)
    assert out["reason"] == "hard_stop"
    assert out["exit_sec"] == 4.0
    _, sell_fill = adverse_fill(_ENTRY, 9550.0, 2)
    assert out["exit_price"] == sell_fill
    assert out["net_rate"] == pytest.approx(net_rate(_ENTRY, sell_fill))


def test_simulate_exit_trigger_at_last_sec_fills_same_sec():
    path = [(1, 9700.0), (2, 9500.0)]
    out = simulate_exit(path, {"hard_stop_pct": -5.0}, entry_price=_ENTRY)
    assert out["exit_sec"] == 2.0
    _, sell_fill = adverse_fill(_ENTRY, 9500.0, 2)
    assert out["exit_price"] == sell_fill


def test_simulate_exit_trailing_requires_arm():
    # 최고 +2%대(암 3.0 미달) 후 급락 — 트레일링 미발동, force_exit.
    path = [(1, 10250.0), (2, 10000.0), (3, 10000.0)]
    out = simulate_exit(path, {"trailing_pct": 60.0}, entry_price=_ENTRY)
    assert out["reason"] == "force_exit"
    # 최고 +3% 초과 후 60% 리테이스 이탈 → 발동.
    armed = [(1, 10400.0), (2, 10150.0), (3, 10100.0)]
    assert _mark(10400.0) > 3.0
    assert _mark(10150.0) <= _mark(10400.0) * 0.6
    out2 = simulate_exit(armed, {"trailing_pct": 60.0}, entry_price=_ENTRY)
    assert out2["reason"] == "trailing"
    assert out2["exit_sec"] == 3.0


def test_simulate_exit_profit_cap_and_time_stop():
    path = [(1, 10200.0), (2, 10400.0), (3, 10400.0)]
    out = simulate_exit(path, {"profit_cap_pct": 3.0}, entry_price=_ENTRY)
    assert out["reason"] == "profit_cap" and out["exit_sec"] == 3.0
    path2 = [(30, 10000.0), (61, 10000.0), (65, 10000.0)]
    out2 = simulate_exit(path2, {"time_stop_sec": 60}, entry_price=_ENTRY)
    assert out2["reason"] == "time_stop" and out2["exit_sec"] == 65.0


def test_simulate_exit_priority_hard_stop_first():
    # 암 후 -5% 급락 초: hard_stop과 trailing 동시 충족 → hard_stop 우선(봉인).
    path = [(1, 10400.0), (2, 9500.0), (3, 9500.0)]
    policy = {"hard_stop_pct": -5.0, "trailing_pct": 60.0}
    out = simulate_exit(path, policy, entry_price=_ENTRY)
    assert out["reason"] == "hard_stop"


def test_simulate_exit_force_exit_and_empty_path():
    path = [(1, 10000.0), (1000, 10050.0)]
    out = simulate_exit(path, {"hard_stop_pct": -5.0}, entry_price=_ENTRY)
    assert out["reason"] == "force_exit"
    assert out["exit_sec"] == 1000.0
    with pytest.raises(ValueError):
        simulate_exit([], {"hard_stop_pct": -5.0}, entry_price=_ENTRY)


# ---------------------------------------------------------------------------
# 엔진 미러 재현(replay_champion_exit)
# ---------------------------------------------------------------------------

_COLS = ("현재가", "시가", "등락율", "초당매수수량", "초당매도수량", "시가총액",
         "매수총잔량", "매수호가1", "매수호가2", "매수호가3",
         "매수잔량1", "매수잔량2", "매수잔량3")


def _mk_day(n, buy_pos, price_fn, ladder_fn):
    """합성 일 배열 — 090000부터 초당 1행(n<=60*60 가정), 시가총액 2조(절 6~9 차단)."""
    idxs = []
    rows = []
    for i in range(n):
        hh, rem = divmod(i, 3600)
        mm, ss = divmod(rem, 60)
        idxs.append(20250103090000 + hh * 10000 + mm * 100 + ss)
        price = price_fn(i)
        bid1, bid2, bid3, r1, r2, r3 = ladder_fn(i)
        rows.append([price, 9000.0, 5.0, 10.0, 10.0, 20000.0, 1000.0,
                     bid1, bid2, bid3, r1, r2, r3])
    arr = np.array(rows, dtype=np.float64)
    ci = {c: i for i, c in enumerate(_COLS)}
    return np.array(idxs, dtype=np.int64), arr, ci


def test_replay_champion_hard_stop_with_ladder_retry():
    # 매수 후 -6%대 급락(절 4 발동). 첫 발동 행은 3호가 잔량 부족(90<100)으로
    # 미체결 보유(엔진 Sell no-op 미러), 다음 행에서 체결.
    buy_pos = 60

    def price_fn(i):
        return 10000.0 if i <= buy_pos + 1 else 9400.0

    def ladder_fn(i):
        if i == buy_pos + 2:
            return (9390.0, 9380.0, 9370.0, 30.0, 30.0, 30.0)  # 부족
        return (9390.0, 9380.0, 9370.0, 100.0, 0.0, 0.0)
    idxs, arr, ci = _mk_day(buy_pos + 6, buy_pos, price_fn, ladder_fn)
    pre = precompute_windows(arr, ci)
    out = replay_champion_exit(
        idxs, arr, ci, pre, buy_time=int(idxs[buy_pos]), buy_price=10000.0, qty=100,
    )
    assert out["status"] == "ok"
    assert out["cond"] == 4
    assert out["sell_time"] == int(idxs[buy_pos + 3])  # 미체결 1행 지연.
    assert out["sell_price"] == 9390.0
    _, _, expected_sp = kiwoom_pgsgsp(100 * 10000, 100 * 9390)
    assert out["profit_pct"] == expected_sp


def test_replay_champion_last_row_is_lastsell_only():
    # 어떤 절도 발동하지 않는 평탄 경로 → 일 마지막 행 LastSell(cond 0),
    # 사다리 잔량 0이면 매수호가1 강제 체결(GetLastSellPrice 미러).
    buy_pos = 60

    def price_fn(i):
        return 10000.0

    def ladder_fn(i):
        return (9990.0, 9980.0, 9970.0, 0.0, 0.0, 0.0)
    idxs, arr, ci = _mk_day(buy_pos + 5, buy_pos, price_fn, ladder_fn)
    pre = precompute_windows(arr, ci)
    out = replay_champion_exit(
        idxs, arr, ci, pre, buy_time=int(idxs[buy_pos]), buy_price=10000.0, qty=100,
    )
    assert out["status"] == "ok"
    assert out["cond"] == 0
    assert out["sell_time"] == int(idxs[-1])
    assert out["sell_price"] == 9990.0


def test_replay_champion_low_price_clause_gated_by_tick_count():
    # 절 3(보유시간>60 & 현재가<최저현재가(60,보유시간))은 tick_count(일중 행수)가
    # 60+보유시간에 미달이면 0을 반환해 발동 불가(엔진 _Parameter_Area 게이트
    # 미러). 이른 매수(buy_pos=10)면 60+hold = 60+(i-10) > i+1 이 항상 성립해
    # 지속 신저가에도 절 3은 영구 불발 → LastSell(cond 0)로 종료해야 한다.
    buy_pos = 10
    n = buy_pos + 90

    def price_fn(i):
        if i <= buy_pos:
            return 10000.0
        return 9950.0 - 0.5 * (i - buy_pos)  # 지속 신저가(수익률 > -5 유지).

    def ladder_fn(i):
        return (9900.0, 9890.0, 9880.0, 1000.0, 0.0, 0.0)
    idxs, arr, ci = _mk_day(n, buy_pos, price_fn, ladder_fn)
    pre = precompute_windows(arr, ci)
    out = replay_champion_exit(
        idxs, arr, ci, pre, buy_time=int(idxs[buy_pos]), buy_price=10000.0, qty=100,
    )
    assert out["status"] == "ok"
    assert out["cond"] == 0  # 절 3이 게이트로 전 구간 불발 → 전략종료청산.


def test_replay_champion_entry_row_missing():
    idxs, arr, ci = _mk_day(70, 60, lambda i: 10000.0,
                            lambda i: (9990.0, 9980.0, 9970.0, 1.0, 1.0, 1.0))
    pre = precompute_windows(arr, ci)
    out = replay_champion_exit(
        idxs, arr, ci, pre, buy_time=20250103095959, buy_price=10000.0, qty=10,
    )
    assert out["status"] == "entry_row_missing"


def test_precompute_windows_semantics():
    rng = np.random.default_rng(7)
    n = 90
    price = 10000 + np.cumsum(rng.integers(-5, 6, size=n)).astype(np.float64)
    pct = np.linspace(1.0, 4.0, n)
    arr = np.zeros((n, len(_COLS)))
    ci = {c: i for i, c in enumerate(_COLS)}
    arr[:, ci["현재가"]] = price
    arr[:, ci["등락율"]] = pct
    pre = precompute_windows(arr, ci)
    # 이동평균60 = rolling(60).mean().round(3) (utility.static.add_rolling_data 미러).
    assert np.isnan(pre["ma60"][58])
    assert pre["ma60"][59] == pytest.approx(round(price[:60].mean(), 3))
    assert pre["ma60"][75] == pytest.approx(round(price[16:76].mean(), 3))
    # 등락율각도30 = shift(29) 의미론(avg_list=[30] 게이트런 실측).
    expect = round(
        float(np.arctan2((pct[40] - pct[11]) * 5.0, 30.0) / (2 * np.pi) * 360.0), 2,
    )
    assert pre["ang30"][40] == pytest.approx(expect)


def test_load_day_rows_reads_ro_and_orders(tmp_path):
    db = tmp_path / "day.db"
    conn = sqlite3.connect(db)
    cols = ", ".join(f'"{c}" REAL' for c in _COLS)
    conn.execute(f'CREATE TABLE "654321" ("index" INTEGER, {cols})')
    row = [1.0] * len(_COLS)
    conn.execute(f'INSERT INTO "654321" VALUES (20250103092000, {", ".join(map(str, row))})')
    conn.execute(f'INSERT INTO "654321" VALUES (20250103090001, {", ".join(map(str, row))})')
    conn.execute(f'INSERT INTO "654321" VALUES (20250103093000, {", ".join(map(str, row))})')
    conn.commit()
    conn.close()
    ro = connect_back_ro(db)
    try:
        idxs, arr, ci = load_day_rows(ro, "654321", 20250103)
    finally:
        ro.close()
    # 92800 창 밖(093000) 제외 + index 오름차순.
    assert idxs.tolist() == [20250103090001, 20250103092000]
    assert arr.shape == (2, len(_COLS))
    with pytest.raises(ValueError):
        load_day_rows(ro, "65432x", 20250103)


# ---------------------------------------------------------------------------
# 챔피언 절 원문 계약 — 커밋된 원장과의 대조(파일 부재 시 skip)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LEDGER.exists(), reason="champion ledger not present")
def test_champion_cond_texts_cover_ledger():
    conds = {}
    with open(_LEDGER, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                text = json.loads(line)["매도조건"]
                conds[text] = conds.get(text, 0) + 1
    known = set(CHAMPION_SELL_CONDS.values())
    covered = sum(v for k, v in conds.items() if k in known)
    foreign = sum(v for k, v in conds.items() if k not in known)
    # 실측: 671행 중 667행이 챔피언 매도식 절, 4행은 변형 런 절(정직 제외 대상).
    assert covered == 667
    assert foreign == 4
