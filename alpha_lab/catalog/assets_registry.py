"""자산 레지스트리 데이터 — 계획(2026-07-12 WBS v3) §1 관계표의 기계가독 사본.

각 항목: base='run'이면 run 디렉토리 기준, base='root'면 워크트리 루트 기준 경로.
produced_commit은 핸드오프 v3 §2 커밋 체인·계획 §1 표에서 옮긴 값이며, 체인
문서에 명시가 없으면 None(빌더는 git을 호출하지 않는다 — 읽기 git 금지 규율).
regen_cmd는 git 제외 자산 유실 대비 재생성 명령(계획 §5-2). git 추적 자산은
'git 정본(재생성 불필요)'로 표기한다.
"""
from __future__ import annotations

from typing import Dict, List

_GIT = "git 정본(재생성 불필요)"
_WIN_DISC = "2022-03-23~2023-12-31(발견 가용)"
_SEAL_D1 = "plans/2026-07-12_d1_clause_ablation_preregistration.md(56564cba)"
_SEAL_STRACK = "plans/2026-07-10_s_track_preregistration.md(0b8dcd43)"
_SEAL_V2A = "plans/2026-07-11_w3r_v2a 봉인(bb0778ef)"
_SEAL_O1G = "plans/2026-07-11_o1g_gap_feasibility_preregistration.md(8bc8dbb9)"
_SEAL_D5R = "plans/2026-07-12_d5r_conditional_exit_preregistration.md(ac5ca448)"

# 자산 레지스트리(계획 §1 표 + 핸드오프 v3 §6). 필드 누락 없이 유지할 것.
ASSET_REGISTRY: List[Dict[str, object]] = [
    dict(
        asset_id="onset_l3_bank_parquet", kind="bank_parquet", base="run",
        path="stats_map/onset_l3_bank.parquet", produced_commit="7171a561",
        seal_doc=_SEAL_D1, window=_WIN_DISC,
        status_tag="RR8_12 출구 조건부·bit-identical 검증(Jul-11 npz 일치)",
        regen_cmd="전용 CLI 없음 — alpha_lab/clause_lab(bank.py) 경로를 D1 사전등록(56564cba) 절차로 재실행, d1_clause_ablation_summary.json consolidate 절 참조",
        summary="출구 은행: 온셋 86.3만 행, L3=RR8_12 출구 net%p 라벨. D5/O-3/2절 교호작용의 공용 입력",
    ),
    dict(
        asset_id="d1_onset_clause_bits_parquet", kind="bank_parquet", base="run",
        path="stats_map/d1_onset_clause_bits.parquet", produced_commit="7171a561",
        seal_doc=_SEAL_D1, window=_WIN_DISC,
        status_tag="RR8_12 계보·절 39종 비트 행렬",
        regen_cmd="전용 CLI 없음 — alpha_lab/clause_lab(clauses.py 비트 평가) 경로를 D1 사전등록 절차로 재실행",
        summary="온셋×절 비트 행렬 — 2절 교호작용 측정의 재사용 입력",
    ),
    dict(
        asset_id="stats_map_sv1_db", kind="map_db", base="run",
        path="stats_map/stats_map.db", produced_commit="3a9b7843",
        seal_doc=_SEAL_STRACK, window=_WIN_DISC,
        status_tag="함정 설명 전용·자동 veto 금지(칸-조준 kill-2)",
        regen_cmd="STOM_ALLOW_MINIMAL_SETTING=1 python scripts/s_track_build_main.py",
        summary="S-v1 h300 지도(cells_l0/cells_l1 각 288행) — 엣지는 칸이 아니라는 설명 자산",
    ),
    dict(
        asset_id="stats_map_v2a_full_db", kind="map_db", base="run",
        path="stats_map/stats_map_v2a_full.db", produced_commit="f553378b",
        seal_doc=_SEAL_V2A, window=_WIN_DISC,
        status_tag="함정 설명 전용·자동 veto 금지(V2-C KILL 0/2)",
        regen_cmd="전용 CLI 없음 — alpha_lab/stats_map(pilot_v2·config_v2) 경로를 V2-A 봉인(bb0778ef) 절차로 재실행",
        summary="V2 본 적재 L3/h300 이중 라벨 셀(192행)",
    ),
    dict(
        asset_id="stats_map_v2a_pilot_db", kind="map_db", base="run",
        path="stats_map/stats_map_v2a_pilot.db", produced_commit="303c5fba",
        seal_doc=_SEAL_V2A, window="2022 파일럿 부분창",
        status_tag="함정 설명 전용·파일럿 참고(V2-B)",
        regen_cmd="전용 CLI 없음 — alpha_lab/stats_map(pilot_v2) 경로를 V2-A 봉인 절차로 재실행",
        summary="V2-B 리플레이 파일럿 셀(192행) — 재현 게이트 4/4 통과 기록",
    ),
    dict(
        asset_id="o1g_grid_summary", kind="judgment_json", base="run",
        path="o1g/o1g_grid_summary.json", produced_commit="19138c90",
        seal_doc=_SEAL_O1G, window=_WIN_DISC,
        status_tag="시초 함정 지도·O-3 null 기준선·자동 veto 금지",
        regen_cmd="STOM_ALLOW_MINIMAL_SETTING=1 python scripts/o1g_gap_analysis.py",
        summary="O-1G 갭×시총×진입창 144셀 수치 정본 — 양EV 증거 0",
    ),
    dict(
        asset_id="o1g_figs", kind="figure_set", base="run",
        path="o1g", produced_commit="19138c90",
        seal_doc=_SEAL_O1G, window=_WIN_DISC,
        status_tag="시초 함정 지도 그림 4종(자동 veto 금지)",
        regen_cmd="STOM_ALLOW_MINIMAL_SETTING=1 python scripts/o1g_gap_analysis.py",
        summary="fig_heatmap_gap_x_mktcap 등 히트맵·분포 그림 — 대시보드 V2 후보",
    ),
    dict(
        asset_id="d1_clause_ablation_summary", kind="judgment_json", base="run",
        path="d1_clause_ablation_summary.json", produced_commit="7171a561",
        seal_doc=_SEAL_D1, window=_WIN_DISC,
        status_tag="RR8_12 계보·L3 출구 조건부·원-임계 이식 금지",
        regen_cmd=_GIT,
        summary="D1 절-단위 A/B 분해 수치 정본 — 압력 절 5종 양성·역생산 6절",
    ),
    dict(
        asset_id="d1_f2_whitelist_gate", kind="gate_json", base="run",
        path="d1_f2_whitelist_gate.json", produced_commit="7171a561",
        seal_doc=_SEAL_D1, window=_WIN_DISC,
        status_tag="D1 F2 화이트리스트 게이트 기록",
        regen_cmd=_GIT, summary="D1 측정 전 화이트리스트 게이트 통과 기록",
    ),
    dict(
        asset_id="d5r_triage_summary", kind="judgment_json", base="run",
        path="d5r_triage_summary.json", produced_commit="951c9748",
        seal_doc=_SEAL_D5R, window=_WIN_DISC,
        status_tag="RR8_12 매도식(8ef01e0e) 지배·kill-2(B1만 실전 이관)",
        regen_cmd="STOM_ALLOW_MINIMAL_SETTING=1 python scripts/d5r_triage.py",
        summary="D5-R 조건부 청산 8후보 triage — 전부 하한 미달, 메커니즘 실재",
    ),
    dict(
        asset_id="w2_strategy_inventory", kind="inventory_json", base="run",
        path="w2_strategy_inventory.json", produced_commit="721db080",
        seal_doc="plans/2026-07-10_alpha_restart(W1+W2)", window="창 혼재(전략별 상이 — 연/월 정규화 비교만)",
        status_tag="랭킹 정본·창 혼재 주의(직접 총수익 비교 금지)",
        regen_cmd=_GIT,
        summary="전략 랭킹: 엔진 top40/top20·ALP_V4 4종·인간 전당 19종(외부 벤치마크)",
    ),
    dict(
        asset_id="w3_profiling", kind="cost_json", base="run",
        path="w3_profiling.json", produced_commit="0b8dcd43",
        seal_doc="W3 봉인(0b8dcd43)", window=_WIN_DISC,
        status_tag="경계·비용 프로파일(초판)", regen_cmd=_GIT,
        summary="거래 경계·왕복비용 초판 산정",
    ),
    dict(
        asset_id="w3r_boundary_reseal", kind="cost_json", base="run",
        path="w3r_boundary_reseal.json", produced_commit="bb0778ef",
        seal_doc="W3-R 재봉인(bb0778ef)", window=_WIN_DISC,
        status_tag="경계·왕복비용 재산정 정본(현행)", regen_cmd=_GIT,
        summary="W3-R 경계·비용 재산정 — 이후 측정의 비용 기준",
    ),
    dict(
        asset_id="w4_full_build", kind="build_json", base="run",
        path="w4_full_build.json", produced_commit=None,
        seal_doc=_SEAL_STRACK, window=_WIN_DISC,
        status_tag="S-v1 본 적재 빌드 영수증(게이트 4종)",
        regen_cmd="STOM_ALLOW_MINIMAL_SETTING=1 python scripts/s_track_build_main.py",
        summary="L0 3,262만/L1 86.3만 적재 영수증 — param_sha·summary_sha 지문 포함",
    ),
    dict(
        asset_id="w4_champion_overlay", kind="overlay_json", base="run",
        path="w4_champion_overlay.json", produced_commit=None,
        seal_doc=_SEAL_STRACK, window=_WIN_DISC,
        status_tag="챔피언 진입 칸 오버레이(advisory)",
        regen_cmd="STOM_ALLOW_MINIMAL_SETTING=1 python scripts/s_track_champion_gate.py",
        summary="ALP_V4 4종 진입 칸 게이트·인간 전당 공통 밴드 advisory",
    ),
    dict(
        asset_id="w5_composite_survey", kind="vocab_json", base="run",
        path="w5_composite_survey.json", produced_commit="4ee6ed80",
        seal_doc="W5 조사(4ee6ed80 — 측정 아님)", window="정적 파싱(창 비접촉)",
        status_tag="절 어휘 사전 2,278절·Composite 설계 입력",
        regen_cmd=_GIT,
        summary="절 어휘 유형 9종 분포 + 병합 문법 + RR8 신호 중복 조사",
    ),
    dict(
        asset_id="w6a_giveback", kind="map_json", base="run",
        path="w6a_giveback.json", produced_commit="8b95eb09",
        seal_doc="W6a 포렌식(진단 전용 — 채택 판정 아님)", window=_WIN_DISC,
        status_tag="진단 전용·n_trials 비등록(give-back 지도)",
        regen_cmd=_GIT,
        summary="MFE 반납(give-back) 상태 지도 — D5-R 격자의 근거",
    ),
    dict(
        asset_id="ground_grammar_map", kind="grammar_json", base="run",
        path="ground_grammar_map.json", produced_commit="721db080",
        seal_doc="W1 문법 지도", window="정적(창 비접촉)",
        status_tag="조건식 작성·번역 검증 정본", regen_cmd=_GIT,
        summary="변수·구문 문법 지도 — 모든 조건식 번역 검증 관문",
    ),
    dict(
        asset_id="probe_min_d9", kind="probe_json", base="run",
        path="probe_min_d9.json", produced_commit="3ade1286",
        seal_doc="probe(3ade1286)", window=_WIN_DISC + " 스팟",
        status_tag="min=audit-grade 전용·D9 접목 가능(일치 100%)",
        regen_cmd=_GIT,
        summary="min DB·D9 전이 온셋 프로브 — 둘 다 생존",
    ),
    dict(
        asset_id="v2b_pilot_summary", kind="judgment_json", base="run",
        path="v2b_pilot_summary.json", produced_commit="303c5fba",
        seal_doc=_SEAL_V2A, window="2022 파일럿 부분창",
        status_tag="V2-B 파일럿 — 재현 게이트 4/4 통과", regen_cmd=_GIT,
        summary="L3 리플레이 파일럿 요약(비대칭 개선 1차 관찰)",
    ),
    dict(
        asset_id="v2c_gate_summary", kind="judgment_json", base="run",
        path="v2c_gate_summary.json", produced_commit="f553378b",
        seal_doc=_SEAL_V2A, window=_WIN_DISC,
        status_tag="칸-조준 KILL(0/2) 정본 — 두 라벨 교차 실패", regen_cmd=_GIT,
        summary="V2-C 가문 투표 게이트 — 칸-조준 최종 kill 판정 수치",
    ),
    dict(
        asset_id="n_trials_ledger", kind="ledger_jsonl", base="run",
        path="n_trials_ledger.jsonl", produced_commit="0608043c~(지속 갱신)",
        seal_doc="plans/2026-07-10_window_status_ledger.md", window="전 창 등록부",
        status_tag="측정 관문 — append-only·모든 측정 전 대조", regen_cmd=_GIT,
        summary="n_trials 시도 장부 — 사전등록·판정·엔진확인 행 전수",
    ),
    dict(
        asset_id="window_status_ledger_doc", kind="ledger_md", base="root",
        path="docs/research/condition_research/plans/2026-07-10_window_status_ledger.md",
        produced_commit="0608043c",
        seal_doc="자체(원장 정본)", window="전 창 등록부",
        status_tag="창-지위 원장 — known=veto 전용", regen_cmd=_GIT,
        summary="창 오염 지위 원장 — 모든 측정의 관문",
    ),
    dict(
        asset_id="b1_ab_verdict", kind="engine_ab_json", base="run",
        path="d5r_b1_live/_ab_verdict.json", produced_commit=None,
        seal_doc="plans/2026-07-12_b1_supervised_live_protocol.md", window="2022·2023 연도별 A/B",
        status_tag="엔진 A/B 4런 전체 PASS — 30거래일 채점 전 성공 주장 금지",
        regen_cmd="d5r_b1_live/ab_judge.py(엔진 A/B 재실행은 메인 세션 승인 필요 — type-a)",
        summary="B1 감독형 이관 엔진 A/B 판정(ΣΔ+1,538,872원 동방향)",
    ),
    dict(
        asset_id="b1_registration_receipt", kind="receipt_json", base="run",
        path="d5r_b1_live/b1_registration_receipt.json", produced_commit=None,
        seal_doc="plans/2026-07-12_b1_supervised_live_protocol.md", window="—",
        status_tag="ALP_D5R_B1_S INSERT-only 등록·3중 sha 검증",
        regen_cmd="d5r_b1_live/register_b1.py(재실행 금지 — 등록 영수증 정본)",
        summary="B1 전략쌍 등록 영수증(매수=348c5181 미러·매도=48018620)",
    ),
    dict(
        asset_id="b1_protocol_doc", kind="protocol_md", base="root",
        path="docs/research/condition_research/plans/2026-07-12_b1_supervised_live_protocol.md",
        produced_commit=None,
        seal_doc="자체(절차서 정본)", window="실전 30거래일 채점",
        status_tag="감독형 소액 실전 절차서 — 킬스위치·채점표 정본", regen_cmd=_GIT,
        summary="B1 실전 운용 규칙·킬스위치·채점표·기록 양식",
    ),
    dict(
        asset_id="research_assets_db", kind="catalog_db", base="run",
        path="research_assets.db", produced_commit=None,
        seal_doc="plans/2026-07-12_asset_integration_and_dashboard_plan.md §3", window="—",
        status_tag="카탈로그+요약 계층(정본 아님 — 원본 파일이 정본)",
        regen_cmd="python scripts/build_research_catalog.py",
        summary="본 카탈로그 DB — 언제든 재생성 가능, git 제외",
    ),
]
