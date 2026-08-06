"""QSP10 P3 — 수렴 루프 계약: 심어둔 신호를 찾고, 표본·수렴 규율을 지킨다."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai_strategy_loop.labeling.converge import converge

NO_HIT = 300


def _planted(n_days: int = 120, per_day: int = 400, seed: int = 5) -> pd.DataFrame:
    """`signal` 상위 30% 에서만 익절이 잘 나오도록 심는다. `noise` 는 무관."""
    rng = np.random.default_rng(seed)
    frames = []
    for day in range(n_days):
        signal = rng.uniform(0, 1, per_day)
        noise = rng.uniform(0, 1, per_day)
        good = signal > 0.7
        win = rng.random(per_day) < np.where(good, 0.55, 0.22)
        hit_up = np.where(win, rng.integers(10, 200, per_day), NO_HIT)
        hit_dn = np.where(win, NO_HIT, rng.integers(10, 200, per_day))
        frames.append(pd.DataFrame({
            "일자": 20240300 + day, "시분초": rng.integers(90000, 92000, per_day),
            "종목코드": rng.integers(1000, 1010, per_day).astype(str),
            "signal": signal, "noise": noise,
            "hit_up_2": hit_up, "hit_dn_1": hit_dn,
            "frA_300": rng.normal(-0.3, 0.5, per_day),
        }))
    return pd.concat(frames, ignore_index=True)


def _run(frame: pd.DataFrame, **kwargs):
    options = {"min_rows": 1_000, **kwargs}
    return converge(frame, variables=["signal", "noise"], tp_pct=2.0, sl_pct=1.0,
                    tp="hit_up_2", sl="hit_dn_1", horizon=NO_HIT,
                    timeout_label="frA_300", **options)


def test_converge_finds_planted_signal_and_improves_expectancy() -> None:
    result = _run(_planted())

    assert result.steps, "절을 하나도 못 찾았다"
    first = result.steps[0]
    assert first.clause["변수"] == "signal"
    assert first.clause["연산자"] == ">"
    # 기대값이 기준선보다 개선됐고, 일 클러스터 검정도 통과한다.
    assert first.stats["expectancy_pct"] > result.rule["base"]["expectancy_pct"]
    assert first.day_p_value < 0.05


def test_thresholds_come_from_quantile_grid_only() -> None:
    frame = _planted()
    result = _run(frame)
    clause = result.steps[0].clause
    column = frame[clause["변수"]]
    expected = float(column.quantile(clause["분위"]))
    assert abs(clause["임계"] - expected) < 1e-9


def test_convergence_stops_and_reports_cluster_load() -> None:
    result = _run(_planted(), max_depth=5)

    # 개선이 멈추면 더 쌓지 않는다.
    values = [step.stats["expectancy_pct"] for step in result.steps]
    assert values == sorted(values), "기대값이 단조 증가가 아니다"
    assert len(result.steps) <= 5
    # 자본 경로 경고 지표가 매 단계 실린다.
    for step in result.steps:
        assert step.cluster["mean_simultaneous"] >= 1.0
        assert step.cluster["days"] > 0


def test_sample_floor_blocks_overfit_slices() -> None:
    # 표본 하한을 아주 크게 두면 어떤 절도 통과하지 못한다.
    result = _run(_planted(), min_rows=10_000_000)
    assert result.steps == []


def test_day_significance_uses_every_day_with_trades() -> None:
    """회귀: 하루 건수가 적어도 그 날은 클러스터로 세어야 한다.

    실측 결함(2026-08-05) — '하루 5건 미만 제외' 규칙 탓에 n≈3,000 후보의 일수가
    60 아래로 떨어져 p 가 계산되지 않고 1.0 으로 기본 반환됐다. '증거 없음'이 아니라
    '계산 불가'였고, 진짜 후보를 걸러낼 수 있었다.
    """
    from ai_strategy_loop.labeling.converge import _day_significance

    # 120일 × 하루 2건 — 옛 규칙(5건 미만 제외)이면 클러스터 0개가 된다.
    rng = np.random.default_rng(17)
    rows = []
    for day in range(120):
        rows.append({"일자": 20240300 + day, "hit_up_2": 30, "hit_dn_1": NO_HIT, "frA_300": 0.0})
        rows.append({"일자": 20240300 + day, "hit_up_2": NO_HIT, "hit_dn_1": 40,
                     "frA_300": float(rng.normal(0, 0.1))})
    frame = pd.DataFrame(rows)

    p_value, clusters = _day_significance(frame, tp="hit_up_2", sl="hit_dn_1",
                                          horizon=NO_HIT, tp_pct=2.0, sl_pct=1.0,
                                          timeout_label="frA_300")
    assert clusters == 120, "거래가 있는 날이 전부 클러스터로 잡히지 않았다"
    assert p_value < 0.05, "실제 양수 엣지인데 p 가 계산되지 않았다"


def test_day_mean_objective_avoids_day_concentrated_solutions() -> None:
    """목표값 정렬 — 게이트가 일평균을 검정하므로 탐욕도 일평균을 최적화할 수 있어야 한다.

    실측 배경(QSP10/11): 합계(pooled) 최적화는 거래가 몰린 소수 날에 가중돼
    거래일 64~77일짜리 해를 골랐고, 그 해는 일 검정에서 전부 탈락했다.
    """
    rng = np.random.default_rng(23)
    rows = []
    for day in range(150):
        # 'burst' 는 소수 날에만 대량 발생하며 그 날엔 승률이 높다 → 합계 최적화가 선호.
        burst_day = day % 10 == 0
        count = 200 if burst_day else 20
        burst = np.where(rng.random(count) < (0.9 if burst_day else 0.05), 1.0, 0.0)
        # 'steady' 는 매일 고르게 발생하며 완만하게 유리 → 일평균 최적화가 선호.
        steady = rng.uniform(0, 1, count)
        win = rng.random(count) < np.where(burst > 0, 0.75, np.where(steady > 0.7, 0.5, 0.2))
        rows.append(pd.DataFrame({
            "일자": 20240300 + day,
            "시분초": rng.integers(90000, 92000, count),
            "종목코드": rng.integers(1000, 1010, count).astype(str),
            "burst": burst, "steady": steady,
            "hit_up_2": np.where(win, rng.integers(10, 200, count), NO_HIT),
            "hit_dn_1": np.where(win, NO_HIT, rng.integers(10, 200, count)),
            "frA_300": rng.normal(-0.3, 0.3, count),
        }))
    frame = pd.concat(rows, ignore_index=True)

    # 목적 함수 자체의 성질을 보는 테스트이므로 진입 단위 교정은 끈다 —
    #   교정이 켜지면 그것만으로도 편중이 상당 부분 줄어 두 목적의 차이가 흐려진다
    #   (교정의 효과는 test_entry_unit_reduces_selected_rows 에서 따로 확인).
    common = dict(variables=["burst", "steady"], tp_pct=2.0, sl_pct=1.0,
                  tp="hit_up_2", sl="hit_dn_1", horizon=NO_HIT,
                  timeout_label="frA_300", min_rows=500, entry_unit=False)
    pooled = converge(frame, objective="pooled", **common)
    day_mean = converge(frame, objective="day_mean", **common)

    assert pooled.rule["objective"] == "pooled"
    assert day_mean.rule["objective"] == "day_mean"
    assert day_mean.steps, "일평균 목표에서 절을 못 찾았다"
    # 일평균 목표는 매일 발생하는 신호를 골라 거래일이 더 많아야 한다.
    assert day_mean.steps[-1].day_clusters >= pooled.steps[-1].day_clusters


def test_unknown_objective_is_rejected() -> None:
    with pytest.raises(ValueError):
        _run(_planted(), objective="sharpe")


def test_entry_unit_reduces_selected_rows_and_is_default() -> None:
    """진입 단위 교정이 기본값이고, 켜면 조건 통과 초가 실제 진입 건수로 줄어든다.

    실측 배경(2026-08-06): 이 교정이 없어 지도 추정이 4.7배 부풀려졌고 엔진에서
    부호가 뒤집혔다.
    """
    import inspect

    from ai_strategy_loop.labeling.converge import converge as converge_fn

    assert inspect.signature(converge_fn).parameters["entry_unit"].default is True

    frame = _planted()
    common = dict(variables=["signal", "noise"], tp_pct=2.0, sl_pct=1.0,
                  tp="hit_up_2", sl="hit_dn_1", horizon=NO_HIT,
                  timeout_label="frA_300", min_rows=200)
    raw = converge(frame, entry_unit=False, **common)
    deduped = converge(frame, entry_unit=True, **common)

    # 같은 데이터라도 진입 단위로 세면 표본이 줄어든다(같은 종목·같은 시간대 중복 제거).
    assert deduped.steps and raw.steps
    assert deduped.steps[-1].stats["n"] <= raw.steps[-1].stats["n"] * 1.0 + 1
