# 2U_C V3 backport queue 시작 기준

작성일: 2026-05-06
대상 root: `C:/System_Trading/STOM/STOM_V`
대상 custom worktree: `C:/System_Trading/STOM/STOM_V.wt-dev`
대상 branch: `STOM_Version_2U_C`

## 1. 목적

V3 공식 ingress와 V3U pyd-free 전환이 완료되었으므로, 초기 V3 전환 계획의 Phase 11인 `2U_C V3 backport queue`를 시작할 수 있는 운영 기준을 고정한다.

이 문서는 코드 backport를 수행하지 않는다. 먼저 queue 기준, 금지선, preflight, 기록 양식을 고정해 다음 단계에서 누락 없이 안전하게 후보를 검토하기 위한 문서다.

## 2. 현재 판정

```text
V3 official ingress        완료: STOM_Version_3 / STOM V3.18
V3U pyd-free               완료: STOM_Version_3U / tracked .pyd 없음
3U_C 생성                  보류 유지
2U_C V3 backport queue     지금부터 준비/시작
```

`STOM_Version_2U_C`는 V3 branch가 아니다. V2/Kiwoom 유지 custom lane이며, V3 기능은 선별 backport만 허용한다.

## 3. 현재 worktree 증거

```text
STOM_V/          -> STOM_Version_2
STOM_V.wt-2u/    -> STOM_Version_2U
STOM_V.wt-dev/   -> STOM_Version_2U_C
STOM_V.wt-3/     -> STOM_Version_3
STOM_V.wt-3u/    -> STOM_Version_3U
STOM_V.wt-2uc/   -> integration/adopt-cli-v267-into-2uc archive
```

현재 `STOM_V.wt-dev` 상태에서 `backtest/graph/` untracked output이 확인되었다. 이 경로는 backport source로 취급하지 않으며, 이후 2U_C 작업 diff와 섞이지 않게 별도 주의한다.

## 4. Phase 11 진입 조건 점검

| 조건 | 상태 | 근거 |
|---|---|---|
| V3 official 반영 | 충족 | `STOM_Version_3` HEAD `STOM V3.18` |
| V3 기능 source 명확화 | 충족 | source는 `STOM_Version_3`, 후보별 commit/version 기록 필요 |
| V3U pyd-free 완료 | 충족 | `STOM_Version_3U` tracked `.pyd` 없음 |
| 3U_C 보류 | 충족 | `STOM_Version_3U_C` branch 없음 |
| backport template 준비 | 이번 문서와 registry 보정으로 충족 | `docs/CARRY_FORWARD_REGISTRY.md` 보정 |
| 2U_C clean preflight | 다음 단계 필요 | `backtest/graph/` untracked output 주의 |

## 5. Backport 후보 선정 원칙

1. broker-neutral 기능부터 검토한다.
2. LS API 전제를 그대로 가져오지 않는다.
3. DB 비호환 변경은 migration spec 전에는 제외한다.
4. Kiwoom 유지 보정이 필요한 경우 범위를 명확히 기록한다.
5. 후보별 source V3 version, source commit, source files를 기록한다.
6. 하나의 backport 후보는 하나의 문서/커밋 단위로 작게 진행한다.
7. 2U_C와 2U의 차이는 registry 또는 update log allowlist로 남긴다.

## 6. 우선순위

### 1순위: broker-neutral 후보

- UI 편의 개선 중 거래 API와 무관한 부분
- 차트 예외처리/표시 보정 중 API 의존 없는 부분
- 로그 정리
- 순수 계산 함수 최적화
- 전략 문법 테스트/검증 helper 중 API 의존 없는 부분
- backtest 계산 개선 중 DB migration이 필요 없는 부분

### 2순위: 분리 가능한 구조 개선

- 분석 시스템 일부
- 학습 데이터 저장/로딩 중 독립 가능한 helper
- strategy helper 중 V3 trade runtime 전제가 없는 부분
- backtest 엔진 공통 개선
- UI tab/dialog 개선 중 trade runtime과 무관한 부분

### 3순위: 보류 후보

- LS REST/runtime 직접 사용
- `trade/restapi_ls.py`, `trade/restapi_lsdata.py` 직접 이식
- LS TR/REAL/주문체결 타입 전제
- Kiwoom 파일 제거를 전제로 한 trade 구조
- DB primary key/schema 비호환 migration
- 계좌/주문/체결 runtime 전제 변경

## 7. Backport 기록 양식

각 후보는 아래 양식을 사용한다.

```text
Backport ID:
Source V3 version:
Source upstream commit:
Source files:
Target branch: STOM_Version_2U_C
Target worktree: C:/System_Trading/STOM/STOM_V.wt-dev
Goal:
Applied scope:
Excluded LS dependency:
Kiwoom 유지 보정:
DB impact:
UI impact:
Verification commands:
Verification result:
Remaining risk:
Rollback plan:
```

## 8. 다음 단계

다음 단계는 코드 수정이 아니라 `STOM_V.wt-dev`의 2U_C clean preflight와 기존 custom diff inventory다.

권장 확인:

```powershell
git -C C:/System_Trading/STOM/STOM_V.wt-dev status --short
git -C C:/System_Trading/STOM/STOM_V.wt-dev log -5 --oneline
git -C C:/System_Trading/STOM/STOM_V.wt-dev diff --name-status STOM_Version_2U...STOM_Version_2U_C
git -C C:/System_Trading/STOM/STOM_V.wt-dev ls-files _database/* _log/* *.db
git -C C:/System_Trading/STOM/STOM_V branch --list STOM_Version_3U_C
```

## 9. 금지선

- 아직 `STOM_Version_3U_C`를 만들지 않는다.
- 2U_C에 LS API runtime을 직접 넣지 않는다.
- DB 비호환 변경을 migration spec 없이 넣지 않는다.
- `_database`, `_log`, `*.db`, `backtest/graph/`를 커밋하지 않는다.
- V3U pyd-free 구현을 2U_C backport로 위장하지 않는다.
- backport 후보 문서 없이 2U_C 코드를 먼저 수정하지 않는다.

## 10. Phase 11.4 allowlist 문서화 결과

Phase 11.3 읽기 전용 후보 분석 결과는 `docs/update_log/2026-05-06_2uc_v3_backport_allowlist_plan.md`에 별도 고정했다.

요약:

- allowlist 후보: `BP-001` 백테스트 엔진 안정화, `BP-002` 차트/DB차트/크로스헤어 안정화, `BP-003` Binance/Upbit 안정화, `BP-004` webcrawling/sound/log 안정화, `BP-005` UI bounce/progress 중복 확인
- 보류 후보: `HOLD-001` V3 분석 시스템 확장, `HOLD-002` V3 DB 구조 개선
- 금지선 유지: LS API runtime, DB 비호환 migration, V3U pyd-free 구현, `STOM_Version_3U_C`, `_database`, `_log`, `*.db`, `backtest/graph/`
- 다음 단계: Phase 11.5에서 첫 적용 후보를 하나만 선택하거나, 코드 적용 없이 큐만 유지하는 종료 판정을 한다.

## 11. Phase 11.5 최종 판정

Phase 11.5 최종 판정은 `docs/update_log/2026-05-06_2uc_v3_backport_phase11_final_decision.md`에 별도 고정했다.

요약:

- 첫 적용 후보는 `BP-004`로 선택한다.
- 즉시 2U_C runtime 코드는 변경하지 않는다.
- 다음 실제 구현은 `2UC-V3-BP-004A` 또는 `2UC-V3-BP-004B` 같은 micro-candidate 단위로만 시작한다.
- Phase 11은 전략/문서/후보 선정 단계로 완료 처리한다.
