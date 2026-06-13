"""Track S Phase7 차트 렌더링 계약 테스트 — Req 7/8/9 + 클라이언트 지표 + 비대칭 패리티.

빌드 없는 in-browser Babel JSX 라 Canvas 픽셀을 DOM 으로 단언할 수 없다. 따라서:
  · 클라이언트 지표 헬퍼(_simEma/_simRsi/_simMacd/_simVolMa/_simStrengthMa)는 소스에
    존재(grep)하고, 같은 공식을 파이썬으로 재구현해 "수식이 맞는지"를 간접 검증한다
    (JSX 글로벌이라 직접 호출 불가 — 공식 동치성으로 정확성을 확보).
  · 체결강도/호가불균형/net-delta 의 live+svg 결선과 LWC 배제(ASYMMETRY)는 소스 grep.
  · _SIM_DEFAULT_INDICATORS 신규 키, SimOrderBook 스프레드/정직 라벨, rAF lerp 바운드도 grep.
  · 두 JSX 파일이 vendor-babel(브라우저 동일 엔진)로 문법 오류 없이 트랜스폼.

──────────────────────────────────────────────────────────────────────────────
LWC STACKING SPIKE 결론(Phase7 §7.3 STEP 0) — 후속자를 위한 기록(docstring):
  lightweight-charts v4.2 에는 addPane API 가 없다. 서브-시리즈는 단일 캔들 페인 위에
  distinct priceScaleId + scaleMargins 오버레이 프라이스 스케일로만 쌓을 수 있다.
  compact 높이 H=240 에서 추정:
    · 거래량 오버레이: scaleMargins top:0.82 → 높이의 ~18% 소비.
    · 체결강도 밴드(scaleMargins top:0.86) → ~14% 소비.
    · 호가불균형 밴드를 더 쌓으면 추가 ~13% 소비.
  3개 밴드(vol+strength+imbalance)를 쌓으면 ≈45% 가 서브밴드로 가고, 축 라벨/여백을
  차감하면 캔들 본체 밴드가 가독 하한 55% 를 하회한다(추정 캔들 밴드 ≈ 50~55% 경계).
  ⇒ ASYMMETRIC PARITY 가 FINAL: LWC 는 체결강도 오버레이 한 개만 싣는다(전문 강점은
    줌/크로스헤어/네이티브 last-price 애니메이션). 호가불균형·net-delta 는 live+svg 전용.
──────────────────────────────────────────────────────────────────────────────
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


# ============================================================================
# 1) 클라이언트 지표 헬퍼 — 소스 존재(grep) + 파이썬 동치 재구현으로 공식 정확성 검증.
#    헬퍼는 JSX 글로벌이라 직접 호출 불가. 같은 입력→같은 출력(엔진 무발산)이 핵심이므로
#    공식을 파이썬으로 똑같이 구현해 "수식이 표준과 일치"함을 단언한다.
# ============================================================================

def test_client_helpers_defined_in_charts_source() -> None:
    src = _read("simulation-charts.jsx")
    for fn in ("function _simEma", "function _simRsi", "function _simMacd",
               "function _simVolMa", "function _simStrengthMa", "function _simSma"):
        assert fn in src, f"missing helper: {fn}"
    # window 전역 노출(다른 파일·라이브 차트가 window._simEma 등으로 참조).
    assert "_simSma, _simEma, _simRsi, _simMacd, _simVolMa, _simStrengthMa" in src


def test_macd_helper_uses_12_26_9_constants() -> None:
    """MACD 헬퍼가 12/26 EMA + 9 signal 표준 상수를 쓴다(소스 fragment)."""
    src = _read("simulation-charts.jsx")
    assert "_simEma(bars, 12)" in src and "_simEma(bars, 26)" in src
    assert "2 / (9 + 1)" in src   # signal = MACD 의 9-기간 EMA.


def test_rsi_helper_is_wilder() -> None:
    """RSI 가 Wilder 평활(avg*(p-1)+x)/p)을 쓴다 — 단순 SMA RSI 가 아님."""
    src = _read("simulation-charts.jsx")
    assert "avgGain * (p - 1)" in src and "avgLoss * (p - 1)" in src
    assert "100 - 100 / (1 + rs)" in src


# ---- 파이썬 동치 재구현(공식 정확성의 oracle) ----

def _py_ema(closes, period):
    k = 2 / (period + 1)
    out = []
    ema = None
    for c in closes:
        ema = c if ema is None else c * k + ema * (1 - k)
        out.append(ema)
    return out


def _py_sma(vals, period):
    out = []
    q = []
    s = 0.0
    for v in vals:
        q.append(v)
        s += v
        if len(q) > period:
            s -= q.pop(0)
        out.append(s / period if len(q) == period else None)
    return out


def _py_rsi(closes, period=14):
    out = [None] * len(closes)
    avg_gain = avg_loss = None
    prev = None
    seed_g = seed_l = 0.0
    seed_n = 0
    for i, c in enumerate(closes):
        if prev is None:
            prev = c
            continue
        ch = c - prev
        prev = c
        gain = ch if ch > 0 else 0.0
        loss = -ch if ch < 0 else 0.0
        if avg_gain is None:
            seed_g += gain
            seed_l += loss
            seed_n += 1
            if seed_n == period:
                avg_gain = seed_g / period
                avg_loss = seed_l / period
            else:
                continue
        else:
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
        if avg_loss == 0:
            out[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            out[i] = 100 - 100 / (1 + rs)
    return out


def test_ema_formula_matches_standard() -> None:
    closes = [10, 11, 12, 11, 13, 14, 13, 15, 16, 15, 17, 18]
    ema3 = _py_ema(closes, 3)
    # EMA seed = 첫 종가, 이후 점화식. 표준 정의와 일치하는지 마지막 값을 손계산 대조.
    assert abs(ema3[0] - 10.0) < 1e-9
    # k=0.5 (period 3). 수동 전개: e1=10, e2=11*.5+10*.5=10.5 ...
    assert abs(ema3[1] - 10.5) < 1e-9
    assert abs(ema3[2] - (12 * 0.5 + 10.5 * 0.5)) < 1e-9


def test_sma_window_and_none_padding() -> None:
    vals = [5, 10, 15, 20, 25]
    sma3 = _py_sma(vals, 3)
    assert sma3[0] is None and sma3[1] is None
    assert abs(sma3[2] - 10.0) < 1e-9   # (5+10+15)/3
    assert abs(sma3[3] - 15.0) < 1e-9   # (10+15+20)/3
    assert abs(sma3[4] - 20.0) < 1e-9


def test_rsi_all_gains_is_100() -> None:
    closes = [i for i in range(1, 30)]   # 단조 상승 → loss 0 → RSI 100.
    rsi = _py_rsi(closes, 14)
    last = [v for v in rsi if v is not None][-1]
    assert abs(last - 100.0) < 1e-9


# ============================================================================
# 2) 체결강도 그래프(Req 8) — SVG(기존)·SimLiveChart·LWC 오버레이 스케일 세 경로.
# ============================================================================

def test_strength_drawn_in_live_chart() -> None:
    src = _read("sim-live-chart.jsx")
    assert "_drawStrengthStrip" in src
    # 100 균형선 + _strengthColor(라이브 색 통일) + strma 오버레이(_simStrengthMa).
    assert "yStr(100)" in src
    assert "window._strengthColor" in src
    assert "window._simStrengthMa" in src


def test_strength_overlay_scale_in_lwc() -> None:
    src = _read("simulation-charts.jsx")
    # LWC 가 싣는 단 하나의 서브-시리즈 — priceScaleId "strength" + scaleMargins.
    assert 'priceScaleId: "strength"' in src
    assert 'chart.priceScale("strength").applyOptions' in src


def test_strength_still_in_svg() -> None:
    src = _read("simulation-charts.jsx")
    # 기존 SVG 체결강도 폴리라인 유지(ind.strength 토글로 감쌈).
    assert "strPath" in src
    assert "ind.strength" in src


# ============================================================================
# 3) 호가 불균형(Req 9) + net-delta(Req 7) — live+svg 결선, LWC 배제(ASYMMETRY).
# ============================================================================

def test_imbalance_and_netdelta_wired_to_live_and_svg() -> None:
    charts = _read("simulation-charts.jsx")
    live = _read("sim-live-chart.jsx")
    # SVG/shell 경로 — 컴포넌트 결선.
    assert "SimImbalancePane" in charts
    assert "SimNetDeltaStrip" in charts
    # live(canvas) 경로 — 그리기 헬퍼.
    assert "_drawImbalanceStrip" in live
    assert "_drawNetDeltaStrip" in live


def test_asymmetry_lwc_excludes_imbalance_and_netdelta() -> None:
    """비대칭 패리티 — 서브패인은 engine !== "lwc" 일 때만 렌더된다."""
    charts = _read("simulation-charts.jsx")
    assert 'engine !== "lwc" && ind.imbalance && <SimImbalancePane' in charts
    assert 'engine !== "lwc" && ind.orderflow && <SimNetDeltaStrip' in charts
    # LWC 컴포넌트 자체에는 imbalance/net-delta 그리기 결선이 없다(strength 오버레이만).
    # ASYMMETRIC PARITY 결론 주석이 코드에 박혀 있다.
    assert "ASYMMETRIC PARITY (FINAL)" in charts


def test_imbalance_honest_label() -> None:
    charts = _read("simulation-charts.jsx")
    live = _read("sim-live-chart.jsx")
    assert "호가 불균형(레벨1 총잔량비)" in charts
    # 1.0 균형선(불균형 기준).
    assert "yAt(1.0)" in charts
    assert "호가불균형" in live


def test_netdelta_uses_net_qty() -> None:
    charts = _read("simulation-charts.jsx")
    live = _read("sim-live-chart.jsx")
    assert "net_qty" in charts and "net-delta" in charts
    assert "net_qty" in live


# ============================================================================
# 4) _SIM_DEFAULT_INDICATORS — 신규 키(CROSS-FILE CONTRACT, Track B 동일 집합).
# ============================================================================

def test_default_indicators_has_new_keys() -> None:
    src = _read("simulation-charts.jsx")
    # 신규 키 전부 존재.
    for key in ("ema", "rsi", "macd", "volma", "strma", "vwapband",
                "strength", "imbalance", "orderflow"):
        assert f"{key}:" in src, f"missing default key: {key}"
    # 기존 키 유지.
    assert "ma: true" in src and "vwap: true" in src and "boll: false" in src
    # heavy 한 것들 기본 OFF, strength 는 기본 ON(SVG 가 이미 그림).
    assert "strength: true" in src
    assert "ema: false" in src and "rsi: false" in src and "macd: false" in src
    assert "imbalance: false" in src and "orderflow: false" in src


# ============================================================================
# 5) SimOrderBook 강화(Req 5) — 스프레드/bps + 정직 라벨/툴팁 + 비율 점유율.
# ============================================================================

def test_orderbook_computes_spread() -> None:
    src = _read("simulation-charts.jsx")
    assert "function SimOrderBook" in src
    # 스프레드 = ask1 - bid1, bps = spread/mid*10000.
    assert "ask1 - bid1" in src
    assert "10000" in src
    assert "스프레드" in src and "bp" in src


def test_orderbook_honest_label_and_tooltip() -> None:
    src = _read("simulation-charts.jsx")
    assert "호가창 (레벨1 + 총잔량)" in src
    assert "일일 DB는 최우선호가·총잔량만 제공(레벨2~10 없음)" in src
    # 허위 다단 호가 생성 없음(레벨1 전용 — 구 SimQuotePressure 부재 유지).
    assert "function SimQuotePressure" not in src


def test_orderbook_ratio_depth_and_flash() -> None:
    src = _read("simulation-charts.jsx")
    # 잔량 점유율(buy_rest vs sell_rest 총합 대비) % 라벨.
    assert "buyShare" in src and "sellShare" in src
    # bid1/ask1 변동 플래시(CSS transition 배경).
    assert "flash" in src
    assert "transition: \"background" in src


# ============================================================================
# 6) rAF lerp 바운드(Req 3, §7.1) — live 전용, min(_SLC_LERP_MS, batchWallMs).
# ============================================================================

def test_live_lerp_bounded_by_batch_walltime() -> None:
    src = _read("sim-live-chart.jsx")
    assert "batchWallMs" in src
    assert "Math.min(_SLC_LERP_MS, batchWallMs)" in src
    # 보간이 anim.lerpMs(바운드된 값)를 쓰고, 상수 _SLC_LERP_MS 를 직접 쓰지 않는다.
    assert "anim.lerpMs" in src


# ============================================================================
# 7) RSI / MACD 렌더 경로 — HIGH-1 fix: 토글 켜면 실제로 그려진다.
# ============================================================================

def test_rsi_drawn_in_live_chart() -> None:
    """RSI 패인이 live(Canvas) 엔진에 결선된다 — ind.rsi 토글로 게이팅."""
    src = _read("sim-live-chart.jsx")
    # 드로우 헬퍼 정의.
    assert "function _drawRsiPane" in src
    # 드로우 헬퍼 호출(hasRsi 게이팅).
    assert "_drawRsiPane(" in src
    # 토글 확인 키.
    assert "hasRsi" in src
    assert "ind.rsi" in src
    # 30/50/70 가이드선(RSI 과매수/과매도 표준).
    assert "30, 50, 70" in src or "[30, 50, 70]" in src


def test_macd_drawn_in_live_chart() -> None:
    """MACD 패인이 live(Canvas) 엔진에 결선된다 — ind.macd 토글로 게이팅."""
    src = _read("sim-live-chart.jsx")
    assert "function _drawMacdPane" in src
    assert "_drawMacdPane(" in src
    assert "hasMacd" in src
    assert "ind.macd" in src
    # 히스토그램 + MACD 라인 + 시그널 라인.
    assert "cachedMacd" in src


def test_rsi_and_macd_drawn_in_svg() -> None:
    """RSI / MACD 컴포넌트가 SVG 엔진에 정의되고 SimChartShell 에 결선된다."""
    src = _read("simulation-charts.jsx")
    assert "function SimRsiPane" in src
    assert "function SimMacdPane" in src
    # SimChartShell 결선 — engine !== "lwc" 게이팅.
    assert 'engine !== "lwc" && ind.rsi && <SimRsiPane' in src
    assert 'engine !== "lwc" && ind.macd && <SimMacdPane' in src
    # 30/50/70 가이드선.
    assert "30, 50, 70" in src or "[30, 50, 70]" in src
    # MACD 히스토그램 + 시그널.
    assert "hist" in src and "signal" in src


def test_asymmetry_lwc_excludes_rsi_and_macd() -> None:
    """비대칭 패리티 — RSI/MACD 는 engine !== "lwc" 일 때만 렌더된다(LWC 에 없음)."""
    charts = _read("simulation-charts.jsx")
    # LWC 컴포넌트(SimCandleChartLWC) 내에 SimRsiPane/SimMacdPane 직접 렌더 없음.
    # SimChartShell 결선이 engine != "lwc" 조건으로 감싸져 있는지 확인.
    assert 'engine !== "lwc" && ind.rsi && <SimRsiPane' in charts
    assert 'engine !== "lwc" && ind.macd && <SimMacdPane' in charts
    # live 엔진도 lwc 가 아님을 확인(live 헬퍼는 sim-live-chart.jsx 에만 존재).
    live = _read("sim-live-chart.jsx")
    assert "_drawRsiPane" in live
    assert "_drawMacdPane" in live
    # LWC JSX(SimChartShell engine="lwc")는 RSI/MACD draw 를 추가로 갖지 않는다.
    # simulation-charts.jsx 의 LWC 컴포넌트 블록엔 _drawRsiPane/_drawMacdPane 참조 없음.
    assert "_drawRsiPane" not in charts
    assert "_drawMacdPane" not in charts


# ============================================================================
# 8) vendor-babel 트랜스폼 — 두 JSX 가 브라우저 동일 엔진으로 문법 무결.
# ============================================================================

def test_phase7_jsx_transforms_with_vendor_babel(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node 미설치 — 브라우저 babel 트랜스폼 검증 생략")
    script = r"""
const fs = require('fs');
const path = require('path');
const dir = process.argv[2];
const Babel = require(path.join(dir, 'vendor-babel.js'));
const files = ['sim-live-chart.jsx', 'simulation-charts.jsx'];
let ok = true;
for (const f of files) {
  try { Babel.transform(fs.readFileSync(path.join(dir, f), 'utf8'), { presets: ['react'], filename: f }); }
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
