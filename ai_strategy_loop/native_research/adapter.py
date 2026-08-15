"""Fresh-process preparation and integrity checks for STOM native tools."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
from typing import Any

from utility.sqlite_readonly import (
    assert_sqlite_sidefiles_unchanged,
    connect_existing_db_readonly,
    sqlite_fingerprint,
    sqlite_sidefile_snapshot,
)
from .contracts import NativeRunSpec, NativeTerminalStatus
from .sidecar import NativeSidecar, canonical_json

_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")
_MARKET_ENV_BY_NAME = {
    "stock_tick_back.db": "STOM_CLI_DB_STOCK_BACK_TICK",
    "stock_min_back.db": "STOM_CLI_DB_STOCK_BACK_MIN",
    "coin_tick_back.db": "STOM_CLI_DB_COIN_BACK_TICK",
    "coin_min_back.db": "STOM_CLI_DB_COIN_BACK_MIN",
}


def _copy_sqlite_snapshot(source: str | Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(destination)
    source_connection = connect_existing_db_readonly(source)
    destination_connection = sqlite3.connect(destination)
    try:
        source_connection.backup(destination_connection)
        destination_connection.commit()
    finally:
        destination_connection.close()
        source_connection.close()


class NativeResearchAdapter:
    def __init__(self, spec: NativeRunSpec):
        if not _RUN_ID.fullmatch(spec.run_id):
            raise ValueError("invalid native run_id")
        if spec.authority != "existing_db_development_no_oos_no_adoption":
            raise ValueError("native research authority mismatch")
        self.spec = spec
        self.output_root = Path(spec.output_root).expanduser().resolve()
        self.run_dir = (self.output_root / spec.run_id).resolve()
        if self.run_dir.parent != self.output_root:
            raise ValueError("native run path escaped output root")
        self.receipt_path = self.run_dir / "receipt.json"
        self.ledger = NativeSidecar(self.run_dir / "native_ledger.db")
        self._before: dict[str, dict[str, Any]] = {}
        self._sidefiles_before: dict[str, Any] = {}

    def prepare_run(self) -> dict[str, Any]:
        if self.run_dir.exists():
            raise FileExistsError(self.run_dir)
        self.run_dir.mkdir(parents=True)
        (self.run_dir / "csv").mkdir()
        sources = {
            "strategy": self.spec.strategy_db,
            "backtest": self.spec.backtest_db,
            "setting": self.spec.setting_db,
        }
        if self.spec.optuna_db:
            sources["optuna"] = self.spec.optuna_db
        for name, source in sources.items():
            _copy_sqlite_snapshot(source, self.run_dir / f"{name}.db")
        self._before = {str(Path(path).resolve()): sqlite_fingerprint(path) for path in self.spec.market_db_paths}
        self._sidefiles_before = {str(Path(path).resolve()): sqlite_sidefile_snapshot(path) for path in self.spec.market_db_paths}
        config = asdict(self.spec)
        config_sha256 = hashlib.sha256(canonical_json(config).encode("utf-8")).hexdigest()
        self.ledger.init_schema()
        receipt = {
            "schema": "stom.native_research.receipt.v1",
            "run_id": self.spec.run_id,
            "tool": self.spec.tool.value,
            "status": NativeTerminalStatus.PREPARED.value,
            "authority": self.spec.authority,
            "config_sha256": config_sha256,
            "operational_fingerprints_before": self._before,
            "operational_fingerprints_after": {},
            "sidefiles_before": self._sidefiles_before,
            "sidefiles_after": {},
        }
        self._write_receipt(receipt)
        return receipt

    def environment(self) -> dict[str, str]:
        required = ("strategy.db", "backtest.db", "setting.db", "csv")
        if any(not (self.run_dir / name).exists() for name in required):
            raise RuntimeError("native sidecar is not prepared")
        environment = dict(os.environ)
        environment.update({
            "STOM_CLI_DB_STRATEGY": str(self.run_dir / "strategy.db"),
            "STOM_CLI_DB_BACKTEST": str(self.run_dir / "backtest.db"),
            "STOM_CLI_BACKTEST_CSV_DIR": str(self.run_dir / "csv"),
            "STOM_CLI_DB_SETTING": str(self.run_dir / "setting.db"),
            "STOM_NATIVE_RUN_ID": self.spec.run_id,
            "STOM_NATIVE_AUTHORITY": self.spec.authority,
        })
        optuna = self.run_dir / "optuna.db"
        if optuna.exists():
            environment["STOM_CLI_DB_OPTUNA"] = str(optuna)
        for raw_path in self.spec.market_db_paths:
            market_path = Path(raw_path).expanduser().resolve()
            variable = _MARKET_ENV_BY_NAME.get(market_path.name.lower())
            if variable is None:
                raise ValueError(f"unsupported native market DB: {market_path.name}")
            if variable in environment and Path(environment[variable]).resolve() != market_path:
                raise ValueError(f"duplicate native market DB binding: {variable}")
            environment[variable] = str(market_path)
        return environment

    def verify_operational_unchanged(self) -> dict[str, Any]:
        if not self._before and self.receipt_path.exists():
            receipt = json.loads(self.receipt_path.read_text(encoding="utf-8"))
            self._before = receipt.get("operational_fingerprints_before") or {}
            self._sidefiles_before = receipt.get("sidefiles_before") or {}
        after: dict[str, Any] = {}
        for raw_path, before in self._before.items():
            current = sqlite_fingerprint(raw_path)
            after[raw_path] = current
            if current != before:
                raise RuntimeError(f"operational source changed: {raw_path}")
            assert_sqlite_sidefiles_unchanged(raw_path, self._sidefiles_before[raw_path])
        receipt = json.loads(self.receipt_path.read_text(encoding="utf-8"))
        receipt["operational_fingerprints_after"] = after
        receipt["sidefiles_after"] = {
            raw_path: sqlite_sidefile_snapshot(raw_path) for raw_path in self._before
        }
        self._write_receipt(receipt)
        return receipt

    def run_subprocess(self, argv: list[str], *, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
        if not argv or timeout_seconds <= 0:
            raise ValueError("native subprocess command and positive timeout are required")
        environment = self.environment()
        receipt = json.loads(self.receipt_path.read_text(encoding="utf-8"))
        receipt["status"] = NativeTerminalStatus.RUNNING.value
        receipt["argv"] = list(argv)
        receipt["timeout_seconds"] = timeout_seconds
        self._write_receipt(receipt)
        try:
            completed = subprocess.run(
                argv,
                cwd=Path(__file__).resolve().parents[2],
                env=environment,
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            receipt["status"] = NativeTerminalStatus.RUNNER_TIMEOUT.value
            self._write_receipt(receipt)
            self.verify_operational_unchanged()
            raise
        receipt["returncode"] = completed.returncode
        receipt["status"] = (
            NativeTerminalStatus.ENGINE_SUCCESS.value
            if completed.returncode == 0
            else NativeTerminalStatus.EXECUTION_FAILURE.value
        )
        receipt["stdout_tail"] = completed.stdout[-4000:]
        receipt["stderr_tail"] = completed.stderr[-4000:]
        self._write_receipt(receipt)
        self.verify_operational_unchanged()
        return completed

    def _write_receipt(self, receipt: dict[str, Any]) -> None:
        temporary = self.receipt_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self.receipt_path)
