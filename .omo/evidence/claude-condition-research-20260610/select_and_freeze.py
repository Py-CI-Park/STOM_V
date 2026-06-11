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
from ai_strategy_loop.controller._yearly_sparse_robust_selection import (  # noqa: E402
    YearlySparseRobustThresholds,
)
from ai_strategy_loop.fitness.overfit_stats import (  # noqa: E402
    align_daily_matrix,
    block_bootstrap_daily,
    daily_correlation_matrix,
    daily_pnl_series,
    deflated_sharpe_ratio,
    effective_independent_count,
    pbo_cscv,
)

# C3 — yearly advisory 임계를 seed_relative_v1과 정합(거래 50~400, MDD 20).
#   기존 DEFAULT(150~250, MDD 10)는 원인1과 같은 절대-기준 비정합을 가진다.
SEED_ALIGNED_YEARLY_THRESHOLDS = YearlySparseRobustThresholds(
    min_trade_count=50,
    max_trade_count=400,
    min_daily_avg_trades=0.05,
    max_mdd=20.0,
    min_payoff_ratio=1.05,
    min_trades_per_year=10,
    min_year_profit=0.0,
    min_full_period_uptrend_r2=0.5,
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


def _overfit_advisory(candidates, labels, primary, run_ids=None, trial_runs=None):
    """C1 — PBO(CSCV)·DSR 실측치(advisory). 어떤 실패도 흡수한다(판정 불변).

    - PBO: 선택 풀(베이스라인 제외, csv 보유) 후보들의 일별 손익 행렬로 CSCV.
    - DSR: 선택 후보의 일별 손익(거래일 기준).
    - n_trials [N5 교정 2026-06-11]: 종전엔 CLDGEN_%만 세서 **TMAP 스윕 그리드
      (최대 다중성 원천, 재설계 문서 T3가 명시한 '그리드 전체=시도 집합')가
      누락**됐다 — 설계-구현 불일치. 이제 선택 대상 run + --trial-runs(후보를
      낳은 스윕 run들) + 사이클 CLDGEN 풀의 고유 매수 전략 수를 합산한다
      (중복은 DISTINCT로 제거, 과대 계상 쪽이 보수적).
    - pool_independence [N2 2026-06-11]: 후보 풀 평균 상관·유효 독립 후보 수
      병기 — 1-D 변형 쌍둥이 풀에서 PBO 과소평가 위험 공시.
    """
    out = {"note": "advisory only — selection/판정에 미사용", "pbo": None, "dsr": None}
    try:
        series = {}
        for c in candidates:
            if c.status == "ok" and c.csv_path:
                s = daily_pnl_series(c.csv_path)
                if s:
                    series[f"gen{c.gen_no}:{labels.get(c.gen_no, '')}"] = s
        if len(series) >= 2:
            _days, names, matrix = align_daily_matrix(series)
            out["pbo"] = pbo_cscv(matrix, n_blocks=8)
            if out["pbo"] is not None:
                out["pbo"]["pool"] = names
        else:
            out["pbo_blocked"] = f"csv 보유 후보 {len(series)}개(<2) — PBO 계산 불가"

        trial_run_ids = [str(r) for r in (list(run_ids or []) + list(trial_runs or []))]
        con = sqlite3.connect(str(RUNS_DB))
        try:
            in_clause = ""
            if trial_run_ids:
                placeholders = ",".join("?" for _ in trial_run_ids)
                in_clause = f"run_id IN ({placeholders}) OR "
            n_trials = con.execute(
                "SELECT COUNT(DISTINCT buy_name) FROM generations"
                f" WHERE {in_clause}(run_id LIKE 'cldgen_%' AND buy_name LIKE 'CLDGEN_%')",
                trial_run_ids,
            ).fetchone()[0]
        finally:
            con.close()
        out["n_trials_definition"] = (
            "이 선택을 낳은 평가 점 전체의 고유 매수 전략 수 = 선택 대상 run"
            " + trial-runs(TMAP 스윕 그리드) + 사이클 CLDGEN 풀"
            " (N5 교정: 종전 CLDGEN만 카운트 → 스윕 그리드 누락 수정)"
        )
        out["n_trials"] = int(n_trials or 1)
        out["n_trials_runs"] = trial_run_ids

        if primary.selected_candidate is not None and primary.selected_candidate.csv_path:
            s = daily_pnl_series(primary.selected_candidate.csv_path)
            if s:
                out["dsr"] = deflated_sharpe_ratio(
                    list(s.values()), n_trials=max(int(n_trials or 1), 1)
                )
                if out["dsr"] is not None:
                    out["dsr"]["definition"] = "선택 후보의 거래일 기준 일별 손익 DSR"
                # R3(2026-06-11) — 블록 부트스트랩 MC: 일별 손익 블록 재추출로 레짐
                #   군집을 보존한 총손익·MDD(낙폭금액) 분포. iid 거래 추출 MC의
                #   OOS 전이 실패(6/2) 교훈 반영. advisory 전용.
                mc = block_bootstrap_daily(list(s.values()))
                if mc is not None:
                    mc.pop("fan", None)  # 아티팩트엔 요약만(팬차트는 /freeze_mc 라우트).
                    out["mc_block_bootstrap"] = mc

        # R7(2026-06-11) — 후보 간 일별 손익 상관(포트폴리오/앙상블 재료).
        if len(series) >= 2:
            corr = daily_correlation_matrix(series)
            out["daily_correlation"] = corr
            if corr:
                eff = effective_independent_count(corr)  # N2 — PBO 신뢰도 주석.
                if eff:
                    out["pool_independence"] = eff
    except Exception as exc:  # noqa: BLE001 - advisory는 절대 판정을 막지 않는다.
        out["error"] = str(exc)
    return out


def main() -> int:
    # N5 — --trial-runs=<run_id,...>: 후보를 낳은 스윕 run들(시도 횟수에 합산).
    trial_runs: list = []
    args = []
    for a in sys.argv[1:]:
        if a.startswith("--trial-runs="):
            trial_runs = [s for s in a.split("=", 1)[1].split(",") if s]
        else:
            args.append(a)
    run_ids = args or ["cldgen_train_2023_2025_20260610"]
    run_label = "+".join(run_ids)
    config_hash = hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()

    rows = _load_rows(run_ids)
    if not rows:
        print(f"no rows for run_ids={run_ids}")
        return 2

    candidates, labels = [], {}
    seed_profile = None
    seed_csv = ""  # M1 — 거래 중복도 비교용 시드 per-trade CSV.
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
            seed_csv = d.get("csv_path") or ""
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
        thresholds=SEED_ALIGNED_YEARLY_THRESHOLDS,
    )
    write_yearly_sparse_robust_artifact(advisory, EVID / "p5-yearly-advisory.json")

    # ── C1: 과적합 advisory (PBO/CSCV + DSR) — 분석 전용, 판정 불변 ────────
    overfit = _overfit_advisory(
        candidates, labels, primary, run_ids=run_ids, trial_runs=trial_runs
    )
    (EVID / "p5-overfit-advisory.json").write_text(
        json.dumps(overfit, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # ── M1(2026-06-11): 시드↔선택 후보 거래 중복도 — V6(대체 vs 보완) 입력 ──
    overlap = None
    if (primary.selected_candidate is not None and seed_csv
            and primary.selected_candidate.csv_path):
        from ai_strategy_loop.fitness.trade_overlap import trade_overlap  # noqa: PLC0415

        overlap = trade_overlap(seed_csv, primary.selected_candidate.csv_path)
        if overlap:
            (EVID / "p5-trade-overlap.json").write_text(
                json.dumps(overlap, ensure_ascii=False, indent=2), encoding="utf-8"
            )

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
