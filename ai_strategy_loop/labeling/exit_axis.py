"""매도 축 평가기 (마스터 웨이브 W3) — 봉투 데이터로 청산 규칙군을 탁상 평가한다.

배경(QSP12 지도 적정성 검증 실측): 챔피언 902/905 수익의 상당 부분은 **8종 매도
규칙**에서 나오는데, QSP10~13 의 지도는 고정 배리어(익절/손절)만 표현할 수 있었다.
그래서 "진입은 맞았는데 청산이 문제"인 후보를 볼 방법이 없었다.

이 모듈은 라벨 v3 의 봉투(30초~10분 MFE/MAE) + 배리어 최초 도달 시각으로
청산 규칙 **군(family)** 을 평가한다.

## 정직성 계약 — 정확 / 하한 / 상한을 반드시 구분한다

라벨은 경로 전체가 아니라 **요약 통계**(구간 최고/최저, 최초 도달 시각, 지평별
수익률)만 담는다. 따라서 규칙마다 평가 정확도가 다르다. 모든 결과는 `exactness`
를 달고 나간다.

  - `trailing_exact`   : **exact**       — 라벨 v4 가 경로를 그대로 시뮬레이션한 실현값.
                         러닝 최고만 쓰므로 미래 참조 없음(trailing.py). W3 재현
                         게이트가 "청산 표현력 부족"으로 멈춘 지점을 여는 열.
  - `time_stop`        : **exact**       — 지평 h 에 청산 = frA_h (라벨 값 그 자체)
  - `barrier`          : **exact**       — 최초 도달 시각 비교로 승/패/만기 결정
  - `trailing`         : **lower_bound** — 무장 여부는 `hit_up_arm < h` 로 **정확**하고,
                         무장 후 최소 실현(arm − give)만 인정한다. 미래 참조 없음.
  - `trailing_ceiling` : **upper_bound** — 무장 후 구간 최고점에서 give 만 되돌렸다고
                         본다. 실제 트레일링은 **첫 되돌림**에 나가므로 그때의 러닝
                         최고점은 구간 최종 MFE 보다 작다 → 이 값은 달성 불가한 천장.
  - `mfe_capture`      : **upper_bound** — 고점 전량 포착(완전 예지). 절대 천장.

> ⚠ 이 구분은 실측으로 얻었다. 초판은 `trailing` 을 구간 최종 MFE 로 계산했고,
> 무필터 우주(기저 −0.43~−0.71%)에서 일평균 **+0.046%** 가 나왔다. 진입 필터가
> 하나도 없는데 양수가 나오는 것이 이상해 되짚어 보니, 구간 최종 최고점을 쓰는
> 순간 **미래를 참조**하고 있었다. 하한/상한으로 갈라 다시 세운다.

## 비용
MFE/MAE 는 총(gross) 값이고 frB_* 는 순(net) 값이다. 근사 규칙은 총값에서
`gross_to_net` 로 비용을 차감해 frB 와 같은 축에 올린다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, Sequence

import numpy as np
import pandas as pd

from ai_strategy_loop.labeling import label_spec as spec
from ai_strategy_loop.labeling.trailing import TRAILING_GRID
from ai_strategy_loop.labeling.universe import ROUND_TRIP_COST_PCT

Exactness = Literal["exact", "lower_bound", "upper_bound"]

#: 봉투(MFE/MAE) 지평(초) — mfe_capture 만 여기까지 쓸 수 있다.
ENVELOPE_HORIZONS: Final = (30, 60, 120, 300, 600)

#: **만기 수익률(frA_*)이 존재하는** 지평. 라벨 실측: 600s 는 없다.
#:   만기값이 필요한 규칙군(time_stop/barrier/trailing)은 여기까지만 평가 가능하다.
RETURN_HORIZONS: Final = (30, 60, 120, 300)

#: 배리어 그리드(라벨 v3 봉인분)와 짝이 되는 열 이름.
_UP_COLUMN: Final = {1.0: "hit_up_1", 2.0: "hit_up_2", 3.0: "hit_up_3", 5.0: "hit_up_5"}
_DOWN_COLUMN: Final = {1.0: "hit_dn_1", 2.0: "hit_dn_2", 3.0: "hit_dn_3"}


def gross_to_net(gross_pct: np.ndarray) -> np.ndarray:
    """총 수익률(%) → 왕복비용 차감 순 수익률(%). frB_* 와 같은 축으로 만든다."""
    ratio = 1.0 + np.asarray(gross_pct, dtype=np.float64) / 100.0
    return ((ratio * (1 - spec.COST_OUT)) / (1 + spec.COST_IN) - 1) * 100.0


@dataclass(frozen=True)
class ExitRule:
    """청산 규칙 하나. family 마다 필요한 인자가 다르다."""

    family: Literal[
        "trailing_exact", "time_stop", "barrier", "trailing", "trailing_ceiling", "mfe_capture",
    ]
    horizon: int = 600
    tp_pct: float | None = None
    sl_pct: float | None = None
    arm_pct: float | None = None       # trailing: 무장 임계(고점이 이만큼 오르면)
    give_pct: float | None = None      # trailing: 고점 대비 되돌림 허용폭

    @property
    def exactness(self) -> Exactness:
        if self.family in ("time_stop", "barrier", "trailing_exact"):
            return "exact"
        if self.family == "trailing":
            return "lower_bound"      # 무장 정확 + 최소 실현만 인정(미래 참조 없음)
        return "upper_bound"          # trailing_ceiling · mfe_capture (완전/부분 예지)

    @property
    def label(self) -> str:
        if self.family == "time_stop":
            return f"time_stop({self.horizon}s)"
        if self.family == "barrier":
            return f"barrier(TP+{self.tp_pct:g}/SL-{self.sl_pct:g}, {self.horizon}s)"
        if self.family == "trailing_exact":
            return f"trailing(arm+{self.arm_pct:g}/give{self.give_pct:g})"
        if self.family == "trailing":
            return f"trailing_min(arm+{self.arm_pct:g}/give{self.give_pct:g}, {self.horizon}s)"
        if self.family == "trailing_ceiling":
            return f"trailing_max(arm+{self.arm_pct:g}/give{self.give_pct:g}, {self.horizon}s)"
        return f"mfe_capture({self.horizon}s)"


def _timeout_return(frame: pd.DataFrame, horizon: int) -> np.ndarray:
    column = f"frA_{horizon}" if f"frA_{horizon}" in frame.columns else f"frB_{horizon}"
    if column not in frame.columns:
        raise KeyError(f"지평 {horizon}s 의 만기 수익률 열이 없다: {column}")
    return np.nan_to_num(frame[column].to_numpy(dtype=np.float64))


def _mfe(frame: pd.DataFrame, horizon: int) -> np.ndarray:
    column = f"mfe_{horizon}"
    if column not in frame.columns:
        raise KeyError(f"지평 {horizon}s 의 MFE 열이 없다: {column}")
    return np.nan_to_num(frame[column].to_numpy(dtype=np.float64))


def _armed(frame: pd.DataFrame, arm_pct: float, horizon: int) -> np.ndarray:
    """무장 여부 — +arm% **최초 도달 시각**이 지평 안인가. 라벨로 정확히 안다."""
    column = _UP_COLUMN.get(float(arm_pct))
    if column is None:
        raise ValueError(f"봉인 배리어 격자 밖의 무장 임계: {arm_pct}")
    if column not in frame.columns:
        raise KeyError(f"무장 임계 열이 없다: {column}")
    return frame[column].to_numpy() < horizon


def evaluate(frame: pd.DataFrame, rule: ExitRule) -> np.ndarray:
    """행별 순 수익률(%) 벡터. 진입 1건 = 원소 1개."""
    if rule.family == "time_stop":
        return _timeout_return(frame, rule.horizon)

    if rule.family == "barrier":
        if rule.tp_pct is None or rule.sl_pct is None:
            raise ValueError("barrier 규칙에는 tp_pct/sl_pct 가 필요하다")
        up = _UP_COLUMN.get(float(rule.tp_pct))
        down = _DOWN_COLUMN.get(float(rule.sl_pct))
        if up is None or down is None:
            raise ValueError(f"봉인 배리어 격자 밖: TP {rule.tp_pct} / SL {rule.sl_pct}")
        tp_time = frame[up].to_numpy()
        sl_time = frame[down].to_numpy()
        # 기존 지도 경로(frontier.row_values)와 **같은 규약**을 쓴다 — 축이 다르면
        #   배리어 계열과 신규 계열을 나란히 읽을 수 없다.
        win = float(rule.tp_pct) - ROUND_TRIP_COST_PCT
        loss = -(float(rule.sl_pct) + ROUND_TRIP_COST_PCT)
        timeout = _timeout_return(frame, rule.horizon)
        # 동시 도달은 보수적으로 손절 — universe.barrier_outcome 과 같은 규약.
        return np.where(
            tp_time < sl_time, win,
            np.where(sl_time < tp_time, loss,
                     np.where(tp_time < rule.horizon, loss, timeout)),
        ).astype(np.float64)

    if rule.family == "trailing_exact":
        # 라벨 v4 — 경로를 그대로 시뮬레이션한 **실현값**이다(근사 아님).
        #   러닝 최고만 쓰므로 미래 참조가 없다(trailing.py 참조).
        if rule.arm_pct is None or rule.give_pct is None:
            raise ValueError("trailing_exact 규칙에는 arm_pct/give_pct 가 필요하다")
        column = f"trail_{rule.arm_pct:g}_{rule.give_pct:g}"
        if column not in frame.columns:
            raise KeyError(f"라벨 v4 트레일링 열이 없다: {column} (라벨 재빌드 필요)")
        return np.nan_to_num(frame[column].to_numpy(dtype=np.float64))

    if rule.family in ("trailing", "trailing_ceiling"):
        if rule.arm_pct is None or rule.give_pct is None:
            raise ValueError("trailing 규칙에는 arm_pct/give_pct 가 필요하다")
        armed = _armed(frame, rule.arm_pct, rule.horizon)
        timeout = _timeout_return(frame, rule.horizon)
        if rule.family == "trailing":
            # 하한 — 무장 직후 곧바로 give 만큼 되돌렸다고 본다(미래 참조 없음).
            #   실제 트레일링은 이보다 나쁠 수 없다: 무장했다는 사실 자체가 정확하고,
            #   되돌림 청산가는 최소한 (arm - give) 이다.
            realized = gross_to_net(np.full(len(frame), float(rule.arm_pct) - float(rule.give_pct)))
        else:
            # 상한 — 구간 최종 최고점에서 give 만 되돌렸다고 본다. 실제 트레일링은
            #   **첫 되돌림**에 나가므로 그때의 러닝 최고점 <= 구간 최종 MFE 다.
            #   따라서 이 값은 달성 불가한 천장이며 후보 판정 근거가 아니다.
            realized = gross_to_net(np.maximum(_mfe(frame, rule.horizon) - rule.give_pct, 0.0))
        return np.where(armed, realized, timeout).astype(np.float64)

    if rule.family == "mfe_capture":
        # 이론 상한 — 어떤 규칙도 이보다 좋을 수 없다는 천장. 후보 평가가 아니라
        #   "이 진입에 남은 여지가 얼마인가"를 재는 자다.
        return gross_to_net(_mfe(frame, rule.horizon))

    raise ValueError(f"알 수 없는 규칙군: {rule.family}")


def default_grid(horizons: Sequence[int] = ENVELOPE_HORIZONS) -> list[ExitRule]:
    """사전 고정 청산 격자 — 실행 전에 확정하고 전셀 보고한다(웨이브 헌법 2항).

    탐색이 아니라 **지도**다. 셀을 고른 뒤 보고하는 것이 아니라 전부 보고한다.
    """
    rules: list[ExitRule] = []
    for horizon in horizons:
        # 천장은 봉투만 있으면 계산된다(만기값 불필요).
        rules.append(ExitRule("mfe_capture", horizon=horizon))
        if horizon not in RETURN_HORIZONS:
            continue                      # 만기값이 없는 지평은 나머지 규칙군 불가.
        rules.append(ExitRule("time_stop", horizon=horizon))
    for horizon in (120, 300):
        for tp, sl in ((2.0, 1.0), (3.0, 1.0), (2.0, 2.0), (3.0, 2.0), (5.0, 3.0)):
            rules.append(ExitRule("barrier", horizon=horizon, tp_pct=tp, sl_pct=sl))
        for arm, give in ((1.0, 0.5), (2.0, 1.0), (3.0, 1.0), (3.0, 1.5)):
            rules.append(ExitRule("trailing", horizon=horizon, arm_pct=arm, give_pct=give))
            rules.append(ExitRule("trailing_ceiling", horizon=horizon, arm_pct=arm, give_pct=give))
    # 라벨 v4 실현값 — 열이 있으면 정확 계열로 평가된다(없으면 unavailable 로 보고).
    for arm, give in TRAILING_GRID:
        rules.append(ExitRule("trailing_exact", arm_pct=arm, give_pct=give))
    return rules


def evaluate_grid(
    frame: pd.DataFrame, rules: Sequence[ExitRule] | None = None,
) -> list[dict]:
    """격자 전셀 평가 — 각 셀에 exactness 를 달아 반환한다."""
    grid = list(rules) if rules is not None else default_grid()
    days = frame["일자"].to_numpy() if "일자" in frame.columns else None
    day_codes = pd.factorize(days)[0] if days is not None else None
    n_days = int(day_codes.max() + 1) if day_codes is not None and len(day_codes) else 0

    out: list[dict] = []
    for rule in grid:
        try:
            values = evaluate(frame, rule)
        except (KeyError, ValueError) as exc:
            out.append({"rule": rule.label, "family": rule.family,
                        "exactness": rule.exactness, "available": False,
                        "reason": str(exc)})
            continue
        row = {
            "rule": rule.label,
            "family": rule.family,
            "horizon": rule.horizon,
            "exactness": rule.exactness,
            "available": True,
            "n": int(values.size),
            "expectancy_pct": float(values.mean()) if values.size else float("nan"),
        }
        if day_codes is not None and values.size:
            counts = np.bincount(day_codes, minlength=n_days)
            sums = np.bincount(day_codes, weights=values, minlength=n_days)
            active = counts > 0
            daily = sums[active] / counts[active]
            row["day_mean_pct"] = float(daily.mean())
            row["day_positive_ratio"] = float((daily > 0).mean())
            row["days"] = int(len(daily))
        out.append(row)
    return out
