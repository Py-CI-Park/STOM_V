# -*- coding: utf-8 -*-
"""QSP 보고서 매니페스트 무결성 회귀 테스트.

배경(실측 2026-08-07): 대시보드는 매니페스트의 `content_sha256`·`bytes` 가 **디스크
파일과 일치할 때만** 보고서를 'verified' 로 표시한다. 그런데 `core.autocrlf=true`
환경에서 체크아웃되면 HTML 이 CRLF 로 변환돼 바이트가 늘어난다 — 등록해 둔 보고서가
아무 경고 없이 'unverified' 로 떨어진다(wave_w05: 11,596B → 11,794B).

**조용히 신뢰를 잃는 것**이 이 프로젝트가 반복해서 당하는 실패 유형이라, 그것을
테스트로 잡는다. `.gitattributes` 가 `eol=lf` 를 고정하고, 이 테스트가 그 고정이
실제로 먹었는지 확인한다.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
_MANIFEST = _REPO / "docs" / "research" / "quant_scoring_pipeline" / "qsp_report_manifest.json"


def _manifest() -> dict:
    if not _MANIFEST.exists():
        pytest.skip("QSP 보고서 매니페스트가 없는 체크아웃")
    return json.loads(_MANIFEST.read_text(encoding="utf-8"))


def test_every_registered_report_exists():
    for row in _manifest()["reports"]:
        target = _MANIFEST.parent / row["path"]
        assert target.exists(), f"등록됐는데 파일이 없다: {row['report_id']} → {row['path']}"


def test_every_registered_report_hash_matches_disk():
    """★ 대시보드가 'verified' 를 띄우는 조건 그대로 확인한다."""
    mismatched = []
    for row in _manifest()["reports"]:
        data = (_MANIFEST.parent / row["path"]).read_bytes()
        if (hashlib.sha256(data).hexdigest() != row["content_sha256"]
                or len(data) != row["bytes"]):
            mismatched.append(f"{row['report_id']} (disk {len(data)}B / 등록 {row['bytes']}B)")
    assert not mismatched, (
        "매니페스트와 디스크가 어긋났다 — 대시보드에서 'unverified' 로 표시된다.\n"
        "  줄바꿈 변환이 원인이면 .gitattributes 의 eol=lf 고정을 확인하라.\n  "
        + "\n  ".join(mismatched)
    )


def test_report_html_uses_lf_line_endings():
    """CRLF 가 섞이면 다음 체크아웃에서 해시가 깨진다 — 원인 쪽을 직접 막는다."""
    crlf = [row["path"] for row in _manifest()["reports"]
            if b"\r\n" in (_MANIFEST.parent / row["path"]).read_bytes()]
    assert not crlf, f"CRLF 가 섞인 보고서: {crlf}"


def test_count_matches_rows():
    payload = _manifest()
    assert payload["count"] == len(payload["reports"])


def test_report_ids_are_unique():
    ids = [row["report_id"] for row in _manifest()["reports"]]
    assert len(ids) == len(set(ids)), f"중복 report_id: {sorted({i for i in ids if ids.count(i) > 1})}"


def test_paths_stay_inside_reports_directory():
    """경로 규약 — 매니페스트 디렉토리 밖으로 나가는 path 는 대시보드가 거부한다."""
    for row in _manifest()["reports"]:
        assert ".." not in row["path"], f"상위 경로 참조: {row['path']}"
        assert not Path(row["path"]).is_absolute(), f"절대 경로: {row['path']}"
