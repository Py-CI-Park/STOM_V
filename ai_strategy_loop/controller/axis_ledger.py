"""변이축 효과 원장 (Axis Effect Ledger) — T3.3.

문제: repair 프롬프트가 매 라운드 같은 축을 다시 건드린다. 예컨대
`turnover_min_902 1.5 -> 3.0`은 이미 부모 대비 profit -524,096 / MDD +6.62p로
악화가 확인되어 수동 금지됐지만, 그 근거가 사람 기억과 문서에만 있다.

해결: 축(mutation axis) 단위 효과를 JSONL append-only 원장에 누적하고,
축별 사전확률(개선확률·평균효과)을 집계해 (1) 프롬프트 주입용 한국어 라인,
(2) 반복 악화 축 자동 금지 목록을 결정론적으로 만들어 낸다.

설계 원칙:
  - 모듈 내 시계 사용 금지. recorded_at 은 호출자가 주입한다(재현성).
  - 같은 원장 파일 → 같은 집계 / 같은 라인 (결정론).
  - 원장은 append-only. 수정/삭제 API를 제공하지 않는다.
  - LLM 호출 없음. 순수 파일 I/O + 산술만 수행한다.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence

AXIS_LEDGER_SCHEMA_VERSION = 1

# 원장 레코드 필수 필드. recorded_at 은 호출자가 주입해야 한다(모듈 내 시계 금지).
REQUIRED_FIELDS: Sequence[str] = (
    "run_id",
    "parent_id",
    "candidate_id",
    "axis",
    "param",
    "from_value",
    "to_value",
    "delta_profit",
    "delta_mdd",
    "delta_trades",
    "delta_win_rate",
    "slippage_profile",
    "window",
    "verdict",
    "recorded_at",
)

# 문자열이어야 하고 비어 있으면 안 되는 필드.
_NON_EMPTY_STR_FIELDS: Sequence[str] = (
    "run_id",
    "parent_id",
    "candidate_id",
    "axis",
    "param",
    "slippage_profile",
    "window",
    "verdict",
    "recorded_at",
)

# 수치(int/float, bool 제외)여야 하는 델타 필드.
_NUMERIC_FIELDS: Sequence[str] = (
    "delta_profit",
    "delta_mdd",
    "delta_trades",
    "delta_win_rate",
)

# 집계 시 축별로 보존하는 최근 판정 수.
LAST_VERDICTS_K = 5

# banned_axes 기본값 — 시도 3회 이상 & 개선확률 20% 이하이면 자동 금지.
DEFAULT_BAN_MIN_N = 3
DEFAULT_BAN_MAX_IMPROVE_RATE = 0.2


def _validate_entry(entry: Mapping[str, Any]) -> List[str]:
    """레코드 위반 사유 목록. 비어 있으면 유효."""
    reasons: List[str] = []
    for field in REQUIRED_FIELDS:
        if field not in entry:
            reasons.append(f"missing_field:{field}")
    for field in _NON_EMPTY_STR_FIELDS:
        value = entry.get(field)
        if field in entry and (not isinstance(value, str) or not value.strip()):
            reasons.append(f"non_empty_string_required:{field}")
    for field in _NUMERIC_FIELDS:
        value = entry.get(field)
        if field in entry and (isinstance(value, bool) or not isinstance(value, (int, float))):
            reasons.append(f"numeric_required:{field}")
    return reasons


class AxisLedger:
    """JSONL append-only 변이축 효과 원장.

    한 레코드 = 부모 대비 단일 축 변이 실험 1건의 효과.
    recorded_at 은 호출자가 주입한다 — 이 모듈은 시계를 쓰지 않는다.
    """

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def record(self, entry: Mapping[str, Any]) -> Dict[str, Any]:
        """레코드 검증 후 원장에 append. 기록된 레코드 사본을 반환.

        위반 시 ValueError — 사유는 '|'로 결합(기존 failure_reason 규약).
        입력 Mapping 은 변형하지 않는다(불변성).
        """
        reasons = _validate_entry(entry)
        if reasons:
            raise ValueError("|".join(reasons))
        stored = {**dict(entry), "schema_version": AXIS_LEDGER_SCHEMA_VERSION}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(stored, ensure_ascii=False, sort_keys=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        return stored

    def iter_entries(
        self, where: Optional[Mapping[str, Any]] = None
    ) -> Iterator[Dict[str, Any]]:
        """원장 레코드를 기록 순서대로 순회. where 는 동등 비교 필터.

        파일이 없으면 빈 순회. 손상된 JSON 라인은 조용히 넘기지 않고
        줄 번호를 담아 ValueError 를 낸다(원장 손상은 시끄럽게).
        """
        if not self._path.exists():
            return
        with self._path.open("r", encoding="utf-8") as handle:
            for line_no, raw in enumerate(handle, start=1):
                text = raw.strip()
                if not text:
                    continue
                try:
                    entry = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"corrupt_ledger_line:{self._path}:{line_no}"
                    ) from exc
                if not isinstance(entry, dict):
                    raise ValueError(
                        f"corrupt_ledger_line:{self._path}:{line_no}"
                    )
                if where and any(entry.get(k) != v for k, v in where.items()):
                    continue
                yield entry

    def aggregate_axis_priors(self) -> Dict[str, Dict[str, Any]]:
        """축별 사전확률 집계 — 개선확률·평균효과.

        반환: {axis: {n, improve_rate, mean_delta_profit, std,
                      mean_delta_mdd, last_verdicts}}
        결정론: 레코드는 파일 순서로 접기(fold), 축 키는 이름순 정렬.
        """
        return aggregate_axis_priors(self.iter_entries())


def aggregate_axis_priors(
    entries: Iterator[Dict[str, Any]] | Sequence[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """레코드 나열 → 축별 사전확률. AxisLedger 밖에서도 재사용 가능."""
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for entry in entries:
        axis = entry.get("axis")
        if not isinstance(axis, str) or not axis:
            continue
        grouped.setdefault(axis, []).append(entry)

    priors: Dict[str, Dict[str, Any]] = {}
    for axis in sorted(grouped):
        rows = grouped[axis]
        profits = [float(r.get("delta_profit", 0.0)) for r in rows]
        mdds = [float(r.get("delta_mdd", 0.0)) for r in rows]
        n = len(rows)
        improves = sum(1 for p in profits if p > 0.0)
        mean_profit = sum(profits) / n
        variance = sum((p - mean_profit) ** 2 for p in profits) / n
        verdicts = [str(r.get("verdict", "")) for r in rows]
        priors[axis] = {
            "n": n,
            "improve_rate": improves / n,
            "mean_delta_profit": mean_profit,
            "std": math.sqrt(variance),
            "mean_delta_mdd": sum(mdds) / n,
            "last_verdicts": verdicts[-LAST_VERDICTS_K:],
        }
    return priors


def _promising_order(item: tuple) -> tuple:
    axis, p = item
    return (-p["improve_rate"], -p["mean_delta_profit"], axis)


def _worsening_order(item: tuple) -> tuple:
    axis, p = item
    return (p["improve_rate"], p["mean_delta_profit"], axis)


def _ban_eligible(p: Mapping[str, Any], min_n: int, max_improve_rate: float) -> bool:
    """banned_axes 와 동일한 금지 적격 판정.

    to_prompt_lines 가 같은 판정을 공유해야 '유망 축' 라벨과 banned_axes
    목록이 같은 priors 에서 서로 모순되지 않는다.
    """
    return int(p["n"]) >= min_n and float(p["improve_rate"]) <= max_improve_rate


def _axis_line(axis: str, p: Mapping[str, Any], tag: str, note: str) -> str:
    return (
        f"- [{tag}] {axis}: 시도 {p['n']}회, 개선확률 {p['improve_rate'] * 100:.0f}%, "
        f"평균 손익효과 {p['mean_delta_profit']:+,.0f}원, "
        f"평균 MDD효과 {p['mean_delta_mdd']:+.2f}p{note}"
    )


def to_prompt_lines(
    priors: Mapping[str, Mapping[str, Any]],
    top_k: int = 3,
    bottom_k: int = 2,
    ban_min_n: int = DEFAULT_BAN_MIN_N,
    ban_max_improve_rate: float = DEFAULT_BAN_MAX_IMPROVE_RATE,
) -> List[str]:
    """repair 프롬프트 주입용 한국어 라인.

    상위 유망 축(top_k) + 반복 악화 축 경고(bottom_k)를 결정론적 순서로.
    banned_axes 적격 축(n >= ban_min_n, 개선확률 <= ban_max_improve_rate)은
    개선확률이 0 보다 커도 '유망 축'으로 라벨하지 않는다 — 같은 priors 의
    금지 목록과 프롬프트 라벨이 모순되면 안 된다. priors 가 비면 빈 목록.
    """
    if not priors:
        return []
    items = [(axis, dict(p)) for axis, p in sorted(priors.items())]
    lines: List[str] = ["## 변이축 사전확률 (원장 기반, 부모 대비 효과)"]

    promising = [
        it for it in sorted(items, key=_promising_order)
        if it[1]["improve_rate"] > 0.0
        and not _ban_eligible(it[1], ban_min_n, ban_max_improve_rate)
    ][: max(top_k, 0)]
    for axis, p in promising:
        lines.append(_axis_line(axis, p, "유망 축", ""))

    promoted = {axis for axis, _ in promising}
    worsening = [
        it for it in sorted(items, key=_worsening_order)
        if it[0] not in promoted and it[1]["improve_rate"] < 0.5 and it[1]["n"] >= 2
    ][: max(bottom_k, 0)]
    for axis, p in worsening:
        recent = ", ".join(p["last_verdicts"]) if p["last_verdicts"] else "없음"
        note = f" — 반복 악화. 이 축 재시도는 지양 (최근 판정: {recent})"
        lines.append(_axis_line(axis, p, "경고 축", note))
    return lines


def banned_axes(
    priors: Mapping[str, Mapping[str, Any]],
    min_n: int = DEFAULT_BAN_MIN_N,
    max_improve_rate: float = DEFAULT_BAN_MAX_IMPROVE_RATE,
) -> List[str]:
    """반복 악화 축 자동 금지 목록 (이름순 정렬, 결정론).

    조건: 시도 횟수 n >= min_n 이고 개선확률 <= max_improve_rate.
    기존 수동 금지 사례(turnover_min_902 1.5 -> 3.0 반복 악화)를
    데이터만으로 재현하는 것이 목적이다.
    """
    return sorted(
        axis
        for axis, p in priors.items()
        if _ban_eligible(p, min_n, max_improve_rate)
    )
