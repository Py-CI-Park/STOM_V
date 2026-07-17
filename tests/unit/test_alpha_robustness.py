"""alpha_lab.ensemble.robustness 단위 테스트 (알파 랩 v4.1 견고성 4검정 — 엔진 0회, 오프라인).

봉인 근거: v4_1_robustness_preregistration.json (sha256 db829ed9...).

검증 범위:
  - slice_window: 챔피언별 (ym, pnl) 목록 → [start_ym, end_ym] 포함구간만 남긴 슬라이스.
  - window_report: 정렬된 챔피언 시퀀스 → {oneN RiskMetrics, singles RiskMetrics} 손계산.
  - walk_forward: 창 목록 → 창별 window_report 딕셔너리(슬라이스+정렬+계산 통합).
  - subperiod_split: 정렬된 시퀀스를 전/후반으로 나눈 두 window_report.
  - t1_diversification_pass / t2_riskadj_pass: 봉인된 T1/T2 판정 규칙(평균 vs 중앙값
    혼동 방지) — 손계산 양성/음성대조.
  - monte_carlo_calmar: 월 단위 블록 부트스트랩(같은 재표집 월 인덱스를 전 챔피언에
    동시 적용) → P(1/N calmar > 단일 calmar 중앙값). seed 결정성, 손계산 point,
    양성대조(다각화 효과 있음 → 확률 높음), 음성대조(동일 챔피언 → 확률 정확히 0.0).

실DB/백테/네트워크 미사용 — 전부 손으로 만든 합성 시퀀스.
실행: python -m pytest tests/unit/test_alpha_robustness.py -q
"""

from __future__ import annotations

import pytest

from alpha_lab.ensemble.portfolio import align_monthly_series

from alpha_lab.ensemble.robustness import (
    monte_carlo_calmar,
    slice_window,
    subperiod_split,
    t1_diversification_pass,
    t2_riskadj_pass,
    walk_forward,
    window_report,
)


# ---------------------------------------------------------------------------
# slice_window
# ---------------------------------------------------------------------------
class TestSliceWindow:
    def test_keeps_only_inclusive_range(self):
        champs = [
            ("A", [("202201", 10.0), ("202202", 20.0), ("202203", 30.0), ("202204", 40.0)]),
            ("B", [("202201", -1.0), ("202202", -2.0), ("202203", -3.0), ("202204", -4.0)]),
        ]
        out = slice_window(champs, "202202", "202203")
        assert out == [
            ("A", [("202202", 20.0), ("202203", 30.0)]),
            ("B", [("202202", -2.0), ("202203", -3.0)]),
        ]

    def test_no_months_in_range_gives_empty_list(self):
        champs = [("A", [("202201", 10.0)])]
        out = slice_window(champs, "202301", "202312")
        assert out == [("A", [])]

    def test_preserves_champion_order_and_labels(self):
        champs = [("Z", [("202201", 1.0)]), ("A", [("202201", 2.0)])]
        out = slice_window(champs, "202201", "202201")
        assert [label for label, _ in out] == ["Z", "A"]


# ---------------------------------------------------------------------------
# window_report — 손계산 (부분 상보 사례: 1/N이 MDD 개선 + calmar 개선)
# ---------------------------------------------------------------------------
class TestWindowReport:
    def _partial_complementary(self):
        """A=[400,-300,200,-100] mdd=300,calmar=200/300; B=[-100,200,-300,400] mdd=300,
        calmar=200/300 동일. 1/N=[150,-50,-50,150] → mdd=100, calmar=200/100=2.0
        (손계산: 아래 test_hand_computed_metrics에서 각 단계 재검증)."""
        return [("A", [400.0, -300.0, 200.0, -100.0]), ("B", [-100.0, 200.0, -300.0, 400.0])]

    def test_hand_computed_metrics(self):
        report = window_report(self._partial_complementary())
        assert report["n_months"] == 4
        # 단일 챔피언: 둘 다 profit=200, mdd=300, calmar=200/300.
        assert report["singles"]["A"].profit == 200.0
        assert report["singles"]["A"].mdd == 300.0
        assert report["singles"]["A"].calmar == pytest.approx(200.0 / 300.0)
        assert report["singles"]["B"].profit == 200.0
        assert report["singles"]["B"].mdd == 300.0
        # 1/N = [150,-50,-50,150] → cum 150,100,50,200. peak 150,150,150,200.
        # giveback 0,50,100,0 → mdd=100. profit=200. calmar=2.0.
        assert report["oneN"].profit == 200.0
        assert report["oneN"].mdd == 100.0
        assert report["oneN"].calmar == pytest.approx(2.0)

    def test_t1_and_t2_pass_on_diversification_benefit(self):
        report = window_report(self._partial_complementary())
        assert t1_diversification_pass(report) is True  # 100 < mean(300,300)=300
        assert t2_riskadj_pass(report) is True  # 2.0 > median(0.667,0.667)=0.667

    def test_t1_and_t2_fail_when_champions_identical(self):
        """완전 동일 챔피언 두 개 → 1/N == 단일과 완전히 같아 다각화 이득이 전혀 없다
        (엄격부등호라 경계에서 FAIL이 맞다)."""
        seq = [100.0, -150.0, 80.0, -30.0]
        champs = [("A", seq), ("B", list(seq))]
        report = window_report(champs)
        assert report["oneN"].mdd == report["singles"]["A"].mdd
        assert report["oneN"].calmar == report["singles"]["A"].calmar
        assert t1_diversification_pass(report) is False
        assert t2_riskadj_pass(report) is False


# ---------------------------------------------------------------------------
# walk_forward — 슬라이스 + 정렬 + 계산 통합
# ---------------------------------------------------------------------------
class TestWalkForward:
    def test_multi_window_matches_manual_slice_and_report(self):
        champs = [
            (
                "A",
                [
                    ("202201", 400.0), ("202202", -300.0), ("202203", 200.0), ("202204", -100.0),
                    ("202205", 10.0), ("202206", 20.0),
                ],
            ),
            (
                "B",
                [
                    ("202201", -100.0), ("202202", 200.0), ("202203", -300.0), ("202204", 400.0),
                    ("202205", 5.0), ("202206", -5.0),
                ],
            ),
        ]
        windows = [("w1", "202201", "202204"), ("w2", "202205", "202206")]
        out = walk_forward(champs, windows)

        assert set(out) == {"w1", "w2"}
        # w1은 window_report 손계산 테스트와 동일 벡터.
        assert out["w1"]["oneN"].mdd == 100.0
        assert out["w1"]["oneN"].calmar == pytest.approx(2.0)
        assert out["w1"]["singles"]["A"].mdd == 300.0

        # w2: A=[10,20], B=[5,-5] → 1/N=[(10+5)/2,(20-5)/2]=[7.5,7.5] → 단조증가 → mdd=0,calmar=0.0
        oneN_w2 = out["w2"]["oneN"]
        assert oneN_w2.profit == 15.0
        assert oneN_w2.mdd == 0.0
        assert oneN_w2.calmar == 0.0

    def test_window_out_of_range_raises_via_align(self):
        """슬라이스 결과 두 챔피언 개월수가 달라지면(한쪽만 그 구간에 데이터 있음)
        align_monthly_series의 ValueError가 그대로 전파돼야 한다(무음 오정렬 방지)."""
        champs = [
            ("A", [("202201", 1.0), ("202202", 2.0)]),
            ("B", [("202201", 1.0)]),
        ]
        with pytest.raises(ValueError):
            walk_forward(champs, [("w1", "202201", "202202")])


# ---------------------------------------------------------------------------
# subperiod_split
# ---------------------------------------------------------------------------
class TestSubperiodSplit:
    def test_splits_into_two_hand_verified_halves(self):
        champs = [
            ("A", [("202201", 100.0), ("202202", -50.0), ("202203", 60.0), ("202204", -20.0)]),
            ("B", [("202201", -30.0), ("202202", 40.0), ("202203", -10.0), ("202204", 90.0)]),
        ]
        first, second = subperiod_split(champs, split_at=2)
        assert first["n_months"] == 2
        assert second["n_months"] == 2
        # first half A=[100,-50], B=[-30,40] → 1/N=[35,-5]
        assert first["oneN"].profit == 30.0
        # second half A=[60,-20], B=[-10,90] → 1/N=[25,35]
        assert second["oneN"].profit == 60.0
        assert second["oneN"].mdd == 0.0  # 단조증가

    def test_invalid_split_at_raises(self):
        champs = [("A", [("202201", 1.0), ("202202", 2.0)])]
        with pytest.raises(ValueError):
            subperiod_split(champs, split_at=0)
        with pytest.raises(ValueError):
            subperiod_split(champs, split_at=2)
        with pytest.raises(ValueError):
            subperiod_split(champs, split_at=-1)


# ---------------------------------------------------------------------------
# monte_carlo_calmar
# ---------------------------------------------------------------------------
class TestMonteCarloCalmar:
    def _diversifying_champions(self):
        """부분 상보 + 잡음 8개월 — 재표집해도 대체로 1/N이 우세하도록 설계."""
        a = [400.0, -300.0, 200.0, -100.0, 380.0, -260.0, 210.0, -90.0]
        b = [-100.0, 200.0, -300.0, 400.0, -80.0, 190.0, -270.0, 410.0]
        months = [f"2022{m:02d}" for m in range(1, 9)]
        return [("A", list(zip(months, a))), ("B", list(zip(months, b)))]

    def test_same_seed_is_deterministic(self):
        champs = self._diversifying_champions()
        r1 = monte_carlo_calmar(champs, n=300, seed=42)
        r2 = monte_carlo_calmar(champs, n=300, seed=42)
        assert r1 == r2

    def test_point_matches_hand_computed_original_data(self):
        """point는 재표집 없는 원본 데이터의 지표(4개월 부분상보 사례 재사용) — 2.0 > 0.667."""
        champs = [
            ("A", [("202201", 400.0), ("202202", -300.0), ("202203", 200.0), ("202204", -100.0)]),
            ("B", [("202201", -100.0), ("202202", 200.0), ("202203", -300.0), ("202204", 400.0)]),
        ]
        result = monte_carlo_calmar(champs, n=50, seed=1)
        assert result["point"] == 1.0
        assert result["n_months"] == 4
        assert result["labels"] == ["A", "B"]

    def test_positive_control_high_probability_with_diversification(self):
        champs = self._diversifying_champions()
        result = monte_carlo_calmar(champs, n=2000, seed=20260707)
        assert result["prob"] > 0.7

    def test_negative_control_identical_champions_is_exactly_zero(self):
        """완전 동일 챔피언 → 어떤 재표집에서도 1/N calmar == 단일 calmar(중앙값) →
        엄격부등호라 단 한 번도 참이 될 수 없다(정확히 0.0, 재표집 무관 결정론)."""
        seq = [100.0, -50.0, 30.0, -80.0, 200.0, -10.0]
        months = [f"2022{m:02d}" for m in range(1, 7)]
        champs = [("A", list(zip(months, seq))), ("B", list(zip(months, list(seq))))]
        result = monte_carlo_calmar(champs, n=500, seed=7)
        assert result["prob"] == 0.0
        assert result["point"] == 0.0

    def test_mismatched_month_labels_raises(self):
        champs = [
            ("A", [("202201", 1.0), ("202202", 2.0)]),
            ("B", [("202201", 1.0), ("202203", 2.0)]),
        ]
        with pytest.raises(ValueError):
            monte_carlo_calmar(champs, n=10, seed=1)


# ---------------------------------------------------------------------------
# 회귀 방지: align_monthly_series 재사용 확인(재구현 아님) — JSON list-of-list 입력 호환
# ---------------------------------------------------------------------------
def test_walk_forward_uses_same_alignment_contract_as_portfolio():
    champs = [
        ("A", [["202201", 10.0], ["202202", 20.0]]),  # JSON 역직렬화 형태(list of list)
        ("B", [["202201", -5.0], ["202202", 15.0]]),
    ]
    ym_labels, aligned = align_monthly_series(champs)
    out = walk_forward(champs, [("only", "202201", "202202")])
    assert out["only"]["n_months"] == len(ym_labels)
    # 1/N = [(10-5)/2, (20+15)/2] = [2.5, 17.5] → profit = 20.0
    assert out["only"]["oneN"].profit == 20.0
