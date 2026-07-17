from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]


def load() -> object:
    spec = importlib.util.spec_from_file_location("g002_materializer_test", ROOT / "scripts/u7_f0_materialize.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _tiny_parquet(tmp_path: Path, materializer, *, duplicate: bool = False) -> tuple[Path, Path]:
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    branch = next(iter(materializer.BRANCH_BITS))
    l3_rows, d1_rows = [], []
    for ordinal in range(2):
        t0 = f"2022010309000{ordinal}"
        l3 = {"code": "000001", "day": "20220103", "off": str(ordinal), "t0": t0, "year": 2022,
              "updown_q": 0, "mktcap_b": 0, "time_b": 0, "l3_net": 0.01, "l3_labeled": 0,
              "l3_clause": "x", "l3_exit": "x"}
        d1 = {"code": "000001", "day": "20220103", "off": str(0 if duplicate else ordinal), "t0": t0}
        d1.update({f"bit_{number}": int(f"bit_{number}" in materializer.BRANCH_BITS[branch]) for number in range(1, 40)})
        l3_rows.append(l3)
        d1_rows.append(d1)
    tmp_path.mkdir(parents=True, exist_ok=True)
    l3_path, d1_path = tmp_path / "l3.parquet", tmp_path / "d1.parquet"
    pq.write_table(pa.Table.from_pylist(l3_rows), l3_path)
    pq.write_table(pa.Table.from_pylist(d1_rows), d1_path)
    return l3_path, d1_path


def test_real_arrow_join_requires_schema_bits_exact_keys_and_test_row_count(tmp_path: Path) -> None:
    materializer = load()
    l3, d1 = _tiny_parquet(tmp_path, materializer)
    rows = materializer._joined_l3(l3, d1, identity_only=True, expected_row_count=2)
    assert len(rows) == 2
    # The injectable count is limited to this tiny real-Parquet fixture; production omits it.
    with pytest.raises(ValueError, match="row count"):
        materializer._joined_l3(l3, d1, identity_only=True, expected_row_count=3)
    l3, d1 = _tiny_parquet(tmp_path / "duplicate", materializer, duplicate=True)
    with pytest.raises(ValueError, match="identity join"):
        materializer._joined_l3(l3, d1, identity_only=True, expected_row_count=2)


def test_day_aware_resolution_and_null_replay_parity(tmp_path: Path) -> None:
    materializer = load()
    db = sqlite3.connect(tmp_path / "ticks.db")
    columns = ", ".join(f'"{name}" REAL' for name in materializer.TICK_COLUMNS)
    db.execute(f'CREATE TABLE "000001" ({columns})')
    db.execute('CREATE TABLE stockinfo ("종목명" TEXT, "index" TEXT)')
    db.execute('INSERT INTO stockinfo VALUES ("same", "000001")')
    db.execute('INSERT INTO "000001" VALUES (' + ",".join("?" for _ in materializer.TICK_COLUMNS) + ")",
               [20220103090000, None, 5000, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1])
    assert materializer._stock_code(db, "000001", "20220103") == "000001"
    assert materializer._stock_code(db, "same", "20220103") == "000001"
    with pytest.raises(ValueError, match="trade day"):
        materializer._stock_code(db, "same", "20220104")
    idx, ticks, _ = materializer._load_rows(db, "000001", "20220103")
    assert idx.tolist() == [20220103090000] and ticks[0, 0] == 0.0


def test_identity_projection_is_outcome_blind_and_endpoints_positive(tmp_path: Path) -> None:
    materializer = load()
    db = sqlite3.connect(tmp_path / "ticks.db")
    db.execute('CREATE TABLE "000001" ("index" INTEGER)')
    db.execute('INSERT INTO "000001" VALUES (20220103090000)')
    source = {"종목코드": "000001", "진입일자": "20220103", "매수시간": 20220103090000,
              "매도가": 999999, "매도시간": 20220103093000, "수익률": 999}
    projected = materializer._identity_rows([source], db)[0]
    assert set(projected) == {"code", "year", "day", "buy_timestamp", "ledger_ordinal"}
    with pytest.raises(ValueError, match="invalid sell_price"):
        materializer._ledger({"매수가": 100, "매수금액": 1000, "매도가": 0, "매도시간": 20220103090001}, "20220103", "20220103090000")
def test_authoritative_ledger_filters_only_valid_entry_days_and_preserves_source_ordinals() -> None:
    materializer = load()
    rows = (
        [{"진입일자": "20220103"} for _ in range(101)]
        + [{"진입일자": "20230103"} for _ in range(197)]
        + [{"진입일자": "20240103"} for _ in range(373)]
    )
    selected = materializer._authoritative_ledger(rows)
    assert len(selected) == 298
    assert [selected[index][0] for index in (0, 100, 101, 297)] == [0, 100, 101, 297]
    rows[-1] = {"진입일자": "20240230"}
    with pytest.raises(ValueError, match="entry day"):
        materializer._authoritative_ledger(rows)


def test_tick_authority_requires_one_external_physical_identity() -> None:
    materializer = load()
    sha = "a" * 64
    commitment = {
        "path": "C:/sealed/ticks.db",
        "sha256": sha,
        "size_bytes": 1,
        "physical_id": f"C:/sealed/ticks.db:1:{sha}",
    }
    assert materializer._tick_commitment(commitment, "test") == commitment
    with pytest.raises(ValueError, match="physical identity"):
        materializer._tick_commitment({**commitment, "sha256": "b" * 64}, "test")

@pytest.mark.parametrize("suffix", ("-wal", "-shm", "-journal"))
def test_sqlite_sidecars_fail_closed_before_read_or_artifact_consumption(tmp_path: Path, monkeypatch, suffix: str) -> None:
    materializer = load()
    db = tmp_path / "ticks.db"
    sqlite3.connect(db).close()
    db.with_name(db.name + suffix).write_bytes(b"uncommitted")
    monkeypatch.setattr(materializer.sqlite3, "connect", lambda *_args, **_kwargs: pytest.fail("SQLite connection opened despite sidecar"))
    with pytest.raises(ValueError, match="SQLite sidecar"):
        materializer.open_readonly(db)
    with pytest.raises(ValueError, match="SQLite sidecar"):
        materializer._reject_sqlite_sidecars(db)


def test_sqlite_sidecar_created_after_read_is_rejected_before_commitment(tmp_path: Path) -> None:
    materializer = load()
    db = tmp_path / "ticks.db"
    sqlite3.connect(db).close()
    with materializer.open_readonly(db) as conn:
        assert conn.execute("PRAGMA query_only").fetchone()[0] == 1
    db.with_name(db.name + "-wal").write_bytes(b"uncommitted")
    with pytest.raises(ValueError, match="SQLite sidecar"):
        materializer._reject_sqlite_sidecars(db)

def test_producer_uses_the_full_consumer_shape_validator() -> None:
    materializer = load()
    with pytest.raises(ValueError):
        materializer._validate_snapshot({"contract": materializer.CONTRACT, "events": [], "flow": {"engine_rows": 298}})
def test_measurement_target_drift_is_rejected_before_validator_import(monkeypatch) -> None:
    materializer = load()
    target = materializer._measurement_target()
    assert target["path"] == "scripts/u7_f0_frame_measure.py"
    with pytest.raises(ValueError, match="measurement target bytes disagree"):
        materializer._measurement_target("0" * 64)
    monkeypatch.setattr(materializer.importlib.util, "spec_from_file_location", lambda *_args: pytest.fail("alternate validator import attempted"))
    with pytest.raises(ValueError, match="measurement target bytes disagree"):
        materializer._validate_snapshot({"provenance": {"measurement_target": {**target, "sha256": "0" * 64}}})


def test_canonical_layout_and_launch_prereg_bindings(tmp_path: Path) -> None:
    materializer = load()
    assert materializer.CANONICAL["authority"] == materializer.G002_DIR / "source_authority.json"
    assert materializer.CANONICAL["launch"] == materializer.G002_DIR / "materialization_launch.json"
    assert materializer.CANONICAL["output"] == materializer.G002_DIR / "u7_f0_materialized_input.json"
    assert materializer.CANONICAL["prereg"] == materializer.ROOT / "docs/research/condition_research/plans/2026-07-16_g002_u7_f0_preregistration.md"
    parser = __import__("argparse").Namespace(
        evidence=materializer.CANONICAL["authority"], design_marker=materializer.CANONICAL["design"],
        identity_input=materializer.CANONICAL["crosswalk"], output=tmp_path / "output.json",
        attempt=tmp_path / "attempt.json", status=tmp_path / "status.json")
    with pytest.raises(ValueError, match="canonical G002 path"):
        materializer._check_paths(parser, identity=False)
    parser.evidence = materializer.CANONICAL["launch"]
    parser.output, parser.attempt, parser.status = (materializer.CANONICAL[key] for key in ("output", "attempt", "status"))
    materializer._check_paths(parser, identity=False)
    source = (materializer.CANONICAL["prereg"], materializer.CANONICAL["launch"])
    assert "preregistration_sha256" in __import__("inspect").getsource(materializer._provenance)
    assert source == (materializer.CANONICAL["prereg"], materializer.CANONICAL["launch"])
def _authority_with_source(materializer, source: dict[str, object]) -> dict[str, object]:
    sha = "a" * 64
    sources = {
        key: {"path": f"artifacts/{key}", "sha256": sha, "size_bytes": 1}
        for key in materializer.SOURCES
    }
    for key in ("onset_l3_bank", "d1_onset_clause_bits"):
        sources[key].update({"arrow_schema_sha256": sha, "row_groups": 1, "row_count": 1})
    sources["onset_l3_bank"] = source
    tick = {"path": "C:/sealed/ticks.db", "sha256": sha, "size_bytes": 1, "physical_id": f"C:/sealed/ticks.db:1:{sha}"}
    return {
        "schema": "u7-f0-source-authority-v3",
        "state": "sealed",
        "experiment_id": materializer.EXPERIMENT_ID,
        "attempt_id": materializer.ATTEMPT_ID,
        "identity_attempt_id": materializer.IDENTITY_ATTEMPT_ID,
        "preregistration_sha256": sha,
        "materializer_sha256": sha,
        "measurement_sha256": sha,
        "sources": sources,
        "semantic_receipts": {key: {} for key in ("p5_receipt", "equivalence_receipt", "champion_passport", "sell_expression")},
        "tick_db": tick,
    }


def test_external_read_path_is_authoritative_only_and_stripped_from_consumer_descriptor(tmp_path: Path) -> None:
    materializer = load()
    external = tmp_path / "onset_l3_bank.parquet"
    external.write_bytes(b"sealed external source")
    source = {
        "path": "alpha_lab/catalog/onset_l3_bank.parquet",
        "read_path": external.as_posix(),
        "sha256": "a" * 64,
        "size_bytes": 1,
        "arrow_schema_sha256": "a" * 64,
        "row_groups": 1,
        "row_count": 1,
    }
    materializer._validate_authority(_authority_with_source(materializer, source))
    assert materializer._authority_source_path(source) == external
    descriptor = materializer._artifact(materializer._authority_source_path(source), canonical=source["path"])
    assert descriptor["path"] == source["path"]
    assert "read_path" not in descriptor
    physical = {"onset_l3_bank": {"pre": {"sha256": descriptor["sha256"], "size_bytes": descriptor["size_bytes"], "physical_id": materializer._physical(descriptor)}, "post": None}}
    materializer._seal_post(physical, {"onset_l3_bank": (materializer._authority_source_path(source), descriptor)})
    assert physical["onset_l3_bank"]["post"] == physical["onset_l3_bank"]["pre"]
    assert external.as_posix() not in physical["onset_l3_bank"]["post"]["physical_id"]
    frame_spec = importlib.util.spec_from_file_location("g002_frame_consumer_test", ROOT / "scripts/u7_f0_frame_measure.py")
    frame = importlib.util.module_from_spec(frame_spec)
    assert frame_spec and frame_spec.loader
    frame_spec.loader.exec_module(frame)
    assert frame._artifact(descriptor, "provenance.sources.onset_l3_bank") == descriptor


@pytest.mark.parametrize("read_path", ("relative/onset_l3_bank.parquet", r"C:\sealed\onset_l3_bank.parquet"))
def test_authority_rejects_relative_or_backslash_ambiguous_read_path(read_path: str) -> None:
    materializer = load()
    source = {
        "path": "alpha_lab/catalog/onset_l3_bank.parquet",
        "read_path": read_path,
        "sha256": "a" * 64,
        "size_bytes": 1,
        "arrow_schema_sha256": "a" * 64,
        "row_groups": 1,
        "row_count": 1,
    }
    with pytest.raises(ValueError, match="read_path"):
        materializer._validate_authority(_authority_with_source(materializer, source))


def test_authority_rejects_extra_read_path_field() -> None:
    materializer = load()
    source = {
        "path": "alpha_lab/catalog/onset_l3_bank.parquet",
        "read_path": "C:/sealed/onset_l3_bank.parquet",
        "read_path_hint": "forbidden",
        "sha256": "a" * 64,
        "size_bytes": 1,
        "arrow_schema_sha256": "a" * 64,
        "row_groups": 1,
        "row_count": 1,
    }
    with pytest.raises(ValueError, match="source descriptor"):
        materializer._validate_authority(_authority_with_source(materializer, source))
def test_identity_preflight_captures_authority_before_reservation_or_ledger_reads() -> None:
    materializer = load()
    source = __import__("inspect").getsource(materializer.main)
    assert materializer.IDENTITY_ATTEMPT_ID
    assert materializer.CANONICAL["identity_attempt"].name == "identity_attempt.json"
    assert materializer.CANONICAL["identity_status"].name == "identity_status.json"
    assert source.index("_provenance(") < source.index("_reserve_identity()") < source.index("_records(")
    assert "identity attempt/status/crosswalk/design is immutable" in source
    assert "identity_attempt_id" in __import__("inspect").getsource(materializer._validate_authority)


def test_identity_status_is_no_clobber_after_a_failed_identity_attempt(tmp_path: Path, monkeypatch) -> None:
    materializer = load()
    monkeypatch.setitem(materializer.CANONICAL, "identity_attempt", tmp_path / "identity_attempt.json")
    monkeypatch.setitem(materializer.CANONICAL, "identity_status", tmp_path / "identity_status.json")
    materializer._reserve_identity()
    materializer._identity_status("failed")
    with pytest.raises(FileExistsError):
        materializer._reserve_identity()
    with pytest.raises(FileExistsError):
        materializer._identity_status("succeeded")
    assert materializer._read_json(materializer.CANONICAL["identity_status"], "identity status")["state"] == "failed"
@pytest.mark.parametrize("after_ledger_parse", (False, True))
def test_identity_failures_after_authority_capture_consume_the_attempt(tmp_path: Path, monkeypatch, after_ledger_parse: bool) -> None:
    materializer = load()
    monkeypatch.setitem(materializer.CANONICAL, "identity_attempt", tmp_path / "identity_attempt.json")
    monkeypatch.setitem(materializer.CANONICAL, "identity_status", tmp_path / "identity_status.json")
    monkeypatch.setattr(materializer, "_check_paths", lambda *_args, **_kwargs: None)
    read_json = materializer._read_json
    monkeypatch.setattr(materializer, "_read_json", lambda path, label: {} if label == "materialization launch" else read_json(path, label))
    if after_ledger_parse:
        monkeypatch.setattr(materializer, "_provenance", lambda *_args: ({}, {}))
        monkeypatch.setattr(materializer, "_records", lambda *_args: [])
        monkeypatch.setattr(materializer, "_authoritative_ledger", lambda *_args: (_ for _ in ()).throw(ValueError("after ledger parse")))
    else:
        monkeypatch.setattr(materializer, "_provenance", lambda *_args: (_ for _ in ()).throw(ValueError("before reservation")))
    argv = ["u7", "--identity-only", "--ledger", str(tmp_path / "ledger.json"), "--l3", str(tmp_path / "l3.parquet"), "--d1-bits", str(tmp_path / "d1.parquet"), "--tick-db", str(tmp_path / "ticks.db"), "--evidence", str(tmp_path / "launch.json"), "--identity-output", str(tmp_path / "crosswalk.json"), "--design-marker", str(tmp_path / "design.json")]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(ValueError):
        materializer.main()
    if after_ledger_parse:
        assert materializer._read_json(materializer.CANONICAL["identity_attempt"], "attempt")["identity_attempt_id"] == materializer.IDENTITY_ATTEMPT_ID
        assert materializer._read_json(materializer.CANONICAL["identity_status"], "status")["state"] == "failed"
        with pytest.raises(ValueError, match="immutable"):
            materializer.main()
    else:
        assert not materializer.CANONICAL["identity_attempt"].exists()
        assert not materializer.CANONICAL["identity_status"].exists()
def test_cells_seal_forced_and_non_forced_clause_domains() -> None:
    materializer = load()
    raw = {name: {"entry": {"quantity": 1, "price": 100.0}, "exit": {"price": 101.0, "time": "20220103090100", "forced": False}, "cause": {"kind": "sell_clause", "clause": 17}} for name in materializer.CELL_NAMES}
    assert {cell["clause"] for cell in materializer._cells(raw, "20220103090000").values()} == {17}
    for clause in (0, True, 1.0):
        raw["E0D0T0"]["cause"]["clause"] = clause
        with pytest.raises(ValueError, match="positive integer"):
            materializer._cells(raw, "20220103090000")
    raw["E0D0T0"]["exit"]["forced"] = True
    raw["E0D0T0"]["cause"] = {"kind": "cap", "clause": None}
    assert materializer._cells(raw, "20220103090000")["E0D0T0"]["clause"] == 0
    raw["E0D0T0"]["cause"]["clause"] = 17
    with pytest.raises(ValueError, match="clause 0"):
        materializer._cells(raw, "20220103090000")
def test_cells_bind_buy_time_and_enforce_factor_horizons() -> None:
    materializer = load()
    raw = {name: {"entry": {"quantity": 1, "price": 100.0}, "exit": {"price": 101.0, "time": "20220103092800", "forced": False}, "cause": {"kind": "sell_clause", "clause": 17}} for name in materializer.CELL_NAMES}
    cells = materializer._cells(raw, "20220103090000")
    assert all(cell["entry_time"] == "20220103090000" for cell in cells.values())
    raw["E0D0T1"]["exit"]["time"] = "20220103092801"
    with pytest.raises(ValueError, match="sealed horizon"):
        materializer._cells(raw, "20220103090000")
    raw["E0D0T1"]["exit"]["time"] = "20220103092800"
    raw["E0D0T0"]["exit"]["time"] = "20220103093001"
    with pytest.raises(ValueError, match="sealed horizon"):
        materializer._cells(raw, "20220103090000")
def test_seal_post_accepts_full_tick_descriptor(tmp_path: Path) -> None:
    materializer = load()
    tick = tmp_path / "ticks.db"
    tick.write_bytes(b"sealed")
    descriptor = materializer._artifact(tick, canonical=str(tick.resolve()))
    physical = {"tick_db": {"pre": {"sha256": descriptor["sha256"], "size_bytes": descriptor["size_bytes"], "physical_id": materializer._physical(descriptor)}, "post": None}}
    materializer._seal_post(physical, {"tick_db": (tick, descriptor)})
    assert physical["tick_db"]["post"] == physical["tick_db"]["pre"]
def test_identity_closure_fixture_is_satisfiable_and_rejects_tick_custody_drift() -> None:
    materializer = load()
    sha = "a" * 64
    def descriptor(path: str) -> dict[str, object]:
        return {"path": path, "sha256": sha, "size_bytes": 1}
    source_names = materializer.SOURCES
    physical = {key: materializer._sealed_physical(descriptor(f"artifacts/{key}")) for key in source_names + ("source_authority", "preregistration", "launch", "materializer", "measurement_target", "tick_db")}
    physical["tick_db"] = materializer._sealed_physical(descriptor("C:/sealed/ticks.db"))
    tick = {"path": "C:/sealed/ticks.db", "sha256": sha, "size_bytes": 1, "physical_id": f"C:/sealed/ticks.db:1:{sha}", "read_only": True, "query_only": True, "pre": physical["tick_db"]["pre"], "post": physical["tick_db"]["pre"]}
    provenance = {"physical_inputs": {key: {"pre": value["pre"], "post": None} for key, value in physical.items()}, "tick_db": {**tick, "post": None}, "source_authority": descriptor("artifacts/source_authority"), "preregistration": descriptor("artifacts/preregistration"), "materializer": descriptor("scripts/u7_f0_materialize.py"), "measurement_target": descriptor("scripts/u7_f0_frame_measure.py")}
    authority_sources = {key: {"arrow_schema_sha256": sha, "row_groups": 1, "row_count": 1} if key in ("onset_l3_bank", "d1_onset_clause_bits") else {} for key in source_names}
    crosswalk_artifact = descriptor("C:/sealed/identity_crosswalk.json")
    custody = {"physical_inputs": physical, "arrow_metadata": materializer._arrow_metadata(authority_sources), "tick_db": tick}
    events = []
    for year, count, offset in ((2022, 101, 0), (2023, 197, 101)):
        for number in range(count):
            day = (__import__("datetime").date(year, 1, 1) + __import__("datetime").timedelta(days=number)).strftime("%Y%m%d")
            events.append({"identity": {"code": f"{number + offset:06d}", "year": year, "day": day, "buy_time": day + "090000"}, "ledger_ordinal": number + offset, "branch": None, "match_status": "engine_only"})
    crosswalk = {"schema": "u7-f0-identity-crosswalk-v2", "experiment_id": materializer.EXPERIMENT_ID, "attempt_id": materializer.ATTEMPT_ID, "identity_attempt_id": materializer.IDENTITY_ATTEMPT_ID, "events": events, "source_custody": custody}
    marker = {"schema": "u7-f0-identity-design-marker-v2", "experiment_id": materializer.EXPERIMENT_ID, "attempt_id": materializer.ATTEMPT_ID, "identity_attempt_id": materializer.IDENTITY_ATTEMPT_ID, "full_attempt_id": materializer.ATTEMPT_ID, "state": "sealed", "crosswalk_sha256": sha, "source_authority_sha256": sha, "preregistration_sha256": sha, "materializer_sha256": sha, "measurement_sha256": sha, "tick_db": tick, "source_custody": {**custody, "physical_inputs": {**physical, "identity_crosswalk": materializer._sealed_physical(crosswalk_artifact)}}}
    materializer._validate_identity_closure(crosswalk, marker, provenance, crosswalk_artifact, authority_sources)
    crosswalk["events"] = []
    with pytest.raises(ValueError, match="crosswalk universe"):
        materializer._validate_identity_closure(crosswalk, marker, provenance, crosswalk_artifact, authority_sources)
    crosswalk["events"] = events
    marker["source_custody"]["tick_db"] = {**tick, "physical_id": "forged"}
    with pytest.raises(ValueError, match="source custody closure"):
        materializer._validate_identity_closure(crosswalk, marker, provenance, crosswalk_artifact, authority_sources)


def test_projected_join_ambiguity_is_not_silently_collapsed() -> None:
    materializer = load()
    source = __import__("inspect").getsource(materializer.build_snapshot)
    assert "ambiguous projected (code, day, t0+1) join" in source
    assert "fields=None" not in source
def test_actual_sealed_p5_receipt_passes() -> None:
    materializer = load()
    receipt = materializer.ROOT / "docs/research/condition_research/research_runs/alpha_lab_20260705/distill/p5_phase0_receipt.json"
    materializer._p5_receipt(materializer._read_json(receipt, "actual P5 receipt"))


def test_type_specific_semantic_receipt_validators(tmp_path: Path, monkeypatch) -> None:
    materializer = load()
    p5 = {
        "program": "P5", "phase": "phase0_champion_ledger_wiring", "unique": 671,
        "ledger_records": 671, "ledger_schema_version": 1, "source_csv_access": "read-only",
        "champion_condition_id": materializer.CHAMPION_CONDITION_ID, "champion_buy_strategy_id": materializer.CHAMPION_BUY_STRATEGY_ID,
        "ledger_path": materializer.CANONICAL_LEDGER_PATH, "identity_fields": materializer.P5_IDENTITY_FIELDS,
        "dedup_policy": "first-wins, scan order = filename ascending (earliest run wins)",
        "sources": [
            {"path": "stock_bt_GATE_20260628014938.csv", "source": "GATE_rr8_12_turnover_min_902_1_5_B", "rows": 190, "kept": 190, "dropped": 0, "buy_time_digit_hist": {"14": 190}, "entry_day_range": ["20250103", "20251230"]},
            {"path": "stock_bt_GATE_20260628094538.csv", "source": "GATE_rr8_12_turnover_min_902_1_5_B", "rows": 101, "kept": 101, "dropped": 0, "buy_time_digit_hist": {"14": 101}, "entry_day_range": ["20220323", "20221222"]},
            {"path": "stock_bt_GATE_20260628095000.csv", "source": "GATE_rr8_12_turnover_min_902_1_5_B", "rows": 197, "kept": 197, "dropped": 0, "buy_time_digit_hist": {"14": 197}, "entry_day_range": ["20230102", "20231219"]},
            {"path": "stock_bt_GATE_cross_year.csv", "source": "GATE_rr8_12_turnover_min_902_1_5_B", "rows": 298, "kept": 298, "dropped": 0, "buy_time_digit_hist": {"14": 298}, "entry_day_range": ["20221230", "20230103"]},
        ],
    }
    equivalence = {
        "kind": "v2_labeler_equivalence", "generated": "2026-07-06T14:05:35.473320",
        "sealed_threshold": .999, "compare_basis": "replay.replay_champion_exit (P5 재현게이트 검증 스칼라)",
        "n_ledger_rows": 671, "n_trades": 667, "n_time_match": 667, "n_price_match": 667,
        "n_both_match": 667, "exclusions": {"foreign_sell_condition": 4}, "cond_match_rate": 1.0,
        "equivalence_pct": 100.0, "gate_pass": True, "mismatches": [],
    }
    materializer._p5_receipt(p5)
    materializer._equivalence_receipt(equivalence)
    with pytest.raises(ValueError, match="P5"):
        materializer._p5_receipt({**p5, "source_csv_access": "write"})
    with pytest.raises(ValueError, match="P5"):
        materializer._p5_receipt({**p5, "champion_condition_id": "other"})
    with pytest.raises(ValueError, match="equivalence"):
        materializer._equivalence_receipt({**equivalence, "mismatches": [{"bad": True}]})
    passport = tmp_path / "passport.md"
    passport.write_text(
        f"| field | value |\n| --- | --- |\n| sell_code_sha256 | `{materializer.SELL_CODE_SHA256}` |\n",
        encoding="utf-8",
    )
    materializer._passport(passport)
    expression = tmp_path / "sell.txt"
    expression.write_text("raw expression", encoding="utf-8")
    monkeypatch.setattr(materializer, "_sha256", lambda _path: materializer.SELL_CODE_SHA256)
    materializer._sell_expression(expression)
    with pytest.raises(ValueError, match="passport"):
        passport.write_text(f"| sell_code_sha256 | {materializer.SELL_CODE_SHA256} |", encoding="utf-8")
        materializer._passport(passport)
    with pytest.raises(ValueError, match="P5"):
        materializer._p5_receipt({**p5, "sources": [p5["sources"][0], {**p5["sources"][1], "dropped": 1}, p5["sources"][2]]})
def test_evaluator_cells_mark_d0_and_d1_cap_liquidations_forced(monkeypatch) -> None:
    materializer = load()
    factorial = sys.modules["alpha_lab.distill.factorial"]
    monkeypatch.setattr(factorial, "_eval_sell_clauses", lambda *_args, **_kwargs: None)
    ci = {name: index for index, name in enumerate(materializer.TICK_COLUMNS[1:])}
    idxs = np.array([20220103090000, 20220103090100, 20220103092800, 20220103093000], dtype=np.int64)
    arr = np.zeros((len(idxs), len(ci)), dtype=np.float64)
    for name, value in {"현재가": 100, "시가": 100, "매도호가1": 100, "매수호가1": 100, "매수호가2": 99, "매수호가3": 98, "매수잔량1": 100_000, "매수잔량2": 100_000, "매수잔량3": 100_000}.items():
        arr[:, ci[name]] = value
    raw = materializer.evaluate_event(
        {"매수시간": int(idxs[0]), "매수가": 100, "매수금액": 1000},
        idxs, arr, ci, {}, branch="902",
    )
    cells = materializer._cells(raw["cells"], str(int(idxs[0])))
    for name in ("E0D0T0", "E0D1T0", "E1D0T0", "E1D1T0"):
        assert cells[name]["status"] == "matched"
        assert cells[name]["forced"] is True
        assert cells[name]["clause"] == 0
    assert raw["cells"]["E0D1T0"]["exit"]["method"] == "bid1_bid3_ladder"
    arr[:, ci["매수잔량1"]] = 0
    arr[:, ci["매수잔량2"]] = 0
    arr[:, ci["매수잔량3"]] = 0
    exit_i, fill, _cause = factorial._capped_exit(
        idxs, arr, ci, {}, buy_i=0, buy_price=100, qty=10, depth="D1", day=20220103,
    )
    assert exit_i is None and fill is None


def test_mixed_cell_exclusion_canonicalizes_all_cells_without_losing_event_context(monkeypatch) -> None:
    materializer = load()
    ledger, l3 = [], []
    for ordinal in range(298):
        year = 2022 if ordinal < 101 else 2023
        day = f"{year}0103"
        code = f"{ordinal:06d}"
        buy = f"{day}090000"
        ledger.append({"code": code, "year": year, "day": day, "buy_timestamp": buy, "buy_price": 100, "buy_amount": 1000, "sell_price": 101, "sell_timestamp": f"{day}090100"})
        l3.append({"code": code, "day": day, "t0": f"{day}085959", "branch": 902, "l3_net": 0.01, "l3_exit": "retained", "l3_clause": 17})
    raw = {name: {"entry": {"quantity": 1, "price": 100.0}, "exit": {"price": 101.0, "time": "20220103090100", "forced": False}, "cause": {"kind": "sell_clause", "clause": 17}} for name in materializer.CELL_NAMES}
    raw["E0D1T0"] = {"entry": {"quantity": 1, "price": 100.0}, "exit": {"price": 0.0, "time": None}, "cause": {"kind": "cap", "reason": "no_valid_exit"}}
    monkeypatch.setattr(materializer, "_load_rows", lambda *_args: (np.array([20220103090000]), np.zeros((1, 1)), {}))
    monkeypatch.setattr(materializer, "precompute_windows", lambda *_args: {})
    monkeypatch.setattr(materializer, "evaluate_event", lambda *_args, **_kwargs: {"cells": raw})
    snapshot = materializer.build_snapshot(ledger, l3, sqlite3.connect(":memory:"), provenance={})
    event = snapshot["events"][0]
    assert event["status"] == "excluded"
    assert event["reason"] == "factorial_cell_unavailable"
    assert event["branch"] == 902 and event["l3_net_ref"] == 0.01 and event["ledger"]["sell_price"] == 101
    assert all(cell == materializer._missing("factorial_cell_unavailable")[name] for name, cell in event["cells"].items())
def test_full_preflight_finishes_before_reservation_and_outcome_reads() -> None:
    materializer = load()
    source = __import__("inspect").getsource(materializer.main)
    full_mode = source[source.index('if any(getattr(args,x) is None for x in ("output","attempt","status","identity_input","design_marker"))'):]
    reserve = full_mode.index("attempt=_reserve()")
    assert full_mode.index("provenance,source_read_paths=_provenance(") < reserve
    assert full_mode.index("crosswalk,crosswalk_artifact=_capture_json(") < reserve
    assert full_mode.index("_validate_identity_closure(") < reserve < full_mode.index("_records(")
    assert "authority=_read_json(CANONICAL[\"authority\"]" not in full_mode

def test_capture_json_hashes_and_parses_one_payload_without_artifact_recapture(tmp_path: Path) -> None:
    materializer = load()
    payload = b'{"state":"sealed"}'
    path = tmp_path / "sealed.json"
    path.write_bytes(payload)
    value, descriptor = materializer._capture_json(path, "sealed", canonical="sealed.json")
    assert value == {"state": "sealed"}
    assert descriptor == {"path": "sealed.json", "sha256": __import__("hashlib").sha256(payload).hexdigest(), "size_bytes": len(payload)}
    assert "_artifact(path" not in __import__("inspect").getsource(materializer._capture_json)

@pytest.mark.parametrize("path", ("docs/research/source.json", "alpha_lab/catalog/input.parquet"))
def test_producer_accepted_source_paths_are_canonical(path: str) -> None:
    materializer = load()
    assert materializer._canonical_project_path(path) == path

@pytest.mark.parametrize("path", ("/sealed/input.json", "C:/sealed/input.json", r"C:\sealed\input.json", r"docs\source.json", "docs/../source.json", "./source.json", "docs//source.json", "docs/source.json/"))
def test_producer_rejects_noncanonical_source_paths(path: str) -> None:
    materializer = load()
    with pytest.raises(ValueError):
        materializer._canonical_project_path(path)
@pytest.mark.parametrize("stage", ("marker_or_crosswalk", "provenance", "identity_closure"))
def test_malformed_full_preflight_never_consumes_attempt_or_writes_status_or_output(tmp_path: Path, monkeypatch, stage: str) -> None:
    materializer = load()
    for key, payload in (
        ("identity_attempt", b'{"schema":"u7-f0-identity-attempt-v1","experiment_id":"alpha_restart_20260710-g002","identity_attempt_id":"alpha_restart_20260710-g002-identity-attempt-001","state":"reserved"}'),
        ("identity_status", b'{"schema":"u7-f0-identity-status-v1","experiment_id":"alpha_restart_20260710-g002","identity_attempt_id":"alpha_restart_20260710-g002-identity-attempt-001","state":"succeeded"}'),
    ):
        path = tmp_path / f"{key}.json"
        path.write_bytes(payload)
        monkeypatch.setitem(materializer.CANONICAL, key, path)
    output, attempt, status = (tmp_path / name for name in ("output.json", "attempt.json", "status.json"))
    monkeypatch.setattr(materializer, "_check_paths", lambda *_args, **_kwargs: None)
    descriptor = {"path": "sealed.json", "sha256": "a" * 64, "size_bytes": 1}
    if stage == "marker_or_crosswalk":
        monkeypatch.setattr(materializer, "_capture_json", lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("malformed prerequisite")))
    elif stage == "provenance":
        monkeypatch.setattr(materializer, "_capture_json", lambda *_args, **_kwargs: ({}, descriptor))
        monkeypatch.setattr(materializer, "_provenance", lambda *_args: (_ for _ in ()).throw(ValueError("malformed prerequisite")))
    else:
        monkeypatch.setattr(materializer, "_capture_json", lambda *_args, **_kwargs: ({}, descriptor))
        monkeypatch.setattr(materializer, "_provenance", lambda *_args: ({"sources": {}}, {}))
        monkeypatch.setattr(materializer, "_validate_identity_closure", lambda *_args: (_ for _ in ()).throw(ValueError("malformed prerequisite")))
    monkeypatch.setattr(sys, "argv", ["u7", "--ledger", str(tmp_path / "ledger.json"), "--l3", str(tmp_path / "l3.parquet"), "--d1-bits", str(tmp_path / "d1.parquet"), "--tick-db", str(tmp_path / "ticks.db"), "--output", str(output), "--attempt", str(attempt), "--status", str(status), "--evidence", str(tmp_path / "launch.json"), "--identity-input", str(tmp_path / "crosswalk.json"), "--design-marker", str(tmp_path / "design.json")])
    with pytest.raises(ValueError, match="malformed prerequisite"):
        materializer.main()
    assert not output.exists() and not attempt.exists() and not status.exists()
def test_malformed_crosswalk_main_preflight_does_not_consume_attempt(tmp_path: Path, monkeypatch) -> None:
    materializer = load()
    monkeypatch.setattr(materializer, "_check_paths", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(materializer, "_reject_sqlite_sidecars", lambda *_args: None)
    for key, state in (("identity_attempt", "reserved"), ("identity_status", "succeeded")):
        path = tmp_path / f"{key}.json"
        materializer._exclusive_json(path, {"schema": f"u7-f0-identity-{'attempt' if key.endswith('attempt') else 'status'}-v1", "experiment_id": materializer.EXPERIMENT_ID, "identity_attempt_id": materializer.IDENTITY_ATTEMPT_ID, "state": state})
        monkeypatch.setitem(materializer.CANONICAL, key, path)
    output, attempt, status = (tmp_path / name for name in ("output.json", "attempt.json", "status.json"))
    descriptor = {"path": "sealed", "sha256": "a" * 64, "size_bytes": 1}
    malformed = {"schema": "u7-f0-identity-crosswalk-v2", "experiment_id": materializer.EXPERIMENT_ID, "attempt_id": materializer.ATTEMPT_ID, "identity_attempt_id": materializer.IDENTITY_ATTEMPT_ID, "events": [], "source_custody": {}}
    monkeypatch.setattr(materializer, "_capture_json", lambda *_args, **_kwargs: (malformed, descriptor))
    monkeypatch.setattr(materializer, "_provenance", lambda *_args: ({"sources": {}}, {}))
    def validate(crosswalk, *_args):
        if not isinstance(crosswalk["events"], list) or len(crosswalk["events"]) != 298:
            raise ValueError("full mode crosswalk universe is invalid")
    monkeypatch.setattr(materializer, "_validate_identity_closure", validate)
    monkeypatch.setattr(sys, "argv", ["u7", "--ledger", str(tmp_path / "ledger.json"), "--l3", str(tmp_path / "l3.parquet"), "--d1-bits", str(tmp_path / "d1.parquet"), "--tick-db", str(tmp_path / "ticks.db"), "--output", str(output), "--attempt", str(attempt), "--status", str(status), "--evidence", str(tmp_path / "launch.json"), "--identity-input", str(tmp_path / "crosswalk.json"), "--design-marker", str(tmp_path / "design.json")])
    with pytest.raises(ValueError, match="crosswalk universe"):
        materializer.main()
    assert not output.exists() and not attempt.exists() and not status.exists()
