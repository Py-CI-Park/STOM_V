"""LLM 메시지 조립 + 코드 블록 추출 (US-003 Phase 1b).

system 메시지는 v1 자산(system_prompt.md + variables_reference.md + forbidden.md)을
이어붙여 만든다. user 메시지는 모델에게 STOM 정규 형태의 매수/매도 전략을 쓰라고
요청한다 (재시도 시 prior_error, US-006용 autopsy_feedback 슬롯 포함).

CRITICAL: 상위 프록시 API는 system 메시지를 필수로 요구한다 (없으면 HTTP 400
"Instructions are required"). build_messages는 항상 system 메시지를 포함한다.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional

# v1 자산 디렉토리 (저장소 고정 위치).
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ASSET_DIR = _REPO_ROOT / "utility" / "ai_agent" / "system_prompt" / "v1"

# system 메시지에 이어붙일 자산 순서 (examples.md는 길어서 system_prompt가 참조로 안내).
_SYSTEM_ASSETS = ("system_prompt.md", "variables_reference.md", "forbidden.md")

_VALID_KINDS = ("buy", "sell")
_VALID_TIMEFRAMES = ("min", "tick")

# ```python ... ``` 또는 ``` ... ``` 코드 펜스 추출.
_FENCE_RE = re.compile(
    r"```(?:python|py)?\s*\n(.*?)```",
    re.DOTALL | re.IGNORECASE,
)


def _read_asset(name: str) -> str:
    path = _ASSET_DIR / name
    return path.read_text(encoding="utf-8")


def _build_system_message() -> str:
    """v1 자산을 이어붙여 system 프롬프트를 만든다."""
    parts: List[str] = []
    for name in _SYSTEM_ASSETS:
        parts.append(f"# ===== {name} =====\n\n{_read_asset(name)}")
    return "\n\n".join(parts)


def _kind_label(kind: str) -> Dict[str, str]:
    """kind별 한글 상태변수/실행함수 라벨."""
    if kind == "buy":
        return {"state": "매수", "action": "self.Buy()", "ko": "매수"}
    return {"state": "매도", "action": "self.Sell()", "ko": "매도"}


def _timeframe_lines(timeframe: str) -> List[str]:
    """타임프레임 전용 변수 지침을 만든다 (min/tick 상호 배타).

    min 엔진에 초당* 같은 TICK 전용 변수를 쓰면 엔진의 exec(buystg)가
    NameError로 죽어 백테스트가 데드락한다(역도 동일). 그래서 모델에게
    해당 타임프레임 변수 계열만 쓰고 반대편 계열은 절대 쓰지 말라고 명시한다.
    """
    if timeframe == "min":
        return [
            "",
            "데이터 형태: **1분봉(min)**. 다음 규칙을 반드시 지켜라:",
            "- 거래량/거래대금/금액은 분당* 계열만 쓴다: "
            "분당매수수량/분당매도수량/분당거래대금/분당매수금액/분당매도금액.",
            "- 분봉 가격(분봉시가/분봉고가/분봉저가)과 보조지표(RSI/MACD/ATR 등)도 사용 가능하다.",
            "- 초당* 계열(초당매수수량/초당매도수량/초당거래대금/초당매수금액/초당매도금액) "
            "TICK 전용 변수는 **절대 쓰지 마라**. 분봉 엔진엔 없어 백테스트가 죽는다. "
            "초당거래대금이 아니라 분당거래대금을 써라.",
            "- 공통 변수(현재가/등락율/체결강도/시가총액/관심종목/시분초)와 "
            "함수형 이름(이동평균()/호가상승압력()/거래대금급증및연속상승() 등)은 그대로 쓴다.",
        ]
    return [
        "",
        "데이터 형태: **1초스냅샷(tick)**. 다음 규칙을 반드시 지켜라:",
        "- 거래량/거래대금/금액은 초당* 계열만 쓴다: "
        "초당매수수량/초당매도수량/초당거래대금/초당매수금액/초당매도금액.",
        "- 분당*/분봉* 계열과 보조지표(RSI/MACD 등 1분봉 전용)는 **절대 쓰지 마라**. "
        "틱 엔진엔 없어 백테스트가 죽는다.",
        "- 공통 변수(현재가/등락율/체결강도/시가총액/관심종목/시분초)와 "
        "함수형 이름(이동평균()/호가상승압력()/거래대금급증및연속상승() 등)은 그대로 쓴다.",
    ]


def build_messages(
    kind: str,
    *,
    timeframe: str = "min",
    base_code: Optional[str] = None,
    autopsy_feedback: Optional[str] = None,
    history_summary: Optional[str] = None,
    prior_error: Optional[str] = None,
) -> List[Dict[str, str]]:
    """OpenAI Chat Completions 메시지 리스트를 만든다.

    Args:
        kind: 'buy' 또는 'sell'.
        timeframe: 'min' 또는 'tick'. 해당 타임프레임 변수 계열만 쓰도록 지시한다.
        base_code: seed-and-refine 출발점. 현재까지 가장 좋은 전략 코드.
            주어지면 fresh 생성 대신 이 코드를 **출발점**으로 부검 피드백을
            반영해 점진 개선(hill-climb)하라고 최우선 지침으로 지시한다.
            None이면 기존 fresh 생성 동작 그대로(하위호환).
        autopsy_feedback: 직전 백테스트 부검 피드백(게이트 거리 + 변별 변수).
        history_summary: 누적 세대 이력 요약(CONVERGENCE). 무엇을 시도했고
            무엇을 회피할지·어느 방향이 graded를 올리는지 알려준다. 첫 세대면 None.
        prior_error: 직전 시도의 compile/token 오류 (재시도 시 모델에 전달).

    Returns:
        [{"role": "system", ...}, {"role": "user", ...}] — 항상 system 포함.

    Raises:
        ValueError: kind가 'buy'/'sell'가 아니거나 timeframe이 'min'/'tick'가 아닐 때.
    """
    if kind not in _VALID_KINDS:
        raise ValueError(f"kind는 {_VALID_KINDS} 중 하나여야 합니다: {kind!r}")
    if timeframe not in _VALID_TIMEFRAMES:
        raise ValueError(f"timeframe은 {_VALID_TIMEFRAMES} 중 하나여야 합니다: {timeframe!r}")

    label = _kind_label(kind)
    system_content = _build_system_message()

    user_lines = [
        f"STOM {label['ko']}전략을 정규 형태로 한 개 작성하라.",
        "",
        "요구 형태:",
        f"- 한글 변수명과 화이트리스트 함수형 이름만 사용한다.",
        f"- `{label['state']} = True` 또는 `{label['state']} = False`로 상태를 시작하고,",
        f"  조건 분기 후 마지막에 반드시 `if {label['state']}: {label['action']}`로 끝낸다.",
        "- import/exec/eval/open/compile/dunder 등 금지 토큰을 절대 쓰지 않는다.",
        "- 설명 없이 ```python 코드 블록 하나만 출력한다.",
    ]
    user_lines += _timeframe_lines(timeframe)

    # seed-and-refine 출발점(최우선 지침): 현재까지 가장 좋은 전략을 출발점으로,
    #   부검 피드백을 반영해 점진 개선(hill-climb)하라고 지시한다. 전면 재작성을
    #   금지하고 핵심 구조를 유지한 채 1~2개 조건만 조정/추가/완화하게 한다.
    #   부검/이력보다 앞에 두어 모델이 "어디서 출발하는지"를 먼저 인지하게 한다.
    if base_code:
        user_lines += [
            "",
            f"아래는 현재까지 가장 좋은 {label['ko']}전략이다. 이것을 **출발점**으로, "
            "부검 피드백을 반영해 **점진적으로 개선**하라. 전면 재작성 금지 — "
            "핵심 구조를 유지하고 1~2개 조건만 조정/추가/완화해 "
            "게이트(거래수/MDD/수익)를 개선하라.",
            f"```python\n{base_code}\n```",
        ]

    # 0거래 낭비 방지(매수 전략): 진입이 한 번도 안 되면 그 세대는 통째로 버려진다.
    #   매수 전략은 "합리적 거래 빈도"를 목표로 하고, 직전 피드백이 0거래를 가리키면
    #   진입 조건을 1~2개의 단순 필터로 줄이라고 명시한다(프롬프트 가이드, 로직 게이팅 없음).
    if kind == "buy":
        user_lines += [
            "",
            "거래 빈도(중요): 진입이 0건이면 그 세대는 평가 불가로 버려진다. "
            "과도하게 좁은 임계값이나 많은 AND 조건으로 진입을 0건으로 만들지 마라. "
            "백테 구간에서 실제로 여러 번 진입이 발생하도록 합리적인 빈도를 목표로 하라.",
        ]
        fb_text = autopsy_feedback or ""
        if ("0건" in fb_text) or ("0거래" in fb_text) or ("거래가" in fb_text and "적" in fb_text):
            user_lines.append(
                "직전 세대가 거래 0건(또는 과소)이었다 → 진입 조건을 1~2개의 단순한 "
                "필터로만 줄여 진입 문턱을 확실히 낮춰라(복합 AND 조건 제거)."
            )

    if history_summary:
        user_lines += [
            "",
            "누적 진화 이력(이전 세대들의 점수/실패 — 같은 실패를 반복하지 말 것):",
            history_summary,
        ]

    if autopsy_feedback:
        user_lines += [
            "",
            "직전 백테스트 부검 피드백(개선 반영):",
            autopsy_feedback,
        ]

    if prior_error:
        user_lines += [
            "",
            "직전 시도가 아래 사유로 거부되었다. 이를 고쳐 다시 작성하라:",
            prior_error,
        ]

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": "\n".join(user_lines)},
    ]


def extract_code(response_text: str) -> str:
    """LLM 응답에서 python 코드 블록을 추출한다.

    ```python ... ``` 또는 ``` ... ``` 펜스만 코드로 인정한다. 펜스가 전혀
    없으면 빈 문자열을 반환한다 — 산문 응답을 통째로 '코드'로 넘기면 생성기의
    compile/token 게이트가 엉뚱한 텍스트를 검사하게 되므로, 차라리 빈 코드로
    돌려 생성기의 재시도 루프가 "코드 블록 없음" 사유로 다시 프롬프트하게 한다.

    Args:
        response_text: LLM 응답 텍스트.

    Returns:
        추출된 코드 문자열 (양끝 공백 제거). 입력이 비거나 펜스가 없으면 빈 문자열.
    """
    if not response_text:
        return ""

    matches = _FENCE_RE.findall(response_text)
    if matches:
        # 가장 긴 블록을 채택 (모델이 여러 블록을 낼 경우 본 전략일 확률↑).
        return max(matches, key=len).strip()

    # 펜스 없음 — 산문 폴백을 쓰지 않는다. 생성기가 재프롬프트하도록 빈 코드 반환.
    return ""
