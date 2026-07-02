# AI 조건식 자율 개선 루프 전수 검사 및 코드 업데이트 계획 (2026-07-02)

> 작성 경위: 사용자 요청으로 설계 문서 / 개발 로그 / 코드 구현 / 실험 증거 / 외부 원리 문서(chart_sulsa v7.0) 5축 병렬 전수 검사 수행 후 종합.
> 성격: research-only 감사 보고서 + 실행 계획. export/live/promotion 권한 변경 없음.

---

## 0부. 요청 커버리지 매트릭스

| # | 사용자 요청 | 수행 내용 | 보고 위치 |
|---|---|---|---|
| 1 | AI 루프 전수 검사 (연구·개발 노트, 프로세스) | 5축 병렬 검토 (프로세스 문서 12+편, 업데이트 로그 41편, 코드 ~60파일, 증거 40+ 디렉터리, 원리 문서 전문) | 1부 |
| 2 | 목적 달성 가능 여부·부족분 | 판정 완료 — 검증기 완성 / 생성기 미배선, 사실 15건 확정 | 1.2절 |
| 3 | 목표·방향 이해 + 퀀트 자문 | 아이디어별 평가 + 자문 7건 | 2부 |
| 4 | 상세 코드 업데이트 계획 | Phase 0~6, 태스크 24개, 파일 단위 | 3부 |
| 5 | 시드 선택/생성 개선 | 격자 시드 생성 설계 (Phase 1) | 3부 P1 |
| 6 | 백테스트 상세 출력→무효 부분 분석→재생성 자료 | Context Pack 배선 + 절 단위 ablation + 거래 원장 (Phase 2) | 3부 P2 |
| 7 | 다중 후보·경향 분석·데이터 축적 | 후보 확대 + 축 원장 + 교차비교 (Phase 3) | 3부 P3 |
| 8 | 명예의 전당 수준 도달 | 측정계 정합 + 포트폴리오 층 (Phase 5) | 3부 P5 |
| 9 | tick/min 전 시간대·시총 구분 광폭 거래 | 시간창 정책 완화 + coverage map (T1.3/T1.4) | 3부 P1 |
| 10 | chart_sulsa v7.0 문서 활용성 | 전문 분석 — 21개 조건식·3계층 주입안 (Phase 4) | 2부·3부 P4 |

미정독 항목(목록만 확인): `.gjc/` 미커밋 증거, `.omo/drafts/` 초안 1건 — T6.2 커밋 정리 시 흡수 예정.

## 1부. 전수 검사 종합 결론

### 1.1 한 줄 결론

**검증기(게이트·OOS·영수증 체계)는 명예의 전당 수준 목표를 감당할 만큼 완성됐지만, 생성기(시드 공급·분석 환류·후보 생산)는 설계만 완성되고 프로덕션에 배선되지 않았다.** 병목은 엔진도 데이터도 게이트도 아닌 "분석 → 후보 연결" 단계다.

### 1.2 교차 검증된 핵심 사실 (5축 일치)

| # | 사실 | 근거 |
|---|---|---|
| 1 | 데이터에 알파 실재, 게이트 정상 — 인간 챔피언 4종 positive control 4/4 통과 (+9.55M~+10.97M) | `docs/update_log/2026-06-16_champion_positive_control_diagnostic.md` |
| 2 | 콜드 LLM 생성은 88회+ 시도 전부 실패 (OOS PROMISING 0/40, 0/8, 0/8, 1/40 smoke) | `.omo/evidence/tmap-walkforward/full_stateful_n40.md`, `ab_*_n8.md` |
| 3 | 유일한 성공 경로 = 인간 시드 + LLM 무관 파라미터 힐클라임 (r8_4 train +13.93M / rr8_12 4/4 연도 OOS gate) | `2026-06-17_ovn_r8_oos_verification_and_freeze.md`, `2026-06-28_12h_followup_research_execution.md` |
| 4 | 힐클라임은 8라운드 만에 국소최적 수렴 (이후 10라운드 증분 0) | `2026-06-17_anchor_mutation_convergence_structural_analogy.md` |
| 5 | 상위 후보 전원 3틱 슬리피지에 음수 전환 (rr8_12: tick0 +15.7M → tick3 -7.5M) | `artifacts/12h-followup-research-20260628/gpt_b_seeded_summary.json` |
| 6 | Context Pack·Analysis Card v2·repair/discovery 프롬프트는 완성·테스트됐으나 **프로덕션 미배선** — 실제 루프 환류는 1,400자 NL 요약뿐 | `ai_strategy_loop/brain/prompt.py:442-584`, `autopsy/summarize.py:42`, 소비처는 `artifacts/process-research-*/run_*.py` 뿐 |
| 7 | 넓은 시드 "생성" 코드 부재 — 고정 시드 1쌍 또는 사후 선택기뿐. band_compiler는 P0 미소비, 분류축 프롬프트 넛지는 기본 OFF | `config.py:216-217`, `brain/band_compiler.py:16`, `config.py:467,470` |
| 8 | tick 연구는 09:00~09:28 정책 고정 | `controller/condition_discovery.py:59-60, 1416-1431` |
| 9 | AND/OR 절 단위 기여도(ablation) 부재 — 6/18 재검토 32% 부족분 | `2026-06-18_condition_research_current_state_rereview.md` |
| 10 | `research_candidate_pack` 생산 코드 부재 → 연구 반복은 실질 결정론 필터식 생성기로 동작 (diagnostic fallback, prompt credit 0) | `cli/research_loop.py:1757-1781` |
| 11 | feature importance 환류는 죽은 배선 (config·프롬프트 슬롯만 있고 `loop.py` 호출 0건) | `config.py:543`, `brain/prompt.py:1167-1173` |
| 12 | 명예의 전당은 대시보드 표시 전용 — 루프 목표함수/종료조건에 미연결 | `dashboard/app.py:740-844`, `reference_strategies.json` |
| 13 | 명예의 전당 수치(연 130~262%, MDD 2~7%)는 **6~12 다중보유 측정계** — 1포지션 니치와 직접 비교 불가 | `2026-06-10_measurement_calibration_audit.md` |
| 14 | baseline replay 불일치: rr8_12 2025 replay가 +3,062,696(06-28) vs +518,822(07-01)로 문서 간 상충 | `2026-06-28_human_process_research_loop.md` vs `2026-07-01_ai_strategy_loop_branch_handoff_commit_record.md` |
| 15 | claim-gap matrix 자가 판정: "강한 연구 플랫폼, 아직 신뢰할 만한 좋은-조건식 공장 아님" confirmed | `.omo/evidence/condition-research-claim-gap-matrix.csv` C02 |

### 1.3 점수 이력과 현재 위치

- 자기개선 점수: 56%(6/15) → 68%(6/17) → 전체 프로세스 72점 / 생성 AI 67점 / **승격 준비도 56점**(6/18). 이후 재채점 없음.
- 최근 실행(6/29~7/02): 6/29 default 분석 후보 0개(`completed_with_no_promotable_candidate`), 7/01 buy 후보 4종 전원 baseline 미달, 7/02 sell-only는 hard-stop 축 1개만 개선(+40,125 / MDD -1.45%p).

---

## 2부. 퀀트/데이터 분석 전문가 자문

### 2.1 사용자 방향("광산 넓게 파기")에 대한 평가

**증거와 정확히 일치하는 올바른 방향이다.** 증거가 보여주는 것: (a) 무에서 창조(cold LLM)는 실패, (b) 좋은 출발점 근방 정제(힐클라임)는 성공하나 국소최적에 갇힘. 따라서 해법은 "좋은 출발점의 수를 체계적으로 늘리고(격자 시드), 정제 단계를 공업화(ablation + 축 원장 + 구조화 환류)"하는 것 — 이것이 곧 사용자가 말한 "금인지 모르지만 많이 캐서 계속 발굴"이다. LLM의 역할을 "알파 발명가"에서 "구조화 데이터를 받는 편집자"로 재정의해야 한다.

### 2.2 핵심 자문 7개

1. **목표 재정의(측정계 정합)**: 연 130~262%는 다중보유 6~12 측정계의 산물. 단일 니치로는 구조적으로 도달 불가. 목표를 "OOS 생존 니치 N개 발굴 → 시간대 상보·상관 캡 포트폴리오 결합 → 동일 측정계에서 명예의 전당 비교"로 재정의하라. 광산 전략과 자연스럽게 결합된다.
2. **거래수 우선 시드(통계 검정력)**: 9건 OOS 창은 진짜 에지도 17~27% 확률로 기각(기록됨). 셀당 거래 수백 건을 만드는 완화 시드는 분석 엔진에 진짜 데이터를 공급하고 거짓 기각을 줄인다. 단 수익 무관 채택이므로 n_trials 정직 합산과 부활 레지스트리 규율을 격자에도 그대로 적용해야 한다.
3. **슬리피지를 1급 시민으로**: 3틱에 전멸하는 후보에 연구 예산을 쓰지 마라. 랭킹 단계부터 tick0/1/2/3 병기, 승격 레인은 hard gate.
4. **절 단위 ablation이 최고 가성비**: 사용자가 원하는 "불필요/무효 부분 식별"은 LLM 없이 결정론으로 가능(거래행 기반 절 평가). 이 결과가 repair 프롬프트의 mutation axis를 데이터로 구속한다.
5. **경향 학습은 축 원장(axis ledger)으로**: (변이축, from→to, Δ지표)를 전 실험에 걸쳐 축적 → 축별 개선확률/평균효과 사전확률 → 프롬프트 주입 + 반복 악화 축 자동 금지. 현재 수동 금지 목록의 데이터화.
6. **원리 문서는 3계층 주입**: chart_sulsa v7.0의 §1.15(원리)/§26+§10(금지·제약)/§2+§4~6(원리→STOM 변수 관용구 사전). 21개 완성 조건식은 가설 시드로 격자에 투입(임계값 무근거이므로 게이트 통과 의무).
7. **재현성 먼저**: baseline replay 불일치(사실 14)를 해소하기 전의 모든 개선 비교는 신뢰 불가. Phase 0가 선행 조건인 이유.

---

## 3부. 상세 코드 업데이트 계획

### Phase 0 — 측정·재현성 기반 정비 (선행 필수)

| 태스크 | 내용 | 대상 파일 | 완료 기준 |
|---|---|---|---|
| T0.1 | baseline replay 정합화: rr8_12 +3,062,696 vs +518,822 원인 규명(엔진 수/기간/유니버스/체결가정), 공식 replay 프로파일 1개를 receipt로 동결 | `cli/research_loop.py`(baseline replay), 신규 `ai_strategy_loop/controller/replay_profile.py`, 회귀 테스트 | 동일 seed 2회 replay 손익 오차 0, 프로파일 sha256 영수증 |
| T0.2 | 슬리피지 다중 프로파일 지표화: tick0/1/2/3 손익·MDD 병기, 연구 레인 advisory / 승격 레인 hard gate | `ai_strategy_loop/fitness/`(`_score_outcome` 경유 `controller/loop.py:2392`), `cli/research_ranking.py:149`, `controller/condition_discovery.py`(승격 프리셋) | 모든 후보 결과에 4프로파일 기록, 승격 게이트에 tick2 흑자 조건 |
| T0.3 | 측정계 이원화: niche(1포지션, seed-relative) vs portfolio(다중보유) 지표 필드 분리, 명예의 전당 비교는 portfolio 프레임 전용 계약 | `cli/research_metrics.py`, `dashboard/backtest_report.py` | 리포트에 프레임 라벨 필수화, 교차 비교 시 경고 |

### Phase 1 — 시드 격자(Seed Lattice): 광산 넓게 파기

| 태스크 | 내용 | 대상 파일 | 완료 기준 |
|---|---|---|---|
| T1.1 | 격자 열거기: 시간밴드(tick 5분 버킷 / min 6버킷=기존 36셀 지도 재사용) × 시총 4단계 × 등락률 국면 3 × 패턴 패밀리(chart_sulsa 12패턴군 + F-원리 생존 계열). 셀당 완화 임계 시드 자동 생성, 목표는 수익이 아니라 **거래수(셀당 train ≥300건)** | 신규 `ai_strategy_loop/seeds/lattice.py`, 신규 `cli/seed_lattice.py` | 격자 정의 JSON + 셀별 시드 코드 산출 |
| T1.2 | band_compiler 소비 배선: 밴드→코드 컴파일러를 격자 시드 빌드에 사용 (현재 P0 미소비) | `brain/band_compiler.py`, `seeds/lattice.py` | 컴파일러 경유 시드가 빌드 가드(compile/token/scope/시간무결성) 통과 |
| T1.3 | tick 시간창 정책 완화(연구 레인 한정): 09:00~09:28 강제를 research 프리셋에서 configurable로. **선행: tick DB의 09:30 이후 커버리지 실측** — 데이터가 없으면 min 레인으로 대체 | `controller/condition_discovery.py:59-60, 1416-1431` | 연구 프리셋에서 창 설정 가능 + 승격 레인은 기존 고정 유지 |
| T1.4 | coverage map 산출기: 셀×(시드 수, 거래수, 손익분포) 아티팩트 — discovery 프롬프트 계약의 미구현 입력 `coverage_gap`(`prompt.py:665-717`)을 실데이터로 공급 | 신규 `ai_strategy_loop/seeds/coverage.py`, `dashboard/`(패널) | discovery 레인 프롬프트에 coverage_gap 실주입 |
| T1.5 | 스모크 예산 연동: 기존 smoke protocol(go/no-go -2M, 창 비례 축소)을 셀 단위 적용 + 부활 레지스트리 등재 | `cli/research_loop.py`, `2026-06-12_smoke_screening_protocol.md` 준수 | n_trials 정직 합산 유지 확인 테스트 |

### Phase 2 — 상세 백테스트 분석 → 구조화 환류 (프로덕션 배선)

| 태스크 | 내용 | 대상 파일 | 완료 기준 |
|---|---|---|---|
| T2.1 | Context Pack 생산자 승격: `artifacts/process-research-validation-20260701/run_process_research_validation.py:506`의 주입 로직을 컨트롤러 모듈로 이관, `run_research_iteration`(`research_loop.py:1633`)과 진화 루프에 배선 | 신규 `ai_strategy_loop/controller/context_pack_builder.py`, `cli/research_loop.py`, `controller/loop.py` | 모든 연구 run에서 250k 예산 내 pack 자동 생성 (기존 `test_research_prompt_contracts.py` 계약 통과) |
| T2.2 | Analysis Card v2 생산자: autopsy 산출물(세그먼트 cross-tab `segment.py:189-325`, MFE/MAE·worst_sell_rule `analyze.py:398-562`)을 카드 스키마로 조립 + edge_ratio/feature importance/상관 중복 계산 | 신규 `ai_strategy_loop/autopsy/analysis_card.py` | 카드가 pack의 분석 섹션을 채움, 대시보드 노출 |
| T2.3 | **절(clause) 단위 기여도 엔진**: 매수/매도식 최상위 AND/OR 절 분해 → 거래행 기반 절 통과율·제거 시 Δprofit/ΔMDD/Δtrades·절간 중복도 → "무효 절/유해 절" 목록 → Analysis Card root_cause + repair mutation axis 입력 | 신규 `ai_strategy_loop/autopsy/ablation.py` | 6/18 부족분 "branch별 기여도 32%" 해소, 카드에 절 기여 테이블 |
| T2.4 | 죽은 배선 수리: `build_feature_importance_lines` 호출을 `controller/loop.py`에 추가, 관련 토글을 연구 프리셋에서 기본 ON (`segment_feedback:380`, `quantile_feedback:524`, `hypothesis_tracking:609`, `feature_importance:543`) | `controller/loop.py`, `config.py` | 프롬프트 영수증에 prefer/avoid 힌트 실제 포함 |
| T2.5 | 거래 원장 보존: 후보별 전체 거래행 + 진입 컨텍스트 피처 parquet 영속 → 교차 후보 코호트 분석 기반 | 신규 `ai_strategy_loop/autopsy/trade_ledger.py` | 후보 간 동일 거래일 비교 쿼리 가능 |

### Phase 3 — 다후보 생성·경향 학습

| 태스크 | 내용 | 대상 파일 | 완료 기준 |
|---|---|---|---|
| T3.1 | LLM 후보팩 생산 경로: repair(`prompt.py:611-662`)/discovery(`prompt.py:665-717`) 프롬프트 실호출로 `research_candidate_pack` 생산 → `research_loop.py:1757` 배선. LLM 장애 시 결정론 폴백 유지(prompt credit 0 규약 유지) | 신규 `ai_strategy_loop/brain/pack_producer.py` | LLM 팩 사용률 ≥80% (영수증 기준) |
| T3.2 | 라운드 후보 4→8~12 확대 + 레인 쿼터(repair/discovery/sell-only/principle-seeded) + 병렬 백테 | `controller/condition_discovery.py:70-72`, `cli/research_loop.py:233-236` | 슬롯 재배분 로직(`condition_discovery.py:1111-1247`)과 정합 |
| T3.3 | **축 원장(axis ledger)**: (변이축, from→to, Δ지표) JSONL 전 실험 축적 → 축별 사전확률(개선확률·평균효과·분산) 집계 → repair 프롬프트 주입 + 반복 악화 축 자동 금지 | 신규 `ai_strategy_loop/controller/axis_ledger.py` | 수동 금지 목록(`turnover_min 1.5→3.0` 등)이 데이터로 재현됨 |
| T3.4 | 라운드 교차비교 매트릭스: 후보×지표 + 변이 귀속 리포트 영속 + 대시보드 | `cli/research_compare.py` 확장, `dashboard/` | 라운드마다 비교 아티팩트 자동 생성 |

### Phase 4 — 원리 문서 주입 (chart_sulsa v7.0)

| 태스크 | 내용 | 대상 파일 | 완료 기준 |
|---|---|---|---|
| T4.1 | 3계층 추출: `principles.md`(§1.15 마스터 프롬프트 0~28장), `constraints_checklist.md`(§26 AI 금지 7개조+§10 검증 주의), `idiom_dictionary.md`(§2 수식 변환+§4~6 원리→STOM 변수 관용구) | `utility/ai_agent/system_prompt/v1/` 신규 3파일, Context Pack 소스 등록 | 예산 내 포함, fail-closed 유지 |
| T4.2 | 21개 완성 조건식(tick 매수3+매도2, min 매수7+매도5, 통합·최적화형)을 격자 패턴 패밀리 시드로 등록, `self.vars` 범위(tick 27, min 31)를 변이 경계로 등록 | `seeds/lattice.py` 데이터, `condition_passports/` 자동 생성 | 전부 "가설 시드" 라벨 + 게이트 통과 의무 |
| T4.3 | strict validation에 원리 일관성 필드: 후보 메타데이터에 principle_id 요구, 금지사항 위반 검증(예: 거래량 없는 돌파, 손절 없는 매수식) | `brain/prompt.py`(`validate_research_candidate_response:720-800`) 확장, `brain/generator.py` PRE-SAVE 게이트 | 위반 후보 저장 전 거부 |

### Phase 5 — 명예의 전당 벤치마크·포트폴리오 층

| 태스크 | 내용 | 대상 파일 | 완료 기준 |
|---|---|---|---|
| T5.1 | 벤치마크 루프 연결: `reference_strategies.json`을 주기적 positive control 자동 실행(게이트 건전성 감시) + 니치=seed-relative / 포트폴리오=명예의 전당 상대 지표(TPI·payoff·MDD비) 산출 | `controller/loop.py`, `fitness/champion_challenger.py` 재활용 | positive control 4/4 유지가 정기 receipt로 남음 |
| T5.2 | 포트폴리오 조립기: OOS 생존 니치들을 시간대 상보성+상관 캡(<0.5)으로 결합 → 다중보유 백테 → 동일 측정계 비교 (기존 combined portfolio 연구의 공식화) | 신규 `ai_strategy_loop/portfolio/assembler.py` | 포트폴리오 OOS vs THETA/T2C3 정기 리포트 |
| T5.3 | 승격 전제 유지: promotion-review zero-generation + 슬리피지 hard gate + capacity 점검 | `controller/condition_discovery.py` | export/live/final promotion 금지 불변 |

### Phase 6 — 증거·운영 위생

| 태스크 | 내용 | 완료 기준 |
|---|---|---|
| T6.1 | evidence lineage 자동화 (summary/jsonl consistency, campaign registry — 6/18 30% 부족분) | lineage 검사 스크립트 + CI |
| T6.2 | 미커밋 evidence(`.gjc/`, `.omo/`) 커밋 계획 실행 (7/01 §7.4 보류분) | 인벤토리 문서와 대조 후 커밋 |
| T6.3 | LLM auth 이중화(GPT OAuth 장애 fallback), 고아 `--multiprocessing-fork` 정리 자동화(06-19 사례) | 장애 시 결정론 폴백 자동 전환 로그 |

### 실행 순서와 근거

```
Phase 0 (재현성·슬리피지)  ──선행 필수──▶  Phase 2 (분석·환류 배선)  ──▶  Phase 3 (다후보·축 원장)
        │                                        ▲
        └──병렬 가능──▶  Phase 1 (시드 격자) ────┘ (coverage_gap 공급)
                              │
                              └── Phase 4 (원리 시드) 는 Phase 1 데이터 준비와 병행 (LLM 불요)
Phase 5 (포트폴리오·벤치마크) 는 OOS 생존자가 2개+ 확보된 후
Phase 6 은 상시 병행
```

- Phase 0 없이는 모든 개선 비교가 신뢰 불가 (baseline 불일치).
- Phase 2가 Phase 3보다 먼저인 이유: 환류 데이터 품질이 후보 품질의 상한 (6/29 자가진단 — 병목은 분석→후보 연결).
- Phase 1·4는 LLM 의존이 없어 병렬 진행 가능하고, 즉시 거래 표본을 늘려 Phase 2의 분석 재료를 공급.

### 리스크와 결정 지점

1. **tick DB 시간 커버리지**: 09:30 이후 tick 데이터 실존 여부 실측 후 T1.3 범위 확정 (기존 교훈 "시간 확장은 일관되게 악화"는 동일 임계 이식의 실패였음 — 격자는 셀별 독립 임계이므로 다름).
2. **min DB 11개월**: 연 단위 OOS 불가 — min 레인은 월 단위 walk-forward advisory로 기대치 설정.
3. **연산 예산**: ablation·8~12후보는 백테 부하 증가 — 거래행 기반 절 평가(재백테 회피), 스모크 예산, 32/64 엔진 벤치마크 결과 재사용으로 완화.
4. **탐색 확대 = 과최적화 위험 확대**: n_trials 정직 합산·부활 레지스트리·OOS-blind 동결을 격자 전체에 확장 적용. DSR/PBO advisory 승격 검토.
5. **원리 문서 임계값 무근거**: 전부 가설 시드로 취급, 게이트 통과 전 어떤 주장도 금지.

### 성공 지표 (KPI)

| Phase | KPI |
|---|---|
| 0 | replay 재현 오차 0, 전 후보 슬리피지 4프로파일 기록률 100% |
| 1 | 격자 셀 커버리지 ≥80%, 신규 거래 표본 수 (셀당 ≥300건) |
| 2 | Context Pack/Analysis Card/ablation 자동 생성률 100%, prompt credit>0 비율 |
| 3 | LLM 팩 사용률 ≥80%, 라운드당 baseline 초과 후보 비율 (현재 ~0), 축 원장 인용 영수증 |
| 4 | 원리 시드 스모크 통과율·거래수 (콜드 LLM 0/40 대비 개선 폭) |
| 5 | 포트폴리오 OOS 지표 vs THETA(+10.97M)/T2C3, 3틱 슬리피지 생존 여부 |
| 최종 | 동일 측정계 포트폴리오 프레임에서 명예의 전당(연 130~262%, MDD 2~7%, TPI 1.25+) 대비 격차 추적 |
