# -*- coding: utf-8 -*-
"""QSP 보고서를 대시보드 Reports 허브 매니페스트에 등록/갱신.

대시보드는 `docs/generated_reports/manifest.json` 의 항목을 **바이트 수·SHA256 이
실제 파일과 일치할 때만** 신뢰 표시한다(app.py `_report_manifest_rows`). 보고서를
재생성하면 해시가 바뀌므로 이 스크립트를 다시 돌려 등록 정보를 갱신한다.

실행: python docs/research/quant_scoring_pipeline/register_reports.py
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
# 매니페스트는 보고서와 같은 디렉토리에 둔다 — 대시보드 경로 규약이 항목 path 에
#   '..' 를 허용하지 않기 때문(app.py `_report_manifest_relative_path`).
MANIFEST = HERE / "qsp_report_manifest.json"
SCHEMA = "stom-research-report-v1"

# (파일, 제목, 연구 ID) — path 는 매니페스트와 같은 디렉토리 기준(파일명 그대로).
REPORTS = [
    ("2026-07-31_qsp3_report.html", "QSP3 대수술 캠페인 보고서", "qsp3_map_surgery"),
    ("2026-07-31_qsp3_evolution.html", "QSP3 세대 진화 — 액션별 기여·리프 지형", "qsp3_map_surgery"),
    ("2026-07-31_qsp2_report.html", "QSP2 anchor 캠페인 보고서", "qsp2_anchor"),
    ("2026-07-31_qsp2_evolution.html", "QSP2 세대 진화 — 리프 히트맵·제거 시나리오", "qsp2_anchor"),
    ("2026-07-30_final_report.html", "QSP1 최종 연구 보고서(정정 포함)", "qsp1_pipeline"),
]


def _digest(path: Path):
    h = hashlib.sha256()
    n = 0
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(64 * 1024), b""):
            n += len(chunk)
            h.update(chunk)
    return h.hexdigest(), n


def main() -> int:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {
        "schema_version": SCHEMA, "generated_at": "", "count": 0, "reports": []}
    reports = [r for r in payload.get("reports", [])
               if not str(r.get("report_id", "")).startswith("qsp:")]
    added = 0
    for fname, title, research_id in REPORTS:
        f = HERE / fname
        if not f.exists():
            print(f"  skip(없음): {fname}")
            continue
        sha, nbytes = _digest(f)
        reports.append({
            "schema_version": SCHEMA,
            "report_id": f"qsp:{fname}",
            "report_type": "research",
            "research_id": research_id,
            "run_id": None, "generation": None, "cycle": None,
            "status": "published", "publication_status": "published",
            "generator": "quant_scoring_pipeline",
            "title": title,
            "path": fname,
            "content_sha256": sha, "source_sha256": sha, "bytes": nbytes,
            "generated_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="seconds"),
            "trust": "verified", "provenance": "quant_scoring_pipeline builders",
            "toc": [], "profile": "research", "evidence": [], "decision": None,
            "limitations": "limitation_ledger.md 참조 — 실전 반영 없음",
            "step_id": None, "sha256": sha,
            "pdf_path": None, "pdf_bytes": None, "pdf_sha256": None,
            "pdf_source_content_sha256": None,
        })
        added += 1
        print(f"  등록: {fname} ({nbytes:,} bytes)")
    payload["schema_version"] = SCHEMA
    payload["reports"] = reports
    payload["count"] = len(reports)
    payload["generated_at"] = datetime.now().isoformat(timespec="seconds")
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"매니페스트 갱신: {MANIFEST} (QSP {added}건 / 전체 {len(reports)}건)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
