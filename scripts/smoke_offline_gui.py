from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from gui_contract_manifest import ContractItem, build_contract, contract_summary


ROOT = Path.cwd()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class OfflineViolation(RuntimeError):
    pass


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


class OfflineGuard:
    def __init__(self) -> None:
        self.events: list[dict[str, str]] = []

    def record(self, kind: str, detail: str) -> None:
        self.events.append({"kind": kind, "detail": detail})

    def violation(self, kind: str, detail: str) -> None:
        self.record(f"blocked_{kind}", detail)
        raise OfflineViolation(f"offline guard blocked {kind}: {detail}")


class DummyProcess:
    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs
        self.started = False

    def start(self) -> None:
        self.started = True

    def is_alive(self) -> bool:
        return False

    def terminate(self) -> None:
        self.started = False

    def join(self, timeout=None) -> None:
        self.started = False


class DummyThreadObject:
    def __init__(self, *args, **kwargs) -> None:
        self.started = False

    def start(self) -> None:
        self.started = True

    def isRunning(self) -> bool:
        return False

    def quit(self) -> None:
        self.started = False

    def wait(self, *args, **kwargs) -> bool:
        self.started = False
        return True

    def terminate(self) -> None:
        self.started = False

    def stop(self) -> None:
        self.started = False


class DummyDatabaseReadOnly:
    def __getattr__(self, name):
        def _method(*args, **kwargs):
            return None

        return _method


class SafeDict(dict):
    def __missing__(self, key):
        text = str(key)
        if "테마" in text:
            value = "다크레드"
        elif "증권사" in text:
            value = "키움증권"
        elif "거래소" in text:
            value = "업비트"
        elif "종료시간" in text:
            value = 153000 if "주식" in text else 235959
        elif "시작시간" in text:
            value = 90000 if "주식" in text else 0
        elif "날짜" in text:
            value = 1
        elif "팩터선택" in text:
            value = "0;1;2;3;4;5;6"
        elif "창위치" in text:
            value = None if text == "창위치" else False
        elif "투자금" in text or "자금" in text:
            value = 20.0
        elif "타임프레임" in text:
            value = True
        else:
            value = False
        self[key] = value
        return value


def smoke_settings() -> SafeDict:
    return SafeDict(
        {
            "테마": "다크레드",
            "증권사": "키움증권",
            "거래소": "업비트",
            "주식에이전트": False,
            "코인리시버": False,
            "주식타임프레임": True,
            "코인타임프레임": True,
            "주식전략종료시간": 153000,
            "코인전략종료시간": 235959,
            "주식투자금": 20.0,
            "코인투자금": 20.0,
            "백테날짜고정": False,
            "백테날짜": 1,
            "창위치기억": False,
            "창위치": None,
            "저해상도": False,
            "팩터선택": "0;1;2;3;4;5;6",
        }
    )


class DummyDrawObject:
    def __init__(self, *args, **kwargs) -> None:
        pass

    def __getattr__(self, name):
        def _method(*args, **kwargs):
            return None

        return _method


def configure_environment() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox --disable-gpu")
    platform.uname()
    platform.system()
    from PyQt5.QtCore import QCoreApplication, Qt

    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)


def install_preimport_guards(guard: OfflineGuard) -> None:
    import socket
    import subprocess
    import urllib.request

    import requests
    import zmq
    from PyQt5.QtCore import QThread

    class BlockedSocket(socket.socket):
        def __new__(cls, *args, **kwargs):
            guard.violation("socket", "socket.socket")

    class BlockedPopen(subprocess.Popen):
        def __init__(self, *args, **kwargs):
            guard.violation("process", "subprocess.Popen")

    def blocked_urlopen(*args, **kwargs):
        guard.violation("network", "urllib.request.urlopen")

    def blocked_request(self, method, url, *args, **kwargs):
        guard.violation("network", f"requests {method} {url}")

    class BlockedZmqSocket:
        def bind(self, endpoint):
            guard.violation("zmq", f"bind {endpoint}")

        def connect(self, endpoint):
            guard.violation("zmq", f"connect {endpoint}")

        def setsockopt_string(self, *args, **kwargs):
            return None

        def close(self):
            return None

    class BlockedZmqContext:
        def socket(self, *args, **kwargs):
            return BlockedZmqSocket()

        def term(self):
            return None

    def mocked_qthread_start(self):
        guard.record("mocked_qthread_start", self.__class__.__name__)
        return None

    socket.socket = BlockedSocket
    subprocess.Popen = BlockedPopen
    urllib.request.urlopen = blocked_urlopen
    requests.sessions.Session.request = blocked_request
    zmq.Context = BlockedZmqContext
    QThread.start = mocked_qthread_start

    import utility.database_check as database_check
    import utility.setting_user as setting_user
    import utility.static as static

    database_check.database_check = lambda: (True, "")
    setting_user.load_settings = smoke_settings
    static.read_key = lambda: guard.violation("credential", "utility.static.read_key")

    guard.record("guards_installed", "pre-import offline guards")


def patch_mainwindow_module(mw, guard: OfflineGuard) -> None:
    def process_factory(*args, **kwargs):
        target = kwargs.get("target")
        if target is None and args:
            target = args[0]
        guard.record("mocked_process", getattr(target, "__name__", str(target)))
        return DummyProcess(*args, **kwargs)

    def qthread_factory(*args, **kwargs):
        guard.record("mocked_qthread_object", "zmq/webcrawling/writer")
        return DummyThreadObject()

    mw.Process = process_factory
    mw.ZmqRecv = qthread_factory
    mw.ZmqServ = qthread_factory
    mw.LiveClient = lambda *args, **kwargs: None
    mw.port_available = lambda port: True
    mw.resolve_stock_python = lambda: (None, [])
    mw.load_database = lambda ui: guard.record("mocked_database_load", "load_database")
    mw.DatabaseReadOnly = DummyDatabaseReadOnly
    mw.DrawDBChart = DummyDrawObject
    mw.DrawRealChart = DummyDrawObject
    mw.DrawTremap = DummyDrawObject
    mw.DrawHomeChart = DummyDrawObject
    mw.MainWindow.closeEvent = lambda self, event: event.accept()

    class SmokeDialogChart:
        def __init__(self, ui_class, wc):
            self.ui = ui_class
            self.wc = wc
            self.ui.dialog_chart = self.wc.setDialog("STOM CHART")

    mw.SetDialogChart = SmokeDialogChart

    mw.dict_set = smoke_settings()
    guard.record("mainwindow_patched", "runtime side-effect paths mocked")


def get_qapplication():
    from PyQt5.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(["smoke_offline_gui"])
    return app


def build_mainwindow(guard: OfflineGuard):
    configure_environment()
    install_preimport_guards(guard)
    app = get_qapplication()
    import ui.ui_mainwindow as mw

    patch_mainwindow_module(mw, guard)
    window = mw.MainWindow(0, None)
    app.processEvents()
    return app, window


def check_attr(item: ContractItem, window) -> ActionResult:
    if item.attr is None:
        return ActionResult(item.item_id, item.category, item.label, "skipped", "static tab label")
    if hasattr(window, item.attr):
        obj = getattr(window, item.attr)
        detail = obj.__class__.__name__
        if hasattr(obj, "receivers") and hasattr(obj, "clicked"):
            try:
                detail = f"{detail}; clicked_receivers={obj.receivers(obj.clicked)}"
            except Exception:
                pass
        return ActionResult(item.item_id, item.category, item.label, "passed", detail)
    if item.required:
        return ActionResult(item.item_id, item.category, item.label, "failed", f"missing attr {item.attr}")
    return ActionResult(item.item_id, item.category, item.label, "skipped", f"optional missing attr {item.attr}")


def exercise_main_menu(window) -> list[ActionResult]:
    results: list[ActionResult] = []
    for index in range(8):
        try:
            window.mnButtonClicked_01(index)
            results.append(ActionResult(f"main_menu_switch_{index}", "main_menu_switch", str(index), "passed"))
        except Exception as exc:
            results.append(ActionResult(f"main_menu_switch_{index}", "main_menu_switch", str(index), "failed", repr(exc)))
    return results


def exercise_tab_widgets(window) -> list[ActionResult]:
    from PyQt5.QtWidgets import QTabWidget

    results: list[ActionResult] = []
    for tab_widget in window.findChildren(QTabWidget):
        name = tab_widget.objectName() or _object_attr_name(window, tab_widget) or tab_widget.__class__.__name__
        for index in range(tab_widget.count()):
            label = tab_widget.tabText(index)
            try:
                tab_widget.setCurrentIndex(index)
                results.append(ActionResult(f"{name}:{index}", "tab_switch", label, "passed"))
            except Exception as exc:
                results.append(ActionResult(f"{name}:{index}", "tab_switch", label, "failed", repr(exc)))
    if not results:
        results.append(ActionResult("tab_switch:none", "tab_switch", "all tabs", "failed", "no QTabWidget discovered"))
    return results


def exercise_strategy_activation_wrappers(window) -> list[ActionResult]:
    results: list[ActionResult] = []
    combo_attrs = [
        "svjb_comboBoxx_01", "svjs_comboBoxx_01", "svc_comboBoxxx_01", "svc_comboBoxxx_02",
        "svc_comboBoxxx_08", "sva_comboBoxxx_01", "svo_comboBoxxx_01", "svo_comboBoxxx_02",
        "cvjb_comboBoxx_01", "cvjs_comboBoxx_01", "cvc_comboBoxxx_01", "cvc_comboBoxxx_02",
        "cvc_comboBoxxx_08", "cva_comboBoxxx_01", "cvo_comboBoxxx_01", "cvo_comboBoxxx_02",
        "sj_stock_cbBox_01", "sj_coin_comBox_01",
    ]
    for attr in combo_attrs:
        combo = getattr(window, attr, None)
        if combo is None:
            continue
        try:
            combo.clear()
            combo.setCurrentIndex(-1)
        except Exception:
            pass

    wrapper_names = [
        *(f"sActivated_{index:02d}" for index in range(1, 10)),
        *(f"cActivated_{index:02d}" for index in range(1, 12)),
    ]
    for name in wrapper_names:
        method = getattr(window, name, None)
        if method is None:
            results.append(ActionResult(name, "strategy_activation_wrapper", name, "failed", "missing method"))
            continue
        try:
            method()
            results.append(ActionResult(name, "strategy_activation_wrapper", name, "passed"))
        except Exception as exc:
            results.append(ActionResult(name, "strategy_activation_wrapper", name, "failed", repr(exc)))
    return results


def _object_attr_name(window, obj) -> str | None:
    for name, value in vars(window).items():
        if value is obj:
            return name
    return None


def run_smoke(branch: str, version: str) -> dict[str, object]:
    guard = OfflineGuard()
    actions: list[ActionResult] = []
    status = "passed"
    error = ""

    contract = build_contract(ROOT)
    try:
        app, window = build_mainwindow(guard)
        actions.append(ActionResult("main_launch", "launch", "MainWindow", "passed"))
        actions.extend(exercise_main_menu(window))
        actions.extend(exercise_tab_widgets(window))
        actions.extend(exercise_strategy_activation_wrappers(window))
        actions.extend(check_attr(item, window) for item in contract)
        app.processEvents()
        window.close()
        app.processEvents()
    except Exception as exc:
        status = "failed"
        error = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip()
        actions.append(ActionResult("main_launch", "launch", "MainWindow", "failed", error))

    failures = [action for action in actions if action.result in {"failed", "not_checked"}]
    if failures:
        status = "failed"

    return {
        "branch": branch,
        "version": version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "error": error,
        "summary": contract_summary(contract),
        "offline_guard_events": guard.events,
        "actions": [action.to_dict() for action in actions],
    }


def write_log(payload: dict[str, object], log_dir: Path, branch: str, version: str) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    safe_branch = branch.replace("/", "_")
    safe_version = version.replace(".", "_")
    path = log_dir / f"smoke_{safe_branch}_{safe_version}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run offline GUI smoke with fail-closed side-effect guards.")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--offline", action="store_true", help="Required marker for side-effect-safe execution.")
    parser.add_argument("--log-dir", default=".omx/logs/v279")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if not args.offline:
        print("[FAIL] --offline is required")
        return 2

    payload = run_smoke(args.branch, args.version)
    path = write_log(payload, ROOT / args.log_dir, args.branch, args.version)
    print(f"[INFO] smoke log: {path}")
    if payload["status"] != "passed":
        print("[FAIL] offline GUI smoke failed")
        print(payload.get("error", ""))
        return 1
    print("[OK] offline GUI smoke passed")
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)
