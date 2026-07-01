# 2026-06-19 2U AI Loop 연구 재개 권장 시작 범위

## 목적

이 문서는 2U AI loop 최신 연구 흐름에서 **이 워크트리에서 바로 진행 가능한 권장 시작 범위**만 고정한다. 다른 워크트리에서 UI 개선이 진행 중이므로, 여기서는 UI/frontend/bundle 변경 없이 연구 재개 준비와 공식 OOS 실행 후보의 범위를 문서화한다.

## 현재 기준

| 항목 | 상태 |
|---|---|
| 현재 작업 브랜치 | `lazycodex/tick-sparse-positive-generation-improvement-20260604` |
| 기준 anchor | `origin/STOM_Version_2U_C-ai-strategy-loop` |
| anchor 대비 상태 | 현재 HEAD가 anchor보다 3커밋 뒤처짐 |
| 워크트리 상태 | 기존 연구/대시보드 산출물이 많이 dirty/untracked 상태이므로 reset, clean, stash 금지 |
| 연구 우선순위 | 신규 cold 대량 생성보다 `seed bank + 공식 OOS + branch attribution + evidence lineage` 우선 |
| 다음 실행 계획 | `.omo/plans/post-20260618-official-oos-dashboard-cleanup.md` |

## 권장 시작 범위 테이블

| 우선 | 작업 | 여기서 진행 가능 여부 | 예상 소요 | 산출물 | 완료 기준 |
|---:|---|---|---:|---|---|
| 0 | 실행 전 안전 스냅샷 | 가능 | 5~10분 | branch/status, protected path 상태 | dirty 파일을 보존하고 protected runtime path 변경이 없음을 확인 |
| 1 | 후보 입력 artifact 재검증 | 가능 | 10~15분 | 추천 후보 JSON/scoreboard parse 확인 | `post-q4-3h-official-oos-recommendations-20260618.json`와 scoreboard를 읽고 후보/수치가 일치 |
| 2 | 1순위 공식 OOS 사전등록 | 가능 | 10~20분 | preregistration 문서 | 후보, 기간, engine command, stop rule, evidence type을 실행 전 고정 |
| 3 | `저시총 제외 방어 조합` 공식 OOS | 가능 | 45~70분 | raw OOS 결과, log, summary card | 공식 엔진 결과가 있고 CSV 재분석과 구분되어 기록됨 |
| 4 | 결과 판단 카드 작성 | 가능 | 20~30분 | `oos_passed` / `deferred` / `rejected` decision card | 수익, MDD, trades, caveat, next action이 남음 |
| 5 | registry/research record용 요약 갱신 | 가능 | 20~40분 | evidence index, dashboard-record 입력용 요약 | UI 코드 변경 없이 alias/evidence type/OOS status/promotion status/next action을 남김 |
| 6 | 최종 검증 | 가능 | 15~30분 | JSON parse, protected path status, OOS process cleanup 확인 | 문서/JSON이 읽히고 protected path가 깨끗하며 고아 OOS 프로세스가 없음 |

## 전체 단계/Page 현황

| Page | 단계 | 상태 | 예상 소요 | 수행 위치 | 비고 |
|---:|---|---|---:|---|---|
| P0 | 연구 재개 범위 문서화 | 완료 | 완료 | 현재 문서 | 공식 OOS 실행 전 권장 범위와 금지 범위를 고정 |
| P1 | 실행 전 안전 스냅샷 | 남음 | 5~10분 | 이 워크트리 | branch/status, protected path 상태 기록 |
| P2 | 후보 입력 artifact 재검증 | 남음 | 10~15분 | 이 워크트리 | 추천 후보 JSON과 scoreboard parse 확인 |
| P3 | 1순위 공식 OOS 사전등록 | 남음 | 10~20분 | 이 워크트리 | 후보, 기간, command, stop rule, evidence type 고정 |
| P4 | `저시총 제외 방어 조합` 공식 OOS | 남음 | 45~70분 | 이 워크트리 | raw OOS 결과와 log 생성, CSV 재분석과 구분 |
| P5 | 결과 판단 카드 | 남음 | 20~30분 | 이 워크트리 | `oos_passed` / `deferred` / `rejected` 중 하나로 판단 |
| P6 | registry/research record 요약 | 남음 | 20~40분 | 이 워크트리 | UI 코드 변경 없이 dashboard 입력용 데이터만 정리 |
| P7 | 최종 검증/정리 | 남음 | 15~30분 | 이 워크트리 | JSON parse, protected path, OOS process cleanup 확인 |
| P8 | shadow/보조 후보 후속 | 후속 | 1.5~3시간 추가 | 이 워크트리 | `11월 제외`, exit2 규칙, r8 단독은 1순위 완료 후 진행 |

## 완료/남은 작업 표시

| 구분 | 완료 | 남음 |
|---|---|---|
| 문서화 | 권장 시작 범위 문서 작성, 전체 단계/Page 표 작성 | 없음 |
| 실행 준비 | 다음 계획과 후보명 정리 | 안전 스냅샷, 입력 artifact parse, preregistration |
| 공식 OOS | 없음 | `저시총 제외 방어 조합` 1순위 공식 OOS |
| 판단/기록 | 금지 범위와 완료 기준 정리 | decision card, registry/research record 요약 |
| UI | 여기서 하지 않기로 명시 | 다른 워크트리에서 별도 진행 |
| live/V3K/DB | 접근 금지로 명시 | 없음. 다음 연구에서도 계속 제외 |

## 다음 진행용 GJC 추천 명령어

최소 재개 준비와 1순위 공식 OOS 실행을 durable goal로 이어갈 때의 권장 명령어는 아래 순서다.

```powershell
gjc ultragoal create-goals --brief-file .omo/plans/post-20260618-official-oos-dashboard-cleanup.md
gjc ultragoal complete-goals
```

다만 위 plan 파일은 긴 단일 계획 문서이므로, 실행 전에는 `complete-goals`가 출력하는 현재 story objective를 확인하고 **P1 안전 스냅샷 → P2 artifact 재검증 → P3 preregistration**까지만 먼저 닫는 것이 안전하다. 실제 공식 OOS는 preregistration 산출물이 생긴 뒤 별도 story로 계속 진행한다.

## 현실적인 권장 시작 묶음

| 범위 | 예상 총 소요 | 추천도 | 설명 |
|---|---:|---|---|
| 최소 재개 준비: 0~2 | 25~45분 | 필수 | 공식 OOS 실행 전에 안전성과 입력 artifact를 고정 |
| 1순위 연구 완료: 0~4 + 6 | 1.5~2.5시간 | 가장 추천 | `저시총 제외 방어 조합` 공식 OOS 1건과 판단 카드까지 완료 |
| robust + shadow 비교: 0~6 + shadow 후보 추가 | 2.5~4시간 | 후속 추천 | 1순위 후보 이후 `11월 제외 비교용`을 shadow OOS로만 비교 |
| 전체 후속 계획 | 4~6시간 | 장시간 작업 | exit2 포트폴리오 규칙, r8 단독 필터, registry/dashboard 요약까지 모두 정리 |

## 1순위 후보

| 쉬운 이름 | 내부 이름 | 현재 근거 | 주의 |
|---|---|---|---|
| 저시총 제외 방어 조합 | `r8_exclude_cap_lt_1500__exit2_skip_after_prior_exit2_loss_500k_else_full` | CSV 재분석 기준 전체 +39,402,438원, 연평균 38.68%, MDD 7.68%, Q4 +952,502원 | 아직 공식 OOS 전이므로 최종 후보로 주장 금지 |

## 비교용 후보

| 쉬운 이름 | 내부 이름 | 역할 | 주의 |
|---|---|---|---|
| 11월 제외 비교용 후보 | `r8_exclude_month_11__exit2_skip_after_prior_exit2_loss_500k_else_full` | raw score 1위 shadow 비교 | 달력 월 제외 규칙이라 과최적화 위험이 크며 직접 채택 후보가 아님 |

## 여기서 하지 않을 작업

| 제외 작업 | 이유 |
|---|---|
| dashboard frontend/UI 개선 | 다른 워크트리에서 진행 중이며 충돌 위험이 큼 |
| bundle 재생성 | UI 변경 범위에 속함 |
| `backtest.py` 수정 | 문서상 exit-rule 설계가 미확정이라 보류 |
| live, V3K, `strategy.db`, export/final approval | 연구 범위를 벗어나며 별도 승인 게이트 필요 |
| 대량 cold AI 생성 재가동 | 현재 문서 기준 우선순위가 아님. 먼저 robust 후보 공식 OOS 필요 |
| reset, clean, stash | 기존 dirty/untracked 연구 산출물 보존 필요 |

## 완료 안내 기준

이 문서 작성만으로 공식 OOS가 수행된 것은 아니다. 실제 연구 재개는 위 테이블의 **최소 재개 준비 0~2**를 먼저 수행한 뒤, **1순위 연구 완료 범위 0~4 + 6**으로 `저시총 제외 방어 조합` 공식 OOS를 실행하는 것이 안전하다.
