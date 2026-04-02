from pathlib import Path


def test_backengine_base_initializes_separate_hoga_and_remaining_arrays():
    text = Path('backtest/backengine_base.py').read_text(encoding='utf-8')

    assert 'self.shogainfo       = []' in text
    assert 'self.shreminfo       = []' in text
    assert 'self.bhogainfo       = []' in text
    assert 'self.bhreminfo       = []' in text


def test_backengine_base_uses_split_hoga_and_remaining_arrays_in_buy_sell_paths():
    text = Path('backtest/backengine_base.py').read_text(encoding='utf-8')

    assert '호가배열 = self.shogainfo[:self.buy_hj_limit]' in text
    assert '잔량배열 = self.shreminfo[:self.buy_hj_limit]' in text
    assert '호가배열 = self.bhogainfo[:self.buy_hj_limit]' in text
    assert '잔량배열 = self.bhreminfo[:self.buy_hj_limit]' in text
    assert 'for 호가, 잔량 in zip(호가배열, 잔량배열):' in text
    assert 'for 호가, 잔량 in 호가정보:' not in text
