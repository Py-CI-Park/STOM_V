"""research_assets 카탈로그 단위 테스트 — 스키마·방어적 파싱·멱등성.

원본 DB/실물 의존 없음: 원천의 실측 스키마(2026-07-12 확인)를 축소 복제한
소형 픽스처(tmp_path)로만 검증한다. known 창 데이터 측정 없음 — 그릇 검증만.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import os
import threading
from pathlib import Path

import pytest

from alpha_lab.catalog import builder, schema, sources
from alpha_lab.catalog.assets_registry import ASSET_REGISTRY

# ---------------------------------------------------------------------------
# 픽스처 데이터 — 원천 실측 스키마의 최소 축소판.
# ---------------------------------------------------------------------------

_CLAUSE_COMMON = {
    "tier": "M", "n_sat": 10, "n_unsat": 20, "mde_pp": 0.01,
    "p_one_sided": 0.0, "p_two_sided": 0.0, "floor_pass": True,
    "n_boot": 4, "seed": 1, "year_delta": {"2022": {"delta_pp": 0.2, "sign": 1}},
}
_D1 = {
    "kind": "d1_clause_ablation_summary",
    "buy_sha256": "b" * 64, "sell_sha256": "s" * 64,
    "judgment": {
        "per_clause": {
            "1": dict(_CLAUSE_COMMON, num=1, text="1 < 초당매수수량", cat="quote_qty",
                      family="초당매수수량", delta_pp=0.2, ci_low_pp=0.1,
                      ci_high_pp=0.3, both_year_positive=True,
                      both_year_negative=False, fdr_survive=True,
                      classification="load_bearing"),
            "5": dict(_CLAUSE_COMMON, num=5, text="시가총액 < 3000", cat="cap_price",
                      family="시가총액", delta_pp=-0.125, ci_low_pp=-0.2,
                      ci_high_pp=-0.05, both_year_positive=False,
                      both_year_negative=True, fdr_survive=True,
                      classification="counter_productive"),
            # 실측 재현: inconclusive 절은 per_clause에 classification 필드가 없다.
            "22": dict(_CLAUSE_COMMON, num=22, text="고저평균대비등락율 > 0",
                       cat="change_band", family="고저평균", delta_pp=0.01,
                       ci_low_pp=-0.01, ci_high_pp=0.03,
                       both_year_positive=False, both_year_negative=False,
                       fdr_survive=False),
        },
        "n_load_bearing": 1, "n_counter_productive": 1, "n_weak_signal": 0,
        "load_bearing_nums": [1], "counter_productive_nums": [5],
        "weak_signal_nums": [], "inconclusive_nums": [22], "fdr_denominator": 2,
        "fdr_q": 0.1, "sanity_anchor_tripped": False,
        "kill1_all_zero_survivors": False,
    },
}
_W2 = {
    "api_compat": {"stockbuy": {"legacy_names": ["OLD_B"]}},
    "alp_v4_champions": [
        {"strategy": "ALP_V4_RR8_12", "family": "alpha_lab_v4",
         "total_return_pct": 100.0, "annual_return_pct": 40.0, "mdd_pct": 8.0,
         "win_rate": 57.0, "payoff_tpi": 1.2, "trades": 300,
         "rank_by_total": 3, "lineage": "902905 파생"}],
    "engine_top40_by_total_return": [
        {"strategy": "ALP_V4_RR8_12", "total_return_pct": 100.0, "rank_by_total": 3},
        {"strategy": "OLD_B", "total_return_pct": 55.0, "rank_by_total": 9}],
    "engine_top20_by_annualized": [],
    "human_hall_of_fame": [
        {"id": "#1", "total_return_pct": 50.0, "win_rate_pct": 60.0, "payoff": 1.5}],
}
_O1G = {
    "cells": [
        {"exit": "L3", "gap_b": 0, "gap_label": "0~5", "mktcap_b": 1,
         "mktcap_label": "소형", "win": 0, "win_label": "09:00", "n": 100,
         "n_candidates": 120, "exclusion_rate": 0.1, "censor_rate": 0.0,
         "insufficient": 0, "mean_net": -0.5, "median_net": -0.4,
         "q25_net": -1.0, "q75_net": 0.2, "p_net_ge0": 0.4, "p_net_ge1": 0.1,
         "mfe_mean": 0.8, "mae_mean": -1.2, "ci_low": -0.7, "ci_high": -0.3},
        {"exit": "h300", "gap_b": 3, "gap_label": "20~", "mktcap_b": 2,
         "mktcap_label": "대형", "win": 1, "win_label": "09:05", "n": 50,
         "n_candidates": 60, "exclusion_rate": 0.2, "censor_rate": 0.0,
         "insufficient": 1, "mean_net": -2.1, "median_net": -1.9,
         "q25_net": -3.0, "q75_net": -0.5, "p_net_ge0": 0.2, "p_net_ge1": 0.05,
         "mfe_mean": 0.3, "mae_mean": -2.5, "ci_low": -2.6, "ci_high": -1.7}],
    "judgment_raw": {"fdr_q": 0.1, "fdr_denominator": 144, "n_fdr_survivors": 0,
                     "strong_cells": [], "weak_cells": [],
                     "insufficient_cells": [], "kill_all_ci_high_negative": False},
}
_W5 = {"section3_signal_overlap": {
    "merged_RR8_3sib": {"overlap_absorbed_%": 60.7},
    "pairwise_overlap_RR8": {"RR8_0|RR8_12": 0.98}}}
_V2C = {"v2c_gate": {"n_families": 2, "n_pass": 0, "verdicts": {}},
        "overall_l1_l3_mean": -0.01, "overall_l1_h300_mean": -0.011}
_PROBE = {"probe1_min": {"verdict": "생존(audit-grade 전용)", "key_numbers": {}},
          "probe2_d9": {"verdict": "생존(일치 100%)", "key_numbers": {}}}
_D5R = {"headline": {"n_candidates": 8, "n_backstop_qualified": 2,
                     "any_pass": False, "best_candidate": "B1"}}
_B1V = {"all_pass": True, "both_pos": True, "agg_dP": 1538872,
        "y2022": {"dP": 947387}, "y2023": {"dP": 591485}}
_B1R = {"name": "ALP_D5R_B1_S",
        "pre": {"incumbent_buy_sha": "348c5181", "patch_sell_sha": "48018620"},
        "register": {"inserted": [
            {"name": "ALP_D5R_B1_S", "buy_sha256": "x" * 64,
             "sell_sha256": "y" * 64, "meta": {"sell_note": "rr8_12+절1"}}]},
        "post": {"incumbent_unchanged": True}}
_LEDGER_LINES = (
    {"ts": "t1", "series": "D1", "window": "w", "trial_type": "b(판정)",
     "target": "d1", "result": "양성", "session": "s"},
    {"ts": "t2", "series": "D5-R", "window": "w", "trial_type": "b(판정)",
     "target": "d5r", "result": "kill-2", "session": "s"},
    {"ts": "t3", "series": "D5-R", "window": "w", "trial_type": "a(엔진 확인)",
     "target": "b1", "result": "PASS", "session": "s"},
    {"ts": "t4", "series": "S-트랙", "window": "w", "trial_type": "b(판정)",
     "target": "v2c", "result": "KILL", "session": "s"},
)

_SV1_COLS = (
    "axis_set TEXT, map_type TEXT, time_label INTEGER, time_b INTEGER,"
    " updown_q INTEGER, mktcap_b INTEGER, h INTEGER, n INTEGER,"
    " n_candidates INTEGER, censor_rate REAL, insufficient INTEGER,"
    " p_net_ge0 REAL, p_net_ge1 REAL, mean_net REAL, median_net REAL,"
    " q25_net REAL, q75_net REAL, ci_low REAL, ci_high REAL,"
    " year2022_mean REAL, year2022_sign INTEGER, year2023_mean REAL,"
    " year2023_sign INTEGER, winrate REAL, payoff REAL, mfe_mean REAL,"
    " mae_mean REAL")
_V2_COLS = (
    "label_kind TEXT, axis_set TEXT, time_label INTEGER, time_b INTEGER,"
    " updown_q INTEGER, mktcap_b INTEGER, h INTEGER, n INTEGER,"
    " n_candidates INTEGER, censor_rate REAL, insufficient INTEGER,"
    " p_net_ge0 REAL, p_net_ge1 REAL, mean_net REAL, median_net REAL,"
    " q25_net REAL, q75_net REAL, ci_low REAL, ci_high REAL,"
    " winrate REAL, payoff REAL")


def _write_stats_dbs(run: Path) -> None:
    """S-v1 실측 스키마 축소판 db 2종 생성(v2a_pilot은 고의로 미생성)."""
    sv1 = sqlite3.connect(run / "stats_map" / "stats_map.db")
    for table in ("cells_l0", "cells_l1"):
        sv1.execute(f"CREATE TABLE {table} ({_SV1_COLS})")
        sv1.execute(
            f"INSERT INTO {table} (axis_set, map_type, time_label, h, n,"
            " mean_net, ci_low, ci_high) VALUES ('time_ud','l0',0,300,100,"
            " -0.1,-0.2,0.0)")
    sv1.commit(); sv1.close()
    v2 = sqlite3.connect(run / "stats_map" / "stats_map_v2a_full.db")
    v2.execute(f"CREATE TABLE cells_pilot_v2 ({_V2_COLS})")
    v2.execute("INSERT INTO cells_pilot_v2 (label_kind, n, mean_net, ci_low,"
               " ci_high) VALUES ('L3', 80, -0.05, -0.1, 0.01)")
    v2.execute("INSERT INTO cells_pilot_v2 (label_kind, n, mean_net, ci_low,"
               " ci_high) VALUES ('h300', 80, -0.06, -0.12, 0.0)")
    v2.commit(); v2.close()


@pytest.fixture()
def run_dir(tmp_path: Path) -> Path:
    """원천 실측 스키마 축소 픽스처 run 디렉토리."""
    run = tmp_path / "run"
    for sub in ("o1g", "d5r_b1_live", "stats_map"):
        (run / sub).mkdir(parents=True)
    files = {
        "d1_clause_ablation_summary.json": _D1,
        "d5r_triage_summary.json": _D5R,
        "o1g/o1g_grid_summary.json": _O1G,
        "w2_strategy_inventory.json": _W2,
        "w5_composite_survey.json": _W5,
        "w6a_giveback.json": {"task": "w6a"},
        "w4_full_build.json": {"build": {}},
        "w4_champion_overlay.json": {"champion_gate": {}},
        "v2c_gate_summary.json": _V2C,
        "probe_min_d9.json": _PROBE,
        "d5r_b1_live/_ab_verdict.json": _B1V,
        "d5r_b1_live/b1_registration_receipt.json": _B1R,
    }
    for rel, data in files.items():
        (run / rel).write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8")
    (run / "n_trials_ledger.jsonl").write_text(
        "\n".join(json.dumps(o, ensure_ascii=False) for o in _LEDGER_LINES) + "\n",
        encoding="utf-8")
    _write_stats_dbs(run)
    return run
def test_json_parse_uses_verified_bytes_when_source_path_is_swapped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    path = tmp_path / "source.json"
    original = b'{"value":"verified"}'
    path.write_bytes(original)
    receipt = {"sources": [], "missing": [], "skipped": [], "notes": []}
    original_loads = sources.json.loads

    def swap_then_parse(payload: str) -> object:
        path.write_text('{"value":"replacement"}', encoding="utf-8")
        return original_loads(payload)

    monkeypatch.setattr(sources.json, "loads", swap_then_parse)
    assert sources.read_json(receipt, tmp_path, "source.json") == {"value": "verified"}
    assert receipt["sources"] == [{
        "path": "source.json", "status": "loaded",
        "sha256": hashlib.sha256(original).hexdigest(),
        "size_bytes": len(original),
    }]


def test_sqlite_snapshot_remains_the_verified_database_after_source_swap(tmp_path: Path):
    source = tmp_path / "source.db"
    con = sqlite3.connect(source)
    con.execute("CREATE TABLE source_rows (value TEXT)")
    con.execute("INSERT INTO source_rows VALUES ('verified')")
    con.commit()
    con.close()
    expected = builder.sha256_file(source)
    snapshot = sources.snapshot_sources(tmp_path, tmp_path, {"source.db": expected})
    try:
        con = sqlite3.connect(source)
        con.execute("DROP TABLE source_rows")
        con.execute("CREATE TABLE source_rows (value TEXT)")
        con.execute("INSERT INTO source_rows VALUES ('replacement')")
        con.commit()
        con.close()
        snap_con = sqlite3.connect(f"file:{(snapshot / 'source.db').as_posix()}?mode=ro", uri=True)
        try:
            assert snap_con.execute("SELECT value FROM source_rows").fetchone()[0] == "verified"
        finally:
            snap_con.close()
    finally:
        (snapshot / "source.db").unlink()
        snapshot.rmdir()

def test_retained_snapshot_rejects_swap_after_snapshot_creation(tmp_path: Path):
    source = tmp_path / "source.json"
    source.write_text('{"value":"A"}', encoding="utf-8")
    snapshot = sources.snapshot_sources(
        tmp_path, tmp_path, {"source.json": builder.sha256_file(source)})
    try:
        snap_source = snapshot / "source.json"
        original = snap_source.read_bytes()
        replacement = snapshot / "replacement.json"
        replacement.write_text('{"value":"B"}', encoding="utf-8")
        with sources.retain_snapshot_sources(snapshot):
            if os.name == "nt":
                with pytest.raises(PermissionError):
                    os.replace(replacement, snap_source)
                assert snap_source.read_bytes() == original
                sources.validate_retained_snapshot_sources()
            else:
                os.replace(replacement, snap_source)
                assert sources.read_json(
                    {"sources": [], "missing": [], "skipped": [], "notes": []},
                    snapshot, "source.json",
                ) is None
                with pytest.raises(OSError, match="identity changed"):
                    sources.validate_retained_snapshot_sources()
    finally:
        if snapshot.exists():
            for path in sorted(snapshot.rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
            snapshot.rmdir()


def test_duplicate_source_record_rejects_a_hash_for_b_parse(tmp_path: Path):
    source = tmp_path / "source.json"
    source.write_bytes(b"A")
    receipt = {"sources": [], "missing": [], "skipped": [], "notes": []}
    sources.record_source(receipt, tmp_path, source)
    source.write_bytes(b"B")
    with pytest.raises(ValueError, match="different bytes"):
        sources.record_source(receipt, tmp_path, source)


def test_retained_published_pair_rejects_post_validation_db_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    db_path = tmp_path / "catalog.db"
    receipt_path = tmp_path / "catalog.receipt.json"
    db_path.write_bytes(b"verified DB")
    db_descriptor = os.open(db_path, os.O_RDONLY)
    receipt_descriptor: int | None = None
    monkeypatch.setattr(builder, "validate_catalog_promotion_receipt_v2", lambda *args, **kwargs: None)
    try:
        receipt_path.write_text(json.dumps({"promotion_receipt": {
            "catalog_db": {"sha256": builder._sha256_retained_file(
                db_path, db_descriptor, "published catalog authority DB")},
        }}), encoding="utf-8")
        receipt_descriptor = os.open(receipt_path, os.O_RDONLY)
        original = db_path.read_bytes()
        replacement = tmp_path / "replacement.db"
        replacement.write_bytes(b"replacement DB")
        if os.name == "nt":
            with pytest.raises(PermissionError):
                os.replace(replacement, db_path)
            assert db_path.read_bytes() == original
            builder._validate_published_catalog_pair(
                db_path, db_descriptor, receipt_path, receipt_descriptor, tmp_path)
        else:
            os.replace(replacement, db_path)
            with pytest.raises(ValueError, match="identity changed"):
                builder._validate_published_catalog_pair(
                    db_path, db_descriptor, receipt_path, receipt_descriptor, tmp_path)
    finally:
        if receipt_descriptor is not None:
            os.close(receipt_descriptor)
        os.close(db_descriptor)

# ---------------------------------------------------------------------------
# 스키마.
# ---------------------------------------------------------------------------

def test_schema_creates_exactly_six_tables():
    con = sqlite3.connect(":memory:")
    schema.create_schema(con)
    names = {r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
        " AND name NOT LIKE 'sqlite_%'")}
    assert names == set(schema.TABLES)
    assert len(schema.TABLES) == 6


def test_cells_label_tag_not_null_enforced():
    con = sqlite3.connect(":memory:")
    schema.create_schema(con)
    with pytest.raises(sqlite3.IntegrityError):
        con.execute(
            "INSERT INTO cells (source, source_path, label_tag)"
            " VALUES ('x', 'p', NULL)")
    # 딱지가 있으면 통과.
    con.execute("INSERT INTO cells (source, source_path, label_tag)"
                " VALUES ('x', 'p', '함정 설명 전용')")


# ---------------------------------------------------------------------------
# 빌드 — 소형 픽스처 파싱.
# ---------------------------------------------------------------------------

def test_build_all_counts_and_receipt(run_dir: Path):
    receipt = builder.build_all(run_dir)
    counts = receipt["table_counts"]
    assert counts["assets"] == len(ASSET_REGISTRY)
    assert counts["judgments"] == 7
    assert counts["clauses"] == 3
    # RR8_12(챔피언·top40 중복 union) + OLD_B + 인간 #1 + B1 = 4.
    assert counts["strategies"] == 4
    # sv1 l0 1 + l1 1 + v2a_full 2 + o1g 2 = 6 (v2a_pilot은 부재 → 스킵).
    assert counts["cells"] == 6
    assert counts["ledger_mirror"] == 4
    # 부재 원천이 '재생성 필요'로 기록됐는지.
    assert any("stats_map_v2a_pilot" in m for m in receipt["missing"])
    assert any(s.get("regen_cmd") for s in receipt["skipped"])
    # 영수증에 원천 sha256이 실렸는지.
    hashed = [s for s in receipt["sources"] if s.get("sha256")]
    assert hashed, "원천 sha256 기록이 비어 있다"


def test_build_all_strategy_details(run_dir: Path):
    builder.build_all(run_dir, write_receipt=False)
    con = sqlite3.connect(run_dir / builder.LEGACY_NON_AUTHORITATIVE_CATALOG_ROOT / "research_assets.db")
    rows = dict(con.execute("SELECT name, api_compat FROM strategies"))
    assert rows["OLD_B"].startswith("legacy")
    assert rows["#1"].startswith("원문없음")
    sha, = con.execute(
        "SELECT source_sha256 FROM strategies WHERE name='ALP_V4_RR8_12'"
    ).fetchone()
    assert json.loads(sha)["buy_sha256"] == "b" * 64  # D1 요약에서 보강
    tag, = con.execute(
        "SELECT status_tag FROM strategies WHERE name='#1'").fetchone()
    assert "외부 벤치마크" in tag
    b1 = con.execute(
        "SELECT api_compat, status_tag FROM strategies WHERE name='ALP_D5R_B1_S'"
    ).fetchone()
    assert b1[0] == "historical/non-authoritative(등록 영수증)"
    assert "비권위" in b1[1]
    # 분류 필드 부재 절(22)은 판정부 inconclusive_nums 목록으로 보강된다.
    assert con.execute(
        "SELECT classification FROM clauses WHERE clause_num=22"
    ).fetchone()[0] == "inconclusive"
    con.close()


def test_build_all_judgment_ledger_links(run_dir: Path):
    builder.build_all(run_dir, write_receipt=False)
    con = sqlite3.connect(run_dir / builder.LEGACY_NON_AUTHORITATIVE_CATALOG_ROOT / "research_assets.db")
    rows = {r[0]: (r[1], r[2], r[3]) for r in con.execute(
        "SELECT series, verdict, ledger_rows, n_ledger_rows FROM judgments")}
    assert rows["B1 감독형 이관 엔진 A/B"][0].startswith("PASS")
    assert rows["B1 감독형 이관 엔진 A/B"][1] == "3"  # type-a 행만
    assert rows["D1 절-단위 분해"][1] == "1"
    assert rows["D5-R 조건부 청산 triage"][1] == "2"  # type-b 행만
    assert all(r[2] >= 0 for r in rows.values())
    # 확정 판정 GA 플래그는 전부 0.
    assert con.execute(
        "SELECT COUNT(*) FROM judgments WHERE ga_path_flag != 0").fetchone()[0] == 0
    con.close()


def test_missing_source_is_recorded_not_fatal(run_dir: Path):
    (run_dir / "w6a_giveback.json").unlink()
    receipt = builder.build_all(run_dir, write_receipt=False)
    assert "w6a_giveback.json" in receipt["missing"]
    assert receipt["table_counts"]["judgments"] == 7  # 빌드는 계속된다


def test_rebuild_is_idempotent(run_dir: Path):
    first = builder.build_all(run_dir)
    second = builder.build_all(run_dir)
    assert first["table_counts"] == second["table_counts"]
    con = sqlite3.connect(run_dir / builder.LEGACY_NON_AUTHORITATIVE_CATALOG_ROOT / "research_assets.db")
    n, max_id = con.execute("SELECT COUNT(*), MAX(cell_id) FROM cells").fetchone()
    con.close()
    assert n == max_id  # cell_id 시퀀스 초기화 — 재빌드 중복 없음


# ---------------------------------------------------------------------------
# .gitignore 보장.
# ---------------------------------------------------------------------------

def test_gitignore_created_and_then_ok(run_dir: Path):
    first = builder.ensure_gitignore(run_dir)
    assert first["action"] == "created"
    text = (run_dir / ".gitignore").read_text(encoding="utf-8")
    assert "research_assets.db*" in text
    second = builder.ensure_gitignore(run_dir)
    assert second["action"].startswith("ok")


def test_gitignore_existing_star_db_pattern_is_respected(tmp_path: Path):
    run = tmp_path / "run2"
    run.mkdir()
    (run / ".gitignore").write_text("*.db\n", encoding="utf-8")
    result = builder.ensure_gitignore(run)
    assert result["action"].startswith("ok")
    assert (run / ".gitignore").read_text(encoding="utf-8") == "*.db\n"


def test_gitignore_appends_preserving_content(tmp_path: Path):
    run = tmp_path / "run3"
    run.mkdir()
    (run / ".gitignore").write_text("*.parquet", encoding="utf-8")  # 개행 없음
    result = builder.ensure_gitignore(run)
    assert result["action"].startswith("appended")
    text = (run / ".gitignore").read_text(encoding="utf-8")
    assert text.startswith("*.parquet\n")
    assert "research_assets.db*" in text
def _promotion_status(evidence_id: str = "a" * 64) -> dict[str, object]:
    return {
        "schema_version": 2,
        "phase": "PRE",
        "valid": True,
        "evidence_id": evidence_id,
        "source_kind": "promotion_manifest",
        "source_path": "promotions/test.pre.json",
        "source_sha256": "b" * 64,
        "catalog_dir": "promotion_catalogs",
    }


class _ReservationGuard:
    """Minimal mutation-guard double that exposes only verified open handles."""

    def __init__(self) -> None:
        self.opened: list[Path] = []

    def open_path(self, path: Path, flags: int, mode: int = 0o666) -> int:
        self.opened.append(path)
        return os.open(path, flags, mode)

    def validate_file(self, path: Path) -> None:
        if path.exists() and path.stat().st_nlink != 1:
            raise builder.EvidenceSchemaError("test guard rejected hardlinked target")

    def hold_path(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

    def hold_write_denied_file(self, path: Path) -> None:
        return None
    def __enter__(self) -> "_ReservationGuard":
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _reserve(db_path: Path, receipt_path: Path) -> builder._PublicationReservation:
    return builder._reserve_publication(db_path, receipt_path, _ReservationGuard())


def test_catalog_output_paths_keep_legacy_defaults_non_authoritative(run_dir: Path):
    db_path, receipt_path = builder._catalog_output_paths(run_dir, None, None, None)

    assert db_path == run_dir / builder.LEGACY_NON_AUTHORITATIVE_CATALOG_ROOT / "research_assets.db"
    assert receipt_path == run_dir / builder.LEGACY_NON_AUTHORITATIVE_CATALOG_ROOT / "research_assets_build_receipt.json"


def test_catalog_output_paths_use_evidence_bound_promotion_defaults(run_dir: Path):
    evidence_id = "a" * 64
    status = {**_promotion_status(evidence_id), "catalog_dir": "sealed_catalogs"}
    db_path, receipt_path = builder._catalog_output_paths(run_dir, None, None, status)

    assert db_path == run_dir / "sealed_catalogs" / f"{evidence_id}.pre.db"
    assert receipt_path == run_dir / "sealed_catalogs" / f"{evidence_id}.pre.receipt.json"


@pytest.mark.parametrize("field", ["db_path", "receipt_path"])
def test_promotion_output_aliases_are_rejected_before_mutation(
    run_dir: Path, monkeypatch: pytest.MonkeyPatch, field: str,
):
    evidence_id = "a" * 64
    canonical_db = run_dir / "promotion_catalogs" / f"{evidence_id}.db"
    canonical_receipt = run_dir / "promotion_catalogs" / f"{evidence_id}.receipt.json"
    alias = canonical_db.parent / "alias" / ".." / canonical_db.name
    kwargs = {
        "db_path": canonical_db,
        "receipt_path": canonical_receipt,
        field: alias,
        "repo_root": run_dir,
        "promotion_manifest_path": run_dir / "promotions" / "test.pre.json",
    }
    monkeypatch.setattr(builder, "_promotion_status", lambda *args: _promotion_status(evidence_id))

    with pytest.raises(ValueError, match="authority-owned canonical path"):
        builder.build_all(run_dir, **kwargs)

    assert not (run_dir / "promotion_catalogs").exists()
    assert not (run_dir / ".gitignore").exists()


@pytest.mark.parametrize("field", ["db_path", "receipt_path"])
def test_legacy_outputs_reject_promotion_namespace_before_mutation(
    run_dir: Path, field: str,
):
    namespace_path = run_dir / "promotion_catalogs" / "untrusted.db"
    kwargs = {field: namespace_path}

    with pytest.raises(ValueError, match="authority-owned canonical path"):
        builder.build_all(run_dir, **kwargs)

    assert not (run_dir / "promotion_catalogs").exists()
    assert not (run_dir / ".gitignore").exists()


def test_build_all_rejects_shape_only_promotion_before_catalog_mutation(run_dir: Path):
    db_path = run_dir / builder.LEGACY_NON_AUTHORITATIVE_CATALOG_ROOT / "research_assets.db"
    builder.build_all(run_dir, write_receipt=False)
    before = db_path.read_bytes()
    manifest_path = run_dir / "promotion_manifest.json"
    manifest_path.write_text(json.dumps({"schema_version": 2, "kind": "promotion_manifest"}), encoding="utf-8")
    with pytest.raises(ValueError):
        builder.build_all(
            run_dir, write_receipt=False, repo_root=run_dir,
            promotion_manifest_path=manifest_path)
    assert db_path.read_bytes() == before


@pytest.mark.parametrize("field, value", [
    ("missing", ["required.json"]),
    ("skipped", [{"path": "required.json", "reason": "parse failure"}]),
])
def test_promotion_source_receipt_rejects_incomplete_inputs(
    tmp_path: Path, field: str, value: list,
):
    source = tmp_path / "required.json"
    source.write_text("{}", encoding="utf-8")
    receipt = {
        "run_dir": str(tmp_path),
        "missing": [],
        "skipped": [],
        "sources": [{"path": "required.json", "status": "loaded",
                     "sha256": builder.sha256_file(source), "size_bytes": 2}],
    }
    receipt[field] = value
    with pytest.raises(ValueError):
        builder._strict_source_hashes(receipt, tmp_path, tmp_path)


def test_strict_ledger_loader_rejects_unrelated_malformed_row(tmp_path: Path):
    ledger = tmp_path / "n_trials_ledger.jsonl"
    ledger.write_text('{"ts":"not-a-timestamp"}\n', encoding="utf-8")
    con = sqlite3.connect(":memory:")
    schema.create_schema(con)
    receipt = {"missing": [], "skipped": [], "sources": [], "notes": []}
    with pytest.raises(ValueError):
        builder.load_ledger_mirror(con, tmp_path, receipt, strict=True)
    con.close()
@pytest.mark.skipif(os.name != "nt", reason="Windows authority is the supported platform")
def test_retained_snapshot_ledger_and_sqlite_deny_same_inode_overwrite(tmp_path: Path):
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    ledger = snapshot / "n_trials_ledger.jsonl"
    ledger.write_text('{"ts":"2026-01-01T00:00:00+00:00"}\n', encoding="utf-8")
    catalog = snapshot / "source.db"
    con = sqlite3.connect(catalog)
    try:
        con.execute("CREATE TABLE snapshot_authority (value TEXT NOT NULL)")
        con.execute("INSERT INTO snapshot_authority VALUES ('verified')")
        con.commit()
    finally:
        con.close()
    originals = {path: path.read_bytes() for path in (ledger, catalog)}

    with sources.retain_snapshot_sources(snapshot):
        assert json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])["ts"]
        con = sqlite3.connect(f"{catalog.as_uri()}?mode=ro", uri=True)
        try:
            assert con.execute("SELECT value FROM snapshot_authority").fetchone() == ("verified",)
        finally:
            con.close()
        for path in (ledger, catalog):
            with pytest.raises(OSError) as exc:
                path.write_bytes(b"same-inode overwrite")
            assert (
                getattr(exc.value, "winerror", None) in {5, 32}
                or exc.value.errno == 13
            )
            assert path.read_bytes() == originals[path]
            assert sources.sha256_file(path) == hashlib.sha256(originals[path]).hexdigest()


@pytest.mark.skipif(os.name != "nt", reason="Windows authority is the supported platform")
def test_final_publication_pair_denies_in_place_overwrite_until_guard_release(tmp_path: Path):
    from alpha_lab.discipline.prereg import _WindowsAuthorityGuard

    db_path = tmp_path / "published.db"
    receipt_path = tmp_path / "published.receipt.json"
    db_path.write_bytes(b"verified database bytes")
    receipt_path.write_bytes(b'{"verified":true}')
    originals = {path: path.read_bytes() for path in (db_path, receipt_path)}
    guard = _WindowsAuthorityGuard(tmp_path, {}, ())
    try:
        for path in originals:
            guard.hold_write_denied_file(path)
        for path in originals:
            with pytest.raises(OSError) as exc:
                path.write_bytes(b"same-inode overwrite")
            assert (
                getattr(exc.value, "winerror", None) in {5, 32}
                or exc.value.errno == 13
            )
            assert path.read_bytes() == originals[path]
    finally:
        guard.close()
def test_promotion_sources_must_exactly_match_manifest_artifacts(tmp_path: Path):
    source = tmp_path / "bound.json"
    extra = tmp_path / "extra.json"
    source.write_text("bound", encoding="utf-8")
    extra.write_text("extra", encoding="utf-8")
    receipt = {
        "run_dir": str(tmp_path), "missing": [], "skipped": [], "notes": [],
        "sources": [
            {"path": "bound.json", "status": "loaded",
             "sha256": builder.sha256_file(source), "size_bytes": source.stat().st_size},
        ],
    }
    bound = [{"path": "bound.json", "sha256": builder.sha256_file(source)}]

    assert builder._strict_source_hashes(receipt, tmp_path, tmp_path, bound) == bound
    receipt["sources"].append(
        {"path": "extra.json", "status": "loaded",
         "sha256": builder.sha256_file(extra), "size_bytes": extra.stat().st_size})
    with pytest.raises(ValueError, match="exactly equal"):
        builder._strict_source_hashes(receipt, tmp_path, tmp_path, bound)
def _authority_status(phase: str) -> dict[str, object]:
    candidates = [
        {"name": "ALP_A", "buy_sha256": "a" * 64, "sell_sha256": "b" * 64},
        {"name": "ALP_B", "buy_sha256": "c" * 64, "sell_sha256": "d" * 64},
    ]
    return {
        "phase": phase,
        "candidate_set": candidates,
        "outcomes": (
            None if phase == "PRE" else {
                "inserted": [{
                    "name": "ALP_A", "buy_sha256": "a" * 64,
                    "sell_sha256": "b" * 64,
                }],
                "conflicts": [{
                    "name": "ALP_B", "reason": "name_exists",
                    "existing_tables": ["stockbuy"],
                }],
            }
        ),
    }


@pytest.mark.parametrize("phase", ["PRE", "POST"])
def test_catalog_authority_records_bind_every_candidate_and_disposition(
    tmp_path: Path, phase: str,
):
    status = _authority_status(phase)
    records = builder._canonical_authority_records(status)

    assert [record["name"] for record in records] == ["ALP_A", "ALP_B"]
    assert records[0]["buy_sha256"] == "a" * 64
    assert records[1]["sell_sha256"] == "d" * 64
    assert records[0]["phase"] == phase
    if phase == "PRE":
        assert {record["disposition"] for record in records} == {"pending_post"}
    else:
        assert [(record["outcome"], record["disposition"]) for record in records] == [
            ("inserted", "published"), ("conflict", "name_exists"),
        ]

    con = sqlite3.connect(tmp_path / f"{phase}.db")
    try:
        persisted = builder._write_authority_records(con, status)
        assert builder._authority_summary(persisted) == {
            "canonical_record_count": 2,
            "canonical_record_sha256": builder.sha256_canonical(records),
        }
        con.execute(
            "INSERT INTO catalog_authority VALUES ('extra', ?, ?, ?, ?, ?)",
            ("e" * 64, "f" * 64, phase, "extra", "extra"),
        )
        with pytest.raises(ValueError, match="omitted, extra, or misstated"):
            builder._verify_authority_records(con, records)
        con.execute("DELETE FROM catalog_authority WHERE name = 'extra'")
        con.execute("DELETE FROM catalog_authority WHERE name = 'ALP_B'")
        with pytest.raises(ValueError, match="omitted, extra, or misstated"):
            builder._verify_authority_records(con, records)
        con.execute(
            "INSERT INTO catalog_authority VALUES ('ALP_B', ?, ?, ?, ?, ?)",
            ("c" * 64, "d" * 64, phase, "wrong", "wrong"),
        )
        with pytest.raises(ValueError, match="omitted, extra, or misstated"):
            builder._verify_authority_records(con, records)
    finally:
        con.close()


def test_no_replace_publication_preserves_first_authority_bytes(tmp_path: Path):
    first = builder._write_temp_bytes(tmp_path, ".first.", b"first")
    second = builder._write_temp_bytes(tmp_path, ".second.", b"second")
    destination = tmp_path / "canonical.db"
    guard = _ReservationGuard()
    try:
        builder._publish_no_replace(first, destination, guard)
        with pytest.raises(FileExistsError):
            builder._publish_no_replace(second, destination, guard)
        assert destination.read_bytes() == b"first"
        assert destination.stat().st_nlink == 1
        assert first.stat().st_nlink == 1
    finally:
        for path in (first, second):
            if path.exists():
                path.unlink()
def test_retained_catalog_temp_rejects_protected_hardlink_swap(tmp_path: Path):
    protected = tmp_path / "protected.db"
    protected.write_bytes(b"protected authority bytes")
    guard = _ReservationGuard()
    candidate, descriptor = builder._create_authority_temp(tmp_path, ".candidate.", guard)
    try:
        with pytest.raises((builder.EvidenceSchemaError, PermissionError)):
            os.unlink(candidate)
            os.link(protected, candidate)
            builder._validate_retained_file_identity(
                candidate, descriptor, "catalog authority temporary file")
        assert protected.read_bytes() == b"protected authority bytes"
    finally:
        os.close(descriptor)
        if candidate.exists():
            candidate.unlink()


def test_live_publication_owner_cannot_be_stolen(tmp_path: Path):
    db_path = tmp_path / "evidence.pre.db"
    receipt_path = tmp_path / "evidence.pre.receipt.json"
    barrier = threading.Barrier(2)
    wins: list[builder._PublicationReservation] = []
    failures: list[BaseException] = []

    def reserve() -> None:
        barrier.wait()
        try:
            wins.append(_reserve(db_path, receipt_path))
        except FileExistsError as exc:
            failures.append(exc)

    workers = [threading.Thread(target=reserve), threading.Thread(target=reserve)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    try:
        assert len(wins) == 1
        assert len(failures) == 1
        assert wins[0].path.exists()
    finally:
        for reservation in wins:
            builder._release_reservation(reservation)


def test_abandoned_publication_reservation_is_recovered_after_crash(tmp_path: Path):
    db_path = tmp_path / "evidence.pre.db"
    receipt_path = tmp_path / "evidence.pre.receipt.json"
    crashed_owner = _reserve(db_path, receipt_path)

    builder._abandon_reservation(crashed_owner)

    assert crashed_owner.path.exists()
    retry_owner = _reserve(db_path, receipt_path)
    try:
        assert retry_owner.path == crashed_owner.path
        assert retry_owner.token != crashed_owner.token
    finally:
        builder._release_reservation(retry_owner)
    assert crashed_owner.path.exists()
    assert crashed_owner.path.read_bytes() == b"UNOWNED\n"


def test_preplaced_hardlink_reservation_is_rejected(tmp_path: Path):
    db_path = tmp_path / "evidence.pre.db"
    receipt_path = tmp_path / "evidence.pre.receipt.json"
    reservation_path = tmp_path / f".{db_path.name}.{receipt_path.name}.publish"
    original = tmp_path / "preplaced"
    original.write_bytes(b"attacker")
    os.link(original, reservation_path)

    with pytest.raises(ValueError, match="single-link"):
        _reserve(db_path, receipt_path)


def test_reservation_locks_empty_inode_before_token_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
):
    db_path = tmp_path / "evidence.pre.db"
    receipt_path = tmp_path / "evidence.pre.receipt.json"
    observed_sizes: list[int] = []
    original_lock = builder._lock_reservation

    def lock_after_observing_empty(descriptor: int) -> None:
        observed_sizes.append(os.fstat(descriptor).st_size)
        original_lock(descriptor)

    monkeypatch.setattr(builder, "_lock_reservation", lock_after_observing_empty)
    reservation = _reserve(db_path, receipt_path)
    try:
        assert observed_sizes == [0]
    finally:
        builder._release_reservation(reservation)

def test_build_all_recovers_db_only_crash_with_abandoned_reservation(
    run_dir: Path, monkeypatch: pytest.MonkeyPatch,
):
    status = {
        **_authority_status("PRE"),
        "schema_version": 2,
        "valid": True,
        "evidence_id": "a" * 64,
        "source_kind": "promotion_manifest",
        "source_path": "promotions/test.pre.json",
        "source_sha256": "b" * 64,
        "catalog_dir": "promotion_catalogs",
        "source_artifacts": [],
        "authority_paths": {"catalog_dir": "promotion_catalogs"},
    }
    db_path = run_dir / "promotion_catalogs" / f"{status['evidence_id']}.pre.db"
    receipt_path = run_dir / "promotion_catalogs" / f"{status['evidence_id']}.pre.receipt.json"
    original_publish = builder._publish_no_replace
    original_release = builder._release_reservation

    monkeypatch.setattr(builder, "_promotion_status", lambda *args: status)
    test_guard = _ReservationGuard()
    monkeypatch.setattr(builder, "authority_mutation_guard", lambda *args, **kwargs: test_guard)
    monkeypatch.setattr(builder, "_strict_source_hashes", lambda *args, **kwargs: [])
    monkeypatch.setattr(builder, "load_ledger_mirror", lambda *args, **kwargs: [])
    monkeypatch.setattr(builder, "_revalidate_authority_paths", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        builder,
        "_promotion_receipt",
        lambda *args, **kwargs: {
            "schema_version": 2,
            "catalog_db": {"sha256": kwargs["verified_db_sha256"]},
        },
    )
    monkeypatch.setattr(builder, "validate_catalog_promotion_receipt_v2", lambda *args, **kwargs: None)

    class SimulatedCrash(BaseException):
        pass

    def publish_db_then_crash(
        source: Path,
        destination: Path,
        mutation_guard: _ReservationGuard,
        *,
        source_descriptor: int | None = None,
    ) -> None:
        original_publish(
            source, destination, mutation_guard, source_descriptor=source_descriptor)
        if destination == db_path:
            raise SimulatedCrash()

    monkeypatch.setattr(builder, "_publish_no_replace", publish_db_then_crash)
    monkeypatch.setattr(builder, "_release_reservation", builder._abandon_reservation)
    with pytest.raises(SimulatedCrash):
        builder.build_all(
            run_dir, repo_root=run_dir,
            promotion_manifest_path=run_dir / "promotions" / "test.pre.json",
        )

    db_bytes = db_path.read_bytes()
    reservation_path = db_path.parent / f".{db_path.name}.{receipt_path.name}.publish"
    assert reservation_path.exists()
    assert not receipt_path.exists()

    monkeypatch.setattr(builder, "_publish_no_replace", original_publish)
    monkeypatch.setattr(builder, "_release_reservation", original_release)
    builder.build_all(
        run_dir, repo_root=run_dir,
        promotion_manifest_path=run_dir / "promotions" / "test.pre.json",
    )

    assert db_path.read_bytes() == db_bytes
    assert receipt_path.exists()
    assert reservation_path.exists()
    assert reservation_path.read_bytes() == b"UNOWNED\n"
