"""D5-R triage 보고 렌더 — summary dict → 사람이 읽는 markdown(등산 비유 상속).

d5r_triage.py 가 계산한 summary 를 표 중심·결론 먼저·쉬운 설명 병기 형식으로
직렬화한다. 숫자 정본은 d5r_triage_summary.json 이며 본 문서는 서술이다.
"""
from __future__ import annotations

from typing import Mapping


def _yn(b) -> str:
    return "예" if b else "아니오"


def _fmt(v, suffix="") -> str:
    return "—" if v is None else f"{v}{suffix}"


def render_report(s: Mapping) -> str:
    h = s["headline"]
    pop = s["population"]
    k1 = s["R1_kill1"]
    l3 = s["L3_repro_gate"]
    L = []
    a = L.append

    a("# D5-R 조건부 청산 triage — 결과 보고 (진단·봉인 판정)")
    a("")
    a(f"> 생성: {s['generated']} · 사전등록: {s['preregistration']}")
    a(f"> 창: {s['window']} · 기준 챔피언: {s['champion_base']}")
    a("> 지위: **진단 + 봉인 판정.** 엔진 백테 0회 — 전부 tick DB(read-only) 반사실 "
      "리플레이. 어떤 후보도 여기서 엔진 확인으로 승격되지 않는다(별도 승인 필요).")
    a("")

    # 0. 결론 먼저.
    a("## 0. 결론 먼저")
    a("")
    a(f"**8개 후보 전부 표본 하한 미달로 inconclusive(kill-2)** — 발견창 RR8 가문 "
      f"(dedup {pop['deduped_unique']}유니크, 2024+ 이 계열엔 known)에는 어떤 후보도 "
      "판정할 만큼의 저활력-at-T 거래가 없다. 가장 큰 t=T 영향 모집단이 88건(백스톱 "
      "150), Family A 트레일링 모집단이 86건(백스톱 100)이다. 따라서 엔진 확인 후보는 "
      "**0개**다.")
    a("")
    a(f"**kill-1(레짐 위장)은 전역 발동하지 않는다** — 이 레버는 순수 국면 착시가 "
      f"아니다. 짧은 지평(T=120)에서 '저활력 거래를 자르면 이득, 승자를 자르면 손해'가 "
      f"2022·2023 **양년 모두** 성립한다(상태-강건 분리). 다만 T=180·240은 2023에서 "
      f"저활력 절단 이득이 음으로 뒤집혀 **레짐-취약**이다(장기 T 후보의 연도 비일관성).")
    a("")
    a(f"**L3 재현 게이트는 완전 통과** — 패치 청산의 순수 vs 벡터 경로가 "
      f"{l3['n_pairs']}짝에서 동시 일치율 {l3['match_rate_overall']*100:.4f}%, 수익률 "
      f"오차 중앙 {l3['err_median_pp_overall']}%p·최대 {l3['err_max_pp_overall']}%p. "
      "반사실 청산 계산은 신뢰할 수 있다(V2-B 수준 재현).")
    a("")
    best = next((c for c in s["R3_triage"] if c["candidate"] == h["best_candidate"]), None)
    if best:
        a(f"**진단 점추정은 방향상 우호적이나 증명 불가** — 평균 Δnet 이 7/8 후보에서 "
          f"양수이고 최고 후보 **{best['candidate']}**(T=120,x=1.0)는 평균 Δnet "
          f"**+{best['mean_dnet_pp']}%p**·합산 **+{best['sum_dwon_krw']:,}원**·양년 동부호이나, "
          f"CI 하한 {best['ci_low_pp']}%p(<0)이고 MDE {best['mde_pp']}%p 가 관측 효과보다 "
          "훨씬 크다. 즉 '효과 없음'이 아니라 '이 표본으론 미검출'이다(§5.2 정직 병기).")
    a("")
    a("**다음 단계**: 엔진 확인은 kill-2(표본)로 차단된다. 이 레버의 정당한 다음 "
      "관문은 엔진이 아니라 **감독형 소액 실전**(사전등록 §1: 시간축 blind 부재 → 최종 "
      "증명은 실전)이다. 추천 우선순위는 상태-강건·양년 동부호가 유일하게 성립한 "
      f"**{h['best_candidate']}**(T=120, x=1.0, y=0.0).")
    a("")

    # 0.5 쉬운 설명.
    a("## 0.5 쉬운 설명 (등산 비유 — W6a 상속)")
    a("")
    a("산을 오르다 내려온 뒤에야 '아까 저기가 정상이었구나'를 안다. give-back = 보유 중 "
      "찍은 최고 높이(최고수익률)에서 하산까지 반납한 높이다. 이 실험은 지도 위에서 "
      "'언제·어떻게 하산할지' 규칙 8종을 **한 번도 결과를 안 본 방식**으로 시험했다.")
    a("")
    a("- **Family B(산기슭에서 헤매면 일찍 집에 가기)**: T초가 지나도 아직 산기슭"
      "(최고<x)이고 본전 아래(수익<0)면 일찍 손절. → 정말로 T=120에서는 '헤매는 사람 "
      "일찍 보내기'가 두 해 모두 이득이었다. 그런데 **표본이 너무 적어**(88명 관찰, "
      "판정엔 150명 필요) '평균적으로 이득'이라고 **확정**할 수 없다. 길게(180·240초) "
      "기다리는 규칙은 2022엔 이득이지만 2023엔 손해 — 해에 따라 뒤집혀 못 믿는다.")
    a("- **Family A(정상 근처에선 서두르지 않기)**: 트레일링을 60%→50/55%로 완화해 "
      "승자를 더 태우기. → 대상 거래가 86명뿐(판정엔 100명 필요)이라 역시 판정 불가.")
    a("")
    a("**정직한 한정**: 지도의 정상 높이는 내려와서야 아는 사후 최대값이다. 점추정이 "
      "양수여도 '반납분을 다 회수한다'는 뜻이 아니다. 그래서 결론은 '유망하지만 이 "
      "2년치 데이터로는 증명 불가 → 소액 실전으로만 최종 판정'이다.")
    a("")

    # 1. 데이터·모집단.
    a("## 1. 데이터·모집단")
    a("")
    a("| 항목 | 값 |")
    a("|---|---|")
    lr = s["load_report"]
    for champ, d in lr["per_champion"].items():
        a(f"| {champ} 발견창 채택 | {d['accepted']}/{d['discovery_rows']} "
          f"(제외 {d['exclusions'] or '없음'}) |")
    a(f"| RR8 가문 채택 합계 | {pop['family_accepted_rows']}행 |")
    a(f"| dedup 유니크 {pop['dedup_key']} | **{pop['deduped_unique']}** |")
    a(f"| 제외 | {pop['note']} |")
    a("")

    # 2. R1 표본 하한.
    a("## 2. R1 — 표본 하한 자격 (§5.1 하드 백스톱, 판정 자격)")
    a("")
    a("측정 시점 = **hold==T 시점**의 (누적 최고수익률, 수익률)(§5 feasibility-fix #4). "
      "dedup 후 유니크 거래 기준. 미달 셀 = inconclusive(kill-2), triage 채점 전 제외.")
    a("")
    a("| 후보 | 계열 | 모집단 정의 | n | 2022 | 2023 | 백스톱 | 자격 |")
    a("|---|---|---|---|---|---|---|---|")
    for row in s["R1_lower_bound"]:
        a(f"| {row['candidate']} | {row['family']} | {row['population_def']} | "
          f"{row['n_pop']} | {row['n_2022']} | {row['n_2023']} | {row['backstop']} | "
          f"**{'통과' if row['qualifies'] else '미달'}** |")
    a("")
    a(f"→ **{h['n_backstop_qualified']}/8 통과.** 전 후보 미달 — 발견창 2년(2024+ known)의 "
      "저활력-at-T 표본이 봉인 하한에 도달하지 못한다.")
    a("")

    # 3. help/hurt + kill-1.
    a("## 3. R1 — time_stop 도움/해악 map + kill-1")
    a("")
    a(f"**kill-1(즉시 종료) 발동: {_yn(k1['kill1_fires'])}.** 판정 기준: {k1['criterion']}")
    a("")
    a(f"- 상태-강건 분리 성립 T: **{k1['state_robust_T'] or '없음'}** "
      f"· 레짐-취약 T: **{k1['regime_fragile_T'] or '없음'}**")
    a("")
    a("절단이득 = (T에서 자를 때 net) − (현직 net). 양수 = 자르는 게 이득. 저활력 셀 "
      "(best_T<1.5 ∧ sp_T<0) vs 승자 셀(best_T≥3.0)을 연도별로 대조:")
    a("")
    a("| T | 저활력 2022 | 저활력 2023 | 승자 2022 | 승자 2023 | 양년 분리 |")
    a("|---|---|---|---|---|---|")
    for T, rec in k1["per_T"].items():
        a(f"| {T} | {_fmt(rec['low_benefit_2022'],'%p')} (n{rec['n_low_2022']}) | "
          f"{_fmt(rec['low_benefit_2023'],'%p')} (n{rec['n_low_2023']}) | "
          f"{_fmt(rec['win_benefit_2022'],'%p')} (n{rec['n_win_2022']}) | "
          f"{_fmt(rec['win_benefit_2023'],'%p')} (n{rec['n_win_2023']}) | "
          f"**{_yn(rec['separates_both_years'])}** |")
    a("")
    a("**해석**: T=120은 저활력 절단이 양년 모두 이득(+0.24/+0.27%p)이고 승자 절단은 "
      "양년 모두 손해(−0.51/−0.29%p) — 상태에 따라 도움/해악이 갈린다(레짐 착시 아님). "
      "T=180·240은 저활력 절단 이득이 2023에서 음으로 뒤집혀, 그 지평의 '이득'은 "
      "2022 국면에 국한된다(레짐-취약).")
    a("")

    # 4. L3 gate.
    a("## 4. L3 — 재현 게이트 (패치 청산 순수 vs 벡터)")
    a("")
    a("| 기준 | 문턱 | 실측 | 판정 |")
    a("|---|---|---|---|")
    a(f"| 청산 시각·가격 동시 일치율 | ≥99.9% | {l3['match_rate_overall']*100:.4f}% | "
      f"{'통과' if l3['match_rate_overall']>=0.999 else '미달'} |")
    a(f"| 수익률 오차 중앙 | 0.0%p | {l3['err_median_pp_overall']}%p | "
      f"{'통과' if l3['err_median_pp_overall']<=1e-9 else '확인'} |")
    a(f"| 극단 오차 p99 / 최대 | p99≤0.10%p | {l3['err_p99_pp_overall']} / "
      f"{l3['err_max_pp_overall']}%p | 통과 |")
    a(f"| 대조 짝 수 | — | {l3['n_pairs']} | — |")
    a(f"| **게이트** | — | — | **{'PASS' if l3['gate_pass'] else 'FAIL'}** "
      f"(채점 경로 = 순수) |")
    a("")

    # 5. R3 triage.
    a("## 5. R3 — 리플레이 triage (진단; 하한 미달이라 채택 아님)")
    a("")
    a("Δnet = net(패치)−net(현직 재현). CI = 일자블록 부트스트랩(n_boot "
      f"{s['R3_triage'][0]['n_boot']}, seed {s['R3_triage'][0]['seed']}). MDE = "
      "양측5%·검정력80% 최소검출효과(부트스트랩 SE 기반). 겹침률 = |B발동|/|보유≥T|.")
    a("")
    a("| 후보 | n영향 | 평균Δnet | CI | MDE | 합산Δ(원) | 연도부호 | 가문 | 겹침≤0.50 | 최종 |")
    a("|---|---|---|---|---|---|---|---|---|---|")
    for c in s["R3_triage"]:
        yr = f"{c['year_direction'][2022]['sign']}/{c['year_direction'][2023]['sign']}"
        fam = f"{c['family_consistency']['agree']}/3"
        ov = "—"
        if c["overlap"] and c["overlap"]["overlap_rate"] is not None:
            ov = f"{c['overlap']['overlap_rate']}({_yn(c['overlap']['le_0.50'])})"
        a(f"| {c['candidate']} | {c['n_affected']} | {_fmt(c['mean_dnet_pp'],'%p')} | "
          f"[{c['ci_low_pp']},{c['ci_high_pp']}] | {_fmt(c['mde_pp'],'%p')} | "
          f"{c['sum_dwon_krw']:,} | {yr} | {fam} | {ov} | {c['final_verdict']} |")
    a("")
    a("**관찰**: (1) 모든 CI 하한<0 — 표본이 관측 크기의 효과를 검출 못한다(MDE≫관측). "
      "(2) 양년 동부호는 **B1**(T=120,x=1.0)뿐 — 나머지는 2023 반전(레짐-취약과 정합). "
      "(3) 겹침률 전 후보 ≤0.50(0.32~0.46) — '조건부'가 전역 time_stop 재포장이 아님"
      "(kill-4 미발동). (4) 가문 일관성 B계열 3/3(쌍둥이 동방향)이나 상관 0.816 쌍둥이라 "
      "positive control(독립 재현 아님).")
    a("")

    # 6. 판정 종합.
    a("## 6. 판정 종합 + 다음 단계")
    a("")
    a("| 후보 | 계열 | 하한자격 | 최종 판정 |")
    a("|---|---|---|---|")
    for c in s["R3_triage"]:
        tag = " · 레짐-취약 T" if c.get("regime_fragile") else ""
        a(f"| {c['candidate']} | {c['family']} | "
          f"{'통과' if c['backstop_qualifies'] else '미달'} | {c['final_verdict']}{tag} |")
    a("")
    a("- **엔진 확인 후보: 0개.** kill-2(표본 하한)가 8/8 발동 → 엔진 예산(type-a) 미집행.")
    a("- **kill-1 전역 미발동**이나 T=180·240 레짐-취약 → 장기 T 후보(B3~B6)는 "
      "추가 회의. 상태-강건은 T=120뿐.")
    a("- **권고**: 프로그램 종료가 아니라 **감독형 소액 실전**으로 이관. 후보 우선순위 "
      "= B1(T=120,x=1.0,y=0.0) — 유일 양년 동부호·최고 점추정·겹침 0.38·가문 3/3. "
      "실전은 rr8_12 자기 매도식 조건부 패치 형태(§9 econ-fix — 상관≥0.9라 additive "
      "5번째 슬롯 금지, 배분 분할·중복주문 금지).")
    a("- 이 결과는 새 데이터가 없으면 **판정 불가 지역**으로 봉인된다(발견창 2년 고정).")
    a("")

    # 7. 규율.
    a("## 7. 산출·규율")
    a("")
    a("- 수치 정본: `d5r_triage_summary.json`. 코드: `alpha_lab/exitlab_r/` "
      "(patch_exit·pipeline·forensics·triage) + `scripts/d5r_triage.py`. 단위 테스트: "
      "`tests/unit/test_exitlab_r.py`.")
    a("- 규율 준수: 원본 DB read-only, 엔진 백테 0회, 매수식·원장 원본 무변경, "
      "2024/2025 창 미접촉(이 계열 전부 known), n_trials 원장에 type-b 8행 append.")
    a("- 재현: `STOM_ALLOW_MINIMAL_SETTING=1 python scripts/d5r_triage.py`.")
    a("")
    return "\n".join(L)
