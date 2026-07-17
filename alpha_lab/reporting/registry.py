"""연구 레지스트리 — 11개 연구의 정체(id·이름·쉬운 한줄·봉인 커밋·판정·봉인 문서·증거 json·추출기 키).

판정 라벨과 봉인 커밋은 봉인된 프로그램 사실(핸드오프 v3 §3·봉인 커밋 체인)이고, **핵심 수치는
loaders 추출기가 판정 json 에서 로드**한다(하드코딩 금지·부재 시 '증거 파일 없음'). 정적 서사(점수
65·전당 표·정직 한정 §5·SOP·창-지위)는 결산 v1(`reports/2026-07-16_b1_program_report.html`)에서
가져오되 본 모듈에 출처를 명기한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

__all__ = [
    "FUNNEL", "HONESTY", "PLANS", "SCORE", "SOP_STEPS", "STUDIES", "WINDOW_LEDGER",
    "Study", "verdict_badge", "verdict_counts",
]

PLANS = "docs/research/condition_research/plans"


@dataclass(frozen=True)
class Study:
    id: str
    name: str
    easy: str          # 쉬운 한줄(비유 포함).
    method: str        # 방법 한 단락.
    commit: str        # 봉인 커밋(핸드오프 §2 체인).
    verdict: str       # 양성 / 기각 / 미결 / 실전이관 / 종결.
    badge: str         # css: posv/kill/hold/live.
    seal_doc: str      # 봉인 문서(plans 상대).
    evidence: Tuple[str, ...]   # 판정 json(연구랩 상대) — 각주용.
    extractor: str     # loaders.EXTRACTORS 키.

    @property
    def date(self) -> str:
        """봉인 문서 파일명의 날짜(YYYY-MM-DD)."""
        base = self.seal_doc.split("/")[-1]
        return base[:10] if base[:4].isdigit() else ""

    @property
    def detail_href(self) -> str:
        """허브→상세 상대 링크(reports/ 기준)."""
        return f"research/{self.id}.html"


STUDIES: Tuple[Study, ...] = (
    Study("strack", "S-트랙 칸-조준", "지도를 아무리 촘촘히 그려도 챔피언 사냥터가 '평균 이하 칸'으로 보였다 — 엣지는 구역이 아니었다.",
          "시간대×등락율×시총으로 시초 30분을 격자로 나눠 챔피언 점유 칸의 실현손익(L3) 우위를 두 라벨(h300·L3)로 가문 투표 검정.",
          "f553378b", "기각", "kill", "2026-07-11_s_track_preregistration_v2a.md",
          ("v2c_gate_summary.json",), "strack"),
    Study("o1g", "시초 갭×시총 144셀", "'싸게 시작해 튀는 소형주'라는 직관을 144칸 전수로 재보니 양(+)인 칸이 하나도 없었다.",
          "시가갭×시총×진입창×출구 4종의 144셀 전수 측정 — 각 셀 조건부 기대값(비용 차감 L3)에 BH-FDR.",
          "8bc8dbb9", "기각", "kill", "2026-07-11_o1g_gap_feasibility_preregistration.md",
          ("o1g/o1g_grid_summary.json",), "o1g"),
    Study("d1", "D1 챔피언 절 분해", "우승 레시피(챔피언 매수식)를 재료 하나씩 뜯어 '진짜 맛을 내는 재료' 5개를 찾았다.",
          "챔피언 매수식의 39 유니크 절을 863,446 서지 온셋 위에서 만족/미만족으로 갈라 L3 평균차(Δ)를 효과크기·CI·FDR·연도부호로 검정.",
          "56564cba", "양성", "posv", "2026-07-12_d1_clause_ablation_preregistration.md",
          ("d1_clause_ablation_summary.json",), "d1"),
    Study("d5r", "D5-R 청산 triage", "8가지 청산 개선안을 재보니 통계 하한엔 못 미쳤지만, 그 안에서 진짜 메커니즘 하나(저활력 절단)가 살아 있었다.",
          "챔피언 실거래를 재현해 8개 청산 후보의 손익 개선을 하한·상태강건성으로 triage — kill-2였으나 T=120 저활력 절단만 실전 후보로.",
          "ac5ca448", "기각", "kill", "2026-07-12_d5r_conditional_exit_preregistration.md",
          ("d5r_triage_summary.json",), "d5r"),
    Study("b1", "B1 청산 패치 (실전 이관)", "\"120초 들고도 최고 1%도 못 갔고 지금 손실이면 잘라라\" — 매수는 그대로, 매도에 절 하나 추가.",
          "챔피언 매도식 + 저활력 절단 절 1개. STOM 엔진 A/B 4런(2022·2023 × 원본/B1, tick·배팅 500만)으로 실측 검증 → 전략 DB 등록.",
          "1ca2c7aa", "실전이관", "live", "2026-07-12_b1_supervised_live_protocol.md",
          ("d5r_b1_live/_ab_verdict.json", "d5r_b1_live/A_2022.json", "d5r_b1_live/B_2022.json"), "b1"),
    Study("d5d9", "D5·D9 전이 온셋", "'관심종목에 새로 등장하는 순간'이 특별한가 봤더니, 대개 '거래급증' ±30초 안에서 일어나는 같은 사건이었다.",
          "관심종목 진입(D9 전이) 온셋을 서지 온셋과 ±30초 겹침률로 대조 — 겹침이 상한 0.50을 넘으면 구별되는 모집단 아님(kill-3).",
          "99944213", "기각", "kill", "2026-07-12_d5_d9_transition_onset_preregistration.md",
          ("d5_d9/d5_d9_r3_summary.json",), "d5d9"),
    Study("d1pair", "D1 2절 시너지", "혼자 넣으면 맛을 깎던 재료(가격대 필터)가 압력 재료와 함께면 해가 사라진다 — '궁합'의 최초 실증.",
          "D1 압력 5절 × 선정가드 6절 등 39짝의 2×2 차이-속-차이(교호 효과 I)를 CI·FDR·연도부호로 검정.",
          "e1c12697", "양성", "posv", "2026-07-12_d1_pairwise_interaction_preregistration.md",
          ("d1_pairwise_interaction_summary.json",), "d1pair"),
    Study("o3", "O-3 돌파 온셋", "차트술사가 사랑하는 '벽 뚫는 순간'(돌파)에 들어가 봤더니 다섯 종류 모두 평균 손해였다.",
          "구간최고가·신고가·시가·VI 돌파 5변형 70만건 온셋에 챔피언 출구(L3)를 붙여 변형×모집단별 절대 EV를 검정 — 전 단위 음(−).",
          "96a37d28", "기각", "kill", "2026-07-12_o3_breakout_onset_preregistration.md",
          ("o3/o3_breakout_summary.json",), "o3"),
    Study("o4", "O-4 생성 문법", "합격한 부품(압력 절+결합 규칙)으로 후보 158개를 조립했지만 전 조합이 전원 음(−) — 가산 조합엔 금맥이 없었다.",
          "압력 4족 ± 조건부 가드 ± 함정 회피로 조립한 매수 후보 158개(닫힌 문법)의 발화 집합 mean L3 를 효과 하한·FDR·겹침으로 검정.",
          "fd7bae48", "기각", "kill", "2026-07-13_o4_generation_grammar_preregistration.md",
          ("o4/o4_candidate_summary.json",), "o4"),
    Study("btrack", "B-트랙 가지 분해", "챔피언은 '경우의 수(가지)'로 사는데 우리 후보는 단일 AND였다 — 챔피언 깊은 가지가 최초의 양(+) 신호였다(표본 부족).",
          "챔피언 시간-분리 2가지(902 24절·905 26절)의 AND 발화 합집합 mean L3 를 3분법(재현/프레임갭/미결)으로 — n=114, +0.166%p, CI 0 걸침(c).",
          "db08c1de", "미결", "hold", "2026-07-13_b_track_branch_decomposition_preregistration.md",
          ("b_track/b_branch_summary.json",), "btrack"),
    Study("bext", "B-ext 다전략 확장", "같은 가문 전략들의 깊은 가지를 모아 표본을 늘려도 여전히 확정 불가(c) — 오프라인 발굴 축을 정직하게 종결했다.",
          "902905 가문 13종의 깊은 가지 + 챔피언 902/905 발화 합집합(합동 anchor) mean L3 를 3분법·층화로 재검정 — 표본 확장에도 (c) 재발.",
          "1e179bb6", "종결", "kill", "2026-07-14_b_track_ext_multistrategy_branches_preregistration.md",
          ("b_track_ext/b_ext_summary.json",), "bext"),
    Study("sell_d1", "매도식 D1 (절 제거 ablation)", "매도식 9개 절을 하나씩 꺼 보니 '빼서 좋아질 절'은 없었다 — 다섯 절은 확실히 돈을 지키는 절(load-bearing)이었다.",
          "매도식 발화 절 9개를 drop 미러 하니스로 하나씩 제거 재채점(영향 집합 {l3_clause==k} 서로소 분할) — 원본재현 862,932건 전수 비트동일 게이트 후 Δ·CI·FDR·연도부호 판정.",
          "bd5bb3c4", "양성", "posv", "2026-07-16_sell_d1_exit_ablation_preregistration.md",
          ("sell_d1/sell_d1_summary.json",), "sell_d1"),
    Study("x1", "X1 매수 절-삭제 엔진 A/B", "그물코(매수 조건) 4개를 하나씩 빼고 실제 바다(엔진)에 던져 봤다 — 더 많이 잡되 총어획이 느는 그물은 없었다.",
          "역생산 절 4종(시총 게이트·회전율·잔량비 2종)을 각각 삭제한 변형 매수식의 엔진 A/B 8런(기준 A=B1 런 재사용, 프로파일 동일) — C1 Δ총수익 양년동방향·C2 거래수 ≤4×·C3 MDD(×1.5 ∧ ≤15%)·C4 무오류 전건 요구.",
          "cb8a9d6a", "기각", "kill", "2026-07-17_x1_buy_clause_drop_ab_preregistration.md",
          ("x1/x1_summary.json",), "x1"),
)


def verdict_badge(v: str) -> str:
    return {"양성": "posv", "실전이관": "live", "미결": "hold"}.get(v, "kill")


def verdict_counts() -> dict:
    """레지스트리 판정 집계(프로그램 사실 — json 재계산 아님)."""
    c = {"양성": 0, "실전이관": 0, "미결": 0, "기각": 0, "종결": 0}
    for s in STUDIES:
        c[s.verdict] = c.get(s.verdict, 0) + 1
    return c


# ---------------------------------------------------------------------------
# 정적 서사 — 결산 v1(reports/2026-07-16_b1_program_report.html) §2·§4·§5 계승(출처 명기).
# ---------------------------------------------------------------------------

# §4 냉정한 자체 평가 65/100 — (항목, 득점, 만점, fill class, 폭%).
SCORE: Tuple[Tuple[str, int, int, str, int], ...] = (
    ("신규 수익 조건식 발굴", 14, 40, "dn", 35),
    ("오답 소거·확정 지식", 17, 20, "acc", 85),
    ("챔피언 이해·보호", 12, 15, "acc", 80),
    ("인프라·재사용성", 13, 15, "acc", 87),
    ("규율·신뢰성", 9, 10, "acc", 90),
)
SCORE_TOTAL = (65, 100)

# §5 정직한 한정 — (강조, 본문).
HONESTY: Tuple[Tuple[str, str], ...] = (
    ("① 발견창 성적이다.", "백테스트(2022~2023)는 챔피언 전략이 그 시기를 보며 만들어진 구간의 성적 — 시험 범위를 알고 본 시험에 가깝다. B1 패치는 시간축 미공개 구간이 없어 데이터로는 더 검증할 수 없다(절차서가 '실전 30거래일이 최종 심판'으로 봉인)."),
    ("② 자본을 키우면 가정이 달라진다.", "모든 수치는 종목당 500만원·체결 ±2틱 불리 가정. 자본을 억대로 올리면 슬리피지가 커져 수익률이 낮아질 수 있다 — 실전 실체결이 이 가정을 교정할 첫 데이터."),
    ("③ 승률 지표의 해석.", "B1은 설계상 승률을 낮추고 손익 구조를 개선하는 패치. 실전 채점은 승률이 아니라 총수익 실현율·손익비·킬스위치 소진율로 한다(절차서 §3)."),
)

# 검증 깔때기 — (라벨, 값, css 색 var). 245는 원장 동적, 나머지는 프로그램 사실.
FUNNEL: Tuple[Tuple[str, str, str], ...] = (
    ("측정 시행 (전량 장부 기록)", "{ledger_total}", "var(--muted)"),
    ("검정된 후보 (조합·셀·가지·온셋)", "400+ 개", "var(--down)"),
    ("통계 관문 통과 (양성 지식)", "3건", "var(--accent)"),
    ("실전 후보로 승격", "1건 (B1)", "var(--up)"),
)

# SOP-M 측정 사이클 9단계 — 실행 계획 정본 §3.
SOP_STEPS: Tuple[Tuple[str, str], ...] = (
    ("① 봉인 확인", "봉인 커밋 존재 + 문서 헤더 '봉인본'·§14 존재 확인"),
    ("② 코드 게이트", "measure_gate.py 로 봉인 문서↔측정 코드 무결성 검사(기동 허용 필수)"),
    ("③ 인자 대조", "봉인 게이트 요건을 CLI --help 와 대조해 인자 완전성 확보"),
    ("④ 분리 기동", "detached_runner 경유(세션 종료에도 생존·체크포인트 재개)"),
    ("⑤ 감시", "batch_watch.py 보고 전용 — 자동 재시작 금지, STALLED/DEAD 원인 규명"),
    ("⑥ 게이트 검수", "산출 게이트 json 전 게이트 pass 확인(하나라도 fail 시 판정 진입 금지)"),
    ("⑦ 원장 기입", "discipline.ledger.append_trial 단일 경로로 시행 계상(분모·행수 규칙 준수)"),
    ("⑧ 산출물 커밋", "md/json 리포트 + 원장 + 핸드오프 갱신을 논리 단위로 커밋"),
    ("⑨ 판정 해석", "수치 기입까지가 집행 몫 — 경계 사례·다음 연구 결정은 봉인 주체(Fable)"),
)

# 창-지위 원장 §1 요약 — (창, 지위, 사용 규칙).
WINDOW_LEDGER: Tuple[Tuple[str, str, str], ...] = (
    ("2022-03-23 ~ 2023-12-31 (437일)", "발견 가용(DISCOVERY)", "모든 측정창 — 발견·프로파일링·판정"),
    ("2024-01-01 ~ 2024-12-31", "조건부/known", "청산 레버·챔피언 선정 계열엔 known — 측정 금지"),
    ("2025-01-01 ~ 2026-02-27", "known/audit (전 방향)", "veto 전용 — 선택·튜닝 금지·blind 주장 금지"),
    ("2026-03 이후", "부재(NONE)", "데이터 없음 — 미래 검증 = 감독형 소액 실전"),
)

CANON_SOURCE = "reports/2026-07-16_b1_program_report.html (결산 v1)"
