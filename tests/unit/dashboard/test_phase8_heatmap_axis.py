"""Phase8 — 요일×시간대 히트맵(수익률 합계 기준) + 차트 X/Y축 정보 보강 계약.

사용자 요청 2건을 비브라우저 오라클로 검증한다.
  TASK1: 히트맵 셀 지표를 `수익금(원)` → `수익률 합계(%)` 로 전환.
    - backtest_analysis.time_heatmap 이 셀당 profit_pct_sum(= 그 (요일,슬롯) 거래들의
      profit_pct 합) 필드를 제공한다. 빈 입력 무예외 계약 유지.
    - BtHeatmap(backtest-charts.jsx) 이 profit_pct_sum 을 1차 지표로 쓰고
      "수익률 합계" + "%" 라벨/범례를 노출한다.
  TASK2: 날짜 X축에 연도(YYYY) 정보, Y축에 양끝 외 중간 눈금 라벨을 추가.
    - chart.jsx / backtest-charts.jsx 에 연도 포맷터(YYYY-MM-DD)와 _axisTicks/_btAxisTicks
      (중간 눈금) 가 존재하고 실제 렌더에 쓰인다.
  + 두 JSX 가 vendor-babel(브라우저 동일 엔진)로 문법 무결하게 트랜스폼.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.dashboard import backtest_analysis as A  # noqa: E402

FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"


# ---------------------------------------------------------------------------
# 합성 트레이드 헬퍼 — time_heatmap 이 읽는 최소 필드(buy_time, profit_pct, profit_krw).
# ---------------------------------------------------------------------------
def _trade(buy: str, pct: float, krw: float) -> dict:
    return {"buy_time": buy, "profit_pct": float(pct), "profit_krw": float(krw)}


# ============================================================================
# TASK1 — 백엔드: time_heatmap 수익률 합계(profit_pct_sum) 집계.
# ============================================================================
def test_heatmap_cell_value_is_return_pct_sum() -> None:
    """한 (요일,슬롯) 셀의 profit_pct_sum 이 그 셀 거래들의 profit_pct 합과 같다."""
    # 2025-04-07 = 월요일(weekday 0). 09:30 → slot=(9*60+30)//30=19.
    #   같은 셀에 3건(+2.0, -1.0, +0.5), 다른 슬롯에 1건을 둬 셀 분리도 확인.
    trades = [
        _trade("202504070930", 2.0, 20000),
        _trade("202504070935", -1.0, -10000),
        _trade("202504070945", 0.5, 5000),
        _trade("202504071030", 3.0, 30000),  # 10:30 → slot 21(별도 셀).
    ]
    hm = A.time_heatmap(trades)
    cells = {(c["weekday"], c["slot"]): c for c in hm["cells"]}

    mon_0930 = cells[(0, 19)]
    # 핵심 단언 — 셀 값 = 수익률(%) 합계.
    assert mon_0930["profit_pct_sum"] == pytest.approx(2.0 - 1.0 + 0.5)  # = 1.5
    assert mon_0930["trades"] == 3
    # 수익금도 함께 보존(저렴하면 유지) — 비교 보조용.
    assert mon_0930["profit_krw"] == pytest.approx(20000 - 10000 + 5000)

    mon_1030 = cells[(0, 21)]
    assert mon_1030["profit_pct_sum"] == pytest.approx(3.0)
    assert mon_1030["trades"] == 1


def test_heatmap_pct_sum_separates_weekdays() -> None:
    """요일이 다르면 셀이 분리되고 각자의 수익률 합계를 갖는다."""
    trades = [
        _trade("202504070930", 4.0, 1),   # 월(weekday 0)
        _trade("202504080930", -2.5, 1),  # 화(weekday 1) 같은 슬롯
    ]
    hm = A.time_heatmap(trades)
    by_wd = {c["weekday"]: c for c in hm["cells"]}
    assert by_wd[0]["profit_pct_sum"] == pytest.approx(4.0)
    assert by_wd[1]["profit_pct_sum"] == pytest.approx(-2.5)


def test_heatmap_empty_input_no_raise_and_shape() -> None:
    """빈 입력 무예외 — cells 비고, 셀 스키마에 profit_pct_sum 키 존재(거래 있을 때)."""
    assert A.time_heatmap([]) == {"cells": []}
    one = A.time_heatmap([_trade("202504070930", 1.23, 100)])
    assert one["cells"], "거래 1건이면 셀 1개"
    cell = one["cells"][0]
    for key in ("weekday", "slot", "slot_label", "profit_pct_sum", "profit_krw", "trades"):
        assert key in cell, f"셀에 {key} 필드 누락"
    assert cell["profit_pct_sum"] == pytest.approx(1.23)


def test_heatmap_skips_unparseable_buy_time_no_raise() -> None:
    """매수시각이 12자리 미만/비정상이면 건너뛰되 예외 없이 정상 셀만 남는다."""
    trades = [
        _trade("2025", 9.9, 1),          # 너무 짧음 → 스킵
        _trade("20259999XXYY", 9.9, 1),  # 파싱 실패 → 스킵
        _trade("202504070930", 1.0, 1),  # 정상
    ]
    hm = A.time_heatmap(trades)
    assert len(hm["cells"]) == 1
    assert hm["cells"][0]["profit_pct_sum"] == pytest.approx(1.0)


# ============================================================================
# TASK1 — 프런트: BtHeatmap 이 수익률 합계(%) 를 셀 지표로 사용.
# ============================================================================
def test_btheatmap_uses_return_pct_metric_and_label() -> None:
    # P5.1 분해 — BtHeatmap 은 backtest-charts.jsx(배럴)에서 bt-distribution-charts.jsx 로 이동.
    src = (FRONTEND / "bt-distribution-charts.jsx").read_text(encoding="utf-8")
    # 백엔드 새 필드를 1차 지표로 소비한다.
    assert "profit_pct_sum" in src, "BtHeatmap 이 profit_pct_sum 을 사용해야 한다"
    # 사용자 표현(수익률 합계) + % 단위 라벨이 노출된다.
    assert "수익률 합계" in src, "히트맵 라벨/범례에 '수익률 합계' 표기 필요"
    # % 부호 라벨 포맷터(예: "+12.3%") 존재.
    assert "cellPctLabel" in src
    assert "%" in src
    # 헤더 부제가 더 이상 '손익 합'(수익금 합계) 단독이 아님 — 수익률 기준 전환 확인.
    assert "수익률 합계(%)" in src


# ============================================================================
# TASK2 — 프런트: 날짜 X축 연도 보강 + Y축 중간 눈금.
# ============================================================================
def test_backtest_charts_axis_year_and_yticks() -> None:
    # P5.1 분해 — 축 헬퍼(_btDateLabelY/_btAxisTicks)는 bt-chart-utils.jsx 에 정의되고
    #   bt-equity-charts.jsx·bt-distribution-charts.jsx 에서 사용된다. 정의+사용을 합쳐 검증.
    src = "\n".join(
        (FRONTEND / f).read_text(encoding="utf-8")
        for f in ("bt-chart-utils.jsx", "bt-equity-charts.jsx", "bt-distribution-charts.jsx")
    )
    # 연도 포함 날짜 포맷터(YYYY-MM-DD)와 그 호출.
    assert "_btDateLabelY" in src, "연도 보강 날짜 포맷터 누락"
    # 중간 눈금 헬퍼와 실제 사용(여러 y 눈금 라벨 렌더).
    assert "_btAxisTicks" in src, "중간 눈금 헬퍼 누락"
    # 헬퍼가 정의만 되고 안 쓰이면 안 된다 — 정의 1 + 사용 ≥1.
    assert src.count("_btAxisTicks") >= 2, "_btAxisTicks 가 렌더에 실제 사용돼야 한다"
    assert src.count("_btDateLabelY") >= 2, "_btDateLabelY 가 x축 렌더에 실제 사용돼야 한다"
    # 연도 포맷이 슬라이스 기반 YYYY 를 만든다(0~4 자리).
    assert "slice(0, 4)" in src


def test_chart_jsx_axis_year_and_yticks() -> None:
    src = (FRONTEND / "chart.jsx").read_text(encoding="utf-8")
    # BacktestDetailChart 날짜 X축에 연도 보강 포맷터.
    assert "fmtDateY" in src, "chart.jsx 연도 보강 날짜 포맷터 누락"
    assert src.count("fmtDateY") >= 2, "fmtDateY 가 x축 렌더에 실제 사용돼야 한다"
    # 중간 눈금 헬퍼 + 실제 사용(ProfitChart·BacktestDetailChart 양 축).
    assert "_axisTicks" in src, "chart.jsx 중간 눈금 헬퍼 누락"
    assert src.count("_axisTicks") >= 3, "_axisTicks 가 여러 차트 축에 실제 사용돼야 한다"
    # 연도 포맷이 YYYY 를 만든다.
    assert "slice(0, 4)" in src


# ============================================================================
# vendor-babel 트랜스폼 — 두 JSX 가 브라우저 동일 엔진으로 문법 무결.
# ============================================================================
def test_phase8_jsx_transforms_with_vendor_babel(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node 미설치 — 브라우저 babel 트랜스폼 검증 생략")
    if not (FRONTEND.parent / "webui-build" / "node_modules" / "esbuild").exists():
        pytest.skip("esbuild 미설치(webui-build/node_modules gitignored) — 트랜스폼 검증 생략")
    script = r"""
const fs = require('fs');
const path = require('path');
const dir = process.argv[2];
const esbuild = require(path.join(dir, '..', 'webui-build', 'node_modules', 'esbuild'));
const files = ['backtest-charts.jsx', 'chart.jsx'];
let ok = true;
for (const f of files) {
  try { esbuild.transformSync(fs.readFileSync(path.join(dir, f), 'utf8'), { loader: 'jsx', jsx: 'transform', jsxFactory: 'React.createElement', jsxFragment: 'React.Fragment' }); }
  catch (e) { ok = false; console.error('FAIL ' + f + ': ' + e.message); }
}
process.exit(ok ? 0 : 1);
"""
    script_path = tmp_path / "check.js"
    script_path.write_text(script, encoding="utf-8")
    result = subprocess.run(
        [node, str(script_path), str(FRONTEND)],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, f"babel transform failed: {result.stderr}"
