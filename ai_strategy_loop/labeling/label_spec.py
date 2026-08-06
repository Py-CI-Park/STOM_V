"""라벨 명세 상수 — 실행계획 v2 §3 을 코드로 옮긴 정본.

여기 값은 **사전 고정**이다. "잘 나오는 horizon" 을 나중에 고르는 것 자체가
과최적이므로(함정 5), 이 파일의 변경은 라운드 시작 전에만 허용된다.
"""

from __future__ import annotations

from typing import Final

# 고정 horizon (초). "최적 청산" 라벨은 사후 정보라 만들지 않는다(함정 6).
HORIZONS: Final = (30, 60, 120, 300)

# 진입 후보 창(사용자 지정: 09:20 까지만 매수)과 전체청산.
ENTRY_START: Final = 90000
ENTRY_END: Final = 92000
FORCED_EXIT: Final = 92800

# 왕복 비용 ≈0.21% — 매수 수수료 0.015% / 매도 수수료 0.015% + 세금 0.18%.
# 라벨은 반드시 비용 차감 후로만 정의한다(규율 L1).
COST_IN: Final = 0.00015
COST_OUT: Final = 0.00195

# 스테일 허용: 관측이 이보다 오래된 가격으로는 체결을 가정하지 않는다(함정 2).
STALE_TOLERANCE_SEC: Final = 10

# close 라벨이 이 시각 이전에 끝나면 절단 플래그(수집 이탈).
CLOSE_TRUNCATED_BEFORE: Final = 92700

# 상한가 근접 제외(함정 3).
LIMIT_UP_RATE: Final = 29.0

# VI 근접: 현재가 >= VI가격 - 5*VI호가단위 (902/905 의 `VI아래5호가` 관행).
VI_TICKS_BELOW: Final = 5

# 경로 라벨(MFE/MAE) 창 — 모양 라벨이지 청산 시뮬레이션이 아니다.
PATH_WINDOW_SEC: Final = 300

# parquet 로 남길 스냅샷 열(원본 54열 중 연구에 쓰는 부분집합 + 호가 1단).
SNAPSHOT_COLUMNS: Final = (
    "현재가", "시가", "고가", "저가", "등락율", "당일거래대금", "체결강도",
    "초당매수수량", "초당매도수량", "거래대금증감", "전일비", "회전율", "전일동시간비",
    "시가총액", "라운드피겨위5호가이내", "VI가격", "VI호가단위", "초당거래대금",
    "고저평균대비등락율", "저가대비고가등락율", "초당매수금액", "초당매도금액",
    "매도호가1", "매수호가1", "매도총잔량", "매수총잔량", "관심종목",
)


def hhmmss_to_sod(hhmmss: int) -> int:
    """HHMMSS 정수 → 그날 0시 기준 초. 분·시 경계 산술 오류(함정)를 원천 차단."""
    return (hhmmss // 10000) * 3600 + ((hhmmss // 100) % 100) * 60 + (hhmmss % 100)


def sod_to_hhmmss(sod: int) -> int:
    return (sod // 3600) * 10000 + ((sod % 3600) // 60) * 100 + (sod % 60)
