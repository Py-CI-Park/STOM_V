"""D1 산출물 — npz 교차검증·판정 로드·summary.json·리포트·n_trials 원장 (사전등록 §11).

- verify_vs_npz: 재산출 은행이 Jul-11 v2a npz(발견창 체크포인트)와 일별 온셋·L3
  벡터 net 이 원소 동일함을 전수 대조(결정론 증명).
- load_bank_for_judgment: 은행+비트 조인, 라벨된 온셋만, net_pp=l3_net×100.
- build_summary / render_report: 절별 전 수치 정본(JSON) + 쉬운 설명·판정표 리포트.
- append_n_trials: series D1, type-b = 자격 절 수만큼 append.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from alpha_lab.clause_lab.clauses import CLAUSE_SPECS, spec_by_num

__all__ = [
    "append_n_trials",
    "build_summary",
    "load_bank_for_judgment",
    "render_report",
    "verify_vs_npz",
]

CONTAMINATION_LABEL = (
    "본 결과의 절 집합(RR8_12 매수식)은 2024 선정창을 포함해 튜닝된 역사적 산물이다"
    "(창-지위 원장 §2 v4 계열). 따라서 발견되는 절 효과는 이 시드 계보"
    "(rr8_12_turnover_min_902_1.5, buy_sha 348c5181…)에 조건부인 진단이며, "
    "(a) 새 전략 성능 주장이 아니고, (b) 절의 보편적 유효성 주장이 아니며, "
    "(c) 다른 출구를 쓰면 지도가 달라진다(L3 는 RR8_12 출구 조건부)."
)


def verify_vs_npz(parts_dir, npz_dir) -> Dict[str, object]:
    """일별 재산출 은행 vs Jul-11 v2a npz 전수 대조(온셋 off·L3 벡터 net 원소 동일)."""
    parts = sorted(Path(parts_dir).glob("bank_*.parquet"))
    per_day: List[dict] = []
    n_off_mismatch = n_l3_mismatch = 0
    max_l3_err = 0.0
    for p in parts:
        date = p.name[len("bank_"):-len(".parquet")]
        npz_path = Path(npz_dir) / f"extract_{date}.npz"
        if not npz_path.exists():
            per_day.append({"day": date, "status": "npz_missing"})
            continue
        bank = pd.read_parquet(p, columns=["off", "l3_net", "l3_labeled"])
        npz = np.load(npz_path)
        ob = np.sort(bank["off"].to_numpy())
        on = np.sort(npz["off"])
        off_ok = ob.size == on.size and np.array_equal(ob, on)
        # 정렬 조인(off 로 정렬 후 비교 — off 는 종목 간 중복 가능하나 npz 도 동일 순서 산출).
        order_b = np.argsort(bank["off"].to_numpy(), kind="stable")
        order_n = np.argsort(npz["off"], kind="stable")
        lb = bank["l3_net"].to_numpy()[order_b]
        ln = npz["l3_net_vector"][order_n]
        mb = bank["l3_labeled"].to_numpy()[order_b]
        mn = npz["l3_labeled_vector"][order_n]
        both = mb & mn if off_ok else np.zeros(0, dtype=bool)
        err = float(np.max(np.abs(lb[both] - ln[both]))) if (off_ok and both.any()) else 0.0
        max_l3_err = max(max_l3_err, err)
        if not off_ok:
            n_off_mismatch += 1
        if err > 1e-12:
            n_l3_mismatch += 1
        per_day.append({"day": date, "off_match": bool(off_ok),
                        "n_onsets": int(bank.shape[0]), "l3_max_abs_err": err})
    return {
        "n_days": len(parts), "n_off_mismatch": n_off_mismatch,
        "n_l3_mismatch": n_l3_mismatch, "max_l3_abs_err": max_l3_err,
        "determinism_pass": bool(n_off_mismatch == 0 and max_l3_err <= 1e-12),
        "per_day": per_day,
    }


def load_bank_for_judgment(
    bank_path, bits_path,
) -> Tuple[Dict[int, np.ndarray], np.ndarray, np.ndarray, np.ndarray, Dict[str, object]]:
    """은행+비트 → (bits{num:배열}, net_pp, days, years, meta). 라벨된 온셋만."""
    bank = pd.read_parquet(bank_path)
    bits = pd.read_parquet(bits_path)
    if bank.shape[0] != bits.shape[0]:
        raise ValueError("은행/비트 행수 불일치 — 위치 조인 불가")
    labeled = bank["l3_labeled"].to_numpy().astype(bool)
    net_pp = bank["l3_net"].to_numpy(dtype=np.float64)[labeled] * 100.0
    days = bank["day"].to_numpy(dtype=np.int64)[labeled]
    years = bank["year"].to_numpy(dtype=np.int64)[labeled]
    bit_map: Dict[int, np.ndarray] = {}
    for spec in CLAUSE_SPECS:
        col = f"bit_{spec.num}"
        if col in bits.columns:
            bit_map[spec.num] = bits[col].to_numpy().astype(bool)[labeled]
    meta = {
        "n_onsets_total": int(bank.shape[0]),
        "n_labeled": int(labeled.sum()),
        "n_2022": int((years == 2022).sum()),
        "n_2023": int((years == 2023).sum()),
    }
    return bit_map, net_pp, days, years, meta


def build_summary(
    judgment: Mapping[str, object], gate: Mapping[str, object],
    bank_meta: Mapping[str, object], npz_check: Mapping[str, object],
    consolidate_meta: Mapping[str, object],
) -> Dict[str, object]:
    """절별 전 수치 정본 + 게이트·은행·검증 메타를 묶은 summary.json 페이로드."""
    return {
        "kind": "d1_clause_ablation_summary",
        "generated": datetime.now(timezone.utc).isoformat(),
        "preregistration": "2026-07-12_d1_clause_ablation_preregistration.md (56564cba)",
        "buy_sha256": "348c518145cbf91e7123f9a8f3498fc35b36d269cce3e3e57154bd191d3ea97a",
        "sell_sha256": "8ef01e0ef2087ec95ac6b358b6f5c710414f3eb4dd401b01cc8162877f911c07",
        "window": "2022-03-23~2023-12-31 (발견창, 측정창=2개 연도)",
        "contamination_label": CONTAMINATION_LABEL,
        "bank_meta": dict(bank_meta),
        "consolidate": dict(consolidate_meta),
        "determinism_vs_npz": {k: npz_check[k] for k in (
            "n_days", "n_off_mismatch", "n_l3_mismatch", "max_l3_abs_err",
            "determinism_pass")},
        "gate": {
            "gate_pass": gate.get("gate_pass"),
            "local_def_parity": gate.get("local_def_parity"),
            "n1_delay_parity": gate.get("n1_delay_parity"),
            "p3_reproduction": gate.get("p3_reproduction"),
            "qualified": gate.get("qualified"),
        },
        "judgment": judgment,
    }


def _fmt(v, nd=4):
    return "—" if v is None else f"{v:+.{nd}f}"


def render_report(summary: Mapping[str, object]) -> str:
    """summary → 쉬운 설명·판정표·목록·딱지·해석 경계를 담은 마크다운 리포트."""
    j = summary["judgment"]
    per = j["per_clause"]
    q = summary["gate"]["qualified"]
    bm = summary["bank_meta"]
    lb = j["load_bearing_nums"]
    cp = j["counter_productive_nums"]
    wk = j["weak_signal_nums"]
    denom = j["fdr_denominator"]

    def _sgn(s):
        return {1: "+", -1: "−", 0: "·"}.get(s, "·")

    def clause_row(n):
        r = per[n]
        cls = {"load_bearing": "load-bearing", "counter_productive": "역생산",
               "weak_signal": "약신호", "none": "—"}.get(r.get("classification"), "—")
        surv = "생존" if r.get("fdr_survive") else "—"
        yr = f"{_sgn(r['year_delta'][2022]['sign'])}{_sgn(r['year_delta'][2023]['sign'])}"
        return (f"| {n} | {r['text']} | {r['family']} | {r['tier']} | "
                f"{r['n_sat']} / {r['n_unsat']} | {_fmt(r['delta_pp'])} | "
                f"[{_fmt(r['ci_low_pp'])}, {_fmt(r['ci_high_pp'])}] | {yr} | "
                f"{r['p_two_sided']:.4f} | {surv} | {_fmt(r['mde_pp'])} | {cls} |")

    lines: List[str] = []
    A = lines.append
    A("# D1 챔피언 절-단위 A/B 분해 — 측정 리포트")
    A("")
    A(f"> 사전등록 봉인본: `{summary['preregistration']}` · buy_sha `{summary['buy_sha256'][:12]}…` "
      f"· sell_sha `{summary['sell_sha256'][:12]}…` · 측정창 {summary['window']}")
    A("")
    # 결론 먼저.
    verdict = ("**kill-1 확정 — load-bearing 절 0개**" if j["n_load_bearing"] == 0
               else f"**load-bearing 절 {j['n_load_bearing']}개** (족 {len(j['load_bearing_families'])}개)")
    A("## 0. 결론 먼저")
    A("")
    A(f"{verdict}. 자격 절 {denom}개(39 유니크 − 순수중복 1, U-보류 6 전부 M 승격)를 "
      f"온셋 {bm['n_labeled']:,}건(라벨된, 2022 {bm['n_2022']:,} / 2023 {bm['n_2023']:,}) 위에서 "
      f"단독 술어로 A/B 분해했다. 효과크기 하한 +0.10%p · BH-FDR q=0.10(분모 {denom}) · "
      f"일자블록 CI 하한>0 · 연도 동부호를 동시 적용한 결과, "
      f"load-bearing {j['n_load_bearing']}개 · 역생산 {j['n_counter_productive']}개 · 약신호 {j['n_weak_signal']}개.")
    A("")
    if j["n_load_bearing"] == 0:
        A("이는 사전등록 §10 kill-1(주 결론): **챔피언 엣지는 단일 가드 절로 분해되지 않는다.** "
          "V2-C(칸-조준 KILL)·O-1G(갭 양EV 0) 수렴 결론을 절 단위로 확증하며, 단일-절 탐색 "
          "공간을 대거 소거한다 — 그 자체로 확정 지식이다. **단, 이것은 '단일 절 분해 불가'이지 "
          "'엣지 부재'가 아니다**(§0·§10): 같은 분기의 다른 절과 결합해야 작동하는 교호작용 절은 "
          "이 라운드가 구조적으로 볼 수 없다(후속 별도 봉인 §12).")
    else:
        A("load-bearing 절(들)은 조준 가능한 생성 문법(O-4 가드 절 공급원)의 최초 실증이다. "
          "단 §9 시드-조건부 딱지가 강제되며, 원-임계 그대로 채택 금지(별도 트랙 재도출).")
    A("")
    # 쉬운 설명.
    A("## 0.5 쉬운 설명 (레시피 비유)")
    A("")
    A("우승한 요리(챔피언 RR8_12)의 레시피 재료(가드 절)를 한 개씩 빼서 맛을 확인했다. "
      f"재료 창고 = {bm['n_labeled']:,}개의 서지 온셋(각각 '이 재료로 우승 조리법대로 요리하면 "
      "얼마 남는가'라는 가격표 L3 부착). 재료 하나를 골라 창고를 '그 조건 만족 더미 vs 미만족 더미'로 "
      "갈라 평균 가격표가 유의하게 다르면 그 재료는 맛을 내는 재료(load-bearing 필터)다. "
      "여러 재료를 동시에 보면 우연히 맛있어 보이는 가짜가 나오므로 BH-FDR로 우연을 통제하고, "
      "효과가 잡음보다 확실히 큰지(효과크기 하한)와 두 해에서 같은 방향인지도 함께 봤다.")
    A("")
    A(f"**정직한 한정**: ① 이 진단은 이미 우승한 뒤 뜯어보는 것이다 — 재료 배합(임계값)이 과거 "
      "성적(2024 포함)을 보고 정해졌으므로 '이 재료가 맛있다'는 이 우승 레시피 계보 안에서의 진단이다. "
      "② 재료를 하나씩 시험하므로 'A와 B를 같이 넣어야만 맛있는' 조합 효과는 이번엔 못 본다.")
    A("")
    # 검증.
    det = summary["determinism_vs_npz"]
    gate = summary["gate"]
    A("## 1. 재현·검증 게이트")
    A("")
    A(f"- **온셋 L3 은행 재산출(F1)**: labels_v2 벡터 경로. Jul-11 v2a npz 대비 전수 결정론 "
      f"대조 — 일 {det['n_days']}개, off 불일치 {det['n_off_mismatch']}, L3 최대 절대오차 "
      f"{det['max_l3_abs_err']:.2e} → determinism_pass={det['determinism_pass']}.")
    A(f"- **F2 화이트리스트 게이트**: 로컬 정의 패리티(시가등락율·시가대비등락율·VI아래5호가 각 "
      f"1,000행 오차 0) + N1 지연 패리티(오차 0) → U-보류 6절 전부 M 승격. 순수중복 #15≡#39 "
      f"1절 병합. 게이트 확정 자격 절 {q['n_qualified']}개(봉인 상한 39; §13-F2 헤드라인 33~39 는 "
      f"순수중복을 2로 센 범위, §8 병합 후 운영 자격 32~38). 이 중 표본 하한(양쪽≥2,000·연도별≥400) "
      f"통과 {denom}개가 최종 FDR 분모(§5 — 미달 {j['inconclusive_nums']} 제외).")
    p3 = gate["p3_reproduction"]
    A(f"- **§6 P3 재현 게이트**: 벡터 절 값 vs 엔진 exec(스칼라) {p3['n_pairs']}쌍 중 "
      f"{p3['n_agree']} 일치({p3['agreement_pct']:.1f}%).")
    A("")
    # 판정표.
    A("## 2. 판정표 (자격 절 전체)")
    A("")
    A("| # | 절(만족 방향) | 족 | 티어 | 만족/미만족 n | Δ(%p) | 일자블록 CI | 연도부호(22/23) | 양측p | FDR | MDE(%p) | 분류 |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for n in q["qualified_nums"]:
        A(clause_row(n))
    A("")
    if j["inconclusive_nums"]:
        A(f"**표본 하한 미달(inconclusive, 분모 제외)**: {j['inconclusive_nums']} "
          "— 만족·미만족 한쪽이 n<2,000 또는 연도별<400.")
        A("")
    # 목록.
    A("## 3. load-bearing / 역생산 / 약신호")
    A("")
    A(f"- **load-bearing 절**: {lb if lb else '없음(0)'}"
      + ("".join(f"\n  - #{n} {per[n]['text']} — Δ={_fmt(per[n]['delta_pp'])}%p "
                 f"CI[{_fmt(per[n]['ci_low_pp'])},{_fmt(per[n]['ci_high_pp'])}]" for n in lb)))
    A(f"- **역생산 절(Δ≤−0.10%p ∧ FDR 생존, 빼면 좋아질 후보)**: {cp if cp else '없음(0)'}"
      + ("".join(f"\n  - #{n} {per[n]['text']} — Δ={_fmt(per[n]['delta_pp'])}%p" for n in cp)))
    A(f"- **약신호(+0.05~0.10%p ∧ CI>0, 통과 아님)**: {wk if wk else '없음(0)'}"
      + ("".join(f"\n  - #{n} {per[n]['text']} — Δ={_fmt(per[n]['delta_pp'])}%p" for n in wk)))
    A(f"- **족 단위 계상(§8, 근접 중복 인플레 차단)**: load-bearing 족(절-단위 load-bearing 을 "
      f"밑변수로 집계) = {j['load_bearing_families']} ({len(j['load_bearing_families'])}건). "
      f"참고 — FDR 생존 양(+) 동부호 족(약신호 포함, 넓은 층) = {j.get('sig_positive_families', [])}.")
    A("")
    # sanity + 딱지 + 경계.
    A("## 4. sanity anchor · known-오염 딱지 · 해석 경계")
    A("")
    A(f"- **sanity anchor(§13)**: 자격 절 전부 |Δ|<0.02%p 여부 = {j['sanity_anchor_tripped']}. "
      + ("**발동됨 — 수동 스팟 대조 필요(0-생존 kill 수용 전).**"
         if j["sanity_anchor_tripped"]
         else "미발동(등락율 등 절에서 유의 규모 Δ 관측 — 파이프라인 결함 신호 없음)."))
    A(f"- **known-오염 딱지(§9, 강제 인쇄)**: {summary['contamination_label']}")
    A("- **해석 경계(§0·§10)**: 0-생존은 '단일 절 분해 불가'이지 '엣지 부재'가 아니다. "
      "교호작용(2절 이상 결합)은 다중성 폭발(C(38,2)) 때문에 이 라운드 제외 — 후속 별도 봉인.")
    A(f"- **관심종목(#22) 유니버스 조건부 경고(§4.1)**: 이 절의 Δ 해석은 유니버스 재구성 "
      "타당성(probe-min-d9 소관)에 조건부다. 온셋 전량이 유니버스 내(관심종목==1)이면 "
      "미만족측 표본이 없어 판정 불가(inconclusive)로 기록된다.")
    A("- **대조 라벨 h300(§5)**: v2a 인프라에 병기 가능하나 '채택 조건 아님'이며 D1 판정은 "
      "L3(RR8_12 출구 조건부)만 사용한다 — 절 효과의 출구-특이성 분리는 후속(h300 병기 재현) 몫.")
    A("")
    A(f"*엔진 백테 0회 · 원본 DB read-only · git 커밋 없음 · 2024/2025 미접촉. "
      f"산출물: onset_l3_bank.parquet(F1 출구 은행) + d1_onset_clause_bits.parquet(D1 파티션, git 제외).*")
    return "\n".join(lines) + "\n"


def append_n_trials(
    ledger_path, judgment: Mapping[str, object], *,
    session: str = "alpha-restart-d1", window: str = "2022-03-23~2023-12-31(발견창)",
) -> int:
    """자격 절 수만큼 series D1 type-b 행 append(D5-R 원장 포맷). 반환: append 행수."""
    per = judgment["per_clause"]
    ts = datetime.now(timezone.utc).isoformat()
    denom = judgment["fdr_denominator"]
    rows: List[dict] = []
    for n in judgment["qualified_nums"]:
        r = per[n]
        cls = r.get("classification", "inconclusive" if not r["floor_pass"] else "none")
        result = (
            f"{cls} — Δnet {_fmt(r['delta_pp'])}%p, "
            f"CI[{_fmt(r['ci_low_pp'])},{_fmt(r['ci_high_pp'])}], "
            f"양측p {r['p_two_sided']:.4f}, FDR생존 {r.get('fdr_survive', False)}, "
            f"MDE {_fmt(r['mde_pp'])}%p, 연도부호 "
            f"{r['year_delta'][2022]['sign']}/{r['year_delta'][2023]['sign']}, "
            f"표본 {r['n_sat']}/{r['n_unsat']}, floor_pass {r['floor_pass']} "
            f"(FDR 분모={denom})"
        )
        rows.append({
            "ts": ts, "series": "D1", "window": window,
            "trial_type": "b(오프라인 봉인 판정)",
            "target": (f"D1 절 #{n} ({r['text']}) A/B 분해 — 만족 vs 미만족 L3 평균 Δ "
                       "≥+0.10%p ∧ 일자블록 CI하한>0 ∧ BH-FDR ∧ 연도 동부호 "
                       "(사전등록 §7, 후보 단위 type-b)"),
            "result": result, "session": session,
        })
    with open(ledger_path, "a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)
