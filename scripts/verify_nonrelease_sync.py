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
            "apply_serial_key_to_dict_set" in setting_user_text and "uses_serial_key()" in setting_user_text,
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
