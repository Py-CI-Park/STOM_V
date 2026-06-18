"""매도식 계산예산 정적 검사 (PRE-SAVE 가드; 2026-06-10 실측 근거).

배경(원인3, docs/update_log/2026-06-10_condition_research_root_cause_and_plan.md):
warm 틱 백테에서 전략 타임아웃(300초)의 지배 변수는 매수식이 아니라 **매도식**이었다
(11/11 완벽 분리). 매도식은 보유 종목의 모든 틱에서 평가되므로, 비유계 역스캔 함수
(`고가미갱신지속틱수`/`저가미갱신지속틱수` — 마지막 신고가/신저가까지 **당일 이력**을
역방향 스캔)의 비용이 (보유 수×보유 시간×스캔 깊이)로 곱해져 폭발한다. 같은 매수가
스칼라 전용 매도로는 350초 타임아웃→21초가 됐다.

⚠️ 실측 교훈(스펙 주의): 타임아웃된 매도식(S_DYN/S_TREND)은 모두 `보유시간 >= N`
시간 청산을 **가지고 있었는데도** 죽었다 — 스캔 깊이는 보유시간이 아니라 당일 데이터
길이에 비례하기 때문이다. 따라서 "보유시간 상한이 있으면 허용" 같은 조건부 면제는
두지 않고, 매도식에서 비유계 스캔 함수는 **무조건** reject한다(가드 ON일 때).

이 모듈은 LLM 생성 매도 코드를 저장 전에 AST로 정적 검사한다:
  1) 비유계 스캔 함수(고가/저가미갱신지속틱수) 사용 → reject.
  2) 윈도우/구간 집계 함수 호출 수가 상한(max_window_calls)을 넘으면 → reject.

설계 원칙(기존 PRE-SAVE 게이트와 동일):
  - 구조 검사이지 품질 판정이 아니다(R7.4 한계 준수).
  - 토글 OFF(기본)면 호출조차 되지 않아 기존 동작 byte-동일(하위호환).
  - 검사 실패는 reject→prior_error 재시도(맹목 변이 차단)로 이어진다.
"""

from __future__ import annotations

import ast
from typing import Tuple

# 비유계 역스캔 함수: 마지막 신고가/신저가까지 당일 이력을 거슬러 올라간다(O(history)).
# 매도식에서는 보유 틱마다 호출되므로 어떤 형태로든 타임아웃 위험이 실측됐다.
UNBOUNDED_SCAN_FUNCS = frozenset({
    "고가미갱신지속틱수",
    "저가미갱신지속틱수",
})

# 윈도우/구간 집계 함수: 호출당 구간 슬라이스 집계 비용이 든다. N-함수(현재가N 등,
# O(1) 인덱스 참조)는 제외한다. 목록은 trade/base_strategy.py SetGlobalsFunc 등록분 중
# 구간 인자(tick)를 받는 집계·조건 함수들이다.
WINDOW_AGG_FUNCS = frozenset({
    "이동평균", "최고현재가", "최저현재가",
    "체결강도평균", "최고체결강도", "최저체결강도",
    "최고초당매수수량", "최고초당매도수량",
    "누적초당매수수량", "누적초당매도수량", "초당거래대금평균",
    "등락율각도", "당일거래대금각도", "전일비각도",
    "고점기준등락율각도", "저점기준등락율각도",
    "이평지지", "시가지지", "변동성",
    "구간저가대비현재가등락율", "구간고가대비현재가등락율",
    "거래대금평균대비비율", "체결강도평균대비비율", "구간호가총잔량비율",
    "매수수량변동성", "매도수량변동성", "횡보감지",
    "연속상승", "연속하락",
    "가격급등", "가격급락", "거래대금급증", "거래대금급감",
    "체결강도급등", "체결강도급락", "매수수량급증", "매수수량급감",
    "매도수량급증", "매도수량급감", "호가상승압력", "호가하락압력",
    "변동성급증", "변동성급감",
    # 매도 전용 복합 청산 함수(내부적으로 구간 집계를 다수 수행)
    "횡보상태장기보유", "변동성급증_역추세매도", "장기보유종목_동적익절청산",
    "거래대금비율기반_동적청산", "호가압력기반_동적청산", "이평기반_동적청산",
    "변동성기반_동적청산", "변동성급증기반_동적청산",
})


def _called_names(tree: ast.AST) -> list:
    """AST에서 단순 이름 호출(Name(...))의 함수명 리스트를 반환한다."""
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            names.append(node.func.id)
    return names


def check_sell_exec_budget(code: str, *, max_window_calls: int = 8) -> Tuple[bool, str]:
    """매도식 계산예산 정적 검사.

    Args:
        code: 매도 전략 코드 전문.
        max_window_calls: 허용하는 윈도우/구간 집계 함수 호출 수 상한.

    Returns:
        (ok, reason). ok=False면 reason에 reject 사유(재생성 프롬프트용 NL)를 담는다.
        구문 오류 코드는 (True, "") — compile 검증은 별도 게이트(앞 단계)가 담당하므로
        여기서 중복 거부하지 않는다(graceful).
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return True, ""

    called = _called_names(tree)
    unbounded_used = sorted({n for n in called if n in UNBOUNDED_SCAN_FUNCS})
    window_calls = [n for n in called if n in WINDOW_AGG_FUNCS]

    if unbounded_used:
        return False, (
            "매도식 계산예산 위반 — 비유계 스캔 함수("
            + ", ".join(unbounded_used)
            + ")는 매도식에서 금지다. 이 함수는 마지막 신고가/신저가까지 당일 이력을 "
            "역방향 스캔해, 보유 종목의 모든 틱에서 평가되는 매도식과 결합하면 "
            "백테스트가 타임아웃된다(실측: 동일 매수가 350초 타임아웃→스칼라 매도 21초). "
            "스칼라 조건(최고수익률 대비 트레일링·수익률·보유시간·초당매도수량 우위)으로 대체하라."
        )

    if len(window_calls) > max_window_calls:
        return False, (
            f"매도식 계산예산 위반 — 윈도우/구간 집계 함수 호출이 {len(window_calls)}개로 "
            f"상한({max_window_calls}개)을 초과한다. 매도식은 보유 종목의 모든 틱에서 "
            "평가되므로 비싼 호출은 백테스트 타임아웃을 유발한다. 스칼라 조건"
            "(수익률/최고수익률/보유시간/초당매수·매도수량/등락율) 위주로 줄여라."
        )

    return True, ""
