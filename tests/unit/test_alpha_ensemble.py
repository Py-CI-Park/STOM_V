"""alpha_lab.ensemble.portfolio 단위 테스트 (알파 랩 v4 R1+R2 — 엔진 0회, 오프라인).

검증 범위:
  - risk_adjusted_metrics: 손계산 시퀀스 → 정확한 (profit, mdd, calmar). MDD==0이면
    calmar=0.0(0-나눗셈 가드). adaptive_timing._equity_mdd와 동일 관례 교차검증.
  - align_monthly_series: 챔피언별 (ym, pnl) 목록 정렬/검증 — 월 라벨 불일치 시 ValueError.
  - static_equal: N개 챔피언 손익의 1/N 등가중 평균(손계산).
  - adaptive_sum: 각 챔피언에 독립적으로 apply_adaptive_timing(재사용, 재구현 아님) 적용 후
    등가중 합산 — "적응형 OFF 로직"이 챔피언별로 독립 판단됨을 검증.
  - regime_rotation: 워밍업=등가중 대체, 그 외 직전 lookback 트레일링 합 최고 챔피언
    택1(동률은 목록 순서상 먼저 나온 챔피언). 무선견(no-lookahead) 검증 포함.
  - 양성대조: 상보적(anti-correlated) 챔피언 쌍에서 앙상블(static_equal) MDD가 두 단일
    챔피언 MDD보다 개선됨을 확인(다각화 효과의 기계적 증거).

실DB/백테/네트워크 미사용 — 전부 손으로 만든 합성 시퀀스.
실행: python -m pytest tests/unit/test_alpha_ensemble.py -q
"""

from __future__ import annotations

import pytest

from ai_strategy_loop.fitness.adaptive_timing import _equity_mdd, apply_adaptive_timing

from alpha_lab.ensemble.portfolio import (
    RiskMetrics,
    align_monthly_series,
    adaptive_sum,
    regime_rotation,
    risk_adjusted_metrics,
    static_equal,
)


# ---------------------------------------------------------------------------
# risk_adjusted_metrics
# ---------------------------------------------------------------------------
class TestRiskAdjustedMetrics:
    def test_known_sequence(self):
        """[100,-30,-50,80] → 누적 100,70,20,100. peak=100. 반납 최대=100-20=80.

        profit=100, mdd=80, calmar=100/80=1.25 (adaptive_timing._equity_mdd 테스트와 동일 벡터).
        """
        result = risk_adjusted_metrics([100.0, -30.0, -50.0, 80.0])
        assert isinstance(result, RiskMetrics)
        assert result.profit == 100.0
        assert result.mdd == 80.0
        assert result.calmar == pytest.approx(1.25)

    def test_monotonic_up_zero_mdd_zero_calmar(self):
        """단조 증가 시퀀스 → MDD=0 → calmar=0.0(0-나눗셈 가드, adaptive_timing_report와 동일 관례)."""
        result = risk_adjusted_metrics([10.0, 20.0, 30.0])
        assert result.profit == 60.0
        assert result.mdd == 0.0
        assert result.calmar == 0.0

    def test_matches_established_equity_mdd_convention(self):
        """독립 구현이 ai_strategy_loop.fitness.adaptive_timing._equity_mdd와 (profit,mdd) byte-동일.

        재구현이 아니라 동일 peak-drawdown 관례(발산 없는 절대 반납액, 원)의 교차검증 —
        equity_series.parse_backtest_series의 drawdown과도 동일한 관례.
        """
        seq = [120.0, -40.0, 300.0, -250.0, 10.0]
        expected_total, expected_mdd = _equity_mdd(seq)
        result = risk_adjusted_metrics(seq)
        assert result.profit == expected_total
        assert result.mdd == expected_mdd

    def test_empty_sequence_is_zero(self):
        result = risk_adjusted_metrics([])
        assert result == RiskMetrics(profit=0.0, mdd=0.0, calmar=0.0)


# ---------------------------------------------------------------------------
# align_monthly_series
# ---------------------------------------------------------------------------
class TestAlignMonthlySeries:
    def test_aligns_labels_and_values(self):
        champs = [
            ("A", [("202201", 10.0), ("202202", 20.0)]),
            ("B", [("202201", -5.0), ("202202", 15.0)]),
        ]
        ym_labels, aligned = align_monthly_series(champs)
        assert ym_labels == ["202201", "202202"]
        assert aligned == [("A", [10.0, 20.0]), ("B", [-5.0, 15.0])]

    def test_mismatched_month_labels_raises(self):
        champs = [
            ("A", [("202201", 10.0), ("202202", 20.0)]),
            ("B", [("202201", -5.0), ("202203", 15.0)]),
        ]
        with pytest.raises(ValueError):
            align_monthly_series(champs)

    def test_empty_champions_raises(self):
        with pytest.raises(ValueError):
            align_monthly_series([])

    def test_accepts_list_of_list_pairs_like_json_deserialization(self):
        """json.load가 만드는 [ym, pnl] 리스트(튜플 아님) 입력도 동일하게 동작한다 —
        v4_characterization.json의 monthly_pnl 실제 형태(JSON 배열)를 그대로 반영."""
        champs = [
            ("A", [["202201", 10.0], ["202202", 20.0]]),
            ("B", [["202201", -5.0], ["202202", 15.0]]),
        ]
        ym_labels, aligned = align_monthly_series(champs)
        assert ym_labels == ["202201", "202202"]
        assert aligned == [("A", [10.0, 20.0]), ("B", [-5.0, 15.0])]


# ---------------------------------------------------------------------------
# static_equal
# ---------------------------------------------------------------------------
class TestStaticEqual:
    def test_two_champions_hand_computed(self):
        """A=[100,-50,60], B=[-20,80,40] → 등가중 평균 = [(100-20)/2,(-50+80)/2,(60+40)/2]
        = [40.0, 15.0, 50.0]."""
        champs = [("A", [100.0, -50.0, 60.0]), ("B", [-20.0, 80.0, 40.0])]
        out = static_equal(champs)
        assert out == [40.0, 15.0, 50.0]

    def test_single_champion_is_identity(self):
        champs = [("A", [10.0, -5.0, 3.0])]
        assert static_equal(champs) == [10.0, -5.0, 3.0]

    def test_length_mismatch_raises(self):
        champs = [("A", [1.0, 2.0, 3.0]), ("B", [1.0, 2.0])]
        with pytest.raises(ValueError):
            static_equal(champs)

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            static_equal([])


# ---------------------------------------------------------------------------
# adaptive_sum — "적응형 OFF 로직"이 챔피언별로 독립 판단됨을 검증
# ---------------------------------------------------------------------------
class TestAdaptiveSum:
    def test_matches_manual_per_champion_apply_adaptive_timing(self):
        """adaptive_sum == 각 챔피언 apply_adaptive_timing(재사용) 결과의 등가중 평균.

        A=[100,-200,-300,50], B=[10,10,10,10], lookback=2.
        A(timed) = apply_adaptive_timing(A,2) = [100,-200,0,0] (test_adaptive_timing.py의
          adaptive_timing_report 벡터와 동일 로직).
        B(timed) = apply_adaptive_timing(B,2) = [10,10,10,10] (전부 양수 트레일링이라 유지).
        등가중 평균 = [(100+10)/2, (-200+10)/2, (0+10)/2, (0+10)/2] = [55.0, -95.0, 5.0, 5.0].
        """
        a = [100.0, -200.0, -300.0, 50.0]
        b = [10.0, 10.0, 10.0, 10.0]
        champs = [("A", a), ("B", b)]
        expected_a = apply_adaptive_timing(a, lookback=2)
        expected_b = apply_adaptive_timing(b, lookback=2)
        assert expected_a == [100.0, -200.0, 0.0, 0.0]
        expected = [(x + y) / 2.0 for x, y in zip(expected_a, expected_b)]

        out = adaptive_sum(champs, lookback=2)
        assert out == expected
        assert out == [55.0, -95.0, 5.0, 5.0]

    def test_off_is_independent_per_champion(self):
        """A는 3번째 달 FLAT(직전 2달 합 음수)로 꺼지고, B는 계속 살아있는 손익을
        그대로 등가중 반영한다 — 한 챔피언의 OFF가 다른 챔피언 값을 오염하지 않는다.
        """
        a = [-100.0, -100.0, 999.0]  # i2: sum(a[0:2])=-200<0 → FLAT(0), 원래 999 손실.
        b = [50.0, 50.0, 50.0]       # i2: sum(b[0:2])=100>=0 → 유지(50).
        out = adaptive_sum([("A", a), ("B", b)], lookback=2)
        # i2 = (0.0[A flat] + 50.0[B kept]) / 2 = 25.0 (999가 섞였다면 크게 달랐을 것).
        assert out[2] == 25.0

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            adaptive_sum([("A", [1.0, 2.0]), ("B", [1.0])], lookback=1)


# ---------------------------------------------------------------------------
# regime_rotation
# ---------------------------------------------------------------------------
class TestRegimeRotation:
    def test_warmup_uses_equal_blend(self):
        """lookback=2 → warmup=max(1,2)=2개월은 트레일링 판단 근거가 없어 등가중 대체."""
        a = [100.0, -50.0, 10.0, 10.0]
        b = [-20.0, 80.0, 10.0, 10.0]
        out, picks = regime_rotation([("A", a), ("B", b)], lookback=2)
        assert out[0] == pytest.approx((100.0 + -20.0) / 2.0)
        assert out[1] == pytest.approx((-50.0 + 80.0) / 2.0)
        assert picks[0] == "EQUAL_WARMUP"
        assert picks[1] == "EQUAL_WARMUP"

    def test_picks_best_trailing_champion_after_warmup(self):
        """i2: 트레일링(=[0:2]) 합 A=50, B=60 → B가 더 높아 B 채택(원본 B[2]=10).
        i3: 트레일링(=[1:3]) 합 A=-40, B=90 → B 채택(B[3]=10)."""
        a = [100.0, -50.0, 10.0, 10.0]
        b = [-20.0, 80.0, 10.0, 10.0]
        out, picks = regime_rotation([("A", a), ("B", b)], lookback=2)
        assert picks[2] == "B"
        assert out[2] == 10.0
        assert picks[3] == "B"
        assert out[3] == 10.0

    def test_switches_champion_when_trailing_favor_flips(self):
        """A가 초반 강세 후 급락, B가 반대 — 로테이션이 실제로 챔피언을 전환하는지 확인."""
        a = [500.0, 500.0, -900.0, -900.0, 5.0]
        b = [1.0, 1.0, 1.0, 400.0, 400.0]
        out, picks = regime_rotation([("A", a), ("B", b)], lookback=2)
        # i2: trailing A=1000,B=2 → A 채택(A[2]=-900).
        assert picks[2] == "A"
        assert out[2] == -900.0
        # i4: trailing(=[2:4]) A=-1800, B=401 → B 채택(B[4]=400).
        assert picks[4] == "B"
        assert out[4] == 400.0

    def test_tie_breaks_to_first_listed_champion(self):
        """트레일링 합이 정확히 동률이면 champion_series 순서상 먼저 나온 챔피언 승리(결정론)."""
        a = [50.0, 50.0, 999.0]
        b = [50.0, 50.0, -999.0]  # i2 트레일링: A=100, B=100 (동률) → A(먼저 나열)가 이김.
        out, picks = regime_rotation([("A", a), ("B", b)], lookback=2)
        assert picks[2] == "A"
        assert out[2] == 999.0

    def test_no_lookahead(self):
        """i번째 달까지의 pick은 i번째 이후 데이터를 바꿔도 변하지 않는다(인과적)."""
        a_full = [10.0, -30.0, 40.0, 999.0, -999.0]
        b_full = [-10.0, 40.0, -30.0, -999.0, 999.0]
        a_alt = [10.0, -30.0, 40.0, 1.0, 1.0]
        b_alt = [-10.0, 40.0, -30.0, 1.0, 1.0]

        _, picks_full = regime_rotation([("A", a_full), ("B", b_full)], lookback=2)
        _, picks_alt = regime_rotation([("A", a_alt), ("B", b_alt)], lookback=2)
        # 인덱스 3(마지막에서 두번째)까지는 두 시나리오 입력이 동일하므로 pick도 동일해야 한다.
        assert picks_full[:3] == picks_alt[:3]

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            regime_rotation([("A", [1.0, 2.0]), ("B", [1.0])], lookback=1)


# ---------------------------------------------------------------------------
# 양성대조: 상보적 쌍에서 앙상블 MDD 개선
# ---------------------------------------------------------------------------
class TestComplementaryPairPositiveControl:
    def test_static_equal_mdd_improves_over_either_single_champion(self):
        """A·B가 완전 상보적(한쪽이 손실인 달엔 다른 쪽이 이익)이면, 등가중 앙상블의
        MDD가 두 단일 챔피언 MDD보다 작아야 한다(다각화 효과의 기계적 증거).

        A = [+100, -100, +100, -100, +100, -100] (변동 큼, 각 -100 손실 후 MDD 발생).
        B = [-100, +100, -100, +100, -100, +100] (A와 정반대 위상).
        등가중 평균 = [0,0,0,0,0,0] → 절대 낙폭 없음(MDD=0) — A/B 단일 MDD(100)보다 개선.
        """
        a = [100.0, -100.0, 100.0, -100.0, 100.0, -100.0]
        b = [-100.0, 100.0, -100.0, 100.0, -100.0, 100.0]

        metrics_a = risk_adjusted_metrics(a)
        metrics_b = risk_adjusted_metrics(b)
        ensemble = static_equal([("A", a), ("B", b)])
        metrics_ensemble = risk_adjusted_metrics(ensemble)

        assert metrics_a.mdd == 100.0
        assert metrics_b.mdd == 100.0
        assert metrics_ensemble.mdd == 0.0
        assert metrics_ensemble.mdd < metrics_a.mdd
        assert metrics_ensemble.mdd < metrics_b.mdd

    def test_static_equal_mdd_improves_with_partial_complementarity(self):
        """완전 상쇄가 아니어도(부분 상보) 앙상블 MDD가 단일 최악보다는 개선됨을 확인.

        A는 초반 급락(큰 손실 몰림), B는 그 구간에 완만한 이익 — 흔한 "약세장에서
        다른 전략은 흑자"(설계 문서 핵심 통찰) 패턴의 축소판.
        """
        a = [-300.0, -200.0, 400.0, 100.0]   # peak=0→누적 -300,-500,-100,0. MDD=500.
        b = [50.0, 60.0, 10.0, 10.0]          # 단조 증가. MDD=0.
        ensemble = static_equal([("A", a), ("B", b)])
        metrics_a = risk_adjusted_metrics(a)
        metrics_ensemble = risk_adjusted_metrics(ensemble)
        assert metrics_a.mdd == 500.0
        assert metrics_ensemble.mdd < metrics_a.mdd
