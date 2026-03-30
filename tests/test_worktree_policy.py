from utility.worktree_policy import (
    apply_serial_key_to_dict_set,
    get_etc_default_row,
    get_etc_setting_columns,
    uses_serial_key,
)


def test_uses_serial_key_only_for_official_stom_v_root():
    assert uses_serial_key("C:/System_Trading/STOM/STOM_V") is True
    assert uses_serial_key("C:/System_Trading/STOM/STOM_V.wt-2u") is False
    assert uses_serial_key("C:/System_Trading/STOM/STOM_V.wt-dev") is False


def test_get_etc_setting_columns_omits_serial_key_for_worktrees():
    assert "시리얼키" not in get_etc_setting_columns(False)
    assert "시리얼키" in get_etc_setting_columns(True)


def test_get_etc_default_row_tracks_serial_key_column_count():
    assert len(get_etc_default_row(False)) == len(get_etc_setting_columns(False))
    assert len(get_etc_default_row(True)) == len(get_etc_setting_columns(True))


def test_apply_serial_key_to_dict_set_respects_policy():
    df_e = {"시리얼키": ["encoded"]}

    dict_set = {}
    apply_serial_key_to_dict_set(dict_set, df_e, lambda value: f"decoded:{value}", False)
    assert "시리얼키" not in dict_set

    dict_set = {}
    apply_serial_key_to_dict_set(dict_set, df_e, lambda value: f"decoded:{value}", True)
    assert dict_set["시리얼키"] == "decoded:encoded"
