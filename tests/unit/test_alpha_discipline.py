"""alpha_lab.discipline 단위 테스트 (WBS v3 P1-1·P1-5 — A1/A21/A6/A4).

실행: python -m pytest tests/unit/test_alpha_discipline.py -q
실DB 불필요 — 합성 픽스처(tmp_path) 중심. 실물 원장/코퍼스 테스트는
존재할 때만(skipif) 읽기 전용으로 수행한다.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from alpha_lab.discipline import ledger, lint, prereg, trials_report, windows

ROOT = Path(__file__).resolve().parents[2]
REAL_LEDGER = (
    ROOT
    / "docs"
    / "research"
    / "condition_research"
    / "research_runs"
    / "alpha_restart_20260710"
    / "n_trials_ledger.jsonl"
)
REAL_RUNS_DIR = REAL_LEDGER.parent

VALID_ROW = {
    "ts": "2026-07-12T23:00:00",
    "series": "D1",
    "window": "2022-03-23~2023-12-31(발견창)",
    "trial_type": "b(오프라인 봉인 판정)",
    "target": "테스트 대상 요약",
    "result": "테스트 결과 요약",
    "session": "unit-test",
}


def _row(**overrides) -> dict:
    return {**VALID_ROW, **overrides}


# ---------------------------------------------------------------------------
# windows — 창-지위 가드
# ---------------------------------------------------------------------------


class TestWindowsGuard:
    def test_discovery_window_passes(self):
        status = windows.assert_measurement_window(
            "2022-03-23", "2023-12-31", "S-트랙 지도"
        )
        assert status == "DISCOVERY"

    def test_known_overlap_rejected_with_ledger_quote(self):
        with pytest.raises(windows.WindowViolation) as excinfo:
            windows.assert_measurement_window("2024-06-01", "2025-03-01", "S-트랙 지도")
        message = str(excinfo.value)
        assert "선택·튜닝 금지" in message  # 원장 §1 known 행 인용
        assert "veto 전용" in message

    def test_full_known_window_rejected(self):
        with pytest.raises(windows.WindowViolation):
            windows.assert_measurement_window("2025-01-01", "2026-02-27", "신규 가설")

    def test_absent_window_rejected(self):
        with pytest.raises(windows.WindowViolation) as excinfo:
            windows.assert_measurement_window("2026-03-01", "2026-06-01", "신규 가설")
        assert "데이터 없음, 수집하지 않음" in str(excinfo.value)

    def test_pre_data_rejected(self):
        with pytest.raises(windows.WindowViolation):
            windows.assert_measurement_window("2021-01-01", "2022-06-01", "신규 가설")

    def test_2024_known_for_exit_lever_series(self):
        with pytest.raises(windows.WindowViolation) as excinfo:
            windows.assert_measurement_window(
                "2024-01-01", "2024-12-31", "청산 레버(P5·D5 계열)"
            )
        assert "청산 레버·챔피언 선정 계열 가설에는 known" in str(excinfo.value)

    def test_2024_known_for_champion_series(self):
        with pytest.raises(windows.WindowViolation):
            windows.assert_measurement_window(
                "2024-03-01", "2024-04-01", "챔피언 선정·앙상블(v4 계열)"
            )

    def test_2024_conditional_requires_prereg(self):
        with pytest.raises(windows.WindowViolation) as excinfo:
            windows.assert_measurement_window("2024-01-01", "2024-06-30", "신규 스냅샷 가설")
        assert "사전등록 필수" in str(excinfo.value)

    def test_2024_conditional_passes_with_prereg(self):
        status = windows.assert_measurement_window(
            "2024-01-01",
            "2024-06-30",
            "신규 스냅샷 가설",
            conditional_2024_prereg="봉인 문서 plans/2026-07-xx_x.md (커밋 deadbeef)",
        )
        assert status == "CONDITIONAL_2024"

    def test_reversed_range_valueerror(self):
        with pytest.raises(ValueError):
            windows.assert_measurement_window("2023-12-31", "2022-03-23", "신규 가설")

    def test_empty_series_kind_rejected(self):
        with pytest.raises(ValueError):
            windows.assert_measurement_window("2022-04-01", "2022-05-01", "  ")


class TestDateTokens:
    def test_parse_date_formats(self):
        assert windows.parse_date("2025-04-07") == dt.date(2025, 4, 7)
        assert windows.parse_date("20250407") == dt.date(2025, 4, 7)
        assert windows.parse_date(dt.date(2022, 3, 23)) == dt.date(2022, 3, 23)
        with pytest.raises(ValueError):
            windows.parse_date("2025/04/07")

    def test_extract_iso_compact_yearmonth(self):
        tokens = windows.extract_date_tokens("경계 2025-04-07, 표본 20250526, 이후 2025-04")
        kinds = {t["kind"] for t in tokens}
        assert kinds == {"full", "compact", "yearmonth"}
        yearmonth = next(t for t in tokens if t["kind"] == "yearmonth")
        assert yearmonth["start"] == dt.date(2025, 4, 1)
        assert yearmonth["end"] == dt.date(2025, 4, 30)

    def test_invalid_dates_skipped(self):
        assert windows.extract_date_tokens("20259999 2025-13-01 값 20,250,526원") == []

    def test_iso_not_double_counted_as_yearmonth(self):
        tokens = windows.extract_date_tokens("2025-04-07 하루만")
        assert [t["kind"] for t in tokens] == ["full"]


# ---------------------------------------------------------------------------
# ledger — 단일 기입 API
# ---------------------------------------------------------------------------


class TestAppendTrial:
    def test_append_success_and_line_format(self, tmp_path):
        path = tmp_path / "ledger.jsonl"
        record = ledger.append_trial(path=path, **VALID_ROW)
        assert record == VALID_ROW
        line = path.read_text(encoding="utf-8").splitlines()[0]
        parsed = json.loads(line)
        assert list(parsed.keys()) == list(ledger.REQUIRED_KEYS)  # 키 순서 계약
        assert json.dumps(parsed, ensure_ascii=False) == line  # 왕복 byte 동일

    @pytest.mark.parametrize("key", list(ledger.REQUIRED_KEYS))
    def test_empty_required_key_rejected(self, tmp_path, key):
        with pytest.raises(ledger.LedgerSchemaError):
            ledger.append_trial(path=tmp_path / "l.jsonl", **_row(**{key: "  "}))

    def test_bad_ts_rejected(self, tmp_path):
        with pytest.raises(ledger.LedgerSchemaError):
            ledger.append_trial(path=tmp_path / "l.jsonl", **_row(ts="어제쯤"))

    def test_trial_type_d_rejected(self, tmp_path):
        with pytest.raises(ledger.LedgerSchemaError) as excinfo:
            ledger.append_trial(
                path=tmp_path / "l.jsonl", **_row(trial_type="d(신규 유형)")
            )
        assert "규약 개정" in str(excinfo.value)  # type-d는 원장 §5로만(A6 조건)

    def test_window_without_date_fail_closed(self, tmp_path):
        with pytest.raises(ledger.LedgerSchemaError) as excinfo:
            ledger.append_trial(path=tmp_path / "l.jsonl", **_row(window="발견창 전체"))
        assert "fail-closed" in str(excinfo.value)

    def test_known_window_rejected_without_known_ok(self, tmp_path):
        with pytest.raises(windows.WindowViolation) as excinfo:
            ledger.append_trial(
                path=tmp_path / "l.jsonl",
                **_row(window="2025-01-01~2026-02-27(known/audit)"),
            )
        assert "선택·튜닝 금지" in str(excinfo.value)

    def test_known_window_allowed_with_known_ok(self, tmp_path):
        path = tmp_path / "l.jsonl"
        ledger.append_trial(
            path=path,
            known_ok=True,
            **_row(window="2025-01-01~2026-02-27(known/audit, veto 기록)"),
        )
        assert len(ledger.read_all(path)) == 1

    def test_2024_window_gated_for_exit_series(self, tmp_path):
        row = _row(series="D5-R", window="2024-01-01~2024-12-31(조건부)")
        with pytest.raises(windows.WindowViolation):
            ledger.append_trial(path=tmp_path / "l.jsonl", **row)
        ledger.append_trial(path=tmp_path / "l.jsonl", known_ok=True, **row)

    def test_2024_window_free_for_non_exit_series(self, tmp_path):
        path = tmp_path / "l.jsonl"
        ledger.append_trial(
            path=path, **_row(series="스냅샷-신규", window="2024-01-01~2024-06-30(조건부 검증)")
        )
        assert ledger.aggregate(path)["known_window_contacts"] == 0

    def test_append_preserves_crlf_convention(self, tmp_path):
        path = tmp_path / "l.jsonl"
        first = json.dumps(VALID_ROW, ensure_ascii=False)
        path.write_bytes(first.encode("utf-8") + b"\r\n")
        ledger.append_trial(path=path, **_row(target="둘째 행"))
        data = path.read_bytes()
        assert data.count(b"\r\n") == 2  # 기존 CRLF 관례 유지
        assert len(ledger.read_all(path)) == 2

    def test_append_repairs_missing_trailing_newline(self, tmp_path):
        path = tmp_path / "l.jsonl"
        path.write_bytes(json.dumps(VALID_ROW, ensure_ascii=False).encode("utf-8"))
        ledger.append_trial(path=path, **_row(target="둘째 행"))
        assert len(ledger.read_all(path)) == 2  # 행 붙음 없음


class TestReadAggregate:
    def test_read_all_missing_file_empty(self, tmp_path):
        assert ledger.read_all(tmp_path / "none.jsonl") == []

    def test_read_all_malformed_line_fail_closed(self, tmp_path):
        path = tmp_path / "l.jsonl"
        path.write_text('{"ts": "x"\n', encoding="utf-8")
        with pytest.raises(ledger.LedgerSchemaError) as excinfo:
            ledger.read_all(path)
        assert "1행" in str(excinfo.value)

    def test_read_all_missing_key_fail_closed(self, tmp_path):
        path = tmp_path / "l.jsonl"
        path.write_text('{"ts": "2026-07-12T00:00:00"}\n', encoding="utf-8")
        with pytest.raises(ledger.LedgerSchemaError) as excinfo:
            ledger.read_all(path)
        assert "필수 키 누락" in str(excinfo.value)

    def test_aggregate_counts_and_sqrt(self, tmp_path):
        path = tmp_path / "l.jsonl"
        ledger.append_trial(path=path, **_row(series="D1"))
        ledger.append_trial(path=path, **_row(series="D1", trial_type="a(엔진 확인)"))
        ledger.append_trial(path=path, **_row(series="S-트랙"))
        agg = ledger.aggregate(path)
        assert agg["total"] == 3
        assert agg["by_series"]["D1"]["n"] == 2
        assert agg["by_series"]["S-트랙"]["n"] == 1
        assert agg["by_trial_type"] == {"a": 1, "b": 2}
        assert agg["sqrt_2_ln_total"] == pytest.approx(1.4823, abs=1e-3)
        assert agg["by_series"]["S-트랙"]["sqrt_2_ln_n"] == 0.0

    def test_sqrt_2_ln_edges(self):
        assert ledger.sqrt_2_ln(0) == 0.0
        assert ledger.sqrt_2_ln(1) == 0.0
        assert ledger.sqrt_2_ln(53) == pytest.approx(2.8180, abs=1e-3)


@pytest.mark.skipif(not REAL_LEDGER.exists(), reason="실물 원장 부재 환경")
class TestRealLedgerRoundTrip:
    def test_all_existing_rows_roundtrip_byte_identical(self):
        """기존 전체 행 파싱 왕복(필수) — 단일 기입 경로의 스키마 호환 증명."""
        raw_lines = [
            line
            for line in REAL_LEDGER.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        entries = ledger.read_all(REAL_LEDGER)
        assert len(entries) == len(raw_lines)
        assert len(entries) >= 53  # 2026-07-12 시점 실측 하한(append-only)
        for raw, entry in zip(raw_lines, entries):
            assert ledger._serialize(entry) == raw

    def test_real_aggregate_series_present(self):
        agg = ledger.aggregate(REAL_LEDGER)
        assert agg["total"] >= 53
        assert "D1" in agg["by_series"]
        assert agg["window_unparsed"] == 0


# ---------------------------------------------------------------------------
# prereg — 스켈레톤 생성기
# ---------------------------------------------------------------------------


class TestPrereg:
    REQUIRED_HEADINGS = (
        "## 0. 결론 먼저",
        "## 2. 가설",
        "## 3. 모집단·대상 봉인",
        "## 5. 표본·라벨 — 표본 하한",
        "## 7. 판정 기준",
        "## 10. Kill 기준",
        "## 11. 엔진 예산 · n_trials",
        "## 13. 미결 결정",
    )

    def test_skeleton_contains_required_sections(self):
        text = prereg.build_skeleton(title="테스트 검정", series_kind="신규 스냅샷 가설")
        for heading in self.REQUIRED_HEADINGS:
            assert heading in text
        assert "BH-FDR" in text and "부트스트랩" in text  # 보정 명시
        assert "+0.10%p" in text  # 효과크기 하한 기본값
        assert "0회" in text  # 엔진 예산 기본값
        assert "1,100+" in text  # 구 프로그램 누계 병기 규약

    def test_skeleton_quotes_window_ledger(self):
        text = prereg.build_skeleton(title="테스트 검정", series_kind="신규 스냅샷 가설")
        assert windows.LEDGER_DOC_PATH in text
        assert "선택·튜닝 금지" in text

    def test_known_window_skeleton_rejected(self):
        with pytest.raises(windows.WindowViolation):
            prereg.build_skeleton(
                title="위반 시도",
                series_kind="신규 가설",
                window_start="2025-01-01",
                window_end="2025-12-31",
            )

    def test_conditional_2024_requires_flag(self):
        with pytest.raises(windows.WindowViolation):
            prereg.build_skeleton(
                title="조건부 시도",
                series_kind="신규 가설",
                window_start="2024-01-01",
                window_end="2024-06-30",
            )
        text = prereg.build_skeleton(
            title="조건부 시도",
            series_kind="신규 가설",
            window_start="2024-01-01",
            window_end="2024-06-30",
            conditional_2024=True,
        )
        assert "CONDITIONAL_2024" in text

    def test_write_skeleton_refuses_overwrite(self, tmp_path):
        target = tmp_path / "prereg.md"
        prereg.write_skeleton(target, title="테스트", series_kind="신규 가설")
        with pytest.raises(FileExistsError):
            prereg.write_skeleton(target, title="테스트", series_kind="신규 가설")


# ---------------------------------------------------------------------------
# trials_report — 시행 병기 블록 (소비 전용)
# ---------------------------------------------------------------------------


class TestTrialsReport:
    def _make_ledger(self, tmp_path) -> Path:
        path = tmp_path / "l.jsonl"
        for i in range(3):
            ledger.append_trial(path=path, **_row(series="D1", target=f"절 #{i}"))
        ledger.append_trial(path=path, **_row(series="S-트랙"))
        return path

    def test_block_contents(self, tmp_path):
        path = self._make_ledger(tmp_path)
        block = trials_report.build_trials_block(
            family_label="D1 절-단위 A/B(자격 절)",
            family_denominator=34,
            series="D1",
            path=path,
            generated_ts="2026-07-12T23:59:00",
        )
        assert "| 족 분모(FDR) | 34 |" in block
        assert "| 계열(D1) 누계 | 3" in block
        assert "| 전역 누계(본 프로그램) | 4" in block
        assert "√(2·ln N)" in block
        assert "1,100+" in block  # 구 프로그램 누계 병기
        assert "기입하지 않는다" in block  # 소비 전용 명시

    def test_unknown_series_rejected(self, tmp_path):
        path = self._make_ledger(tmp_path)
        with pytest.raises(ValueError):
            trials_report.build_trials_block(
                family_label="족", family_denominator=1, series="없는계열", path=path
            )

    def test_denominator_validation(self, tmp_path):
        path = self._make_ledger(tmp_path)
        for bad in (0, -1, True, "34"):
            with pytest.raises(ValueError):
                trials_report.build_trials_block(
                    family_label="족", family_denominator=bad, path=path
                )

    def test_module_has_no_write_path(self):
        """A6 채택 조건 — 리포터는 원장 기입 API를 노출·재정의하지 않는다."""
        assert not hasattr(trials_report, "append_trial")


# ---------------------------------------------------------------------------
# lint — known 창 접촉 문서 린터 (보고 전용)
# ---------------------------------------------------------------------------

V1_FIXTURE = "\n".join(
    [
        "# W3 프로파일링 표본일 목록",
        "",
        "**tick 표본일 20일**:",
        "- 2022: 20220517, 20220714",
        "- 2025: 20250507, 20250728, 20250908",
        "",
        "등락율 축 경계 산정은 pooled 20일 표본으로 수행했다.",
    ]
)

CLEAN_FIXTURE = "\n".join(
    [
        "# 발견창 측정 계획",
        "- 측정창: 2022-03-23~2023-12-31 표본 863,446건 적재",
        "- 작성일: 2026-07-12 (문서 날짜 — 데이터 아님)",
        "- 후속 백테 예산은 0회다.",
    ]
)

POLICY_FIXTURE = "\n".join(
    [
        "## 창 지위",
        "| 2025-01-01 ~ 2026-02-27 | known/audit | 선택·튜닝 금지. veto 전용. 적재 시 별도 파티션 |",
    ]
)


class TestLint:
    def test_v1_fixture_redetected(self):
        findings = lint.scan_text(V1_FIXTURE, source="v1_fixture.md")
        flagged = [f for f in findings if any(t.startswith("2025") for t in f["date_tokens"])]
        assert flagged, "V-1형 known 2025 표본일이 재검출돼야 한다"
        assert flagged[0]["zone"] == "KNOWN"
        assert "표본" in flagged[0]["keywords"] or "산정" in flagged[0]["keywords"]
        assert flagged[0]["category"] == "measurement_context"

    def test_proximity_keyword_within_3_lines(self):
        text = "온셋 20250908 목록\n줄1\n줄2\n표본 하한 검토"
        assert lint.scan_text(text)  # 3행 아래 키워드 — 근접 인정
        text_far = "온셋 20250908 목록\n줄1\n줄2\n줄3\n줄4\n표본 하한 검토"
        assert lint.scan_text(text_far) == []  # 4행 밖 — 근접 아님

    def test_clean_discovery_and_doc_dates_not_flagged(self):
        assert lint.scan_text(CLEAN_FIXTURE, source="clean.md") == []

    def test_policy_line_classified_as_policy_context(self):
        findings = lint.scan_text(POLICY_FIXTURE, source="ledger_doc.md")
        assert findings  # 보고는 유지(억제하지 않음)
        assert findings[0]["category"] == "policy_context"

    def test_2024_flagged_only_with_exit_series_context(self):
        neutral = "신규 가설 측정 표본: 2024-05-13 포함"
        assert lint.scan_text(neutral) == []
        exit_ctx = "청산 레버 반사실 측정 표본: 2024-05-13 포함"
        findings = lint.scan_text(exit_ctx)
        assert findings and "CONDITIONAL_2024" in findings[0]["zone"]

    def test_scan_paths_and_render(self, tmp_path):
        (tmp_path / "a.md").write_text(V1_FIXTURE, encoding="utf-8")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "b.md").write_text(CLEAN_FIXTURE, encoding="utf-8")
        result = lint.scan_paths([tmp_path])
        assert result["files_scanned"] == 2
        assert result["summary"]["flagged_lines"] >= 1
        report = lint.render_report(result)
        assert "보고 전용" in report and "a.md" in report

    def test_cli_main_always_exit_zero(self, tmp_path, capsys):
        """A4 채택 조건 — 플래그가 있어도 차단하지 않는다(exit 0)."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "ledger_lint_cli", ROOT / "scripts" / "ledger_lint.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        (tmp_path / "v1.md").write_text(V1_FIXTURE, encoding="utf-8")
        assert module.main([str(tmp_path)]) == 0
        assert "보고 전용" in capsys.readouterr().out


@pytest.mark.skipif(not REAL_RUNS_DIR.exists(), reason="실물 코퍼스 부재 환경")
class TestLintRealCorpus:
    def test_v1_redetected_in_w3_profiling_report(self):
        """합격 기준(A4): 원장 §6 V-1 — W3 known 2025 표본 접촉 재검출."""
        result = lint.scan_paths([REAL_RUNS_DIR])
        w3_hits = [
            f
            for f in result["findings"]
            if Path(f["file"]).name == "w3_profiling_report.md"
            and any(t.startswith("2025") for t in f["date_tokens"])
        ]
        assert w3_hits, "V-1(W3 known 2025 표본일) 재검출 실패"
