"""Track S 프런트엔드 계약 테스트 — S1/S2/S3/S4/S5 (Phase6).

빌드 없는 in-browser Babel JSX 라 텍스트 계약 + 벤더 babel 트랜스폼으로 검증한다
(기존 dashboard 테스트 관행: 소스 substring 단언 + window 전역 등록 확인).

- S1: simulation.jsx 가 immutable append(새 배열 참조) 로 봉·거래량 동결 결함을 고친다.
- S2: 동시보기 10개 상한 + 반응형 그리드(_responsiveCols).
- S3: simulation-charts.jsx 에 SimFootprint(오더플로우 가격 사다리).
- S4: sim-live-chart.jsx 가 window.SimLiveChart(Canvas 라이브) 를 노출, 기본 엔진 라이브.
- S5: SimOrderBook(HTS형 호가 사다리)로 호가 시각화 강화.
- 세 JSX 파일이 vendor-babel 로 트랜스폼된다(문법 무결).
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


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


# ----------------------------------------------------------------- S1 결함 수정
def test_s1_immutable_append_fixes_frozen_candles() -> None:
    """simulation.jsx bars 핸들러가 push() mutate 가 아닌 새 배열 참조로 append 한다."""
    src = _read("simulation.jsx")
    # 새 배열 참조 생성(불변 append) — LWC useEffect([bars]) 매 프레임 재실행 조건.
    #   Phase6.1 에서 bar 생성이 공용 매퍼 _simWsBar 로 추출됐다("history" 스냅샷과 공유).
    assert "store[it.code] = [...(store[it.code] || []), _simWsBar(it, m.t)]" in src
    # 옛 결함 패턴(push 로 동일 배열 mutate)이 bars 핸들러에서 제거됐다.
    assert "store[it.code].push(" not in src


# -------------------------------------------------------------------- S2 동시보기
def test_s2_max_codes_is_ten() -> None:
    src = _read("simulation.jsx")
    assert "_SIM_MAX_CODES = 10" in src


def test_s2_responsive_grid_helper() -> None:
    src = _read("simulation.jsx")
    assert "_responsiveCols" in src
    # 개수→열 매핑(2~4→2 / 5~9→3 / 10→4) 의도가 코드에 있다.
    assert "repeat(" in src


def test_s2_dense_compact_for_five_plus() -> None:
    src = _read("simulation.jsx")
    # 5개 이상 컴팩트 모드.
    assert "codes.length >= 5" in src


# ------------------------------------------------------------------- S4 라이브 차트
def test_s4_live_chart_file_exists_and_exposes_global() -> None:
    src = _read("sim-live-chart.jsx")
    assert "function SimLiveChart" in src
    assert "Object.assign(window, { SimLiveChart" in src
    # Canvas 라이브 연출 핵심 — rAF 루프·lerp 성장·devicePixelRatio.
    assert "requestAnimationFrame" in src
    assert "devicePixelRatio" in src
    assert "_lerp" in src


def test_s4_live_is_default_engine_mode() -> None:
    src = _read("simulation.jsx")
    # 엔진 모드 기본값 라이브(_loadEngineMode 기본 'live').
    assert '_SIM_ENGINE_MODES' in src
    assert '"라이브"' in src
    assert 'return (v === "lwc" || v === "svg" || v === "live") ? v : "live"' in src
    # 디스패처가 라이브 우선.
    assert "SimChartByEngine" in src


# ------------------------------------------------------------------- S3 footprint
def test_s3_footprint_component() -> None:
    src = _read("simulation-charts.jsx")
    assert "function SimFootprint" in src
    # 매수/매도 체결 분리 — net_qty 실데이터 우선 + 강도 휴리스틱 폴백(정직 표기).
    assert "_barBuySell" in src
    assert "net_qty" in src
    assert "강도 근사" in src
    # 가격 사다리·델타 컬럼.
    assert "델타" in src


# --------------------------------------------------------------------- S5 호가창
def test_s5_orderbook_replaces_quote_pressure() -> None:
    src = _read("simulation-charts.jsx")
    assert "function SimOrderBook" in src
    # 레벨1 + 총잔량 정직 표기(허위 다단 호가 금지).
    assert "레벨1 + 총잔량" in src
    # 총매도/총매수 footer + 체결강도 배지.
    assert "총매도" in src and "총매수" in src
    assert "체결강도" in src
    # 구 SimQuotePressure 는 제거됐다(SimOrderBook 으로 대체).
    assert "function SimQuotePressure" not in src


def test_new_components_registered_on_window() -> None:
    src = _read("simulation-charts.jsx")
    assert "SimFootprint, SimOrderBook" in src
    # SVG/LWC 개별 엔진도 window 노출(엔진 토글 지원).
    assert "SimCandleChartLWC, SimCandleChartSVG" in src


# ------------------------------------------------------------- vendor-babel 트랜스폼
def test_phase6_jsx_transforms_with_vendor_babel(tmp_path: Path) -> None:
    """세 JSX 파일이 vendor-babel(브라우저와 동일 엔진) 로 문법 오류 없이 트랜스폼된다."""
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
const files = ['sim-live-chart.jsx', 'simulation.jsx', 'simulation-charts.jsx'];
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
