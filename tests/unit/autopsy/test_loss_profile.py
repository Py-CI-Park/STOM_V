"""G-0a 손실 형태 프로파일러 계약 테스트.

핵심 회귀 방어:
  - multi_band 를 valley 보다 먼저 판정한다(설계서 §2.3a 초안 오류 재발 방지).
  - 10분위 경계는 설계에서만 산출한다(홀드아웃 누출 금지).
  - 고립 1칸은 제거 후보가 되지 않는다.
  - 무작위 라벨에서 2D 포켓은 0건이어야 한다(FDR).
"""

from __future__ import annotations

import random

import pytest

from ai_strategy_loop.autopsy import loss_profile as lp


def _rows(pairs: list[tuple[float, float]], *, date: int = 20240304) -> list[lp.Sample]:
    """(변수값, 건당손익) 목록 → Sample 목록."""
    return [lp.Sample(values={"X": value}, pnl=pnl, date=date) for value, pnl in pairs]


def _curve(per_bucket: list[float], *, per_cell: int = 200) -> list[lp.Sample]:
    """분위별 건당손익 곡선을 그대로 갖는 합성 표본(분위당 per_cell 건)."""
    out: list[lp.Sample] = []
    for index, per_trade in enumerate(per_bucket):
        for offset in range(per_cell):
            # 분위 내부에서 값이 균등하게 퍼지도록 index + 소수부.
            out.append(
                lp.Sample(
                    values={"X": index + offset / per_cell},
                    pnl=per_trade,
                    date=20240304 + offset % 7,
                )
            )
    return out


# --------------------------------------------------------------------------- 분위

def test_edges_come_from_design_only():
    """홀드아웃 분포가 달라도 경계는 설계 경계를 그대로 쓴다."""
    design = _rows([(float(i), -100.0) for i in range(1000)])
    holdout = _rows([(float(i) * 10, -100.0) for i in range(1000)])
    profile = lp.profile_variable(
        variable="X", design=design, holdout=holdout, min_bucket=50,
    )
    # 설계 값 범위 0~999 → 경계 9개가 전부 그 범위 안.
    assert len(profile.edges) == 9
    assert all(0.0 <= edge <= 999.0 for edge in profile.edges)
    # 홀드아웃은 값이 10배라 상위 분위로 몰린다 — 경계를 다시 잡지 않았다는 증거.
    assert profile.holdout[-1].n > profile.holdout[0].n


def test_insufficient_bucket_is_flagged_and_excluded():
    design = _curve([-100.0] * 10, per_cell=20)   # 분위당 20건 < min_bucket 50
    profile = lp.profile_variable(
        variable="X", design=design, holdout=design, min_bucket=50,
    )
    assert all(bucket.insufficient for bucket in profile.design)
    assert profile.shape == "flat"
    assert profile.worst_span is None


# --------------------------------------------------------------------------- 형태 6종

def test_shape_monotone_down():
    curve = [1000.0, 800.0, 600.0, 400.0, 200.0, 0.0, -200.0, -400.0, -600.0, -800.0]
    profile = lp.profile_variable(
        variable="X", design=_curve(curve), holdout=_curve(curve), min_bucket=50,
    )
    assert profile.shape == "monotone_down"


def test_shape_monotone_up():
    curve = [-800.0, -600.0, -400.0, -200.0, 0.0, 200.0, 400.0, 600.0, 800.0, 1000.0]
    profile = lp.profile_variable(
        variable="X", design=_curve(curve), holdout=_curve(curve), min_bucket=50,
    )
    assert profile.shape == "monotone_up"


def test_shape_tail_high():
    """중간은 평탄하고 상위 2분위만 급락 — 단측 상한 절이 맞는 형태."""
    curve = [-100.0, -105.0, -100.0, -95.0, -100.0, -105.0, -100.0, -95.0, -900.0, -950.0]
    profile = lp.profile_variable(
        variable="X", design=_curve(curve), holdout=_curve(curve), min_bucket=50,
    )
    assert profile.shape == "tail_high"


def test_shape_tail_low():
    curve = [-950.0, -900.0, -95.0, -100.0, -105.0, -100.0, -95.0, -100.0, -105.0, -100.0]
    profile = lp.profile_variable(
        variable="X", design=_curve(curve), holdout=_curve(curve), min_bucket=50,
    )
    assert profile.shape == "tail_low"


def test_shape_valley():
    """중앙부 한 구간만 나쁘고 양끝 2분위가 모두 평균보다 좋음."""
    curve = [400.0, 350.0, -900.0, -950.0, -900.0, -880.0, 300.0, 350.0, 400.0, 380.0]
    profile = lp.profile_variable(
        variable="X", design=_curve(curve), holdout=_curve(curve), min_bucket=50,
    )
    assert profile.shape == "valley"


def test_shape_multi_band_checked_before_valley():
    """체결강도 실측 형태(D1 나쁨 + D3~D7 나쁨)는 valley 가 아니라 multi_band 다.

    설계서 §2.3a: 초안이 valley 로 오분류해 표본밖 개선을 +682 → +310 으로
    절반 이하로 놓칠 뻔했다. 이 테스트가 그 재발을 막는다.
    """
    curve = [-900.0, 300.0, -950.0, -930.0, -940.0, -920.0, -910.0, 400.0, 450.0, 500.0]
    profile = lp.profile_variable(
        variable="X", design=_curve(curve), holdout=_curve(curve), min_bucket=50,
    )
    assert profile.shape == "multi_band"
    # 두 개의 나쁜 구간이 분리되어 보고된다.
    assert len(profile.bad_runs) >= 2


def test_real_체결강도_curve_is_multi_band_with_interior_span():
    """실측 체결강도(tick 69,034건 설계) 곡선 — 형태와 제거 구간이 함께 나와야 한다.

    D1 이 나쁘고 D2~D3 이 평균 근처로 올라왔다가 D4~D8 이 다시 나쁘다.
    ρ=0.55 라 단조도 아니고 꼬리도 아니다. 여기서 flat 으로 떨어뜨리면
    34% 거래를 담은 D4~D8 연속 손실 구간을 통째로 버린다.
    """
    curve = [-6282.0, -4874.0, -5227.0, -5880.0, -5822.0,
             -5700.0, -5459.0, -5652.0, -4467.0, -4048.0]
    profile = lp.profile_variable(
        variable="X", design=_curve(curve), holdout=_curve(curve), min_bucket=50,
    )
    assert profile.shape == "multi_band"
    span = profile.worst_span
    assert span is not None
    # 고립 1칸인 D1 이 아니라 연속 구간 D4~D8 이 선택된다.
    assert (span.from_bucket, span.to_bucket) == (4, 8)
    assert profile.confirmed is True


def test_unclassified_curve_still_reports_its_loss_region():
    """형태 이름을 못 붙여도 실제 연속 손실 구간이 있으면 버리지 않는다."""
    curve = [-900.0, -880.0, 200.0, 210.0, -870.0,
             -860.0, 220.0, 230.0, 240.0, 250.0]
    profile = lp.profile_variable(
        variable="X", design=_curve(curve), holdout=_curve(curve), min_bucket=50,
    )
    assert profile.worst_span is not None
    assert profile.reason != "flat"


def test_shape_flat():
    curve = [-100.0, -101.0, -99.0, -100.0, -102.0, -98.0, -100.0, -101.0, -99.0, -100.0]
    profile = lp.profile_variable(
        variable="X", design=_curve(curve), holdout=_curve(curve), min_bucket=50,
    )
    assert profile.shape == "flat"
    assert profile.worst_span is None


# --------------------------------------------------------------------------- 홀드아웃 검증

def test_design_only_loss_region_is_unstable():
    """설계에서만 나쁜 구간은 confirmed 가 아니라 unstable 이어야 한다."""
    design = _curve([300.0, 350.0, -900.0, -950.0, -900.0, 300.0, 320.0, 340.0, 360.0, 380.0])
    holdout = _curve([100.0, 110.0, 120.0, 130.0, 120.0, 110.0, 100.0, 110.0, 120.0, 130.0])
    profile = lp.profile_variable(
        variable="X", design=design, holdout=holdout, min_bucket=50,
    )
    assert profile.confirmed is False
    assert profile.reason == "holdout_not_bad"


def test_isolated_single_bucket_is_not_a_candidate():
    """고립 1칸(인접 없음)은 제거 후보 구간이 되지 않는다."""
    curve = [200.0, 210.0, -900.0, 220.0, 230.0, 240.0, 250.0, 260.0, 270.0, 280.0]
    profile = lp.profile_variable(
        variable="X", design=_curve(curve), holdout=_curve(curve), min_bucket=50,
    )
    assert profile.worst_span is None
    assert profile.reason == "no_contiguous_run"


def test_worst_span_reports_share_and_edges():
    curve = [400.0, 350.0, -900.0, -950.0, -900.0, -880.0, 300.0, 350.0, 400.0, 380.0]
    profile = lp.profile_variable(
        variable="X", design=_curve(curve), holdout=_curve(curve), min_bucket=50,
    )
    span = profile.worst_span
    assert span is not None
    assert (span.from_bucket, span.to_bucket) == (3, 6)
    assert span.contiguous is True
    # 10분위 중 4칸 → 제거 비중 약 40%.
    assert 0.35 <= span.design_share <= 0.45
    assert span.low is not None and span.high is not None


def test_open_ended_span_has_none_edge():
    """1분위부터 시작하는 구간은 하한이 없다(단측 절로 표현)."""
    curve = [-900.0, -880.0, -870.0, 300.0, 320.0, 340.0, 360.0, 380.0, 400.0, 420.0]
    profile = lp.profile_variable(
        variable="X", design=_curve(curve), holdout=_curve(curve), min_bucket=50,
    )
    span = profile.worst_span
    assert span is not None
    assert span.from_bucket == 1
    assert span.low is None
    assert span.high is not None


# --------------------------------------------------------------------------- 2D 포켓

def _grid_samples(*, seed: int, planted: bool) -> list[lp.Sample]:
    rng = random.Random(seed)
    out: list[lp.Sample] = []
    for _ in range(12000):
        x = rng.uniform(0.0, 100.0)
        y = rng.uniform(0.0, 100.0)
        pnl = rng.gauss(-100.0, 300.0)
        if planted and 30.0 <= x < 50.0 and 60.0 <= y < 80.0:
            pnl -= 3000.0
        out.append(lp.Sample(values={"X": x, "Y": y}, pnl=pnl, date=20240304))
    return out


def test_pocket_scan_finds_planted_pocket():
    design = _grid_samples(seed=11, planted=True)
    holdout = _grid_samples(seed=22, planted=True)
    pockets = lp.pocket_scan(
        design=design, holdout=holdout, variables=("X", "Y"), min_cell=50,
    )
    assert pockets, "심어둔 손실 포켓을 찾지 못했다"
    best = pockets[0]
    assert best.pair == ("X", "Y")
    assert best.design_per_trade < -1000 and best.holdout_per_trade < -1000  # 양쪽 다 나쁨
    assert best.cells >= 2
    assert best.rect_waste <= 0.30


def test_pocket_cells_all_pass_fdr():
    """포켓에 담긴 칸은 전부 FDR 통과분이어야 한다 — 연결 성분을 FDR 뒤에 만드는 이유."""
    design = _grid_samples(seed=11, planted=True)
    holdout = _grid_samples(seed=22, planted=True)
    pockets = lp.pocket_scan(
        design=design, holdout=holdout, variables=("X", "Y"), min_cell=50,
    )
    assert pockets
    assert all(pocket.max_q <= lp.FDR_ALPHA for pocket in pockets)


def test_pocket_scan_on_random_labels_is_empty():
    """무작위 손익에서는 FDR 보정이 포켓을 전부 걸러야 한다."""
    design = _grid_samples(seed=101, planted=False)
    holdout = _grid_samples(seed=202, planted=False)
    pockets = lp.pocket_scan(
        design=design, holdout=holdout, variables=("X", "Y"), min_cell=50,
    )
    assert pockets == ()


def test_pocket_rectangle_approximation_cap():
    """대각선 포켓처럼 직사각형 근사 손실이 크면 후보에서 제외된다."""
    good = [(0, 0), (1, 1), (2, 2), (3, 3)]      # 대각선 → bbox 16칸 중 4칸만 나쁨
    assert lp.rectangle_waste(good) > 0.30
    solid = [(0, 0), (0, 1), (1, 0), (1, 1)]     # 꽉 찬 2×2 → 낭비 0
    assert lp.rectangle_waste(solid) == 0.0


# --------------------------------------------------------------------------- 파레토

def test_pareto_front_keeps_non_dominated_only():
    items = (
        {"name": "a", "removal": 0.10, "gain": 300.0},   # 비지배
        {"name": "b", "removal": 0.20, "gain": 500.0},   # 비지배
        {"name": "c", "removal": 0.30, "gain": 400.0},   # b 에 지배됨
        {"name": "d", "removal": 0.05, "gain": 100.0},   # 비지배
    )
    front = lp.pareto_front(items, removal_key="removal", gain_key="gain")
    assert [item["name"] for item in front] == ["d", "a", "b"]


# --------------------------------------------------------------------------- 통합

def test_profile_csv_payload_shape(tmp_path):
    """CSV 두 개 → 변수별 프로파일 payload(진단 권위 표시 포함)."""
    header = "종목명,매수시간,수익금,B_등락율\n"
    def write(path, rows):
        path.write_text(header + "".join(rows), encoding="utf-8-sig")

    design_rows = [
        f"종목{i},2024030409{i % 60:02d}00,{-900 if i % 10 < 4 else 300},{i % 10}.5\n"
        for i in range(2000)
    ]
    holdout_rows = [
        f"종목{i},2025090109{i % 60:02d}00,{-900 if i % 10 < 4 else 300},{i % 10}.5\n"
        for i in range(1000)
    ]
    design_csv = tmp_path / "design.csv"
    holdout_csv = tmp_path / "holdout.csv"
    write(design_csv, design_rows)
    write(holdout_csv, holdout_rows)

    payload = lp.profile_payload(
        design_csv=design_csv, holdout_csv=holdout_csv, min_bucket=50,
    )
    assert payload["authority"] == "diagnostic"
    assert payload["available"] is True
    assert any(item["variable"] == "B_등락율" for item in payload["profiles"])


def test_derived_time_variable_is_skipped_when_native_column_exists():
    """B_시분초 가 있으면 파생 시분초를 또 만들지 않는다(같은 축 중복)."""
    with_native = lp._default_variables(["종목명", "매수시간", "수익금", "B_시분초", "B_등락율"])
    assert "시분초" not in with_native
    assert "B_시분초" in with_native
    without_native = lp._default_variables(["종목명", "매수시간", "수익금", "B_등락율"])
    assert "시분초" in without_native


def test_only_buy_snapshot_variables_are_proposable():
    """거래기록 원열은 매수 시점 확정값 보장이 없어 진단 전용이다."""
    assert lp.is_proposable("B_체결강도") is True
    assert lp.is_proposable("시분초") is True
    assert lp.is_proposable("시가총액") is False
    assert lp.is_proposable("R_MFE") is False
    assert lp.is_proposable("S_현재가") is False


def test_pareto_excludes_diagnostic_only_variables(tmp_path):
    """파레토 전선(후보 순위)에는 제안 불가 변수가 들어가지 않는다."""
    header = "종목명,매수시간,수익금,시가총액,B_등락율\n"
    def rows(prefix, count):
        # 시가총액·B_등락율 모두 하위 40% 가 손실 — 둘 다 confirmed 가 되게 만든다.
        return [
            f"종목{i},{prefix}09{i % 60:02d}00,{-900 if i % 10 < 4 else 300},"
            f"{i % 10}.5,{i % 10}.5\n"
            for i in range(count)
        ]
    design_csv = tmp_path / "d.csv"
    holdout_csv = tmp_path / "h.csv"
    design_csv.write_text(header + "".join(rows("20240304", 3000)), encoding="utf-8-sig")
    holdout_csv.write_text(header + "".join(rows("20250901", 1500)), encoding="utf-8-sig")

    payload = lp.profile_payload(
        design_csv=design_csv, holdout_csv=holdout_csv, min_bucket=50,
    )
    names = {item["variable"] for item in payload["pareto"]}
    assert "시가총액" not in names
    by_name = {item["variable"]: item for item in payload["profiles"]}
    assert by_name["시가총액"]["proposable"] is False
    assert by_name["B_등락율"]["proposable"] is True


def test_profile_payload_reports_unavailable_when_too_small(tmp_path):
    header = "종목명,매수시간,수익금,B_등락율\n"
    small = tmp_path / "small.csv"
    small.write_text(header + "종목1,20240304090000,100,1.5\n", encoding="utf-8-sig")
    payload = lp.profile_payload(design_csv=small, holdout_csv=small, min_bucket=50)
    assert payload["available"] is False
    assert payload["reason"] == "sample_too_small"


@pytest.mark.parametrize("bad_index", [0, 9])
def test_edge_single_bucket_still_needs_a_neighbour(bad_index):
    """양끝이라도 1칸만 나쁘면 후보가 아니다 — 규율 2는 예외를 두지 않는다."""
    curve = [200.0] * 10
    curve[bad_index] = -900.0
    profile = lp.profile_variable(
        variable="X", design=_curve(curve), holdout=_curve(curve), min_bucket=50,
    )
    assert profile.worst_span is None
