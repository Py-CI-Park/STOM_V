"""V3U attr inventory 3-way diff (재발 방지 액션 §5-1 + §5-2 통합).

세 가지 source의 attr inventory를 추출하고 차이를 분석한다.

| Source | 의미 |
|---|---|
| **2U attr** (`STOM_V.wt-2u/ui/ui_mainwindow.py`) | V2 pyd 추론 노하우 (검증된 패턴) |
| **V3 external refs** (`ui/event_click/`, `ui/update_widget/`, `trade/`, ...) | V3가 외부에서 참조하는 `ui.X` 모음 |
| **V3U init** (`ui/main_window.py`) | 우리가 init한 모든 `self.X` |

핵심 출력 (drift 우선순위):

1. **CRITICAL drift**: V3 external이 참조하는데 V3U init에 없음 → 외부 코드가 깨짐.
2. **WARN drift**: 2U에는 있고 V3 external에서도 참조 가능한데 V3U init에 없음.
3. **INFO**: 2U-only (V2/Kiwoom 전용일 가능성), V3U-only (V3U 추가 자체 attr).

Constraint:
- V3 official source 0줄 수정 검증 (의도 외 source 디렉토리는 inventory 입력만)
- pytest 회귀 테스트로 변환 가능한 JSON 출력
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

# QObject 시스템 메서드/widget builder 산출물 등은 init 누락으로 분류하지 않는다.
_BUILTIN_QOBJECT = frozenset({
    "close", "show", "hide", "isVisible", "raise_", "activateWindow",
    "setCentralWidget", "setWindowTitle", "update", "repaint", "setStyleSheet",
    "setEnabled", "width", "height", "move", "resize", "setGeometry", "geometry",
    "setFocus", "setMaximumSize", "setMinimumSize", "saveGeometry", "restoreGeometry",
    "setPalette", "setIcon", "setFont", "setVisible", "grab", "deleteLater",
    "disconnect", "installEventFilter", "removeEventFilter", "setWindowState",
    "windowState", "x", "y", "isMinimized", "isMaximized", "showNormal",
    "showMaximized", "showMinimized", "setAcceptDrops", "metaObject", "parent",
    "children", "findChild", "findChildren", "sender", "setObjectName", "objectName",
    "isFullScreen", "showFullScreen", "setMouseTracking", "setContextMenuPolicy",
    "setAttribute", "window", "setWindowFlags", "windowFlags", "setWindowIcon",
    "windowIcon", "setWindowOpacity", "connect", "emit", "setMaximum", "setMinimum",
    "setValue", "value", "setText", "text", "count", "setSizePolicy", "sizePolicy",
    "setLayout", "layout", "setMaximumWidth", "setMaximumHeight", "setMinimumWidth",
    "setMinimumHeight", "setSpacing", "setMargin", "setContentsMargins", "isHidden",
    "setHidden", "menuBar", "statusBar", "setMenuBar", "setStatusBar",
    "centralWidget", "setupUi", "retranslateUi", "tr", "format", "insert", "item",
    "itemAt", "insertItem", "addItem", "removeItem", "clearSpacing", "spacing",
    "widthMM", "heightMM", "thread", "blockSignals", "signalsBlocked", "addWidget",
    "addLayout", "stretchFactor", "alignment", "setAlignment",
})

# 위젯 build로 생성되는 attr 접미사 패턴 (init 누락으로 분류하지 않는다)
_WIDGET_SUFFIX_RE = re.compile(
    r"(_pushButton|_pushButtonn|_pushButtonnn|_Button_|_labellllllll|_labell|_labelllllll|"
    r"_lineEdit|_lineEdittt|_lineEditttt|_lineEdittttt|_textEditxxxx|_textEditttt|_textEdit|"
    r"_comboBoxxxxx|_comboBoxxxx|_groupBoxxxxx|_groupBoxxx|_groupBox|_dateEdittttt|"
    r"_checkBoxxxxx|_tableWidget|_dcomboBoxxxx|_dlineEdittt|_radioButton|_spinBoxxxxx|"
    r"_progressBarrr|_progressBar|_treeWidget|_tabWidget|_listWidget|_scrollArea|"
    r"_layout|_btnnn|_boxxxx|_pbtnnn|"
    r"_label\b|_button\b|_widget\b|_combo\b|_check\b|_radio\b|_edit\b|_tab\b|"
    r"_panel\b|_frame\b|_groupbox\b|_layout\b)"
)

# Qt 내장 위젯 메서드 (focusWidget, setFixedSize, winId 등)
_QT_INTERNAL = frozenset({
    "focusWidget", "activeWindow", "topLevelWidget", "parentWidget", "nativeParentWidget",
    "frameGeometry", "size", "pos", "rect", "frameSize", "minimumSize", "maximumSize",
    "setFixedSize", "setFixedWidth", "setFixedHeight", "winId", "main_window",
    "centralWidget", "menuBar", "statusBar",
})

# V3 모듈 namespace (`ui.etcetera`, `ui.event_click` 등 — 모듈 import path)
_MODULE_NAMESPACES = frozenset({
    "etcetera", "event_activate", "event_change", "event_click", "event_keypress",
    "event_doubleclick", "set_style", "draw_chart", "create_widget", "update_widget",
    "event_filter",
})

# 사용자 위젯 카테고리 prefix (Coin*, Stock*, Pyd*, Legacy* 등 V2/Kiwoom 메서드 패턴)
_V2_LEGACY_PREFIX_RE = re.compile(
    r"^self\.(Bind|Cleanup|Coin|Stock|Pyd|Legacy|Restore|Save|Get|Handle|Indicator|Setting|Stg|Sv|Sd)[A-Z]"
)


def extract_self_attrs(file_path: Path) -> set[str]:
    """파이썬 파일에서 self.X attr 이름을 추출한다 (set).

    정적 `self.X` + 동적 `setattr(self, "X", ...)` + 클래스 메서드 정의 모두 포함.
    """
    if not file_path.is_file():
        return set()
    text = file_path.read_text(encoding="utf-8", errors="replace")
    attrs = {m.group(0) for m in re.finditer(r"self\.[a-zA-Z_][a-zA-Z0-9_]+", text)}
    # setattr(self, "name", ...) 또는 setattr(self, 'name', ...) 패턴
    for m in re.finditer(r"setattr\(\s*self\s*,\s*['\"]([a-zA-Z_][a-zA-Z0-9_]+)['\"]", text):
        attrs.add(f"self.{m.group(1)}")
    # for name in ("a", "b"): setattr(self, name, ...)
    for m in re.finditer(
        r"for\s+\w+\s+in\s+\(([^)]+)\)\s*:\s*setattr\(\s*self",
        text,
    ):
        for q in re.finditer(r"['\"]([a-zA-Z_][a-zA-Z0-9_]+)['\"]", m.group(1)):
            attrs.add(f"self.{q.group(1)}")
    # 클래스 메서드 정의 `def name(self, ...):` — instance attr로 접근 가능
    for m in re.finditer(r"^\s+def\s+([a-zA-Z_][a-zA-Z0-9_]+)\s*\(\s*self\b", text, re.MULTILINE):
        attrs.add(f"self.{m.group(1)}")
    return attrs


def extract_external_ui_refs(*dirs: Path) -> set[str]:
    """주어진 디렉토리들의 .py 파일에서 ui.X 참조를 self.X 형식으로 변환해 set 반환."""
    refs: set[str] = set()
    for d in dirs:
        if not d.is_dir():
            continue
        for py in d.rglob("*.py"):
            try:
                text = py.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for m in re.finditer(r"\bui\.([a-zA-Z_][a-zA-Z0-9_]+)", text):
                refs.add(f"self.{m.group(1)}")
    return refs


def extract_widget_builder_setattrs(*dirs: Path) -> set[str]:
    """widget builder(set_*.py, dialog_*.py 등)가 setattr하는 ui.X / self.ui.X 추출.

    이 attr은 _build_v3_widgets 실행 후 MainWindow에 부착되므로 _init_runtime_state에서
    별도 init할 필요가 없다. CRITICAL drift에서 제외해야 false positive 방지.
    """
    builder_attrs: set[str] = set()
    patterns = [
        re.compile(r"\bself\.ui\.([a-zA-Z_][a-zA-Z0-9_]+)\s*="),
        re.compile(r"\bui\.([a-zA-Z_][a-zA-Z0-9_]+)\s*="),
    ]
    for d in dirs:
        if not d.is_dir():
            continue
        for py in d.rglob("*.py"):
            try:
                text = py.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for pat in patterns:
                for m in pat.finditer(text):
                    builder_attrs.add(f"self.{m.group(1)}")
    return builder_attrs


def is_builtin_or_widget(attr: str) -> bool:
    name = attr.split(".", 1)[1]
    if name in _BUILTIN_QOBJECT or name in _QT_INTERNAL:
        return True
    if name in _MODULE_NAMESPACES:
        return True
    if _WIDGET_SUFFIX_RE.search(attr):
        return True
    return False


def is_v2_legacy_method(attr: str) -> bool:
    return bool(_V2_LEGACY_PREFIX_RE.match(attr))


def classify(
    *,
    twou: set[str],
    v3_external: set[str],
    v3u_init: set[str],
    v3_widget_setattrs: set[str],
) -> dict[str, list[str]]:
    """3-way diff 분류 + widget builder setattr 보정."""
    critical: set[str] = set()
    warn: set[str] = set()
    info_2u_only: set[str] = set()
    info_v3u_extra: set[str] = set()

    # widget builder가 setattr하면 init 불필요 (외부 참조는 OK)
    effective_present = v3u_init | v3_widget_setattrs

    # CRITICAL: V3 external 참조하는데 V3U init/widget setattr 모두 없음
    for attr in v3_external - effective_present:
        if is_builtin_or_widget(attr) or is_v2_legacy_method(attr):
            continue
        critical.add(attr)

    # WARN: 2U에 있고 V3 external에서도 참조 (확실히 필요한 패턴이지만 V3U 누락)
    for attr in (twou & v3_external) - effective_present:
        if attr in critical:
            continue
        if is_builtin_or_widget(attr) or is_v2_legacy_method(attr):
            continue
        warn.add(attr)

    # INFO: 2U-only (V2/Kiwoom 전용일 가능성)
    for attr in twou - effective_present - v3_external:
        if is_builtin_or_widget(attr) or is_v2_legacy_method(attr):
            continue
        info_2u_only.add(attr)

    # INFO: V3U-only (V3U 자체 추가)
    for attr in v3u_init - twou:
        if is_builtin_or_widget(attr) or is_v2_legacy_method(attr):
            continue
        info_v3u_extra.add(attr)

    return {
        "critical": sorted(critical),
        "warn": sorted(warn),
        "info_2u_only": sorted(info_2u_only),
        "info_v3u_extra": sorted(info_v3u_extra),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="V3U attr inventory 3-way diff (재발 방지 §5-1+§5-2 통합 도구)"
    )
    parser.add_argument(
        "--twou",
        default="C:/System_Trading/STOM/STOM_V.wt-2u/ui/ui_mainwindow.py",
        help="2U 추론본 경로 (V2 pyd 추론 노하우 source)",
    )
    parser.add_argument(
        "--v3u-init",
        default="ui/main_window.py",
        help="V3U MainWindow init source",
    )
    parser.add_argument(
        "--v3-external-dirs",
        nargs="+",
        default=[
            "ui/event_click", "ui/event_keypress", "ui/update_widget",
            "ui/draw_chart", "ui/etcetera", "ui/create_widget",
            "trade", "utility/sub_process_and_thread",
        ],
        help="V3 외부 코드 디렉토리 (ui.X 참조 추출 대상)",
    )
    parser.add_argument(
        "--output",
        default=".omx/logs/v3u/attr_inventory_diff.json",
        help="JSON 출력 경로",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="CRITICAL drift가 있으면 exit code 1로 종료 (CI/회귀 테스트용)",
    )
    parser.add_argument(
        "--max-critical",
        type=int,
        default=0,
        help="허용 CRITICAL drift 최대 개수 (--strict 모드에서만 유효, 기본 0)",
    )
    args = parser.parse_args(argv)

    root = Path.cwd()
    twou_path = Path(args.twou)
    v3u_path = root / args.v3u_init
    ext_dirs = [root / d for d in args.v3_external_dirs]

    twou = extract_self_attrs(twou_path)
    v3u = extract_self_attrs(v3u_path)
    external = extract_external_ui_refs(*ext_dirs)
    # widget builder가 setattr하는 attr은 init 불필요 (false positive 방지)
    # V3 외부 디렉토리 전부 포함 — event_click 같은 곳에서도 setattr 가능
    builder_dirs = ext_dirs + [
        root / "ui/create_widget",
        root / "ui/draw_chart",
        root / "ui/update_widget",
        root / "ui/etcetera",
    ]
    widget_setattrs = extract_widget_builder_setattrs(*builder_dirs)

    classification = classify(
        twou=twou, v3_external=external, v3u_init=v3u,
        v3_widget_setattrs=widget_setattrs,
    )

    payload = {
        "sources": {
            "twou_path": str(twou_path),
            "twou_count": len(twou),
            "v3u_init_path": str(v3u_path),
            "v3u_init_count": len(v3u),
            "v3_external_dirs": [str(d) for d in ext_dirs],
            "v3_external_count": len(external),
            "v3_widget_setattr_count": len(widget_setattrs),
        },
        "diff": classification,
        "summary": {
            "critical_count": len(classification["critical"]),
            "warn_count": len(classification["warn"]),
            "info_2u_only_count": len(classification["info_2u_only"]),
            "info_v3u_extra_count": len(classification["info_v3u_extra"]),
        },
    }

    output_path = root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[INFO] V3U attr inventory diff: {output_path}")
    summary = payload["summary"]
    print(
        f"[INFO] critical={summary['critical_count']} "
        f"warn={summary['warn_count']} "
        f"info_2u_only={summary['info_2u_only_count']} "
        f"info_v3u_extra={summary['info_v3u_extra_count']}"
    )
    if classification["critical"]:
        print("[CRITICAL] V3 external 참조하나 V3U init에 없음:")
        for attr in classification["critical"][:30]:
            print(f"  - {attr}")
        if len(classification["critical"]) > 30:
            print(f"  ... and {len(classification['critical']) - 30} more")

    if args.strict and len(classification["critical"]) > args.max_critical:
        print(f"[FAIL] CRITICAL drift {len(classification['critical'])} > max {args.max_critical}")
        return 1
    print("[OK] V3U attr inventory diff completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
