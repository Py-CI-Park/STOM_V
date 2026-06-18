"""Phase 7 Track B (sim shell + backend) 계약·동작 테스트.

검증 대상(plan §7.0/7.1/7.4/7.6 + acceptance #1~#6):
- replay_engine: 프레임에 server VWAP 밴드(vwap_up/vwap_low)만 추가(윈도우 전 None),
  서버 측 strength_ma5 키는 추가하지 않음(체결강도 MA 는 클라이언트 계산).
- simulation_api: _MAX_SPEED==600, _clamp_speed(600)==600.
- 실측 페이싱 오라클(REAL elapsed): _stream_loop 을 stub _send 로 실제 구동해
  speed=1 의 벽시계 경과 ≈ Σ bar_gap_seconds, 600x 는 그 1/100 미만(분자 산술 아님 — 실측).
- simulation.jsx 소스 계약: _SIM_SPEEDS 에 600, SimViewBar 라벨이 var(--ink-1)/fontWeight:600
  이고 var(--ink-3) 없음, indDefs 새 키, 열(1~5)/splitRows 셀렉터, SimEnginePopover 배선.

실DB/백테 미사용: 합성 SQLite + 소스 substring 단언(기존 dashboard 테스트 관행).
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.dashboard import replay_engine as RE  # noqa: E402
from ai_strategy_loop.dashboard import simulation_api as SA  # noqa: E402

FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"


def _read_frontend(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


# 금액 컬럼을 가진 확장 min 레이아웃(VWAP 밴드 분기 — trade_amt 필요).
_MIN_COLS_FULL = [
    "현재가", "시가", "고가", "저가", "등락율", "당일거래대금",
    "체결강도", "분당매수수량", "분당매도수량",
    "분당매수금액", "분당매도금액",
]


def _make_min_db_full(path: Path, code: str, rows: List[tuple]) -> None:
    con = sqlite3.connect(str(path))
    con.execute('CREATE TABLE moneytop ("index" INTEGER, "x" TEXT)')
    coldef = ", ".join(f'"{c}" REAL' for c in _MIN_COLS_FULL)
    con.execute(f'CREATE TABLE "{code}" ("index" INTEGER, {coldef})')
    ph = ", ".join("?" for _ in range(len(_MIN_COLS_FULL) + 1))
    con.executemany(f'INSERT INTO "{code}" VALUES ({ph})', rows)
    con.commit()
    con.close()


@pytest.fixture
def seeded_band_db(monkeypatch, tmp_path):
    """금액 컬럼을 가진 min DB(20250120) — VWAP 밴드 윈도우(_VWAP_BAND_WINDOW)를 넘기는 봉 수.

    (index, 현재가,시가,고가,저가,등락율,당일거래대금,체결강도,분매수수량,분매도수량,
     분당매수금액,분당매도금액). 종가를 단조 변화시켜 σ>0 인 밴드를 만든다.
    """
    db_dir = tmp_path / "_database"
    db_dir.mkdir()
    n = RE._VWAP_BAND_WINDOW + 6   # 윈도우 충족 전/후가 모두 존재하도록.
    rows = []
    for i in range(n):
        hhmm = 900 + i          # 0900, 0901, ... (분 단위 — 분봉)
        idx = int(f"20250120{hhmm:04d}")
        c = 100.0 + i           # 종가 단조 증가 → typ 분산>0.
        vol_buy, vol_sell = 60.0, 40.0
        amt_buy = c * vol_buy   # 매수금액 = 가격×매수수량(typ≈c 가 되게).
        amt_sell = c * vol_sell
        rows.append((
            idx, c, c, c, c, float(i), 1.0, 100.0, vol_buy, vol_sell,
            amt_buy, amt_sell,
        ))
    _make_min_db_full(db_dir / "stock_min_20250120.db", "005930", rows)
    monkeypatch.setattr(RE, "_DATABASE_DIR", db_dir)
    monkeypatch.setattr(SA, "_DATABASE_DIR", db_dir)
    return db_dir


# ----------------------------------------------------------- §7.0 server VWAP 밴드
class TestVwapBandFrames:
    def test_band_keys_present_and_none_pre_window(self, seeded_band_db):
        """프레임 item 에 vwap_up/vwap_low 가 있고, 윈도우 충족 전엔 None 이다."""
        rd = RE.load_replay(20250120, "min", ["005930"], agg_sec=10)
        items = [f["items"][0] for f in rd.frames]
        assert items, "frames 가 비어 있으면 안 됨"
        # 키 존재(스키마 계약).
        assert "vwap_up" in items[0] and "vwap_low" in items[0]
        w = RE._VWAP_BAND_WINDOW
        # 윈도우 미충족 구간(i < w-1)은 None.
        for i in range(w - 1):
            assert items[i]["vwap_up"] is None, f"bar {i} vwap_up 은 None 이어야 함"
            assert items[i]["vwap_low"] is None, f"bar {i} vwap_low 은 None 이어야 함"
        # 윈도우 충족 후엔 float 이고 밴드가 vwap 를 감싼다(up ≥ vwap ≥ low).
        last = items[-1]
        assert isinstance(last["vwap_up"], float)
        assert isinstance(last["vwap_low"], float)
        assert last["vwap_low"] <= last["vwap"] <= last["vwap_up"]

    def test_no_server_strength_ma5_key(self, seeded_band_db):
        """체결강도 MA 는 클라이언트 계산 — 서버 프레임에 strength_ma5 키를 추가하지 않는다."""
        rd = RE.load_replay(20250120, "min", ["005930"], agg_sec=10)
        for f in rd.frames:
            for it in f["items"]:
                assert "strength_ma5" not in it, "서버는 strength_ma5 를 내보내면 안 됨(클라이언트 계산)"

    def test_band_none_when_amount_columns_absent(self, monkeypatch, tmp_path):
        """금액 컬럼 부재(trade_amt=None) → vwap_up/vwap_low 전부 None(하위호환·무예외)."""
        db_dir = tmp_path / "_database"
        db_dir.mkdir()
        base_cols = [
            "현재가", "시가", "고가", "저가", "등락율", "당일거래대금",
            "체결강도", "분당매수수량", "분당매도수량",
        ]
        con = sqlite3.connect(str(db_dir / "stock_min_20250121.db"))
        con.execute('CREATE TABLE moneytop ("index" INTEGER, "x" TEXT)')
        coldef = ", ".join(f'"{c}" REAL' for c in base_cols)
        con.execute(f'CREATE TABLE "005930" ("index" INTEGER, {coldef})')
        ph = ", ".join("?" for _ in range(len(base_cols) + 1))
        rows = [
            (int(f"20250121{900 + i:04d}"), 100.0 + i, 100.0, 100.0, 100.0,
             float(i), 1.0, 100.0, 60.0, 40.0)
            for i in range(RE._VWAP_BAND_WINDOW + 4)
        ]
        con.executemany(f'INSERT INTO "005930" VALUES ({ph})', rows)
        con.commit()
        con.close()
        monkeypatch.setattr(RE, "_DATABASE_DIR", db_dir)
        rd = RE.load_replay(20250121, "min", ["005930"], agg_sec=10)
        for f in rd.frames:
            it = f["items"][0]
            assert it["vwap_up"] is None and it["vwap_low"] is None

    def test_attach_vwap_band_never_raises_on_empty(self):
        """빈 bar 리스트에도 raise 하지 않는다(무예외 계약)."""
        bars: List[Dict[str, Any]] = []
        RE._attach_vwap(bars)  # no exception
        assert bars == []


# ------------------------------------------------------------- §7.1 speed 600x
class TestSpeed600:
    def test_max_speed_is_600(self):
        assert SA._MAX_SPEED == 600

    def test_clamp_speed_600(self):
        assert SA._clamp_speed(600) == 600
        assert SA._clamp_speed(9999) == 600   # 상한 클램프.
        assert SA._clamp_speed(0) == 1         # 하한 클램프.

    def test_sim_speeds_source_has_600(self):
        # P5.5 분해 — _SIM_SPEEDS 상수는 sim-tab-utils.jsx, 600 라벨 렌더(SimPlaybackBar)는 sim-tab-controls.jsx.
        assert "_SIM_SPEEDS = [1, 5, 20, 60, 240, 600]" in _read_frontend("sim-tab-utils.jsx")
        # 600 라벨 "초고속".
        assert '"초고속"' in _read_frontend("sim-tab-controls.jsx")


# --------------------------------- §acceptance #3 실측 페이싱 오라클(REAL elapsed)
class _RecordingWS:
    """send_json 을 기록만 하는 stub WS(실제 송신 없음·async no-op)."""

    def __init__(self) -> None:
        self.sent: List[Dict[str, Any]] = []

    async def send_json(self, payload: Dict[str, Any]) -> None:
        self.sent.append(payload)


def _tick_frames_one_sec_gaps(n: int) -> List[Dict[str, Any]]:
    """초 단위 gap=1s 인 tick 프레임 n개(각 gap > _FRAME_FLUSH_SLEEP_SEC=0.05s).

    t=090000, 090001, ... → _bar_gap_seconds 가 정확히 1.0 씩(coalesce 없이 매 프레임 paced sleep).
    """
    return [
        {"t": 90000 + i, "items": [{"code": "X", "c": 100.0 + i}]}
        for i in range(n)
    ]


def _run_stream_elapsed(frames: List[Dict[str, Any]], speed: int) -> float:
    """_stream_loop 을 stub _send 로 실제 구동하고 벽시계 경과(초)를 측정한다.

    asyncio.sleep 을 가로채지 않으므로(REAL sleep) 측정값은 실제 페이싱 경과다.
    """
    data = RE.ReplayData(20250120, "tick", ["X"], frames,
                         (frames[0]["t"], frames[-1]["t"]))
    sess = SA.SimReplaySession(_RecordingWS())
    sess.data = data
    sess.speed = speed
    sess.running = True
    start = time.perf_counter()
    asyncio.run(sess._stream_loop())
    elapsed = time.perf_counter() - start
    # 모든 bars + done 전송 확인(루프가 끝까지 돌았다).
    types = [m["type"] for m in sess.ws.sent]
    assert types.count("bars") == len(frames)
    assert types[-1] == "done"
    return elapsed


def test_speed1_elapsed_matches_sum_of_gaps():
    """speed=1 의 실측 벽시계 ≈ Σ bar_gap_seconds.

    페이싱이 _PACED_SLEEP_CHUNK_SEC(0.05s) 청크로 쪼개져 자므로, 청크마다 OS 타이머/스케줄러
    오버헤드가 단조 누적된다(sleep 은 조기 반환 안 함 → 경과는 항상 ≥ 기대). 그래서 허용오차는
    청크 수(expected/chunk)에 비례하는 상한 + 단측 바이어스를 반영한다. 그래도 즉시완료(≈0s)나
    배속 혼동(≈3/600s) 같은 총체적 오류는 잡는다(하한은 기대의 60%).
    """
    frames = _tick_frames_one_sec_gaps(4)   # 3 gaps × 1s = 3.0s 기대.
    expected = sum(
        SA._bar_gap_seconds(frames[i]["t"], frames[i + 1]["t"])
        for i in range(len(frames) - 1)
    )
    assert expected == pytest.approx(3.0)
    elapsed = _run_stream_elapsed(frames, speed=1)
    # 청크당 오버헤드 여유(0.03s/청크) — Windows 타이머 분해능 흡수. 단측(상한) 바이어스.
    chunks = expected / SA._PACED_SLEEP_CHUNK_SEC
    upper = expected + max(0.8, chunks * 0.03)
    lower = expected * 0.6   # 즉시완료·배속 혼동 방어.
    assert lower <= elapsed <= upper, (
        f"speed=1 elapsed={elapsed:.3f}s 는 [{lower:.3f}, {upper:.3f}] 안에 있어야 함 "
        f"(Σgap={expected:.3f}s, chunks≈{chunks:.0f})"
    )


def test_speed600_elapsed_is_tiny_fraction():
    """600x 실측 경과는 1x 경과의 1/100 미만(견고한 단측 경계 — 분자 산술 아님)."""
    frames = _tick_frames_one_sec_gaps(4)
    elapsed_1x = _run_stream_elapsed(frames, speed=1)
    elapsed_600x = _run_stream_elapsed(frames, speed=600)
    assert elapsed_600x < elapsed_1x / 100.0, (
        f"600x elapsed={elapsed_600x:.4f}s 는 1x/100={elapsed_1x / 100.0:.4f}s 미만이어야 함"
    )


# ----------------------------------------- §7.0/7.4/7.6 simulation.jsx 소스 계약
class TestSimulationSource:
    def test_viewbar_labels_use_ink1_not_ink3(self):
        """SimViewBar 라벨 공통 스타일이 var(--ink-1)/fontWeight:600 이고, 그 스타일에 var(--ink-3) 없음."""
        # P5.5 분해 — _SIM_VIEWBAR_LABEL 정의는 simulation.jsx(배럴)에서 sim-tab-utils.jsx 로 이동.
        src = _read_frontend("sim-tab-utils.jsx")
        assert "_SIM_VIEWBAR_LABEL" in src
        # 공통 라벨 스타일 객체 본문을 추출해 토큰/굵기/자간 단언.
        marker = "const _SIM_VIEWBAR_LABEL = {"
        start = src.index(marker)
        end = src.index("};", start)
        block = src[start:end]
        assert "var(--ink-1)" in block
        assert "fontWeight: 600" in block
        assert "fontSize: 11" in block
        assert "letterSpacing" in block
        # 라벨 공통 스타일엔 ink-3 가 없어야 한다(가독성 회귀 방지).
        assert "var(--ink-3)" not in block

    def test_ind_defs_have_new_grouped_keys(self):
        """indGroups 에 새 지표 키(Track S 와 교차파일 계약)가 모두 있다."""
        # P5.5 분해 — indGroups(SimViewBar)는 sim-tab-controls.jsx 로 이동.
        src = _read_frontend("sim-tab-controls.jsx")
        assert "indGroups" in src
        for key in ("ema", "rsi", "macd", "volma", "strma", "vwapband",
                    "strength", "imbalance", "orderflow"):
            assert f'["{key}"' in src, f"indGroups 에 {key} 키 누락"
        # 그룹 헤더(가격/모멘텀/흐름).
        assert '"가격"' in src and '"모멘텀"' in src and '"흐름"' in src

    def test_cols_selector_1_to_5_and_split_rows(self):
        """열 셀렉터 1~5 + splitRows 상태/지속이 배선되어 있다."""
        # P5.5 분해 — 상수/로더는 sim-tab-utils.jsx, 그리드 파생/지속 핸들러는 sim-tab-root.jsx.
        utils = _read_frontend("sim-tab-utils.jsx")
        root = _read_frontend("sim-tab-root.jsx")
        assert "_SIM_MAX_SPLIT_COLS = 5" in utils
        assert "_loadSplitRows" in utils and "_saveSplitRows" in utils
        assert "splitRows" in root
        assert "setSplitRowsPersist" in root
        # 열 클램프(min(5, codes.length))·자동 행수.
        assert "colCap" in root
        assert "autoRows" in root
        # 그리드에 행 캡 시 스크롤(overflowY) 적용.
        assert "gridExtra" in root

    def test_engine_popover_wired(self):
        """SimEnginePopover 가 정의·배선되고, 비대칭(LWC=체결강도 오버레이만)을 설명한다."""
        # P5.5 분해 — SimEnginePopover 정의·SimViewBar 배선은 sim-tab-controls.jsx 로 이동.
        src = _read_frontend("sim-tab-controls.jsx")
        assert "function SimEnginePopover" in src
        assert "<SimEnginePopover" in src
        # 3엔진 모두 + LWC 비대칭 문구. "라이브"/"체결강도 오버레이만" 문구는 _SIM_ENGINE_ROWS(utils).
        utils = _read_frontend("sim-tab-utils.jsx")
        assert "라이브" in utils and "SVG" in utils and "LWC" in utils
        assert "체결강도 오버레이만" in utils
        assert "var(--ink-1)" in src

    def test_vwap_band_carried_into_store_bar(self):
        """_simWsBar 매퍼가 서버 vwap_up/vwap_low 를 스토어 bar 로 전달한다(Track S 소비용)."""
        # P5.5 분해 — _simWsBar 매퍼는 sim-tab-utils.jsx 로 이동.
        src = _read_frontend("sim-tab-utils.jsx")
        assert "vwap_up: it.vwap_up" in src
        assert "vwap_low: it.vwap_low" in src
