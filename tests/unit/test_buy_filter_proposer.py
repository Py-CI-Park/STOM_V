"""R2-2 매수 진입 필터 생성기 — 얕은 단일 절·분위수 근거·intent gate 계약."""

from __future__ import annotations

import csv
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_strategy_loop.revision.buy_filter_proposer import (
    BuyFilterValidationError,
    derive_buy_code,
    propose_buy_filters,
    validate_buy_filter_code,
)


BASE = """# 분봉 기반 변수 정의
전일종가추정 = 현재가 / (1 + (등락율 / 100))

매수 = True

if not (0 < 현재가 <= 50000):
    매수 = False
elif 시분초 < 120000:
    if 시가총액 < 100000:
        if not (1.0 < 등락율 <= 20.0):
            매수 = False

if 매수:
    self.Buy()
"""


def _stat(feature: str, d: float, positive: float, negative: float,
          passes: bool = True, fold: bool = True):
    return SimpleNamespace(
        feature=feature, d=d, p=0.0001, q=0.001, passes_fdr=passes,
        fold_consistent=fold, n_positive=168, n_negative=3615,
        positive_mean=positive, negative_mean=negative,
    )


def _csv(path: Path, rows: int = 400) -> Path:
    fields = ["B_회전율", "B_등락율각도", "B_미지원변수"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in range(rows):
            writer.writerow({
                "B_회전율": round(index * 0.1, 2),        # 0.0 ~ 39.9
                "B_등락율각도": round(index * 0.05, 2),    # 0.0 ~ 19.95
                "B_미지원변수": index,
            })
    return path


def test_filter_keeps_high_side_when_recovered_group_is_higher(tmp_path: Path) -> None:
    csv_path = _csv(tmp_path / "trades.csv")
    stats = [_stat("B_회전율", 0.534, 37.1, 23.6)]

    proposals, skipped = propose_buy_filters(
        csv_path=csv_path, stats=stats, base_code=BASE, timeframe="min",
    )

    assert len(proposals) == 1 and skipped == ()
    row = proposals[0]
    assert row.direction == "keep_high"
    assert row.variable == "회전율"
    assert ">=" in row.clause
    # p25 컷이므로 유지율이 약 75% 여야 한다.
    assert 0.70 <= row.expected_retention <= 0.80
    assert row.intent_gate == "pass"
    assert any("p25" in source for source in row.threshold_sources)
    assert "ADD_FILTER R2" in row.stom_code


def test_filter_keeps_low_side_and_uses_window_argument_for_angle(tmp_path: Path) -> None:
    csv_path = _csv(tmp_path / "trades.csv")
    stats = [_stat("B_등락율각도", -0.450, 4.74, 14.38)]

    proposals, _ = propose_buy_filters(
        csv_path=csv_path, stats=stats, base_code=BASE, timeframe="min",
    )

    row = proposals[0]
    assert row.direction == "keep_low"
    # 구간연산 변수는 창 인자 없이 쓰면 런타임 오류 — 창(30)이 반드시 붙어야 한다.
    assert row.variable == "등락율각도(30)"
    assert "등락율각도(30) <=" in row.clause


def test_unmapped_columns_are_skipped_not_guessed(tmp_path: Path) -> None:
    csv_path = _csv(tmp_path / "trades.csv")
    stats = [_stat("B_미지원변수", 0.9, 10.0, 1.0)]

    proposals, skipped = propose_buy_filters(
        csv_path=csv_path, stats=stats, base_code=BASE, timeframe="min",
    )

    assert proposals == ()
    assert skipped and skipped[0]["column"] == "B_미지원변수"
    assert "추정하지 않음" in skipped[0]["reason"]


def test_statistically_weak_variables_never_become_candidates(tmp_path: Path) -> None:
    csv_path = _csv(tmp_path / "trades.csv")
    stats = [
        _stat("B_회전율", 0.9, 30.0, 10.0, passes=False),          # FDR 미통과
        _stat("B_등락율각도", 0.8, 30.0, 10.0, fold=False),         # fold 혼재
    ]

    proposals, _ = propose_buy_filters(
        csv_path=csv_path, stats=stats, base_code=BASE, timeframe="min",
    )

    assert proposals == ()


def test_intent_gate_rejects_any_edit_beyond_the_single_filter_clause() -> None:
    good = derive_buy_code(BASE, "회전율 >= 10")
    validate_buy_filter_code(code=good, base_code=BASE, clause="회전율 >= 10",
                             expected_consts=(10.0,))

    # 본문을 함께 고치면 골격 불변 위반.
    tampered = good.replace("0 < 현재가 <= 50000", "0 < 현재가 <= 90000")
    with pytest.raises(BuyFilterValidationError):
        validate_buy_filter_code(code=tampered, base_code=BASE, clause="회전율 >= 10")

    # 화이트리스트 밖 변수는 차단.
    with pytest.raises(BuyFilterValidationError, match="unknown_runtime_variable"):
        validate_buy_filter_code(
            code=derive_buy_code(BASE, "미확인변수 >= 10"), base_code=BASE,
            clause="미확인변수 >= 10",
        )

    # 선언 임계값이 코드에 없으면 차단.
    with pytest.raises(BuyFilterValidationError, match="declared_threshold_missing"):
        validate_buy_filter_code(code=good, base_code=BASE, clause="회전율 >= 10",
                                 expected_consts=(99.0,))


def test_anchor_missing_is_reported_instead_of_guessing() -> None:
    with pytest.raises(BuyFilterValidationError, match="anchor_not_found"):
        derive_buy_code("매수 = True\nif 매수:\n    self.Buy()\n", "회전율 >= 10")
