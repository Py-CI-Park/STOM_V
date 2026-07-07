"""사전등록 봉인 레지스트리 + 통합 n_trials 원장.

봉인(seal): 결정적 canonical JSON을 파일로 고정하고 sha256으로 무결성을
지킨다. 봉인 이후 내용이 다른 payload로 다시 봉인하려 하면 SealViolation
으로 거부한다 — 임계값·피처 목록·사건 정의 변경은 새 사전등록 파일
(새 n_trials)로만 가능하다.

원장(ledger): P1/P2/P3/P5 탐색 시도 수를 JSONL append-only로 전수 합산한다.
이중 장부 금지 — 모든 탐색은 단일 원장에 정직하게 기록한다.

규율: 현재시각은 호출자가 now 인자로 주입한다(내부 datetime.now() 금지).
파일 입출력은 바이트 단위로 처리해 OS 개행 변환 없이 sha 결정성을 보장한다.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

# v1 프로그램 4태그 + 알파 랩 v2 additive 태그(V2M=채굴 리프, V2F=필터 A/B)
# + 알파 랩 v3 additive 태그(V3M=EV 채굴 리프, V3H=힐클라임 엔진 시행)
# + 알파 랩 v4 additive 태그(V4E=레짐-적응 챔피언 앙상블 엔진 시행).
# 기존 태그 의미는 불변 — v2/v3/v4 확장은 각 preregistration_v{2,3,4}.json
# ledger.tags 봉인값(v3: 50d3d38a — {"path":..., "tags":["V3M","V3H"]};
# v4: 87821aaa... — {"path":..., "tags":["V4E"]}).
ALLOWED_PROGRAMS: frozenset[str] = frozenset(
    {"P1", "P2", "P3", "P5", "V2M", "V2F", "V3M", "V3H", "V4E"}
)


class SealViolation(Exception):
    """봉인 파일 변경 시도 또는 봉인 sha 불일치."""


def canonical_json(payload: dict) -> str:
    """결정적 직렬화: 키 정렬, ensure_ascii=False, separators=(",", ": "), 끝 개행 1개."""
    body = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ": ")
    )
    return body + "\n"


def seal(payload: dict, path) -> str:
    """payload를 canonical JSON으로 path에 봉인하고 sha256 hex를 반환한다.

    파일이 이미 존재하면: 내용이 동일할 때만 sha를 반환하고(멱등),
    다르면 SealViolation을 던진다(봉인 후 변경 거부 — 기존 파일 보존).
    """
    target = Path(path)
    data = canonical_json(payload).encode("utf-8")
    if target.exists():
        existing = target.read_bytes()
        if existing != data:
            raise SealViolation(
                f"봉인 후 변경 거부: 기존 봉인과 내용이 다릅니다 — {target}"
            )
        return hashlib.sha256(existing).hexdigest()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def sha256_of(path) -> str:
    """파일 바이트 전체의 sha256 hex."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_seal(path, expected_sha: str) -> None:
    """파일 sha256이 기대값과 일치하지 않으면 SealViolation."""
    actual = sha256_of(path)
    if actual != expected_sha:
        raise SealViolation(
            f"봉인 불일치: {path} 실제 sha {actual} != 기대 sha {expected_sha}"
        )


def append_trials(
    ledger_path,
    *,
    program: str,
    batch: str,
    n: int,
    now,
    meta: dict | None = None,
) -> None:
    """n_trials 원장(JSONL)에 1줄 append한다 — append 모드 전용(append-only).

    program은 ALLOWED_PROGRAMS({'P1','P2','P3','P5'})만 허용하며 위반 시
    ValueError. now는 호출자가 주입하는 datetime(ts = now.isoformat()).
    """
    if program not in ALLOWED_PROGRAMS:
        raise ValueError(
            f"허용되지 않은 program: {program!r} (허용: {sorted(ALLOWED_PROGRAMS)})"
        )
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ValueError(f"n은 0 이상의 int여야 합니다: {n!r}")
    record = {
        "ts": now.isoformat(),
        "program": program,
        "batch": batch,
        "n": n,
        "meta": meta,
    }
    line = json.dumps(
        record, sort_keys=True, ensure_ascii=False, separators=(",", ": ")
    )
    target = Path(ledger_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "ab") as handle:
        handle.write((line + "\n").encode("utf-8"))


def total_trials(ledger_path, program: str | None = None) -> int:
    """원장의 n 총합을 반환한다. program 지정 시 해당 프로그램만 합산.

    원장 파일이 없으면 0. 알 수 없는 program 필터는 ValueError
    (오타 필터가 조용히 0을 반환해 합산을 오도하는 것을 방지).
    """
    if program is not None and program not in ALLOWED_PROGRAMS:
        raise ValueError(
            f"허용되지 않은 program 필터: {program!r} (허용: {sorted(ALLOWED_PROGRAMS)})"
        )
    target = Path(ledger_path)
    if not target.exists():
        return 0
    total = 0
    with open(target, "r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            record = json.loads(line)
            if program is None or record.get("program") == program:
                total += int(record.get("n", 0))
    return total
