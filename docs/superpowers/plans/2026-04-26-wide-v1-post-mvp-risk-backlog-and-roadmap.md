# Wide v1 Post-MVP Risk Backlog And Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record the Wide v1 post-MVP roadmap, risk backlog, and PR report so the project can close Wide v1 cleanly and then move to Wide v2 automatic condition optimization without losing direction.

**Architecture:** This is a documentation-only implementation. It creates one roadmap document, one risk backlog/live-pilot checklist, and one Korean PR report, all grounded in the committed Wide v1 freeze evidence and the approved design spec.

**Tech Stack:** Markdown, PowerShell, Git, existing STOM documentation layout.

---

## File Structure

- Create: `docs/research/condition_research/mvp/2026-04-26_wide_v1_post_mvp_roadmap.md`
  - Responsibility: explain the whole development path from Wide v1 MVP freeze to the final automatic condition-improvement system.
- Create: `docs/research/condition_research/mvp/2026-04-26_wide_v1_post_mvp_risk_backlog.md`
  - Responsibility: list what Wide v1 WFO/freeze proves, what it does not prove, and what must be checked before any live/paper pilot.
- Create: `docs/pr/2026-04-26_wide_v1_post_mvp_risk_backlog_pr.md`
  - Responsibility: provide the Korean PR body for this branch, including changed files, verification, and the next Wide v2 command.
- Modify only if needed: `docs/superpowers/plans/2026-04-26-wide-v1-post-mvp-risk-backlog-and-roadmap.md`
  - Responsibility: keep this implementation plan current while executing.

Do not modify:

- `utility/strategy.db`
- `utility/ai_agent/WideV1Final_B_20260425.py`
- `backtest/graph/`
- `backtest/temp/`
- `backtest/csv/`
- `cli/` code
- tests

---

### Task 1: Create The Wide v1 Post-MVP Roadmap

**Files:**
- Create: `docs/research/condition_research/mvp/2026-04-26_wide_v1_post_mvp_roadmap.md`

- [ ] **Step 1: Write the roadmap document**

Create `docs/research/condition_research/mvp/2026-04-26_wide_v1_post_mvp_roadmap.md` with this exact content:

```markdown
# Wide v1 post-MVP roadmap

## Purpose

이 문서는 Wide v1 MVP freeze 이후 프로젝트 방향을 고정한다.

최종 목표는 단일 백테스트에서 좋아 보이는 조건식을 하나 찾는 것이 아니라, 백테스트 결과를 기반으로 조건식을 자동 개선하는 시스템을 구현하는 것이다.

```text
기준 조건식
-> 백테스트
-> 결과 기록
-> 데이터/퀀트 분석
-> 개선 후보 조건식 생성
-> 후보별 백테스트
-> 후보 ranking
-> best_candidate 선택
-> 반복 개선
-> 최종 후보 선택
-> 마지막 WFO 검증
-> freeze 또는 재연구
```

## Current baseline

- branch=feature/wide-v1-post-mvp-risk-backlog
- base_branch=STOM_Version_2U_C
- base_commit=9c4ad20d
- base_commit_title=Wide v1 MVP freeze 및 운영 재현 문서화

## Wide v1 frozen candidate

- final_buy_strategy=WideV1Final_B_20260425
- base_buy_strategy=WideV1IterationV2_20260423__cand005
- sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419
- primary_candidate=WideV1IterationV5ObservableFull_20260425__cand017
- primary_expression=66.999 <= 시가총액 < 2_580 and 등락율 > 4.83
- source_candidate_csv=backtest/csv\stock_bt_WideV1IterationV5ObservableFull_20260425__cand017_20260425125216.csv

## Wide v1 completed scope

```text
1. 백테스트 CSV 분석
2. 후보 조건식 생성
3. 단일 후보 전략 생성/백테스트
4. 후보 백테스트 runtime 안정화
5. discovery research에서 WFO 제거 및 역할 분리
6. 후보 N개 1라운드 백테스트/ranking
7. 거래 유지율 기반 후보 선별
8. row-level 후보 차이 분석
9. score baseline 비교 가능성 보강
10. v3 후보 생성 규칙과 candidate_count=10 실행
11. v4 proxy row-set 다양성 보강
12. v5 actual row-set 대표 후보 선택
13. cand017 영구 전략 WideV1Final_B_20260425 재생성
14. runtime-preflight 통과
15. WFO 8개 window 검증 통과
16. MVP freeze 및 운영 재현 문서화
```

## Wide v1 WFO evidence

- round_count=8
- success_count=8
- success_rate=1.0
- metric=tpi
- mean_oos_metric=0.5762499999999999
- best_oos_metric=0.68
- mean_trade_count=2131.75
- zero_trade_rounds=0
- balanced_preset=pass
- conservative_preset=pass

## Wide v1 did not complete

Wide v1은 자동 조건식 개선 시스템의 MVP 후보를 만든 단계다. 다음 기능은 아직 최종 구현이 아니다.

```text
1. best_candidate를 다음 라운드 baseline으로 자동 승격
2. 여러 라운드 반복 실행
3. 라운드별 leaderboard 누적
4. 개선 정체 시 자동 종료
5. tighten/loosen/add/remove/replace 조건식 변형 정책
6. 최종 후보만 WFO에 넘기는 optimizer-level workflow
7. Wide v2 전용 리포트와 재현 명령어
```

## WFO role

WFO는 조건식 생성 도구가 아니라 최종 검증 도구다.

```text
discovery research:
  빠른 조건식 연구, 후보 생성, 후보 백테스트, ranking

discovery promote / cli.wfo / auto_discovery:
  최종 후보 검증, OOS 안정성 확인
```

따라서 다음 조건식 개선 개발에서도 WFO는 매 후보마다 실행하지 않는다. 백테스트 반복으로 최종 후보를 고른 뒤 마지막에만 WFO를 실행한다.

## Why this branch exists before Wide v2

이 브랜치는 운영 투입을 바로 시작하기 위한 브랜치가 아니다. Wide v1을 닫고, 다음 Wide v2 조건식 자동 개선 시스템 개발 전에 다음 기준을 고정하기 위한 브랜치다.

```text
1. Wide v1 freeze가 의미하는 것과 의미하지 않는 것을 기록한다.
2. WFO 통과를 실거래 수익 보장으로 오해하지 않게 한다.
3. 운영 위험과 조건식 연구 개발을 분리한다.
4. v6가 아니라 Wide v2로 새 연구 사이클을 여는 이유를 기록한다.
5. 다음 PR에서 자동 반복 개선 루프 설계를 시작할 수 있게 한다.
```

## Why Wide v2, not v6

v6는 v5가 실패했을 때 필요한 최소 보강 단계였다.

```text
v5 actual row-set 검증 성공:
  promote/WFO 진행

v5 actual row-set 대표 후보 부족:
  v6 후보 생성 확장

v5 runtime 실패:
  runtime recovery
```

실제 Wide v1은 v5 검증을 통과했고 WFO까지 완료했다. 따라서 다음 조건식 개선 개발은 v5 실패 보강인 v6가 아니라 Wide v2 자동 조건식 개선 루프로 시작한다.

## Remaining development flow

```text
[현재 PR]
Wide v1 post-MVP risk backlog
  - v1 완료 상태 정리
  - 위험 목록 정리
  - 운영 파일럿 체크리스트 정리
  - Wide v2 다음 명령 고정

[다음 PR]
Wide v2 백테스트 반복 기반 조건식 자동 개선 루프 설계
  - best_candidate -> next baseline
  - multi-round runner
  - leaderboard
  - stop condition
  - final candidate selection
  - WFO deferred validation

[후속 PR들]
Wide v2 구현
  - round state
  - candidate generation policy
  - automated backtest loop
  - result accumulation
  - ranking/reporting
  - final candidate freeze candidate

[마지막 검증]
Final WFO
  - 최종 후보만 WFO 실행
  - 통과 시 freeze
  - 실패 시 failure analysis 후 새 연구 cycle 판단
```

## Next command

현재 PR을 완료한 뒤 다음 조건식 개선 작업은 아래 명령으로 시작한다.

```text
$brainstorming Wide v2 백테스트 반복 기반 조건식 자동 개선 루프 설계
```
```

- [ ] **Step 2: Verify the roadmap document contains the key anchors**

Run:

```powershell
Select-String -Path docs\research\condition_research\mvp\2026-04-26_wide_v1_post_mvp_roadmap.md -Pattern "WideV1Final_B_20260425|WFO는 조건식 생성 도구가 아니라 최종 검증 도구|Wide v2 백테스트 반복 기반 조건식 자동 개선 루프"
```

Expected:

```text
WideV1Final_B_20260425
WFO는 조건식 생성 도구가 아니라 최종 검증 도구
Wide v2 백테스트 반복 기반 조건식 자동 개선 루프
```

- [ ] **Step 3: Commit the roadmap**

Run:

```powershell
git add docs/research/condition_research/mvp/2026-04-26_wide_v1_post_mvp_roadmap.md
git commit -m "Wide v1 이후 조건식 개선 로드맵을 기록한다" -m "Wide v1 freeze 이후 post-MVP 정리와 Wide v2 자동 조건식 개선 루프가 섞이지 않도록 전체 개발 흐름을 문서화한다." -m "Constraint: 이번 커밋은 문서 전용 변경이다`nRejected: v6를 다음 기본 단계로 기록 | v5가 통과했으므로 v6는 실패 보강 분기다`nConfidence: high`nScope-risk: narrow`nTested: Select-String key anchors`nNot-tested: 문서 변경만 포함하므로 unit test는 실행하지 않았다"
```

Expected:

```text
[feature/wide-v1-post-mvp-risk-backlog <hash>] Wide v1 이후 조건식 개선 로드맵을 기록한다
```

---

### Task 2: Create The Post-MVP Risk Backlog And Live-Pilot Checklist

**Files:**
- Create: `docs/research/condition_research/mvp/2026-04-26_wide_v1_post_mvp_risk_backlog.md`

- [ ] **Step 1: Write the risk backlog document**

Create `docs/research/condition_research/mvp/2026-04-26_wide_v1_post_mvp_risk_backlog.md` with this exact content:

```markdown
# Wide v1 post-MVP risk backlog

## Purpose

이 문서는 `WideV1Final_B_20260425`가 Wide v1 MVP 후보로 freeze된 이후 남아 있는 위험을 기록한다.

이 문서는 조건식 개선 개발을 중단하기 위한 문서가 아니다. Wide v1 결과를 과대 해석하지 않고, 다음 Wide v2 자동 조건식 개선 작업과 운영/실거래 위험 관리를 분리하기 위한 문서다.

## Frozen candidate

- final_buy_strategy=WideV1Final_B_20260425
- primary_candidate=WideV1IterationV5ObservableFull_20260425__cand017
- primary_expression=66.999 <= 시가총액 < 2_580 and 등락율 > 4.83
- sell_strategy=ResearchTest_Tick_S_090000_092800_Wide_20260419

## What WFO pass means

WFO 통과는 다음 의미를 가진다.

```text
1. 최종 후보가 단일 전체기간 백테스트에만 의존하지 않았다.
2. 여러 forward validation window에서 성능 기준을 통과했다.
3. zero-trade window 없이 검증 구간마다 거래가 발생했다.
4. Wide v1 MVP 후보로 freeze할 근거가 있다.
```

Wide v1 WFO 요약:

- round_count=8
- success_rate=1.0
- mean_oos_metric=0.5762499999999999
- mean_trade_count=2131.75
- zero_trade_rounds=0
- balanced_preset=pass
- conservative_preset=pass

## What WFO pass does not mean

WFO 통과는 다음을 보장하지 않는다.

```text
1. 실거래 수익 보장
2. 슬리피지 없는 체결
3. 호가 잔량과 주문 우선순위 반영
4. 장중 네트워크/API 장애 대응
5. 주문 실패나 부분 체결 처리 안전성
6. 미래 시장 구조 변화 대응
7. 모든 기간에서 항상 수익
```

따라서 Wide v1 freeze는 연구 MVP 성공이지 live trading release 승인이 아니다.

## Risk backlog

| Area | Risk | Required before live use | Status |
| --- | --- | --- | --- |
| Slippage | 백테스트 체결가와 실제 체결가 차이 | 백테스트 예측 체결가와 paper/live 체결가 비교 표준화 | Open |
| Fill quality | 호가 잔량, 주문 우선순위, 부분 체결 미반영 | 주문 체결 로그와 미체결 로그 수집 | Open |
| Broker/API runtime | Kiwoom/API 장애, 지연, disconnect | 장애 감지와 중지 조건 확인 | Open |
| Network | 장중 네트워크 장애 | 재접속/중지 절차 문서화 | Open |
| Cash guard | 예수금 부족 또는 주문 크기 오류 | 주문 전 예수금, 종목당 금액, 일일 총액 guard 확인 | Open |
| Symbol concentration | 특정 종목 집중 | 종목별/일자별 집중도 live report 작성 | Open |
| Daily stop | 하루 손실 확대 | 일일 손실/연속 실패 중지 조건 정의 | Open |
| Rollback | 문제 발생 시 전략 중지 지연 | 전략 disable/rollback 절차 작성 | Open |
| Logging | 실거래와 백테스트 비교 근거 부족 | 장 종료 후 비교 템플릿 작성 | Open |
| Research continuity | 운영 검증과 조건식 개선 개발 혼동 | Wide v2 연구 브랜치를 별도로 시작 | Open |

## Paper or live pilot checklist

실거래 또는 paper pilot 전에 아래 항목을 별도 PR에서 닫아야 한다.

- [ ] pilot 기간 정의
- [ ] pilot 대상 계좌 또는 paper 환경 정의
- [ ] 주문 금액 상한 정의
- [ ] 종목당 최대 노출 정의
- [ ] 일일 최대 손실 중지 조건 정의
- [ ] 주문 실패 시 행동 정의
- [ ] 미체결 시 행동 정의
- [ ] 장중 API 장애 시 행동 정의
- [ ] 장 종료 후 거래 로그 저장 위치 정의
- [ ] 장 종료 후 백테스트 예측과 실제 체결 비교 템플릿 작성
- [ ] pilot 중단 기준 정의
- [ ] rollback/disable 명령어 문서화

## Condition optimizer continuation

운영 위험 정리는 Wide v2 조건식 개선 개발을 막지 않는다.

다음 조건식 개선 작업은 아래처럼 별도 연구 사이클로 진행한다.

```text
WideV1Final_B_20260425 또는 별도 기준 조건식
-> 백테스트
-> 결과 분석
-> 후보 조건식 생성
-> 후보 N개 백테스트
-> best_candidate 선택
-> 다음 baseline으로 승격
-> 여러 라운드 반복
-> 최종 후보만 WFO
```

## Stop conditions

- WFO 통과만으로 실거래 수익을 보장한다고 표현하지 않는다.
- Wide v1 WFO 결과를 덮어쓰지 않는다. 재실행이 필요하면 새 브랜치와 새 PR에서 수행한다.
- `STOM_Version_2U_C`에 직접 커밋하지 않는다.
- 신규 조건식 자동 개선은 Wide v2 브랜치에서 진행한다.

## Next command

```text
$brainstorming Wide v2 백테스트 반복 기반 조건식 자동 개선 루프 설계
```
```

- [ ] **Step 2: Verify the risk backlog document contains the key risk claims**

Run:

```powershell
Select-String -Path docs\research\condition_research\mvp\2026-04-26_wide_v1_post_mvp_risk_backlog.md -Pattern "실거래 수익 보장|Slippage|rollback|Wide v2 백테스트 반복 기반 조건식 자동 개선 루프"
```

Expected:

```text
실거래 수익 보장
Slippage
rollback
Wide v2 백테스트 반복 기반 조건식 자동 개선 루프
```

- [ ] **Step 3: Commit the risk backlog**

Run:

```powershell
git add docs/research/condition_research/mvp/2026-04-26_wide_v1_post_mvp_risk_backlog.md
git commit -m "Wide v1 post-MVP 위험 목록을 고정한다" -m "WideV1Final_B_20260425의 WFO 통과 의미와 한계를 분리하고, 실거래 전 확인해야 할 운영 위험과 파일럿 체크리스트를 문서화한다." -m "Constraint: WFO 통과는 live profitability proof가 아니다`nRejected: 운영 위험 문서를 생략하고 Wide v2로 바로 이동 | freeze 후보의 의미가 과대 해석될 수 있다`nConfidence: high`nScope-risk: narrow`nTested: Select-String key risk claims`nNot-tested: 문서 변경만 포함하므로 unit test는 실행하지 않았다"
```

Expected:

```text
[feature/wide-v1-post-mvp-risk-backlog <hash>] Wide v1 post-MVP 위험 목록을 고정한다
```

---

### Task 3: Create The Korean PR Report

**Files:**
- Create: `docs/pr/2026-04-26_wide_v1_post_mvp_risk_backlog_pr.md`

- [ ] **Step 1: Write the PR report**

Create `docs/pr/2026-04-26_wide_v1_post_mvp_risk_backlog_pr.md` with this exact content:

```markdown
# Wide v1 post-MVP risk backlog 및 향후 조건식 개선 로드맵 PR

## 목적

Wide v1 MVP freeze 이후 방향성을 잃지 않도록, `WideV1Final_B_20260425`의 의미와 한계를 정리하고 다음 조건식 자동 개선 개발 흐름을 고정한다.

이번 PR은 신규 조건식 구현 PR이 아니다. Wide v1을 닫고 Wide v2 자동 조건식 개선 루프로 넘어가기 위한 post-MVP 정리 PR이다.

## 전체 개발 흐름

```text
Wide v1
  백테스트 CSV 분석
  -> 후보 조건식 생성
  -> 후보 N개 백테스트
  -> ranking
  -> row-set 중복 제거
  -> cand017 선택
  -> WideV1Final_B_20260425 생성
  -> WFO 검증
  -> MVP freeze

현재 PR
  post-MVP roadmap
  -> risk backlog
  -> 운영 파일럿 체크리스트
  -> Wide v2 다음 명령 고정

다음 PR
  Wide v2 백테스트 반복 기반 조건식 자동 개선 루프 설계
```

## 변경 사항

- Wide v1 post-MVP roadmap 문서 추가
- Wide v1 post-MVP risk backlog 및 운영 파일럿 체크리스트 추가
- Wide v2 조건식 자동 개선 루프의 다음 명령 고정

## Wide v1 freeze 근거

- final_buy_strategy=`WideV1Final_B_20260425`
- primary_candidate=`WideV1IterationV5ObservableFull_20260425__cand017`
- primary_expression=`66.999 <= 시가총액 < 2_580 and 등락율 > 4.83`
- WFO `round_count=8`
- WFO `success_rate=1.0`
- WFO `mean_oos_metric=0.5762499999999999`
- WFO `mean_trade_count=2131.75`
- WFO `zero_trade_rounds=0`
- balanced preset 통과
- conservative preset 통과

## 중요한 판단

### WFO는 최종 검증 단계다

`discovery research`는 빠른 후보 생성/백테스트/ranking 루프로 유지한다. WFO는 최종 후보가 선택된 뒤 `discovery promote`, `cli.wfo`, `auto_discovery` 계층에서 수행한다.

### v6가 아니라 Wide v2가 다음 조건식 개선 단계다

v6는 v5 actual row-set 검증이 부족할 때 필요한 보강 분기였다. 실제로 v5는 통과했고 promote/WFO까지 완료했다. 따라서 추가 조건식 개선은 Wide v2 자동 반복 개선 루프로 새로 시작한다.

### WFO 통과는 실거래 수익 보장이 아니다

이번 문서는 실거래 전 위험을 닫는 문서가 아니라, 남은 위험을 명확히 드러내는 문서다.

## 변경 파일

- `docs/superpowers/specs/2026-04-26-wide-v1-post-mvp-roadmap-and-risk-backlog-design.md`
- `docs/superpowers/plans/2026-04-26-wide-v1-post-mvp-risk-backlog-and-roadmap.md`
- `docs/research/condition_research/mvp/2026-04-26_wide_v1_post_mvp_roadmap.md`
- `docs/research/condition_research/mvp/2026-04-26_wide_v1_post_mvp_risk_backlog.md`
- `docs/pr/2026-04-26_wide_v1_post_mvp_risk_backlog_pr.md`

## 검증

- `Select-String`으로 roadmap 핵심 문구 확인
- `Select-String`으로 risk backlog 핵심 문구 확인
- `git diff --check --ignore-cr-at-eol`

## 남은 위험

- 운영 파일럿 체크리스트 항목은 아직 닫힌 것이 아니라 Open 상태로 기록했다.
- Wide v2 자동 반복 개선 루프는 이번 PR에서 구현하지 않는다.
- 신규 백테스트나 WFO 재실행은 이번 PR 범위가 아니다.

## 다음 단계

```text
$brainstorming Wide v2 백테스트 반복 기반 조건식 자동 개선 루프 설계
```
```

- [ ] **Step 2: Verify the PR report contains the next command and changed files**

Run:

```powershell
Select-String -Path docs\pr\2026-04-26_wide_v1_post_mvp_risk_backlog_pr.md -Pattern "Wide v2 백테스트 반복 기반 조건식 자동 개선 루프|변경 파일|git diff --check"
```

Expected:

```text
Wide v2 백테스트 반복 기반 조건식 자동 개선 루프
변경 파일
git diff --check
```

- [ ] **Step 3: Commit the PR report**

Run:

```powershell
git add docs/pr/2026-04-26_wide_v1_post_mvp_risk_backlog_pr.md
git commit -m "Wide v1 post-MVP PR 보고서를 작성한다" -m "post-MVP roadmap과 risk backlog 문서를 설명하는 한글 PR 본문을 추가하고, 다음 Wide v2 조건식 자동 개선 루프 설계 명령을 고정한다." -m "Constraint: PR 본문은 문서 변경의 범위와 다음 명령만 설명한다`nRejected: 구현 완료처럼 표현 | Wide v2 optimizer는 다음 PR에서 설계한다`nConfidence: high`nScope-risk: narrow`nTested: Select-String PR report anchors`nNot-tested: 문서 변경만 포함하므로 unit test는 실행하지 않았다"
```

Expected:

```text
[feature/wide-v1-post-mvp-risk-backlog <hash>] Wide v1 post-MVP PR 보고서를 작성한다
```

---

### Task 4: Final Verification And Handoff

**Files:**
- Verify: `docs/research/condition_research/mvp/2026-04-26_wide_v1_post_mvp_roadmap.md`
- Verify: `docs/research/condition_research/mvp/2026-04-26_wide_v1_post_mvp_risk_backlog.md`
- Verify: `docs/pr/2026-04-26_wide_v1_post_mvp_risk_backlog_pr.md`

- [ ] **Step 1: Run whitespace verification**

Run:

```powershell
git diff --check --ignore-cr-at-eol
```

Expected:

```text
<no output>
```

- [ ] **Step 2: Confirm only expected tracked documentation changed since base**

Run:

```powershell
git diff --name-only STOM_Version_2U_C...HEAD
```

Expected output contains these files:

```text
docs/superpowers/specs/2026-04-26-wide-v1-post-mvp-roadmap-and-risk-backlog-design.md
docs/superpowers/plans/2026-04-26-wide-v1-post-mvp-risk-backlog-and-roadmap.md
docs/research/condition_research/mvp/2026-04-26_wide_v1_post_mvp_roadmap.md
docs/research/condition_research/mvp/2026-04-26_wide_v1_post_mvp_risk_backlog.md
docs/pr/2026-04-26_wide_v1_post_mvp_risk_backlog_pr.md
```

- [ ] **Step 3: Check untracked runtime artifacts are not staged**

Run:

```powershell
git status --short
```

Expected:

```text
?? backtest/graph/
```

If `git status --short` shows staged files under `backtest/graph/`, `backtest/temp/`, or `backtest/csv/`, unstage them before continuing:

```powershell
git restore --staged backtest/graph/ backtest/temp/ backtest/csv/
```

- [ ] **Step 4: Confirm no unexpected unstaged documentation changes remain**

Run:

```powershell
git status --short
```

Expected:

```text
?? backtest/graph/
```

- [ ] **Step 5: Report the next implementation command**

Report:

```text
다음 실행 단계는 이 계획을 실행해 post-MVP roadmap, risk backlog, PR 보고서를 작성하는 것입니다.

실행 완료 후 다음 연구 명령은:
$brainstorming Wide v2 백테스트 반복 기반 조건식 자동 개선 루프 설계
```

---

## Self-Review

Spec coverage:

- Whole condition-improvement roadmap: Task 1.
- Wide v1 completion and incomplete scope: Task 1.
- WFO final-validation role: Task 1 and Task 2.
- Post-MVP risk backlog and live-pilot checklist: Task 2.
- PR/branch direction and next Wide v2 command: Task 3.
- Verification and no runtime artifact staging: Task 4.

Placeholder scan:

- No placeholder markers or unspecified implementation placeholders are intentionally left.

Type and name consistency:

- Strategy names match the approved spec:
  - `WideV1Final_B_20260425`
  - `WideV1IterationV5ObservableFull_20260425__cand017`
  - `ResearchTest_Tick_S_090000_092800_Wide_20260419`
- Next command is consistently:
  - `$brainstorming Wide v2 백테스트 반복 기반 조건식 자동 개선 루프 설계`
