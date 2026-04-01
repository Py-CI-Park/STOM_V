import importlib
from pathlib import Path


def test_v270_removed_jisu_chart_references_are_fully_cleaned():
    mainwindow_text = Path('ui/ui_mainwindow.py').read_text(encoding='utf-8')
    process_kill_text = Path('ui/ui_process_kill.py').read_text(encoding='utf-8')

    assert not Path('ui/ui_draw_jisuchart.py').exists(), 'V2.70 이후 지수차트 모듈은 삭제 상태여야 합니다.'
    assert 'ui.ui_draw_jisuchart' not in mainwindow_text, '삭제된 지수차트 모듈 import가 남아 있습니다.'
    assert 'DrawRealJisuChart' not in mainwindow_text, '삭제된 지수차트 드로어 객체 참조가 남아 있습니다.'
    assert 'show_jisu(' not in mainwindow_text, '삭제된 지수차트 표시 함수 참조가 남아 있습니다.'
    assert 'dialog_jisu' not in process_kill_text, '삭제된 지수차트 다이얼로그 종료/직렬화 참조가 남아 있습니다.'
    assert "ui.dict_set['창위치'][7]" in process_kill_text, 'dialog_info 창 위치 인덱스가 지수차트 제거 기준으로 재정렬되어야 합니다.'


def test_ui_mainwindow_import_succeeds_without_deleted_jisu_module():
    module = importlib.import_module('ui.ui_mainwindow')
    assert hasattr(module, 'MainWindow')
