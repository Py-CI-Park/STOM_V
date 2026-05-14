# V3U Test Automation Guide

- 작성일: 2026-05-12
- 대상 lane: `STOM_Version_3U`
- 시스템 도입 사이클: Phase 1~6 (`1c794774` ~ `096cc1a7` + 본 커밋)
- 선행 문서: `docs/V3U_PYD_REMOVAL_PLAN.md` §11

본 가이드는 V3U lane의 자동 GUI 검증 시스템을 운영·확장하는 작업자를 위한 운영 매뉴얼이다.

## 1. 시스템 개요

### 1.1 목적

매 V3 정규 업데이트(V3.19, V3.20...) 흡수 시 사용자가 GUI를 직접 띄워 시각 검증하는 부담(약 30분)을 자동화로 대체하고, V3 official source 0줄 수정 invariant를 자동 게이트로 보장한다.

### 1.2 구성 요소

```
tests/v3u/
├── conftest.py                          픽스처 (qapp/main_window/dict_findex/synthetic_ohlcv)
├── fixtures/
│   ├── synthetic_ohlcv.py               결정적 분봉/틱 생성기
│   ├── dict_findex_v318.json            V3.18 키 스냅샷
│   └── mock_exchange.py                 거래소 mock 응답
├── test_smoke.py                        1순위 (5 케이스)
├── test_widgets.py                      위젯/시그널/아이콘 (3 케이스)
├── test_lifecycle.py                    백테/분석기 (5 케이스)
├── test_data_layer.py                   잔고/거래소/DB (6 케이스)
├── test_units.py                        분석기/유틸 단위 (5 케이스)
├── test_rest_api_contract.py            REST 정적 + mock (7 케이스)
└── README.md                            상세 사용법

scripts/verify_v3u_pyd_gui_contract.py   통합 게이트 (정적+구조+동적)
requirements-dev.txt                     pytest, pytest-qt, pytest-timeout, pytest-mock
pytest.ini                               testpaths=tests/v3u, qt_api=pyqt5, timeout=60
```

총 31 자동 케이스 + 통합 verifier = V3U lane의 단일 검증 게이트.

## 2. 일상 사용

### 2.1 새 워크트리 또는 머신에서 처음 한 번

```powershell
python -m pip install -r requirements-dev.txt
```

### 2.2 V3 정규 업데이트 흡수 시

```powershell
# 1. V3 흡수
git checkout STOM_Version_3U
git merge STOM_Version_3

# 2. 통합 게이트
python scripts/verify_v3u_pyd_gui_contract.py `
    --branch STOM_Version_3U --version V3.19 `
    --upstream-ref STOM_Version_3 `
    --manifest .omx/logs/v3u/verify_v3_19_$(Get-Date -Format yyyyMMdd).json

# 3. PASS 메시지 확인:
#    [INFO] pytest gate: passed (31 passed, ...)
#    [OK] V3U pyd GUI contract + pytest gate passed
```

### 2.3 빠른 정적 검증만 (CI 외)

```powershell
python scripts/verify_v3u_pyd_gui_contract.py ... --skip-pytest
```

### 2.4 묶음별 실행

```powershell
python -m pytest tests/v3u/ -m smoke -v          # 1순위 (5 케이스, ~20초)
python -m pytest tests/v3u/ -m integration -v    # 2·3순위 (14 케이스, ~20초)
python -m pytest tests/v3u/ -m unit -v           # 단위 (5 케이스, ~5초)
python -m pytest tests/v3u/ -m contract -v       # REST mock (7 케이스, ~5초)
```

### 2.5 단일 케이스 디버그

```powershell
python -m pytest tests/v3u/test_smoke.py::test_main_window_starts -v -s
```

## 3. 신규 테스트 추가

### 3.1 위치 결정

| 검증 대상 | 추가할 파일 | marker |
|---|---|---|
| 메인창/탭/아이콘 첫 인스턴스화 | `test_smoke.py` | `@pytest.mark.smoke` |
| 위젯 시그널/슬롯 | `test_widgets.py` | `@pytest.mark.integration` |
| 백테 spawn/분석기/엔진 | `test_lifecycle.py` | `@pytest.mark.integration` |
| 잔고/거래소/DB | `test_data_layer.py` | `@pytest.mark.integration` |
| 분석기/설정 단위 | `test_units.py` | `@pytest.mark.unit` |
| REST API 정적/mock | `test_rest_api_contract.py` | `@pytest.mark.contract` |

### 3.2 픽스처 활용

| 픽스처 | scope | 용도 |
|---|---|---|
| `qapp` | session | QApplication + AA_ShareOpenGLContexts 사전 설정 |
| `main_window` | function | V3U pyd-free MainWindow 인스턴스 |
| `factor_lists` | session | LIST_STOCK_TICK/MIN 라이브 import |
| `dict_findex_min` | function | 분봉 dict_findex (round-trip 키 포함) |
| `dict_findex_tick` | function | 틱 dict_findex |
| `dict_findex_snapshot` | session | V3.18 시점 스냅샷 (drift 감지용) |
| `synthetic_ohlcv` | function | 결정적 OHLCV 생성기 |
| `project_root` | session | 워크트리 루트 Path |

### 3.3 새 케이스 작성 패턴

```python
import pytest

pytestmark = pytest.mark.integration

def test_새_검증(main_window, dict_findex_min, synthetic_ohlcv) -> None:
    """짧은 한글 docstring으로 검증 의도 명시."""
    arr = synthetic_ohlcv["min"](dict_findex_min, n=200)
    # ... 검증 로직 ...
    assert ...
```

### 3.4 한글 커밋 규칙

CLAUDE.md "Commit Language Rules"에 따라 모든 커밋 제목·본문은 한글이며, 의도 중심 제목을 사용한다.

```
V3U <검증 영역> 자동 케이스를 추가한다

## 추가
- test_<file>.py::test_<func>: <검증 내용>

## Tested
- python -m pytest tests/v3u/test_<file>.py -v: N passed
```

## 4. 통합 게이트 출력 해석

### 4.1 PASS 예시

```
[INFO] V3U contract manifest: ...verify_v3_19.json
[INFO] pytest gate: passed (31 passed, 3 warnings in 20.58s)
[OK] V3U pyd GUI contract + pytest gate passed
```

### 4.2 FAIL 예시 (drift 감지)

```
[INFO] V3U contract manifest: ...verify_v3_19.json
[INFO] pytest gate: failed (log: .omx/logs/v3u/pytest_summary.txt)
[FAIL] pytest gate failed (exit=1): FAILED tests/v3u/test_smoke.py::test_backtest_proc_attrs_initialized
```

이 경우 `pytest_summary.txt`를 열어 정확한 위치를 확인하고 `ui/main_window.py` 또는 `tests/v3u/`에서만 수정한다. **V3 official source는 절대 수정하지 않는다.**

### 4.3 환경 문제

```
[FAIL] pytest 미설치. requirements-dev.txt 설치 필요: python -m pip install -r requirements-dev.txt
```

→ `python -m pip install -r requirements-dev.txt` 실행 후 재시도.

## 5. 자동화 한계 (사용자 영역 영구 보존)

본 시스템은 다음을 자동화하지 않는다 — 본질적 자동화 불가이며 release 전 사용자 직접 검증이 필수다.

| 항목 | 자동화 불가 사유 | 사용자 검증 방법 |
|---|---|---|
| C1 LS증권 모의투자 주문/체결/잔고 | 자격증명·영업시간 | 실 모의투자 계좌로 주문 라이프사이클 |
| C2 바이낸스 테스트넷 주문 | API key | 테스트넷 계정으로 주문/체결 |
| C3 업비트 실 최소금액 매수/매도 | 실 자금 위험 | 사용자 본인이 신중히 |
| C4 base_strategy 1시간 무인 운영 | 실시간 시장 race condition | 모의투자 1시간 무인 |
| B3 LS 웹소켓 체결/호가 분리 라이브 | 라이브 시장 | LS 로그인 후 두 채널 별도 수신 로그 |
| D1 사용자 실 DB 마이그레이션 | 사용자 환경 고유 | 백업 DB로 V3U 기동 |
| F1 STOM_Version_3U_C 생성 시점 | 정책 판단 | 1·2순위 통과 후 사용자 결정 |
| 시각 미적 판단 | UX는 사람만 | 직접 띄워 확인 |

## 6. drift 감지 사례 (Phase 1~6 도입 시 발견)

본 시스템 도입 과정에서 audit doc과 실 코드 간 불일치 2건이 자동 감지됐다.

### 6.1 백테 프로세스 핸들 카운트

- `2026-05-07` 핸드오프 체크리스트 추측: 22개
- 실측: 26개 (Phase 2 `test_backtest_proc_attrs_initialized` 발견)
- 처리: baseline을 26으로 갱신하고 drift 시 명시적 skip 신호 부여

### 6.2 잔고 dt-guard 카운트

- `2026-05-12` 확장 자동 감사 보고: 3곳 (line 237, 315, 503)
- 실측: 2곳 (line 237, 315). line 504는 dt-guard 없는 unconditional push
- 처리: baseline을 2로 갱신, 보고서 §4.7 정정 (Phase 6.2 도입 감사에 기록)

이 두 사례는 본 자동 검증 시스템이 audit doc 부정확함을 자동 검출함을 증명한다.

## 7. 확장 로드맵 (별도 ralplan으로 분리)

| 옵션 | 내용 |
|---|---|
| 옵션 D | 스크린샷 회귀 (시각 깨짐 자동 감지, Pillow + imagehash) |
| 옵션 E | Claude 자동 시나리오 생성기 (`ui/event_click/` 자동 분석) |
| CI 통합 | GitHub Actions 또는 pre-commit hook |
| V2.79 lane 동일 패턴 | V2.79 wave 종료 후 검토 |

## 8. 관련 문서

- `.omc/plans/2026-05-12_v3u_test_automation_and_governance.md` 본 시스템 컨센서스 플랜
- `docs/V3U_PYD_REMOVAL_PLAN.md` §11 자동 검증 시스템 extension
- `docs/WORKTREE_STRATEGY.md` V3 Lane Branch Parity Invariants
- `docs/UPSTREAM_SYNC_STRATEGY.md` V3 Wave Source Of Truth + V3 Ingress Policy
- `docs/CARRY_FORWARD_REGISTRY.md` V3U custom allowlist rule
- `CLAUDE.md` V3U Test Automation Gate
- `tests/v3u/README.md` 운영자 빠른 참조
- `docs/update_log/2026-05-06_v3u_final_parity_audit.md` 최종 parity 감사
- `docs/update_log/2026-05-07_v3u_handoff_verification_checklist.md` 사용자 잔여 작업 25개
- `docs/update_log/2026-05-12_v3u_extended_automation_audit.md` 확장 자동 감사
- `docs/update_log/2026-05-12_v3u_test_automation_setup.md` 본 시스템 도입 감사
