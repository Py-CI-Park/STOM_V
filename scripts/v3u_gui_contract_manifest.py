from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ContractItem:
    category: str
    item_id: str
    label: str
    attr: str | None
    source: str
    required: bool = True

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


V3_PYD_TARGET = "ui/main_window.pyd"
V3_PY_TARGET = "ui/main_window.py"
V3_IMPORT_CONTRACT = "ui.main_window.MainWindow"

CREATE_WIDGET_SOURCES = [
    "ui/create_widget/set_main_menu.py",
    "ui/create_widget/set_table.py",
    "ui/create_widget/set_widget.py",
    "ui/create_widget/set_setup_tap.py",
    "ui/create_widget/set_order_tap.py",
    "ui/create_widget/set_stg_tap.py",
    "ui/create_widget/set_home_tap.py",
    "ui/create_widget/set_log_tap.py",
    "ui/create_widget/set_icon.py",
    "ui/create_widget/set_text.py",
    "ui/create_widget/set_text_stg_button.py",
    "ui/create_widget/set_dialog_back.py",
    "ui/create_widget/set_dialog_chart.py",
    "ui/create_widget/set_dialog_etc.py",
    "ui/create_widget/set_dialog_formula.py",
    "ui/create_widget/set_dialog_strategy.py",
]

EVENT_SOURCES = [
    "ui/event_click",
    "ui/event_activate",
    "ui/event_change",
    "ui/event_keypress",
    "ui/update_widget",
    "ui/draw_chart",
    "ui/etcetera",
]

RUNTIME_STATE_ATTRS = [
    ("runtime_state", "proc_receiver", "receiver process handle", "proc_receiver"),
    ("runtime_state", "proc_trader", "trader process handle", "proc_trader"),
    ("runtime_state", "proc_strategys", "strategy process list", "proc_strategys"),
    ("runtime_state", "proc_backtester_bs", "backtester process handle", "proc_backtester_bs"),
    ("runtime_state", "webEngineView", "web dialog engine view", "webEngineView"),
    ("runtime_state", "dialog_list", "dialog registry", "dialog_list"),
    ("runtime_state", "main_btn_list", "main menu buttons", "main_btn_list"),
    ("runtime_state", "main_box_list", "main tab boxes", "main_box_list"),
    ("runtime_state", "ctpg_code", "current chart code", "ctpg_code"),
    ("runtime_state", "database_chart", "database chart mode flag", "database_chart"),
]

MAJOR_DIALOG_ATTRS = {
    "dialog_db": "STOM DATABASE",
    "dialog_chart": "STOM CHART",
    "dialog_hoga": "STOM HOGA",
    "dialog_scheduler": "STOM BACKTEST SCHEDULER",
    "dialog_order": "STOM ORDER",
    "dialog_strategy": "STOM STRATEGY",
    "dialog_backengine": "STOM BACKTEST ENGINE",
    "dialog_formula": "STOM FORMULA",
    "dialog_factor": "STOM FACTOR",
    "dialog_info": "STOM INFO",
    "dialog_web": "STOM WEB",
    "dialog_giup": "STOM COMPANY INFO",
    "dialog_kimp": "STOM KIMP",
    "dialog_tree": "STOM TREEMAP",
    "radar_dialog": "STOM MICROSTRUCTURE RADAR",
}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def safe_id(text: str) -> str:
    value = re.sub(r"[^0-9A-Za-z_]+", "_", text).strip("_")
    return value or "item"


def iter_existing(root: Path, relatives: list[str]) -> list[Path]:
    return [root / relative for relative in relatives if (root / relative).exists()]


def iter_python_files(root: Path, relatives_or_dirs: list[str]) -> list[Path]:
    files: list[Path] = []
    for relative in relatives_or_dirs:
        path = root / relative
        if path.is_dir():
            files.extend(sorted(path.glob("*.py")))
        elif path.exists():
            files.append(path)
    return files


def parse_created_attrs(root: Path) -> list[ContractItem]:
    items: list[ContractItem] = []
    assignment = re.compile(r"self\.ui\.(?P<attr>[A-Za-z0-9_]+)\s*=")
    factory = re.compile(r"self\.wc\.(?P<factory>set[A-Za-z0-9_]+)\(")
    for path in iter_existing(root, CREATE_WIDGET_SOURCES):
        rel = path.relative_to(root).as_posix()
        text = read_text(path)
        for line_no, line in enumerate(text.splitlines(), start=1):
            attr_match = assignment.search(line)
            if not attr_match:
                continue
            attr = attr_match.group("attr")
            factory_match = factory.search(line)
            label = factory_match.group("factory") if factory_match else "created attr"
            category = "created_widget"
            if attr.startswith("dialog_") or attr == "radar_dialog":
                category = "dialog"
                label = MAJOR_DIALOG_ATTRS.get(attr, label)
            elif "push" in attr.lower() or "button" in attr.lower():
                category = "button"
            elif "combo" in attr.lower():
                category = "combobox"
            elif "table" in attr.lower():
                category = "table"
            elif "tab" in attr.lower():
                category = "tab_or_group"
            items.append(ContractItem(category, f"{rel}:{line_no}:{attr}", label, attr, rel))
    return items


def parse_event_referenced_attrs(root: Path) -> list[ContractItem]:
    items: list[ContractItem] = []
    attr_pattern = re.compile(r"\bui\.([A-Za-z_][A-Za-z0-9_]*)")
    for path in iter_python_files(root, EVENT_SOURCES):
        rel = path.relative_to(root).as_posix()
        seen: set[str] = set()
        for match in attr_pattern.finditer(read_text(path)):
            attr = match.group(1)
            if attr in seen:
                continue
            seen.add(attr)
            items.append(ContractItem("referenced_attr", f"{rel}:{attr}", attr, attr, rel, False))
    return items


def parse_signal_function_names(root: Path) -> list[ContractItem]:
    items: list[ContractItem] = []
    for path in iter_python_files(root, ["ui/event_click", "ui/event_activate", "ui/event_change", "ui/event_keypress"]):
        rel = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(read_text(path))
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith(("activated_", "bactivated_", "dactivated_", "cell_clicked", "mnbutton", "button", "checkbox", "text", "return_press", "keypress")) or "clicked" in node.name:
                    items.append(ContractItem("event_function", f"{rel}:{node.name}", node.name, None, rel, False))
    return items


def mainwindow_contract_items(root: Path) -> list[ContractItem]:
    return [
        ContractItem("pyd_target", V3_PYD_TARGET, "V3 official pyd target", V3_PYD_TARGET, "manifest", True),
        ContractItem("python_target", V3_PY_TARGET, "V3U pyd-free MainWindow target", V3_PY_TARGET, "manifest", True),
        ContractItem("import_contract", V3_IMPORT_CONTRACT, "stom.py imports MainWindow from ui.main_window", "MainWindow", "stom.py", True),
    ]


def build_contract(root: Path) -> list[ContractItem]:
    items: list[ContractItem] = []
    items.extend(mainwindow_contract_items(root))
    items.extend(ContractItem(category, item_id, label, attr, "ui/main_window.py") for category, item_id, label, attr in RUNTIME_STATE_ATTRS)
    items.extend(parse_created_attrs(root))
    items.extend(parse_event_referenced_attrs(root))
    items.extend(parse_signal_function_names(root))

    unique: dict[tuple[str, str], ContractItem] = {}
    for item in items:
        unique[(item.category, item.item_id)] = item
    return list(unique.values())


def contract_summary(items: list[ContractItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.category] = counts.get(item.category, 0) + 1
    return dict(sorted(counts.items()))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the V3U GUI contract inventory.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--output", default="")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.root).resolve()
    items = build_contract(root)
    payload = {
        "root": str(root),
        "summary": contract_summary(items),
        "items": [item.to_dict() for item in items],
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        output = root / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
        print(f"[INFO] V3U GUI contract inventory: {output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
