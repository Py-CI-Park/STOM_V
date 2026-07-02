# 2026-07-02 AI 조건식 루프 Phase 0~6 구현 기록

## 요약

2026-07-02 전수 감사(`docs/research/condition_research/2026-07-02_ai_loop_full_audit_and_code_update_plan.md`)에서 확정한 Phase 0~6 코드 업데이트 계획을 당일 멀티에이전트 병렬 개발로 전량 구현하고 11개 코드/문서 커밋으로 기록했다. 모든 커밋은 전체 unit 게이트(최종 3,972 통과, 실패 8건은 변경 전부터 존재한 브랜치 기존 이슈 허용 목록과 동일) + `verify_nonrelease_sync` 통과 후 수행했다.

## 커밋 목록 (이 작업분)

| 커밋 | 내용 |
|---|---|
| `a79b2b27` | Phase 0 — replay 프로파일 동결(포렌식: betting/avg_time 2개 차이 확정), 슬리피지 tick0~3 지표, 측정계 프레임 이원화 |
| `a5948fb5` | Phase 1 — 시드 격자 144셀×4패밀리=576시드, coverage_gap 실공급, passport/CLI |
| `be5e98fc` | Phase 2 — 거래 원장, 절 단위 ablation, Analysis Card v2 생산자 |
| `db85f594` | Phase 3 — 변이축 원장(axis_ledger), LLM 후보팩 생산자(pack_producer) |
| `bc604a97` | Phase 4 — chart_sulsa v7.0 원리 3계층 + 조건식 25개 가설 시드 + 원리 게이트 |
| `f1140b85` | 전수 감사 계획·실행 체크리스트 문서 |
| `12a247af` | P1 잔여 — tick 서브밴드 설정화, 셀 스모크 예산, 부활 레지스트리 |
| `7e5104f5` | P2 잔여 — feature importance 죽은 배선 수리, Context Pack 루프 연결(영수증만 영속) |
| `ee1d0c9f` | P5 부분 — 포트폴리오 조립기, 승격 전제 판정(fail-closed), lineage 검사기 |
| `1d199a33` | P3 완료 — LLM 팩 실배선(credit 경로), 축 원장 기록·주입, 슬롯 2~12 opt-in, 교차비교 매트릭스 |
| `221aee7c` | Wave C — positive control 자동화(실측 19/19 gate_healthy), 고아 프로세스 정리, auth 폴백 격차 노트 |

## 설계 원칙 (전 커밋 공통)

- 전 신규 동작 opt-in(기본 OFF)/additive — 기존 파이프라인 byte-불변, 기존 계약 테스트(4슬롯 캡, 프롬프트 계약, condition_generator 검증) 전부 보존
- 연구 레인 전용: `can_promote/export/live=false`, promotion-review zero-generation, `backtest/graph/` 불가침 유지
- 정직 라벨: 데이터 부족/평가 불능은 insufficient_data·not_evaluable·스킵으로 기록 (0 채움·추측 금지)
- 결정론: 시계/난수 미사용(원장 recorded_at은 호출자 주입), 동일 입력→동일 산출 테스트

## 전수 감사 결함 → 해소 매핑

| 감사 결함 | 해소 |
|---|---|
| baseline replay 불일치 (+3.06M vs +0.52M) | 원인 확정(betting 500만/100만, avg_time 30/60) + 공식 프로파일 동결 + sha 스냅샷 회귀 테스트 |
| 3틱 슬리피지 전멸이 advisory에 그침 | tick0~3 4프로파일 지표 + 승격 프리셋 tick2 hard gate 판정 함수(fail-closed) |
| 명예의 전당 측정계 불일치 | niche/portfolio 프레임 이원화 + 포트폴리오 조립기(상관 캡·상보성) + 벤치마크 비교는 portfolio 프레임 전용 |
| 광폭 시드 생성 부재 | 격자 576시드(DB 실측 기반: tick 09:00~09:30 한정, min 풀세션 6밴드) + 완화 임계(거래수 우선) + 스모크 예산·부활 레지스트리 |
| Context Pack 프로덕션 미배선 | context_pack_builder 승격 + research_loop opt-in(영수증만 영속, 250k fail-closed) |
| feature importance 죽은 배선 | loop.py 실배선(gen0 CSV→gen1 프롬프트 환류 폐루프 테스트) + 환류 4종 토글 세트 |
| 절 단위 기여도 부재 (6/18 32% 부족분) | ablation 엔진(행 기반, 무효/유해 절 판정→변이축 제안) |
| LLM 팩 생산 경로 부재 (결정론 폴백만) | pack_producer + research_loop 실배선(credit 인정, 실패 시 credit 0 폴백 유지) |
| 경향 학습 얕음 (수동 금지 목록) | 축 원장: 사전확률 집계→프롬프트 주입 + 반복 악화 축 자동 금지(turnover 사례 데이터 재현) |
| 원리 문서 미활용 | 3계층 주입(원리/제약/관용구) + 조건식 25개 가설 시드 + 원리 게이트(opt-in) |
| positive control 수동 1회성 | 자동화 + 실측 19/19 gate_healthy 확인 |
| evidence lineage 30% 부족분 | lineage 검사기(요약-원장 일관성) |

## 이월 항목 (다음 사이클)

1. **발굴 루프 LLM auth 폴백**: `FailoverProvider` 배선안 — `docs/research/condition_research/2026-07-02_llm_auth_fallback_gap_note.md`
2. **provider 상위 진입점 배선**: `run_research_iteration(provider=)` 직접 주입은 완료, `cli/ai_controller.py`/`research_optimizer.py` 레벨 전달은 후속
3. **baseline mdd 외부 주입**: baseline_csv 직접 지정 모드에서 축 원장 delta_mdd 확보 경로
4. **승격 슬리피지 게이트 실배선**: 판정 함수까지 완료 — promotion-review 파이프라인 연결은 별도 승인 사항(zero-generation 계약)
5. **`.gjc`/`.omo` 미커밋 증거**: 7/01 인벤토리 문서의 보류 결정 유지
6. **대시보드 번들 7파일**: 이전 세션(09:56) 번들 재생성 잔재 — 이번 작업과 무관하여 미커밋

## 다음 실행 순서 (연구 재개 시)

1. `python -m cli.seed_lattice build` → 576 격자 시드 + passport 생성
2. 기존 러너로 셀 배치 백테스트 → `cli.seed_lattice coverage`/`smoke-plan` 으로 셀 예산 판정
3. 연구 루프 config: `context_pack_enabled` + `slippage_profiles_enabled` + `axis_ledger_path` + (provider 준비 시) `llm_candidate_pack_enabled` + `research_feedback_config_overrides()` 병합
4. 라운드마다 Analysis Card/ablation/교차비교 매트릭스 산출 → OOS 생존자 2개+ 확보 시 `portfolio.assembler`로 결합 → 명예의 전당 상대 지표 추적
5. 주기적으로 `scripts/run_positive_control.py`(게이트 건전성)와 `scripts/check_research_evidence_lineage.py`(증거 일관성) 실행
