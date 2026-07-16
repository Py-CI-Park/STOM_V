#!/usr/bin/env python3
"""Build an immutable, outcome-blind G003 static-veto input snapshot."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any

try:
    import pyarrow.parquet as pq
except ImportError as exc:  # pragma: no cover
    raise SystemExit("pyarrow is required to read the supplied parquet inputs") from exc

O3_VARIANTS = frozenset({"P20", "P300", "DH", "OP", "VI"})
O3_UNITS = frozenset(f"{variant}:{scope}" for variant in O3_VARIANTS for scope in ("all", "surge_nonoverlap"))
O4_PRESSURES = frozenset({"F1", "F2", "F3", "F4@0.22", "F4@0.35", "F4@0.50"})
O4_FIXED_BITS = frozenset({"o4_netbuy_gt1", "bit_4", "bit_10", "o4_qty_022"})
KEY_COLUMNS = ("code", "day", "off", "t0")
O4_O4_COLUMNS = ("o4_avoid_gap_lt8", "o4_netbuy_gt1", "o4_qty_022", "o4_qty_035", "o4_qty_050")
O4_D1_COLUMNS = ("bit_4", "bit_10", "bit_16", "bit_17")
O4_CARRIER_BITS = frozenset(O4_O4_COLUMNS + O4_D1_COLUMNS)
_CODE6 = re.compile(r"^\d{6}$")


def _fail(message: str) -> None:
    raise ValueError(message)


def _json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _field(record: dict[str, Any], names: tuple[str, ...], what: str) -> Any:
    found = [record[name] for name in names if name in record]
    if len(found) != 1:
        _fail(f"{what} must contain exactly one of {names}")
    return found[0]
def _alias(record: dict[str, Any], names: tuple[str, ...], parser: Any, what: str) -> Any:
    values = [(name, parser(record[name])) for name in names if name in record]
    if not values:
        _fail(f"{what} must contain one of {names}")
    canonical = values[0][1]
    if any(value != canonical for _, value in values[1:]):
        _fail(f"{what} has conflicting aliases: {[name for name, _ in values]}")
    return canonical


def _entry_aliases(record: dict[str, Any], day_names: tuple[str, ...],
                   time_names: tuple[str, ...], what: str) -> tuple[str, str]:
    day = _alias(record, day_names, _day, f"{what} day")
    second = _alias(record, time_names,
                    lambda value: _time_for_day(day, value, f"{what} time"),
                    f"{what} time")
    return day, second


def _digits(value: Any, length: int, what: str) -> str:
    if isinstance(value, bool):
        _fail(f"invalid {what} {value!r}")
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            _fail(f"invalid {what} {value!r}")
        value = int(value)
    text = str(value)
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    if not (len(text) == length and text.isascii() and text.isdigit()):
        _fail(f"invalid {what} {value!r}")
    return text


def _day(value: Any) -> str:
    result = _digits(value, 8, "day")
    try:
        dt.datetime.strptime(result, "%Y%m%d")
    except ValueError as exc:
        raise ValueError(f"invalid day {value!r}") from exc
    return result


def _clock(value: Any) -> str:
    result = _digits(value, 6, "second")
    try:
        dt.datetime.strptime(result, "%H%M%S")
    except ValueError as exc:
        raise ValueError(f"invalid second {value!r}") from exc
    return result


def _full_timestamp(value: Any) -> tuple[str, str]:
    result = _digits(value, 14, "timestamp")
    try:
        dt.datetime.strptime(result, "%Y%m%d%H%M%S")
    except ValueError as exc:
        raise ValueError(f"invalid timestamp {value!r}") from exc
    return result[:8], result[8:]


def _time_for_day(day: str, value: Any, what: str) -> str:
    text = str(value)
    if isinstance(value, float) and value.is_integer():
        text = str(int(value))
    if len(text) == 14 or (text.endswith(".0") and len(text) == 16):
        timestamp_day, second = _full_timestamp(value)
        if timestamp_day != day:
            _fail(f"{what} timestamp day conflicts with day")
        return second
    return _clock(value)


def _entry_parts(day_value: Any, time_value: Any, what: str) -> tuple[str, str]:
    day = _day(day_value)
    return day, _time_for_day(day, time_value, what)


def _stamp(day: str, second: str) -> dt.datetime:
    return dt.datetime.strptime(day + second, "%Y%m%d%H%M%S")


def _key(record: dict[str, Any], what: str) -> tuple[str, str, int, str]:
    code = str(_field(record, ("code",), what))
    day = _day(_field(record, ("day",), what))
    off = _field(record, ("off",), what)
    if isinstance(off, bool):
        _fail(f"{what} has invalid off")
    try:
        off = int(off)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{what} has invalid off") from exc
    return code, day, off, _time_for_day(day, _field(record, ("t0",), what), what)


def _sha_size(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest(), path.stat().st_size


def _source_ref(path: Path, rows: int, root: Path) -> dict[str, Any]:
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"source path must be under repository root: {path}") from exc
    sha256, size = _sha_size(path)
    return {"path": relative, "sha256": sha256, "size": size, "rows": rows}


def _parquet_records(path: Path, columns: tuple[str, ...], what: str) -> list[dict[str, Any]]:
    parquet = pq.ParquetFile(path)
    missing = set(columns) - set(parquet.schema.names)
    if missing:
        _fail(f"{what} missing required columns: {sorted(missing)}")
    # Explicit projection prevents outcome columns from being materialized.
    return pq.read_table(path, columns=list(columns)).to_pylist()


def _o3_membership(summary: Any) -> None:
    try:
        units = summary["judgment"]["variant_kill_units"]
    except (KeyError, TypeError) as exc:
        raise ValueError("O3 summary must contain judgment.variant_kill_units") from exc
    if not isinstance(units, list) or len(units) != 10 or set(units) != O3_UNITS:
        _fail("O3 judgment.variant_kill_units must be exactly the ten fixed negative-family units")


def _candidate_ids(value: Any) -> set[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        _fail("O4 candidate IDs must be a list of strings")
    result = set(value)
    if len(result) != len(value):
        _fail("O4 candidate IDs must be unique")
    return result


def _candidate_slots(cid: str) -> tuple[str, ...]:
    slots = tuple(cid.split("+"))
    if not cid or any(not slot for slot in slots) or len(set(slots)) != len(slots):
        _fail(f"invalid O4 candidate ID {cid!r}")
    allowed = O4_PRESSURES | {"A", "G@30000", "G@50000"}
    if set(slots) - allowed or not set(slots) & O4_PRESSURES:
        _fail(f"invalid O4 candidate grammar {cid!r}")
    f4 = {slot for slot in slots if slot.startswith("F4@")}
    if len(f4) > 1 or (("G@30000" in slots or "G@50000" in slots) and not f4):
        _fail(f"invalid O4 candidate grammar {cid!r}")
    return slots


def _expected_o4_cids() -> set[str]:
    result = set()
    for f1 in (None, "F1"):
        for f2 in (None, "F2"):
            for f3 in (None, "F3"):
                for f4 in (None, "F4@0.22", "F4@0.35", "F4@0.50"):
                    for guard in ((None, "G@30000", "G@50000") if f4 else (None,)):
                        for avoid in (None, "A"):
                            slots = tuple(slot for slot in (f1, f2, f3, f4, guard, avoid) if slot)
                            if set(slots) & O4_PRESSURES:
                                result.add("+".join(slots))
    return result


def _candidate_bits(slots: tuple[str, ...]) -> tuple[str, ...]:
    mapping = {
        "F1": "o4_netbuy_gt1", "F2": "bit_4", "F3": "bit_10",
        "F4@0.22": "o4_qty_022", "F4@0.35": "o4_qty_035", "F4@0.50": "o4_qty_050",
        "G@30000": "bit_16", "G@50000": "bit_17", "A": "o4_avoid_gap_lt8",
    }
    return tuple(sorted(mapping[slot] for slot in slots))


def _o4_membership(summary: Any) -> dict[str, tuple[str, ...]]:
    try:
        qualified = _candidate_ids(summary["qualification"]["qualified_cids"])
        judgment = summary["judgment"]
        no_positive = _candidate_ids(judgment["no_positive_ev_cids"])
        survivors = _candidate_ids(judgment["survive_cids"])
        weak = _candidate_ids(judgment["weak_signal_cids"])
        n_survive = judgment["n_survive"]
        per_candidate = judgment["per_candidate"]
    except (KeyError, TypeError) as exc:
        raise ValueError("O4 summary missing qualification/judgment membership fields") from exc
    expected = _expected_o4_cids()
    if len(expected) != 158 or len(qualified) != 158 or qualified != expected:
        _fail("O4 qualified candidates must be the explicit 158 sealed grammar IDs")
    if qualified != no_positive or survivors or weak or n_survive != 0:
        _fail("O4 qualified candidates must exactly equal no_positive_ev_cids with no survivors or weak signals")
    if not isinstance(per_candidate, dict) or set(per_candidate) != qualified:
        _fail("O4 judgment.per_candidate must contain exactly the qualified candidates")
    oracle = {}
    for cid in sorted(qualified):
        slots = _candidate_slots(cid)
        details = per_candidate[cid]
        bits = details.get("bits") if isinstance(details, dict) else None
        if not isinstance(details, dict) or details.get("classification") != "no_positive_ev":
            _fail(f"O4 per_candidate classification is not no_positive_ev for {cid}")
        if not isinstance(bits, list) or tuple(sorted(bits)) != _candidate_bits(slots):
            _fail(f"O4 per_candidate bits conflict with sealed grammar for {cid}")
        oracle[cid] = tuple(bits)
    if set(bit for bits in oracle.values() for bit in bits) != O4_CARRIER_BITS:
        _fail("O4 per_candidate bits do not use the sealed carrier")
    return oracle


def _o3_mask(path: Path) -> tuple[dict[tuple[str, str, int, str], bool], int]:
    rows = _parquet_records(path, KEY_COLUMNS + ("variant", "onset_type"), "O3 parquet")
    masks: dict[tuple[str, str, int, str], bool] = {}
    for row in rows:
        key = _key(row, "O3 row")
        if str(row["variant"]) not in O3_VARIANTS or str(row["onset_type"]) != "breakout":
            _fail("O3 parquet contains a non-fixed variant or non-breakout onset_type")
        masks[key] = True
    return masks, len(rows)


def _bool(value: Any, what: str) -> bool:
    if not isinstance(value, bool):
        _fail(f"{what} must be boolean")
    return value


def _unique_bits(rows: list[dict[str, Any]], names: tuple[str, ...], what: str) -> dict[tuple[str, str, int, str], dict[str, bool]]:
    answer: dict[tuple[str, str, int, str], dict[str, bool]] = {}
    for row in rows:
        key = _key(row, what)
        values = {name: _bool(row[name], f"{what}.{name}") for name in names}
        if key in answer:
            _fail(f"{what} contains duplicate key {key}")
        answer[key] = values
    return answer


def _o4_mask(o4_path: Path, d1_path: Path, oracle: dict[str, tuple[str, ...]]) -> tuple[dict[tuple[str, str, int, str], bool], dict[tuple[str, str, int, str], bool], int, int, int]:
    o4_rows = _parquet_records(o4_path, KEY_COLUMNS + O4_O4_COLUMNS, "O4 parquet")
    d1_rows = _parquet_records(d1_path, KEY_COLUMNS + O4_D1_COLUMNS, "D1 parquet")
    o4 = _unique_bits(o4_rows, O4_O4_COLUMNS, "O4 parquet")
    d1 = _unique_bits(d1_rows, O4_D1_COLUMNS, "D1 parquet")
    if len(o4_rows) != len(o4) or len(d1_rows) != len(d1):
        _fail("O4 and D1 row counts must equal unique-key counts")
    if set(o4) != set(d1):
        _fail("O4 and D1 parquet key universes differ")
    simplified, carrier, mismatches = {}, {}, 0
    for key in o4:
        values = o4[key] | d1[key]
        explicit = any(all(values[bit] for bit in bits) for bits in oracle.values())
        simple = values["o4_netbuy_gt1"] or values["bit_4"] or values["bit_10"] or values["o4_qty_022"]
        carrier[key], simplified[key] = explicit, simple
        mismatches += explicit != simple
    if mismatches:
        _fail(f"O4 explicit DNF and simplified carrier differ on {mismatches} rows")
    return simplified, carrier, len(o4_rows), len(d1_rows), mismatches


def _p3_rows(document: Any) -> list[dict[str, Any]]:
    if not isinstance(document, dict):
        _fail("P3 rejoin chunk must be an object")
    rows = []
    for name in ("samples", "exclusions"):
        value = document.get(name)
        if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
            _fail(f"P3 rejoin chunk must contain object list {name}")
        rows.extend(row for row in value if "code6" in row)
    return rows


def _mapping(paths: tuple[Path, Path]) -> tuple[dict[tuple[str, str, str], str], list[int]]:
    mapping: dict[tuple[str, str, str], str] = {}
    counts = []
    for path in paths:
        rows = _p3_rows(_json(path))
        counts.append(len(rows))
        for row in rows:
            identifier = _alias(row, ("code", "종목코드"), str, "P3 identifier")
            day, second = _entry_aliases(row, ("day", "진입일자"), ("t0", "진입시각"), "P3")
            code = str(row["code6"])
            if not _CODE6.fullmatch(code):
                _fail("P3 code6 must be a six-digit literal")
            key = identifier, day, second
            if key in mapping and mapping[key] != code:
                _fail(f"P3 mapping ambiguity for {key}")
            mapping[key] = code
    return mapping, counts


def _ledger(path: Path, mapping: dict[tuple[str, str, str], str]) -> tuple[list[dict[str, Any]], int]:
    trades, ledger_rows = [], 0
    with path.open("r", encoding="utf-8") as handle:
        for ordinal, line in enumerate(handle):
            ledger_rows = ordinal + 1
            record = json.loads(line)
            if not isinstance(record, dict):
                _fail("ledger JSONL row must be an object")
            identifier = _alias(record, ("종목코드", "identifier"), str, "ledger identifier")
            day, buy = _entry_aliases(record, ("진입일자", "entry_day"),
                                      ("진입시각", "매수시간", "buy_second"), "ledger entry")
            if day[:4] not in {"2022", "2023"}:
                continue
            mapped = mapping.get((identifier, day, buy))
            if mapped is None:
                if not _CODE6.fullmatch(identifier):
                    _fail(f"unmapped non-literal identifier for ledger ordinal {ordinal}")
                code, resolution = identifier, "code_literal"
            else:
                code, resolution = mapped, "p3_rejoin"
            sell_day, sell = _alias(record, ("매도시간", "sell_timestamp"), _full_timestamp, "ledger sell")
            if sell_day != day:
                _fail("ledger sell timestamp day conflicts with entry day")
            trades.append({"trade_id": ordinal, "code6": code, "code_resolution": resolution, "entry_day": day,
                           "buy_second": buy, "sell_day": sell_day, "sell_second": sell,
                           "notional": _field(record, ("매수금액", "notional"), "ledger row")})
    return trades, ledger_rows


def _index(masks: dict[tuple[str, str, int, str], bool]) -> dict[tuple[str, str, str], list[tuple[str, str, int, str]]]:
    index: dict[tuple[str, str, str], list[tuple[str, str, int, str]]] = {}
    for key, enabled in masks.items():
        if enabled:
            index.setdefault((key[0], key[1], key[3]), []).append(key)
    for keys in index.values():
        keys.sort()
    return index


def _matches(index: dict[tuple[str, str, str], list[tuple[str, str, int, str]]], code: str, day: str, buy: str, source: str) -> list[dict[str, Any]]:
    target = _stamp(day, buy)
    candidates = ((target, 0), (target - dt.timedelta(seconds=1), 1))
    refs = []
    for candidate, offset in candidates:
        for key in index.get((code, candidate.strftime("%Y%m%d"), candidate.strftime("%H%M%S")), []):
            refs.append({"source": source, "key": [key[0], key[1], key[2], key[3]], "offset": offset})
    return refs


def build(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    paths = {name: Path(getattr(args, name)) for name in ("ledger", "o3_summary", "o4_summary", "o3_parquet", "o4_parquet", "d1_parquet", "p3_chunk1", "p3_chunk2")}
    _o3_membership(_json(paths["o3_summary"]))
    oracle = _o4_membership(_json(paths["o4_summary"]))
    mapping, p3_rows = _mapping((paths["p3_chunk1"], paths["p3_chunk2"]))
    trades, ledger_rows = _ledger(paths["ledger"], mapping)
    o3, o3_rows = _o3_mask(paths["o3_parquet"])
    o4, o4_carrier, o4_rows, d1_rows, o4_mismatches = _o4_mask(paths["o4_parquet"], paths["d1_parquet"], oracle)
    o3_index, o4_index = _index(o3), _index(o4)
    carrier_index = _index({key: True for key in o4_carrier})
    output_trades = []
    for trade in trades:
        o3_refs = _matches(o3_index, trade["code6"], trade["entry_day"], trade["buy_second"], "o3")
        o4_refs = _matches(o4_index, trade["code6"], trade["entry_day"], trade["buy_second"], "o4")
        carrier_refs = _matches(carrier_index, trade["code6"], trade["entry_day"], trade["buy_second"], "o4_carrier")
        output_trades.append({**trade, "o3_mask": bool(o3_refs), "o4_mask": bool(o4_refs),
                              "o4_carrier_match": bool(carrier_refs), "union_mask": bool(o3_refs or o4_refs),
                              "deep_anchor_overlap": bool(o3_refs and o4_refs), "o3_refs": o3_refs, "o4_refs": o4_refs})
    counts = [ledger_rows, 1, 1, o3_rows, o4_rows, d1_rows, p3_rows[0], p3_rows[1]]
    refs = {name: _source_ref(path, rows, root) for (name, path), rows in zip(paths.items(), counts)}
    return {"schema": "g003-static-veto-input-v1", "kind": "outcome_blind_static_veto_input",
            "contract": {"driver": "O3 five-variant union OR O4 F1 OR F2 OR F3 OR F4@0.22", "join": "source t0 equals buy second or exactly one real-clock second before it", "drop_driver": "union_mask", "deep_anchor_overlap": "diagnostic_only", "o4_evaluation_scope": "o4_onset_carrier_only", "o4_explicit_union": "158_candidate_dnf", "o4_simplified_union": "F1_OR_F2_OR_F3_OR_F4_0_22"},
            "sources": refs, "row_flow": {"ledger_scoped": len(trades), "o3_rows": o3_rows, "o4_rows": o4_rows, "d1_rows": d1_rows, "o4_carrier_rows": len(o4_carrier), "o4_equivalence_mismatches": o4_mismatches}, "trades": output_trades}


def publish(path: Path, payload: dict[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            return
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    for name in ("ledger", "o3_summary", "o4_summary", "o3_parquet", "o4_parquet", "d1_parquet", "p3_chunk1", "p3_chunk2", "output"):
        result.add_argument("--" + name.replace("_", "-"), dest=name, required=True)
    return result


def main() -> None:
    args = parser().parse_args()
    payload = build(args)
    publish(Path(args.output), payload)


if __name__ == "__main__":
    main()
