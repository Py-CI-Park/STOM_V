"""B-트랙 2단계(타 전략 가지 확장) 측정 CLI — 봉인본 §5·§6·§11·§14.

phase:
  select = §14-F1 기계 선정(strategy.db read-only) → 선정·sha·가지·매핑·신규비트 정의를 게이트 리포트로
           영속화(**L3 관측 전** — 확인③). 값/L3 무관측.
  bits   = 확정 신규 절만 발견창 온셋 위 벡터 술어(일자 체크포인트) → btrack_ext_bits.parquet.
  gates  = 무결성 지문(은행·d1 비트) + ext 비트 키 정합 + 신규비트 패리티(벡터 vs 스칼라 100%).
  judge  = 가지/합동 anchor mean L3·등급·FDR·3분법·층화 mean·엔진 갭 → summary + report.
  all    = select → bits → gates → judge.

산출물 research_runs/alpha_restart_20260710/b_track_ext/(parquet·parts·progress·run_ctl·log git 제외).
**전 창 bits·judge 는 메인**(measure_gate 후 분리 러너). --phase select 는 read-only 스모크 허용.
git 커밋은 메인 몫. STOM_ALLOW_MINIMAL_SETTING=1.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from alpha_lab.btrack import ext_bits, ext_judge, ext_select  # noqa: E402
from alpha_lab.btrack.branches import BRANCH_902_NUMS, BRANCH_905_NUMS  # noqa: E402
from alpha_lab.clause_lab.bank import day_list  # noqa: E402
from alpha_lab.clause_lab.pair_gate import EXPECTED_ROWS, check_integrity  # noqa: E402

_RUN_DIR = (_REPO / "docs/research/condition_research/research_runs" / "alpha_restart_20260710")
_DEFAULT_OUT = _RUN_DIR / "b_track_ext"
_DEFAULT_BANK = _RUN_DIR / "stats_map" / "onset_l3_bank.parquet"
_DEFAULT_D1_BITS = _RUN_DIR / "stats_map" / "d1_onset_clause_bits.parquet"
_DEFAULT_STRATEGY = _REPO / "_database" / "strategy.db"
_DEFAULT_LIVE = _RUN_DIR / "d5r_b1_live"
_KEYS = ["code", "day", "off", "t0"]
_D1_BITS = [f"bit_{n}" for n in range(1, 40)]

_TAGS = [
    "① 출구 조건부: L3 는 RR8_12 매도식(sell_sha 8ef01e0e…)에 조건부 — 각 전략 자기 출구 아님.",
    "② 각 전략 계보·known 선정 입력: 가지 절·임계는 각 전략(2024/2025 튜닝 포함) 산물. 측정창(2022-2023) "
    "clean 이나 계보 조건부 진단·성능 주장 아님.",
    "③ AND 프록시 하한: 가지 AND 발화는 실발화 과소집합(엔진 상태변수·1일1회·순위·서지밖 미포함).",
    "④ 이질 혼합: 합동 anchor 는 전략 혼합 — 층화(가문/비가문·전략별) 병기 없이 단일 인용 금지.",
]


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="B-트랙 2단계 다전략 가지 확장 측정")
    ap.add_argument("--phase", choices=("select", "bits", "gates", "judge", "all"), default="all")
    ap.add_argument("--db-dir", default=str(_REPO / "_database"))
    ap.add_argument("--strategy-db", default=str(_DEFAULT_STRATEGY))
    ap.add_argument("--bank", default=str(_DEFAULT_BANK))
    ap.add_argument("--d1-bits", default=str(_DEFAULT_D1_BITS))
    ap.add_argument("--live-dir", default=str(_DEFAULT_LIVE))
    ap.add_argument("--out-dir", default=str(_DEFAULT_OUT))
    ap.add_argument("--days", nargs="*", default=None, help="스모크 일자(YYYYMMDD)")
    ap.add_argument("--smoke", action="store_true")
    return ap.parse_args(argv)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _dump(path: Path, obj) -> None:
    _write(path, json.dumps(obj, ensure_ascii=False, indent=1, allow_nan=False) + "\n")


def _ensure_gitignore(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / ".gitignore").write_text(
        "parts/\n*.parquet\n*progress.txt\nrun_ctl/\n*.log\n", encoding="utf-8")


def _ext_bits_path(out_dir: Path) -> Path:
    return out_dir / "stats_map_ext" / "btrack_ext_bits.parquet"


def _fmt(v, nd=4) -> str:
    return "—" if v is None else f"{v:+.{nd}f}"


def _selection_report(sel: ext_select.SelectionResult) -> dict:
    """선정 결과 → 게이트 리포트 dict(가지 bit_cols·신규비트 정의 포함, L3 관측 전)."""
    id_by_key = sel.new_bit_ids
    new_bit_defs = {}
    for (canon, negated), bid in id_by_key.items():
        from alpha_lab.btrack.ext_parse import compile_clause
        ci = compile_clause(canon, negated=negated)
        new_bit_defs[bid] = {"canon": canon, "negated": bool(negated), "symbols": list(ci.symbols)}
    branches = []
    for name in sel.selected:
        info = sel.strategies[name]
        for b in info.branches:
            if not b.measurable:
                continue
            cols = [f"bit_{n}" for n in b.bit_nums] + [id_by_key[k] for k in b.new_keys]
            branches.append({"id": f"{name}#{b.index}", "strategy": name, "index": b.index,
                             "bit_cols": cols, "is_family": info.is_family, "n_atoms": b.n_atoms})
    return {
        "kind": "b_ext_selection_gate", "note": "L3 관측 전 영속(확인③ 정본)",
        "selected": sel.selected, "family_expand": sel.family_expand, "nonfamily": sel.nonfamily,
        "n_selected": len(sel.selected), "n_new_bits": sel.n_new_bits,
        "n_branches_measurable": sel.n_branches_measurable, "caps": sel.caps,
        "champion_branches": {"902": list(BRANCH_902_NUMS), "905": list(BRANCH_905_NUMS)},
        "strategies": {n: {"sha256": sel.strategies[n].sha256,
                           "is_family": sel.strategies[n].is_family,
                           "reuse_ratio": round(sel.strategies[n].reuse_ratio, 4),
                           "n_branches": sel.strategies[n].n_branches,
                           "n_measurable": sel.strategies[n].n_measurable}
                       for n in sel.selected},
        "new_bit_defs": new_bit_defs, "branches": branches, "excluded": sel.excluded,
    }


def run_select(args) -> dict:
    out_dir = Path(args.out_dir)
    _ensure_gitignore(out_dir)
    sel = ext_select.select(args.strategy_db)
    report = _selection_report(sel)
    _dump(out_dir / "b_ext_selection_gate.json", report)
    print(f"[SELECT] 선정 {report['n_selected']}종(가문확장 {len(sel.family_expand)}·비가문 {len(sel.nonfamily)}) "
          f"· 측정 가지 {report['n_branches_measurable']} · 신규 비트 {report['n_new_bits']}/{sel.caps['new_bit_cap']}")
    return report


def _new_bit_defs(report: dict) -> dict:
    return {bid: (d["canon"], d["negated"]) for bid, d in report["new_bit_defs"].items()}


def run_bits(args, report: dict) -> dict:
    out_dir = Path(args.out_dir)
    parts_dir = out_dir / "parts"
    defs = _new_bit_defs(report)
    preds = ext_bits.compile_ext_predicates(defs)
    days = None
    if args.days:
        full = day_list(args.db_dir)
        days = [(d, p) for (d, p) in full if d in set(args.days)]
    ext_bits.run_bits(args.db_dir, out_dir, parts_dir, preds, days=days)
    cons = None
    if not args.days:
        cons = ext_bits.consolidate(parts_dir, _ext_bits_path(out_dir), list(defs.keys()))
        _dump(out_dir / "b_ext_bits_summary.json", {"consolidate": cons})
    print(f"[BITS] n_ext={len(defs)} consolidated={cons is not None}"
          + (f" n_onsets={cons['n_onsets']}" if cons else " (부분 — consolidate 생략)"))
    return {"consolidate": cons}


def run_gates(args, report: dict) -> dict:
    out_dir = Path(args.out_dir)
    ext_path = _ext_bits_path(out_dir)
    integ = check_integrity(args.bank, args.d1_bits)
    defs = _new_bit_defs(report)
    key_ok = None
    if ext_path.exists():
        e = pd.read_parquet(ext_path, columns=_KEYS)
        key_ok = bool(int(e.shape[0]) == EXPECTED_ROWS and int(e.duplicated(subset=_KEYS).sum()) == 0)
    days = [d for (d, _) in day_list(args.db_dir)] if not args.days else args.days
    parity = ext_judge.ext_parity_gate(args.db_dir, days[:2] if args.days else days, defs)
    gate_pass = bool(integ.get("all_match") and (key_ok in (True, None)) and parity["pass"])
    gates = {"kind": "b_ext_gates", "integrity": integ, "ext_key_ok": key_ok,
             "new_bit_parity": parity, "gate_pass": gate_pass}
    _dump(out_dir / "b_ext_gates_summary.json", gates)
    print(f"[GATES] integrity={integ.get('all_match')} ext_key={key_ok} "
          f"parity={parity['pass']}({parity['agreement_pct']:.1f}%) → gate_pass={gate_pass}")
    return gates


def _load_labeled(bank_path, d1_bits_path, ext_path, ext_cols):
    bank = pd.read_parquet(bank_path, columns=_KEYS + ["year", "l3_net", "l3_labeled"])
    d1 = pd.read_parquet(d1_bits_path, columns=_KEYS + _D1_BITS)
    ext = pd.read_parquet(ext_path, columns=_KEYS + list(ext_cols))
    base = bank.merge(d1, on=_KEYS, how="inner").merge(ext, on=_KEYS, how="inner")
    if base.shape[0] != bank.shape[0]:
        raise SystemExit(f"은행/비트 키 병합 손실({bank.shape[0]}→{base.shape[0]}, kill)")
    lab = base["l3_labeled"].to_numpy().astype(bool)
    net_pp = base["l3_net"].to_numpy(dtype=np.float64)[lab] * 100.0
    days = base["day"].to_numpy(dtype=np.int64)[lab]
    years = base["year"].to_numpy(dtype=np.int64)[lab]
    cols = _D1_BITS + list(ext_cols)
    bit_arrays = {c: base[c].to_numpy().astype(bool)[lab] for c in cols}
    return net_pp, days, years, bit_arrays


def run_judge(args, report: dict) -> dict:
    out_dir = Path(args.out_dir)
    ext_cols = list(report["new_bit_defs"].keys())
    net_pp, days, years, bit_arrays = _load_labeled(
        args.bank, args.d1_bits, _ext_bits_path(out_dir), ext_cols)
    engine_ref = judge_engine_ref(args.live_dir)
    judgment = ext_judge.judge_ext(report["branches"], bit_arrays, net_pp, days, years,
                                   engine_ref=engine_ref)
    result = {
        "kind": "b_ext_branch_judgment",
        "preregistration": "2026-07-14_b_track_ext_multistrategy_branches_preregistration.md (1e179bb6)",
        "n_labeled": int(net_pp.size),
        "pool_mean_pp_measured": round(float(net_pp.mean()), 6) if net_pp.size else None,
        "selection": {k: report[k] for k in ("selected", "family_expand", "nonfamily",
                                             "n_new_bits", "n_branches_measurable")},
        "engine_reference": engine_ref, "judgment": judgment, "tags": _TAGS, "smoke": bool(args.smoke),
    }
    _dump(out_dir / "b_ext_summary.json", result)
    _write(out_dir / "b_ext_report.md", render_report(result))
    j = judgment
    print(f"[JUDGE] anchor n={j['anchor']['n_fire']} verdict={j['anchor_frame_verdict']} "
          f"· 정식 양(+) {j['n_positive_formal']} 관찰 양(+) {j['n_positive_observational']} "
          f"· B-3 좌표 {len(j['b3_coordinates'])} · sanity={j['sanity_anchor_tripped']}")
    return result


def judge_engine_ref(live_dir):
    from alpha_lab.btrack.judge_b import load_engine_reference
    return load_engine_reference(live_dir)


def render_report(result: dict) -> str:
    j = result["judgment"]
    a = j["anchor"]
    L: list = []
    A = L.append
    tag = " (스모크 — 판정 아님)" if result["smoke"] else ""
    A(f"# B-트랙 2단계 다전략 가지 확장 판정 리포트{tag}")
    A("")
    A(f"> 사전등록: `{result['preregistration']}` · 엔진 0회 · L3=RR8_12 출구 조건부 · 신규 비트 "
      f"{result['selection']['n_new_bits']}")
    A("")
    A("## 0. 결론 먼저")
    A("")
    vtext = {"reproduce": "**(a) 재현 확정** — 깊은 양(+) 모집단 존재. B-3 OR 조립 착수 근거.",
             "frame_gap": "**(b) 프레임 갭 확정** — 표본 확장에도 anchor CI 상한<0. 엔진 프레임 피벗.",
             "undetermined": "**(c) 여전히 미결** — anchor CI 0걸침. 오프라인 축 최종 종결(층화 하위 (a) 후보만 유보)."}
    A(f"{vtext[j['anchor_frame_verdict']]} 합동 anchor n={a['n_fire']:,}(등급 {a['tier']}) "
      f"mean {_fmt(a['mean_net_pp'])}%p CI[{_fmt(a['ci_low_pp'])},{_fmt(a['ci_high_pp'])}] "
      f"(챔피언 단독 114 대비 확장). 정식 양(+) {j['n_positive_formal']}·관찰 양(+) {j['n_positive_observational']} "
      f"→ B-3 좌표 {len(j['b3_coordinates'])}.")
    A("")
    A(f"- 서지 풀 평균(측정): {_fmt(result['pool_mean_pp_measured'])}%p · sanity: {j['sanity_anchor_tripped']}")
    A("")
    A("## 1. 층화 mean (§7 — 이질 혼합 정직)")
    A("")
    st = j["stratified_mean"]
    A("| 층 | n | mean(%p) |")
    A("|---|---|---|")
    A(f"| 가문 | {st['family']['n']:,} | {_fmt(st['family']['mean_pp'])} |")
    A(f"| 비가문 | {st['nonfamily']['n']:,} | {_fmt(st['nonfamily']['mean_pp'])} |")
    for s, v in list(st["per_strategy"].items())[:20]:
        A(f"| {s} | {v['n']:,} | {_fmt(v['mean_pp'])} |")
    A("")
    A("> '합동 양(+)'은 이 집합 어딘가에 깊은 양(+) 모집단이 있다는 존재 증명이지 각 전략 보증이 아니다.")
    A("")
    A("## 2. 엔진 갭 (오프라인 anchor vs B1 엔진)")
    A("")
    A("| 연도 | 엔진 거래 | 엔진 avg(%) | 오프라인 anchor mean(%p) | 갭 |")
    A("|---|---|---|---|---|")
    for yr in (2022, 2023):
        g = j["engine_gap"].get(yr, {}) if j["engine_gap"] else {}
        A(f"| {yr} | {g.get('engine_trades','—')} | {_fmt(g.get('engine_avg_pct'),2)} | "
          f"{_fmt(g.get('offline_anchor_mean_pp'))} | {_fmt(g.get('gap_pp'))} |")
    A("")
    A(f"## 3. B-3 좌표 (정식·관찰 양(+) 가지 — {len(j['b3_coordinates'])})")
    A("")
    A("`" + ", ".join(j["b3_coordinates"]) + "`" if j["b3_coordinates"] else "(없음)")
    A("")
    A("## 4. 딱지 (강제 인쇄 — §9)")
    A("")
    for t in result["tags"]:
        A(f"- {t}")
    A("")
    A("*엔진 0회 · 원본 read-only · git 커밋 없음 · 2024/2025 미접촉 · 최종 심판=U-4 감독형 소액 실전.*")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.out_dir)
    report = None

    def _load_report():
        p = out_dir / "b_ext_selection_gate.json"
        if not p.exists():
            raise SystemExit("선정 게이트 없음 — 먼저 --phase select 실행")
        return json.loads(p.read_text(encoding="utf-8"))

    if args.phase in ("select", "all"):
        report = run_select(args)
    if args.phase in ("bits", "all"):
        report = report or _load_report()
        run_bits(args, report)
    if args.phase in ("gates", "all"):
        report = report or _load_report()
        run_gates(args, report)
    if args.phase in ("judge", "all"):
        report = report or _load_report()
        run_judge(args, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
