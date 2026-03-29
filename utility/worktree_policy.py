from pathlib import Path
import os


_ETC_BASE_COLUMNS = [
    "index", "테마", "저해상도", "휴무프로세스종료", "휴무컴퓨터종료",
    "창위치기억", "창위치", "스톰라이브", "프로그램종료", "팩터선택"
]

_ETC_BASE_DEFAULT_ROW = [
    0, "다크블루", 0, 1, 0, 1, "", 1, 0,
    "1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1;1"
]


def uses_serial_key(path=None):
    name = Path(path or os.getcwd()).name.lower()
    return name == "stom_v"


def get_etc_setting_columns(include_serial_key):
    columns = list(_ETC_BASE_COLUMNS)
    if include_serial_key:
        columns.append("시리얼키")
    return columns


def get_etc_default_row(include_serial_key):
    row = list(_ETC_BASE_DEFAULT_ROW)
    if include_serial_key:
        row.append("")
    return row
