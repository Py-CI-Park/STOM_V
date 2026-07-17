"""onset_bank_v2 단위 테스트 — WBS v3 P2 은행 v2 스키마 그릇.

검증 대상:
- BANK_V2_SCHEMA 구성(v1 12컬럼 보존 + 신규 4컬럼 전부 필수).
- migrate_v1_to_v2: dry_run 영수증(행수·스키마)·파일 미생성, 스키마 불일치 검출,
  잘못된 계보 값 거부, (소형 픽스처 한정) 실제 마이그레이션의 "기존 값 불변" 보증.
- append_contract: 정상 통과, onset_type 불일치·창 이탈·중복 키·스키마 결손·
  빈 필수값 검출.
- MIN_OVERLAY_SCHEMA 스텁(조인 키 + audit-grade 딱지 필수).
- (존재 시) 실물 v1 은행의 스키마가 봉인 BANK_V1_SCHEMA 와 일치하는지 —
  스키마만 판독(전량 로드 없음), 파일 부재 시 skip.

픽스처는 합성 6행 parquet(tmp_path) — 실물 자산은 만들지도 고치지도 않는다.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_lab.stats_map import onset_bank_v2 as obv

REAL_BANK = Path(
    "C:/System_Trading/STOM/STOM_V.wt-alpha/docs/research/condition_research/"
    "research_runs/alpha_restart_20260710/stats_map/onset_l3_bank.parquet")

_SEAL = "2026-07-12_d1_clause_ablation_preregistration.md"


def _v1_frame() -> pd.DataFrame:
    """v1 은행 실측 스키마를 미러링한 합성 6행(2022 3행 + 2023 3행)."""
    return pd.DataFrame({
        "code": np.array(["005930", "005930", "000660",
                          "035720", "005930", "000660"], dtype=object),
        "day": np.array([20220323, 20220323, 20220323,
                         20230105, 20230105, 20230105], dtype=np.int32),
        "off": np.array([12, 84, 240, 12, 96, 300], dtype=np.int16),
        "t0": np.array([20220323090012, 20220323090124, 20220323090400,
                        20230105090012, 20230105090136, 20230105090500],
                       dtype=np.int64),
        "year": np.array([2022, 2022, 2022, 2023, 2023, 2023], dtype=np.int16),
        "updown_q": np.array([0, 1, 2, 3, 1, 2], dtype=np.int8),
        "mktcap_b": np.array([2, 2, 1, 0, 2, 1], dtype=np.int8),
        "time_b": np.array([0, 0, 1, 0, 0, 1], dtype=np.int8),
        "l3_net": np.array([0.42, -0.55, 0.0, 1.2, -0.61, 0.13],
                           dtype=np.float64),
        "l3_labeled": np.array([True, True, False, True, True, True],
                               dtype=bool),
        "l3_clause": np.array([1, 3, -1, 2, 5, 0], dtype=np.int16),
        "l3_exit": np.array([20220323090312, 20220323090754, -1,
                             20230105090812, 20230105091001, 20230105093000],
                            dtype=np.int64),
    })


def _v2_frame() -> pd.DataFrame:
    """정상 v2 배치 — v1 6행 + 신규 4컬럼 상수(불변 원칙: assign으로 새 프레임)."""
    return _v1_frame().assign(
        onset_type="surge", exit_label="L3_RR8_12",
        source_seal=_SEAL, audit_tag="RR8_12-conditional")


@pytest.fixture()
def v1_parquet(tmp_path) -> Path:
    p = tmp_path / "onset_l3_bank_fixture.parquet"
    _v1_frame().to_parquet(p, index=False)
    return p


# ── BANK_V2_SCHEMA 구성 ──────────────────────────────────────────────────────
def test_v2_schema_preserves_v1_and_adds_four_required_columns():
    assert list(obv.BANK_V2_SCHEMA)[:12] == list(obv.BANK_V1_SCHEMA)
    assert list(obv.BANK_V2_SCHEMA)[12:] == [
        "onset_type", "exit_label", "source_seal", "audit_tag"]
    assert len(obv.BANK_V2_SCHEMA) == 16
    assert all(obv.BANK_V2_NEW_COLUMNS[c] == "string"
               for c in obv.BANK_V2_NEW_COLUMNS)
    assert obv.ONSET_TYPES == ("surge", "breakout", "d9_transition")


def test_schema_constants_are_read_only():
    with pytest.raises(TypeError):
        obv.BANK_V2_SCHEMA["hack"] = "string"  # type: ignore[index]
    with pytest.raises(TypeError):
        obv.MIN_OVERLAY_SCHEMA["hack"] = "string"  # type: ignore[index]


def test_min_overlay_stub_requires_join_keys_and_audit_grade_tag():
    for col in ("code", "day", "t0"):  # 은행 v2 조인 키와 dtype 일치
        assert obv.MIN_OVERLAY_SCHEMA[col] == obv.BANK_V2_SCHEMA[col]
    assert obv.MIN_OVERLAY_SCHEMA["audit_tag"] == "string"
    assert obv.MIN_OVERLAY_SCHEMA["source_seal"] == "string"
    assert obv.MIN_OVERLAY_REQUIRED_AUDIT_TAG == "audit-grade"
    assert "audit-grade" in obv.KNOWN_AUDIT_TAGS


# ── migrate_v1_to_v2: dry_run ────────────────────────────────────────────────
def test_migrate_dry_run_receipt_without_creating_file(tmp_path, v1_parquet):
    dst = tmp_path / "onset_exit_bank_v2.parquet"
    receipt = obv.migrate_v1_to_v2(v1_parquet, dst, source_seal=_SEAL)
    assert receipt["mode"] == "dry_run"
    assert receipt["n_rows_src"] == 6
    assert receipt["n_columns_src"] == 12
    assert receipt["v1_schema_ok"] is True
    assert receipt["order_match"] is True
    assert receipt["created"] is False
    assert receipt["v2_columns"] == list(obv.BANK_V2_SCHEMA)
    assert receipt["new_column_values"]["onset_type"] == "surge"
    assert receipt["new_column_values"]["exit_label"] == "L3_RR8_12"
    assert not dst.exists()  # dry_run 은 어떤 파일도 만들지 않는다


def test_migrate_dry_run_detects_missing_and_mismatched_columns(tmp_path):
    broken = _v1_frame().drop(columns=["l3_exit"]).astype({"day": np.int64})
    src = tmp_path / "broken_v1.parquet"
    broken.to_parquet(src, index=False)
    receipt = obv.migrate_v1_to_v2(src, tmp_path / "out.parquet",
                                   source_seal=_SEAL)
    assert receipt["v1_schema_ok"] is False
    diff = receipt["schema_diff"]
    assert diff["missing"] == ["l3_exit"]
    assert {"column": "day", "expected": "int32", "actual": "int64"} \
        in diff["dtype_mismatch"]


def test_migrate_rejects_invalid_lineage_values(tmp_path, v1_parquet):
    dst = tmp_path / "out.parquet"
    with pytest.raises(ValueError):  # 닫힌 집합 밖 온셋 유형
        obv.migrate_v1_to_v2(v1_parquet, dst, source_seal=_SEAL,
                             onset_type="gap")
    with pytest.raises(ValueError):  # 봉인 문서 파일명 공백 금지
        obv.migrate_v1_to_v2(v1_parquet, dst, source_seal="   ")
    with pytest.raises(TypeError):  # source_seal 은 필수 키워드
        obv.migrate_v1_to_v2(v1_parquet, dst)  # type: ignore[call-arg]
    with pytest.raises(FileNotFoundError):
        obv.migrate_v1_to_v2(tmp_path / "없음.parquet", dst, source_seal=_SEAL)


# ── migrate_v1_to_v2: 실행 경로(소형 픽스처 한정 — 실물 은행 금지) ───────────
def test_migrate_wet_adds_columns_and_keeps_v1_values(tmp_path, v1_parquet):
    dst = tmp_path / "bank_v2.parquet"
    receipt = obv.migrate_v1_to_v2(v1_parquet, dst, source_seal=_SEAL,
                                   dry_run=False)
    assert receipt["created"] is True and receipt["n_rows_written"] == 6
    out = pd.read_parquet(dst)
    assert list(out.columns) == list(obv.BANK_V2_SCHEMA)
    pd.testing.assert_frame_equal(  # 기존 12컬럼 값·dtype 완전 불변
        out[list(obv.BANK_V1_SCHEMA)], pd.read_parquet(v1_parquet))
    assert (out["onset_type"] == "surge").all()
    assert (out["exit_label"] == "L3_RR8_12").all()
    assert (out["source_seal"] == _SEAL).all()
    assert (out["audit_tag"] == "RR8_12-conditional").all()
    with pytest.raises(FileExistsError):  # 덮어쓰기 거부
        obv.migrate_v1_to_v2(v1_parquet, dst, source_seal=_SEAL, dry_run=False)


def test_migrate_wet_refuses_on_schema_mismatch(tmp_path):
    src = tmp_path / "broken.parquet"
    _v1_frame().drop(columns=["l3_net"]).to_parquet(src, index=False)
    with pytest.raises(ValueError):
        obv.migrate_v1_to_v2(src, tmp_path / "out.parquet",
                             source_seal=_SEAL, dry_run=False)
    assert not (tmp_path / "out.parquet").exists()


# ── append_contract ──────────────────────────────────────────────────────────
def test_append_contract_pass_on_clean_batch():
    res = obv.append_contract(_v2_frame(), "surge", 20220323, 20231231)
    assert res["ok"] is True and res["violations"] == []
    assert res["n_rows"] == 6 and res["window"] == [20220323, 20231231]
    assert all(res["checks"].values())


def test_append_contract_detects_wrong_onset_type():
    df = _v2_frame()
    df = df.assign(onset_type=["surge"] * 5 + ["breakout"])
    res = obv.append_contract(df, "surge", 20220323, 20231231)
    assert res["ok"] is False
    v = [x for x in res["violations"] if x["kind"] == "onset_type_mismatch"]
    assert v and v[0]["n_bad"] == 1 and v[0]["observed"] == ["breakout"]
    with pytest.raises(ValueError):  # 기대 유형 자체가 집합 밖이면 호출 오류
        obv.append_contract(df, "gap", 20220323, 20231231)


def test_append_contract_detects_window_breach():
    res = obv.append_contract(_v2_frame(), "surge", 20220323, 20221231)
    v = [x for x in res["violations"] if x["kind"] == "day_out_of_range"]
    assert res["ok"] is False and v[0]["n_bad"] == 3  # 2023년 3행 이탈
    assert res["checks"]["window"] is False
    with pytest.raises(ValueError):  # 창 역전은 호출 오류
        obv.append_contract(_v2_frame(), "surge", 20231231, 20220323)


def test_append_contract_detects_duplicate_keys_in_batch():
    df = _v2_frame()
    dup = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    res = obv.append_contract(dup, "surge", 20220323, 20231231)
    v = [x for x in res["violations"] if x["kind"] == "duplicate_in_batch"]
    assert res["ok"] is False and v[0]["n_bad"] == 2
    assert v[0]["keys"] == [(20220323, "005930", 20220323090012)]


def test_append_contract_detects_collision_with_existing_bank():
    df = _v2_frame()
    existing = df[["day", "code", "t0"]].iloc[:2]  # 기존 은행에 이미 있는 2키
    res = obv.append_contract(df, "surge", 20220323, 20231231,
                              existing_keys=existing)
    v = [x for x in res["violations"] if x["kind"] == "collision_with_bank"]
    assert res["ok"] is False and v[0]["n_bad"] == 2
    tuple_keys = {(20220323, "005930", 20220323090012),
                  (20220323, "005930", 20220323090124)}
    assert set(map(tuple, v[0]["keys"])) == tuple_keys


def test_append_contract_detects_schema_gaps_and_empty_seal():
    missing = _v2_frame().drop(columns=["audit_tag"])
    res = obv.append_contract(missing, "surge", 20220323, 20231231)
    kinds = {x["kind"] for x in res["violations"]}
    assert res["ok"] is False and "missing_column" in kinds

    extra = _v2_frame().assign(bit_1=True)  # 절 비트는 별도 파일 — 은행 오염 금지
    res2 = obv.append_contract(extra, "surge", 20220323, 20231231)
    assert any(x["kind"] == "unexpected_column" for x in res2["violations"])

    blank = _v2_frame().assign(source_seal=[_SEAL] * 5 + [""])
    res3 = obv.append_contract(blank, "surge", 20220323, 20231231)
    v = [x for x in res3["violations"] if x["kind"] == "empty_required"]
    assert v and v[0]["column"] == "source_seal" and v[0]["n_bad"] == 1

    empty = _v2_frame().iloc[0:0]
    res4 = obv.append_contract(empty, "surge", 20220323, 20231231)
    assert any(x["kind"] == "empty_batch" for x in res4["violations"])


# ── 실물 v1 은행 스키마 대조(존재 시 — 스키마만 판독, 전량 로드 없음) ────────
@pytest.mark.skipif(not REAL_BANK.is_file(), reason="실물 은행 부재(git 제외 자산)")
def test_real_bank_schema_matches_sealed_v1_schema():
    actual = obv.read_parquet_schema_map(REAL_BANK)
    assert actual == dict(obv.BANK_V1_SCHEMA)
    assert list(actual) == list(obv.BANK_V1_SCHEMA)  # 순서까지 일치
