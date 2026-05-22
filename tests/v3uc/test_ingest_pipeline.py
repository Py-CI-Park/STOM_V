"""V3.X 흡수 파이프라인 단위 테스트 (E1).

T-step 함수의 dry-run 모드를 mock으로 검증. 실 git merge·commit·push는 호출 안 함.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PIPELINE = _REPO_ROOT / "scripts" / "v3uc_ingest_pipeline.py"


pytestmark = pytest.mark.unit


def test_pipeline_script_exists() -> None:
    assert _PIPELINE.is_file(), f"{_PIPELINE} 누락"


def test_pipeline_dry_run_help_runnable() -> None:
    """--help 호출 가능 (parser sanity)."""
    result = subprocess.run(
        [sys.executable, str(_PIPELINE), "--help"],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=10,
    )
    assert result.returncode == 0
    assert "T-step" in result.stdout or "흡수" in result.stdout or "--version" in result.stdout


def test_pipeline_t03_audit_json_schema_v2(tmp_path) -> None:
    """T03 audit JSON이 schema v2 (primary/corroborating signal 분리) 따른다."""
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))
    import importlib.util

    spec = importlib.util.spec_from_file_location("v3uc_ingest_pipeline", str(_PIPELINE))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    t01_mock = {"status": "passed", "mode": "dry-run", "diff_stat": "(2 files)"}
    t02_mock = {"status": "passed", "manifest_path": "/tmp/m.json", "stdout_tail": ["line1", "line2"]}
    # cwd를 tmp_path로 변경해 audit이 tmp에 작성되도록
    import os

    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        # mod.ROOT 갱신
        mod.ROOT = tmp_path
        t03 = mod.step_t03_audit_json(
            version="99", upstream_ref="STOM_Version_3", log_dir=tmp_path / "logs",
            t01=t01_mock, t02=t02_mock, dry=True,
        )
    finally:
        os.chdir(original_cwd)

    assert t03["status"] == "passed"
    audit_path = Path(t03["audit_path"])
    assert audit_path.is_file()
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "v2"
    assert "primary_signals" in payload
    assert "corroborating_signals" in payload
    assert payload["decision"] == "PASS"


def test_pipeline_t01_aborts_on_wrong_branch(tmp_path) -> None:
    """T01: 현재 branch가 STOM_Version_3U 아니면 즉시 fail.

    본 테스트는 wt-3uc 워크트리(STOM_Version_3U_C branch)에서 실행되므로
    T01 호출 시 expected fail이 보장된다.
    """
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))
    import importlib.util

    spec = importlib.util.spec_from_file_location("v3uc_ingest_pipeline_t01", str(_PIPELINE))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # 본 테스트는 wt-3uc(STOM_Version_3U_C) 워크트리에서 실행되므로 T01이 fail해야 함
    mod.ROOT = _REPO_ROOT
    t01 = mod.step_t01_upstream_merge(version="99", upstream_ref="STOM_Version_3", dry=True)
    assert t01["status"] == "failed"
    assert "STOM_Version_3U" in t01["reason"]
