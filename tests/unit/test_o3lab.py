"""O-3 돌파 온셋 측정 단위 테스트 — 합성 픽스처(원본 DB·엔진 불요).

봉인본 §3·§7·§14 검증:
  - 변형 검출: P20/P300 롤링max 교차·창 관측 가드·DH 고가 스텝·OP 상향 교차만·
    VI 첫 present 행·쿨다운·워밍업·t_prev=직전 present 행(허위 재점화 방지).
  - 은행 dedup 키 = (day,code,t0,variant) — 변형이 같은 (day,code,t0) 공유 허용.
  - 연도 세율 reduce-to-v1(0.18%) 정합.
  - 단독 EV 판정: 표본 하한·FDR·strong/variant_kill/insufficient·모집단 분리.
  - 체크포인트 재개(완료 일 건너뜀).
"""
import os
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from alpha_lab.o3lab import bank, breakouts, detect, judge, run  # noqa: E402
from alpha_lab.stats_map import config, costs_v2  # noqa: E402

_W = config.WINDOW_SECONDS
_DAY = 20220517


def _dense(**over):
    """전 오프셋 present dense(benign 기본값) — over 로 특정 컬럼 교체."""
    n = _W + 1
    d = {c: np.zeros(n, dtype=np.float64) for c in detect.COLUMNS_O3}
    d["present"] = np.ones(n, dtype=bool)
    d["매도호가1"][:] = 100.0
    d["매수호가1"][:] = 99.0
    d["시가총액"][:] = 5000.0
    d["현재가"][:] = 100.0
    d["고가"][:] = 100.0
    d["시가"][:] = 100.0
    for k, v in over.items():
        d[k] = np.asarray(v, dtype=(bool if k == "present" else np.float64))
    return d


# --------------------------------------------------------------------------
# 1. 변형 검출 — 롤링max 교차·고가 스텝·상향 교차·VI 첫 행·쿨다운·워밍업·t_prev.
# --------------------------------------------------------------------------

def test_p20_rolling_max_cross():
    cur = np.full(_W + 1, 100.0)
    cur[100:] = 101.0                       # 100초에서 직전 20초 최고 초과.
    on = detect.breakout_onset_offsets(_dense(현재가=cur), "P20", _DAY)
    assert on.tolist() == [100]


def test_p20_warmup_excludes_early():
    cur = np.full(_W + 1, 100.0)
    cur[10:] = 101.0                        # 오프셋 10 교차(<30 워밍업 제외).
    cur[100:] = 102.0                       # 오프셋 100 교차(채택).
    on = detect.breakout_onset_offsets(_dense(현재가=cur), "P20", _DAY).tolist()
    assert 10 not in on and 100 in on


def test_p20_min_obs_guard():
    present = np.zeros(_W + 1, dtype=bool)
    for o in (0, 40, 80, 120, 160):         # 창 [140,159] 내 present 0개 <7.
        present[o] = True
    cur = np.full(_W + 1, 100.0)
    cur[160] = 200.0
    on = detect.breakout_onset_offsets(_dense(present=present, 현재가=cur), "P20", _DAY)
    assert on.size == 0


def test_p300_min_obs_100():
    cur = np.full(_W + 1, 100.0)
    cur[50:] = 101.0                        # 50초: 직전 present 50개 <100 → 온셋 아님.
    cur[400:] = 102.0                       # 400초: 직전 300개 ≥100 → 온셋.
    on = detect.breakout_onset_offsets(_dense(현재가=cur), "P300", _DAY)
    assert on.tolist() == [400]


def test_dh_high_step():
    high = np.full(_W + 1, 100.0)
    high[50:] = 101.0
    high[200:] = 102.0
    on = detect.breakout_onset_offsets(_dense(고가=high), "DH", _DAY)
    assert on.tolist() == [50, 200]


def test_dh_cooldown_within_30s():
    high = np.full(_W + 1, 100.0)
    high[50:] = 101.0
    high[60:] = 102.0                       # 50과 10초 간격 → 쿨다운 억제.
    on = detect.breakout_onset_offsets(_dense(고가=high), "DH", _DAY)
    assert on.tolist() == [50]


def test_op_up_cross_only():
    cur = np.full(_W + 1, 110.0)
    cur[:50] = 90.0                         # 시가 100 아래 → 50초 상향 교차.
    cur[400:] = 90.0                        # 하향 교차는 온셋 아님.
    on = detect.breakout_onset_offsets(_dense(현재가=cur), "OP", _DAY)
    assert on.tolist() == [50]


def test_vi_first_present_row_only():
    rel = detect._offset_to_index(_DAY, 100)
    vi = np.zeros(_W + 1)
    vi[100:] = rel                          # 재개 후 VI해제시간 값 유지.
    on = detect.breakout_onset_offsets(_dense(VI해제시간=vi), "VI", _DAY)
    assert on.tolist() == [100]             # 같은 VI값 첫 present 행 1회.


def test_cross_uses_prev_present_row_no_refire():
    # 결측 갭 후 재점화 방지(F7-①): 갭 이전 이미 상태 True → 갭 뒤 재발화 없음.
    present = np.ones(_W + 1, dtype=bool)
    present[100:131] = False                # 100~130 결측 갭.
    cur = np.full(_W + 1, 110.0)
    cur[:40] = 90.0                         # 40초 상향 교차, 이후 계속 위.
    on = detect.breakout_onset_offsets(_dense(present=present, 현재가=cur), "OP", _DAY)
    assert on.tolist() == [40]              # 갭 뒤(131) 재발화 없음.


# --------------------------------------------------------------------------
# 2. 은행 dedup 키 = (day,code,t0,variant) — 변형 공유 (day,code,t0) 허용.
# --------------------------------------------------------------------------

def _bank_rows(variants, *, same_t0=True):
    n = len(variants)
    t0 = [_DAY * 1_000_000 + 90140] * n if same_t0 else \
        [_DAY * 1_000_000 + 90140 + i for i in range(n)]
    return pd.DataFrame({
        "code": ["000001"] * n, "day": [_DAY] * n, "off": [140] * n, "t0": t0,
        "year": [2022] * n, "variant": list(variants),
        "updown_q": [0] * n, "mktcap_b": [0] * n, "time_b": [0] * n, "gap_b": [0] * n,
        "l3_net": [0.001] * n, "l3_labeled": [True] * n, "l3_clause": [5] * n,
        "l3_exit": [0] * n, "h300_net": [0.0] * n, "h300_valid": [True] * n,
    })


def test_bank_variants_share_t0_no_dup():
    df = bank.stamp_lineage(_bank_rows(["P20", "P300", "DH"], same_t0=True))
    res = bank.append_contract(df, 20220323, 20231231)
    assert res["ok"] is True                # 같은 (day,code,t0) 다른 variant → 위반 없음.


def test_bank_identical_key_is_dup():
    df = bank.stamp_lineage(_bank_rows(["P20", "P20"], same_t0=True))
    res = bank.append_contract(df, 20220323, 20231231)
    assert res["ok"] is False
    assert any(v["check"] == "dup_key" for v in res["violations"])


def test_bank_lineage_stamped():
    df = bank.stamp_lineage(_bank_rows(["P20"]))
    assert (df["onset_type"] == "breakout").all()
    assert (df["exit_label"] == "L3_RR8_12").all()
    assert (df["audit_tag"] == "RR8_12-conditional").all()


def test_bank_write_and_read(tmp_path):
    df = _bank_rows(["P20", "OP"], same_t0=True)
    receipt = bank.write_bank(df, tmp_path / "o3_bank.parquet", window=(20220323, 20231231))
    assert receipt["written"] is True
    got = pd.read_parquet(tmp_path / "o3_bank.parquet")
    assert set(bank.BANK_SCHEMA).issubset(set(got.columns))
    assert (got["onset_type"] == "breakout").all()


# --------------------------------------------------------------------------
# 3. 연도 세율 reduce-to-v1(0.18%) — 발화 무관 회계.
# --------------------------------------------------------------------------

def test_year_tax_reduces_to_v1_at_018():
    from alpha_lab.dataset import labels
    buy, sell = labels.adverse_fill(1000.0, 1010.0)
    assert abs(labels.net_rate(buy, sell) - costs_v2.net_rate_year(buy, sell, 0.0018)) < 1e-12


def test_year_tax_sealed_keys():
    from alpha_lab.stats_map import config_v2
    assert config_v2.year_tax_rate(2022) == 0.0023
    assert config_v2.year_tax_rate(2023) == 0.0020


# --------------------------------------------------------------------------
# 4. 단독 EV 판정 — 하한·strong/variant_kill/insufficient·모집단 분리.
# --------------------------------------------------------------------------

def _days(n, year):
    base = year * 10000 + 300
    return np.array([base + 1 + (i % 20) for i in range(n)], dtype=np.int64)


def _unit(mean, n, spread=0.02, seed=0):
    rng = np.random.default_rng(seed)
    half = n // 2
    day = np.concatenate([_days(half, 2022), _days(n - half, 2023)])
    return {"net_pp": mean + rng.normal(0, spread, n), "day": day, "year": day // 10000}


def test_judge_strong_when_high_mean():
    res = judge.judge_all_o3({"P20:all": _unit(0.30, 3000)})
    r = res["per_unit"]["P20:all"]
    assert r["floor_pass"] is True
    assert r["classification"] == "strong"
    assert res["n_strong"] == 1 and res["fdr_denominator"] == 1


def test_judge_variant_kill_when_ci_high_negative():
    res = judge.judge_all_o3({"P20:all": _unit(-0.50, 3000)})
    assert res["per_unit"]["P20:all"]["classification"] == "variant_kill"
    assert res["kill1_all_ci_high_negative"] is True


def test_judge_insufficient_when_below_floor():
    res = judge.judge_all_o3({"P20:all": _unit(0.30, 100)})     # n<2000.
    assert res["per_unit"]["P20:all"]["floor_pass"] is False
    assert res["per_unit"]["P20:all"]["classification"] == "insufficient"
    assert "P20:all" in res["insufficient_units"]
    assert res["fdr_denominator"] == 0


def test_judge_fdr_denominator_counts_qualified_only():
    res = judge.judge_all_o3({"P20:all": _unit(0.30, 3000),
                              "OP:all": _unit(0.30, 100)})       # OP 하한 미달.
    assert res["fdr_denominator"] == 1                          # 자격 1(P20)만.


def test_split_qualified_units_population():
    variant = np.array(["P20", "P20", "OP"])
    net = np.array([0.1, 0.2, 0.3])
    day = np.array([_DAY] * 3)
    year = np.array([2022] * 3)
    labeled = np.array([True, True, True])
    nonover = np.array([True, False, True])                     # 두 번째 P20 은 서지 겹침.
    units = judge.split_qualified_units(variant, net, day, year, labeled, nonover,
                                        variants=("P20", "OP"))
    assert units["P20:all"]["net_pp"].size == 2
    assert units["P20:surge_nonoverlap"]["net_pp"].size == 1
    assert units["OP:surge_nonoverlap"]["net_pp"].size == 1


# --------------------------------------------------------------------------
# 5. 체크포인트 재개 + consolidate census(스텁 — DB 불요).
# --------------------------------------------------------------------------

def _stub_day(_db_path, date, _sell_text, *, spot_pure=False):
    rec = {k: np.array([]) for k in breakouts.BREAKOUT_COLUMNS}
    rec["code"] = np.array(["000001", "000001"], dtype="U6")
    rec["day"] = np.array([int(date)] * 2, dtype=np.int32)
    rec["off"] = np.array([100, 400], dtype=np.int16)
    rec["t0"] = np.array([int(date) * 1_000_000 + 90140,
                          int(date) * 1_000_000 + 90640], dtype=np.int64)
    rec["year"] = np.array([int(date) // 10000] * 2, dtype=np.int16)
    rec["variant"] = np.array(["P20", "OP"], dtype="U4")
    for k in ("updown_q", "mktcap_b", "time_b", "gap_b"):
        rec[k] = np.array([0, 0], dtype=np.int8)
    rec["l3_net"] = np.array([0.001, -0.002], dtype=np.float64)
    rec["l3_labeled"] = np.array([True, True])
    rec["l3_clause"] = np.array([5, 0], dtype=np.int16)
    rec["l3_exit"] = np.array([0, 0], dtype=np.int64)
    rec["h300_net"] = np.array([0.001, np.nan], dtype=np.float64)
    rec["h300_valid"] = np.array([True, False])
    meta = {"n_codes": 1, "n_onsets": 2, "per_variant": breakouts._variant_meta(rec)}
    return rec, meta


def test_run_extract_checkpoint_resume(tmp_path, monkeypatch):
    monkeypatch.setattr(breakouts, "build_day_breakouts", _stub_day)
    parts = tmp_path / "parts"
    days = [("20220517", tmp_path / "f1.db"), ("20220518", tmp_path / "f2.db")]

    r1 = run.run_extract(tmp_path, tmp_path, parts, "SELLTEXT", days=days)
    assert r1["days_done"] == 2
    assert (parts / "o3_20220517.parquet").exists()
    assert (parts / "meta_20220517.json").exists()

    calls = {"n": 0}

    def _counting(*a, **k):
        calls["n"] += 1
        return _stub_day(*a, **k)

    monkeypatch.setattr(breakouts, "build_day_breakouts", _counting)
    r2 = run.run_extract(tmp_path, tmp_path, parts, "SELLTEXT", days=days)
    assert r2["days_done"] == 2
    assert calls["n"] == 0                                     # 재계산 없음(재개).


def test_consolidate_writes_bank_and_census(tmp_path, monkeypatch):
    monkeypatch.setattr(breakouts, "build_day_breakouts", _stub_day)
    parts = tmp_path / "parts"
    days = [("20220517", tmp_path / "f1.db")]
    run.run_extract(tmp_path, tmp_path, parts, "SELLTEXT", days=days)
    cons = run.consolidate(parts, tmp_path / "o3_bank.parquet", window=(20220323, 20231231))
    assert cons["bank_write"]["written"] is True
    assert cons["per_variant"]["P20"]["n_onsets"] == 1
    assert cons["per_variant"]["OP"]["n_onsets"] == 1
    assert (tmp_path / "o3_bank.parquet").exists()
