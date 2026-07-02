"""T6.3 — 고아 multiprocessing-fork 정리 스크립트 단위 테스트.

검증(전부 mock — 실 프로세스 열거/종료 없음):
  (a) 기본 dry-run: 후보 목록만, kill 콜러블 미호출, exit 0.
  (b) --older-than-minutes 필터(나이 미상 프로세스는 보수적으로 제외).
  (c) 자기/부모/--exclude-pid 화이트리스트 제외.
  (d) --kill 경로: 후보 pid 에만 kill 호출(mock 검증), 실패 시 exit 1.
  (e) receipt 스키마(orphan_cleanup_receipt_v1) + --report 만 파일 쓰기.
  (f) 열거 실패 정직 에러(exit 2) / PowerShell JSON 변형(단일 객체, /Date(ms)/) 파싱.
"""

import importlib.util
import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _load_module():
    """scripts/cleanup_orphan_backtest_procs.py 를 모듈로 로드한다(패키지 아님)."""
    script_path = os.path.join(PROJECT_ROOT, "scripts", "cleanup_orphan_backtest_procs.py")
    spec = importlib.util.spec_from_file_location("cleanup_orphan_backtest_procs", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MOD = _load_module()

NOW = datetime(2026, 7, 2, 12, 0, 0, tzinfo=timezone.utc)
SELF_PID = 111
PARENT_PID = 222

FORK_CMD = (
    'C:\\Python\\python.exe -c "from multiprocessing.spawn import spawn_main; '
    'spawn_main(parent_pid=999, pipe_handle=612)" --multiprocessing-fork'
)


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _rec(pid, *, name="python.exe", cmd=FORK_CMD, ppid=999, created_min_ago=120):
    created = None if created_min_ago is None else _iso(NOW - timedelta(minutes=created_min_ago))
    return {
        "ProcessId": pid,
        "ParentProcessId": ppid,
        "Name": name,
        "CommandLine": cmd,
        "CreationDateIso": created,
    }


def _query_for(records):
    payload = json.dumps(records)
    return lambda: payload


def _run(argv, records, kill_calls=None, kill_result="killed"):
    """main 을 mock 경계로 실행하고 (exit_code, stdout, stderr, kill_calls) 반환."""
    calls = kill_calls if kill_calls is not None else []

    def fake_kill(pid):
        calls.append(pid)
        if kill_result == "killed":
            return {"pid": pid, "status": "killed", "detail": ""}
        return {"pid": pid, "status": "error", "detail": "access denied"}

    out, err = io.StringIO(), io.StringIO()
    code = MOD.main(
        argv,
        process_query=_query_for(records),
        kill_func=fake_kill,
        now=NOW,
        self_pid=SELF_PID,
        parent_pid=PARENT_PID,
        stdout=out,
        stderr=err,
    )
    return code, out.getvalue(), err.getvalue(), calls


class TestDryRunDefault:
    def test_lists_fork_candidates_without_killing(self):
        records = [
            _rec(500),                                   # orphan fork → 후보
            _rec(501, cmd="python dashboard/app.py"),    # 마커 없음 → 제외
            _rec(502, name="notepad.exe"),               # python 아님 → 제외
        ]
        code, out, _err, calls = _run([], records)
        assert code == 0
        assert calls == []  # 기본 dry-run 은 kill 콜러블을 절대 호출하지 않는다.
        assert "pid=500" in out
        assert "pid=501" not in out
        assert "pid=502" not in out
        assert "dry-run" in out

    def test_dry_run_writes_no_files(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        code, _out, _err, _calls = _run([], [_rec(500)])
        assert code == 0
        assert list(tmp_path.iterdir()) == []  # --report 미지정 → 파일 쓰기 없음.


class TestOlderThanFilter:
    def test_keeps_only_older_processes(self):
        records = [
            _rec(500, created_min_ago=120),  # 오래됨 → 후보
            _rec(501, created_min_ago=2),    # 신생 → 제외
        ]
        code, out, _err, _calls = _run(["--older-than-minutes", "30"], records)
        assert code == 0
        assert "pid=500" in out
        assert "pid=501" not in out

    def test_unknown_creation_date_excluded_when_filter_set(self):
        records = [_rec(500, created_min_ago=None)]
        code, out, _err, _calls = _run(["--older-than-minutes", "30"], records)
        assert code == 0
        assert "pid=500" not in out
        assert "candidates=0" in out

    def test_unknown_creation_date_listed_without_filter(self):
        code, out, _err, _calls = _run([], [_rec(500, created_min_ago=None)])
        assert code == 0
        assert "pid=500" in out
        assert "age=unknown" in out

    def test_negative_filter_is_usage_error(self):
        code, _out, err, _calls = _run(["--older-than-minutes", "-5"], [])
        assert code == 2
        assert "older-than-minutes" in err


class TestExclusions:
    def test_self_and_parent_never_candidates(self):
        records = [_rec(SELF_PID), _rec(PARENT_PID), _rec(500)]
        code, out, _err, _calls = _run([], records)
        assert code == 0
        assert f"pid={SELF_PID}" not in out
        assert f"pid={PARENT_PID}" not in out
        assert "pid=500" in out
        assert "candidates=1" in out

    def test_exclude_pid_whitelist(self):
        records = [_rec(500), _rec(600)]
        code, out, _err, calls = _run(["--kill", "--exclude-pid", "600"], records)
        assert code == 0
        assert calls == [500]
        assert "pid=600" not in out

    def test_self_and_parent_never_killed_even_if_fork_marked(self):
        records = [_rec(SELF_PID), _rec(PARENT_PID), _rec(500)]
        code, _out, _err, calls = _run(["--kill"], records)
        assert code == 0
        assert calls == [500]


class TestKillPath:
    def test_kill_invokes_kill_func_only_for_candidates(self):
        records = [
            _rec(500),
            _rec(700),
            _rec(501, cmd="python stom.py"),  # 마커 없음 → kill 안 됨
        ]
        code, out, _err, calls = _run(["--kill"], records)
        assert code == 0
        assert sorted(calls) == [500, 700]
        assert "killed pid=500" in out
        assert "killed pid=700" in out

    def test_kill_failure_returns_exit_1_with_error_detail(self):
        code, out, _err, calls = _run(["--kill"], [_rec(500)], kill_result="error")
        assert code == 1
        assert calls == [500]
        assert "kill-error pid=500" in out
        assert "access denied" in out

    def test_kill_respects_older_than_filter(self):
        records = [_rec(500, created_min_ago=120), _rec(501, created_min_ago=1)]
        code, _out, _err, calls = _run(["--kill", "--older-than-minutes", "30"], records)
        assert code == 0
        assert calls == [500]


class TestReceipt:
    def test_report_writes_schema_v1_receipt(self, tmp_path):
        report = tmp_path / "receipt.json"
        records = [_rec(500), _rec(501, cmd="python stom.py")]
        code, out, _err, _calls = _run(["--report", str(report)], records)
        assert code == 0
        assert str(report) in out
        receipt = json.loads(report.read_text(encoding="utf-8"))
        assert receipt["schema"] == "orphan_cleanup_receipt_v1"
        assert receipt["authority"] == "advisory_only"
        assert receipt["mode"] == "dry_run"
        assert receipt["self_pid"] == SELF_PID
        assert receipt["parent_pid"] == PARENT_PID
        assert receipt["scanned_python_processes"] == 2
        assert receipt["candidate_count"] == 1
        assert receipt["killed"] == [] and receipt["kill_errors"] == []
        assert "--multiprocessing-fork" in receipt["fork_markers"]
        cand = receipt["candidates"][0]
        for key in ("pid", "parent_pid", "command_line_summary", "creation_date", "age_minutes"):
            assert key in cand
        assert cand["pid"] == 500
        assert cand["age_minutes"] == pytest.approx(120.0, abs=0.1)

    def test_kill_mode_receipt_records_killed(self, tmp_path):
        report = tmp_path / "receipt.json"
        code, _out, _err, _calls = _run(["--kill", "--report", str(report)], [_rec(500)])
        assert code == 0
        receipt = json.loads(report.read_text(encoding="utf-8"))
        assert receipt["mode"] == "kill"
        assert [k["pid"] for k in receipt["killed"]] == [500]


class TestEnumerationAndParsing:
    def test_enumeration_error_returns_exit_2(self):
        def broken_query():
            raise MOD.EnumerationError("powershell 실패")

        out, err = io.StringIO(), io.StringIO()
        code = MOD.main(
            [], process_query=broken_query, kill_func=lambda pid: {"status": "killed"},
            now=NOW, self_pid=SELF_PID, parent_pid=PARENT_PID, stdout=out, stderr=err,
        )
        assert code == 2
        assert "열거 실패" in err.getvalue()

    def test_invalid_json_is_honest_error(self):
        with pytest.raises(MOD.EnumerationError):
            MOD.parse_process_records("{not json")

    def test_single_object_and_ps51_date_format(self):
        # PS 5.1: 단일 결과는 배열이 아닌 객체 + '/Date(ms)/' 날짜 직렬화.
        epoch_ms = int((NOW - timedelta(minutes=60)).timestamp() * 1000)
        raw = json.dumps({
            "ProcessId": 500, "ParentProcessId": 1, "Name": "python.exe",
            "CommandLine": FORK_CMD, "CreationDate": f"/Date({epoch_ms})/",
        })
        records = MOD.parse_process_records(raw)
        assert len(records) == 1
        cands = MOD.select_candidates(records, now=NOW)
        assert cands[0]["pid"] == 500
        assert cands[0]["age_minutes"] == pytest.approx(60.0, abs=0.1)

    def test_empty_and_null_outputs(self):
        assert MOD.parse_process_records("") == []
        assert MOD.parse_process_records("[]") == []
        assert MOD.parse_process_records("null") == []

    def test_marker_gate_requires_python_name_and_marker(self):
        assert MOD.is_python_fork_process(
            {"name": "python3.13.exe", "command_line": "x --multiprocessing-fork y"})
        assert not MOD.is_python_fork_process(
            {"name": "java.exe", "command_line": "--multiprocessing-fork"})
        assert not MOD.is_python_fork_process(
            {"name": "python.exe", "command_line": "python stom.py"})
        assert MOD.is_python_fork_process(
            {"name": "python.exe",
             "command_line": 'python -c "from multiprocessing.resource_tracker import main;main(5)"'})
