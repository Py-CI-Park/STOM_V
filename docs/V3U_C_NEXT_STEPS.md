# V3U_C lane Next Steps Decision Tree (지속 관리)

- 최초 작성: 2026-05-22
- 대상 lane: `STOM_Version_3U_C`
- 갱신 주기: 매 V3U_C 사이클 종료 시 §5 선택 이력 추가
- 상위 진실 원천: `docs/V3U_NEXT_STEPS.md` (V3U lane decision tree, V3U_C 옵션 그룹 E 정의)

## 1. 본 문서의 목적

3U_C lane의 미래 결정 옵션을 정렬한다. V3U lane이 `V3U_NEXT_STEPS.md`로 옵션 카탈로그 운영하는 것과 동일 패턴.

## 2. 현재 상태 (사이클 8 종료, 2026-07-12)

| 지표 | 값 |
|---|---|
| 활성 사이클 | 8 (V3.35 흡수 — V3U lane 따라잡기) |
| lane 버전 | **V3.35** (사이클 8, 사이클 7에서 V3.34 → V3.35) |
| 결함 누적 | 2 (사이클 4 #1·#2) — 사이클 5~8 신규 0건 |
| 회귀 테스트 | custom 32 + V3U 안전망 상속 49 = 81 |
| 신규 자동 도구 | 4 (v3uc_ingest_pipeline / db_compatibility_check / strategy_migration / cli) |
| commit 누적 | 사이클 1 `ebd9a8f3`, 2 `c0c43958`, 3 `87b6645b`, 4 `28d9bf9b`, 5 merge `32900141`, 6 merge `705fb7fd`, 7 merge `352a3838`, 8 merge `ff704397` |
| V3U 안전망 상속 상태 | 49 pytest + baseline 0 (통합 게이트 8/8 PASS, 3U_C 워크트리) |

## 3. 옵션 카탈로그

V3U lane V3U_NEXT_STEPS.md 그룹 E의 V3U_C custom 작업 옵션 (E1~E4) + 3U_C-specific 옵션 추가.

### E1: V3.X 흡수 자동화 파이프라인 ✅ **사이클 1 완료** (용도 주의)

- 산출: scripts/v3uc_ingest_pipeline.py + tests/v3uc/test_ingest_pipeline.py + docs/V3U_C_INGEST_PIPELINE.md
- **용도 = `STOM_Version_3`(V3공식) → `STOM_Version_3U` merge 전용** (V3U lane에서 실행)
- ⚠️ **3U_C 따라잡기(`V3U → 3U_C`)에는 사용하지 않는다** — 그건 `git merge
  STOM_Version_3U` (사이클 5 방식). E1 docstring "3U_C는 본 스크립트 보관만" 참조.
- 운영(V3공식→V3U): V3.X 발표 시 wt-3u에서 `--dry-run` → 성공 시 `--live`

### E2: V3U/3U_C 통합 CLI ✅ **사이클 4 완료** (2026-05-30)

- 산출: scripts/v3uc_cli.py + tests/v3uc/test_cli.py (16) + docs/V3U_C_CLI_GUIDE.md
- 7 subcommand: status / verify / db scan|migrate / test / ingest / gui
- 디스패처 패턴: 실 도구는 기존 v3uc_* 4종 + verify_v3u_pyd_gui_contract.py 호출
- 안전 가드: db migrate `--confirm` 또는 `--dry-run` 필수, utf-8 stdout 재설정
- 운영: 매 세션 `cli status`로 양 lane 상태 1-key 확인

### E3: 실시간 모니터링 dashboard ⏳ 미진행

- 후보 작업: `ui.web_dashboard` 활성화 (V3U lane 결함 #15에서 placeholder만 부착)
- 자체 web server worker + 사이드카 승인 패턴 (2U_C 참고)

### E4: 고급 백테 자동화 ⏳ 미진행

- 후보 작업: 백테 결과 자동 분석 + GA + Optuna 자동 ranking
- 2U_C V3K mapping 지도 패턴 참고

### E5: DB 마이그레이션 호환성 진단·자동 PK 추가 도구 ✅ **사이클 2 완료** (2026-05-22)

- 산출: scripts/v3uc_db_compatibility_check.py + tests/v3uc/test_db_compatibility.py + docs/V3U_C_DB_MIGRATION_PLAN.md
- 동작: --scan (read-only PK 매트릭스) / --add-pk (자동 추가, 백업 검증) / --analyze-extra (기타 DB)
- 운영: 사용자가 update_db_20260418.bat 후 호출 (V3.08+ 호환성 검증)

### E7: strategy.db V2→V3 조건식 마이그레이션 ✅ **사이클 3 완료** (2026-05-23)

- 산출: scripts/v3uc_strategy_migration.py + tests/v3uc/test_strategy_migration.py
- 동작: V2 `stockbuy/stocksell/...` → V3 `stock_buy/stock_sell/...` (밑줄 추가), 거래소별 target prefix
- 운영: 사용자가 strategy.db V2 데이터 보유 시 호출 (백테 조건식 사전 사용 가능)
- 실 실행 결과: 51 매수 + 35 매도 + 2/2/5 옵티 = 총 95 rows V2→V3 복사

### E6 (신규 후보): T-step extension (T06 pre-flight + T07 notification)

- E1 운영하며 발견되는 패턴을 본 옵션으로 흡수
- T06: V3 upstream fetch + delta 미리 보기 (사용자 결정 보조)
- T07: 흡수 완료 후 Telegram/email 알림

### E6 (신규 후보): multi-version 흡수

- E1을 V3.19 + V3.20 연속 처리 가능하도록 확장
- 각 버전별 audit JSON 누적

## 4. 우선순위 추천 매트릭스 (사이클 4 종료 시점 재평가)

| 우선순위 | 옵션 | 사유 |
|---|---|---|
| 🟢 1 | E1 운영 dry-run (V3.30+ 발표 시) | `cli ingest --version X --dry-run` 1-key 호출 가능 |
| 🟡 2 | E4 고급 백테 자동화 | 사용자 백테 정상 확인 후 backtest 결과 자동 분석·ranking |
| 🟠 3 | E3 실시간 dashboard | web_dashboard 활성화 + 사이드카 패턴 |
| ⚪ 4 | 기타 DB PK 도구 (E5 v2) | **분석 결과 백테 사용 시 불필요** — 실시간 수집 사용 시에만 |
| ⚪ 5 | E6 multi-version 흡수 / T06·T07 extension | E1 실 운영 사이클 후 자연 발견 |

## 5. 선택 이력 (지속 갱신)

```
### 사이클 N (YYYY-MM-DD): 선택 옵션 / 결과 요약

- 사용자 선택: <옵션 ID>
- 실행 결과: <commit hash, pytest 케이스 변화, 결함 N건 fix>
- 발견 신규 결함: <카테고리·#번호 또는 "없음">
- 본 문서 갱신: <§3·§4 변경 요약>
- 다음 사이클 후보: <다음 우선순위 옵션>
```

### 사이클 8 (2026-07-12): V3.35 흡수 (V3U lane 따라잡기)

- 사용자 선택: "최신 업스트림 확인·반영, 3U/3U_C까지, 2* 시리즈는 계획서만"
- 실행 결과:
  - merge commit `ff704397` (`git merge --no-ff STOM_Version_3U`), lane V3.34 → **V3.35**
  - V3.35 바이낸스선물 정정주문 + LS 시장가 주문가격 수정 + 주문 예외 처리 강화 + tail 4건 상속
  - custom 보존, 충돌 0건
  - 통합 게이트 8/8 PASS (pytest 49) + tests/v3uc 32 = 81 PASS, invariant 만족 (diff allowlist only)
- 발견 신규 결함: 0건
- 사이클 5에서 명문화한 hop별 메커니즘 그대로 적용 (V3U→3U_C는 git merge)
- 본 문서 갱신: §2 상태표(V3.35) + 본 §5 항목
- 다음 사이클 후보: 사용자 GUI 확인(주문 경로), 3U_C custom 작업(E3/E4), V3.36+ 발표 시 동일 패턴

### 사이클 7 (2026-06-29): V3.34 흡수 (V3U lane 따라잡기)

- 사용자 선택: "올바른 프로세스로 1,2,3 진행 후 4 5 안내"
- 실행 결과:
  - merge commit `352a3838` (`git merge --no-ff STOM_Version_3U`), lane V3.33 → **V3.34**
  - V3.34 해외주식 주문체결 처리 오류 수정 + 바이낸스선물 감시종목제한 설정 추가 상속
  - V3U data-layer test adjustment 상속, custom 보존, 충돌 0건
  - 통합 게이트 8/8 PASS (pytest 49) + tests/v3uc 32 = 81 PASS, invariant 만족
- 발견 신규 결함: 0건
- 사이클 5에서 명문화한 hop별 메커니즘 그대로 적용 (V3U→3U_C는 git merge)
- 본 문서 갱신: §2 상태표(V3.34) + 본 §5 항목
- 다음 사이클 후보: 사용자 GUI 확인(안내 4), V3U backup 정리 판단(안내 5), 3U_C custom 작업(E3/E4) 또는 V3.35+ 발표 시 동일 패턴

### 사이클 6 (2026-06-13): V3.33 흡수 (V3U lane 따라잡기)

- 사용자 선택: "흡수 진행해" (V3.33 신규 발표 흡수)
- 실행 결과:
  - merge commit `705fb7fd` (`git merge --no-ff STOM_Version_3U`), lane V3.32 → **V3.33**
  - V3.32 tail fcc626a5(윈도우 핸들) 포함, custom 보존, 충돌 0건
  - 통합 게이트 8/8 PASS (pytest 49) + tests/v3uc 32 = 81 PASS, invariant 만족
- 발견 신규 결함: 0건
- 사이클 5에서 명문화한 hop별 메커니즘 그대로 적용 (V3U→3U_C는 git merge)
- 본 문서 갱신: §2 상태표(V3.33) + 본 §5 항목
- 다음 사이클 후보: 3U_C custom 작업(E3/E4) 또는 V3.34+ 발표 시 동일 패턴

### 사이클 5 (2026-06-13): V3.19~V3.32 흡수 (V3U lane 따라잡기)

- 사용자 선택: "A 진행" (3U_C에 V3.19~V3.32 흡수, V3U lane 결정 트리 옵션 A)
- 실행 결과:
  - merge commit `32900141` (`git merge --no-ff STOM_Version_3U`, 27 commit 상속)
  - lane 버전 V3.18 → **V3.32**, custom 15파일 보존, 충돌 0건
  - 통합 게이트 8/8 PASS (pytest 49) + tests/v3uc 32 = 81 PASS
  - invariant 만족: 3U_C vs V3U diff = custom 파일만 (허용 외 0건)
- 발견 신규 결함: 0건
- 핵심 발견: **흡수 메커니즘이 hop마다 다름** — V3공식→V3U는 overlay/E1,
  V3U→3U_C는 git merge. E1 파이프라인(`v3uc_ingest_pipeline.py`)은 본 hop에
  쓰지 않음 (docstring "3U_C는 보관만"). §3 E1 항목 주석 갱신.
- 본 문서 갱신: §2 상태표(V3.32) + 본 §5 항목 + §3 E1 용도 명확화 + §4 재평가
- 흡수 감사: docs/update_log/2026-06-13_v3uc_v319_v332_absorption.md
- 다음 사이클 후보:
  - 사용자 stom.py 직접 테스트 (3U_C custom 도구 `cli status` 등)
  - E3 실시간 dashboard 또는 E4 고급 백테 자동화
  - V3.33+ 발표 시 동일 패턴 (V3U 먼저 흡수 → git merge로 3U_C)

### 사이클 4 (2026-05-30): E2 V3U/3U_C 통합 CLI 도입

- 사용자 선택: "c 진행 ultracode" (E2/E3/E4 중 자율 선택)
- 실행 결과:
  - scripts/v3uc_cli.py (~330 라인, 7 subcommand, 디스패처 패턴)
  - tests/v3uc/test_cli.py (16 케이스, 모두 PASS, 32 누적 회귀)
  - docs/V3U_C_CLI_GUIDE.md (운영 매뉴얼)
  - 본 문서 §2/§3 E2/§4 우선순위 갱신
- 발견 신규 결함: 2건 (자체 도구 결함, V3 official 영향 없음)
  - #1 argparse `parents=` gotcha: subparser default가 부모 namespace를 None으로 덮어씀
  - #2 Windows cp949 콘솔에서 em-dash 등 비-cp949 글자 UnicodeEncodeError
  - 둘 다 사이클 내 즉시 fix + 회귀 테스트로 커버
- V3U lane cross-link: V3U_NEXT_STEPS.md §5 사이클 12 항목으로 등록
- 사전 분석 부수 산출: backtest 순수 SELECT 확인 → 기타 DB PK 우선순위 ⚪로 하향
- 다음 사이클 후보:
  - 사용자 stom.py 백테 시각 확인 (사이클 10/11 Step 6 누적)
  - E3/E4 중 선택 또는 V3.30 발표 시 `cli ingest` 첫 실 사용

### 사이클 1 (2026-05-22): E1 V3.X 흡수 자동화 파이프라인 도입

- 사용자 선택: "E1 진행"
- 실행 결과:
  - scripts/v3uc_ingest_pipeline.py (5 T-step, ~270 lines)
  - tests/v3uc/test_ingest_pipeline.py (4 unit test 케이스, 모두 PASS)
  - docs/V3U_C_INGEST_PIPELINE.md (운영 매뉴얼)
  - docs/V3U_C_INFERENCE_LESSONS.md (결함 진실 원천 신규)
  - 본 문서 (NEXT_STEPS 신규)
- 발견 신규 결함: 0건 (dry-run 안전, 단위 테스트로 검증)
- 다음 사이클 후보:
  - E1 실 운영 (V3.19 발표 시 dry-run → live)
  - E2/E3/E4 중 선택 (3U_C lane 발전)

## 6. 운영 규칙

### 6.1 사이클 종료 시점의 정의

V3U lane과 동일 (V3U_NEXT_STEPS.md §6.1).

### 6.2 본 문서 갱신 의무

각 사이클 종료 시 다음 수행:
1. §2 현재 상태 표 갱신
2. §5 선택 이력에 본 사이클 항목 추가
3. §3 옵션 카탈로그에 신규 옵션 추가 또는 완료 옵션 표시
4. §4 우선순위 매트릭스 재평가

### 6.3 V3U lane과의 진실 원천 동기화

- V3U lane V3U_NEXT_STEPS.md §5 사이클 이력에도 V3U_C 사이클 진행을 간략히 기록
- 본 문서가 V3U_C 상세 기록의 진실 원천

## 7. 관련 문서

- `docs/V3U_C_INGEST_PIPELINE.md` E1 운영 매뉴얼
- `docs/V3U_C_INFERENCE_LESSONS.md` 결함 진실 원천
- `docs/CARRY_FORWARD_REGISTRY.md` V3U_C custom allowlist rule
- (V3U lane) `docs/V3U_NEXT_STEPS.md` V3U decision tree (V3U_C 옵션 그룹 E 정의)
- (V3U lane) `docs/V3U_INFERENCE_LESSONS.md` pyd-free 결함 진실 원천
- (V3U lane) `docs/V3U_TRANSITION_AUDIT_2026-05-22.md` 3U_C 생성 전 중간 점검
