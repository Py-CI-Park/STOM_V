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
from typing import Dict, List, Optional, Tuple

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


def _report_pattern_lines(kind: str, timeframe: str) -> List[str]:
    """보고서 우수전략(연130~262%·매매성능지수1.25+) 공통 변수패턴/철학 가이드.

    사용자 제공 보고서 19개 우수전략 분석 환류. LLM이 음의 엣지 시드를 벗어나
    보고서급 엣지를 찾도록 변수 '범주'와 운용 철학을 주입한다. 변수 범주만 권하고
    구체 변수명은 timeframe(_timeframe_lines)이 강제한 계열을 따르게 한다 — 분봉(min)
    엔진에 초당* 변수를 강제하면 exec(buystg)가 NameError로 죽어 백테가 데드락하므로,
    여기서는 절대 특정 계열을 못박지 않고 "현재 timeframe 계열을 쓰라"고만 안내한다.
    """
    series = "분당*(분당거래대금/분당매수수량 등)" if timeframe == "min" else "초당*(초당거래대금/초당매수수량 등)"
    if kind == "buy":
        return [
            "",
            "우수 전략 공통 진입 신호(보고서 환류, 연130~262%·매매성능지수1.25+ 전략): "
            "가격(현재가/고가/시가)·거래량·거래대금·등락율·체결강도·시가총액·VI·호가잔량 "
            "범주를 조합해 진입한다. 거래량/거래대금은 반드시 현재 timeframe 계열을 써라"
            f"(지금은 {series}). 다른 계열을 강제하지 마라(가드 위반=백테 죽음).",
            "운용 철학: 유니버스에서 **합리적 빈도**로 진입하라(과선별 금지, 단 0건도 금지). "
            "**다종목 분산 매매를 전제**로 한다 — 한 종목에 과도하게 의존하지 말고 "
            "적정 보유 종목 수(6~12)를 염두에 두고 진입 신호를 설계하라.",
        ]
    return [
        "",
        "우수 전략 청산 패턴(보고서 환류, 매매성능지수1.25+ 전략): "
        "체결강도(및 평균/직전)·이동평균·수익률/최고수익률 범주를 조합해 청산하라. "
        "거래량/거래대금이 필요하면 현재 timeframe 계열만 써라"
        f"(지금은 {series}). 다른 계열을 강제하지 마라(가드 위반=백테 죽음).",
        "운용 철학: **승률보다 매매성능지수(payoff ratio)를 우선**하라 — 목표 payoff≥1.25. "
        "**MDD를 낮게(목표 3~7%대)** 유지하고, 보유 시간은 200~300초 수준을 지향하라. "
        "손실은 빨리 끊고 이익은 관리(트레일링/부분익절)해 손익비를 키워라.",
    ]


def _crossover_lines(label: Dict[str, str], parents: Tuple[str, str]) -> List[str]:
    """crossover(부모 2개 결합) 지침 라인을 만든다 (P2 GA).

    두 부모 전략의 강점을 결합하되 선별성·MDD·수익을 유지하라고 지시한다.
    전면 재작성이 아니라 두 전략에서 잘 통하는 조건들을 조합해 하나의 정규
    전략을 만들게 한다. base_code(단일 mutation) 경로와 상호 배타다.
    """
    parent_a, parent_b = parents
    return [
        "",
        f"아래는 현재까지 좋은 성과를 낸 두 개의 {label['ko']}전략(부모 A, 부모 B)이다. "
        "이 둘의 **강점을 결합(crossover)**해 새로운 정규 전략 하나를 만들어라. "
        "전면 재작성이 아니라 두 전략에서 효과적인 조건/임계값을 골라 조합하라.",
        "결합 원칙: **선별성을 유지하라**(거래 횟수를 크게 늘리지 마라 — 단 0건은 금지). "
        "**MDD(최대낙폭)는 낮추고 총수익은 양(+)으로 유지**해야 한다. 두 부모보다 "
        "과매매가 되지 않도록 진입 조건을 더 엄격한 쪽으로 결합하라.",
        f"=== 부모 A ===\n```python\n{parent_a}\n```",
        f"=== 부모 B ===\n```python\n{parent_b}\n```",
    ]


def build_messages(
    kind: str,
    *,
    timeframe: str = "min",
    base_code: Optional[str] = None,
    crossover_parents: Optional[Tuple[str, str]] = None,
    autopsy_feedback: Optional[str] = None,
    history_summary: Optional[str] = None,
    meta_seed: Optional[str] = None,
    prior_error: Optional[str] = None,
) -> List[Dict[str, str]]:
    """OpenAI Chat Completions 메시지 리스트를 만든다.

    Args:
        kind: 'buy' 또는 'sell'.
        timeframe: 'min' 또는 'tick'. 해당 타임프레임 변수 계열만 쓰도록 지시한다.
        base_code: seed-and-refine 출발점(단일 부모 mutation). 현재까지 가장 좋은
            전략 코드. 주어지면 fresh 생성 대신 이 코드를 **출발점**으로 부검
            피드백을 반영해 점진 개선(hill-climb)하라고 최우선 지침으로 지시한다.
            None이면 기존 fresh 생성 동작 그대로(하위호환).
        crossover_parents: (부모A, 부모B) 두 전략 코드 (P2 GA crossover). 주어지면
            두 전략의 강점을 결합하는 지침을 최우선으로 둔다. base_code(단일 부모
            mutation)와 상호 배타 — crossover_parents가 주어지면 base_code는 무시된다.
            None이면 기존 경로(base_code mutation 또는 fresh)를 그대로 탄다.
        autopsy_feedback: 직전 백테스트 부검 피드백(게이트 거리 + 변별 변수).
        history_summary: 누적 세대 이력 요약(CONVERGENCE). 무엇을 시도했고
            무엇을 회피할지·어느 방향이 graded를 올리는지 알려준다. 첫 세대면 None.
        meta_seed: 누적 메타분석 환류 가이드(P4). 과거 여러 run에서 학습한 "통과
            전략 공통 변수/개선 변경/실패 패턴"을 담은 NL 가이드. config.meta_seed_enabled가
            ON일 때만 주입된다(기본 OFF=None → 하위호환, 기존 프롬프트 불변).
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

    # P2 GA crossover(최우선 지침): 두 부모를 받으면 결합 지침을 먼저 둔다.
    #   crossover와 단일 base_code(mutation)는 상호 배타 — crossover면 base_code 무시.
    if crossover_parents:
        user_lines += _crossover_lines(label, crossover_parents)
        base_code = None  # crossover 경로에선 단일 base 지침을 붙이지 않는다(상호 배타).

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
            "개선 방향: 진입을 **더 선별적으로** 만들어 거래 횟수를 "
            "**늘리지 말고 유지하거나 줄여라**(단 0건은 금지 — 0건이면 평가 불가). "
            "과도한 진입(과매매)은 MDD와 손실을 키운다.",
            "**MDD(최대낙폭)를 낮추는 것**이 핵심 목표다. 단, MDD를 낮추되 익절(상방 "
            "포착)을 죽이지 마라 — give-back(평가익을 토해내는 손실)을 줄여 payoff "
            "ratio(평균이익/평균손실)를 높이는 방향으로 낮춰라. 거래 횟수를 크게 "
            "늘리는 변형은 하지 마라 — 현재 전략의 거래 수준을 넘지 않게 하라. "
            "즉 거래수는 유지 또는 적당히 감소(0 금지), MDD는 익절을 죽이지 않고 낮춰라.",
            "**필수: 총수익을 양수로 유지하라.** MDD만 낮추고 손실이 나는 변형은 "
            "실패다. 낮은 MDD와 **양(+)의 수익**을 동시에 달성해야 한다.",
            "익절 조건(상방 포착)은 함부로 죽이지 말고, **손절/리스크 조건만 조여** "
            "MDD를 낮춰라. 진입 선별성은 손실 거래를 줄이는 방향으로 다듬어라.",
            f"```python\n{base_code}\n```",
        ]

    # 0거래 낭비 방지(매수 전략): 진입이 한 번도 안 되면 그 세대는 통째로 버려진다.
    #   매수 전략은 "합리적 거래 빈도"를 목표로 하고, 직전 피드백이 0거래를 가리키면
    #   진입 조건을 1~2개의 단순 필터로 줄이라고 명시한다(프롬프트 가이드, 로직 게이팅 없음).
    if kind == "buy":
        user_lines += _report_pattern_lines("buy", timeframe)
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

    # 청산 품질(매도 전략): 부검 결과 손실의 대부분이 give-back이고 청산이 승패를
    #   결정하므로, 평가익을 토해내지 않는 청산(트레일링/되돌림/부분익절)과
    #   payoff ratio 개선을 매도 전략의 최우선 지침으로 둔다. 변수는 STOM 정규
    #   화이트리스트(현재가/등락율/시분초/수익률 관련)만 권장한다.
    if kind == "sell":
        user_lines += _report_pattern_lines("sell", timeframe)
        user_lines += [
            "",
            "청산 품질(매우 중요 — 부검 결과): 손실의 70~88%가 give-back이다. "
            "평가익(매수후 최고수익률)을 2~3% 찍고도 청산 로직이 못 잡아 그대로 "
            "토해내며 -2~-3% 손실로 마감한다. 진입 피처는 승패를 예측하지 못하고 "
            "**청산이 승패를 결정**한다 — 매도 전략의 품질이 곧 시스템의 손익이다.",
            "따라서 다음을 지켜라:",
            "- ①평가익을 토해내지 마라: 보유 중 고점(매수후 최고수익률) 대비 일정폭 "
            "되밀리면 청산하라(트레일링/되돌림 청산). 또는 목표 수익 도달 시 "
            "부분/전량 익절로 이익을 **확정**하라.",
            "- ②손절은 너무 느슨하지 않게 하라: 평가익을 냈다가 손실로 마감하는 "
            "give-back을 억제하도록, 일정 손실폭에서 확실히 끊어라.",
            "- ③목표는 payoff ratio(평균이익/평균손실)를 **1.1 이상**으로 끌어올리는 "
            "것이다. 작은 이익을 빨리 확정하고 큰 손실을 막아 이익/손실 비율을 키워라.",
            "- ④[필수] 모든 포지션은 반드시 닫혀야 한다: 트레일링/손절 조건이 "
            "안 걸려도 보유가 무한정 길어지지 않도록 **강제 종료 청산**을 반드시 "
            "포함하라 — 예) `보유시간 > 600: 매도 = True` 또는 `시분초 >= 92700: "
            "매도 = True`(장 시작 후 일정 시간 경과 시 무조건 전량 청산). 닫히지 "
            "않는 포지션이 쌓이면 백테스트가 폭주해 300초 타임아웃으로 그 세대가 "
            "통째로 버려진다. **이것은 가장 흔한 실패 원인이다.**",
            "- ⑤청산 조건은 단순·가볍게: 청산은 보유 종목마다 매 틱 평가되므로, "
            "무거운 함수(다중 이동평균/등락율각도/최저현재가 등)를 남발하지 마라. "
            "핵심 트레일링 1개 + 손절 1개 + 강제 시간청산 1개 수준으로 간결하게 "
            "끝내라. 복잡한 청산식은 백테스트를 느리게 만들어 타임아웃을 유발한다.",
            "- 변수는 STOM 정규 화이트리스트(현재가/등락율/시분초 및 수익률 관련 "
            "변수)만 사용하라.",
        ]

    if history_summary:
        user_lines += [
            "",
            "누적 진화 이력(이전 세대들의 점수/실패 — 같은 실패를 반복하지 말 것):",
            history_summary,
        ]

    # P4 메타 환류(선택 — config.meta_seed_enabled ON일 때만 호출부가 채운다).
    #   과거 여러 run에서 학습한 공통 신호. 현재 run 이력/부검과 조화시키도록 안내한다.
    if meta_seed:
        user_lines += [
            "",
            meta_seed,
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
