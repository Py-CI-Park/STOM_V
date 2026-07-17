# 조건식 연구 종합·성과 분석 보고서 (2026-07-17)

- 범위: STOM AI 조건식 연구 전체 (loop_runs.db 527런 · 60시리즈 + 워크트리 연구 라인 2개)
- 성격: 읽기 전용 종합 분석. `performance_proved=false` — 본 문서의 어떤 항목도
  전략 수익성 입증이 아니며, 프로세스·지식·도구 성과와 실측 사실만 기록한다.
- 데이터 출처: `ai_strategy_loop/state/loop_runs.db`(runs/generations),
  `/history/index` 전수(544항목), 연구 문서(`docs/research/`, `docs/update_log/`)

## A-1. 연구 계보도

### 시대 구분 (loop_runs.db 527런의 시계열 분류)

| 시대 | 기간(런 생성 기준) | 대표 시리즈 (런 수) | 목적 | 대표 결과 |
|---|---|---|---|---|
| 1. 초기 진화 루프 | ~2026.05 말 | run(18), fullevo1~5, fullsmoke, trackb1~4, yr1* | 루프 자체의 최초 가동·세대 진화 검증 | 루프 동작 확립, gate 통과 산발(최대 7/8) |
| 2. 캠페인·시드 탐색 | 2026.06 초 | campaign(20), myr1~5, seed3yr, ens(7), tickwide, minfull | 월별/기간별 캠페인, 시드 대 AI 비교 | campaign_e1~e3 gate 2~4회, 시드(ens_seed) 우위 확인 |
| 3. tick OOS·평가 체계 | 2026.06 초~중 | tick(37), tmap(60), tmap2, theta, wf(24), multiseed | tick 레인 OOS/워크포워드, 902/905 계열 시드맵 | tmap_seed_micro 59.93 score·gate 10/12, wf 시나리오D 통과 다수 |
| 4. 검증·통제 실험 | 2026.06 중 | placebo, r1~r5c, t1/t2/t2c3, gate_p0b, champ, ctrl, exit2*, pa, r2r3 | 양성대조·플라시보·ablation·청산 실험 | champ 4/4 통과(게이트 건전성 실증), placebo 0/12(선택편향 부재), exit2 계열 train 전부 통과 |
| 5. 대량 발굴·야간 배치 | 2026.06 중~하 | mbdisc(48), ovn(79), mbtest, m1 | 멀티밴드 발굴, 야간 anchor/exit2/r2full 반복 | ovn_anchor r1~r6 gate 21~25/25, mbdisc는 대부분 0~산발 |
| 6. provider 전환·인간 시드 | 2026.06 말 | gptauth(4), overnight, follow12(6), human(2) | ChatGPT OAuth 전환, 인간 전략 재현 | follow12_fallback OOS 3/3 다수, human replay 4/4 |
| 7. CSS v7·격자 | 2026.07 초 | smoke(41), lat(77), train_css_v7, timeout | CSS v7 수리·격자 시드, 타임아웃 프로브 | lat 계열 다수 미기동(0 gen) — 실행 불안정 기록 |
| 8. V4 프로세스 감사·A/B | 2026.07.14~16 | ab20260716(2)+b(2), abmain0716(1)/c(1)/d(2)/e(3)/f(10) | 본 세션 라인 — 아래 상세 | f-런 10/10 완주, M1~M5 판정 |

### 8시대 상세: V4 감사/계약 라인 (research/v4-condition-process-audit-20260714)

| 단계 | 내용 | 근거 |
|---|---|---|
| 계약 폐쇄 | 후보 식별(CandidateIdentityV2)·HOLDOUT 격리·typed 봉투·AnalysisCardV3 | `004dd622`, `d5dece4f` |
| 기준선 복구 | BackTest 12인자+13필드 backQ 계약 통일(UI/CLI/warm), 기존 실패 7건 해소 | `3d6e8675` |
| 병합 차단 해소 | warm spawn 결함·경로 방어·비유한 attribution 차단, 독립 리뷰 CLEAR | `f3ddbd14` |
| **결함 수정 1** | anti-copy 가드 맨숫자 오차단(연구 프리셋 생성 0건 마비) → 삼중항 판정 | `ee7cd8a1` |
| **결함 수정 2** | typed 지시 mappingproxy 무발화(처치 사망) → Mapping 판별 | `cf995e03` |
| 대시보드 정합 | 홀드아웃 폼 노출, 정본 /ui 고정, typed/card 토글 폼 노출 | `9b3f951e`, `8b3f5395` |

### 실 A/B 실험 계보 (사전등록 기반)

| 실험 | 설계 | 결과 | 판정 |
|---|---|---|---|
| 파일럿 #1 (ab20260716) | min 백지 6세대 1쌍 | 양팔 0/6 생성(가드 오차단) | 무정보 — **결함 1 확정** |
| 파일럿 #2 (ab20260716b) | 가드 수정 후 재실행 | 양팔 6/6 생성, 게이트 0, 카드 미발화 | 무해성 확인, 효과 판정 불가 |
| 본실험 c/d/e (셰이크다운) | tick 시드 5쌍 15세대 | c: 카드 토글 누락, d: 가드·복잡도 모순으로 gen1+ 전멸, e: typed 처치 사망 발견 | **결함 2·설정 모순 2건 확정** |
| **본실험 f (abmain0716f)** | 모든 결함 수정 후 10런 | 10/10 완주, M1 5/5쌍 발화, M2 오염 0, M3/M4 전쌍 동률(홀드아웃 도달 1회) | **M5 미충족 — typed 기본 OFF 유지** |

### condtree 라인 (research/condition-history-tree-seeds-20260715)

| 산출 | 내용 | 근거 |
|---|---|---|
| History 인프라 | condition_history_v1 스키마·단일 발행기·이중 어댑터·v4.1 트리 패널 (+테스트 152) | `65defbbf`, `80d102f6` |
| 와이드시드V1 | 등록기·TrialSpec 계획기·Stage-0 인벤토리·Stage-1 12셀 분해 | `d84b06bb`, `b86c87c2` |
| Stage-1 실측 | tick 178,247건 전 셀 순손실 / min 26,198건 중 **장초 30분×중대형(≥6000억) 승률 41% 상대 우위** | `2026-07-17_wide_seed_v1_stage1_exploratory_results.md` |

두 라인은 2026-07-17 본선(loop/process-research-pipeline)으로 체리픽 통합됐다
(변경 파일 겹침 0, 핸드오프 절차 준수).

## A-2. 검증된 사실 대장 (실측 확정 지식만)

| # | 사실 | 근거 |
|---|---|---|
| F1 | 홀드아웃 졸업검사는 과적합을 실제로 차단한다 — TRAIN 통과 후보(best 1.008)가 홀드아웃 MDD 163%로 탈락 | abmain0716f_p1_legacy 로그, 본실험 결과 문서 |
| F2 | 발굴 게이트의 지배 병목은 빈도-MDD 트레이드오프다 — MDD를 잡으면 일평균 거래가 정책 하한(0.5/일) 미달로 떨어지는 패턴이 3개 실험 30+세대에서 반복 | 파일럿#2·본실험 e/f 게이트 로그 |
| F3 | 검증 시드(902/905 계열)도 2023~2025 tick 창에서는 빈도 0.3/일로 게이트 미달 — 시드의 과거 검증(0.7/일)과 창 의존성이 크다 | abmain0716f gen0 시드 평가 |
| F4 | typed 피드백 계약은 무해하다(생성 149/150 평가 무제약, 교차 오염 0) — 단 효과 우열은 미판정 | 본실험 M1~M4, 프롬프트 원장 전수 검사 |
| F5 | anti-copy 가드의 맨숫자 항목 판정은 few-shot 연구를 100% 마비시켰다(36회 전 차단) → 삼중항 판정으로 수정·실증(0/6→6/6) | 파일럿#1 vs #2, `ee7cd8a1` |
| F6 | AnalysisCardV3 typed 결의 배선의 dict isinstance는 mappingproxy 지시를 전량 폐기했다(프로덕션 상시 무발화) → Mapping 판별로 수정·실증(카드 0→feedback 3~9라인) | e-런 vs f-런, `cf995e03` |
| F7 | tick 3년 warm 로딩은 15~20분 실측 — bt_timeout 900초는 cold 폴백을 유발(완주 40h+) | c/d-런, 프리셋 2400초 반영 |
| F8 | 양성대조(챔피언 4/4)·플라시보(0/12)로 게이트·데이터 건전성과 선택편향 부재가 검증돼 있다 | champ_diag, placebo_train (4시대) |
| F9 | min 장초 30분×중대형 셀은 승률 41%로 유일한 상대 우위 — 단 exploratory이며 OOS/승격 근거 아님 | Stage-1 결과 문서 |
| F10 | AnalysisCardV3 카드 채널의 원천 토글 누락 시 자유문/typed 모두 무발화 — 연구 프리셋 필수 ON | c-런, `95ebc82c` |

## A-3. 미해결 병목 대차대조표 (우선순위 순)

| 순위 | 병목 | 실측 근거 | 유력 접근 |
|---|---|---|---|
| 1 | **생성 능력**: AI가 빈도·MDD를 동시 만족하는 후보를 못 만든다 | F2·F3 | 41% 셀 세분화(C-1), 빈도 명시 프롬프트, 창 재선정 |
| 2 | **청산 미분리**: 손실이 진입 탓인지 청산 탓인지 미확인 | Stage-1 매도 프로필 미검증 | 청산 A/B (C-2) |
| 3 | **승격 관문 부재**: exploratory→수익 전략 확정 경로 없음 | Frozen OOS 게이트 미구축 | C-3 (별도 ralplan+승인) |
| 4 | **이력 메타데이터 결손**: A-4 참조 | 544항목 계보 0 | 대시보드 고도화 (G002) |
| 5 | typed 효과 미판정 | F4, M3 동률 | 1번 해결 후 재실험 |

## A-4. History 데이터 품질 평가 (대시보드 고도화 요구사항)

실측 (2026-07-17, /history/index 전수 544항목 = loop_run 527 + campaign 17):

| 항목 | 현재 인덱스 보유 필드 | 결손 (이력 관리 실패의 원인) |
|---|---|---|
| 식별 | research_id, label(=run_id 원문), source_kind, updated_at, counts, condition_tree_status | **실험 계열/시리즈**(예: abmain0716f가 5쌍 A/B의 일부라는 정보), **쌍/팔 구분**(legacy/typed), **파일럿→본실험 계보** |
| 목적/판정 | 없음 | **실험 목적 요약**, **사전등록·결과 문서 링크**, **판정 배지**(M1~M5, gate 통과 수, 홀드아웃 판정) |
| 상세 | evaluations에 metrics·status, conditions에 label·coverage | **게이트 탈락 사유의 구조화**(현재 원문 문자열), **홀드아웃 verdict 노출** |

파생 요구사항 (G002 입력):

1. run_id 접두사 기반 시리즈 그룹핑과 A/B 쌍/팔 배지 (읽기 전용 파생 — 발행 경로 신설 금지)
2. 연구 문서(사전등록/결과) 경로 참조 표시
3. 게이트 통과/홀드아웃 판정 배지
4. 쌍대비교 뷰·12셀 히트맵·홀드아웃 퍼널 시각화 (로드맵 B-3)

## 결론

8시대 527런의 연구는 "루프 가동 → 평가 체계 → 통제 실험 → 대량 발굴 →
프로세스 신뢰성"으로 성숙해 왔고, 현재 시스템은 **정확한 저울(검증된
게이트·홀드아웃·계약)과 탐색 지도(41% 셀)를 모두 갖춘 최초의 상태**다.
남은 것은 병목 1~3의 순차 해소이며, 그 전 단계로 이 지식을 화면에서
관리 가능하게 만드는 대시보드 고도화(G002)가 선행된다.
