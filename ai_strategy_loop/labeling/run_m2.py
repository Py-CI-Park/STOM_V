"""M-2 실행기 — 변수 정보력 랭킹 → 이익 포켓 → 얕은 트리 → 흑자 영역 게이트.

산출: state/labels/design/_m2_report.json (관측 권위). 게이트 판정 포함:
확정 이익 포켓(일 클러스터 FDR 통과·인접 2칸+)이 0이면 min 레인 피벗 신호.
"""

from __future__ import annotations

import itertools
import json
import os
import time

from ai_strategy_loop.labeling.info_rank import (
    profit_pockets, rank_variables, shallow_tree_paths,
)
from ai_strategy_loop.labeling.terrain import load_usable

_OUT = os.path.join(os.path.dirname(__file__), "..", "state", "labels", "design",
                    "_m2_report.json")

VARIABLES = [
    "등락율", "체결강도", "초당거래대금", "초당매수수량", "초당매도수량",
    "당일거래대금", "거래대금증감", "전일비", "회전율", "전일동시간비",
    "시가총액", "고저평균대비등락율", "저가대비고가등락율", "매도총잔량", "매수총잔량",
    "시가등락율", "시가대비등락율", "초당순매수금액", "spread_pct", "일중위치", "분",
]
LABEL = "frA_300"
_PAIR_CORR_CAP = 0.6
_TOP_FOR_PAIRS = 8
_MAX_PAIRS = 12


def main() -> dict:
    t0 = time.time()
    frame = load_usable(["일자", *VARIABLES])
    print(f"loaded rows={len(frame)} {time.time()-t0:.0f}s", flush=True)

    ranking = rank_variables(frame, VARIABLES, label=LABEL)
    print(f"ranked {time.time()-t0:.0f}s", flush=True)

    top = [v for v in ranking[ranking["fdr_pass"]]["변수"] if v != "분"][:_TOP_FOR_PAIRS]
    corr = frame[top].corr().abs()
    pairs = [(a, b) for a, b in itertools.combinations(top, 2)
             if corr.loc[a, b] < _PAIR_CORR_CAP][:_MAX_PAIRS]
    pockets = []
    for var_x, var_y in pairs:
        found = profit_pockets(frame, var_x, var_y, label=LABEL)
        pockets.extend(found)
        print(f"pair {var_x}×{var_y}: pockets={len(found)} {time.time()-t0:.0f}s", flush=True)
    pockets.sort(key=lambda p: p["mean_pp"] * p["n"], reverse=True)

    tree_vars = [v for v in ranking["변수"].head(10) if v != "분"]
    paths = shallow_tree_paths(frame, tree_vars, label=LABEL, max_depth=3)
    print(f"tree paths={len(paths)} {time.time()-t0:.0f}s", flush=True)

    report = {
        "label": LABEL,
        "rows": int(len(frame)),
        "ranking": ranking.to_dict(orient="records"),
        "pairs_scanned": [list(p) for p in pairs],
        "pockets": pockets[:20],
        "tree_paths": paths[:10],
        "gate_profit_region_exists": bool(pockets or paths),
        "elapsed_sec": round(time.time() - t0, 1),
    }
    with open(_OUT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print(json.dumps({"pockets": len(pockets), "tree_paths": len(paths),
                      "gate": report["gate_profit_region_exists"]}, ensure_ascii=False))
    return report


if __name__ == "__main__":
    main()
