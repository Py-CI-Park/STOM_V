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


def _report_pattern_lines(
    kind: str,
    timeframe: str,
    target_daily_trades: Optional[float] = None,
) -> List[str]:
    """보고서 우수전략(연130~262%·매매성능지수1.25+) 공통 변수패턴/철학 가이드.

    사용자 제공 보고서 19개 우수전략 분석 환류. LLM이 음의 엣지 시드를 벗어나
    보고서급 엣지를 찾도록 변수 '범주'와 운용 철학을 주입한다. 변수 범주만 권하고
    구체 변수명은 timeframe(_timeframe_lines)이 강제한 계열을 따르게 한다 — 분봉(min)
    엔진에 초당* 변수를 강제하면 exec(buystg)가 NameError로 죽어 백테가 데드락하므로,
    여기서는 절대 특정 계열을 못박지 않고 "현재 timeframe 계열을 쓰라"고만 안내한다.

    target_daily_trades가 주어지면(buy) "적정 보유 종목 수(6~12)" 문구에 분산-기반
    고빈도 산식을 덧붙인다 — "6~12종목 × 종목당 일평균 1.5~2회 ≈ 일평균 {target}회".
    None이면 기존 문구 그대로(하위호환). 이 함수는 fresh·base_code 양 경로 공용이라
    한 곳 수정으로 양쪽이 정렬된다.
    """
    series = "분당*(분당거래대금/분당매수수량 등)" if timeframe == "min" else "초당*(초당거래대금/초당매수수량 등)"
    if kind == "buy":
        philosophy = (
            "운용 철학: 유니버스에서 **합리적 빈도**로 진입하라(과선별 금지, 단 0건도 금지). "
            "**다종목 분산 매매를 전제**로 한다 — 한 종목에 과도하게 의존하지 말고 "
            "적정 보유 종목 수(6~12)를 염두에 두고 진입 신호를 설계하라."
        )
        if target_daily_trades is not None:
            philosophy += (
                f" (6~12종목 × 종목당 일평균 1.5~2회 ≈ 일평균 {target_daily_trades:.4g}회)"
            )
        return [
            "",
            "우수 전략 공통 진입 신호(보고서 환류, 연130~262%·매매성능지수1.25+ 전략): "
            "가격(현재가/고가/시가)·거래량·거래대금·등락율·체결강도·시가총액·VI·호가잔량 "
            "범주를 조합해 진입한다. 거래량/거래대금은 반드시 현재 timeframe 계열을 써라"
            f"(지금은 {series}). 다른 계열을 강제하지 마라(가드 위반=백테 죽음).",
            philosophy,
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
    dispersion_prompt_enabled: bool = False,
    target_daily_trades: Optional[float] = None,
    mdd_control_enabled: bool = False,
    exit_edge_feedback_enabled: bool = False,
    encourage_time_dispersion: bool = False,
    require_filter_gates: bool = False,
    classification_generation_enabled: bool = False,
    hypothesis_feedback: Optional[str] = None,
    few_shot_examples: Optional[List[str]] = None,
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
        dispersion_prompt_enabled: True면(매수 seed-refine 경로) 저빈도 압력 문장을
            다종목 분산매매 유도 문장으로 치환하고, 매수 "거래 빈도" 블록 뒤에 단일
            종목 과발화 억제 한 줄을 더한다. 기본 False면 기존 프롬프트가 byte-동일
            유지된다(하위호환). 분산은 매수 의미가 크므로 매도 경로엔 영향이 없다.
        target_daily_trades: 프롬프트 산식 노출용 목표 일평균거래수. 주어지면
            _report_pattern_lines(buy)에 "6~12종목 × 종목당 일평균 1.5~2회 ≈ 일평균
            {target}회" 산식을 덧붙인다. None이면 기존 문구 그대로(하위호환).
        mdd_control_enabled: True면(매도 경로) 기존 청산 지침에 더해 MDD 억제 최우선
            블록(타이트 손절·트레일링·시간 손절·손실구간 신규노출 자제)을 매도
            프롬프트에 추가한다. kind=='sell'일 때만 반영되며 매수(buy)엔 영향이 없다.
            기본 False면 이 블록이 미추가되어 출력이 byte-동일 유지된다(하위호환).
        exit_edge_feedback_enabled: True면(매도 경로) edge_ratio 부검 발견(손실 MAE가
            승리 대비 ~2.6배 깊음 · 최고 평가익의 ~20%만 실현)을 가르치는 블록을 기존
            청산 지침에 더해 매도 프롬프트에 추가한다 — 진입 엣지는 있으니 손익을
            가르는 건 청산 품질임을 명시하고, 손실은 얕고 빠르게 끊고 이익은 고점
            근처에서 확정하도록 유도한다. kind=='sell'일 때만 반영되며 매수(buy)엔
            영향이 없다. 기본 False면 미추가되어 출력이 byte-동일 유지된다(하위호환).
        encourage_time_dispersion: True면(매수 경로) 진입 시점을 09:00~09:20 시초
            구간에 분산하라는 소프트 가이드 한 줄을 매수 프롬프트에 추가한다(Phase
            C-3). 시간 분산은 정적 탐지가 불가하므로 reject 게이트가 아닌 프롬프트
            넛지 전용이다. kind=='buy'일 때만 반영되며 매도(sell)엔 영향이 없다.
            기본 False면 이 줄이 미추가되어 출력이 byte-동일 유지된다(하위호환).
        require_filter_gates: True면(매수 경로) 시드 게이팅 구조(시총·가격/등락율
            밴드·당일거래대금 바닥+각도·체결강도·호가압력·시초 시간창 등을 AND로
            충분히 결합)를 가르치는 과발화 방지 가이드 블록을 매수 프롬프트에
            추가한다(생성 품질 (A)). kind=='buy'일 때만 반영되며 매도(sell)엔 영향이
            없다. 게이트(reject) 자체는 generate_strategy가 수행하고, 여기서는 그에
            맞춰 LLM을 유도하는 프롬프트 역할이다. 기본 False면 이 블록이 미추가되어
            출력이 byte-동일 유지된다(하위호환).
        classification_generation_enabled: True면(매수 경로) 3개 분류축(①시가총액 구분
            ②등락률 구분 ③넓은 시간창 09:00~09:30)에서 매 세대 일관된 니치를 의도적으로
            선택해 설계하라는 블록을 매수 프롬프트에 추가한다. require_filter_gates(범주 폭
            게이트)와 짝 — 넓게 고르되(축 선택) 좁게 게이트하라(니치 내 선별). require_filter_gates
            블록 뒤에 배치된다. kind=='buy'일 때만 반영되며 매도(sell)엔 영향이 없다. 기본
            False면 이 블록이 미추가되어 출력이 byte-동일 유지된다(하위호환).
        hypothesis_feedback: 직전 세대의 판정된 가정 환류 문자열(P2b-1). 특히 **기각**
            가정을 강조해 "이 방향은 효과 없었으니 다른 레버로 접근하라"고 알린다.
            autopsy_feedback 슬롯보다 **먼저(상위)** 주입돼 "이전에 틀린 방향" 경고가
            부검 피드백보다 우선 보이게 한다. None/빈 문자열이면 미주입되어 출력이
            기존과 byte-동일하다(하위호환). 호출부(controller.loop)가 토글 ON일 때만 채운다.
        few_shot_examples: 검증된 우수 전략 few-shot 코드 샘플 리스트(#67). 주어지면
            user 메시지 끝부분에 "구조/게이팅을 학습하되 변수값·조건을 그대로 복제하지
            말라"는 헤더(§3.14 과적합 방지)와 함께 각 샘플을 코드펜스로 주입한다. 부검·
            가드레일 슬롯과 조화시키되 중복 강조는 피한다. None이거나 빈 리스트면 미주입
            되어 출력이 기존과 byte-동일하다(하위호환). 호출부가 토글 ON일 때만 채운다.

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
        # 저빈도 압력 문장(개선 방향 + MDD 라인의 거래-억제 절)을 분산매매 토글로
        #   분기한다. OFF(기본)면 기존 문장 byte-동일 유지(하위호환). ON(매수)이면
        #   종목당 발화↓·종목 수↑로 분산 진입하라는 취지로 치환한다.
        if dispersion_prompt_enabled and kind == "buy":
            direction_line = (
                "개선 방향: 한 종목에서 같은 봉/짧은 구간에 매수가 연속 과발화하지 "
                "않게 진입 조건을 다듬되(직전 대비 새 돌파/급증이 성립한 순간에만 진입), "
                "진입 자격 종목 폭을 넓혀 서로 다른 다수 종목(동시보유 6~12 지향)에서 "
                "각 1~2회씩 분산 진입하라. 종목당 발화는 줄이고 종목 수를 늘려 총 "
                "진입을 늘려라 — 과매매가 아니라 분산매매다."
            )
            mdd_line = (
                "**MDD(최대낙폭)를 낮추는 것**이 핵심 목표다. 단, MDD를 낮추되 익절(상방 "
                "포착)을 죽이지 마라 — give-back(평가익을 토해내는 손실)을 줄여 payoff "
                "ratio(평균이익/평균손실)를 높이는 방향으로 낮춰라. "
                "진입 시간대를 09:00 직후 몇 분에 가두지 말고 유니버스 시간창 전반"
                "(예: 09:00~09:30)에 분산하라. 단, 흑자의 핵심인 유동성 게이트"
                "(당일거래대금 절대 바닥, 당일거래대금각도 같은 거래대금 가속 윈도우)는 "
                "반드시 유지하고 삭제·완화하지 마라 — 이 게이트를 빼서 빈도를 올리면 "
                "흑자가 깨진다."
            )
        else:
            direction_line = (
                "개선 방향: 진입을 **더 선별적으로** 만들어 거래 횟수를 "
                "**늘리지 말고 유지하거나 줄여라**(단 0건은 금지 — 0건이면 평가 불가). "
                "과도한 진입(과매매)은 MDD와 손실을 키운다."
            )
            mdd_line = (
                "**MDD(최대낙폭)를 낮추는 것**이 핵심 목표다. 단, MDD를 낮추되 익절(상방 "
                "포착)을 죽이지 마라 — give-back(평가익을 토해내는 손실)을 줄여 payoff "
                "ratio(평균이익/평균손실)를 높이는 방향으로 낮춰라. 거래 횟수를 크게 "
                "늘리는 변형은 하지 마라 — 현재 전략의 거래 수준을 넘지 않게 하라. "
                "즉 거래수는 유지 또는 적당히 감소(0 금지), MDD는 익절을 죽이지 않고 낮춰라."
            )
        user_lines += [
            "",
            f"아래는 현재까지 가장 좋은 {label['ko']}전략이다. 이것을 **출발점**으로, "
            "부검 피드백을 반영해 **점진적으로 개선**하라. 전면 재작성 금지 — "
            "핵심 구조를 유지하고 1~2개 조건만 조정/추가/완화해 "
            "게이트(거래수/MDD/수익)를 개선하라.",
            direction_line,
            mdd_line,
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
        user_lines += _report_pattern_lines("buy", timeframe, target_daily_trades)
        user_lines += [
            "",
            "거래 빈도(중요): 진입이 0건이면 그 세대는 평가 불가로 버려진다. "
            "과도하게 좁은 임계값이나 많은 AND 조건으로 진입을 0건으로 만들지 마라. "
            "백테 구간에서 실제로 여러 번 진입이 발생하도록 합리적인 빈도를 목표로 하라.",
        ]
        # 생성 품질 (A) 필터 게이팅 가이드(매수 전용 토글): 시드 우수전략의 정의적
        #   특성인 "여러 필터 범주를 AND로 충분히 결합"을 가르쳐 과발화를 막는다.
        #   generate_strategy의 require_filter_gates reject 게이트와 짝을 이루는
        #   프롬프트 측 유도다. OFF(기본)면 미추가(byte 보존).
        if require_filter_gates:
            user_lines.append(
                "필터 게이팅(매우 중요 — 과발화 방지): 매수 진입은 아래 필터 범주를 "
                "**여러 개 AND로 충분히 결합**해야 한다(시드 우수전략의 정의적 특성). "
                "단일/느슨한 조건, OR 결합, 항상참(예 현재가>0)은 과발화→손실/타임아웃이다.\n"
                "- 시가총액 밴드(예: 시가총액 < N)\n"
                "- 가격·등락율 밴드(현재가 범위, 등락율/시가등락율/시가대비등락율 범위)\n"
                "- 당일거래대금 절대 바닥 + 당일거래대금각도(유동성·가속)\n"
                "- 초당거래대금 급증비율(초당거래대금/초당거래대금평균 > 배수) — 신선 이벤트\n"
                "- 체결강도 범위(예: 50~300)\n"
                "- 호가/체결 압력(매도총잔량·매수총잔량·초당매수수량 비교)\n"
                "- 시초 시간창(시분초로 09:00~09:05 같은 구간 한정)\n"
                "진입은 돌파/급증 이벤트가 성립한 순간에만 — 매 틱 항상 참이 되지 않게 하라."
            )
        # 생성 분류축 유도(매수 전용 토글): 시드 5분 고착을 깨고 인간 고수처럼 시총 티어·
        #   등락률 국면·넓은 시초 시간창(09:00~09:30, tick 데이터 상한)에서 먼저 니치를 고르도록 유도한다.
        #   require_filter_gates(범주 폭 구조 게이트)와 짝 — 넓게 고르되 좁게 게이트하라.
        #   require_filter_gates 블록 뒤에 배치된다. OFF(기본)면 미추가(byte 보존).
        if classification_generation_enabled:
            user_lines.append(
                "전략 설계 분류축(매우 중요 — 넓은 탐색): 이 매수 전략을 아래 3개 분류축에서 "
                "**하나의 일관된 니치(조합)**를 의도적으로 선택해 설계하라. 매 세대 서로 다른 "
                "조합을 시도해 탐색 공간을 넓혀라(획일적 반복 금지).\n"
                "- ①시가총액 구분: 초대형/대형/중형/소형/초소형 중 한 티어를 고르고 시가총액을 "
                "그 밴드로 게이트하라(예: 중소형 = 1000억~5000억). 티어마다 변동성·유동성·수급이 "
                "다르니 진입 조건을 그 티어에 맞춰라.\n"
                "- ②등락률 구분: 진입 시점의 등락 국면을 한 가지로 정하라 — 갭상승 초입(시가등락율 "
                "+0~5%)·강세 지속(등락율 +5~15%)·급등 후 눌림 반등 등. 등락율/시가등락율/"
                "시가대비등락율을 조합해 그 국면만 포착하라.\n"
                "- ③시간대 구분(넓게): 시간창을 09:00~09:05 한 점에 고정하지 마라. 시초 전체 "
                "구간(09:00~09:30, tick 데이터 상한)에서 한 시간대를 의도적으로 선택하라 — 시초 급등"
                "(09:00~09:05)·안정화(09:05~09:15)·후반(09:15~09:30). 고른 시간대의 수급 특성에 맞춰 진입하라.\n"
                "세 축에서 고른 니치 안에서 위 필터 게이팅(여러 범주 AND)을 촘촘히 적용하라 — "
                "넓게 고르되(축 선택) 좁게 게이트하라(니치 내 선별). 이렇게 해야 다양한 시총·"
                "등락국면·시간대의 우상향 엣지를 탐색할 수 있다."
            )
        # 분산매매 토글 ON: 단일 종목 과발화(매 틱/봉 항상참 임계로 매수=True 연발)를
        #   억제하라는 한 줄을 더한다. OFF면 미추가(byte 보존).
        if dispersion_prompt_enabled:
            user_lines.append(
                "단일 종목 과발화 억제 — 현재가>0 같은 항상참 임계로 매 틱 매수=True를 "
                "켜지 마라. 새 돌파/급증 이벤트가 성립한 순간에만 진입하라."
            )
        # Phase C-3 시간 분산 넛지(매수 전용 토글): 진입 시점을 09:00~09:20 시초
        #   구간에 분산하라는 소프트 가이드 한 줄. 정적 탐지 불가라 reject 게이트가
        #   아닌 프롬프트 넛지 전용이다. OFF면 미추가(byte 보존).
        if encourage_time_dispersion:
            user_lines.append(
                "진입 시점을 09:00~09:20 구간에 분산하라 — 단일 분(예: 09:02)에만 "
                "집중하지 말고 시초 20분 내 여러 시간대 조건을 고려하라(시분초/시간 "
                "조건을 한 점에 고정하지 말 것)."
            )
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
        # Track B 3차 MDD 제어 강화(매도 전용 토글): 기존 청산 지침에 더해 MDD 억제를
        #   최우선 목표로 못박는다. OFF(기본)면 이 블록을 미추가해 출력이 byte-동일하다.
        #   타임프레임 가드 준수 — 변수명을 못박지 않고 "수익률/최고수익률/보유" 같은
        #   범주만 권해 분봉/틱 어느 계열도 깨지 않는다.
        if mdd_control_enabled:
            user_lines += [
                "",
                "★MDD 억제 최우선(Track B 3차): 이 전략의 최대낙폭(MDD)을 게이트 상한 "
                "이내로 억제하라. 위 청산 지침과 충돌하지 않게 더 강하게 적용한다:",
                "- ①손절을 타이트하게 — 손실이 커지기 전 빠르게 청산하라"
                "(예: 수익률 <= -2.0 이면 즉시 매도).",
                "- ②트레일링 청산 — 최고수익률 도달 후 일정 폭을 되돌리면 즉시 청산해 "
                "이익 반납(give-back)을 막아라.",
                "- ③시간 손절 — 보유가 길어지면 강제 청산하라(앞의 강제 종료 청산과 "
                "동일 취지를 더 짧은 보유로 적용).",
                "- ④손실 구간에서는 신규 노출을 늘리지 마라 — 동시에 여러 포지션이 "
                "함께 물리지 않도록 한다.",
                "- ⑤[핵심·인간 우수전략의 정의적 청산] 체결강도 페이드 청산: 매수세가 "
                "꺾이는 순간을 체결강도(및 직전/평균)로 감지해 즉시 청산하라 — 체결강도가 "
                "직전 대비 떨어지거나 일정 임계 아래로 내려가면(매수 모멘텀 약화) 청산. "
                "보고서 19개 우수전략 중 18개가 매도에 체결강도 계열을 쓰며, 이것이 "
                "낮은 MDD(1.9~6.75%)를 만든 핵심 레버다. 고점을 토해내기 전에 모멘텀 "
                "꺾임에서 먼저 빠져나오는 것이 give-back을 막는 최선이다.",
                "- ⑥추세이탈 청산(보조): 현재가가 이동평균(현재 timeframe 계열) 아래로 "
                "이탈하거나 직전 대비 추세가 꺾이면 청산해 추세 붕괴 손실을 막아라.",
                "목표는 높은 수익이 아니라 '낮고 안정적인 MDD'다.",
            ]
        # 청산 효율 환류(매도 전용 토글): edge_ratio 부검 발견을 청산 프롬프트에 환류한다.
        #   진입 엣지는 존재(edge_ratio≈1.54)하나 mae_efficiency≈0.20(최고익의 ~20%만
        #   실현)·손실 MAE가 승리 대비 ~2.6배 깊음 → 손익을 가르는 건 청산. OFF(기본)면
        #   이 블록을 미추가해 출력이 byte-동일하다. 타임프레임 가드 준수 — 변수명을
        #   못박지 않고 수익률/매수후최고수익률/매수후최저수익률 범주만 권해 분봉/틱
        #   어느 계열도 깨지 않는다.
        # Exit-efficiency feedback (sell-only toggle): feed the edge_ratio autopsy
        #   finding into the exit prompt — entry has edge, exit quality decides P/L.
        if exit_edge_feedback_enabled:
            user_lines += [
                "",
                "★청산 효율 환류(부검 edge_ratio): 데이터상 ①손실거래가 승리거래보다 약 2.6배 깊게 "
                "역행한다(손실을 오래 끌어 깊은 손실 MAE를 허용) ②최고평가익의 약 20%만 실현하고 80%를 "
                "반납한다. 진입 엣지는 존재하므로(평가익 > 역행) 손익을 가르는 건 *청산 품질*이다. 따라서:\n"
                "- ①손실 측(비대칭 역행 차단): 매수후최저수익률(역행)이 일정폭(예: -1.5~-2%)을 넘으면 *즉시* "
                "손절하라 — 손실거래가 승리거래보다 깊어지게 두지 마라. 손실 MAE를 승리 수준으로 타이트하게.\n"
                "- ②이익 측(평가익 반납 차단): 매수후최고수익률 대비 일정폭 되돌리면 *즉시* 트레일 익절하라 — "
                "최고평가익의 더 큰 비율을 확정해 mae_efficiency를 올려라(80% 반납 → 줄이기).\n"
                "목표: 손실은 얕고 빠르게, 이익은 고점 근처에서 확정. 승리·손실 MAE 비대칭을 줄이는 것이 핵심."
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

    # P2b-1 가정 환류(선택 — 토글 ON일 때만 호출부가 채운다). 부검 피드백보다 **먼저**
    #   둬 "이전에 틀린 방향" 경고를 우선 노출한다. None/빈 문자열이면 미주입(byte-동일).
    if hypothesis_feedback:
        user_lines += [
            "",
            hypothesis_feedback,
        ]

    if autopsy_feedback:
        user_lines += [
            "",
            "직전 백테스트 부검 피드백(개선 반영):",
            autopsy_feedback,
        ]

    # few-shot 우수 전략 샘플(#67 — 선택, 호출부 토글 ON일 때만 채운다). 검증된
    #   전략의 변수 조합·다중 필터 AND 게이팅 **구조**를 학습시키되, §3.14(시드 지문
    #   과적합) 교훈에 따라 변수값·조건을 그대로 복제하지 말라고 명시한다. None/빈
    #   리스트면 이 블록이 통째로 미추가되어 출력이 기존과 byte-동일하다(하위호환).
    if few_shot_examples:
        user_lines += [
            "",
            "아래는 검증된 우수 전략 예시다 — 변수조합·다중필터 AND 게이팅 구조를 "
            "학습하되, 변수값·조건을 그대로 복제하지 말고 현재 목표에 맞게 새로 설계하라.",
        ]
        for ex in few_shot_examples:
            user_lines.append(f"```python\n{ex}\n```")

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
