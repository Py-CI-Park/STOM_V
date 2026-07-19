"""G007 V5.7 — rdc-1 research catalog API contract tests."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_strategy_loop.controller import state as state_module
from ai_strategy_loop.dashboard import research_api, research_catalog_api
from ai_strategy_loop.dashboard.app import create_app

ORIGIN = "http://127.0.0.1:8770"
ENV_KEY = "STOM_RESEARCH_ASSETS_DB"


ASSET_COLUMNS = (
    "asset_id",
    "kind",
    "path",
    "produced_commit",
    "seal_doc",
    "window",
    "status_tag",
    "regen_cmd",
    "summary",
    "exists_on_disk",
    "sha256",
    "size_bytes",
    "mtime_utc",
)
JUDGMENT_COLUMNS = (
    "series",
    "verdict",
    "key_metrics_json",
    "ledger_rows",
    "n_ledger_rows",
    "report_path",
    "source_path",
    "produced_commit",
    "ga_path_flag",
    "note",
)
CLAUSE_COLUMNS = (
    "clause_num",
    "text",
    "family",
    "w5_category",
    "tier",
    "n_sat",
    "n_unsat",
    "delta_pp",
    "ci_low_pp",
    "ci_high_pp",
    "mde_pp",
    "p_one_sided",
    "p_two_sided",
    "both_year_positive",
    "both_year_negative",
    "floor_pass",
    "fdr_survive",
    "classification",
    "year_delta_json",
    "extra_json",
)
CELL_COLUMNS = (
    "cell_id",
    "source",
    "source_path",
    "label_kind",
    "label_tag",
    "axis_set",
    "map_type",
    "time_label",
    "time_b",
    "updown_q",
    "mktcap_b",
    "gap_b",
    "gap_label",
    "win",
    "win_label",
    "exit_kind",
    "h",
    "n",
    "n_candidates",
    "censor_rate",
    "exclusion_rate",
    "insufficient",
    "mean_net",
    "median_net",
    "q25_net",
    "q75_net",
    "p_net_ge0",
    "p_net_ge1",
    "ci_low",
    "ci_high",
    "winrate",
    "payoff",
    "mfe_mean",
    "mae_mean",
    "year2022_mean",
    "year2022_sign",
    "year2023_mean",
    "year2023_sign",
    "extra_json",
)
LEDGER_COLUMNS = ("row_num", "ts", "series", "window", "trial_type", "target", "result", "session", "raw_json")


def _insert(conn: sqlite3.Connection, table: str, row: dict[str, object]) -> None:
    columns = tuple(row)
    placeholders = ", ".join("?" for _ in columns)
    conn.execute(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
        tuple(row[column] for column in columns),
    )


def _make_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE assets (
            asset_id TEXT PRIMARY KEY, kind TEXT, path TEXT, produced_commit TEXT,
            seal_doc TEXT, window TEXT, status_tag TEXT, regen_cmd TEXT, summary TEXT,
            exists_on_disk INTEGER, sha256 TEXT, size_bytes INTEGER, mtime_utc TEXT
        );
        CREATE TABLE judgments (
            series TEXT PRIMARY KEY, verdict TEXT, key_metrics_json TEXT, ledger_rows TEXT,
            n_ledger_rows INTEGER, report_path TEXT, source_path TEXT, produced_commit TEXT,
            ga_path_flag INTEGER, note TEXT
        );
        CREATE TABLE clauses (
            clause_num INTEGER PRIMARY KEY, text TEXT, family TEXT, w5_category TEXT,
            tier TEXT, n_sat INTEGER, n_unsat INTEGER, delta_pp REAL, ci_low_pp REAL,
            ci_high_pp REAL, mde_pp REAL, p_one_sided REAL, p_two_sided REAL,
            both_year_positive INTEGER, both_year_negative INTEGER, floor_pass INTEGER,
            fdr_survive INTEGER, classification TEXT, year_delta_json TEXT, extra_json TEXT
        );
        CREATE TABLE strategies (
            name TEXT PRIMARY KEY, source_section TEXT, family TEXT, rank_by_total INTEGER,
            total_return_pct REAL, annual_return_pct REAL, monthly_return_pct REAL,
            mdd_pct REAL, win_rate REAL, payoff REAL, trades INTEGER, api_compat TEXT,
            source_sha256 TEXT, lineage TEXT, rank_metrics_json TEXT, status_tag TEXT
        );
        CREATE TABLE cells (
            cell_id INTEGER PRIMARY KEY, source TEXT, source_path TEXT, label_kind TEXT,
            label_tag TEXT, axis_set TEXT, map_type TEXT, time_label INTEGER, time_b INTEGER,
            updown_q INTEGER, mktcap_b INTEGER, gap_b INTEGER, gap_label TEXT, win INTEGER,
            win_label TEXT, exit_kind TEXT, h INTEGER, n INTEGER, n_candidates INTEGER,
            censor_rate REAL, exclusion_rate REAL, insufficient INTEGER, mean_net REAL,
            median_net REAL, q25_net REAL, q75_net REAL, p_net_ge0 REAL, p_net_ge1 REAL,
            ci_low REAL, ci_high REAL, winrate REAL, payoff REAL, mfe_mean REAL, mae_mean REAL,
            year2022_mean REAL, year2022_sign INTEGER, year2023_mean REAL,
            year2023_sign INTEGER, extra_json TEXT
        );
        CREATE TABLE ledger_mirror (
            row_num INTEGER PRIMARY KEY, ts TEXT, series TEXT, window TEXT, trial_type TEXT,
            target TEXT, result TEXT, session TEXT, raw_json TEXT
        );
        """
    )
    _insert(
        conn,
        "assets",
        dict(
            zip(
                ASSET_COLUMNS,
                (
                    "a1",
                    "bank_parquet",
                    "docs/research/run/onset_l3_bank.parquet",
                    "7171a561",
                    "plans/seal.md(56564cba)",
                    "2022-03-23~2023-12-31",
                    "RR8_12 출구 조건부·bit-identical 검증",
                    "python scripts/build_research_catalog.py",
                    "온셋 은행 합성 행",
                    1,
                    "0" * 64,
                    123,
                    "2026-07-12T10:38:00+00:00",
                ),
            )
        ),
    )
    _insert(
        conn,
        "assets",
        dict(
            zip(
                ASSET_COLUMNS,
                (
                    "a2",
                    "judgment_json",
                    "docs/research/run/d1.json",
                    None,
                    "plans/seal.md",
                    "2022",
                    "판정 원문 딱지",
                    None,
                    "D1 판정 합성 행",
                    0,
                    None,
                    None,
                    None,
                ),
            )
        ),
    )
    _insert(
        conn,
        "judgments",
        dict(
            zip(
                JUDGMENT_COLUMNS,
                (
                    "D1 절-단위 분해",
                    "양성 — 압력 절 5종 load-bearing·원문 그대로",
                    '{"fdr_q":0.1,"load_bearing_nums":[1,4]}',
                    "12,13",
                    2,
                    "d1_clause_ablation_report.md",
                    "d1_clause_ablation_summary.json",
                    "7171a561",
                    0,
                    None,
                ),
            )
        ),
    )
    _insert(
        conn,
        "judgments",
        dict(
            zip(
                JUDGMENT_COLUMNS,
                ("BAD", "KILL", "not json", "bad,14", 1, None, None, None, 0, "bad json"),
            )
        ),
    )
    _insert(
        conn,
        "clauses",
        dict(
            zip(
                CLAUSE_COLUMNS,
                (
                    1,
                    "1 < 초당순매수금액 < 1000",
                    "초당순매수금액",
                    "quote_qty",
                    "M-namespace",
                    373112,
                    489820,
                    0.133951,
                    0.125539,
                    0.1434,
                    0.012767,
                    0.0,
                    0.0,
                    1,
                    0,
                    1,
                    1,
                    "load_bearing",
                    '{"2022":{"delta_pp":0.1215,"sign":1}}',
                    '{"polarity_note":"not(P)→만족=P","seed":20260712}',
                ),
            )
        ),
    )
    _insert(
        conn,
        "clauses",
        dict(
            zip(
                CLAUSE_COLUMNS,
                (
                    2,
                    "시간 필터",
                    "시간",
                    "time_gate",
                    "aux",
                    10,
                    20,
                    -0.1,
                    -0.2,
                    0.0,
                    0.1,
                    0.5,
                    1.0,
                    0,
                    1,
                    0,
                    0,
                    "none",
                    "{}",
                    "{}",
                ),
            )
        ),
    )
    _insert(
        conn,
        "cells",
        dict(
            zip(
                CELL_COLUMNS,
                (
                    961,
                    "o1g",
                    "o1g/o1g_grid_summary.json",
                    "h60",
                    "시초 함정 지도·O-3 null 기준선·자동 veto 금지",
                    None,
                    None,
                    None,
                    None,
                    None,
                    0,
                    0,
                    "lt0",
                    0,
                    "0900-0904",
                    "h60",
                    None,
                    13201,
                    13943,
                    0.0,
                    0.053216667862,
                    0,
                    -0.010445,
                    -0.011242,
                    -0.018928,
                    -0.0023,
                    0.2121,
                    0.0946,
                    -0.012246,
                    -0.008459,
                    None,
                    None,
                    -0.000642,
                    -0.026465,
                    -0.009515,
                    -1,
                    -0.010884,
                    -1,
                    '{"mktcap_label":"lt1000","p_one_sided":1.0}',
                ),
            )
        ),
    )
    _insert(
        conn,
        "cells",
        dict(
            zip(
                CELL_COLUMNS,
                (
                    1,
                    "sv1_l0",
                    "sv1/sv1_l0.db",
                    "h300",
                    "함정 설명 전용(S-v1 칸-조준 kill-2)·자동 veto 금지",
                    "time_ud",
                    "sv1",
                    900,
                    0,
                    1,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    300,
                    10,
                    10,
                    None,
                    None,
                    1,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    "{}",
                ),
            )
        ),
    )
    for row_num in (12, 13, 14):
        _insert(
            conn,
            "ledger_mirror",
            dict(
                zip(
                    LEDGER_COLUMNS,
                    (
                        row_num,
                        "2026-07-12T00:00:00+00:00",
                        "D1 절-단위 분해" if row_num != 14 else "BAD",
                        "2022~2023",
                        "trial",
                        f"target-{row_num}",
                        "sealed",
                        "alpha_restart_20260710",
                        json.dumps({"row_num": row_num}, ensure_ascii=False),
                    ),
                )
            ),
        )
    conn.commit()
    conn.close()


def _client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    monkeypatch.setattr(state_module, "CURRENT_STATE_FILE", tmp_path / "cs.json")
    monkeypatch.setattr(state_module, "STOP_FLAG_FILE", tmp_path / "STOP")
    return TestClient(create_app(), base_url=ORIGIN)


def _configured_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    db = tmp_path / "research_assets.db"
    _make_db(db)
    monkeypatch.setenv(ENV_KEY, str(db.resolve()))
    return _client(monkeypatch, tmp_path)


def test_env_only_catalog_configuration_and_retired_summary_route(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv(ENV_KEY, raising=False)
    client = _client(monkeypatch, tmp_path)

    for endpoint in ("/research/assets", "/research/judgments", "/research/cells", "/research/clauses"):
        response = client.get(endpoint)
        assert response.status_code == 200, endpoint
        payload = response.json()
        assert payload == {"available": False, "reason": "catalog_not_configured", "contract_version": "rdc-1"}

    assert client.get("/research/summary").status_code == 404

    monkeypatch.setenv(ENV_KEY, "relative/research_assets.db")
    payload = _client(monkeypatch, tmp_path).get("/research/assets").json()
    assert payload["reason"] == "catalog_not_configured"


def test_catalog_missing_path_uses_soft_error_without_full_path_leak(monkeypatch, tmp_path: Path) -> None:
    missing = (tmp_path / "secret_parent" / "research_assets.db").resolve()
    monkeypatch.setenv(ENV_KEY, str(missing))
    payload = _client(monkeypatch, tmp_path).get("/research/assets").json()

    assert payload["available"] is False
    assert payload["reason"] == "catalog_not_found"
    assert payload["path_hint"] == "secret_parent/research_assets.db"
    assert str(tmp_path) not in json.dumps(payload, ensure_ascii=False)


def test_catalog_schema_mismatch_is_unavailable_not_empty_success(monkeypatch, tmp_path: Path) -> None:
    db = tmp_path / "bad.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE assets (asset_id TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()
    monkeypatch.setenv(ENV_KEY, str(db.resolve()))

    payload = _client(monkeypatch, tmp_path).get("/research/assets").json()

    assert payload["available"] is False
    assert payload["reason"] == "schema_mismatch"
    assert payload["catalog"]["structure_ok"] is False
    assert "assets.kind" in payload["missing"]
    assert "judgments" in payload["missing"]


def test_assets_endpoint_filters_limits_and_preserves_catalog_fields(monkeypatch, tmp_path: Path) -> None:
    client = _configured_client(monkeypatch, tmp_path)

    payload = client.get("/research/assets?kind=bank_parquet&q=온셋&exists=1&limit=1&offset=0").json()

    assert payload["available"] is True
    assert payload["contract_version"] == "rdc-1"
    assert payload["catalog"]["structure_ok"] is True
    assert payload["catalog"]["db_mtime_utc"]
    assert payload["count"] == 1
    assert "assets" not in payload
    assert payload["items"][0]["asset_id"] == "a1"
    assert payload["items"][0]["status_tag"] == "RR8_12 출구 조건부·bit-identical 검증"

    empty = client.get("/research/assets?kind=not-a-kind").json()
    assert empty["available"] is True
    assert empty["items"] == []
    assert empty["count"] == 0

    invalid = client.get("/research/assets?exists=2").json()
    assert invalid["available"] is False
    assert invalid["reason"] == "invalid_param"
    assert invalid["param"] == "exists"


def test_judgments_decode_metrics_and_attach_ledger_without_recalculation(monkeypatch, tmp_path: Path) -> None:
    client = _configured_client(monkeypatch, tmp_path)

    payload = client.get("/research/judgments?include_ledger=1").json()

    assert payload["available"] is True
    assert payload["count"] == 2
    assert [item["series"] for item in payload["items"]] == ["D1 절-단위 분해", "BAD"]
    by_series = {item["series"]: item for item in payload["items"]}
    assert by_series["D1 절-단위 분해"]["key_metrics"] == {"fdr_q": 0.1, "load_bearing_nums": [1, 4]}
    assert by_series["D1 절-단위 분해"]["ledger_rows"] == [12, 13]
    assert [row["row_num"] for row in by_series["D1 절-단위 분해"]["ledger"]] == [12, 13]
    assert by_series["D1 절-단위 분해"]["ledger"][0]["raw_json"] == '{"row_num": 12}'
    assert by_series["BAD"]["key_metrics"] == {}
    assert by_series["BAD"]["key_metrics_error"] is True
    assert by_series["BAD"]["ledger_rows"] == [14]
    assert by_series["BAD"]["ledger_rows_error"] is True

    empty = client.get("/research/judgments?series=missing").json()
    assert empty["available"] is True
    assert empty["items"] == []


def test_cells_endpoint_requires_dynamic_source_and_empty_valid_filters_stay_available(monkeypatch, tmp_path: Path) -> None:
    client = _configured_client(monkeypatch, tmp_path)

    missing_source = client.get("/research/cells").json()
    assert missing_source["available"] is False
    assert missing_source["reason"] == "invalid_param"
    assert missing_source["param"] == "source"
    assert missing_source["allowed"] == ["o1g", "sv1_l0"]

    payload = client.get("/research/cells?source=o1g&label_kind=h60&gap_b=0&limit=10").json()
    assert payload["available"] is True
    assert payload["allowed"] == ["o1g", "sv1_l0"]
    assert payload["count"] == 1
    assert payload["items"][0]["label_tag"] == "시초 함정 지도·O-3 null 기준선·자동 veto 금지"
    assert payload["items"][0]["extra"] == {"mktcap_label": "lt1000", "p_one_sided": 1.0}

    empty = client.get("/research/cells?source=o1g&gap_b=99").json()
    assert empty["available"] is True
    assert empty["items"] == []
    assert empty["count"] == 0
    assert empty["allowed"] == ["o1g", "sv1_l0"]

    invalid = client.get("/research/cells?source=does-not-exist").json()
    assert invalid["available"] is False
    assert invalid["reason"] == "invalid_param"
    assert invalid["allowed"] == ["o1g", "sv1_l0"]


def test_clauses_endpoint_filters_single_item_and_decodes_json_fields(monkeypatch, tmp_path: Path) -> None:
    client = _configured_client(monkeypatch, tmp_path)

    payload = client.get("/research/clauses?classification=load_bearing&w5_category=quote_qty").json()
    assert payload["available"] is True
    assert payload["count"] == 1
    assert payload["items"][0]["text"] == "1 < 초당순매수금액 < 1000"
    assert payload["items"][0]["year_delta"] == {"2022": {"delta_pp": 0.1215, "sign": 1}}
    assert payload["items"][0]["extra"] == {"polarity_note": "not(P)→만족=P", "seed": 20260712}

    single = client.get("/research/clauses?clause_num=1").json()
    assert single["available"] is True
    assert single["count"] == 1
    assert single["item"]["clause_num"] == 1

    empty = client.get("/research/clauses?family=없는가문").json()
    assert empty["available"] is True
    assert empty["count"] == 0
    assert empty["items"] == []


def test_catalog_connection_uses_sqlite_uri_mode_ro(monkeypatch, tmp_path: Path) -> None:
    db = tmp_path / "research_assets.db"
    _make_db(db)
    monkeypatch.setenv(ENV_KEY, str(db.resolve()))

    conn, catalog, error = research_catalog_api._catalog_connection()
    assert error is None
    assert catalog is not None and catalog["structure_ok"] is True
    assert conn is not None
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("INSERT INTO assets (asset_id) VALUES ('blocked')")
    conn.close()


def test_static_catalog_backend_forbids_legacy_default_aggregation_and_mutation_sql() -> None:
    catalog_source = Path(research_catalog_api.__file__).read_text(encoding="utf-8")
    research_source = Path(research_api.__file__).read_text(encoding="utf-8")

    assert "STOM_RESEARCH_ASSETS_DB" in catalog_source
    assert "?mode=ro" in catalog_source
    assert "legacy_non_authoritative_catalogs" not in catalog_source + research_source
    assert "/research/summary" not in catalog_source + research_source
    assert "_CATALOG_DB" not in research_source
    assert re.findall(r'@router\.get\("([^"]+)"\)', catalog_source) == [
        "/research/assets",
        "/research/judgments",
        "/research/cells",
        "/research/clauses",
    ]

    forbidden_sql = (
        r"\bCOUNT\s*\(",
        r"\bAVG\s*\(",
        r"\bSUM\s*\(",
        r"\bGROUP\s+BY\b",
        r"\bINSERT\s+(?:INTO|OR)\b",
        r"\bUPDATE\s+[A-Za-z_][A-Za-z0-9_]*\s+SET\b",
        r"\bDELETE\s+FROM\b",
        r"\bATTACH\s+(?:DATABASE|\?)\b",
        r"\bCREATE\s+(?:TABLE|INDEX|VIEW)\b",
        r"\bDROP\s+(?:TABLE|INDEX|VIEW)\b",
        r"immutable=1",
    )
    for pattern in forbidden_sql:
        assert re.search(pattern, catalog_source, flags=re.IGNORECASE) is None, pattern
