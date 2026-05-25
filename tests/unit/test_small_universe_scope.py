"""small_universe 스코프 백테 invocation 단위 테스트 (실 백테 미실행, 네트워크 없음).

검증:
  - bt_scope='small_universe' 이면 run_backtest_for가
      * STOM_CLI_DB_STOCK_BACK_MIN 을 subset DB로 설정하고
      * --divid-mode '종목코드별 분류' 를 쓰며
      * --one-code 를 쓰지 않는다.
  - bt_scope='single_stock' (기존)은
      * --divid-mode '한종목 로딩' + --one-code 를 쓰고
      * STOM_CLI_DB_STOCK_BACK_MIN 오버라이드를 추가하지 않는다.
  - subset DB가 없으면 raise 없이 구체 실패 outcome을 반환한다(never-raises 계약).

subprocess.run 은 monkeypatch로 가로채 cmd/env를 캡처한다(실 백테 미실행).
"""

import os
import sqlite3
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import loop as L  # noqa: E402
from ai_strategy_loop.scripts import build_subset_db as B  # noqa: E402

_MIN_DAY_DIV = 10_000


class _FakeProc:
    """subprocess.run 결과 모킹: 성공 status JSON을 stdout으로 돌려준다."""

    def __init__(self, csv_path="fake.csv"):
        self.returncode = 0
        self.stdout = (
            '{"status": "success", "csv_path": "%s", '
            '"metrics": {"trade_count": 3}}' % csv_path
        )
        self.stderr = ""


def _make_tiny_subset(tmp_path):
    """small_universe 경로가 윈도우를 산출할 수 있도록 TINY subset DB를 만든다.

    build_subset_db로 합성 소스에서 N=3 subset을 만들어, 실제 빌더 산출물이
    moneytop 윈도우 산출에 그대로 쓰이는지까지 함께 커버한다.
    """
    src = tmp_path / "src.db"
    con = sqlite3.connect(str(src))
    cur = con.cursor()
    cur.execute('CREATE TABLE "moneytop" ("index" INTEGER, "거래대금순위" TEXT)')
    cur.execute('CREATE TABLE "stockinfo" ("index" TEXT, "종목명" TEXT, "코스닥" INTEGER)')
    codes = ["AAAAAA", "BBBBBB", "CCCCCC"]
    days = [20250101, 20250102, 20250103, 20250104, 20250105]
    for c in codes:
        cur.execute(f'CREATE TABLE "{c}" ("index" INTEGER, "현재가" INTEGER)')
        cur.executemany(
            f'INSERT INTO "{c}" VALUES (?,?)',
            [(d * _MIN_DAY_DIV + 900, 1000) for d in days],
        )
    cur.executemany(
        'INSERT INTO moneytop ("index","거래대금순위") VALUES (?,?)',
        [(d * _MIN_DAY_DIV + 900, ";".join(codes)) for d in days],
    )
    cur.executemany(
        "INSERT INTO stockinfo VALUES (?,?,?)", [(c, f"N_{c}", 0) for c in codes]
    )
    con.commit()
    con.close()

    subset = tmp_path / "subset.db"
    B.build_subset_db(src, subset, size=3)
    return str(subset)


def _capture_run(monkeypatch):
    """subprocess.run 을 가로채 (cmd, env)를 캡처하고 성공 proc을 돌려준다."""
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs.get("env", {})
        return _FakeProc()

    monkeypatch.setattr(L.subprocess, "run", fake_run)
    return captured


def test_small_universe_uses_subset_db_and_code_division(monkeypatch, tmp_path):
    """small_universe: STOM_CLI_DB_STOCK_BACK_MIN=subset + '종목코드별 분류', one_code 없음."""
    subset = _make_tiny_subset(tmp_path)
    captured = _capture_run(monkeypatch)

    config = LoopConfig(
        bt_scope="small_universe",
        bt_subset_db=subset,
        bt_window_days_universe=3,
        bt_engine_count=2,  # distinct 코드(3) >= 엔진 수(2) 충족.
    )
    outcome = L.run_backtest_for(config, "AILOOP_min_buy", "AILOOP_min_sell")

    assert outcome.ok is True
    cmd = captured["cmd"]
    env = captured["env"]

    # subset DB가 back-min DB로 오버라이드됐다.
    assert env.get("STOM_CLI_DB_STOCK_BACK_MIN") == subset
    # '종목코드별 분류' 사용, one_code 미사용.
    assert "종목코드별 분류" in cmd
    assert "--one-code" not in cmd
    assert "한종목 로딩" not in cmd
    # 윈도우는 subset moneytop에서 산출(앞쪽 3거래일 → 20250101~20250103).
    si = cmd.index("--start")
    ei = cmd.index("--end")
    assert cmd[si + 1] == "20250101"
    assert cmd[ei + 1] == "20250103"
    # 전략 DB는 여전히 격리 루프 DB.
    assert env.get("STOM_CLI_DB_STRATEGY") == str(L.bootstrap.LOOP_DB_STRATEGY)


def test_single_stock_uses_one_code_and_no_back_min_override(monkeypatch, tmp_path):
    """single_stock(기존): '한종목 로딩' + --one-code, back-min 오버라이드 없음."""
    captured = _capture_run(monkeypatch)
    # 종목 자동 선택을 결정론적으로 고정(실 1.4GB DB 미접근).
    monkeypatch.setattr(
        L, "_select_single_stock",
        lambda timeframe, window_days: ("005930", 20250101, 20250105, 5),
    )

    config = LoopConfig(bt_scope="single_stock", bt_timeframe="min")
    outcome = L.run_backtest_for(config, "AILOOP_min_buy", "AILOOP_min_sell")

    assert outcome.ok is True
    cmd = captured["cmd"]
    env = captured["env"]

    assert "한종목 로딩" in cmd
    assert "--one-code" in cmd
    assert cmd[cmd.index("--one-code") + 1] == "005930"
    assert "종목코드별 분류" not in cmd
    # single_stock은 back-min DB를 오버라이드하지 않는다(부모 env 상속분만).
    assert "STOM_CLI_DB_STOCK_BACK_MIN" not in env


def test_small_universe_missing_subset_db_returns_failure_outcome(monkeypatch, tmp_path):
    """subset DB가 없으면 raise 없이 구체 실패 outcome(never-raises 계약)."""
    # subprocess는 호출되면 안 됨(그 전에 실패해야 함) → 호출 시 폭발하도록.
    monkeypatch.setattr(
        L.subprocess, "run",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("백테가 호출되면 안 됨")),
    )
    missing = str(tmp_path / "nope_subset.db")

    config = LoopConfig(bt_scope="small_universe", bt_subset_db=missing)
    outcome = L.run_backtest_for(config, "buy_x", "sell_x")

    assert outcome.ok is False
    assert outcome.status == "error"
    assert "subset DB 없음" in outcome.reason
