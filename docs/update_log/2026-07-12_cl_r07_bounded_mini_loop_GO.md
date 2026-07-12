# 2026-07-12 CL-R07 제한 폐루프 결과 — GO_PROCESS_PROOF

- 단계: CL-R07 (제한 3라운드 폐루프, 프로세스 증명)
- 승인: `I approve CL-R07 bounded mini-loop only`
- **판정: `GO_PROCESS_PROOF`** — 2026-07-11 `CL-R07_ENVIRONMENT_BLOCKED`를 대체(재인증으로 해소).

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
