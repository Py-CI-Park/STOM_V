"""Materialize the one sealed, offline G002 frame; no alternate attempt is valid."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import math
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import importlib.util
from typing import Any, Iterable, Mapping

import numpy as np

from alpha_lab.btrack.branches import BRANCH_BITS
from alpha_lab.distill.factorial import CELL_NAMES, evaluate_event, strict_bit
from alpha_lab.distill.replay import precompute_windows

ROOT = Path(__file__).resolve().parents[1]
G002_DIR = ROOT / "docs/research/condition_research/research_runs/alpha_restart_20260710/g002"
EXPERIMENT_ID = "alpha_restart_20260710-g002"
ATTEMPT_ID = "alpha_restart_20260710-g002-attempt-001"
IDENTITY_ATTEMPT_ID = "alpha_restart_20260710-g002-identity-attempt-001"
IDENTITY_ATTEMPT_NAME = "identity_attempt.json"
IDENTITY_STATUS_NAME = "identity_status.json"
CANONICAL = {
    "authority": G002_DIR / "source_authority.json",
    "prereg": ROOT / "docs/research/condition_research/plans/2026-07-16_g002_u7_f0_preregistration.md",
    "launch": G002_DIR / "materialization_launch.json",
    "design": G002_DIR / "identity_design_marker.json",
    "crosswalk": G002_DIR / "identity_crosswalk.json",
    "identity_attempt": G002_DIR / IDENTITY_ATTEMPT_NAME,
    "identity_status": G002_DIR / IDENTITY_STATUS_NAME,
    "attempt": G002_DIR / "materialization_attempt.json",
    "status": G002_DIR / "materialization_status.json",
    "output": G002_DIR / "u7_f0_materialized_input.json",
}
CONTRACT = {"schema": "u7-f0-materialized-input-v2", "factor_coding": {"E0":"synthetic", "E1":"recorded", "D0":"l3_topbook", "D1":"engine_ladder3", "T0":"cap093000", "T1":"terminal092800"}, "years":[2022,2023], "seed":20260715, "replicates":20000, "cell_net_support_pp":[-100,100], "modeled_gap_support_pp":[-200,200], "explanation_threshold":.5}
SOURCES = ("champion_ledger", "p5_receipt", "onset_l3_bank", "d1_onset_clause_bits", "equivalence_receipt", "champion_passport", "sell_expression")
class _SourceReadPaths(dict[str, Path]):
    """Internal read locations and sealed source descriptors from one authority capture."""

    def __init__(self, paths: Mapping[str, Path], descriptors: Mapping[str, Any]) -> None:
        super().__init__(paths)
        self.descriptors = descriptors

TICK_COLUMNS = ("index", "현재가", "시가", "등락율", "초당매수수량", "초당매도수량", "시가총액", "매수총잔량", "매도호가1", "매수호가1", "매수호가2", "매수호가3", "매수잔량1", "매수잔량2", "매수잔량3")
L3_COLUMNS = ("code", "day", "off", "t0", "year", "updown_q", "mktcap_b", "time_b", "l3_net", "l3_labeled", "l3_clause", "l3_exit")
D1_COLUMNS = ("code", "day", "off", "t0") + tuple(f"bit_{n}" for n in range(1,40))
IDENTITY_KEYS = frozenset(("code", "code6", "종목코드", "name", "종목명", "day", "date", "진입일자", "일자", "buy_timestamp", "buy_time", "매수시간"))


def _fail(message: str) -> None: raise ValueError(message)
def _sha256(path: Path) -> str:
    digest=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024), b""): digest.update(block)
    return digest.hexdigest()
def _artifact(path: Path, *, canonical: str | None=None) -> dict[str, Any]:
    if not path.is_file(): _fail(f"missing sealed artifact: {path}")
    return {"path":canonical or path.as_posix(),"sha256":_sha256(path),"size_bytes":path.stat().st_size}
def _reject_sqlite_sidecars(path: Path) -> None:
    sidecars = tuple(path.with_name(path.name + suffix) for suffix in ("-wal", "-shm", "-journal"))
    if any(sidecar.exists() for sidecar in sidecars):
        _fail("SQLite sidecar is present; sealed tick DB must be standalone")
def _physical(item: Mapping[str, Any]) -> str: return f"{item['path']}:{item['size_bytes']}:{item['sha256']}"
def _is_absolute_path(value: Any) -> bool:
    return isinstance(value, str) and bool(re.match(r"^(?:[A-Za-z]:[\\/]|\\\\[^\\/]+[\\/][^\\/]+|/)", value))
def _canonical_project_path(value: Any) -> str:
    if not isinstance(value, str) or not value or _is_absolute_path(value) or "\\" in value or ":" in value:
        _fail("source authority source path is not canonical")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        _fail("source authority source path is not canonical")
    return value
def _canonical_read_path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        _fail("source authority read_path is not canonical")
    if value.startswith("/"):
        parts = value[1:].split("/")
    elif re.match(r"^[A-Za-z]:/", value):
        parts = value[3:].split("/")
    else:
        _fail("source authority read_path is not canonical")
    if not parts or any(part in ("", ".", "..") for part in parts):
        _fail("source authority read_path is not canonical")
    return value
def _authority_source_path(item: Mapping[str, Any]) -> Path:
    value = _canonical_project_path(item["path"])
    if "read_path" in item:
        return Path(_canonical_read_path(item["read_path"]))
    path = (ROOT / Path(*value.split("/"))).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError:
        _fail("source authority source path escapes project root")
    return path
def _capture_json(path: Path, label: str, *, canonical: str | None=None) -> tuple[Mapping[str, Any], dict[str, Any]]:
    if not path.is_file():
        _fail(f"missing sealed artifact: {path}")
    try:
        payload = path.read_bytes()
        value = json.loads(payload.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid {label}") from exc
    artifact = {"path": canonical or path.as_posix(), "sha256": hashlib.sha256(payload).hexdigest(), "size_bytes": len(payload)}
    if not isinstance(value, Mapping):
        _fail(f"invalid {label}")
    return value, artifact
def _same_path(actual: Path, expected: Path, label: str) -> None:
    if actual.resolve() != expected.resolve(): _fail(f"{label} must use canonical G002 path")
def _exclusive_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x",encoding="utf-8") as f: json.dump(value,f,ensure_ascii=False,sort_keys=True); f.write("\n")
def _read_json(path: Path, label: str) -> Mapping[str, Any]:
    try: value=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: raise ValueError(f"invalid {label}") from exc
    if not isinstance(value,Mapping): _fail(f"invalid {label}")
    return value
def _hash(value: Any, label: str) -> str:
    if not isinstance(value,str) or len(value)!=64 or any(c not in "0123456789abcdef" for c in value): _fail(f"invalid {label} hash")
    return value
def _measurement_target(expected_hash: str | None=None) -> dict[str, Any]:
    target = _artifact(ROOT / "scripts/u7_f0_frame_measure.py", canonical="scripts/u7_f0_frame_measure.py")
    if expected_hash is not None and target["sha256"] != _hash(expected_hash, "measurement_target"):
        _fail("measurement target bytes disagree")
    return target

def _records(path: Path) -> list[dict[str, Any]]:
    text=path.read_text(encoding="utf-8"); value=[json.loads(x) for x in text.splitlines() if x.strip()] if path.suffix==".jsonl" else json.loads(text)
    rows=value.get("events") if isinstance(value,Mapping) else value
    if not isinstance(rows,list) or not all(isinstance(row,Mapping) for row in rows): _fail("ledger has no record list")
    return [dict(row) for row in rows]
def _ledger_day(row: Mapping[str, Any]) -> tuple[int, str]:
    value=row.get("진입일자",row.get("day"))
    if isinstance(value,bool) or isinstance(value,(float,np.floating)): _fail("ledger entry day must be an exact eight-digit date")
    day=str(int(value)) if isinstance(value,(int,np.integer)) else value if isinstance(value,str) and value.isdigit() else None
    if day is None or len(day)!=8: _fail("ledger entry day must be an exact eight-digit date")
    try: datetime.strptime(day,"%Y%m%d")
    except ValueError as exc: raise ValueError("ledger entry day is invalid") from exc
    return int(day[:4]),day
def _authoritative_ledger(rows: Iterable[Mapping[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    source=list(rows)
    if len(source)!=671: _fail("authoritative champion ledger must contain exactly 671 rows")
    selected=[]
    for ordinal,row in enumerate(source):
        year,day=_ledger_day(row)
        if year in CONTRACT["years"]: selected.append((ordinal,{**dict(row),"day":day}))
    yearly={year:sum(_ledger_day(row)[0]==year for _,row in selected) for year in CONTRACT["years"]}
    if yearly!={2022:101,2023:197} or len(selected)!=298: _fail("authoritative ledger filter must seal exactly 101/197/298 rows")
    return selected
def _timestamp(value: Any, day: str | None=None) -> str:
    if isinstance(value,bool) or isinstance(value,(float,np.floating)): _fail("timestamp must be an exact integer or digit string")
    text=str(int(value)) if isinstance(value,(int,np.integer)) else value if isinstance(value,str) and value.isdigit() else None
    if text is None: _fail("timestamp must be an exact integer or digit string")
    if len(text)==6 and day is not None: text=day+text
    if len(text)!=14 or (day is not None and text[:8]!=day): _fail("timestamp must be a same-day 14-digit identity")
    try: datetime.strptime(text,"%Y%m%d%H%M%S")
    except ValueError as exc: raise ValueError("invalid timestamp") from exc
    return text
def _next_second(stamp: str) -> str: return (datetime.strptime(stamp,"%Y%m%d%H%M%S")+timedelta(seconds=1)).strftime("%Y%m%d%H%M%S")
def _finite(value: Any, name: str, *, positive: bool=False) -> float:
    if isinstance(value,bool): _fail(f"invalid {name}")
    try: result=float(value)
    except (TypeError,ValueError) as exc: raise ValueError(f"missing {name}") from exc
    if not math.isfinite(result) or (positive and result<=0): _fail(f"invalid {name}")
    return result

def _day_has_rows(conn: sqlite3.Connection, code: str, day: str) -> bool:
    try: return conn.execute(f'SELECT 1 FROM "{code}" WHERE "index" BETWEEN ? AND ? LIMIT 1',(int(day)*1_000_000,int(day)*1_000_000+235959)).fetchone() is not None
    except sqlite3.OperationalError: return False
def _stock_code(conn: sqlite3.Connection, value: Any, day: str) -> str:
    text=str(value)
    if text.isdigit(): candidates=[text] if len(text)==6 else []; method="literal"
    else:
        candidates=[str(x[0]) for x in conn.execute('SELECT "index" FROM stockinfo WHERE "종목명"=?',(text,)).fetchall()]; method="name"
    if not candidates and text.isdigit(): _fail("direct code must be exactly six digits")
    candidates=[c for c in candidates if c.isdigit() and len(c)==6 and _day_has_rows(conn,c,day)]
    if len(candidates)!=1: _fail(f"{method} must resolve to exactly one candidate with rows on trade day")
    return candidates[0]
def _identity(row: Mapping[str,Any], *, l3: bool=False, conn: sqlite3.Connection | None=None) -> tuple[str,int,str,str]:
    day=str(row.get("day",row.get("date",row.get("진입일자",row.get("일자","")))))
    raw=row.get("code",row.get("code6",row.get("종목코드",row.get("name",row.get("종목명","")))))
    code=_stock_code(conn,raw,day) if conn is not None and not l3 else str(raw).zfill(6)
    stamp=_timestamp(row.get("t0",row.get("onset",row.get("onset_time"))) if l3 else row.get("buy_timestamp",row.get("buy_time",row.get("매수시간"))),day)
    if not code.isdigit() or len(code)!=6 or not day.isdigit() or len(day)!=8 or int(day[:4]) not in CONTRACT["years"]: _fail("invalid source identity")
    return code,int(day[:4]),day,stamp
def _ledger_row(item: Mapping[str, Any] | tuple[int, Mapping[str, Any]], fallback_ordinal: int) -> tuple[int, Mapping[str, Any]]:
    if isinstance(item,tuple) and len(item)==2 and isinstance(item[0],int) and isinstance(item[1],Mapping):
        return item
    if not isinstance(item,Mapping): _fail("ledger row is invalid")
    return fallback_ordinal,item
def _identity_rows(rows: Iterable[Mapping[str,Any] | tuple[int, Mapping[str,Any]]], conn: sqlite3.Connection) -> list[dict[str,Any]]:
    # Deliberately construct an allowlisted projection; outcomes never enter identity mode.
    result=[]
    for fallback_ordinal,item in enumerate(rows):
        ordinal,row=_ledger_row(item,fallback_ordinal)
        code,year,day,buy=_identity(row,conn=conn)
        result.append({"code":code,"year":year,"day":day,"buy_timestamp":buy,"ledger_ordinal":ordinal})
    return result
def _material_rows(rows: Iterable[Mapping[str,Any] | tuple[int, Mapping[str,Any]]], conn: sqlite3.Connection) -> list[dict[str,Any]]:
    """Normalize full ledger rows after the separate identity-only commitment."""
    result=[]
    for fallback_ordinal,item in enumerate(rows):
        ordinal,row=_ledger_row(item,fallback_ordinal)
        code,year,day,buy=_identity(row,conn=conn)
        result.append({**dict(row),"code":code,"year":year,"day":day,"buy_timestamp":buy,"ledger_ordinal":ordinal})
    return result

def _joined_l3(l3_path: Path,d1_path: Path,*,identity_only: bool=False,expected: Mapping[str,Any] | None=None,expected_row_count: int=863446) -> list[dict[str,Any]]:
    try: from pyarrow.parquet import ParquetFile
    except ImportError as exc: raise ValueError("pyarrow is required for sealed parquet inputs") from exc
    before=(_artifact(l3_path,canonical=str(l3_path.resolve())),_artifact(d1_path,canonical=str(d1_path.resolve())))
    l3,d1=ParquetFile(l3_path),ParquetFile(d1_path)
    if tuple(l3.schema_arrow.names)!=L3_COLUMNS or tuple(d1.schema_arrow.names)!=D1_COLUMNS or not l3.metadata.num_row_groups or not d1.metadata.num_row_groups: _fail("L3/D1 parquet schema or row groups are not sealed")
    for name,file in (("onset_l3_bank",l3),("d1_onset_clause_bits",d1)):
        fingerprint=hashlib.sha256(file.schema_arrow.serialize().to_pybytes()).hexdigest()
        source=expected.get(name) if expected else None
        if expected and (not isinstance(source,Mapping) or source.get("arrow_schema_sha256")!=fingerprint or source.get("row_groups")!=file.metadata.num_row_groups or source.get("row_count")!=file.metadata.num_rows): _fail(f"{name} Arrow provenance drift")
    l3_columns=L3_COLUMNS[:4] if identity_only else L3_COLUMNS
    a,b=l3.read(columns=list(l3_columns)),d1.read(columns=list(D1_COLUMNS))
    if a.num_rows!=expected_row_count or b.num_rows!=expected_row_count: _fail("L3 and D1 row count is not sealed")
    masks=[]
    for branch,cols in BRANCH_BITS.items():
        mask=np.ones(b.num_rows,dtype=bool)
        for col in cols:
            values=np.asarray(b.column(col).to_numpy(zero_copy_only=False))
            if values.dtype.kind not in "biuf" or not np.isfinite(values).all() or not np.isin(values,(0,1)).all(): _fail(f"{col} must be finite numeric bits")
            mask &= values.astype(bool)
        masks.append((int(branch),mask))
    if np.any(masks[0][1]&masks[1][1]): _fail("D1 branch rows cannot satisfy both branches")
    branch=np.full(b.num_rows,-1,dtype=np.int16)
    for key,mask in masks: branch[mask]=key
    def keys(table: Any) -> list[tuple[str,str,str,str]]: return [(str(code).zfill(6),str(day),str(off),_timestamp(t0,str(day))) for code,day,off,t0 in zip(*(table.column(k).to_pylist() for k in ("code","day","off","t0")))]
    lk,dk=keys(a),keys(b)
    if len(set(lk))!=len(lk) or len(set(dk))!=len(dk) or set(lk)!=set(dk): _fail("L3/D1 exact identity join or duplicates failed")
    bykey=dict(zip(dk,branch)); rows=[]
    for i,key in enumerate(lk):
        if bykey[key]<0: continue
        row={col:a.column(col)[i].as_py() for col in l3_columns}
        rows.append({**row,"code":key[0],"day":key[1],"t0":key[3],"branch":int(bykey[key])})
    if before!=(_artifact(l3_path,canonical=str(l3_path.resolve())),_artifact(d1_path,canonical=str(d1_path.resolve()))): _fail("L3/D1 source drifted during read")
    return rows

def _ledger(row: Mapping[str,Any],day: str,buy: str) -> dict[str,Any]:
    price=_finite(row.get("buy_price",row.get("매수가")),"buy_price",positive=True); amount=_finite(row.get("buy_amount",row.get("매수금액")),"buy_amount",positive=True); qty=_finite(row.get("qty",row.get("수량",row.get("quantity",amount/price))),"qty",positive=True)
    sell_price=_finite(row.get("sell_price",row.get("매도가")),"sell_price",positive=True); sell=_timestamp(row.get("sell_timestamp",row.get("sell_time",row.get("매도시간"))),day)
    if qty!=int(qty) or amount!=price*qty or sell<=buy: _fail("ledger endpoints must be positive and exact")
    return {"buy_price":price,"buy_amount":amount,"qty":int(qty),"sell_price":sell_price,"buy_timestamp":buy,"sell_timestamp":sell}
def _load_rows(conn: sqlite3.Connection,code: str,day: str) -> tuple[np.ndarray,np.ndarray,dict[str,int]]:
    cols=", ".join(f'"{x}"' for x in TICK_COLUMNS); rows=conn.execute(f'SELECT {cols} FROM "{code}" WHERE "index" BETWEEN ? AND ? ORDER BY "index"',(int(day)*1_000_000+90000,int(day)*1_000_000+93000)).fetchall()
    if not rows: _fail("tick rows are absent")
    # Replay's numeric coercion is deliberate: NULL ticks mean zero, not exclusion.
    matrix=np.asarray([[0.0 if x is None else float(x) for x in row] for row in rows],dtype=np.float64)
    if not np.isfinite(matrix).all() or len(set(matrix[:,0].astype(np.int64)))!=len(matrix): _fail("tick rows are nonfinite or duplicated")
    return matrix[:,0].astype(np.int64),matrix[:,1:],{x:i for i,x in enumerate(TICK_COLUMNS[1:])}
def _missing(reason: str) -> dict[str,dict[str,Any]]: return {n:{"status":"missing","entry_price":None,"entry_time":None,"exit_price":None,"exit_time":None,"qty":None,"clause":None,"forced":False,"missing_reason":reason} for n in CELL_NAMES}
def _cells(raw: Mapping[str,Any],buy: str) -> dict[str,dict[str,Any]]:
    out={}
    for name in CELL_NAMES:
        cell=raw[name]; entry,exit_,cause=cell["entry"],cell["exit"],cell["cause"]
        if not entry["quantity"] or exit_["time"] is None: out[name]=_missing(str(cause.get("reason","no_valid_exit")))[name]
        else:
            forced=bool(exit_.get("forced",False))
            kind=cause.get("kind")
            raw_clause=cause.get("clause")
            if kind in {"cap","last_sell"} and not forced: _fail("cap/LastSell exits must be forced")
            if forced:
                if kind not in {"cap","last_sell"} or isinstance(raw_clause,bool) or raw_clause not in (None,0): _fail("forced cap/LastSell exits must use clause 0")
                clause=0
            else:
                if isinstance(raw_clause,bool) or not isinstance(raw_clause,int) or raw_clause <= 0: _fail("non-forced cells must record a positive integer fired clause")
                clause=raw_clause
            exit_time=_timestamp(exit_["time"], buy[:8])
            if exit_time <= buy or exit_time > buy[:8] + ("093000" if name.endswith("T0") else "092800"):
                _fail("cell exit violates its sealed horizon")
            out[name]={"status":"matched","entry_price":entry["price"],"entry_time":buy,"exit_price":exit_["price"],"exit_time":exit_time,"qty":entry["quantity"],"clause":clause,"forced":forced,"missing_reason":None}
    return out
def open_readonly(path: Path) -> sqlite3.Connection:
    _reject_sqlite_sidecars(path)
    conn=sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro",uri=True); conn.execute("PRAGMA query_only=ON")
    if conn.execute("PRAGMA query_only").fetchone()[0]!=1: _fail("query_only unavailable")
    return conn

def build_identity_crosswalk(ledger: Iterable[Mapping[str,Any]],l3: Iterable[Mapping[str,Any]]) -> dict[str,Any]:
    led,joined=list(ledger),list(l3); lids=[(x["code"],x["year"],x["day"],x["buy_timestamp"]) for x in led]
    if len(led)!=298 or {y:sum(x[1]==y for x in lids) for y in CONTRACT["years"]}!={2022:101,2023:197} or len(set(lids))!=len(lids): _fail("identity crosswalk must be the fixed unique 298 ledger universe")
    candidate_rows=[(str(x["code"]).zfill(6),str(x["day"]),_next_second(_timestamp(x["t0"],str(x["day"]))),x["branch"]) for x in joined]
    candidate_keys=[row[:3] for row in candidate_rows]
    if len(set(candidate_keys))!=len(candidate_keys): _fail("ambiguous projected (code, day, t0+1) join")
    candidates={key:branch for *key,branch in candidate_rows}
    return {"schema":"u7-f0-identity-crosswalk-v2","experiment_id":EXPERIMENT_ID,"attempt_id":ATTEMPT_ID,"identity_attempt_id":IDENTITY_ATTEMPT_ID,"events":[{"identity":{"code":c,"year":y,"day":d,"buy_time":buy},"ledger_ordinal":row["ledger_ordinal"],"branch":candidates.get((c,d,buy)),"match_status":"matched" if (c,d,buy) in candidates else "engine_only"} for row,(c,y,d,buy) in zip(led,lids)]}
SELL_CODE_SHA256 = "8ef01e0ef2087ec95ac6b358b6f5c710414f3eb4dd401b01cc8162877f911c07"

CHAMPION_CONDITION_ID = "rr8_12_turnover_min_902=1.5"
CHAMPION_BUY_STRATEGY_ID = "GATE_rr8_12_turnover_min_902_1_5_B"
CANONICAL_LEDGER_PATH = "docs/research/condition_research/research_runs/alpha_lab_20260705/distill/champion_ledger.jsonl"
P5_IDENTITY_FIELDS = ["전략명", "종목코드", "진입일자", "진입시각"]
def _p5_receipt(value: Mapping[str, Any]) -> None:
    expected = {
        "program": "P5", "phase": "phase0_champion_ledger_wiring", "unique": 671,
        "ledger_records": 671, "ledger_schema_version": 1, "source_csv_access": "read-only",
        "champion_condition_id": CHAMPION_CONDITION_ID, "champion_buy_strategy_id": CHAMPION_BUY_STRATEGY_ID,
        "ledger_path": CANONICAL_LEDGER_PATH, "identity_fields": P5_IDENTITY_FIELDS, "dedup_policy": "first-wins, scan order = filename ascending (earliest run wins)",
    }
    if any(value.get(key) != required for key, required in expected.items()):
        _fail("P5 receipt semantics are invalid")
    entries = value.get("sources")
    if not isinstance(entries, list) or not entries:
        _fail("P5 receipt source entries are invalid")
    if any(not isinstance(entry, Mapping) or entry.get("source") != CHAMPION_BUY_STRATEGY_ID for entry in entries):
        _fail("P5 receipt must bind the exact champion source strategy ID")
    expected_years = {2022: 101, 2023: 197}
    observed = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            _fail("P5 receipt source entry is invalid")
        day_range = entry.get("entry_day_range")
        if not isinstance(day_range, (list, tuple)) or len(day_range) != 2:
            _fail("P5 receipt entry_day_range is invalid")
        try:
            start, end = (int(day) for day in day_range)
        except (TypeError, ValueError) as exc:
            raise ValueError("P5 receipt entry_day_range is invalid") from exc
        if start > end:
            _fail("P5 receipt source range is invalid")
        year = start // 10000
        if year not in expected_years:
            continue
        if end // 10000 != year:
            continue
        if entry.get("rows") == expected_years[year] and entry.get("kept") == expected_years[year] and entry.get("dropped") == 0:
            observed[year] = observed.get(year, 0) + 1
    if observed != {2022: 1, 2023: 1}:
        _fail("P5 receipt lacks exactly one required year source entry")

def _equivalence_receipt(value: Mapping[str, Any]) -> None:
    expected = {
        "kind": "v2_labeler_equivalence", "sealed_threshold": .999, "n_ledger_rows": 671,
        "n_trades": 667, "n_time_match": 667, "n_price_match": 667, "n_both_match": 667,
        "exclusions": {"foreign_sell_condition": 4}, "cond_match_rate": 1.0,
        "equivalence_pct": 100.0, "gate_pass": True, "mismatches": [],
    }
    if any(value.get(key) != required for key, required in expected.items()):
        _fail("equivalence receipt semantics are invalid")

def _passport(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if re.search(rf"^\|\s*sell_code_sha256\s*\|\s*`{SELL_CODE_SHA256}`\s*\|", text, re.MULTILINE) is None:
        _fail("champion passport does not declare the sealed sell code hash")

def _sell_expression(path: Path) -> None:
    if _sha256(path) != SELL_CODE_SHA256:
        _fail("sell expression bytes do not match the sealed sell code hash")

def _validate_semantic_artifact(key: str, path: Path) -> None:
    if key == "p5_receipt":
        _p5_receipt(_read_json(path, "P5 receipt"))
    elif key == "equivalence_receipt":
        _equivalence_receipt(_read_json(path, "equivalence receipt"))
    elif key == "champion_passport":
        _passport(path)
    elif key == "sell_expression":
        _sell_expression(path)


def _tick_commitment(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value,Mapping) or set(value)!={"path","sha256","size_bytes","physical_id"}: _fail(f"{label} tick DB commitment is malformed")
    path=value["path"]
    if not _is_absolute_path(path): _fail(f"{label} tick DB path must be canonical and external")
    _hash(value["sha256"],f"{label}.sha256")
    if isinstance(value["size_bytes"],bool) or not isinstance(value["size_bytes"],int) or value["size_bytes"]<=0 or not isinstance(value["physical_id"],str) or not value["physical_id"]: _fail(f"{label} tick DB identity is malformed")
    if value["physical_id"]!=f"{path}:{value['size_bytes']}:{value['sha256']}": _fail(f"{label} tick DB physical identity drift")
    return value
def _validate_authority(authority: Mapping[str,Any]) -> None:
    required={"schema","state","experiment_id","attempt_id","identity_attempt_id","preregistration_sha256","materializer_sha256","measurement_sha256","sources","semantic_receipts","tick_db"}
    if set(authority)!=required or authority["schema"]!="u7-f0-source-authority-v3" or authority["state"]!="sealed" or authority["experiment_id"]!=EXPERIMENT_ID or authority["attempt_id"]!=ATTEMPT_ID or authority["identity_attempt_id"]!=IDENTITY_ATTEMPT_ID: _fail("source authority semantics are not sealed")
    sources=authority["sources"]
    if not isinstance(sources,Mapping) or set(sources)!=set(SOURCES) or not isinstance(authority["semantic_receipts"],Mapping) or set(authority["semantic_receipts"])!={"p5_receipt","equivalence_receipt","champion_passport","sell_expression"}: _fail("source authority receipt binding is invalid")
    for key,item in sources.items():
        fields={"path","sha256","size_bytes"}
        if key in ("onset_l3_bank","d1_onset_clause_bits"): fields|={"arrow_schema_sha256","row_groups","row_count"}
        if isinstance(item, Mapping) and "read_path" in item:
            fields.add("read_path")
        if not isinstance(item,Mapping) or set(item)!=fields or not isinstance(item["path"],str) or not item["path"]:
            _fail("source authority source descriptor is invalid")
        _canonical_project_path(item["path"])
        if "read_path" in item:
            _canonical_read_path(item["read_path"])
        _hash(item["sha256"],f"sources.{key}.sha256")
        if isinstance(item["size_bytes"],bool) or not isinstance(item["size_bytes"],int) or item["size_bytes"]<=0:
            _fail("source authority source descriptor is invalid")
        if key in ("onset_l3_bank","d1_onset_clause_bits"):
            _hash(item["arrow_schema_sha256"],f"sources.{key}.arrow_schema_sha256")
            if any(isinstance(item[field],bool) or not isinstance(item[field],int) or item[field] <= 0 for field in ("row_groups","row_count")):
                _fail("source authority Arrow binding is invalid")
    _tick_commitment(authority["tick_db"],"source authority")
    for key in ("preregistration_sha256","materializer_sha256","measurement_sha256"):_hash(authority[key],key)
    for key,receipt in authority["semantic_receipts"].items():
        if not isinstance(receipt, Mapping): _fail(f"{key} semantic receipt authority binding is invalid")
def _arrow_metadata(sources: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {key:{field:sources[key][field] for field in ("arrow_schema_sha256","row_groups","row_count")} for key in ("onset_l3_bank","d1_onset_clause_bits")}
def _seal_post(physical: dict[str, Any], paths: Mapping[str, tuple[Path, Mapping[str, Any]]]) -> None:
    for key,(path,before) in paths.items():
        artifact=_artifact(path,canonical=before["path"])
        if artifact["sha256"]!=before["sha256"] or artifact["size_bytes"]!=before["size_bytes"]: _fail("consumed artifact drifted during materialization")
        physical.setdefault(key,{"pre":{"sha256":before["sha256"],"size_bytes":before["size_bytes"],"physical_id":_physical(before)}})["post"]={"sha256":artifact["sha256"],"size_bytes":artifact["size_bytes"],"physical_id":_physical(artifact)}
def _provenance(ledger: Path,l3: Path,d1: Path,db: Path) -> tuple[dict[str,Any], _SourceReadPaths]:
    _reject_sqlite_sidecars(db)
    authority,authority_artifact=_capture_json(CANONICAL["authority"],"source authority",canonical=str(CANONICAL["authority"].relative_to(ROOT).as_posix())); _validate_authority(authority)
    sources={}; source_read_paths={}
    for key,item in authority["sources"].items():
        path=_authority_source_path(item)
        got=_artifact(path,canonical=item["path"])
        if got["sha256"]!=item["sha256"] or got["size_bytes"]!=item["size_bytes"]:
            _fail("source authority bytes disagree")
        if key in authority["semantic_receipts"]:
            _validate_semantic_artifact(key, path)
        sources[key]=got
        source_read_paths[key]=path
    expected_paths={"champion_ledger":ledger,"onset_l3_bank":l3,"d1_onset_clause_bits":d1}
    for key,path in expected_paths.items():
        if path.resolve()!=_authority_source_path(authority["sources"][key]).resolve() or sources[key]!=_artifact(path,canonical=authority["sources"][key]["path"]):
            _fail("input source authority drift")
    prereg=_artifact(CANONICAL["prereg"],canonical=str(CANONICAL["prereg"].relative_to(ROOT).as_posix()))
    launch,launch_artifact=_capture_json(CANONICAL["launch"],"materialization launch",canonical=str(CANONICAL["launch"].relative_to(ROOT).as_posix()))
    measurement_target=_measurement_target(authority["measurement_sha256"])
    launch_required={"schema","state","experiment_id","attempt_id","identity_attempt_id","source_authority_sha256","preregistration_sha256","measurement_sha256","tick_db"}
    if set(launch)!=launch_required or launch["schema"]!="u7-f0-materialization-launch-v2" or launch["state"]!="sealed" or launch["experiment_id"]!=EXPERIMENT_ID or launch["attempt_id"]!=ATTEMPT_ID or launch["identity_attempt_id"]!=IDENTITY_ATTEMPT_ID:
        _fail("materialization launch is not the sealed canonical attempt")
    if launch["source_authority_sha256"]!=authority_artifact["sha256"] or launch["preregistration_sha256"]!=prereg["sha256"] or launch["measurement_sha256"]!=measurement_target["sha256"] or launch["tick_db"]!=authority["tick_db"]:
        _fail("materialization launch hash binding drift")
    if prereg["sha256"]!=authority["preregistration_sha256"] or authority["materializer_sha256"]!=_sha256(Path(__file__)): _fail("preregistration or materializer binding drift")
    if db.resolve()!=Path(authority["tick_db"]["path"]).resolve(): _fail("tick DB must use the source-authority physical path")
    tick=_artifact(db,canonical=authority["tick_db"]["path"])
    if tick["sha256"]!=authority["tick_db"]["sha256"] or tick["size_bytes"]!=authority["tick_db"]["size_bytes"] or _physical(tick)!=authority["tick_db"]["physical_id"]: _fail("tick DB source authority drift")
    materializer=_artifact(Path(__file__),canonical="scripts/u7_f0_materialize.py")
    physical={key:{"pre":{"sha256":item["sha256"],"size_bytes":item["size_bytes"],"physical_id":_physical(item)},"post":None} for key,item in sources.items()}
    for key,item in (("tick_db",tick),("source_authority",authority_artifact),("preregistration",prereg),("launch",launch_artifact),("materializer",materializer),("measurement_target",measurement_target)):
        physical[key]={"pre":{"sha256":item["sha256"],"size_bytes":item["size_bytes"],"physical_id":_physical(item)},"post":None}
    provenance={"schema":"u7-f0-provenance-v3","source_authority":authority_artifact,"sources":sources,"preregistration":prereg,"launch":launch_artifact,"cell_definition_binding":{"champion_sell_sha256":sources["sell_expression"]["sha256"],"equivalence_receipt_sha256":sources["equivalence_receipt"]["sha256"],"champion_passport_sha256":sources["champion_passport"]["sha256"],"states":{"equivalence":"validated","passport":"validated"}},"physical_inputs":physical,"tick_db":{**tick,"physical_id":_physical(tick),"read_only":True,"query_only":True,"pre":{"sha256":tick["sha256"],"size_bytes":tick["size_bytes"],"physical_id":_physical(tick)},"post":None},"materializer":materializer,"measurement_target":measurement_target}
    return provenance,_SourceReadPaths(source_read_paths,authority["sources"])

def _validate_snapshot(snapshot: Mapping[str,Any]) -> None:
    """Import only the measurement validator whose committed bytes match provenance."""
    target=snapshot.get("provenance",{}).get("measurement_target") if isinstance(snapshot.get("provenance"),Mapping) else None
    if not isinstance(target,Mapping):
        _fail("strict consumer validator target is unavailable")
    measurement_target=_measurement_target(target.get("sha256"))
    if dict(target) != measurement_target:
        _fail("strict consumer validator target drift")
    consumer_path=ROOT / measurement_target["path"]
    spec=importlib.util.spec_from_file_location("u7_f0_frame_measure_contract",consumer_path)
    if spec is None or spec.loader is None: _fail("strict consumer validator is unavailable")
    consumer=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(consumer)
    validator=getattr(consumer,"validate_snapshot",None)
    if not callable(validator): _fail("strict consumer validator is unavailable")
    validator(snapshot)

def build_snapshot(ledger_rows: Iterable[Mapping[str,Any]],l3_rows: Iterable[Mapping[str,Any]],conn: sqlite3.Connection,*,provenance: Mapping[str,Any]) -> dict[str,Any]:
    ledger,l3=list(ledger_rows),list(l3_rows); lids=[(x["code"],x["year"],x["day"],x["buy_timestamp"]) for x in ledger]
    if len(ledger)!=298 or {y:sum(x[1]==y for x in lids) for y in CONTRACT["years"]}!={2022:101,2023:197} or len(set(lids))!=len(lids): _fail("sealed champion ledger must be unique 101/197 298 rows")
    fields=[_ledger(row,day,buy) for row,(_code,_year,day,buy) in zip(ledger,lids)]
    joined_rows=[(str(x["code"]).zfill(6),str(x["day"]),_next_second(_timestamp(x["t0"],str(x["day"]))),x) for x in l3]
    join_keys=[row[:3] for row in joined_rows]
    if len(set(join_keys))!=len(join_keys): _fail("ambiguous projected (code, day, t0+1) join")
    join={tuple(key):row for *key,row in joined_rows}
    events=[]; used=set()
    for row,field,(code,year,day,buy) in zip(ledger,fields,lids):
        hit=join.get((code,day,buy)); status="engine_only"; reason="no_exact_l3_t0_plus_one_join"; net=None; branch=None; l3_exit=None; l3_clause=None; cells=_missing(reason)
        if hit is not None:
            used.add(id(hit)); branch=int(hit["branch"]); net=_finite(hit.get("l3_net"),"l3_net_ref")
            l3_exit=hit.get("l3_exit"); l3_clause=hit.get("l3_clause")
            try:
                idxs,arr,ci=_load_rows(conn,code,day); raw=evaluate_event(row,idxs,arr,ci,precompute_windows(arr,ci),branch=str(branch)); cells=_cells(raw["cells"],buy)
                if any(x["status"]!="matched" for x in cells.values()): status="excluded"; reason="factorial_cell_unavailable"; cells=_missing(reason)
                else: status="matched"; reason=None
            except (KeyError,TypeError,ValueError,OverflowError) as exc: status="excluded"; reason=str(exc); cells=_missing(reason)
        events.append({"identity":{"code":code,"year":year,"day":day,"buy_time":buy},"status":status,"reason":reason,"ledger":field,"l3_net_ref":net,"branch":branch,"cells":cells})
    offline=[{"identity":{"code":c,"year":y,"day":d,"buy_time":_next_second(t)},"status":"offline_only","reason":"no_champion_ledger_exact_t0_plus_one_join"} for c,y,d,t in ((str(x["code"]).zfill(6),int(str(x["day"])[:4]),str(x["day"]),_timestamp(x["t0"],str(x["day"]))) for x in l3) if id(join[(c,d,_next_second(t))]) not in used]
    counts={s:sum(x["status"]==s for x in events) for s in ("matched","engine_only","excluded")}
    committed_provenance=dict(provenance)
    committed_provenance["endpoint_reconciliation"]=[{"identity":event["identity"],"engine":{"ledger_sell_price":event["ledger"]["sell_price"],"ledger_sell_timestamp":event["ledger"]["sell_timestamp"],"cell_sell_price":event["cells"]["E1D1T1"]["exit_price"],"cell_sell_timestamp":event["cells"]["E1D1T1"]["exit_time"],"parity":event["ledger"]["sell_price"]==event["cells"]["E1D1T1"]["exit_price"] and event["ledger"]["sell_timestamp"]==event["cells"]["E1D1T1"]["exit_time"]},"l3":{"bank_exit_timestamp":hit["l3_exit"],"bank_clause":hit["l3_clause"],"cell_exit_timestamp":event["cells"]["E0D0T0"]["exit_time"],"cell_clause":event["cells"]["E0D0T0"]["clause"],"parity":hit["l3_exit"]==event["cells"]["E0D0T0"]["exit_time"] and hit["l3_clause"]==event["cells"]["E0D0T0"]["clause"]}} for event,hit in ((event,join.get((event["identity"]["code"],event["identity"]["day"],event["identity"]["buy_time"]))) for event in events if event["status"]=="matched")]
    snapshot={"contract":dict(CONTRACT),"provenance":committed_provenance,"flow":{"engine_rows":298,**counts,"offline_only":len(offline),"conservation_ok":sum(counts.values())==298,"year_rows":{"2022":101,"2023":197}},"events":events,"offline_only":offline,"side_effect_counters":{"engine_calls":0,"db_writes":0,"strategy_registrations":0,"outcome_executions":0}}
    return snapshot

def _reserve_identity() -> dict[str,Any]:
    record={"schema":"u7-f0-identity-attempt-v1","experiment_id":EXPERIMENT_ID,"identity_attempt_id":IDENTITY_ATTEMPT_ID,"state":"reserved"}; _exclusive_json(CANONICAL["identity_attempt"],record); return record
def _identity_status(state: str) -> None:
    _exclusive_json(CANONICAL["identity_status"],{"schema":"u7-f0-identity-status-v1","experiment_id":EXPERIMENT_ID,"identity_attempt_id":IDENTITY_ATTEMPT_ID,"state":state})
def _reserve() -> dict[str,Any]:
    record={"schema":"u7-f0-materialization-attempt-v3","experiment_id":EXPERIMENT_ID,"attempt_id":ATTEMPT_ID,"identity_attempt_id":IDENTITY_ATTEMPT_ID,"state":"reserved"}; _exclusive_json(CANONICAL["attempt"],record); return record
def _status(state: str) -> None: _exclusive_json(CANONICAL["status"],{"schema":"u7-f0-materialization-status-v3","experiment_id":EXPERIMENT_ID,"attempt_id":ATTEMPT_ID,"identity_attempt_id":IDENTITY_ATTEMPT_ID,"state":state})
def _check_paths(args: argparse.Namespace, *, identity: bool) -> None:
    for name,key in (("evidence","launch"),("design_marker","design"),("identity_output" if identity else "identity_input","crosswalk")):
        path=getattr(args,name)
        if path is None: _fail(f"{name} is required")
        _same_path(path,CANONICAL[key],name)
    if not identity:
        for name,key in (("output","output"),("attempt","attempt"),("status","status")): _same_path(getattr(args,name),CANONICAL[key],name)

def _sealed_physical(descriptor: Mapping[str, Any]) -> dict[str, Any]:
    return {"pre":{"sha256":descriptor["sha256"],"size_bytes":descriptor["size_bytes"],"physical_id":_physical(descriptor)},"post":{"sha256":descriptor["sha256"],"size_bytes":descriptor["size_bytes"],"physical_id":_physical(descriptor)}}
def _validate_identity_closure(crosswalk: Mapping[str, Any], marker: Mapping[str, Any], provenance: Mapping[str, Any], crosswalk_artifact: Mapping[str, Any], authority_sources: Mapping[str, Any]) -> None:
    crosswalk_keys={"schema","experiment_id","attempt_id","identity_attempt_id","events","source_custody"}
    marker_keys={"schema","experiment_id","attempt_id","identity_attempt_id","full_attempt_id","state","crosswalk_sha256","source_authority_sha256","preregistration_sha256","materializer_sha256","measurement_sha256","tick_db","source_custody"}
    if set(crosswalk)!=crosswalk_keys or set(marker)!=marker_keys or crosswalk.get("schema")!="u7-f0-identity-crosswalk-v2" or marker.get("schema")!="u7-f0-identity-design-marker-v2" or marker.get("state")!="sealed" or any(item.get(key)!=value for item in (crosswalk,marker) for key,value in (("experiment_id",EXPERIMENT_ID),("attempt_id",ATTEMPT_ID),("identity_attempt_id",IDENTITY_ATTEMPT_ID))) or marker.get("full_attempt_id")!=ATTEMPT_ID:
        _fail("full mode requires canonical identity schemas")
    expected_tick={**provenance["tick_db"],"post":provenance["tick_db"]["pre"]}
    expected_physical={key:{"pre":value["pre"],"post":value["pre"]} for key,value in provenance["physical_inputs"].items()}
    if expected_physical["tick_db"] != {"pre":expected_tick["pre"],"post":expected_tick["pre"]}:
        _fail("full mode tick custody is not closed")
    expected_marker_physical={**expected_physical,"identity_crosswalk":_sealed_physical(crosswalk_artifact)}
    for item,physical in ((crosswalk,expected_physical),(marker,expected_marker_physical)):
        custody=item.get("source_custody")
        if not isinstance(custody,Mapping) or set(custody)!={"physical_inputs","arrow_metadata","tick_db"} or custody.get("physical_inputs")!=physical or custody.get("arrow_metadata")!=_arrow_metadata(authority_sources) or custody.get("tick_db")!=expected_tick:
            _fail("full mode lacks exact source custody closure")
    if marker.get("crosswalk_sha256")!=crosswalk_artifact["sha256"] or marker.get("source_authority_sha256")!=provenance["source_authority"]["sha256"] or marker.get("preregistration_sha256")!=provenance["preregistration"]["sha256"] or marker.get("materializer_sha256")!=provenance["materializer"]["sha256"] or marker.get("measurement_sha256")!=provenance["measurement_target"]["sha256"] or marker.get("tick_db")!=expected_tick:
        _fail("full mode marker binding drift")
    events=crosswalk["events"]
    if not isinstance(events,list) or len(events)!=298:
        _fail("full mode crosswalk universe is invalid")
    identities=set(); ordinals=set(); annual={2022:0,2023:0}
    for event in events:
        if not isinstance(event,Mapping) or set(event)!={"identity","ledger_ordinal","branch","match_status"}:
            _fail("full mode crosswalk event is invalid")
        identity=event["identity"]
        if not isinstance(identity,Mapping) or set(identity)!={"code","year","day","buy_time"}:
            _fail("full mode crosswalk identity is invalid")
        code,year,day,buy=identity["code"],identity["year"],identity["day"],identity["buy_time"]
        if not isinstance(code,str) or not code.isdigit() or len(code)!=6 or isinstance(year,bool) or not isinstance(year,int) or year not in CONTRACT["years"] or not isinstance(day,str) or not re.fullmatch(r"\d{8}",day) or year!=int(day[:4]) or not isinstance(buy,str) or not re.fullmatch(r"\d{14}",buy) or buy[:8]!=day:
            _fail("full mode crosswalk identity is invalid")
        try:
            datetime.strptime(day,"%Y%m%d"); datetime.strptime(buy,"%Y%m%d%H%M%S")
        except ValueError:
            _fail("full mode crosswalk identity is invalid")
        key=(code,year,day,buy)
        ordinal=event["ledger_ordinal"]
        status,branch=event["match_status"],event["branch"]
        if key in identities or isinstance(ordinal,bool) or not isinstance(ordinal,int) or ordinal not in range(671) or ordinal in ordinals or status not in ("matched","engine_only") or (status=="engine_only" and branch is not None) or (status=="matched" and (isinstance(branch,bool) or branch not in (902,905))):
            _fail("full mode crosswalk event is invalid")
        identities.add(key); ordinals.add(ordinal); annual[year]+=1
    if annual!={2022:101,2023:197}:
        _fail("full mode crosswalk annual universe is invalid")
def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("ledger","l3","d1_bits","tick_db","output","attempt","status","evidence","identity_output","identity_input","design_marker"): parser.add_argument("--"+name.replace("_","-"),type=Path)
    parser.add_argument("--identity-only",action="store_true"); args=parser.parse_args()
    if any(getattr(args,x) is None for x in ("ledger","l3","d1_bits","tick_db")): _fail("ledger, l3, d1-bits, and tick-db are required")
    _check_paths(args,identity=args.identity_only); _reject_sqlite_sidecars(args.tick_db)
    if args.identity_only:
        if any(path.exists() for path in (args.identity_output,args.design_marker,CANONICAL["identity_attempt"],CANONICAL["identity_status"])): _fail("identity attempt/status/crosswalk/design is immutable")
        provenance,source_read_paths=_provenance(args.ledger,args.l3,args.d1_bits,args.tick_db)
        _reserve_identity()
        try:
            ledger=_authoritative_ledger(_records(args.ledger))
            with open_readonly(args.tick_db) as conn: identities=_identity_rows(ledger,conn)
            _reject_sqlite_sidecars(args.tick_db)
            crosswalk=build_identity_crosswalk(identities,_joined_l3(args.l3,args.d1_bits,identity_only=True,expected=source_read_paths.descriptors))
            custody_paths={key:(source_read_paths[key],provenance["sources"][key]) for key in SOURCES}
            custody_paths.update({"tick_db":(args.tick_db,provenance["tick_db"]),"source_authority":(CANONICAL["authority"],provenance["source_authority"]),"preregistration":(CANONICAL["prereg"],provenance["preregistration"]),"launch":(CANONICAL["launch"],provenance["launch"]),"materializer":(Path(__file__),provenance["materializer"]),"measurement_target":(ROOT / provenance["measurement_target"]["path"],provenance["measurement_target"])})
            _reject_sqlite_sidecars(args.tick_db)
            _seal_post(provenance["physical_inputs"],custody_paths)
            tick_post=provenance["physical_inputs"]["tick_db"]["post"]
            provenance["tick_db"]["post"]=tick_post
            crosswalk["source_custody"]={"physical_inputs":provenance["physical_inputs"],"arrow_metadata":_arrow_metadata(source_read_paths.descriptors),"tick_db":provenance["tick_db"]}
            _exclusive_json(args.identity_output,crosswalk)
            crosswalk_artifact=_artifact(args.identity_output,canonical=str(args.identity_output.resolve()))
            design_physical={**provenance["physical_inputs"],"identity_crosswalk":{"pre":{"sha256":crosswalk_artifact["sha256"],"size_bytes":crosswalk_artifact["size_bytes"],"physical_id":_physical(crosswalk_artifact)},"post":{"sha256":crosswalk_artifact["sha256"],"size_bytes":crosswalk_artifact["size_bytes"],"physical_id":_physical(crosswalk_artifact)}}}
            _exclusive_json(args.design_marker,{"schema":"u7-f0-identity-design-marker-v2","experiment_id":EXPERIMENT_ID,"attempt_id":ATTEMPT_ID,"identity_attempt_id":IDENTITY_ATTEMPT_ID,"full_attempt_id":ATTEMPT_ID,"state":"sealed","crosswalk_sha256":crosswalk_artifact["sha256"],"source_authority_sha256":provenance["source_authority"]["sha256"],"preregistration_sha256":provenance["preregistration"]["sha256"],"materializer_sha256":provenance["materializer"]["sha256"],"measurement_sha256":provenance["measurement_target"]["sha256"],"tick_db":provenance["tick_db"],"source_custody":{"physical_inputs":design_physical,"arrow_metadata":_arrow_metadata(source_read_paths.descriptors),"tick_db":provenance["tick_db"]}})
        except Exception:
            _identity_status("failed"); raise
        _identity_status("succeeded"); return
    if any(getattr(args,x) is None for x in ("output","attempt","status","identity_input","design_marker")): _fail("full mode requires sealed canonical artifacts")
    if any(x.exists() for x in (args.output,args.attempt,args.status)): _fail("canonical attempt is already consumed")
    identity_attempt=_read_json(CANONICAL["identity_attempt"],"identity attempt")
    identity_status=_read_json(CANONICAL["identity_status"],"identity status")
    if identity_attempt!={"schema":"u7-f0-identity-attempt-v1","experiment_id":EXPERIMENT_ID,"identity_attempt_id":IDENTITY_ATTEMPT_ID,"state":"reserved"} or identity_status!={"schema":"u7-f0-identity-status-v1","experiment_id":EXPERIMENT_ID,"identity_attempt_id":IDENTITY_ATTEMPT_ID,"state":"succeeded"}: _fail("full mode requires the succeeded canonical identity attempt")
    marker,marker_before=_capture_json(args.design_marker,"design marker",canonical=str(args.design_marker.resolve()))
    provenance,source_read_paths=_provenance(args.ledger,args.l3,args.d1_bits,args.tick_db)
    crosswalk,crosswalk_artifact=_capture_json(args.identity_input,"identity crosswalk",canonical=str(args.identity_input.resolve()))
    _validate_identity_closure(crosswalk,marker,provenance,crosswalk_artifact,provenance["sources"])
    attempt=_reserve()
    try:
        ledger=_authoritative_ledger(_records(args.ledger))
        with open_readonly(args.tick_db) as conn:
            material=_material_rows(ledger,conn)
            snapshot=build_snapshot(material,_joined_l3(args.l3,args.d1_bits,expected=source_read_paths.descriptors),conn,provenance=provenance)
        _reject_sqlite_sidecars(args.tick_db)
        projected=[{"identity":event["identity"],"ledger_ordinal":row["ledger_ordinal"],"branch":event["branch"],"match_status":"matched" if event["status"]!="engine_only" else "engine_only"} for row,event in zip(material,snapshot["events"])]
        if crosswalk.get("events")!=projected: _fail("identity crosswalk does not equal recomputed universe")
        snapshot["provenance"]["identity_crosswalk"]=crosswalk_artifact
        snapshot["provenance"]["design_marker"]=marker_before
        custody_paths={key:(source_read_paths[key],provenance["sources"][key]) for key in SOURCES}
        custody_paths.update({"tick_db":(args.tick_db,provenance["tick_db"]),"source_authority":(CANONICAL["authority"],provenance["source_authority"]),"preregistration":(CANONICAL["prereg"],provenance["preregistration"]),"launch":(CANONICAL["launch"],provenance["launch"]),"materializer":(Path(__file__),provenance["materializer"]),"measurement_target":(ROOT / provenance["measurement_target"]["path"],provenance["measurement_target"]),"identity_crosswalk":(args.identity_input,crosswalk_artifact),"design_marker":(args.design_marker,marker_before)})
        _reject_sqlite_sidecars(args.tick_db)
        _seal_post(snapshot["provenance"]["physical_inputs"],custody_paths)
        snapshot["provenance"]["tick_db"]["post"]=snapshot["provenance"]["physical_inputs"]["tick_db"]["post"]
        _validate_snapshot(snapshot)
        _exclusive_json(args.output,snapshot)
    except Exception:
        _status("failed"); raise
    _status("succeeded")

if __name__ == "__main__": main()
