"""wt-webbt 전용 DB 환경 구성 스크립트 (1회성, 멱등).

원본(wt-dev)의 `_database/` 와 `ai_strategy_loop/state/` 를 새 워크트리
(wt-webbt)로 가져온다. 원칙:

- 읽기 전용 대용량 시세 DB(per-day tick/min, *_back.db, tick/min subset):
  NTFS **하드링크** — 디스크 추가 사용 0, 즉시 완료. 양쪽 모두 읽기만 한다.
- 쓰기 가능 DB(strategy/setting/backtest/loop_runs 등):
  sqlite3 **online backup API** — 원본이 활성 쓰기 중(WAL)이어도 일관된
  스냅샷 복사를 보장한다(단순 파일 복사는 mid-transaction 손상 위험).
- 작은 일반 파일: 그대로 복사.
- 라이브 상태 파일(current_state.json, STOP)은 가져오지 않는다 — 새 워크트리
  대시보드는 idle로 시작해야 한다.

재실행 안전: 대상 파일이 이미 존재하면 건너뛴다.
"""

from __future__ import annotations

import re
import shutil
import sqlite3
import sys
from pathlib import Path

SRC_ROOT = Path("C:/System_Trading/STOM/STOM_V.wt-dev")
DST_ROOT = Path("C:/System_Trading/STOM/STOM_V.wt-webbt")

# 일일 시세 DB: stock_tick_20250407.db / stock_min_20240102.db / coin_*_YYYYMMDD.db
DAILY_RE = re.compile(r"_(20\d{6})\.db$")

# _database/ 안에서 하드링크할 대용량 읽기 전용 DB
DB_HARDLINK = {"stock_tick_back.db", "stock_min_back.db"}
# _database/ 안에서 건너뛸 항목(백업/임시)
DB_SKIP_PREFIX = ("_debug_backup", "setting.db.bak")

# state/ 안에서 하드링크할 대용량 읽기 전용 파생 서브셋
STATE_HARDLINK = {"tick_subset.db", "tick_subset_small.db", "min_subset.db"}
# state/ 안에서 가져오지 않을 항목(라이브 상태/세션 로컬)
STATE_SKIP = {"current_state.json", "STOP", ".omc"}


def sqlite_backup(src: Path, dst: Path) -> str:
    """활성 쓰기 중에도 안전한 SQLite 온라인 백업 복사."""
    if src.stat().st_size == 0:
        shutil.copy2(src, dst)
        return "copy(empty)"
    src_con = sqlite3.connect(f"file:{src.as_posix()}?mode=ro", uri=True, timeout=30)
    try:
        dst_con = sqlite3.connect(str(dst))
        try:
            src_con.backup(dst_con)
        finally:
            dst_con.close()
    finally:
        src_con.close()
    return "sqlite-backup"


def hardlink(src: Path, dst: Path) -> str:
    dst.hardlink_to(src)
    return "hardlink"


def process_database_dir() -> None:
    src_dir = SRC_ROOT / "_database"
    dst_dir = DST_ROOT / "_database"
    dst_dir.mkdir(exist_ok=True)
    stats = {"hardlink": 0, "sqlite-backup": 0, "copy": 0, "skip": 0, "exists": 0}

    for src in sorted(src_dir.iterdir()):
        name = src.name
        dst = dst_dir / name
        if any(name.startswith(p) for p in DB_SKIP_PREFIX):
            stats["skip"] += 1
            continue
        # WAL/SHM 사이드카는 backup API가 본체에 흡수하므로 복사하지 않는다.
        if name.endswith(("-wal", "-shm", ".db-journal")):
            stats["skip"] += 1
            continue
        if dst.exists():
            stats["exists"] += 1
            continue
        if src.is_dir():
            shutil.copytree(src, dst)
            stats["copy"] += 1
            continue
        if DAILY_RE.search(name) or name in DB_HARDLINK:
            hardlink(src, dst)
            stats["hardlink"] += 1
        elif name.endswith(".db"):
            mode = sqlite_backup(src, dst)
            stats["sqlite-backup" if mode == "sqlite-backup" else "copy"] += 1
            print(f"  [{mode}] _database/{name}", flush=True)
        else:
            shutil.copy2(src, dst)
            stats["copy"] += 1
    print(f"_database done: {stats}", flush=True)


def process_state_dir() -> None:
    src_dir = SRC_ROOT / "ai_strategy_loop" / "state"
    dst_dir = DST_ROOT / "ai_strategy_loop" / "state"
    dst_dir.mkdir(parents=True, exist_ok=True)
    stats = {"hardlink": 0, "sqlite-backup": 0, "copy": 0, "skip": 0, "exists": 0}

    for src in sorted(src_dir.iterdir()):
        name = src.name
        dst = dst_dir / name
        if name in STATE_SKIP or name.endswith(("-wal", "-shm", ".db-journal")):
            stats["skip"] += 1
            continue
        if dst.exists():
            stats["exists"] += 1
            continue
        if src.is_dir():
            shutil.copytree(src, dst)
            stats["copy"] += 1
            continue
        if name in STATE_HARDLINK:
            hardlink(src, dst)
            stats["hardlink"] += 1
        elif name.endswith(".db"):
            mode = sqlite_backup(src, dst)
            stats["sqlite-backup" if mode == "sqlite-backup" else "copy"] += 1
            print(f"  [{mode}] state/{name}", flush=True)
        else:
            shutil.copy2(src, dst)
            stats["copy"] += 1
    print(f"state done: {stats}", flush=True)


def verify() -> int:
    """복사된 핵심 DB의 무결성을 빠르게 확인한다."""
    failures = 0
    for rel in ("_database/strategy.db", "_database/setting.db",
                "ai_strategy_loop/state/loop_runs.db"):
        path = DST_ROOT / rel
        if not path.exists():
            print(f"  MISSING: {rel}")
            failures += 1
            continue
        try:
            con = sqlite3.connect(str(path))
            ok = con.execute("PRAGMA quick_check").fetchone()[0]
            con.close()
            print(f"  quick_check {rel}: {ok}")
            if ok != "ok":
                failures += 1
        except Exception as exc:  # noqa: BLE001 — 검증 단계는 전부 보고
            print(f"  ERROR {rel}: {exc}")
            failures += 1
    return failures


if __name__ == "__main__":
    print("== _database ==", flush=True)
    process_database_dir()
    print("== ai_strategy_loop/state ==", flush=True)
    process_state_dir()
    print("== verify ==", flush=True)
    sys.exit(1 if verify() else 0)
