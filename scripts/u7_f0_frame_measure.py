"""SEALED-v2 JSON-only measurement for the U7-F0 identified factorial frame."""
import json
def _date(value):
    if not isinstance(value, str) or not value.isdigit() or len(value) != 8:
        return False
    year, month, day = int(value[:4]), int(value[4:6]), int(value[6:])
    if not 1 <= month <= 12 or day < 1:
        return False
    days = (31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    return day <= days[month - 1]


def _timestamp(value, day=None):
    if not isinstance(value, str) or not value.isdigit() or len(value) != 14 or not _date(value[:8]) or (day is not None and value[:8] != day):
        return False
    return int(value[8:10]) < 24 and int(value[10:12]) < 60 and int(value[12:]) < 60


INPUT_PATH = "docs/research/condition_research/research_runs/alpha_restart_20260710/g002/u7_f0_materialized_input.json"
SCHEMA = "u7-f0-materialized-input-v2"
YEARS = (2022, 2023)
SEED = 20260715
REPLICATES = 20000
CELL_KEYS = ("E0D0T0", "E0D0T1", "E0D1T0", "E0D1T1", "E1D0T0", "E1D0T1", "E1D1T0", "E1D1T1")
SOURCES = ("champion_ledger", "p5_receipt", "onset_l3_bank", "d1_onset_clause_bits", "equivalence_receipt", "champion_passport", "sell_expression")
MEASURES = ("primary_gap_pp", "modeled_gap_pp", "residual_gap_pp", "shapley_E_pp", "shapley_D_pp", "shapley_T_pp", "explanation")


def _fail(message):
    int("invalid:" + message)


def _closed(value, keys, name):
    if not isinstance(value, dict) or set(value) != set(keys):
        _fail(name + " must contain exactly " + str(sorted(keys)))
    return value


def _finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value or value <= -1000000000000000000 or value >= 1000000000000000000:
        _fail(name + " must be finite")
    return float(value)


def _hash(value, name):
    if not isinstance(value, str) or len(value) != 64 or not all(char in "0123456789abcdefABCDEF" for char in value):
        _fail(name + " must be SHA-256")


def _absolute_path(value):
    return isinstance(value, str) and (value.startswith("/") or (len(value) >= 3 and value[0].isalpha() and value[1] == ":" and value[2] in "/\\") or (value.startswith("\\\\") and len(value.split("\\")) >= 4 and bool(value.split("\\")[2]) and bool(value.split("\\")[3])))
def _project_path(value):
    if not isinstance(value, str) or not value or _absolute_path(value) or "\\" in value or ":" in value or any(part in ("", ".", "..") for part in value.split("/")):
        return False
    return True
def _artifact(value, name, absolute=False):
    item = _closed(value, ("path", "sha256", "size_bytes"), name)
    if not isinstance(item["path"], str) or not item["path"] or (absolute and not _absolute_path(item["path"])) or (not absolute and not _project_path(item["path"])):
        _fail(name + ".path is not canonical")
    _hash(item["sha256"], name + ".sha256")
    if isinstance(item["size_bytes"], bool) or not isinstance(item["size_bytes"], int) or item["size_bytes"] <= 0:
        _fail(name + ".size_bytes must be positive")
    return item


def _identity(value, name):
    item = _closed(value, ("code", "year", "day", "buy_time"), name)
    if not isinstance(item["code"], str) or not item["code"].isdigit() or len(item["code"]) != 6 or isinstance(item["year"], bool) or not isinstance(item["year"], int) or item["year"] not in YEARS or not _date(item["day"]) or item["year"] != int(item["day"][:4]) or not _timestamp(item["buy_time"], item["day"]):
        _fail(name + " is invalid")
    return (item["code"], item["year"], item["day"], item["buy_time"])


def _physical(value, name, expected):
    item = _closed(value, ("pre", "post"), name)
    for phase in ("pre", "post"):
        identity = _closed(item[phase], ("sha256", "size_bytes", "physical_id"), name + "." + phase)
        _hash(identity["sha256"], name + "." + phase + ".sha256")
        if isinstance(identity["size_bytes"], bool) or not isinstance(identity["size_bytes"], int) or identity["size_bytes"] <= 0 or not isinstance(identity["physical_id"], str) or not identity["physical_id"]:
            _fail(name + " physical identity is invalid")
        if identity != expected:
            _fail(name + " does not match its immutable artifact descriptor")
    return item


def net_rate(buy, sell, qty, year):
    if buy <= 0 or sell <= 0 or qty <= 0:
        _fail("prices and quantity must be positive")
    fee = 0.00015
    tax = 0.0023 if year == 2022 else 0.0020
    return (sell * (1 - tax - fee) - buy * (1 + fee)) / (buy * (1 + fee))


def _ledger(value, identity):
    ledger = _closed(value, ("buy_price", "buy_amount", "qty", "sell_price", "buy_timestamp", "sell_timestamp"), "ledger")
    buy = _finite(ledger["buy_price"], "ledger.buy_price")
    amount = _finite(ledger["buy_amount"], "ledger.buy_amount")
    qty = _finite(ledger["qty"], "ledger.qty")
    sell = _finite(ledger["sell_price"], "ledger.sell_price")
    if buy <= 0 or amount <= 0 or qty <= 0 or sell <= 0 or amount != buy * qty or ledger["buy_timestamp"] != identity[3] or not _timestamp(ledger["buy_timestamp"], identity[2]) or not _timestamp(ledger["sell_timestamp"], identity[2]) or ledger["sell_timestamp"] <= identity[3]:
        _fail("ledger is invalid")
    return ledger


def _cell(value, year, day, branch, matched, buy_time, key, reason):
    cell = _closed(value, ("status", "entry_price", "entry_time", "exit_price", "exit_time", "qty", "clause", "forced", "missing_reason"), "cell")
    if not matched:
        if cell["status"] != "missing" or cell["forced"] is not False or cell["missing_reason"] != reason or any(cell[key] is not None for key in ("entry_price", "entry_time", "exit_price", "exit_time", "qty", "clause")):
            _fail("missing cell is not canonical")
        return None
    if cell["status"] != "matched" or cell["missing_reason"] is not None or not isinstance(cell["forced"], bool) or isinstance(cell["clause"], bool) or not isinstance(cell["clause"], int) or (cell["forced"] and cell["clause"] != 0) or (not cell["forced"] and cell["clause"] <= 0):
        _fail("matched cell clause is not canonical")
    entry = _finite(cell["entry_price"], "cell.entry_price")
    exit_ = _finite(cell["exit_price"], "cell.exit_price")
    qty = _finite(cell["qty"], "cell.qty")
    if entry <= 0 or exit_ <= 0 or qty <= 0 or cell["entry_time"] != buy_time or not _timestamp(cell["exit_time"], day) or cell["entry_time"] >= cell["exit_time"] or cell["exit_time"] > day + ("093000" if key.endswith("T0") else "092800"):
        _fail("matched cell is invalid")
    value_pp = net_rate(entry, exit_, qty, year) * 100
    if not -100 <= value_pp <= 100:
        _fail("cell endpoint exceeds support")
    return value_pp


def _provenance(value, events):
    provenance = _closed(value, ("schema", "source_authority", "sources", "preregistration", "launch", "cell_definition_binding", "physical_inputs", "tick_db", "materializer", "measurement_target", "identity_crosswalk", "design_marker", "endpoint_reconciliation"), "provenance")
    if provenance["schema"] != "u7-f0-provenance-v3":
        _fail("provenance schema is not canonical")
    authority = _artifact(provenance["source_authority"], "provenance.source_authority")
    preregistration = _artifact(provenance["preregistration"], "provenance.preregistration")
    launch = _artifact(provenance["launch"], "provenance.launch")
    materializer = _artifact(provenance["materializer"], "provenance.materializer")
    target = _artifact(provenance["measurement_target"], "provenance.measurement_target")
    crosswalk = _artifact(provenance["identity_crosswalk"], "provenance.identity_crosswalk", absolute=True)
    design_marker = _artifact(provenance["design_marker"], "provenance.design_marker", absolute=True)
    if preregistration["path"] != "docs/research/condition_research/plans/2026-07-16_g002_u7_f0_preregistration.md" or materializer["path"] != "scripts/u7_f0_materialize.py" or target["path"] != "scripts/u7_f0_frame_measure.py":
        _fail("canonical provenance artifact path is invalid")
    sources = _closed(provenance["sources"], SOURCES, "provenance.sources")
    source_descriptors = {key: _artifact(sources[key], "provenance.sources." + key) for key in SOURCES}
    binding = _closed(provenance["cell_definition_binding"], ("champion_sell_sha256", "equivalence_receipt_sha256", "champion_passport_sha256", "states"), "cell_definition_binding")
    if binding["champion_sell_sha256"] != sources["sell_expression"]["sha256"] or binding["equivalence_receipt_sha256"] != sources["equivalence_receipt"]["sha256"] or binding["champion_passport_sha256"] != sources["champion_passport"]["sha256"] or binding["states"] != {"equivalence": "validated", "passport": "validated"}:
        _fail("cell definition binding is invalid")
    tick = _closed(provenance["tick_db"], ("path", "sha256", "size_bytes", "physical_id", "read_only", "query_only", "pre", "post"), "provenance.tick_db")
    if tick["read_only"] is not True or tick["query_only"] is not True or not _absolute_path(tick["path"]):
        _fail("tick DB must be read-only and query-only")
    _hash(tick["sha256"], "provenance.tick_db.sha256")
    if isinstance(tick["size_bytes"], bool) or not isinstance(tick["size_bytes"], int) or tick["size_bytes"] <= 0:
        _fail("provenance.tick_db.size_bytes must be positive")
    tick_expected = {"sha256": tick["sha256"], "size_bytes": tick["size_bytes"], "physical_id": f"{tick['path']}:{tick['size_bytes']}:{tick['sha256']}"}
    if tick["physical_id"] != tick_expected["physical_id"]:
        _fail("tick DB physical identity is invalid")
    expected_physical = SOURCES + ("tick_db", "source_authority", "preregistration", "launch", "materializer", "measurement_target", "identity_crosswalk", "design_marker")
    physical = _closed(provenance["physical_inputs"], expected_physical, "physical_inputs")
    descriptors = {**source_descriptors, "tick_db": tick, "source_authority": authority, "preregistration": preregistration, "launch": launch, "materializer": materializer, "measurement_target": target, "identity_crosswalk": crosswalk, "design_marker": design_marker}
    for key in expected_physical:
        descriptor = descriptors[key]
        expected = tick_expected if key == "tick_db" else {"sha256": descriptor["sha256"], "size_bytes": descriptor["size_bytes"], "physical_id": f"{descriptor['path']}:{descriptor['size_bytes']}:{descriptor['sha256']}"}
        _physical(physical[key], "physical_inputs." + key, expected)
    _physical({"pre": tick["pre"], "post": tick["post"]}, "provenance.tick_db", tick_expected)
    matched = [event for event in events if event["status"] == "matched"]
    reconciliation = provenance["endpoint_reconciliation"]
    if not isinstance(reconciliation, list) or len(reconciliation) != len(matched):
        _fail("endpoint reconciliation count is invalid")
    expected = {tuple(event["identity"][key] for key in ("code", "year", "day", "buy_time")): event for event in matched}
    seen = set()
    for row in reconciliation:
        row = _closed(row, ("identity", "engine", "l3"), "endpoint_reconciliation")
        key = _identity(row["identity"], "endpoint_reconciliation.identity")
        if key not in expected or key in seen:
            _fail("endpoint reconciliation identities are invalid")
        seen.add(key)
        engine = _closed(row["engine"], ("ledger_sell_price", "ledger_sell_timestamp", "cell_sell_price", "cell_sell_timestamp", "parity"), "endpoint_reconciliation.engine")
        l3 = _closed(row["l3"], ("bank_exit_timestamp", "bank_clause", "cell_exit_timestamp", "cell_clause", "parity"), "endpoint_reconciliation.l3")
        event = expected[key]
        timestamps = (engine["ledger_sell_timestamp"], engine["cell_sell_timestamp"], l3["bank_exit_timestamp"], l3["cell_exit_timestamp"])
        if not all(_timestamp(timestamp, key[2]) for timestamp in timestamps) or not isinstance(engine["parity"], bool) or not isinstance(l3["parity"], bool) or engine["ledger_sell_price"] != event["ledger"]["sell_price"] or engine["ledger_sell_timestamp"] != event["ledger"]["sell_timestamp"] or engine["cell_sell_price"] != event["cells"]["E1D1T1"]["exit_price"] or engine["cell_sell_timestamp"] != event["cells"]["E1D1T1"]["exit_time"] or engine["parity"] != (engine["ledger_sell_price"] == engine["cell_sell_price"] and engine["ledger_sell_timestamp"] == engine["cell_sell_timestamp"]) or l3["cell_exit_timestamp"] != event["cells"]["E0D0T0"]["exit_time"] or l3["cell_clause"] != event["cells"]["E0D0T0"]["clause"] or l3["parity"] != (l3["bank_exit_timestamp"] == l3["cell_exit_timestamp"] and l3["bank_clause"] == l3["cell_clause"]):
            _fail("endpoint reconciliation parity is invalid")
    if len(seen) != len(expected):
        _fail("endpoint reconciliation coverage is invalid")


def _integrity(snapshot):
    root = _closed(snapshot, ("contract", "provenance", "flow", "events", "offline_only", "side_effect_counters"), "snapshot")
    contract = _closed(root["contract"], ("schema", "factor_coding", "years", "seed", "replicates", "cell_net_support_pp", "modeled_gap_support_pp", "explanation_threshold"), "contract")
    if contract["schema"] != SCHEMA or contract["years"] != [2022, 2023] or contract["seed"] != SEED or contract["replicates"] != REPLICATES or contract["factor_coding"] != {"E0": "synthetic", "E1": "recorded", "D0": "l3_topbook", "D1": "engine_ladder3", "T0": "cap093000", "T1": "terminal092800"} or contract["cell_net_support_pp"] != [-100, 100] or contract["modeled_gap_support_pp"] != [-200, 200] or contract["explanation_threshold"] != 0.5:
        _fail("contract is not sealed")
    flow = _closed(root["flow"], ("engine_rows", "matched", "engine_only", "excluded", "offline_only", "conservation_ok", "year_rows"), "flow")
    if flow["engine_rows"] != 298 or flow["year_rows"] != {"2022": 101, "2023": 197} or flow["conservation_ok"] is not True or sum(flow[key] for key in ("matched", "engine_only", "excluded")) != 298 or _closed(root["side_effect_counters"], ("engine_calls", "db_writes", "strategy_registrations", "outcome_executions"), "counters") != {"engine_calls": 0, "db_writes": 0, "strategy_registrations": 0, "outcome_executions": 0} or not isinstance(root["events"], list) or len(root["events"]) != 298 or not isinstance(root["offline_only"], list) or len(root["offline_only"]) != flow["offline_only"]:
        _fail("fixed universe is invalid")
    offline_keys = set()
    for ordinal, item in enumerate(root["offline_only"]):
        item = _closed(item, ("identity", "status", "reason"), "offline_only[" + str(ordinal) + "]")
        identity = _identity(item["identity"], "offline_only.identity")
        if identity in offline_keys or item["status"] != "offline_only" or not isinstance(item["reason"], str) or not item["reason"]:
            _fail("offline-only commitment invalid")
        offline_keys.add(identity)
    keys = set()
    counts = {2022: 0, 2023: 0, "matched": 0, "engine_only": 0, "excluded": 0}
    for ordinal, event in enumerate(root["events"]):
        item = _closed(event, ("identity", "status", "reason", "ledger", "l3_net_ref", "branch", "cells"), "event[" + str(ordinal) + "]")
        identity = _identity(item["identity"], "identity")
        if identity in keys or item["status"] not in ("matched", "engine_only", "excluded"):
            _fail("invalid event identity or status")
        keys.add(identity); counts[identity[1]] += 1; counts[item["status"]] += 1
        ledger = _ledger(item["ledger"], identity)
        ledger_pp = net_rate(ledger["buy_price"], ledger["sell_price"], ledger["qty"], identity[1]) * 100
        if not -100 <= ledger_pp <= 100:
            _fail("ledger endpoint exceeds support")
        cells = _closed(item["cells"], CELL_KEYS, "cells")
        if item["status"] == "engine_only":
            if not isinstance(item["reason"], str) or not item["reason"] or item["l3_net_ref"] is not None or item["branch"] is not None:
                _fail("engine-only commitment invalid")
            for key in CELL_KEYS: _cell(cells[key], identity[1], identity[2], 0, False, identity[3], key, item["reason"])
        else:
            if not isinstance(item["reason"], type(None) if item["status"] == "matched" else str) or (item["status"] == "excluded" and not item["reason"]) or item["branch"] not in (902, 905):
                _fail("matched or excluded commitment invalid")
            l3 = _finite(item["l3_net_ref"], "l3_net_ref") * 100
            if not -100 <= l3 <= 100:
                _fail("L3 endpoint exceeds support")
            for key in CELL_KEYS: _cell(cells[key], identity[1], identity[2], item["branch"], item["status"] == "matched", identity[3], key, item["reason"])
    if counts != {2022: 101, 2023: 197, "matched": flow["matched"], "engine_only": flow["engine_only"], "excluded": flow["excluded"]}:
        _fail("annual/status flow mismatch")
    _provenance(root["provenance"], root["events"])
    return root


validate_snapshot = _integrity
FrameSchemaError = ValueError


def _shapley(values):
    base = values["E0D0T0"]
    return {"E": (values["E1D0T0"] - base) / 3 + ((values["E1D1T0"] - values["E0D1T0"]) + (values["E1D0T1"] - values["E0D0T1"])) / 6 + (values["E1D1T1"] - values["E0D1T1"]) / 3, "D": (values["E0D1T0"] - base) / 3 + ((values["E1D1T0"] - values["E1D0T0"]) + (values["E0D1T1"] - values["E0D0T1"])) / 6 + (values["E1D1T1"] - values["E1D0T1"]) / 3, "T": (values["E0D0T1"] - base) / 3 + ((values["E1D0T1"] - values["E1D0T0"]) + (values["E0D1T1"] - values["E0D1T0"])) / 6 + (values["E1D1T1"] - values["E1D1T0"]) / 3}


def measure_events(snapshot):
    root = _integrity(snapshot)
    measurements = []
    for event in root["events"]:
        identity = event["identity"]; year = identity["year"]
        ledger = event["ledger"]
        ledger_pp = net_rate(ledger["buy_price"], ledger["sell_price"], ledger["qty"], year) * 100
        if event["status"] == "engine_only":
            primary = (ledger_pp - 100, ledger_pp + 100); modeled = (-200.0, 200.0); shapley = None
        elif event["status"] == "excluded":
            primary_value = ledger_pp - float(event["l3_net_ref"]) * 100; primary = (primary_value, primary_value); modeled = (-200.0, 200.0); shapley = None
        else:
            values = {key: _cell(event["cells"][key], year, identity["day"], event["branch"], True, identity["buy_time"], key, event["reason"]) for key in CELL_KEYS}
            primary_value = ledger_pp - float(event["l3_net_ref"]) * 100; modeled_value = values["E1D1T1"] - values["E0D0T0"]
            primary = (primary_value, primary_value); modeled = (modeled_value, modeled_value); shapley = _shapley(values)
        measurements.append({"identity": (identity["code"], year, identity["day"], identity["buy_time"]), "year": year, "day": identity["day"], "primary_range_pp": primary, "modeled_range_pp": modeled, "residual_range_pp": (primary[0] - modeled[1], primary[1] - modeled[0]), "primary_gap_pp": (primary[0] + primary[1]) / 2, "modeled_gap_pp": (modeled[0] + modeled[1]) / 2, "residual_gap_pp": ((primary[0] + primary[1]) - (modeled[0] + modeled[1])) / 2, "shapley_pp": shapley})
    return measurements


def _aggregate(items):
    if not items: _fail("cannot aggregate empty sample")
    primary = sum(item["primary_gap_pp"] for item in items) / len(items)
    modeled = sum(item["modeled_gap_pp"] for item in items) / len(items)
    return {"primary_gap_pp": primary, "modeled_gap_pp": modeled, "residual_gap_pp": primary - modeled, "shapley_E_pp": sum((item["shapley_pp"] or {"E": 0})["E"] for item in items) / len(items), "shapley_D_pp": sum((item["shapley_pp"] or {"D": 0})["D"] for item in items) / len(items), "shapley_T_pp": sum((item["shapley_pp"] or {"T": 0})["T"] for item in items) / len(items), "explanation": 1 - abs(primary - modeled) / abs(primary) if primary else 0.0}


def _lcg_states(count):
    state = SEED
    for ignored in range(count):
        state = (1664525 * state + 1013904223) % 4294967296
        yield state


def _year_sample(items, states):
    days = tuple(sorted(set(item["day"] for item in items)))
    blocks = {day: tuple(item for item in items if item["day"] == day) for day in days}
    return tuple(event for ignored in days for event in blocks[days[next(states) % len(days)]])


def _weighted_aggregate(left, right):
    weight_2022 = 101 / 298
    weight_2023 = 197 / 298
    primary = left["primary_gap_pp"] * weight_2022 + right["primary_gap_pp"] * weight_2023
    modeled = left["modeled_gap_pp"] * weight_2022 + right["modeled_gap_pp"] * weight_2023
    return {"primary_gap_pp": primary, "modeled_gap_pp": modeled, "residual_gap_pp": primary - modeled, "shapley_E_pp": left["shapley_E_pp"] * weight_2022 + right["shapley_E_pp"] * weight_2023, "shapley_D_pp": left["shapley_D_pp"] * weight_2022 + right["shapley_D_pp"] * weight_2023, "shapley_T_pp": left["shapley_T_pp"] * weight_2022 + right["shapley_T_pp"] * weight_2023, "explanation": 1 - abs(primary - modeled) / abs(primary) if primary else 0.0}


def _bootstrap(items):
    annual = {year: tuple(item for item in items if item["year"] == year) for year in YEARS}
    if len(annual[2022]) != 101 or len(annual[2023]) != 197:
        _fail("bootstrap must preserve fixed annual composition")
    output = {"2022": {key: [] for key in MEASURES}, "2023": {key: [] for key in MEASURES}, "pooled": {key: [] for key in MEASURES}}
    states = _lcg_states(REPLICATES * sum(len(set(item["day"] for item in annual[year])) for year in YEARS))
    for ignored in range(REPLICATES):
        aggregates = {year: _aggregate(_year_sample(annual[year], states)) for year in YEARS}
        for year in YEARS:
            for key in MEASURES: output[str(year)][key].append(aggregates[year][key])
        pooled = _weighted_aggregate(aggregates[2022], aggregates[2023])
        for key in MEASURES: output["pooled"][key].append(pooled[key])
    return output


def _ci(values):
    ordered = sorted(values)
    return (ordered[int(.025 * (len(ordered) - 1))], ordered[int(.975 * (len(ordered) - 1))])


def _annual_ranges(root, items):
    annual = {}
    for year in YEARS:
        rows = [item for item in items if item["year"] == year]
        count = root["flow"]["year_rows"][str(year)]
        if len(rows) != count: _fail("identified ranges lost an event")
        primary = tuple(sum(item["primary_range_pp"][side] for item in rows) / count for side in (0, 1))
        modeled = tuple(sum(item["modeled_range_pp"][side] for item in rows) / count for side in (0, 1))
        annual[year] = {"primary_gap_pp": primary, "modeled_gap_pp": modeled, "residual_gap_pp": (primary[0] - modeled[1], primary[1] - modeled[0])}
    total = 298
    primary = tuple((annual[2022]["primary_gap_pp"][side] * 101 + annual[2023]["primary_gap_pp"][side] * 197) / total for side in (0, 1))
    modeled = tuple((annual[2022]["modeled_gap_pp"][side] * 101 + annual[2023]["modeled_gap_pp"][side] * 197) / total for side in (0, 1))
    return {"2022": annual[2022], "2023": annual[2023], "pooled": {"primary_gap_pp": primary, "modeled_gap_pp": modeled, "residual_gap_pp": (primary[0] - modeled[1], primary[1] - modeled[0])}}


def _sign_ranges(primary, modeled, sign):
    if sign > 0:
        return (max(primary[0], 0.0), primary[1]), (max(modeled[0], 0.0), modeled[1])
    return (max(-primary[1], 0.0), -primary[0]), (max(-modeled[1], 0.0), -modeled[0])


def _ratio_gate(primary, modeled, sign, universal):
    (primary_low, primary_high), (modeled_low, modeled_high) = _sign_ranges(primary, modeled, sign)
    if primary_high <= 0 or modeled_high <= 0:
        return False
    if universal:
        return modeled_low >= .5 * primary_high and modeled_high <= 1.5 * primary_low
    return modeled_high >= .5 * primary_low and modeled_low <= 1.5 * primary_high


def _same_sign_gate(ranges, universal):
    return any(all(_ratio_gate(ranges[str(year)]["primary_gap_pp"], ranges[str(year)]["modeled_gap_pp"], sign, universal) for year in YEARS) for sign in (1, -1))


def decide(snapshot):
    try: root = _integrity(snapshot)
    except ValueError as error: return {"decision": "UNDETERMINED", "integrity_reasons": (str(error),)}
    items = measure_events(root); ranges = _annual_ranges(root, items); bootstrap = _bootstrap(items)
    ci = {year: {key: _ci(bootstrap[year][key]) for key in MEASURES} for year in ("2022", "2023", "pooled")}
    universal = _same_sign_gate(ranges, True); possible = _same_sign_gate(ranges, False)
    confirmed = False
    for sign in (1, -1):
        if all((ci[str(year)]["primary_gap_pp"][0] > 0 and ci[str(year)]["modeled_gap_pp"][0] > 0) if sign > 0 else (ci[str(year)]["primary_gap_pp"][1] < 0 and ci[str(year)]["modeled_gap_pp"][1] < 0) for year in YEARS) and all(ci[str(year)]["explanation"][0] >= .5 for year in YEARS): confirmed = True
    aggregate = _aggregate(items)
    return {"decision": "PASS" if universal and confirmed else "KILL" if not possible else "UNDETERMINED", "integrity_reasons": (), **aggregate, "bootstrap_ci_pp": ci, "annual_identified_ranges_pp": ranges, "decision_diagnostics": {"rule": "PASS requires universal same-sign annual identified-set M/P ratios in [0.5, 1.5] and annual fixed-year joint-bootstrap same-sign primary/model CIs with aggregate explanation lower bounds at least .5; KILL requires no possible annual identified-set pass.", "identified_set_universally_passes": universal, "identified_set_possibly_passes": possible, "annual_joint_bootstrap_confirms": confirmed, "bootstrap_design": "whole-day cluster resamples stratified by year; every event in a sampled day has the same multiplicity, annual replicate means use complete sampled clusters, pooled statistics use fixed 101/298 and 197/298 annual weights, and explanation is recomputed as 1 - abs(P-M)/abs(P) from each aggregate replicate, with P=0 fail-safe 0"}, "denominator_flow": root["flow"]}


if __name__ == "__main__":
    with open("docs/research/condition_research/research_runs/alpha_restart_20260710/g002/u7_f0_materialized_input.json", mode="r", encoding="utf-8") as snapshot_handle:
        snapshot = json.load(snapshot_handle)
    print(json.dumps(decide(snapshot)))
