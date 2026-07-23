# -*- coding: utf-8 -*-
"""V5.6 report_writer 계약 테스트 — 표준양식·escape·atomic·manifest·링크 재작성."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import types
from pathlib import Path
import pytest

from ai_strategy_loop.dashboard.report_writer import (
    STANDARD_SECTIONS,
    normalize_manifest,
    render_report_html,
    write_report,
    write_reports,
)
import ai_strategy_loop.dashboard.report_writer as report_writer


_PDF_EXPORT_SPEC = importlib.util.spec_from_file_location(
    "export_research_report_pdfs",
    Path(__file__).resolve().parents[3] / "scripts" / "export_research_report_pdfs.py",
)
assert _PDF_EXPORT_SPEC and _PDF_EXPORT_SPEC.loader
pdf_export = importlib.util.module_from_spec(_PDF_EXPORT_SPEC)
sys.modules[_PDF_EXPORT_SPEC.name] = pdf_export
_PDF_EXPORT_SPEC.loader.exec_module(pdf_export)


def _spec() -> dict:
    return {
        "research_id": "r8_exclude_cap",
        "step_id": "stage2",
        "title": "r8 저시총 제외 필터 검증",
        "purpose": "저시총 제외가 표본 외 안정성을 높이는지 확인",
        "date": "2026-07-19",
        "hypothesis": "저시총 종목이 슬리피지·MDD 를 키운다",
        "method": "공식 OOS 재실행 · 시총 임계 스윕",
        "results": ["연 수익 +12%", "MDD -8%"],
        "analysis": "필터 적용 시 MDD 개선이 유의",
        "conclusion": "저시총 제외 채택 후보",
        "limits": "단일 구간 · 인과 아님",
        "history": ["v1 초안", "v2 OOS 반영"],
        "related_docs": ["r8_exclude_cap__stage1.html", "https://example.com/x"],
        "related_commits": ["abc1234 필터 도입"],
        "provenance": ".omo/evidence/tmap-walkforward",
        "trust": "derived",
    }


def test_render_contains_all_standard_sections() -> None:
    html = render_report_html(_spec())
    for _key, label in STANDARD_SECTIONS:
        assert label in html, f"표준 섹션 누락: {label}"
    assert "template_id" in html and "r8_exclude_cap" in html


def test_render_escapes_content_and_has_no_script() -> None:
    spec = _spec()
    spec["analysis"] = "<script>alert(1)</script> & <b>x</b>"
    html = render_report_html(spec)
    assert "<script>" not in html  # 주입 차단
    assert "&lt;script&gt;" in html
    assert "&amp;" in html


def test_related_internal_report_link_rewritten_external_not() -> None:
    html = render_report_html(_spec())
    assert '/reports/view?path=r8_exclude_cap__stage1.html' in html  # 내부 리포트 → allowlisted 앵커
    assert '<a href="https://example.com/x"' not in html  # 외부는 앵커화하지 않음(escape 텍스트)
    assert "https://example.com/x" in html


def test_write_report_atomic_and_manifest_entry(tmp_path: Path) -> None:
    entry = write_report(_spec(), str(tmp_path))
    out = tmp_path / entry["path"]
    assert out.is_file()
    assert entry["research_id"] == "r8_exclude_cap" and entry["step_id"] == "stage2"
    assert len(entry["sha256"]) == 64 and entry["bytes"] == out.stat().st_size
    assert entry["trust"] == "derived" and entry["generated_at"].endswith("Z")
    assert entry["provenance"] == ".omo/evidence/tmap-walkforward"


def test_write_reports_manifest_shape_and_typed_envelope(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    second = _spec()
    second["step_id"] = "stage3"
    manifest = write_reports([_spec(), second], str(tmp_path), str(manifest_path))
    assert manifest["schema_version"] == "stom-research-report-v1"
    assert manifest["status"] == "complete"
    assert manifest["generator"] == "ai_strategy_loop.dashboard.report_writer"
    assert manifest["count"] == 2
    assert set(manifest["limits"]) == {"max_reports", "max_bytes_each"}
    on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert on_disk["count"] == 2 and len(on_disk["reports"]) == 2
    for report in on_disk["reports"]:
        assert report["report_type"] == "step"
        assert report["run_id"] == "r8_exclude_cap"
        assert report["generation"] is None and report["cycle"] is None
        assert report["status"] == "complete"
        assert len(report["content_sha256"]) == len(report["source_sha256"]) == 64
        assert report["sha256"] == report["content_sha256"]  # legacy alias
        assert report["toc"][0] == {"id": "sec-hypothesis", "label": "가설 / 원인"}
        assert report["content_sha256"] == __import__("hashlib").sha256(
            (tmp_path / report["path"]).read_bytes()
        ).hexdigest()
def test_normalize_manifest_reads_legacy_shape() -> None:
    legacy = {
        "generated_at": "2026-07-19T00:00:00Z",
        "count": 1,
        "reports": [{
            "research_id": "legacy-run", "step_id": "gen7", "path": "legacy-run__gen7.html",
            "sha256": "a" * 64, "bytes": 1, "trust": "derived",
        }],
    }
    normalized = normalize_manifest(legacy)
    report = normalized["reports"][0]
    assert normalized["schema_version"] == "stom-research-report-v1"
    assert report["generation"] == 7 and report["content_sha256"] == "a" * 64
    assert report["sha256"] == "a" * 64  # legacy consumer remains supported
def test_normalize_manifest_rejects_unknown_version_and_unrecognized_legacy_shape() -> None:
    with pytest.raises(ValueError, match="not recognized"):
        normalize_manifest({"schema_version": "stom-research-report-v2"})
    with pytest.raises(ValueError, match="recognized schema-less"):
        normalize_manifest({"generated_at": "2026-07-19T00:00:00Z", "count": 0, "reports": [], "extra": True})


def test_publish_reports_rejects_incomplete_v1_entry_before_mutation(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    write_reports([_spec()], str(tmp_path), str(manifest_path))
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    del payload["reports"][0]["report_id"]
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    before = manifest_path.read_bytes()

    with pytest.raises(ValueError, match="invalid"):
        write_reports([dict(_spec(), step_id="stage3")], str(tmp_path), str(manifest_path))

    assert manifest_path.read_bytes() == before
    assert not (tmp_path / "r8_exclude_cap__stage3.html").exists()


def test_specs_from_loop_runs_builds_standard_specs(tmp_path: Path) -> None:
    # V6.4(S5): loop_runs.db → 세대별 스텝 spec 자동 구성(SELECT-only·오프라인).
    import sqlite3
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
    from build_step_reports import specs_from_loop_runs

    db = tmp_path / "loop_runs.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE runs (run_id TEXT PRIMARY KEY, started_at REAL, config_json TEXT, status TEXT, best_gen INTEGER, best_score REAL, finished_at REAL)")
    conn.execute("CREATE TABLE generations (run_id TEXT, gen_no INTEGER, buy_name TEXT, sell_name TEXT, status TEXT, score REAL, calmar REAL, uptrend_r2 REAL, gate_passed INTEGER, reason TEXT, csv_path TEXT, trade_count INTEGER, mdd REAL, profit REAL, strategy_gist TEXT, created_at REAL, PRIMARY KEY (run_id, gen_no))")
    conn.execute("INSERT INTO runs VALUES ('runA', 1752900000, '{}', 'done', 2, 1.5, 1752903600)")
    conn.execute("INSERT INTO generations (run_id, gen_no, buy_name, sell_name, status, score, gate_passed, reason, trade_count, mdd, profit, strategy_gist, created_at) "
                 "VALUES ('runA', 1, 'buy1', 'sell1', 'done', 0.8, 0, '거래빈도 미달', 3, 12.0, -50000, '갭 상승 추종', 1752900100)")
    conn.execute("INSERT INTO generations (run_id, gen_no, buy_name, sell_name, status, score, gate_passed, reason, trade_count, mdd, profit, strategy_gist, created_at) "
                 "VALUES ('runA', 2, 'buy2', 'sell2', 'done', 1.5, 1, '', 9, 8.0, 120000, '갭+거래강도', 1752900200)")
    conn.commit()
    conn.close()

    specs = specs_from_loop_runs(str(db))
    assert len(specs) == 2
    s2 = specs[1]
    assert s2["research_id"] == "runA" and s2["step_id"] == "gen2"
    assert "게이트 통과 후보" in s2["conclusion"] and "best gen 2" in s2["conclusion"]
    assert s2["hypothesis"] == "갭+거래강도"
    assert any("gate 통과" in r for r in s2["results"])
    assert s2["date"] == "2026-07-19" or s2["date"].startswith("20")  # epoch 포맷
    # 표준양식 렌더까지 통과(주입 없음)
    from ai_strategy_loop.dashboard.report_writer import render_report_html
    html = render_report_html(s2)
    assert "<script" not in html and "runA" in html

def test_build_run_report_flow_svg_and_blocks(tmp_path: Path) -> None:
    # v5.3.3(U4): run 종합 보고서 — 개선 흐름도 SVG + 세대 블록 + 무script + 안전 문구.
    import sqlite3
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
    from build_step_reports import build_run_report

    db = tmp_path / "loop_runs.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE runs (run_id TEXT PRIMARY KEY, started_at REAL, config_json TEXT, status TEXT, best_gen INTEGER, best_score REAL, finished_at REAL)")
    conn.execute("CREATE TABLE generations (run_id TEXT, gen_no INTEGER, buy_name TEXT, sell_name TEXT, status TEXT, score REAL, calmar REAL, uptrend_r2 REAL, gate_passed INTEGER, reason TEXT, csv_path TEXT, trade_count INTEGER, mdd REAL, profit REAL, strategy_gist TEXT, created_at REAL, PRIMARY KEY (run_id, gen_no))")
    conn.execute("INSERT INTO runs VALUES ('runB', 1752900000, '{}', 'done', 3, 1.7, 1752903600)")
    for gen, score, gate in [(1, 0.6, 0), (2, 1.1, 0), (3, 1.7, 1)]:
        conn.execute("INSERT INTO generations (run_id, gen_no, buy_name, sell_name, status, score, gate_passed, reason, trade_count, mdd, profit, strategy_gist, created_at) "
                     "VALUES ('runB', ?, 'b', 's', 'done', ?, ?, 'r', 5, 10.0, 1000, 'g', 1752900100)", (gen, score, gate))
    conn.commit()
    conn.close()

    written = build_run_report(str(db), str(tmp_path))
    assert len(written) == 1 and written[0]["run_id"] == "runB"
    html = (tmp_path / "run_report_runB.html").read_text(encoding="utf-8")
    assert "<script" not in html  # 무script(CSP/sandbox 그대로 통과)
    assert "<svg" in html and "<polyline" in html  # 개선 흐름도
    assert 'id="sec-flow"' in html and 'id="sec-gens"' in html
    assert "통과" in html
    assert "표본 내 지표이며 성능 증명이 아님" in html
    assert "/reports/view?path=generated_reports/runB__gen1.html" not in html  # 생성하지 않은 상세 리포트 링크 금지
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["reports"][0]["report_type"] == "run"
    assert manifest["reports"][0]["status"] == "done"
    assert manifest["reports"][0]["publication_status"] == "complete"
    assert manifest["reports"][0]["content_sha256"] == written[0]["content_sha256"]
    assert "누적 profit" not in html
    assert "세대별 스텝 기록" in html


def test_publish_reports_rejects_tampered_registered_entry_without_rewriting(tmp_path: Path) -> None:
    first = dict(_spec(), research_id="first", step_id="stage1")
    second = dict(_spec(), research_id="second", step_id="stage2")
    manifest_path = tmp_path / "manifest.json"
    write_reports([first, second], str(tmp_path), str(manifest_path))
    (tmp_path / "first__stage1.html").write_text("tampered", encoding="utf-8")
    before_manifest = manifest_path.read_bytes()
    before_second = (tmp_path / "second__stage2.html").read_bytes()

    third = dict(_spec(), research_id="third", step_id="stage3")
    with pytest.raises(ValueError, match=r"(?:bytes|content_sha256) mismatch"):
        write_reports([third], str(tmp_path), str(manifest_path))

    assert manifest_path.read_bytes() == before_manifest
    assert (tmp_path / "second__stage2.html").read_bytes() == before_second
def test_publish_reports_rejects_corrupt_manifest_without_rewriting(tmp_path: Path) -> None:
    first = dict(_spec(), research_id="first", step_id="stage1")
    manifest_path = tmp_path / "manifest.json"
    write_reports([first], str(tmp_path), str(manifest_path))
    before_report = (tmp_path / "first__stage1.html").read_bytes()
    manifest_path.write_text("{corrupt", encoding="utf-8")
    before_manifest = manifest_path.read_bytes()

    with pytest.raises(ValueError, match="corrupt"):
        write_reports([dict(_spec(), research_id="second", step_id="stage2")], str(tmp_path), str(manifest_path))

    assert manifest_path.read_bytes() == before_manifest
    assert (tmp_path / "first__stage1.html").read_bytes() == before_report
    assert not (tmp_path / "second__stage2.html").exists()
@pytest.mark.parametrize("raw", [
    '{"schema_version":"stom-research-report-v1","schema_version":"stom-research-report-v1"}',
    '{"schema_version":NaN}',
])
def test_publish_reports_rejects_non_strict_json_before_mutation(tmp_path: Path, raw: str) -> None:
    manifest_path = tmp_path / "manifest.json"
    write_reports([_spec()], str(tmp_path), str(manifest_path))
    manifest_path.write_text(raw, encoding="utf-8")
    before = manifest_path.read_bytes()

    with pytest.raises(ValueError, match="unreadable or corrupt"):
        write_reports([dict(_spec(), step_id="stage3")], str(tmp_path), str(manifest_path))

    assert manifest_path.read_bytes() == before
    assert not (tmp_path / "r8_exclude_cap__stage3.html").exists()


def test_publish_reports_rejects_invalid_registered_entry_without_rewriting(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    write_reports([_spec()], str(tmp_path), str(manifest_path))
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["reports"][0]["path"] = "not-html.txt"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    before_manifest = manifest_path.read_bytes()

    with pytest.raises(ValueError, match="invalid"):
        write_reports([dict(_spec(), step_id="stage3")], str(tmp_path), str(manifest_path))

    assert manifest_path.read_bytes() == before_manifest
    assert not (tmp_path / "r8_exclude_cap__stage3.html").exists()


@pytest.mark.parametrize(
    ("paths", "message"),
    [
        (["report.txt"], "HTML path"),
        (["same.html", "nested/../same.html"], "canonical"),
        (["manifest.json"], "HTML path"),
    ],
)
def test_publish_reports_rejects_invalid_or_colliding_destinations(tmp_path: Path, paths: list[str], message: str) -> None:
    rendered = [
        (dict(_spec(), step_id=f"stage{index}"), path, render_report_html(_spec()), "step")
        for index, path in enumerate(paths)
    ]

    with pytest.raises(ValueError, match=message):
        report_writer.publish_reports(rendered, str(tmp_path))

    assert not (tmp_path / "manifest.json").exists()
    assert not (tmp_path / "same.html").exists()


def test_publish_reports_rejects_custom_manifest_collision(tmp_path: Path) -> None:
    rendered = [(_spec(), "custom-manifest.json.html", render_report_html(_spec()), "step")]

    with pytest.raises(ValueError, match="collides"):
        report_writer.publish_reports(rendered, str(tmp_path), str(tmp_path / "custom-manifest.json.html"))

    assert not (tmp_path / "custom-manifest.json.html").exists()


def test_publish_reports_rejects_linked_parent_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory links unavailable: {error}")

    with pytest.raises(ValueError, match="escapes"):
        report_writer.publish_reports([(_spec(), "linked/escape.html", render_report_html(_spec()), "step")], str(tmp_path))

    assert not (outside / "escape.html").exists()


def test_publish_reports_rolls_back_when_completed_snapshot_verification_fails(tmp_path: Path, monkeypatch) -> None:
    first = dict(_spec(), research_id="first", step_id="stage1")
    manifest_path = tmp_path / "manifest.json"
    write_reports([first], str(tmp_path), str(manifest_path))
    before_manifest = manifest_path.read_bytes()
    before_report = (tmp_path / "first__stage1.html").read_bytes()

    def fail_verification(*_args: object, **_kwargs: object) -> None:
        raise ValueError("injected snapshot verification failure")

    monkeypatch.setattr(report_writer, "_verify_published_snapshot", fail_verification)
    with pytest.raises(ValueError, match="snapshot verification"):
        write_reports([dict(first, analysis="replacement")], str(tmp_path), str(manifest_path))

    assert manifest_path.read_bytes() == before_manifest
    assert (tmp_path / "first__stage1.html").read_bytes() == before_report
def test_publish_reports_rolls_back_replaced_files_when_later_replacement_fails(tmp_path: Path, monkeypatch) -> None:
    first = _spec()
    first["research_id"] = "first"
    first["step_id"] = "stage1"
    manifest_path = tmp_path / "manifest.json"
    write_reports([first], str(tmp_path), str(manifest_path))
    old_manifest = manifest_path.read_bytes()
    old_first = (tmp_path / "first__stage1.html").read_bytes()

    updated = dict(first, analysis="new bytes must not survive a failed publication")
    second = dict(_spec(), research_id="second", step_id="stage2")
    real_replace = report_writer.os.replace

    def fail_second_replace(source: str, destination: str) -> None:
        if Path(destination) == tmp_path / "second__stage2.html":
            raise OSError("injected replacement failure")
        real_replace(source, destination)

    monkeypatch.setattr(report_writer.os, "replace", fail_second_replace)
    with pytest.raises(OSError, match="injected replacement failure"):
        write_reports([updated, second], str(tmp_path), str(manifest_path))

    assert manifest_path.read_bytes() == old_manifest
    assert (tmp_path / "first__stage1.html").read_bytes() == old_first
    assert not (tmp_path / "second__stage2.html").exists()
def test_publish_reports_retains_recovery_backups_when_rollback_fails(tmp_path: Path, monkeypatch) -> None:
    first = dict(_spec(), research_id="first", step_id="stage1")
    manifest_path = tmp_path / "manifest.json"
    write_reports([first], str(tmp_path), str(manifest_path))
    second = dict(_spec(), research_id="second", step_id="stage2")
    first_path = tmp_path / "first__stage1.html"
    second_path = tmp_path / "second__stage2.html"
    old_first = first_path.read_bytes()
    real_replace = report_writer.os.replace

    def fail_replacement_and_rollback(source: str, destination: str) -> None:
        if Path(destination) == second_path:
            raise OSError("injected replacement failure")
        if Path(destination) == first_path and ".rollback." in str(source):
            raise OSError("injected rollback failure")
        real_replace(source, destination)

    monkeypatch.setattr(report_writer.os, "replace", fail_replacement_and_rollback)
    with pytest.raises(RuntimeError, match=r"injected rollback failure.*recovery backups retained") as error:
        write_reports([dict(first, analysis="replacement"), second], str(tmp_path), str(manifest_path))

    recovery = str(error.value).split("recovery backups retained: ", 1)[1]
    assert Path(recovery).exists()
    assert Path(recovery).read_bytes() == old_first
    assert list(tmp_path.parent.glob(f".{tmp_path.name}.rollback.*"))


def test_loop_runs_source_digest_includes_committed_wal_rows(tmp_path: Path) -> None:
    import sqlite3
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
    from build_step_reports import specs_from_loop_runs

    db = tmp_path / "loop_runs.db"
    writer = sqlite3.connect(db)
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("CREATE TABLE runs (run_id TEXT PRIMARY KEY, status TEXT, best_gen INTEGER, best_score REAL)")
    writer.execute("CREATE TABLE generations (run_id TEXT, gen_no INTEGER, buy_name TEXT, sell_name TEXT, status TEXT, score REAL, mdd REAL, profit REAL, trade_count INTEGER, gate_passed INTEGER, reason TEXT, strategy_gist TEXT, created_at REAL)")
    writer.execute("INSERT INTO runs VALUES ('wal-run', 'complete', 1, 1.0)")
    writer.execute("INSERT INTO generations VALUES ('wal-run', 1, 'b', 's', 'success', 1.0, 2, 3, 4, 1, '', '', 1752900000)")
    writer.commit()
    before = specs_from_loop_runs(str(db))[0]["source_sha256"]
    writer.execute("UPDATE generations SET score = 2.0 WHERE run_id = 'wal-run'")
    writer.commit()
    after = specs_from_loop_runs(str(db))[0]["source_sha256"]
    writer.close()

    assert before != after


def test_run_report_excludes_failed_measurements_and_preserves_unavailable_evidence(tmp_path: Path) -> None:
    import sqlite3
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
    from build_step_reports import build_run_report

    db = tmp_path / "loop_runs.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE runs (run_id TEXT PRIMARY KEY, started_at REAL, config_json TEXT, status TEXT, best_gen INTEGER, best_score REAL, finished_at REAL)")
    conn.execute("CREATE TABLE generations (run_id TEXT, gen_no INTEGER, buy_name TEXT, sell_name TEXT, status TEXT, score REAL, mdd REAL, profit REAL, trade_count INTEGER, gate_passed INTEGER, reason TEXT, strategy_gist TEXT)")
    conn.execute("INSERT INTO runs VALUES ('runC', 1, '{}', 'complete', 1, 10, 2)")
    conn.execute("INSERT INTO generations VALUES ('runC', 1, 'b', 's', 'ok', 10, 2, 100, 5, 1, '', '')")
    conn.execute("INSERT INTO generations VALUES ('runC', 2, 'b', 's', 'error', 0, 0, 0, 0, 0, 'failed', '')")
    conn.commit()
    conn.close()

    written = build_run_report(str(db), str(tmp_path))
    html = (tmp_path / "run_report_runC.html").read_text(encoding="utf-8")
    assert "평균 score" in html and "10.00" in html
    assert "성과 집계 제외: 1건" in html
    assert "unavailable: RuntimeError" in html
    assert written[0]["evidence"]["prompts"] is None
    assert written[0]["evidence"]["availability"]["prompts"] == "unavailable: RuntimeError"


def test_standard_report_has_scriptless_internal_navigation_and_print_contract() -> None:
    html = render_report_html(_spec())

    assert '<meta name="viewport"' in html
    assert '<nav class="toc" aria-label="보고서 목차">' in html
    assert 'href="#sec-hypothesis"' in html
    assert "@media print" in html
    assert "<script" not in html
    assert "table-wrap{overflow-x:auto" in html
    assert "print-break" in html
    assert 'name="report-theme"' in html
    assert "template-executive" in html


@pytest.mark.parametrize("template_id,marker", [
    ("executive", "경영 요약"), ("quant_research", "QUANT RESEARCH"), ("research_journal", "SOURCE-BACKED RESEARCH REPORT"),
])
@pytest.mark.parametrize("theme", ["system", "light", "dark", "print"])
def test_templates_have_distinct_hierarchy_and_theme_metadata(template_id: str, marker: str, theme: str) -> None:
    spec = dict(_spec(), template_id=template_id, theme=theme, blocks=[
        {"type": "table", "id": "metrics", "title": "긴 표", "columns": ["A", "B"], "rows": [["<unsafe>", "+1"]]},
        {"type": "svg", "id": "chart", "title": "차트", "svg": '<svg class="chart" viewBox="0 0 1 1"><circle cx="0" cy="0" r="1"/></svg>'},
        {"type": "decision", "id": "decision", "title": "결정", "text": "hold", "page_break": True},
    ])
    rendered = render_report_html(spec)
    assert marker in rendered and f"<dd>{theme}</dd>" in rendered
    assert 'class="table-wrap"' in rendered and 'class="signed-positive">+1' in rendered
    assert "&lt;unsafe&gt;" in rendered and "<script" not in rendered
    assert "<svg" in rendered and "print-break" in rendered
    assert "sticky" in rendered and "@media print" in rendered


def test_manifest_records_renderer_and_template_metadata(tmp_path: Path) -> None:
    entry = write_report(dict(_spec(), template_id="research_journal", theme="print"), str(tmp_path))
    assert entry["renderer_version"] == report_writer.RENDERER_VERSION
    assert entry["template_id"] == "research_journal" and entry["theme"] == "print"
def test_svg_rejects_event_handlers_and_external_references() -> None:
    html = render_report_html(dict(_spec(), blocks=[
        {"type": "svg", "id": "chart", "title": "차트", "svg": '<svg onerror="x" href="https://bad"><circle/></svg>'},
    ]))
    assert "onerror=" not in html and 'href="https://bad"' not in html
    assert "차트를 안전하게 표시할 수 없음" in html


def test_unknown_template_or_theme_is_rejected() -> None:
    with pytest.raises(ValueError, match="template_id"):
        render_report_html(dict(_spec(), template_id="untrusted"))
    with pytest.raises(ValueError, match="theme"):
        render_report_html(dict(_spec(), theme="untrusted"))



def _pdf_renderer(html_path: Path, pdf_path: Path) -> None:
    assert html_path.read_bytes()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(b"%PDF-1.4\noffline fixture\n")


def test_pdf_publication_adds_html_provenance_parity_fields(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    original = write_reports([_spec()], str(tmp_path), str(manifest_path))

    published = pdf_export.publish_pdf_companions(tmp_path, manifest_path, renderer=_pdf_renderer)

    before = original["reports"][0]
    entry = published["reports"][0]
    pdf_path = tmp_path / entry["pdf_path"]
    assert entry["path"] == before["path"]
    assert entry["content_sha256"] == before["content_sha256"]
    assert entry["pdf_path"] == before["path"].replace(".html", ".pdf")
    assert entry["pdf_source_content_sha256"] == entry["content_sha256"]
    assert entry["pdf_bytes"] == pdf_path.stat().st_size
    assert entry["pdf_sha256"] == hashlib.sha256(pdf_path.read_bytes()).hexdigest()
@pytest.mark.parametrize("damage", ["missing", "tampered"])
def test_writer_rejects_missing_or_tampered_registered_pdf_before_rewriting(tmp_path: Path, damage: str) -> None:
    manifest_path = tmp_path / "manifest.json"
    write_reports([_spec()], str(tmp_path), str(manifest_path))
    pdf_export.publish_pdf_companions(tmp_path, manifest_path, renderer=_pdf_renderer)
    manifest_before = manifest_path.read_bytes()
    entry = json.loads(manifest_before)["reports"][0]
    pdf_path = tmp_path / entry["pdf_path"]
    if damage == "missing":
        pdf_path.unlink()
    else:
        pdf_path.write_bytes(b"tampered PDF")
    damaged_pdf = pdf_path.read_bytes() if pdf_path.exists() else None

    with pytest.raises(ValueError, match=r"PDF (?:is unreadable|bytes mismatch)"):
        write_reports(
            [dict(_spec(), research_id="replacement", step_id="stage3")],
            str(tmp_path),
            str(manifest_path),
        )

    assert manifest_path.read_bytes() == manifest_before
    assert (pdf_path.read_bytes() if pdf_path.exists() else None) == damaged_pdf
    assert not (tmp_path / "replacement__stage3.html").exists()




def test_pdf_publication_rejects_tampered_registered_html(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest = write_reports([_spec()], str(tmp_path), str(manifest_path))
    html_path = tmp_path / manifest["reports"][0]["path"]
    html_path.write_text("tampered", encoding="utf-8")
    original_manifest = manifest_path.read_bytes()
    called = False

    def renderer(_html: Path, _pdf: Path) -> None:
        nonlocal called
        called = True

    with pytest.raises(ValueError, match=r"HTML (?:bytes|content_sha256) mismatch"):
        pdf_export.publish_pdf_companions(tmp_path, manifest_path, renderer=renderer)

    assert not called
    assert manifest_path.read_bytes() == original_manifest


def test_pdf_publication_rolls_back_pdfs_when_later_replacement_fails(tmp_path: Path, monkeypatch) -> None:
    manifest_path = tmp_path / "manifest.json"
    second = dict(_spec(), research_id="second", step_id="stage2")
    write_reports([_spec(), second], str(tmp_path), str(manifest_path))
    pdf_export.publish_pdf_companions(tmp_path, manifest_path, renderer=_pdf_renderer)
    original_manifest = manifest_path.read_bytes()
    original_pdfs = {
        path.name: path.read_bytes()
        for path in tmp_path.glob("*.pdf")
    }
    real_replace = pdf_export.os.replace

    def fail_second_pdf_replace(source: str | Path, destination: str | Path) -> None:
        if (
            Path(source).suffix == ".tmp"
            and Path(destination).suffix == ".pdf"
            and Path(destination).name.startswith("second")
        ):
            raise OSError("injected PDF replacement failure")
        real_replace(source, destination)

    monkeypatch.setattr(pdf_export.os, "replace", fail_second_pdf_replace)
    with pytest.raises(OSError, match="injected PDF replacement failure"):
        pdf_export.publish_pdf_companions(tmp_path, manifest_path, renderer=_pdf_renderer)

    assert manifest_path.read_bytes() == original_manifest
    assert {path.name: path.read_bytes() for path in tmp_path.glob("*.pdf")} == original_pdfs
@pytest.mark.parametrize("publish", [False, True])
def test_pdf_validator_rejects_repeated_destination_identity_even_with_same_label(tmp_path: Path, publish: bool) -> None:
    manifest_path = tmp_path / "manifest.json"
    write_reports([_spec()], str(tmp_path), str(manifest_path))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["reports"].append(dict(manifest["reports"][0]))
    manifest["count"] = 2
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    before = manifest_path.read_bytes()

    if publish:
        with pytest.raises(ValueError, match="destinations collide"):
            pdf_export.publish_pdf_companions(tmp_path, manifest_path, renderer=_pdf_renderer)
    else:
        with pytest.raises(ValueError, match="destinations collide"):
            pdf_export.validate_pdf_companions(tmp_path, manifest_path)

    assert manifest_path.read_bytes() == before
    assert not list(tmp_path.glob("*.pdf"))


def test_pdf_postcommit_verification_failure_restores_manifest_and_pdfs(tmp_path: Path, monkeypatch) -> None:
    manifest_path = tmp_path / "manifest.json"
    write_reports([_spec()], str(tmp_path), str(manifest_path))
    pdf_export.publish_pdf_companions(tmp_path, manifest_path, renderer=_pdf_renderer)
    before_manifest = manifest_path.read_bytes()
    before_pdfs = {path.name: path.read_bytes() for path in tmp_path.glob("*.pdf")}

    def fail_verification(*_args: object, **_kwargs: object) -> None:
        raise ValueError("injected PDF snapshot verification failure")

    monkeypatch.setattr(pdf_export, "_verify_published_pdf_snapshot", fail_verification)
    with pytest.raises(ValueError, match="snapshot verification"):
        pdf_export.publish_pdf_companions(tmp_path, manifest_path, renderer=_pdf_renderer)

    assert manifest_path.read_bytes() == before_manifest
    assert {path.name: path.read_bytes() for path in tmp_path.glob("*.pdf")} == before_pdfs


def test_pdf_check_rejects_tampered_pdf_without_rewriting(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    write_reports([_spec()], str(tmp_path), str(manifest_path))
    published = pdf_export.publish_pdf_companions(tmp_path, manifest_path, renderer=_pdf_renderer)
    pdf_path = tmp_path / published["reports"][0]["pdf_path"]
    pdf_path.write_bytes(b"tampered PDF")
    before_manifest = manifest_path.read_bytes()

    with pytest.raises(ValueError, match="PDF bytes mismatch"):
        pdf_export.validate_pdf_companions(tmp_path, manifest_path)

    assert manifest_path.read_bytes() == before_manifest


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda manifest: manifest.__setitem__("count", True), "strict"),
        (lambda manifest: manifest.__setitem__("status", "done"), "strict"),
        (lambda manifest: manifest["limits"].__setitem__("max_reports", 1), "strict"),
        (lambda manifest: manifest["reports"][0].__setitem__("content_sha256", "A" * 64), "provenance"),
        (lambda manifest: manifest["reports"][0].__setitem__("bytes", True), "provenance"),
        (lambda manifest: manifest["reports"][0].__setitem__("path", "nested/../r8_exclude_cap__stage2.html"), "canonical"),
    ],
)
def test_pdf_publication_rejects_strict_manifest_tampering_before_render(
    tmp_path: Path, mutate, message: str,
) -> None:
    manifest_path = tmp_path / "manifest.json"
    write_reports([_spec()], str(tmp_path), str(manifest_path))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mutate(manifest)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    before = manifest_path.read_bytes()
    called = False

    def renderer(_html: Path, _pdf: Path) -> None:
        nonlocal called
        called = True

    with pytest.raises(ValueError, match=message):
        pdf_export.publish_pdf_companions(tmp_path, manifest_path, renderer=renderer)

    assert not called
    assert manifest_path.read_bytes() == before
    assert not list(tmp_path.glob("*.pdf"))
@pytest.mark.parametrize(
    "mutate",
    [
        lambda entry: entry.pop("report_id"),
        lambda entry: entry.__setitem__("unexpected", "field"),
        lambda entry: entry.__setitem__("publication_status", "draft"),
    ],
)
@pytest.mark.parametrize("publish", [False, True])
def test_pdf_check_and_publish_share_complete_v1_entry_validation(tmp_path: Path, mutate, publish: bool) -> None:
    manifest_path = tmp_path / "manifest.json"
    write_reports([_spec()], str(tmp_path), str(manifest_path))
    if not publish:
        pdf_export.publish_pdf_companions(tmp_path, manifest_path, renderer=_pdf_renderer)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mutate(manifest["reports"][0])
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    before = manifest_path.read_bytes()
    called = False

    def renderer(_html: Path, _pdf: Path) -> None:
        nonlocal called
        called = True

    if publish:
        with pytest.raises(ValueError, match="strict"):
            pdf_export.publish_pdf_companions(tmp_path, manifest_path, renderer=renderer)
        assert not called
    else:
        with pytest.raises(ValueError, match="strict"):
            pdf_export.validate_pdf_companions(tmp_path, manifest_path)
    assert manifest_path.read_bytes() == before


def test_pdf_publication_replaces_existing_live_files_without_a_gap(tmp_path: Path, monkeypatch) -> None:
    manifest_path = tmp_path / "manifest.json"
    write_reports([_spec()], str(tmp_path), str(manifest_path))
    published = pdf_export.publish_pdf_companions(tmp_path, manifest_path, renderer=_pdf_renderer)
    pdf_path = tmp_path / published["reports"][0]["pdf_path"]
    real_replace = pdf_export.os.replace
    observed: list[Path] = []

    def assert_live_before_replace(source: str | Path, destination: str | Path) -> None:
        target = Path(destination)
        if target in {pdf_path, manifest_path} and Path(source).suffix == ".tmp":
            assert target.exists()
            observed.append(target)
        real_replace(source, destination)

    monkeypatch.setattr(pdf_export.os, "replace", assert_live_before_replace)
    pdf_export.publish_pdf_companions(tmp_path, manifest_path, renderer=_pdf_renderer)

    assert observed == [pdf_path, manifest_path]


def test_pdf_rollback_failure_preserves_copy_backup_and_reports_path(tmp_path: Path, monkeypatch) -> None:
    manifest_path = tmp_path / "manifest.json"
    write_reports([_spec()], str(tmp_path), str(manifest_path))
    published = pdf_export.publish_pdf_companions(tmp_path, manifest_path, renderer=_pdf_renderer)
    pdf_path = tmp_path / published["reports"][0]["pdf_path"]
    original_pdf = pdf_path.read_bytes()
    real_replace = pdf_export.os.replace

    def fail_manifest_commit_and_pdf_restore(source: str | Path, destination: str | Path) -> None:
        source_path = Path(source)
        destination_path = Path(destination)
        if source_path.parent.name.startswith(".report-pdf-rollback.") and destination_path == pdf_path:
            raise OSError("injected PDF rollback failure")
        if source_path.suffix == ".tmp" and destination_path == manifest_path:
            raise OSError("injected manifest commit failure")
        real_replace(source, destination)

    monkeypatch.setattr(pdf_export.os, "replace", fail_manifest_commit_and_pdf_restore)
    with pytest.raises(RuntimeError, match="recovery backups retained:") as error:
        pdf_export.publish_pdf_companions(tmp_path, manifest_path, renderer=_pdf_renderer)

    recovery_dirs = list(tmp_path.parent.glob(".report-pdf-rollback.*"))
    assert len(recovery_dirs) == 1
    backup = recovery_dirs[0] / "0.backup"
    assert backup.read_bytes() == original_pdf
    assert str(backup) in str(error.value)



def test_pdf_publication_rejects_manifest_destination_collision_before_render(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest = write_reports([_spec()], str(tmp_path), str(manifest_path))
    colliding_manifest = tmp_path / manifest["reports"][0]["path"].replace(".html", ".pdf")
    colliding_manifest.write_bytes(manifest_path.read_bytes())
    called = False

    def renderer(_html: Path, _pdf: Path) -> None:
        nonlocal called
        called = True

    with pytest.raises(ValueError, match="manifest destination collides"):
        pdf_export.publish_pdf_companions(tmp_path, colliding_manifest, renderer=renderer)

    assert not called
    assert colliding_manifest.read_bytes() == manifest_path.read_bytes()


def test_pdf_rollback_attempts_every_restoration_and_aggregates_failures(tmp_path: Path, monkeypatch) -> None:
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"
    first_backup = tmp_path / "first.backup"
    second_backup = tmp_path / "second.backup"
    first.write_bytes(b"new-first")
    second.write_bytes(b"new-second")
    first_backup.write_bytes(b"old-first")
    second_backup.write_bytes(b"old-second")
    attempted: list[Path] = []
    real_replace = pdf_export.os.replace

    def fail_restores(source: str | Path, destination: str | Path) -> None:
        attempted.append(Path(destination))
        if Path(source).suffix == ".backup":
            raise OSError(f"cannot restore {Path(destination).name}")
        real_replace(source, destination)

    monkeypatch.setattr(pdf_export.os, "replace", fail_restores)
    failures = pdf_export._rollback_replacements([(first, first_backup), (second, second_backup)])

    assert [path.name for path in attempted] == ["second.pdf", "first.pdf"]
    assert [str(error) for error in failures] == [
        "cannot restore second.pdf",
        "cannot restore first.pdf",
    ]


def test_local_pdf_renderer_blocks_unregistered_file_requests(tmp_path: Path, monkeypatch) -> None:
    allowed = tmp_path / "allowed.html"
    unrelated = tmp_path / "unrelated.html"
    output = tmp_path / "output.pdf"
    allowed.write_text("<html></html>", encoding="utf-8")
    unrelated.write_text("<html></html>", encoding="utf-8")
    routes: list[object] = []
    context_options: dict[str, object] = {}

    class Route:
        def __init__(self, url: str) -> None:
            self.request = types.SimpleNamespace(url=url)
            self.result = ""

        def continue_(self) -> None:
            self.result = "continued"

        def abort(self) -> None:
            self.result = "aborted"

    class Page:
        def route(self, _pattern: str, handler) -> None:
            self.handler = handler

        def goto(self, url: str, **_kwargs) -> None:
            route = Route(url)
            routes.append(route)
            self.handler(route)

        def pdf(self, *, path: str, **_kwargs) -> None:
            route = Route(unrelated.resolve().as_uri())
            routes.append(route)
            self.handler(route)
            Path(path).write_bytes(b"%PDF-1.4\nfixture\n")

    class Context:
        def new_page(self) -> Page:
            return Page()

        def close(self) -> None:
            pass

    class Browser:
        def new_context(self, **kwargs) -> Context:
            context_options.update(kwargs)
            return Context()

        def close(self) -> None:
            pass

    class Playwright:
        chromium = types.SimpleNamespace(launch=lambda: Browser())

    class PlaywrightManager:
        def __enter__(self) -> Playwright:
            return Playwright()

        def __exit__(self, *_args) -> None:
            pass

    sync_api = types.ModuleType("playwright.sync_api")
    sync_api.sync_playwright = lambda: PlaywrightManager()
    monkeypatch.setitem(sys.modules, "playwright", types.ModuleType("playwright"))
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api)

    pdf_export._render_pdf_locally(allowed, output, allowed_assets={allowed})

    assert context_options == {"java_script_enabled": False, "service_workers": "block"}
    assert [route.result for route in routes] == ["continued", "aborted"]
    assert output.read_bytes()
