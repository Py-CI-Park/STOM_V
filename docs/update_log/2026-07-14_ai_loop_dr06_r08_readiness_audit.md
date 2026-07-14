# DR-06 — 기존 동결 R08 manifest/readiness 읽기 전용 감사

- 날짜: 2026-07-14
- 브랜치: `feature/loop-remaining-research-plan-20260713`
- HEAD: `bcdce049` (DR-00 `70da4702` 위 DR-01~05 + 통합 E2E 7커밋)
- 성격: **읽기 전용 감사** — provider 호출 0, 공식 평가 0, 보호 DB 쓰기/개방 0, 신규 후보·순위·tie rule 생성/변경 0.
- 근거 계약: `docs/update_log/2026-07-13_ai_condition_generation_backtest_analysis_research_review.md` §DR-06, `docs/update_log/2026-07-12_cl_r07_bounded_mini_loop_GO.md`.

## 1. 감사 대상 — 동결 R08 계약 항목

| 항목 | 동결 값 |
|---|---|
| 기간 | 마지막 60 min 거래일 = train 40 + validation 20 |
| universe | train-only top-20 |
| 후보 | 8개(repair 4 + discovery 4), family당 최대 2, semantic duplicate 0 |
| 동결 후 provider | 0 호출 |
| 공식 평가 | train 8 전수 + validation 최대 3 = 최대 11, wall 4h |
| validation gate | 비용후 profit>0, MDD≤35, daily≥0.5, chronological half 각각 profit>0 |
| tie-break | validation worst-half profit → total profit → lower MDD → candidate ID |

## 2. 감사 결과

| 감사 항목 | 판정 | 근거 |
|---|---|---|
| R08 manifest·후보배분·순위·tie rule hash가 CL-R07 첫 결과 전 존재 | 부분 충족 | 동결 계약 문서는 존재하나(§DR-06), 정본 manifest의 cost/fill 식별자가 결함 상태 |
| 현재 정본 spec/protocol/실행계획과 hash 일치 | **불일치** | DR-01~05가 manifest/profile/evidence 계약을 변경(아래 3장) |
| cost/fill 필드가 frozen 의미와 실제 실행 의미를 식별 | **미흡** | 동결 manifest의 `fill_model`/`cost`가 사전등록 식별자상 "fake" 표기(CL-R07 GO LOW-1). 실제 실행은 실어댑터지만 식별자가 이를 식별하지 못함 |
| DSR/PBO 중복 계약이 frozen hard gate 변경 | 미변경 | DR-05 통계는 train-only 환류 게이팅이며 R08 hard gate(비용후 profit/MDD/daily/half)를 바꾸지 않음 |
| defect remediation이 candidate/config/profile hash 변경 | **변경함** | DR-02 effective profile hash + Manifest v2(cost/fill/engine 실바인딩), DR-03 실제 prompt FK/evidence, DR-01 R²/MDD 교정 → 동결 당시 hash 의미와 달라짐 |

## 3. 핵심 결론 — 동결 R08은 그대로 실행 불가

동결 R08 preregistration은 **결함 교정(DR-01~05) 이전**의 계약이다. 특히:

1. **cost/fill "fake" 식별자**: 동결 manifest는 비용·체결 모델을 "fake"로 표기했고, 이를 실값으로 바꾸면 `frozen config_hash`가 깨진다(CL-R07 GO LOW-1). 즉 동결 계약 자체가 비용후 성능을 정직하게 식별하지 못한다.
2. **DR-01~05가 계약 의미를 변경**: 이번에 커밋된 교정은 리뷰가 CL-R08 전 필수라고 명시한 BLOCKER(가짜 cost/fill manifest, 잘못된 우상향/낙폭, 실 prompt 미연결 증거, 통계 미보정)를 정확히 고친다. 그 결과 manifest/profile/evidence hash 의미가 동결 시점과 달라졌다.
3. 리뷰 §요약(line 1075): BLOCKER 교정 + **사전등록 재동결** 후에만 CL-R08 실행 가능. R08 후보 밴드도 train-40/train-only universe에서 재채굴해 manifest hash에 묶어야 한다(line 309).

## 4. Readiness Verdict

**`R08_CONTRACT_AMENDMENT_REQUIRED`**

- `R08_READY` 아님: 동결 계약을 그대로 실행하면 가짜 cost/fill·교정 전 수학으로 성능을 검증하게 되어 부당하다.
- `READINESS_BLOCKED` 아님: 증거·계약은 존재하며 무엇을 재동결해야 하는지 식별 가능하다.
- 결론: **결함 교정으로 hash·계약 변경이 필요**하므로 amendment가 요구된다. 이 감사 보고서는 계약을 **고치지 않고** 정본 planner로 반환한다(§DR-06 line 875 준수).

### 정본 planner 반환 항목(이 보고서에서 수정 금지)
- Manifest v2(실 cost/fill/engine 바인딩)로 R08 manifest 재작성 + config_hash 재동결.
- effective profile hash(DR-02)와 실 prompt evidence(DR-03) 기준으로 candidate/config/profile hash 재동결.
- R08 후보 밴드 train-40/train-only 재채굴 후 manifest hash 결속.

## 5. HARD STOP

`HARD_STOP_AWAITING_CL_R08_DECISION`

- `R08_READY`도 실행 승인이 아니며, 본 결과는 `R08_CONTRACT_AMENDMENT_REQUIRED`다.
- CL-R08/R09/R10은 각 정확 승인 문구 확보 전까지 잠금 유지:
  - `I approve CL-R08 bounded min performance only`
  - `I approve CL-R09 sealed OOS/WF only` (추가로 2026-07-11 이후 20 거래일 데이터 필요)
  - `I approve CL-R10 benchmark promotion review only`
- `performance_proved=false`, `human_comparison_proved=false`, `live_authorized=false` 유지.
- DR-06 결과와 무관하게 CL-R08을 자동 실행하지 않는다. 계약 재동결은 정본 planner의 별도 canonical amendment로만 수행한다.
