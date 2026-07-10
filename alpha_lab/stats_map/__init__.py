"""S-트랙 통계 지도 DB 빌더 — 사전등록 봉인 스펙 구현(연구 전용).

상위: docs/research/condition_research/plans/2026-07-10_s_track_preregistration.md
근거: research_runs/alpha_restart_20260710/w3_profiling.json(+report).

이 패키지는 원본 tick DB를 read-only로 읽어 (시간대×등락율[×시총]) 셀별
비용차감 라벨 통계를 SQLite 지도(stats_map.db)로 적재한다. 엔진 백테는 0회다.
셀 축·경계·라벨·비용식·절단 규약은 전부 사전등록에서 봉인됐고, config.py가
그 단일 출처다 — 이 패키지의 어떤 모듈도 봉인값을 재정의하지 않는다.
"""
from __future__ import annotations
