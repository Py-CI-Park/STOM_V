"""Phase13-S 시뮬 차트 계약 테스트 — C-3(LWC 신호 마커 패리티) + C-4(체결 로그 CSV 내보내기).

빌드 없는 in-browser Babel JSX 라 DOM/Canvas 를 직접 단언할 수 없다. 따라서:
  · C-3: SimCandleChartLWC 가 signals 로부터 markers 배열을 만들어 candle.setMarkers(markers)
    를 호출하고(빈 배열만 거는 죽은 분기가 아님), curT 게이트로 도달분만 그리며 매수/매도
    마커 시맨틱(belowBar/aboveBar·arrowUp/arrowDown·매수 라벨)이 SVG/live 와 일치함을 grep.
  · C-4: SimSignalLog 패널 헤더에 'CSV 내보내기' 버튼 + Blob 다운로드 + 컬럼 헤더 + utf-8 BOM
    이 존재함을 grep.
  · simulation-charts.jsx 가 vendor-babel(브라우저 동일 엔진)로 문법 오류 없이 트랜스폼.
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

FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"
SIM_JSX = FRONTEND / "simulation-charts.jsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _slice(src: str, start_marker: str, end_marker: str) -> str:
    """start_marker 부터 end_marker 직전까지 잘라 해당 컴포넌트/함수 범위만 검사한다."""
    i = src.index(start_marker)
    j = src.index(end_marker, i + len(start_marker))
    return src[i:j]


# ============================================================================
# C-3) LWC 신호 마커 패리티 — SimCandleChartLWC 가 실제로 markers 를 그린다.
# ============================================================================

def test_c3_lwc_marker_effect_builds_markers_from_signals() -> None:
    """SimCandleChartLWC 범위 안에서 signals 순회로 markers 를 채우고 setMarkers 로 전달한다."""
    src = _read(SIM_JSX)
    lwc = _slice(src, "function SimCandleChartLWC", "function SimCandleChartSVG")
    # signals 순회 + markers 배열 push.
    assert "(signals || []).forEach" in lwc
    assert "markers.push(" in lwc
    # setMarkers 를 비어있지 않은 markers 배열로 호출(죽은 분기가 아님).
    assert "candle.setMarkers(markers)" in lwc


def test_c3_lwc_markers_gated_by_curt() -> None:
    """매수/매도 마커가 curT 도달분만(curT == null || hms <= curT) 그려진다 — SVG/live 와 동일 게이트."""
    src = _read(SIM_JSX)
    lwc = _slice(src, "function SimCandleChartLWC", "function SimCandleChartSVG")
    assert "curT == null || sig.buy_hms <= curT" in lwc
    assert "curT == null || sig.sell_hms <= curT" in lwc


def test_c3_lwc_marker_semantics_match_svg_live() -> None:
    """매수=belowBar/arrowUp/teal/매수, 매도=aboveBar/arrowDown/red — SVG(▲teal/▼red)·live 와 일치."""
    src = _read(SIM_JSX)
    lwc = _slice(src, "function SimCandleChartLWC", "function SimCandleChartSVG")
    # 매수 마커.
    assert 'position: "belowBar"' in lwc
    assert 'shape: "arrowUp"' in lwc
    assert 'text: "매수"' in lwc
    assert '"#4cd6b3"' in lwc  # teal — SVG var(--teal) 와 동일 색.
    # 매도 마커.
    assert 'position: "aboveBar"' in lwc
    assert 'shape: "arrowDown"' in lwc
    assert '"#ff5d6c"' in lwc  # red — SVG var(--red) 와 동일 색.


def test_c3_lwc_marker_setmarkers_is_not_only_empty() -> None:
    """죽은 분기 회귀 방지: setMarkers 가 항상 빈 배열([])만 받는 형태가 아니어야 한다."""
    src = _read(SIM_JSX)
    lwc = _slice(src, "function SimCandleChartLWC", "function SimCandleChartSVG")
    # 빈-배열 clear(early-return)는 허용되지만, 채워진 markers 호출이 반드시 존재해야 한다.
    assert lwc.count("setMarkers(") >= 2  # 빈배열 clear + markers 전달 둘 다.
    assert "candle.setMarkers(markers)" in lwc


# ============================================================================
# C-4) 체결 로그 CSV 내보내기 — SimSignalLog 헤더 버튼 + Blob 다운로드.
# ============================================================================

def test_c4_signal_log_has_csv_export_button() -> None:
    """SimSignalLog 범위 안에 'CSV 내보내기' 버튼이 존재하고 다운로드 핸들러에 연결된다."""
    src = _read(SIM_JSX)
    log = _slice(src, "function SimSignalLog", "Object.assign(window")
    assert "CSV 내보내기" in log
    assert "_simDownloadSignalLogCsv(rows)" in log
    # 0건일 때 버튼 숨김(rows.length > 0 게이트).
    assert "rows.length > 0 &&" in log


def test_c4_csv_blob_download_clientside() -> None:
    """백엔드 없이 Blob + a[download] 클릭으로 클라이언트 다운로드한다."""
    src = _read(SIM_JSX)
    dl = _slice(src, "function _simDownloadSignalLogCsv", "function SimSignalLog")
    assert "new Blob(" in dl
    assert "text/csv" in dl
    assert "URL.createObjectURL" in dl
    assert ".download = fname" in dl or "a.download" in dl
    assert ".click()" in dl
    # 파일명 체결로그_YYYY-MM-DD.csv.
    assert '"체결로그_"' in dl
    assert '".csv"' in dl


def test_c4_csv_has_column_headers() -> None:
    """CSV 헤더 컬럼: 매수시간·매도시간·매수가·매도가·수익률(%) (+ 종목코드 조건부)."""
    src = _read(SIM_JSX)
    csvfn = _slice(src, "function _simSignalLogCsv", "function _simDownloadSignalLogCsv")
    for col in ("매수시간", "매도시간", "매수가", "매도가", "수익률(%)"):
        assert col in csvfn, f"누락된 CSV 컬럼: {col}"
    # 종목코드는 행에 code 가 있을 때만 조건부 포함.
    assert "종목코드" in csvfn
    assert "hasCode" in csvfn


def test_c4_csv_has_utf8_bom() -> None:
    """엑셀 한글 호환 위해 utf-8 BOM(\\ufeff) 을 선행한다."""
    src = _read(SIM_JSX)
    csvfn = _slice(src, "function _simSignalLogCsv", "function _simDownloadSignalLogCsv")
    assert "﻿" in csvfn, "CSV 출력에 utf-8 BOM 이 없습니다"


def test_c4_csv_time_prefers_full_time_then_hms() -> None:
    """시각은 buy_time/sell_time(YYYYMMDDHHMMSS) 우선, 부재 시 hms 폴백(_simTimeLabel)."""
    src = _read(SIM_JSX)
    timefn = _slice(src, "function _simCsvTime", "function _simSignalLogCsv")
    assert "_simTimeLabel(hms)" in timefn
    # full(buy_time/sell_time) 우선 분기.
    assert "full != null" in timefn


# ============================================================================
# 문법 무결 — vendor-babel(브라우저 동일 엔진) 트랜스폼.
# ============================================================================

def test_p13_jsx_transforms_with_vendor_babel(tmp_path: Path) -> None:
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
const f = 'simulation-charts.jsx';
try {
  esbuild.transformSync(fs.readFileSync(path.join(dir, f), 'utf8'), { loader: 'jsx', jsx: 'transform', jsxFactory: 'React.createElement', jsxFragment: 'React.Fragment' });
} catch (e) {
  console.error('FAIL ' + f + ': ' + e.message);
  process.exit(1);
}
process.exit(0);
"""
    script_path = tmp_path / "check.js"
    script_path.write_text(script, encoding="utf-8")
    result = subprocess.run(
        [node, str(script_path), str(FRONTEND)],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, f"babel transform failed: {result.stderr}"
