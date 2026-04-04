from pathlib import Path


def test_webcrawling_runtime_contract_no_longer_uses_helper_timeout_calls():
    text = Path('utility/webcrawling.py').read_text(encoding='utf-8')

    assert 'timeout=self._get_timeout()' not in text
