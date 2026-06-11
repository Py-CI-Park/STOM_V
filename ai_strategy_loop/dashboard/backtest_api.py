"""Backtest workbench API — tab shell skeleton (PR1).

이 모듈은 웹 대시보드 "백테스트" 탭의 백엔드 자리표시자다. PR1 에서는 헬스 체크
라우트 하나만 노출하고, PR2 에서 GUI 백테스트의 웹 이관(조건식 CRUD, 잡 실행,
결과/분석 엔드포인트)을 이 라우터 위에 확장한다.

설계 계약(무예외):
- 모든 엔드포인트는 데이터가 없어도 빈 구조를 반환하고, 절대 500 으로 대시보드를
  깨지 않는다(기존 대시보드 엔드포인트 컨벤션과 동일).
- app.py 접점은 ``include_router`` 한 줄로 제한한다(wt-dev 와의 머지 충돌 최소화).
"""

from __future__ import annotations

from typing import TypedDict

from fastapi import APIRouter


class HealthResponse(TypedDict):
    status: str
    module: str
    api_version: int


backtest_router = APIRouter(prefix="/bt", tags=["backtest"])


@backtest_router.get("/health")
def backtest_health() -> HealthResponse:
    """백테스트 API 골격의 헬스 체크. 탭 셸 연결 상태 배지가 소비한다."""
    return {"status": "ok", "module": "backtest_api", "api_version": 1}
