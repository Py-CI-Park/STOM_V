from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ACK_ENV = "V3K_CUTOVER_USER_ACK"


def run_cmd(args: list[str], *, env: dict[str, str] | None = None, expect: int = 0) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    result = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        env=merged_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != expect:
        raise AssertionError(
            "unexpected command result\n"
            f"args={args}\nexpected={expect} actual={result.returncode}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
    return result


def create_db(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as con:
        con.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        con.execute("INSERT INTO sample(value) VALUES (?)", (value,))
        con.commit()


def read_value(path: Path) -> str:
    uri = path.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as con:
        return con.execute("SELECT value FROM sample WHERE id = 1").fetchone()[0]


def main() -> int:
    evidence: dict[str, Any] = {"checks": []}
    with tempfile.TemporaryDirectory(prefix="v3k-cutover-dryrun-") as tmp:
        base = Path(tmp)
        operational = base / "operational"
        shadow = base / "shadow"
        backup = base / "backup"
        target = base / "target"
        corrupt_backup = base / "corrupt_backup"

        create_db(operational / "pattern_analysis.db", "old-operational")
        create_db(shadow / "pattern_analysis.db", "new-shadow")

        run_cmd(
            [
                "scripts/backup_operational_database.py",
                "--apply",
                "--source-dir",
                str(operational),
                "--target-dir",
                str(backup),
                "--stdout",
            ],
            env={ACK_ENV: "1"},
        )
        evidence["checks"].append("backup apply with tempfile source/target passed")
        if read_value(backup / "pattern_analysis.db") != "old-operational":
            raise AssertionError("backup did not preserve original operational DB")

        run_cmd(
            [
                "scripts/cutover_v3k_shadow_to_database.py",
                "--apply",
                "--backup-first",
                "--backup-dir",
                str(backup),
                "--shadow-dir",
                str(shadow),
                "--target-dir",
                str(target),
            ],
            expect=1,
        )
        evidence["checks"].append("cutover apply without ACK was rejected")

        run_cmd(
            [
                "scripts/cutover_v3k_shadow_to_database.py",
                "--apply",
                "--backup-dir",
                str(backup),
                "--shadow-dir",
                str(shadow),
                "--target-dir",
                str(target),
            ],
            env={ACK_ENV: "1"},
            expect=1,
        )
        evidence["checks"].append("cutover apply without --backup-first was rejected")

        run_cmd(
            [
                "scripts/cutover_v3k_shadow_to_database.py",
                "--apply",
                "--backup-first",
                "--backup-dir",
                str(backup),
                "--shadow-dir",
                str(shadow),
                "--target-dir",
                str(target),
                "--stdout",
            ],
            env={ACK_ENV: "1"},
        )
        evidence["checks"].append("cutover apply with tempfile target passed")
        if read_value(target / "pattern_analysis.db") != "new-shadow":
            raise AssertionError("cutover target did not receive shadow DB")

        run_cmd(
            [
                "scripts/rollback_v3k_cutover.py",
                "--backup-dir",
                str(backup),
                "--target-dir",
                str(target),
                "--apply",
            ],
            expect=1,
        )
        evidence["checks"].append("rollback apply without ACK was rejected")

        run_cmd(
            [
                "scripts/rollback_v3k_cutover.py",
                "--backup-dir",
                str(backup),
                "--target-dir",
                str(target),
                "--apply",
                "--stdout",
            ],
            env={ACK_ENV: "1"},
        )
        evidence["checks"].append("rollback apply with tempfile target passed")
        if read_value(target / "pattern_analysis.db") != "old-operational":
            raise AssertionError("rollback target did not restore backup DB")

        run_cmd(
            [
                "scripts/backup_operational_database.py",
                "--apply",
                "--source-dir",
                str(operational),
                "--target-dir",
                str(corrupt_backup),
                "--stdout",
            ],
            env={ACK_ENV: "1"},
        )
        with closing(sqlite3.connect(corrupt_backup / "pattern_analysis.db")) as con:
            con.execute("INSERT INTO sample(value) VALUES ('corrupted')")
            con.commit()

        run_cmd(
            [
                "scripts/cutover_v3k_shadow_to_database.py",
                "--apply",
                "--backup-first",
                "--backup-dir",
                str(corrupt_backup),
                "--shadow-dir",
                str(shadow),
                "--target-dir",
                str(target),
            ],
            env={ACK_ENV: "1"},
            expect=1,
        )
        evidence["checks"].append("cutover rejected corrupted backup checksum")

    evidence["result"] = "PASS"
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
