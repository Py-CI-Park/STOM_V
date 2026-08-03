"""회복 판별 인사이트(P3) — 무엇이 회복군과 비회복군을 가르는지 기계 탐색.

계약:
  - 라벨은 연구 라벨이다(회복 = 매도 후 경계 전 비용 후 손익 ≥0 관측).
    조건식 입력으로 누출하지 않으며, 근거 제시(변수 선별)에만 쓴다.
  - 통계 게이트: 그룹 표본 각 ≥ MIN_GROUP, BH-FDR q ≤ 0.10 통과분만 노출 표시.
  - fold 일관성: 날짜 3분할에서 효과 부호가 전부 같아야 True — 우연 구분력 방어.
  - 변수 풀은 공식 CSV 의 B_* 열(존재·분산>0) — 사후 정보(R_*/S_*)는 넣지 않는다.
"""

from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass
from pathlib import Path


MIN_GROUP = 30
FDR_ALPHA = 0.10
_FOLDS = 3


@dataclass(frozen=True, slots=True)
class VariableStat:
    feature: str
    d: float                 # Cohen's d (양성군 - 음성군)
    p: float                 # Welch t 양측 p
    q: float                 # BH-FDR 보정 q
    passes_fdr: bool
    fold_consistent: bool    # 날짜 3분할 부호 일관
    n_positive: int
    n_negative: int
    positive_mean: float
    negative_mean: float


def bh_fdr(pvalues: list[float]) -> list[float]:
    """Benjamini-Hochberg q-values (단조 보정 포함)."""
    m = len(pvalues)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda index: pvalues[index])
    q = [0.0] * m
    minimum = 1.0
    for rank_from_end, index in enumerate(reversed(order)):
        rank = m - rank_from_end
        value = min(1.0, pvalues[index] * m / rank)
        minimum = min(minimum, value)
        q[index] = minimum
    return q


def cohen_d(positive: list[float], negative: list[float]) -> float:
    n1, n2 = len(positive), len(negative)
    mean1 = sum(positive) / n1
    mean2 = sum(negative) / n2
    var1 = sum((x - mean1) ** 2 for x in positive) / max(1, n1 - 1)
    var2 = sum((x - mean2) ** 2 for x in negative) / max(1, n2 - 1)
    pooled = ((n1 - 1) * var1 + (n2 - 1) * var2) / max(1, n1 + n2 - 2)
    if pooled <= 0:
        return 0.0
    return (mean1 - mean2) / math.sqrt(pooled)


def welch_p(positive: list[float], negative: list[float]) -> float:
    """Welch t 양측 p — 정규 근사(표본 게이트 ≥30 전제라 충분)."""
    n1, n2 = len(positive), len(negative)
    mean1 = sum(positive) / n1
    mean2 = sum(negative) / n2
    var1 = sum((x - mean1) ** 2 for x in positive) / max(1, n1 - 1)
    var2 = sum((x - mean2) ** 2 for x in negative) / max(1, n2 - 1)
    se = math.sqrt(var1 / n1 + var2 / n2)
    if se == 0:
        return 1.0
    z = abs(mean1 - mean2) / se
    # 표준정규 생존함수 2배(erfc 기반) — SciPy 의존 없이 결정적.
    return max(0.0, min(1.0, math.erfc(z / math.sqrt(2))))


def _fold_consistent(
    dates: list[int], values: list[float], labels: list[bool],
) -> bool:
    unique_dates = sorted(set(dates))
    if len(unique_dates) < _FOLDS:
        return False
    chunk = max(1, len(unique_dates) // _FOLDS)
    boundaries = [set(unique_dates[i * chunk:(i + 1) * chunk if i < _FOLDS - 1 else None])
                  for i in range(_FOLDS)]
    signs: list[int] = []
    for fold_dates in boundaries:
        positive = [v for v, lab, dt in zip(values, labels, dates) if lab and dt in fold_dates]
        negative = [v for v, lab, dt in zip(values, labels, dates) if not lab and dt in fold_dates]
        if len(positive) < 5 or len(negative) < 5:
            return False
        difference = (sum(positive) / len(positive)) - (sum(negative) / len(negative))
        signs.append(1 if difference > 0 else (-1 if difference < 0 else 0))
    return len(set(signs)) == 1 and signs[0] != 0


def _number(value: str | None) -> float | None:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def variable_stats(
    *, csv_path: Path, labels_by_row: dict[int, bool], date_by_row: dict[int, int],
) -> tuple[VariableStat, ...]:
    """공식 CSV 의 B_* 열 × 라벨 → 판별 통계 전수(FDR 은 전체 검정에 대해 보정)."""
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        b_columns = [name for name in (reader.fieldnames or ()) if name.startswith("B_")]
        rows = list(reader)
    candidates: list[tuple[str, list[float], list[float], list[float], list[bool], list[int]]] = []
    for column in b_columns:
        positive: list[float] = []
        negative: list[float] = []
        values: list[float] = []
        labels: list[bool] = []
        dates: list[int] = []
        for row_id, row in enumerate(rows):
            label = labels_by_row.get(row_id)
            if label is None:
                continue
            number = _number(row.get(column))
            if number is None:
                continue
            (positive if label else negative).append(number)
            values.append(number)
            labels.append(label)
            dates.append(date_by_row.get(row_id, 0))
        if len(positive) < MIN_GROUP or len(negative) < MIN_GROUP:
            continue
        if len(set(positive + negative)) <= 1:
            continue  # zero-variance
        candidates.append((column, positive, negative, values, labels, dates))
    pvalues = [welch_p(positive, negative) for _, positive, negative, *_ in candidates]
    qvalues = bh_fdr(pvalues)
    stats = [
        VariableStat(
            feature=column,
            d=round(cohen_d(positive, negative), 4),
            p=round(p, 6),
            q=round(q, 6),
            passes_fdr=q <= FDR_ALPHA,
            fold_consistent=_fold_consistent(dates, values, labels),
            n_positive=len(positive),
            n_negative=len(negative),
            positive_mean=round(sum(positive) / len(positive), 4),
            negative_mean=round(sum(negative) / len(negative), 4),
        )
        for (column, positive, negative, values, labels, dates), p, q
        in zip(candidates, pvalues, qvalues)
    ]
    return tuple(sorted(stats, key=lambda item: abs(item.d), reverse=True))


def insight_payload(
    *, csv_path: Path, labels_by_row: dict[int, bool], date_by_row: dict[int, int],
    label_name: str, top: int = 10,
) -> dict[str, object]:
    positive_total = sum(1 for value in labels_by_row.values() if value)
    negative_total = len(labels_by_row) - positive_total
    if positive_total < MIN_GROUP or negative_total < MIN_GROUP:
        return {
            "available": False,
            "authority": "diagnostic",
            "reason": "cohort_too_small",
            "label": label_name,
            "n_positive": positive_total,
            "n_negative": negative_total,
            "min_group": MIN_GROUP,
        }
    stats = variable_stats(
        csv_path=csv_path, labels_by_row=labels_by_row, date_by_row=date_by_row,
    )
    return {
        "available": True,
        "authority": "diagnostic",
        "label": label_name,
        "n_positive": positive_total,
        "n_negative": negative_total,
        "fdr_alpha": FDR_ALPHA,
        "tested": len(stats),
        "top": [asdict(item) for item in stats[:top]],
        "passing_count": sum(1 for item in stats if item.passes_fdr),
        "guard": "라벨은 연구 라벨이며 조건식 입력으로 사용하지 않습니다.",
    }
