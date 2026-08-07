from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cli.strategy_generator import save_strategy_to_db  # noqa: E402

RUN_ROOT = Path(__file__).resolve().parent
SOURCE_SANDBOX = ROOT / ".omo" / "evidence" / "tmap-walkforward" / "post-q4-oos-strategy-20260619.sqlite"
STRATEGY_SQLITE = RUN_ROOT / "proxy-oos-strategy-20260619.sqlite"
RUNS_SQLITE = RUN_ROOT / "proxy-oos-loop-runs-20260619.sqlite"
SNAPSHOTS = RUN_ROOT / "snapshots"
LOGS = RUN_ROOT / "logs"
CURRENT_STATE = RUN_ROOT / "current-state.json"
STOP_FLAG = RUN_ROOT / "STOP"
PAIRS_JSON = RUN_ROOT / "pairs-proxy-oos-20260619.json"
CANDIDATE_REPORT = RUN_ROOT / "proxy-candidate-design-20260619.md"
PREFLIGHT_JSON = RUN_ROOT / "proxy-oos-preflight-20260619.json"

FORBIDDEN_MUTABLE_FRAGMENTS = [
    "ai_strategy_loop/state/loop_strategies.db",
    "ai_strategy_loop/state/loop_runs.db",
    "_database/",
    "_database\\",
    "_database_v3k_shadow/",
    "_database_v3k_shadow\\",
    "v3k_settings",
    "KHOPENAPI",
    "live",
    "export",
]


def _read_strategy(table: str, name: str) -> str:
    con = sqlite3.connect(f"file:{SOURCE_SANDBOX}?mode=ro", uri=True)
    try:
        row = con.execute(f'SELECT "전략코드" FROM {table} WHERE "index"=?', (name,)).fetchone()
    finally:
        con.close()
    if not row:
        raise RuntimeError(f"missing source strategy {table}:{name}")
    return str(row[0])


def _insert_before_buy(base_code: str, block: str) -> str:
    marker = "\nif 매수:\n    self.Buy()"
    if marker not in base_code:
        raise RuntimeError("buy marker not found")
    return base_code.replace(marker, "\n" + block.rstrip() + "\n\nif 매수:\n    self.Buy()")


def _insert_before_first_sell_rule(base_code: str, block: str) -> str:
    marker = "# 등락율 상한가 직전\nif 등락율 > 29.5:"
    if marker not in base_code:
        raise RuntimeError("sell marker not found")
    return base_code.replace(marker, block.rstrip() + "\n\n" + marker)


def _compile(name: str, code: str) -> None:
    compile(code, f"<proxy-oos:{name}>", "exec")


def _save(name: str, code: str, kind: str) -> None:
    _compile(name, code)
    result = save_strategy_to_db(str(STRATEGY_SQLITE), name, code, kind)
    if result.get("status") != "ok":
        raise RuntimeError(f"failed saving {name}: {result}")


def _ensure_formula_table() -> None:
    con = sqlite3.connect(str(STRATEGY_SQLITE))
    try:
        con.execute(
            'CREATE TABLE IF NOT EXISTS formula ('
            '"수식명" TEXT, "차트표시" TEXT, "전략연산" TEXT, "팩터명" TEXT, '
            '"표시형태" TEXT, "색상" TEXT, "굵기" TEXT, "종류" TEXT, "수식코드" TEXT)'
        )
        con.commit()
    finally:
        con.close()


def _normalized(path: Path) -> str:
    return path.resolve().as_posix()


def _validate_mutable_paths(paths: dict[str, Path]) -> list[str]:
    violations: list[str] = []
    for key, path in paths.items():
        resolved = _normalized(path)
        repo_rel = path.resolve().relative_to(ROOT).as_posix() if path.resolve().is_relative_to(ROOT) else resolved
        if not path.resolve().is_relative_to(RUN_ROOT.resolve()):
            violations.append(f"{key} is outside run root: {repo_rel}")
        lowered = repo_rel.lower()
        for fragment in FORBIDDEN_MUTABLE_FRAGMENTS:
            if fragment.lower() in lowered:
                violations.append(f"{key} targets forbidden fragment {fragment}: {repo_rel}")
    return violations


def main() -> int:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)

    base_buy = _read_strategy("stockbuy", "POSTQ4_r8_exclude_cap_lt_1500_B")
    base_sell = _read_strategy("stocksell", "POSTQ4_r8_exclude_cap_lt_1500_S")

    p1_buy_filter = """
# PROXY_P1_entry_liquidity: 저시총 제외 유지 + 중소형 유동성/체결강도 과열 완화 필터
if 매수:
    if not (시가총액 >= 1800):
        매수 = False
if 매수:
    if 시분초 < 90200:
        if not (회전율 >= 2.2 and 당일거래대금각도(30) >= 8 and 80 <= 체결강도 <= 230):
            매수 = False
    elif 90200 <= 시분초 < 90700:
        if not (회전율 >= 1.8 and 당일거래대금각도(30) >= 12 and 80 <= 체결강도 <= 230):
            매수 = False
    else:
        매수 = False
"""
    p2_sell_filter = """
# PROXY_P2_defensive_exit: exit2의 방어 성향을 단일 매도 조건식으로 근사
if 수익률 <= -4.2:
    매도 = True
elif 보유시간 > 25 and 수익률 <= -2.2 and 현재가 < 이동평균(30):
    매도 = True
elif 최고수익률 >= 2.8 and 수익률 <= 최고수익률 * 0.45:
    매도 = True
elif 보유시간 > 120 and 수익률 <= 0.4 and 체결강도 < 체결강도평균(30):
    매도 = True
"""
    p3_sell_filter = """
# PROXY_P3_trend_vol_exit: r2full의 추세 참여/변동성 대응 성향을 단일 매도 조건식으로 근사
if 수익률 <= -5.5:
    매도 = True
elif 보유시간 > 45 and 수익률 <= -3.0 and 현재가 < 이동평균(60):
    매도 = True
elif 최고수익률 >= 6.0 and 수익률 <= 최고수익률 * 0.50:
    매도 = True
elif 보유시간 > 180 and 수익률 > 1.0 and 체결강도 >= 체결강도평균(30):
    매도 = False
"""

    candidates = [
        {
            "label": "P1_entry_liquidity_proxy",
            "buy": "PROXY_P1_entry_liquidity_B",
            "sell": "PROXY_P1_entry_liquidity_S",
            "buy_code": _insert_before_buy(base_buy, p1_buy_filter),
            "sell_code": base_sell,
            "intent": "entry-pure: r8 저시총 제외를 유지하면서 1500~3000억 구간의 유동성/회전율/체결강도 과열 필터를 추가한다.",
        },
        {
            "label": "P2_defensive_exit_proxy",
            "buy": "PROXY_P2_defensive_exit_B",
            "sell": "PROXY_P2_defensive_exit_S",
            "buy_code": base_buy,
            "sell_code": _insert_before_first_sell_rule(base_sell, p2_sell_filter),
            "intent": "exit-behavior: prior-month PnL state 없이 손실 차단과 최고수익률 반납 제한으로 exit2 방어 성향을 근사한다.",
        },
        {
            "label": "P3_trend_vol_exit_proxy",
            "buy": "PROXY_P3_trend_vol_exit_B",
            "sell": "PROXY_P3_trend_vol_exit_S",
            "buy_code": base_buy,
            "sell_code": _insert_before_first_sell_rule(
                base_sell.replace("if 수익률 >= 9 or 수익률 <= -7.0:", "if 수익률 >= 12 or 수익률 <= -5.5:")
                .replace("elif 최고수익률 > 4 and 최고수익률 * 0.6 >= 수익률:", "elif 최고수익률 > 5.5 and 최고수익률 * 0.50 >= 수익률:"),
                p3_sell_filter,
            ),
            "intent": "exit-behavior: 더 큰 수익 구간은 보유하고 변동성/추세 이탈 손실은 제한해 r2full 참여 성향을 근사한다.",
        },
    ]

    for candidate in candidates:
        _save(candidate["buy"], candidate["buy_code"], "buy")
        _save(candidate["sell"], candidate["sell_code"], "sell")
    _ensure_formula_table()

    pairs = [{"label": c["label"], "buy": c["buy"], "sell": c["sell"]} for c in candidates]
    PAIRS_JSON.write_text(json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8")

    report_lines = [
        "# Proxy OOS Candidate Design (2026-06-19)",
        "",
        "Scope: run-owned proxy official OOS candidates derived from `POSTQ4_r8_exclude_cap_lt_1500` baseline.",
        "",
        "Evidence taxonomy: these are candidate condition pairs for official OOS; they do not encode CSV switching, prior-month strategy PnL state, live/export behavior, or operating DB mutation.",
        "",
        "| Candidate | Buy | Sell | Intent | Leakage review |",
        "|---|---|---|---|---|",
    ]
    for candidate in candidates:
        report_lines.append(
            f"| {candidate['label']} | `{candidate['buy']}` | `{candidate['sell']}` | {candidate['intent']} | Uses only tick/current position variables listed in `utility/ai_agent/strategy.txt`; no future/result label, CSV selection, or prior-month strategy-PnL state. |"
        )
    report_lines.extend([
        "",
        "## Run-owned mutable paths",
        "",
        f"- strategy sqlite: `{STRATEGY_SQLITE.relative_to(ROOT).as_posix()}`",
        f"- loop runs sqlite: `{RUNS_SQLITE.relative_to(ROOT).as_posix()}`",
        f"- snapshots: `{SNAPSHOTS.relative_to(ROOT).as_posix()}`",
        f"- current state: `{CURRENT_STATE.relative_to(ROOT).as_posix()}`",
        f"- stop flag: `{STOP_FLAG.relative_to(ROOT).as_posix()}`",
        f"- pairs json: `{PAIRS_JSON.relative_to(ROOT).as_posix()}`",
    ])
    CANDIDATE_REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    mutable_paths = {
        "strategy_sqlite": STRATEGY_SQLITE,
        "loop_runs_sqlite": RUNS_SQLITE,
        "snapshots": SNAPSHOTS,
        "current_state": CURRENT_STATE,
        "stop_flag": STOP_FLAG,
        "logs": LOGS,
        "pairs_json": PAIRS_JSON,
    }
    violations = _validate_mutable_paths(mutable_paths)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_root": RUN_ROOT.relative_to(ROOT).as_posix(),
        "source_sandbox": SOURCE_SANDBOX.relative_to(ROOT).as_posix(),
        "candidate_count": len(candidates),
        "pairs_json": PAIRS_JSON.relative_to(ROOT).as_posix(),
        "candidate_report": CANDIDATE_REPORT.relative_to(ROOT).as_posix(),
        "mutable_paths": {k: v.relative_to(ROOT).as_posix() for k, v in mutable_paths.items()},
        "forbidden_mutable_fragments": FORBIDDEN_MUTABLE_FRAGMENTS,
        "violations": violations,
        "status": "ok" if not violations else "blocked",
    }
    PREFLIGHT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if violations:
        raise RuntimeError("preflight violations: " + "; ".join(violations))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
