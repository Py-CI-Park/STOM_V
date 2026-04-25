import json

import pytest

from cli.research_runtime_output import (
    ResearchRuntimeRecorder,
    ResearchRuntimeWriteError,
)


def test_runtime_recorder_writes_json_atomically(tmp_path):
    output_path = tmp_path / 'nested' / 'runtime.json'
    recorder = ResearchRuntimeRecorder(str(output_path))
    recorder.mark('iteration_started', phase='candidate_iteration')

    payload = {'status': 'ok', 'phase': 'candidates_evaluated'}
    written = recorder.write(payload)

    assert written == str(output_path)
    data = json.loads(output_path.read_text(encoding='utf-8'))
    assert data['status'] == 'ok'
    assert data['phase'] == 'candidates_evaluated'
    assert data['checkpoints'][0]['name'] == 'iteration_started'
    assert data['checkpoint_summary']['event_count'] == 1
    assert data['checkpoint_summary']['last_checkpoint'] == 'iteration_started'


def test_runtime_recorder_noops_without_output_path():
    recorder = ResearchRuntimeRecorder(None)
    recorder.mark('iteration_started')

    assert recorder.write({'status': 'ok'}) is None
    assert recorder.summary()['event_count'] == 1


def test_runtime_recorder_raises_structured_write_error(tmp_path):
    output_dir = tmp_path / 'as_directory.json'
    output_dir.mkdir()
    recorder = ResearchRuntimeRecorder(str(output_dir))

    with pytest.raises(ResearchRuntimeWriteError) as excinfo:
        recorder.write({'status': 'ok'})

    assert excinfo.value.path == str(output_dir)
    assert 'runtime output write failed' in str(excinfo.value)
