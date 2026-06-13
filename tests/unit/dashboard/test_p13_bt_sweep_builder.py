"""Phase13 백테탭 C-2 — 파라미터 스윕 빌더 UI + 백엔드 스펙 직렬화/경로 게이트.

검증 대상:
  - 프론트(backtest.jsx): _SweepParamBuilder 행([변수명][min][max][step]) 추가/삭제 +
    sweep_spec 페이로드 스레딩 + 빌더/파일 입력 토글(파일 경로 폴백 유지).
  - 백엔드(backtest_api.py) 순수 함수:
      _expand_sweep_range — [min,max,step] → 명시 값 리스트(포함 구간, 무예외).
      _build_sweep_spec   — 빌더 행 → {변수명:[값,...]} (CLI generate_combinations 입력 형식).
      _write_sweep_spec_file — 스펙을 게이트된 _database/ 임시 JSON 으로 직렬화(allowlist 통과).
  - /bt/run 인라인 sweep_spec → 게이트 임시 파일 → sweep_params 스레딩(무예외).
  - CLI 계약 round-trip: _build_sweep_spec 출력이 cli.sweep.generate_combinations 와 호환.

스윕 JSON 스키마는 {변수명: [명시 값 리스트]} 이다(NOT {min,max,step}) — 2026-06-13
cli/sweep.generate_combinations(product(*values)) · cli/subcommands._handle_sweep(json.load)
실측. 빌더의 min/max/step 행은 백엔드 _expand_sweep_range 가 명시 값 리스트로 펼친다.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.dashboard import backtest_api as api  # noqa: E402


def _read_front(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def _make_strategy_db(path: Path) -> None:
    con = sqlite3.connect(str(path))
    cur = con.cursor()
    cur.execute('CREATE TABLE stockbuy ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    cur.execute('INSERT INTO stockbuy VALUES (?, ?)', ("기존매수", "매수 = True"))
    cur.execute('CREATE TABLE stocksell ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    cur.execute('INSERT INTO stocksell VALUES (?, ?)', ("기존매도", "self.sell_cond = 1"))
    con.commit()
    con.close()


@pytest.fixture
def client(monkeypatch, tmp_path: Path):
    from fastapi.testclient import TestClient

    db_path = tmp_path / "strategy.db"
    _make_strategy_db(db_path)
    monkeypatch.setenv("STOM_WEBBT_STRATEGY_DB", str(db_path))
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    from ai_strategy_loop.dashboard.app import create_app
    return TestClient(create_app())


# ============================================================ 프론트 정적 가드
class TestSweepBuilderFrontend:
    """_SweepParamBuilder 컴포넌트 + BtRunPanel 스레딩."""

    def test_builder_component_defined(self):
        src = _read_front("backtest.jsx")
        assert "function _SweepParamBuilder(" in src

    def test_builder_rows_have_name_min_max_step(self):
        src = _read_front("backtest.jsx")
        start = src.find("function _SweepParamBuilder(")
        body = src[start:start + 4000]
        # 각 행이 변수명·min·max·step 필드를 다룬다(상태 패치 키).
        for key in ("name", "min", "max", "step"):
            assert key in body, f"빌더 행에 {key} 필드가 없습니다"
        # 한글 라벨(변수명/최소/최대/간격 류) 확인.
        assert "변수명" in body

    def test_builder_add_remove_rows(self):
        src = _read_front("backtest.jsx")
        start = src.find("function _SweepParamBuilder(")
        body = src[start:start + 4000]
        # 행 추가/삭제 핸들러.
        assert "addRow" in body and "removeRow" in body
        assert "concat(" in body  # 추가는 불변 concat.
        assert "filter(" in body  # 삭제는 불변 filter.

    def test_builder_does_not_mutate_rows(self):
        """행 수정은 불변(map 으로 새 배열) — 변이 패턴(rows[i]=)이 없어야 한다."""
        src = _read_front("backtest.jsx")
        start = src.find("function _SweepParamBuilder(")
        body = src[start:start + 4000]
        assert ".map(" in body
        assert not re.search(r"rows\[\s*\w+\s*\]\s*=", body), "rows 배열을 직접 변이하면 안 됩니다"

    def test_run_panel_sends_sweep_spec(self):
        src = _read_front("backtest.jsx")
        # submit 이 빌더 모드에서 sweep_spec(행 배열)을 페이로드로 보낸다.
        assert "sweep_spec" in src
        assert "sweepRows" in src
        assert "setSweepRows" in src

    def test_run_panel_keeps_file_path_fallback(self):
        src = _read_front("backtest.jsx")
        # 파일 경로 입력이 폴백으로 남아있다(sweepInputMode == file → sweep_params).
        assert "sweepInputMode" in src
        assert "sweep_params" in src
        assert "sweep_params.json" in src  # 폴백 placeholder.

    def test_builder_uses_builder_component_tag(self):
        src = _read_front("backtest.jsx")
        # BtRunPanel 이 빌더 컴포넌트를 마운트한다.
        assert "<_SweepParamBuilder" in src


# ============================================================ 백엔드 순수 함수
class TestExpandSweepRange:
    """_expand_sweep_range — [min,max,step] → 명시 값 리스트."""

    def test_int_range_inclusive(self):
        assert api._expand_sweep_range(60, 180, 60) == [60, 120, 180]

    def test_int_values_are_int(self):
        for v in api._expand_sweep_range(1, 3, 1):
            assert isinstance(v, int)

    def test_float_range_inclusive(self):
        assert api._expand_sweep_range(0.5, 2.0, 0.5) == [0.5, 1.0, 1.5, 2.0]

    def test_step_zero_returns_single(self):
        assert api._expand_sweep_range(60, 180, 0) == [60]

    def test_lo_gt_hi_returns_single(self):
        assert api._expand_sweep_range(180, 60, 10) == [180]

    def test_value_count_capped(self):
        out = api._expand_sweep_range(0, 100000, 1)
        assert len(out) <= api._SWEEP_MAX_VALUES_PER_VAR


class TestBuildSweepSpec:
    """_build_sweep_spec — 빌더 행 → {변수명:[값,...]} 스펙."""

    def test_min_max_step_rows(self):
        spec = api._build_sweep_spec([
            {"name": "avg_time", "min": 60, "max": 180, "step": 60},
            {"name": "betting", "min": 1, "max": 3, "step": 1},
        ])
        assert spec == {"avg_time": [60, 120, 180], "betting": [1, 2, 3]}

    def test_explicit_values_list(self):
        spec = api._build_sweep_spec([{"name": "avg_time", "values": [60, 120, "180", "x"]}])
        # 숫자만 수용, 'x' 는 버린다.
        assert spec == {"avg_time": [60, 120, 180]}

    def test_skips_empty_name_rows(self):
        spec = api._build_sweep_spec([
            {"name": "", "min": 1, "max": 3, "step": 1},
            {"name": "avg_time", "min": 60, "max": 60, "step": 1},
        ])
        assert spec == {"avg_time": [60]}

    def test_empty_rows_returns_none(self):
        assert api._build_sweep_spec([]) is None
        assert api._build_sweep_spec("nope") is None
        assert api._build_sweep_spec([{"min": 1, "max": 3, "step": 1}]) is None

    def test_invalid_numbers_skipped(self):
        spec = api._build_sweep_spec([{"name": "x", "min": "a", "max": "b", "step": "c"}])
        assert spec is None

    def test_bool_values_excluded(self):
        # bool 은 파라미터 값으로 부적절(숫자 취급 차단).
        spec = api._build_sweep_spec([{"name": "x", "values": [True, False, 5]}])
        assert spec == {"x": [5]}

    def test_var_count_capped(self):
        rows = [{"name": f"v{i}", "min": 1, "max": 2, "step": 1} for i in range(20)]
        spec = api._build_sweep_spec(rows)
        assert len(spec) <= api._SWEEP_MAX_VARS

    def test_does_not_mutate_input(self):
        rows = [{"name": "avg_time", "values": [60, 120]}]
        original = [{"name": "avg_time", "values": [60, 120]}]
        api._build_sweep_spec(rows)
        assert rows == original


class TestWriteSweepSpecFile:
    """_write_sweep_spec_file — 스펙 → 게이트된 _database/ 임시 JSON."""

    def test_writes_gated_path(self):
        spec = {"avg_time": [60, 120, 180]}
        path = api._write_sweep_spec_file(spec)
        try:
            assert path is not None
            # allowlist(_database/) 안에 쓰였고 sweep_params 게이트를 통과한다.
            assert api._gated_json_path(path) == path
            loaded = json.loads(Path(path).read_text(encoding="utf-8"))
            assert loaded == spec
        finally:
            if path and os.path.isfile(path):
                os.remove(path)

    def test_empty_spec_returns_none(self):
        assert api._write_sweep_spec_file({}) is None
        assert api._write_sweep_spec_file("nope") is None


class TestSweepSpecCliRoundTrip:
    """_build_sweep_spec 출력이 CLI generate_combinations 입력과 호환되는지 round-trip."""

    def test_round_trip_through_generate_combinations(self):
        from cli.sweep import generate_combinations

        spec = api._build_sweep_spec([
            {"name": "avg_time", "min": 60, "max": 180, "step": 60},
            {"name": "betting", "min": 1, "max": 3, "step": 1},
        ])
        combos = generate_combinations(spec)
        assert len(combos) == 9  # 3 x 3 데카르트 곱.
        assert {"avg_time": 60, "betting": 1} in combos
        assert {"avg_time": 180, "betting": 3} in combos

    def test_written_file_loads_as_cli_expects(self):
        from cli.sweep import generate_combinations

        spec = api._build_sweep_spec([{"name": "avg_time", "min": 60, "max": 180, "step": 60}])
        path = api._write_sweep_spec_file(spec)
        try:
            # CLI _handle_sweep 와 동일하게 json.load 로 읽어 generate_combinations 에 넣는다.
            with open(path, encoding="utf-8") as fh:
                loaded = json.load(fh)
            combos = generate_combinations(loaded)
            assert len(combos) == 3
        finally:
            if path and os.path.isfile(path):
                os.remove(path)


# ============================================================ /bt/run 라우팅
class TestRunRouteInlineSweepSpec:
    """POST /bt/run 인라인 sweep_spec → 게이트 임시 파일 → 잡 큐잉(무예외)."""

    def test_inline_sweep_spec_submits_job(self, client):
        r = client.post("/bt/run", json={
            "buy": "기존매수", "sell": "기존매도", "start": 20250407, "end": 20250409,
            "mode": "sweep", "sweep_action": "param",
            "sweep_spec": [
                {"name": "avg_time", "min": 60, "max": 180, "step": 60},
            ],
        })
        body = r.json()
        # 잡이 큐잉되고 job_id 가 발급된다(스펙→임시파일→sweep_params 스레딩 성공).
        assert body["status"] == "ok", body
        assert "job_id" in body
        client.post("/bt/job/cancel", json={"job_id": body["job_id"]})

    def test_empty_sweep_spec_rejected(self, client):
        r = client.post("/bt/run", json={
            "buy": "기존매수", "sell": "기존매도", "start": 20250407, "end": 20250409,
            "mode": "sweep", "sweep_action": "param",
            "sweep_spec": [{"name": "", "min": 1, "max": 3, "step": 1}],  # 변수명 빈 행만.
        })
        body = r.json()
        assert body["status"] == "error"
        assert "스윕 스펙" in body["message"] or "변수" in body["message"]

    def test_file_path_takes_precedence_over_spec_when_both(self, client):
        # 파일 경로가 직접 오면 그 경로가 우선(폴백 유지) — allowlist 밖 경로는 거부된다.
        r = client.post("/bt/run", json={
            "buy": "기존매수", "sell": "기존매도", "start": 20250407, "end": 20250409,
            "mode": "sweep", "sweep_action": "param",
            "sweep_params": "C:/Windows/evil.json",
            "sweep_spec": [{"name": "avg_time", "min": 60, "max": 180, "step": 60}],
        })
        body = r.json()
        # sweep_params 가 allowlist 게이트에서 먼저 거부된다(인라인 스펙으로 우회 불가).
        assert body["status"] == "error"
        assert "허용" in body["message"]
