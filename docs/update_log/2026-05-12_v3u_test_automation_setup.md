# V3U 자동 검증 시스템 도입 감사 (2026-05-12)

- 작성일: 2026-05-12
- 대상 worktree: `C:/System_Trading/STOM/STOM_V.wt-3u`
- 대상 branch: `STOM_Version_3U`
- 도입 사이클 시작 HEAD: `e01a96bf V3U 확장 자동 검증 감사 증적을 고정한다`
- 컨센서스 플랜: `.omc/plans/2026-05-12_v3u_test_automation_and_governance.md`
- 운영 가이드: `docs/V3U_TEST_AUTOMATION_GUIDE.md`

## 1. 도입 목적

선행 핸드오프 체크리스트(`docs/update_log/2026-05-07_v3u_handoff_verification_checklist.md`)의 사용자 잔여 검증 25개 항목 중 헤드리스(`QT_QPA_PLATFORM=offscreen`) 환경에서 자동화 가능한 영역을 모두 자동 검증으로 전환하여 매 V3 정규 업데이트마다 발생하던 사용자 GUI 시각 검증 부담(약 30분)을 줄이고, V3 official source 0줄 수정 invariant를 자동 게이트로 보강한다.

## 2. 6 Phase 단계적 도입 결과

| Phase | 커밋 | 산출물 |
|---|---|---|
| Phase 1 | `1c794774` | requirements-dev.txt + pytest.ini + tests/v3u/{conftest,fixtures,README} (9 파일, 568 lines) |
| Phase 2 | `96787192` | tests/v3u/test_smoke.py 5 케이스 |
| Phase 3 | `4059ce36` | test_widgets.py + test_lifecycle.py + test_data_layer.py 14 케이스 |
| Phase 4 | `fc1870fe` | test_units.py + test_rest_api_contract.py + fixtures/mock_exchange.py 12 케이스 |
| Phase 5 | `b43fef6e` | scripts/verify_v3u_pyd_gui_contract.py에 pytest 게이트 통합 (76 line 추가) |
| Phase 6.1 | `096cc1a7` | docs/WORKTREE_STRATEGY/UPSTREAM_SYNC_STRATEGY/CARRY_FORWARD_REGISTRY V3 lane 명문화 (117 line 추가) |
| Phase 6.2 | (본 커밋) | docs/V3U_PYD_REMOVAL_PLAN §11 + CLAUDE.md V3U 게이트 + V3U_TEST_AUTOMATION_GUIDE.md + 본 감사 |

## 3. 검증 매트릭스 (전체 회귀 PASS)

```
$ python -m pytest tests/v3u/ -q
... 31 passed, 3 warnings in 20.58s

$ python scripts/verify_v3u_pyd_gui_contract.py \
    --branch STOM_Version_3U --version V3.18 \
    --upstream-ref STOM_Version_3 \
    --manifest .omx/logs/v3u/verify_v3u_pyd_gui_contract_phase5.json
[INFO] pytest gate: passed (31 passed, 3 warnings in 20.58s)
[OK] V3U pyd GUI contract + pytest gate passed
```

| 영역 | 케이스 | 결과 |
|---|---|---|
| smoke (1순위) | 5 | PASS |
| integration widgets/lifecycle/data_layer (2·3순위) | 14 | PASS |
| unit (분석기·설정) | 5 | PASS |
| contract (REST 정적 + mock) | 7 | PASS |
| **합계** | **31** | **PASS** |
| 통합 verifier | 정적+구조+동적 5단계 | PASS |

## 4. drift 감지 사례 (자동 검증 시스템의 가치 증명)

본 도입 과정에서 audit doc과 실 코드 간 불일치 2건이 자동 검출됐다.

### 4.1 백테 프로세스 핸들 카운트

- 2026-05-07 핸드오프 체크리스트 추측: 22개
- 실측: 26개
- 검출: Phase 2 `test_backtest_proc_attrs_initialized`
- 처리: baseline 22 → 26 갱신 + drift 시 명시적 skip 신호

### 4.2 잔고 dt-guard 카운트

- 2026-05-12 확장 자동 감사 보고: 3곳 (line 237, 315, 503)
- 실측: 2곳 (line 237, 315). line 504는 dt-guard 없는 unconditional push
- 검출: Phase 3 `test_b5_balance_dt_guard_pattern_in_source`
- 처리: baseline 3 → 2 갱신

두 사례 모두 자동 검증이 prior audit의 부정확함을 정확한 위치와 함께 즉시 검출한 사례다.

## 5. 거버넌스 갱신 4건 (Phase 6.1·6.2)

| 문서 | 추가 섹션 |
|---|---|
| docs/WORKTREE_STRATEGY.md | V3 Lane Branch Parity Invariants + V3 Verification Order + V3 Worktree Roles + V3 Verification Gate |
| docs/UPSTREAM_SYNC_STRATEGY.md | V3 Wave Source Of Truth + V3 Wave Exclusion Note + V3 Ingress Policy + V3 Release Overlay Boundaries |
| docs/CARRY_FORWARD_REGISTRY.md | V3U custom allowlist rule + V3 lane carry-forward placeholder |
| docs/V3U_PYD_REMOVAL_PLAN.md | §11 자동 검증 시스템 extension |
| CLAUDE.md | V3U Test Automation Gate |
| docs/V3U_TEST_AUTOMATION_GUIDE.md | 신규 운영 가이드 |
| docs/update_log/2026-05-12_v3u_test_automation_setup.md | 본 도입 감사 |

## 6. acceptance criteria 검증

| # | 기준 | 결과 |
|---|---|---|
| AC1 | V3 official source 0줄 수정 | PASS (모든 변경이 V3U 전용 경로) |
| AC2 | pytest 31 케이스 PASS | PASS |
| AC3 | contract verifier 통합 PASS | PASS |
| AC4 | tracked .pyd / DB / log 0건 | PASS |
| AC5 | STOM_Version_3U_C 미생성 | PASS |
| AC6 | 거버넌스 문서 grep marker 4건 | PASS (V3 Lane Branch Parity / V3 Wave Source Of Truth / V3U custom allowlist / V3U Test Automation Gate) |
| AC7 | 신규 가이드 + 감사 문서 2건 | PASS |
| AC8 | 한글 commit 6개 (Phase 1~6.2) | PASS (1c794774, 96787192, 4059ce36, fc1870fe, b43fef6e, 096cc1a7, + 본 커밋 = 7개) |

## 7. V3 정규 업데이트 흡수 흐름 (도입 후)

```
1. V3 upstream에서 새 버전 (V3.19) 발표
2. git checkout STOM_Version_3U
3. git merge STOM_Version_3
4. python scripts/verify_v3u_pyd_gui_contract.py \
       --branch STOM_Version_3U --version V3.19 \
       --upstream-ref STOM_Version_3 \
       --manifest .omx/logs/v3u/verify_v3_19_<date>.json
5. PASS → V3.19에서 pyd 인터페이스 변화 없음. 본 update_log/에 감사 한 개 추가.
   FAIL → pytest 출력의 정확한 위치를 본다. ui/main_window.py 또는 tests/v3u/에서만 수정.
          V3 official source는 절대 수정하지 않는다.
```

## 8. 자동화 한계 (사용자 영역 영구 보존)

본 시스템 도입 후에도 다음은 본질적 자동화 불가다.

- C1·C2·C3·C4: LS/바이낸스/업비트 실거래 (자격증명·실 자금·라이브 시장)
- B3: LS 웹소켓 체결/호가 분리 라이브 수신
- D1: 사용자 실 DB 마이그레이션 (사용자 환경 고유)
- F1: `STOM_Version_3U_C` 생성 시점 결정 (정책 판단)
- E1·E2: V3 upstream V3.0 태그 reconcile (V3 wave 시작 시 별도 결정)
- 시각 미적 판단 (UX는 사람만)

## 9. 남은 위험과 차후 개선

| 위험 | 완화 |
|---|---|
| pytest-qt EventLoop hang | session-scope qapp + pytest-timeout 60s + verifier 600s |
| 합성 데이터가 V3 분석기 가정과 어긋남 | dict_findex_v318.json 스냅샷 + factor_lists 라이브 import |
| V3 upstream handler 시그니처 변경 | 의도된 fail 신호 (ui/main_window.py만 수정) |
| 합성 데이터 픽스처 유지보수 | V3 흡수 시 schema 자동 비교 (Phase D 별도 ralplan) |

차후 개선:
- 옵션 D: 스크린샷 회귀 (시각 깨짐 자동 감지)
- 옵션 E: AI 자동 시나리오 생성기 (`ui/event_click/` 자동 분석)
- CI 통합: GitHub Actions 또는 pre-commit hook
- V2.79 lane 동일 패턴 도입 (V2.79 wave 종료 후)

## 10. 감사 메타

- Constraint: V3 official runtime source 0줄 수정. 본 커밋 포함 모든 Phase가 V3U 전용 경로만 수정.
- Constraint: 자격증명·실거래 API 호출 0건. 모든 거래소는 mock 응답으로만 검증.
- Constraint: `_database/`, `_log/`, `*.db`, `STOM_Version_3U_C` 변경 0건.
- Confidence: High (자동 검증 영역 31 케이스 전체 PASS + verifier 통합 PASS).
- Scope-risk: narrow (V3U 전용 경로 + docs/ 갱신만).
- Directive: 본 감사 commit 후에도 `STOM_Version_3U_C` 생성은 사용자 시각 검증(1·2순위) 통과 후 별도 결정.
- Tested: 본 문서 §3, §6 매트릭스 전체 PASS.
- Not-tested: 본 문서 §8의 사용자 영역 6개 항목.
- Reference: `.omc/plans/2026-05-12_v3u_test_automation_and_governance.md` 컨센서스 플랜 12 섹션 + ADR.
