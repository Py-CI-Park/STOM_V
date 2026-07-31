"""다후보 라운드 러너 (QSP1 P3) — 1회 호출 = 1라운드(재개 가능·감사 가능).

사용자 방법론: "하나의 조건식이 아니라 여러 후보를 생성하여 모두 평가·분석하여
개선해 나가는 방식" + "한번 개선으로 항상 좋아질 수는 없다 — 여러 개가 복합적으로".

라운드 절차(전 단계가 기존 공식 부품 재사용 — 사설 채점 금지):
  1) base 매수식 + 직전 라벨 CSV → proposer 로 N개 수정 명세(서로 다른 리프/변수 축).
  2) 각 명세: apply → intent_gate → PASS 만 loop_strategies.db 등록(INSERT-only).
  3) 공식 배치(claude_candidate_batch_eval) 로 base+후보 전부 평가.
  4) 세대 행(공식 채점)에서 객관값을 뽑아 베스트 선택 + 교훈(무효 축) 합성.
  5) convergence.judge 로 계속/수렴/발산 판정.
  6) 라운드 기록 JSON 저장(rounds/) — 대시보드 라운드 보드가 읽는다.

CLI:
  python -m ai_strategy_loop.revision.round_runner \
      --base-buy QSP1_M_HIER_900_1500_B --base-sell QSP1_M_HIER_900_1500_S \
      --config docs/research/quant_scoring_pipeline/config_qsp1_min_1mo.json \
      --tag qsp1min1mo --round 1 --n 3
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[2]
ROUNDS_DIR = REPO / "docs" / "research" / "quant_scoring_pipeline" / "rounds"
LOOP_DB = REPO / "ai_strategy_loop" / "state" / "loop_strategies.db"
PY = sys.executable


def _read_rounds(tag: str) -> List[Dict[str, Any]]:
    out = []
    if ROUNDS_DIR.exists():
        for p in sorted(ROUNDS_DIR.glob(f"{tag}_r*.json")):
            if p.name.endswith("_pairs.json"):  # 배치 입력(리스트) — 라운드 기록 아님.
                continue
            try:
                doc = json.loads(p.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            if isinstance(doc, dict) and "round" in doc:
                out.append(doc)
    return sorted(out, key=lambda r: r.get("round", 0))


def _register_buy(name: str, code: str) -> None:
    con = sqlite3.connect(LOOP_DB)
    try:
        if con.execute('SELECT 1 FROM stockbuy WHERE "index"=?', (name,)).fetchone():
            con.execute('DELETE FROM stockbuy WHERE "index"=?', (name,))  # 같은 라운드 재실행 허용
        con.execute('INSERT INTO stockbuy ("index","전략코드") VALUES (?,?)', (name, code))
        con.commit()
    finally:
        con.close()


def _load_code(name: str) -> Optional[str]:
    from ai_strategy_loop.controller.strategy_preflight import load_loop_strategy_code

    return load_loop_strategy_code("buy", name)


def _gen_rows(run_id: str) -> List[Dict[str, Any]]:
    from ai_strategy_loop.controller.state import LoopState

    st = LoopState(readonly=True)
    try:
        return list(st.get_generations(run_id))
    finally:
        st.close()


def _objective(rows: List[Dict[str, Any]]) -> None:
    """행마다 objective 주입: 게이트 통과가 하나라도 있으면 score, 아니면 총손익."""
    any_gate = any(bool(r.get("gate_passed")) for r in rows)
    for r in rows:
        r["objective"] = float(r.get("score", 0) or 0) if any_gate else float(r.get("profit", 0) or 0)


def _holdout_label_csv(prev: List[Dict[str, Any]], holdout_config: Optional[str],
                       base_name: str) -> Optional[str]:
    """base 의 홀드아웃 라벨 CSV — 직전 라운드 홀드아웃 run, 없으면 baseline 포인터.

    drop 제안(QSP3)은 '홀드아웃도 손실' 확인이 필수라 base 의 표본외 거래 CSV 가 필요.
    base == 직전 베스트이므로 직전 라운드의 홀드아웃 run 이 정확히 그 CSV 다.
    """
    run_id = None
    if prev and (prev[-1].get("holdout") or {}).get("run_id"):
        run_id = prev[-1]["holdout"]["run_id"]
    elif holdout_config:
        ptr = Path(holdout_config).with_suffix(".baseline.json")
        if ptr.exists():
            run_id = json.loads(ptr.read_text(encoding="utf-8")).get("run_id")
    if not run_id:
        return None
    rows = [r for r in _gen_rows(run_id) if r.get("status") == "ok" and r.get("csv_path")]
    if not rows:
        return None
    named = [r for r in rows if r.get("buy_name") == base_name]
    return str((named or rows)[0]["csv_path"])


def run_round(base_buy: str, base_sell: str, config_path: str, tag: str,
              round_no: int, n_cand: int,
              holdout_config: Optional[str] = None,
              actions: str = "tighten") -> Dict[str, Any]:
    from ai_strategy_loop.autopsy import label_dataset as lds
    from ai_strategy_loop.revision import intent_gate as gate
    from ai_strategy_loop.revision import filtersmith
    from ai_strategy_loop.revision import proposer
    from ai_strategy_loop.revision import surgeon
    from ai_strategy_loop.revision.convergence import RoundStat, judge

    ROUNDS_DIR.mkdir(parents=True, exist_ok=True)
    prev = _read_rounds(tag)
    # 중복 라운드 가드 — 죽은 드라이버의 잔존 러너가 기록을 남긴 뒤 재기동하면
    #   같은 round_no 가 이력으로 읽혀 base 가 뒤바뀐다(qsp2anch 실사고). exit 3.
    if any(r.get("round") == round_no for r in prev):
        print(f"[ROUND{round_no}] 기록이 이미 존재 — 건너뜀(드라이버는 다음 라운드로)", flush=True)
        raise SystemExit(3)
    # 라벨 CSV: 직전 라운드 베스트의 CSV. 첫 라운드는 base 의 기준 CSV(직전 평가 run).
    if prev:
        label_csv = prev[-1]["best"]["csv_path"]
        base_code_name = prev[-1]["best"]["buy_name"]
        seed_trades = int(prev[0]["base"].get("trade_count") or 0)  # None 가드(감사 BUG-G)
    else:
        base_run = json.loads(Path(config_path).with_suffix(".baseline.json").read_text(encoding="utf-8")) \
            if Path(config_path).with_suffix(".baseline.json").exists() else None
        if not base_run:
            raise SystemExit("첫 라운드에는 <config>.baseline.json({run_id}) 이 필요합니다 — base 평가 run 지정")
        rows = _gen_rows(base_run["run_id"])
        base_row = next(r for r in rows if r.get("buy_name") == base_buy)
        label_csv = str(base_row["csv_path"])
        base_code_name = base_buy
        seed_trades = int(base_row.get("trade_count", 0) or 0)

    base_code = _load_code(base_code_name)
    if not base_code:
        raise SystemExit(f"base 매수식 로드 실패: {base_code_name}")

    ds = lds.build(str(REPO / label_csv) if not os.path.isabs(str(label_csv)) else str(label_csv))
    # P3.1(F-R3-1) 교훈 환류 — 이전 라운드들에서 base 대비 |Δ| 가 미미했던(사실상 무효)
    #   (축, 리프) 조합은 재제안하지 않는다. 임계: base objective 의 1% 또는 10만원 중 큰 값.
    exclude_axes: List[tuple] = []
    for rec in prev:
        base_obj = abs(float((rec.get("base") or {}).get("objective") or 0.0))
        thresh = max(base_obj * 0.01, 100_000.0)
        for lesson in rec.get("lessons", []):
            # abs() 제거(감사 BUG-D): 크게 악화된 축(delta 음수)도 제외 대상.
            #   '유의미하게 양(+)' 이 아니면 재제안 금지 — 양의 축은 tried_specs 가
            #   동일 상수 반복만 차단하므로 base 갱신 시 재시도가 살아있다.
            if float(lesson.get("delta_vs_base") or 0.0) < thresh:
                exclude_axes.append((lesson.get("axis"), lesson.get("leaf")))
    # BUG-4 교정: 이전 라운드에서 이미 평가된 (변수, 리프, 상수) 동일 제안은 재백테 금지.
    tried_specs = set()
    for rec in prev:
        for m in rec.get("candidates", []):
            sp = m.get("spec") or {}
            # apply_fail/gate_fail 도 포함(재검증 구멍 1): 같은 명세는 결정적으로
            #   같은 실패를 반복하므로 재생성은 슬롯 낭비다. (실패 원인 코드가
            #   고쳐진 경우엔 base 갱신으로 상수가 이동해 자연히 재시도된다.)
            if sp.get("new_consts"):
                tried_specs.add((sp.get("feature"), sp.get("leaf_label"),
                                 tuple(float(x) for x in sp["new_consts"])))
    # QSP3 — 액션 우선순위: drop(대수술) 이 가능하면 먼저, 소진되면 tighten(조임).
    #   drop 후보 = 설계+홀드아웃 양쪽 손실 리프(사용자 규칙: 홀드아웃 동방향 필수).
    specs: List[Dict[str, Any]] = []
    mode = "tighten"
    h_csv = _holdout_label_csv(prev, holdout_config, base_code_name)
    h_abs = l_abs = None
    if h_csv:
        h_abs = str(REPO / h_csv) if not os.path.isabs(h_csv) else h_csv
        l_abs = str(REPO / str(label_csv)) if not os.path.isabs(str(label_csv)) else str(label_csv)
    tf = "min" if "min" in str(config_path).lower() else "tick"
    if "drop" in actions:
        tried_drops = {(m.get("spec") or {}).get("leaf_label") for rec in prev
                       for m in rec.get("candidates", [])
                       if (m.get("spec") or {}).get("action") == "drop_leaf"}
        if h_abs:
            specs = surgeon.propose_drops(l_abs, h_abs, base_code, top_k=n_cand,
                                          exclude_leaves=tried_drops, timeframe=tf)
            if specs:
                mode = "drop"
        else:
            print(f"[ROUND{round_no}] 홀드아웃 라벨 CSV 없음 — drop 건너뜀", flush=True)
    if not specs and "filter" in actions and h_abs:
        tried_filters = {((m.get("spec") or {}).get("feature"), (m.get("spec") or {}).get("leaf_label"))
                         for rec in prev for m in rec.get("candidates", [])
                         if (m.get("spec") or {}).get("action") == "add_filter"}
        specs = filtersmith.propose_filters(l_abs, h_abs, base_code, top_k=n_cand,
                                            exclude=tried_filters, timeframe=tf)
        if specs:
            mode = "filter"
    if not specs:
        specs = proposer.propose(ds, base_code, base_code_name, top_k=n_cand,
                                 exclude_axes=exclude_axes, exclude_specs=tried_specs)
    print(f"[ROUND{round_no}] base={base_code_name} 라벨={label_csv} 모드={mode}"
          f" 제안={len(specs)} (무효 축 제외 {len(set(exclude_axes))})", flush=True)

    # 후보 생성·게이트·등록.
    pairs: List[Dict[str, str]] = [{"label": f"r{round_no}_base", "buy": base_code_name, "sell": base_sell}]
    cand_meta: List[Dict[str, Any]] = []
    for i, spec in enumerate(specs, 1):
        if spec.get("action") == "drop_leaf":
            new_code, reason = surgeon.apply_drop(spec, base_code)
            if not new_code:
                cand_meta.append({"cand": i, "spec": spec, "status": "apply_fail", "reason": reason})
                continue
            ok, greason = surgeon.verify_drop(spec, base_code, new_code)
            if not ok:
                cand_meta.append({"cand": i, "spec": spec, "status": "gate_fail", "reason": greason})
                print(f"[ROUND{round_no}] C{i} DROP GATE FAIL — {greason}", flush=True)
                continue
        elif spec.get("action") == "add_filter":
            new_code, reason = filtersmith.apply_filter(spec, base_code)
            if not new_code:
                cand_meta.append({"cand": i, "spec": spec, "status": "apply_fail", "reason": reason})
                continue
            ok, greason = filtersmith.verify_filter(spec, base_code, new_code)
            if not ok:
                cand_meta.append({"cand": i, "spec": spec, "status": "gate_fail", "reason": greason})
                print(f"[ROUND{round_no}] C{i} FILTER GATE FAIL — {greason}", flush=True)
                continue
        else:
            new_code, reason = proposer.apply(spec, base_code)
            if not new_code:
                cand_meta.append({"cand": i, "spec": spec, "status": "apply_fail", "reason": reason})
                continue
            gres = gate.verify(base_code, new_code, [spec])
            if not gres.ok:
                cand_meta.append({"cand": i, "spec": spec, "status": "gate_fail", "reason": gres.reason})
                print(f"[ROUND{round_no}] C{i} GATE FAIL — {gres.reason}", flush=True)
                continue
        name = f"{tag.upper()}_R{round_no}C{i}_B"
        _register_buy(name, new_code)
        pairs.append({"label": f"r{round_no}_c{i}", "buy": name, "sell": base_sell})
        cand_meta.append({"cand": i, "spec": spec, "status": "registered",
                          "buy_name": name, "gate": "PASS"})
        print(f"[ROUND{round_no}] C{i} 등록 {name} — {spec['change']}", flush=True)

    # 공식 배치 실행(동기).
    pairs_path = ROUNDS_DIR / f"{tag}_r{round_no}_pairs.json"
    pairs_path.write_text(json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8")
    run_id = f"{time.strftime('%Y%m%d-%H%M')}_{tag}-r{round_no}"
    cmd = [PY, "-m", "ai_strategy_loop.scripts.claude_candidate_batch_eval",
           "--pairs-json", str(pairs_path), "--config-json", config_path, "--run-id", run_id]
    env = dict(os.environ, STOM_ALLOW_MINIMAL_SETTING="1", PYTHONUTF8="1")
    print(f"[ROUND{round_no}] 배치 {run_id} ({len(pairs)}쌍)…", flush=True)
    proc = subprocess.run(cmd, cwd=str(REPO), env=env, capture_output=True, text=True,
                          timeout=60 * 60)
    tail = "\n".join((proc.stdout or "").splitlines()[-12:])
    print(tail, flush=True)

    rows = _gen_rows(run_id)
    _objective(rows)
    # 위치 기반 결합 가드(감사 BUG-E): 행 수가 어긋나면 결과가 엉뚱한 전략에
    #   귀속되므로 즉시 중단(조용한 절단 금지).
    if len(rows) != len(pairs):
        raise SystemExit(f"세대 행 {len(rows)}개 ≠ pairs {len(pairs)}개 — run {run_id} 귀속 불가")
    by_label: Dict[str, Dict[str, Any]] = {}
    for r, p in zip(rows, pairs):
        # 재정렬 가드(재검증 5): 행이 자체 보유한 buy_name 이 pairs 와 다르면 오귀속.
        if r.get("buy_name") and str(r["buy_name"]) != str(p["buy"]):
            raise SystemExit(f"세대 행 buy_name={r['buy_name']} ≠ pair {p['buy']} — 순서 오염")
        by_label[p["label"]] = {**r, "pair_label": p["label"], "buy_name": p["buy"]}
    ok_rows = [v for v in by_label.values() if v.get("status") == "ok"]
    if not ok_rows:
        raise SystemExit(f"라운드 전멸 — run {run_id} 에 ok 세대 없음")
    best = max(ok_rows, key=lambda r: r["objective"])
    base_row = by_label.get(f"r{round_no}_base")

    # 교훈 합성: 베스트가 아닌 후보의 (feature, 리프) 축과 성적.
    lessons = []
    for v in ok_rows:
        if v is best:
            continue
        meta = next((m for m in cand_meta if m.get("buy_name") == v.get("buy_name")), None)
        if meta:
            lessons.append({
                "axis": meta["spec"].get("feature") or meta["spec"].get("action", "?"),
                "leaf": meta["spec"]["leaf_label"],
                "objective": v["objective"], "delta_vs_base": v["objective"] - (base_row or {}).get("objective", 0.0),
            })

    # QSP3 — 재유입 비용: drop 후보의 빼기 추정 vs 재백테 실측(추정은 순위용일 뿐).
    reentry: List[Dict[str, Any]] = []
    base_obj = float((base_row or {}).get("objective") or 0.0)
    for m in cand_meta:
        if (m.get("spec") or {}).get("est_delta_design") is None or m.get("status") != "registered":
            continue
        row = next((v for v in ok_rows if v.get("buy_name") == m.get("buy_name")), None)
        if row is None:
            continue
        measured = float(row["objective"]) - base_obj
        est = float(m["spec"].get("est_delta_design") or 0.0)
        reentry.append({"cand": m["cand"], "leaf": m["spec"]["leaf_label"],
                        "est_delta": est, "measured_delta": measured,
                        "reentry_cost": est - measured})
    if reentry:
        for r_ in reentry:
            print(f"[ROUND{round_no}] 재유입 {r_['leaf']}: 추정 {r_['est_delta']:+,.0f}"
                  f" → 실측 {r_['measured_delta']:+,.0f} (비용 {r_['reentry_cost']:,.0f})", flush=True)

    # QSP2 — 홀드아웃 평가: 이 라운드 베스트를 표본외 구간에서 1회 재평가(공식 배치).
    holdout_rec: Optional[Dict[str, Any]] = None
    if holdout_config:
        h_pairs = [{"label": f"r{round_no}_hold", "buy": best["buy_name"], "sell": base_sell}]
        h_pairs_path = ROUNDS_DIR / f"{tag}_r{round_no}_hold_pairs.json"
        h_pairs_path.write_text(json.dumps(h_pairs, ensure_ascii=False, indent=2), encoding="utf-8")
        h_run_id = f"{time.strftime('%Y%m%d-%H%M')}_{tag}-r{round_no}-hold"
        print(f"[ROUND{round_no}] 홀드아웃 배치 {h_run_id}…", flush=True)
        h_proc = subprocess.run(
            [PY, "-m", "ai_strategy_loop.scripts.claude_candidate_batch_eval",
             "--pairs-json", str(h_pairs_path), "--config-json", holdout_config,
             "--run-id", h_run_id],
            cwd=str(REPO), env=env, capture_output=True, text=True, timeout=60 * 60)
        print("\n".join((h_proc.stdout or "").splitlines()[-4:]), flush=True)
        h_rows = _gen_rows(h_run_id)
        h_ok = [r for r in h_rows if r.get("status") == "ok"]
        if h_ok:
            # 홀드아웃 objective 는 총손익으로 고정(재검증 잔존 지적): 1행 배치라
            #   any_gate 가 그 행 하나로 뒤집혀 score(~1e-3)↔profit(~-1e8) 스케일이
            #   라운드마다 섞이면 과최적 괴리 판정이 허위 발화/은폐된다.
            holdout_rec = {"run_id": h_run_id,
                           "objective": float(h_ok[0].get("profit", 0) or 0),
                           "trade_count": int(h_ok[0].get("trade_count", 0) or 0),
                           "profit": h_ok[0].get("profit"), "mdd": h_ok[0].get("mdd"),
                           "score": h_ok[0].get("score")}
        else:
            holdout_rec = {"run_id": h_run_id, "objective": None, "error": "no ok row"}

    history = [RoundStat(r["round"], r["best"]["objective"], r["best"]["trade_count"]) for r in prev]
    history.append(RoundStat(round_no, best["objective"], int(best.get("trade_count", 0) or 0)))
    seed_n = seed_trades if prev else int((base_row or {}).get("trade_count", seed_trades) or seed_trades)
    hold_hist = [((r.get("holdout") or {}).get("objective")) for r in prev]
    hold_hist.append((holdout_rec or {}).get("objective"))
    use_hold = any(h is not None for h in hold_hist)
    verdict = judge(history, seed_trades=seed_n,
                    holdout=hold_hist if use_hold else None)

    # objective 척도(regime) 기록 — 이전 라운드와 다르면 judge 이력이 이질 척도가
    #   되므로 경고(혼입 처리 자체는 백로그, 원장 참조).
    regime = "score" if any(bool(r.get("gate_passed")) for r in rows) else "profit"
    prev_regimes = {r.get("regime") for r in prev if r.get("regime")}
    if prev_regimes and regime not in prev_regimes:
        print(f"[ROUND{round_no}] ⚠ objective 척도 전환 {prev_regimes} → {regime}"
              f" — 라운드 간 개선율 해석 주의", flush=True)

    record = {
        "tag": tag, "round": round_no, "run_id": run_id, "regime": regime,
        "base": {"buy_name": base_code_name,
                 "objective": (base_row or {}).get("objective"),
                 "trade_count": (base_row or {}).get("trade_count"),
                 "csv_path": (base_row or {}).get("csv_path")},
        "candidates": cand_meta,
        "results": [{k: v.get(k) for k in ("pair_label", "buy_name", "objective", "score",
                                           "profit", "mdd", "trade_count", "gate_passed", "csv_path")}
                    for v in by_label.values()],
        "best": {k: best.get(k) for k in ("pair_label", "buy_name", "objective", "score",
                                          "profit", "mdd", "trade_count", "csv_path")},
        "lessons": lessons,
        "reentry": reentry,
        "judgment": {"state": verdict.state, "reason": verdict.reason,
                     "improvement_pct": verdict.improvement_pct},
        "holdout": holdout_rec,
        "seed_trades": seed_n,
    }
    out_path = ROUNDS_DIR / f"{tag}_r{round_no}.json"
    out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ROUND{round_no}] best={record['best']['buy_name']} obj={record['best']['objective']:,.0f} "
          f"judgment={verdict.state} — {verdict.reason}", flush=True)
    print(f"[ROUND{round_no}] 기록 {out_path}", flush=True)
    return record


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-buy", required=True)
    ap.add_argument("--base-sell", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--round", type=int, required=True)
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--holdout-config", default=None,
                    help="표본외 config JSON — 지정 시 라운드 베스트를 재평가해 판정에 반영")
    ap.add_argument("--actions", default="tighten",
                    help="액션 우선순위 CSV — 'drop,tighten'(QSP3 대수술) / 'tighten'(기존)")
    args = ap.parse_args()
    record = run_round(args.base_buy, args.base_sell, args.config, args.tag, args.round,
                       args.n, holdout_config=args.holdout_config, actions=args.actions)
    # 캠페인 드라이버(bat 루프)용 종료 코드: continue=0, 수렴/발산=2(루프 중단 신호).
    return 0 if record["judgment"]["state"] == "continue" else 2


if __name__ == "__main__":
    raise SystemExit(main())
