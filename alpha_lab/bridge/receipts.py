"""alpha_lab 등록 provenance 영수증 원장 (JSONL append-only).

전략 DB에 등록된 각 조건식의 출처를 결정론적으로 남긴다:
{name, source: {kind: 'leaf'|'event_cell', payload}, prereg_sha,
 n_trials_context, created_at}

- 'leaf'는 P1 규칙채굴 트리 잎, 'event_cell'은 P2 이벤트 스터디 셀 출처.
- prereg_sha: 봉인된 사전등록(preregistration_v1.json)의 sha256 — 등록 시점의
  사전등록 버전을 못박는다.
- n_trials_context: 등록 시점까지의 통합 n_trials 원장 총합(다중검정 맥락).
- created_at은 호출자가 주입한 now에서만 유도한다(내부 datetime.now() 금지).
  레코드에 created_at이 미리 들어있으면 이중 출처 방지를 위해 거부한다.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from alpha_lab.bridge.registrar import NAME_PREFIX

logger = logging.getLogger(__name__)

ALLOWED_SOURCE_KINDS: frozenset = frozenset({"leaf", "event_cell"})
_REQUIRED_KEYS: tuple = ("name", "source", "prereg_sha", "n_trials_context")


def _validate_record(record: dict) -> None:
    """영수증 레코드 스키마 검증 — 위반 시 ValueError (파일 접근 전)."""
    if not isinstance(record, dict):
        raise ValueError("record는 dict여야 합니다: %r" % (record,))
    for key in _REQUIRED_KEYS:
        if key not in record:
            raise ValueError("영수증 필수 키 누락: %r" % key)
    if "created_at" in record:
        raise ValueError("created_at은 now 인자에서만 유도합니다(사전 지정 거부)")
    name = record["name"]
    if not isinstance(name, str) or not name.startswith(NAME_PREFIX):
        raise ValueError("영수증 name은 %r 접두가 강제됩니다: %r" % (NAME_PREFIX, name))
    source = record["source"]
    if not isinstance(source, dict) or "payload" not in source:
        raise ValueError("source는 {kind, payload} dict여야 합니다: %r" % (source,))
    if source.get("kind") not in ALLOWED_SOURCE_KINDS:
        raise ValueError(
            "source.kind는 %s만 허용: %r"
            % (sorted(ALLOWED_SOURCE_KINDS), source.get("kind"))
        )
    if not isinstance(record["prereg_sha"], str) or not record["prereg_sha"]:
        raise ValueError("prereg_sha는 비어있지 않은 str: %r" % (record["prereg_sha"],))
    n_ctx = record["n_trials_context"]
    if isinstance(n_ctx, bool) or not isinstance(n_ctx, int) or n_ctx < 0:
        raise ValueError("n_trials_context는 0 이상의 int: %r" % (n_ctx,))


def append_receipt(path, record: dict, *, now) -> dict:
    """영수증 1건을 JSONL로 append하고, 기록된(불변 확장) 레코드를 반환한다.

    입력 record는 변형하지 않는다(불변) — created_at을 덧붙인 새 dict를 쓴다.
    """
    _validate_record(record)
    written = {**record, "created_at": now.isoformat()}
    line = json.dumps(
        written, sort_keys=True, ensure_ascii=False, separators=(",", ": ")
    )
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "ab") as handle:
        handle.write((line + "\n").encode("utf-8"))
    logger.info("append_receipt path=%s name=%s", target, written["name"])
    return written


def read_receipts(path) -> list:
    """영수증 원장을 기록 순서대로 list[dict]로 읽는다. 파일 없으면 []."""
    target = Path(path)
    if not target.exists():
        return []
    records: list = []
    with open(target, "r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if line:
                records.append(json.loads(line))
    return records
