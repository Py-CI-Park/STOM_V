"""alpha_lab.stats_map 단위 테스트 — S-트랙 봉인 로직(비용식·축·서지·추출·스키마).

검증 대상(사전등록 2026-07-10_s_track_preregistration.md 봉인):
- costs: 벡터식 net_rate가 labels.py 스칼라식과 원소별 max_err=0(패리티 게이트 근거).
- axes: 분위/시총/시간대 버킷 경계(경계값 상단 포함), 서지배수(관측<10·평균>0
  가드), 온셋(교차 + 30초 쿨다운).
- extract: 합성 미니 DB에서 후보/지평별 절단/온셋/MFE≥net≥MAE 불변식.
- schema: 요약 sha 결정론 + 적재 왕복.

합성 미니 1일 DB는 실측 계약을 미러링한다(index=int YYYYMMDDHHMMSS,
moneytop '거래대금순위'='code;...').
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pytest

from alpha_lab.dataset import labels as _labels
from alpha_lab.stats_map import axes, builder, config, costs, extract, schema, stats

# extract._load_dense가 SELECT하는 저장 컬럼(순서 무관, 존재만 필요).
_STOCK_COLUMNS = (
    "매도호가1", "매수호가1", "초당거래대금", "등락율", "시가총액",
    "체결강도", "매수총잔량", "매도총잔량",
)


# ── costs: 벡터식 ↔ labels.py 패리티 ────────────────────────────────────────
def test_cost_parity_zero_error():
    rng = np.random.default_rng(7)
    ask = rng.uniform(1000, 400000, 4000)
    bid = np.clip(ask - rng.uniform(0, 800, 4000), 1.0, None)
    assert costs.parity_max_err(ask, bid) == 0.0


def test_krx_tick_size_band_boundaries():
    prices = np.array([1999, 2000, 4999, 5000, 19999, 50000, 199999, 500000])
    expected = np.array([1, 5, 5, 10, 10, 100, 100, 1000.0])
    assert np.array_equal(costs.krx_tick_size_vec(prices), expected)


def test_net_rate_vec_matches_scalar():
    buy, sell = 10000.0, 10050.0
    bf, sf = costs.adverse_fill_vec(np.array([buy]), np.array([sell]))
    scalar = _labels.net_rate(*_labels.adverse_fill(buy, sell))
    assert costs.net_rate_vec(bf, sf)[0] == pytest.approx(scalar, abs=0.0)


# ── axes: 버킷 경계 + 서지 ──────────────────────────────────────────────────
def test_bucket_edges_upper_inclusive():
    assert list(axes.updown_quartile(np.array(config.UPDOWN_EDGES))) == [1, 2, 3]
    assert list(axes.mktcap_bucket(np.array(config.MKTCAP_EDGES))) == [1, 2]
    off = np.array([0, 299, 300, 1499, 1500])
    assert list(axes.time_bucket_label(axes.time_bucket_offset(off))) == \
        [900, 900, 905, 920, 925]


def test_surge_ratio_obs_and_positive_guards():
    present = np.zeros(60, bool)
    amt = np.zeros(60)
    present[0:40] = True          # 앞 40초 관측.
    amt[0:40] = 100.0
    amt[40] = 500.0; present[40] = True
    ratio = axes.surge_ratio(amt, present)
    # off=40: 직전 30초 관측 30개(≥10), 평균 100 → 500/100=5.0.
    assert ratio[40] == pytest.approx(5.0)
    # off<10: 직전 관측<10 → NaN.
    assert np.isnan(ratio[5])


def test_surge_onset_crossing_and_cooldown():
    n = 80
    ratio = np.zeros(n)
    present = np.ones(n, bool)
    ratio[10] = 3.0            # 첫 교차(온셋).
    ratio[20] = 3.0            # 쿨다운(10~39) 내 → 억제.
    ratio[45] = 3.0            # 쿨다운 밖 → 온셋.
    onset = axes.surge_onset_mask(ratio, present)
    assert list(np.nonzero(onset)[0]) == [10, 45]


# ── extract: 합성 미니 DB 불변식 ────────────────────────────────────────────
def _make_mini_db(path: Path) -> None:
    """한 종목이 09:24:00~09:30:00 매초 연속 관측되는 미니 tick DB.

    창 끝(09:30:00=오프셋 1800) 부근을 덮어 h300 절단 경계(off>1500)를 실제로
    검증할 수 있게 한다. 09:25:00(오프셋 1500)까지는 exit 존재 → 유효,
    그 이후 t0는 exit이 창을 넘어 절단된다.
    """
    conn = sqlite3.connect(str(path))
    cols = ", ".join(f'"{c}" REAL' for c in _STOCK_COLUMNS)
    conn.execute(f'CREATE TABLE "005930" ("index" INTEGER, {cols})')
    conn.execute('CREATE TABLE moneytop ("index" INTEGER, "거래대금순위" TEXT)')
    base = 20220323_090000
    for sec in range(1440, 1801):                 # 09:24:00..09:30:00.
        ts = _add_seconds(base, sec)
        row = (ts, 10000.0, 9990.0, 100.0, 2.5, 1500.0, 110.0, 200.0, 180.0)
        conn.execute(
            f'INSERT INTO "005930" VALUES ({",".join("?" for _ in row)})', row)
        conn.execute('INSERT INTO moneytop VALUES (?, ?)', (ts, "005930"))
    conn.commit()
    conn.close()


def _add_seconds(base: int, sec: int) -> int:
    from datetime import datetime, timedelta
    dt = datetime.strptime(str(base), "%Y%m%d%H%M%S") + timedelta(seconds=sec)
    return int(dt.strftime("%Y%m%d%H%M%S"))


def test_extract_candidates_and_censor(tmp_path):
    db = tmp_path / "stock_tick_20220323.db"
    _make_mini_db(db)
    rec = extract.extract_day(db, "20220323")
    assert rec["off"].size > 0
    # h300 절단은 off+300>1800 → off>1500(09:25:00 이후)에서만 발생(계단).
    cens = rec["censored_300"]
    off = rec["off"]
    assert cens[off > 1500].all()
    assert not cens[off <= 1500].any()
    # 유효 표본은 MFE≥net≥MAE(비용식 단조).
    v = rec["valid_300"]
    net, mfe, mae = rec["net_300"][v], rec["mfe_300"][v], rec["mae_300"][v]
    fin = np.isfinite(mfe) & np.isfinite(mae)
    assert (mfe[fin] >= net[fin] - 1e-6).all()
    assert (mae[fin] <= net[fin] + 1e-6).all()


def test_extract_readonly_does_not_write(tmp_path):
    db = tmp_path / "stock_tick_20220323.db"
    _make_mini_db(db)
    before = db.stat().st_mtime_ns
    extract.extract_day(db, "20220323")
    assert db.stat().st_mtime_ns == before  # read-only — 원본 무변경.


# ── stats + schema: 결정론 ─────────────────────────────────────────────────
def test_spearman_monotone_is_one():
    x = np.arange(100.0)
    assert stats.spearman(x, 2 * x + 1) == pytest.approx(1.0)
    assert stats.spearman(x, -x) == pytest.approx(-1.0)


def test_summary_sha_deterministic():
    cells = {"cells_l0": [{c: 1 for c in schema.CELL_COLUMNS}], "cells_l1": []}
    corr = [{"kind": "ic", "var1": "updown", "var2": "net_300",
             "value": 0.1, "n": 10}]
    assert schema.summary_sha(cells, corr) == schema.summary_sha(cells, corr)


def test_schema_roundtrip(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "m.db"))
    schema.create_schema(conn)
    row = {c: 0 for c in schema.CELL_COLUMNS}
    row["mean_net"] = -0.01
    schema.insert_cells(conn, "cells_l0", [row])
    got = conn.execute("SELECT mean_net FROM cells_l0").fetchone()[0]
    assert got == pytest.approx(-0.01)
    conn.close()
