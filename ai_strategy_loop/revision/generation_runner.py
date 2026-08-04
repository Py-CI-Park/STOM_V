"""세대 러너와 수렴 판정(G-0e) — 언제 멈출지 정한다.

왜 필요한가:
  구조해석 최적화처럼 처음엔 크게 좋아지다가 수렴한다. 개선이 체감했는데 계속 자르면
  표본만 줄고 과최적만 남는다. 그래서 **멈추는 규칙을 코드로 고정**한다.

수렴 판정 3규칙:
  - `converged`        — 홀드아웃 건당 개선이 3세대 연속 ε(기본 50원) 미만
  - `budget_exhausted` — 누적 유지율이 40% 하한 아래
  - `diverged`         — 홀드아웃 건당이 2세대 연속 악화 → **직전 세대로 롤백**

계약:
  - 판정 입력은 **홀드아웃 건당 손익**이다. 총손익은 거래를 줄이기만 해도 좋아진다.
  - 세대 기록은 추가만 하고 고쳐 쓰지 않는다(연구 이력 보존).
  - 이 모듈은 판정만 한다. 백테스트 실행·채택은 각각 대시보드와 사람의 몫이다.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Sequence

from ai_strategy_loop.revision.region_proposer import CUMULATIVE_FLOOR


EPSILON: Final = 50.0          # 홀드아웃 건당 개선이 이보다 작으면 '체감'으로 본다
FLAT_ROUNDS: Final = 3         # 체감이 이만큼 연속되면 수렴
WORSE_ROUNDS: Final = 2        # 악화가 이만큼 연속되면 발산

_STATE_PATH: Final = Path(
    os.environ.get("STOM_GENERATION_LEDGER")
    or Path(__file__).resolve().parents[1] / "state" / "generation_records.jsonl"
)


@dataclass(frozen=True, slots=True)
class GenerationRecord:
    lane: str
    generation: int
    candidate_id: str
    clauses: tuple[str, ...]
    design_per_trade: float
    holdout_per_trade: float
    design_retention: float
    holdout_retention: float
    cumulative_retention: float
    baseline_job_id: str = ""
    candidate_job_id: str = ""
    gate_verdict: str = ""          # adoptable | blocked | ""(미실행)
    note: str = ""


def _delta(records: Sequence[GenerationRecord], index: int) -> float:
    """직전 세대 대비 홀드아웃 건당 개선폭. 1세대는 기준선 대비를 note 로만 남긴다."""
    if index == 0:
        return 0.0
    return records[index].holdout_per_trade - records[index - 1].holdout_per_trade


def verdict(records: Sequence[GenerationRecord]) -> tuple[str, str]:
    """수렴 판정과 한국어 사유. 세대가 없으면 not_started."""
    if not records:
        return "not_started", "아직 세대가 없습니다."
    latest = records[-1]
    if latest.cumulative_retention < CUMULATIVE_FLOOR:
        return "budget_exhausted", (
            f"누적 유지율 {latest.cumulative_retention:.1%} 가 하한 "
            f"{CUMULATIVE_FLOOR:.0%} 아래입니다. 더 자르지 않습니다."
        )
    deltas = [_delta(records, index) for index in range(1, len(records))]
    if len(deltas) >= WORSE_ROUNDS and all(value < 0 for value in deltas[-WORSE_ROUNDS:]):
        return "diverged", (
            f"홀드아웃 건당이 {WORSE_ROUNDS}세대 연속 악화했습니다. "
            f"{records[-WORSE_ROUNDS - 1].generation}세대로 롤백하세요."
        )
    if len(deltas) >= FLAT_ROUNDS and all(
        abs(value) < EPSILON for value in deltas[-FLAT_ROUNDS:]
    ):
        return "converged", (
            f"홀드아웃 건당 개선이 {FLAT_ROUNDS}세대 연속 {EPSILON:,.0f}원 미만입니다. "
            "수렴으로 봅니다."
        )
    return "running", "계속 진행할 수 있습니다."


def rollback_target(records: Sequence[GenerationRecord]) -> int | None:
    """발산했을 때 돌아갈 세대 번호."""
    state, _ = verdict(records)
    if state != "diverged" or len(records) <= WORSE_ROUNDS:
        return None
    return records[-WORSE_ROUNDS - 1].generation


def _path() -> Path:
    return _STATE_PATH


def load(lane: str) -> tuple[GenerationRecord, ...]:
    path = _path()
    if not path.is_file():
        return ()
    out: list[GenerationRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue                     # 손상된 줄은 건너뛴다(이력은 추가 전용)
        if data.get("lane") != lane:
            continue
        data["clauses"] = tuple(data.get("clauses") or ())
        try:
            out.append(GenerationRecord(**data))
        except TypeError:
            continue
    return tuple(sorted(out, key=lambda item: item.generation))


def append(record: GenerationRecord) -> None:
    """세대 기록 추가(추가 전용). 같은 세대를 다시 쓰면 두 줄이 남는다 — 의도다."""
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def history_payload(*, lane: str) -> dict[str, object]:
    records = load(lane)
    state, reason = verdict(records)
    return {
        "available": True,
        "authority": "official",
        "lane": lane,
        "generations": [
            {
                **asdict(record),
                "holdout_delta": _delta(records, index),
            }
            for index, record in enumerate(records)
        ],
        "verdict": state,
        "reason": reason,
        "rollback_to": rollback_target(records),
        "epsilon": EPSILON,
        "cumulative_floor": CUMULATIVE_FLOOR,
        "rule": (
            "홀드아웃 건당 개선 <50원 3세대 연속이면 수렴, 누적 유지율 40% 미만이면 "
            "예산 소진, 2세대 연속 악화면 발산(롤백)"
        ),
    }
