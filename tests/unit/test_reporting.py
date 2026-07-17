"""탭형 연구 리포트 빌더 단위 테스트 — 실 데이터 통합 + 픽스처(부재 graceful).

검증: 탭 5개 섹션 존재·조건식 sha·핵심 수치 렌더·HTML 이스케이프·B1 마킹·파일 부재 graceful·
레지스트리 11개 연구·판정 집계.
"""
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import re  # noqa: E402

from alpha_lab.reporting import loaders, registry  # noqa: E402
from alpha_lab.reporting.build_html import build, build_all, build_detail  # noqa: E402
from alpha_lab.reporting.util import escape, highlight_code  # noqa: E402


# --------------------------------------------------------------------------
# 1. util — 이스케이프·하이라이터.
# --------------------------------------------------------------------------

def test_escape():
    assert escape("1000 < 현재가 <= 50000") == "1000 &lt; 현재가 &lt;= 50000"
    assert "&amp;" == escape("&")


def test_highlight_escapes_and_marks_b1():
    code = ("if not (현재가 < 100):\n    매수 = False\n"
            "elif 보유시간 >= 120 and 최고수익률 < 1.0 and 수익률 < 0.0:\n"
            "    # D5R_B1_저활력절단\n    매도 = True")
    out = highlight_code(code)
    assert "&lt;" in out and "<" not in out.replace('<span', '').replace('</span', '').replace('<mark', '').replace('</mark', '')
    assert '<span class="k">if</span>' in out
    assert '<span class="k">elif</span>' in out
    assert "<mark>" in out and out.count("<mark>") == 3   # B1 절 3줄 마킹.


# --------------------------------------------------------------------------
# 2. registry.
# --------------------------------------------------------------------------

def test_registry_13_studies():
    assert len(registry.STUDIES) == 13
    ids = [s.id for s in registry.STUDIES]
    assert len(set(ids)) == 13
    vc = registry.verdict_counts()
    # 양성 3(D1·2절·매도식D1) + 실전이관 1(B1) = 성과 4 · 미결 1(B-트랙) · 기각7+종결1 = 오답 8축.
    assert vc["양성"] == 3 and vc["실전이관"] == 1 and vc["미결"] == 1
    assert vc["양성"] + vc["실전이관"] == 4
    assert vc["기각"] + vc["종결"] == 8
    assert sum(vc.values()) == 13


def test_every_study_has_extractor():
    for s in registry.STUDIES:
        assert s.extractor in loaders.EXTRACTORS


# --------------------------------------------------------------------------
# 3. 실 데이터 통합 빌드.
# --------------------------------------------------------------------------

def test_build_hub_5_tabs():
    h = build(commit="test")
    assert h.strip().startswith("<!doctype html>")
    assert h.count('class="tabpanel') == 5 and h.count('class="tabbtn') == 5
    for tid in ("overview", "studies", "reports", "conditions", "ledger"):
        assert f'id="tab-{tid}"' in h
    assert "prefers-color-scheme:dark" in h            # 다크 토큰 이중 정의.
    assert 'body.js .tabpanel' in h                    # JS 폴백 규칙.


def test_build_conditions_sha_and_escape():
    h = build()
    assert "348c5181" in h                             # 매수 sha 접두.
    assert "&lt;" in h                                 # 조건식 이스케이프.
    assert "<mark>" in h                               # B1 절 마킹.


def test_build_13_study_cards():
    h = build()
    assert h.count('<div class="studycard">') == 13


def test_build_key_numbers_from_json():
    h = build()
    # 판정 json 에서 로드된 대표 수치.
    assert "158" in h                                  # O-4 후보 158.
    assert "n=114" in h                                # B-트랙 anchor.
    led = loaders.load_ledger()                        # 원장 합계 — 살아있는 값 대조.
    assert led.get("total") is None or str(led["total"]) in h


def test_build_no_missing_with_real_data():
    for s in registry.STUDIES:
        assert "_missing" not in loaders.extract_study(s.extractor), s.id


# --------------------------------------------------------------------------
# 4. 파일 부재 graceful.
# --------------------------------------------------------------------------

def test_graceful_missing(monkeypatch):
    monkeypatch.setattr(loaders, "load_json", lambda *a: None)
    # 추출기 전부 _missing 이어도 빌드 크래시 금지.
    h = build(commit="test")
    assert "<!doctype html>" in h
    assert "증거 파일 없음" in h
    assert h.count('class="tabpanel') == 5


def test_missing_extractor_key():
    assert "_missing" in loaders.extract_study("nonexistent_key")


# --------------------------------------------------------------------------
# 5. 계층형 — 허브 + 상세 11 + 링크 무결성.
# --------------------------------------------------------------------------

def test_build_all_hub_plus_details():
    files = build_all(commit="test")
    assert "research_lab_report.html" in files
    assert len(files) == 1 + len(registry.STUDIES) == 14
    for s in registry.STUDIES:
        assert f"research/{s.id}.html" in files


def test_hub_detail_link_integrity():
    files = build_all(commit="test")
    hub = files["research_lab_report.html"]
    links = set(re.findall(r'href="(research/\w+\.html)"', hub))
    assert links, "허브에 상세 링크 없음"
    for l in links:
        assert l in files, f"깨진 링크: {l}"        # 링크 대상 파일 전부 생성됨.
    assert "2026-07-16_b1_program_report.html" in hub   # 결산 v1 링크.


def test_detail_6_tabs_and_backlink():
    for s in registry.STUDIES:
        d = build_detail(s, commit="test")
        assert d.strip().startswith("<!doctype html>")
        assert d.count('class="tabpanel') == 6 and d.count('class="tabbtn') == 6
        for tid in ("overview", "method", "results", "fulltable", "verdict", "evidence"):
            assert f'id="tab-{tid}"' in d, (s.id, tid)
        assert "../research_lab_report.html" in d       # ← 허브로 상대 링크.


def test_detail_graceful_missing(monkeypatch):
    monkeypatch.setattr(loaders, "load_json", lambda *a: None)
    d = build_detail(registry.STUDIES[0], commit="test")
    assert d.count('class="tabpanel') == 6            # 데이터 없어도 6탭 유지.
    assert "증거" in d                                  # 증거 미수록/증거·재현 표기.
