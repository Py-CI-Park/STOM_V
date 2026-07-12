"""G005 — 연구 프로그램 성숙도 스코어카드 계약 테스트.

계약: build_scorecard(repo_root=None) -> dict
  {"schema", "generated_at", "overall_score", "stages" (9개), "markdown"}
  - 결정론: 같은 저장소 상태 -> 같은 점수(generated_at 제외).
  - 무예외: repo_root가 빈 디렉터리여도 예외를 던지지 않고 전 단계 0점 + note.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.research_maturity_scorecard import build_scorecard, main  # noqa: E402

_EXPECTED_STAGE_IDS = (
    "engine_contract",
    "generation",
    "gates",
    "scoring",
    "autopsy_feedback",
    "evidence_ledger",
    "profiles_toggles",
    "dashboard",
    "profit_proof",
)


def _without_timestamp(scorecard: dict) -> dict:
    return {k: v for k, v in scorecard.items() if k != "generated_at"}


def test_determinism_same_repo_state_same_score():
    first = build_scorecard(PROJECT_ROOT)
    second = build_scorecard(PROJECT_ROOT)
    assert _without_timestamp(first) == _without_timestamp(second)


def test_no_exceptions_on_empty_repo_root(tmp_path):
    scorecard = build_scorecard(str(tmp_path))
    assert scorecard["schema"] == "research_maturity_v1"
    assert scorecard["overall_score"] == 0
    assert len(scorecard["stages"]) == 9
    for stage in scorecard["stages"]:
        assert stage["score"] == 0
        for signal in stage["signals"]:
            assert signal["points"] == 0
            assert signal["note"]


def test_current_repo_overall_score_positive_and_nine_stages():
    scorecard = build_scorecard(PROJECT_ROOT)
    assert scorecard["overall_score"] > 0
    assert len(scorecard["stages"]) == 9
    stage_ids = tuple(s["id"] for s in scorecard["stages"])
    assert stage_ids == _EXPECTED_STAGE_IDS
    for stage in scorecard["stages"]:
        assert 0 <= stage["score"] <= 100
        assert stage["max_score"] == 100
        assert stage["signals"]
        for signal in stage["signals"]:
            assert 0 <= signal["points"] <= signal["max_points"]


def test_profit_proof_stage_is_fixed_zero():
    scorecard = build_scorecard(PROJECT_ROOT)
    profit_stage = next(s for s in scorecard["stages"] if s["id"] == "profit_proof")
    assert profit_stage["score"] == 0
    assert profit_stage["signals"][0]["points"] == 0
    assert "CL-R08" in profit_stage["signals"][0]["note"]


def test_markdown_contains_stage_table():
    scorecard = build_scorecard(PROJECT_ROOT)
    md = scorecard["markdown"]
    assert "연구 프로그램 성숙도 스코어카드" in md
    assert "| 단계 | 점수 | 신호 |" in md
    for stage in scorecard["stages"]:
        assert stage["label"] in md


def test_default_repo_root_matches_explicit(tmp_path):
    default = build_scorecard(None)
    explicit = build_scorecard(PROJECT_ROOT)
    assert _without_timestamp(default) == _without_timestamp(explicit)


def test_cli_writes_json_and_prints_markdown(tmp_path):
    out_path = tmp_path / "research_maturity.json"
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        [sys.executable, os.path.join(PROJECT_ROOT, "scripts", "research_maturity_scorecard.py"),
         "--out", str(out_path)],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "연구 프로그램 성숙도 스코어카드" in result.stdout
    assert out_path.is_file()
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["schema"] == "research_maturity_v1"
    assert len(payload["stages"]) == 9


def test_main_returns_zero(tmp_path):
    out_path = tmp_path / "research_maturity.json"
    rc = main(["--out", str(out_path), "--repo-root", PROJECT_ROOT])
    assert rc == 0
    assert out_path.is_file()


@pytest.mark.parametrize("stage_id", _EXPECTED_STAGE_IDS)
def test_each_stage_has_at_least_one_signal(stage_id):
    scorecard = build_scorecard(PROJECT_ROOT)
    stage = next(s for s in scorecard["stages"] if s["id"] == stage_id)
    assert len(stage["signals"]) >= 1
    for signal in stage["signals"]:
        assert {"name", "value", "points", "max_points", "note"} <= set(signal)
