import argparse
import importlib.util
import json
from pathlib import Path

import pytest

pa = pytest.importorskip("pyarrow")
pq = pytest.importorskip("pyarrow.parquet")

SCRIPT = Path(__file__).parents[2] / "scripts" / "build_g003_veto_inputs.py"
spec = importlib.util.spec_from_file_location("build_g003_veto_inputs", SCRIPT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def parquet(path, rows):
    pq.write_table(pa.Table.from_pylist(rows), path)


def args(root):
    names = {"ledger": "ledger.jsonl", "o3_summary": "o3.json", "o4_summary": "o4.json",
             "o3_parquet": "o3.parquet", "o4_parquet": "o4.parquet", "d1_parquet": "d1.parquet",
             "p3_chunk1": "p3a.json", "p3_chunk2": "p3b.json", "output": "output.json"}
    return argparse.Namespace(**{name: str(root / filename) for name, filename in names.items()})


def make_inputs(root):
    root.mkdir(parents=True)
    a = args(root)
    dump(Path(a.o3_summary), {"judgment": {"variant_kill_units": sorted(mod.O3_UNITS)}})
    candidates = sorted(mod._expected_o4_cids())
    per_candidate = {cid: {"bits": list(mod._candidate_bits(mod._candidate_slots(cid))), "classification": "no_positive_ev"} for cid in candidates}
    dump(Path(a.o4_summary), {"qualification": {"qualified_cids": candidates}, "judgment": {
        "no_positive_ev_cids": candidates, "survive_cids": [], "weak_signal_cids": [], "n_survive": 0,
        "per_candidate": per_candidate,
    }})
    Path(a.ledger).write_text(
        json.dumps({"종목코드": "alias", "진입일자": "20230101", "진입시각": "20230101000000", "매도시간": 20230101090000.0, "매수금액": 11, "수익금": 999}) + "\n" +
        json.dumps({"종목코드": "123456", "진입일자": "20230101", "매수시간": "20230101000001", "매도시간": 20230101090000.0, "매수금액": 12, "label": "never read"}) + "\n" +
        json.dumps({"종목코드": "654321", "진입일자": "20240101", "진입시각": "20240101000000", "매도시간": 20240101090000.0, "매수금액": 13}) + "\n",
        encoding="utf-8")
    dump(Path(a.p3_chunk1), {"samples": [{"code": "alias", "day": "20230101", "t0": "20230101000000", "code6": "123456"}], "exclusions": [{"reason": "no code"}]})
    dump(Path(a.p3_chunk2), {"samples": [], "exclusions": []})
    parquet(Path(a.o3_parquet), [
        {"code": "123456", "day": "20221231", "off": 7, "t0": "235959", "variant": "P20", "onset_type": "breakout", "pnl": 100},
        {"code": "123456", "day": "20221231", "off": 7, "t0": "235959", "variant": "VI", "onset_type": "breakout", "pnl": 100},
    ])
    parquet(Path(a.o4_parquet), [
        {"code": "123456", "day": "20230101", "off": 8, "t0": "000001", "o4_avoid_gap_lt8": False, "o4_netbuy_gt1": True, "o4_qty_022": False, "o4_qty_035": False, "o4_qty_050": False, "profit": 9},
        {"code": "123456", "day": "20221231", "off": 7, "t0": "235959", "o4_avoid_gap_lt8": False, "o4_netbuy_gt1": False, "o4_qty_022": False, "o4_qty_035": False, "o4_qty_050": False, "profit": 9},
    ])
    parquet(Path(a.d1_parquet), [
        {"code": "123456", "day": "20230101", "off": 8, "t0": "000001", "bit_4": False, "bit_10": False, "bit_16": False, "bit_17": False, "rate": 9},
        {"code": "123456", "day": "20221231", "off": 7, "t0": "235959", "bit_4": True, "bit_10": False, "bit_16": False, "bit_17": False, "rate": 9},
    ])
    return a


@pytest.fixture
def repo(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    monkeypatch.setattr(mod, "__file__", str(root / "scripts" / "build_g003_veto_inputs.py"))
    return root


def test_actual_artifact_schemas_are_deterministic_outcome_blind_and_indexed(repo):
    a = make_inputs(repo / "fixtures")
    payload = mod.build(a)
    mod.publish(Path(a.output), payload)
    repeat = repo / "new" / "g003" / "repeat.json"
    mod.publish(repeat, mod.build(a))
    assert Path(a.output).read_bytes() == repeat.read_bytes()
    saved = json.loads(Path(a.output).read_text(encoding="utf-8"))
    assert len(saved["trades"]) == 2
    assert [trade["trade_id"] for trade in saved["trades"]] == [0, 1]
    first, second = saved["trades"]
    assert first["code_resolution"] == "p3_rejoin" and second["code_resolution"] == "code_literal"
    assert first["o3_mask"] and first["o4_mask"] and first["deep_anchor_overlap"]
    assert first["o3_refs"] == [{"source": "o3", "key": ["123456", "20221231", 7, "235959"], "offset": 1}]
    assert second["o4_refs"][0]["offset"] == 0 and first["o4_carrier_match"]
    assert all(not Path(ref["path"]).is_absolute() for ref in saved["sources"].values())
    assert saved["row_flow"]["o4_carrier_rows"] == 2
    assert saved["row_flow"]["o4_equivalence_mismatches"] == 0
    assert saved["contract"]["o4_evaluation_scope"] == "o4_onset_carrier_only"
    assert saved["contract"]["o4_explicit_union"] == "158_candidate_dnf"
    assert saved["contract"]["o4_simplified_union"] == "F1_OR_F2_OR_F3_OR_F4_0_22"
    assert "수익금" not in json.dumps(saved, ensure_ascii=False) and "profit" not in json.dumps(saved)
    with pytest.raises(FileExistsError):
        mod.publish(Path(a.output), payload)


@pytest.mark.parametrize("mutation, message", [
    ("o3_drift", "variant_kill_units"), ("o4_drift", "explicit 158"),
    ("no_positive_extra", "exactly equal"), ("classification", "classification is not"),
    ("unmapped", "unmapped non-literal"), ("ambiguous", "mapping ambiguity"),
    ("universe", "key universes differ"),
])
def test_builder_rejects_membership_mapping_and_key_drift(repo, mutation, message):
    a = make_inputs(repo / "fixtures")
    if mutation == "o3_drift":
        doc = json.loads(Path(a.o3_summary).read_text())
        doc["judgment"]["variant_kill_units"].pop()
        dump(Path(a.o3_summary), doc)
    elif mutation == "o4_drift":
        doc = json.loads(Path(a.o4_summary).read_text())
        doc["qualification"]["qualified_cids"].pop()
        dump(Path(a.o4_summary), doc)
    elif mutation == "no_positive_extra":
        doc = json.loads(Path(a.o4_summary).read_text())
        doc["judgment"]["no_positive_ev_cids"].append("extra")
        dump(Path(a.o4_summary), doc)
    elif mutation == "classification":
        doc = json.loads(Path(a.o4_summary).read_text())
        doc["judgment"]["per_candidate"][next(iter(doc["judgment"]["per_candidate"]))]["classification"] = "weak_signal"
        dump(Path(a.o4_summary), doc)
    elif mutation == "unmapped":
        Path(a.ledger).write_text(json.dumps({"종목코드": "not-a-code", "진입일자": "20230101", "진입시각": "20230101000000", "매도시간": "20230101090000", "매수금액": 1}) + "\n", encoding="utf-8")
    elif mutation == "ambiguous":
        dump(Path(a.p3_chunk2), {"samples": [{"code": "alias", "day": "20230101", "t0": "20230101000000", "code6": "654321"}], "exclusions": []})
    else:
        parquet(Path(a.d1_parquet), [{"code": "999999", "day": "20230101", "off": 8, "t0": "000001", "bit_4": False, "bit_10": False, "bit_16": False, "bit_17": False}])
    with pytest.raises(ValueError, match=message):
        mod.build(a)


def test_explicit_o4_grammar_reduces_to_fixed_union_and_conflicting_duplicates_fail(repo):
    candidates = mod._expected_o4_cids()
    assert len(candidates) == 158
    assert all(mod._candidate_slots(cid) for cid in candidates)
    assert {slot for cid in candidates for slot in mod._candidate_slots(cid) if slot in {"F1", "F2", "F3", "F4@0.22"}} == {"F1", "F2", "F3", "F4@0.22"}
    a = make_inputs(repo / "fixtures")
    parquet(Path(a.o4_parquet), [
        {"code": "123456", "day": "20230101", "off": 8, "t0": "000001", "o4_avoid_gap_lt8": False, "o4_netbuy_gt1": True, "o4_qty_022": False, "o4_qty_035": False, "o4_qty_050": False},
        {"code": "123456", "day": "20230101", "off": 8, "t0": "000001", "o4_avoid_gap_lt8": False, "o4_netbuy_gt1": True, "o4_qty_022": False, "o4_qty_035": False, "o4_qty_050": False},
    ])
    with pytest.raises(ValueError, match="duplicate key"):
        mod.build(a)
