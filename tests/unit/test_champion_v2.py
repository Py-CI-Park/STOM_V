"""alpha_lab.stats_map.champion_v2 단위 테스트 — V2-C family vote 게이트.

실DB 불필요(합성 CSV + 합성 온셋 표본). 실행:
    python -m pytest tests/unit/test_champion_v2.py -q

검증 축:
- family_trade_cells: v1 사상 재사용 + v2 등락율 경계 재버킷 + 발견창/창내 필터.
- _improvement_ci: 알려진 표본에서 개선폭·CI 부호.
- _verdict/_ladder: pass/weak/fail·해석 사다리.
- occupied_judgment/run_family_gate/run_gate_v2c: 점유 판정·대조군·민감도.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_lab.stats_map import champion_v2


def _write_csv(path: Path, rows):
    """합성 챔피언 per-trade CSV(매수시간·B_등락율·B_시가총액)."""
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8")
    return path


# 매수시간 20220401090305 → fill_off 185, t0_off 184, time_b 0.
# B_등락율 5.0 → updown_q_v2 2 (searchsorted[1.59,3.56,6.88]). 시총 500 → mc 0.
_TRADE = {"매수시간": 20220401090305, "B_등락율": 5.0, "B_시가총액": 500.0}


class TestFamilyTradeCells:
    def test_v2_bucket_and_window(self, tmp_path):
        rows = [
            dict(_TRADE),                                    # 셀 (0,2,0).
            {"매수시간": 20220401091500, "B_등락율": 2.0,     # t0=fill-1=091459 → tb 2.
             "B_시가총액": 4000.0},                          # uq 1, mc 2 → (2,1,2).
            {"매수시간": 20240102090305, "B_등락율": 5.0,     # 발견창 밖(2024) → 제외.
             "B_시가총액": 500.0},
        ]
        cells = champion_v2.family_trade_cells([_write_csv(tmp_path / "c.csv", rows)])
        assert cells["n_trades"] == 2  # 2024 제외.
        assert cells["cells_2axis"] == {(0, 2): 1, (2, 1): 1}
        assert cells["cells_3axis"] == {(0, 2, 0): 1, (2, 1, 2): 1}
        assert cells["coverage"]["after_discovery"] == 1

    def test_family_union_counts(self, tmp_path):
        a = _write_csv(tmp_path / "a.csv", [dict(_TRADE), dict(_TRADE)])
        b = _write_csv(tmp_path / "b.csv", [dict(_TRADE)])
        cells = champion_v2.family_trade_cells([a, b])
        assert cells["n_trades"] == 3
        assert cells["cells_2axis"] == {(0, 2): 3}


def _mk_sample(n_days=12, per_day=100, occ_frac=0.2, occ_net=0.02,
               other_net=-0.01, occ_cell=(0, 2)):
    """합성 온셋 표본 — occ_cell 셀에 occ_net, 나머지 other_net."""
    days, tb, uq, mc, l3 = [], [], [], [], []
    rngdays = [20220401 + d for d in range(n_days)]
    for day in rngdays:
        for i in range(per_day):
            days.append(day)
            if i < int(per_day * occ_frac):
                tb.append(occ_cell[0]); uq.append(occ_cell[1]); mc.append(0)
                l3.append(occ_net)
            else:
                tb.append(1); uq.append(1); mc.append(1)
                l3.append(other_net)
    n = len(days)
    arr = lambda x, dt: np.array(x, dtype=dt)
    return {
        "day": arr(days, np.int32), "time_b": arr(tb, np.int8),
        "updown_q": arr(uq, np.int8), "mktcap_b": arr(mc, np.int8),
        "l3_net_pure": arr(l3, np.float64), "l3_labeled_pure": np.ones(n, bool),
        "h300_net": arr(l3, np.float64), "h300_valid": np.ones(n, bool),
    }


class TestImprovementCI:
    def test_positive_improvement_ci_above_zero(self):
        s = _mk_sample()
        occ = (s["time_b"] == 0) & (s["updown_q"] == 2)
        allm = s["l3_labeled_pure"].astype(bool)
        stat = champion_v2._improvement_ci(
            s["day"], s["l3_net_pure"], occ, allm, seed=1)
        # occ_mean=0.02, overall=(0.2*0.02+0.8*-0.01)=-0.004 → improve=+0.024.
        assert stat["occ_mean"] == pytest.approx(0.02)
        assert stat["improvement"] == pytest.approx(0.024, abs=1e-9)
        assert stat["ci_low"] > 0.0

    def test_negative_improvement_ci_below_zero(self):
        s = _mk_sample(occ_net=-0.03)
        occ = (s["time_b"] == 0) & (s["updown_q"] == 2)
        stat = champion_v2._improvement_ci(
            s["day"], s["l3_net_pure"], occ, s["l3_labeled_pure"].astype(bool),
            seed=1)
        assert stat["improvement"] < 0.0
        assert stat["ci_high"] < 0.0


class TestVerdict:
    def test_thresholds(self):
        assert champion_v2._verdict(0.0012, 0.0001) == "pass"
        assert champion_v2._verdict(0.0007, 0.0001) == "weak"
        assert champion_v2._verdict(0.0012, -0.0001) == "fail"   # CI 하한 음.
        assert champion_v2._verdict(0.0003, 0.0001) == "fail"    # 개선폭 미달.
        assert champion_v2._verdict(None, None) == "fail"


class TestLadder:
    def test_positions(self):
        assert champion_v2._ladder({"RR8": "pass", "GPTAUTH": "fail"}
                                   )["position"] == "positive_control"
        assert champion_v2._ladder({"RR8": "pass", "GPTAUTH": "pass"}
                                   )["position"] == "limited_generalization"
        assert champion_v2._ladder({"RR8": "fail", "GPTAUTH": "fail"}
                                   )["position"] == "kill"
        assert champion_v2._ladder({"RR8": "weak", "GPTAUTH": "fail"}
                                   )["position"] == "kill"


class TestGateEndToEnd:
    def test_run_gate_pass_and_control(self, tmp_path):
        s = _mk_sample()
        rr8 = _write_csv(tmp_path / "rr8.csv", [dict(_TRADE)])          # 셀 (0,2).
        gpt = _write_csv(tmp_path / "gpt.csv", [
            {"매수시간": 20220401091500, "B_등락율": 2.0, "B_시가총액": 4000.0}])
        res = champion_v2.run_gate_v2c(
            s, {"RR8": [rr8], "GPTAUTH": [gpt]}, {"RR8_12": rr8})
        # RR8 점유 셀(0,2)=고수익 → pass. GPTAUTH 점유 셀(3,1)=미존재 온셋 → fail.
        assert res["verdicts"]["RR8"] == "pass"
        assert res["interpretation_ladder"]["position"] == "positive_control"
        # 대조군 h300 병기 존재.
        assert "h300_time_ud" in res["families"]["RR8"]
        assert res["families"]["RR8"]["verdict_h300_control"] in {"pass", "weak", "fail"}
        # RR8 내부 민감도 병기.
        assert "RR8_12" in res["rr8_internal_sensitivity_l3_time_ud"]
