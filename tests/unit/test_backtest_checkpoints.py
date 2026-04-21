import json

from cli.backtest_checkpoints import BacktestCheckpointRecorder


def test_checkpoint_recorder_tracks_last_checkpoint():
    recorder = BacktestCheckpointRecorder()

    recorder.mark('preflight_started')
    recorder.mark('strategy_validated')

    assert recorder.last_checkpoint == 'strategy_validated'
    assert [item['name'] for item in recorder.events] == [
        'preflight_started',
        'strategy_validated',
    ]


def test_checkpoint_recorder_builds_timeout_payload():
    recorder = BacktestCheckpointRecorder()
    recorder.mark('shared_data_loaded', detail={'back_count': 1638})

    payload = recorder.to_result_fields(
        status='timeout',
        cleanup_status='ok',
    )

    assert payload['last_checkpoint'] == 'shared_data_loaded'
    assert payload['checkpoints'][0]['detail'] == {'back_count': 1638}
    assert payload['checkpoint_status'] == 'timeout'
    assert payload['cleanup_status'] == 'ok'
    assert payload['elapsed_seconds'] >= 0


def test_checkpoint_recorder_converts_non_json_detail_values():
    recorder = BacktestCheckpointRecorder()
    bad_value = object()
    recorder.mark('shared_data_loaded', detail={'bad': bad_value, 'ok': 1})

    payload = recorder.to_result_fields(status='timeout')

    json.dumps(payload)
    assert payload['checkpoints'][0]['detail']['ok'] == 1
    assert payload['checkpoints'][0]['detail']['bad'] == repr(bad_value)
