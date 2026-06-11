"""A2 — 다년 지도에서 고원 θ*를 판독하고 동결 재평가 배치(pairs)를 생성한다.

입력: tmap_sweep이 남긴 run_id (다년 train 지도).
판독 규칙(사전선언, tmap_walkforward.select_theta와 동일 정신):
  - 적격 슬롯: plateau 존재 AND positive_ratio >= 0.5 AND 고원 평균손익 > 베이스라인 손익.
  - plateau_score 내림차순 상위 슬롯들에서:
      싱글 θ*: 상위 max_singles개 슬롯의 고원 중심값 1개 변경.
      조합 점: 상위 2~3개 슬롯의 고원 중심 조합(2-슬롯 쌍 전부 + 3-슬롯 1개) 4~6개.
  - 조합은 인샘플 advisory — 동결 판정은 재평가 run의 seed_relative_v1이 한다.

출력:
  - theta_star_summary.json : 슬롯별 적격 판정·θ*·조합 정의(근거 포함)
  - pairs-theta-star.json   : [BASE_SEED + 싱글 + 조합] 배치 평가용 pairs
  - 전략은 loop_strategies.db에 THETA_* 이름으로 주입(공식 가드 통과 필수)

실행(스윕 완료 후):
  PYTHONUTF8=1 python .omo/evidence/tmap-walkforward/gen_theta_star_batch.py <sweep_run_id> [--dry-run]
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

import ai_strategy_loop.bootstrap as bootstrap  # noqa: E402
from ai_strategy_loop.tmap.tendency import summarize_tendency  # noqa: E402
from ai_strategy_loop.tmap.template import (  # noqa: E402
    load_template,
    render,
    validate_rendered,
)

EVID = Path(__file__).resolve().parent
SEED_BUY = "Tick_B_902_905_Update_2"
SEED_SELL = "Tick_S_902_905_Update_2"
TEMPLATE = "seed_902905"
MAX_SINGLES = 3
MAX_COMBOS = 6


def _dominant_plateau(curve: list[dict], base_profit: float) -> dict | None:
    """v2(사전선언 보조 규칙): profit이 베이스라인을 '엄격 초과'하는 최장 연속 구간.

    v1(전체 흑자 고원 평균>베이스라인)은 전 점이 흑자인 슬롯에서 고원이 곡선
    전체로 잡혀 평균이 희석되는 약점이 있다(전 슬롯 부적격 위험). v2는 베이스라인
    '지배' 구간만 고원으로 본다. 폭 >= 2(이웃 동반 흑자 — 고원다움) 요구.

    [2026-06-11 배치 실행 전 교정] 비교를 >= 에서 > 로 강화한다. 이유: 본 스윕에서
    stop_deep·trail_keep이 모든 값에서 베이스라인과 바이트 동일 결과(불활성 슬롯
    — 해당 분기가 한 번도 발동하지 않음)를 내며 등호로 '지배 고원'에 적격 판정됐다.
    개선 증거가 0인 점(profit == base)은 지배가 아니다 — 등호 포함 시 시드와 동일한
    후보가 배치를 점유하고, 실제 우세 슬롯(trail_start)이 싱글 정원에서 밀린다.
    이 교정은 특정 결과를 고르는 사후 선택이 아니라 규칙의 퇴화 케이스 제거이며,
    적용 후 재판독 결과를 그대로 따른다.
    """
    best = None
    run: list[dict] = []
    for p in curve:
        # [N9] max(base, 0): 베이스라인이 적자여도 절대 흑자가 아닌 점은 지배 아님.
        if p.get("ok") and p["profit"] > max(base_profit, 0.0):
            run.append(p)
        else:
            run = []
        if len(run) >= 2 and (best is None or len(run) > best["width"]
                              or (len(run) == best["width"]
                                  and sum(q["profit"] for q in run) / len(run) > best["mean_profit"])):
            center = run[len(run) // 2]
            best = {
                "width": len(run),
                "center_value": center["value"],
                "mean_profit": sum(q["profit"] for q in run) / len(run),
                "min_profit": min(q["profit"] for q in run),
                "values": [q["value"] for q in run],
            }
    return best


def qualified_slots(summary: dict) -> list[dict]:
    """적격 슬롯을 plateau_score 내림차순으로 돌려준다(근거 포함).

    적격 = v1(positive_ratio>=0.5 AND 고원 평균>베이스라인)
        OR v2(베이스라인 지배 연속 구간 폭>=2). v1 실패·v2 통과 슬롯의
    θ* 중심값은 v2 지배 고원의 중심을 쓴다(qualified_rule 필드에 명시).
    """
    base_profit = float((summary.get("baseline") or {}).get("profit") or 0.0)
    out = []
    for name, m in (summary.get("params") or {}).items():
        plateau = m.get("plateau")
        curve = m.get("curve") or []
        reasons = []
        if not plateau:
            reasons.append("no plateau")
        else:
            if (m.get("positive_ratio") or 0.0) < 0.5:
                reasons.append(f"positive_ratio {m.get('positive_ratio')} < 0.5")
            # [N9] max(base, 0): 적자 베이스라인 구간에서 '덜 나쁜' 적자 고원 차단.
            if plateau["mean_profit"] <= max(base_profit, 0.0):
                reasons.append(
                    f"plateau mean {plateau['mean_profit']:,.0f}"
                    f" <= max(baseline {base_profit:,.0f}, 0)"
                )
        v1_ok = not reasons
        dominant = _dominant_plateau(curve, base_profit)
        rule = "v1" if v1_ok else ("v2_dominant" if dominant else None)
        effective = plateau if v1_ok else dominant
        out.append({
            "param": name,
            "qualified": rule is not None,
            "qualified_rule": rule,
            "reject_reasons": [] if rule else reasons + ["no dominant sub-plateau (width>=2)"],
            "v1_reject_reasons": reasons,
            "plateau_score": m.get("plateau_score"),
            "positive_ratio": m.get("positive_ratio"),
            "plateau": m.get("plateau"),
            "dominant_plateau": dominant,
            "effective_plateau": effective,
            "cliff": m.get("cliff"),
        })
    out.sort(key=lambda s: -(s["plateau_score"] or 0.0))
    return out


def build_points(slots: list[dict]) -> list[dict]:
    """싱글 θ*(상위 MAX_SINGLES) + 조합 점(상위 2~3 슬롯 쌍/트리플)."""
    qual = [s for s in slots if s["qualified"]][:MAX_SINGLES]
    points = []
    for s in qual:
        theta = {s["param"]: s["effective_plateau"]["center_value"]}
        points.append({"label": f"THETA {s['param']}={s['effective_plateau']['center_value']}",
                       "theta": theta, "kind": "single"})
    combos = []
    for a, b in itertools.combinations(qual, 2):
        combos.append({a["param"]: a["effective_plateau"]["center_value"],
                       b["param"]: b["effective_plateau"]["center_value"]})
    if len(qual) >= 3:
        combos.append({s["param"]: s["effective_plateau"]["center_value"] for s in qual[:3]})
    for theta in combos[:MAX_COMBOS]:
        label = "THETA " + "+".join(f"{k}={v}" for k, v in sorted(theta.items()))
        points.append({"label": label, "theta": theta, "kind": "combo"})
    return points


def _merged_summary(run_ids: list[str]) -> dict:
    """복수 run_id의 스윕 행을 합산해 summarize_tendency와 동일 구조를 만든다.

    파트 분할 재기동(같은 윈도우·같은 config) 시 사용. 단일 run이면
    summarize_tendency 결과 그대로다. 베이스라인은 첫 발견 행을 쓰고,
    같은 (param,value) 중복은 뒤 run의 행(재측정)을 우선한다.
    """
    if len(run_ids) == 1:
        return summarize_tendency(run_ids[0])
    from ai_strategy_loop.tmap.tendency import (  # noqa: PLC0415
        _curve_for,
        load_sweep_rows,
        plateau_metrics,
    )
    dedup: dict = {}
    for rid in run_ids:
        for r in load_sweep_rows(rid):
            dedup[(r["param"], r["value"])] = r
    rows = list(dedup.values())
    out = {"run_id": "+".join(run_ids), "baseline": None, "params": {}, "count": len(rows)}
    if not rows:
        return out
    base = next((r for r in rows if r["param"] == "__default__"), None)
    if base is not None:
        out["baseline"] = {
            "profit": float(base.get("profit") or 0.0),
            "mdd": float(base.get("mdd") or 0.0),
            "trades": int(base.get("trade_count") or 0),
            "status": base.get("status"),
        }
    base_profit = abs(out["baseline"]["profit"]) if out["baseline"] else 1.0
    for name in sorted({r["param"] for r in rows if r["param"] != "__default__"}):
        curve = _curve_for(rows, name)
        metrics = plateau_metrics(curve)
        plateau = metrics.get("plateau")
        score = 0.0
        if plateau:
            score = (metrics["positive_ratio"] * plateau["width"]
                     * (plateau["mean_profit"] / max(base_profit, 1.0)))
        out["params"][name] = {"curve": curve, **metrics, "plateau_score": round(score, 4)}
    return out


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    run_ids = args or ["tmap_seed_full_train_20260611"]
    run_id = "+".join(run_ids)

    summary = _merged_summary(run_ids)
    if not summary.get("count"):
        print(f"no sweep rows for run_ids={run_ids}")
        return 2
    slots = qualified_slots(summary)
    points = build_points(slots)

    template = load_template(TEMPLATE)
    # window_end 슬롯은 int여야 한다(시분초 비교) — float 중심값 방어 변환.
    int_params = {p.name for p in template.params if isinstance(p.default, int)}
    for pt in points:
        pt["theta"] = {k: (int(v) if k in int_params else v) for k, v in pt["theta"].items()}
        pt["label"] = "THETA " + "+".join(f"{k}={v}" for k, v in sorted(pt["theta"].items()))

    pairs = [{"label": "BASE_SEED", "buy": SEED_BUY, "sell": SEED_SELL}]
    injected = []
    for i, pt in enumerate(points):
        buy_code, sell_code = render(template, pt["theta"])
        errors = validate_rendered(buy_code, sell_code, template.timeframe)
        if errors:
            pt["status"] = f"guard_failed: {errors}"
            continue
        bn, sn = f"THETA_{TEMPLATE}_{i:02d}_B", f"THETA_{TEMPLATE}_{i:02d}_S"
        if not dry_run:
            from cli.strategy_generator import save_strategy_to_db  # noqa: PLC0415
            db = str(bootstrap.LOOP_DB_STRATEGY)
            r1 = save_strategy_to_db(db, bn, buy_code, "buy")
            r2 = save_strategy_to_db(db, sn, sell_code, "sell")
            if r1.get("status") != "ok" or r2.get("status") != "ok":
                pt["status"] = f"save_failed: {r1} {r2}"
                continue
        pt["status"] = "ok"
        pt["buy_name"], pt["sell_name"] = bn, sn
        pairs.append({"label": pt["label"], "buy": bn, "sell": sn})
        injected.append(pt)

    (EVID / "theta_star_summary.json").write_text(
        json.dumps({"sweep_run_id": run_id, "baseline": summary.get("baseline"),
                    "slots": slots, "points": points, "dry_run": dry_run},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if not dry_run:
        (EVID / "pairs-theta-star.json").write_text(
            json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(f"sweep_run={run_id} qualified={sum(1 for s in slots if s['qualified'])}"
          f"/{len(slots)} points={len(injected)} (dry_run={dry_run})")
    for s in slots:
        mark = "O" if s["qualified"] else "X"
        plateau = s.get("effective_plateau") or s.get("plateau") or {}
        print(f"  [{mark}] {s['param']}: score={s['plateau_score']} rule={s.get('qualified_rule')}"
              f" center={plateau.get('center_value')}"
              f" width={plateau.get('width')} pos={s['positive_ratio']}"
              + ("" if s["qualified"] else f" — {'; '.join(s['reject_reasons'])}"))
    for pt in points:
        print(f"  -> {pt['kind']}: {pt['label']} [{pt.get('status')}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
