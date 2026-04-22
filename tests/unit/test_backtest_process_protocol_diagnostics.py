import json
import sys
from multiprocessing import Queue
from pathlib import Path


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
