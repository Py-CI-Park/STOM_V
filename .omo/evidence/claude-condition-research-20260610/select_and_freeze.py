"""train run 행에 공식 선택기를 적용해 OOS-blind 동결 아티팩트를 작성한다.

- 1차(동결 기준, 사전선언): sparse_positive_v1 (무수정)
- 참고(advisory): yearly_sparse_robust_v1 (무수정)
- OOS 필드가 행에 존재하면 parse 단계에서 거부된다(ForbiddenOosFieldError).

실행:
  PYTHONUTF8=1 python .omo/evidence/claude-condition-research-20260610/select_and_freeze.py <run_id>
"""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

import ai_strategy_loop.bootstrap as bootstrap  # noqa: E402
from ai_strategy_loop.controller.candidate_selection import (  # noqa: E402
    parse_candidate_generation,
    select_sparse_positive_v1,
    select_yearly_sparse_robust_v1,
    write_selection_artifact,
    write_yearly_sparse_robust_artifact,
)

EVID = Path(__file__).resolve().parent
RUNS_DB = REPO / "ai_strategy_loop" / "state" / "loop_runs.db"
CONFIG_PATH = EVID / "train-config.json"


def main() -> int:
    run_id = sys.argv[1] if len(sys.argv) > 1 else "cldgen_train_2023_2025_20260610"
    config_bytes = CONFIG_PATH.read_bytes()
    config_hash = hashlib.sha256(config_bytes).hexdigest()

    con = sqlite3.connect(str(RUNS_DB))
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT gen_no, status, score, gate_passed, reason, profit, total_profit_pct,"
            " mdd, trade_count, daily_avg_trades, payoff_ratio, max_hold_count,"
            " buy_name, sell_name, csv_path, strategy_gist"
            " FROM generations WHERE run_id=? ORDER BY gen_no",
            (run_id,),
        ).fetchall()
    finally:
        con.close()
    if not rows:
        print(f"no rows for run_id={run_id}")
        return 2

    candidates = []
    labels = {}
    for r in rows:
        d = dict(r)
        gist = d.pop("strategy_gist", "") or ""
        labels[int(d.get("gen_no") or 0)] = gist
        # 베이스라인(인간 시드/과거 동결 후보)은 발굴 후보가 아니므로 선택기 입력에서
        # 출처 기준으로 제외한다(성과 기반 제외 아님 — 사전선언 정책).
        if gist.startswith("BASE_"):
            continue
        d.setdefault("payoff_ratio", 0.0)
        d.setdefault("max_hold_count", 0.0)
        for k in ("payoff_ratio", "max_hold_count", "profit", "mdd", "daily_avg_trades", "score"):
            if d.get(k) is None:
                d[k] = 0.0
        if d.get("csv_path") is None:
            d["csv_path"] = ""
        candidates.append(parse_candidate_generation(d))

    primary = select_sparse_positive_v1(
        candidates, run_id=run_id, config_path=str(CONFIG_PATH), config_hash=config_hash,
    )
    write_selection_artifact(primary, EVID / "p5-selected-candidate.json")

    policy_hash = hashlib.sha256(
        (EVID / "p0-predeclared-policy.md").read_bytes()
    ).hexdigest()
    advisory = select_yearly_sparse_robust_v1(
        candidates, run_id=run_id, config_path=str(CONFIG_PATH),
        config_hash=config_hash, policy_hash=policy_hash, diagnostic_only=True,
    )
    write_yearly_sparse_robust_artifact(advisory, EVID / "p5-yearly-advisory.json")

    print(f"selector={primary.selector_version} selected={primary.selected}")
    if primary.selected_candidate is not None:
        c = primary.selected_candidate
        print(f"  -> gen{c.gen_no} [{labels.get(c.gen_no, '')}] buy={c.buy_name} sell={c.sell_name}")
        print(f"     profit={c.profit:,.0f} mdd={c.mdd} trades={c.trade_count} payoff={c.payoff_ratio}")
    print("eligible:", [(e.gen_no, labels.get(e.gen_no, ""), e.bucket) for e in primary.eligible_candidates])
    print("rejected:")
    for rj in primary.rejected_candidates:
        print(f"  gen{rj.gen_no} [{labels.get(rj.gen_no, '')}]: {'; '.join(rj.reasons)}")
    print(f"advisory yearly selected={advisory.selected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
