"""원천 파일 접근·빌드 영수증 헬퍼 — 전 원천 read-only, sha256 지문 기록.

원칙: 원본 파일은 절대 변형하지 않는다. 누락/파싱 실패는 예외로 죽이지 않고
영수증(receipt dict)에 기록한 뒤 빌드를 계속한다(계획 §3 — 원본이 정본,
DB는 카탈로그 계층일 뿐이므로 부분 적재가 전체 실패보다 낫다).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def new_receipt(run_dir: Path, db_path: Path) -> Dict[str, Any]:
    """빌드 영수증 뼈대 — 테이블별 건수·원천 sha256·누락/스킵·생성시각."""
    return {
        "kind": "research_assets_build_receipt",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_dir": str(run_dir),
        "db_path": str(db_path),
        "table_counts": {},
        "sources": [],
        "missing": [],
        "skipped": [],
        "notes": [],
        "gitignore": None,
    }


def sha256_file(path: Path) -> str:
    """파일 sha256 — 대용량(parquet 수 MB)도 청크 단위로 안전하게."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel_to(run_dir: Path, path: Path) -> str:
    """run 디렉토리 기준 상대 경로(불가하면 절대 경로 문자열)."""
    try:
        return path.resolve().relative_to(Path(run_dir).resolve()).as_posix()
    except (ValueError, OSError):
        return str(path)


def record_source(
    receipt: Dict[str, Any], run_dir: Path, path: Path,
    status: str = "loaded", note: str = "",
) -> None:
    """원천 파일 1건을 영수증 sources에 기록(동일 경로 중복 기록 방지)."""
    rel = rel_to(run_dir, path)
    for entry in receipt["sources"]:
        if entry.get("path") == rel:
            return
    entry: Dict[str, Any] = {"path": rel, "status": status}
    if note:
        entry["note"] = note
    if path.is_file():
        entry["sha256"] = sha256_file(path)
        entry["size_bytes"] = path.stat().st_size
    receipt["sources"].append(entry)


def read_json(receipt: Dict[str, Any], run_dir: Path, rel: str) -> Optional[dict]:
    """run 상대 json을 읽는다 — 없으면 missing, 깨졌으면 skipped 기록 후 None."""
    path = Path(run_dir) / rel
    if not path.is_file():
        receipt["missing"].append(rel)
        receipt["sources"].append({"path": rel, "status": "missing"})
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        receipt["skipped"].append({"path": rel, "reason": f"json 파싱 실패: {exc}"})
        return None
    record_source(receipt, run_dir, path)
    return data if isinstance(data, dict) else {"_root": data}


def add_note(receipt: Dict[str, Any], msg: str) -> None:
    """영수증 notes에 방어적 파싱 관찰 사항을 남긴다."""
    receipt["notes"].append(msg)
