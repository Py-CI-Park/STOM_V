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
import sqlite3
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, List, Optional, Tuple

from alpha_lab.discipline.evidence import (
    EvidenceSchemaError,
    sha256_canonical,
    validate_promotion_result_v2,
    verify_promotion_manifest_v2,
)

from alpha_lab.catalog.assets_registry import ASSET_REGISTRY
from alpha_lab.catalog.loaders import (
    load_cells, load_clauses, load_ledger_mirror, load_strategies,
)
from alpha_lab.catalog.schema import create_schema, reset_tables, table_counts
from alpha_lab.catalog.sources import (
    add_note, new_receipt, read_json, record_source, sha256_file,
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
) -> None:
    """자산 레지스트리 전량 적재 — 부재 자산도 행은 남기고 missing 기록."""
    root = root_from_run_dir(run_dir)
    for asset in ASSET_REGISTRY:
        base = root if asset["base"] == "root" else Path(run_dir)
        path = base / str(asset["path"])
        exists, sha, size, mtime = _stat_asset(path, str(asset["asset_id"]))
        if exists and path.is_file() and asset["asset_id"] != "research_assets_db":
            # 빌드 중인 자기 자신은 원천이 아니다 — 영수증 sources에서 제외
            # (빌드 중간 상태 해시가 '원천 sha'로 남는 자기모순 방지, 검증 지적).
            record_source(receipt, run_dir, path)
        elif not exists:
            receipt["missing"].append(f"[asset:{asset['asset_id']}] {asset['path']}")
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
    else:
        source = Path(promotion_result_path).resolve()
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EvidenceSchemaError("promotion result must be readable JSON") from exc
        result = validate_promotion_result_v2(raw, repo_root=repo_root)
        manifest_path = repo_root / Path(*PurePosixPath(result["promotion_manifest_path"]).parts)
        manifest, manifest_digest = verify_promotion_manifest_v2(
            manifest_path, repo_root=repo_root)
        if (
            result["evidence_id"] != manifest["evidence_id"]
            or result["promotion_manifest_sha256"] != manifest_digest
        ):
            raise EvidenceSchemaError("promotion result does not bind the verified PRE manifest")
        expected_names = {candidate["name"] for candidate in manifest["candidates"]}
        inserted_names = set()
        for item in result["inserted"]:
            if not isinstance(item, dict) or set(item) != {
                "name", "tables", "buy_sha256", "sell_sha256", "meta"
            } or item["name"] not in expected_names or item["tables"] != ["stockbuy", "stocksell"]:
                raise EvidenceSchemaError("promotion result inserted structure is invalid")
            inserted_names.add(item["name"])
        conflict_names = set()
        for item in result["conflicts"]:
            if not isinstance(item, dict) or set(item) != {"name", "reason", "tables"}:
                raise EvidenceSchemaError("promotion result conflicts structure is invalid")
            if item["name"] not in expected_names or item["reason"] != "name_exists":
                raise EvidenceSchemaError("promotion result conflict does not bind a candidate")
            conflict_names.add(item["name"])
        if inserted_names | conflict_names != expected_names or inserted_names & conflict_names:
            raise EvidenceSchemaError("promotion result must account for every PRE candidate exactly once")
        digest, phase, kind, evidence_id = sha256_canonical(raw), "POST", "promotion_result", result["evidence_id"]
    try:
        relative = source.relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise EvidenceSchemaError("promotion source must be inside repo_root") from exc
    return {
        "schema_version": 2, "phase": phase, "valid": True, "evidence_id": evidence_id,
        "source_kind": kind, "source_path": relative, "source_sha256": digest,
    }



# ---------------------------------------------------------------------------
# build_all — 전체 오케스트레이션(멱등).
# ---------------------------------------------------------------------------

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
    db_path = Path(db_path) if db_path else run_dir / "research_assets.db"
    receipt_path = (Path(receipt_path) if receipt_path
                    else run_dir / "research_assets_build_receipt.json")
    receipt = new_receipt(run_dir, db_path)
    if promotion_status is not None:
        receipt["promotion_status"] = promotion_status
    con = sqlite3.connect(db_path)
    try:
        create_schema(con)
        reset_tables(con)
        docs = {rel: read_json(receipt, run_dir, rel) for rel in _SHARED_RELS}
        load_assets(con, run_dir, receipt)
        ledger_rows = load_ledger_mirror(con, run_dir, receipt)
        load_clauses(con, docs[_REL_D1], receipt)
        load_strategies(con, docs[_REL_W2], docs[_REL_D1], docs[_REL_B1R], receipt)
        load_cells(con, run_dir, docs[_REL_O1G], receipt)
        load_judgments(con, docs, ledger_rows, receipt)
        con.commit()
        receipt["table_counts"] = table_counts(con)
    finally:
        con.close()
    receipt["gitignore"] = ensure_gitignore(run_dir)
    if write_receipt:
        Path(receipt_path).write_text(
            json.dumps(receipt, ensure_ascii=False, indent=1), encoding="utf-8")
    return receipt
