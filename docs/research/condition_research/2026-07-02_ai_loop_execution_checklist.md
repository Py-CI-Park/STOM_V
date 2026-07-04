# AI 조건식 루프 코드 업데이트 실행 체크리스트 (2026-07-02)

> 근거 계획: `2026-07-02_ai_loop_full_audit_and_code_update_plan.md`
> 진행 규칙: Phase 단위로 구현 → 신규 단위테스트 + 전체 `tests/unit` 통과 → `scripts/verify_nonrelease_sync.py` 통과 → 한글 커밋. 연구 레인 전용 변경만 허용 (export/live/final promotion 권한 불변, `backtest/graph/` 불가침).

## 진행 현황

| Phase | 상태 | 커밋 |
|---|---|---|
| Phase 0 측정·재현성 기반 | ✅ 완료 | a79b2b27 |
| Phase 1 시드 격자 | 🔶 부분 완료 (T1.3/T1.5 배선 잔여) | a5948fb5 |
| Phase 2 분석·환류 배선 | 🔶 부분 완료 (T2.1/T2.4 배선 잔여) | be5e98fc |
| Phase 3 다후보·축 원장 | ✅ 완료 | db85f594 + 1d199a33 |
| Phase 4 원리 주입 | ✅ 완료 | bc604a97 |
| Phase 5 벤치마크·포트폴리오 | ✅ 완료 | ee1d0c9f + 221aee7c |
| Phase 6 위생 | ✅ 완료 (T6.2는 문서화된 보류 유지) | ee1d0c9f + 221aee7c |

## Phase 0 — 측정·재현성 기반

- [x] T0.1a replay 불일치 포렌식 — **원인 확정: `betting`(500만 vs 100만원)·`avg_time`(30 vs 60) 2개 파라미터 차이**. 조건식/기간/유니버스/엔진 수는 동일, 각 프로파일 내부는 byte-identical 재현. 공식 프로파일 = 06-28 설정(betting "5", avg_time 30) 동결. 보고서: `2026-07-02_replay_profile_forensics.md`
- [x] T0.1b `controller/replay_profile.py` — ReplayProfile frozen dataclass + CANONICAL_REPLAY_PROFILE_V1 동결(sha 4c5acdc5...) + compare/receipt (테스트 26개)
- [x] T0.1c research_loop opt-in 배선 (`record_replay_profile`, additive 키 5종, 기본 OFF 스키마 불변)
- [x] T0.2a `fitness/slippage_profiles.py` — 기존 slippage_stress.py 재사용, tick0/1/2/3 프로파일 + MDD(일별 재집계 가능 시만, 불가 시 None 정직 라벨) (테스트 30개)
- [x] T0.2b research_ranking advisory 병기(랭킹 순서 불변) + research_loop opt-in 배선(`slippage_profiles_enabled`)
- [x] T0.2c promotion 프리셋 `slippage_gate_profile='tick2'` 선언 + `evaluate_slippage_gate` 순수 판정 함수(fail-closed). 실배선은 승격 파이프라인 별도 승인 사항으로 보류(zero-generation 계약)
- [x] T0.3 `fitness/measurement_frame.py` — 프레임 열거+annotate/assert_comparable(무예외 advisory)+명예의 전당 portfolio 전용 상수, research_metrics additive, backtest_report 라벨 표기 (테스트 44개)
- [x] 검증: 전체 3,737 통과 / 실패 8건 전부 사전 허용 목록 내 / verify_nonrelease_sync 전부 OK
- [x] 커밋 a79b2b27

## Phase 1 — 시드 격자

- [x] T1.0 tick/min DB 시간 커버리지 실측 — **tick 952일 전부 09:00~09:30만 존재**(1,801초/일), min 213일 풀세션(09:00~15:19). 결론: tick 격자=시초 30분 내 5분 버킷 6개, 전 시간대 광폭은 min 레인 6밴드 담당
- [x] T1.1 `seeds/lattice.py` 격자 열거기 — 144셀(lane 2×시간밴드 6×시총 4×등락률 3)×패밀리 4=576시드, 기각 계열(F03/F04/F10/F18) 제외, 전수 compile+금지토큰+변수스코프 통과
- [x] T1.2 band_compiler 소비 배선 — buy는 compile_to_code 경유, sell은 자체 템플릿(force_exit tick 92900/min 145900)
- [ ] T1.3 tick 시간창 연구 레인 configurable — **범위 축소 확정**: DB에 09:30 이후 없음 → "09:00~09:28 고정 → 09:00~09:30 내 서브밴드 설정"으로 변경 (Phase 0 커밋 후, condition_discovery.py 충돌 회피 대기)
- [x] T1.4 `seeds/coverage.py` — 144셀 coverage map + `coverage_gaps`가 discovery 프롬프트 `coverage_gap` 계약 실충족(실프롬프트 주입 테스트 포함)
- [ ] T1.5 셀 단위 스모크 예산 + 부활 레지스트리 연동 (Phase 0 커밋 후, research_loop.py 충돌 회피 대기)
- [x] `cli/seed_lattice.py` CLI (build/coverage 커맨드, passport 자동 생성)
- [x] 자체 검증: 신규 테스트 27개 통과 + 적대적 리뷰(MEDIUM 1건 수정 반영)
- [x] 전체 게이트 통과 + 커밋 a5948fb5 (T1.3/T1.5는 배선 라운드로)

## Phase 2 — 분석·환류 배선

- [ ] T2.1 `controller/context_pack_builder.py` — artifacts 로직 승격 + 루프 배선
- [x] T2.2 `autopsy/analysis_card.py` — 10개 섹션 카드, insufficient_data 정직 라벨 (테스트 25개)
- [x] T2.3 `autopsy/ablation.py` — AND/OR 절 분해+통과율/제거 효과/자카드+변이축 제안, 실 v7 조건 파싱 실증 (테스트 24개)
- [ ] T2.4 feature importance 죽은 배선 수리 + 연구 프리셋 토글 ON
- [x] T2.5 `autopsy/trade_ledger.py` — 48컬럼 원장, parquet/sqlite 자동, 코호트 비교 (테스트 24개)
- [x] 자체 검증 73개 통과 + 커밋 be5e98fc (T2.1/T2.4는 배선 라운드로)

## Phase 3 — 다후보·축 원장

- [x] T3.1 `brain/pack_producer.py` — repair/discovery 프롬프트 실호출로 팩 생산, `condition_generator` 검증 실통과 확인, partial/shortfall 정직 기록, 권한 밀반입 차단, 결정론 영수증. **배선(research_loop 연결)은 잔여**
- [x] T3.2 라운드 슬롯 opt-in 확장 — 기본 4 불변, 연구 레인 한정 2~12+레인 쿼터(fail-closed), promotion/fast 무영향 (테스트 17개)
- [x] T3.3 `controller/axis_ledger.py` — JSONL 원장 + 축별 사전확률 + 프롬프트 라인 + 자동 금지(`turnover_min_902 1.5→3.0` 수동 금지의 데이터 재현 테스트 포함). 리뷰 결함 2건(유망/금지 라벨 모순, sell repair 부모 코드) 수정 반영 확인
- [x] T3.4 라운드 교차비교 매트릭스 — 후보×지표+변이 귀속 아티팩트, opt-in 저장
- [x] 자체 검증: 테스트 35개(axis 20+pack 15) 통과
- [x] LLM 팩 실배선(credit 인정 경로+폴백 사유 기록) + 축 원장 기록·주입 배선(mdd_pct 키 수정 반영) + 게이트 3,972 통과 + 커밋 1d199a33

## Phase 4 — 원리 주입 (chart_sulsa v7.0)

- [x] T4.1 3계층 추출 완료 — `principles.md`(P0~P15 원리), `constraints_checklist.md`(CSC-01~14 기계 판정), `idiom_dictionary.md`(원리→STOM 변수 관용구 10섹션, tick/min 구분) + `brain/principles.py` 로더. 전 임계값 '무근거 가설' 라벨
- [x] T4.2 조건식 25개 추출(HTML 원문 양방향 검증, sha256 25/25 일치, compile 전건 통과) → `brain/data/chart_sulsa_v7_conditions.json` + 패턴 패밀리 12종 JSON + Condition Passport 25개
- [x] T4.3 원리 게이트 `brain/principle_gate.py` (CSC-06/07/10 reject + advisory, opt-in 토글 기본 OFF, generator PRE-SAVE '4g' 최소 배선) — 리뷰 결함 D1(시간 비교 방향)·D2(손절 패턴 협소) 수정 반영, 레퍼런스 자기일관성 테스트 포함
- [x] 자체 검증: 신규+계약 테스트 통과 (수정 후 43 passed)
- [x] 전체 게이트 통과 + 커밋 bc604a97

## Phase 5 — 벤치마크·포트폴리오

- [x] T5.1 positive control 자동화(compute_fitness 재사용 byte-동일 게이트) — **실측 19/19 통과, gate_healthy** + receipt 스크립트
- [x] T5.2 `portfolio/assembler.py` — 상관 캡 0.5(제외 사유 필수), 시간밴드 상보성, 결합 MDD, 포트폴리오 프레임 라벨, 명예의 전당 19전략 상대 지표 (테스트 32개)
- [x] T5.3 승격 전제 판정 모듈 — 5체크 fail-closed, can_promote 항상 False 고정 (테스트 25개)
- [x] 검증 80개 통과 + 커밋 ee1d0c9f / 221aee7c

## Phase 6 — 위생

- [x] T6.1 `scripts/check_research_evidence_lineage.py` — summary·jsonl 일관성/3종 문서 완결성 읽기 전용 검사
- [x] T6.2 인벤토리 대조 완료 — 7/01 문서의 명시 결정('.gjc/.omo는 별도 인벤토리 없이 커밋 금지') 유효 확인, 보류 유지
- [x] T6.3 고아 프로세스 정리 스크립트(dry-run 기본, 실환경 스모크) + auth 폴백 격차 확정(연구 루프=실존, 발굴 루프=부재 → FailoverProvider 배선안 격차 노트로 이월)
- [x] 검증 41개 통과 + 커밋 221aee7c

## 불변 조건 (모든 Phase 공통)

1. 연구 레인 전용 — `can_promote/export/live=false` 계약 불변
2. `backtest/graph/` 불가침
3. n_trials 정직 합산·부활 레지스트리·OOS-blind 동결 규율 유지
4. 결정론 폴백은 prompt credit 0 규약 유지
5. 기존 테스트 계약 (`test_research_prompt_contracts.py` 등) 파괴 금지
