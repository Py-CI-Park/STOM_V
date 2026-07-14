#!/usr/bin/env python
"""G2 — 저장 전 기계 검사 사슬(variable_scope/token_check/filter_gate/exec_budget/
principle_gate)의 오탐(false-reject) 실측 감사 (읽기 전용, 연구 레인 전용).

동작 원칙:
  - `_database/strategy.db`는 반드시 읽기 전용(`file:...?mode=ro`)으로만 연다.
    이 스크립트는 어떤 DB에도 쓰지 않는다.
  - 검사기(ai_strategy_loop/brain/{variable_scope,token_check,filter_gate,
    exec_budget,principle_gate}.py)의 공개 함수를 그대로 호출한다 — 이 스크립트는
    검사 로직을 재구현하지 않는다.
  - `__AUTO_TMP__` 접두 전략(임시 산출물)은 감사 대상에서 제외하되 제외 수를
    기록한다.

이름 휴리스틱 (실측 근거: seed_db 명명 관례):
  - timeframe: `Tick_`/`C_T_` 접두 또는 이름에 `TICK` 부분일치 → tick.
    `Min_` 접두 또는 이름에 `MIN` 부분일치 → min. 둘 다 매칭되거나 둘 다
    매칭되지 않으면 불확실 → tick/min 양쪽 각각 별도로 기록한다.
  - buy/sell 짝: 이름 토큰 경계(밑줄/문자열 끝)에 홀로 있는 `B`를 `S`로 바꾼
    후보 이름이 반대쪽 테이블에 존재하면 짝으로 본다(`Tick_B_902` ↔
    `Tick_S_902`, `CSS_V7_MIN_B_MASTER...` ↔ `CSS_V7_MIN_S_MASTER...`).
    후보가 없으면 unpaired로 기록한다(principle_gate는 그 전략에 대해
    실행하지 않는다 — 판정에는 buy+sell 쌍이 필요하다).

출력: artifacts/g2_gate_false_reject_audit.json (기본 경로).
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
import sys

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import ai_strategy_loop.bootstrap  # noqa: E402,F401  # env-before-import 계약

from ai_strategy_loop.brain.exec_budget import check_sell_exec_budget
from ai_strategy_loop.brain.filter_gate import count_filter_categories
from ai_strategy_loop.brain.principle_gate import (
    SEVERITY_ADVISORY,
    SEVERITY_REJECT,
    check_principle_consistency,
)
from ai_strategy_loop.brain.token_check import check_tokens
from ai_strategy_loop.brain.variable_scope import check_variable_scope

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "_database" / "strategy.db"
DEFAULT_OUT_PATH = ROOT / "artifacts" / "g2_gate_false_reject_audit.json"

AUTO_TMP_PREFIX = "__AUTO_TMP__"
MIN_FILTER_CATEGORIES = 5

TABLE_BY_KIND = {"buy": "stockbuy", "sell": "stocksell"}
NAME_COLUMN = "index"
CODE_COLUMN_PREFERRED = "전략코드"

# 토큰 경계에 홀로 있는 B/S만 치환 (예: "TICK_B_902" 의 B, "BOX" 의 B는 제외).
_B_TOKEN_RE = re.compile(r"(^|_)B(_|$)")


def _connect_readonly(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _code_column(con: sqlite3.Connection, table: str) -> str:
    cur = con.execute(f'PRAGMA table_info("{table}")')
    cols = [row[1] for row in cur.fetchall()]
    if CODE_COLUMN_PREFERRED in cols:
        return CODE_COLUMN_PREFERRED
    return cols[1] if len(cols) >= 2 else CODE_COLUMN_PREFERRED


def load_rows(con: sqlite3.Connection, kind: str) -> List[Tuple[str, str]]:
    """(name, code) 목록을 이름순으로 반환한다. code는 문자열로 강제한다."""
    table = TABLE_BY_KIND[kind]
    code_col = _code_column(con, table)
    cur = con.execute(f'SELECT "{NAME_COLUMN}", "{code_col}" FROM "{table}" ORDER BY "{NAME_COLUMN}"')
    rows = []
    for name, code in cur.fetchall():
        rows.append((str(name), "" if code is None else str(code)))
    return rows


def classify_timeframe(name: str) -> List[str]:
    """이름 휴리스틱으로 timeframe을 분류한다. 불확실하면 ['tick', 'min'] (양쪽)."""
    upper = name.upper()
    is_tick = name.startswith("Tick_") or name.startswith("C_T_") or "TICK" in upper
    is_min = name.startswith("Min_") or "MIN" in upper
    if is_tick and not is_min:
        return ["tick"]
    if is_min and not is_tick:
        return ["min"]
    return ["tick", "min"]


def candidate_sell_name(buy_name: str) -> Optional[str]:
    """buy 이름의 토큰 경계 단독 'B'를 'S'로 바꾼 후보 sell 이름(없으면 None)."""
    match = _B_TOKEN_RE.search(buy_name)
    if not match:
        return None
    start, end = match.span()
    return buy_name[:start] + match.group(1) + "S" + match.group(2) + buy_name[end:]


def pair_strategies(
    buy_rows: Sequence[Tuple[str, str]], sell_rows: Sequence[Tuple[str, str]]
) -> Tuple[List[Tuple[str, str, str, str]], List[str], List[str]]:
    """(buy_name, buy_code, sell_name, sell_code) 쌍 목록과 unpaired buy/sell 이름 목록."""
    sell_by_name = {name: code for name, code in sell_rows}
    paired: List[Tuple[str, str, str, str]] = []
    unpaired_buy: List[str] = []
    matched_sell_names: set = set()
    for buy_name, buy_code in buy_rows:
        candidate = candidate_sell_name(buy_name)
        if candidate is not None and candidate in sell_by_name:
            paired.append((buy_name, buy_code, candidate, sell_by_name[candidate]))
            matched_sell_names.add(candidate)
        else:
            unpaired_buy.append(buy_name)
    unpaired_sell = [name for name, _ in sell_rows if name not in matched_sell_names]
    return paired, unpaired_buy, unpaired_sell


def _rate(rejected: int, evaluated: int) -> float:
    return round(rejected / evaluated, 6) if evaluated else 0.0


def audit_variable_scope(
    buy_rows: Sequence[Tuple[str, str]], sell_rows: Sequence[Tuple[str, str]]
) -> Dict[str, Any]:
    evaluated = 0
    rejected = 0
    reason_counter: Counter = Counter()
    rejected_strategies: List[Dict[str, Any]] = []
    for kind, rows in (("buy", buy_rows), ("sell", sell_rows)):
        for name, code in rows:
            for tf in classify_timeframe(name):
                evaluated += 1
                ok, offending = check_variable_scope(code, tf, kind)
                if not ok:
                    rejected += 1
                    for off in offending:
                        reason_counter[off] += 1
                    rejected_strategies.append(
                        {
                            "name": name,
                            "kind": kind,
                            "timeframe": tf,
                            "reasons": offending,
                        }
                    )
    return {
        "evaluated": evaluated,
        "rejected": rejected,
        "reject_rate": _rate(rejected, evaluated),
        "reason_distribution": dict(reason_counter.most_common()),
        "rejected_strategies": rejected_strategies,
    }


def audit_token_check(
    buy_rows: Sequence[Tuple[str, str]], sell_rows: Sequence[Tuple[str, str]]
) -> Dict[str, Any]:
    evaluated = 0
    rejected = 0
    reason_counter: Counter = Counter()
    rejected_strategies: List[Dict[str, Any]] = []
    for kind, rows in (("buy", buy_rows), ("sell", sell_rows)):
        for name, code in rows:
            evaluated += 1
            ok, reason = check_tokens(code)
            if not ok:
                rejected += 1
                reason_counter[reason] += 1
                rejected_strategies.append({"name": name, "kind": kind, "reason": reason})
    return {
        "evaluated": evaluated,
        "rejected": rejected,
        "reject_rate": _rate(rejected, evaluated),
        "reason_distribution": dict(reason_counter.most_common()),
        "rejected_strategies": rejected_strategies,
    }


def audit_filter_gate(
    buy_rows: Sequence[Tuple[str, str]], *, min_filter_categories: int = MIN_FILTER_CATEGORIES
) -> Dict[str, Any]:
    evaluated = 0
    rejected = 0
    category_count_distribution: Counter = Counter()
    rejected_category_count_distribution: Counter = Counter()
    rejected_strategies: List[Dict[str, Any]] = []
    for name, code in buy_rows:
        evaluated += 1
        count = count_filter_categories(code)
        category_count_distribution[str(count)] += 1
        if count < min_filter_categories:
            rejected += 1
            rejected_category_count_distribution[str(count)] += 1
            rejected_strategies.append(
                {"name": name, "category_count": count, "min_required": min_filter_categories}
            )
    return {
        "evaluated": evaluated,
        "rejected": rejected,
        "reject_rate": _rate(rejected, evaluated),
        "min_filter_categories": min_filter_categories,
        "category_count_distribution": dict(sorted(category_count_distribution.items(), key=lambda kv: int(kv[0]))),
        "rejected_category_count_distribution": dict(
            sorted(rejected_category_count_distribution.items(), key=lambda kv: int(kv[0]))
        ),
        "rejected_strategies": rejected_strategies,
    }


def audit_exec_budget(sell_rows: Sequence[Tuple[str, str]]) -> Dict[str, Any]:
    evaluated = 0
    rejected = 0
    reason_counter: Counter = Counter()
    rejected_strategies: List[Dict[str, Any]] = []
    for name, code in sell_rows:
        evaluated += 1
        ok, reason = check_sell_exec_budget(code)
        if not ok:
            rejected += 1
            # 사유 메시지에 동적 수치가 섞여 있어, 첫 문장(위반 종류)만 분포 키로 쓴다.
            bucket = reason.split(" — ", 1)[-1].split(".", 1)[0]
            reason_counter[bucket] += 1
            rejected_strategies.append({"name": name, "reason": reason})
    return {
        "evaluated": evaluated,
        "rejected": rejected,
        "reject_rate": _rate(rejected, evaluated),
        "reason_distribution": dict(reason_counter.most_common()),
        "rejected_strategies": rejected_strategies,
    }


def audit_principle_gate(
    paired: Sequence[Tuple[str, str, str, str]], unpaired_buy: Sequence[str], unpaired_sell: Sequence[str]
) -> Dict[str, Any]:
    evaluated = 0
    rejected = 0
    reject_reason_counter: Counter = Counter()
    advisory_reason_counter: Counter = Counter()
    rejected_pairs: List[Dict[str, Any]] = []
    for buy_name, buy_code, sell_name, sell_code in paired:
        for tf in classify_timeframe(buy_name):
            evaluated += 1
            metadata = {"timeframe": tf}
            violations = check_principle_consistency(buy_code, sell_code, metadata)
            reject_violations = [v for v in violations if v["severity"] == SEVERITY_REJECT]
            advisory_violations = [v for v in violations if v["severity"] == SEVERITY_ADVISORY]
            for v in reject_violations:
                reject_reason_counter[v["rule_id"]] += 1
            for v in advisory_violations:
                advisory_reason_counter[v["rule_id"]] += 1
            if reject_violations:
                rejected += 1
                rejected_pairs.append(
                    {
                        "buy_name": buy_name,
                        "sell_name": sell_name,
                        "timeframe": tf,
                        "reject_violations": reject_violations,
                        "advisory_violations": advisory_violations,
                    }
                )
    return {
        "evaluated": evaluated,
        "rejected": rejected,
        "reject_rate": _rate(rejected, evaluated),
        "reject_reason_distribution": dict(reject_reason_counter.most_common()),
        "advisory_reason_distribution": dict(advisory_reason_counter.most_common()),
        "rejected_pairs": rejected_pairs,
        "paired_count": len(paired),
        "unpaired_buy_count": len(unpaired_buy),
        "unpaired_sell_count": len(unpaired_sell),
        "unpaired_buy_names": list(unpaired_buy),
        "unpaired_sell_names": list(unpaired_sell),
    }


def build_summary(
    buy_rows: Sequence[Tuple[str, str]],
    sell_rows: Sequence[Tuple[str, str]],
    checks: Dict[str, Any],
) -> Dict[str, Any]:
    rejected_any: set = set()
    for entry in checks["variable_scope"]["rejected_strategies"]:
        rejected_any.add((entry["kind"], entry["name"]))
    for entry in checks["token_check"]["rejected_strategies"]:
        rejected_any.add((entry["kind"], entry["name"]))
    for entry in checks["filter_gate"]["rejected_strategies"]:
        rejected_any.add(("buy", entry["name"]))
    for entry in checks["exec_budget"]["rejected_strategies"]:
        rejected_any.add(("sell", entry["name"]))
    for entry in checks["principle_gate"]["rejected_pairs"]:
        rejected_any.add(("buy", entry["buy_name"]))
        rejected_any.add(("sell", entry["sell_name"]))

    strategies_total = len(buy_rows) + len(sell_rows)
    top_reasons: Dict[str, List[List[Any]]] = {}
    for check_name, dist_key in (
        ("variable_scope", "reason_distribution"),
        ("token_check", "reason_distribution"),
        ("filter_gate", "rejected_category_count_distribution"),
        ("exec_budget", "reason_distribution"),
        ("principle_gate", "reject_reason_distribution"),
    ):
        dist = checks[check_name][dist_key]
        top_reasons[check_name] = [[k, v] for k, v in list(dist.items())[:5]]

    return {
        "strategies_total": strategies_total,
        "strategies_rejected_by_any_check": len(rejected_any),
        "rejected_by_any_rate": _rate(len(rejected_any), strategies_total),
        "top_reject_reasons_by_check": top_reasons,
    }


def run_audit(
    db_path: Path, *, min_filter_categories: int = MIN_FILTER_CATEGORIES
) -> Dict[str, Any]:
    con = _connect_readonly(db_path)
    try:
        raw_buy_rows = load_rows(con, "buy")
        raw_sell_rows = load_rows(con, "sell")
    finally:
        con.close()

    excluded_buy = [name for name, _ in raw_buy_rows if name.startswith(AUTO_TMP_PREFIX)]
    excluded_sell = [name for name, _ in raw_sell_rows if name.startswith(AUTO_TMP_PREFIX)]
    buy_rows = [(n, c) for n, c in raw_buy_rows if not n.startswith(AUTO_TMP_PREFIX)]
    sell_rows = [(n, c) for n, c in raw_sell_rows if not n.startswith(AUTO_TMP_PREFIX)]

    paired, unpaired_buy, unpaired_sell = pair_strategies(buy_rows, sell_rows)

    checks = {
        "variable_scope": audit_variable_scope(buy_rows, sell_rows),
        "token_check": audit_token_check(buy_rows, sell_rows),
        "filter_gate": audit_filter_gate(buy_rows, min_filter_categories=min_filter_categories),
        "exec_budget": audit_exec_budget(sell_rows),
        "principle_gate": audit_principle_gate(paired, unpaired_buy, unpaired_sell),
    }

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "db_path": str(db_path.resolve()),
        "excluded_auto_tmp": {
            "buy": len(excluded_buy),
            "sell": len(excluded_sell),
            "total": len(excluded_buy) + len(excluded_sell),
            "buy_names": excluded_buy,
            "sell_names": excluded_sell,
        },
        "counts": {
            "buy_total_raw": len(raw_buy_rows),
            "sell_total_raw": len(raw_sell_rows),
            "buy_audited": len(buy_rows),
            "sell_audited": len(sell_rows),
        },
        "checks": checks,
    }
    result["summary"] = build_summary(buy_rows, sell_rows, checks)
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="strategy.db 경로(읽기 전용으로만 연다).")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_PATH, help="출력 JSON 경로.")
    parser.add_argument(
        "--min-filter-categories",
        type=int,
        default=MIN_FILTER_CATEGORIES,
        help="filter_gate 최소 범주 수 기준(기본 5).",
    )
    args = parser.parse_args(argv)

    if not args.db.exists():
        print(f"[audit_gate_false_rejects] DB를 찾을 수 없습니다: {args.db}")
        return 1

    result = run_audit(args.db, min_filter_categories=args.min_filter_categories)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = result["summary"]
    print(f"[audit_gate_false_rejects] wrote {args.out}")
    print(
        f"[audit_gate_false_rejects] strategies_total={summary['strategies_total']} "
        f"rejected_by_any={summary['strategies_rejected_by_any_check']} "
        f"rate={summary['rejected_by_any_rate']}"
    )
    for check_name in ("variable_scope", "token_check", "filter_gate", "exec_budget", "principle_gate"):
        c = result["checks"][check_name]
        print(
            f"[audit_gate_false_rejects] {check_name}: evaluated={c['evaluated']} "
            f"rejected={c['rejected']} rate={c['reject_rate']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
