import re
from pathlib import Path


def test_telegram_runtime_contract_uses_helper_and_updated_queue_slot():
    text = Path('utility/telegram_bot.py').read_text(encoding='utf-8')

    assert 'def get_telegram_runtime_queues(qlist):' in text
    assert 'return qlist[0], qlist[3], qlist[9], qlist[10], qlist[13]' in text
    assert 'self.windowQ, self.teleQ, self.ctraderQ, self.cstgQ, self.wdzservQ = get_telegram_runtime_queues(qlist)' in text
    assert not re.search(r"self\.wdzservQ\s*=\s*qlist\[12\]", text)
