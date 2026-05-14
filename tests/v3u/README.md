# V3U 자동 GUI 검증

본 디렉토리는 STOM_Version_3U lane 전용 자동 검증 시스템이다.

## 설계 원칙

1. **V3 official source 0줄 수정.** `tests/v3u/` 외부 코드는 import만 허용한다.
2. **사용자 시각 검증 보강이지 대체가 아니다.** 실거래·실 자금·UX 미적 판단은 사용자 영역.
3. **자격증명·실거래 API 호출 0건.** mock 응답만 사용한다.
4. **테스트 실패 = pyd 추론 갱신 신호.** 항상 V3U 전용 파일에서만 수정한다.

## 디렉토리 구조

```
tests/v3u/
├── conftest.py                   픽스처 (qapp, main_window, dict_findex_min/tick, synthetic_ohlcv)
├── fixtures/
│   ├── synthetic_ohlcv.py        합성 분봉/틱 생성기
│   ├── dict_findex_v318.json     V3.18 키 스냅샷 (drift 감지용)
│   └── responses/                REST API mock 응답 (Phase 4)
├── test_smoke.py                 1순위 사용자 검증 자동화 (Phase 2)
├── test_widgets.py               2·3순위 위젯/시그널 (Phase 3)
├── test_lifecycle.py             백테 spawn·분석기 (Phase 3)
├── test_data_layer.py            잔고·18거래소·DB (Phase 3)
├── test_units.py                 분석기/설정 단위 (Phase 4)
└── test_rest_api_contract.py     LS/바이낸스/업비트 mock 계약 (Phase 4)
```

## 실행

### 의존성 설치

```powershell
python -m pip install -r requirements-dev.txt
```

### 전체 실행

```powershell
python -m pytest tests/v3u/ -v
```

### 묶음별

```powershell
python -m pytest tests/v3u/ -m smoke -v          # 1순위
python -m pytest tests/v3u/ -m integration -v    # 2·3순위
python -m pytest tests/v3u/ -m unit -v           # 단위
python -m pytest tests/v3u/ -m contract -v       # REST API mock
```

### contract verifier 통합 실행 (Phase 5 이후)

```powershell
python scripts/verify_v3u_pyd_gui_contract.py `
    --branch STOM_Version_3U --version V3.18 `
    --upstream-ref STOM_Version_3
```

이 한 번이 정적·구조·동적 검증 통합 게이트가 된다.

## 사용자 잔여 작업과 본 시스템의 매핑

선행 핸드오프 체크리스트 25개 중 본 시스템이 자동화하는 항목:

| 사용자 수동 검증 | 자동 테스트 |
|---|---|
| `python stom.py` 메인창 기동 | `test_smoke.py::test_main_window_starts` |
| 9개 탭 클릭 | `test_smoke.py::test_all_tabs_switch_without_error` |
| 22개 백테 프로세스 핸들 | `test_smoke.py::test_22_backtest_proc_attrs_initialized` |
| 12개 큐 + stgQs | `test_smoke.py::test_12_queues_initialized` |
| strategy 아이콘 | `test_smoke.py::test_strategy_icons_render` |
| 백테 1 사이클 | `test_lifecycle.py::test_a4_backtest_process_spawn_with_synthetic` |
| 변손익분석 | `test_lifecycle.py::test_b6_volatility_analyzer_loads` |
| 미시구조 | `test_lifecycle.py::test_b7_microstructure_instantiation` |
| 잔고 변동시만 INSERT | `test_data_layer.py::test_b5_balance_dt_guard` |
| 18거래소 | `test_data_layer.py::test_d2_18_exchanges_isolated` |
| DB 자동 생성 | `test_data_layer.py::test_d3_database_check_empty_db` |
| AnalyzerRisk min_data | `test_units.py::test_b1_risk_min_data_30` |
| 실시간 prange 0건 | `test_units.py::test_b2_realtime_no_prange` |
| LS/바이낸스/업비트 import | `test_rest_api_contract.py::test_c{1,2,3}_*_signature_static` |

## 본질적 자동화 한계

다음 항목은 어떤 테스트 시스템을 도입해도 자동화 불가하며 사용자 영역으로 영구 보존된다.

| 항목 | 사유 |
|---|---|
| 위젯 시각 미적 판단 | UX는 사람만 |
| LS/바이낸스/업비트 실거래 (C1~C4·B3) | 자격증명·실 자금·라이브 시장 |
| 사용자 실 DB 마이그레이션 (D1) | 사용자 환경 고유 schema drift |
| `STOM_Version_3U_C` 생성 시점 (F1) | 정책 결정 |

## V3 정규 업데이트 흡수 흐름

```
1. V3 upstream에서 새 버전 발표 (예: V3.19)
2. git merge STOM_Version_3 → STOM_Version_3U
3. python scripts/verify_v3u_pyd_gui_contract.py … (= 본 디렉토리 + 정적 검증)
4. PASS → V3.19에서 pyd 인터페이스 변화 없음. 감사 증적만 추가.
   FAIL → 정확한 깨진 위치를 본 시스템이 지적. ui/main_window.py만 수정 후 재검증.
5. V3 official source는 항상 0줄 수정 유지.
```

## 새 테스트 추가 절차

1. `tests/v3u/test_*.py` 신규 파일 또는 기존 파일에 함수 추가
2. `pytest.ini`의 markers 중 적절한 것 부여 (`@pytest.mark.smoke` 등)
3. `python -m pytest tests/v3u/<file>::<func> -v`로 단독 실행 검증
4. 한글 의도 중심 커밋 (CLAUDE.md "Commit Language Rules")

## 관련 문서

- `.omc/plans/2026-05-12_v3u_test_automation_and_governance.md` 본 시스템 도입 계획
- `docs/V3U_PYD_REMOVAL_PLAN.md` pyd 제거 계획
- `docs/update_log/2026-05-06_v3u_final_parity_audit.md` 최종 parity 감사
- `docs/update_log/2026-05-07_v3u_handoff_verification_checklist.md` 핸드오프 체크리스트
- `docs/update_log/2026-05-12_v3u_extended_automation_audit.md` 확장 자동 감사
