"""T4.3 — 차트술사 구조론 원리 일관성 게이트 (순수 함수, opt-in).

utility/ai_agent/system_prompt/v1/constraints_checklist.md 의 기계 판정 가능
항목 중 조건식 텍스트만으로 결정론 판정이 가능한 부분집합을 구현한다:

  - CSC-07 (reject)  : 매수식에 대응 손절 매도조건 부재 — sell_code 에
                       수익률<-임계 하드 스톱 / 매수가 기준 이탈 / 구조 하단
                       이탈 청산이 하나도 없으면 위반.
  - CSC-06 (reject)  : 거래량/거래대금 조건 없는 돌파성 매수 — buy_code 에
                       최고현재가(...) 돌파 비교가 있는데 거래대금/체결강도/
                       수량 계열 비교 조건이 전혀 없으면 위반.
  - CSC-10 (reject)  : tick 조건식 시간창 09:00~09:30 위반 — tick 매수식의
                       시분초 창이 없거나 93000(09:30)을 넘는 구간을 허용하면
                       위반. tick 매도식에 `시분초 >= X`(90000 < X <= 93000)
                       강제 종료 분기가 없으면 위반 — X > 93000 은 09:30 이후
                       보유 허용이라 무효, X <= 90000 은 상시 참 분기라 무효.
  - PG-META-01 (advisory) : metadata.principle_ids 부재 — 생성물이 어떤 원리
                       (P0~P15)에 근거했는지 표시가 없다는 advisory.

⚠️ 출처 문서(constraints_checklist.md)는 백테스트 미검증 가설 체계에서 유래
한다. 이 게이트가 검사하는 구조 규칙 자체도 '무근거 가설' 라벨을 승계한다 —
검증된 품질 판정기가 아니라, 원리 문서와의 **일관성** 정적 검사다.

설계(liquidity_gate/filter_gate 스타일):
  - 부작용 없는 순수 함수(단위테스트 가능). 코드 텍스트만 본다. 엔진 import 없음.
  - `#` 주석 제거(_strip_comments) 후 정규식/경계 가드로 검사한다.
  - buy_code/sell_code 가 None 이면 해당 코드가 필요한 규칙은 **판정 보류(skip)**
    한다 — generator 는 한 번에 한 kind 만 생성하므로 반대편 코드를 모른다.
    None(모름)과 빈 문자열(존재하지만 비어 있음)을 구분한다.
  - 반환은 {"rule_id", "severity", "message"} dict 리스트. severity 는
    'reject'(저장 거부 대상) | 'advisory'(로그만) 두 값이다.

향후 배선 지점(노트): brain/prompt.py 의 validate_research_candidate_response
는 프롬프트 계약 테스트가 보호하므로 이번에 손대지 않는다. 후속 Phase 에서
연구 후보 응답 검증 체인에 이 함수를 독립 단계로 추가할 수 있다.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional

# liquidity_gate 의 검출 보조를 재사용(동일 의미 — 주석 제거 + 부등호 검출).
from ai_strategy_loop.brain.filter_gate import time_window_bounds
from ai_strategy_loop.brain.liquidity_gate import _COMPARISON_RE, _strip_comments

# 반환 위반 항목 타입(문서화용 별칭) — {"rule_id", "severity", "message"}.
Violation = Dict[str, str]

SEVERITY_REJECT = "reject"
SEVERITY_ADVISORY = "advisory"

# 한글/영숫자 식별자 경계 가드 — `수익률` 이 `최고수익률`/`최저수익률` 의
#   부분문자열로 매칭되는 것을 막는다(변수명 오염 방지).
_B_LEFT = r"(?<![가-힣A-Za-z0-9_])"
_B_RIGHT = r"(?![가-힣A-Za-z0-9_])"
_NUM = r"\d+(?:\.\d+)?"

# --- CSC-07: 손절로 인정하는 패턴(매도식) ---
#   ①수익률 <= -k 하드 스톱(역방향 -k >= 수익률 포함) ②매수가 기준 이탈
#   ③구조 하단(최저현재가) 이탈 ④중간변수 경유 구조 하단 이탈
#     (`현재가 < 도지하단*0.997` — '하단' 으로 끝나는 한글 변수)
#   ⑤하단이탈율 계열(`하단이탈율 <= -0.25`) ⑥self.vars 하드 스톱
#     (`수익률 <= self.vars[20]` — 음수 기본값 관용구, idiom_dictionary §10).
#   constraints_checklist.md CSC-07 의 인정 목록("구조 하단 이탈 청산" 포함).
_STOP_LOSS_RES = (
    re.compile(rf"{_B_LEFT}수익률{_B_RIGHT}\s*<=?\s*-"),
    re.compile(rf"-{_NUM}\s*>=?\s*{_B_LEFT}수익률{_B_RIGHT}"),
    re.compile(rf"{_B_LEFT}현재가{_B_RIGHT}\s*<=?\s*매수가"),
    re.compile(rf"{_B_LEFT}현재가{_B_RIGHT}\s*<=?\s*최저현재가"),
    re.compile(rf"{_B_LEFT}현재가{_B_RIGHT}\s*<=?\s*[가-힣A-Za-z0-9_]*하단{_B_RIGHT}"),
    re.compile(rf"[가-힣A-Za-z0-9_]*이탈율{_B_RIGHT}\s*<=?\s*-{_NUM}"),
    re.compile(rf"{_B_LEFT}수익률{_B_RIGHT}\s*<=?\s*self\.vars\[\d+\]"),
)

# --- CSC-06: 돌파성 매수 판정 + 거래량/거래대금 계열 토큰 ---
#   돌파성 = 최고현재가(...) 비교(현재가 vs 과거 최고가 갱신형)가 비교 연산과
#   함께 등장. 거래량 조건으로 인정하는 토큰은 checklist CSC-06 예시를 따른다
#   ("거래대금" 부분일치는 초당/분당/당일거래대금·각도·증감 전 계열을 덮는다).
_BREAKOUT_TOKEN = "최고현재가"
_VOLUME_TOKENS = (
    "거래대금",  # 초당/분당/당일거래대금(+평균/각도/증감) 전 계열 부분일치
    "체결강도",
    "거래량",
    "초당매수수량", "초당매도수량",
    "분당매수수량", "분당매도수량",
)

# --- CSC-10: tick 시간창 경계(HHMMSS). 09:00~09:30 은 원문 §10 의 tick 시스템
#   정의 자체이므로 시간창 '경계값'은 가설 라벨 대상이 아니다(checklist 서두). ---
_TICK_WINDOW_LO = 90000
_TICK_WINDOW_HI = 93000

# tick 매도식 강제 종료 분기: `시분초 >= X`(또는 `X <= 시분초`) 꼴.
#   유효 임계값은 90000 < X <= 93000 — 조기청산(예: 92000=09:20)은 09:30 이내
#   청산을 보장하므로 유효, X > 93000(예: 152000)은 09:30 이후 보유 허용이라
#   무효, X <= 90000 은 세션 내 상시 참이라 강제 종료 분기로 무의미.
_TIME_BOUNDARY = r"(?![가-힣A-Za-z0-9_])"
_SELL_CLOSE_LEFT_RE = re.compile(rf"시분초{_TIME_BOUNDARY}\s*>=?\s*({_NUM})")
_SELL_CLOSE_RIGHT_RE = re.compile(rf"({_NUM})\s*<=?\s*시분초{_TIME_BOUNDARY}")


def _has_stop_loss(sell_code: str) -> bool:
    """매도식에 손절 분기(하드 스톱/매수가 이탈/구조 하단 이탈)가 있는지 검사."""
    stripped = _strip_comments(sell_code)
    return any(p.search(stripped) for p in _STOP_LOSS_RES)


def _is_breakout_buy(buy_code: str) -> bool:
    """매수식이 돌파성(최고현재가 비교 포함)인지 검사(주석 제외·비교 문맥 필수)."""
    stripped = _strip_comments(buy_code)
    for line in stripped.splitlines():
        if _BREAKOUT_TOKEN in line and _COMPARISON_RE.search(line):
            return True
    return False


def _has_volume_condition(buy_code: str) -> bool:
    """매수식에 거래량/거래대금/체결강도/수량 계열 비교 조건이 있는지 검사."""
    stripped = _strip_comments(buy_code)
    for line in stripped.splitlines():
        if not _COMPARISON_RE.search(line):
            continue
        if any(tok in line for tok in _VOLUME_TOKENS):
            return True
    return False


def _has_session_close_exit(sell_code: str) -> bool:
    """tick 매도식에 유효한 강제 종료 분기(`시분초 >= X`, 90000 < X <= 93000)가 있는지 검사.

    임계값 X 가 93000(09:30)을 넘으면(예: 152000) 09:30 이후 보유를 허용하는
    분기이므로 무효, 90000 이하면 세션 내 상시 참이라 무효. 90000 < X <= 93000
    조기청산(예: 92000=09:20)은 09:30 이내 청산을 보장하므로 유효로 인정한다.
    """
    stripped = _strip_comments(sell_code)
    for m in _SELL_CLOSE_LEFT_RE.finditer(stripped):
        if _TICK_WINDOW_LO < int(float(m.group(1))) <= _TICK_WINDOW_HI:
            return True
    for m in _SELL_CLOSE_RIGHT_RE.finditer(stripped):
        if _TICK_WINDOW_LO < int(float(m.group(1))) <= _TICK_WINDOW_HI:
            return True
    return False


def _check_csc06(buy_code: Optional[str]) -> List[Violation]:
    """CSC-06 — 거래량/거래대금 조건 없는 돌파성 매수 (reject)."""
    if buy_code is None or not buy_code.strip():
        return []  # 매수식 모름/없음 → 판정 보류.
    if _is_breakout_buy(buy_code) and not _has_volume_condition(buy_code):
        return [{
            "rule_id": "CSC-06",
            "severity": SEVERITY_REJECT,
            "message": (
                "돌파성 매수(최고현재가 비교)에 거래량/거래대금 조건이 없다 — "
                "초당·분당거래대금(평균 비율)·당일거래대금 하한·체결강도 등 "
                "사건거래대금 확인 조건을 함께 두어라."
            ),
        }]
    return []


def _check_csc07(buy_code: Optional[str], sell_code: Optional[str]) -> List[Violation]:
    """CSC-07 — 매수식에 대응 손절 매도조건 부재 (reject).

    sell_code=None(모름)이면 판정 보류. sell_code 가 주어졌는데(빈 문자열 포함)
    손절 분기가 없으면 위반 — 매수식 존재 여부와 무관하게 매도식 단독으로
    판정 가능하다(모든 매도식은 손절 경로를 가져야 한다).
    """
    if sell_code is None:
        return []  # 매도식 모름 → 판정 보류(반대편 코드 없이 판정 불가).
    if not _has_stop_loss(sell_code):
        return [{
            "rule_id": "CSC-07",
            "severity": SEVERITY_REJECT,
            "message": (
                "매수식에 대응하는 손절 매도조건이 없다 — 수익률 <= -k 하드 스톱, "
                "매수가 기준 이탈(현재가 < 매수가*k), 구조 하단 이탈 중 최소 1개를 "
                "매도식에 두어라."
            ),
        }]
    return []


def _check_csc10(
    buy_code: Optional[str],
    sell_code: Optional[str],
    timeframe: Optional[str],
) -> List[Violation]:
    """CSC-10 — tick 조건식 시간창 09:00~09:30 강제 (reject).

    timeframe != 'tick'(min/모름)이면 판정 보류. tick 매수식은 시분초 창이
    [90000, 93000] 이내여야 한다: 시간 게이트 없음·상한 없음·상한>93000·
    하한<90000 이면 위반(하한 없음은 세션이 09:00 에 시작하므로 허용 — 판정
    기준의 세부 해석은 무근거 가설 라벨 승계). tick 매도식은 `시분초 >= X`
    (90000 < X <= 93000) 강제 종료 분기가 없으면 위반.
    """
    if timeframe != "tick":
        return []
    violations: List[Violation] = []
    if buy_code is not None and buy_code.strip():
        bounds = time_window_bounds(buy_code)
        lo, hi = bounds if bounds is not None else (None, None)
        out_of_window = (
            bounds is None
            or hi is None
            or hi > _TICK_WINDOW_HI
            or (lo is not None and lo < _TICK_WINDOW_LO)
        )
        if out_of_window:
            violations.append({
                "rule_id": "CSC-10",
                "severity": SEVERITY_REJECT,
                "message": (
                    "tick 매수식의 시간창이 09:00~09:30 밖이다 — "
                    "90000 <= 시분초 < 93000(또는 그 이내) 필터를 두고 "
                    "93000 초과 구간을 허용하지 마라."
                ),
            })
    if sell_code is not None and sell_code.strip():
        if not _has_session_close_exit(sell_code):
            violations.append({
                "rule_id": "CSC-10",
                "severity": SEVERITY_REJECT,
                "message": (
                    "tick 매도식에 유효한 강제 종료 분기(시분초 >= X, "
                    "90000 < X <= 93000)가 없다 — 늦어도 09:30 도달 시 "
                    "잔여 포지션을 청산하는 분기를 두어라(93000 초과 임계값은 "
                    "09:30 이후 보유 허용이라 무효)."
                ),
            })
    return violations


def _check_meta(metadata: Optional[Mapping[str, Any]]) -> List[Violation]:
    """PG-META-01 — metadata.principle_ids 부재 (advisory)."""
    principle_ids = None if metadata is None else metadata.get("principle_ids")
    if not principle_ids:
        return [{
            "rule_id": "PG-META-01",
            "severity": SEVERITY_ADVISORY,
            "message": (
                "metadata.principle_ids 가 없다 — 이 조건식이 근거한 원리(P0~P15, "
                "utility/ai_agent/system_prompt/v1/principles.md)를 표시하라(advisory)."
            ),
        }]
    return []


def check_principle_consistency(
    buy_code: Optional[str],
    sell_code: Optional[str] = None,
    metadata: Optional[Mapping[str, Any]] = None,
) -> List[Violation]:
    """조건식 쌍(buy/sell)과 metadata 의 원리 일관성 위반 목록을 돌려준다.

    순수 함수 — 코드 텍스트/metadata 만 보고, 부작용·엔진 import 가 없다.
    None 인 코드가 필요한 규칙은 판정 보류(skip)하므로, 한쪽 kind 만 아는
    generator 배선에서도 안전하다.

    Args:
        buy_code: 매수 조건식 텍스트(모르면 None).
        sell_code: 매도 조건식 텍스트(모르면 None).
        metadata: {'timeframe': 'tick'|'min', 'principle_ids': [...], ...} 등
            부가 정보(없으면 None). timeframe 이 'tick' 일 때만 CSC-10 을 판정.

    Returns:
        위반 목록. 각 항목은 {"rule_id", "severity", "message"} 이며 severity 는
        'reject' | 'advisory'. 위반이 없으면 빈 리스트.
    """
    timeframe = None if metadata is None else metadata.get("timeframe")
    violations: List[Violation] = []
    violations.extend(_check_csc06(buy_code))
    violations.extend(_check_csc07(buy_code, sell_code))
    violations.extend(_check_csc10(buy_code, sell_code, timeframe))
    violations.extend(_check_meta(metadata))
    return violations
