"""연구 증거 lineage 검사기 단위 테스트 — scripts/check_research_evidence_lineage.py."""

from __future__ import annotations

import json
import os
import sys

import pytest

# ---------------------------------------------------------------------------
# 프로젝트 루트/scripts 를 sys.path 에 추가해 스크립트 모듈을 import 한다.
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import check_research_evidence_lineage as crel


# ---------------------------------------------------------------------------
# 합성 세트 헬퍼
# ---------------------------------------------------------------------------

def _write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=True), encoding="utf-8")


def _write_jsonl(path, rows):
    lines = [json.dumps(row, ensure_ascii=True) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _iter_row(iter_no, template, both_positive):
    return {
        "iter": iter_no,
        "track": "tick_new",
        "template": template,
        "timeframe": "tick",
        "eval": {"slots": ["a"], "verdict": "no-go", "both_positive": both_positive},
    }


def _make_iter_eval_set(root, name, rows, promising, out_name=None):
    """iter/eval 형식 summary + jsonl + out md 세트를 생성한다."""
    out_name = out_name if out_name is not None else f"{name}.md"
    _write_jsonl(root / f"{name}.jsonl", rows)
    (root / out_name).write_text("| table |\n", encoding="utf-8")
    _write_json(root / f"{name}_summary.json", {
        "promising": promising,
        "out": out_name,
        "finished": "2026-06-15 16:22",
    })


def _make_round_event_set(root, name, rounds, gate_flags, summary_overrides=None):
    """round/event 형식 summary + jsonl 세트를 생성한다."""
    rows = [{"event": "start", "template": "seed", "ts": 1.0}]
    profits = []
    for idx, gate in enumerate(gate_flags):
        profit = 1000.0 * (idx + 1)
        profits.append(profit)
        rows.append({
            "event": "cand", "round": (idx % rounds) + 1,
            "label": f"c{idx}", "gate": gate,
            "profit": profit, "mdd": 5.0, "trades": 10, "ts": 2.0 + idx,
        })
    for round_no in range(1, rounds + 1):
        rows.append({"event": "round_done", "round": round_no, "ts": 99.0 + round_no})
    _write_jsonl(root / f"{name}.jsonl", rows)
    summary = {
        "rounds": rounds,
        "adopted_total": sum(1 for g in gate_flags if g),
        "best_overall": {"label": "best", "profit": max(profits), "mdd": 5.0},
        "finished_ts": 123.0,
    }
    if summary_overrides:
        summary = {**summary, **summary_overrides}
    _write_json(root / f"{name}_summary.json", summary)


def _issues_by_check(report):
    grouped = {}
    for issue in report["issues"]:
        grouped.setdefault(issue["check"], []).append(issue)
    return grouped


def _empty_runs_dir(tmp_path):
    runs = tmp_path / "research_runs"
    runs.mkdir()
    return runs


# ===========================================================================
# iter/eval 형식
# ===========================================================================

class TestIterEvalConsistency:

    def test_consistent_set_has_no_errors(self, tmp_path):
        """정상 세트(promising 일치, _n2 행수 일치)는 error 0 이어야 한다."""
        root = tmp_path / "evidence"
        root.mkdir()
        rows = [_iter_row(0, "tpl_a", False), _iter_row(1, "tpl_b", True)]
        _make_iter_eval_set(root, "camp_n2", rows, promising=["tpl_b"])

        report = crel.run_checks(root, research_runs_dir=_empty_runs_dir(tmp_path))

        assert report["exit_code"] == 0
        assert report["counts"]["error"] == 0
        assert report["summaries_checked"] == 1

    def test_promising_mismatch_is_error(self, tmp_path):
        """summary promising 과 jsonl 재계산이 다르면 error 를 낸다."""
        root = tmp_path / "evidence"
        root.mkdir()
        rows = [_iter_row(0, "tpl_a", False), _iter_row(1, "tpl_b", False)]
        _make_iter_eval_set(root, "camp_n2", rows, promising=["tpl_b"])

        report = crel.run_checks(root, research_runs_dir=_empty_runs_dir(tmp_path))

        checks = _issues_by_check(report)
        assert "promising_mismatch" in checks
        assert checks["promising_mismatch"][0]["severity"] == "error"
        assert report["exit_code"] == 1

    def test_row_count_mismatch_is_error(self, tmp_path):
        """이름 규약 _n{N} 과 실제 행수가 다르면 error 를 낸다."""
        root = tmp_path / "evidence"
        root.mkdir()
        rows = [_iter_row(0, "tpl_a", False)]
        _make_iter_eval_set(root, "camp_n8", rows, promising=[])

        report = crel.run_checks(root, research_runs_dir=_empty_runs_dir(tmp_path))

        checks = _issues_by_check(report)
        assert "row_count_mismatch" in checks
        assert checks["row_count_mismatch"][0]["severity"] == "error"

    def test_missing_jsonl_pair_is_error(self, tmp_path):
        """짝 jsonl 이 없으면 missing_jsonl_pair error 를 낸다."""
        root = tmp_path / "evidence"
        root.mkdir()
        _write_json(root / "lost_summary.json", {
            "promising": [], "out": "lost.md", "finished": "2026-06-15",
        })

        report = crel.run_checks(root, research_runs_dir=_empty_runs_dir(tmp_path))

        checks = _issues_by_check(report)
        assert "missing_jsonl_pair" in checks
        assert report["exit_code"] == 1

    def test_missing_out_path_is_warning(self, tmp_path):
        """out 경로가 존재하지 않으면 warning 을 낸다."""
        root = tmp_path / "evidence"
        root.mkdir()
        rows = [_iter_row(0, "tpl_a", False)]
        _write_jsonl(root / "camp.jsonl", rows)
        _write_json(root / "camp_summary.json", {
            "promising": [], "out": "nonexistent.md", "finished": "x",
        })

        report = crel.run_checks(root, research_runs_dir=_empty_runs_dir(tmp_path))

        checks = _issues_by_check(report)
        assert "out_path_missing" in checks
        assert checks["out_path_missing"][0]["severity"] == "warning"

    def test_absolute_out_path_is_advisory(self, tmp_path):
        """절대경로 out 표기는 advisory 로 보고한다."""
        root = tmp_path / "evidence"
        root.mkdir()
        rows = [_iter_row(0, "tpl_a", False)]
        _write_jsonl(root / "camp.jsonl", rows)
        out_md = root / "camp.md"
        out_md.write_text("| t |\n", encoding="utf-8")
        _write_json(root / "camp_summary.json", {
            "promising": [], "out": str(out_md), "finished": "x",
        })

        report = crel.run_checks(root, research_runs_dir=_empty_runs_dir(tmp_path))

        checks = _issues_by_check(report)
        assert "out_path_absolute" in checks
        assert checks["out_path_absolute"][0]["severity"] == "advisory"
        assert "out_path_missing" not in checks


# ===========================================================================
# round/event 형식
# ===========================================================================

class TestRoundEventConsistency:

    def test_consistent_set_has_no_errors(self, tmp_path):
        """rounds/adopted_total 이 재계산과 일치하면 error 0 이어야 한다."""
        root = tmp_path / "evidence"
        root.mkdir()
        _make_round_event_set(root, "ovn_x", rounds=2, gate_flags=[True, False, True])

        report = crel.run_checks(root, research_runs_dir=_empty_runs_dir(tmp_path))

        assert report["counts"]["error"] == 0
        assert report["exit_code"] == 0

    def test_adopted_total_mismatch_is_error(self, tmp_path):
        """adopted_total 이 gate=true cand 수와 다르면 error 를 낸다."""
        root = tmp_path / "evidence"
        root.mkdir()
        _make_round_event_set(
            root, "ovn_x", rounds=2, gate_flags=[True, False, True],
            summary_overrides={"adopted_total": 0},
        )

        report = crel.run_checks(root, research_runs_dir=_empty_runs_dir(tmp_path))

        checks = _issues_by_check(report)
        assert "adopted_total_mismatch" in checks
        assert report["exit_code"] == 1

    def test_rounds_mismatch_is_error(self, tmp_path):
        """rounds 가 round_done 재계산과 다르면 error 를 낸다."""
        root = tmp_path / "evidence"
        root.mkdir()
        _make_round_event_set(
            root, "ovn_x", rounds=2, gate_flags=[True],
            summary_overrides={"rounds": 9},
        )

        report = crel.run_checks(root, research_runs_dir=_empty_runs_dir(tmp_path))

        assert "rounds_mismatch" in _issues_by_check(report)

    def test_best_overall_absent_from_jsonl_is_warning(self, tmp_path):
        """best_overall.profit 이 cand 레코드에 없으면 warning 을 낸다."""
        root = tmp_path / "evidence"
        root.mkdir()
        _make_round_event_set(
            root, "ovn_x", rounds=1, gate_flags=[True, True],
            summary_overrides={"best_overall": {"label": "ghost", "profit": 777777.0}},
        )

        report = crel.run_checks(root, research_runs_dir=_empty_runs_dir(tmp_path))

        checks = _issues_by_check(report)
        assert "best_overall_not_in_jsonl" in checks
        assert checks["best_overall_not_in_jsonl"][0]["severity"] == "warning"

    def test_missing_artifact_is_error(self, tmp_path):
        """artifacts 등록부의 파일이 없으면 error 를 낸다."""
        root = tmp_path / "evidence"
        root.mkdir()
        (root / "present.json").write_text("{}", encoding="utf-8")
        _make_round_event_set(
            root, "ovn_x", rounds=1, gate_flags=[True],
            summary_overrides={"artifacts": ["present.json", "absent.json"]},
        )

        report = crel.run_checks(root, research_runs_dir=_empty_runs_dir(tmp_path))

        checks = _issues_by_check(report)
        assert "artifact_missing" in checks
        details = [i["detail"] for i in checks["artifact_missing"]]
        assert any("absent.json" in d for d in details)
        assert not any("present.json" in d for d in details)

    def test_empty_artifact_is_error(self, tmp_path):
        """artifacts 등록부의 파일이 0바이트면 error 를 낸다."""
        root = tmp_path / "evidence"
        root.mkdir()
        (root / "hollow.json").write_text("", encoding="utf-8")
        _make_round_event_set(
            root, "ovn_x", rounds=1, gate_flags=[True],
            summary_overrides={"artifacts": ["hollow.json"]},
        )

        report = crel.run_checks(root, research_runs_dir=_empty_runs_dir(tmp_path))

        assert "artifact_empty" in _issues_by_check(report)


# ===========================================================================
# 형식 판별 / 기타 lineage
# ===========================================================================

class TestFormatAndInventory:

    def test_unknown_format_is_advisory_skip(self, tmp_path):
        """알 수 없는 summary 형식은 unknown_format advisory 로 스킵한다."""
        root = tmp_path / "evidence"
        root.mkdir()
        _write_json(root / "theta_summary.json", {"sweep_run_id": "x", "slots": []})

        report = crel.run_checks(root, research_runs_dir=_empty_runs_dir(tmp_path))

        checks = _issues_by_check(report)
        assert "unknown_format" in checks
        assert checks["unknown_format"][0]["severity"] == "advisory"
        assert report["exit_code"] == 0

    def test_orphan_jsonl_is_warning(self, tmp_path):
        """summary 짝이 없는 jsonl 은 warning 으로 보고한다."""
        root = tmp_path / "evidence"
        root.mkdir()
        _write_jsonl(root / "orphan.jsonl", [_iter_row(0, "t", False)])

        report = crel.run_checks(root, research_runs_dir=_empty_runs_dir(tmp_path))

        assert "jsonl_without_summary" in _issues_by_check(report)
        assert report["exit_code"] == 0

    def test_zero_byte_file_is_warning(self, tmp_path):
        """0바이트 파일은 empty_file warning 으로 보고한다."""
        root = tmp_path / "evidence"
        root.mkdir()
        (root / "void.txt").write_text("", encoding="utf-8")

        report = crel.run_checks(root, research_runs_dir=_empty_runs_dir(tmp_path))

        assert "empty_file" in _issues_by_check(report)

    def test_missing_root_is_error(self, tmp_path):
        """root 디렉터리가 없으면 root_missing error + exit 1."""
        report = crel.run_checks(
            tmp_path / "nope", research_runs_dir=_empty_runs_dir(tmp_path))

        assert "root_missing" in _issues_by_check(report)
        assert report["exit_code"] == 1


# ===========================================================================
# research_runs 3종 문서 세트
# ===========================================================================

class TestResearchRunsDocSet:

    def test_complete_triple_is_clean(self, tmp_path):
        """plan/management/result 3종이 모두 있으면 error 0."""
        root = tmp_path / "evidence"
        root.mkdir()
        runs = tmp_path / "research_runs"
        runs.mkdir()
        for suffix in ("_plan.md", "_management.md", "_result.md"):
            (runs / f"run_a{suffix}").write_text("# doc\n", encoding="utf-8")

        report = crel.run_checks(root, research_runs_dir=runs)

        assert report["counts"]["error"] == 0

    def test_missing_member_is_error(self, tmp_path):
        """result 문서가 빠지면 research_run_doc_missing error."""
        root = tmp_path / "evidence"
        root.mkdir()
        runs = tmp_path / "research_runs"
        runs.mkdir()
        (runs / "run_a_plan.md").write_text("# p\n", encoding="utf-8")
        (runs / "run_a_management.md").write_text("# m\n", encoding="utf-8")

        report = crel.run_checks(root, research_runs_dir=runs)

        checks = _issues_by_check(report)
        assert "research_run_doc_missing" in checks
        assert "_result.md" in checks["research_run_doc_missing"][0]["detail"]
        assert report["exit_code"] == 1

    def test_empty_member_is_error(self, tmp_path):
        """3종 문서 중 0바이트 문서는 research_run_doc_empty error."""
        root = tmp_path / "evidence"
        root.mkdir()
        runs = tmp_path / "research_runs"
        runs.mkdir()
        (runs / "run_a_plan.md").write_text("# p\n", encoding="utf-8")
        (runs / "run_a_management.md").write_text("# m\n", encoding="utf-8")
        (runs / "run_a_result.md").write_text("", encoding="utf-8")

        report = crel.run_checks(root, research_runs_dir=runs)

        assert "research_run_doc_empty" in _issues_by_check(report)

    def test_absent_runs_dir_is_advisory(self, tmp_path):
        """research_runs 디렉터리 자체가 없으면 advisory 스킵."""
        root = tmp_path / "evidence"
        root.mkdir()

        report = crel.run_checks(root, research_runs_dir=tmp_path / "no_runs")

        checks = _issues_by_check(report)
        assert "research_runs_missing" in checks
        assert checks["research_runs_missing"][0]["severity"] == "advisory"
        assert report["exit_code"] == 0


# ===========================================================================
# CLI 계약
# ===========================================================================

class TestCli:

    def test_main_writes_report_and_returns_exit_code(self, tmp_path, capsys):
        """--report 파일 기록 + stdout JSON + error 존재 시 종료코드 1."""
        root = tmp_path / "evidence"
        root.mkdir()
        _write_json(root / "lost_summary.json", {
            "promising": [], "out": "lost.md", "finished": "x",
        })
        runs = _empty_runs_dir(tmp_path)
        report_path = tmp_path / "out" / "report.json"

        code = crel.main([
            "--root", str(root),
            "--research-runs", str(runs),
            "--report", str(report_path),
        ])

        assert code == 1
        assert report_path.exists()
        on_disk = json.loads(report_path.read_text(encoding="utf-8"))
        on_stdout = json.loads(capsys.readouterr().out)
        assert on_disk == on_stdout
        assert on_disk["counts"]["error"] >= 1
        assert all(
            set(issue) == {"path", "check", "severity", "detail"}
            for issue in on_disk["issues"]
        )

    def test_main_clean_set_returns_zero(self, tmp_path, capsys):
        """정상 세트에서는 종료코드 0."""
        root = tmp_path / "evidence"
        root.mkdir()
        rows = [_iter_row(0, "tpl_a", True)]
        _make_iter_eval_set(root, "camp_n1", rows, promising=["tpl_a"])
        runs = _empty_runs_dir(tmp_path)

        code = crel.main(["--root", str(root), "--research-runs", str(runs)])

        assert code == 0
        assert json.loads(capsys.readouterr().out)["exit_code"] == 0


# ===========================================================================
# 실 evidence 디렉터리 스모크 (존재 시)
# ===========================================================================

REAL_EVIDENCE_ROOT = os.path.join(
    PROJECT_ROOT, ".omo", "evidence", "tmap-walkforward")


@pytest.mark.skipif(
    not os.path.isdir(REAL_EVIDENCE_ROOT),
    reason="real evidence directory not present",
)
class TestRealEvidenceSmoke:

    def test_run_checks_produces_wellformed_report(self):
        """실 디렉터리에서 보고 구조가 유효해야 한다 (읽기 전용)."""
        report = crel.run_checks(REAL_EVIDENCE_ROOT)

        assert report["summaries_checked"] > 0
        assert set(report["counts"]) >= {"error", "warning", "advisory"}
        assert report["exit_code"] in (0, 1)
        for issue in report["issues"]:
            assert set(issue) == {"path", "check", "severity", "detail"}
            assert issue["severity"] in ("error", "warning", "advisory")
