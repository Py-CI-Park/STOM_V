"""P3 회복 판별 인사이트 — FDR·fold·표본 게이트 계약."""

from __future__ import annotations

import csv
import random
from pathlib import Path

from ai_strategy_loop.autopsy.recovery_insight import (
    FDR_ALPHA,
    bh_fdr,
    insight_payload,
)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = ["종목명", "B_판별변수", "B_잡음변수", "B_상수변수"]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _fixture(tmp_path: Path, n_per_group: int = 60):
    random.seed(42)
    rows: list[dict[str, object]] = []
    labels: dict[int, bool] = {}
    dates: dict[int, int] = {}
    for index in range(n_per_group * 2):
        recovered = index % 2 == 0
        # 판별변수: 회복군이 뚜렷이 높다. 잡음변수: 라벨과 무관. 상수변수: 분산 0.
        rows.append({
            "종목명": f"T{index}",
            "B_판별변수": round((3.0 if recovered else 1.0) + random.gauss(0, 0.3), 4),
            "B_잡음변수": round(random.gauss(0, 1.0), 4),
            "B_상수변수": 7,
        })
        labels[index] = recovered
        dates[index] = 20250401 + (index % 9)  # 9거래일 → 3-fold 가능
    csv_path = tmp_path / "trades.csv"
    _write_csv(csv_path, rows)
    return csv_path, labels, dates


def test_discriminating_variable_passes_fdr_and_folds_noise_does_not(tmp_path: Path) -> None:
    csv_path, labels, dates = _fixture(tmp_path)

    payload = insight_payload(
        csv_path=csv_path, labels_by_row=labels, date_by_row=dates,
        label_name="recovery",
    )

    assert payload["available"] is True
    by_name = {row["feature"]: row for row in payload["top"]}
    strong = by_name["B_판별변수"]
    assert strong["passes_fdr"] is True and strong["q"] <= FDR_ALPHA
    assert strong["fold_consistent"] is True
    assert strong["d"] > 1.0
    noise = by_name.get("B_잡음변수")
    if noise is not None:  # 상위 10에 들었어도 게이트는 통과 못 해야 한다.
        assert noise["passes_fdr"] is False
    # 분산 0 변수는 검정 대상에서 제외된다.
    assert "B_상수변수" not in by_name
    assert payload["guard"].startswith("라벨은 연구 라벨")


def test_small_cohort_returns_unavailable_with_reason(tmp_path: Path) -> None:
    csv_path, labels, dates = _fixture(tmp_path, n_per_group=10)

    payload = insight_payload(
        csv_path=csv_path, labels_by_row=labels, date_by_row=dates,
        label_name="recovery",
    )

    assert payload["available"] is False
    assert payload["reason"] == "cohort_too_small"


def test_bh_fdr_is_monotone_and_bounded() -> None:
    q = bh_fdr([0.001, 0.02, 0.04, 0.9])
    assert all(0.0 <= value <= 1.0 for value in q)
    assert q[0] <= q[1] <= q[2] <= q[3]
    assert q[0] < 0.01
