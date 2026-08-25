# 핸드오프 — Process Research Pipeline 재출발 (2026-08-24)

> **최신 실행 핸드오프**
>
> 브랜치: `codex/process-research-pipeline-restart`
>
> worktree: `C:\System_Trading\STOM\STOM_V.wt-process-research-restart`
>
> 시작 기준: `loop/process-research-pipeline` @ `f75b80ebcb7fd72cd41c8933c4f6e63df8c2ae52`
>
> **2026-08-26 최신 실행:** BOOT-01·PIPE-01·SYS-01A·SYS-01B에 이어 UX-01 V4 Global Truth Bar를 완료했다. 실제 취소 job과 명시적 5상태 fixture를 브라우저에서 직접 선택했고, 실패 기록도 분석 결과를 가장하지 않은 채 Truth만 확인하도록 교정했다. 상세 정본은 `2026-08-26_UX-01_V4_Global_Truth_Bar_구현결과.md`, 다음 한 단위는 **ANA-01 AnalysisBundle v2**다.

---

## 1. 이번에 완료한 것

| 항목 | 결과 |
|---|---|
| 원격 갱신 | `origin/loop/process-research-pipeline`과 `origin/research/v516-d3-mcap-dev` fetch |
| 계보 확인 | 원격 loop `1add7f85`는 연구 `97a59ad`의 조상, 연구가 47커밋 앞섬 |
| 로컬 loop 정렬 | `c9a71c1c → 1add7f85` fast-forward |
| 연구 통합 | `1add7f85` + `97a59ad`를 병합 커밋 `f75b80eb`으로 통합 |
| 재출발 브랜치 | `codex/process-research-pipeline-restart` 생성 |
| 작업 격리 | 기존 `STOM_V.wt-dev`의 삭제·미추적 파일을 건드리지 않음 |
| 계획 정본 | `2026-08-24_process_research_pipeline_재출발_대시보드_연구_성숙화_마스터플랜.md` 작성 |

## 2. 현재 판정

| 범위 | 상태 |
|---|---|
| 플랫폼·Census·시드·공식엔진 연결 | 재사용 가능한 기반 있음 |
| D3 1일 feasibility | 역사 screen raw label 40건: metrics 2, no-trades 21, error 15, timeout 2 — **전체 40건은 아직 증거 기반 재분류하지 않음** |
| `<3000` 반복 연구 | 미완료 |
| 나머지 3Band 반복 연구 | 미완료 |
| 개선 세대 lineage | 없음 |
| 실제 Controls/Folds/FDR/posterior | 미실행 |
| Robust 후보 | 0 |
| OOS/실전/자동채택 | 미검증/금지 |

플랫폼 완료를 연구 완료로 표현하지 않는다. `81/81`은 당시 플랫폼·거버넌스 체크리스트와 typed terminal 상태에 대한 역사 기록일 뿐, 사용자가 요청한 Band별 반복 연구 완료율이 아니다.

## 3. 먼저 읽을 문서

| 순서 | 문서 | 목적 |
|---:|---|---|
| 1 | 본 핸드오프 | Git·재개 지점 확인 |
| 2 | `2026-08-24_process_research_pipeline_재출발_대시보드_연구_성숙화_마스터플랜.md` | 전체 단계·페이지·분석·성숙도 |
| 3 | `HANDOFF_2026-08-24_v516_시총별_반복연구_재개.md` | D3 실제 실행과 실패 원장 |
| 4 | `2026-08-15_기존DB_시가총액분할_상태전이연구와_v5.16_재출발_마스터플랜.md` | 기존 설계와 Native gate |
| 5 | D3 Evidence 5종 | 원 데이터 대조 |

## 4. 다음 실제 착수 단위

### PIPE-01 — `<3000` 10건 실행 실패 원장 — 완료

2026-08-25 읽기 전용으로 10/10 원장화를 완료했다. 아래 표의 `입력 상태`는 역사 screen의 원래 표기이며, 오른쪽은 원시 Evidence 정정이다.

| 입력 상태 | 원래 수 | 증거 기반 상태 | 정정 수 |
|---|---:|---|---:|
| metrics | 2 | 지표 생성, 소표본 손실 | 2 |
| no-trades | 2 | `engine_strategy_exception` / TypeError | 정상 무거래 0, 오류 2 |
| error | 4 | `engine_data_response_timeout` | 오류 4 |
| timeout | 2 | watchdog 회수, 내부 원인 `NOT_OBSERVED` | timeout 2 |

완료 조건:

- 10/10 job에 typed boundary cause와 재실행 정책을 기록했다.
- PnL을 보고 조건식을 고치거나 과거 Evidence를 덮어쓰지 않았다.
- job ID 중복을 발견해 provenance 복합 identity 요구사항으로 올렸다.
- 지표 생성 2건도 거래 2/4건의 손실이므로 경제 판정은 `INCONCLUSIVE`다.

### SYS-01A — Research Truth Contract — 완료

실행·경제·권위·행동을 분리한 strict type과 invariant validator를 구현하고 PIPE-01 10건을 회귀 fixture로 고정했다. 아직 UI·연구 재실행으로 넘어가지 않는다.

| 축 | 상태 |
|---|---|
| 실행 | SUCCESS / NO_TRADES / ERROR / TIMEOUT / CANCELLED / PARTIAL |
| 경제 | POSITIVE / NEGATIVE / INCONCLUSIVE / NOT_EVALUABLE |
| 권위 | FEASIBILITY / DEVELOPMENT / FROZEN_OOS / SHADOW / LIVE |
| 행동 | DEBUG / REPRODUCE / STRUCTURAL_REVISE / EXPAND / STOP / HOLDOUT |

### SYS-01B — legacy adapter와 read-only API — 완료

과거 artifact를 수정하지 않고 typed view로 읽으며, 새 terminal 판정은 exception·timeout 증거를 일반 `without metrics` 메시지보다 우선한다. API와 WebSocket은 같은 schema를 사용하고 job ID 단독 조회를 허용하지 않는다.

| 완료 계약 | 결과 |
|---|---|
| exact `total_report_no_trades` receipt | 새 정상 무거래 판정의 필수 조건 |
| exception/data-timeout precedence | 새 job은 `error`, 과거 job은 additive Truth에서 `ERROR` |
| REST/WS parity | 동일 builder·동일 Truth payload |
| scope identity | configured manager/jobs-dir와 job/source identity 결합 |
| persistence | `none`; 과거 JSON·DB 수정 없음 |
| PIPE-01 adapter projection | `SUCCESS 2 / NO_TRADES 0 / ERROR 6 / TIMEOUT 2` |

### UX-01 — V4 Global Truth Bar — 완료

V4 백테스트 최상단에 실행·경제·권위·다음 행동과 차단 사유를 배치했다. 산출물이 없는 취소·오류·시간초과 기록도 선택할 수 있지만 결과 화면은 열지 않는다.

| 완료 계약 | 결과 |
|---|---|
| 5상태 browser fixture | success/no-trades/error/timeout/partial 모두 PASS |
| 실제 job | 취소 기록 `CANCELLED / NOT_EVALUABLE / FEASIBILITY / REPRODUCE` 확인 |
| 반응형 | 1280 4축·720 2열·560 1열, 가로 넘침 없음 |
| 접근성 | landmark/live region/keyboard focus/색 비의존 |
| read-only | `LEGACY_INCOMPLETE`, `persistence none`; 원본 수정 없음 |
| frontend 품질 | production build·typecheck·V1~V7 harness·console error 0 |

## 5. 권장 구현 순서

| 순서 | 작업 |
|---:|---|
| 1 | PIPE-01 failure ledger — **완료** |
| 2 | SYS-01A pure Truth Contract — **완료** |
| 3 | SYS-01B adapter/read-only API — **완료** |
| 4 | UX-01 Global Truth Bar — **완료** |
| 5 | ANA-01 AnalysisBundle v2 — **다음** |
| 6 | UX-02 Result Overview |
| 7 | RES-01 `<3000` 다기간 사전등록 |
| 8 | RES-02 G0 공식 실행 |
| 9 | ANA-02 구조 부검 |
| 10 | RES-03 G1 구조 개선·동일 계약 재실행 |
| 11 | UX-03 실제 데이터 사용성 반복 |

## 6. 연구 불변식

- Band 경계 `3000/5000/10000`을 결과 후 이동하지 않는다.
- 실행 실패와 경제 실패를 분리한다.
- 후보 선택에 PnL을 쓰지 않는다.
- 좋은 달·좋은 거래·좋은 Family만 사후 선택하지 않는다.
- threshold 미세조정을 구조 개선으로 부르지 않는다.
- development를 OOS·실전·자동채택으로 표현하지 않는다.
- 실제 Controls/Folds/posterior 전 D4를 실행하지 않는다.
- strategy DB와 보호 DB에 쓰지 않는다.
- advisory counterfactual을 공식 결과로 승격하지 않는다.
- OOS는 후보 봉인 전 열지 않는다.

## 7. 구현 불변식

- `backtest_api.py`, `backtest_analysis.py`, `bt-result-area.jsx`는 과대 모듈이다. 회귀 테스트를 먼저 고정하고 책임별로 분리한다.
- 새 기능은 실제 job과 failure/no-trades fixture 모두로 검증한다.
- 실행 버튼은 필수 입력과 권위 조건을 모두 만족하기 전 비활성화한다.
- 화면은 `정체성 → 실행 완전성 → 경제 결과 → 강건성 → 다음 행동` 순서로 읽힌다.
- 페이지별 스크롤·필터 상태가 다른 탭으로 새지 않게 한다.
- 최신 판정은 역사 HOF보다 먼저 보인다.
- frontend JSX 변경 시 bundle/manifest를 다시 빌드하고 직접 브라우저에서 확인한다.

## 8. 시작 확인

```powershell
Set-Location 'C:\System_Trading\STOM\STOM_V.wt-process-research-restart'
git branch --show-current
git log -1 --oneline
git status --short
git rev-parse loop/process-research-pipeline
```

예상:

| 확인 | 값 |
|---|---|
| branch | `codex/process-research-pipeline-restart` |
| loop integration | `f75b80ebcb7fd72cd41c8933c4f6e63df8c2ae52` |
| 작업 상태 | 문서 커밋 이후 clean |

## 9. 검증 명령

### 9.1 현재 fresh worktree에서 안전한 검증

```powershell
python -m pytest tests/unit/test_d3_engine_screen.py tests/unit/test_d3_screen_decision.py -q -p no:cacheprovider
python scripts/verify_nonrelease_sync.py
python scripts/build_research_docs_index.py --check
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

### 9.2 명시적 provisioning 이후에만 실행할 검증

현재 worktree에는 `node_modules`, `_database/strategy.db`, `loop_strategies.db`가 없다. 특히 일부 DB 결합 테스트는 누락 DB를 0-byte 파일로 만들 수 있으므로, 아래 명령은 BOOT preflight가 `NODE_RUNTIME_PROVISIONED`와 `DB_FIXTURE_PROVISIONED_READ_ONLY`를 모두 확인하기 전에는 실행하지 않는다.

```powershell
python -m pytest tests/unit/ -q
python scripts/smoke_offline_gui.py --branch codex/process-research-pipeline-restart --version V2.79 --offline --log-dir .omx/logs/process-research-restart
python scripts/verify_pyd_gui_contract.py --branch codex/process-research-pipeline-restart --version V2.79 --upstream-ref STOM_Version_2 --manifest .omx/logs/process-research-restart/verify_pyd_gui_contract.json --log-dir .omx/logs/process-research-restart
```

## 10. 중지 조건

아래 중 하나면 연구 실행을 시작하지 말고 원인을 기록한다.

| 조건 | 행동 |
|---|---|
| prereg commit 없음 | 실행 중지 |
| source/engine/DB identity 불일치 | 실행 중지 |
| error/timeout 원인 미분류 | 해당 후보 재실행 중지 |
| protected path write 감지 | 즉시 중지·원상 확인 |
| 결과 후 기간/기준 변경 요구 | 새 프로그램으로 분리 |
| D4 gate 미충족 | Native 최적화 중지 |

## 11. 다음 세션의 첫 보고 형식

| 항목 | 보고 |
|---|---|
| 플랫폼 진행률 | PIPE/SYS/UX/ANA 작업 단위 |
| 연구 진행률 | Band/세대/후보/유효 실행/분석/개선 횟수 |
| 실행 실패 | error/timeout 원인과 재시도 |
| 경제 결과 | 거래수·net PnL·MDD·표본력 |
| 통계 | controls/folds/FDR/posterior |
| 권위 | feasibility/development/OOS/live |
| 다음 행동 | 정확히 하나 |

현재 다음 행동은 **`ANA-01 — 동일 입력에서 결정적으로 생성되는 AnalysisBundle v2 schema/builder`**다.
