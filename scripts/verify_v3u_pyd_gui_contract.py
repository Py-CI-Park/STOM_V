from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from v3u_gui_contract_manifest import V3_PY_TARGET, V3_PYD_TARGET, build_contract, contract_summary


ROOT = Path.cwd()


def run_git(args: list[str], *, binary: bool = False):
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=not binary,
        check=False,
    )


def upstream_pyd_evidence(upstream_ref: str) -> tuple[dict[str, object], str | None]:
    spec = f"{upstream_ref}:{V3_PYD_TARGET}"
    result = run_git(["show", spec], binary=True)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace") if isinstance(result.stderr, bytes) else result.stderr
        return {}, f"failed to read {spec}: {detail.strip()}"
    data = result.stdout
    return {
        "path": V3_PYD_TARGET,
        "upstream_ref": upstream_ref,
        "byte_size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }, None


def tracked_pyd_files() -> list[str]:
    result = run_git(["ls-files", "*.pyd"])
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


def python_mainwindow_ast_failures() -> list[str]:
    path = ROOT / V3_PY_TARGET
    if not path.exists():
        return [f"{V3_PY_TARGET} is missing"]
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as exc:
        return [f"{V3_PY_TARGET} syntax error: {exc}"]
    main_window = next((node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "MainWindow"), None)
    if main_window is None:
        return ["MainWindow class is missing"]
    init_method = next((node for node in main_window.body if isinstance(node, ast.FunctionDef) and node.name == "__init__"), None)
    if init_method is None:
        return ["MainWindow.__init__ is missing"]
    return []


def missing_import_modules() -> list[str]:
    path = ROOT / V3_PY_TARGET
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    missing: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("from ui."):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        module = parts[1]
        relative = module.replace(".", "/") + ".py"
        if not (ROOT / relative).exists():
            missing.append(module)
    return sorted(set(missing))


def run_pytest_gate(log_dir: Path) -> tuple[dict[str, object], str | None]:
    """V3U 자동 GUI 검증 pytest 게이트 (Phase 5 통합).

    tests/v3u/ 전체를 subprocess로 실행하고 stdout/stderr/exit를 수집한다.
    pytest-qt 미설치 또는 timeout 등 예외 상황은 명시적 fail로 처리한다.
    """
    pytest_log = log_dir / "pytest_summary.txt"
    pytest_log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "pytest", "tests/v3u/", "--tb=short", "-q"]
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=600,
        )
    except subprocess.TimeoutExpired as exc:
        pytest_log.write_text(f"TIMEOUT after 600s\n{exc}\n", encoding="utf-8")
        return {"command": " ".join(cmd), "exit_code": None,
                "log_path": str(pytest_log), "status": "timeout"}, "pytest gate timed out"
    except FileNotFoundError as exc:
        pytest_log.write_text(f"pytest 미설치: {exc}\n", encoding="utf-8")
        return {"command": " ".join(cmd), "exit_code": -1,
                "log_path": str(pytest_log), "status": "missing"}, (
            "pytest 미설치. requirements-dev.txt 설치 필요: "
            "python -m pip install -r requirements-dev.txt"
        )
    pytest_log.write_text(
        f"$ {' '.join(cmd)}\nexit={proc.returncode}\n\n--- STDOUT ---\n{proc.stdout}\n--- STDERR ---\n{proc.stderr}\n",
        encoding="utf-8",
    )
    last_line = ""
    for line in proc.stdout.splitlines()[::-1]:
        if line.strip():
            last_line = line.strip()
            break
    payload = {
        "command": " ".join(cmd),
        "exit_code": proc.returncode,
        "log_path": str(pytest_log),
        "status": "passed" if proc.returncode == 0 else "failed",
        "summary_line": last_line,
    }
    if proc.returncode != 0:
        return payload, f"pytest gate failed (exit={proc.returncode}): {last_line}"
    return payload, None


def evaluate(branch: str, version: str, upstream_ref: str, log_dir: Path, allow_existing_pyd: bool, *, skip_pytest: bool = False) -> tuple[dict[str, object], list[str]]:
    failures: list[str] = []
    pyd_evidence, pyd_error = upstream_pyd_evidence(upstream_ref)
    if pyd_error:
        failures.append(pyd_error)

    pyd_files = tracked_pyd_files()
    if pyd_files and not allow_existing_pyd:
        failures.append(f"tracked .pyd files are not allowed after V3U pyd removal: {', '.join(pyd_files)}")

    ast_failures = python_mainwindow_ast_failures()
    failures.extend(ast_failures)

    imports_missing = missing_import_modules()
    if imports_missing:
        failures.append(f"{V3_PY_TARGET} imports missing modules: {', '.join(imports_missing)}")

    contract = build_contract(ROOT)
    if not contract:
        failures.append("V3U GUI contract manifest is empty")

    smoke, smoke_error = read_smoke(log_dir, branch, version)
    if smoke_error:
        failures.append(smoke_error)
    elif smoke and smoke.get("status") != "passed":
        failures.append(f"smoke status is {smoke.get('status')}")

    if skip_pytest:
        pytest_payload: dict[str, object] = {"status": "skipped", "reason": "--skip-pytest"}
    else:
        pytest_payload, pytest_error = run_pytest_gate(log_dir)
        if pytest_error:
            failures.append(pytest_error)

    # A3: attr_inventory_diff 별도 단계 (CRITICAL drift 측정 + strict baseline 검증)
    attr_inv_payload, attr_inv_error = run_attr_inventory_diff(log_dir)
    if attr_inv_error:
        failures.append(attr_inv_error)

    payload = {
        "branch": branch,
        "version": version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "upstream_pyd": pyd_evidence,
        "tracked_pyd_count": len(pyd_files),
        "tracked_pyd_files": pyd_files,
        "allow_existing_pyd": allow_existing_pyd,
        "python_mainwindow_ast_failures": ast_failures,
        "missing_import_modules": imports_missing,
        "contract_summary": contract_summary(contract),
        "contract_items": [item.to_dict() for item in contract],
        "smoke_log": str(smoke_log_path(log_dir, branch, version)),
        "smoke_status": smoke.get("status") if smoke else None,
        "pytest_gate": pytest_payload,
        "attr_inventory_diff": attr_inv_payload,
        "stage_results": {
            "1_upstream_pyd_evidence": "passed" if not pyd_error else "failed",
            "2_tracked_pyd_guard": "passed" if not (pyd_files and not allow_existing_pyd) else "failed",
            "3_mainwindow_ast": "passed" if not ast_failures else "failed",
            "4_imports": "passed" if not imports_missing else "failed",
            "5_contract_manifest": "passed" if contract else "failed",
            "6_offline_smoke": (smoke.get("status") if smoke else "missing"),
            "7_pytest_gate": pytest_payload.get("status", "unknown"),
            "8_attr_inventory_diff": attr_inv_payload.get("status", "unknown"),
        },
        "result": "failed" if failures else "passed",
        "failures": failures,
    }
    return payload, failures


def run_attr_inventory_diff(log_dir: Path) -> tuple[dict[str, object], str | None]:
    """A3 신규 단계: attr_inventory_diff 자동 도구를 별도로 호출해 결과 분리 보고.

    pytest 게이트가 test_attr_inventory_drift를 포함하지만 verifier 출력에 단계별
    명시 표시를 위해 별도 stage로 분리. CRITICAL > baseline 시 명시적 fail.
    """
    diff_script = ROOT / "scripts" / "v3u_attr_inventory_diff.py"
    if not diff_script.is_file():
        return {"status": "missing", "reason": f"{diff_script} not found"}, None
    out_rel = "attr_inventory_verifier_run.json"
    output_abs = log_dir / out_rel
    try:
        proc = subprocess.run(
            [sys.executable, str(diff_script), "--strict",
             "--output", str(output_abs.relative_to(ROOT))],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return {"status": "timeout"}, "attr_inventory_diff timed out (120s)"
    except FileNotFoundError as exc:
        return {"status": "missing", "reason": str(exc)}, None
    summary_line = ""
    for line in (proc.stdout or "").splitlines():
        if "critical=" in line:
            summary_line = line.strip()
            break
    payload = {
        "exit_code": proc.returncode,
        "log_path": str(output_abs),
        "status": "passed" if proc.returncode == 0 else "failed",
        "summary_line": summary_line,
    }
    if proc.returncode != 0:
        return payload, f"attr_inventory_diff strict mode fail: {summary_line or 'see log'}"
    return payload, None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify V3U pyd-free GUI contract.")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--upstream-ref", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--log-dir", default=".omx/logs/v3u")
    parser.add_argument("--allow-existing-pyd", action="store_true", help="Inventory-only mode before pyd removal.")
    parser.add_argument("--skip-pytest", action="store_true",
                        help="Phase 5 pytest 게이트 건너뜀 (CI 외 빠른 정적 검증용).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    payload, failures = evaluate(
        args.branch, args.version, args.upstream_ref,
        ROOT / args.log_dir, args.allow_existing_pyd,
        skip_pytest=args.skip_pytest,
    )
    manifest_path = ROOT / args.manifest
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[INFO] V3U contract manifest: {manifest_path}")
    # A3: 단계별 PASS/FAIL 명시 출력 (V3 흡수 시 fail 단계 즉시 파악)
    stage_results = payload.get("stage_results", {})
    if isinstance(stage_results, dict):
        print("[STAGE] V3U 통합 게이트 단계별 결과:")
        for stage_name, stage_status in stage_results.items():
            tag = "PASS" if stage_status == "passed" else (
                "SKIP" if stage_status == "skipped" else "FAIL"
            )
            print(f"  [{tag}] {stage_name}: {stage_status}")
    pytest_gate = payload.get("pytest_gate", {})
    if isinstance(pytest_gate, dict):
        status = pytest_gate.get("status")
        if status == "passed":
            print(f"[INFO] pytest gate: passed ({pytest_gate.get('summary_line', '')})")
        elif status == "skipped":
            print("[INFO] pytest gate: skipped (--skip-pytest)")
        else:
            print(f"[INFO] pytest gate: {status} (log: {pytest_gate.get('log_path')})")
    attr_inv = payload.get("attr_inventory_diff", {})
    if isinstance(attr_inv, dict):
        ai_status = attr_inv.get("status")
        if ai_status == "passed":
            print(f"[INFO] attr inventory: passed ({attr_inv.get('summary_line', '')})")
        else:
            print(f"[INFO] attr inventory: {ai_status} (log: {attr_inv.get('log_path')})")
    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        return 1
    print("[OK] V3U pyd GUI contract + pytest gate + attr inventory diff passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
