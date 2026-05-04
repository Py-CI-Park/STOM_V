from __future__ import annotations

import re
from dataclasses import dataclass, asdict
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


MAIN_MENU_ITEMS = [
    ("main_menu", "home", "Home(Ctrl+1)", "pushButton_00"),
    ("main_menu", "stock_future_trader", "stock/futures trader(Ctrl+2)", "pushButton_01"),
    ("main_menu", "coin_trader", "Upbit/Binance trader(Ctrl+3)", "pushButton_02"),
    ("main_menu", "stock_future_strategy", "stock/futures strategy(Ctrl+4)", "pushButton_03"),
    ("main_menu", "coin_strategy", "Upbit/Binance strategy(Ctrl+5)", "pushButton_04"),
    ("main_menu", "stom_live", "STOM live(Ctrl+6)", "pushButton_05"),
    ("main_menu", "log", "log(Ctrl+7)", "pushButton_06"),
    ("main_menu", "settings", "settings(Ctrl+8)", "pushButton_07"),
]


MAJOR_DIALOG_ATTRS = {
    "dialog_db": "STOM DATABASE",
    "dialog_chart": "STOM CHART",
    "dialog_hoga": "STOM HOGA",
    "dialog_scheduler": "STOM BACKTEST SCHEDULER",
    "dialog_order": "STOM ORDER",
    "dialog_strategy": "STOM STRATEGY",
    "dialog_backengine": "STOM BACKTEST ENGINE",
    "dialog_optuna": "STOM OPTUNA",
    "dialog_std": "OPTIMIZ STD LIMIT",
    "dialog_leverage": "BINANCE FUTURE LEVERAGE",
    "dialog_setsj": "STOM SETSJ",
    "dialog_cetsj": "STOM CETSJ",
    "dialog_comp": "STOM COMPARISON",
    "dialog_kimp": "STOM KIMP",
    "dialog_tree": "STOM TREEMAP",
    "dialog_info": "STOM INFO",
    "dialog_web": "STOM WEB",
    "dialog_stg_input1": "strategy custom button settings 1",
    "dialog_stg_input2": "strategy custom button settings 2",
}


STRATEGY_BUTTON_SOURCES = [
    "ui/set_stg_stock_tap.py",
    "ui/set_stg_coin_tap.py",
    "ui/set_stg_unified_tap.py",
]

MAJOR_BUTTON_SOURCES = [
    *STRATEGY_BUTTON_SOURCES,
    "ui/set_setup_tap.py",
    "ui/set_dialog_back.py",
]

TAB_SOURCES = [
    "ui/set_setup_tap.py",
    "ui/set_dialog_etc.py",
]

RUNTIME_STATE_ATTRS = [
    ("runtime_state", "trading", "trading flag", "trading"),
    ("runtime_state", "ctpg_code", "current chart code", "ctpg_code"),
    ("runtime_state", "canvas", "treemap canvas", "canvas"),
    ("runtime_state", "saqsize", "stock agent queue size", "saqsize"),
    ("runtime_state", "stqsize", "stock trader queue size", "stqsize"),
    ("runtime_state", "ssqsize", "stock strategy queue size", "ssqsize"),
]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def _safe_id(text: str) -> str:
    value = re.sub(r"[^0-9A-Za-z가-힣_]+", "_", text).strip("_")
    return value or "item"


def _iter_existing(root: Path, relatives: list[str]) -> list[Path]:
    return [root / relative for relative in relatives if (root / relative).exists()]


def parse_pushbuttons(root: Path, relatives: list[str], category: str) -> list[ContractItem]:
    items: list[ContractItem] = []
    pattern = re.compile(
        r"self\.ui\.(?P<attr>[A-Za-z0-9_]+)\s*=\s*self\.wc\.setPushbutton\((?P<quote>['\"])(?P<label>.*?)(?P=quote)",
    )
    for path in _iter_existing(root, relatives):
        rel = path.relative_to(root).as_posix()
        for match in pattern.finditer(read_text(path)):
            attr = match.group("attr")
            label = match.group("label")
            item_id = f"{rel}:{attr}"
            items.append(ContractItem(category, item_id, label, attr, rel))
    return items


def parse_dialogs(root: Path) -> list[ContractItem]:
    items: list[ContractItem] = []
    dialog_sources = [path.relative_to(root).as_posix() for path in (root / "ui").glob("set_dialog*.py")]
    pattern = re.compile(
        r"self\.ui\.(?P<attr>dialog_[A-Za-z0-9_]+)\s*=\s*self\.wc\.setDialog\((?P<quote>['\"])(?P<label>.*?)(?P=quote)",
    )
    seen: set[str] = set()
    for path in _iter_existing(root, dialog_sources):
        rel = path.relative_to(root).as_posix()
        for match in pattern.finditer(read_text(path)):
            attr = match.group("attr")
            if attr in seen:
                continue
            seen.add(attr)
            label = MAJOR_DIALOG_ATTRS.get(attr, match.group("label"))
            items.append(ContractItem("dialog", attr, label, attr, rel, attr in MAJOR_DIALOG_ATTRS))

    for attr, label in MAJOR_DIALOG_ATTRS.items():
        if attr not in seen:
            items.append(ContractItem("dialog", attr, label, attr, "manifest", True))
    return items


def parse_tabs(root: Path) -> list[ContractItem]:
    items: list[ContractItem] = []
    pattern = re.compile(r"\.addTab\([^,]+,\s*(?P<quote>['\"])(?P<label>.*?)(?P=quote)\)")
    for path in _iter_existing(root, TAB_SOURCES):
        rel = path.relative_to(root).as_posix()
        for index, match in enumerate(pattern.finditer(read_text(path)), start=1):
            label = match.group("label")
            item_id = f"{rel}:tab:{index}:{_safe_id(label)}"
            items.append(ContractItem("tab", item_id, label, None, rel))
    return items


def build_contract(root: Path) -> list[ContractItem]:
    items = [
        ContractItem(category, item_id, label, attr, "ui/set_main_menu.py")
        for category, item_id, label, attr in MAIN_MENU_ITEMS
    ]
    items.extend(
        ContractItem(category, item_id, label, attr, "ui/ui_mainwindow.py")
        for category, item_id, label, attr in RUNTIME_STATE_ATTRS
    )
    items.extend(parse_dialogs(root))
    items.extend(parse_tabs(root))
    items.extend(parse_pushbuttons(root, STRATEGY_BUTTON_SOURCES, "strategy_button"))
    items.extend(parse_pushbuttons(root, ["ui/set_dialog_strategy.py"], "strategy_dialog_button"))
    items.extend(parse_pushbuttons(root, ["ui/set_dialog_back.py"], "backtest_button"))
    items.extend(parse_pushbuttons(root, ["ui/set_setup_tap.py"], "settings_button"))

    unique: dict[tuple[str, str], ContractItem] = {}
    for item in items:
        unique[(item.category, item.item_id)] = item
    return list(unique.values())


def contract_summary(items: list[ContractItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.category] = counts.get(item.category, 0) + 1
    return counts

