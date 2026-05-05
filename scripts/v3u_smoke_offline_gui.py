from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from v3u_gui_contract_manifest import V3_PY_TARGET, build_contract, contract_summary


ROOT = Path.cwd()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass
class ActionResult:
    action_id: str
    category: str
    target: str
    result: str
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "action_id": self.action_id,
            "category": self.category,
            "target": self.target,
            "result": self.result,
            "detail": self.detail,
        }


def configure_environment() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("STOM_OFFLINE_SMOKE", "1")


def import_python_mainwindow() -> tuple[object | None, str | None]:
    target = ROOT / V3_PY_TARGET
    if not target.exists():
        return None, f"{V3_PY_TARGET} is missing; pyd-free MainWindow has not been implemented yet"
    spec = importlib.util.spec_from_file_location("ui.main_window", target)
    if spec is None or spec.loader is None:
        return None, f"cannot build import spec for {V3_PY_TARGET}"
    module = importlib.util.module_from_spec(spec)
    sys.modules["ui.main_window"] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        return None, "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip()
    main_window = getattr(module, "MainWindow", None)
    if main_window is None:
        return None, "MainWindow class is missing from ui/main_window.py"
    return main_window, None


def structural_smoke(branch: str, version: str) -> dict[str, object]:
    configure_environment()
    actions: list[ActionResult] = []
    status = "passed"
    error = ""

    contract = build_contract(ROOT)
    tracked_pyd = sorted(path for path in os.popen("git ls-files *.pyd").read().splitlines() if path)
    if tracked_pyd:
        status = "failed"
        detail = "tracked .pyd files still exist: " + ", ".join(tracked_pyd)
        actions.append(ActionResult("tracked_pyd", "pyd_free_gate", "*.pyd", "failed", detail))
    else:
        actions.append(ActionResult("tracked_pyd", "pyd_free_gate", "*.pyd", "passed"))

    main_window, import_error = import_python_mainwindow()
    if import_error:
        status = "failed"
        error = import_error
        actions.append(ActionResult("main_window_import", "import", V3_PY_TARGET, "failed", import_error))
    else:
        actions.append(ActionResult("main_window_import", "import", V3_PY_TARGET, "passed", repr(main_window)))

    return {
        "branch": branch,
        "version": version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "error": error,
        "summary": contract_summary(contract),
        "actions": [action.to_dict() for action in actions],
    }


def write_log(payload: dict[str, object], log_dir: Path, branch: str, version: str) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    safe_branch = branch.replace("/", "_")
    safe_version = version.replace(".", "_")
    path = log_dir / f"smoke_{safe_branch}_{safe_version}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run V3U offline structural GUI smoke after pyd removal.")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--offline", action="store_true", help="Required marker for side-effect-safe execution.")
    parser.add_argument("--log-dir", default=".omx/logs/v3u")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if not args.offline:
        print("[FAIL] --offline is required")
        return 2
    payload = structural_smoke(args.branch, args.version)
    path = write_log(payload, ROOT / args.log_dir, args.branch, args.version)
    print(f"[INFO] V3U smoke log: {path}")
    if payload["status"] != "passed":
        print("[FAIL] V3U offline structural smoke failed")
        print(payload.get("error", ""))
        return 1
    print("[OK] V3U offline structural smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
