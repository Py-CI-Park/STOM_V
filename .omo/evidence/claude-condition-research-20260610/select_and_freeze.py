"""train run 행에 공식 선택기를 적용해 OOS-blind 동결 아티팩트를 작성한다.

- 1차(동결 기준, B1 사전선언): seed_relative_v1 — 같은 측정계의 시드 프로파일
  (같은 run의 BASE_SEED 행)에 임계값을 상대화한다. 근거: 원인1(절대 기준이 시드조차
  탈락) + B2 측정계 감사(MDD 분모=동시보유 규모 — 절대 기준은 레짐 간 이식 불가).
- 비교(병기): sparse_positive_v1(무수정), yearly_sparse_robust_v1(advisory).
- OOS 필드가 행에 존재하면 parse 단계에서 거부된다(ForbiddenOosFieldError).
- 베이스라인 행(strategy_gist가 BASE_ 접두사)은 발굴 후보가 아니므로 출처 기준으로
  선택기 입력에서 제외한다(성과 기준 아님 — 사전선언 정책).

실행:
  PYTHONUTF8=1 python .omo/evidence/claude-condition-research-20260610/select_and_freeze.py <run_id> [<run_id2> ...]
여러 run_id를 주면 행을 합산해 한 풀로 선택한다(동일 윈도우 train run들만 합칠 것).
"""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

import ai_strategy_loop.bootstrap as bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller.candidate_selection import (  # noqa: E402
    SeedProfile,
    parse_candidate_generation,
    select_seed_relative_v1,
    select_sparse_positive_v1,
    select_yearly_sparse_robust_v1,
    write_seed_relative_artifact,
    write_selection_artifact,
    write_yearly_sparse_robust_artifact,
)

EVID = Path(__file__).resolve().parent
RUNS_DB = REPO / "ai_strategy_loop" / "state" / "loop_runs.db"
CONFIG_PATH = EVID / "train-config.json"


def _load_rows(run_ids):
    con = sqlite3.connect(str(RUNS_DB))
    con.row_factory = sqlite3.Row
    rows = []
    try:
        for rid in run_ids:
            rows.extend(con.execute(
                "SELECT gen_no, status, score, gate_passed, reason, profit, total_profit_pct,"
                " mdd, trade_count, daily_avg_trades, payoff_ratio, max_hold_count,"
                " buy_name, sell_name, csv_path, strategy_gist"
                " FROM generations WHERE run_id=? ORDER BY gen_no",
                (rid,),
            ).fetchall())
    finally:
        con.close()
    return rows


def main() -> int:
    run_ids = sys.argv[1:] or ["cldgen_train_2023_2025_20260610"]
    run_label = "+".join(run_ids)
    config_hash = hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()

    rows = _load_rows(run_ids)
    if not rows:
        print(f"no rows for run_ids={run_ids}")
        return 2

    candidates, labels = [], {}
    seed_profile = None
    offset = 0  # 복수 run 합산 시 gen_no 충돌 방지용 오프셋
    for r in rows:
        d = dict(r)
        gist = d.pop("strategy_gist", "") or ""
        d["gen_no"] = int(d.get("gen_no") or 0) + offset
        labels[d["gen_no"]] = gist
        # SQLite는 bool을 int(0/1)로 돌려준다 — 파서는 진짜 bool을 요구한다.
        d["gate_passed"] = bool(d.get("gate_passed"))
        for k in ("payoff_ratio", "max_hold_count", "profit", "mdd", "daily_avg_trades", "score"):
            if d.get(k) is None:
                d[k] = 0.0
        if d.get("csv_path") is None:
            d["csv_path"] = ""
        # 시드 프로파일: 같은 측정계(BASE_SEED 행)에서 추출(첫 발견 행 사용).
        if gist == "BASE_SEED" and seed_profile is None and d.get("status") == "ok":
            seed_profile = SeedProfile(
                mdd=float(d["mdd"]), trade_count=int(d["trade_count"]),
                profit=float(d["profit"]),
                source=f"BASE_SEED gen{d['gen_no']} of {run_label}",
            )
        # 베이스라인은 발굴 후보가 아니므로 출처 기준 제외(사전선언).
        if gist.startswith("BASE_"):
            continue
        candidates.append(parse_candidate_generation(d))

    # ── 1차: seed_relative_v1 (동결 기준) ───────────────────────────────
    primary = select_seed_relative_v1(
        candidates, run_id=run_label, config_path=str(CONFIG_PATH),
        config_hash=config_hash, seed_profile=seed_profile,
    )
    write_seed_relative_artifact(primary, EVID / "p5-selected-candidate.json")

    # ── 비교 병기: sparse_positive_v1 / yearly advisory ────────────────
    sparse = select_sparse_positive_v1(
        candidates, run_id=run_label, config_path=str(CONFIG_PATH),
        config_hash=config_hash, diagnostic_only=True,
    )
    write_selection_artifact(sparse, EVID / "p5-sparse-comparison.json")
    policy_hash = hashlib.sha256((EVID / "p0-predeclared-policy.md").read_bytes()).hexdigest()
    advisory = select_yearly_sparse_robust_v1(
        candidates, run_id=run_label, config_path=str(CONFIG_PATH),
        config_hash=config_hash, policy_hash=policy_hash, diagnostic_only=True,
    )
    write_yearly_sparse_robust_artifact(advisory, EVID / "p5-yearly-advisory.json")

    print(f"selector={primary.selector_version} selected={primary.selected} "
          f"mdd_limit={primary.mdd_limit:.2f} "
          f"seed_profile={'%.2f/%d' % (seed_profile.mdd, seed_profile.trade_count) if seed_profile else None}")
    if primary.selected_candidate is not None:
        c = primary.selected_candidate
        yearly = primary.selected_yearly
        print(f"  -> gen{c.gen_no} [{labels.get(c.gen_no, '')}] buy={c.buy_name} sell={c.sell_name}")
        print(f"     profit={c.profit:,.0f} mdd={c.mdd} trades={c.trade_count} payoff={c.payoff_ratio}")
        if yearly is not None:
            print(f"     yearly={dict(yearly.years)} positive={yearly.positive_years}/{yearly.observed_years}")
    print("eligible:", [(e.gen_no, labels.get(e.gen_no, "")) for e in primary.eligible_candidates])
    for rj in primary.rejected_candidates:
        print(f"  rejected gen{rj.gen_no} [{labels.get(rj.gen_no, '')}]: {'; '.join(rj.reasons)}")
    print(f"comparison: sparse_positive_v1 selected={sparse.selected} / yearly advisory selected={advisory.selected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
