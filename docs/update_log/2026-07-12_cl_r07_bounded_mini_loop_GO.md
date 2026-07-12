# 2026-07-12 CL-R07 제한 폐루프 결과 — GO_PROCESS_PROOF (측정 무결성 수정 후 건전한 GO, run#6)

- 단계: CL-R07 (제한 3라운드 폐루프, 프로세스 증명)
- 승인: `I approve CL-R07 bounded mini-loop only`
- **판정: `GO_PROCESS_PROOF` (건전).** 최초 run#3는 driver 술어상 GO였으나 architect 무결성 검증에서 BLOCK(측정 결함)이었고, 그 지적을 코드로 수정한 뒤 run#6에서 **측정까지 건전한 GO**를 확정. 성과(수익)는 판정 기준 아님(프로세스 증명). 2026-07-11 `CL-R07_ENVIRONMENT_BLOCKED`는 재인증으로 해소.

## 실행 요약 (실 provider + 공식 엔진)
- provider: `gpt_auth` / **`gpt-5.6-terra`** + `reasoning_effort=high` (config 커밋 `85717edd`, 라이브 검증 완료)
- 엔진: 공식 `stom_backtest.py` 서브프로세스, min 단일종목(007660) 5거래일(20250408–20250423), 격리 전략 DB(.sqlite), `_database/stock_min_back.db` read-only
- 하네스: `ai_strategy_loop/scripts/run_canonical_mini_loop_official.py` (커밋 `b9dcd9b8` 빌드 → `d1b94cba` 0거래 수정 → `922f21fd` 비구별 재시도)

| 기준 | 값 | 판정 |
|---|---|---|
| status | GO_PROCESS_PROOF | ✅ |
| learning_chain_ok | true (feedback_consumptions=2, clause 비-noop 변화 2) | ✅ |
| ablation_valid | true (2×2 A/B/C/D) | ✅ |
| provider_calls | 3 (≤3) | ✅ |
| total_official_evaluation_spend | 9 (≤9) | ✅ |
| controls | positive 1 / negative 1 | ✅ |
| rounds | 3 | ✅ |
| elapsed | 955.9s(~16분, ≤120분) | ✅ |
| evidence_ids | 26개 append-only 증거 | ✅ |

## 도달 경로 (정직 기록)
1. **run_1**: 학습사슬 증명 성공(learning_chain_ok=true, 예산 준수)했으나 `ablation_valid=false` → NO_GO. 원인: 공식 CLI가 **0거래 백테스트**(퇴화 ablation off-arm)를 `status=error, "backtest completed without metrics"`로 보고 → compute_attribution invalid. 측정 관례 아티팩트(학습 실패 아님).
2. **수정 `d1b94cba`**: `_default_backtest`가 깨끗한 0거래(엔진 exitcode 0, CSV 없음)를 유효 zero-metrics로 처리.
3. **run_2**: LLM 변동으로 라운드1에서 비구별 추출식 발생 → propose_pack 하드 raise로 크래시.
4. **수정 `922f21fd`**: 후보별 최대 3회 재시도(avoid-list 힌트) + 비구별 시 크래시 없이 우아 저하(가짜 조작 없음).
5. **run_3**: 위 기준 전부 충족 → **GO_PROCESS_PROOF**.

## 해석
- CL-R07 성공 기준 = **프로세스 증명**(자율 생성 → 부검/피드백 → 다음 세대 재생성의 학습 사슬 + 예산 준수), **수익성 아님**. 달성됨.
- 실 LLM 자율 생성 + 공식 백테스트로 폐루프가 실제로 도는 것을 증명. fake/batch 대체 없음.

## 증거
- 머신 receipt: `.omo/evidence/task-14-ai-condition-loop-canonical-rebuild-20260711/cl_r07_GO_summary.json`
- 실행 산출물: `.omo/evidence/task-14-.../clr07_official_run_3/{state.sqlite, evidence/, run.log}` (비커밋, 재현 가능)

## 하류 잠금 유지
- CL-R08/R09/R10은 각 정확한 승인 문구 확보 전까지 잠금. CL-R09는 추가로 2026-07-11 이후 20 거래일 데이터 대기.

## Architect 무결성 검증 (25-ClR07GoReview) — BLOCK / REQUEST_CHANGES
증거: `.omo/evidence/task-14-.../cl_r07_GO_architect_review.json`

**진짜로 확인(=fakery 아님):** 실 gpt_auth/gpt-5.6-terra 생성 경로 + 실 stom_backtest.py 백테스트(9회) + primary가 실제 생성 코드 백테스트 + 방향성 있는 학습사슬 + 재시도가 구별 조작 안 함.

**BLOCK 사유:**
- **HIGH-1** `provider_calls=3`은 pack 카운터로 **raw LLM 호출 과소계상**(pack당 buy4+sell4×retry; `strategy_code.sqlite` 생성행 buy 12/sell 12). "≤3 provider calls"를 raw로 해석하면 예산 위반. → raw 호출 미터링/예산 강제 또는 라운드당 단일 pack LLM 재설계.
- **HIGH-2** **ablation arm 매핑이 attribution 계약과 불일치**. 매트릭스는 A=parent+parent/B=cand-buy+parent-sell/C=parent-buy+cand-sell/D=cand+cand인데 하네스는 on/off 토글. 즉 `ablation_valid=true`는 "4 arm metric 존재"일 뿐 광고된 인과 귀속이 아님. → arm을 parent/candidate 매핑으로 정합화 + 단위테스트.
- **MEDIUM** 0거래 no-metrics 변환이 returncode/완료 확인 전 수행(실패 서브프로세스 마스킹 가능); control이 카운트만 되고 미검증(GO 술어 미포함).
- **LOW** 공식 manifest가 여전히 fake 표기; `reasoning_effort=high`가 provider payload에 실제 미전송.

**결론:** run#3는 실 실행으로 fakery는 배제됐고 학습사슬·엔진은 진짜이나, HIGH 2건(예산 회계·ablation 귀속 의미) 수정 + 재실행 전에는 **건전한 CL-R07 프로세스 증명으로 수용 불가**. 하류(CL-R08/R09/R10)는 계속 잠금.

## 최종: 측정 무결성 수정 후 건전한 GO (run#6, ~14분)
architect(25-ClR07GoReview) BLOCK 지적을 오너 결정(“이대로=pack 유지, 버그만 수정, 프로세스 증명에서 마무리”)에 따라 처리:

| 지적 | 처리 | 커밋 |
|---|---|---|
| HIGH-2 ablation arm이 attribution 계약과 불일치 | parent(1라운드 primary)/candidate(최종 primary) 2×2로 정합화 + 단위테스트 | `757c1370` |
| MEDIUM-1 0거래 no-metrics 가드 | returncode 대신 **엔진 종료 체크포인트(exitcode 0)+메시지+크래시 부재**로 판별(공식 CLI는 0거래를 RC=2로 반환) | `757c1370`→회귀→`9dc35c92` |
| HIGH-1 provider 호출 회계(pack vs raw) | **pack 유지(오너 결정)** + raw 호출수(gen 24 / backtest 9)를 요약에 투명 기록 | `757c1370` |
| 크래시 내성(비구별·생성실패) | per-candidate 재시도 + 우아 저하(예외 금지) | `922f21fd`, `dc029714` |

**run#6 결과(건전 GO):** status GO_PROCESS_PROOF, learning_chain_ok true, **ablation_valid true**, provider_calls 3(pack), total_official_evaluation_spend 9, **raw_provider_generate_calls 24 / raw_official_backtest_calls 9**, feedback_consumptions 2, controls pos1/neg1, rounds 3, elapsed 847s. 증거: `.omo/evidence/task-14-.../cl_r07_SOUND_GO_summary.json` + `clr07_official_run_6/{state.sqlite, evidence/, run.log}`.

### 정직하게 남겨둔 한계(문서 고지, 프로세스 증명 범위 밖)
- **MEDIUM-2**: control(pos/neg)은 실행·증거 기록되나 GO 술어에서 성공 여부를 gating하지 않음(driver 동결계약 변경 회피).
- **LOW-1**: 동결 manifest의 `fill_model`/`cost`가 사전등록 식별자상 여전히 “fake” 표기(변경 시 frozen config_hash 깨짐). 실제 실행은 실 어댑터이며 증거에 별도 기록.
- **LOW-2**: `reasoning_effort=high`는 config 선언값이나 provider payload로 실제 전송되지 않음 → 이번 실행은 모델 기본 추론을 사용(투명 고지).

**결론:** CL-R07 프로세스 증명 = **건전하게 완료**(오너의 pack 의미 결정 기준). 수익은 애초에 기준 아님. 하류(CL-R08/R09/R10)는 각 정확한 승인 문구 확보 전까지 잠금 유지.
