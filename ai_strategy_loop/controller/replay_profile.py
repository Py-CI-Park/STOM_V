"""공식 replay 프로파일 동결/비교 모듈.

2026-07-02 replay 포렌식(docs/research/condition_research/
2026-07-02_replay_profile_forensics.md)에서 확정된 프로파일 분기 필드
(betting, avg_time)와 동일 확인 필드(engine_count, 기간, 시간창, DB,
divid_mode, 조건식 sha)를 하나의 불변 dataclass로 동결한다.

이 모듈은 영수증(advisory receipt) 전용이다. 백테스트 실행 경로,
게이트, promotion/export/live 권한 로직을 절대 건드리지 않는다.
stdlib 만 사용하며 부트스트랩 부작용 없이 import 가능하다.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Mapping
import hashlib
import json

# 영수증 스키마 버전. 필드 추가/의미 변경 시 올린다(sha에 포함되어 구분됨).
REPLAY_PROFILE_SCHEMA_VERSION = 1

# 실행 환경 비교(canonical diff)에서 제외하는 식별자 필드.
# 프로파일 라벨과 조건식 식별자는 "같은 실행 환경에서 다른 전략을 돌렸는가"를
# 판정할 때 차이로 세지 않는다. 원시 receipt에는 전부 그대로 남는다.
REPLAY_PROFILE_IDENTITY_FIELDS = (
    "profile_id",
    "buy_strategy_name",
    "sell_strategy_name",
    "buy_condition_sha256",
    "sell_condition_sha256",
)

# canonical 실행 환경 diff에서 제외하는 필드 전체(식별자 + 비재현성 메타).
# fallback_engine_count는 "1차 엔진 기동 실패 시 재시도 용량" 메타라서 replay
# 산출물 동일성을 가르는 필드가 아니고, research loop 실행 경로에는 대체 엔진
# 개념 자체가 없어 항상 0으로 기록된다 — diff에 넣으면 canonical 일치 판정이
# 구조적으로 불가능해진다. 원시 receipt/sha/compare()에는 전부 그대로 남는다.
REPLAY_PROFILE_EXECUTION_IGNORED_FIELDS = REPLAY_PROFILE_IDENTITY_FIELDS + (
    "fallback_engine_count",
)


def condition_code_sha256(code: str) -> str:
    """조건식 코드 sha256(hex). CRLF/CR을 LF로 정규화해 OS 간 안정성을 확보한다."""
    normalized = str(code or "").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ReplayProfile:
    """공식 replay 실행 프로파일(불변).

    포렌식에서 2025 replay 상충의 원인으로 확정된 차이 필드(betting,
    avg_time)와, 동일 확인되었지만 재발 방지를 위해 동결해야 하는 필드
    전부를 담는다. 값 비교/sha는 to_receipt() 기반이므로 필드 추가는
    스키마 버전과 함께 관리한다.
    """

    profile_id: str = ""                      # 프로파일 라벨(식별자, 실행 환경 비교에서는 제외)
    is_tick: bool = True                      # 틱(True)/분봉(False) 스코프
    universe: str = "stock"                   # 유니버스/스코프 (stock 등)
    betting: str = "1"                        # 종목당 매수금액 코드 — 호가 스윕 체결 모델 입력 (포렌식 차이 필드 1)
    avg_time: object = 60                     # 워밍업 평균틱 수 — backengine_kiwoom_tick.py:136 게이트 (포렌식 차이 필드 2)
    engine_count: int = 64                    # 백테스트 엔진 수
    fallback_engine_count: int = 0            # 실패 시 대체 엔진 수 (0 = 대체 없음)
    start_date: int = 0                       # 기간 시작 YYYYMMDD
    end_date: int = 0                         # 기간 끝 YYYYMMDD
    start_time: int = 90000                   # 시간창 시작 HHMMSS
    end_time: int = 92800                     # 시간창 끝 HHMMSS
    divid_mode: str = "종목코드별 분류"       # 엔진 분배 모드 (cli/config.py 기본값과 동일)
    db_path: str = ""                         # 백테스트 DB 식별자(머신 독립 상대 경로 권장)
    fill_model: str = "engine_builtin_hoga_sweep"   # 체결 가정: 공식 엔진 내장 호가 스윕
    slippage_model: str = "engine_builtin"    # 슬리피지/수수료 가정: 엔진 내장(per-run override 없음)
    buy_strategy_name: str = ""               # 매수 조건식 식별자(이름)
    sell_strategy_name: str = ""              # 매도 조건식 식별자(이름)
    buy_condition_sha256: str = ""            # 매수 조건식 코드 sha256 (미확인 시 빈 문자열)
    sell_condition_sha256: str = ""           # 매도 조건식 코드 sha256 (미확인 시 빈 문자열)

    def to_receipt(self) -> dict:
        """JSON-safe 영수증 dict. 스키마 버전을 포함한다(sha 입력과 동일)."""
        return {"schema_version": REPLAY_PROFILE_SCHEMA_VERSION, **asdict(self)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReplayProfile":
        """dict에서 복원. 알 수 없는 키(schema_version 포함)는 무시, 누락 키는 기본값."""
        known = {field.name for field in fields(cls)}
        kwargs = {key: value for key, value in dict(data).items() if key in known}
        return cls(**kwargs)

    def profile_sha256(self) -> str:
        """정렬된 compact JSON(to_receipt 기준) sha256 hex. 동일 설정이면 항상 동일."""
        payload = json.dumps(
            self.to_receipt(),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def compare(self, other: "ReplayProfile", *, ignore: tuple = ()) -> list:
        """다른 프로파일과 값이 다른 필드 이름 목록(정렬). 동일하면 빈 리스트."""
        if not isinstance(other, ReplayProfile):
            raise TypeError(f"ReplayProfile과만 비교할 수 있습니다: {type(other)!r}")
        return sorted(
            field.name
            for field in fields(self)
            if field.name not in ignore
            and getattr(self, field.name) != getattr(other, field.name)
        )


# 2026-07-02 포렌식 권장 공식 동결 프로파일.
# 근거: ai_strategy_loop/config.py:140-141 기본값(betting "5"=500만원, avg_time 30)
# 이 실전 GUI 정합이며, 2022-2025 4개년 OOS/엔진 벤치마크/슬리피지 스트레스/
# condition passport prior 전부 이 프로파일 산출물이라 비교 가능성이 보존된다.
# 공식 2025 기준선 수치: +3,062,696 / 190거래 / MDD 12.87 (4개 실행 byte-identical).
CANONICAL_REPLAY_PROFILE_ID_V1 = "official_replay_v1_20260702"
CANONICAL_REPLAY_PROFILE_V1 = ReplayProfile(
    profile_id=CANONICAL_REPLAY_PROFILE_ID_V1,
    is_tick=True,
    universe="stock",
    betting="5",
    avg_time=30,
    engine_count=64,
    fallback_engine_count=32,
    start_date=20250101,
    end_date=20251231,
    start_time=90000,
    end_time=92800,
    divid_mode="종목코드별 분류",
    db_path="_database/stock_tick_back.db",
)


def canonical_execution_diff(profile: ReplayProfile) -> list:
    """공식 프로파일 대비 실행 환경 차이 필드 목록(식별자/재시도 메타 제외)."""
    return profile.compare(
        CANONICAL_REPLAY_PROFILE_V1,
        ignore=REPLAY_PROFILE_EXECUTION_IGNORED_FIELDS,
    )
