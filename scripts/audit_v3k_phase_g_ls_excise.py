from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CODE_TARGETS = (
    "strategy/v3k_microstructure_engine.py",
    "scripts/smoke_v3k_phase_g_engine_unit.py",
    "scripts/backtest_v3k_phase_g_parity.py",
    "scripts/benchmark_v3k_phase_g_engine.py",
)

FORBIDDEN_MARKERS = (
    "LSOPEN" + "API",
    "lsopen" + "api",
    "LS" + "Api",
    "LS" + " API",
    "xing" + "api",
    "e" + "best",
    "restapi_" + "ls",
    "ls_" + "securities",
)

FORBIDDEN_IMPORT_PREFIXES = (
    "trade",
    "receiver",
)

FORBIDDEN_RUNTIME_TOKENS = (
    "_database",
    "sqlite3",
    "KiwoomAPI",
    "SendOrder",
    "주문",
    "청산",
)


def _python_import_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def main() -> None:
    hits: list[str] = []
    for rel_path in CODE_TARGETS:
        path = ROOT / rel_path
        if not path.is_file():
            hits.append(f"missing target: {rel_path}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in FORBIDDEN_MARKERS:
            if marker in text:
                hits.append(f"{rel_path}: forbidden broker marker {marker}")
        for token in FORBIDDEN_RUNTIME_TOKENS:
            if token in text:
                hits.append(f"{rel_path}: forbidden runtime token {token}")
        imports = _python_import_roots(path)
        for prefix in FORBIDDEN_IMPORT_PREFIXES:
            if prefix in imports:
                hits.append(f"{rel_path}: forbidden import root {prefix}")

    from strategy.v3k_microstructure_engine import V3KMicrostructureEngine

    engine = V3KMicrostructureEngine()
    if engine.enabled:
        hits.append("V3KMicrostructureEngine must be default-OFF")

    if hits:
        raise AssertionError("phase g excise audit failed:\n" + "\n".join(hits))

    print("V3K Phase G excise audit passed")
    print("Targets:")
    for rel_path in CODE_TARGETS:
        print(f"  - {rel_path}")


if __name__ == "__main__":
    main()
