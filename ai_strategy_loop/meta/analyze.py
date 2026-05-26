"""P4 — 메타분석: 누적 generations에서 학습 신호를 집계한다.

여러 run에 걸친 누적 세대(loop_runs.db)에서 "어떤 변경이 개선을 낳나"를 학습한다.
작게 시작한다(통과 전략 공통 조건부터):

  (a) 통과(gate) 전략 공통 변수/임계값 — gist에서 STOM 변수 출현 빈도를 집계해
      "통과 전략은 공통적으로 X 변수를 쓴다"를 뽑는다.
  (b) 개선을 낳은 변경 유형 — parent_gen 대비 graded가 오른 세대들의 diff_from_parent
      문구를 집계해 "어떤 변경이 점수를 올렸나"를 뽑는다.
  (c) 실패 패턴 — 과매매(거래 과다)·과선별(0거래)·고MDD 세대의 빈도를 집계한다.

설계 원칙(SIMPLICITY): 읽기 전용·무예외. 휴리스틱(정규식 변수 추출)으로 가볍게.
대규모 ML은 P4 후속(cli/ml_factor_model.py 연동)으로 미룬다 — 여기선 자기완결.
한국어 주석, 작은 함수.
"""

from __future__ import annotations

import json
import os
import re
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# 메타 인사이트 영속 경로(런타임 생성물 → state/.gitignore가 추적 제외).
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
META_INSIGHTS_FILE = _PACKAGE_DIR / "state" / "meta_insights.json"

# gist/diff에서 STOM 진입 변수를 추출하는 화이트리스트(과탐 방지). 주요 공통 변수만.
#   분당*/초당* 같은 타임프레임 계열과 공통 변수(체결강도/등락율/시가총액 등)를 포함.
_KNOWN_VARS = (
    "체결강도", "등락율", "현재가", "시가총액", "분당거래대금", "초당거래대금",
    "분당매수수량", "분당매도수량", "초당매수수량", "초당매도수량",
    "분당매수금액", "분당매도금액", "초당매수금액", "초당매도금액",
    "이동평균", "호가상승압력", "거래대금급증및연속상승", "관심종목",
    "분봉시가", "분봉고가", "분봉저가", "RSI", "MACD", "ATR",
)

# 실패 패턴 임계(휴리스틱): 과매매/고MDD 판정 기본값. config로 덮을 수 있게 인자화.
_DEFAULT_OVERTRADE = 150   # 거래수 > 이 값이면 과매매로 센다.
_DEFAULT_HIGH_MDD = 30.0   # MDD > 이 값이면 고MDD로 센다.

# 최소 통과 표본 — 이만큼 통과 세대가 있어야 "공통 조건"이 의미를 가진다.
MIN_PASSING_FOR_COMMON = 2


@dataclass
class MetaInsights:
    """누적 메타분석 1회 결과(영속 + 환류용).

    total_generations  : 집계에 쓰인 총 세대 수.
    passing_count      : 게이트 통과 세대 수.
    common_pass_vars   : 통과 전략 공통 변수 [(변수, 출현빈도) ...] 빈도순.
    improving_changes  : 개선을 낳은 변경 문구 [(문구, 횟수) ...] (diff_from_parent 집계).
    failure_patterns   : {'overtrade': n, 'zero_trade': n, 'high_mdd': n}.
    note               : 사람이 읽는 요약 한 줄.
    generated_at       : 생성 epoch.
    """

    total_generations: int = 0
    passing_count: int = 0
    common_pass_vars: List[List[Any]] = field(default_factory=list)
    improving_changes: List[List[Any]] = field(default_factory=list)
    failure_patterns: Dict[str, int] = field(default_factory=dict)
    note: str = ""
    generated_at: float = 0.0


def _extract_vars(text: str) -> List[str]:
    """gist/diff 문자열에서 알려진 STOM 변수 출현을 추출한다(중복 제거)."""
    if not text:
        return []
    found = []
    for var in _KNOWN_VARS:
        if var in text:
            found.append(var)
    return found


def _normalize_change_phrase(diff_text: str) -> Optional[str]:
    """diff_from_parent 문구를 집계 가능한 짧은 키로 정규화한다.

    공백 정리 + 앞 80자 컷. 비면 None(개선 변경 미기록 세대).
    """
    if not diff_text:
        return None
    s = re.sub(r"\s+", " ", str(diff_text)).strip()
    if not s:
        return None
    return s[:80]


def aggregate_meta_insights(
    generations: List[Dict[str, Any]],
    *,
    overtrade_threshold: int = _DEFAULT_OVERTRADE,
    high_mdd_threshold: float = _DEFAULT_HIGH_MDD,
) -> MetaInsights:
    """누적 generations 행에서 메타 인사이트를 집계한다(여러 run 가능).

    Args:
        generations: state.get_all_generations() 형태의 행 리스트(여러 run 누적).
        overtrade_threshold: 거래수 > 이 값이면 과매매로 센다.
        high_mdd_threshold: MDD > 이 값이면 고MDD로 센다.

    Returns:
        MetaInsights. 데이터가 비면 빈 인사이트(note에 사유).
    """
    gens = [g for g in (generations or []) if g is not None]
    total = len(gens)
    if total == 0:
        return MetaInsights(note="누적 세대가 없어 메타분석 불가.", generated_at=time.time())

    passing = [g for g in gens if bool(g.get("gate_passed"))]

    # (a) 통과 전략 공통 변수 — gist에서 변수 출현 빈도.
    var_counter: Counter = Counter()
    for g in passing:
        for var in _extract_vars(str(g.get("strategy_gist", "") or "")):
            var_counter[var] += 1
    # 통과 표본이 충분할 때만 공통 변수를 신뢰(소표본 과적합 방지).
    common_pass_vars: List[List[Any]] = []
    if len(passing) >= MIN_PASSING_FOR_COMMON:
        common_pass_vars = [[var, cnt] for var, cnt in var_counter.most_common(8)]

    # (b) 개선을 낳은 변경 유형 — graded가 부모보다 오른 세대의 diff_from_parent 집계.
    by_run_gen: Dict[Any, Dict[int, Dict[str, Any]]] = {}
    for g in gens:
        rid = g.get("run_id")
        by_run_gen.setdefault(rid, {})[int(g.get("gen_no", -1))] = g
    change_counter: Counter = Counter()
    for g in gens:
        parent = g.get("parent_gen")
        if parent is None:
            continue
        rid = g.get("run_id")
        parent_row = by_run_gen.get(rid, {}).get(int(parent))
        if parent_row is None:
            continue
        improved = float(g.get("score", 0.0) or 0.0) > float(parent_row.get("score", 0.0) or 0.0)
        if not improved:
            continue
        phrase = _normalize_change_phrase(str(g.get("diff_from_parent", "") or ""))
        if phrase:
            change_counter[phrase] += 1
    improving_changes = [[phrase, cnt] for phrase, cnt in change_counter.most_common(8)]

    # (c) 실패 패턴 — 과매매/0거래/고MDD 빈도.
    overtrade = sum(1 for g in gens if int(g.get("trade_count", 0) or 0) > overtrade_threshold)
    zero_trade = sum(1 for g in gens if int(g.get("trade_count", 0) or 0) == 0)
    high_mdd = sum(1 for g in gens if float(g.get("mdd", 0.0) or 0.0) > high_mdd_threshold)
    failure_patterns = {
        "overtrade": int(overtrade),
        "zero_trade": int(zero_trade),
        "high_mdd": int(high_mdd),
    }

    note = (
        f"누적 {total}세대 · 통과 {len(passing)} · 공통변수 {len(common_pass_vars)} · "
        f"개선변경 {len(improving_changes)} · "
        f"과매매 {overtrade}/0거래 {zero_trade}/고MDD {high_mdd}"
    )
    return MetaInsights(
        total_generations=total,
        passing_count=len(passing),
        common_pass_vars=common_pass_vars,
        improving_changes=improving_changes,
        failure_patterns=failure_patterns,
        note=note,
        generated_at=time.time(),
    )


# =====================================================================
# 영속(meta_insights.json) — 자기완결 파일 저장/로드.
# =====================================================================
def save_meta_insights(insights: MetaInsights, path: Optional[str] = None) -> None:
    """MetaInsights를 JSON 파일로 영속한다(atomic write).

    경로 기본값 META_INSIGHTS_FILE(state/, gitignore 추적 제외). 쓰기 실패는
    학습 신호의 보조 경로이므로 흡수한다(루프/메타집계를 막지 않음).
    """
    target = Path(path or META_INSIGHTS_FILE)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(asdict(insights), fh, ensure_ascii=False, indent=2)
        os.replace(tmp, target)
    except OSError:
        pass


def load_meta_insights(path: Optional[str] = None) -> Optional[MetaInsights]:
    """영속된 MetaInsights를 로드한다. 없거나 손상이면 None.

    환류(생성 프롬프트 주입) 직전에 호출해 가장 최근 인사이트를 가져온다.
    """
    target = Path(path or META_INSIGHTS_FILE)
    try:
        with open(target, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    known = set(MetaInsights().__dataclass_fields__.keys())
    filtered = {k: v for k, v in data.items() if k in known}
    try:
        return MetaInsights(**filtered)
    except TypeError:
        return None
