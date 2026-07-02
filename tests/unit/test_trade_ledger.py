"""T2.5 거래 원장(TradeLedger) 단위 테스트 (네트워크 없음).

검증:
  - 백엔드 자동 감지: pyarrow 있으면 parquet, 없으면 sqlite — 어느 쪽이든 API 동일.
  - append/load 라운드트립: 정본 컬럼 값 보존, trade_date(매수시간 앞 8자리) 파생,
    진입 컨텍스트(B_*) 보존, schema_version 필드 포함.
  - MFE/MAE(R_*) 원천 부재 → 결측(None/NaN) 허용, 무예외.
  - cohort_compare: 동일 거래일 교집합 제한 후 거래수/손익/승률 비교 + status 코드.
  - 계약 위반만 ValueError (meta 필수 필드, 미지 필터 키, 정본 컬럼 0개 df).
  - 결정론 직렬화: 동일 입력 → 동일 레코드 JSON / 동일 비교 dict.
  - 원본 df 불변성, 인스턴스 재생성 후 영속성.
"""

import json
import os
import sys

import pandas as pd
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.autopsy.trade_ledger import (  # noqa: E402
    COMPARE_STATUS_EMPTY,
    COMPARE_STATUS_NO_COMMON,
    COMPARE_STATUS_OK,
    DATE_COLUMN,
    FULL_COLUMNS,
    LEDGER_COLUMNS,
    TRADE_LEDGER_SCHEMA_VERSION,
    TradeLedger,
    TradeLedgerMeta,
    frame_to_records,
)


def _pyarrow_available():
    try:
        import pyarrow  # noqa: F401
    except Exception:
        return False
    return True


# 이 환경에서 실제 사용 가능한 백엔드만 파라미터화 — 어느 쪽이든 테스트는 통과해야 한다.
BACKENDS = ["sqlite"] + (["parquet"] if _pyarrow_available() else [])


@pytest.fixture(params=BACKENDS)
def ledger(request, tmp_path):
    """가용 백엔드별 TradeLedger 인스턴스."""
    return TradeLedger(tmp_path / "ledger", backend=request.param)


def _meta(candidate="cand_a", run="run_1", buy="b" * 16, sell="s" * 16):
    return TradeLedgerMeta(
        run_id=run, candidate_id=candidate, buy_sha256=buy, sell_sha256=sell
    )


def _rows(specs):
    """specs: (거래일 8자리 str, 수익률, 수익금) 리스트 → 거래행 dict 리스트."""
    rows = []
    for i, (date, ret, profit) in enumerate(specs):
        rows.append({
            "종목명": f"테스트종목{i}",
            "매수시간": f"{date}0901",       # YYYYMMDDHHMM — 앞 8자리가 거래일.
            "매도시간": f"{date}0935",
            "보유시간": 34,
            "매수가": 10000 + i,
            "매도가": 10100 + i,
            "수익률": ret,
            "수익금": profit,
            "매도조건": "손절" if ret <= 0 else "익절",
            "B_체결강도": 120.5 + i,
            "B_등락율": 3.2,
            "B_매수총잔량": 50000 + i * 10,
        })
    return rows


# ---------------------------------------------------------------------
# 백엔드 자동 감지.
# ---------------------------------------------------------------------
def test_auto_backend_matches_pyarrow_presence(tmp_path):
    """auto: pyarrow 있으면 parquet, 없으면 sqlite(표준 라이브러리)."""
    led = TradeLedger(tmp_path / "auto")
    expected = "parquet" if _pyarrow_available() else "sqlite"
    assert led.backend_name == expected


def test_explicit_parquet_without_pyarrow_raises(tmp_path):
    """pyarrow 없는 환경에서 parquet 강제 지정은 명시적 ValueError."""
    if _pyarrow_available():
        pytest.skip("pyarrow 설치 환경 — 해당 없음")
    with pytest.raises(ValueError):
        TradeLedger(tmp_path / "pq", backend="parquet")


def test_unknown_backend_raises(tmp_path):
    with pytest.raises(ValueError):
        TradeLedger(tmp_path / "x", backend="csv")


# ---------------------------------------------------------------------
# append / load 라운드트립.
# ---------------------------------------------------------------------
def test_roundtrip_preserves_values_and_derives_trade_date(ledger):
    """저장 → 조회: 값 보존 + trade_date 파생 + schema_version 포함."""
    df = pd.DataFrame(_rows([("20260405", 1.0, 1000.0), ("20260406", -0.5, -500.0)]))
    written = ledger.append_trades(_meta(), df)
    assert written == 2

    loaded = ledger.load_trades({"candidate_id": "cand_a"})
    assert list(loaded.columns) == list(FULL_COLUMNS)
    assert len(loaded) == 2
    assert loaded["schema_version"].tolist() == [TRADE_LEDGER_SCHEMA_VERSION] * 2
    assert loaded["run_id"].tolist() == ["run_1"] * 2
    assert loaded["buy_sha256"].iloc[0] == "b" * 16
    assert loaded[DATE_COLUMN].tolist() == [20260405, 20260406]
    assert loaded["매수시간"].iloc[0] == pytest.approx(202604050901.0)
    assert loaded["수익률"].tolist() == pytest.approx([1.0, -0.5])
    assert loaded["종목명"].tolist() == ["테스트종목0", "테스트종목1"]
    assert loaded["매도조건"].tolist() == ["익절", "손절"]


def test_entry_context_b_columns_preserved(ledger):
    """진입 컨텍스트(B_*)가 그대로 영속된다."""
    df = pd.DataFrame(_rows([("20260405", 1.0, 1000.0)]))
    ledger.append_trades(_meta(), df)
    loaded = ledger.load_trades(None)
    assert loaded["B_체결강도"].iloc[0] == pytest.approx(120.5)
    assert loaded["B_매수총잔량"].iloc[0] == pytest.approx(50000.0)
    # 원천에 없던 B_ 컬럼은 결측으로 채워져 스키마가 고정된다.
    assert pd.isna(loaded["B_회전율"].iloc[0])


def test_missing_mfe_mae_columns_allowed(ledger):
    """R_MFE/R_MAE 등 R_* 컬럼이 원천에 없어도 결측 허용, 무예외."""
    df = pd.DataFrame(_rows([("20260405", 1.0, 1000.0)]))
    assert "R_MFE" not in df.columns
    ledger.append_trades(_meta(), df)
    loaded = ledger.load_trades(None)
    for column in ("R_MFE", "R_MAE", "R_매수후최고수익률", "R_매수후최저수익률"):
        assert pd.isna(loaded[column].iloc[0])


def test_mfe_mae_values_roundtrip_when_present(ledger):
    """R_* 값이 있으면 그대로 보존된다."""
    rows = _rows([("20260405", 1.0, 1000.0)])
    rows[0]["R_MFE"] = 2.5
    rows[0]["R_MAE"] = -1.2
    ledger.append_trades(_meta(), pd.DataFrame(rows))
    loaded = ledger.load_trades(None)
    assert loaded["R_MFE"].iloc[0] == pytest.approx(2.5)
    assert loaded["R_MAE"].iloc[0] == pytest.approx(-1.2)


def test_append_empty_df_returns_zero(ledger):
    df = pd.DataFrame(columns=["종목명", "매수시간", "수익률"])
    assert ledger.append_trades(_meta(), df) == 0
    assert len(ledger.load_trades(None)) == 0


def test_append_does_not_mutate_input_df(ledger):
    """불변성: append_trades 는 원본 df 를 변형하지 않는다."""
    df = pd.DataFrame(_rows([("20260405", 1.0, 1000.0)]))
    snapshot = df.copy(deep=True)
    ledger.append_trades(_meta(), df)
    pd.testing.assert_frame_equal(df, snapshot)


def test_meta_mapping_accepted_and_extra_keys_ignored(ledger):
    """meta 는 Mapping 도 허용 — 여분 키(lane 등)는 무시."""
    meta = {
        "run_id": "run_1", "candidate_id": "cand_m",
        "buy_sha256": "b" * 16, "sell_sha256": "s" * 16, "lane": "repair",
    }
    ledger.append_trades(meta, pd.DataFrame(_rows([("20260405", 1.0, 100.0)])))
    loaded = ledger.load_trades({"candidate_id": "cand_m"})
    assert len(loaded) == 1


# ---------------------------------------------------------------------
# 계약 위반 → ValueError.
# ---------------------------------------------------------------------
def test_invalid_meta_raises():
    with pytest.raises(ValueError):
        TradeLedgerMeta(run_id="", candidate_id="c")
    with pytest.raises(ValueError):
        TradeLedgerMeta(run_id="r", candidate_id="   ")
    with pytest.raises(ValueError):
        TradeLedgerMeta(run_id="r", candidate_id="c", buy_sha256=None)  # type: ignore[arg-type]


def test_unknown_filter_key_raises(ledger):
    with pytest.raises(ValueError):
        ledger.load_trades({"lane": "repair"})


def test_df_without_any_ledger_column_raises(ledger):
    """정본 컬럼이 전무한 비어있지 않은 df 는 호출측 버그로 간주."""
    df = pd.DataFrame([{"foo": 1, "bar": 2}])
    with pytest.raises(ValueError):
        ledger.append_trades(_meta(), df)


# ---------------------------------------------------------------------
# meta 필터 / 후보 목록 / 영속성.
# ---------------------------------------------------------------------
def test_filter_by_meta_fields(ledger):
    ledger.append_trades(
        _meta(candidate="cand_a", buy="aa"), pd.DataFrame(_rows([("20260405", 1.0, 100.0)]))
    )
    ledger.append_trades(
        _meta(candidate="cand_b", buy="bb"),
        pd.DataFrame(_rows([("20260405", -1.0, -100.0), ("20260406", 2.0, 200.0)])),
    )
    assert len(ledger.load_trades({"candidate_id": "cand_a"})) == 1
    assert len(ledger.load_trades({"buy_sha256": "bb"})) == 2
    assert len(ledger.load_trades({"candidate_id": "cand_b", "buy_sha256": "aa"})) == 0
    assert len(ledger.load_trades(None)) == 3


def test_list_candidates_sorted_deterministic(ledger):
    ledger.append_trades(_meta(candidate="cand_b"), pd.DataFrame(_rows([("20260405", 1.0, 1.0)])))
    ledger.append_trades(_meta(candidate="cand_a"), pd.DataFrame(_rows([("20260405", 1.0, 1.0)])))
    keys = ledger.list_candidates()
    assert [k["candidate_id"] for k in keys] == ["cand_a", "cand_b"]
    assert set(keys[0]) == {"run_id", "candidate_id", "buy_sha256", "sell_sha256"}


def test_persistence_across_instances(tmp_path):
    """같은 root 로 재생성해도 데이터가 남아 있다 (영속성)."""
    root = tmp_path / "persist"
    first = TradeLedger(root, backend=BACKENDS[0])
    first.append_trades(_meta(), pd.DataFrame(_rows([("20260405", 1.0, 1000.0)])))
    second = TradeLedger(root, backend=BACKENDS[0])
    loaded = second.load_trades({"candidate_id": "cand_a"})
    assert len(loaded) == 1
    assert loaded["수익금"].iloc[0] == pytest.approx(1000.0)


# ---------------------------------------------------------------------
# cohort_compare — 동일 거래일 교집합 비교.
# ---------------------------------------------------------------------
def _seed_two_candidates(ledger):
    """A: 4/05, 4/06, 4/07 — B: 4/06, 4/07, 4/08 → 교집합 {4/06, 4/07}."""
    ledger.append_trades(_meta(candidate="cand_a"), pd.DataFrame(_rows([
        ("20260405", 1.0, 1000.0),
        ("20260405", -0.5, -500.0),
        ("20260406", 2.0, 2000.0),
        ("20260407", -1.0, -800.0),
    ])))
    ledger.append_trades(_meta(candidate="cand_b"), pd.DataFrame(_rows([
        ("20260406", 0.5, 300.0),
        ("20260406", 1.5, 700.0),
        ("20260407", -2.0, -1000.0),
        ("20260408", 3.0, 1500.0),
    ])))


def test_cohort_compare_restricts_to_common_dates(ledger):
    _seed_two_candidates(ledger)
    result = ledger.cohort_compare("cand_a", "cand_b")

    assert result["schema_version"] == TRADE_LEDGER_SCHEMA_VERSION
    assert result["status"] == COMPARE_STATUS_OK
    assert result["common_dates"] == [20260406, 20260407]
    assert result["a_only_date_count"] == 1   # 20260405
    assert result["b_only_date_count"] == 1   # 20260408
    assert result["total_rows_a"] == 4
    assert result["total_rows_b"] == 4

    # 교집합 제한 후: A = [+2.0/2000, -1.0/-800], B = [+0.5/300, +1.5/700, -2.0/-1000].
    assert result["a"]["trade_count"] == 2
    assert result["a"]["total_profit"] == pytest.approx(1200.0)
    assert result["a"]["avg_return"] == pytest.approx(0.5)
    assert result["a"]["win_rate"] == pytest.approx(0.5)
    assert result["b"]["trade_count"] == 3
    assert result["b"]["total_profit"] == pytest.approx(0.0)
    assert result["b"]["avg_return"] == pytest.approx(0.0)
    assert result["b"]["win_rate"] == pytest.approx(0.666667)

    assert result["delta"]["trade_count"] == -1
    assert result["delta"]["total_profit"] == pytest.approx(1200.0)
    assert result["delta"]["avg_return"] == pytest.approx(0.5)
    assert result["delta"]["win_rate"] == pytest.approx(-0.166667)

    assert result["per_date"] == [
        {"date": 20260406, "a_trades": 1, "a_profit": 2000.0,
         "b_trades": 2, "b_profit": 1000.0},
        {"date": 20260407, "a_trades": 1, "a_profit": -800.0,
         "b_trades": 1, "b_profit": -1000.0},
    ]


def test_cohort_compare_no_common_dates(ledger):
    ledger.append_trades(_meta(candidate="cand_a"),
                         pd.DataFrame(_rows([("20260405", 1.0, 100.0)])))
    ledger.append_trades(_meta(candidate="cand_b"),
                         pd.DataFrame(_rows([("20260408", 1.0, 100.0)])))
    result = ledger.cohort_compare("cand_a", "cand_b")
    assert result["status"] == COMPARE_STATUS_NO_COMMON
    assert result["common_dates"] == []
    assert result["a"]["trade_count"] == 0
    assert result["b"]["trade_count"] == 0


def test_cohort_compare_empty_candidate(ledger):
    ledger.append_trades(_meta(candidate="cand_a"),
                         pd.DataFrame(_rows([("20260405", 1.0, 100.0)])))
    result = ledger.cohort_compare("cand_a", "cand_missing")
    assert result["status"] == COMPARE_STATUS_EMPTY
    assert result["total_rows_b"] == 0
    assert result["b"]["trade_count"] == 0
    assert result["b"]["avg_return"] is None
    assert result["b"]["win_rate"] is None
    assert result["delta"]["avg_return"] is None


def test_cohort_compare_accepts_meta_and_mapping(ledger):
    """후보 지정: candidate_id 문자열 / 필터 Mapping / TradeLedgerMeta 모두 허용."""
    _seed_two_candidates(ledger)
    by_meta = ledger.cohort_compare(_meta(candidate="cand_a"), {"candidate_id": "cand_b"})
    assert by_meta["status"] == COMPARE_STATUS_OK
    assert by_meta["candidate_a"]["candidate_id"] == "cand_a"
    with pytest.raises(ValueError):
        ledger.cohort_compare("", "cand_b")
    with pytest.raises(ValueError):
        ledger.cohort_compare({}, "cand_b")


# ---------------------------------------------------------------------
# 결정론 직렬화.
# ---------------------------------------------------------------------
def test_deterministic_records_and_compare(tmp_path):
    """동일 입력 → 두 원장에서 레코드 JSON / 비교 dict JSON 이 완전히 같다."""
    outputs = []
    for name in ("one", "two"):
        led = TradeLedger(tmp_path / name, backend=BACKENDS[0])
        _seed_two_candidates(led)
        records = frame_to_records(led.load_trades(None))
        compare = led.cohort_compare("cand_a", "cand_b")
        outputs.append((
            json.dumps(records, ensure_ascii=True, sort_keys=True),
            json.dumps(compare, ensure_ascii=True, sort_keys=True),
        ))
    assert outputs[0] == outputs[1]


def test_frame_to_records_is_json_safe(ledger):
    """NaN 은 None 으로 치환되어 json 직렬화가 항상 성공한다."""
    ledger.append_trades(_meta(), pd.DataFrame(_rows([("20260405", 1.0, 1000.0)])))
    records = frame_to_records(ledger.load_trades(None))
    assert len(records) == 1
    assert records[0]["R_MFE"] is None
    assert list(records[0].keys()) == list(FULL_COLUMNS)
    json.dumps(records)  # 예외 없이 직렬화되어야 한다.


def test_trade_date_unparsable_becomes_missing(ledger):
    """매수시간이 없거나 8자리 미만이면 trade_date 는 결측 — 교집합 계산에서 제외."""
    rows = _rows([("20260405", 1.0, 100.0)])
    rows[0]["매수시간"] = "0901"          # 8자리 미만 → 파싱 불가.
    rows.append({**rows[0], "매수시간": None})
    ledger.append_trades(_meta(), pd.DataFrame(rows))
    loaded = ledger.load_trades(None)
    assert loaded[DATE_COLUMN].isna().all()


def test_schema_columns_cover_ledger_contract():
    """정본 스키마에 진입(B_*)/청산(S_*)/결과(R_*) 컬럼이 모두 포함된다."""
    assert sum(c.startswith("B_") for c in LEDGER_COLUMNS) == 14
    assert sum(c.startswith("S_") for c in LEDGER_COLUMNS) == 5
    assert sum(c.startswith("R_") for c in LEDGER_COLUMNS) == 4
    assert FULL_COLUMNS[0] == "schema_version"
    assert DATE_COLUMN in FULL_COLUMNS
