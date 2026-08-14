import json
import sys
from multiprocessing import Queue
from pathlib import Path
from queue import Empty


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def test_emit_cli_protocol_checkpoint_is_env_gated(monkeypatch):
    from backtest.backtest import _emit_cli_protocol_checkpoint

    q = Queue()
    monkeypatch.delenv('STOM_CLI_BACKTEST_PROTOCOL_DIAG', raising=False)

    _emit_cli_protocol_checkpoint(q, 'BackTest', 'backtest_child_started', {'pid': 123})

    assert q.empty()


def test_emit_cli_protocol_checkpoint_writes_json_message(monkeypatch):
    from backtest.backtest import _emit_cli_protocol_checkpoint

    q = Queue()
    monkeypatch.setenv('STOM_CLI_BACKTEST_PROTOCOL_DIAG', '1')

    _emit_cli_protocol_checkpoint(q, 'BackTest', 'backtest_child_started', {'pid': 123})

    ui_id, message = q.get(timeout=1)
    assert isinstance(ui_id, (int, float))
    assert message.startswith('[CLI_DIAG] ')
    payload = json.loads(message[len('[CLI_DIAG] '):])
    assert payload['source'] == 'BackTest'
    assert payload['checkpoint'] == 'backtest_child_started'
    assert payload['detail'] == {'pid': 123}


def test_wait_for_tq_message_uses_normal_blocking_get_when_diagnostics_are_off(monkeypatch):
    from backtest.backtest import _wait_for_tq_message

    class FakeQueue:
        def __init__(self):
            self.calls = []

        def get(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            return '백테완료'

    monkeypatch.delenv('STOM_CLI_BACKTEST_PROTOCOL_DIAG', raising=False)
    tq = FakeQueue()

    assert _wait_for_tq_message(tq, None, {}) == '백테완료'
    assert tq.calls == [((), {})]


def test_wait_for_tq_message_emits_bounded_heartbeat_before_receiving_message(monkeypatch):
    from backtest.backtest import _wait_for_tq_message

    class FakeTq:
        def __init__(self):
            self.calls = []

        def get(self, *args, **kwargs):
            self.calls.append((args, kwargs))
            if len(self.calls) == 1:
                raise Empty
            return ('백테결과', ['large payload that must not be serialized'])

    class FakeWq:
        def __init__(self):
            self.items = []

        def put(self, item):
            self.items.append(item)

    monkeypatch.setenv('STOM_CLI_BACKTEST_PROTOCOL_DIAG', '1')
    tq = FakeTq()
    wq = FakeWq()
    timestamps = iter((100.0, 107.8))
    context = {
        'engine_count': 2,
        'subtotal_count': 5,
        'row_count': 123,
        'day_count': 4,
        'avgtime': 30,
        'buystg_name': 'b' * 256,
        'sellstg_name': 'sell-strategy',
    }

    data = _wait_for_tq_message(
        tq, wq, context, timeout_seconds=5, monotonic=lambda: next(timestamps)
    )

    assert data[0] == '백테결과'
    assert tq.calls == [((), {'timeout': 5}), ((), {'timeout': 5})]
    _, message = wq.items[0]
    payload = json.loads(message[len('[CLI_DIAG] '):])
    assert payload['checkpoint'] == 'backtest_child_waiting_mq_heartbeat'
    assert payload['detail'] == {
        **context, 'buystg_name': 'b' * 128, 'elapsed_seconds': 7
    }
    assert all(
        value is None or isinstance(value, (bool, int, float, str))
        for value in payload['detail'].values()
    )
    assert all(
        not isinstance(value, str) or len(value) <= 128
        for value in payload['detail'].values()
    )


def test_tq_message_kind_omits_result_payload():
    from backtest.backtest import _tq_message_kind

    assert _tq_message_kind(('백테결과', 'x' * 10000)) == '백테결과'


def test_backtest_start_emits_key_protocol_checkpoints():
    content = (ROOT / 'backtest' / 'backtest.py').read_text(encoding='utf-8')

    for checkpoint in [
        'backtest_child_started',
        'backtest_child_config_received',
        'backtest_child_moneytop_loaded',
        'backtest_child_total_process_started',
        'backtest_child_engine_start_sent',
        'backtest_child_waiting_mq_first',
        'backtest_child_mq_first_received',
        'backtest_child_waiting_mq_second',
        'backtest_child_completed',
    ]:
        assert checkpoint in content


def test_total_emits_key_protocol_checkpoints():
    content = (ROOT / 'backtest' / 'backtest.py').read_text(encoding='utf-8')

    for checkpoint in [
        'total_process_started',
        'total_info_received',
        'total_engine_done_count',
        'total_subtotal_collection_done_count',
        'total_result_received',
        'total_report_started',
        'total_report_no_trades',
        'total_report_db_written',
        'total_report_csv_written',
        'total_report_mq_sent',
    ]:
        assert checkpoint in content
