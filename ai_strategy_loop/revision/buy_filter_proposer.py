"""매수 진입 필터 생성기(R2) — 회복 판별 통계에서 얕은 필터 절 1개를 만든다.

설계 근거(과거 실증 승계):
  - QSP3 국면별 일반화 검정: **필터·제거는 표본외 동반 개선, 조임은 설계만 개선**.
    그래서 R2 는 경계 조임이 아니라 '진입 필터 추가' 축을 쓴다.
  - QSP6 전이율 실측: 얕은 선별(37%) > 깊은 조합(9%). 그래서 후보는 **변수 1개**만
    쓰는 단일 절이며, 조합·양측범위는 만들지 않는다.
  - QSP3 건당 엣지 교훈: 거래를 줄이면 총손익은 좋아 보인다. 그래서 임계는
    '기대 진입 유지율'을 실측해 함께 보고하고, 채택 게이트가 건당 엣지를 요구한다.

안전 규율:
  - 변수는 **런타임 표현이 확인된 화이트리스트**만 사용한다(구간연산 변수는 창 인자
    포함). 확인되지 않은 컬럼은 추정하지 않고 skipped 로 남긴다(fail-closed).
  - 라벨(회복/승패)은 근거 선별에만 쓰고 조건식 입력으로 넣지 않는다.
  - 생성 코드는 기준선 대비 **삽입 2줄 외 diff 0**이어야 한다(intent gate).
"""

from __future__ import annotations

import ast
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Iterable, Sequence


ANCHOR: Final = "elif 시분초 < 120000:"
DEFAULT_QUANTILE: Final = 0.25
MIN_EXPECTED_RETENTION: Final = 0.50

# B_* 캡처 컬럼 → 매수식에서 실제로 쓸 수 있는 런타임 표현.
#   구간연산 변수는 공식 avg 창(30)을 명시한다(utility/static.py get_ema/avg 계약).
#   여기 없는 컬럼은 후보로 만들지 않는다 — 문법 추정 금지.
RUNTIME_EXPRESSION: Final[dict[str, str]] = {
    "B_현재가": "현재가",
    "B_등락율": "등락율",
    "B_당일거래대금": "당일거래대금",
    "B_거래대금증감": "거래대금증감",
    "B_체결강도": "체결강도",
    "B_시가총액": "시가총액",
    "B_회전율": "회전율",
    "B_전일동시간비": "전일동시간비",
    "B_매수총잔량": "매수총잔량",
    "B_매도총잔량": "매도총잔량",
    "B_시분초": "시분초",
    "B_분봉시가": "분봉시가",
    "B_분봉고가": "분봉고가",
    "B_분봉저가": "분봉저가",
    "B_시가": "시가",
    "B_고가": "고가",
    "B_저가": "저가",
    "B_전일비": "전일비",
    "B_고저평균대비등락율": "고저평균대비등락율",
    "B_체결강도평균": "체결강도평균(30)",
    "B_등락율각도": "등락율각도(30)",
    "B_당일거래대금각도": "당일거래대금각도(30)",
}
_INTEGER_COLUMNS: Final = frozenset({
    "B_시분초", "B_현재가", "B_시가", "B_고가", "B_저가",
    "B_분봉시가", "B_분봉고가", "B_분봉저가", "B_시가총액",
})
_FORBIDDEN: Final = ("R_", "S_", "F_", "미래", "oracle")


class BuyFilterValidationError(ValueError):
    """생성된 매수 필터가 연구 계약을 위반했다."""


@dataclass(frozen=True, slots=True)
class BuyFilterProposal:
    proposal_id: str
    title: str
    family: str
    timeframe: str
    column: str
    variable: str
    direction: str          # keep_high | keep_low
    threshold: float
    clause: str
    stom_code: str
    intent: str
    evidence: str
    counterevidence: str
    risk: str
    threshold_sources: tuple[str, ...]
    expected_retention: float
    intent_gate: str = "pass"
    authority: str = "advisory"


def _number(value: object) -> float | None:
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def _quantile(values: Sequence[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise BuyFilterValidationError("empty_distribution")
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _round_threshold(column: str, value: float) -> float:
    if column in _INTEGER_COLUMNS:
        return float(int(round(value)))
    if abs(value) >= 1000:
        return float(int(round(value)))
    return round(value, 2)


def derive_buy_code(base_code: str, clause: str) -> str:
    """기준선 매수식의 시간밴드 분기 앞에 필터 절 1개를 삽입한다(계층 보존)."""
    lines = base_code.splitlines()
    try:
        anchor = next(index for index, line in enumerate(lines) if line.strip() == ANCHOR)
    except StopIteration as exc:  # 앵커가 없으면 추정하지 않는다.
        raise BuyFilterValidationError("anchor_not_found") from exc
    indent = " " * (len(lines[anchor]) - len(lines[anchor].lstrip()))
    inserted = [f"{indent}elif not ({clause}):  # ADD_FILTER R2",
                f"{indent}    매수 = False"]
    return "\n".join(lines[:anchor] + inserted + lines[anchor:])


def validate_buy_filter_code(
    *, code: str, base_code: str, clause: str, expected_consts: tuple[float, ...] = (),
) -> None:
    """intent gate — 요청한 필터 절 1개만 정확히 추가됐는지 기계 판정한다."""
    if any(token in clause for token in _FORBIDDEN):
        raise BuyFilterValidationError("future_label_leakage")
    if "매수 = True" not in code or "self.Buy()" not in code:
        raise BuyFilterValidationError("invalid_stom_buy_shape")
    base_lines = base_code.splitlines()
    new_lines = code.splitlines()
    if len(new_lines) != len(base_lines) + 2:
        raise BuyFilterValidationError("unexpected_line_count")
    # 마커 위치 기반 검증 — '매수 = False' 는 기준선에도 있어 집합/정렬 diff 로는
    #   판정이 흔들린다. 삽입 절을 찾아 그 2줄만 제거했을 때 기준선과 동일해야 한다.
    marked = [index for index, line in enumerate(new_lines) if "ADD_FILTER R2" in line]
    if len(marked) != 1:
        raise BuyFilterValidationError("diff_not_single_filter_clause")
    anchor = marked[0]
    if anchor + 1 >= len(new_lines) or new_lines[anchor + 1].strip() != "매수 = False":
        raise BuyFilterValidationError("diff_not_single_filter_clause")
    if not new_lines[anchor].lstrip().startswith("elif not ("):
        raise BuyFilterValidationError("diff_not_single_filter_clause")
    stripped = new_lines[:anchor] + new_lines[anchor + 2:]
    if stripped != base_lines:
        raise BuyFilterValidationError("baseline_body_changed")
    try:
        tree = ast.parse(f"if not ({clause}):\n    pass\n")
    except SyntaxError as exc:
        raise BuyFilterValidationError(f"clause_syntax:{exc}") from exc
    names = {
        node.id for node in ast.walk(tree)
        if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Store)
    }
    allowed = {expr.split("(")[0] for expr in RUNTIME_EXPRESSION.values()}
    unknown = names - allowed
    if unknown:
        raise BuyFilterValidationError(f"unknown_runtime_variable:{sorted(unknown)}")
    if expected_consts:
        consts = {
            abs(round(float(node.value), 4)) for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float))
        }
        missing = [value for value in expected_consts if abs(round(value, 4)) not in consts]
        if missing:
            raise BuyFilterValidationError(f"declared_threshold_missing:{missing}")


def _column_values(csv_path: Path, columns: Iterable[str]) -> dict[str, list[float]]:
    wanted = set(columns)
    collected: dict[str, list[float]] = {name: [] for name in wanted}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            for name in wanted:
                number = _number(row.get(name))
                if number is not None:
                    collected[name].append(number)
    return collected


def propose_buy_filters(
    *, csv_path: Path, stats: Sequence[object], base_code: str, timeframe: str,
    top: int = 6, quantile: float = DEFAULT_QUANTILE,
) -> tuple[tuple[BuyFilterProposal, ...], tuple[dict[str, str], ...]]:
    """FDR 통과·fold 일관 변수만으로 얕은 진입 필터 후보를 만든다.

    반환 (후보들, 제외 사유들) — 제외도 숨기지 않고 함께 돌려준다.
    """
    eligible = [
        stat for stat in stats
        if getattr(stat, "passes_fdr", False) and getattr(stat, "fold_consistent", False)
    ]
    eligible.sort(key=lambda stat: abs(getattr(stat, "d", 0.0)), reverse=True)
    skipped: list[dict[str, str]] = []
    usable = []
    for stat in eligible:
        column = getattr(stat, "feature", "")
        if column not in RUNTIME_EXPRESSION:
            skipped.append({"column": column, "reason": "런타임 표현 미확인 — 추정하지 않음"})
            continue
        usable.append(stat)
        if len(usable) >= top:
            break
    if not usable:
        return (), tuple(skipped)

    values = _column_values(csv_path, [getattr(stat, "feature") for stat in usable])
    proposals: list[BuyFilterProposal] = []
    for stat in usable:
        column = getattr(stat, "feature")
        series = values.get(column) or []
        if len(series) < 100:
            skipped.append({"column": column, "reason": f"표본 부족({len(series)})"})
            continue
        keep_high = getattr(stat, "positive_mean", 0.0) > getattr(stat, "negative_mean", 0.0)
        cut_q = quantile if keep_high else 1.0 - quantile
        threshold = _round_threshold(column, _quantile(series, cut_q))
        kept = (sum(1 for value in series if value >= threshold) if keep_high
                else sum(1 for value in series if value <= threshold))
        retention = round(kept / len(series), 4)
        if retention < MIN_EXPECTED_RETENTION:
            skipped.append({
                "column": column,
                "reason": f"기대 진입 유지율 {retention:.0%} < {MIN_EXPECTED_RETENTION:.0%}",
            })
            continue
        variable = RUNTIME_EXPRESSION[column]
        operator = ">=" if keep_high else "<="
        clause = f"{variable} {operator} {threshold:g}"
        code = derive_buy_code(base_code, clause)
        validate_buy_filter_code(
            code=code, base_code=base_code, clause=clause, expected_consts=(threshold,),
        )
        direction_ko = "높은 쪽만 남김" if keep_high else "낮은 쪽만 남김"
        proposals.append(BuyFilterProposal(
            proposal_id=f"buy_filter_{column[2:]}",
            title=f"{variable} {operator} {threshold:g} 진입 필터",
            family="진입 필터",
            timeframe=timeframe,
            column=column,
            variable=variable,
            direction="keep_high" if keep_high else "keep_low",
            threshold=threshold,
            clause=clause,
            stom_code=code,
            intent=(
                f"회복하지 못한 손실 진입에 몰려 있는 {variable} 구간을 잘라낸다"
                f"({direction_ko})"
            ),
            evidence=(
                f"판별 d={getattr(stat, 'd', 0.0):+.3f} · FDR q={getattr(stat, 'q', 1.0):.4f} · "
                f"fold 일관 · 회복군 평균 {getattr(stat, 'positive_mean', 0.0):,.2f} vs "
                f"비회복군 {getattr(stat, 'negative_mean', 0.0):,.2f} "
                f"(n={getattr(stat, 'n_positive', 0)}/{getattr(stat, 'n_negative', 0)})"
            ),
            counterevidence=(
                "판별력은 회복 라벨 기준이며 수익 개선을 보장하지 않는다 — "
                "잘라낸 구간에 이익 거래도 포함된다"
            ),
            risk=(
                f"설계구간 진입의 약 {1 - retention:.0%}가 사라진다. 총손익이 좋아져도 "
                "건당 엣지가 나빠지면 게이트가 차단한다"
            ),
            threshold_sources=(
                f"{variable} {operator} {threshold:g} ← 전체 진입 분포 p{int(cut_q * 100)} "
                f"(n={len(series)})",
                f"기대 진입 유지율 {retention:.1%} (설계구간 실측)",
            ),
            expected_retention=retention,
        ))
    return tuple(proposals), tuple(skipped)
