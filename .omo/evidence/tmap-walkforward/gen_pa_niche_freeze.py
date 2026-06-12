"""P-A 첫 적용 (2026-06-12) — multiseed 풀에 absolute_niche_v1 선택·동결.

사전선언(portfolio_corr_scan_20260612.md §다음 절차 그대로):
- 풀: multiseed_train_20260611의 비-BASE 후보 전원(선별 없음).
- 니치 자격 측정치(주입): 오늘 실측한 THETA 일별 상관 — g20 0.318, g9 0.444,
  g8 0.560, g14 0.547. 나머지는 미측정(None) → 선택기가 판정불가 기각(설계).
- 아티팩트: pa_niche_selected_20260612.json — **챔피언 p5-* 경로와 분리**
  (덮어쓰기 사고 원천 차단).
- n_trials 공시: multiseed 21 + 시드 패밀리 누적은 OOS 결과 카드에 병기.
실행: PYTHONUTF8=1 python .omo/evidence/tmap-walkforward/gen_pa_niche_freeze.py
"""
from __future__ import annotations

import hashlib
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller.candidate_selection import (  # noqa: E402
    NicheMetricEntry,
    parse_candidate_generation,
    select_absolute_niche_v1,
    write_absolute_niche_artifact,
)

EVID = Path(__file__).resolve().parent
RUNS_DB = REPO / "ai_strategy_loop" / "state" / "loop_runs.db"
CONFIG = REPO / ".omo/evidence/claude-condition-research-20260610/train-config.json"
RUN_ID = "multiseed_train_20260611"
OUT = EVID / "pa_niche_selected_20260612.json"

# 오늘 실측(portfolio_corr_scan_20260612.md + 보완 측정) — THETA 일별 상관.
# 시간버킷은 같은 창(09:00~09:30) 시드 계열이라 '겹침' — corr 분기만 사용.
# 보완 사유(2차 실행): 1차에서 절대 기준 통과자가 '미측정'만으로 기각되는 것은
# 측정 누락이지 성과 기반 판정이 아니므로, OOS 접촉 전에 전원 측정해 재선택.
NICHE_METRICS = {
    0: NicheMetricEntry(corr_vs_frozen=0.896, time_bucket_overlap=True),
    1: NicheMetricEntry(corr_vs_frozen=0.548, time_bucket_overlap=True),
    2: NicheMetricEntry(corr_vs_frozen=0.488, time_bucket_overlap=True),
    8: NicheMetricEntry(corr_vs_frozen=0.560, time_bucket_overlap=True),
    9: NicheMetricEntry(corr_vs_frozen=0.444, time_bucket_overlap=True),
    12: NicheMetricEntry(corr_vs_frozen=0.639, time_bucket_overlap=True),
    13: NicheMetricEntry(corr_vs_frozen=0.470, time_bucket_overlap=True),
    14: NicheMetricEntry(corr_vs_frozen=0.547, time_bucket_overlap=True),
    16: NicheMetricEntry(corr_vs_frozen=0.636, time_bucket_overlap=True),
    20: NicheMetricEntry(corr_vs_frozen=0.318, time_bucket_overlap=True),
}


def main() -> int:
    con = sqlite3.connect(str(RUNS_DB))
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT gen_no, status, score, gate_passed, reason, profit, total_profit_pct,"
        " mdd, trade_count, daily_avg_trades, payoff_ratio, max_hold_count,"
        " buy_name, sell_name, csv_path, strategy_gist"
        " FROM generations WHERE run_id=? ORDER BY gen_no", (RUN_ID,)
    ).fetchall()
    con.close()

    candidates, labels = [], {}
    for r in rows:
        d = dict(r)
        gist = d.pop("strategy_gist", "") or ""
        labels[int(d["gen_no"])] = gist
        d["gate_passed"] = bool(d.get("gate_passed"))
        for k in ("payoff_ratio", "max_hold_count", "profit", "mdd",
                  "daily_avg_trades", "score"):
            if d.get(k) is None:
                d[k] = 0.0
        if d.get("csv_path") is None:
            d["csv_path"] = ""
        if gist.startswith("BASE_"):
            continue  # 출처 기준 제외(사전선언) — 베이스라인은 발굴 후보가 아님.
        candidates.append(parse_candidate_generation(d))

    # OOS 기접촉 제외(3차 실행에서 추가된 규율 — 사후 재선택 금지의 적용):
    # 고정 OOS run에 buy_name이 등장한 후보는 같은 OOS로 재동결 불가.
    # 해당 후보의 경로는 패자부활 레지스트리(신규 데이터)뿐이다.
    # 실측: gen2 CLDGEN_0610_C7_SEEDPLUS_B — 6/10 동결·OOS 기각 이력
    # (cldgen_oos_2022/2026_20260610, 2026 -229,360) → 풀에서 제외.
    con2 = sqlite3.connect(str(RUNS_DB))
    seen = {r[0] for r in con2.execute(
        "SELECT DISTINCT buy_name FROM generations WHERE run_id LIKE '%oos%'"
    ).fetchall()}
    con2.close()
    excluded = [c for c in candidates if c.buy_name in seen]
    for c in excluded:
        print(f"  [OOS 기접촉 제외] gen{c.gen_no} {c.buy_name} — 재동결 불가(부활 경로만)")
    candidates = [c for c in candidates if c.buy_name not in seen]

    config_hash = hashlib.sha256(CONFIG.read_bytes()).hexdigest()
    result = select_absolute_niche_v1(
        candidates, niche_metrics=NICHE_METRICS, run_id=RUN_ID,
        config_path=str(CONFIG), config_hash=config_hash,
    )
    write_absolute_niche_artifact(result, OUT)

    print(f"selector={result.selector_version} selected={result.selected}")
    if result.selected_candidate is not None:
        c = result.selected_candidate
        print(f"  -> gen{c.gen_no} [{labels.get(c.gen_no, '')}]"
              f" buy={c.buy_name} sell={c.sell_name}")
        print(f"     profit={c.profit:,.0f} mdd={c.mdd} trades={c.trade_count}"
              f" payoff={c.payoff_ratio}")
    print("eligible:", [(e.gen_no, labels.get(e.gen_no, "")) for e in result.eligible_candidates])
    for rj in result.rejected_candidates:
        print(f"  rejected gen{rj.gen_no} [{labels.get(rj.gen_no, '')[:36]}]:"
              f" {'; '.join(rj.reasons)[:110]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
