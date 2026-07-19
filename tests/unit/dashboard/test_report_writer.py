# -*- coding: utf-8 -*-
"""V5.6 report_writer 계약 테스트 — 표준양식·escape·atomic·manifest·링크 재작성."""
from __future__ import annotations

import json
from pathlib import Path

from ai_strategy_loop.dashboard.report_writer import (
    STANDARD_SECTIONS,
    render_report_html,
    write_report,
    write_reports,
)


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
    assert "연구목적" in html and "r8_exclude_cap" in html


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


def test_write_reports_manifest_shape(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest = write_reports([_spec(), _spec()], str(tmp_path), str(manifest_path))
    assert manifest["count"] == 2
    assert set(manifest["limits"]) == {"max_reports", "max_bytes_each"}
    on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert on_disk["count"] == 2 and len(on_disk["reports"]) == 2
    assert all(len(r["sha256"]) == 64 for r in on_disk["reports"])

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
    assert html.count('id="h-gen-') == 3  # 세대 블록 3개(v5.3.9 앵커 id 포함)
    assert 'id="sec-flow"' in html and 'id="gen-1"' in html  # TOC 앵커
    assert "gate 통과 ✓" in html  # gen3 통과 마커
    assert "performance_proved=false" in html  # 안전 문구
    assert "/reports/view?path=generated_reports/runB__gen1.html" in html  # 스텝 리포트 링크
