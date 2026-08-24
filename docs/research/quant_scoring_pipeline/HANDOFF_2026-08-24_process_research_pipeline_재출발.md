# 핸드오프 — Process Research Pipeline 재출발 (2026-08-24)

> **최신 실행 핸드오프**
>
> 브랜치: `codex/process-research-pipeline-restart`
>
> worktree: `C:\System_Trading\STOM\STOM_V.wt-process-research-restart`
>
> 시작 기준: `loop/process-research-pipeline` @ `f75b80ebcb7fd72cd41c8933c4f6e63df8c2ae52`

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
| D3 1일 feasibility | 40건: metrics 2, no-trades 21, error 15, timeout 2 |
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

### PIPE-01 — `<3000` 10건 실행 실패 원장

이 작업이 다음 구현·연구의 첫 단위다.

| 입력 상태 | 건수 | 해야 할 일 |
|---|---:|---|
| metrics | 2 | 결과 identity와 CSV/engine/source hash 대조 |
| no-trades | 2 | 정상 무거래인지 조건식/기간/데이터 부재인지 분류 |
| error | 4 | compile/runtime/worker/source/contract 범주로 분류 |
| timeout | 2 | 계산량/heartbeat/queue/교착을 분리 |

완료 조건:

- 10/10 job에 typed cause가 있다.
- 재실행 가능 여부와 이유가 있다.
- PnL을 보지 않고 교정 가능한 문제만 분리한다.
- 과거 Evidence를 덮어쓰지 않는다.
- 결과가 없어도 `UNKNOWN`이 아니라 `NOT_OBSERVED` 또는 구체적 실패 상태를 쓴다.

### SYS-01 — Research Truth Contract

PIPE-01과 병렬 설계는 가능하지만 구현 병합은 실패 분류 용어를 확정한 뒤 한다.

| 축 | 상태 |
|---|---|
| 실행 | SUCCESS / NO_TRADES / ERROR / TIMEOUT / CANCELLED / PARTIAL |
| 경제 | POSITIVE / NEGATIVE / INCONCLUSIVE / NOT_EVALUABLE |
| 권위 | FEASIBILITY / DEVELOPMENT / FROZEN_OOS / SHADOW / LIVE |
| 행동 | DEBUG / REPRODUCE / STRUCTURAL_REVISE / EXPAND / STOP / HOLDOUT |

## 5. 권장 구현 순서

| 순서 | 작업 |
|---:|---|
| 1 | PIPE-01 failure ledger |
| 2 | SYS-01 typed Truth Contract |
| 3 | UX-01 Global Truth Bar |
| 4 | ANA-01 AnalysisBundle v2 |
| 5 | UX-02 Result Overview |
| 6 | RES-01 `<3000` 다기간 사전등록 |
| 7 | RES-02 G0 공식 실행 |
| 8 | ANA-02 구조 부검 |
| 9 | RES-03 G1 구조 개선·동일 계약 재실행 |
| 10 | UX-03 실제 데이터 사용성 반복 |

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

```powershell
python -m pytest tests/unit/ -q
python scripts/verify_nonrelease_sync.py
python scripts/smoke_offline_gui.py --branch codex/process-research-pipeline-restart --version V2.79 --offline --log-dir .omx/logs/process-research-restart
python scripts/verify_pyd_gui_contract.py --branch codex/process-research-pipeline-restart --version V2.79 --upstream-ref STOM_Version_2 --manifest .omx/logs/process-research-restart/verify_pyd_gui_contract.json --log-dir .omx/logs/process-research-restart
python scripts/build_research_docs_index.py --check
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
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

최초 다음 행동은 **`PIPE-01 — <3000 10건 실행 실패 원장`**이다.
