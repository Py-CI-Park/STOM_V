"""QSP7 거래 에피소드·잔여경로·가상 매도 파이프라인 계약."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

import pytest

from ai_strategy_loop.autopsy.exit_counterfactual import evaluate_policy
from ai_strategy_loop.autopsy.market_path import MarketPathRepository
from ai_strategy_loop.autopsy.trade_path_clock import add_seconds
from ai_strategy_loop.autopsy.trade_episode import EpisodeBuilder, read_trade_rows
from ai_strategy_loop.autopsy.trade_path_models import (
    Authority,
    Clause,
    ExitPolicy,
    ExitRule,
    Timeframe,
)


def _write_tick_db(database_dir: Path) -> None:
    database_dir.mkdir(parents=True)
    db_path = database_dir / "stock_tick_20250102.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            'CREATE TABLE "005930" ('
            '"index" INTEGER PRIMARY KEY, "현재가" REAL, "체결강도" REAL, '
            '"초당매수수량" REAL, "초당매도수량" REAL, '
            '"매수총잔량" REAL, "매도총잔량" REAL)'
        )
        connection.executemany(
            'INSERT INTO "005930" VALUES (?, ?, ?, ?, ?, ?, ?)',
            [
                (20250102090000, 1_000, 105, 10, 8, 120, 100),
                (20250102090030, 980, 92, 5, 12, 90, 130),
                (20250102090100, 970, 88, 4, 15, 80, 150),
                (20250102090130, 990, 101, 11, 8, 120, 110),
                (20250102090200, 1_020, 118, 18, 6, 160, 90),
                (20250102090300, 1_040, 121, 20, 5, 180, 80),
            ],
        )
    with sqlite3.connect(database_dir / "code_info.db") as connection:
        connection.execute('CREATE TABLE stockinfo ("index" TEXT, "종목명" TEXT)')
        connection.execute('INSERT INTO stockinfo VALUES (?, ?)', ("005930", "삼성전자"))


def _write_trade_csv(path: Path, *, name: str = "삼성전자") -> None:
    fields = [
        "종목명", "매수시간", "매도시간", "보유시간", "매수가", "매도가",
        "매수금액", "매도금액", "수익률", "수익금", "매도조건", "추가매수시간",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({
            "종목명": name,
            "매수시간": "20250102090000",
            "매도시간": "20250102090100",
            "보유시간": "60",
            "매수가": "1000",
            "매도가": "970",
            "매수금액": "1000000",
            "매도금액": "968260",
            "수익률": "-3.17",
            "수익금": "-31740",
            "매도조건": "손절",
            "추가매수시간": "[]",
        })


@pytest.fixture
def episode_fixture(tmp_path: Path):
    database_dir = tmp_path / "database"
    _write_tick_db(database_dir)
    csv_path = tmp_path / "trades.csv"
    _write_trade_csv(csv_path)
    repository = MarketPathRepository(database_dir=database_dir)
    rows = read_trade_rows(csv_path)
    builder = EpisodeBuilder(repository=repository, code_info_db=database_dir / "code_info.db")
    episode = builder.build(
        run_id="job-1",
        row=rows[0],
        timeframe=Timeframe.TICK,
        forced_liquidation_time=90300,
        decision_horizons=(30, 60, 120, 180, 240),
        continuation_horizons=(30, 60, 120, 180),
    )
    return episode, repository, csv_path


def test_episode_stops_at_forced_liquidation_and_marks_censoring(episode_fixture) -> None:
    # Given: 09:01 실제 손절, 09:03 전체청산 경계인 거래.
    episode, _, _ = episode_fixture

    # When: 진입/실제매도 기준 horizon을 함께 구성한다.
    by_horizon = {row.horizon_seconds: row for row in episode.continuation_outcomes}

    # Then: 경계 안의 60/120초는 회복을 보지만 180초는 경계를 넘어 차단된다.
    assert episode.authority is Authority.DIAGNOSTIC
    assert episode.market_path[-1].timestamp == 20250102090300
    assert by_horizon[60].available is True
    assert by_horizon[60].net_return_pct == pytest.approx(1.79, abs=0.01)
    assert by_horizon[120].net_return_pct == pytest.approx(3.78, abs=0.01)
    assert by_horizon[180].available is False
    assert by_horizon[180].reason == "forced_liquidation_boundary"


def test_counterfactual_uses_first_trigger_in_rule_order(episode_fixture) -> None:
    # Given: 손절 대신 수익 회복과 시간 만료 규칙이 순서대로 있는 정책.
    episode, _, _ = episode_fixture
    policy = ExitPolicy(
        name="회복 후 익절",
        rules=(
            ExitRule(
                rule_id="take_profit",
                clauses=(Clause(field="net_return_pct", operator=">=", value=1.5),),
                after_seconds=90,
            ),
            ExitRule(
                rule_id="time_exit",
                clauses=(Clause(field="hold_seconds", operator=">=", value=180),),
            ),
        ),
    )

    # When: 동일 진입을 고정하고 전체청산까지만 재생한다.
    outcome = evaluate_policy(episode, policy)

    # Then: 09:02 최초 익절 발동이 선택되고 자문 권위로 표시된다.
    assert outcome.authority is Authority.ADVISORY
    assert outcome.triggered_rule_id == "take_profit"
    assert outcome.exit_timestamp == 20250102090200
    assert outcome.net_return_pct == pytest.approx(1.79, abs=0.01)
    assert outcome.delta_profit_krw == 49_604


def test_market_repository_is_read_only_and_returns_no_post_boundary_rows(
    episode_fixture,
) -> None:
    # Given: 실제 fixture DB에는 경계 이후 행을 추가할 수 있는 구조다.
    _, repository, _ = episode_fixture

    # When: 명시된 전체청산까지만 시계열을 조회한다.
    path = repository.load(
        date=20250102,
        code="005930",
        timeframe=Timeframe.TICK,
        start_timestamp=20250102090000,
        end_timestamp=20250102090200,
    )

    # Then: 반환 시계열은 경계를 넘지 않고 연결은 query_only다.
    assert [point.timestamp for point in path.points][-1] == 20250102090200
    assert path.read_only is True


def test_consolidated_db_serves_every_trading_date_for_the_same_symbol(tmp_path: Path) -> None:
    # Given: 일별 DB가 없고 통합 stock_min_back.db 하나에 같은 종목의 두 날짜가 담긴 상태.
    database_dir = tmp_path / "database"
    database_dir.mkdir(parents=True)
    with sqlite3.connect(database_dir / "stock_min_back.db") as connection:
        connection.execute(
            'CREATE TABLE "005930" ("index" INTEGER PRIMARY KEY, "현재가" REAL)'
        )
        connection.executemany(
            'INSERT INTO "005930" VALUES (?, ?)',
            [
                (202504010900, 100.0), (202504010901, 101.0), (202504010902, 102.0),
                (202504040900, 200.0), (202504040901, 201.0), (202504040902, 202.0),
            ],
        )
    repository = MarketPathRepository(database_dir=database_dir)

    # When: 같은 저장소 인스턴스로 첫째 날 다음 둘째 날을 조회한다.
    first = repository.load(
        date=20250401, code="005930", timeframe=Timeframe.MIN,
        start_timestamp=202504010900, end_timestamp=202504011520,
    )
    second = repository.load(
        date=20250404, code="005930", timeframe=Timeframe.MIN,
        start_timestamp=202504040900, end_timestamp=202504041520,
    )

    # Then: 캐시가 날짜를 구분해 둘째 날 데이터가 비지 않는다.
    assert [point.timestamp for point in first.points] == [202504010900, 202504010901, 202504010902]
    assert [point.timestamp for point in second.points] == [202504040900, 202504040901, 202504040902]


def test_date_coverage_counts_rows_not_file_presence(tmp_path: Path) -> None:
    # Given: 통합 min DB 하나에 moneytop 이 2일치만 있고, 일별 파일은 하루치만 있다.
    database_dir = tmp_path / "database"
    database_dir.mkdir(parents=True)
    with sqlite3.connect(database_dir / "stock_min_back.db") as connection:
        connection.execute('CREATE TABLE moneytop ("index" INTEGER PRIMARY KEY, "종목코드" TEXT)')
        connection.executemany(
            'INSERT INTO moneytop VALUES (?, ?)',
            [(202504010900, "005930"), (202504040900, "005930")],
        )
    with sqlite3.connect(database_dir / "stock_min_20250407.db") as connection:
        connection.execute('CREATE TABLE "005930" ("index" INTEGER PRIMARY KEY, "현재가" REAL)')
    repository = MarketPathRepository(database_dir=database_dir)

    # When: 4개 날짜의 커버리지를 묻는다 (통합 2일 + 일별 1일 + 공백 1일).
    covered = repository.covered_dates(
        dates=(20250401, 20250404, 20250407, 20250410), timeframe=Timeframe.MIN,
    )

    # Then: 파일 존재가 아니라 실제 데이터 존재 기준으로 3일만 커버된다.
    assert covered == {20250401, 20250404, 20250407}


def test_ambiguous_symbol_is_excluded(tmp_path: Path) -> None:
    # Given: 동일 종목명이 두 코드에 연결된 code_info DB.
    database_dir = tmp_path / "database"
    _write_tick_db(database_dir)
    with sqlite3.connect(database_dir / "code_info.db") as connection:
        connection.execute('INSERT INTO stockinfo VALUES (?, ?)', ("000001", "삼성전자"))
    csv_path = tmp_path / "trades.csv"
    _write_trade_csv(csv_path)
    row = read_trade_rows(csv_path)[0]
    builder = EpisodeBuilder(
        repository=MarketPathRepository(database_dir=database_dir),
        code_info_db=database_dir / "code_info.db",
    )

    # When / Then: 이름 하나를 임의 코드로 추정하지 않는다.
    with pytest.raises(ValueError, match="ambiguous_symbol"):
        builder.build(
            run_id="job-1",
            row=row,
            timeframe=Timeframe.TICK,
            forced_liquidation_time=90300,
            decision_horizons=(60,),
            continuation_horizons=(60,),
        )


def test_counterfactual_forced_liquidation_replacement_requires_a_real_trigger(
    episode_fixture,
) -> None:
    # Given: 실제 매도사유가 전략종료청산인 에피소드 (사유만 교체한 복제).
    episode, _, _ = episode_fixture
    from dataclasses import replace as _replace
    forced_episode = _replace(
        episode,
        actual_exit=_replace(episode.actual_exit, reason="전략종료청산"),
    )
    never_policy = ExitPolicy("never", (
        ExitRule("rule-none", (Clause("net_return_pct", "<=", -99.0),)),
    ))

    # When: 가상 정책도 아무 규칙을 발동시키지 못해 전체청산으로 끝난다.
    outcome = evaluate_policy(forced_episode, never_policy)

    # Then: 실제 사유만 보고 "강제청산을 대체했다"고 과대 표시하지 않는다(P0-4).
    assert outcome.triggered_rule_id == "forced_liquidation"
    assert outcome.replaced_forced_liquidation is False


def test_min_horizon_rounds_forward_to_the_next_observed_bar() -> None:
    # Given/When: 1분봉에서 30초 horizon을 요청한다.
    observed = add_seconds(202501020900, 30, Timeframe.MIN)

    # Then: 같은 09:00 봉을 미래로 오인하지 않고 다음 09:01 봉으로 전진한다.
    assert observed == 202501020901


def test_six_digit_symbol_value_uses_the_existing_market_table(tmp_path: Path) -> None:
    # Given: 과거/상장폐지 종목처럼 종목명 칸에 6자리 코드가 직접 기록된 결과.
    database_dir = tmp_path / "database"
    _write_tick_db(database_dir)
    csv_path = tmp_path / "coded-trades.csv"
    _write_trade_csv(csv_path, name="005930")
    builder = EpisodeBuilder(
        repository=MarketPathRepository(database_dir=database_dir),
        code_info_db=database_dir / "code_info.db",
    )

    # When: code_info 이름 역조인이 없어도 해당 날짜 시장 테이블은 존재한다.
    episode = builder.build(
        run_id="job-code",
        row=read_trade_rows(csv_path)[0],
        timeframe=Timeframe.TICK,
        forced_liquidation_time=90300,
        decision_horizons=(60,),
        continuation_horizons=(60,),
    )

    # Then: 숫자를 이름으로 추정하지 않고 코드 자체로만 식별한다.
    assert episode.key.stock_code == "005930"
