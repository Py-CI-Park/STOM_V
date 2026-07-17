"""alpha_lab.exitlab_r forensics·triage 단위 테스트 — 합성 레코드(실DB 불필요).

실행: python -m pytest tests/unit/test_exitlab_r_analysis.py -q

검증 축:
- lower_bound_table: 하드 백스톱 자격(Family A/B, 연도별) 판정.
- family_b_population: §5 t=T 상태 정의(held∧best_T<x∧sp_T<y) 선택.
- help_hurt_map / kill1_verdict: 절단이득 상태 분리·연도 반전(레짐-취약).
- run_r3_candidate: Δnet·연도부호·가문 일관성·겹침률·MDE.
"""
from __future__ import annotations

from alpha_lab.exitlab_r.forensics import (
    family_a_population, family_b_population, help_hurt_map, kill1_verdict,
    lower_bound_table,
)
from alpha_lab.exitlab_r.pipeline import CANDIDATES
from alpha_lab.exitlab_r.patch_exit import Patch
from alpha_lab.exitlab_r.triage import _mde_from_ci, run_r3_candidate


def _rec(champ, day, hms, *, inc_pct, inc_cond, per_T, cand, inc_won=0):
    year = int(day) // 10000
    return {
        "champ": champ, "code6": "000001", "day": int(day), "hms": hms,
        "buy_time": int(f"{day}{hms}"), "year": year, "qty": 100,
        "buy_price": 10000.0, "dedup_key": (str(day), "000001", hms),
        "status": "ok", "inc_time": int(f"{day}{hms}") + 100, "inc_pct": inc_pct,
        "inc_won": inc_won, "inc_cond": inc_cond, "inc_hold": 300, "inc_best": 0.0,
        "led_pct": inc_pct, "per_T": per_T, "cand": cand,
    }


def _cell(held, best_T, sp_T, cut_pct, cut_won=0.0):
    return {"held": held, "best_T": best_T, "sp_T": sp_T, "cut_pct": cut_pct,
            "cut_won": cut_won, "cut_time": 0.0}


def _b_cand(label, *, affected, dnet, b_fired, cond=100, won=0):
    return {label: {"time": 1, "price": 9900.0, "pct": 0.0, "won": won, "cond": cond,
                    "hold": 130, "affected": affected, "dnet_pp": dnet, "dwon": won,
                    "b_fired": b_fired}}


class TestLowerBound:
    def test_family_b_backstop(self):
        # 저활력 t=T 200건(연 100씩) — B 백스톱(>=150 ∧ 연>=40) 통과.
        recs = []
        for i in range(200):
            day = 20220401 if i < 100 else 20230401
            recs.append(_rec("RR8_12", day, f"09{i%60:02d}00",
                             inc_pct=-1.0, inc_cond=3,
                             per_T={120: _cell(1, 0.5, -0.5, -0.8), 180: _cell(1, 0.5, -0.5, -0.9),
                                    240: _cell(1, 0.5, -0.5, -1.0)},
                             cand={p.label: _b_cand(p.label, affected=1, dnet=0.2, b_fired=1)[p.label]
                                   for p in CANDIDATES}))
        rows = lower_bound_table(recs, [c for c in CANDIDATES if c.label == "B2"])
        assert rows[0]["qualifies"] is True
        assert rows[0]["n_pop"] == 200

    def test_family_b_inconclusive_small(self):
        recs = [_rec("RR8_12", 20220401, f"09{i:02d}00", inc_pct=-1.0, inc_cond=3,
                     per_T={120: _cell(1, 0.5, -0.5, -0.8), 180: _cell(1, 0.5, -0.5, -0.9),
                            240: _cell(1, 0.5, -0.5, -1.0)},
                     cand={p.label: _b_cand(p.label, affected=1, dnet=0.2, b_fired=1)[p.label]
                           for p in CANDIDATES})
                for i in range(30)]
        rows = lower_bound_table(recs, [c for c in CANDIDATES if c.label == "B1"])
        assert rows[0]["qualifies"] is False
        assert "inconclusive" in rows[0]["verdict"]

    def test_family_a_population_is_clause5(self):
        recs = [_rec("RR8_12", 20220401, "090100", inc_pct=2.0, inc_cond=5,
                     per_T={120: _cell(1, 4.0, 2.0, 3.0), 180: _cell(1, 4.0, 2.0, 3.0),
                            240: _cell(1, 4.0, 2.0, 3.0)},
                     cand={p.label: _b_cand(p.label, affected=0, dnet=0.0, b_fired=0)[p.label]
                           for p in CANDIDATES})]
        assert len(family_a_population(recs)) == 1


class TestFamilyBPopulation:
    def test_selects_low_state(self):
        recs = [
            _rec("RR8_12", 20220401, "090100", inc_pct=-1.0, inc_cond=3,
                 per_T={120: _cell(1, 0.5, -0.5, -0.8), 180: _cell(0, 0, 0, float("nan")),
                        240: _cell(0, 0, 0, float("nan"))}, cand={}),
            _rec("RR8_12", 20220401, "090200", inc_pct=3.0, inc_cond=5,   # 승자 — best_T 큼.
                 per_T={120: _cell(1, 4.0, 3.0, 3.5), 180: _cell(1, 4.0, 3.0, 3.5),
                        240: _cell(1, 4.0, 3.0, 3.5)}, cand={}),
        ]
        pop = family_b_population(recs, 120, 1.0, 0.0)
        assert len(pop) == 1 and pop[0]["hms"] == "090100"


class TestKill1:
    def _mk(self, low_2023_cut):
        """저활력(best 0.5) + 승자(best 4.0) 각각 연도별. low_2023_cut 로 2023 반전 제어."""
        recs = []
        for yr, day in ((2022, 20220401), (2023, 20230401)):
            lc = -0.8 if yr == 2022 else low_2023_cut
            for i in range(20):
                recs.append(_rec("RR8_12", day, f"09{i:02d}00", inc_pct=-1.0, inc_cond=3,
                                 per_T={T: _cell(1, 0.5, -0.5, lc) for T in (120, 180, 240)},
                                 cand={}))
            for i in range(20, 40):
                recs.append(_rec("RR8_12", day, f"09{i:02d}00", inc_pct=3.0, inc_cond=5,
                                 per_T={T: _cell(1, 4.0, 3.0, 2.0) for T in (120, 180, 240)},
                                 cand={}))
        return recs

    def test_state_separates_not_fire(self):
        # 저활력 절단이득 +0.2(양년), 승자 절단이득 -1.0(양년) → 분리, kill1 미발동.
        v = kill1_verdict(self._mk(-0.8), (120, 180, 240))
        assert v["kill1_fires"] is False
        assert 120 in v["state_robust_T"]

    def test_regime_flip_fragile(self):
        # 2023 저활력 절단가 +2.0(현직 -1.0 대비 이득 +3.0>0) 이지만 승자보다 크므로 분리 유지;
        # 반전 케이스: 2023 저활력 cut = -3.0 → 절단이득 -2.0<0 → 그 해 분리 실패.
        v = kill1_verdict(self._mk(-3.0), (120, 180, 240))
        assert 120 in v["regime_fragile_T"]

    def test_help_hurt_map_benefit_sign(self):
        recs = self._mk(-0.8)
        hh = help_hurt_map(recs, (120,))
        # 저활력 셀(best<1.0, sp<0): 절단이득 = cut(-0.8) - inc(-1.0) = +0.2.
        cell = next(c for c in hh[120]["grid"] if c["best_bin"] == "best<1.0" and c["sp_sign"] == "sp<0")
        assert cell["mean_cut_benefit"] == 0.2


class TestR3Candidate:
    def test_dnet_year_overlap(self):
        recs = []
        for yr, day in ((2022, 20220401), (2023, 20230401)):
            for i in range(10):
                recs.append(_rec("RR8_12", day, f"09{i:02d}00", inc_pct=-1.0, inc_cond=3,
                                 per_T={T: _cell(1, 0.5, -0.5, -0.7) for T in (120, 180, 240)},
                                 cand=_b_cand("B1", affected=1, dnet=0.3, b_fired=1, won=1000)))
        res = run_r3_candidate(
            Patch(family="B", T=120, x=1.0, y=0.0, label="B1"), recs, recs, adopt_floor=0.10,
        )
        assert res["n_affected"] == 20
        assert abs(res["mean_dnet_pp"] - 0.3) < 1e-9
        assert res["year_direction"][2022]["sign"] == 1
        assert res["overlap"]["overlap_rate"] == 1.0   # 20 발동 / 20 보유≥T.
        assert res["family_consistency"]["per_champion"]["RR8_12"]["sign"] == 1

    def test_mde_from_ci(self):
        # CI 폭 4.0 → SE ≈ 4/3.92 ≈ 1.0204 → MDE ≈ 2.802*1.0204 ≈ 2.86.
        mde = _mde_from_ci(-2.0, 2.0)
        assert 2.8 < mde < 2.95
