"""T4 반복 정제 폐루프 — 패배 세그먼트 'avoid 가이드' 환류 단위 테스트.

배경: 백테 결과를 시간대×시총×등락률 셀로 쪼개면(fitness/edge_ratio.edge_by_segment)
일부 셀이 만성 적자/저승률이다. 이 '패배·불필요 구간'을 다음 세대 매수 프롬프트에
'avoid 가이드'로 환류해, 루프가 스스로 불필요 구간을 줄이며 재생성하게 한다
("실행→분석→불필요 구간 제거→재생성" 폐루프). 토글 기본 OFF·byte-identical·
하드게이트 무관(프롬프트 넛지 전용).

검증:
  (A) build_segment_avoid_lines(순수 헬퍼):
      - 패배 셀(적자 또는 저승률 + 표본>=min_count) 결정론적 추출 + NL avoid 라인 생성.
      - min_count 필터: 표본 미달 셀은 avoid에서 제외.
      - 데이터 없음/빈 입력/없는 경로 → 빈 리스트(graceful·무예외).
      - 흑자·고승률만이면 빈 리스트(패배 셀 없음).
  (B) build_messages 매수 avoid 환류:
      - 라인 주어짐 + kind=='buy' → 매수 프롬프트에 'avoid 가이드' 블록 + 각 라인 존재.
      - 라인 주어져도 kind=='sell' → 매도 프롬프트엔 부재(매수 전용).
      - 라인 None/빈 리스트(기본) → buy/sell 모두 명시 None과 byte-동일(기존 동작 보존).
  (C) LoopConfig: 기본 OFF + min_count 기본 8 + from_dict 안전 파싱.

OFF=기존동작 보존이 핵심 — 모든 신규 동작은 토글/인자 뒤에만 있다.
실DB/백테 미사용: tmp 경로 CSV + 손계산 DataFrame만 쓴다.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd  # noqa: E402

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.brain.prompt import build_messages  # noqa: E402
from ai_strategy_loop.brain.segment_feedback import build_segment_avoid_lines  # noqa: E402
from ai_strategy_loop.brain.segment_feedback import (  # noqa: E402
    render_directives_from_card_v3,
)



# base_code(seed-refine) 경로를 타게 하는 더미 출발점 전략(내용 무관).
_BASE_BUY = "매수 = False\nif 현재가 > 0:\n    매수 = True\nif 매수:\n    self.Buy()"

# avoid 블록 마커 문구(주입 시에만 존재해야 한다).
_AVOID_MARKER = "최근 백테 패배 구간(avoid 가이드"


def _user_text(messages):
    """messages에서 user 메시지 본문을 꺼낸다."""
    return next(m["content"] for m in messages if m["role"] == "user")


# ---------------------------------------------------------------------------
# 손계산 세그먼트 DataFrame 빌더
# ---------------------------------------------------------------------------
def _losing_winning_df():
    """패배 시간대(장초반 적자/저승률) + 흑자 시간대(오전 흑자/고승률) 거래 df.

    각 셀 8건(min_count=8 통과). B_시분초=HHMMSS, B_시가총액=억원, B_등락율=%.
    - 장초반(09:01) 8건: 전부 손실(수익률 -1.0, 수익금 -100) → 적자 + 승률 0%.
    - 오전(10:00) 8건: 전부 이익(수익률 +2.0, 수익금 +200) → 흑자 + 승률 100%.
    """
    rows = []
    for _ in range(8):
        rows.append({"수익률": -1.0, "수익금": -100.0, "R_MFE": 1.0, "R_MAE": -2.0,
                     "B_시분초": 90100, "B_시가총액": 500.0, "B_등락율": 4.0})
    for _ in range(8):
        rows.append({"수익률": 2.0, "수익금": 200.0, "R_MFE": 4.0, "R_MAE": -0.5,
                     "B_시분초": 100000, "B_시가총액": 5000.0, "B_등락율": 1.0})
    return pd.DataFrame(rows)


# ============================================================
# (A) build_segment_avoid_lines — 순수 헬퍼
# ============================================================

def test_avoid_lines_extracts_losing_cell_deterministic():
    """패배 셀(장초반 적자/승률0%)이 avoid 라인으로 추출된다(결정론)."""
    df = _losing_winning_df()
    lines = build_segment_avoid_lines(df, min_count=8)
    assert lines  # 비어있지 않다.
    joined = "\n".join(lines)
    # 패배 시간대 '장초반' 라벨이 avoid 라인에 등장한다.
    assert "장초반" in joined
    # 적자 셀이므로 '적자' framing.
    assert "적자" in joined
    # 결정론: 동일 입력 → 동일 출력.
    assert build_segment_avoid_lines(df, min_count=8) == lines


def test_avoid_lines_min_count_filter():
    """표본 < min_count 셀은 avoid에서 제외된다(잡음 배제)."""
    # 장초반 적자 5건만(8 미만) → min_count=8이면 어떤 패배 셀도 안 잡힌다.
    rows = [
        {"수익률": -1.0, "수익금": -100.0, "R_MFE": 1.0, "R_MAE": -2.0,
         "B_시분초": 90100, "B_시가총액": 500.0, "B_등락율": 4.0}
        for _ in range(5)
    ]
    lines = build_segment_avoid_lines(pd.DataFrame(rows), min_count=8)
    assert lines == []
    # min_count=5로 낮추면 잡힌다(표본 충분 판정).
    lines5 = build_segment_avoid_lines(pd.DataFrame(rows), min_count=5)
    assert lines5  # 비어있지 않다.


def test_avoid_lines_low_win_rate_cell():
    """적자는 아니어도 저승률(<0.45) 셀은 패배 셀로 잡힌다(OR 조건)."""
    # 승률 25%(8건 중 2건만 이익)이지만 총수익금은 +(흑자) — 저승률 분기 검증.
    rows = []
    for i in range(8):
        win = i < 2  # 2건만 이익.
        rows.append({
            "수익률": 1.0 if win else -0.2,
            "수익금": 500.0 if win else -10.0,  # 총합 = 2*500 - 6*10 = 940 > 0(흑자).
            "R_MFE": 2.0, "R_MAE": -1.0,
            "B_시분초": 90100, "B_시가총액": 500.0, "B_등락율": 4.0,
        })
    lines = build_segment_avoid_lines(pd.DataFrame(rows), min_count=8)
    assert lines  # 저승률로 잡힘.
    joined = "\n".join(lines)
    # 흑자이므로 '저승률' framing(적자 아님).
    assert "저승률" in joined


def test_avoid_lines_no_losing_cells_returns_empty():
    """흑자·고승률만이면 패배 셀이 없어 빈 리스트(graceful)."""
    rows = [
        {"수익률": 2.0, "수익금": 200.0, "R_MFE": 4.0, "R_MAE": -0.5,
         "B_시분초": 100000, "B_시가총액": 5000.0, "B_등락율": 1.0}
        for _ in range(10)
    ]
    assert build_segment_avoid_lines(pd.DataFrame(rows), min_count=8) == []


def test_avoid_lines_empty_and_missing_graceful():
    """빈 입력·None·없는 경로는 빈 리스트로 흡수한다(무예외)."""
    assert build_segment_avoid_lines(pd.DataFrame()) == []
    assert build_segment_avoid_lines(None) == []
    assert build_segment_avoid_lines("") == []
    assert build_segment_avoid_lines("does_not_exist_xyz.csv") == []


def test_avoid_lines_from_csv_path(tmp_path):
    """CSV 경로(utf-8-sig)에서도 패배 셀 avoid 라인을 산출한다(로드 경로)."""
    p = os.path.join(str(tmp_path), "trades.csv")
    header = "수익률,수익금,R_MFE,R_MAE,B_시분초,B_시가총액,B_등락율\n"
    with open(p, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write(header)
        for _ in range(8):  # 장초반 적자 8건.
            fh.write("-1.0,-100.0,1.0,-2.0,90100,500.0,4.0\n")
    lines = build_segment_avoid_lines(p, min_count=8)
    assert lines
    assert "장초반" in "\n".join(lines)


# ============================================================
# (B) build_messages 매수 avoid 환류
# ============================================================

def test_build_messages_buy_injects_avoid_block():
    """라인 주어짐 + kind=='buy' → 매수 프롬프트에 avoid 블록 + 각 라인 존재."""
    avoid = ["- 시간대 '장초반' 구간은 최근 백테서 적자 — 피하라.",
             "- 시총 '초소형' 구간은 최근 백테서 저승률 — 피하라."]
    user = _user_text(build_messages("buy", timeframe="min", segment_avoid_lines=avoid))
    assert _AVOID_MARKER in user
    for line in avoid:
        assert line in user


def test_build_messages_sell_ignores_avoid_block():
    """라인 주어져도 kind=='sell' → 매도 프롬프트엔 avoid 블록 부재(매수 전용)."""
    avoid = ["- 시간대 '장초반' 구간은 최근 백테서 적자 — 피하라."]
    user = _user_text(build_messages("sell", timeframe="min", segment_avoid_lines=avoid))
    assert _AVOID_MARKER not in user


def test_build_messages_buy_off_default_byte_identical():
    """avoid None(기본) == 명시 None(매수): messages byte-동일(기존 동작 보존)."""
    default_buy = build_messages("buy", timeframe="min", base_code=_BASE_BUY)
    none_buy = build_messages("buy", timeframe="min", base_code=_BASE_BUY,
                              segment_avoid_lines=None)
    empty_buy = build_messages("buy", timeframe="min", base_code=_BASE_BUY,
                               segment_avoid_lines=[])
    assert default_buy == none_buy
    # 빈 리스트도 미주입(byte-동일).
    assert default_buy == empty_buy
    assert _AVOID_MARKER not in _user_text(default_buy)


def test_build_messages_sell_off_default_byte_identical():
    """avoid None(기본) == 명시 None(매도): messages byte-동일(기존 동작 보존)."""
    default_sell = build_messages("sell", timeframe="min")
    none_sell = build_messages("sell", timeframe="min", segment_avoid_lines=None)
    assert default_sell == none_sell


def test_build_messages_sell_with_avoid_byte_identical_to_off():
    """avoid 주어져도 매도 경로는 OFF와 byte-동일(인자가 매수에만 작용)."""
    off_sell = build_messages("sell", timeframe="min")
    on_sell = build_messages("sell", timeframe="min",
                             segment_avoid_lines=["- 시간대 '장초반' 적자 — 피하라."])
    assert off_sell == on_sell


# ============================================================
# (C) LoopConfig 기본 OFF + min_count + from_dict 안전 파싱
# ============================================================

def test_config_default_off():
    """LoopConfig.segment_feedback_enabled 기본값은 False, min_count 기본 8."""
    cfg = LoopConfig()
    assert cfg.segment_feedback_enabled is False
    assert cfg.segment_feedback_min_count == 8


def test_config_from_dict_parses_toggle():
    """from_dict가 segment_feedback_enabled/min_count를 안전하게 파싱한다."""
    cfg = LoopConfig.from_dict({
        "segment_feedback_enabled": True,
        "segment_feedback_min_count": 12,
    })
    assert cfg.segment_feedback_enabled is True
    assert cfg.segment_feedback_min_count == 12


def test_config_from_dict_ignores_unknown():
    """알 수 없는 키는 무시하고 토글 기본값은 OFF로 유지한다(안전 파싱)."""
    cfg = LoopConfig.from_dict({"unknown_key_xyz": 123})
    assert cfg.segment_feedback_enabled is False
    assert cfg.segment_feedback_min_count == 8


# ---------------------------------------------------------------------------
# DR-05 — render_directives_from_card_v3: AnalysisCardV3 영속 지시 렌더러.
# ---------------------------------------------------------------------------


class _FakeCardV3:
    def __init__(self, actionable_directives, content_hash="deadbeef"):
        self.actionable_directives = actionable_directives
        self.content_hash = content_hash


def test_render_directives_from_card_v3_rejects_unverified_card_like_objects():
    card = _FakeCardV3(
        actionable_directives=[
            {
                "statement": "B_signal 진입 우위",
                "reason_code": "OK",
                "data_role": "TRAIN",
                "status": "READY",
            },
            {
                "statement": "B_other 진입 우위",
                "reason_code": "OK",
                "data_role": "TRAIN",
                "status": "READY",
            },
        ],
        content_hash="abc123",
    )
    assert render_directives_from_card_v3(card) == []


def test_render_directives_from_card_v3_empty_when_no_directives():
    card = _FakeCardV3(actionable_directives=[])
    assert render_directives_from_card_v3(card) == []


def test_render_directives_from_card_v3_never_raises_on_malformed_card():
    """무예외 계약: card에 필드가 없어도 예외를 던지지 않고 빈 리스트를 돌려준다."""
    class _Empty:
        pass

    assert render_directives_from_card_v3(_Empty()) == []


def test_render_directives_from_card_v3_matches_real_analysis_card_v3_hash():
    """실제 build_analysis_card_v3 로 만든 카드로도 동일 계약을 만족한다(통합 확인)."""
    from ai_strategy_loop.autopsy.analysis_card import build_analysis_card_v3

    rows = []
    for i in range(40):
        day = (i % 12) + 1
        rows.append({
            "매수시간": f"202601{day:02d}120000",
            "종목코드": f"S{i % 3}",
            "수익률": 1.0 if i % 3 else -0.5,
            "수익금": 100.0 if i % 3 else -50.0,
        })
    df = pd.DataFrame(rows)
    finding = {
        "finding_id": "f1", "statement": "테스트 지시", "axis": "entry_feature",
        "p_value": 0.001, "prereg_axis": False, "ci_low": 1.0, "ci_high": 5.0,
        "full_population": True,
    }
    card = build_analysis_card_v3(
        df, source={"alias": "fixture://x"}, role="train", candidate_findings=[finding],
    )
    lines = render_directives_from_card_v3(card)
    assert lines
    assert all(card.content_hash in line for line in lines)
