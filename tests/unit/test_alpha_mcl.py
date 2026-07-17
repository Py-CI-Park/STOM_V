"""alpha_lab.mcl 단위 테스트 — P3 MCL 스크리닝 코어 (합성 데이터 전용).

검증 대상(보수 설계 확정안 2026-07-05_p3_mcl_remediation_preregistration_draft.md):
- 봉인 예정 상수(§3·§4·§7)와 진입 컷오프의 datetime 재유도.
- (a) 재라벨: labels.py 재사용 파리티(l1_label/l2_triple_barrier 직접 호출과
  일치), MFE/MAE 고정창 300초 극값(오프셋 1 포함·301 제외), 정직 제외 사유,
  분 롤오버 시각 산술(ts_shift 재사용).
- (b) dedup: ledger_wiring identity/dedup_records 재사용, C1/C2/C4 감사
  카운트, first-wins 대표, 입력 불변, 발견창 필터 경계 포함.
- (c) 분위수 lift 스크리닝: stats_common 재사용 파리티(bh_fdr), 4분위 셀,
  단조·방향·p_trial, 연도 폴드 안정/불안정, MAE 억제형 플래그, 판정 불가
  (셀 미달·양성 0)·결측 카운트, 결정성, JSON 직렬화, 판정 3분지.
실 CSV·tick DB 접촉 없음 — 전부 합성.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

import numpy as np
import pytest

from alpha_lab.dataset.labels import (
    TIMEOUT_SEC,
    adverse_fill,
    l1_label,
    l2_triple_barrier,
    net_rate,
)
from alpha_lab.mcl import (
    C1_RETURN_TOL,
    DISCOVERY_END_DAY,
    ENTRY_HMS_MAX,
    ENTRY_HMS_MIN,
    FDR_Q,
    L1_HORIZONS,
    LABEL_TARGETS,
    MAE_TAIL_PCT,
    MAE_TARGET,
    MFE_TARGET,
    MIN_CELL_N,
    MIN_POOL_N,
    N_QUANTILES,
    PATH_WINDOW_SEC,
    TRIAL_INSUFFICIENT,
    TRIAL_NO_POSITIVES,
    TRIAL_OK,
    VALID_TRIAL_MIN_FRACTION,
    YEAR_AGREE_MIN_FRACTION,
    apply_fdr,
    build_targets,
    dedup_trades,
    filter_discovery,
    quantile_cells,
    relabel_trade,
    relabel_trades,
    screen_trials,
    screen_verdict,
)
from alpha_lab.stats_common import bh_fdr

DATE = "20240103"


def _t(hms: str) -> int:
    return int(DATE + hms)


def _rows(bids: dict, *, ask: float = 10000.0) -> dict:
    """{HHMMSS 문자열: 매수호가1} → tick 재조인 행 dict (진입 초에 ask 포함)."""
    return {
        _t(hms): {"매도호가1": ask, "매수호가1": bid} for hms, bid in bids.items()
    }


# TP 시나리오 — t0=09:10:00, 진입 (t0+1) ask 10000.
_TP_BIDS = {
    "091001": 9990.0,    # 오프셋 1 (진입 초 — 경로 포함)
    "091030": 10600.0,   # 오프셋 30 — TP first-touch·MFE 극값
    "091100": 10050.0,   # 오프셋 60 — L1_60 청산
    "091200": 9500.0,    # 오프셋 120 — MAE 극값 (TP 이후에도 고정창 관측)
    "091300": 10300.0,   # 오프셋 180 — L1_180 청산
    "091500": 10100.0,   # 오프셋 300 — L1_300 청산 (창 경계 포함)
    "091501": 99999.0,   # 오프셋 301 — 창 밖 (극값에 영향 금지)
}
_T0 = _t("091000")


def _net(entry_ask: float, bid: float) -> float:
    return net_rate(*adverse_fill(entry_ask, bid))


# ------------------------------------------------------------- 봉인 상수 --


def test_sealed_constants():
    assert LABEL_TARGETS == ("L1_60", "L1_180", "L1_300", "L2", "MFE_300", "MAE_300")
    assert L1_HORIZONS == (60, 180, 300)
    assert PATH_WINDOW_SEC == TIMEOUT_SEC == 300
    assert (MFE_TARGET, MAE_TARGET) == ("MFE_300", "MAE_300")
    assert MIN_POOL_N == 2000 and MIN_CELL_N == 500
    assert FDR_Q == 0.05 and N_QUANTILES == 4
    assert DISCOVERY_END_DAY == "20241231"
    assert MAE_TAIL_PCT == 5.0
    assert C1_RETURN_TOL == 1e-9
    assert YEAR_AGREE_MIN_FRACTION == pytest.approx(2.0 / 3.0)
    assert VALID_TRIAL_MIN_FRACTION == 0.5


def test_entry_cutoff_rederived_with_datetime():
    """컷오프 = 그리드 끝 09:30:00 − 고정창 300초 (§3.2 절단 방지 규칙)."""
    end = datetime.strptime("093000", "%H%M%S")
    cutoff = end - timedelta(seconds=PATH_WINDOW_SEC)
    assert ENTRY_HMS_MAX == int(cutoff.strftime("%H%M%S")) == 92500
    assert ENTRY_HMS_MIN == 90001  # tick DB 커버리지 시작 초.


# ------------------------------------------------------ (a) 재라벨 파리티 --


def test_relabel_tp_scenario_matches_sealed_label_functions():
    labels, reason = relabel_trade(_rows(_TP_BIDS), _T0)
    assert reason == "ok"
    assert set(labels) == set(LABEL_TARGETS)
    # L1 파리티 — labels.l1_label 직접 호출과 동일(재사용 봉인).
    assert labels["L1_60"] == float(l1_label(10000.0, 10050.0))
    assert labels["L1_180"] == float(l1_label(10000.0, 10300.0))
    assert labels["L1_300"] == float(l1_label(10000.0, 10100.0))
    assert (labels["L1_60"], labels["L1_180"], labels["L1_300"]) == (0.0, 1.0, 0.0)
    # L2 파리티 — 동일 경로로 l2_triple_barrier 직접 호출과 동일.
    path = [(1, 9990.0), (30, 10600.0), (60, 10050.0), (120, 9500.0),
            (180, 10300.0), (300, 10100.0)]
    assert labels["L2"] == float(l2_triple_barrier(10000.0, path)) == 1.0


def test_relabel_mfe_mae_fixed_window_extremes():
    labels, _ = relabel_trade(_rows(_TP_BIDS), _T0)
    rates = [_net(10000.0, bid) for bid in
             (9990.0, 10600.0, 10050.0, 9500.0, 10300.0, 10100.0)]
    assert labels[MFE_TARGET] == pytest.approx(max(rates))  # bid 10600 극값.
    assert labels[MAE_TARGET] == pytest.approx(min(rates))  # bid 9500 극값.
    # 창 밖(오프셋 301, bid 99999)이 극값에 반영되지 않았음을 확인.
    assert labels[MFE_TARGET] < _net(10000.0, 99999.0)
    # TP first-touch(오프셋 30) 이후의 오프셋 120 저점도 고정창 MAE 에 반영됨.
    assert labels[MAE_TARGET] == pytest.approx(_net(10000.0, 9500.0))


def test_relabel_sl_and_timeout_scenarios():
    sl_bids = dict(_TP_BIDS, **{"091030": 9700.0})  # 오프셋 30 급락 → SL 선터치.
    labels_sl, _ = relabel_trade(_rows(sl_bids), _T0)
    assert labels_sl["L2"] == -1.0
    flat_bids = {k: 10050.0 for k in _TP_BIDS}      # 배리어 미터치 → timeout.
    labels_to, _ = relabel_trade(_rows(flat_bids), _T0)
    assert labels_to["L2"] == 0.0


def test_relabel_honest_exclusion_reasons():
    rows = _rows(_TP_BIDS)
    assert relabel_trade(None, _T0) == (None, "rows_missing")
    assert relabel_trade(rows, _t("092501")) == (None, "time_ineligible")
    assert relabel_trade(rows, _t("090000")) == (None, "time_ineligible")
    # 경계 092500/090001 은 시각 게이트 통과(행 부재로 entry_missing).
    assert relabel_trade({}, _t("092500")) == (None, "entry_missing")
    assert relabel_trade({}, _t("090001")) == (None, "entry_missing")
    bad_ask = {_t("091001"): {"매도호가1": 0.0, "매수호가1": 9990.0}}
    assert relabel_trade(bad_ask, _T0) == (None, "entry_ask_nonpositive")
    no_h180 = {ts: row for ts, row in rows.items() if ts != _t("091300")}
    assert relabel_trade(no_h180, _T0) == (None, "horizon_missing")


def test_relabel_minute_rollover_uses_ts_shift():
    t0 = _t("090959")  # +1초 = 09:10:00 (분 롤오버).
    bids = {"091000": 9990.0, "091059": 10300.0, "091259": 10300.0,
            "091459": 10300.0}
    labels, reason = relabel_trade(_rows(bids), t0)
    assert reason == "ok"
    assert labels["L1_60"] == float(l1_label(10000.0, 10300.0)) == 1.0


def test_relabel_horizons_validation():
    with pytest.raises(ValueError):
        relabel_trade(_rows(_TP_BIDS), _T0, horizons=(60, PATH_WINDOW_SEC + 1))
    with pytest.raises(ValueError):
        relabel_trade(_rows(_TP_BIDS), _T0, horizons=())


def _ledger_rec(strategy="champ", code="005930", day=DATE, hms="091000",
                ret=1.0, sell=20240103091500.0, file=None):
    rec = {"전략명": strategy, "종목코드": code, "진입일자": day,
           "진입시각": hms, "수익률": ret}
    if sell is not None:
        rec["매도시간"] = sell
    if file is not None:
        rec["source_file"] = file
    return rec


def test_relabel_trades_batch_audit_and_sample_fields():
    records = [_ledger_rec(), _ledger_rec(code="000660")]  # 두 번째는 재조인 불가.
    samples, counts = relabel_trades(
        records, {(DATE, "005930"): _rows(_TP_BIDS)}
    )
    assert counts["input"] == 2 and counts["ok"] == 1
    assert counts["rows_missing"] == 1
    assert len(samples) == 1
    sample = samples[0]
    assert (sample["strategy"], sample["code"]) == ("champ", "005930")
    assert (sample["day"], sample["t0"]) == (int(DATE), _T0)
    assert set(LABEL_TARGETS) <= set(sample)


# ------------------------------------------- (b) 발견창 필터 + dedup 감사 --


def test_filter_discovery_boundary_inclusive():
    records = [_ledger_rec(day="20241231"), _ledger_rec(day="20250101")]
    kept, dropped = filter_discovery(records)
    assert [r["진입일자"] for r in kept] == ["20241231"] and dropped == 1
    with pytest.raises(ValueError):
        filter_discovery(records, end_day="2024-12-31")


def test_dedup_c1_exact_duplicate_first_wins():
    a, b = _ledger_rec(file="run_a.csv"), _ledger_rec(file="run_b.csv")
    a["marker"] = "first"
    unique, audit = dedup_trades([a, b])
    assert len(unique) == 1 and unique[0]["marker"] == "first"
    assert audit["c1_rows_dropped"] == 1 and audit["c2_rows_dropped"] == 0
    assert audit["c4_rows_dropped"] == 0
    assert audit["input_rows"] == audit["unique_rows"] + 1


def test_dedup_c2_when_result_differs_or_sell_time_missing():
    _, audit = dedup_trades([_ledger_rec(), _ledger_rec(ret=2.0)])
    assert (audit["c1_rows_dropped"], audit["c2_rows_dropped"]) == (0, 1)
    # 매도시간 결측 → 완전 중복 확인 불가 → C2(보수).
    _, audit2 = dedup_trades([_ledger_rec(sell=None), _ledger_rec(sell=None)])
    assert (audit2["c1_rows_dropped"], audit2["c2_rows_dropped"]) == (0, 1)


def test_dedup_c4_same_file_tag_poisons_identity():
    records = [
        _ledger_rec(file="f1.csv"), _ledger_rec(file="f1.csv"),  # C4 이상.
        _ledger_rec(code="000660", file="f1.csv"),               # 무관 identity.
    ]
    unique, audit = dedup_trades(records)
    assert audit["c4_identities"] == 1 and audit["c4_rows_dropped"] == 2
    assert [r["종목코드"] for r in unique] == ["000660"]
    # 태그 없는 멤버가 섞여도 identity 전체 제외(보수).
    _, audit2 = dedup_trades(
        [_ledger_rec(file="f1.csv"), _ledger_rec(file="f1.csv"), _ledger_rec()]
    )
    assert audit2["c4_rows_dropped"] == 3 and audit2["unique_rows"] == 0


def test_dedup_untagged_records_never_c4():
    unique, audit = dedup_trades([_ledger_rec(), _ledger_rec()])
    assert audit["c4_identities"] == 0 and audit["c1_rows_dropped"] == 1
    assert len(unique) == 1 and audit["file_tagged_rows"] == 0


def test_dedup_audit_identity_and_input_immutability():
    records = [
        _ledger_rec(file="f1.csv"), _ledger_rec(file="f1.csv"),
        _ledger_rec(code="000660"), _ledger_rec(code="000660", ret=9.9),
        _ledger_rec(code="035420"),
    ]
    snapshot = [dict(r) for r in records]
    unique, audit = dedup_trades(records)
    assert records == snapshot  # 입력 불변.
    total = (audit["unique_rows"] + audit["c1_rows_dropped"]
             + audit["c2_rows_dropped"] + audit["c4_rows_dropped"])
    assert audit["input_rows"] == total == 5
    assert audit["identity_groups"] == 3
    assert {r["종목코드"] for r in unique} == {"000660", "035420"}


# ----------------------------------------------------- (c) 표적 조작화 --


def _label_sample(l60=0.0, l180=0.0, l300=0.0, l2=0.0, mfe=0.0, mae=-0.01):
    return {"L1_60": l60, "L1_180": l180, "L1_300": l300, "L2": l2,
            "MFE_300": mfe, "MAE_300": mae}


def test_build_targets_l1_passthrough_and_l2_tp_indicator():
    samples = [_label_sample(l60=1.0, l2=1.0), _label_sample(l2=0.0),
               _label_sample(l2=-1.0)]
    targets, _ = build_targets(samples)
    assert targets["L1_60"].tolist() == [1.0, 0.0, 0.0]
    assert targets["L2"].tolist() == [1.0, 0.0, 0.0]  # -1(SL)은 양성 아님.


def test_build_targets_mfe_threshold_and_mae_tail():
    mae_values = [-(i + 1) / 100.0 for i in range(100)]
    samples = [_label_sample(mfe=0.009, mae=mae_values[i] if i < 100 else -0.01)
               for i in range(100)]
    samples[1]["MFE_300"] = 0.01   # 임계 경계(포함).
    samples[2]["MFE_300"] = 0.05
    targets, thresholds = build_targets(samples)
    assert targets[MFE_TARGET][:3].tolist() == [0.0, 1.0, 1.0]
    assert thresholds[MFE_TARGET] == 0.01  # 기본 = L1_NET_THRESHOLD.
    expected_tail = float(np.quantile(np.asarray(mae_values), MAE_TAIL_PCT / 100.0))
    assert thresholds[MAE_TARGET] == pytest.approx(expected_tail)
    assert targets[MAE_TARGET].sum() == float(
        (np.asarray(mae_values) <= expected_tail).sum()
    )
    # 임계 커스텀은 additive 로만.
    targets2, thresholds2 = build_targets(samples, mfe_threshold=0.02)
    assert thresholds2[MFE_TARGET] == 0.02
    assert targets2[MFE_TARGET][:3].tolist() == [0.0, 0.0, 1.0]


def test_build_targets_validation():
    with pytest.raises(ValueError):
        build_targets([])
    broken = [_label_sample()]
    del broken[0]["L2"]
    with pytest.raises(ValueError):
        build_targets(broken)
    with pytest.raises(ValueError):
        build_targets([_label_sample()], mae_tail_pct=0.0)


# -------------------------------------------------- (c) 분위수 셀 규약 --


def test_quantile_cells_equal_split_and_upper_bin_boundary():
    values = np.arange(100, dtype=float)
    cells, edges = quantile_cells(values)
    assert np.bincount(cells, minlength=4).tolist() == [25, 25, 25, 25]
    assert edges.tolist() == np.quantile(values, [0.25, 0.5, 0.75]).tolist()
    # 경계값 == 상위 빈 (bisect_right 규약 — events.stratify 정합).
    cells2, edges2 = quantile_cells([1.0, 2.0, 2.0, 3.0], n_quantiles=2)
    assert edges2.tolist() == [2.0]
    assert cells2.tolist() == [0, 1, 1, 1]


def test_quantile_cells_validation():
    with pytest.raises(ValueError):
        quantile_cells([])
    with pytest.raises(ValueError):
        quantile_cells([1.0, float("nan")])
    with pytest.raises(ValueError):
        quantile_cells([1.0, 2.0], n_quantiles=1)


# ----------------------------------------------- (c) 시행 스크리닝 본체 --


def _make_pool(rates, *, n_per_cell=600, seed=7, years=(2022, 2023, 2024)):
    """셀 k 양성률 rates[k] 인 합성 풀 — (x, y, days). 일자는 연도×20일."""
    rng = np.random.default_rng(seed)
    xs, ys = [], []
    for k, rate in enumerate(rates):
        xs.append(k + rng.random(n_per_cell))
        ys.append((rng.random(n_per_cell) < rate).astype(np.float64))
    x, y = np.concatenate(xs), np.concatenate(ys)
    day_pool = np.asarray([yr * 10000 + 101 + d for yr in years for d in range(20)])
    days = rng.choice(day_pool, size=x.size)
    perm = rng.permutation(x.size)
    return x[perm], y[perm], days[perm]


def test_screen_trials_detects_monotone_signal_and_noise_fails():
    x, y, days = _make_pool((0.05, 0.10, 0.20, 0.40))
    noise = np.random.default_rng(11).random(x.size)
    rows = screen_trials({"F_sig": x, "F_noise": noise}, {"L1_60": y}, days,
                         n_boot=200, seed=3)
    assert [(r["feature"], r["target"]) for r in rows] == [
        ("F_sig", "L1_60"), ("F_noise", "L1_60")
    ]
    sig = rows[0]
    assert sig["verdict"] == TRIAL_OK
    assert sig["cell_n"] == [600, 600, 600, 600]
    assert sig["monotone"] is True and sig["direction"] == "up"
    assert (sig["extreme_cell"], sig["opposite_cell"]) == (3, 0)
    assert sig["p_trial"] <= 0.05
    assert len(sig["cells"]) == 4
    assert set(sig["cells"][0]) == {"cell", "n", "lift", "ci_low", "ci_high", "p"}
    assert sig["cells"][3]["lift"] > 1.5 > sig["cells"][0]["lift"]
    assert sig["year_stable"] is True
    assert set(sig["year_lifts"]) == {"2022", "2023", "2024"}
    scored = apply_fdr(rows)
    assert scored[0]["survivor"] is True
    assert scored[1]["survivor"] is False  # 노이즈는 생존 불가.


def test_screen_trials_mae_suppressor_flag_only_for_mae_target():
    x, y, days = _make_pool((0.10, 0.06, 0.03, 0.01), seed=5)
    row = screen_trials({"F": x}, {MAE_TARGET: y}, days, n_boot=200, seed=5)[0]
    assert row["direction"] == "down"
    assert (row["extreme_cell"], row["opposite_cell"]) == (0, 3)
    assert row["monotone"] is True
    assert row["cells"][3]["ci_high"] < 1.0  # 심꼬리 억제 CI 분리.
    assert row["mae_suppressor"] is True
    # 같은 데이터라도 표적명이 MAE_300 이 아니면 억제형 플래그 없음.
    row2 = screen_trials({"F": x}, {"L1_60": y}, days, n_boot=200, seed=5)[0]
    assert row2["mae_suppressor"] is False


def test_screen_trials_year_fold_instability():
    x1, y1, d1 = _make_pool((0.05, 0.10, 0.20, 0.40), n_per_cell=400,
                            seed=13, years=(2023,))
    x2, y2, d2 = _make_pool((0.40, 0.20, 0.10, 0.05), n_per_cell=200,
                            seed=17, years=(2024,))
    x = np.concatenate([x1, x2])
    y = np.concatenate([y1, y2])
    days = np.concatenate([d1, d2])
    row = screen_trials({"F": x}, {"L1_60": y}, days, n_boot=200, seed=9)[0]
    assert row["verdict"] == TRIAL_OK and row["direction"] == "up"
    assert row["year_stable"] is False  # 부호 일치 1/2 < 2/3.
    assert apply_fdr([row])[0]["survivor"] is False


def test_screen_trials_insufficient_cell_and_missing_counted():
    x, y, days = _make_pool((0.1, 0.1, 0.1, 0.1), n_per_cell=100)
    row = screen_trials({"F": x}, {"L1_60": y}, days, n_boot=50, seed=1)[0]
    assert row["verdict"] == TRIAL_INSUFFICIENT
    assert row["p_trial"] == 1.0 and row["cells"] == []
    assert row["monotone"] is False and row["year_stable"] is False
    # 결측(NaN)은 그 시행에서만 제외·카운트.
    x2, y2, days2 = _make_pool((0.1, 0.1, 0.1, 0.1))
    x2_missing = x2.copy()
    x2_missing[:100] = np.nan
    row2 = screen_trials({"F": x2_missing}, {"L1_60": y2}, days2,
                         n_boot=50, seed=1)[0]
    assert row2["n_missing"] == 100 and row2["n"] == x2.size - 100


def test_screen_trials_no_positives_verdict():
    x, _, days = _make_pool((0.5, 0.5, 0.5, 0.5))
    row = screen_trials({"F": x}, {"L1_60": np.zeros(x.size)}, days,
                        n_boot=50, seed=1)[0]
    assert row["verdict"] == TRIAL_NO_POSITIVES and row["p_trial"] == 1.0


def test_screen_trials_validation_errors():
    x, y, days = _make_pool((0.1, 0.2, 0.3, 0.4), n_per_cell=10)
    with pytest.raises(ValueError):
        screen_trials({"F": x}, {"L1_60": y + 1.0}, days)  # 0/1 아님.
    y_nan = y.copy()
    y_nan[0] = np.nan
    with pytest.raises(ValueError):
        screen_trials({"F": x}, {"L1_60": y_nan}, days)
    with pytest.raises(ValueError):
        screen_trials({"F": x[:-1]}, {"L1_60": y}, days)
    with pytest.raises(ValueError):
        screen_trials({"F": x}, {"L1_60": y}, days.reshape(2, -1))


def test_screen_trials_deterministic_and_json_serializable():
    x, y, days = _make_pool((0.05, 0.1, 0.2, 0.4))
    kwargs = dict(n_boot=100, seed=42)
    rows_a = screen_trials({"F": x}, {"L1_60": y}, days, **kwargs)
    rows_b = screen_trials({"F": x}, {"L1_60": y}, days, **kwargs)
    assert rows_a == rows_b
    json.dumps(apply_fdr(rows_a))  # numpy 타입 잔존 시 TypeError.


# --------------------------------------------------- FDR·판정 3분지 --


def _fake_trial(p, *, verdict=TRIAL_OK, monotone=True, year_stable=True,
                mae_suppressor=False):
    return {"p_trial": p, "verdict": verdict, "monotone": monotone,
            "year_stable": year_stable, "mae_suppressor": mae_suppressor}


def test_apply_fdr_parity_with_stats_common_and_gate_conjunction():
    ps = [0.001, 0.002, 0.4, 0.9, 1.0]
    rows = [_fake_trial(p) for p in ps]
    rows[1]["monotone"] = False  # FDR 생존해도 단조 실패면 비생존.
    scored = apply_fdr(rows)
    expected = bh_fdr(ps, q=FDR_Q)
    assert [r["fdr_pass"] for r in scored] == [bool(v) for v in expected]
    assert scored[0]["survivor"] is True
    assert scored[1]["survivor"] is False
    assert apply_fdr([]) == []
    # 판정 불가 시행(p=1.0)도 모수에 잔류하며 생존 불가.
    scored2 = apply_fdr([_fake_trial(1.0, verdict=TRIAL_INSUFFICIENT,
                                     monotone=False, year_stable=False)])
    assert scored2[0]["survivor"] is False


def _scored(survivor, *, verdict=TRIAL_OK, mae_suppressor=False):
    return {"verdict": verdict, "survivor": survivor,
            "mae_suppressor": mae_suppressor}


def test_screen_verdict_three_way_plus_below_threshold():
    ok2_with_supp = [_scored(True, mae_suppressor=True), _scored(True),
                     _scored(False), _scored(False)]
    assert screen_verdict(ok2_with_supp, pool_n=2500)["verdict"] == "success"
    assert screen_verdict([_scored(False)] * 4, pool_n=2500)["verdict"] == "abandon"
    assert screen_verdict([_scored(True), _scored(False)],
                          pool_n=2500)["verdict"] == "below_threshold"
    no_supp = [_scored(True), _scored(True)]
    assert screen_verdict(no_supp, pool_n=2500)["verdict"] == "below_threshold"


def test_screen_verdict_inconclusive_gates():
    rows = [_scored(True, mae_suppressor=True), _scored(True)]
    assert screen_verdict(rows, pool_n=MIN_POOL_N - 1)["verdict"] == "inconclusive"
    assert screen_verdict([], pool_n=99999)["verdict"] == "inconclusive"
    # 유효 시행 과반 탈락(1/4 < 1/2) → 판정 불가.
    mostly_invalid = [_scored(True, mae_suppressor=True)] + [
        _scored(False, verdict=TRIAL_INSUFFICIENT)] * 3
    assert screen_verdict(mostly_invalid, pool_n=2500)["verdict"] == "inconclusive"
    # 정확히 절반 유효는 과반 탈락이 아니다.
    half_valid = [_scored(True, mae_suppressor=True), _scored(True),
                  _scored(False, verdict=TRIAL_INSUFFICIENT),
                  _scored(False, verdict=TRIAL_INSUFFICIENT)]
    summary = screen_verdict(half_valid, pool_n=2500)
    assert summary["verdict"] == "success"
    assert summary["survivors"] == 2 and summary["mae_suppressors"] == 1


def test_screen_verdict_requires_apply_fdr():
    with pytest.raises(ValueError):
        screen_verdict([{"verdict": TRIAL_OK}], pool_n=2500)
