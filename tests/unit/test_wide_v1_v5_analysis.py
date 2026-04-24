from __future__ import annotations

# pyright: reportAny=none, reportExplicitAny=none, reportUnusedCallResult=none

import json
from pathlib import Path
import runpy
import sys

import pytest


def test_analyze_wide_v1_v5_actual_rowset_selection_proceeds_when_actual_rows_are_distinct(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).resolve().parents[2]
    script_path = project_root / 'scripts' / 'analyze_wide_v1_v5_actual_rowset_selection.py'
    runtime_path = tmp_path / 'runtime.json'
    output_path = tmp_path / 'v5_report.md'
    runtime_path.write_text(
        json.dumps(
            {
                'status': 'ok',
                'actual_rowset_selection': {
                    'status': 'ok',
                    'row_set_identity_status': 'all_distinct',
                    'requested_count': 10,
                    'selected_count': 10,
                    'executed_count': 18,
                    'actual_group_count': 12,
                    'duplicate_actual_rowset_count': 6,
                },
            },
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    monkeypatch.setattr(
        sys,
        'argv',
        [
            str(script_path),
            '--runtime-path',
            str(runtime_path),
            '--output',
            str(output_path),
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(script_path), run_name='__main__')
    stdout = capsys.readouterr().out
    markdown = output_path.read_text(encoding='utf-8')

    assert excinfo.value.code == 0
    assert 'decision=PROCEED_TO_PROMOTE_WFO_PLAN' in stdout
    assert 'next_command=$writing-plans Wide v1 v5 promote 및 WFO 검증 계획 작성' in stdout
    assert 'row_set_identity_status=all_distinct' in stdout
    assert 'selected_count=10' in stdout
    assert '# Wide v1 v5 actual row-set selection' in markdown
    assert 'decision=PROCEED_TO_PROMOTE_WFO_PLAN' in markdown


def test_analyze_wide_v1_v5_actual_rowset_selection_holds_on_shortfall(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).resolve().parents[2]
    script_path = project_root / 'scripts' / 'analyze_wide_v1_v5_actual_rowset_selection.py'
    runtime_path = tmp_path / 'runtime.json'
    output_path = tmp_path / 'v5_report.md'
    runtime_path.write_text(
        json.dumps(
            {
                'status': 'ok',
                'actual_rowset_selection': {
                    'status': 'shortfall',
                    'row_set_identity_status': 'partially_distinct',
                    'requested_count': 10,
                    'selected_count': 7,
                },
            },
            ensure_ascii=False,
        ),
        encoding='utf-8',
    )
    monkeypatch.setattr(
        sys,
        'argv',
        [
            str(script_path),
            '--runtime-path',
            str(runtime_path),
            '--output',
            str(output_path),
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(script_path), run_name='__main__')
    stdout = capsys.readouterr().out

    assert excinfo.value.code == 0
    assert 'decision=HOLD_V5_ACTUAL_ROW_SET_SHORTFALL' in stdout
    assert 'next_command=$brainstorming Wide v1 v6 actual row-set generation expansion 설계' in stdout


def test_analyze_wide_v1_v5_actual_rowset_selection_holds_on_runtime_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).resolve().parents[2]
    script_path = project_root / 'scripts' / 'analyze_wide_v1_v5_actual_rowset_selection.py'
    runtime_path = tmp_path / 'runtime.json'
    output_path = tmp_path / 'v5_report.md'
    runtime_path.write_text(json.dumps({'status': 'error', 'phase': 'candidate_iteration'}), encoding='utf-8')
    monkeypatch.setattr(
        sys,
        'argv',
        [
            str(script_path),
            '--runtime-path',
            str(runtime_path),
            '--output',
            str(output_path),
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(script_path), run_name='__main__')
    stdout = capsys.readouterr().out

    assert excinfo.value.code == 0
    assert 'decision=HOLD_V5_RUNTIME_FAILURE' in stdout
    assert 'next_command=$brainstorming Wide v1 v5 runtime failure recovery 설계' in stdout
