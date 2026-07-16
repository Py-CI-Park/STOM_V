"""wide_seed_trial_planner -- 통합 넓은(wide) 시드 쌍을 위한 결정론적 시행(trial) 계획기 (G004).

이 모듈은 순수 함수/데이터클래스로만 구성되며, 명시적으로 호출되는
``append_ledger_entry`` 를 제외하면 어떠한 I/O 도 수행하지 않는다.
`cli.wide_seed_v1` 의 ``SEED_NAMES`` / ``LEAF_CELLS`` 를 소비하여
정확히 2개(틱 쌍, 분봉 쌍)의 시행 스펙(TrialSpec)을 생성하고,
예산 계약(고유 시행 <= 2, 총 시도 <= 4)을 검증하며,
테스트된 셀(tested cell)에 대한 append-only JSONL 원장(ledger)을 관리한다.

절대 하지 않는 것:
  - 백테스트 실행, 프로덕션 DB 접근, 조건(윈도우 x 캡 x 갭 x 변화가드)의
    카르테시안 곱 전개.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from cli.condition_history_schema import canonical_sha256
from cli.wide_seed_v1 import LEAF_CELLS, SEED_NAMES

# ---------------------------------------------------------------------------
# 예산 계약 상수 -- 임의 변경 금지.
# ---------------------------------------------------------------------------

#: 허용되는 고유(unique) 시행 수의 상한.
MAX_UNIQUE_TRIALS = 2

#: 허용되는 총 시도(attempt, 자동 재시도 포함) 수의 상한.
MAX_ATTEMPTS = 4

#: 시행 1개당 자동 재시도 허용 횟수의 상한.
RETRY_LIMIT_PER_TRIAL = 1

#: 각 레인(lane)이 가져야 하는 리프 셀(leaf cell) 개수.
CELLS_PER_LANE = 12

#: 계획에 포함되는 레인 값(순서 고정: 틱 -> 분봉).
PLAN_LANES: tuple[str, ...] = ("tick", "min")

#: 시행에 부여되는 고정 역할(role) 값.
TRIAL_ROLE = "unified_wide"

#: 시행의 데이터셋 범위(scope) -- 전체 가용 히스토리.
DATASET_SCOPE = "full_available_history"

#: 시행의 결과 역할(result role) -- 탐색적(exploratory) 전체 히스토리 실행.
RESULT_ROLE = "exploratory_full_history"

#: 원장(ledger)에 기록 가능한 이벤트 종류.
LEDGER_EVENTS: tuple[str, ...] = ("planned", "executed", "failed", "skipped")


# ---------------------------------------------------------------------------
# TrialSpecV1
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrialSpecV1:
    """시행(trial) 하나에 대한 불변 스펙.

    ``trial_id`` 는 lane + buy/sell 이름 + 경계(boundary) 영수증 sha 의
    정준 해시로 결정론적으로 계산되며, 동일 입력이면 항상 동일한 값을 갖는다.
    """

    trial_id: str
    lane: str
    buy_name: str
    sell_name: str
    role: str
    cell_metadata: tuple[dict[str, Any], ...]
    dataset_scope: str
    result_role: str


def compute_trial_id(lane: str, buy_name: str, sell_name: str, boundary_sha: str) -> str:
    """lane/이름/경계 영수증 sha 로부터 결정론적 ``trial_id`` 를 계산한다."""

    digest = canonical_sha256(
        {
            "lane": lane,
            "buy_name": buy_name,
            "sell_name": sell_name,
            "boundary_sha": boundary_sha,
        }
    )
    return f"trial_{lane}_{digest[:16]}"


def _cells_for_lane(lane: str) -> tuple[dict[str, Any], ...]:
    """``LEAF_CELLS`` 중 ``lane`` 에 속하는 12개 셀을 ordinal 순으로 반환한다."""

    cells = tuple(
        sorted(
            (cell for cell in LEAF_CELLS if cell["lane"] == lane),
            key=lambda cell: cell["ordinal"],
        )
    )
    if len(cells) != CELLS_PER_LANE:
        raise ValueError(
            f"lane {lane!r} 의 리프 셀 개수가 {CELLS_PER_LANE} 이 아니라 {len(cells)} 입니다."
        )
    return cells


def build_default_plan(boundary_sha: str, exit_sha: str) -> list[TrialSpecV1]:
    """기본 시행 계획을 만든다 -- 항상 정확히 2개(틱 쌍, 분봉 쌍)를 반환한다.

    ``exit_sha`` 는 현재 스펙 생성에 직접 관여하지 않지만, 호출자가 경계와
    종료 프로파일 영수증을 함께 전달하도록 강제하여 계약 완전성을 보장한다.
    """

    if not boundary_sha:
        raise ValueError("boundary_sha 는 비어 있을 수 없습니다.")
    if not exit_sha:
        raise ValueError("exit_sha 는 비어 있을 수 없습니다.")

    specs: list[TrialSpecV1] = []
    for lane in PLAN_LANES:
        buy_name = SEED_NAMES[f"{lane}_buy"]
        sell_name = SEED_NAMES[f"{lane}_sell"]
        trial_id = compute_trial_id(lane, buy_name, sell_name, boundary_sha)
        specs.append(
            TrialSpecV1(
                trial_id=trial_id,
                lane=lane,
                buy_name=buy_name,
                sell_name=sell_name,
                role=TRIAL_ROLE,
                cell_metadata=_cells_for_lane(lane),
                dataset_scope=DATASET_SCOPE,
                result_role=RESULT_ROLE,
            )
        )

    if len(specs) != MAX_UNIQUE_TRIALS:
        raise AssertionError(
            f"기본 계획은 항상 {MAX_UNIQUE_TRIALS}개여야 하는데 {len(specs)}개가 생성되었습니다."
        )
    return specs


# ---------------------------------------------------------------------------
# 계획 검증
# ---------------------------------------------------------------------------


def validate_plan(specs: list[TrialSpecV1]) -> None:
    """시행 계획을 검증한다.

    다음 경우 ``ValueError`` 를 발생시킨다:
      - 고유 시행 수가 ``MAX_UNIQUE_TRIALS`` 를 초과.
      - 중복된 ``trial_id``.
      - 어떤 스펙이라도 ``cell_metadata`` 개수가 ``CELLS_PER_LANE`` 과 다름.
    """

    if len(specs) > MAX_UNIQUE_TRIALS:
        raise ValueError(
            f"고유 시행 수 {len(specs)}개가 상한 {MAX_UNIQUE_TRIALS}개를 초과했습니다."
        )

    trial_ids = [spec.trial_id for spec in specs]
    if len(trial_ids) != len(set(trial_ids)):
        raise ValueError("중복된 trial_id 가 계획에 포함되어 있습니다.")

    for spec in specs:
        if len(spec.cell_metadata) != CELLS_PER_LANE:
            raise ValueError(
                f"trial_id={spec.trial_id!r} 의 cell_metadata 개수가 "
                f"{CELLS_PER_LANE} 이 아니라 {len(spec.cell_metadata)} 입니다."
            )


def assert_no_cartesian(specs: list[TrialSpecV1]) -> None:
    """계획이 윈도우 x 캡 x 갭 x 변화가드의 카르테시안 곱을 전개하지 않았는지 확인한다.

    이 계획기는 오직 unified_wide 쌍(레인당 1개, 최대 2개)만 생성해야 하므로,
    시행 개수가 ``MAX_UNIQUE_TRIALS`` 를 넘으면 카르테시안 전개가 의심된다.
    """

    if len(specs) > MAX_UNIQUE_TRIALS:
        raise ValueError(
            "카르테시안 곱 전개가 의심됩니다: "
            f"시행 개수 {len(specs)}개가 상한 {MAX_UNIQUE_TRIALS}개를 초과했습니다."
        )


# ---------------------------------------------------------------------------
# TestedCellLedgerV1 -- append-only JSONL 원장
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TestedCellLedgerV1:
    """원장(ledger)에 기록되는 항목 1건.

    ``timestamp`` 를 지정하지 않으면 ``append_ledger_entry`` 가 UTC 현재
    시각(ISO-8601)을 채운다.
    """

    event: str
    trial_id: str
    spec_hash: str
    timestamp: Optional[str] = None
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """JSONL 한 줄에 대응하는 평범한 dict 로 변환한다."""

        return {
            "event": self.event,
            "trial_id": self.trial_id,
            "spec_hash": self.spec_hash,
            "timestamp": self.timestamp,
            "detail": dict(self.detail),
        }


def append_ledger_entry(path: Path | str, entry: TestedCellLedgerV1 | dict[str, Any]) -> dict[str, Any]:
    """원장 파일(``path``, JSONL)에 항목 1건을 추가(append)한다.

    ``entry`` 는 ``TestedCellLedgerV1`` 인스턴스이거나 최소한
    ``event``/``trial_id``/``spec_hash`` 키를 가진 dict 여야 한다.
    ``timestamp`` 가 없으면 UTC ISO-8601 현재 시각을 채운다.
    기록된(정규화된) dict 를 반환한다.
    """

    record: dict[str, Any]
    if isinstance(entry, TestedCellLedgerV1):
        record = entry.to_dict()
    else:
        record = dict(entry)

    for required_key in ("event", "trial_id", "spec_hash"):
        if required_key not in record:
            raise ValueError(f"원장 항목에 필수 키 {required_key!r} 가 없습니다.")

    if record["event"] not in LEDGER_EVENTS:
        raise ValueError(f"알 수 없는 원장 이벤트 {record['event']!r} 입니다.")

    if not record.get("timestamp"):
        record["timestamp"] = datetime.now(timezone.utc).isoformat()

    record.setdefault("detail", {})

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
        fh.write("\n")

    return record


def read_ledger(path: Path | str) -> list[dict[str, Any]]:
    """원장 파일(``path``)의 모든 JSONL 항목을 순서대로 읽어 반환한다.

    파일이 존재하지 않으면 빈 리스트를 반환한다.
    """

    target = Path(path)
    if not target.exists():
        return []

    entries: list[dict[str, Any]] = []
    with target.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
    return entries
