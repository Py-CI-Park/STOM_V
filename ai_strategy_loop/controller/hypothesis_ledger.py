"""가설 원장 + 표본 밖 판정 — 자율 루프의 심판 규율 (마스터 웨이브 W2).

배경(감사 결함 #6, QSP13 실측): 루프의 가정 채택/기각이 **같은 설계 구간의
in-sample 델타**로 이뤄지고 있었다. 그러면 세대를 거듭할수록 설계 구간에
과적합되고, 그 과적합이 곧 QSP13 이 측정한 선택 편의(0.6225%p)가 된다.

이 모듈이 세우는 규율 셋:

1. **수정 예산** — 아이디어(run)당 수정 횟수 상한(기본 15). 무한 수정은 그 자체로
   탐색 공간을 키워 편의를 키운다. 예산을 넘기면 그 가설은 폐기하고 기록한다.
2. **표본 밖 판정** — 가정의 채택/기각을 학습 구간이 아니라 **경계 이후 거래**의
   델타로 한다. 경계는 아이디어마다 전진하며 되돌아가지 않는다(홀드아웃 재사용 금지).
3. **편의 차감 판독** — 설계 구간 성적은 항상 0.6225%p 를 뺀 값과 나란히 읽는다.

원장은 append-only JSONL 이다. 기록을 덮어쓰지 않는다 — 폐기된 가설도 남아야
"같은 곳을 또 팠다"를 다음 라운드가 알 수 있다.
"""

from __future__ import annotations

import dataclasses
import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from ai_strategy_loop.autopsy.hypothesis import (
    VERDICT_ACCEPTED,
    VERDICT_INCONCLUSIVE,
    VERDICT_REJECTED,
    Hypothesis,
)

#: 아이디어당 수정 상한 — 넘기면 폐기하고 기록한다(웨이브 W2 헌법 2항).
DEFAULT_REVISION_BUDGET = 15

#: 선택 편의 보정 계수(%p) — QSP13 워크포워드 30폴드 실측.
SELECTION_BIAS_PCT = 0.6225

#: 델타가 이보다 작으면 "움직임 없음"으로 본다(hypothesis._EPS 와 같은 취지).
_EPS = 1e-9

_DEFAULT_PATH = Path(__file__).resolve().parents[1] / "state" / "hypothesis_ledger.jsonl"
_lock = threading.Lock()


class BudgetExhausted(RuntimeError):
    """수정 예산 소진 — 더 고치지 않고 폐기 기록으로 넘긴다."""


@dataclass(frozen=True)
class RevisionRecord:
    """수정 1건 = 가설 1건. 무엇을 왜 바꿨고 표본 밖에서 어땠는가."""

    run_id: str
    revision_no: int
    hypothesis_text: str
    target_metric: str
    expected_direction: int
    basis: str = ""
    verdict: str = "untested"
    observed_delta: Optional[float] = None
    oos_days: int = 0
    boundary: Optional[int] = None
    design_pct: Optional[float] = None
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        payload = dataclasses.asdict(self)
        payload["bias_adjusted_pct"] = bias_adjusted(self.design_pct)
        return payload


def bias_adjusted(design_pct: Optional[float]) -> Optional[float]:
    """설계 구간 성적에서 선택 편의를 뺀 값 — 원값과 함께 읽어야 한다."""
    if design_pct is None:
        return None
    return float(design_pct) - SELECTION_BIAS_PCT


def ledger_path() -> Path:
    raw = os.getenv("STOM_AILOOP_HYPOTHESIS_LEDGER", "").strip()
    return Path(raw) if raw else _DEFAULT_PATH


# ---------------------------------------------------------------------------
# 원장 (append-only)
# ---------------------------------------------------------------------------

def read_ledger(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    target = Path(path) if path else ledger_path()
    if not target.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except ValueError:
            continue          # 손상 줄은 건너뛴다 — 원장 전체를 잃지 않는다.
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def append_record(record: RevisionRecord, path: Optional[Path] = None) -> Dict[str, Any]:
    """원장에 한 줄 추가(append-only). 덮어쓰지 않는다."""
    target = Path(path) if path else ledger_path()
    payload = record.to_dict()
    with _lock:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return payload


def budget_state(
    run_id: str, *, budget: int = DEFAULT_REVISION_BUDGET, path: Optional[Path] = None,
) -> Dict[str, Any]:
    """이 아이디어가 예산을 얼마나 썼는가."""
    used = sum(1 for row in read_ledger(path) if row.get("run_id") == run_id)
    return {
        "run_id": run_id,
        "revisions_used": used,
        "revision_budget": int(budget),
        "budget_remaining": max(0, int(budget) - used),
        "exhausted": used >= int(budget),
        "selection_bias_pct": SELECTION_BIAS_PCT,
    }


def next_revision_no(
    run_id: str, *, budget: int = DEFAULT_REVISION_BUDGET, path: Optional[Path] = None,
) -> int:
    """다음 수정 번호. 예산이 소진됐으면 거부한다(조용히 넘어가지 않는다)."""
    state = budget_state(run_id, budget=budget, path=path)
    if state["exhausted"]:
        raise BudgetExhausted(
            f"수정 예산 소진: {run_id} — {state['revisions_used']}/{state['revision_budget']}회. "
            "이 가설은 폐기하고 기록한다."
        )
    return state["revisions_used"] + 1


# ---------------------------------------------------------------------------
# 표본 밖 판정
# ---------------------------------------------------------------------------

def split_out_of_sample(
    trade_dates: Sequence[int], values: Sequence[float], boundary: int,
) -> Dict[str, Any]:
    """경계(포함하지 않음) 이후 거래만 표본 밖으로 가른다.

    boundary 는 아이디어마다 **전진만** 한다 — 뒤로 물리면 이미 본 구간을
    다시 심판에 쓰는 것이고, 그게 홀드아웃 재사용이다.
    """
    if len(trade_dates) != len(values):
        raise ValueError("trade_dates 와 values 길이가 다르다")
    design: List[float] = []
    oos: List[float] = []
    oos_days: set[int] = set()
    for day, value in zip(trade_dates, values):
        if day is None:
            continue
        if int(day) > int(boundary):
            oos.append(float(value))
            oos_days.add(int(day))
        else:
            design.append(float(value))
    return {
        "boundary": int(boundary),
        "design_n": len(design),
        "oos_n": len(oos),
        "oos_days": len(oos_days),
        "design_mean": (sum(design) / len(design)) if design else None,
        "oos_mean": (sum(oos) / len(oos)) if oos else None,
    }


def adjudicate_out_of_sample(
    hypotheses: Iterable[Hypothesis],
    oos_deltas: Optional[Mapping[str, float]],
    *,
    min_oos_days: int = 20,
    oos_days: int = 0,
) -> List[Hypothesis]:
    """가정을 **표본 밖 델타**로 채택/기각한다.

    in-sample 델타로 판정하던 기존 경로(autopsy.hypothesis.adjudicate)와 같은
    규칙을 쓰되, 입력이 경계 이후 성적이라는 점만 다르다. 표본 밖 일수가
    모자라면 **판정하지 않는다**(inconclusive) — 적은 표본의 우연을 채택으로
    바꾸는 것이 과적합의 출발점이다.

    입력을 변형하지 않고 새 리스트를 반환한다.
    """
    from ai_strategy_loop.autopsy.hypothesis import _METRIC_TO_DELTA_KEY  # noqa: PLC0415

    enough = int(oos_days) >= int(min_oos_days)
    out: List[Hypothesis] = []
    for item in hypotheses:
        observed: Optional[float] = None
        key = _METRIC_TO_DELTA_KEY.get(item.target_metric)
        if enough and oos_deltas is not None and key is not None and key in oos_deltas:
            raw = oos_deltas.get(key)
            if raw is not None:
                observed = float(raw)

        if observed is None:
            verdict = VERDICT_INCONCLUSIVE
        elif abs(observed) < _EPS:
            verdict = VERDICT_INCONCLUSIVE
        elif (observed > 0) == (item.expected_direction > 0):
            verdict = VERDICT_ACCEPTED
        else:
            verdict = VERDICT_REJECTED
        out.append(dataclasses.replace(item, verdict=verdict, observed_delta=observed))
    return out


def record_hypotheses(
    run_id: str,
    hypotheses: Sequence[Hypothesis],
    *,
    design_pct: Optional[float] = None,
    boundary: Optional[int] = None,
    oos_days: int = 0,
    budget: int = DEFAULT_REVISION_BUDGET,
    path: Optional[Path] = None,
    note: str = "",
) -> List[Dict[str, Any]]:
    """판정된 가정들을 원장에 남긴다. 예산 초과면 BudgetExhausted."""
    written: List[Dict[str, Any]] = []
    for item in hypotheses:
        revision_no = next_revision_no(run_id, budget=budget, path=path)
        record = RevisionRecord(
            run_id=run_id,
            revision_no=revision_no,
            hypothesis_text=item.text,
            target_metric=item.target_metric,
            expected_direction=int(item.expected_direction),
            basis=item.basis,
            verdict=item.verdict,
            observed_delta=item.observed_delta,
            oos_days=int(oos_days),
            boundary=boundary,
            design_pct=design_pct,
            note=note,
        )
        written.append(append_record(record, path=path))
    return written


def run_summary(
    run_id: str, *, budget: int = DEFAULT_REVISION_BUDGET, path: Optional[Path] = None,
) -> Dict[str, Any]:
    """아이디어 하나의 원장 요약 — 적중률과 예산을 한 눈에."""
    rows = [row for row in read_ledger(path) if row.get("run_id") == run_id]
    counts: Dict[str, int] = {}
    for row in rows:
        verdict = str(row.get("verdict") or "untested")
        counts[verdict] = counts.get(verdict, 0) + 1
    judged = counts.get(VERDICT_ACCEPTED, 0) + counts.get(VERDICT_REJECTED, 0)
    state = budget_state(run_id, budget=budget, path=path)
    return {
        **state,
        "records": len(rows),
        "verdicts": counts,
        "hit_rate": (counts.get(VERDICT_ACCEPTED, 0) / judged) if judged else None,
        "last_boundary": rows[-1].get("boundary") if rows else None,
    }
