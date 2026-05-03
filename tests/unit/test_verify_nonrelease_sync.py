from __future__ import annotations

import contextlib
import importlib
import io
import os
import sys
import textwrap
from pathlib import Path


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import verify_nonrelease_sync as vns


def _write_files(root: Path, files: dict[str, str]) -> None:
    for relative_path, content in files.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


def _base_files() -> dict[str, str]:
    return {
        "utility/telegram_bot.py": """
            def get_telegram_runtime_queues(qlist):
                return qlist[0], qlist[3], qlist[9], qlist[10], qlist[13]
        """,
        "ui/ui_mainwindow.py": """
            from utility.webcrawling import WebCrawling
            from multiprocessing import Process

            self.proc_tele = Process(target=TelegramBot, args=(self.qlist, dict_set), daemon=True)
            self.proc_chqs = Process(target=ChartHogaQuerySound, args=(self.qlist, dict_set), daemon=True)
            self.webc = WebCrawling(self.qlist)
            self.proc_tele.start()
            self.webc.signal.connect(self.windowQ.put)
            self.webc.start()
        """,
        "ui/ui_etc.py": """
            if ui.TelegramProcessAlive():
                pass
        """,
        "ui/ui_process_alive.py": """
            def telegram_process_alive(ui):
                return True
        """,
        "ui/set_setup_tap.py": """
            def setup():
                if uses_serial_key():
                    pass
                self.ui.sj_etc_labelll_02 = None
        """,
        "ui/ui_button_clicked_settings.py": """
            columns = get_etc_setting_columns(uses_serial_key())
        """,
        "utility/setting_user.py": """
            if uses_serial_key():
                pass

            apply_serial_key_to_dict_set(dict_set, uses_serial_key())
        """,
        "utility/setting.py": """
            if uses_serial_key():
                pass

            apply_serial_key_to_dict_set(dict_set, uses_serial_key())
        """,
        "ui/ui_process_kill.py": """
            from time import monotonic

            SHUTDOWN_CHILD_WAIT_SEC = 5.0

            def _remember_window_positions(ui):
                pass

            if hasattr(ui, 'webc') and ui.webc.isRunning():
                ui.webc.stop()
            _remember_window_positions(ui)
            if ui.dialog_backengine.isVisible(): ui.dialog_backengine.close()
            deadline = monotonic() + SHUTDOWN_CHILD_WAIT_SEC
            while ui.proc_chqs.is_alive() and monotonic() < deadline:
                pass
            if ui.proc_chqs.is_alive():
                ui.proc_chqs.terminate()
                ui.proc_chqs.join(timeout=1)
        """,
        "ui/ui_backtest_engine.py": """
            BACKTEST_STOP_WAIT_SEC = 5.0

            def backtest_process_kill(ui, coin, enginekill):
                alive_procs = []
                deadline = monotonic() + BACKTEST_STOP_WAIT_SEC
                while count < wait_target and monotonic() < deadline:
                    data = ui.backQ.get(timeout=0.1)
                _terminate_processes(alive_procs)
        """,
        "utility/static.py": """
            summer_t = 3600
            summer_time = summer_t

            def get_profile_text(profile_obj, sort_by='cumulative', limit=None):
                return ''

            def _setting_db_has_encrypted_payload():
                return False

            if _setting_db_has_encrypted_payload():
                raise RuntimeError('missing key')

            def GetKiwoomPgSgSp(bg, cg):
                pg = 1
                sg = int(round(pg - bg))
                return pg, sg, 0
        """,
        "utility/database_check.py": """
            try:
                read_key()
            except RuntimeError:
                raise
            except Exception:
                write_key()
        """,
        "utility/webcrawling.py": """
            import requests
            from urllib import request

            self.request_timeout = 10
            self.treemap_timer = None

            while self.alive:
                pass

            self.session.get(url, headers=self.headers, timeout=self.request_timeout)
            self.session.get(url, headers=self.headers, timeout=self.request_timeout)
            self.session.get(url, headers=self.headers, timeout=self.request_timeout)
            self.session.get(url, headers=self.headers, timeout=self.request_timeout)
            self.session.get(url, headers=self.headers, timeout=self.request_timeout)
            self.session.get(url, headers=self.headers, timeout=self.request_timeout)
            self.session.get(url, headers=self.headers, timeout=self.request_timeout)
            self.session.get(url, headers=self.headers, timeout=self.request_timeout)
            request.urlopen(random.choice(self.imagelist1), timeout=self.request_timeout).read()
            request.urlopen(random.choice(self.imagelist2), timeout=self.request_timeout).read()
            requests.get(url, headers=self.headers, timeout=self.request_timeout)

            def stop(self):
                self.treemap_timer.cancel()
                self.wait(2000)
        """,
    }


def _run_main(tmp_path: Path, monkeypatch) -> tuple[int, str]:
    monkeypatch.setattr(vns, "ROOT", tmp_path)
    monkeypatch.setattr(vns, "uses_serial_key", lambda: False)

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        result = vns.main()
    return result, buffer.getvalue()


def test_verify_nonrelease_sync_passes_when_all_runtime_guards_exist(tmp_path, monkeypatch):
    _write_files(tmp_path, _base_files())

    result, output = _run_main(tmp_path, monkeypatch)

    assert result == 0
    assert "[FAIL]" not in output


def test_verify_nonrelease_sync_fails_when_webcrawling_qthread_wiring_is_missing(tmp_path, monkeypatch):
    files = _base_files()
    files["ui/ui_mainwindow.py"] = """
        from multiprocessing import Process

        self.proc_tele = Process(target=TelegramBot, args=(self.qlist, dict_set), daemon=True)
        self.proc_tele.start()
        self.proc_webc = Process(target=WebCrawling, args=(self.qlist,), daemon=True)
        self.proc_webc.start()
    """
    _write_files(tmp_path, files)

    result, output = _run_main(tmp_path, monkeypatch)

    assert result == 1
    assert "WebCrawling runtime wiring is out of sync." in output


def test_verify_nonrelease_sync_fails_when_kiwoom_loss_rounding_regresses(tmp_path, monkeypatch):
    files = _base_files()
    files["utility/static.py"] = """
        summer_t = 3600
        summer_time = summer_t

        def get_profile_text(profile_obj, sort_by='cumulative', limit=None):
            return ''

        def _setting_db_has_encrypted_payload():
            return False

        def GetKiwoomPgSgSp(bg, cg):
            pg = 1
            sg = int(pg - bg + 0.5)
            return pg, sg, 0
    """
    _write_files(tmp_path, files)

    result, output = _run_main(tmp_path, monkeypatch)

    assert result == 1
    assert "Kiwoom P/L rounding regressed." in output


def test_verify_nonrelease_sync_fails_when_shutdown_geometry_is_after_dialog_close(tmp_path, monkeypatch):
    files = _base_files()
    files["ui/ui_process_kill.py"] = """
        if hasattr(ui, 'webc') and ui.webc.isRunning():
            ui.webc.stop()
        if ui.dialog_backengine.isVisible(): ui.dialog_backengine.close()
        def _remember_window_positions(ui):
            pass
        _remember_window_positions(ui)
    """
    _write_files(tmp_path, files)

    result, output = _run_main(tmp_path, monkeypatch)

    assert result == 1
    assert "Window geometry persistence must run before dialog close calls." in output


def test_verify_nonrelease_sync_fails_when_process_kill_calls_sys_exit(tmp_path, monkeypatch):
    files = _base_files()
    files["ui/ui_process_kill.py"] = """
        def _remember_window_positions(ui):
            pass

        if hasattr(ui, 'webc') and ui.webc.isRunning():
            ui.webc.stop()
        _remember_window_positions(ui)
        if ui.dialog_backengine.isVisible(): ui.dialog_backengine.close()
        sys.exit()
    """
    _write_files(tmp_path, files)

    result, output = _run_main(tmp_path, monkeypatch)

    assert result == 1
    assert "process_kill must not call sys.exit()" in output


def test_verify_nonrelease_sync_fails_when_proc_chqs_wait_is_unbounded(tmp_path, monkeypatch):
    files = _base_files()
    files["ui/ui_process_kill.py"] = """
        def _remember_window_positions(ui):
            pass

        if hasattr(ui, 'webc') and ui.webc.isRunning():
            ui.webc.stop()
        _remember_window_positions(ui)
        if ui.dialog_backengine.isVisible(): ui.dialog_backengine.close()
        while ui.proc_chqs.is_alive():
            pass
    """
    _write_files(tmp_path, files)

    result, output = _run_main(tmp_path, monkeypatch)

    assert result == 1
    assert "process_kill must not wait indefinitely for proc_chqs shutdown." in output


def test_verify_nonrelease_sync_fails_when_backtest_stop_wait_is_unbounded(tmp_path, monkeypatch):
    files = _base_files()
    files["ui/ui_backtest_engine.py"] = """
        def backtest_process_kill(ui, coin, enginekill):
            while True:
                data = ui.backQ.get()
    """
    _write_files(tmp_path, files)

    result, output = _run_main(tmp_path, monkeypatch)

    assert result == 1
    assert "backtest_process_kill must not wait indefinitely for backtest stop acknowledgements." in output
