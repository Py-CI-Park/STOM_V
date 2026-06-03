"""백파인더 원리 headless 재현 단위 테스트(분석/생성-시드 전용 — 네트워크/실LLM/실백테 없음).

검증:
  - label_forward_winners: 합성 tick으로 forward-winner 라벨 결정론(미래 +X% 도달 정확)·
    끝부분(미래 부족) 제외(NaN)·lookahead<=0/컬럼부재 graceful·negative 포함.
  - mine_tick_window: 합성 tick DB(tmp sqlite) 로드→라벨→피처 수집; 없는 DB/종목/날짜 graceful.
  - winning_setup_distribution: 세그먼트(시간대×시총) 분포·precision(winner_rate)·lift 산출·
    min_count 필터·'미분류' 제외·is_winner 부재 graceful([]).
  - to_band_seeds: winners q25~q75 → BandSpec(between_le) 시드 후보·NL 가이드·min_lift 필터.
  - 실DB 1종목 1일 smoke(있으면): mine_tick_window가 무예외로 행을 반환.

실LLM/실백테 미사용: tmp sqlite + 손계산 DataFrame만 쓴다(실DB smoke는 있으면 read-only).
"""

import os
import sqlite3
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd  # noqa: E402

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.brain.band_compiler import BandSpec  # noqa: E402
from ai_strategy_loop.fitness.backfinder_principle import (  # noqa: E402
    FORWARD_RETURN_COLUMN,
    IS_WINNER_COLUMN,
    label_forward_winners,
    mine_tick_window,
    to_band_seeds,
    winning_setup_distribution,
)


# ---------------------------------------------------------------------------
# label_forward_winners
# ---------------------------------------------------------------------------
def test_label_forward_winners_is_deterministic_and_excludes_tail():
    """미래 +X% 도달을 정확히 라벨; 끝부분(미래 부족)은 NaN/<NA>로 제외."""
    # prices: 100,100,100,120,100 / lookahead=2, thr=10.
    #   i=0: max(price[1:3])=100 → 0%   (False)
    #   i=1: max(price[2:4])=120 → +20% (True winner)
    #   i=2: max(price[3:5])=120 → +20% (True winner)
    #   i=3: end(3+1+2=6) > n(5) → NaN  (라벨 불가)
    #   i=4: 마지막 행 → NaN
    df = pd.DataFrame({"현재가": [100.0, 100.0, 100.0, 120.0, 100.0]})
    out = label_forward_winners(df, lookahead_ticks=2, threshold_pct=10.0)

    fwd = out[FORWARD_RETURN_COLUMN].tolist()
    assert fwd[0] == 0.0
    assert fwd[1] == 20.0
    assert fwd[2] == 20.0
    assert pd.isna(fwd[3])
    assert pd.isna(fwd[4])

    win = out[IS_WINNER_COLUMN]
    assert win.iloc[0] == False  # noqa: E712 - nullable bool 명시
    assert win.iloc[1] == True   # noqa: E712
    assert win.iloc[2] == True   # noqa: E712
    assert pd.isna(win.iloc[3])
    assert pd.isna(win.iloc[4])


def test_label_forward_winners_threshold_boundary_is_inclusive():
    """상승률이 정확히 threshold면 승자(>= 임계)로 라벨한다."""
    # i=0: max(price[1:2])=110 → +10% == thr 10 → True.
    df = pd.DataFrame({"현재가": [100.0, 110.0, 100.0]})
    out = label_forward_winners(df, lookahead_ticks=1, threshold_pct=10.0)
    assert out[FORWARD_RETURN_COLUMN].iloc[0] == 10.0
    assert out[IS_WINNER_COLUMN].iloc[0] == True  # noqa: E712


def test_label_forward_winners_no_future_winner_is_all_negative():
    """미래에 상승이 없으면 라벨 가능 행은 전부 negative(False)."""
    df = pd.DataFrame({"현재가": [100.0, 100.0, 100.0, 100.0]})
    out = label_forward_winners(df, lookahead_ticks=2, threshold_pct=5.0)
    labelable = out[out[IS_WINNER_COLUMN].notna()]
    assert len(labelable) >= 1
    assert not labelable[IS_WINNER_COLUMN].any()


def test_label_forward_winners_graceful_missing_price_column():
    """현재가 컬럼이 없으면 라벨 컬럼을 NaN/<NA>로 덧붙이고 예외 없이 돌려준다."""
    df = pd.DataFrame({"등락율": [1.0, 2.0, 3.0]})
    out = label_forward_winners(df, lookahead_ticks=2)
    assert FORWARD_RETURN_COLUMN in out.columns
    assert IS_WINNER_COLUMN in out.columns
    assert out[FORWARD_RETURN_COLUMN].isna().all()
    assert out[IS_WINNER_COLUMN].isna().all()


def test_label_forward_winners_graceful_empty_and_nonpositive_lookahead():
    """빈 df·lookahead<=0은 라벨 불가(전부 NaN)로 무예외 흡수."""
    empty = label_forward_winners(pd.DataFrame({"현재가": []}), lookahead_ticks=2)
    assert FORWARD_RETURN_COLUMN in empty.columns and len(empty) == 0

    df = pd.DataFrame({"현재가": [100.0, 120.0, 100.0]})
    zero = label_forward_winners(df, lookahead_ticks=0, threshold_pct=10.0)
    assert zero[FORWARD_RETURN_COLUMN].isna().all()
    assert zero[IS_WINNER_COLUMN].isna().all()


# ---------------------------------------------------------------------------
# mine_tick_window (합성 sqlite DB)
# ---------------------------------------------------------------------------
def _build_synthetic_tick_db(path: str, code: str, day: int):
    """09:00~ 시초에 한 종목이 +X% 급등하는 합성 tick 테이블을 만든다.

    index=YYYYMMDDHHMMSS 정수, 현재가는 초반 평탄→후반 급등(winners 생성). raw 종목 테이블에
    필요한 진입 피처(등락율·체결강도·당일거래대금·시가총액·회전율·초당거래대금·고저평균대비등락율)
    도 함께 채운다. 시분초는 명시하지 않고 index에서 파생되게 한다(레이블러 보강 경로 검증).
    """
    rows = []
    base = day * 1_000_000 + 90000  # 09:00:00.
    n = 60
    for i in range(n):
        # 초반 30틱 평탄(100), 후반 급등(앞 30틱은 미래에 120 도달 → winner).
        price = 100.0 if i < 30 else 120.0
        rows.append({
            "index": base + i,
            "현재가": price,
            "시가": 100.0,
            "고가": max(100.0, price),
            "저가": 100.0,
            "등락율": (price / 100.0 - 1.0) * 100.0,
            "당일거래대금": 1_000_000 + i * 1000,
            "체결강도": 100.0 + i,
            "시가총액": 800.0,  # 억원 단위(초소형 < 1000) — research_segments 정규화 후 초소형.
            "회전율": 1.0 + i * 0.01,
            "초당거래대금": 5000 + i,
            "고저평균대비등락율": 0.5,
        })
    df = pd.DataFrame(rows)
    con = sqlite3.connect(path)
    df.to_sql(code, con, if_exists="replace", index=False)
    con.close()


def test_mine_tick_window_loads_labels_and_collects_features(tmp_path):
    """합성 tick DB에서 라벨링·피처 수집이 동작하고 승자가 잡힌다."""
    db = str(tmp_path / "tick.db")
    code, day = "999999", 20240102
    _build_synthetic_tick_db(db, code, day)

    result = mine_tick_window(
        db, [code], [day],
        time_lo=90000, time_hi=93000,
        lookahead_ticks=5, threshold_pct=10.0,
    )
    assert result["rows"] > 0
    assert result["codes_loaded"] == 1
    # 초반 평탄 구간은 5틱 안에 120 도달 못 하나, 급등 직전 행들은 winner.
    assert result["winner_count"] >= 1
    all_df = result["all"]
    assert IS_WINNER_COLUMN in all_df.columns
    assert "등락율" in all_df.columns
    assert "_code" in all_df.columns and "_day" in all_df.columns
    # winners 부분집합은 전부 is_winner True.
    assert (result["winners"][IS_WINNER_COLUMN] == True).all()  # noqa: E712


def test_mine_tick_window_graceful_missing_db_and_missing_code(tmp_path):
    """없는 DB·없는 종목·없는 날짜는 빈 결과로 무예외 흡수."""
    missing = mine_tick_window(str(tmp_path / "nope.db"), ["999999"], [20240102])
    assert missing["rows"] == 0 and missing["codes_loaded"] == 0
    assert len(missing["all"]) == 0 and len(missing["winners"]) == 0

    db = str(tmp_path / "tick.db")
    _build_synthetic_tick_db(db, "999999", 20240102)
    # 존재하는 DB지만 없는 종목/날짜.
    no_code = mine_tick_window(db, ["000000"], [20240102])
    assert no_code["rows"] == 0 and no_code["codes_loaded"] == 0
    no_day = mine_tick_window(db, ["999999"], [19990101])
    assert no_day["rows"] == 0 and no_day["codes_loaded"] == 0


# ---------------------------------------------------------------------------
# winning_setup_distribution
# ---------------------------------------------------------------------------
def _labeled_for_distribution(n_win=40, n_lose=40):
    """시초(09:00~09:05)·초소형 한 셀에 winners/losers를 섞은 라벨 df.

    winners는 높은 체결강도(~200), losers는 낮은 체결강도(~50)로 둬 분위경계가 분리되게 한다.
    시분초=900xx(09:00~09:05), 시가총액=800(억원 → 초소형).
    """
    rows = []
    for i in range(n_win):
        rows.append({
            "is_winner": True, "forward_return_pct": 15.0,
            "체결강도": 200.0 + (i % 5), "등락율": 5.0 + (i % 3) * 0.1,
            "당일거래대금": 2_000_000.0, "시가총액": 800.0, "회전율": 3.0,
            "초당거래대금": 9000.0, "고저평균대비등락율": 1.0,
            "시분초": 90000 + (i % 200),
        })
    for i in range(n_lose):
        rows.append({
            "is_winner": False, "forward_return_pct": 1.0,
            "체결강도": 50.0 + (i % 5), "등락율": 1.0 + (i % 3) * 0.1,
            "당일거래대금": 1_000_000.0, "시가총액": 800.0, "회전율": 1.0,
            "초당거래대금": 4000.0, "고저평균대비등락율": 0.2,
            "시분초": 90000 + (i % 200),
        })
    df = pd.DataFrame(rows)
    df[IS_WINNER_COLUMN] = df["is_winner"].astype("boolean")
    return df


def test_winning_setup_distribution_emits_quantiles_precision_lift():
    """세그먼트 셀에 winners 분위(q25/q50/q75)·precision(winner_rate)·lift가 산출된다."""
    df = _labeled_for_distribution()
    dist = winning_setup_distribution(df, fine_time=True, min_count=20)
    assert len(dist) >= 1
    cell = dist[0]
    assert cell["market_cap_segment"] == "초소형"
    assert cell["time_segment"] == "0900-0905"
    # precision = winners/total = 40/80 = 0.5.
    assert abs(cell["winner_rate"] - 0.5) < 1e-9
    # 단일 셀이라 base_rate==winner_rate → lift≈1.
    assert cell["lift"] is not None and abs(cell["lift"] - 1.0) < 1e-9
    feats = cell["features"]
    assert feats["체결강도"] is not None
    # winners 체결강도 ~200 → 분위경계가 200 근방.
    assert feats["체결강도"]["q25"] >= 195.0
    assert feats["체결강도"]["q75"] <= 210.0
    assert feats["체결강도"]["n"] == 40


def test_winning_setup_distribution_min_count_filters_small_cells():
    """min_count 미만 셀은 우연변수 제거를 위해 제외된다."""
    df = _labeled_for_distribution(n_win=5, n_lose=5)  # 셀 총 10건.
    dist = winning_setup_distribution(df, fine_time=True, min_count=30)
    assert dist == []


def test_winning_setup_distribution_graceful_missing_label():
    """is_winner 컬럼 부재·빈 df는 빈 리스트로 무예외 흡수."""
    assert winning_setup_distribution(pd.DataFrame(), min_count=1) == []
    assert winning_setup_distribution(pd.DataFrame({"등락율": [1.0, 2.0]}), min_count=1) == []


def test_winning_setup_distribution_lift_above_one_for_rich_cell():
    """승률이 base보다 높은 셀은 lift>1, 낮은 셀은 lift<1로 갈린다(2셀 풀)."""
    # 셀A(초소형/시초): winners 많음(40/50). 셀B(중형/시초): winners 적음(5/50).
    rows = []
    for i in range(40):
        rows.append({"is_winner": True, "체결강도": 200.0, "시가총액": 800.0,
                     "시분초": 90010 + (i % 100), "등락율": 5.0, "당일거래대금": 2e6,
                     "회전율": 3.0, "초당거래대금": 9000.0, "고저평균대비등락율": 1.0})
    for i in range(10):
        rows.append({"is_winner": False, "체결강도": 60.0, "시가총액": 800.0,
                     "시분초": 90010 + (i % 100), "등락율": 1.0, "당일거래대금": 1e6,
                     "회전율": 1.0, "초당거래대금": 4000.0, "고저평균대비등락율": 0.2})
    for i in range(5):
        rows.append({"is_winner": True, "체결강도": 150.0, "시가총액": 5000.0,
                     "시분초": 90010 + (i % 100), "등락율": 4.0, "당일거래대금": 2e6,
                     "회전율": 2.0, "초당거래대금": 8000.0, "고저평균대비등락율": 0.8})
    for i in range(45):
        rows.append({"is_winner": False, "체결강도": 70.0, "시가총액": 5000.0,
                     "시분초": 90010 + (i % 100), "등락율": 1.5, "당일거래대금": 1e6,
                     "회전율": 1.0, "초당거래대금": 4500.0, "고저평균대비등락율": 0.3})
    df = pd.DataFrame(rows)
    df[IS_WINNER_COLUMN] = df["is_winner"].astype("boolean")

    dist = winning_setup_distribution(df, fine_time=True, min_count=20)
    by_mcap = {c["market_cap_segment"]: c for c in dist}
    assert "초소형" in by_mcap and "중형" in by_mcap
    # 초소형 셀(40/50=0.8)은 base(45/100=0.45) 대비 lift>1, 중형(5/50=0.1)은 lift<1.
    assert by_mcap["초소형"]["lift"] > 1.0
    assert by_mcap["중형"]["lift"] < 1.0


# ---------------------------------------------------------------------------
# to_band_seeds
# ---------------------------------------------------------------------------
def test_to_band_seeds_emits_bandspec_between_le_and_nl_guide():
    """winners q25~q75 → BandSpec(between_le) 시드 후보 + NL 가이드."""
    df = _labeled_for_distribution()
    dist = winning_setup_distribution(df, fine_time=True, min_count=20)
    seeds = to_band_seeds(dist, min_lift=0.5)
    assert len(seeds) >= 1
    seed = seeds[0]
    assert seed["band_specs"]
    spec = seed["band_specs"][0]
    assert isinstance(spec, BandSpec)
    assert spec.op == "between_le"
    assert spec.lo is not None and spec.hi is not None and spec.lo < spec.hi
    # 시분초는 시간 분기 전용 → BandSpec으로 만들지 않는다.
    assert all(s.var != "시분초" for s in seed["band_specs"])
    assert isinstance(seed["nl_guide"], str) and len(seed["nl_guide"]) > 0


def test_to_band_seeds_min_lift_filters_and_graceful_empty():
    """min_lift 미만 셀은 시드 제외; 빈 분포는 빈 리스트."""
    assert to_band_seeds([]) == []
    df = _labeled_for_distribution()
    dist = winning_setup_distribution(df, fine_time=True, min_count=20)
    # 단일 셀 lift≈1.0 < min_lift 2.0 → 전부 제외.
    assert to_band_seeds(dist, min_lift=2.0) == []


# ---------------------------------------------------------------------------
# 실DB smoke (있으면) — read-only, 무예외만 검증.
# ---------------------------------------------------------------------------
def test_real_tick_db_smoke_is_graceful():
    """실 tick_subset.db가 있으면 1종목 1일 채굴이 무예외로 끝난다(없으면 skip-동등)."""
    db = os.path.join(PROJECT_ROOT, "ai_strategy_loop", "state", "tick_subset.db")
    if not os.path.isfile(db):
        return  # 실DB 없음 → smoke 스킵(합성 테스트가 본 검증을 담당).
    con = sqlite3.connect(db)
    try:
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        codes = [t for t in tables if t.isdigit()]
        if not codes:
            return
        code = codes[0]
        idx = con.execute(f'SELECT MIN("index") FROM "{code}"').fetchone()[0]
    finally:
        con.close()
    if idx is None:
        return
    day = int(str(int(idx))[:8])
    result = mine_tick_window(db, [code], [day], lookahead_ticks=300, threshold_pct=10.0)
    # 무예외 계약: dict 구조와 키가 항상 존재(행 수는 데이터 의존).
    assert set(result) == {"all", "winners", "rows", "winner_count", "codes_loaded"}
    assert result["rows"] >= 0
