from __future__ import annotations

import ast
import hashlib
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "ai_strategy_loop" / "brain" / "data" / "chart_sulsa_v7_conditions.json"
MAIN_DB = ROOT / "_database" / "strategy.db"
LOOP_DB = ROOT / "ai_strategy_loop" / "state" / "loop_strategies.db"
ENGINE = ROOT / "backtest" / "backengine_base.py"
OUT = (
    ROOT
    / ".omo"
    / "evidence"
    / "css-v7-root-cause-before-plan-b-20260703"
    / "r1-static-runtime-audit.json"
)


@dataclass(frozen=True)
class CallSite:
    method: str
    line: int
    arg_count: int


class BuySellVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.calls: list[CallSite] = []

    def visit_Call(self, node: ast.Call) -> Any:
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr in {"Buy", "Sell"}
            and isinstance(func.value, ast.Name)
            and func.value.id == "self"
        ):
            self.calls.append(CallSite(func.attr, node.lineno, len(node.args)))
        self.generic_visit(node)


class DummyQueue:
    def __init__(self) -> None:
        self.events: list[str] = []

    def put(self, item: object) -> None:
        self.events.append(repr(item))


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_catalog() -> dict[str, Any]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def table_for(side: str) -> str:
    return "stockbuy" if side == "buy" else "stocksell"


def read_db_code(db_path: Path, table: str, name: str) -> str | None:
    if not db_path.exists():
        return None
    con = sqlite3.connect(db_path)
    try:
        cols = [row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()]
        if len(cols) < 2:
            return None
        row = con.execute(
            f'SELECT "{cols[1]}" FROM {table} WHERE "index" = ?',
            (name,),
        ).fetchone()
        return row[0] if row else None
    finally:
        con.close()


def inspect_calls(code: str) -> tuple[list[dict[str, int | str]], str | None]:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [], f"{exc.__class__.__name__}: {exc}"
    visitor = BuySellVisitor()
    visitor.visit(tree)
    return [call.__dict__ for call in visitor.calls], None


def engine_contract() -> dict[str, dict[str, int]]:
    tree = ast.parse(ENGINE.read_text(encoding="utf-8"))
    result: dict[str, dict[str, int]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != "BackEngineBase":
            continue
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name in {"Buy", "Sell"}:
                positional = [a.arg for a in item.args.args]
                user_args = [arg for arg in positional if arg != "self"]
                defaults = len(item.args.defaults)
                required = max(0, len(user_args) - defaults)
                result[item.name] = {
                    "required_positional_args": required,
                    "max_positional_args": len(user_args),
                    "line": item.lineno,
                }
    return result


def compile_gate(code: str, side: str) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT))
    from backtest.back_static import GetBuyStg, GetSellStg

    queue = DummyQueue()
    if side == "buy":
        compiled, _indicator = GetBuyStg(code, 0, queue)
    else:
        compiled, _dict_cond = GetSellStg(code, 0, queue)
    return {"compiled": compiled is not None, "events": queue.events}


def main() -> int:
    catalog = load_catalog()
    contract = engine_contract()
    rows = []
    mismatches = []
    invalid_calls = []

    for condition in catalog["conditions"]:
        name = condition["id"]
        side = condition["side"]
        code = condition["code"]
        table = table_for(side)
        calls, ast_error = inspect_calls(code)
        compile_result = compile_gate(code, side)
        row = {
            "id": name,
            "side": side,
            "lane": condition.get("lane"),
            "catalog_sha_expected": condition.get("code_sha256"),
            "catalog_sha_actual": sha_text(code),
            "main_db_sha": None,
            "loop_db_sha": None,
            "main_db_present": False,
            "loop_db_present": False,
            "catalog_sha_match": condition.get("code_sha256") == sha_text(code),
            "main_db_matches_catalog": False,
            "loop_db_matches_catalog": False,
            "compile_gate": compile_result,
            "ast_error": ast_error,
            "self_buy_sell_calls": calls,
            "invalid_runtime_calls": [],
        }

        for db_label, db_path in (("main", MAIN_DB), ("loop", LOOP_DB)):
            db_code = read_db_code(db_path, table, name)
            row[f"{db_label}_db_present"] = db_code is not None
            if db_code is not None:
                db_sha = sha_text(db_code)
                row[f"{db_label}_db_sha"] = db_sha
                row[f"{db_label}_db_matches_catalog"] = db_sha == row["catalog_sha_actual"]

        for call in calls:
            allowed = contract.get(call["method"], {}).get("max_positional_args")
            if allowed is None or call["arg_count"] > allowed:
                defect = {
                    "id": name,
                    "method": call["method"],
                    "line": call["line"],
                    "arg_count": call["arg_count"],
                    "engine_max_positional_args": allowed,
                }
                row["invalid_runtime_calls"].append(defect)
                invalid_calls.append(defect)

        if not row["catalog_sha_match"] or not row["main_db_matches_catalog"] or not row["loop_db_matches_catalog"]:
            mismatches.append(name)
        rows.append(row)

    summary = {
        "catalog_path": str(CATALOG.relative_to(ROOT)),
        "catalog_sha256": hashlib.sha256(CATALOG.read_bytes()).hexdigest(),
        "condition_count": len(rows),
        "engine_contract": contract,
        "catalog_sha_mismatch_count": sum(1 for row in rows if not row["catalog_sha_match"]),
        "main_db_mismatch_count": sum(1 for row in rows if not row["main_db_matches_catalog"]),
        "loop_db_mismatch_count": sum(1 for row in rows if not row["loop_db_matches_catalog"]),
        "compile_gate_fail_count": sum(1 for row in rows if not row["compile_gate"]["compiled"]),
        "invalid_runtime_call_condition_count": len({item["id"] for item in invalid_calls}),
        "invalid_runtime_call_count": len(invalid_calls),
        "invalid_runtime_call_ids": sorted({item["id"] for item in invalid_calls}),
        "mismatch_ids": mismatches,
    }
    report = {"summary": summary, "conditions": rows}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
