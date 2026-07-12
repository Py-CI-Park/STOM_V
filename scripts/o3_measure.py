"""O-3 돌파 온셋 × L3 출구 접목 측정 CLI — 봉인본 §6·§11·§14.

phase 분리:
  extract = 돌파 온셋 추출(발견창 437일 루프, 일별 체크포인트·재시작) →
            o3_breakout_onset_bank.parquet(v2+variant) + 변형별 census.
  gates   = G1 정의 스팟(변형별 100, 원시 행 독립) · G2 VI 필드 덤프(20) ·
            G3 순수/벡터 재현(스팟 일) · G4 서지 정확일치 L3 bit-identical.
  judge   = 변형×모집단(전체/서지-비중첩) 단독 EV 판정 + 서술.
  all     = extract → gates → judge.

산출물은 research_runs/alpha_restart_20260710/o3/ (parquet·parts·progress 는 git 제외).
전 창 본 측정은 분리형 러너(메인 세션)가 measure_gate 통과 후 기동 — 본 스크립트는
--days 스모크만 직접 실행 권장.

사용:
  STOM_ALLOW_MINIMAL_SETTING=1 python scripts/o3_measure.py --phase all --days 20220517 --spot-days 20220517 --smoke
원본 tick DB read-only(URI mode=ro). 엔진 백테 0회. git 커밋은 메인 세션 몫.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from alpha_lab.clause_lab.bank import champion_sell_text, day_list  # noqa: E402
from alpha_lab.o3lab import bank, detect, judge, run  # noqa: E402

_RUN_DIR = (_REPO / "docs/research/condition_research/research_runs"
            / "alpha_restart_20260710")
_DEFAULT_OUT = _RUN_DIR / "o3"
_DEFAULT_SURGE = _RUN_DIR / "stats_map" / "onset_l3_bank.parquet"
_DEFAULT_STRATEGY = _REPO / "_database" / "strategy.db"
_DISCOVERY = (20220323, 20231231)   # 발견창(append 계약 창 검사).


def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="O-3 돌파 온셋 × L3 접목 측정")
    ap.add_argument("--phase", choices=("extract", "gates", "judge", "all"), default="all")
    ap.add_argument("--db-dir", default=str(_REPO / "_database"))
    ap.add_argument("--strategy-db", default=str(_DEFAULT_STRATEGY))
    ap.add_argument("--surge-bank", default=str(_DEFAULT_SURGE))
    ap.add_argument("--out-dir", default=str(_DEFAULT_OUT))
    ap.add_argument("--days", nargs="*", default=None,
                    help="측정 일자(YYYYMMDD) 제한 — 스모크/부분. 미지정=발견창 전체")
    ap.add_argument("--spot-days", nargs="*", default=[],
                    help="재현 게이트(순수/벡터 L3)용 스팟 일자")
    ap.add_argument("--smoke", action="store_true",
                    help="스모크 관통 — 리포트에 스모크 딱지, 서지 기준선 일자 매칭, n_trials 미기입")
    return ap.parse_args(argv)


def _resolve_days(db_dir: str, days):
    full = day_list(db_dir)
    if not days:
        return full
    want = set(days)
    picked = [(d, p) for (d, p) in full if d in want]
    missing = want - {d for d, _ in picked}
    if missing:
        raise SystemExit(f"발견창에 없는 일자: {sorted(missing)}")
    return picked


def _pct(v) -> str:
    return "—" if v is None or (isinstance(v, float) and v != v) else f"{v * 100:.4f}%"


def _fmt(v, nd=4) -> str:
    return "—" if v is None else f"{v:+.{nd}f}"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _dump(path: Path, obj) -> None:
    _write(path, json.dumps(obj, ensure_ascii=False, indent=1, allow_nan=False) + "\n")


def _ensure_gitignore(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / ".gitignore").write_text(
        "parts/\n*.parquet\n*progress.txt\n", encoding="utf-8")


_CONTAM = (
    "본 지도·판정의 L3 는 챔피언 RR8_12 매도식(sell_sha 8ef01e0e…, 청산 레버·v4 계열, "
    "2024·2025 known)에 조건부다 — 다른 출구면 다른 지도다. 측정창(2022-2023)은 clean 이나 "
    "결과는 이 시드 계보 조건부 진단이며 성능·실전 수익 주장이 아니다. tick DB 09:00-09:30 한정 "
    "→ '시초 30분 내 돌파'로 한정(장중 일반화 금지). P300·DH·VI 어휘 딱지는 §3·§9 유지."
)


def render_report(result: dict, census: dict, gates: dict, *, smoke: bool) -> str:
    """판정 result + census + gates → 리포트(md, 결론 먼저·쉬운 설명 병기)."""
    j = result["judgment"]
    L: list = []
    A = L.append
    tag = " (스모크 — 판정 아님)" if smoke else ""
    A(f"# O-3 돌파 온셋 단독 ablation 판정 리포트{tag}")
    A("")
    A(f"> 사전등록: `{result['preregistration']}` · 엔진 백테 0회 · 원본 read-only · "
      "L3=RR8_12 출구 조건부")
    A("")
    A("## 0. 결론 먼저")
    A("")
    if smoke:
        A("> 스모크 관통 — 아래 수치는 파이프라인 검증용이며 판정이 아니다(발견창 1일, "
          "서지 기준선 동일-일 매칭, 일자블록 부트스트랩 축소, n_trials 미기입).")
        A("")
    verdict = (f"**양EV(strong) {j['n_strong']}건**: {j['strong_units']}" if j["n_strong"]
               else ("**kill-1 — 전 자격 단위 CI 상한<0(돌파도 시초 음의 지형 못 뒤집음)**"
                     if j["kill1_all_ci_high_negative"]
                     else "**양EV 증거 0**(strong 0 — O-1G·서지에 이은 부정 지도)"))
    A(f"{verdict}. 자격 (변형×모집단) {j['fdr_denominator']}개(FDR 분모) 중 "
      f"strong {j['n_strong']}·약신호 {j['n_weak_signal']}·변형 kill {len(j['variant_kill_units'])}. "
      "판정 기준 = mean_net ≥ +0.10%p ∧ 일자블록 CI 하한>0 ∧ BH-FDR(q=0.10) ∧ 연도 동부호.")
    A("")
    A("## 1. 변형별 온셋 census (자격 = 라벨 n≥2,000 ∧ 연도 각 ≥400)")
    A("")
    A("| 변형 | 온셋 | 라벨 | 2022 | 2023 |")
    A("|---|---|---|---|---|")
    for v in detect.VARIANTS:
        c = census.get(v, {})
        A(f"| {v} | {c.get('n_onsets', 0):,} | {c.get('n_labeled', 0):,} | "
          f"{c.get('n_2022', 0):,} | {c.get('n_2023', 0):,} |")
    A("")
    A("## 2. 판정표 (변형×모집단 — 단독 절대 EV)")
    A("")
    A("| 단위 | n(라벨) | mean(%p) | 일자블록 CI | 연도(22/23) | 양측p | FDR | MDE(%p) | 하한 | 분류 |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for name in j["units"]:
        r = j["per_unit"][name]
        ym = r["year_mean"]
        yr = f"{_sgn(ym[2022]['sign'])}{_sgn(ym[2023]['sign'])}"
        A(f"| {name} | {r['n_labeled']:,} | {_fmt(r['mean_net_pp'])} | "
          f"[{_fmt(r['ci_low_pp'])}, {_fmt(r['ci_high_pp'])}] | {yr} | "
          f"{r['p_two_sided']:.4f} | {'생존' if r['fdr_survive'] else '—'} | "
          f"{_fmt(r['mde_pp'])} | {'통과' if r['floor_pass'] else '미달'} | {r['classification']} |")
    A("")
    ov = result["surge_overlap"]
    A(f"- **서지 겹침률(±30 pooled)**: {_pct(ov.get('pooled_rate'))} "
      "(서지-비중첩 모집단 = 겹치지 않는 온셋 — 돌파 고유 몫)")
    A(f"- **sanity anchor(§10-5)**: 전 자격 |mean − 서지풀 −1.01%p|<0.02 = "
      f"{j['sanity_anchor_tripped']}"
      + ("→ **파이프라인 결함 의심, 수동 스팟 필수**" if j["sanity_anchor_tripped"] else "(미발동)"))
    A("")
    if gates:
        A("## 3. 게이트 (G1 정의·G2 VI·G3 재현·G4 은행 앵커)")
        A("")
        g1, g3, g4 = gates.get("g1", {}), gates.get("g3", {}), gates.get("g4", {})
        A(f"- **G1 정의 스팟**: gate_pass={g1.get('gate_pass')} — "
          + " · ".join(f"{v} {(_pct(g1.get('per_variant', {}).get(v, {}).get('match_rate')))}"
                       for v in detect.VARIANTS))
        A(f"- **G3 재현(순수/벡터)**: reproduction_pass={g3.get('reproduction_pass')}")
        A(f"- **G4 은행 앵커**: 정확 겹침 {g4.get('n_exact_overlap', 0):,}건 "
          f"불일치 {g4.get('n_mismatch', 0)} (max_err {g4.get('max_abs_err', 0.0):.2e}) → "
          f"gate_pass={g4.get('gate_pass')}")
        A("")
    A(f"> **딱지(강제 인쇄, §9)**: {_CONTAM}")
    A("")
    A("*엔진 백테 0회 · 원본 read-only · git 커밋 없음 · 2024/2025 미접촉. "
      "산출: o3_breakout_onset_bank.parquet(git 제외, onset_l3_bank 원본 불변).*")
    return "\n".join(L) + "\n"


def _sgn(s) -> str:
    return {1: "+", -1: "−", 0: "·"}.get(s, "·")


def _bank_path(out_dir: Path) -> Path:
    return out_dir / "o3_breakout_onset_bank.parquet"


def run_phase_extract(args, sell_text: str) -> dict:
    out_dir = Path(args.out_dir)
    _ensure_gitignore(out_dir)
    parts_dir = out_dir / "parts"
    days = _resolve_days(args.db_dir, args.days)
    run.run_extract(args.db_dir, out_dir, parts_dir, sell_text,
                    days=days, spot_days=args.spot_days)
    cons = run.consolidate(parts_dir, _bank_path(out_dir), window=_DISCOVERY)
    _dump(out_dir / "o3_extract_summary.json",
          {"days_measured": len(days), "consolidate": cons})
    pv = cons["per_variant"]
    print(f"[EXTRACT] days={len(days)} onsets={cons['n_onsets']} labeled={cons['n_labeled']} "
          + " ".join(f"{v}={pv[v]['n_onsets']}" for v in detect.VARIANTS)
          + f" written={cons['bank_write']['written']}")
    return cons


def run_phase_gates(args, sell_text: str) -> dict:
    out_dir = Path(args.out_dir)
    parts_dir = out_dir / "parts"
    df = run.load_bank(_bank_path(out_dir))
    gates = {
        "g1": run.gate_g1_definition(df, args.db_dir),
        "g2": run.gate_g2_vi_dump(df, args.db_dir),
        "g3": (run.spot_reproduction_check(parts_dir, args.spot_days)
               if args.spot_days else {"spot_days": [], "reproduction_pass": None}),
        "g4": run.gate_g4_bank_anchor(df, args.surge_bank),
    }
    _dump(out_dir / "o3_gates_summary.json", gates)
    print(f"[GATES] G1={gates['g1']['gate_pass']} "
          f"G3={gates['g3'].get('reproduction_pass')} "
          f"G4={gates['g4']['gate_pass']}(n={gates['g4']['n_exact_overlap']})")
    return gates


def run_phase_judge(args, gates: dict) -> dict:
    out_dir = Path(args.out_dir)
    result = run.run_judge(_bank_path(out_dir), args.surge_bank,
                           match_surge_days=args.smoke)
    _dump(out_dir / "o3_breakout_summary.json", result)
    extract_json = out_dir / "o3_extract_summary.json"
    census = (json.loads(extract_json.read_text(encoding="utf-8"))["consolidate"]["per_variant"]
              if extract_json.exists() else {})
    _write(out_dir / "o3_breakout_report.md",
           render_report(result, census, gates, smoke=args.smoke))
    j = result["judgment"]
    print(f"[JUDGE] denom={j['fdr_denominator']} strong={j['n_strong']} "
          f"weak={j['n_weak_signal']} kill={len(j['variant_kill_units'])} "
          f"overlap±30={_pct(result['surge_overlap'].get('pooled_rate'))}")
    return result


def main(argv=None) -> int:
    args = parse_args(argv)
    sell_text = champion_sell_text(args.strategy_db)   # sha 봉인 검증(8ef01e0e).
    gates: dict = {}
    if args.phase in ("extract", "all"):
        run_phase_extract(args, sell_text)
    if args.phase in ("gates", "all"):
        gates = run_phase_gates(args, sell_text)
    if args.phase in ("judge", "all"):
        run_phase_judge(args, gates)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
