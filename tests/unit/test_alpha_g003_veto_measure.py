import importlib.util
import json
from pathlib import Path

from alpha_lab.discipline import prereg

ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "alpha_lab" / "distill" / "g003_veto_measure.py"
SNAPSHOT = ROOT / "docs/research/condition_research/research_runs/alpha_restart_20260710/g003/g003_veto_input.json"
INPUT_PATH = "docs/research/condition_research/research_runs/alpha_restart_20260710/g003/g003_veto_input.json"
LEDGER_PATH = "docs/research/condition_research/research_runs/alpha_lab_20260705/distill/champion_ledger.jsonl"


def module():
    spec = importlib.util.spec_from_file_location("g003_veto_measure", SOURCE)
    result = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(result)
    return result


def valid(pnl=-1, masked=True):
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    trades = snapshot["trades"]
    if not masked:
        trades = [{**trade, "o3_mask": False, "o4_mask": False, "union_mask": False,
                   "deep_anchor_overlap": False} for trade in trades]
        snapshot = {**snapshot, "trades": trades}
    ledger = tuple({"진입일자": trade["entry_day"], "진입시각": trade["buy_second"],
                    "매수시간": float(trade["entry_day"] + trade["buy_second"]),
                    "매도시간": float(trade["sell_day"] + trade["sell_second"]),
                    "매수금액": trade["notional"], "수익금": pnl}
                   for trade in trades)
    prefix = tuple({"진입일자": "20210101", "진입시각": "000000",
                    "매수시간": 20210101000000.0, "매도시간": 20210101000000.0,
                    "매수금액": 1, "수익금": 0} for index in range(trades[0]["trade_id"]))
    return snapshot, prefix + ledger


def test_import_is_data_free_and_source_has_no_assert(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    module()
    assert "assert" not in SOURCE.read_text(encoding="utf-8")


def test_valid_zero_drop_is_fail_and_negative_drops_pass():
    target = module()
    zero_snapshot, zero_ledger = valid(masked=False)
    assert target.measure(zero_snapshot, zero_ledger)["verdict"] == "FAIL"
    snapshot, ledger = valid()
    assert target.measure(snapshot, ledger)["verdict"] == "PASS"
    ignored_2024 = (*ledger, {"진입일자": "20240101"})
    assert target.measure(snapshot, ignored_2024) == target.measure(snapshot, ledger)


def test_forged_source_refs_and_scalars_are_insufficient():
    target = module()
    snapshot, ledger = valid()
    forged = {**snapshot, "sources": {**snapshot["sources"], "ledger": {**snapshot["sources"]["ledger"], "size": 1}}}
    assert target.measure(forged, ledger)["integrity_reasons"] == ("source_refs",)
    forged_flow = {**snapshot, "row_flow": {**snapshot["row_flow"], "o3_rows": 1}}
    assert target.measure(forged_flow, ledger)["integrity_reasons"] == ("row_flow",)
    missing_contract = {**snapshot, "contract": {"o4_evaluation_scope": "o4_onset_carrier_only"}}
    assert target.measure(missing_contract, ledger)["integrity_reasons"] == ("provenance",)
    malformed_id = {**snapshot, "trades": [{**snapshot["trades"][0], "trade_id": []}, *snapshot["trades"][1:]]}
    assert target.measure(malformed_id, ledger)["verdict"] == "INSUFFICIENT"
    scoped_index = snapshot["trades"][0]["trade_id"]
    bad_timestamp = (*ledger[:scoped_index], {**ledger[scoped_index], "매수시간": "bad"}, *ledger[scoped_index + 1:])
    assert target.measure(snapshot, bad_timestamp)["integrity_reasons"] == ("identity",)
    notional_mismatch = (*ledger[:scoped_index], {**ledger[scoped_index], "매수금액": ledger[scoped_index]["매수금액"] + 1}, *ledger[scoped_index + 1:])
    assert target.measure(snapshot, notional_mismatch)["integrity_reasons"] == ("identity",)


def test_target_derives_with_declared_inputs(tmp_path):
    source = tmp_path / "alpha_lab/distill/g003_veto_measure.py"
    source.parent.mkdir(parents=True)
    source.write_text(SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
    paths = tuple(sorted((INPUT_PATH, LEDGER_PATH)))
    for path in paths:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{}\n", encoding="utf-8")
    for directory in ("seals", "promotions", "catalog", "journal", "backups"):
        (tmp_path / directory).mkdir()
    contract = {"schema_version": 2, "hypothesis_id": "G003", "discovery_window": {"start": "2022-03-23", "end": "2023-12-31"}, "primary_estimand": "static veto", "sample_floors": {"n": 1}, "multiplicity_family": "G003", "kill_rule": "fail", "ledger_path": "ledger.jsonl", "authority_paths": {"seal_dir": "seals", "promotions_dir": "promotions", "catalog_dir": "catalog", "target_db": "alpha_lab/distill/g003_veto_measure.py", "journal_dir": "journal", "backup_dir": "backups"}, "dependency_roots": ["alpha_lab/distill/g003_veto_measure.py"], "dynamic_python_dependencies": [], "non_python_dependencies": list(paths)}
    document = tmp_path / "prereg.md"
    document.write_text("> 지위: **SEALED**\n```json prereg-contract-v2\n" + json.dumps(contract) + "\n```\n", encoding="utf-8")
    assert prereg.derive_prereg_code_manifest(document.read_text(encoding="utf-8"), tmp_path) == {"alpha_lab/distill/g003_veto_measure.py", *paths}
