# Process Research Pipeline 재출발 · 대시보드/연구 성숙화 마스터플랜 (2026-08-24)

> 상태: **재출발 계획 정본**
>
> 통합 기준: `loop/process-research-pipeline` @ `f75b80ebcb7fd72cd41c8933c4f6e63df8c2ae52`
>
> 연구 브랜치: `codex/process-research-pipeline-restart`
>
> 선행 연구 HEAD: `research/v516-d3-mcap-dev` @ `97a59ad311e3af7555ecb7e86fda69e8e6667461`
>
> 문서 성격: 이 문서는 개발 성공, 연구 성공, OOS 성공, 운영 승격을 서로 다른 상태로 관리한다.

> **2026-08-26 실행 갱신:** BOOT-01부터 RES-01까지 완료했고, RES-02 런타임 사전점검과 성과 비사용 Event Gate도 통과했다. 160개 중 Event 하한 통과 24개, 사전등록 maximin 선택 7개를 봉인했다. 현재 다음 단위는 별도 브랜치의 **7후보 × 4Fold = 28개 공식 G0 job 실행**이다. 경제성은 아직 `NOT_EVALUATED`, holdout은 `SEALED_NOT_TOUCHED`다.

---

## 0. 결론부터

| 질문 | 결론 | 이유 |
|---|---|---|
| 직접 사용하면서 하나씩 고치는 것이 좋은가 | **예. 단, 임의 페이지 순회가 아니라 작은 종단 슬라이스로 진행한다.** | 화면만 고치면 실제 연구 흐름이 검증되지 않고, 연구만 돌리면 실패 원인이 다시 흩어진다. 한 번에 `실행 → 결과 번들 → 분석 → 다음 행동`을 완성해야 한다. |
| 현재 프로젝트는 실패한 것인가 | **경제적 연구는 아직 성공하지 못했다. 플랫폼은 상당 부분 구현됐지만 반복 연구는 미완료다.** | Robust 후보 0개, OOS 미검증, 자동채택 금지다. 동시에 Census·시드·공식엔진 연결·분석 자산은 재사용 가능하다. |
| 백테스트 후 결과 분석을 더 고도화할 수 있는가 | **가능성이 높다.** | 이미 다수 분석 API와 화면이 존재한다. 새로 처음 만드는 것보다 흩어진 분석을 하나의 불변 결과 번들과 결정 화면으로 묶는 일이 핵심이다. |
| 지금 가장 먼저 할 일 | **`<3000` Band 10건의 error/timeout/무거래/metrics를 원인별로 재분류하고, 결과 권위와 다음 허용 행동을 화면 상단에 고정한다.** | 실행 실패를 경제 실패와 섞지 않아야 다음 연구가 정직해진다. |
| D4/BO를 바로 시작할 수 있는가 | **아니다.** | 실제 Controls, 다기간 fold, posterior를 통과한 `BO_ELIGIBLE` Cell이 0개다. |
| 대시보드 리디자인부터 크게 할 것인가 | **아니다.** | 첫 종단 슬라이스에서 실제 데이터로 사용성 문제를 확인한 뒤 정보구조를 단계적으로 바꾼다. |

### 권장 방식

```text
정본/권위 고정
→ <3000 실행 실패 부검
→ 백테스트 결과 번들 v2
→ 결과 개요/다음 행동 화면
→ <3000 G0 다기간 개발 실행
→ 구조 부검과 G1 생성
→ 같은 계약으로 재실행
→ 직접 사용성 검증
→ 나머지 Band 확장
```

---

## 1. 통합 사실과 현재 판정

### 1.1 Git 통합 사실

| 항목 | 값 | 판정 |
|---|---|---|
| 원격 파이프라인 기준 | `origin/loop/process-research-pipeline` @ `1add7f85` | 현재 연구 HEAD의 조상 |
| 통합한 연구 | `research/v516-d3-mcap-dev` @ `97a59ad` | 원격 파이프라인보다 47커밋 앞섬 |
| 통합 커밋 | `f75b80eb` | 부모: `1add7f85` + `97a59ad` |
| 재출발 브랜치 | `codex/process-research-pipeline-restart` | `f75b80eb`에서 생성 |
| 원 작업 폴더 | `STOM_V.wt-dev` | 기존 삭제·미추적 파일을 건드리지 않음 |
| 재출발 worktree | `C:\System_Trading\STOM\STOM_V.wt-process-research-restart` | 연구 재개 전용 |

### 1.2 실제 연구 상태

| 구분 | 관측 사실 | 성공 여부 |
|---|---|---|
| 데이터 Census | 시총 4Band 모두 Population 연구 가능 | **개발 기반 성공** |
| D3 시드 생성 | 5Family × 4Band × QMC32 = 640, 성과 비사용 최대거리 40 선택 | **생성 계약 성공** |
| 공식엔진 screen | 2023-11-14 단 하루, 40건 실행 | **feasibility만 수행** |
| 실행 결과 | metrics 2, no-trades 21, error 15, timeout 2 | **17건 실행 실패 미해결** |
| 양성 후보 | 선택된 40개 초기 시드에서 양성 후보 없음 | **경제적 실패/불충분** |
| Band 반복 개선 | `생성 → 다기간 백테스트 → 분석 → 구조 개선 → 재실행` | **미실행** |
| Negative controls | 계약은 있으나 실제 Evidence 없음 | **미실행** |
| Nested folds·통계 | 실제 fold/FDR/posterior 없음 | **미실행** |
| D4 Native 최적화 | `BO_ELIGIBLE` 0 | **정상 중지** |
| Frozen OOS | 미개봉/미검증 | **주장 불가** |
| 실전·자동채택 | 수행하지 않음 | **권한 없음** |

### 1.3 성공 용어를 네 단계로 분리한다

| 상태 | 의미 | 현재 |
|---|---|---|
| 구현 성공 | 코드·API·화면·테스트가 계약대로 동작 | 일부 영역 성공 |
| 연구 실행 성공 | 사전등록한 후보가 공식엔진에서 유효 결과로 완주 | D3 40건 중 23 terminal 비실패, 17 실패 |
| 경제적 연구 성공 | 다기간 development에서 사전 기준을 통과 | 0개 |
| 일반화/운영 성공 | frozen OOS와 인간 승인을 통과 | 미검증 |

---

## 2. 왜 많이 만들었는데도 성공하지 못했는가

| 근본 원인 | 과거 증상 | 이번 구조적 교정 |
|---|---|---|
| 완료 단위 치환 | API·UI·문서·terminal 행 수를 연구 완료로 계산 | 대시보드에 `플랫폼 진행률`과 `연구 진행률`을 별도 표시 |
| 1일 screen 과대해석 | 실행 가능성 확인을 Band 연구 결론으로 표현 | 권위 배지에 `FEASIBILITY / DEVELOPMENT / OOS / LIVE` 고정 |
| 실패 terminal 오집계 | error/timeout도 완료 행으로 포함 | 실행 완전성 카드에서 성공·무거래·오류·타임아웃을 분리 |
| 다음 행동 부재 | 화면은 많지만 무엇을 해야 하는지 불명확 | 모든 핵심 페이지에 `다음 허용 행동` 1개와 차단 사유 표시 |
| 분석 파편화 | 차트/API는 많으나 하나의 판정 패킷이 없음 | `AnalysisBundle v2`를 job/generation의 불변 산출물로 정의 |
| 조건식 개선 루프 미실행 | 초기 시드를 탈락시킨 뒤 구조 개선 세대가 없음 | G0 부검 → 구조 가설 → G1 → 동일 기준 비교를 필수 단위로 설정 |
| 결과 후 미세조정 위험 | 실패 주변 threshold를 계속 만질 유혹 | 변경 유형을 `구조 변경`과 `금지된 미세조정`으로 분류 |
| 현재와 과거 권위 충돌 | 과거 양수 후보/HOF가 최신 Robust 0보다 강하게 보임 | 최신 판정과 역사 기록을 UI에서 시각적으로 분리 |

---

## 3. 작업 원칙: 작은 수정이 아니라 작은 종단 슬라이스

### 3.1 한 종단 슬라이스의 완료 조건

| 단계 | 반드시 남길 것 |
|---|---|
| 입력 | 사전등록 ID, 데이터/기간/비용/후보 hash |
| 실행 | 공식 job ID, source snapshot, 상태·진행·로그 |
| 결과 | success/no-trades/error/timeout/cancelled 구분 |
| 분석 | 분포·안정성·에피소드·진입/청산·비용·강건성 |
| 판정 | 경제 판정과 권위 수준 |
| 다음 행동 | debug/rerun/revise/expand/stop/holdout 중 정확히 하나 |
| 증거 | 불변 bundle hash, 문서, 재현 명령 |

### 3.2 하지 않을 방식

| 금지 방식 | 이유 |
|---|---|
| 화면 전체를 한 번에 리디자인 | 실제 데이터 없이 정보구조를 추측하게 됨 |
| 차트를 계속 추가 | 차트 수가 의사결정 품질을 보장하지 않음 |
| error/timeout을 제외하고 좋은 결과만 분석 | 실행 편향과 선택 편향 발생 |
| 결과를 본 뒤 Band·기간·threshold 변경 | 사후 최적화 |
| development 양수를 OOS 또는 실전 성공으로 표시 | 권위 혼동 |
| 분석 추천을 자동으로 strategy DB에 저장 | 연구/운영 경계 위반 |

---

## 4. 성숙도 모델

> 아래 점수는 테스트 통과율이 아니라 2026-08-24 코드·문서·직접 사용 감사에 따른 설계 판단이다.

### 4.1 대시보드 성숙도

| 차원 | 현재(5점) | 근거 | 1차 목표 |
|---|---:|---|---:|
| 시각 완성도 | 4 | 일관된 다크 테마·카드·차트·다수 화면 | 4 |
| 데이터 연결성 | 3 | 공식 job, generation, reports, replay 연결 | 4 |
| 상태의 진실성 | 2 | 과거 HOF·오래된 live·현재 Robust 0의 우선순위 충돌 | 4 |
| 다음 행동 안내 | 2 | 페이지는 많지만 현재 허용 행동이 한곳에 없음 | 4 |
| 실패 복구성 | 2 | error/timeout 원인·재실행 계약이 흩어짐 | 4 |
| 증거/계보 | 3 | hash·문서·job 자산은 있으나 결정과 분리 | 4 |
| 백테스트 후 분석 | 3 | 분석 폭은 넓지만 결정 번들·페이지 계층 부족 | 4 |
| 접근성/반응형 | 3 | ARIA·키보드 일부 존재, 긴 스크롤과 상태 보존 문제 | 4 |
| 실제 운영 증명 | 2 | 로컬 사용 증거는 있으나 설치/장시간/복구 QA가 제한적 | 3 |

### 4.2 연구 성숙도

| 단계 | 정의 | 현재 |
|---|---|---|
| R0 임의 실험 | 결과를 보고 다음 조건을 즉석 변경 | 과거 위험 존재 |
| R1 결정론 실행 | 같은 입력·source로 공식엔진 재현 | 부분 달성 |
| R2 사전등록 개발 | 기간·비용·후보·중지 기준을 실행 전에 봉인 | 계약은 있으나 D3 반복에는 미완료 |
| R3 강건성 검정 | 다기간 folds·controls·FDR·posterior | 미실행 |
| R4 Frozen OOS | 개발과 격리된 확인구간 1회 평가 | 미실행 |
| R5 인간 승인/Shadow | 운영 권위자가 승격 여부 판정 | 미진입 |

### 4.3 이번 프로그램의 목표

| 기간 | 대시보드 목표 | 연구 목표 |
|---|---|---|
| 1차 종단 슬라이스 | D3: 진실한 상태 + 행동 유도 | R2: `<3000` G0/G1 사전등록 개발 |
| 4Band 완료 시 | D4: 증거 통합 결정 지원 | R3: folds·controls·posterior |
| 후보 생존 시 | D4 유지 | R4: Frozen OOS |
| 인간 승인 시만 | Shadow 운영 화면 | R5 |

---

## 5. 목표 정보 구조

### 5.1 현재 9개 탭의 문제

직접 사용 감사에서 `라이브` 페이지는 1280×720 기준 약 10화면 높이였고, 탭 이동 뒤 스크롤 위치가 의도와 다르게 남았다. 최신 재개 문서는 `보고서 → Wiki → 검색`을 거쳐야 했으며, `성과`는 과거 양수 후보를 현재 Robust 0 판정보다 강하게 보였다. 백테스트는 필수 입력이 비어 있어도 “실행 준비” 인상이 남았다. 콘솔 오류는 관측되지 않았으므로, 핵심 문제는 시각 품질보다 정보 권위와 동선이다.

### 5.2 제안 상위 내비게이션

| 상위 영역 | 포함 페이지 | 목적 |
|---|---|---|
| 오늘의 연구 | Mission Control, Program, 다음 행동 | 현재 상태를 30초 안에 이해 |
| 실행 | Queue, Backtest 설계, Job Health | 안전하고 재현 가능한 실행 |
| 결과 분석 | Overview, Stability, Episode, Entry, Exit, Counterfactual, Robustness, Cost | 결과를 원인과 행동으로 변환 |
| 비교·계보 | Generation Compare, Condition Diff, Lineage | 무엇이 왜 바뀌었는지 추적 |
| 증거 | History, Decision, Reports/Wiki | 감사·재현·인간 승인 |
| 관리 | Research Assets, Settings, Glossary | 설정·자료·도움말 |

기존 deep link는 유지하되, 좌측 레일의 9개 동등 탭을 위 6개 목적 그룹으로 재구성한다.

### 5.3 모든 화면에 고정할 “연구 진실 바”

| 필드 | 예시 |
|---|---|
| 프로그램 | `v5.16 D3 MCap Restart` |
| 현재 단계 | `<3000 / failure triage` |
| 권위 | `DEVELOPMENT PRE-RUN` |
| 실행 완전성 | `2 metrics · 2 no-trades · 4 error · 2 timeout` |
| 경제 판정 | `INCONCLUSIVE / ROBUST 0` |
| Evidence 시각 | 마지막 bundle 생성 시각 + hash |
| 다음 허용 행동 | `오류 4건 원인 분류` |
| 차단 사유 | `다기간 사전등록 전 재백테스트 금지` |

이 바가 이번 UX의 가장 기억에 남는 요소이며, 색보다 텍스트·아이콘·상태 코드를 함께 쓴다.

---

## 6. 페이지별 상세 계획

### 6.1 핵심 페이지

| 페이지 | 레인 | 사용자가 답할 질문 | 반드시 보여줄 것 | 주 행동 | 완료 기준 |
|---|---|---|---|---|---|
| Mission Control | UX+시스템 | 지금 무엇이 사실이고 무엇을 해야 하나 | 진실 바, 플랫폼/연구 진행률, 최근 실패, 다음 행동 | 다음 허용 작업 열기 | 30초 내 현재 단계·권위·차단 사유 설명 가능 |
| Program | 시스템 | 전체 계획에서 어디까지 왔나 | Band×세대×단계 매트릭스, gate, prereg ID | 해당 단계 증거 보기 | 완료/실패/미진입이 별도 상태 |
| Queue & Job Health | 파이프라인 | 무엇이 실행 중이고 왜 멈췄나 | queue, manager/port/jobs dir, heartbeat, elapsed, checkpoint, cancel 권위 | 안전 재시도 준비 | error/timeout마다 typed 원인과 재시도 가능 여부 |
| Backtest 설계 | 시스템+연구 | 무엇을 어떤 권위로 실행하나 | 후보 hash, source, 기간, 비용, fold, engine, 사전등록 | 검증 후 실행 | 필수 입력 없으면 실행 불가, 예상 실행량 표시 |
| Result Overview | 분석 | 이 결과를 믿고 해석해도 되나 | identity, execution completeness, KPI, authority, economic verdict | 분석 시작/재현 | CSV 없는 축약 결과와 실제 거래 결과 명확 분리 |
| Stability | 분석+연구 | 성과가 시간·종목·레짐에 안정적인가 | daily/monthly/rolling, fold, segment, contribution concentration | 취약 구간 열기 | 최소 표본·불확실성·다중비교 상태 포함 |
| Episode Explorer | 분석 | 어떤 거래 경로에서 벌고 잃었나 | candle/tick path, entry/exit, MFE/MAE, giveback, context | Replay 열기 | 임의 top 거래가 아니라 cohort에서 drill-down |
| Entry Autopsy | 분석+연구 | 진입 edge가 어디서 생기거나 사라지나 | fired/reached/entered funnel, orderflow, feature map, loss pockets | 구조 가설 작성 | 미래 정보 없이 진입 시점 변수만 사용 |
| Exit Autopsy | 분석+연구 | 청산이 edge를 보존하거나 훼손했나 | exit reason, MFE→realized, time in trade, forced exit | 공식 pair 또는 advisory replay 선택 | official과 same-entry advisory를 시각 분리 |
| Counterfactual Lab | 분석 | 바꿨다면 어떻게 되었나 | baseline, counterfactual assumptions, matched/new/lost trades | 분석 제안 저장 | 채택 권한 없음, 가정·한계·source 표시 |
| Robustness & Controls | 연구 | 우연·과적합·누수를 견뎠나 | folds, negative controls, BH-FDR, posterior, plateau | gate 판정 | 미실행 항목은 0점이 아니라 NOT_RUN |
| Cost & Capacity | 분석+연구 | 비용·회전율·자본 제약 후에도 남는가 | fee/slippage scenarios, turnover, occupancy, concurrency | 비용 시나리오 비교 | gross/net 분리, 비용 가정 hash |
| Generation Compare | 연구 | 구조 변경이 실제로 개선했나 | parent/child AST diff, hypothesis, metrics delta, fold delta | G+1 판정 | 단순 threshold 미세조정 경고 |
| Decision & Evidence | 시스템 | 다음 단계로 가도 되는가 | bundle hash, gate matrix, 실패 이유, 재현 명령 | 승인 요청/중지 | development/OOS/live 권위 분리 |

### 6.2 기존 탭 보강

| 기존 탭 | 현재 강점 | 문제 | 보강 방향 |
|---|---|---|---|
| 라이브 | 실시간 단계·연구 Cockpit | 너무 길고 최신 행동이 묻힘 | 상단 Mission Control + 접힌 상세 섹션 |
| 기록 | run/gen 검색·비교 | 실행 상태와 경제 판정 혼재 | 상태 facet, authority facet, failure facet 추가 |
| 보고서 | HTML/Wiki 읽기 전용 | 최신 정본 발견 비용 큼 | “현재 정본” 고정 카드와 supersedes 링크 |
| 성과 | 인간/AI 비교 자산 | 과거 양수 후보가 최신 실패 판정을 압도 | “역사 성과”로 명시하고 현재 권위 경고 |
| 백테스트 | 편집·실행·결과 분석 폭이 넓음 | 설정과 분석이 한 페이지에 과밀 | 설계/실행과 결과 분석을 독립 페이지로 분리 |
| 리플레이 | 거래 맥락 확인 | 결과 cohort와 연결 약함 | Episode Explorer에서 정확한 trade key로 진입 |
| 연구 자산 | 풍부한 실험 자산 | preview와 정본 경계 이해 비용 | 자산마다 authority/owner/last verified 배지 |
| 설정 | 연결·표시 관리 | 연구 실행 설정과 혼동 가능 | UI 설정과 실행 정책 완전 분리 |
| 용어 | 지표 설명 | 현재 화면 맥락과 떨어짐 | 모든 핵심 지표에 inline 정의와 glossary deep link |

### 6.3 공통 상태 설계

| 상태 | UI 규칙 |
|---|---|
| loading | 마지막 성공 데이터 시각을 유지하고 “갱신 중” 표시 |
| empty | 왜 비었는지, 무엇을 해야 채워지는지 설명 |
| no-trades | 정상 terminal이지만 경제 표본 없음으로 표시 |
| error | 원인 분류·checkpoint·재시도 정책 표시 |
| timeout | 성능 문제인지 교착인지 구분 전까지 UNKNOWN_TIMEOUT |
| partial | 완료 KPI를 숨기고 분석 제한 표시 |
| stale | 최신 정본과 시간 차이를 상단 경고 |
| forbidden | 권한/사전등록/gate 중 어느 이유인지 명시 |

---

## 7. 백테스트 후 결과 분석 고도화 가능성

### 7.1 현재 자산

| 자산 | 현재 기능 | 재사용 가치 |
|---|---|---:|
| `backtest_analysis.py` | summary, equity, distribution, heatmap, underwater, insights, MAE/MFE, exit reason, 통계, orderflow, rolling, monthly, GUI parity, portfolio | 높음 |
| `backtest_api.py` | result, 분석 endpoints, Monte Carlo, feature/leaf, compare, overlay, portfolio, report | 높음 |
| `trade_path_api.py` | cohort, trade path, counterfactual, transition, proposal, recovery, buy filter, calibration, history/ledger | 높음 |
| `loss_region_api.py` | loss profile/pockets, removal simulation, region candidates, split diagnostics | 높음 |
| `analysis_snapshot.py` | 기존 CSV를 읽은 연구 분석 snapshot과 SQLite persistence | 중간~높음 |
| `analysis_card_api.py` | 분석 카드·손실 거래 요약 | 중간 |
| condition/response/ledger APIs | condition diff, response surface, trade pairs, transfer ledger | 높음 |
| `bt-result-area.jsx` | 결과 맥락·차트·전체화면·리플레이 연결 | 높음 |

### 7.2 현재 구조의 한계

| 한계 | 영향 | 개선 |
|---|---|---|
| `backtest_api.py` 2,578줄, `backtest_analysis.py` 2,138줄 | 변경 영향 범위와 검증 비용 증가 | identity/result/analysis/compare/report router와 domain 모듈로 분리 |
| `bt-result-area.jsx` 791줄 | 정보 우선순위와 상태 분기 복잡 | Overview/Stability/Episode/Decision 페이지로 분리 |
| CSV 존재 여부에 따라 기능 차이 | 축약 세대 결과를 실제 분석처럼 오해 | capability matrix를 결과 상단에 고정 |
| 분석 산출물이 요청 시 재계산됨 | 동일 결과 판정의 재현·감사 어려움 | immutable `AnalysisBundle v2` 생성 |
| execution failure와 경제 실패 분리 부족 | 잘못된 조건식 개선 방향 | Execution Diagnosis를 분석 앞단 gate로 배치 |
| advisory counterfactual과 official 비교가 흩어짐 | 반사실 결과 과대해석 | source/authority watermark와 별도 색상 |
| fold/control/cost/lineage가 한 판정 화면에 없음 | Robust 판단이 수동 | Decision Matrix로 통합 |

### 7.3 AnalysisBundle v2

각 공식 job 또는 generation은 아래 구조의 불변 번들을 갖는다.

| 영역 | 필드 |
|---|---|
| identity | bundle_version, job_id/run_id/gen_no, candidate_id, parent_id, code hash |
| source | strategy snapshot, back DB identity, CSV hash, engine version, git commit |
| preregistration | program, Band, Family, fold, 기간, 비용, seed, stop rule |
| execution | status, terminal reason, elapsed, heartbeat, checkpoint, row/trade counts |
| metrics | gross/net PnL, return, MDD, win rate, payoff, turnover, occupancy |
| series | equity, underwater, daily/monthly/rolling |
| distribution | pnl/holding/MFE/MAE/giveback/concentration |
| episodes | best/worst가 아닌 사전 정의 cohort와 trade keys |
| attribution | entry/exit/time/Band/Family/regime/cost contribution |
| counterfactual | method, assumptions, matched/new/lost, authority=ADVISORY/OFFICIAL |
| robustness | folds, controls, FDR, posterior, plateau, sample power |
| decision | execution verdict, economic verdict, authority, next allowed action |
| evidence | artifact paths, hashes, generated_at, generator version |

### 7.4 판정 상태 기계

| 축 | 허용 값 |
|---|---|
| 실행 | `SUCCESS` / `NO_TRADES` / `ERROR` / `TIMEOUT` / `CANCELLED` / `PARTIAL` |
| 경제 | `POSITIVE` / `NEGATIVE` / `INCONCLUSIVE` / `NOT_EVALUABLE` |
| 권위 | `FEASIBILITY` / `DEVELOPMENT` / `FROZEN_OOS` / `SHADOW` / `LIVE` |
| 다음 행동 | `DEBUG` / `REPRODUCE` / `STRUCTURAL_REVISE` / `EXPAND` / `STOP` / `HOLDOUT` |

서로 다른 축을 하나의 PASS/FAIL로 축약하지 않는다.

### 7.5 고도화 우선순위

| 순위 | 기능 | 이유 |
|---:|---|---|
| 1 | 결과 identity·execution completeness | 잘못된 데이터 분석을 먼저 차단 |
| 2 | immutable AnalysisBundle v2 | 모든 후속 화면과 연구의 단일 계약 |
| 3 | Decision Overview | 사용자가 결과를 행동으로 전환 |
| 4 | 시간/레짐/fold 안정성 | 단기 양수 과대해석 방지 |
| 5 | Entry/Exit attribution + Episode | 구조 개선 가설 생성 |
| 6 | 비용·capacity | 경제 가능성 현실화 |
| 7 | controls/FDR/posterior | Robust gate |
| 8 | counterfactual/AI 설명 | 앞선 증거를 소비하는 보조 기능 |

---

## 8. 제품·시스템 파이프라인 개선 단계

> 이 레인은 연구 결과가 양수인지와 무관하게 구현·검증할 수 있다.

| 단계 | 목적 | 산출물 | Gate |
|---|---|---|---|
| S0 정본 통합 | 분산된 연구 이력을 재출발 기준으로 고정 | 병합 커밋, 새 브랜치, 핸드오프 | **이번 작업 완료** |
| S1 Truth Contract | 플랫폼/연구/권위/다음 행동 분리 | typed status schema, API, truth bar | 상태 조합 테스트 + 빈/실패 UI |
| S2 Execution Diagnosis | error/timeout 원인 가시화 | failure taxonomy, checkpoint reader, retry policy | 10개 `<3000` job 모두 분류 |
| S3 AnalysisBundle v2 | 결과 정본화 | schema, builder, read API, hash | 같은 입력에서 동일 hash/내용 |
| S4 Result Decision UX | 분석 우선순위 재편 | Overview, capability, Decision Matrix | 실제 job 5상태 브라우저 QA |
| S5 Analysis Pages | 세부 부검을 목적별 페이지로 분리 | Stability/Episode/Entry/Exit/Cost | deep link와 cohort 일치 |
| S6 Lineage & Compare | 구조 변화와 결과 변화 연결 | AST diff, parent-child comparison | parent/child identity 불변 |
| S7 Evidence & Reports | 정본 발견·재현 강화 | current canonical card, supersedes graph | 2클릭 내 최신 판정 도달 |
| S8 Reliability | 장시간 실행·복구·관측성 | resume, manager isolation, stale detection | 강제 중단 후 안전 복구 QA |
| S9 Accessibility/Responsive | 실제 사용 완성 | keyboard, focus, 1280/1440 layouts | 주요 흐름 키보드 완료·콘솔 오류 0 |

### 8.1 코드 분해 방향

| 현재 파일 | 제안 분리 |
|---|---|
| `backtest_api.py` | `backtest_strategy_routes.py`, `backtest_job_routes.py`, `backtest_result_routes.py`, `backtest_analysis_routes.py`, `backtest_compare_routes.py`, `backtest_report_routes.py` |
| `backtest_analysis.py` | `analysis_summary.py`, `analysis_series.py`, `analysis_distribution.py`, `analysis_robustness.py`, `analysis_portfolio.py` |
| `bt-result-area.jsx` | `bt-result-overview.jsx`, `bt-stability-page.jsx`, `bt-episode-page.jsx`, `bt-decision-page.jsx` |
| `dashboard-v4-shell.jsx` | nav model, global truth bar, page router, shell controls 분리 |

분해는 별도 행동 변경 없이 회귀 테스트를 먼저 고정한 뒤 진행한다.

---

## 9. 연구 레인 단계

> 이 레인은 결과를 보기 전에 입력·기간·비용·후보·중지 규칙을 커밋해야 한다.

| 단계 | 연구 작업 | 산출물 | 진입/종료 Gate |
|---|---|---|---|
| R0 실패 부검 | `<3000` 10건 중 error4·timeout2·no-trades2·metrics2 분류 | failure ledger | PnL 비사용 교정만 허용 |
| R1 재현성 확인 | 교정 전/후 exact source 재실행 구분 | reproduction receipt | source hash·engine identity 일치 |
| R2 다기간 사전등록 | development 기간, fold, 비용, Event 하한, 반복/중지 규칙 봉인 | prereg 문서+manifest | 실행 전 커밋 필수 |
| R3 G0 Event 추정 | 5Family×32 원시 시드 Event 수 산출 | event evidence | 성과 비사용 하한 통과만 공식 실행 |
| R4 G0 공식 실행 | 통과 후보를 다기간 fold에서 실행 | AnalysisBundle v2 집합 | error/timeout은 별도 실패 |
| R5 구조 부검 | 거래/무거래/손실/오류를 Family별 분석 | falsifiable hypotheses | 미래 변수·결과 기반 threshold 금지 |
| R6 G1 생성 | 구조가 달라진 자식 후보 생성 | lineage + AST diff | parent/hypothesis 연결 |
| R7 G1 재실행 | G0와 같은 기간·비용·gate로 재실행 | paired generation comparison | 개선/퇴행/불충분 판정 |
| R8 반복/중지 | 사전등록 횟수 또는 정지 기준까지 반복 | generation ledger | 결과 후 횟수 연장 금지 |
| R9 Controls/Folds | negative controls, nested folds, BH-FDR, posterior | robustness bundle | BO_ELIGIBLE typed gate |
| R10 조건부 D4 | 적격 Cell만 Native 최적화 | trial ledger | 적격 0이면 정상 종료 |
| R11 Frozen OOS | 후보·코드·비용 봉인 후 1회 확인 | OOS receipt | 재튜닝 금지 |
| R12 인간 판정 | 증거 패킷 검토 | 승인/거절 기록 | 자동승격 없음 |

### 9.1 `<3000` 파일럿의 권장 사전등록

아래 값은 제안이며 **실제 실행 전에 별도 사전등록 문서에서 고정**한다.

| 항목 | 제안 |
|---|---|
| 우선 Band | `<3000` |
| 이유 | metrics가 나온 유일 Band이며 error/timeout 진단 표본도 있음 |
| Family | 기존 5Family 고정 |
| 원시 시드 | Family당 QMC32 유지 |
| 후보 선택 | Event 하한 + 성과 비사용 거리 규칙 |
| 세대 | G0 + 구조 개선 G1, 필요 시 사전등록된 G2까지만 |
| 개발 기간 | 복수 시장 구간·복수 fold, 결과 전 고정 |
| 비용 | 현 공식 비용 + 사전 정의 민감도 시나리오 |
| 중지 | 유효 실행 부족, controls 실패, 모든 fold 음수, posterior 미달 |
| 금지 | Band 경계 이동, 좋은 달 선택, 실패 주변 threshold 미세조정 |

### 9.2 구조 개선으로 인정하는 것

| 허용 | 금지 |
|---|---|
| 상태 순서 변경 | 실패 threshold ±작은 값 반복 |
| Family 논리 조합 변경 | 좋은 거래만 남기는 사후 필터 |
| 진입 조건 역할 추가/제거 | 결과를 보고 기간 교체 |
| 매수/매도 책임 재분리 | Band 경계 이동 |
| 실행비용을 줄이는 PnL 비사용 구조 교정 | 양수 후보만 다음 세대로 전달 |

---

## 10. 실제 착수 단위와 권장 순서

### 10.1 바로 착수할 작업 백로그

| 순서 | ID | 레인 | 작업 | 크기 | 완료 증거 |
|---:|---|---|---|---|---|
| 0 | RST-00 | Git/문서 | 정본 병합·재출발 브랜치·마스터플랜 | 완료 | `f75b80eb` + 본 문서 |
| 1 | PIPE-01 | 시스템 | `<3000` 10 job failure ledger와 typed taxonomy | 작음 | 10/10 원인·재시도 정책 |
| 2 | SYS-01 | 시스템 | Truth Contract schema/API 테스트 | 작음 | 잘못된 상태 조합 거부 |
| 3 | UX-01 | UX | Global Truth Bar + 다음 허용 행동 | 작음 | 5상태 fixture 브라우저 QA |
| 4 | ANA-01 | 분석 | AnalysisBundle v2 schema/builder 초안 | 중간 | 동일 입력 deterministic bundle |
| 5 | UX-02 | UX | Result Overview를 bundle 기반으로 재배선 | 중간 | identity/권위/완전성 우선 |
| 6 | RES-01 | 연구 | `<3000` 다기간 개발 사전등록 | 작음 | 실행 전 commit |
| 7 | RES-02 | 연구 | G0 Event estimator + 공식 fold 실행 | 진행 | Event Gate 완료, 7후보·28 jobs 봉인 |
| 8 | ANA-02 | 분석 | G0 구조 부검 패킷 | 중간 | Family별 falsification 가설 |
| 9 | RES-03 | 연구 | G1 구조 후보 생성·동일 계약 재실행 | 큼 | parent-child lineage |
| 10 | UX-03 | UX | 실제 G0/G1 데이터로 결과 분석 사용성 반복 | 중간 | 관찰 기록·수정 전후 QA |
| 11 | RES-04 | 연구 | Controls/FDR/posterior 또는 정상 중지 | 큼 | typed gate |
| 12 | SCALE-01 | 연구 | 나머지 Band 순차 확장 | 큼 | Band별 독립 lineage |

### 10.2 첫 3개 구현 PR

| PR | 범위 | 포함하지 않는 것 |
|---|---|---|
| PR-A Truth & Failure | 상태 schema, failure taxonomy, read-only API, tests | 조건식 생성·DB write |
| PR-B Result Bundle | AnalysisBundle v2, builder, hash, result API | 화면 전면 개편 |
| PR-C Decision UX | Truth Bar, Result Overview, 다음 행동 | 새 통계 알고리즘 |

그 후 실제 `<3000` 사전등록과 연구 실행을 별도 PR/commit으로 진행한다.

### 10.3 직접 사용하며 수정하는 루프

| 회차 | 실제 시나리오 | 관찰할 것 | 수정 한도 |
|---:|---|---|---|
| 1 | error job 열기 | 원인·재시도 가능 여부를 30초 내 아는가 | Failure/Truth UI만 |
| 2 | no-trades job 열기 | 정상 무거래와 분석 불가를 구분하는가 | Empty/Capability만 |
| 3 | metrics job 열기 | identity·기간·권위가 차트보다 먼저 보이는가 | Overview만 |
| 4 | G0/G1 비교 | 무엇이 바뀌고 왜 좋아/나빠졌는가 | Compare/Lineage만 |
| 5 | gate 판정 | 다음 행동과 차단 이유가 하나로 보이는가 | Decision만 |

한 회차에 한 목적만 바꾸고, 수정 전후 동일 fixture와 실제 job을 다시 사용한다.

---

## 11. UX/UI 설계 규칙

| 규칙 | 적용 |
|---|---|
| 한 화면 한 질문 | Overview에서 모든 차트를 한꺼번에 노출하지 않음 |
| 다음 행동 하나 | 주 CTA는 한 개, 나머지는 보조/금지 상태 |
| 색은 권위가 아님 | SUCCESS/FAIL을 텍스트·아이콘·코드와 함께 표시 |
| 최신과 역사 분리 | 현재 판정은 상단, HOF/과거 양수는 “역사” watermark |
| 차트보다 identity 우선 | source/기간/비용/권위/완전성을 먼저 표시 |
| 실패도 1급 데이터 | error/timeout/no-trades를 숨기지 않음 |
| progressive disclosure | 요약 → 원인 → 개별 trade/evidence 순서 |
| deep link 보존 | job, trade, bundle, report를 URL로 재현 |
| 상태 복원은 페이지별 | 탭 간 스크롤 위치·필터가 서로 오염되지 않음 |
| 안전한 실행 | 필수 입력 누락 시 버튼 disabled + 누락 이유 |
| 산업형 시각 언어 | 장식보다 계층·밀도·상태 명료성 우선 |
| 접근성 | 키보드, focus, ARIA, 색각 비의존, 1280px 최소 동작 |

---

## 12. 검증 계획

### 12.1 제품·시스템 검증

| 계층 | 검증 |
|---|---|
| Unit | status state machine, failure taxonomy, bundle normalization/hash |
| Integration | 실제 job artifact/CSV를 read-only로 bundle 생성 |
| API | success/no-trades/error/timeout/partial fixture 계약 |
| E2E | 백테스트 결과 선택 → Overview → Episode → Decision |
| Browser | 1280×720, 1440×900, 1920×1080; keyboard; console error 0 |
| Recovery | manager 중단/재시작, stale job, checkpoint resume |
| Safety | strategy DB/protected DB write 없음, mutation capability 유지 |

### 12.2 연구 검증

| 검증 | 통과 기준 |
|---|---|
| source identity | 후보 코드·DB·CSV·engine hash 일치 |
| execution completeness | 실패율과 원인 공개, 유효 결과만 경제 분석 |
| prereg integrity | 실행 시각보다 prereg commit이 앞섬 |
| leakage | 후보 선택에 결과·미래 변수 사용 없음 |
| fold stability | 사전등록 기준대로 모든 fold 보고 |
| multiple testing | BH-FDR/posterior 실제 계산 또는 NOT_RUN |
| counterfactual authority | advisory와 official 분리 |
| OOS | 후보 봉인 뒤 1회, 결과 후 재튜닝 금지 |

### 12.3 저장소 검증

```powershell
python -m pytest tests/unit/ -q
python scripts/verify_nonrelease_sync.py
python scripts/smoke_offline_gui.py --branch codex/process-research-pipeline-restart --version V2.79 --offline --log-dir .omx/logs/process-research-restart
python scripts/verify_pyd_gui_contract.py --branch codex/process-research-pipeline-restart --version V2.79 --upstream-ref STOM_Version_2 --manifest .omx/logs/process-research-restart/verify_pyd_gui_contract.json --log-dir .omx/logs/process-research-restart
python scripts/build_research_docs_index.py --check
git diff --check
git status --short -- _database _database_v3k_shadow _log backup *.db backtest/graph .omx/reports v3k_settings*.json
```

---

## 13. 브랜치·커밋 전략

| 경계 | 규칙 |
|---|---|
| 재출발 정본 | `codex/process-research-pipeline-restart` |
| 시스템 기능 | 재출발 브랜치에서 작은 `codex/...` feature branch |
| 연구 사전등록 | 실행 코드/결과보다 먼저 독립 commit |
| 실행 Evidence | 과거 파일 덮어쓰기 금지, Batch별 새 artifact |
| 조건식 세대 | parent ID·hypothesis·code hash 필수 |
| 병합 | 테스트·runtime proof·문서 갱신 후 명시적 통합 |
| staging | 파일 경로 명시, `git add -A` 금지 |
| push | 별도 사용자 지시 전 로컬만 유지 |

---

## 14. 위험 등록부

| 위험 | 가능성 | 영향 | 완화 |
|---|---:|---:|---|
| UI 개선이 다시 연구 완료로 계산 | 높음 | 높음 | 두 진행률·두 gate |
| 17 실행 실패의 원인 없이 재실행 | 높음 | 높음 | PIPE-01 선행 |
| 거대 모듈 수정 회귀 | 높음 | 중간~높음 | 테스트 고정 후 책임별 분리 |
| 분석 번들에 미래 정보 혼입 | 중간 | 매우 높음 | entry-time boundary와 schema provenance |
| advisory 반사실 과대해석 | 높음 | 높음 | watermark·권위 상태 |
| 좋은 기간/거래 사후 선택 | 높음 | 매우 높음 | prereg와 cohort definition |
| 장시간 job manager 충돌 | 중간 | 높음 | port별 jobs dir·resume·PID 권위 |
| 대시보드 과밀 재발 | 높음 | 중간 | 한 페이지 한 질문 |
| 과거 HOF 권위 오염 | 높음 | 높음 | 역사/현재 분리 |
| OOS 조기 개봉 | 중간 | 매우 높음 | UI와 CLI 이중 gate |

---

## 15. 완료 정의

### 15.1 1차 종단 슬라이스 완료

- `<3000` 기존 10건이 10/10 typed 원인으로 분류된다.
- Truth Bar가 execution/economic/authority/next action을 분리한다.
- metrics/no-trades/error/timeout/partial fixture가 브라우저에서 구분된다.
- 하나의 실제 job에서 immutable AnalysisBundle v2를 재현한다.
- 보호 DB와 운영 전략 DB write가 없다.

### 15.2 `<3000` 반복 연구 완료

- 다기간 개발 사전등록이 실행 전 봉인된다.
- G0 유효 후보와 모든 실패가 함께 기록된다.
- 분석으로부터 검증 가능한 구조 가설이 생성된다.
- G1이 parent와 동일 계약으로 재실행된다.
- 사전등록 반복/중지 기준까지 수행된다.
- Controls/folds/posterior가 실행되거나 명시적 gate로 정상 중지한다.

### 15.3 4Band 프로그램 완료

- Band마다 독립 prereg·lineage·bundle·판정이 있다.
- 실패 Band를 숨기거나 성공 Band 기준을 복사하지 않는다.
- `BO_ELIGIBLE`이 있을 때만 D4를 실행한다.
- Robust 후보 0이면 “연구 완료·경제 후보 없음”으로 정직하게 종료한다.

### 15.4 성공 주장 조건

| 주장 | 필요한 증거 |
|---|---|
| 개발 성공 | 사전등록 development gate |
| Robust 후보 | folds + controls + FDR/posterior |
| OOS 성공 | frozen OOS receipt |
| 실전 가능 | 비용/capacity + shadow + 인간 승인 |
| 자동채택 | 현재 범위에서는 허용하지 않음 |

---

## 16. 최종 권장 순서

| 순위 | 지금 할 것 | 지금 하지 않을 것 |
|---:|---|---|
| 1 | failure ledger와 Truth Contract | 대규모 리디자인 |
| 2 | AnalysisBundle v2 | 새 AI 모델 도입 |
| 3 | Result Overview 한 페이지 | 모든 차트 재작성 |
| 4 | `<3000` 사전등록 | 나머지 Band 동시 실행 |
| 5 | G0 공식 실행·부검 | D4/BO |
| 6 | G1 구조 개선·재실행 | threshold 미세조정 |
| 7 | 실제 사용 UX 반복 | 과거 양수 후보 승격 |
| 8 | Controls/Folds/통계 | OOS 개봉 |
| 9 | 나머지 Band 순차 확장 | 자동채택 |

가장 중요한 판단은 다음과 같다.

> **이 프로젝트를 성공시키려면 더 많은 기능보다 실패를 정확히 분류하고, 하나의 결과를 다음 구조 가설로 바꾸고, 같은 계약으로 다시 검증하는 반복을 실제로 완주해야 한다.**
