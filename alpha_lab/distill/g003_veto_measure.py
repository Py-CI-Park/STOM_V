"""SEALED-v2 G003 static O3-or-O4 veto measurement."""
import json


_SOURCE_REFS = (
    ("d1_parquet", ("docs/research/condition_research/research_runs/alpha_restart_20260710/stats_map/d1_onset_clause_bits.parquet", "4df57b776bc1cb1ca7afc42e9eecd1b80c6fecbedd13e8379e017530a6600e56", 6783855, 863446)),
    ("ledger", ("docs/research/condition_research/research_runs/alpha_lab_20260705/distill/champion_ledger.jsonl", "72b6a082774a61c235f865a61b34d8162ced1972a8e2e7ccc1be7252aff01477", 779908, 671)),
    ("o3_parquet", ("docs/research/condition_research/research_runs/alpha_restart_20260710/o3/o3_breakout_onset_bank.parquet", "ca06411c7471f9550c8a8727adad4680c60a6bd9431dc23f56043edea519c859", 13061453, 702613)),
    ("o3_summary", ("docs/research/condition_research/research_runs/alpha_restart_20260710/o3/o3_breakout_summary.json", "13a03c57c9ecc74473f88537f6c053ae879e86085b3ac0f9014191d93490f4ba", 9857, 1)),
    ("o4_parquet", ("docs/research/condition_research/research_runs/alpha_restart_20260710/o4/stats_map_o4/o4_candidate_bits.parquet", "105850275408b061d2406da3ec888bfd27a037531183f5827bd178392315b724", 4878692, 863446)),
    ("o4_summary", ("docs/research/condition_research/research_runs/alpha_restart_20260710/o4/o4_candidate_summary.json", "65f20ea3f229f03420c8ef088b60c64b7810330575ddb163096ca95461e1ea37", 141365, 1)),
    ("p3_chunk1", ("docs/research/condition_research/research_runs/alpha_lab_20260705/p3_rejoin_chunk_1of2.json", "a21d0144ca012af3965c74628bc16df584cc11d2aa4fbb0895070de03b77fc54", 240191, 229)),
    ("p3_chunk2", ("docs/research/condition_research/research_runs/alpha_lab_20260705/p3_rejoin_chunk_2of2.json", "58fd87bb74c6af2d24cacc3f033f9ea42458f33ae8040804e9867cd4b4817c9e", 245320, 222)),
)


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and -1000000000000000000 < value < 1000000000000000000


def _rate(numerator, denominator):
    return numerator / denominator if denominator else 0


def _slot(item):
    return (item[0]["sell_day"] + item[0]["sell_second"], item[0]["entry_day"] + item[0]["buy_second"], item[0]["trade_id"])


def _curves(rows, index=0, base=0, base_peak=0, base_mdd=0, shadow=0, shadow_peak=0, shadow_mdd=0):
    if index == len(rows):
        return base, shadow, base_mdd, shadow_mdd
    trade, pnl = rows[index]
    next_base = base + pnl
    next_shadow = shadow + (0 if trade["union_mask"] else pnl)
    next_base_peak, next_shadow_peak = max(base_peak, next_base), max(shadow_peak, next_shadow)
    return _curves(rows, index + 1, next_base, next_base_peak, max(base_mdd, next_base_peak - next_base), next_shadow, next_shadow_peak, max(shadow_mdd, next_shadow_peak - next_shadow))


def _summary(rows, year=None):
    ordered = tuple(sorted(rows, key=_slot))
    base, shadow, base_mdd, shadow_mdd = _curves(ordered)
    census, drops = len(ordered), sum(1 for trade, _ in ordered if trade["union_mask"])
    retained, total = census - drops, sum(trade["notional"] for trade, _ in ordered)
    retained_notional = sum(trade["notional"] for trade, _ in ordered if not trade["union_mask"])
    positives = sum(1 for _, pnl in ordered if pnl > 0)
    false_drops = sum(1 for trade, pnl in ordered if trade["union_mask"] and pnl > 0)
    return {**({"year": year} if year else {}), "baseline_profit": base, "shadow_profit": shadow, "delta_profit": shadow - base, "baseline_mdd": base_mdd, "shadow_mdd": shadow_mdd, "delta_mdd": base_mdd - shadow_mdd, "census_count": census, "drop_count": drops, "drop_rate": _rate(drops, census), "retained_count": retained, "retained_rate": _rate(retained, census), "retained_notional_rate": _rate(retained_notional, total), "positive_trade_count": positives, "positive_false_drop_count": false_drops, "positive_false_drop_rate": _rate(false_drops, positives), "positive_false_drop_share_of_drops": _rate(false_drops, drops), "o3_count": sum(1 for trade, _ in ordered if trade["o3_mask"]), "o4_count": sum(1 for trade, _ in ordered if trade["o4_mask"]), "o4_carrier_match_count": sum(1 for trade, _ in ordered if trade["o4_carrier_match"]), "deep_anchor_overlap_count": sum(1 for trade, _ in ordered if trade["deep_anchor_overlap"])}


def _reasons(snapshot, ledger_rows):
    source_names = tuple(name for name, _ in _SOURCE_REFS)
    trade_keys = {"trade_id", "entry_day", "buy_second", "sell_day", "sell_second", "notional", "o3_mask", "o4_mask", "union_mask", "deep_anchor_overlap", "o4_carrier_match"}
    flow_keys = {"ledger_scoped", "o3_rows", "o4_rows", "d1_rows", "o4_carrier_rows", "o4_equivalence_mismatches"}
    if not isinstance(snapshot, dict) or not isinstance(ledger_rows, (list, tuple)):
        return ("shape",)
    if set(snapshot) != {"schema", "kind", "contract", "row_flow", "sources", "trades"}:
        return ("shape",)
    if snapshot["schema"] != "g003-static-veto-input-v1":
        return ("schema",)
    contract, flow, sources, trades = snapshot["contract"], snapshot["row_flow"], snapshot["sources"], snapshot["trades"]
    if not isinstance(contract, dict) or not isinstance(flow, dict) or not isinstance(sources, dict) or not isinstance(trades, list):
        return ("shape",)
    if not {"o4_evaluation_scope", "o4_explicit_union", "o4_simplified_union"} <= set(contract) or (contract["o4_evaluation_scope"], contract["o4_explicit_union"], contract["o4_simplified_union"]) != ("o4_onset_carrier_only", "158_candidate_dnf", "F1_OR_F2_OR_F3_OR_F4_0_22"):
        return ("provenance",)
    if set(sources) != set(source_names):
        return ("source_refs",)
    if any(not isinstance(sources[name], dict) or set(sources[name]) != {"path", "sha256", "size", "rows"} or (sources[name]["path"], sources[name]["sha256"], sources[name]["size"], sources[name]["rows"]) != expected for name, expected in _SOURCE_REFS):
        return ("source_refs",)
    if set(flow) != flow_keys or (flow["ledger_scoped"], flow["o3_rows"], flow["o4_rows"], flow["d1_rows"], flow["o4_carrier_rows"], flow["o4_equivalence_mismatches"]) != (298, 702613, 863446, 863446, 863446, 0):
        return ("row_flow",)
    if any(not isinstance(row, dict) or not {"진입일자"} <= set(row) or not isinstance(row["진입일자"], str) for row in ledger_rows):
        return ("shape",)
    scoped = tuple((ordinal, row) for ordinal, row in enumerate(ledger_rows) if row["진입일자"][:4] in ("2022", "2023"))
    if any(not {"진입일자", "진입시각", "매수시간", "매도시간", "매수금액", "수익금"} <= set(row) for _, row in scoped):
        return ("shape",)
    if any(not isinstance(row["진입시각"], str) or not _finite(row["매수시간"]) or not _finite(row["매도시간"]) or not _finite(row["매수금액"]) or row["매수금액"] <= 0 or not _finite(row["수익금"]) for _, row in scoped):
        return ("identity",)
    if len(trades) != 298 or len(scoped) != 298 or sum(1 for _, row in scoped if row["진입일자"][:4] == "2022") != 101 or sum(1 for _, row in scoped if row["진입일자"][:4] == "2023") != 197:
        return ("census",)
    if any(not isinstance(trade, dict) or not trade_keys <= set(trade) for trade in trades):
        return ("shape",)
    if any(not isinstance(trade["trade_id"], int) or isinstance(trade["trade_id"], bool) for trade in trades):
        return ("census",)
    by_id = {trade["trade_id"]: trade for trade in trades}
    if len(by_id) != 298 or tuple(sorted(by_id)) != tuple(ordinal for ordinal, _ in scoped):
        return ("census",)
    valid = all(_finite(trade["notional"]) and trade["notional"] > 0 and trade["notional"] == row["매수금액"] and isinstance(trade["entry_day"], str) and isinstance(trade["buy_second"], str) and isinstance(trade["sell_day"], str) and isinstance(trade["sell_second"], str) and len(trade["entry_day"]) == 8 and len(trade["buy_second"]) == 6 and len(trade["sell_day"]) == 8 and len(trade["sell_second"]) == 6 and trade["entry_day"] == row["진입일자"] and trade["buy_second"] == row["진입시각"] and trade["entry_day"] + trade["buy_second"] == str(int(row["매수시간"])) and trade["sell_day"] + trade["sell_second"] == str(int(row["매도시간"])) and all(isinstance(trade[name], bool) for name in ("o3_mask", "o4_mask", "union_mask", "deep_anchor_overlap", "o4_carrier_match")) and (trade["o4_carrier_match"] or not trade["o4_mask"]) and trade["union_mask"] == (trade["o3_mask"] or trade["o4_mask"]) and trade["deep_anchor_overlap"] == (trade["o3_mask"] and trade["o4_mask"]) for ordinal, row in scoped for trade in (by_id[ordinal],))
    return () if valid else ("identity",)


def measure(snapshot, ledger_rows):
    reasons = _reasons(snapshot, ledger_rows)
    if reasons:
        return {"schema": "g003-static-veto-measure-v1", "verdict": "INSUFFICIENT", "integrity_reasons": reasons}
    rows = tuple((trade, row["수익금"]) for ordinal, row in enumerate(ledger_rows) if ordinal in {trade["trade_id"] for trade in snapshot["trades"]} for trade in snapshot["trades"] if trade["trade_id"] == ordinal)
    years = tuple(_summary(tuple(row for row in rows if row[0]["entry_day"][:4] == year), year) for year in ("2022", "2023"))
    combined = _summary(rows)
    return {"schema": "g003-static-veto-measure-v1", "driver": "O3 OR O4", "deep_anchor_overlap": "diagnostic_only", "verdict": "PASS" if all(item["delta_profit"] > 0 and item["delta_mdd"] >= 0 for item in years) else "FAIL", "integrity_reasons": (), "years": {item["year"]: item for item in years}, "combined": {**combined, "o4_equivalence_mismatches": 0}, "caveats": ("Historical drop-only diagnostics; not OOS or live evidence.", "No dynamic capital reallocation, resizing, re-entry, cash reuse, compounding, opportunity cost, or scheduling changes.")}


if __name__ == "__main__":
    with open("docs/research/condition_research/research_runs/alpha_restart_20260710/g003/g003_veto_input.json", mode="r", encoding="utf-8") as snapshot_handle:
        snapshot = json.load(snapshot_handle)
    with open("docs/research/condition_research/research_runs/alpha_lab_20260705/distill/champion_ledger.jsonl", mode="r", encoding="utf-8") as ledger_handle:
        ledger_rows = tuple(json.loads(line) for line in ledger_handle)
    result = measure(snapshot, ledger_rows)
    print(json.dumps(result))
