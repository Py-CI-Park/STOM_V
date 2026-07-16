# -*- coding: utf-8 -*-
"""X1 엔진 A/B 러너 — 분리 러너(detached_runner) 대상 (봉인 cb8a9d6a §14).

A/B 공정성(§14-F8): 기준 A(B1 A_2022/A_2023)가 돈 것과 **동일 기구** =
`stom_backtest.py` CLI(csv_path=stock_bt_* 실물 확인) + **동일 프로파일**
(betting 5 / avg-time 30 / timeframe tick — B1 봉인 프로파일). scratch DB 는
`STOM_CLI_DB_STRATEGY` 환경변수로 주입(utility/setting.py `_resolve_db` 계약
— 실 DB 미접촉, §14-F9). 초기 조립안(claude_candidate_batch_eval 배치)은
기준 A 와 기구가 달라 폐기했다 — 같은 저울로만 A/B 를 잰다.

순서: scratch 준비 → 변형 4종 등록 → 8런 순차(후보 4 × 연도 2, 체크포인트
— 기존 success json skip) → 사후 인자 대조(각 B config vs A config: sell·
start·end 동일, buy 만 변형) → parity 리포트.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.stdout = __import__("io").TextIOWrapper(
    sys.stdout.buffer, encoding="utf-8", errors="replace")
_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from alpha_lab.x1lab import orchestrate, variants  # noqa: E402

_RUN_DIR = (_REPO / "docs/research/condition_research/research_runs"
            / "alpha_restart_20260710")
_OUT = _RUN_DIR / "x1"
_B_DIR = _OUT / "b_metrics"
_A_DIR = _RUN_DIR / "d5r_b1_live"
_REAL_DB = _REPO / "_database" / "strategy.db"
_SCRATCH = Path(r"C:\Temp\claude\C--System-Trading-STOM-STOM-V-wt-alpha"
                r"\f12d90e9-de14-41e1-89a7-5a5a21c801fb\scratchpad"
                r"\x1_scratch_strategy.db")
_PROGRESS = _OUT / "x1_engine_progress.txt"

# B1 봉인 프로파일(§14-F8) — A 런과 동일해야 하는 CLI 인자.
PROFILE = ("--timeframe", "tick", "--betting", "5", "--avg-time", "30")


def _log(msg: str) -> None:
    with open(_PROGRESS, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()}   {msg}\n")
    print(msg, flush=True)


def _run_ok(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("status") == "success"
    except (ValueError, OSError):
        return False


def _post_parity() -> dict:
    """사후 인자 대조 — 각 B config 는 A 와 sell·창 동일, buy 만 변형이어야 함."""
    out = {"pairs": [], "parity_ok": True}
    for yr in (2022, 2023):
        a = json.loads((_A_DIR / f"A_{yr}.json").read_text(encoding="utf-8"))
        ac = a.get("config", {})
        for cand in variants.CANDIDATES:
            bp = _B_DIR / f"B_{cand}_{yr}.json"
            if not bp.exists():
                out["pairs"].append({"cand": cand, "year": yr, "status": "missing"})
                out["parity_ok"] = False
                continue
            b = json.loads(bp.read_text(encoding="utf-8"))
            bc = b.get("config", {})
            issues = []
            if bc.get("sell_strategy") != ac.get("sell_strategy"):
                issues.append(f"sell {bc.get('sell_strategy')}≠{ac.get('sell_strategy')}")
            if (str(bc.get("start_date")), str(bc.get("end_date"))) != (
                    str(ac.get("start_date")), str(ac.get("end_date"))):
                issues.append("창 불일치")
            if bc.get("buy_strategy") != variants.strategy_name(cand):
                issues.append(f"buy {bc.get('buy_strategy')}")
            out["pairs"].append({"cand": cand, "year": yr,
                                 "status": b.get("status"), "issues": issues})
            if issues:
                out["parity_ok"] = False
    return out


def main() -> int:
    _OUT.mkdir(parents=True, exist_ok=True)
    _B_DIR.mkdir(parents=True, exist_ok=True)

    # 1) scratch 준비 + 등록(멱등 — registrar 는 동명 스킵).
    txt = variants.champion_buy_text(_REAL_DB)
    results = variants.generate_all(txt)
    con = sqlite3.connect(f"file:{_REAL_DB.as_posix()}?mode=ro", uri=True)
    try:
        sell_text = con.execute('SELECT "전략코드" FROM stocksell WHERE "index"=?',
                                (orchestrate.SELL_NAME,)).fetchone()[0]
    finally:
        con.close()
    if not _SCRATCH.exists():
        prep = orchestrate.prepare_scratch_db(_REAL_DB, _SCRATCH)
        _log(f"scratch 생성: sell_sha_ok={prep['sell_sha_ok']}")
    reg = orchestrate.register_variants(_SCRATCH, results,
                                        champion_sell_text=sell_text)
    _log(f"등록: inserted={len(reg['inserted'] or [])} "
         f"conflicts={len(reg['conflicts'] or [])} (멱등)")

    # 2) 8런 순차 — A 와 동일 기구(stom_backtest CLI) + scratch env.
    env = dict(os.environ)
    env["STOM_ALLOW_MINIMAL_SETTING"] = "1"
    env["STOM_CLI_DB_STRATEGY"] = str(_SCRATCH)
    n_run = n_skip = n_fail = 0
    for cand in variants.CANDIDATES:
        name = variants.strategy_name(cand)
        for yr, (s, e) in sorted(orchestrate.YEAR_WINDOWS.items()):
            out_json = _B_DIR / f"B_{cand}_{yr}.json"
            if _run_ok(out_json):
                n_skip += 1
                _log(f"skip(성공 기존): {cand} {yr}")
                continue
            cmd = [sys.executable, "-X", "utf8", str(_REPO / "stom_backtest.py"),
                   "--buy", name, "--sell", orchestrate.SELL_NAME,
                   "--start", str(s), "--end", str(e), *PROFILE,
                   "--format", "json", "-o", str(out_json), "--quiet"]
            _log(f"run: {cand} {yr} ({name})")
            t0 = datetime.now()
            proc = subprocess.run(cmd, cwd=str(_REPO), env=env,
                                  capture_output=True, text=True,
                                  encoding="utf-8", errors="replace",
                                  timeout=3600)
            dt = (datetime.now() - t0).total_seconds()
            ok = _run_ok(out_json)
            n_run += 1
            if not ok:
                n_fail += 1
                _log(f"FAIL: {cand} {yr} rc={proc.returncode} ({dt:.0f}s) "
                     f"stderr_tail={proc.stderr[-300:] if proc.stderr else ''}")
            else:
                m = json.loads(out_json.read_text(encoding="utf-8"))["metrics"]
                _log(f"done: {cand} {yr} ({dt:.0f}s) profit={m['total_profit_krw']:,.0f} "
                     f"trades={m['trade_count']} mdd={m['mdd_pct']}")

    # 3) 사후 인자 대조(§14-F8).
    parity = _post_parity()
    (_OUT / "x1_arg_parity.json").write_text(
        json.dumps(parity, ensure_ascii=False, indent=1), encoding="utf-8")
    _log(f"X1-ENGINE done: run={n_run} skip={n_skip} fail={n_fail} "
         f"parity_ok={parity['parity_ok']}")
    return 0 if (n_fail == 0 and parity["parity_ok"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
