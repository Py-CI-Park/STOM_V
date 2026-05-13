from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_v3k_gate_approval_phrase import (  # noqa: E402
    FIRST_GATE,
    FIRST_GATE_PHRASE,
    evaluate_approval_phrase,
)
from scripts.preview_v3k_gui_sidecar_default_payload import (  # noqa: E402
    assert_default_off_payload,
    build_default_off_payload,
)
from strategy.v3k_gui_sidecar import (  # noqa: E402
    V3K_GUI_SIDECAR_BACKUP_DIR,
    V3K_GUI_SIDECAR_FILE,
    load_v3k_gui_sidecar_file,
    validate_v3k_gui_sidecar_payload,
)

USER_ACK_ENV = "V3K_GUI_SIDECAR_USER_ACK"
WRITER_VERSION = "V3K_GUI_SIDECAR_APPROVED_WRITER_V1"

FORBIDDEN_STATUS_PATHS = (
    "_database",
    "_database_v3k_shadow",
    "_log",
    "backup",
    "*.db",
    "backtest/graph",
    ".omx/reports",
    "v3k_settings*.json",
)


@dataclass(frozen=True)
class GuiSidecarWriteResult:
    writer_version: str
    gate: str
    approval_phrase: str
    user_ack_env: str
    target: str
    written: bool
    idempotent: bool
    backup_path: str | None
    all_off: bool
    executes_runtime: bool = False
    touches_database: bool = False
    touches_kiwoom_live: bool = False


def _run_git(*args: str) -> str:
    import subprocess

    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def _assert_forbidden_status_clean() -> None:
    status = _run_git("status", "--short", "--", *FORBIDDEN_STATUS_PATHS)
    if status:
        raise SystemExit(f"forbidden runtime/DB artifact status is not clean before sidecar write:\n{status}")


def _timestamp() -> str:
    return datetime.now(timezone(timedelta(hours=9))).strftime("%Y%m%dT%H%M%S%z")


def _approval_record() -> str:
    return datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


def _build_approved_payload() -> dict[str, Any]:
    payload = build_default_off_payload()
    payload["approval_state"] = "approved-gate1-default-off-written"
    payload["approval_gate"] = FIRST_GATE
    payload["approval_record"] = _approval_record()
    assert_default_off_payload(payload)
    return payload


def _assert_target_in_sidecar_dir(target: Path) -> None:
    resolved = target.resolve()
    expected = (ROOT / V3K_GUI_SIDECAR_FILE).resolve()
    if resolved != expected:
        raise SystemExit(f"target must stay fixed at {expected}: {resolved}")


def _validate_existing_before_replace(target: Path) -> None:
    if not target.exists():
        return
    existing = load_v3k_gui_sidecar_file(target)
    if not existing.valid:
        raise SystemExit(
            "existing sidecar is invalid; refusing to overwrite without manual quarantine: "
            + "; ".join(existing.diagnostics)
        )


def write_default_off_sidecar(*, approval_phrase: str) -> GuiSidecarWriteResult:
    verdict = evaluate_approval_phrase(approval_phrase)
    if not verdict.accepted or approval_phrase != FIRST_GATE_PHRASE:
        raise SystemExit(f"approval phrase rejected: {verdict.status}")
    if os.environ.get(USER_ACK_ENV) != "1":
        raise SystemExit(f"{USER_ACK_ENV}=1 is required for approved gate execution")

    _assert_forbidden_status_clean()
    target = ROOT / V3K_GUI_SIDECAR_FILE
    _assert_target_in_sidecar_dir(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    payload = _build_approved_payload()
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    _validate_existing_before_replace(target)

    idempotent = target.exists() and target.read_text(encoding="utf-8") == serialized
    backup_path: Path | None = None
    if idempotent:
        result = validate_v3k_gui_sidecar_payload(target.read_text(encoding="utf-8"))
        return GuiSidecarWriteResult(
            writer_version=WRITER_VERSION,
            gate=FIRST_GATE,
            approval_phrase=approval_phrase,
            user_ack_env=USER_ACK_ENV,
            target=V3K_GUI_SIDECAR_FILE,
            written=False,
            idempotent=True,
            backup_path=None,
            all_off=result.all_off,
        )

    if target.exists():
        backup_dir = ROOT / V3K_GUI_SIDECAR_BACKUP_DIR
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"v3k_gui_settings.{_timestamp()}.json"
        shutil.copy2(target, backup_path)

    tmp = target.with_name(f"{target.name}.tmp")
    before = target.read_text(encoding="utf-8") if target.exists() else None
    try:
        tmp.write_text(serialized, encoding="utf-8")
        os.replace(tmp, target)
    except OSError as exc:
        if tmp.exists():
            tmp.unlink()
        after = target.read_text(encoding="utf-8") if target.exists() else None
        if after != before:
            raise RuntimeError("sidecar write rollback invariant failed") from exc
        raise

    loaded = load_v3k_gui_sidecar_file(target)
    if not loaded.valid or not loaded.all_off:
        raise RuntimeError(f"written sidecar failed default-OFF validation: {loaded.diagnostics}")

    _assert_forbidden_status_clean()
    return GuiSidecarWriteResult(
        writer_version=WRITER_VERSION,
        gate=FIRST_GATE,
        approval_phrase=approval_phrase,
        user_ack_env=USER_ACK_ENV,
        target=V3K_GUI_SIDECAR_FILE,
        written=True,
        idempotent=False,
        backup_path=str(backup_path.relative_to(ROOT)).replace("\\", "/") if backup_path else None,
        all_off=loaded.all_off,
    )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Approved writer for the first V3K GUI sidecar default-OFF seed."
    )
    parser.add_argument("--approve", required=True, help="Exact first-gate approval phrase.")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(tuple(argv or sys.argv[1:]))
    result = write_default_off_sidecar(approval_phrase=args.approve)
    if args.format == "json":
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"writer_version={result.writer_version}")
        print(f"gate={result.gate}")
        print(f"target={result.target}")
        print(f"written={str(result.written).lower()}")
        print(f"idempotent={str(result.idempotent).lower()}")
        print(f"all_off={str(result.all_off).lower()}")
        if result.backup_path:
            print(f"backup_path={result.backup_path}")


if __name__ == "__main__":
    main()
