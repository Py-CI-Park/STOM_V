"""부검 분석 — working-window 거래 CSV에서 수익/손실을 가른 진입 조건을 찾는다.

핵심 신호: 14개 진입시점 컬럼(B_*) 각각에 대해 수익 그룹 평균과 손실 그룹 평균을
구하고, 표준화 평균차(Cohen's-d 류)로 변별력을 매긴다.

    std_mean_diff = (win_mean - loss_mean) / pooled_std

부호(>0)는 "수익 거래에서 그 값이 더 컸다", 음수는 "손실 거래에서 더 컸다"를 뜻한다.
|std_mean_diff| 가 클수록 그 진입 조건이 승패를 더 잘 갈랐다는 의미다.

데이터 모양으로는 절대 예외를 던지지 않는다(상태 코드로 깔끔히 반환). 단, 부검은
working/train 거래에서만 돌아야 하므로 is_holdout=True 면 ValueError 를 던진다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pandas as pd

# 수익률 컬럼: >0 이면 수익(win), <=0 이면 손실(loss).
RETURN_COLUMN = "수익률"

# FDR(다중검정 보정) 유의수준 — 동결값(P3 §Q7). 한 부검에서 존재하는 B_* 피처
#   전수를 family로 보고 Benjamini-Hochberg로 보정한다. 잡음 피처의 임계 후보가
#   생성 프롬프트에 주입되는 선택편향(R1)을 차단하기 위한 진행 게이트일 뿐,
#   하드게이트·엔진·스코어와 무관하다. 0.10은 발견지향(연구) 표준값.
_FDR_ALPHA = 0.10

# 진입시점(B_*) 컬럼 — backtest/back_static.py TRADE_RESULT_B_COLUMNS 와 동일.
B_COLUMNS = [
    "B_현재가", "B_등락율", "B_당일거래대금", "B_거래대금증감", "B_체결강도",
    "B_시가총액", "B_회전율", "B_전일동시간비", "B_매수총잔량", "B_매도총잔량",
    "B_시분초", "B_분봉시가", "B_분봉고가", "B_분봉저가",
]

# 변별 변수가 매핑되는 실제 STOM 진입 변수(요약 가이드에서 튜닝 힌트로 사용).
B_TO_STOM_VAR = {
    "B_현재가": "현재가",
    "B_등락율": "등락율",
    "B_당일거래대금": "당일거래대금",
    "B_거래대금증감": "거래대금증감",
    "B_체결강도": "체결강도",
    "B_시가총액": "시가총액",
    "B_회전율": "회전율",
    "B_전일동시간비": "전일동시간비",
    "B_매수총잔량": "매수총잔량",
    "B_매도총잔량": "매도총잔량",
    "B_시분초": "시분초",
    "B_분봉시가": "분봉시가",
    "B_분봉고가": "분봉고가",
    "B_분봉저가": "분봉저가",
}

# 최소 거래 수. 이 미만이면 통계가 의미 없어 insufficient_trades 로 처리한다.
DEFAULT_MIN_TRADES = 10

STATUS_OK = "ok"
STATUS_INSUFFICIENT = "insufficient_trades"
STATUS_SINGLE_CLASS = "single_class"

# --- 청산(EXIT) 부검용 컬럼 ---
# 거래당 결과 컬럼 (back_static.py TRADE_RESULT_R_COLUMNS 와 동일 의미).
MFE_COLUMN = "R_매수후최고수익률"   # 매수 후 최고 수익률(Max Favorable Excursion).
MAE_COLUMN = "R_매수후최저수익률"   # 매수 후 최저 수익률(Max Adverse Excursion).
HOLD_COLUMN = "보유시간"            # 보유 시간(분/틱 단위).
SELL_RULE_COLUMN = "매도조건"        # 발화한 매도 규칙 원문(어떤 청산 룰이 닫았는지).

# give-back 판정 기준: MFE가 이 값(%) 이상이었던 거래만 "익절 기회가 있었다"로 본다.
DEFAULT_GIVEBACK_MFE_THRESHOLD = 1.0

# P5 Exit Regret(조기청산 후회): 익절기회 있던 수익거래 중 실현이 MFE의 이 비율 미만이면
#   '고점을 못 지킨 조기청산'으로 본다(기본 0.5 = 고점 절반도 못 지킴).
DEFAULT_EXIT_REGRET_KEEP = 0.5
# P5 False-Break(가짜 돌파): 손실거래의 MFE가 이 값(%) 미만이면 '진입 후 한 번도 의미있게
#   못 오른' 가짜 돌파로 본다(되돌림이 아니라 애초에 진입 신호가 틀렸음).
DEFAULT_FALSE_BREAK_MFE = 0.5


@dataclass
class Discriminator:
    """한 진입(B_*) 컬럼의 수익/손실 변별 통계."""

    column: str
    win_mean: float
    loss_mean: float
    std_mean_diff: float  # (win_mean - loss_mean) / pooled_std (Cohen's-d 류)
    # R1(2026-06-11) — 승자 분위수: "기준을 높여라/낮춰라"(방향)에 구체 임계 후보(숫자)를
    #   더하기 위한 보조 필드. None이면 미산출(하위호환 — 기존 소비자 영향 없음).
    #   근거: 직이식 임계 5/5 음수 실측 — LLM에 방향만 주면 임의 숫자를 찍는다(G1).
    win_q25: Optional[float] = None
    win_q50: Optional[float] = None
    win_q75: Optional[float] = None
    # P3 FDR(다중검정 보정) — 이 피처의 승/패 변별이 우연일 확률(p_value)과 family
    #   전체에 Benjamini-Hochberg를 적용한 보정 q_value, 그리고 _FDR_ALPHA 통과 여부.
    #   None이면 미산출(하위호환 — 기존 소비자 영향 없음). 가법 필드라 OFF 경로 byte-동일.
    p_value: Optional[float] = None
    q_value: Optional[float] = None
    fdr_pass: Optional[bool] = None


@dataclass
class AutopsyResult:
    """부검 1회 결과.

    status:
      - 'ok'                  : 변별 통계 산출됨 (discriminators 채워짐).
      - 'insufficient_trades' : 거래 0건 또는 min_trades 미만 (통계 무의미).
      - 'single_class'        : 전부 수익 또는 전부 손실 (변별 불가).
    """

    trade_count: int
    win_count: int
    loss_count: int
    discriminators: List[Discriminator] = field(default_factory=list)
    status: str = STATUS_OK
    note: str = ""
    min_trades: int = DEFAULT_MIN_TRADES


def _pooled_std(win_vals: pd.Series, loss_vals: pd.Series) -> float:
    """두 그룹의 합동 표준편차(pooled std). 표본<2인 그룹은 std=0으로 본다."""
    win_std = float(win_vals.std(ddof=1)) if len(win_vals) >= 2 else 0.0
    loss_std = float(loss_vals.std(ddof=1)) if len(loss_vals) >= 2 else 0.0
    n_w, n_l = len(win_vals), len(loss_vals)
    if n_w + n_l <= 2:
        return 0.0
    # pooled variance (각 그룹 자유도 가중).
    num = (max(n_w - 1, 0)) * (win_std ** 2) + (max(n_l - 1, 0)) * (loss_std ** 2)
    den = n_w + n_l - 2
    if den <= 0:
        return 0.0
    var = num / den
    return float(var ** 0.5)


def _two_sample_p(std_mean_diff: float, n_win: int, n_loss: int) -> float:
    """승/패 두 그룹 평균차의 양측 p값(정규근사). 표준라이브러리만 사용(scipy 불요).

    표준화 평균차(std_mean_diff = (mw-ml)/pooled)와 두 표본수로 t통계량을 복원한다:
        t = std_mean_diff / sqrt(1/n_win + 1/n_loss)
    충분표본에서 t≈z로 보고 양측 p = 2*(1 - Φ(|t|))를 math.erf로 계산한다. 효과 0·표본
    부족·비유한 입력은 p=1.0(가장 보수적)으로 흡수한다(무예외). 정밀 검정이 목적이
    아니라 잡음 피처를 거르는 진행 게이트라 정규근사로 충분하다.
    """
    if n_win < 2 or n_loss < 2:
        return 1.0
    if not math.isfinite(std_mean_diff) or std_mean_diff == 0.0:
        return 1.0
    se = math.sqrt(1.0 / n_win + 1.0 / n_loss)
    if se <= 0.0:
        return 1.0
    t = abs(std_mean_diff) / se
    # 표준정규 생존함수: 1 - Φ(t) = 0.5 * erfc(t / sqrt(2)).
    p = math.erfc(t / math.sqrt(2.0))
    return float(min(1.0, max(0.0, p)))


def _benjamini_hochberg(
    p_values: List[float], alpha: float = _FDR_ALPHA
) -> Tuple[List[float], List[bool]]:
    """Benjamini-Hochberg FDR 보정. p값 리스트 → (q값 리스트, 통과여부 리스트)(순수·무예외).

    입력 순서를 보존해 (q_values, pass_flags)를 돌려준다. 절차:
      1. p를 오름차순 정렬, rank i(1-based)마다 q_i = p_(i) * m / i (m=family 크기).
      2. 큰 rank부터 누적 최소로 단조성 보정(q는 비감소가 되도록).
      3. 가장 큰 통과 rank k* = max{i : p_(i) <= (i/m)*alpha}; rank<=k*면 통과.
    빈 입력은 ([], [])를 돌린다. 어떤 입력에도 예외를 던지지 않는다.
    """
    m = len(p_values)
    if m == 0:
        return [], []
    # (원래 인덱스, p) 오름차순.
    order = sorted(range(m), key=lambda i: p_values[i])
    # 단조 보정된 q값(작은 rank 방향으로 누적 최소).
    q_sorted = [0.0] * m
    prev = 1.0
    for rank in range(m, 0, -1):  # m..1
        idx_in_order = rank - 1
        raw_q = p_values[order[idx_in_order]] * m / rank
        prev = min(prev, raw_q)
        q_sorted[idx_in_order] = min(1.0, prev)
    # 가장 큰 통과 rank.
    k_star = 0
    for rank in range(1, m + 1):
        if p_values[order[rank - 1]] <= (rank / m) * alpha:
            k_star = rank
    q_values = [0.0] * m
    pass_flags = [False] * m
    for pos, orig_idx in enumerate(order):
        q_values[orig_idx] = q_sorted[pos]
        pass_flags[orig_idx] = (pos + 1) <= k_star
    return q_values, pass_flags


def analyze_trades(
    csv_path: str,
    *,
    min_trades: int = DEFAULT_MIN_TRADES,
    is_holdout: bool = False,
) -> AutopsyResult:
    """거래 CSV를 읽어 진입 조건의 수익/손실 변별력을 분석한다.

    Args:
        csv_path: 백테스트 결과 CSV(utf-8-sig, 거래당 1행, '수익률' 컬럼 보유).
        min_trades: 통계 산출 최소 거래 수 (미만이면 insufficient_trades).
        is_holdout: True면 ValueError (부검은 working/train 거래에서만, RV2-4/A5).

    Returns:
        AutopsyResult. 데이터 모양 문제(0건/단일클래스/B_컬럼없음)는 예외가 아니라
        status 로 표현한다.

    Raises:
        ValueError: is_holdout=True 일 때.
    """
    if is_holdout:
        raise ValueError(
            "autopsy must run on working/train trades only — holdout 거래로는 부검 금지 (RV2-4/A5)"
        )

    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        # 완전히 빈 파일(헤더조차 없음) — 거래 0건과 동일하게 처리.
        return AutopsyResult(
            trade_count=0, win_count=0, loss_count=0,
            status=STATUS_INSUFFICIENT, min_trades=min_trades,
            note="CSV가 비어 있다 — 거래 0건.",
        )

    if RETURN_COLUMN not in df.columns:
        return AutopsyResult(
            trade_count=int(len(df)), win_count=0, loss_count=0,
            status=STATUS_INSUFFICIENT, min_trades=min_trades,
            note=f"수익률 컬럼('{RETURN_COLUMN}')이 없어 승패를 가를 수 없다.",
        )

    # 수익률을 숫자로 강제 변환, 결측 행 제거.
    returns = pd.to_numeric(df[RETURN_COLUMN], errors="coerce")
    valid_mask = returns.notna()
    df = df.loc[valid_mask].reset_index(drop=True)
    returns = returns.loc[valid_mask].reset_index(drop=True)

    trade_count = int(len(df))
    is_win = returns > 0
    win_count = int(is_win.sum())
    loss_count = trade_count - win_count

    # 0건 또는 min_trades 미만 → insufficient.
    if trade_count == 0:
        return AutopsyResult(
            trade_count=0, win_count=0, loss_count=0,
            status=STATUS_INSUFFICIENT, min_trades=min_trades,
            note="거래 0건 — 진입이 한 번도 발생하지 않았다.",
        )
    if trade_count < min_trades:
        return AutopsyResult(
            trade_count=trade_count, win_count=win_count, loss_count=loss_count,
            status=STATUS_INSUFFICIENT, min_trades=min_trades,
            note=f"거래 {trade_count}건 < 최소 {min_trades}건 — 통계가 무의미하다.",
        )

    # 전부 수익 또는 전부 손실 → 변별 불가.
    if win_count == 0 or loss_count == 0:
        only = "수익" if loss_count == 0 else "손실"
        return AutopsyResult(
            trade_count=trade_count, win_count=win_count, loss_count=loss_count,
            status=STATUS_SINGLE_CLASS, min_trades=min_trades,
            note=f"모든 거래가 {only} — 수익/손실 변별이 불가능하다.",
        )

    # --- 변별 통계: 존재하는 B_* 컬럼별 표준화 평균차 ---
    present = [c for c in B_COLUMNS if c in df.columns]
    discriminators: List[Discriminator] = []
    for col in present:
        vals = pd.to_numeric(df[col], errors="coerce")
        win_vals = vals[is_win].dropna()
        loss_vals = vals[~is_win].dropna()
        if len(win_vals) == 0 or len(loss_vals) == 0:
            continue
        win_mean = float(win_vals.mean())
        loss_mean = float(loss_vals.mean())
        pooled = _pooled_std(win_vals, loss_vals)
        if pooled <= 1e-12:
            # 분산이 ~0 (모든 값 동일): 변별력 0으로 둔다(0 나눗셈 가드).
            smd = 0.0
        else:
            smd = (win_mean - loss_mean) / pooled
        # R1 — 승자 분위수(임계값 제안 재료). 산출 실패는 None으로 흡수(보조 필드).
        try:
            win_q25 = float(win_vals.quantile(0.25))
            win_q50 = float(win_vals.quantile(0.50))
            win_q75 = float(win_vals.quantile(0.75))
        except Exception:  # noqa: BLE001
            win_q25 = win_q50 = win_q75 = None
        discriminators.append(
            Discriminator(
                column=col, win_mean=win_mean, loss_mean=loss_mean,
                std_mean_diff=float(smd),
                win_q25=win_q25, win_q50=win_q50, win_q75=win_q75,
                p_value=_two_sample_p(float(smd), len(win_vals), len(loss_vals)),
            )
        )

    # --- P3 FDR(다중검정 보정): 존재한 B_* 피처 전수를 family로 BH 보정 ---
    #   여러 피처를 동시에 검정하면 우연히 "잘 가르는" 잡음 피처가 나온다. BH로
    #   q값·통과여부를 매겨 잡음 피처의 임계 후보 주입(R1 선택편향)을 차단한다.
    #   가법 필드만 채우므로 기존 소비자(기본 summarize) 출력은 byte-동일하다.
    if discriminators:
        q_values, pass_flags = _benjamini_hochberg(
            [d.p_value if d.p_value is not None else 1.0 for d in discriminators],
            alpha=_FDR_ALPHA,
        )
        for d, q, ok in zip(discriminators, q_values, pass_flags):
            d.q_value = q
            d.fdr_pass = bool(ok)

    # |std_mean_diff| 내림차순 정렬 (가장 잘 가른 조건 먼저).
    discriminators.sort(key=lambda d: abs(d.std_mean_diff), reverse=True)

    note = (
        f"거래 {trade_count}건 (수익 {win_count} / 손실 {loss_count}), "
        f"분석 B_컬럼 {len(discriminators)}개."
    )
    return AutopsyResult(
        trade_count=trade_count, win_count=win_count, loss_count=loss_count,
        discriminators=discriminators, status=STATUS_OK, min_trades=min_trades,
        note=note,
    )


# =====================================================================
# 청산(EXIT) 부검 — 매도 전략/되돌림/손절 깊이를 분석한다 (US-006 PROFITABILITY).
# =====================================================================
@dataclass
class SellRuleStat:
    """한 매도 규칙(매도조건 원문)의 발화 통계."""

    rule: str            # 매도조건 원문(if ...:) — 어떤 청산 룰이 닫았는지.
    count: int           # 이 규칙으로 청산된 거래 수.
    win_count: int       # 그중 수익 거래 수.
    loss_count: int      # 그중 손실 거래 수.
    avg_return: float    # 이 규칙으로 닫힌 거래의 평균 실현 수익률(%).


@dataclass
class ExitAutopsyResult:
    """청산(EXIT)-측 부검 1회 결과.

    매도 전략 개선을 직접 겨냥한다:
      - give-back: 수익 거래가 고점(MFE) 대비 얼마를 되돌려 반납했는가.
      - MAE depth: 손실 거래가 청산 전 얼마나 깊이 물렸는가(손절 느슨함).
      - holding time: 수익 vs 손실 거래의 평균 보유 시간.
      - sell-rule 분포: 어떤 매도 규칙이 손실에 연관됐는가.

    status:
      - 'ok'                  : 통계 산출됨.
      - 'insufficient_trades' : 거래 0건 또는 min_trades 미만.
      - 'single_class'        : 전부 수익 또는 전부 손실(give-back/MAE 대비 불가하지만,
                                존재하는 쪽 통계는 채운다).
    """

    trade_count: int
    win_count: int
    loss_count: int
    # give-back (수익 거래 기준, MFE>=threshold 인 거래만).
    giveback_eligible: int = 0       # MFE>=threshold 였던 거래 수(익절 기회).
    avg_mfe_winners: float = 0.0     # 수익 거래 평균 MFE(%).
    avg_realized_winners: float = 0.0  # 수익 거래 평균 실현 수익률(%).
    giveback_gap_winners: float = 0.0  # 수익 거래의 평균 (MFE - 실현) = 반납 폭(%).
    avg_mfe_all: float = 0.0         # 전체 거래 평균 MFE(%).
    avg_realized_all: float = 0.0    # 전체 거래 평균 실현 수익률(%).
    giveback_gap_all: float = 0.0    # 전체 평균 반납 폭(%).
    # MAE depth (손실 거래 기준).
    avg_mae_losers: float = 0.0      # 손실 거래 평균 MAE(%, 보통 음수).
    worst_mae_losers: float = 0.0    # 손실 거래 최악 MAE(%).
    # P5 Exit Regret(조기청산 후회) — 익절기회 있던 수익거래가 고점을 못 지킨 정도.
    exit_regret_eligible: int = 0    # MFE>=threshold 였던 수익거래 수(후회 모집단).
    exit_regret_ratio: float = 0.0   # 그중 실현<MFE*KEEP(고점 절반도 못 지킴) 비율.
    avg_exit_regret: float = 0.0     # 모집단 평균 (MFE - 실현) = 후회 폭(%p).
    # P5 False-Break(가짜 돌파) — 손실거래가 진입 후 한 번도 못 오른(MFE<문턱) 비율.
    false_break_losers: int = 0      # MFE<DEFAULT_FALSE_BREAK_MFE 인 손실거래 수.
    false_break_ratio: float = 0.0   # false_break_losers / 손실거래 수.
    # holding time.
    avg_hold_winners: float = 0.0
    avg_hold_losers: float = 0.0
    # sell-rule 분포 (count 내림차순).
    sell_rules: List[SellRuleStat] = field(default_factory=list)
    worst_sell_rule: Optional[str] = None  # 평균 수익률이 가장 낮은(손실 집중) 규칙.
    status: str = STATUS_OK
    note: str = ""
    min_trades: int = DEFAULT_MIN_TRADES
    giveback_mfe_threshold: float = DEFAULT_GIVEBACK_MFE_THRESHOLD


def analyze_exits(
    csv_path: str,
    *,
    min_trades: int = DEFAULT_MIN_TRADES,
    giveback_mfe_threshold: float = DEFAULT_GIVEBACK_MFE_THRESHOLD,
    exit_regret_keep: float = DEFAULT_EXIT_REGRET_KEEP,
    is_holdout: bool = False,
) -> ExitAutopsyResult:
    """거래 CSV를 읽어 **청산(매도)** 측 신호를 분석한다(수익성 직결).

    entry(B_*) 변별이 아니라 give-back / MAE depth / 보유시간 / 매도규칙 분포를
    계산해 매도 전략 개선을 겨냥한다.

    Args:
        csv_path: 백테스트 결과 CSV(utf-8-sig, 거래당 1행).
        min_trades: 통계 산출 최소 거래 수 (미만이면 insufficient_trades).
        giveback_mfe_threshold: give-back 판정 MFE 문턱(%). 이 값 이상이었던 거래만
            "익절 기회가 있었다"로 본다.
        is_holdout: True면 ValueError (부검은 working/train 거래에서만, RV2-4/A5).

    Returns:
        ExitAutopsyResult. 데이터 모양 문제(0건/컬럼없음)는 예외가 아니라 status로.

    Raises:
        ValueError: is_holdout=True 일 때.
    """
    if is_holdout:
        raise ValueError(
            "autopsy must run on working/train trades only — holdout 거래로는 부검 금지 (RV2-4/A5)"
        )

    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        return ExitAutopsyResult(
            trade_count=0, win_count=0, loss_count=0,
            status=STATUS_INSUFFICIENT, min_trades=min_trades,
            giveback_mfe_threshold=giveback_mfe_threshold,
            note="CSV가 비어 있다 — 거래 0건.",
        )

    if RETURN_COLUMN not in df.columns:
        return ExitAutopsyResult(
            trade_count=int(len(df)), win_count=0, loss_count=0,
            status=STATUS_INSUFFICIENT, min_trades=min_trades,
            giveback_mfe_threshold=giveback_mfe_threshold,
            note=f"수익률 컬럼('{RETURN_COLUMN}')이 없어 청산 분석 불가.",
        )

    returns = pd.to_numeric(df[RETURN_COLUMN], errors="coerce")
    valid_mask = returns.notna()
    df = df.loc[valid_mask].reset_index(drop=True)
    returns = returns.loc[valid_mask].reset_index(drop=True)

    trade_count = int(len(df))
    is_win = returns > 0
    win_count = int(is_win.sum())
    loss_count = trade_count - win_count

    if trade_count == 0:
        return ExitAutopsyResult(
            trade_count=0, win_count=0, loss_count=0,
            status=STATUS_INSUFFICIENT, min_trades=min_trades,
            giveback_mfe_threshold=giveback_mfe_threshold,
            note="거래 0건 — 진입이 한 번도 발생하지 않았다.",
        )
    if trade_count < min_trades:
        return ExitAutopsyResult(
            trade_count=trade_count, win_count=win_count, loss_count=loss_count,
            status=STATUS_INSUFFICIENT, min_trades=min_trades,
            giveback_mfe_threshold=giveback_mfe_threshold,
            note=f"거래 {trade_count}건 < 최소 {min_trades}건 — 통계가 무의미하다.",
        )

    # MFE/실현 수익률 — give-back. MFE 컬럼이 없으면 give-back은 0으로 둔다.
    mfe = pd.to_numeric(df[MFE_COLUMN], errors="coerce") if MFE_COLUMN in df.columns else None
    mae = pd.to_numeric(df[MAE_COLUMN], errors="coerce") if MAE_COLUMN in df.columns else None

    res = ExitAutopsyResult(
        trade_count=trade_count, win_count=win_count, loss_count=loss_count,
        status=STATUS_SINGLE_CLASS if (win_count == 0 or loss_count == 0) else STATUS_OK,
        min_trades=min_trades, giveback_mfe_threshold=giveback_mfe_threshold,
    )

    if mfe is not None:
        all_mfe = mfe.dropna()
        if len(all_mfe) > 0:
            res.avg_mfe_all = float(all_mfe.mean())
        # 전체 give-back gap = 평균 MFE - 평균 실현.
        res.avg_realized_all = float(returns.mean())
        res.giveback_gap_all = res.avg_mfe_all - res.avg_realized_all

        # 수익 거래 give-back (익절 기회가 있던 거래: MFE>=threshold).
        win_mfe = mfe[is_win].dropna()
        win_ret = returns[is_win]
        if len(win_mfe) > 0:
            res.avg_mfe_winners = float(win_mfe.mean())
            res.avg_realized_winners = float(win_ret.dropna().mean())
            res.giveback_gap_winners = res.avg_mfe_winners - res.avg_realized_winners
        eligible_mask = (mfe >= giveback_mfe_threshold) & is_win
        res.giveback_eligible = int(eligible_mask.fillna(False).sum())

    # MAE depth (손실 거래).
    if mae is not None and loss_count > 0:
        loss_mae = mae[~is_win].dropna()
        if len(loss_mae) > 0:
            res.avg_mae_losers = float(loss_mae.mean())
            res.worst_mae_losers = float(loss_mae.min())

    # P5 Exit Regret(조기청산 후회) — 익절기회(MFE>=threshold) 있던 수익거래가 고점을
    #   얼마나 못 지켰나. 실현 < MFE*KEEP 면 '고점 절반도 못 지킨' 조기청산으로 본다.
    if mfe is not None and win_count > 0:
        elig_mask = (is_win & (mfe >= giveback_mfe_threshold)).fillna(False)
        n_elig = int(elig_mask.sum())
        res.exit_regret_eligible = n_elig
        if n_elig > 0:
            elig_mfe = mfe[elig_mask]
            elig_ret = returns[elig_mask]
            kept_little = elig_ret < (exit_regret_keep * elig_mfe)
            res.exit_regret_ratio = round(float(kept_little.sum()) / n_elig, 4)
            res.avg_exit_regret = float((elig_mfe - elig_ret).mean())

    # P5 False-Break(가짜 돌파) — 손실거래가 진입 후 한 번도 의미있게(MFE>=문턱) 못 오른
    #   비율. 되돌림(give-back)이 아니라 애초에 진입 신호가 틀렸다는 신호(진입 품질 문제).
    if mfe is not None and loss_count > 0:
        fb_mask = (mfe[~is_win] < DEFAULT_FALSE_BREAK_MFE).fillna(False)
        res.false_break_losers = int(fb_mask.sum())
        res.false_break_ratio = round(res.false_break_losers / loss_count, 4)

    # 보유시간 (수익 vs 손실).
    if HOLD_COLUMN in df.columns:
        hold = pd.to_numeric(df[HOLD_COLUMN], errors="coerce")
        win_hold = hold[is_win].dropna()
        loss_hold = hold[~is_win].dropna()
        if len(win_hold) > 0:
            res.avg_hold_winners = float(win_hold.mean())
        if len(loss_hold) > 0:
            res.avg_hold_losers = float(loss_hold.mean())

    # 매도규칙(매도조건) 분포 + 손실 집중 규칙.
    if SELL_RULE_COLUMN in df.columns:
        rule_raw = df[SELL_RULE_COLUMN].fillna("(미상)").astype(str).str.strip()
        stats: List[SellRuleStat] = []
        for rule, group_idx in rule_raw.groupby(rule_raw).groups.items():
            sub_ret = returns.loc[group_idx]
            sub_win = int((sub_ret > 0).sum())
            n = int(len(group_idx))
            stats.append(SellRuleStat(
                rule=str(rule) or "(미상)",
                count=n, win_count=sub_win, loss_count=n - sub_win,
                avg_return=float(sub_ret.mean()) if n else 0.0,
            ))
        stats.sort(key=lambda s: s.count, reverse=True)
        res.sell_rules = stats
        # 손실 집중 규칙: 손실 거래를 가진 규칙 중 평균 수익률 최저(2건 이상만 신뢰).
        loss_rules = [s for s in stats if s.loss_count > 0 and s.count >= 2]
        if loss_rules:
            res.worst_sell_rule = min(loss_rules, key=lambda s: s.avg_return).rule

    res.note = (
        f"거래 {trade_count}건 (수익 {win_count}/손실 {loss_count}), "
        f"give-back gap(수익거래) {res.giveback_gap_winners:.4g}%p, "
        f"손실 평균 MAE {res.avg_mae_losers:.4g}%, 매도규칙 {len(res.sell_rules)}종."
    )
    return res
