"""B5 — 복수 결과(compare/overlay/portfolio) 입력이 B4 admission을 통과해야 한다.

기존 경로는 list CSV loader가 행을 조용히 건너뛰어, 부분 파싱·실행 실패·자료 없는
무거래를 정상 자료처럼 비교·합산할 수 있었다. 이 시험은 생산 함수/라우트를 그대로
호출해 차단 계약을 재현한다(red → 최소 수정 → green).

검증 축:
  - compare: 불량 측 metrics/summary/equity=null, 양측 충족 전 delta 없음.
  - overlay: 요청 집합과 표시 집합 구분, 부분 성공을 전체 성공으로 표시하지 않음.
  - portfolio: 실패 입력 하나라도 합산 계산하지 않음, 무거래는 검증된 빈 입력만.
  - 공통: admission 이후 재읽기 금지(load_trades_csv 호출 감시).
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.dashboard import backtest_analysis as analysis  # noqa: E402
from ai_strategy_loop.dashboard import backtest_api as api  # noqa: E402
from tests.unit.dashboard.trade_quality_fixtures import official_pair  # noqa: E402


# --------------------------------------------------------------------- fixtures
_OFFICIAL_COLUMNS = official_pair()[0].strip().split(",")
_OFFICIAL_BASE = dict(zip(
    _OFFICIAL_COLUMNS, next(csv.reader([official_pair()[1].strip()]))
))


def _official_csv(path: Path, rows: List[Dict[str, Any]]) -> str:
    """공식 54열 스키마로 행을 쓴다(미지정 컬럼은 공식 기본 행 값)."""
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_OFFICIAL_COLUMNS, restval="")
        writer.writeheader()
        for overrides in rows:
            values = dict(_OFFICIAL_BASE)
            values.update(overrides)
            writer.writerow(values)
    return str(path)


def _trade_row(name: str, buy: str, sell: str, hold: str,
               pct: str, krw: str) -> Dict[str, Any]:
    return {
        "종목명": name, "매수시간": buy, "매도시간": sell,
        "보유시간": hold, "수익률": pct, "수익금": krw,
    }


def _header_only_csv(path: Path) -> str:
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        csv.DictWriter(fh, fieldnames=_OFFICIAL_COLUMNS).writeheader()
    return str(path)


def _partial_csv(path: Path) -> str:
    """공식 정상 1행 + 깨진 1행 — ROW_PARSE_PARTIAL."""
    header, row = official_pair()
    path.write_text(header + row + "bad\n", encoding="utf-8")
    return str(path)


def _nonofficial_csv(path: Path) -> str:
    """필수 6컬럼만 있는 비공식 스키마 — INVALID_SCHEMA."""
    cols = ["종목명", "매수시간", "매도시간", "보유시간", "수익률", "수익금"]
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=cols)
        writer.writeheader()
        writer.writerow({
            "종목명": "X", "매수시간": "20250407093000",
            "매도시간": "20250407100000", "보유시간": "30",
            "수익률": "1.0", "수익금": "1000",
        })
    return str(path)


class _JobManager:
    """records: {job_id: record-dict}. 없는 잡은 available=False."""

    def __init__(self, records: Dict[str, Dict[str, Any]]) -> None:
        self._records = records

    def get(self, job_id: str, log_tail: int = 0) -> Dict[str, Any]:
        rec = self._records.get(job_id)
        if rec is None:
            return {"available": False, "job_id": job_id}
        out = dict(rec)
        out.setdefault("job_id", job_id)
        return out

    def list_jobs(self) -> Dict[str, Any]:
        return {"jobs": [], "count": 0}


def _patch_jobs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
                records: Dict[str, Dict[str, Any]]) -> None:
    monkeypatch.setattr(api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(api, "get_job_manager", lambda: _JobManager(records))


def _patch_gens(monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
                rows: Dict[tuple, Optional[Dict[str, Any]]]) -> None:
    """(run_id, gen_no) → 세대 행 매핑을 읽기전용 조회로 심는다."""
    monkeypatch.setattr(api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        api, "_gen_row_readonly", lambda run_id, gen_no: rows.get((run_id, gen_no))
    )


def _job_record(csv_path: Optional[str], *, status: str = "success",
                trade_count: Optional[int] = 1, buy: str = "테스트매수",
                metrics: Any = "__auto__") -> Dict[str, Any]:
    if metrics == "__auto__":
        metrics = (
            {"trade_count": trade_count, "total_profit_pct": 1.0}
            if trade_count is not None else None
        )
    return {
        "available": True, "status": status, "csv_path": csv_path,
        "metrics": metrics,
        "spec": {"buy": buy, "sell": "테스트매도", "timeframe": "tick"},
    }


def _gen_row(csv_path: Optional[str], *, status: str = "ok",
             trade_count: Optional[int] = 1) -> Dict[str, Any]:
    return {
        "status": status, "csv_path": csv_path,
        "trade_count": trade_count,
        "buy_name": "g매수", "sell_name": "g매도",
    }


# ==================================================================== B5-1 compare
class TestCompareAdmission:
    """/bt/compare — 각 측이 admission을 통과해야 지표·곡선·delta가 생긴다."""

    def test_two_valid_jobs_admit_both_and_compute_delta(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
            _trade_row("베타", "20250408093000", "20250408100000", "30", "-1.0", "-10000"),
        ])
        csv_b = _official_csv(tmp_path / "b.csv", [
            _trade_row("감마", "20250407093000", "20250407100000", "30", "3.0", "30000"),
        ])
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=2),
            "B": _job_record(csv_b, trade_count=1),
        })
        body = api.compare_jobs(job_a="A", job_b="B")
        assert body["a"]["admitted"] is True
        assert body["b"]["admitted"] is True
        assert body["a"]["summary"]["trade_count"] == 2
        # 저장 metrics는 재계산 summary와 섞이지 않고 별도 표시된다.
        assert body["a"]["metrics_authority"] == "stored_unverified"
        assert body["a"]["data_quality"]["status"] == "VALID"
        assert body["delta"]["trade_count"] == -1.0

    def test_partial_parse_side_blocked_no_delta(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        csv_b = _partial_csv(tmp_path / "b.csv")
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "B": _job_record(csv_b, trade_count=2),
        })
        body = api.compare_jobs(job_a="A", job_b="B")
        bad = body["b"]
        assert bad is not None
        assert bad["admitted"] is False
        assert bad["metrics"] is None
        assert bad["summary"] is None
        assert bad["equity"] is None
        assert bad["data_quality"]["status"] == "ROW_PARSE_PARTIAL"
        assert bad["reason"]
        # 양측 충족 전 delta는 생성되지 않는다.
        assert body["delta"] == {}

    def test_error_status_job_blocked(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        csv_b = _official_csv(tmp_path / "b.csv", [
            _trade_row("감마", "20250407093000", "20250407100000", "30", "3.0", "30000"),
        ])
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "B": _job_record(csv_b, status="error", trade_count=1),
        })
        body = api.compare_jobs(job_a="A", job_b="B")
        assert body["a"]["admitted"] is True
        assert body["b"]["admitted"] is False
        assert body["b"]["blocked_reason"] == "execution_blocked"
        assert body["delta"] == {}

    def test_missing_csv_blocked(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "B": _job_record(str(tmp_path / "missing.csv"), trade_count=1),
        })
        body = api.compare_jobs(job_a="A", job_b="B")
        assert body["b"]["admitted"] is False
        assert body["b"]["data_quality"]["status"] == "MISSING_ARTIFACT"

    def test_unknown_job_side_stays_null(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        _patch_jobs(monkeypatch, tmp_path, {"A": _job_record(csv_a, trade_count=1)})
        body = api.compare_jobs(job_a="A", job_b="ghost")
        assert body["a"]["admitted"] is True
        assert body["b"] is None
        assert body["delta"] == {}

    def test_nonofficial_schema_blocked(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        csv_b = _nonofficial_csv(tmp_path / "b.csv")
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "B": _job_record(csv_b, trade_count=1),
        })
        body = api.compare_jobs(job_a="A", job_b="B")
        assert body["b"]["admitted"] is False
        assert body["b"]["data_quality"]["status"] == "INVALID_SCHEMA"

    def test_row_count_mismatch_blocked(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        csv_b = _official_csv(tmp_path / "b.csv", [
            _trade_row("감마", "20250407093000", "20250407100000", "30", "3.0", "30000"),
        ])
        # 기록상 5행인데 실제 1행 — ROW_COUNT_MISMATCH.
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "B": _job_record(csv_b, trade_count=5),
        })
        body = api.compare_jobs(job_a="A", job_b="B")
        assert body["b"]["admitted"] is False
        assert body["b"]["data_quality"]["status"] == "ROW_COUNT_MISMATCH"

    def test_no_trades_job_admitted_as_verified_empty(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        # 엔진 검증 무거래 잡: metrics 없음 + CSV 산출물 없음(종료 분류 증거).
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "N": _job_record(None, status="no_trades", metrics=None),
        })
        body = api.compare_jobs(job_a="A", job_b="N")
        side = body["b"]
        assert side["admitted"] is True
        assert side["empty"] is True
        assert side["trade_count"] == 0
        assert side["summary"]["trade_count"] == 0
        assert side["equity"]["cumulative"] == []

    def test_no_trades_with_header_csv_verified(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        empty_csv = _header_only_csv(tmp_path / "n.csv")
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "N": _job_record(empty_csv, status="no_trades", trade_count=0),
        })
        body = api.compare_jobs(job_a="A", job_b="N")
        assert body["b"]["admitted"] is True
        assert body["b"]["empty"] is True
        assert body["b"]["data_quality"]["status"] == "NO_TRADES"

    def test_no_trades_contradicting_metrics_blocked(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        # no_trades 라 하면서 trade_count=5 를 주장 — 문자열만으로 빈 승인 금지.
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "N": _job_record(None, status="no_trades", trade_count=5),
        })
        body = api.compare_jobs(job_a="A", job_b="N")
        assert body["b"]["admitted"] is False

    def test_generation_side_valid_and_blocked(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_g = _official_csv(tmp_path / "g.csv", [
            _trade_row("세대", "20250407093000", "20250407100000", "30", "1.0", "5000"),
        ])
        csv_bad = _partial_csv(tmp_path / "bad.csv")
        _patch_gens(monkeypatch, tmp_path, {
            ("run1", 0): _gen_row(csv_g, status="ok", trade_count=1),
            ("run1", 9): _gen_row(csv_bad, status="ok", trade_count=2),
            ("run2", 0): _gen_row(csv_g, status="failed", trade_count=1),
        })
        ok = api.compare_jobs(run_a="run1", gen_a=0, run_b="run1", gen_b=0)
        assert ok["a"]["admitted"] is True
        assert ok["a"]["source_type"] == "generation"
        # 자기 자신과의 비교 — delta는 전부 0.
        assert ok["delta"]
        assert all(abs(v) < 1e-9 for v in ok["delta"].values())

        partial = api.compare_jobs(run_a="run1", gen_a=0, run_b="run1", gen_b=9)
        assert partial["b"]["admitted"] is False
        assert partial["delta"] == {}

        failed = api.compare_jobs(run_a="run1", gen_a=0, run_b="run2", gen_b=0)
        assert failed["b"]["admitted"] is False
        assert failed["b"]["blocked_reason"] == "execution_blocked"

    def test_cross_job_generation(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        csv_g = _official_csv(tmp_path / "g.csv", [
            _trade_row("세대", "20250407093000", "20250407100000", "30", "1.0", "5000"),
        ])
        _patch_jobs(monkeypatch, tmp_path, {"A": _job_record(csv_a, trade_count=1)})
        _patch_gens(monkeypatch, tmp_path, {("run1", 0): _gen_row(csv_g, trade_count=1)})
        body = api.compare_jobs(job_a="A", run_b="run1", gen_b=0)
        assert body["a"]["admitted"] is True
        assert body["b"]["admitted"] is True
        assert body["b"]["source_type"] == "generation"

    def test_blocked_inputs_never_reach_calculators(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_bad = _partial_csv(tmp_path / "b.csv")
        _patch_jobs(monkeypatch, tmp_path, {
            "X": _job_record(csv_bad, trade_count=2),
            "Y": _job_record(str(tmp_path / "none.csv"), trade_count=1),
        })
        calls: List[str] = []
        real_summary = analysis.summary_metrics
        real_equity = analysis.equity_series

        def spy_summary(trades):
            calls.append("summary")
            return real_summary(trades)

        def spy_equity(trades):
            calls.append("equity")
            return real_equity(trades)

        monkeypatch.setattr(analysis, "summary_metrics", spy_summary)
        monkeypatch.setattr(analysis, "equity_series", spy_equity)
        body = api.compare_jobs(job_a="X", job_b="Y")
        assert body["a"]["admitted"] is False
        assert body["b"]["admitted"] is False
        assert calls == []

    def test_checked_snapshot_never_rereads_csv(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        _patch_jobs(monkeypatch, tmp_path, {"A": _job_record(csv_a, trade_count=1)})
        rereads: List[str] = []

        def forbidden(*args, **kwargs):
            rereads.append("read")
            return []

        monkeypatch.setattr(analysis, "load_trades_csv", forbidden)
        body = api.compare_jobs(job_a="A", job_b="A")
        assert rereads == []
        assert body["a"]["admitted"] is True
        assert body["a"]["summary"]["trade_count"] == 1
        # self-compare — delta 전부 0.
        assert all(abs(v) < 1e-9 for v in body["delta"].values())


# ==================================================================== B5-2 overlay
class TestOverlayAdmission:
    """/bt/overlay — 요청 집합과 실제 표시 집합을 구분하고, 실패 입력을 밝힌다."""

    def test_two_valid_sources(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        csv_b = _official_csv(tmp_path / "b.csv", [
            _trade_row("베타", "20250408093000", "20250408100000", "30", "-1.0", "-10000"),
        ])
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "B": _job_record(csv_b, trade_count=1),
        })
        body = api.overlay_jobs(job_ids="A,B")
        assert body["status"] == "ok"
        assert body["count"] == 2
        assert body["requested"] == ["A", "B"]
        assert body["resolved"] == ["A", "B"]
        assert body["failed"] == []
        for s in body["series"]:
            assert s["data_quality"]["status"] == "VALID"
            assert s["source_sha256"]

    def test_three_and_four_sources_within_bounds(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        records = {}
        for tag in ("A", "B", "C", "D"):
            records[tag] = _job_record(
                _official_csv(tmp_path / f"{tag}.csv", [
                    _trade_row(tag, "20250407093000", "20250407100000", "30", "1.0", "1000"),
                ]),
                trade_count=1,
            )
        _patch_jobs(monkeypatch, tmp_path, records)
        three = api.overlay_jobs(job_ids="A,B,C")
        assert three["status"] == "ok" and three["count"] == 3
        four = api.overlay_jobs(job_ids="A,B,C,D")
        assert four["status"] == "ok" and four["count"] == 4
        five = api.overlay_jobs(job_ids="A,B,C,D,E")
        assert five["status"] == "error"  # 2~4 경계 보존

    def test_duplicate_ids_deduped_in_requested(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        csv_b = _official_csv(tmp_path / "b.csv", [
            _trade_row("베타", "20250408093000", "20250408100000", "30", "-1.0", "-10000"),
        ])
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "B": _job_record(csv_b, trade_count=1),
        })
        body = api.overlay_jobs(job_ids="A,A,B")
        assert body["status"] == "ok"
        assert body["requested"] == ["A", "B"]
        assert body["count"] == 2

    def test_failed_source_identified_not_silently_dropped(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        csv_b = _partial_csv(tmp_path / "b.csv")
        csv_c = _official_csv(tmp_path / "c.csv", [
            _trade_row("감마", "20250409093000", "20250409100000", "30", "1.0", "5000"),
        ])
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "B": _job_record(csv_b, trade_count=2),
            "C": _job_record(csv_c, trade_count=1),
        })
        body = api.overlay_jobs(job_ids="A,B,C")
        # 부분 결과를 전체 성공으로 표시하지 않는다 — 요청 3, 표시 2, 실패 식별.
        assert body["requested"] == ["A", "B", "C"]
        assert body["resolved"] == ["A", "C"]
        assert body["failed"] == ["B"]
        failure = body["failures"][0]
        assert failure["job_id"] == "B"
        assert failure["quality_status"] == "ROW_PARSE_PARTIAL"
        assert failure["reason"]
        assert body["status"] in ("ok", "partial")

    def test_all_failed_lists_every_reason(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _patch_jobs(monkeypatch, tmp_path, {
            "X": _job_record(_partial_csv(tmp_path / "x.csv"), trade_count=2),
            "Y": _job_record(str(tmp_path / "none.csv"), trade_count=1),
        })
        body = api.overlay_jobs(job_ids="X,Y")
        assert body["status"] == "error"
        assert body["series"] == []
        assert body["resolved"] == []
        assert set(body["failed"]) == {"X", "Y"}
        assert len(body["failures"]) == 2

    def test_missing_csv_identified(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "M": _job_record(str(tmp_path / "missing.csv"), trade_count=1),
        })
        body = api.overlay_jobs(job_ids="A,M")
        assert body["failed"] == ["M"]
        assert body["failures"][0]["quality_status"] == "MISSING_ARTIFACT"

    def test_empty_verified_member_shown_as_flat_series(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "N": _job_record(None, status="no_trades", metrics=None),
        })
        body = api.overlay_jobs(job_ids="A,N")
        assert body["status"] == "ok"
        assert body["resolved"] == ["A", "N"]
        flat = body["series"][1]
        assert flat["empty"] is True
        assert flat["trade_count"] == 0
        assert flat["cumulative"] == []

    def test_overlay_uses_checked_snapshot_no_reread(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        csv_b = _official_csv(tmp_path / "b.csv", [
            _trade_row("베타", "20250408093000", "20250408100000", "30", "-1.0", "-10000"),
        ])
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "B": _job_record(csv_b, trade_count=1),
        })
        rereads: List[str] = []
        monkeypatch.setattr(analysis, "load_trades_csv",
                            lambda *a, **k: rereads.append("read") or [])
        body = api.overlay_jobs(job_ids="A,B")
        assert rereads == []
        assert body["status"] == "ok"


# ================================================================== B5-3 portfolio
class TestPortfolioAdmission:
    """POST /bt/portfolio — 실패 입력 하나라도 있으면 합산 계산을 하지 않는다."""

    @staticmethod
    def _payload(*items: Dict[str, Any]) -> api.PortfolioPayload:
        return api.PortfolioPayload(
            items=[api.PortfolioItemPayload(**item) for item in items]
        )
    def test_valid_inputs_combine(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        csv_b = _official_csv(tmp_path / "b.csv", [
            _trade_row("베타", "20250408093000", "20250408100000", "30", "-1.0", "-10000"),
        ])
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "B": _job_record(csv_b, trade_count=1),
        })
        body = api.portfolio_combine(self._payload(
            {"job_id": "A", "label": "전략A"}, {"job_id": "B", "label": "전략B"},
        ))
        assert body["status"] == "ok"
        assert body["portfolio"]["count"] == 2
        assert {s["label"] for s in body["portfolio"]["strategies"]} == {"전략A", "전략B"}
        assert {s["job_id"] for s in body["sources"]} == {"A", "B"}
        assert all(s["source_sha256"] for s in body["sources"])

    def test_one_invalid_input_blocks_portfolio(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        csv_b = _partial_csv(tmp_path / "b.csv")
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "B": _job_record(csv_b, trade_count=2),
        })
        calls: List[str] = []
        real = analysis.portfolio_analysis

        def spy(items):
            calls.append("called")
            return real(items)

        monkeypatch.setattr(analysis, "portfolio_analysis", spy)
        body = api.portfolio_combine(self._payload(
            {"job_id": "A"}, {"job_id": "B"},
        ))
        assert calls == []
        assert body["status"] == "error"
        assert body["failed"] == [1]
        assert body["failed_reasons"][0]["reason"] == "job_source_blocked"

    def test_missing_csv_identified(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "M": _job_record(str(tmp_path / "missing.csv"), trade_count=1),
        })
        body = api.portfolio_combine(self._payload(
            {"job_id": "A"}, {"job_id": "M"},
        ))
        assert body["status"] == "error"
        assert body["failed_reasons"] == [{"index": 1, "reason": "job_csv_missing"}]

    def test_job_generation_mix(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        csv_g = _official_csv(tmp_path / "g.csv", [
            _trade_row("세대", "20250408093000", "20250408100000", "30", "1.0", "5000"),
        ])
        _patch_jobs(monkeypatch, tmp_path, {"A": _job_record(csv_a, trade_count=1)})
        _patch_gens(monkeypatch, tmp_path, {
            ("runP", 0): _gen_row(csv_g, status="ok", trade_count=1),
        })
        body = api.portfolio_combine(self._payload(
            {"job_id": "A"}, {"run_id": "runP", "gen_no": 0},
        ))
        assert body["status"] == "ok"
        kinds = {s["source_type"] for s in body["sources"]}
        assert kinds == {"job", "generation"}

    def test_no_trades_verified_empty_member(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "N": _job_record(None, status="no_trades", metrics=None),
        })
        body = api.portfolio_combine(self._payload(
            {"job_id": "A"}, {"job_id": "N"},
        ))
        assert body["status"] == "ok"
        empty = next(s for s in body["sources"] if s["job_id"] == "N")
        assert empty["empty"] is True

    def test_no_trades_contradiction_blocked(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "N": _job_record(None, status="no_trades", trade_count=5),
        })
        body = api.portfolio_combine(self._payload(
            {"job_id": "A"}, {"job_id": "N"},
        ))
        assert body["status"] == "error"
        assert body["failed_reasons"][0]["reason"] == "job_no_trades_contradiction"

    def test_malformed_csv_blocked(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "B": _job_record(_nonofficial_csv(tmp_path / "b.csv"), trade_count=1),
        })
        body = api.portfolio_combine(self._payload(
            {"job_id": "A"}, {"job_id": "B"},
        ))
        assert body["status"] == "error"
        assert body["failed_reasons"][0]["reason"] == "job_source_blocked"

    def test_duplicate_labels_keep_source_identity(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        csv_b = _official_csv(tmp_path / "b.csv", [
            _trade_row("베타", "20250408093000", "20250408100000", "30", "1.0", "10000"),
        ])
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "B": _job_record(csv_b, trade_count=1),
        })
        body = api.portfolio_combine(self._payload(
            {"job_id": "A", "label": "동명"}, {"job_id": "B", "label": "동명"},
        ))
        assert body["status"] == "ok"
        # 라벨 충돌은 portfolio_analysis 가 #N 으로 유일화하고, sources 는
        # job_id/sha 로 두 입력을 구분한다.
        labels = {s["label"] for s in body["portfolio"]["strategies"]}
        assert labels == {"동명", "동명#2"}
        assert {s["job_id"] for s in body["sources"]} == {"A", "B"}

    def test_all_invalid_reports_each_reason(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        _patch_jobs(monkeypatch, tmp_path, {
            "X": _job_record(_partial_csv(tmp_path / "x.csv"), trade_count=2),
            "Y": _job_record(str(tmp_path / "none.csv"), trade_count=1),
        })
        body = api.portfolio_combine(self._payload(
            {"job_id": "X"}, {"job_id": "Y"},
        ))
        assert body["status"] == "error"
        assert body["failed"] == [0, 1]
        reasons = {f["reason"] for f in body["failed_reasons"]}
        assert reasons == {"job_source_blocked", "job_csv_missing"}

    def test_portfolio_uses_checked_snapshot_no_reread(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        csv_a = _official_csv(tmp_path / "a.csv", [
            _trade_row("알파", "20250407093000", "20250407100000", "30", "2.0", "20000"),
        ])
        csv_b = _official_csv(tmp_path / "b.csv", [
            _trade_row("베타", "20250408093000", "20250408100000", "30", "-1.0", "-10000"),
        ])
        _patch_jobs(monkeypatch, tmp_path, {
            "A": _job_record(csv_a, trade_count=1),
            "B": _job_record(csv_b, trade_count=1),
        })
        rereads: List[str] = []
        monkeypatch.setattr(analysis, "load_trades_csv",
                            lambda *a, **k: rereads.append("read") or [])
        body = api.portfolio_combine(self._payload(
            {"job_id": "A"}, {"job_id": "B"},
        ))
        assert rereads == []
        assert body["status"] == "ok"
