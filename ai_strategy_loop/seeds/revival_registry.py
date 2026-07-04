"""패자부활(revival) 레지스트리 (T1.5) — JSONL append 등재 + 전수 재검증 추출.

`.omo/evidence/tmap-walkforward/rejected_registry.json` 의 수기 규율을 시드
격자용 생산 코드로 정식화한다 (기존 evidence JSON/스크립트는 그대로 둔다 —
이 모듈은 신규 JSONL 경로만 다룬다):

  - **삭제 금지**: 동결-기각 시드는 삭제가 아니라 등재된다 (append-only JSONL).
  - **전수 재검증(선별 없음)**: 신규(미접촉) 데이터가 도착하면, 그 데이터를
    아직 접촉하지 않은 등재자 **전원**이 재검증 대상이다 — 사람/모델의 선별
    개입이 없다. 같은 데이터 재선택 금지와 양립하는 유일한 형태.
  - 등재/추출은 어떤 선택·동결·승격 권한도 갖지 않는다 (연구 레인 전용).

n_trials 정직성: 재검증도 시도(trial)다 — 재검증 실행자는 결과 run 을
n_trials 합산에 포함해야 한다 (이 모듈은 목록만 뽑는다).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Union

REGISTRY_SCHEMA = "seed_revival_registry_v1"

# 전수 재검증 원칙의 기계 판독 표식 (등재 엔트리마다 새겨진다).
REVALIDATION_POLICY = "all_no_selection"

# seed_record 에서 그대로 옮기는 신원 키 (있는 것만 — 유연 스키마).
_SEED_IDENTITY_KEYS = (
    "condition_id", "cell_id", "family", "buy", "sell",
    "buy_sha256", "sell_sha256",
)

# verdict 에서 데이터 창 끝을 찾는 동의 키 (앞선 키 우선).
_DATA_END_KEYS = ("data_end", "data_end_date", "window_end")


def _normalize_date(value: Union[str, int], label: str) -> str:
    """날짜를 'YYYY-MM-DD' 로 정규화한다 (int 20260701 / 'YYYYMMDD' 허용).

    Raises:
        ValueError: 해석 불가 형식 (시스템 경계 검증).
    """
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError(f"{label} 날짜 형식 오류 (YYYY-MM-DD 또는 YYYYMMDD): {value!r}")


def register_rejected(
    seed_record: Mapping[str, Any],
    verdict: Mapping[str, Any],
    registry_path: Union[str, Path],
) -> Dict[str, Any]:
    """기각 시드를 레지스트리(JSONL)에 append 등재하고 엔트리를 돌려준다.

    삭제 금지 원칙: 기존 파일을 덮어쓰지 않고 한 줄을 추가한다. 원본
    ``seed_record``/``verdict`` 는 수정하지 않는다 (불변 — 새 dict 반환).

    Args:
        seed_record: 시드 신원 dict — ``label`` 또는 ``condition_id`` 또는
            (``buy`` + ``sell``) 중 하나 이상 필수. cell_id/family/sha 등은
            있으면 그대로 실린다.
        verdict: 기각 판정 dict — ``rejected_at``/``data_end``(동의 키:
            data_end_date|window_end)/``reject_basis`` 를 읽어 최상위로 올리고,
            원본 전체를 ``verdict`` 키에 보존한다. ``data_end`` 는 기각 판정에
            쓰인 데이터 창의 끝 — 전수 재검증 판단 기준이 된다.
        registry_path: JSONL 경로 (부모 디렉토리는 자동 생성).

    Returns:
        등재된 엔트리 dict (JSON 직렬화 가능, schema 포함).

    Raises:
        ValueError: 신원 부재, 날짜 형식 오류 (시스템 경계 검증).
    """
    if not isinstance(seed_record, Mapping):
        raise ValueError(f"seed_record 는 Mapping 이어야 합니다: {type(seed_record)!r}")
    if not isinstance(verdict, Mapping):
        raise ValueError(f"verdict 는 Mapping 이어야 합니다: {type(verdict)!r}")

    label = seed_record.get("label") or seed_record.get("condition_id")
    if not label and not (seed_record.get("buy") and seed_record.get("sell")):
        raise ValueError(
            "seed_record 신원 부재: label/condition_id 또는 buy+sell 이 필요합니다")

    rejected_at_raw = verdict.get("rejected_at")
    data_end_raw = None
    for key in _DATA_END_KEYS:
        if verdict.get(key) is not None:
            data_end_raw = verdict[key]
            break

    entry: Dict[str, Any] = {
        "schema": REGISTRY_SCHEMA,
        "label": None if label is None else str(label),
    }
    for key in _SEED_IDENTITY_KEYS:
        if seed_record.get(key) is not None:
            entry[key] = seed_record[key]
    entry["rejected_at"] = (
        None if rejected_at_raw is None
        else _normalize_date(rejected_at_raw, "rejected_at"))
    entry["data_end"] = (
        None if data_end_raw is None
        else _normalize_date(data_end_raw, "data_end"))
    entry["reject_basis"] = verdict.get("reject_basis")
    entry["verdict"] = dict(verdict)
    entry["revalidation_policy"] = REVALIDATION_POLICY

    path = Path(registry_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(entry, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return entry


def load_registry(registry_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """레지스트리 JSONL 을 읽어 엔트리 리스트로 돌려준다 (등재 순서 보존).

    파일이 없으면 빈 리스트 — 빈 레지스트리는 정상 상태다.

    Raises:
        ValueError: 줄 단위 JSON 파싱 실패, dict 아님, schema 불일치
            (시스템 경계 검증 — 어느 줄인지 메시지에 포함).
    """
    path = Path(registry_path)
    if not path.exists():
        return []
    entries: List[Dict[str, Any]] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        text = raw.strip()
        if not text:
            continue
        try:
            entry = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{lineno} JSONL 파싱 실패: {exc}") from exc
        if not isinstance(entry, dict):
            raise ValueError(f"{path}:{lineno} 엔트리가 dict 가 아닙니다")
        if entry.get("schema") != REGISTRY_SCHEMA:
            raise ValueError(
                f"{path}:{lineno} schema 불일치: {entry.get('schema')!r}")
        entries.append(entry)
    return entries


def pending_revalidation(
    registry: Iterable[Mapping[str, Any]],
    new_data_end_date: Union[str, int],
) -> List[Dict[str, Any]]:
    """신규 데이터 도착 시 재검증 대상 **전원**을 뽑는다 (선별 없음).

    포함 규칙 (전수 — 자격 판정만 있고 선별은 없다):
      - ``data_end`` < ``new_data_end_date`` 인 엔트리 전부 — 기각 판정이
        접촉하지 않은 새 데이터가 존재한다.
      - ``data_end`` 미기록 엔트리 전부 — 접촉 이력을 모르면 보수적으로 포함.
    제외 규칙: ``data_end`` >= ``new_data_end_date`` — 이미 그 데이터까지
    접촉했으므로 재검증은 같은 데이터 재선택이 된다 (금지).

    Args:
        registry: :func:`load_registry` 산출 엔트리들.
        new_data_end_date: 신규 데이터 창의 끝 ('YYYY-MM-DD'|'YYYYMMDD'|int).

    Returns:
        대상 엔트리의 새 dict 리스트 (원본 불변 — ``pending_reason``/
        ``new_data_end`` 필드가 추가된 사본).

    Raises:
        ValueError: 날짜 형식 오류.
    """
    new_end = _normalize_date(new_data_end_date, "new_data_end_date")
    pending: List[Dict[str, Any]] = []
    for entry in registry:
        data_end: Optional[str] = entry.get("data_end")
        if data_end is None:
            reason = "no_data_end_recorded"
        else:
            data_end = _normalize_date(data_end, "data_end")
            if data_end >= new_end:
                continue  # 이미 접촉한 데이터 — 재선택 금지
            reason = "new_untouched_data_available"
        pending.append({**dict(entry),
                        "pending_reason": reason,
                        "new_data_end": new_end})
    return pending
