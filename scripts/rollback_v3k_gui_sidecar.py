from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_v3k_gate_approval_phrase import FIRST_GATE, FIRST_GATE_PHRASE, evaluate_approval_phrase  # noqa: E402
from strategy.v3k_gui_sidecar import V3K_GUI_SIDECAR_BACKUP_DIR, V3K_GUI_SIDECAR_FILE, load_v3k_gui_sidecar_file  # noqa: E402

USER_ACK_ENV = "V3K_GUI_SIDECAR_USER_ACK"
ROLLBACK_VERSION = "V3K_GUI_SIDECAR_ROLLBACK_V1"


@dataclass(frozen=True)
class GuiSidecarRollbackResult:
    rollback_version: str
    gate: str
    target: str
    removed: bool
    quarantined_path: str | None
    target_exists_after: bool
    executes_runtime: bool = False
    touches_database: bool = False
    touches_kiwoom_live: bool = False


def _timestamp() -> str:
    return datetime.now(timezone(timedelta(hours=9))).strftime("%Y%m%dT%H%M%S%z")


def rollback_sidecar(*, approval_phrase: str, execute: bool) -> GuiSidecarRollbackResult:
    verdict = evaluate_approval_phrase(approval_phrase)
    if not verdict.accepted or approval_phrase != FIRST_GATE_PHRASE:
        raise SystemExit(f"approval phrase rejected for rollback: {verdict.status}")
    if os.environ.get(USER_ACK_ENV) != "1":
        raise SystemExit(f"{USER_ACK_ENV}=1 is required for approved rollback")

    target = ROOT / V3K_GUI_SIDECAR_FILE
    if not target.exists():
        return GuiSidecarRollbackResult(
            rollback_version=ROLLBACK_VERSION,
            gate=FIRST_GATE,
            target=V3K_GUI_SIDECAR_FILE,
            removed=False,
            quarantined_path=None,
            target_exists_after=False,
        )

    existing = load_v3k_gui_sidecar_file(target)
    if not existing.valid:
        raise SystemExit("existing sidecar is invalid; refusing automated rollback without manual inspection")

    quarantine = ROOT / V3K_GUI_SIDECAR_BACKUP_DIR / f"v3k_gui_settings.rollback.{_timestamp()}.json"
    if not execute:
        return GuiSidecarRollbackResult(
            rollback_version=ROLLBACK_VERSION,
            gate=FIRST_GATE,
            target=V3K_GUI_SIDECAR_FILE,
            removed=False,
            quarantined_path=str(quarantine.relative_to(ROOT)).replace("\\", "/"),
            target_exists_after=True,
        )

    quarantine.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(target), str(quarantine))
    return GuiSidecarRollbackResult(
        rollback_version=ROLLBACK_VERSION,
        gate=FIRST_GATE,
        target=V3K_GUI_SIDECAR_FILE,
        removed=True,
        quarantined_path=str(quarantine.relative_to(ROOT)).replace("\\", "/"),
        target_exists_after=target.exists(),
    )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rollback/quarantine the approved V3K GUI sidecar seed.")
    parser.add_argument("--approve", required=True, help="Exact first-gate approval phrase.")
    parser.add_argument("--execute", action="store_true", help="Actually quarantine the sidecar file; omitted means dry-run.")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(tuple(argv or sys.argv[1:]))
    result = rollback_sidecar(approval_phrase=args.approve, execute=args.execute)
    if args.format == "json":
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"rollback_version={result.rollback_version}")
        print(f"removed={str(result.removed).lower()}")
        print(f"target_exists_after={str(result.target_exists_after).lower()}")
        if result.quarantined_path:
            print(f"quarantined_path={result.quarantined_path}")


if __name__ == "__main__":
    main()
