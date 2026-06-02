"""적응형 레짐-타이밍 오버레이 — 분석 전용(엔진/하드게이트/스코어/생성 무영향).

KR: 전략 자기 자본곡선을 추종하는 인과적(causal) 오버레이다. 결과 CSV의 월별
    손익(수익금) 시계열을 만든 뒤, 각 월에 대해 **직전 lookback개월 손익 합이
    음수면 그 달은 FLAT(0 기여)**, 아니면 그 달의 손익을 그대로 둔다(워밍업은
    맨 앞 lookback개월만 원본 유지). 이는 미래를 보지 않는다 — 판정은 그 시점
    이전(과거)의 누적 흐름만으로 결정된다. 다년(2022~2026) 연속 시계열 OOS에서
    시드의 수익/MDD(위험조정)를 ~3.5배 개선함이 검증되었다(`_temp_adaptive_multiyear.py`).
    **이 모듈은 분석/리포트 전용이다**: 하드게이트(compute_fitness)·적합도 스코어·
    생성(brain) 경로에 일절 관여하지 않으며, 루프 hot path에서 읽히지 않는다.
    대시보드 엔드포인트(/adaptive_timing)와 오프라인 분석에서만 소비한다.

EN: A causal "equity-curve-following" overlay used for ANALYSIS ONLY. From a
    strategy's per-trade result CSV we build a monthly P&L series; for each month
    we go FLAT (contribute 0) if the trailing `lookback`-month P&L sum is < 0,
    otherwise we keep that month's P&L (warmup keeps the first `lookback` months
    untouched). The decision uses only past months, never the future. Validated to
    improve the seed's return/MDD ~3.5x across 2022-2026. It NEVER touches the
    hard gate, fitness scoring, or generation — it is exposed only via the
    dashboard endpoint and offline analysis. Pure and side-effect-free.
"""

from __future__ import annotations

import csv
from typing import Dict, List, Tuple


def monthly_pnl_from_csv(csv_path: str) -> List[Tuple[str, float]]:
    """per-trade 결과 CSV를 **연속 월별 손익 시계열**로 집계한다(무예외).

    각 행에서 월키 = '매수시간'[:6](YYYYMM)·'수익금'(float)을 추출해 월별로 합산하고,
    첫 월부터 마지막 월까지 **빠진 달은 0.0으로 채운** 시간순(YYYYMM 오름차순) 리스트를
    돌려준다. 빠진 달을 0으로 메우는 이유: lookback 윈도우가 달력월 기준이어야
    (`_temp_adaptive_multiyear.py`와 동일) trailing 합 판정이 의미를 갖는다.

    무예외 계약: 파일 없음·IO 실패·헤더 누락은 빈 리스트([])로 흡수하고, 개별 행의
    파싱 불가(매수시간<6자리·수익금 None/빈칸/비수치)는 그 행만 건너뛴다. 학습/리포트
    보조 경로이므로 어떤 입력에도 예외를 던지지 않는다.

    Args:
        csv_path: per-trade 결과 CSV 경로(매수시간/수익금 컬럼 보유, utf-8-sig).

    Returns:
        [(YYYYMM, pnl_float), ...] — 첫 월~마지막 월 전 구간(gap=0.0) 시간순. 유효 월이
        없으면 [].
    """
    if not csv_path:
        return []

    by_month: Dict[str, float] = {}
    try:
        with open(csv_path, encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                bt = str(row.get("매수시간", "") or "").strip()
                pf = row.get("수익금")
                if len(bt) < 6 or pf in (None, ""):
                    continue
                try:
                    val = float(pf)
                except (TypeError, ValueError):
                    continue
                ym = bt[:6]
                by_month[ym] = by_month.get(ym, 0.0) + val
    except Exception:  # noqa: BLE001 - 파일 없음/IO/헤더 실패는 빈 시계열로 흡수(무예외).
        return []

    if not by_month:
        return []

    labels = sorted(by_month)
    first, last = labels[0], labels[-1]
    # 첫 월~마지막 월 사이 모든 달(빠진 달=0.0)을 채워 연속 시계열을 만든다.
    seq: List[Tuple[str, float]] = []
    ym = first
    while True:
        seq.append((ym, by_month.get(ym, 0.0)))
        if ym == last:
            break
        ym = _next_month(ym)
    return seq


def _next_month(ym: str) -> str:
    """YYYYMM 다음 달(YYYYMM)을 돌려준다(12월→다음해 1월)."""
    y = int(ym[:4])
    m = int(ym[4:6])
    if m >= 12:
        return f"{y + 1:04d}01"
    return f"{y:04d}{m + 1:02d}"


def apply_adaptive_timing(monthly_seq: List[float], lookback: int) -> List[float]:
    """월별 손익 시퀀스에 적응형 레짐-타이밍 규칙을 적용한다(인과적, 미래 미참조).

    인덱스 i에 대해:
      - i < max(1, lookback): 워밍업 — seq[i] 그대로 유지(판정할 과거가 부족).
      - 그 외: 직전 lookback개월 합(sum(seq[i-lookback:i]))이 음수면 0.0(FLAT),
        아니면 seq[i] 유지.

    `_temp_adaptive_multiyear.py`의 adaptive(warmup=max(1,lookback))와 동일하다.
    슬라이스 시작은 음수 인덱스 회피를 위해 max(0, i-lookback)을 쓴다.
    """
    warmup = max(1, lookback)
    out: List[float] = []
    for i, v in enumerate(monthly_seq):
        if i < warmup:
            out.append(v)
            continue
        out.append(0.0 if sum(monthly_seq[max(0, i - lookback):i]) < 0 else v)
    return out


def _equity_mdd(seq: List[float]) -> Tuple[float, float]:
    """월별 손익 시퀀스의 (총수익, MDD_절대값)를 산출한다.

    누적합 곡선을 따라가며 running peak 대비 최대 반납액(고점-누적, ≥0, 원)을 MDD로
    삼는다. `_temp_adaptive_multiyear.py`의 mdd_curve와 동일하다(엔진 equity-MDD%와
    다른 척도 — 발산 없는 절대 반납액).
    """
    cum = 0.0
    peak = 0.0
    mdd = 0.0
    for v in seq:
        cum += v
        if cum > peak:
            peak = cum
        give_back = peak - cum
        if give_back > mdd:
            mdd = give_back
    return cum, mdd


def adaptive_timing_report(csv_path: str, lookback: int = 2) -> dict:
    """결과 CSV에 always-on vs 적응형 타이밍을 적용한 비교 리포트를 만든다(분석 전용, 무예외).

    월별 손익 시계열(monthly_pnl_from_csv)을 만든 뒤, raw(always-on)와 timed(적응형)의
    총수익·MDD를 비교한다. 월이 2개 미만이면 판정할 과거가 없어 insufficient를 돌려준다.

    Args:
        csv_path: per-trade 결과 CSV 경로.
        lookback: 적응형 규칙의 trailing 윈도우(개월). 기본 2.

    Returns:
        월이 2개 미만이면 {"insufficient": True, "months": n}.
        그 외:
          {
            "months": n, "lookback": lookback,
            "raw_total": .., "raw_mdd": .., "timed_total": .., "timed_mdd": ..,
            "off_months": <원본이 0이 아닌데 timed에서 0으로 꺼진 달 수>,
            "raw_ratio": raw_total/raw_mdd (raw_mdd==0이면 0.0),
            "timed_ratio": timed_total/timed_mdd (timed_mdd==0이면 0.0),
            "monthly": [{"ym": .., "raw": .., "timed": ..}, ...],
          }
    """
    seq = monthly_pnl_from_csv(csv_path)
    n = len(seq)
    if n < 2:
        return {"insufficient": True, "months": n}

    labels = [ym for ym, _ in seq]
    raw_vals = [pnl for _, pnl in seq]
    timed_vals = apply_adaptive_timing(raw_vals, lookback)

    raw_total, raw_mdd = _equity_mdd(raw_vals)
    timed_total, timed_mdd = _equity_mdd(timed_vals)

    off_months = sum(1 for r, t in zip(raw_vals, timed_vals) if t == 0.0 and r != 0.0)

    monthly = [
        {"ym": labels[i], "raw": float(raw_vals[i]), "timed": float(timed_vals[i])}
        for i in range(n)
    ]

    return {
        "months": n,
        "lookback": lookback,
        "raw_total": float(raw_total),
        "raw_mdd": float(raw_mdd),
        "timed_total": float(timed_total),
        "timed_mdd": float(timed_mdd),
        "off_months": int(off_months),
        "raw_ratio": (raw_total / raw_mdd) if raw_mdd else 0.0,
        "timed_ratio": (timed_total / timed_mdd) if timed_mdd else 0.0,
        "monthly": monthly,
    }
