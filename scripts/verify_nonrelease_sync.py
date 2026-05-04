from pathlib import Path
import sys

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from utility.worktree_policy import uses_serial_key


def read_text(relative_path):
    return (ROOT / relative_path).read_text(encoding="utf-8")


def check(condition, success, failure, failures):
    if condition:
        print(f"[OK] {success}")
    else:
        print(f"[FAIL] {failure}")
        failures.append(failure)


def main():
    failures = []

    pyd_files = sorted(path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*.pyd"))
    check(
        not pyd_files,
        "워크트리에 .pyd 파일이 없습니다.",
        f".pyd 파일이 남아 있습니다: {', '.join(pyd_files)}",
        failures,
    )

    telegram_bot_text = read_text("utility/telegram_bot.py")
    ui_mainwindow_text = read_text("ui/ui_mainwindow.py")
    ui_etc_text = read_text("ui/ui_etc.py")
    ui_process_alive_text = read_text("ui/ui_process_alive.py")
    ui_process_kill_text = read_text("ui/ui_process_kill.py")
    static_text = read_text("utility/static.py")
    webcrawling_text = read_text("utility/webcrawling.py")
    database_check_text = read_text("utility/database_check.py") if (ROOT / "utility/database_check.py").exists() else ""

    check(
        "return qlist[0], qlist[3], qlist[9], qlist[10], qlist[13]" in telegram_bot_text,
        "텔레그램 qlist 계약이 현재 MainWindow 순서와 일치합니다.",
        "utility/telegram_bot.py의 텔레그램 qlist 계약이 현재 MainWindow 순서와 다릅니다.",
        failures,
    )
    check(
        "Process(target=TelegramBot" in ui_mainwindow_text and "self.proc_tele.start()" in ui_mainwindow_text,
        "MainWindow가 텔레그램 런타임을 시작합니다.",
        "ui/ui_mainwindow.py에 텔레그램 런타임 시작 경로가 없습니다.",
        failures,
    )
    check(
        "ui.TelegramProcessAlive()" in ui_etc_text,
        "설정 변경 전파가 TelegramProcessAlive 경로를 사용합니다.",
        "ui/ui_etc.py가 여전히 raw proc_tele 접근을 사용합니다.",
        failures,
    )
    check(
        "def telegram_process_alive" in ui_process_alive_text,
        "텔레그램 alive helper가 존재합니다.",
        "ui/ui_process_alive.py에 텔레그램 alive helper가 없습니다.",
        failures,
    )
    check(
        all(symbol not in ui_mainwindow_text for symbol in ("ui.ui_draw_jisuchart", "DrawRealJisuChart", "show_jisu(")),
        "Jisu cleanup matches V2.70 removal.",
        "Stale jisu runtime references remain in ui/ui_mainwindow.py.",
        failures,
    )
    check(
        "qtimer0" not in ui_process_kill_text and "dialog_jisu" not in ui_process_kill_text,
        "Shutdown cleanup matches current MainWindow runtime.",
        "Stale runtime shutdown references remain.",
        failures,
    )
    process_kill_offset = ui_process_kill_text.find("def process_kill")
    process_kill_text = ui_process_kill_text[process_kill_offset:] if process_kill_offset != -1 else ""
    check(
        "def _remember_window_positions" in ui_process_kill_text
        and "def _prepare_shutdown_ui" in ui_process_kill_text
        and "_remember_window_positions(ui)" in ui_process_kill_text
        and "_prepare_shutdown_ui(ui)" in process_kill_text
        and "_close_shutdown_dialogs(ui)" in process_kill_text
        and process_kill_text.index("_prepare_shutdown_ui(ui)") < process_kill_text.index("_close_shutdown_dialogs(ui)"),
        "Shutdown persists dialog geometry before closing dialogs.",
        "Window geometry persistence must run before dialog close calls.",
        failures,
    )
    check(
        "def _prepare_shutdown_ui" in ui_process_kill_text
        and "widget.hide()" in ui_process_kill_text
        and "def _process_qt_events" in ui_process_kill_text
        and "app.processEvents()" in ui_process_kill_text
        and "_prepare_shutdown_ui(ui)" in process_kill_text
        and "if ui.proc_manager" in process_kill_text
        and process_kill_text.index("_prepare_shutdown_ui(ui)") < process_kill_text.index("if ui.proc_manager"),
        "Shutdown hides Qt windows before bounded child cleanup.",
        "process_kill must hide/pump Qt before blocking child cleanup.",
        failures,
    )
    check(
        "sys.exit()" not in ui_process_kill_text,
        "Shutdown does not raise SystemExit inside Qt closeEvent.",
        "process_kill must not call sys.exit() from the Qt closeEvent path.",
        failures,
    )
    check(
        "SHUTDOWN_CHILD_WAIT_SEC" in ui_process_kill_text
        and "deadline = monotonic() + SHUTDOWN_CHILD_WAIT_SEC" in ui_process_kill_text
        and "ui.proc_chqs.terminate()" in ui_process_kill_text
        and "ui.proc_chqs.join(timeout=1)" in ui_process_kill_text,
        "Shutdown query/sound child wait is bounded with terminate fallback.",
        "process_kill must not wait indefinitely for proc_chqs shutdown.",
        failures,
    )
    check(
        "BACKTEST_SHUTDOWN_WAIT_SEC" in ui_process_kill_text
        and "ui.backQ.get(timeout=0.1)" in ui_process_kill_text
        and "_terminate_processes(alive_procs)" in ui_process_kill_text,
        "Shutdown backtest stop acknowledgement wait is bounded with terminate fallback.",
        "process_kill must not wait indefinitely for backtest stop acknowledgements.",
        failures,
    )
    check(
        "Process(target=WebCrawling" not in ui_mainwindow_text
        and "WebCrawling(self.qlist)" in ui_mainwindow_text
        and "self.webc.signal.connect(self.windowQ.put)" in ui_mainwindow_text
        and "self.webc.start()" in ui_mainwindow_text
        and "webc.stop()" in ui_process_kill_text,
        "WebCrawling runtime wiring matches QThread contract.",
        "WebCrawling runtime wiring is out of sync.",
        failures,
    )
    check(
        "summer_time = summer_t" in static_text and "def get_profile_text" in static_text,
        "static.py compatibility exports match runtime contract.",
        "static.py runtime compatibility exports are out of sync.",
        failures,
    )
    check(
        "self.request_timeout = 10" in webcrawling_text
        and "self.treemap_timer = None" in webcrawling_text
        and "while self.alive" in webcrawling_text
        and "self.treemap_timer.cancel()" in webcrawling_text
        and "self.wait(2000)" in webcrawling_text
        and "timeout=self.request_timeout" in webcrawling_text,
        "WebCrawling stop contract includes timeout and cancellation guards.",
        "WebCrawling stop contract is incomplete.",
        failures,
    )
    check(
        "_setting_db_has_encrypted_payload" in static_text
        and "if _setting_db_has_encrypted_payload():" in static_text
        and "except RuntimeError:" in database_check_text,
        "Key loading safety guard is present.",
        "Key loading safety guard is missing.",
        failures,
    )
    check(
        "sg = int(round(pg - bg))" in static_text and "sg = int(pg - bg + 0.5)" not in static_text,
        "Kiwoom P/L rounding matches expected loss math.",
        "Kiwoom P/L rounding regressed.",
        failures,
    )

    if not uses_serial_key():
        set_setup_tap_text = read_text("ui/set_setup_tap.py")
        settings_text = read_text("ui/ui_button_clicked_settings.py")
        setting_user_text = read_text("utility/setting_user.py")
        legacy_setting_text = read_text("utility/setting.py") if (ROOT / "utility/setting.py").exists() else ""

        check(
            "if uses_serial_key():" in set_setup_tap_text and "self.ui.sj_etc_labelll_02 = None" in set_setup_tap_text,
            "비정식 워크트리에서 시리얼키 UI 생성이 차단됩니다.",
            "ui/set_setup_tap.py에 비정식 워크트리용 시리얼키 UI 차단이 없습니다.",
            failures,
        )
        check(
            "get_etc_setting_columns(uses_serial_key())" in settings_text,
            "설정 저장이 워크트리 시리얼키 정책을 따릅니다.",
            "ui/ui_button_clicked_settings.py가 워크트리 시리얼키 정책과 분리되어 있습니다.",
            failures,
        )
        check(
            "uses_serial_key()" in setting_user_text and (
                "apply_serial_key_to_dict_set" in setting_user_text or "if uses_serial_key()" in setting_user_text
            ),
            "dict_set 적재가 비정식 워크트리 시리얼키 정책을 따릅니다.",
            "utility/setting_user.py가 비정식 워크트리에서도 시리얼키를 무조건 적재합니다.",
            failures,
        )
        if legacy_setting_text:
            check(
                "apply_serial_key_to_dict_set" in legacy_setting_text and "uses_serial_key()" in legacy_setting_text,
                "legacy utility/setting.py도 비정식 워크트리 시리얼키 정책을 따릅니다.",
                "utility/setting.py가 비정식 워크트리에서도 시리얼키를 무조건 적재합니다.",
                failures,
            )

    if failures:
        print(f"\n총 {len(failures)}개 항목이 실패했습니다.")
        return 1

    print("\n모든 비정식 워크트리 동기화 가드레일 검사를 통과했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
