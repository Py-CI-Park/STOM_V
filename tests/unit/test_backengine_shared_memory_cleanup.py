from pathlib import Path


def test_backengine_base_cleans_up_shared_memory():
    text = Path('backtest/backengine_base.py').read_text(encoding='utf-8')
    assert 'unlink()' in text, 'shared_memory 생성 후 unlink 경로가 필요합니다.'
