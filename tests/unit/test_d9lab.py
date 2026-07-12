"""D9 전이 온셋 측정 단위 테스트 — 합성 픽스처(원본 DB·엔진 불요).

봉인본 §3·§14 검증:
  - 전이 검출: 선두 flag=1(신규), 재진입(직전 이탈), 클램프(관측가능 ≥60).
  - 겹침 판정 window(±30 판정 / 0·60 민감도) + 상한 0.50 게이트.
  - 연도 세율 적용(2022=0.23%/2023=0.20%, reduce-to-v1 at 0.18%).
  - 3 서브모집단 판정: 표본 하한·FDR 분모 3 고정·구별/kill-4·sanity anchor.
  - 체크포인트 재개(완료 일 건너뜀).
"""
import os
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from alpha_lab.d9lab import judge_d9, overlap, run, transitions  # noqa: E402
from alpha_lab.d9lab.transitions import classify_transitions  # noqa: E402
from alpha_lab.stats_map import config_v2, costs_v2  # noqa: E402


# --------------------------------------------------------------------------
# 1. 전이 검출 — 선두 flag=1(신규) · 재진입 · 클램프(관측가능).
# --------------------------------------------------------------------------

def test_classify_leading_flag_is_new_onset():
    # 선두 flag=1 at pos0 = 0→1 전이로 취급(프로브 정의), 신규진입(직전 이력 없음).
    tr = classify_transitions(np.array([1, 1, 1, 0, 0]))
    assert tr["pos"].tolist() == [0]
    assert tr["is_reentry"].tolist() == [False]        # 신규.


def test_classify_reentry_after_exit():
    # 0→1, 이탈(1→0), 다시 0→1 → 두 번째 전이는 재진입.
    tr = classify_transitions(np.array([0, 1, 1, 0, 0, 1, 1]))
    assert tr["pos"].tolist() == [1, 5]
    assert tr["is_reentry"].tolist() == [False, True]  # 첫=신규, 둘째=재진입.


def test_classify_leading_then_reentry():
    # 선두 flag=1(신규) → 이탈 → 재진입.
    tr = classify_transitions(np.array([1, 0, 1]))
    assert tr["pos"].tolist() == [0, 2]
    assert tr["is_reentry"].tolist() == [False, True]


def test_classify_observable_clamp_at_60():
    # 행 위치 <60 = 미관측(관심종목N(60) 클램프-0), ≥60 = 관측가능.
    flags = np.zeros(130, dtype=int)
    flags[10] = 1          # pos10 전이(미관측).
    flags[70] = 1          # pos70 전이(관측가능) — 사이 0 유지.
    tr = classify_transitions(flags)
    assert tr["pos"].tolist() == [10, 70]
    assert tr["observable"].tolist() == [False, True]


def test_classify_no_transition_when_all_zero():
    tr = classify_transitions(np.zeros(50, dtype=int))
    assert tr["pos"].size == 0


def test_classify_empty():
    tr = classify_transitions(np.array([]))
    assert tr["pos"].size == 0 and tr["is_reentry"].size == 0


# --------------------------------------------------------------------------
# 2. 겹침 판정 window — ±30 판정 / 0·60 민감도 / 상한 0.50 게이트.
# --------------------------------------------------------------------------

def test_overlap_mask_one_day_window():
    tr_off = np.array([100, 200, 300])
    sg_off = np.array([105, 500])            # 100↔105 dist5, 200↔105 dist95, 300↔500 dist200.
    assert overlap._overlap_mask_one_day(tr_off, sg_off, 30).tolist() == [True, False, False]
    assert overlap._overlap_mask_one_day(tr_off, sg_off, 0).tolist() == [False, False, False]
    assert overlap._overlap_mask_one_day(tr_off, sg_off, 100).tolist() == [True, True, False]


def test_overlap_no_surge_is_zero():
    tr_off = np.array([10, 20])
    assert overlap._overlap_mask_one_day(tr_off, np.array([]), 30).tolist() == [False, False]


def test_overlap_rate_and_gate(tmp_path):
    # 전이 4건 중 1건만 서지와 ±30 겹침 → 0.25 ≤ 0.50 → gate_pass.
    tr_df = pd.DataFrame({
        "code": ["000001"] * 4,
        "day": [20220517] * 4,
        "off": [100, 400, 800, 1200],
        "observable": [True, True, True, True],
        "is_reentry": [False, True, False, True],
    })
    surge = pd.DataFrame({"code": ["000001"], "day": [20220517], "off": [110]})
    sp = tmp_path / "surge.parquet"
    surge.to_parquet(sp, index=False)
    res = overlap.compute_overlap(tr_df, sp)
    assert abs(res["primary_pooled_rate"] - 0.25) < 1e-9
    assert res["gate_pass"] is True
    # 민감도 window 전부 산출.
    assert set(res["per_window"].keys()) == {"0", "30", "60"}


def test_overlap_gate_fails_over_cap(tmp_path):
    # 전이 2건 모두 서지와 겹침 → 1.0 > 0.50 → gate_pass False(kill-3).
    tr_df = pd.DataFrame({
        "code": ["000001"] * 2, "day": [20220517] * 2, "off": [100, 200],
        "observable": [True, True], "is_reentry": [False, True],
    })
    surge = pd.DataFrame({"code": ["000001"] * 2, "day": [20220517] * 2, "off": [100, 200]})
    sp = tmp_path / "surge.parquet"
    surge.to_parquet(sp, index=False)
    res = overlap.compute_overlap(tr_df, sp)
    assert res["primary_pooled_rate"] == 1.0
    assert res["gate_pass"] is False


# --------------------------------------------------------------------------
# 3. 연도 세율 적용(§14-8 실현 규약) — 2022=0.23%/2023=0.20%, reduce-to-v1 at 0.18%.
# --------------------------------------------------------------------------

def test_year_tax_rates_sealed():
    assert config_v2.year_tax_rate(2022) == 0.0023
    assert config_v2.year_tax_rate(2023) == 0.0020


def test_year_tax_changes_realized_net():
    entry = np.array([1000.0]); exit_ = np.array([1010.0])
    net22 = costs_v2.net_from_quotes_year(entry, exit_, 2022)
    net23 = costs_v2.net_from_quotes_year(entry, exit_, 2023)
    # 2022 세율(0.23%)이 2023(0.20%)보다 높아 실현 net 이 더 낮다.
    assert net22[0] < net23[0]
    # 세율차 ≈ 0.03%p × 매도금액 반영(부호·규모 sanity).
    assert 0.0 < (net23[0] - net22[0]) < 0.01


def test_year_tax_reduces_to_v1_at_018():
    from alpha_lab.dataset import labels
    buy, sell = labels.adverse_fill(1000.0, 1010.0)
    v1 = labels.net_rate(buy, sell)
    v2 = costs_v2.net_rate_year(buy, sell, 0.0018)
    assert abs(v1 - v2) < 1e-12


# --------------------------------------------------------------------------
# 4. 서브모집단 판정 — 하한·FDR 분모 3 고정·구별/kill-4·sanity.
# --------------------------------------------------------------------------

def _synth_days(n, year):
    base = year * 10000 + 300  # YYYY0300 대역.
    return np.array([base + 1 + (i % 20) for i in range(n)], dtype=np.int64)


def _transition(n_new, n_re, net_new, net_re, spread=0.02, seed=0):
    rng = np.random.default_rng(seed)
    parts = []
    for n, net, is_re in ((n_new, net_new, False), (n_re, net_re, True)):
        half = n // 2
        day = np.concatenate([_synth_days(half, 2022), _synth_days(n - half, 2023)])
        year = day // 10000
        val = net + rng.normal(0, spread, n)
        parts.append((val, day, year, np.full(n, is_re, bool)))
    net_pp = np.concatenate([p[0] for p in parts])
    day = np.concatenate([p[1] for p in parts])
    year = np.concatenate([p[2] for p in parts])
    is_re = np.concatenate([p[3] for p in parts])
    return {"net_pp": net_pp, "day": day, "year": year, "is_reentry": is_re}


def _surge(n, net, spread=0.02, seed=1):
    rng = np.random.default_rng(seed)
    half = n // 2
    day = np.concatenate([_synth_days(half, 2022), _synth_days(n - half, 2023)])
    return {"net_pp": net + rng.normal(0, spread, n), "day": day, "year": day // 10000}


def test_fdr_denominator_fixed_three():
    tr = _transition(120, 180, 0.5, 0.5)
    sg = _surge(600, 0.0)
    res = judge_d9.judge_all_d9(tr, sg)
    assert res["fdr_denominator"] == 3
    assert res["subpops"] == ["new", "reentry", "pooled"]


def test_distinct_positive_when_transition_better():
    # 전이 net ≫ 서지 net, 표본 하한 충족 → 구별(양) 판정.
    tr = _transition(120, 180, 0.6, 0.6)
    sg = _surge(800, 0.0)
    res = judge_d9.judge_all_d9(tr, sg)
    assert res["n_distinct"] >= 1
    assert res["kill4_no_distinct"] is False
    for name in ("new", "reentry", "pooled"):
        r = res["per_subpop"][name]
        assert r["floor_pass"] is True
        assert r["delta_pp"] > judge_d9.EFFECT_FLOOR_PP


def test_kill4_and_sanity_when_equal():
    # 전이 ≈ 서지(둘 다 0) → |Δ|<0.02 → kill-4 + sanity anchor 발동.
    tr = _transition(120, 180, 0.0, 0.0)
    sg = _surge(800, 0.0)
    res = judge_d9.judge_all_d9(tr, sg)
    assert res["kill4_no_distinct"] is True
    assert res["n_distinct"] == 0
    assert res["sanity_anchor_tripped"] is True


def test_floor_fail_marks_inconclusive():
    # 재진입 표본 < 150 → 재진입 inconclusive(하한 미달), 판정 자격 없음.
    tr = _transition(120, 20, 0.6, 0.6)   # 재진입 20 < 150.
    sg = _surge(800, 0.0)
    res = judge_d9.judge_all_d9(tr, sg)
    assert res["per_subpop"]["reentry"]["floor_pass"] is False
    assert "reentry" in res["inconclusive_subpops"]


def test_halfyear_labels():
    days = np.array([20220315, 20220815, 20230601, 20231101], dtype=np.int64)
    hy = judge_d9._halfyear_labels(days)
    assert hy.tolist() == ["2022H1", "2022H2", "2023H1", "2023H2"]


# --------------------------------------------------------------------------
# 5. 체크포인트 재개 — 완료 일 건너뜀(재시작 가능).
# --------------------------------------------------------------------------

def _stub_day(_db_path, date, _sell_text, *, spot_pure=False):
    """DB 없이 최소 전이 온셋 레코드 + 메타(build_day_transitions 대체 스텁)."""
    rec = {k: np.array([]) for k in transitions.TRANSITION_COLUMNS}
    rec["code"] = np.array(["000001", "000001"], dtype="U6")
    rec["day"] = np.array([int(date), int(date)], dtype=np.int32)
    rec["off"] = np.array([100, 400], dtype=np.int16)
    rec["t0"] = np.array([int(date) * 1_000_000 + 90140,
                          int(date) * 1_000_000 + 90640], dtype=np.int64)
    rec["year"] = np.array([int(date) // 10000] * 2, dtype=np.int16)
    rec["row_pos"] = np.array([70, 120], dtype=np.int32)
    rec["is_reentry"] = np.array([False, True])
    rec["observable"] = np.array([True, True])
    rec["gt_member"] = np.array([True, True])
    for k in ("updown_q", "mktcap_b", "time_b"):
        rec[k] = np.array([0, 0], dtype=np.int8)
    rec["l3_net"] = np.array([0.001, -0.002], dtype=np.float64)
    rec["l3_labeled"] = np.array([True, True])
    rec["l3_clause"] = np.array([5, 0], dtype=np.int16)
    rec["l3_exit"] = np.array([0, 0], dtype=np.int64)
    rec["h300_net"] = np.array([0.001, np.nan], dtype=np.float64)
    rec["h300_valid"] = np.array([True, False])
    meta = {"n_codes": 1, "parity_n_rows": 200, "parity_n_match": 200,
            "n_onsets": 2, "n_observable": 2, "n_new": 1, "n_reentry": 1, "n_labeled": 2}
    return rec, meta


def test_run_r1_checkpoint_resume(tmp_path, monkeypatch):
    monkeypatch.setattr(transitions, "build_day_transitions", _stub_day)
    parts = tmp_path / "parts"
    days = [("20220517", tmp_path / "fake_20220517.db"),
            ("20220518", tmp_path / "fake_20220518.db")]

    r1 = run.run_r1(tmp_path, tmp_path, parts, "SELLTEXT", days=days)
    assert r1["days_done"] == 2
    assert (parts / "tr_20220517.parquet").exists()
    assert (parts / "meta_20220517.json").exists()

    # 재시작: 완료 2일은 재계산 없이 건너뛴다(스텁 호출 0회여야 함).
    calls = {"n": 0}

    def _counting_stub(*a, **k):
        calls["n"] += 1
        return _stub_day(*a, **k)

    monkeypatch.setattr(transitions, "build_day_transitions", _counting_stub)
    r2 = run.run_r1(tmp_path, tmp_path, parts, "SELLTEXT", days=days)
    assert r2["days_done"] == 2
    assert calls["n"] == 0                      # 재계산 없음(체크포인트 재개).


def test_consolidate_r1_parity_and_floors(tmp_path, monkeypatch):
    monkeypatch.setattr(transitions, "build_day_transitions", _stub_day)
    parts = tmp_path / "parts"
    days = [(f"2022051{i}", tmp_path / f"f{i}.db") for i in range(1, 8)]
    run.run_r1(tmp_path, tmp_path, parts, "SELLTEXT", days=days)
    cons = run.consolidate_r1(parts, tmp_path / "d9_transition_bank.parquet")
    assert cons["parity_match_pct"] == 1.0        # 200/200 × 7일.
    assert cons["parity_gate_pass"] is True
    assert cons["n_observable"] == 2 * len(days)
    assert set(cons["floors"].keys()) == {"new", "reentry", "pooled"}
