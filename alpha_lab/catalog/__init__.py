"""research_assets 카탈로그 패키지 — WBS v3 P0 (2026-07-12 계획 §3).

원칙: 정본은 기존 파일(json/parquet/md — git 추적 or 영수증 재생성 가능).
이 DB는 복제가 아니라 카탈로그+요약 계층이며, 대시보드와 후속 연구의
단일 조회 창구다. 어떤 원본 파일도 변형하지 않는다(read-only).
"""
from alpha_lab.catalog.builder import build_all  # noqa: F401
from alpha_lab.catalog.schema import TABLES, create_schema, table_counts  # noqa: F401
