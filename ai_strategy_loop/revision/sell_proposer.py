"""데이터 구동 매도 후보 생성기(P2) — 결정 임계값은 cohort 분위수에서만 온다.

원칙:
  - 하드코딩 결정 임계값 0: 손절 깊이·지연·트리거는 해당 분석의 회복/비회복/
    승리/강제청산 cohort 분위수로 계산하고 근거(threshold_sources)를 함께 남긴다.
  - 표본 게이트: cohort n < MIN_COHORT 이면 그 family 후보를 만들지 않는다
    ("근거 부족 → 후보 없음"이 정상 동작).
  - 구조 파라미터(창 크기·보존비율)는 값을 숨기지 않고 param_family 로 공개한다
    — 이후 설계 pair 스윕의 대상이지 확정값이 아니다.
  - 모든 후보는 매도 intent gate(validate_candidate_code)를 통과해야 반환된다:
    구조 해부(parse_leaves_flexible) + 허용 변수 화이트리스트(레인 분리) +
    선언 임계값⊆코드 상수 검증.
"""

from __future__ import annotations

from dataclasses import dataclass

from ai_strategy_loop.autopsy.trade_path_analysis_models import TradePathAnalysis
from ai_strategy_loop.autopsy.trade_path_models import Timeframe
from ai_strategy_loop.revision.hier_ast import parse_leaves_flexible
from ai_strategy_loop.revision.variable_catalog import catalog_for_lane


MIN_COHORT = 30

_FORBIDDEN = ("F_", "R_", "S_", "미래", "oracle", "best_future")

# 매도식 런타임 공통 화이트리스트(strategy.txt 매도 문법). 레인 전용은 아래에서 합친다.
_COMMON_NAMES = {
    "매도", "매수가", "수익률", "수익금", "최고수익률", "최저수익률", "보유시간",
    "보유수량", "시분초", "현재가", "체결강도", "등락율", "당일거래대금", "회전율",
    "시가총액", "분봉시가", "분봉고가", "분봉저가", "시가", "고가", "저가",
    "매수총잔량", "매도총잔량", "self",
    "이동평균", "최고현재가", "최저현재가", "체결강도평균", "최고체결강도",
    "최저체결강도", "abs", "min", "max", "round",
}
_TICK_ONLY = {"초당매수수량", "초당매도수량", "최고초당매수수량", "최고초당매도수량"}
_MIN_ONLY = {"분당매수수량", "분당매도수량", "최고분당매수수량", "최고분당매도수량"}


@dataclass(frozen=True, slots=True)
class SellProposal:
    proposal_id: str
    title: str
    family: str
    timeframe: str
    intent: str
    stom_code: str
    evidence: str
    counterevidence: str
    risk: str
    threshold_sources: tuple[str, ...] = ()
    param_family: tuple[str, ...] = ()
    intent_gate: str = ""
    authority: str = "advisory"


class CandidateValidationError(ValueError):
    """Raised when a generated candidate violates the STOM research contract."""


def _quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise CandidateValidationError("empty_cohort")
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _allowed_names(lane: str) -> set[str]:
    lane_extra = _TICK_ONLY if lane == "tick" else _MIN_ONLY
    catalog_names = {item.name for item in catalog_for_lane(lane)}
    return _COMMON_NAMES | lane_extra | catalog_names


def validate_candidate_code(
    code: str, *, lane: str = "", expected_consts: tuple[float, ...] = (),
) -> None:
    """매도 intent gate — 구조·화이트리스트·선언 임계값 일치를 기계 판정한다."""
    if any(token in code for token in _FORBIDDEN):
        raise CandidateValidationError("future_label_leakage")
    if "self.Sell()" not in code or "매도 = True" not in code:
        raise CandidateValidationError("invalid_stom_sell_shape")
    parsed = parse_leaves_flexible(code)
    if not parsed.ok:
        raise CandidateValidationError(f"unparseable_candidate:{parsed.reason}")
    if lane:
        import ast

        tree = ast.parse(code)
        assigned = {
            target.id for node in ast.walk(tree) if isinstance(node, ast.Assign)
            for target in node.targets if isinstance(target, ast.Name)
        }
        used = {
            node.id for node in ast.walk(tree)
            if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Store)
        }
        unknown = used - assigned - _allowed_names(lane)
        if unknown:
            raise CandidateValidationError(f"unknown_or_cross_lane_names:{sorted(unknown)}")
    if expected_consts:
        parsed_consts = {
            abs(round(value, 4))
            for clauses in parsed.leaves.values()
            for clause in clauses
            for value in clause.consts
        }
        missing = [
            value for value in expected_consts
            if abs(round(value, 4)) not in parsed_consts
        ]
        if missing:
            raise CandidateValidationError(f"declared_threshold_missing:{missing}")


def _hold_units(seconds: float, timeframe: Timeframe) -> int:
    value = int(round(seconds if timeframe is Timeframe.TICK else seconds / 60.0))
    return max(1, value)


def _windows(timeframe: Timeframe) -> dict[str, int]:
    # 구조 창(값이 아니라 창 크기) — param_family 로 공개되는 스윕 대상.
    if timeframe is Timeframe.MIN:
        return {"trend": 20, "breakdown": 5}
    return {"trend": 60, "breakdown": 60}


def _proposal(
    *, proposal_id: str, title: str, family: str, intent: str, code: str,
    evidence: str, counterevidence: str, risk: str, timeframe: Timeframe,
    threshold_sources: tuple[str, ...], param_family: tuple[str, ...],
    expected_consts: tuple[float, ...],
) -> SellProposal:
    validate_candidate_code(code, lane=timeframe.value, expected_consts=expected_consts)
    return SellProposal(
        proposal_id=proposal_id, title=title, family=family,
        timeframe=timeframe.value, intent=intent, stom_code=code,
        evidence=evidence, counterevidence=counterevidence, risk=risk,
        threshold_sources=threshold_sources, param_family=param_family,
        intent_gate="pass",
    )


def propose_sell_conditions(analysis: TradePathAnalysis) -> tuple[SellProposal, ...]:
    rows, timeframe = analysis.episodes, analysis.source.timeframe
    if not rows:
        return ()
    unit = "분" if timeframe is Timeframe.MIN else "초"
    windows = _windows(timeframe)
    losses = [row for row in rows if row.actual_profit_krw < 0]
    wins = [row for row in rows if row.actual_profit_krw > 0]
    recovered = [row for row in losses if row.recovered_by_boundary]
    unrecovered = [row for row in losses if not row.recovered_by_boundary]
    forced = [row for row in rows if row.exit_reason.startswith("전략종료")]
    proposals: list[SellProposal] = []

    # ── family 1 · 손실 방어 ──────────────────────────────────────────────
    if len(recovered) >= MIN_COHORT and len(unrecovered) >= MIN_COHORT:
        delay = _hold_units(
            _quantile([float(row.hold_seconds) for row in recovered], 0.25), timeframe,
        )
        stop_pct = min(-0.5, round(
            _quantile([float(row.actual_profit_pct) for row in unrecovered], 0.5), 1,
        ))
        code = (
            "매도 = False\n"
            f"if 보유시간 >= {delay} and 수익률 <= {stop_pct} "
            f"and 현재가 < 최저현재가({windows['breakdown']}, 보유시간):\n"
            "    매도 = True\n\nif 매도:\n    self.Sell()"
        )
        proposals.append(_proposal(
            proposal_id="delay_stop_with_breakdown",
            title="회복 관측 기반 손절 지연 + 진입 전 저점 이탈",
            family="손실 방어", timeframe=timeframe,
            intent=f"회복군이 흔들리던 최소 {delay}{unit}은 견디고, 비회복군 중앙 깊이 이하 구조 이탈만 청산",
            code=code,
            evidence=f"회복 손실 {len(recovered)}건 · 비회복 손실 {len(unrecovered)}건",
            counterevidence="회복 라벨은 연구 라벨이며 조건식 입력이 아님 — 경로 조건으로만 근사",
            risk="지연 구간 MAE 확대 가능 — 공식 pair 재백테스트 필수",
            threshold_sources=(
                f"보유시간≥{delay}{unit} ← 회복 손실군 보유시간 p25 (n={len(recovered)})",
                f"수익률≤{stop_pct}% ← 비회복 손실군 실현수익률 p50 (n={len(unrecovered)})",
            ),
            param_family=(f"저점창={windows['breakdown']}{unit} (구조 창 — 스윕 대상)",),
            expected_consts=(float(delay), stop_pct, float(windows["breakdown"])),
        ))

    # ── family 2 · 이익 보존 ──────────────────────────────────────────────
    if len(wins) >= MIN_COHORT:
        trigger = max(0.5, round(
            _quantile([float(row.actual_profit_pct) for row in wins], 0.6), 1,
        ))
        retention = 0.65
        code = (
            "매도 = False\n"
            f"if 최고수익률 >= {trigger} and 최고수익률 * {retention} >= 수익률:\n"
            "    매도 = True\n"
            f"elif 최고수익률 >= {trigger} and 현재가 < 이동평균({windows['trend']}):\n"
            "    매도 = True\n\nif 매도:\n    self.Sell()"
        )
        proposals.append(_proposal(
            proposal_id="lower_profit_trigger_dual_trail",
            title="승자 분위수 트리거 + 이평 반납 이중 확인",
            family="이익 보존", timeframe=timeframe,
            intent="승리 거래의 실현 분포에서 트리거를 낮춰 보존 빈도를 높이되 고정 익절은 피함",
            code=code,
            evidence=f"이익 거래 {len(wins)}건 실현수익률 분포",
            counterevidence="낮은 트리거는 큰 추세의 조기 이탈을 늘릴 수 있음",
            risk="보존비율·이평창은 구조 파라미터 — 설계 pair 스윕 전 확정값 아님",
            threshold_sources=(
                f"트리거≥{trigger}% ← 승리군 실현수익률 p60 (n={len(wins)})",
            ),
            param_family=(
                f"보존비율={retention} ∈ {{0.5, 0.65, 0.8}} (스윕 대상)",
                f"이평창={windows['trend']}{unit} (구조 창 — 스윕 대상)",
            ),
            expected_consts=(trigger, retention, float(windows["trend"])),
        ))

    # ── family 3 · 수익 반납 ──────────────────────────────────────────────
    if len(wins) >= MIN_COHORT and len(recovered) >= MIN_COHORT:
        once_up = max(0.5, round(
            _quantile([float(row.actual_profit_pct) for row in wins], 0.4), 1,
        ))
        code = (
            "매도 = False\n"
            f"if 최고수익률 >= {once_up} and 수익률 <= 0 "
            f"and 현재가 < 이동평균({windows['trend']}):\n"
            "    매도 = True\n\nif 매도:\n    self.Sell()"
        )
        proposals.append(_proposal(
            proposal_id="mfe_breakeven_guard",
            title="한때 이익 거래의 본전 재진입 방어",
            family="수익 반납", timeframe=timeframe,
            intent=f"승자 하위 분위({once_up}%) 이상 갔던 거래만 본전 아래 추세이탈에서 정리",
            code=code,
            evidence=f"승리군 분포 (n={len(wins)}) · 회복 관측 {len(recovered)}건",
            counterevidence="한때-이익 임계는 승자 분포의 대리값 — 개별 MFE 분포가 아님",
            risk="임계 이하의 큰 하락은 손실 방어군이 담당해야 함",
            threshold_sources=(
                f"한때이익≥{once_up}% ← 승리군 실현수익률 p40 (n={len(wins)})",
            ),
            param_family=(f"이평창={windows['trend']}{unit} (구조 창 — 스윕 대상)",),
            expected_consts=(once_up, 0.0, float(windows["trend"])),
        ))

    # ── family 4 · 시간 가치 ──────────────────────────────────────────────
    if len(losses) >= MIN_COHORT and len(wins) >= MIN_COHORT:
        stagnation = _hold_units(
            _quantile([float(row.hold_seconds) for row in losses], 0.5), timeframe,
        )
        low_progress = max(0.3, round(
            _quantile([float(row.actual_profit_pct) for row in wins], 0.25), 1,
        ))
        code = (
            "매도 = False\n"
            f"if 보유시간 >= {stagnation} and 최고수익률 < {low_progress} and 수익률 < 0 "
            f"and 현재가 < 이동평균({windows['trend']}):\n"
            "    매도 = True\n\nif 매도:\n    self.Sell()"
        )
        proposals.append(_proposal(
            proposal_id="stagnation_trend_decay",
            title="저성과 정체 + 추세 하향 전환 청산",
            family="시간 가치", timeframe=timeframe,
            intent=f"손실군 중앙 보유({stagnation}{unit})가 지나도록 승자 하위 진행({low_progress}%)조차 못 간 손실권만 정리",
            code=code,
            evidence=f"손실군 보유 분포 (n={len(losses)}) · 승리군 진행 분포 (n={len(wins)})",
            counterevidence="시간 구간 자체를 제거하지 않고 경로 상태를 함께 요구함",
            risk="정체 판정이 늦으면 손실 방어군과 역할이 겹칠 수 있음",
            threshold_sources=(
                f"보유시간≥{stagnation}{unit} ← 손실군 보유시간 p50 (n={len(losses)})",
                f"최고수익률<{low_progress}% ← 승리군 실현수익률 p25 (n={len(wins)})",
            ),
            param_family=(f"이평창={windows['trend']}{unit} (구조 창 — 스윕 대상)",),
            expected_consts=(float(stagnation), low_progress, 0.0, float(windows["trend"])),
        ))

    # ── family 5 · 마감 관리 ──────────────────────────────────────────────
    if len(forced) >= MIN_COHORT:
        preclose = _hold_units(
            _quantile([float(row.hold_seconds) for row in forced], 0.5), timeframe,
        )
        code = (
            "매도 = False\n"
            f"if 보유시간 >= {preclose} and 수익률 > 0 "
            f"and 현재가 < 이동평균({windows['trend']}):\n"
            "    매도 = True\n\nif 매도:\n    self.Sell()"
        )
        proposals.append(_proposal(
            proposal_id="preclose_profitable_fade",
            title="강제청산 도달 이전 이익권 추세이탈 정리",
            family="마감 관리", timeframe=timeframe,
            intent=f"강제청산군 중앙 보유({preclose}{unit}) 이후 이익권 반납만 조기 정리 — 강제청산 자체는 유지",
            code=code,
            evidence=(
                f"전략종료 청산 {len(forced)}건 · 합계 "
                f"{sum(row.actual_profit_krw for row in forced):,}원"
            ),
            counterevidence="손실권 포지션에는 적용하지 않아 손실 강제청산을 직접 줄이지 않음",
            risk="마감 전 재상승 구간을 놓칠 수 있음",
            threshold_sources=(
                f"보유시간≥{preclose}{unit} ← 강제청산군 보유시간 p50 (n={len(forced)})",
            ),
            param_family=(f"이평창={windows['trend']}{unit} (구조 창 — 스윕 대상)",),
            expected_consts=(float(preclose), 0.0, float(windows["trend"])),
        ))

    return tuple(proposals)
