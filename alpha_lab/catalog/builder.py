"""research_assets 카탈로그 빌더 — 원천 실물에서 6종 테이블 적재(WBS v3 P0).

원칙(계획 §3): 원본 파일이 정본, 이 DB는 카탈로그+요약 계층. 원본은 전부
read-only로만 접근하며, 쓰기는 research_assets.db·빌드 영수증·run 디렉토리
.gitignore 3가지뿐이다. 빌드는 멱등 — 재실행 시 전 테이블을 비우고 다시 채운다.

판정 카드 7계열(judgments)은 핸드오프 v3 §3 확정 판정 + B1(§4)을 원천 json에서
구성한다. ga_path_flag는 계획 §5-4의 GA/최적화 경로 경고 그릇(현재 전부 0).
"""
from __future__ import annotations

import fnmatch
import json
import os
import stat
import uuid
from dataclasses import dataclass
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, List, Optional, Tuple

from alpha_lab.discipline.evidence import (
    EvidenceSchemaError,
    sha256_canonical,
    validate_catalog_promotion_receipt_v2,
    verify_promotion_manifest_v2,
    verify_promotion_result_v2,
)
from alpha_lab.discipline.prereg import authority_mutation_guard

from alpha_lab.catalog.assets_registry import ASSET_REGISTRY
from alpha_lab.catalog.loaders import (
    load_cells, load_clauses, load_ledger_mirror, load_strategies,
)
from alpha_lab.catalog.schema import create_schema, reset_tables, table_counts
from alpha_lab.catalog.sources import (
    RetainedSourceSnapshots, add_note, new_receipt, read_json, record_inventory,
    record_source, retain_snapshot_sources, sha256_file, snapshot_sources,
    validate_retained_snapshot_sources,
)

# 공유 원천(1회만 읽고 여러 테이블이 소비) — rel 경로 키.
_REL_D1 = "d1_clause_ablation_summary.json"
_REL_D5R = "d5r_triage_summary.json"
_REL_O1G = "o1g/o1g_grid_summary.json"
_REL_W2 = "w2_strategy_inventory.json"
_REL_W5 = "w5_composite_survey.json"
_REL_W6A = "w6a_giveback.json"
_REL_W4F = "w4_full_build.json"
_REL_W4C = "w4_champion_overlay.json"
_REL_V2C = "v2c_gate_summary.json"
_REL_PROBE = "probe_min_d9.json"
_REL_B1V = "d5r_b1_live/_ab_verdict.json"
_REL_B1R = "d5r_b1_live/b1_registration_receipt.json"
_SHARED_RELS = (
    _REL_D1, _REL_D5R, _REL_O1G, _REL_W2, _REL_W5, _REL_W6A,
    _REL_W4F, _REL_W4C, _REL_V2C, _REL_PROBE, _REL_B1V, _REL_B1R,
)


def root_from_run_dir(run_dir: Path) -> Path:
    """run 디렉토리에서 워크트리 루트 추정('docs' 상위) — 실패 시 run 자신."""
    parts = Path(run_dir).resolve().parts
    if "docs" in parts:
        return Path(*parts[: parts.index("docs")])
    return Path(run_dir)


# ---------------------------------------------------------------------------
# assets — 레지스트리(계획 §1 표) 적재 + 실물 존재·sha256 확인.
# ---------------------------------------------------------------------------

def load_assets(
    con: sqlite3.Connection, run_dir: Path, receipt: Dict[str, Any],
    retained_snapshots: RetainedSourceSnapshots | None = None,
    catalog_db_path: Path | None = None,
) -> None:
    """Load asset rows from live files or, for authority, retained snapshot bytes."""
    root = root_from_run_dir(run_dir)
    for asset in ASSET_REGISTRY:
        is_catalog_output = asset["asset_id"] == "research_assets_db"
        base = root if asset["base"] == "root" else Path(run_dir)
        path = Path(catalog_db_path) if is_catalog_output and catalog_db_path is not None else base / str(asset["path"])
        if is_catalog_output:
            # The DB being assembled is an output, never an input observation.  Its
            # row must remain stable when an abandoned publication is rebuilt.
            exists, sha, size, mtime = False, None, None, None
        elif retained_snapshots is None:
            exists, sha, size, mtime = _stat_asset(path, str(asset["asset_id"]))
        else:
            try:
                rel = path.resolve().relative_to(Path(run_dir).resolve()).as_posix()
            except ValueError:
                rel = None
            observation = (
                retained_snapshots.observation_for_relative(rel) if rel is not None else None)
            if observation is not None:
                exists, sha, size, mtime = (
                    True, observation.sha256, observation.size_bytes, observation.mtime_utc)
            elif rel is not None and retained_snapshots.contains_relative_path(rel):
                exists, sha, size, mtime = True, None, None, None
            else:
                exists, sha, size, mtime = False, None, None, None
        record_inventory(
            receipt, run_dir, path, asset_id=str(asset["asset_id"]),
            exists_on_disk=exists, sha256=sha, size_bytes=size, mtime_utc=mtime)
        con.execute(
            "INSERT OR REPLACE INTO assets (asset_id, kind, path,"
            " produced_commit, seal_doc, window, status_tag, regen_cmd,"
            " summary, exists_on_disk, sha256, size_bytes, mtime_utc)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (asset["asset_id"], asset["kind"], _asset_path_str(root, path),
             asset.get("produced_commit"), asset.get("seal_doc"),
             asset.get("window"), asset["status_tag"], asset.get("regen_cmd"),
             asset.get("summary"), int(exists), sha, size, mtime),
        )
    add_note(receipt, "assets.produced_commit=None 행은 커밋 체인 문서에 명시가 없거나 메인 세션 커밋 대기(빌더는 git 미호출)")


def _stat_asset(
    path: Path, asset_id: str,
) -> Tuple[bool, Optional[str], Optional[int], Optional[str]]:
    """자산 실물 확인 — (존재, sha256, 크기, mtime). 자기 자신 DB는 sha 생략."""
    if path.is_dir():
        return True, None, None, None
    if not path.is_file():
        return False, None, None, None
    st = path.stat()
    mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
    if asset_id == "research_assets_db":
        # 빌드 중인 자기 자신 — sha는 빌드 후에도 계속 변하므로 기록하지 않는다.
        return True, None, st.st_size, mtime
    return True, sha256_file(path), st.st_size, mtime


def _asset_path_str(root: Path, path: Path) -> str:
    """루트 기준 상대 경로 문자열(불가하면 절대 경로) — 카탈로그 이식성."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (ValueError, OSError):
        return str(path)


# ---------------------------------------------------------------------------
# judgments — 판정 카드 7계열(핸드오프 v3 §3 + B1 §4).
# ---------------------------------------------------------------------------

def _km_v2c(d: dict) -> dict:
    g = d.get("v2c_gate") or {}
    return {"n_families": g.get("n_families"), "n_pass": g.get("n_pass"),
            "verdicts": g.get("verdicts"),
            "overall_l1_l3_mean": d.get("overall_l1_l3_mean"),
            "overall_l1_h300_mean": d.get("overall_l1_h300_mean")}


def _km_o1g(d: dict) -> dict:
    j = d.get("judgment_raw") or {}
    keys = ("fdr_q", "fdr_denominator", "n_fdr_survivors", "strong_cells",
            "weak_cells", "insufficient_cells", "kill_all_ci_high_negative")
    return {k: j.get(k) for k in keys}


def _km_d1(d: dict) -> dict:
    j = d.get("judgment") or {}
    keys = ("n_load_bearing", "n_counter_productive", "n_weak_signal",
            "load_bearing_nums", "counter_productive_nums", "weak_signal_nums",
            "inconclusive_nums", "fdr_denominator", "fdr_q",
            "sanity_anchor_tripped", "kill1_all_zero_survivors")
    return {k: j.get(k) for k in keys}


def _km_d5r(d: dict) -> dict:
    return dict(d.get("headline") or {})


def _km_w5(d: dict) -> dict:
    s3 = d.get("section3_signal_overlap") or {}
    return {"merged_RR8_3sib": s3.get("merged_RR8_3sib"),
            "pairwise_overlap_RR8": s3.get("pairwise_overlap_RR8")}


def _km_probe(d: dict) -> dict:
    p1, p2 = d.get("probe1_min") or {}, d.get("probe2_d9") or {}
    return {"probe1_min_verdict": p1.get("verdict"),
            "probe1_key_numbers": p1.get("key_numbers"),
            "probe2_d9_verdict": p2.get("verdict"),
            "probe2_key_numbers": p2.get("key_numbers")}


def _km_b1(d: dict) -> dict:
    return dict(d)


def _verdict_b1(d: dict) -> str:
    ok = bool(d.get("all_pass"))
    agg = d.get("agg_dP")
    head = "PASS(엔진 A/B 4런 전체)" if ok else "FAIL(엔진 A/B — 봉인 문구 재확인 필요)"
    return f"{head} — ΣΔ{agg:+,}원" if isinstance(agg, (int, float)) else head


# (계열, 원천 rel, 정적 verdict 또는 파생 fn, 지표 추출 fn, 리포트, 커밋, 장부 선택자)
_JUDGMENT_SPECS: Tuple[Tuple[str, str, Any, Callable[[dict], dict], Optional[str], Optional[str], str], ...] = (
    ("S-트랙 칸-조준(V2-C)", _REL_V2C,
     "KILL(0/2) — 칸-조준은 두 라벨(h300·L3) 모두 실패", _km_v2c,
     "v2c_gate_report.md", "f553378b", "s_track"),
    ("O-1G 시초 갭 조합표", _REL_O1G,
     "KILL — 양EV 증거 0(전 144셀 자격 충족)", _km_o1g,
     "o1g/o1g_report.md", "19138c90", "o1g"),
    ("D1 절-단위 분해", _REL_D1,
     "양성 — 압력 절 5종 load-bearing·역생산 6절(RR8_12 계보·원-임계 이식 금지)",
     _km_d1, "d1_clause_ablation_report.md", "7171a561", "d1"),
    ("D5-R 조건부 청산 triage", _REL_D5R,
     "KILL-2 — 8후보 전부 하한 미달(메커니즘 실재·B1만 실전 이관)", _km_d5r,
     "d5r_triage_report.md", "951c9748", "d5r_b"),
    ("W5 RR8 3형제 병합", _REL_W5,
     "무가치 — 신호 중복 97.6~100%(순증분 +1%), 상보성은 시간대·트리거 분리 출처만",
     _km_w5, "w5_composite_survey.md", "4ee6ed80", "none"),
    ("min·D9 프로브", _REL_PROBE,
     "생존 — min=audit-grade 전용·D9 일치 100%(재진입 관측 75.75%)", _km_probe,
     "probe_min_d9_report.md", "3ade1286", "none"),
    ("B1 감독형 이관 엔진 A/B", _REL_B1V, _verdict_b1, _km_b1,
     "docs/research/condition_research/plans/2026-07-12_b1_supervised_live_protocol.md",
     None, "b1_a"),
)

_LEDGER_PICKERS: Dict[str, Callable[[dict], bool]] = {
    "s_track": lambda o: o.get("series") == "S-트랙",
    "o1g": lambda o: o.get("series") == "O-1G",
    "d1": lambda o: o.get("series") == "D1",
    "d5r_b": lambda o: o.get("series") == "D5-R"
    and not str(o.get("trial_type", "")).startswith("a"),
    "b1_a": lambda o: o.get("series") == "D5-R"
    and str(o.get("trial_type", "")).startswith("a"),
    "none": lambda o: False,
}


def load_judgments(
    con: sqlite3.Connection, docs: Dict[str, Optional[dict]],
    ledger_rows: List[Tuple[int, dict]], receipt: Dict[str, Any],
) -> None:
    """판정 카드 7계열 적재 — 원천 없으면 카드 생략(영수증 기록)."""
    for series, rel, verdict, extract, report, commit, picker in _JUDGMENT_SPECS:
        data = docs.get(rel)
        if data is None:
            receipt["skipped"].append(
                {"path": rel, "reason": f"판정 카드 '{series}' 생략 — 원천 없음"})
            continue
        rows = [num for num, obj in ledger_rows if _LEDGER_PICKERS[picker](obj)]
        metrics = extract(data)
        if not any(v is not None for v in metrics.values()):
            add_note(receipt, f"judgments('{series}'): 핵심 지표 필드 전부 누락 — 원천 스키마 확인 필요")
        con.execute(
            "INSERT OR REPLACE INTO judgments (series, verdict,"
            " key_metrics_json, ledger_rows, n_ledger_rows, report_path,"
            " source_path, produced_commit, ga_path_flag, note)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (series, verdict(data) if callable(verdict) else verdict,
             json.dumps(metrics, ensure_ascii=False),
             ",".join(map(str, rows)), len(rows), report, rel, commit, 0,
             None if commit else "커밋 미상 또는 메인 세션 커밋 대기"),
        )
    add_note(receipt, "judgments.ga_path_flag: 현 7계열 전부 0 — GA/최적화 경로 산출물 경고 그릇(계획 §5-4)")


# ---------------------------------------------------------------------------
# .gitignore 보장 — research_assets.db가 git에 걸리지 않게(계획 §3).
# ---------------------------------------------------------------------------

_GI_PATTERN = "research_assets.db*"
_GI_COMMENT = "# research_assets 카탈로그 DB — 재생성 가능 산물(커밋 금지, WBS v3 P0)"


def ensure_gitignore(run_dir: Path) -> Dict[str, str]:
    """run 디렉토리 .gitignore에 카탈로그 DB 제외를 보장(기존 내용 보존)."""
    gi = Path(run_dir) / ".gitignore"
    existing = gi.read_text(encoding="utf-8") if gi.is_file() else ""
    patterns = [
        ln.strip() for ln in existing.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    if any(fnmatch.fnmatch("research_assets.db", p.lstrip("/")) for p in patterns):
        return {"path": str(gi), "action": "ok(기존 패턴이 이미 제외)", "pattern": ""}
    block = _GI_COMMENT + "\n" + _GI_PATTERN + "\n"
    if existing and not existing.endswith("\n"):
        existing += "\n"
    gi.write_text(existing + block, encoding="utf-8")
    action = "appended(기존 내용 보존)" if existing else "created"
    return {"path": str(gi), "action": action, "pattern": _GI_PATTERN}
LEGACY_NON_AUTHORITATIVE_CATALOG_ROOT = "legacy_non_authoritative_catalogs"


def _catalog_output_paths(
    repo_root: Path,
    db_path: Path | str | None,
    receipt_path: Path | str | None,
    promotion_status: dict[str, Any] | None,
) -> tuple[Path, Path]:
    """Use fixed legacy or sealed evidence-and-phase catalog destinations."""
    if promotion_status is None:
        root = repo_root / LEGACY_NON_AUTHORITATIVE_CATALOG_ROOT
        canonical_db = root / "research_assets.db"
        canonical_receipt = root / "research_assets_build_receipt.json"
    else:
        root = repo_root / Path(*PurePosixPath(promotion_status["catalog_dir"]).parts)
        phase = promotion_status["phase"].lower()
        canonical_db = root / f"{promotion_status['evidence_id']}.{phase}.db"
        canonical_receipt = root / f"{promotion_status['evidence_id']}.{phase}.receipt.json"
    if db_path is not None and Path(db_path).resolve() != canonical_db.resolve():
        raise EvidenceSchemaError("catalog db_path must equal its authority-owned canonical path")
    if receipt_path is not None and Path(receipt_path).resolve() != canonical_receipt.resolve():
        raise EvidenceSchemaError("catalog receipt_path must equal its authority-owned canonical path")
    return canonical_db, canonical_receipt


def _promotion_status(
    repo_root: Path,
    promotion_manifest_path: Path | str | None,
    promotion_result_path: Path | str | None,
) -> dict[str, Any] | None:
    """Verify promotion provenance before allowing any catalog mutation."""
    if promotion_manifest_path is not None and promotion_result_path is not None:
        raise EvidenceSchemaError("promotion manifest and result inputs are mutually exclusive")
    if promotion_manifest_path is None and promotion_result_path is None:
        return None
    if promotion_manifest_path is not None:
        manifest, digest = verify_promotion_manifest_v2(
            promotion_manifest_path, repo_root=repo_root)
        source = Path(promotion_manifest_path).resolve()
        phase, kind, evidence_id = "PRE", "promotion_manifest", manifest["evidence_id"]
        result: dict[str, Any] | None = None
    else:
        source = Path(promotion_result_path).resolve()
        result, manifest, digest = verify_promotion_result_v2(source, repo_root=repo_root)
        phase, kind, evidence_id = "POST", "promotion_result", result["evidence_id"]
        if (
            result["candidate_set"] != manifest["candidate_set"]
            or result["candidate_set_sha256"] != manifest["candidate_set_sha256"]
            or result["status"] != "POST"
        ):
            raise EvidenceSchemaError("POST catalog candidate set or status is not PRE-authorized")
    try:
        relative = source.relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise EvidenceSchemaError("promotion source must be inside repo_root") from exc
    artifacts = [*manifest["input_artifacts"], *manifest["result_artifacts"]]
    if len({item["path"] for item in artifacts}) != len(artifacts):
        raise EvidenceSchemaError("promotion catalog artifacts must have unique paths")
    return {
        "schema_version": 2, "phase": phase, "valid": True, "evidence_id": evidence_id,
        "source_kind": kind, "source_path": relative, "source_sha256": digest,
        "authority_paths": manifest["authority_paths"],
        "catalog_dir": manifest["authority_paths"]["catalog_dir"],
        "candidate_set": manifest["candidate_set"],
        "candidate_set_sha256": manifest["candidate_set_sha256"],
        "source_artifacts": sorted(artifacts, key=lambda item: item["path"]),
        "outcomes": (
            {"inserted": result["inserted"], "conflicts": result["conflicts"]}
            if result is not None else None
        ),
    }


def _repo_ref(path: Path, root: Path, field: str) -> dict[str, str]:
    try:
        relative = path.resolve().relative_to(root).as_posix()
    except ValueError as exc:
        raise EvidenceSchemaError(f"{field} must be inside repo_root") from exc
    return {"path": relative, "sha256": sha256_file(path)}


def _strict_source_hashes(
    receipt: Dict[str, Any], run_dir: Path, root: Path,
    expected: list[dict[str, str]] | None = None,
    verified_run_dir: Path | None = None,
) -> list[dict[str, str]]:
    """Require complete sources bound to the verified snapshots used for parsing."""
    if receipt["missing"] or receipt["skipped"]:
        raise EvidenceSchemaError("promotion catalog requires no missing, skipped, or unparsable sources")
    sources: list[dict[str, str]] = []
    hash_dir = verified_run_dir or run_dir
    for item in receipt["sources"]:
        if set(item) - {"path", "status", "sha256", "size_bytes", "note"} or item.get("status") != "loaded":
            raise EvidenceSchemaError("promotion catalog requires every source to be loaded")
        path = hash_dir / item["path"]
        if not isinstance(item.get("sha256"), str) or sha256_file(path) != item["sha256"]:
            raise EvidenceSchemaError("promotion catalog source hash is incomplete or stale")
        source_path = run_dir / item["path"]
        try:
            relative = source_path.resolve().relative_to(root).as_posix()
        except ValueError as exc:
            raise EvidenceSchemaError("catalog source must be inside repo_root") from exc
        sources.append({"path": relative, "sha256": item["sha256"]})
    if not sources or len({item["path"] for item in sources}) != len(sources):
        raise EvidenceSchemaError("promotion catalog source hashes must be complete and unique")
    sources = sorted(sources, key=lambda item: item["path"])
    if expected is not None and sources != expected:
        raise EvidenceSchemaError(
            "promotion catalog sources must exactly equal manifest input_artifacts and result_artifacts"
        )
    return sources


def _promotion_receipt(
    receipt: Dict[str, Any], *, root: Path, db_path: Path, status: dict[str, Any],
    verified_run_dir: Path | None = None, verified_db_sha256: str | None = None,
) -> dict[str, Any]:
    upstream = {"kind": status["source_kind"], "path": status["source_path"], "sha256": status["source_sha256"]}
    manifest_path = (
        upstream["path"] if status["phase"] == "PRE"
        else Path(root / Path(*PurePosixPath(upstream["path"]).parts)).resolve()
    )
    if status["phase"] == "POST":
        result, manifest, manifest_sha256 = verify_promotion_result_v2(
            root / Path(*PurePosixPath(upstream["path"]).parts), repo_root=root)
        manifest_ref = _repo_ref(
            root / Path(*PurePosixPath(result["promotion_manifest_path"]).parts), root, "promotion manifest")
    else:
        manifest_ref = _repo_ref(root / Path(*PurePosixPath(manifest_path).parts), root, "promotion manifest")
    try:
        catalog_db_path = db_path.resolve().relative_to(root).as_posix()
    except ValueError as exc:
        raise EvidenceSchemaError("catalog DB must be inside repo_root") from exc
    return {
        "schema_version": 2,
        "kind": "catalog_promotion_receipt",
        "phase": status["phase"],
        "valid": True,
        "evidence_id": status["evidence_id"],
        "upstream": upstream,
        "promotion_manifest": manifest_ref,
        "catalog_db": {
            "path": catalog_db_path,
            "sha256": verified_db_sha256 or sha256_file(db_path),
        },
        "source_hashes": _strict_source_hashes(
            receipt, Path(receipt["run_dir"]), root, status["source_artifacts"],
            verified_run_dir),
    }

def _validate_catalog_candidate_identity(status: dict[str, Any]) -> None:
    """Require the phase's candidate and (for POST) outcome identity before publication."""
    candidates = status["candidate_set"]
    expected = {
        candidate["name"]: (candidate["buy_sha256"], candidate["sell_sha256"])
        for candidate in candidates
    }
    if not expected or len(expected) != len(candidates):
        raise EvidenceSchemaError("catalog promotion candidate set is not a unique PRE authority")
    outcomes = status["outcomes"]
    if status["phase"] == "PRE":
        if outcomes is not None:
            raise EvidenceSchemaError("PRE catalog must not carry POST outcomes")
        return
    if status["phase"] != "POST" or not isinstance(outcomes, dict):
        raise EvidenceSchemaError("catalog phase does not match its outcome authority")
    accounted: set[str] = set()
    for field in ("inserted", "conflicts"):
        values = outcomes.get(field)
        if not isinstance(values, list):
            raise EvidenceSchemaError("POST catalog outcomes must be lists")
        for outcome in values:
            name = outcome.get("name") if isinstance(outcome, dict) else None
            if name not in expected or name in accounted:
                raise EvidenceSchemaError("POST catalog outcome does not match PRE candidate identity")
            if field == "inserted":
                hashes = outcome.get("buy_sha256"), outcome.get("sell_sha256")
                if hashes != expected[name]:
                    raise EvidenceSchemaError("POST inserted outcome does not match PRE candidate hashes")
            accounted.add(name)
    if accounted != set(expected):
        raise EvidenceSchemaError("POST catalog outcomes do not account for every PRE candidate")

def _canonical_authority_records(status: dict[str, Any]) -> list[dict[str, str]]:
    """Derive the complete, ordered authority rows from the sealed v2 chain."""
    candidates = {
        candidate["name"]: candidate for candidate in status["candidate_set"]
    }
    if not candidates or len(candidates) != len(status["candidate_set"]):
        raise EvidenceSchemaError("catalog authority candidates must be unique and nonempty")
    records: list[dict[str, str]] = []
    if status["phase"] == "PRE":
        if status["outcomes"] is not None:
            raise EvidenceSchemaError("PRE catalog authority cannot contain outcomes")
        for name, candidate in candidates.items():
            records.append({
                "name": name,
                "buy_sha256": candidate["buy_sha256"],
                "sell_sha256": candidate["sell_sha256"],
                "phase": "PRE",
                "outcome": "authorized",
                "disposition": "pending_post",
            })
    elif status["phase"] == "POST" and isinstance(status["outcomes"], dict):
        outcomes: dict[str, tuple[str, str]] = {}
        for outcome in status["outcomes"].get("inserted", []):
            name = outcome["name"]
            outcomes[name] = ("inserted", "published")
        for outcome in status["outcomes"].get("conflicts", []):
            name = outcome["name"]
            outcomes[name] = ("conflict", outcome["reason"])
        if set(outcomes) != set(candidates):
            raise EvidenceSchemaError("POST catalog authority outcomes are incomplete")
        for name, candidate in candidates.items():
            outcome, disposition = outcomes[name]
            records.append({
                "name": name,
                "buy_sha256": candidate["buy_sha256"],
                "sell_sha256": candidate["sell_sha256"],
                "phase": "POST",
                "outcome": outcome,
                "disposition": disposition,
            })
    else:
        raise EvidenceSchemaError("catalog authority phase/outcomes are invalid")
    return sorted(records, key=lambda record: record["name"])


def _authority_summary(records: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "canonical_record_count": len(records),
        "canonical_record_sha256": sha256_canonical(records),
    }


def _write_authority_records(
    con: sqlite3.Connection, status: dict[str, Any],
) -> list[dict[str, str]]:
    """Persist only the sealed candidate identities and their phase disposition."""
    records = _canonical_authority_records(status)
    con.execute(
        "CREATE TABLE catalog_authority ("
        "name TEXT PRIMARY KEY, buy_sha256 TEXT NOT NULL, sell_sha256 TEXT NOT NULL, "
        "phase TEXT NOT NULL, outcome TEXT NOT NULL, disposition TEXT NOT NULL)"
    )
    con.executemany(
        "INSERT INTO catalog_authority "
        "(name, buy_sha256, sell_sha256, phase, outcome, disposition) "
        "VALUES (:name, :buy_sha256, :sell_sha256, :phase, :outcome, :disposition)",
        records,
    )
    _verify_authority_records(con, records)
    return records


def _verify_authority_records(
    con: sqlite3.Connection, expected: list[dict[str, str]],
) -> None:
    try:
        rows = con.execute(
            "SELECT name, buy_sha256, sell_sha256, phase, outcome, disposition "
            "FROM catalog_authority ORDER BY name"
        ).fetchall()
    except sqlite3.Error as exc:
        raise EvidenceSchemaError("catalog authority DB records are missing") from exc
    actual = [
        dict(zip(
            ("name", "buy_sha256", "sell_sha256", "phase", "outcome", "disposition"),
            row,
        ))
        for row in rows
    ]
    if actual != expected:
        raise EvidenceSchemaError("catalog authority DB records are omitted, extra, or misstated")


def _logical_catalog_state(path: Path, descriptor: int, label: str) -> dict[str, Any]:
    """Read the complete logical SQLite state while the pathname identity is retained."""
    _validate_retained_file_identity(path, descriptor, label)
    con = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True, isolation_level=None)
    try:
        objects = con.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
        ).fetchall()
        tables = [name for kind, name, _, _ in objects if kind == "table"]
        rows: dict[str, list[tuple[Any, ...]]] = {}
        table_info: dict[str, list[tuple[Any, ...]]] = {}
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            table_info[table] = con.execute(
                f"PRAGMA table_xinfo({quoted})").fetchall()
            rows[table] = sorted(
                con.execute(f"SELECT * FROM {quoted}").fetchall(),
                key=lambda row: repr(row),
            )
        pragmas = {
            name: con.execute(f"PRAGMA {name}").fetchone()[0]
            for name in ("application_id", "auto_vacuum", "encoding", "user_version")
        }
        return {
            "objects": objects,
            "table_info": table_info,
            "rows": rows,
            "pragmas": pragmas,
        }
    finally:
        con.close()
        _validate_retained_file_identity(path, descriptor, label)


def _verify_existing_authority_db(
    existing: Path, existing_descriptor: int, expected_db: Path, expected_descriptor: int,
    records: list[dict[str, str]],
) -> str:
    """Accept a crashed canonical DB only when its full logical state equals rebuild."""
    existing_state = _logical_catalog_state(
        existing, existing_descriptor, "published catalog authority DB")
    expected_state = _logical_catalog_state(
        expected_db, expected_descriptor, "catalog authority temporary file")
    if existing_state != expected_state:
        raise EvidenceSchemaError(
            "catalog publication reconciliation failed: existing catalog DB logical state "
            "does not match the rebuilt authority DB")
    _validate_retained_file_identity(
        existing, existing_descriptor, "published catalog authority DB")
    con = sqlite3.connect(f"{existing.as_uri()}?mode=ro", uri=True, isolation_level=None)
    try:
        _verify_authority_records(con, records)
    finally:
        con.close()
    return _sha256_retained_file(
        existing, existing_descriptor, "published catalog authority DB")


def _revalidate_authority_paths(
    root: Path, status: dict[str, Any], db_path: Path, receipt_path: Path,
) -> None:
    source = root / Path(*PurePosixPath(status["source_path"]).parts)
    fresh = _promotion_status(
        root,
        source if status["source_kind"] == "promotion_manifest" else None,
        source if status["source_kind"] == "promotion_result" else None,
    )
    if fresh != status:
        raise EvidenceSchemaError("sealed promotion authority changed during catalog build")
    _catalog_output_paths(root, db_path, receipt_path, fresh)


def _fsync_directory(path: Path) -> None:
    """Persist a POSIX directory entry; Windows publication is write-through."""
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _flush_file(path: Path) -> None:
    with open(path, "rb+") as handle:
        handle.flush()
        os.fsync(handle.fileno())

def _set_windows_readonly(path: Path, readonly: bool) -> None:
    """Persist and verify a Windows read-only publication attribute."""
    if os.name != "nt":
        return
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.GetFileAttributesW.restype = ctypes.c_uint32
    invalid = 0xFFFFFFFF
    attributes = kernel32.GetFileAttributesW(str(path))
    if attributes == invalid:
        raise EvidenceSchemaError(f"cannot inspect catalog publication attributes: {path}")
    desired = attributes | 0x1 if readonly else attributes & ~0x1
    if not kernel32.SetFileAttributesW(str(path), desired):
        raise EvidenceSchemaError(f"cannot set catalog publication immutability: {path}")
    verified = kernel32.GetFileAttributesW(str(path))
    if verified == invalid or bool(verified & 0x1) != readonly:
        raise EvidenceSchemaError(f"catalog publication immutability was not retained: {path}")


def _seal_published_catalog_pair(db_path: Path, receipt_path: Path) -> None:
    """Seal both canonical files while their write-denying handles remain retained."""
    _set_windows_readonly(db_path, True)
    _set_windows_readonly(receipt_path, True)


def recover_published_catalog_immutability(db_path: Path | str, receipt_path: Path | str) -> None:
    """Explicit administrative recovery only; build_all never unseals publications."""
    _set_windows_readonly(Path(db_path), False)
    _set_windows_readonly(Path(receipt_path), False)


def _write_temp_bytes(
    directory: Path, prefix: str, payload: bytes, mutation_guard: Any | None = None,
) -> Path:
    if mutation_guard is None:
        handle = tempfile.NamedTemporaryFile(prefix=prefix, suffix=".tmp", dir=directory, delete=False)
        try:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            handle.close()
        return Path(handle.name)
    path, descriptor = _create_authority_temp(directory, prefix, mutation_guard)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        if path.exists():
            path.unlink()
        raise
    mutation_guard.validate_file(path)
    return path


def _validate_retained_file_identity(path: Path, descriptor: int, label: str) -> None:
    """Require a retained file handle and its pathname to name one safe inode."""
    opened = os.fstat(descriptor)
    try:
        named = os.stat(path, follow_symlinks=False)
    except FileNotFoundError as exc:
        raise EvidenceSchemaError(f"{label} disappeared while retained") from exc
    if (
        not stat.S_ISREG(opened.st_mode)
        or opened.st_nlink != 1
        or not stat.S_ISREG(named.st_mode)
        or named.st_nlink != 1
        or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
    ):
        raise EvidenceSchemaError(f"{label} identity changed or is not a single-link regular file")
def _sha256_retained_file(path: Path, descriptor: int, label: str) -> str:
    """Hash a retained authority file only after confirming its pathname identity."""
    _validate_retained_file_identity(path, descriptor, label)
    import hashlib
    digest = hashlib.sha256()
    os.lseek(descriptor, 0, os.SEEK_SET)
    while chunk := os.read(descriptor, 1 << 20):
        digest.update(chunk)
    _validate_retained_file_identity(path, descriptor, label)
    return digest.hexdigest()
def _read_retained_file_bytes(path: Path, descriptor: int, label: str) -> bytes:
    _validate_retained_file_identity(path, descriptor, label)
    os.lseek(descriptor, 0, os.SEEK_SET)
    payload = bytearray()
    while chunk := os.read(descriptor, 1 << 20):
        payload.extend(chunk)
    _validate_retained_file_identity(path, descriptor, label)
    return bytes(payload)


def _validated_outer_catalog_receipt(
    value: object, expected: dict[str, Any],
) -> dict[str, Any]:
    """Accept a crashed outer receipt only when all non-time fields rebuild exactly."""
    if not isinstance(value, dict) or set(value) != set(expected):
        raise EvidenceSchemaError("published catalog outer receipt schema is not exact")
    generated_at = value.get("generated_at")
    if not isinstance(generated_at, str):
        raise EvidenceSchemaError("published catalog outer receipt generated_at is invalid")
    try:
        parsed = datetime.fromisoformat(generated_at)
    except ValueError as exc:
        raise EvidenceSchemaError(
            "published catalog outer receipt generated_at is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EvidenceSchemaError("published catalog outer receipt generated_at is not timezone-aware")
    deterministic = dict(value)
    deterministic.pop("generated_at")
    rebuilt = dict(expected)
    rebuilt.pop("generated_at", None)
    if deterministic != rebuilt:
        raise EvidenceSchemaError(
            "published catalog outer receipt does not match rebuilt deterministic fields")
    return value

def _validate_published_catalog_pair(
    db_path: Path, db_descriptor: int, receipt_path: Path, receipt_descriptor: int,
    root: Path,
) -> None:
    """Validate the published DB and receipt from their retained destination handles."""
    db_sha256 = _sha256_retained_file(
        db_path, db_descriptor, "published catalog authority DB")
    try:
        published_receipt = json.loads(_read_retained_file_bytes(
            receipt_path, receipt_descriptor, "published catalog authority receipt"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceSchemaError("published catalog receipt is not valid JSON") from exc
    promotion_receipt = published_receipt.get("promotion_receipt")
    if not isinstance(promotion_receipt, dict):
        raise EvidenceSchemaError("published catalog receipt lacks promotion receipt")
    catalog_db = promotion_receipt.get("catalog_db")
    if not isinstance(catalog_db, dict) or catalog_db.get("sha256") != db_sha256:
        raise EvidenceSchemaError("published catalog receipt does not bind the retained DB")
    validate_catalog_promotion_receipt_v2(promotion_receipt, repo_root=root)
    _validate_retained_file_identity(db_path, db_descriptor, "published catalog authority DB")
    _validate_retained_file_identity(
        receipt_path, receipt_descriptor, "published catalog authority receipt")
def _reconcile_published_catalog_pair(
    db_path: Path, db_descriptor: int, receipt_path: Path, receipt_descriptor: int,
    working_db_sha256: str, authority_records: list[dict[str, str]],
    expected_receipt: dict[str, Any], root: Path,
) -> dict[str, Any]:
    """Seal an interrupted publication only when both retained files still match."""
    try:
        if _sha256_retained_file(
            db_path, db_descriptor, "published catalog authority DB",
        ) != working_db_sha256:
            raise EvidenceSchemaError(
                "published catalog DB bytes do not match the rebuilt authority DB")
        con = sqlite3.connect(
            f"{db_path.as_uri()}?mode=ro", uri=True, isolation_level=None)
        try:
            _verify_authority_records(con, authority_records)
        finally:
            con.close()
        _validate_published_catalog_pair(
            db_path, db_descriptor, receipt_path, receipt_descriptor, root)
        published = _validated_outer_catalog_receipt(
            json.loads(_read_retained_file_bytes(
                receipt_path, receipt_descriptor, "published catalog authority receipt")),
            expected_receipt,
        )
    except (OSError, sqlite3.Error, UnicodeDecodeError, json.JSONDecodeError,
            EvidenceSchemaError) as exc:
        raise EvidenceSchemaError(
            f"catalog publication reconciliation failed: {exc}") from exc
    _seal_published_catalog_pair(db_path, receipt_path)
    return published




def _create_authority_temp(
    directory: Path, prefix: str, mutation_guard: Any,
) -> tuple[Path, int]:
    for _ in range(16):
        path = directory / f"{prefix}{uuid.uuid4().hex}.tmp"
        try:
            descriptor = mutation_guard.open_path(
                path, os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
        except FileExistsError:
            continue
        try:
            _validate_retained_file_identity(
                path, descriptor, "catalog authority temporary file")
            mutation_guard.validate_file(path)
        except BaseException:
            os.close(descriptor)
            raise
        return path, descriptor
    raise FileExistsError("cannot create unique catalog publication temporary file")


def _publish_no_replace(
    source: Path,
    destination: Path,
    mutation_guard: Any,
    *,
    source_descriptor: int | None = None,
) -> None:
    """Exclusively copy a retained authority file into a durable canonical path."""
    close_source = source_descriptor is None
    if source_descriptor is None:
        source_descriptor = mutation_guard.open_path(
            source, os.O_RDONLY | getattr(os, "O_BINARY", 0))
    destination_descriptor: int | None = None
    try:
        destination_descriptor = mutation_guard.open_path(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
            0o600,
        )
        _validate_retained_file_identity(
            source, source_descriptor, "catalog authority publication source")
        os.lseek(source_descriptor, 0, os.SEEK_SET)
        while chunk := os.read(source_descriptor, 1024 * 1024):
            view = memoryview(chunk)
            while view:
                written = os.write(destination_descriptor, view)
                if written == 0:
                    raise OSError("catalog authority publication write made no progress")
                view = view[written:]
        os.fsync(destination_descriptor)
    finally:
        if destination_descriptor is not None:
            os.close(destination_descriptor)
        if close_source:
            os.close(source_descriptor)
    published = os.stat(destination, follow_symlinks=False)
    if not stat.S_ISREG(published.st_mode) or published.st_nlink != 1:
        raise EvidenceSchemaError(
            "catalog authority publication destination is not a single-link regular file")
    mutation_guard.validate_file(destination)
    _fsync_directory(destination.parent)

@dataclass
class _PublicationReservation:
    """An OS-locked reservation file retained across a publisher crash."""

    path: Path
    descriptor: int
    token: bytes


def _lock_reservation(descriptor: int) -> None:
    """Take a non-blocking whole-file lock without replacing a live owner."""
    if os.name == "nt":
        import ctypes
        import msvcrt

        class _Overlapped(ctypes.Structure):
            _fields_ = [
                ("internal", ctypes.c_size_t),
                ("internal_high", ctypes.c_size_t),
                ("offset", ctypes.c_uint32),
                ("offset_high", ctypes.c_uint32),
                ("event", ctypes.c_void_p),
            ]

        # LockFileEx can lock a byte beyond EOF, so no contender writes a bootstrap
        # byte before ownership is established.
        if not ctypes.windll.kernel32.LockFileEx(
            msvcrt.get_osfhandle(descriptor), 0x00000002 | 0x00000001,
            0, 1, 0, ctypes.byref(_Overlapped()),
        ):
            raise FileExistsError("catalog publication reservation is held by a live owner")
        return
    import fcntl

    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise FileExistsError("catalog publication reservation is held by a live owner") from exc


def _unlock_reservation(descriptor: int) -> None:
    if os.name == "nt":
        import ctypes
        import msvcrt

        class _Overlapped(ctypes.Structure):
            _fields_ = [
                ("internal", ctypes.c_size_t),
                ("internal_high", ctypes.c_size_t),
                ("offset", ctypes.c_uint32),
                ("offset_high", ctypes.c_uint32),
                ("event", ctypes.c_void_p),
            ]

        if not ctypes.windll.kernel32.UnlockFileEx(
            msvcrt.get_osfhandle(descriptor), 0, 1, 0, ctypes.byref(_Overlapped())
        ):
            raise OSError(ctypes.get_last_error(), "cannot release catalog publication reservation")
        return
    import fcntl

    fcntl.flock(descriptor, fcntl.LOCK_UN)


def _reserve_publication(
    db_path: Path, receipt_path: Path, mutation_guard: Any,
) -> _PublicationReservation:
    """Acquire the durable reservation through the active authority mutation guard."""
    path = db_path.parent / f".{db_path.name}.{receipt_path.name}.publish"
    try:
        descriptor = mutation_guard.open_path(
            path, os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
    except FileExistsError:
        descriptor = mutation_guard.open_path(
            path, os.O_RDWR | getattr(os, "O_BINARY", 0), 0o600)
    try:
        _validate_retained_file_identity(path, descriptor, "catalog publication reservation")
        # POSIX flock and Win32 LockFileEx both acquire an empty reservation inode
        # before any owner token bytes are written.
        _lock_reservation(descriptor)
        token = (uuid.uuid4().hex + "\n").encode("ascii")
        os.ftruncate(descriptor, 0)
        os.lseek(descriptor, 0, os.SEEK_SET)
        os.write(descriptor, token)
        os.fsync(descriptor)
    except BaseException:
        os.close(descriptor)
        raise
    _fsync_directory(path.parent)
    return _PublicationReservation(path, descriptor, token)


def _abandon_reservation(reservation: _PublicationReservation) -> None:
    """Model process termination: release the OS lock but retain its file."""
    _unlock_reservation(reservation.descriptor)
    os.close(reservation.descriptor)


def _release_reservation(reservation: _PublicationReservation) -> None:
    """Mark the permanent reservation inode unowned, then release its OS lock."""
    unowned_marker = b"UNOWNED\n"
    try:
        os.lseek(reservation.descriptor, 0, os.SEEK_SET)
        current = os.read(
            reservation.descriptor, os.fstat(reservation.descriptor).st_size)
        if current != reservation.token:
            raise RuntimeError("catalog publication reservation ownership changed")
        os.ftruncate(reservation.descriptor, 0)
        os.lseek(reservation.descriptor, 0, os.SEEK_SET)
        os.write(reservation.descriptor, unowned_marker)
        os.fsync(reservation.descriptor)
    finally:
        _unlock_reservation(reservation.descriptor)
        os.close(reservation.descriptor)
    _fsync_directory(reservation.path.parent)


# ---------------------------------------------------------------------------
# build_all — 전체 오케스트레이션(멱등).
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# build_all — 전체 오케스트레이션(멱등).
# ---------------------------------------------------------------------------

def _manifest_snapshot_expectations(
    run_dir: Path, root: Path, artifacts: list[dict[str, str]],
) -> dict[str, str]:
    """Translate sealed repo artifact paths to run-relative snapshot paths."""
    expected: dict[str, str] = {}
    for artifact in artifacts:
        source = root / Path(*PurePosixPath(artifact["path"]).parts)
        try:
            rel = source.relative_to(run_dir.resolve()).as_posix()
        except ValueError as exc:
            raise EvidenceSchemaError("catalog manifest source must be inside run_dir") from exc
        if rel in expected or not isinstance(artifact.get("sha256"), str):
            raise EvidenceSchemaError("catalog manifest sources must be unique and hashed")
        expected[rel] = artifact["sha256"]
    return expected
_CATALOG_SOURCE_PACKAGE_RELS = frozenset((*_SHARED_RELS, "n_trials_ledger.jsonl"))


def _has_complete_catalog_source_package(
    run_dir: Path, root: Path, artifacts: list[dict[str, str]],
) -> bool:
    """Legacy corpus parsing is authorized only by a complete sealed package."""
    try:
        paths = {
            (root / Path(*PurePosixPath(item["path"]).parts)).resolve()
            .relative_to(run_dir.resolve()).as_posix()
            for item in artifacts
        }
    except ValueError:
        return False
    return _CATALOG_SOURCE_PACKAGE_RELS <= paths


def _record_manifest_sources(
    receipt: dict[str, Any], snapshot_dir: Path, artifacts: list[dict[str, str]],
    root: Path, run_dir: Path,
) -> None:
    """Record every sealed artifact without interpreting ordinary evidence as corpus."""
    for artifact in artifacts:
        source = root / Path(*PurePosixPath(artifact["path"]).parts)
        rel = source.resolve().relative_to(run_dir.resolve()).as_posix()
        record_source(receipt, snapshot_dir, snapshot_dir / rel)


def build_all(
    run_dir: Path | str,
    db_path: Path | str | None = None,
    receipt_path: Path | str | None = None,
    write_receipt: bool = True,
    *,
    repo_root: Path | str | None = None,
    promotion_manifest_path: Path | str | None = None,
    promotion_result_path: Path | str | None = None,
) -> Dict[str, Any]:
    """카탈로그 전체 빌드 — DB·영수증 생성 후 영수증 dict 반환."""
    run_dir = Path(run_dir)
    root = Path(repo_root).resolve() if repo_root is not None else root_from_run_dir(run_dir)
    promotion_status = _promotion_status(
        root, promotion_manifest_path, promotion_result_path)
    if promotion_status is not None and not write_receipt:
        raise EvidenceSchemaError("promotion catalog requires receipt publication")
    db_path, receipt_path = _catalog_output_paths(
        root, db_path, receipt_path, promotion_status)
    receipt = new_receipt(run_dir, db_path)
    source_snapshot_dir: Path | None = None
    content_run_dir = run_dir
    reservation: _PublicationReservation | None = None
    receipt_temp: Path | None = None
    authority_guard = None
    working_db_descriptor: int | None = None
    source_retention = None
    retained_snapshots: RetainedSourceSnapshots | None = None
    published_db_descriptor: int | None = None
    published_receipt_descriptor: int | None = None
    if promotion_status is not None:
        snapshot_expectations = _manifest_snapshot_expectations(
            run_dir.resolve(), root, promotion_status["source_artifacts"])
        if snapshot_expectations:
            source_snapshot_dir = snapshot_sources(
                run_dir, Path(tempfile.gettempdir()), snapshot_expectations)
            content_run_dir = source_snapshot_dir
    if promotion_status is None:
        receipt["catalog_authority"] = {
            "authoritative": False,
            "reason": "legacy best-effort catalog build; not promotion authority",
        }
        db_path.parent.mkdir(parents=True, exist_ok=True)
        working_db_path = db_path
    else:
        receipt["promotion_status"] = promotion_status
        mutation_guard = None
        if "authority_paths" in promotion_status:
            authority_guard = authority_mutation_guard(
                root, promotion_status["authority_paths"], fields=("catalog_dir",))
            mutation_guard = authority_guard.__enter__()
            mutation_guard.hold_path(db_path)
            mutation_guard.hold_path(receipt_path)
            mutation_guard.validate_file(db_path)
            mutation_guard.validate_file(receipt_path)
        if mutation_guard is None:
            raise EvidenceSchemaError("promotion catalog requires an active authority mutation guard")
        reservation = _reserve_publication(db_path, receipt_path, mutation_guard)
        mutation_guard.validate_file(db_path)
        mutation_guard.validate_file(receipt_path)
        try:
            working_db_path, working_db_descriptor = _create_authority_temp(
                db_path.parent, f".{db_path.name}.", mutation_guard)
        except BaseException:
            _release_reservation(reservation)
            if authority_guard is not None:
                authority_guard.__exit__(None, None, None)
            raise
    try:
        if source_snapshot_dir is not None:
            source_retention = retain_snapshot_sources(source_snapshot_dir)
            retained_snapshots = source_retention.__enter__()
            validate_retained_snapshot_sources()
        if promotion_status is not None:
            _validate_retained_file_identity(
                working_db_path, working_db_descriptor, "catalog authority temporary file")
            mutation_guard.validate_file(working_db_path)
        con = sqlite3.connect(working_db_path)
        try:
            create_schema(con)
            reset_tables(con)
            load_assets(con, run_dir, receipt, retained_snapshots, db_path)
            if promotion_status is not None:
                _record_manifest_sources(
                    receipt, content_run_dir, promotion_status["source_artifacts"], root, run_dir)
            complete_package = (
                promotion_status is None
                or _has_complete_catalog_source_package(
                    run_dir, root, promotion_status["source_artifacts"]))
            if complete_package:
                docs = {
                    rel: read_json(receipt, content_run_dir, rel)
                    for rel in _SHARED_RELS
                }
                ledger_rows = load_ledger_mirror(
                    con, content_run_dir, receipt, strict=promotion_status is not None)
                validate_retained_snapshot_sources()
                load_clauses(con, docs[_REL_D1], receipt)
                load_strategies(
                    con, docs[_REL_W2], docs[_REL_D1], docs[_REL_B1R], receipt)
                load_cells(con, content_run_dir, docs[_REL_O1G], receipt)
                load_judgments(con, docs, ledger_rows, receipt)
                validate_retained_snapshot_sources()
            elif promotion_status is not None:
                add_note(
                    receipt,
                    "promotion catalog used manifest artifacts only; complete sealed "
                    "catalog-source package was not supplied",
                )
            if promotion_status is not None:
                _validate_catalog_candidate_identity(promotion_status)
                authority_records = _write_authority_records(con, promotion_status)
                receipt["catalog_authority"] = {
                    "authoritative": True,
                    "phase": promotion_status["phase"],
                    **_authority_summary(authority_records),
                }
            con.commit()
            receipt["table_counts"] = table_counts(con)
        finally:
            con.close()
        if promotion_status is not None:
            validate_retained_snapshot_sources()
        if promotion_status is not None:
            _validate_retained_file_identity(
                working_db_path, working_db_descriptor, "catalog authority temporary file")
            _flush_file(working_db_path)
            working_db_sha256 = _sha256_retained_file(
                working_db_path, working_db_descriptor, "catalog authority temporary file")
            _strict_source_hashes(
                receipt, run_dir, root, promotion_status["source_artifacts"], source_snapshot_dir)
            if mutation_guard is not None:
                mutation_guard.validate_file(db_path)
                mutation_guard.validate_file(receipt_path)
            if receipt_path.exists() and not db_path.exists():
                raise EvidenceSchemaError("catalog receipt exists without its authority DB")
            canonical_db_sha256 = working_db_sha256
            existing_db = db_path.exists()
            if existing_db:
                mutation_guard.hold_write_denied_file(db_path)
                published_db_descriptor = mutation_guard.open_path(
                    db_path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
                _validate_retained_file_identity(
                    db_path, published_db_descriptor, "published catalog authority DB")
                canonical_db_sha256 = _verify_existing_authority_db(
                    db_path, published_db_descriptor, working_db_path,
                    working_db_descriptor, authority_records)
            else:
                if mutation_guard is not None:
                    mutation_guard.validate_file(db_path)
                _validate_retained_file_identity(
                    working_db_path, working_db_descriptor, "catalog authority temporary file")
                mutation_guard.validate_file(working_db_path)
                _publish_no_replace(
                    working_db_path, db_path, mutation_guard,
                    source_descriptor=working_db_descriptor)
                mutation_guard.validate_file(db_path)
                mutation_guard.hold_write_denied_file(db_path)
                mutation_guard.validate_file(db_path)
            if published_db_descriptor is None:
                published_db_descriptor = mutation_guard.open_path(
                    db_path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
            _validate_retained_file_identity(
                db_path, published_db_descriptor, "published catalog authority DB")
            published_db_sha256 = _sha256_retained_file(
                db_path, published_db_descriptor, "published catalog authority DB")
            if published_db_sha256 != canonical_db_sha256:
                raise EvidenceSchemaError(
                    "published catalog DB bytes do not match the verified canonical DB")
            if not existing_db and published_db_sha256 != working_db_sha256:
                raise EvidenceSchemaError(
                    "published catalog DB bytes do not match the verified working DB")
            _set_windows_readonly(db_path, True)
            receipt["promotion_receipt"] = _promotion_receipt(
                receipt, root=root, db_path=db_path, status=promotion_status,
                verified_run_dir=source_snapshot_dir, verified_db_sha256=canonical_db_sha256)
            validate_catalog_promotion_receipt_v2(
                receipt["promotion_receipt"], repo_root=root)
        if promotion_status is None:
            receipt["gitignore"] = ensure_gitignore(db_path.parent)
        if write_receipt:
            receipt_bytes = json.dumps(receipt, ensure_ascii=False, indent=1).encode("utf-8")
            if promotion_status is None:
                receipt_path.write_bytes(receipt_bytes)
            else:
                if mutation_guard is not None:
                    mutation_guard.validate_file(receipt_path)
                if receipt_path.exists():
                    mutation_guard.hold_write_denied_file(receipt_path)
                    published_receipt_descriptor = mutation_guard.open_path(
                        receipt_path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
                    return _reconcile_published_catalog_pair(
                        db_path, published_db_descriptor, receipt_path,
                        published_receipt_descriptor, canonical_db_sha256,
                        authority_records, receipt, root)
                receipt_temp = _write_temp_bytes(
                    receipt_path.parent, f".{receipt_path.name}.", receipt_bytes, mutation_guard)
                mutation_guard.validate_file(receipt_temp)
                _publish_no_replace(receipt_temp, receipt_path, mutation_guard)
                mutation_guard.validate_file(receipt_path)
                mutation_guard.hold_write_denied_file(receipt_path)
                published_receipt_descriptor = mutation_guard.open_path(
                    receipt_path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
                _validate_published_catalog_pair(
                    db_path, published_db_descriptor, receipt_path,
                    published_receipt_descriptor, root)
                _seal_published_catalog_pair(db_path, receipt_path)
        return receipt
    finally:
        if published_receipt_descriptor is not None:
            os.close(published_receipt_descriptor)
        if published_db_descriptor is not None:
            os.close(published_db_descriptor)
        if source_retention is not None:
            source_retention.__exit__(None, None, None)
        if working_db_descriptor is not None:
            os.close(working_db_descriptor)
            working_db_descriptor = None
        if receipt_temp is not None and receipt_temp.exists():
            receipt_temp.unlink()
        if source_snapshot_dir is not None and source_snapshot_dir.exists():
            for path in sorted(source_snapshot_dir.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
            source_snapshot_dir.rmdir()
        if promotion_status is not None and working_db_path.exists():
            working_db_path.unlink()
        if reservation is not None:
            _release_reservation(reservation)
        if authority_guard is not None:
            authority_guard.__exit__(None, None, None)
