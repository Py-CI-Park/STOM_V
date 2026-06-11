"""M5 (2026-06-11) — 다중 시드 발굴: 이력 전체에서 제2·제3의 산 후보 추출.

전 시스템이 시드 1개(902/905)에 앵커돼 있고, 오늘 동결 후보조차 그 시드의
정제판(거래 중복도 0.888)임이 실측됐다 — 시드의 엣지가 죽으면 함께 죽는
집중 리스크. loop_runs.db의 **전 run 이력**에서 성과 상위 (매수,매도) 쌍을
추려 같은 train 창 재평가 배치(pairs)를 만든다. LLM 호출 0회.

사용:
  PYTHONUTF8=1 python -m ai_strategy_loop.scripts.gen_multiseed_pairs \
      --top 30 --out .omo/evidence/tmap-walkforward/pairs-multiseed.json
  → claude_candidate_batch_eval --pairs-json <out> --config-json <train> ...

주의(정직): 이력 손익은 서로 다른 창/설정에서 측정된 값이라 **순위 참고용**
일 뿐이다. 동일 창 재평가가 끝나야 비교 가능하다(그래서 이 스크립트는
후보 나열까지만 하고 평가는 배치 도구가 한다).
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Dict, List

# 발굴 대상에서 제외할 접두사: 오늘 파생물(시드 정제판·대조군·전진분석 산물)과
#   베이스라인 재측정 — '새로운 산'을 찾는 게 목적이므로.
EXCLUDE_PREFIXES = ("TMAP_", "THETA_", "PLACEBO", "WF_")
EXCLUDE_GIST_PREFIXES = ("BASE_", "TMAP ", "THETA ", "PLACEBO", "WF_")


def top_pairs(
    db_path: str, top: int = 30, min_trades: int = 30
) -> List[Dict[str, object]]:
    """이력 ok 세대에서 (buy,sell) 쌍별 최고 손익 상위 top개. 실패는 빈 리스트."""
    try:
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute(
                "SELECT buy_name, sell_name, MAX(profit) AS best_profit,"
                " MAX(trade_count) AS trades, MAX(strategy_gist) AS gist"
                " FROM generations"
                " WHERE status='ok' AND gate_passed=1 AND profit > 0"
                " GROUP BY buy_name, sell_name"
                " ORDER BY best_profit DESC",
            ).fetchall()
        finally:
            con.close()
    except Exception:  # noqa: BLE001
        return []
    out: List[Dict[str, object]] = []
    for r in rows:
        buy = str(r["buy_name"] or "")
        gist = str(r["gist"] or "")
        if not buy or any(buy.startswith(p) for p in EXCLUDE_PREFIXES):
            continue
        if any(gist.startswith(p) for p in EXCLUDE_GIST_PREFIXES):
            continue
        if int(r["trades"] or 0) < min_trades:
            continue
        out.append({
            "label": f"MULTISEED {buy}",
            "buy": buy,
            "sell": str(r["sell_name"] or ""),
            "history_best_profit": float(r["best_profit"] or 0.0),
            "history_trades": int(r["trades"] or 0),
        })
        if len(out) >= top:
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--min-trades", type=int, default=30)
    ap.add_argument("--out", required=True)
    ap.add_argument("--db", default="")
    args = ap.parse_args()

    if args.db:
        db = args.db
    else:
        from ai_strategy_loop.controller.state import LOOP_RUNS_DB  # noqa: PLC0415

        db = str(LOOP_RUNS_DB)
    pairs = top_pairs(db, top=args.top, min_trades=args.min_trades)
    # 배치 도구 계약: pairs JSON은 label/buy/sell만 필요 — 참고 필드는 함께 저장.
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[MULTISEED] {len(pairs)} pairs -> {args.out}")
    for p in pairs[:10]:
        print(f"  {p['label']} (이력 최고 {p['history_best_profit']:,.0f} / {p['history_trades']}건)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
