from pathlib import Path


def test_backengine_base_exposes_opti_kind_via_opti_turn_alias():
    text = Path('backtest/backengine_base.py').read_text(encoding='utf-8')

    assert '@property\n    def opti_turn(self):' in text
    assert 'return self.opti_kind' in text
    assert '@opti_turn.setter\n    def opti_turn(self, value):' in text
    assert 'self.opti_kind = value' in text


def test_kiwoom_backengines_still_read_opti_kind():
    min_text = Path('backtest/backengine_kiwoom_min.py').read_text(encoding='utf-8')
    tick_text = Path('backtest/backengine_kiwoom_tick.py').read_text(encoding='utf-8')

    assert 'self.opti_kind == 1' in min_text
    assert 'self.opti_kind == 3' in min_text
    assert 'self.opti_kind == 1' in tick_text
    assert 'self.opti_kind == 3' in tick_text
