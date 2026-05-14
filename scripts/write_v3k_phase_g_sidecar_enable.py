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

from scripts.check_v3k_gate_approval_phrase import evaluate_approval_phrase  # noqa: E402
from strategy.v3k_analyzer_adapter import (  # noqa: E402
    FLAG_PHASE_F_ANALYZER_STRATEGY,
    FLAG_PHASE_G_MICROSTRUCTURE_ENGINE,
)
from strategy.v3k_gui_sidecar import (  # noqa: E402
    V3K_GUI_SIDECAR_BACKUP_DIR,
    V3K_GUI_SIDECAR_FILE,
    load_v3k_gui_sidecar_file,
    validate_v3k_gui_sidecar_payload,
)
from strategy.v3k_settings_surface import v3k_settings_defaults  # noqa: E402

USER_ACK_ENV = "V3K_PHASE_G_USER_ACK"
PHASE_G_GATE = "phase-g-g3-on-await-user-approval"
PHASE_G_PHRASE = "I approve phase-g-g3-on-await-user-approval only"
WRITER_VERSION = "V3K_PHASE_G_SIDECAR_ENABLE_WRITER_V1"
ALLOWED_ENABLED = {FLAG_PHASE_F_ANALYZER_STRATEGY, FLAG_PHASE_G_MICROSTRUCTURE_ENGINE}

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
class PhaseGEnableWriteResult:
    writer_version: str
    gate: str
    approval_phrase: str
    user_ack_env: str
    target: str
    written: bool
    idempotent: bool
    backup_path: str | None
    enabled_settings: tuple[str, ...]
    rollback_env: str = "V3K_PHASE_G_DISABLE"
    executes_runtime: bool = False
    touches_database: bool = False
    touches_kiwoom_live: bool = False
    live_order_exit_wiring: bool = False


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
        raise SystemExit(f"forbidden runtime/DB artifact status is not clean before Phase G enable:\n{status}")


def _timestamp() -> str:
    return datetime.now(timezone(timedelta(hours=9))).strftime("%Y%m%dT%H%M%S%z")


def _approval_record() -> str:
    return datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


def _assert_gate_authority(approval_phrase: str) -> None:
    verdict = evaluate_approval_phrase(approval_phrase)
    if not verdict.accepted or verdict.gate != PHASE_G_GATE:
        raise SystemExit(f"approval phrase rejected for Phase G gate: {verdict.status} / {verdict.reason}")
    if os.environ.get(USER_ACK_ENV) != "1":
        raise SystemExit(f"{USER_ACK_ENV}=1 is required for Phase G approved gate execution")


def _load_base_payload(target: Path) -> dict[str, Any]:
    if not target.is_file():
        raise SystemExit(f"gate1/gate2 sidecar must exist before Phase G enable: {V3K_GUI_SIDECAR_FILE}")
    loaded = load_v3k_gui_sidecar_file(target)
    if not loaded.valid:
        raise SystemExit("existing sidecar is invalid; refusing Phase G enable: " + "; ".join(loaded.diagnostics))
    if loaded.settings.get(FLAG_PHASE_F_ANALYZER_STRATEGY) is not True:
        raise SystemExit("Phase F sidecar enable must be completed before Phase G enable")
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("existing sidecar payload must be an object")
    return payload


def _build_phase_g_payload(target: Path) -> dict[str, Any]:
    payload = _load_base_payload(target)
    settings = v3k_settings_defaults()
    existing = payload.get("settings")
    if isinstance(existing, dict):
        settings.update(existing)
    settings[FLAG_PHASE_G_MICROSTRUCTURE_ENGINE] = True
    payload["settings"] = settings
    payload["approval_state"] = "approved-gate3-phase-g-enabled"
    payload["approval_gate"] = PHASE_G_GATE
    payload["phase_g_approval_record"] = _approval_record()
    payload["phase_g_rollback_env"] = "V3K_PHASE_G_DISABLE"
    payload["phase_g_live_order_exit_wiring"] = False
    payload["phase_g_operating_database_written"] = False
    return payload


def _assert_phase_g_payload(payload: dict[str, Any]) -> tuple[str, ...]:
    result = validate_v3k_gui_sidecar_payload(payload)
    if not result.valid:
        raise SystemExit("Phase G sidecar payload failed validation: " + "; ".join(result.diagnostics))
    enabled = tuple(key for key, value in result.settings.items() if value)
    unexpected = [key for key in enabled if key not in ALLOWED_ENABLED]
    if unexpected:
        raise SystemExit(f"Phase G enable may only turn on {sorted(ALLOWED_ENABLED)}; got {unexpected}")
    if FLAG_PHASE_F_ANALYZER_STRATEGY not in enabled:
        raise SystemExit("Phase F analyzer strategy flag was not preserved in sidecar")
    if FLAG_PHASE_G_MICROSTRUCTURE_ENGINE not in enabled:
        raise SystemExit("Phase G microstructure engine flag was not enabled in sidecar")
    return enabled


def write_phase_g_enable(*, approval_phrase: str) -> PhaseGEnableWriteResult:
    _assert_gate_authority(approval_phrase)
    _assert_forbidden_status_clean()
    target = ROOT / V3K_GUI_SIDECAR_FILE
    payload = _build_phase_g_payload(target)
    enabled = _assert_phase_g_payload(payload)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"

    idempotent = target.read_text(encoding="utf-8") == serialized
    backup_path: Path | None = None
    if not idempotent:
        backup_dir = ROOT / V3K_GUI_SIDECAR_BACKUP_DIR
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"v3k_gui_settings.phase-g-enable.{_timestamp()}.json"
        shutil.copy2(target, backup_path)
        tmp = target.with_name(f"{target.name}.phase-g.tmp")
        before = target.read_text(encoding="utf-8")
        try:
            tmp.write_text(serialized, encoding="utf-8")
            os.replace(tmp, target)
        except OSError as exc:
            if tmp.exists():
                tmp.unlink()
            if target.read_text(encoding="utf-8") != before:
                raise RuntimeError("Phase G sidecar rollback invariant failed") from exc
            raise

    loaded = load_v3k_gui_sidecar_file(target)
    if not loaded.valid:
        raise RuntimeError(f"written Phase G sidecar failed validation: {loaded.diagnostics}")
    enabled_after = tuple(key for key, value in loaded.settings.items() if value)
    if enabled_after != enabled:
        raise RuntimeError(f"Phase G sidecar enabled set changed after write: {enabled_after} != {enabled}")
    _assert_forbidden_status_clean()
    return PhaseGEnableWriteResult(
        writer_version=WRITER_VERSION,
        gate=PHASE_G_GATE,
        approval_phrase=approval_phrase,
        user_ack_env=USER_ACK_ENV,
        target=V3K_GUI_SIDECAR_FILE,
        written=not idempotent,
        idempotent=idempotent,
        backup_path=str(backup_path.relative_to(ROOT)).replace("\\", "/") if backup_path else None,
        enabled_settings=enabled_after,
    )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Approved writer for the V3K Phase G sidecar enable gate.")
    parser.add_argument("--approve", required=True, help="Exact Phase G gate approval phrase.")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(tuple(argv or sys.argv[1:]))
    result = write_phase_g_enable(approval_phrase=args.approve)
    if args.format == "json":
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"writer_version={result.writer_version}")
        print(f"gate={result.gate}")
        print(f"target={result.target}")
        print(f"written={str(result.written).lower()}")
        print(f"idempotent={str(result.idempotent).lower()}")
        print(f"enabled_settings={','.join(result.enabled_settings)}")
        if result.backup_path:
            print(f"backup_path={result.backup_path}")


if __name__ == "__main__":
    main()
