from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from gui_contract_manifest import build_contract, contract_summary


ROOT = Path.cwd()


def run_git(args: list[str], *, binary: bool = False):
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=not binary,
        check=False,
    )
    return result


def upstream_pyd_evidence(upstream_ref: str) -> tuple[dict[str, object], str | None]:
    spec = f"{upstream_ref}:ui/ui_mainwindow.pyd"
    result = run_git(["show", spec], binary=True)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace") if isinstance(result.stderr, bytes) else result.stderr
        return {}, f"failed to read {spec}: {detail.strip()}"
    data = result.stdout
    return {
        "path": "ui/ui_mainwindow.pyd",
        "upstream_ref": upstream_ref,
        "byte_size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }, None


def tracked_pyd_files() -> list[str]:
    result = run_git(["ls-files"])
    if result.returncode != 0:
        return ["<git ls-files failed>"]
    return sorted(line for line in result.stdout.splitlines() if line.lower().endswith(".pyd"))


def smoke_log_path(log_dir: Path, branch: str, version: str) -> Path:
    return log_dir / f"smoke_{branch.replace('/', '_')}_{version.replace('.', '_')}.json"


def read_smoke(log_dir: Path, branch: str, version: str) -> tuple[dict[str, object] | None, str | None]:
    path = smoke_log_path(log_dir, branch, version)
    if not path.exists():
        return None, f"missing smoke log: {path}"
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as exc:
        return None, f"invalid smoke log {path}: {exc}"


def unresolved_activated_alias_calls() -> list[str]:
    path = ROOT / "ui" / "ui_mainwindow.py"
    if not path.exists():
        return ["ui/ui_mainwindow.py is missing"]
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as exc:
        return [f"ui/ui_mainwindow.py syntax error: {exc}"]

    main_window = next(
        (node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow"),
        None,
    )
    if main_window is None:
        return ["MainWindow class is missing"]

    unresolved: list[str] = []
    for method in main_window.body:
        if not isinstance(method, ast.FunctionDef):
            continue
        for node in ast.walk(method):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            name = node.func.id
            if name.startswith(("sactivated_", "cactivated_")):
                unresolved.append(f"{method.name}->{name}")
    return sorted(set(unresolved))


def missing_import_modules() -> list[str]:
    text = (ROOT / "ui" / "ui_mainwindow.py").read_text(encoding="utf-8", errors="replace")
    missing: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("from ui."):
            continue
        module = line.split()[1]
        relative = module.replace(".", "/") + ".py"
        if not (ROOT / relative).exists():
            missing.append(module)
    return sorted(set(missing))


def pyd_mainwindow_backtest_parity_failures() -> list[str]:
    path = ROOT / "ui" / "ui_mainwindow.py"
    if not path.exists():
        return ["ui/ui_mainwindow.py is missing"]

    text = path.read_text(encoding="utf-8", errors="replace")
    required_snippets = {
        "legacy button binder": "def BindLegacyStrategyBacktestButtons(self):",
        "stock button connect": "self.svj_pushButton_01, self.StockBacktestStart",
        "coin button connect": "self.cvj_pushButton_01, self.CoinBacktestStart",
        "back progress updater": "update_back_progressbar(self)",
        "back start time state": "self.back_start_time  = None",
        "dialog position binder": "def BindPydDialogPositionPersistence(self):",
        "backengine position binding": "self.BindPydDialogPosition(self.dialog_backengine, 16, 17)",
        "dialog position restore": "def RestorePydDialogPosition(self, dialog, x_index, y_index):",
        "dialog position save": "def SavePydDialogPosition(self, dialog, x_index, y_index):",
        "shortcut handler": "def LegacyBacktestShortcut(self, event):",
        "shortcut stock call": "self.StockBacktestStart()",
        "shortcut coin call": "self.CoinBacktestStart()",
    }
    missing = [label for label, snippet in required_snippets.items() if snippet not in text]
    return [f"pyd mainwindow backtest parity lacks {label}" for label in missing]


def evaluate(branch: str, version: str, upstream_ref: str, log_dir: Path) -> tuple[dict[str, object], list[str]]:
    failures: list[str] = []
    pyd_evidence, pyd_error = upstream_pyd_evidence(upstream_ref)
    if pyd_error:
        failures.append(pyd_error)

    pyd_files = tracked_pyd_files()
    if pyd_files:
        failures.append(f"tracked .pyd files are not allowed: {', '.join(pyd_files)}")

    imports_missing = missing_import_modules()
    if imports_missing:
        failures.append(f"ui_mainwindow.py imports missing modules: {', '.join(imports_missing)}")

    unresolved_alias_calls = unresolved_activated_alias_calls()
    if unresolved_alias_calls:
        failures.append(
            "ui_mainwindow.py has unresolved strategy activated aliases: "
            + ", ".join(unresolved_alias_calls)
        )

    legacy_parity_failures = pyd_mainwindow_backtest_parity_failures()
    if legacy_parity_failures:
        failures.append(
            "pyd-derived ui_mainwindow.py must preserve legacy stock/coin backtest parity: "
            + ", ".join(legacy_parity_failures)
        )

    contract = build_contract(ROOT)
    if not contract:
        failures.append("GUI contract manifest is empty")

    smoke, smoke_error = read_smoke(log_dir, branch, version)
    if smoke_error:
        failures.append(smoke_error)
    elif smoke and smoke.get("status") != "passed":
        failures.append(f"smoke status is {smoke.get('status')}")

    payload = {
        "branch": branch,
        "version": version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "upstream_pyd": pyd_evidence,
        "tracked_pyd_count": len(pyd_files),
        "tracked_pyd_files": pyd_files,
        "missing_import_modules": imports_missing,
        "unresolved_activated_alias_calls": unresolved_alias_calls,
        "pyd_mainwindow_backtest_parity_failures": legacy_parity_failures,
        "contract_summary": contract_summary(contract),
        "contract_items": [item.to_dict() for item in contract],
        "smoke_log": str(smoke_log_path(log_dir, branch, version)),
        "smoke_status": smoke.get("status") if smoke else None,
        "result": "failed" if failures else "passed",
        "failures": failures,
    }
    return payload, failures


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify bounded pyd-derived GUI contract.")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--upstream-ref", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--log-dir", default=".omx/logs/v279")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    payload, failures = evaluate(args.branch, args.version, args.upstream_ref, ROOT / args.log_dir)

    manifest_path = ROOT / args.manifest
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[INFO] contract manifest: {manifest_path}")

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print("[OK] pyd GUI contract passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

