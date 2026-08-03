# tick 레인 manifest (정본)

> 코드 정본: `ai_strategy_loop/dashboard/lane_manifest.py` · API: `GET /bt/trade-path/lane-manifest?lane=tick`
> 확정일: 2026-08-03 · 상태: **확정** (기존 QSP 연구 계열 승계)
> 변경 규칙: 이 문서와 코드 모듈을 함께 수정하고 사유를 커밋 메시지에 남긴다.

| 항목 | 값 |
|---|---|
| timeframe | tick (1초 스냅샷) |
| 기준선 매수 | `ResearchTest_Tick_B_090000_092800_Wide_20260419` |
| 기준선 매도 | `ResearchTest_Tick_S_090000_092800_Wide_20260419` |
| 설계 구간 | **2022-04-01 ~ 2024-03-31** (2년) |
| OOS 구간 | **2024-04-01 ~ 2026-02-27** (23개월, 설계와 비중첩) |
| 세션 | 09:00:00 ~ 09:28:00 |
| 전체청산 | 092800 |
| 비용 | GetKiwoomPgSgSp — 왕복 ≈0.21%, 수익금에 기반영 |

주의: tick DB는 매일 **09:00~09:30만** 존재(4년·952거래일). 기존 tick control CSV(37열)는 legacy이므로 신규 공식 실행은 modern 54열로 재발급한다(P0-8).
