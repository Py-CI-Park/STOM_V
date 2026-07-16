"""stage0_inventory -- Stage-0 재고(inventory) 영수증 빌더 (G004).

이 모듈은 읽기 전용(read-only)이다. 어떤 DB에도 쓰지 않고, 스캔 대상 파일을
수정하지 않는다. 틱/분봉 DB 디렉터리를 파일명 기준(기본값)으로만 훑어
`stage0-inventory-receipt` 딕셔너리를 결정론적으로 구성한다.

- `scan_tick_dbs`는 기본적으로 sqlite를 열지 않는다 (파일명/크기만 사용).
- `scan_min_db`는 `sample_limit > 0`일 때만 READ-ONLY URI(`mode=ro`)로 sqlite를
  열어 테이블 개수를 `sample_limit` 이내로 표본 조사한다.
- `write_receipt`는 임시 파일 + `os.replace` 원자적 교체를 사용하며,
  경로에 `_database` 세그먼트가 포함되면 즉시 거부한다.

이 모듈은 `cli.condition_history_schema.canonical_sha256`만 소비한다
(계약: `cli.wide_seed_trial_planner`가 만드는 시드/계획 산출물과는 독립적).
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cli.condition_history_schema import canonical_sha256

#: `stock_tick_YYYYMMDD.db` 파일명 패턴 -- 거래일자는 파일명에서만 추출한다.
_TICK_DB_NAME_RE = re.compile(r"^stock_tick_(\d{8})\.db$")

#: 쓰기를 거부할 보호된 런타임 경로 세그먼트.
_FORBIDDEN_PATH_SEGMENTS = ("_database",)


def scan_tick_dbs(db_dir: Path) -> dict:
    """`db_dir` 아래 `stock_tick_*.db` 파일명을 훑어 재고 요약을 반환한다.

    sqlite 파일을 열지 않는다 (기본 동작). 파일명에서 `YYYYMMDD` 거래일자를
    추출하고, 존재하는 파일들의 크기(bytes)만 `os.path.getsize`로 조회한다.

    Args:
        db_dir: 틱 DB 디렉터리 경로. 존재하지 않으면 빈 재고를 반환한다.

    Returns:
        ``{"dates": [...], "count": int, "bytes": int,
        "min": str | None, "max": str | None}``. ``dates``는 오름차순
        정렬된 ``YYYYMMDD`` 문자열 리스트.
    """
    db_dir = Path(db_dir)
    entries: list[tuple[str, int]] = []
    if db_dir.is_dir():
        for path in db_dir.glob("stock_tick_*.db"):
            match = _TICK_DB_NAME_RE.match(path.name)
            if not match:
                continue
            date_str = match.group(1)
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            entries.append((date_str, size))

    entries.sort(key=lambda item: item[0])
    dates = [date_str for date_str, _ in entries]
    total_bytes = sum(size for _, size in entries)
    return {
        "dates": dates,
        "count": len(dates),
        "bytes": total_bytes,
        "min": dates[0] if dates else None,
        "max": dates[-1] if dates else None,
    }


def scan_min_db(db_path: Path, sample_limit: int = 0) -> dict:
    """분봉(min) DB 단일 파일의 존재/크기 재고를 반환한다.

    ``sample_limit <= 0``이면 파일 메타데이터만 조회하고 sqlite를 절대 열지
    않는다. ``sample_limit > 0``이면 READ-ONLY URI(``file:...?mode=ro``)로만
    연결하여 ``sqlite_master``에서 테이블 이름을 최대 ``sample_limit``개까지
    표본 조사한다 (쓰기 연결은 만들지 않는다).

    Args:
        db_path: 분봉 DB 파일 경로.
        sample_limit: 0이면 메타데이터만, 양수면 테이블 표본 개수 상한.

    Returns:
        ``{"exists": bool, "bytes": int, "tables_sampled": int | None}``.
        ``tables_sampled``은 ``sample_limit <= 0``일 때 ``None``.
    """
    db_path = Path(db_path)
    exists = db_path.is_file()
    size = 0
    if exists:
        try:
            size = db_path.stat().st_size
        except OSError:
            size = 0

    tables_sampled: Optional[int] = None
    if exists and sample_limit > 0:
        uri = f"file:{db_path.as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' LIMIT ?",
                (sample_limit,),
            )
            tables_sampled = len(cursor.fetchall())
        finally:
            conn.close()

    return {
        "exists": exists,
        "bytes": size,
        "tables_sampled": tables_sampled,
    }


def build_stage0_receipt(
    tick_dir: Path,
    min_db: Path,
    boundary_sha: str,
    exit_sha: str,
    plan_hashes: list[str],
    *,
    sample_limit: int = 0,
    generated_at: Optional[str] = None,
    min_coverage: Optional[dict] = None,
    notes: Optional[dict] = None,
) -> dict:
    """Stage-0 재고 영수증을 결정론적으로 구성한다.

    ``tick_dir``와 ``min_db``를 각각 `scan_tick_dbs`/`scan_min_db`로 훑고,
    커버리지를 비교하여 ``non_common_history`` 플래그를 계산한 뒤 전체
    페이로드의 정준 sha256(``receipt_sha`` 필드 제외)을 부여한다.

    Args:
        tick_dir: 틱 DB 디렉터리.
        min_db: 분봉 DB 파일 경로.
        boundary_sha: `SeedBoundaryIntentReceiptV1.sha256` 등 경계 의도 영수증 해시.
        exit_sha: `ExitProfileReceiptV1.sha256` 등 종료 프로파일 영수증 해시.
        plan_hashes: TrialSpec 계획 해시 목록 (순서는 입력 그대로 보존).
        sample_limit: `scan_min_db`에 전달할 표본 상한 (기본 0 = sqlite 미개방).
        generated_at: 영수증 타임스탬프. ``None``이면 호출 시각(UTC, ISO-8601)을
            사용한다. 결정론적 테스트에서는 고정 문자열을 명시적으로 전달한다.
        min_coverage: 분봉 레인의 실제 커버리지 선언 ``{"min": "YYYYMMDD",
            "max": "YYYYMMDD", "source": "<근거 문서/스캔>"}``. 파일 메타데이터만으로
            분봉 날짜범위를 추출할 수 없으므로 호출자가 명시 선언하면 영수증의
            ``lanes.min.coverage``에 그대로 기록되고, 틱 레인 범위와 비교해
            ``non_common_history``를 정직하게 계산한다.
        notes: 영수증에 남길 추가 메모 딕셔너리(예: data_root_note). 생성기가
            직접 emit하므로 영수증은 항상 이 함수만으로 재현 가능하다.

    Returns:
        `schemaVersion`, `kind`, `lanes`, `non_common_history`,
        `boundary_receipt_sha`, `exit_receipt_sha`, `trial_plan_hashes`,
        `generatedAt`, `receipt_sha` 키를 가진 딕셔너리.
    """
    tick_lane = scan_tick_dbs(tick_dir)
    min_lane = scan_min_db(min_db, sample_limit=sample_limit)
    if min_coverage is not None:
        min_lane = dict(min_lane)
        min_lane["coverage"] = dict(min_coverage)

    # 커버리지 비교: 한쪽 레인이 비었으면 공통 히스토리를 확인할 수 없어 True.
    # 양쪽 범위를 모두 알 때는 시작/끝 일자가 정확히 일치할 때만 공통으로 본다.
    non_common_history = tick_lane["count"] == 0 or not min_lane["exists"]
    if not non_common_history and min_coverage is not None:
        non_common_history = (
            str(min_coverage.get("min")) != str(tick_lane.get("min"))
            or str(min_coverage.get("max")) != str(tick_lane.get("max"))
        )

    if generated_at is None:
        generated_at = datetime.now(timezone.utc).isoformat()

    payload = {
        "schemaVersion": 1,
        "kind": "stage0-inventory-receipt",
        "lanes": {
            "tick": tick_lane,
            "min": min_lane,
        },
        "non_common_history": non_common_history,
        "boundary_receipt_sha": boundary_sha,
        "exit_receipt_sha": exit_sha,
        "trial_plan_hashes": list(plan_hashes),
        "generatedAt": generated_at,
    }
    if notes:
        payload["notes"] = dict(notes)
    payload["receipt_sha"] = canonical_sha256(payload)
    return payload


def _reject_forbidden_receipt_path(out_path: Path) -> None:
    """`_database` 세그먼트를 포함한 경로로의 영수증 기록을 거부한다."""
    parts = {part.lower() for part in out_path.parts}
    for forbidden in _FORBIDDEN_PATH_SEGMENTS:
        if forbidden.lower() in parts:
            raise ValueError(
                f"refusing to write stage0 receipt under protected runtime path segment: {forbidden!r}"
            )


def write_receipt(receipt: dict, out_path: Path) -> Path:
    """`receipt` 딕셔너리를 `out_path`에 원자적으로 기록한다.

    임시 파일에 먼저 쓰고 `os.replace`로 교체하므로, 쓰기 도중 실패해도
    최종 경로에는 이전 상태(또는 무존재) 외의 부분 파일이 남지 않는다.
    `out_path`에 `_database` 세그먼트가 포함되면 기록 전에 즉시 예외를 낸다.

    Args:
        receipt: `build_stage0_receipt`가 만든 딕셔너리 (또는 호환 dict).
        out_path: 기록할 대상 JSON 파일 경로.

    Returns:
        기록된 파일의 `Path`.

    Raises:
        ValueError: `out_path`가 보호된 런타임 경로(`_database` 계열)인 경우.
    """
    out_path = Path(out_path)
    _reject_forbidden_receipt_path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(receipt, sort_keys=True, ensure_ascii=False, indent=2) + "\n"

    fd, tmp_path_str = tempfile.mkstemp(
        prefix=f".{out_path.name}.",
        suffix=".tmp",
        dir=str(out_path.parent),
    )
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, out_path)
    except Exception:
        with contextlib.suppress(OSError):
            tmp_path.unlink()
        raise
    return out_path
