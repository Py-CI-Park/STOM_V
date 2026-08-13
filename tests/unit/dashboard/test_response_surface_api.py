# -*- coding: utf-8 -*-
"""페이지 32는 국소 파라미터 민감도와 산출 provenance만 말한다."""
from __future__ import annotations

import json
from pathlib import Path

from ai_strategy_loop.dashboard import response_surface_api as api


def _write_surface(tmp_path, payload, name="_exit_response_surface_fixture.json"):
    path = tmp_path / name
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return str(path)


def test_in_sample_surface_exposes_provenance_without_oos_or_adoption(monkeypatch, tmp_path):
    """OOS 판정이 없는 격자는 국소 민감도 자료일 뿐이다."""
    path = _write_surface(tmp_path, {
        "cells": [{"verdict": "고원", "arm": 2, "give": 1}],
        "recommendation": "가장 높은 고원 셀을 채택",
        "provenance": {
            "study": "design_v5",
            "artifact": "reproduction_gate.json",
            "split": "in_sample",
            "window": "2024-01-01..2024-12-31",
            "hash": "abc123",
            "created_at": "2026-08-13T00:00:00Z",
        },
    })
    monkeypatch.setattr(api, "_find", lambda out_name, tag: path)

    payload = api.response_surface()

    assert payload["available"] is True
    assert payload["source"] == "_exit_response_surface_fixture.json"
    assert payload["provenance_available"] is True
    assert payload["provenance"]["split"] == "in_sample"
    assert payload["provenance"]["hash"] == "abc123"
    assert "oos_verdict" not in payload
    assert "recommendation" not in payload
    assert all("표본 밖" not in rule and "채택" not in rule for rule in payload["reading_rules"])


def test_missing_or_corrupt_provenance_is_explicit(monkeypatch, tmp_path):
    missing = _write_surface(tmp_path, {"cells": []})
    monkeypatch.setattr(api, "_find", lambda out_name, tag: missing)
    payload = api.response_surface()
    assert payload["provenance_available"] is False
    assert payload["provenance_error"] == "산출 provenance가 없습니다."

    corrupt = _write_surface(tmp_path, {"cells": [], "provenance": []}, "_exit_response_surface_corrupt.json")
    monkeypatch.setattr(api, "_find", lambda out_name, tag: corrupt)
    payload = api.response_surface()
    assert payload["provenance_available"] is False
    assert payload["provenance_error"] == "산출 provenance 형식이 올바르지 않습니다."


def test_frontend_uses_base_url_and_gates_oos_language():
    source = (Path(__file__).parents[3] / "ai_strategy_loop/dashboard/frontend"
              / "loop-response-surface.jsx").read_text(encoding="utf-8")

    assert "국소 파라미터 민감도" in source
    assert "function loopRsGet(baseUrl, path)" in source
    assert 'fetch((baseUrl || "") + path' in source
    assert "LoopRsProvenance" in source
    assert "payload.oos_verdict && payload.recommendation" in source
    assert "권고" not in source
