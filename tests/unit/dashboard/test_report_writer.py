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
