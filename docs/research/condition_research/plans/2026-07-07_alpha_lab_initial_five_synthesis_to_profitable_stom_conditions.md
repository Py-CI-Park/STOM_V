# 알파 랩 초기 5개 아이디어 종합 — 수익형 STOM 조건식으로 가는 재사용 로드맵 (2026-07-07)

> 범위: 본 문서는 기존 증거 문서를 보존한 채, 초기 5개 알파 랩 아이디어가 v1~v5를 거치며 무엇을 남겼고 이후 “수익형 STOM 조건식” 개발에 어떻게 재사용돼야 하는지 정리하는 문서 전용 종합본이다. 코드 변경, DB 쓰기, 엔진 실행, 전략 등록은 이 문서 패키지의 권한 밖이다.
>
> 주요 근거: `docs/research/condition_research/plans/2026-07-07_alpha_lab_master_handoff_ideas_to_deployment.md`, `docs/research/condition_research/plans/2026-07-04_new_alpha_research_program.md`, `docs/research/condition_research/plans/2026-07-05_new_alpha_implementation_design.md`, `docs/update_log/2026-07-06_alpha_lab_management_report_cycle1.md`, `docs/research/condition_research/plans/2026-07-06_alpha_lab_root_cause_and_v3_plan.md`, `docs/update_log/2026-07-07_alpha_lab_three_cycle_synthesis_and_decision.md`, `docs/research/condition_research/research_runs/alpha_lab_20260705/p5_engine_confirmation.md`, `docs/research/condition_research/research_runs/alpha_lab_v4_20260707/v4_final_verdict.md`, `docs/update_log/2026-07-07_alpha_lab_v4_supervised_deployment_protocol.md`.

---

## 1. Executive conclusion

초기 5개 아이디어의 최종 결론은 단순하다. **데이터에서 새 단독 매수 조건식을 직접 캐내는 상위 아이디어 1·2·3은 현재 증거 기준으로 배포 가능한 알파를 만들지 못했다.** 반면 **검증된 챔피언을 원형 그대로 보존하고 단순하게 조립한 v4 정적 등가중 앙상블은 감독형 제약 아래 수익형 자산 후보가 됐다.** 이 결론은 `docs/research/condition_research/plans/2026-07-07_alpha_lab_master_handoff_ideas_to_deployment.md`와 `docs/research/condition_research/research_runs/alpha_lab_v4_20260707/v4_final_verdict.md`의 사이클별 결과를 종합한 것이다.

따라서 이후 “수익형 STOM 조건식”은 다음 중 하나로 정의해야 한다.

1. **단일 신규 조건식**: 현재 증거로는 미확정이다. v1/v2/v3 데이터-우선 채굴은 ranking/lift 신호를 보였지만 단독 경제성으로 번역되지 않았다.
2. **검증 챔피언의 원문 조건식 묶음**: v4 정적 4챔피언 등가중처럼 기존 조건식을 수정하지 않고 1/4 고정 비중으로 운용하는 포트폴리오형 조건 집합은 감독형 후보가 될 수 있다.
3. **조건식 개발의 상류 자산**: 실패한 규칙·이벤트·필터·청산 후보는 “하지 말아야 할 탐색 공간”을 좁히는 부정 지도이며, 후속 개발의 비용 절감 자산이다.

비협상 결론은 다음과 같다.

- P5의 전역 청산 교체 후보 `hard_stop -5 + time_stop 300`은 엔진 확인에서 기각됐고 현행 챔피언 매도식이 기준선이다. 근거: `docs/research/condition_research/research_runs/alpha_lab_20260705/p5_engine_confirmation.md`.
- v4의 성공은 적응형 타이밍이나 레짐 로테이션이 아니라 **정적 1/4 등가중 다각화**다. 근거: `docs/research/condition_research/research_runs/alpha_lab_v4_20260707/v4_final_verdict.md`.
- v4의 2025-01~2026-02 성과는 현재 시점의 알려진 감사 증거다. 당시 봉인 판정에는 미개봉 OOS였더라도, 향후 연구에서 이를 fresh blind OOS로 다시 주장하면 안 된다.
- 이 문서 패키지는 문서화만 승인한다. 소스 코드, DB, 엔진, 백테스트, 전략 등록, 운영 설정을 변경하지 않는다.

---

## 2. Evidence timeline: original five ideas → v1 → v2 → v3 → v4/v4.1/v5 → Idea5 foundation

### 2.1 원안: 다섯 아이디어와 점수

원안은 백테스트를 후보 생성기의 반복 평가자가 아니라 **최종 심판**으로 낮추고, 후보 발견을 오프라인 분석으로 옮기는 구조였다. 초기 점수는 다음과 같다. 근거: `docs/research/condition_research/plans/2026-07-07_alpha_lab_master_handoff_ideas_to_deployment.md`.

| 아이디어 | 원안 점수 | 원래 의도 | 원안 기대 |
|---|---:|---|---|
| Idea1 규칙 채굴 | 83 | 전수 시점 전향 라벨 + 얕은 트리 증류 | 데이터에서 STOM 문법으로 번역 가능한 매수 규칙 직접 추출 |
| Idea2 이벤트 스터디 | 82 | 사전등록 사건의 조건부 수익 분포 측정 | FDR 생존 사건만 조건식 시드화 |
| Idea3 미시구조 레이어 | 77 | 검증 챔피언 위의 필터·베토·청산가속 | 챔피언의 꼬리 손실 억제 |
| Idea5 챔피언 청산/증류 | 75 | 챔피언 원장의 반사실 경로 재생 | 진입 필터 또는 청산 정책 개선 |
| Idea4 레짐 게이트 | 71 | 일 단위 시장 상태로 포트폴리오 on/off·배정 | 새 조건식보다 상위 운용 규칙 개선 |

핵심 공통 원리는 “오프라인 발견, 백테스트/엔진은 최종 심판”이었다. 이는 후속 문서에서도 유지해야 할 안전장치다.

### 2.2 v1: 인프라는 구축됐지만 배포 알파는 없음

v1은 P1/P2/P3/P5를 실제로 구현·측정했다. 결과는 다음과 같이 요약된다. 근거: `docs/update_log/2026-07-06_alpha_lab_management_report_cycle1.md`, `docs/research/condition_research/plans/2026-07-07_alpha_lab_master_handoff_ideas_to_deployment.md`.

- P1 규칙 채굴: 교차창 ranking/lift 신호는 있었고 번역도 수행됐지만, 단독 매수식은 엔진에서 수익성을 확보하지 못했다.
- P2 이벤트: 42,363개 이벤트와 138개 셀을 측정했으나 FDR 생존 셀이 0개였다.
- P3 미시구조 레이어: 챔피언 재조인 표본 346개로, 봉인 최소 2,000개에 크게 미달해 판정 불가였다.
- P5 청산: 리플레이 게이트는 강했지만 엔진 확인에서 전역 청산 후보가 기각됐다.

이 단계의 산출물은 deployable alpha가 아니라 **재사용 가능한 인프라와 부정 증거**다.

### 2.3 v2: 라벨을 실전형으로 바꿔도 채굴은 실패

v2는 규칙 채굴의 라벨을 고정지평 라벨에서 챔피언 매도식 리플레이 실현손익으로 교체하고, 산출물을 단독 매수식이 아니라 챔피언 필터로 바꾸는 개선이었다. 결과는 필터 6종 전멸이었다. 근거: `docs/research/condition_research/plans/2026-07-07_alpha_lab_master_handoff_ideas_to_deployment.md`, `docs/update_log/2026-07-07_alpha_lab_three_cycle_synthesis_and_decision.md`.

이는 “라벨만 실전화하면 데이터-우선 채굴이 살아난다”는 가설을 반증했다.

### 2.4 v3: 파생 피처와 EV 기준까지 넣어도 양EV 채택 0

v3는 엔진과 100% 패리티가 검증된 파생 피처 18항을 추가하고, 채택 기준을 lift가 아니라 EV로 바꾸며, 힐클라임까지 붙인 최종 정제였다. 결과는 EV 채택 0/107, 최선 리프 EV -0.087%, 힐클라임 시드 전멸이었다. 근거: `docs/research/condition_research/plans/2026-07-06_alpha_lab_root_cause_and_v3_plan.md`, `docs/update_log/2026-07-07_alpha_lab_three_cycle_synthesis_and_decision.md`.

따라서 v1/v2/v3는 “데이터-우선 채굴로 새 단독 수익 조건식을 만든다”는 방향이 현재 데이터·해상도·문법에서는 실패했다는 재현된 결론을 남긴다.

### 2.5 v4: 정적 등가중 앙상블만 성공

v4는 방향을 바꿔 검증 챔피언 4종을 조립했다. 최종 성공 후보는 `RR8_12`, `RR8_0`, `RR8_21`, `GPTAUTH_G8` 원본 조건식을 각 1/4 동일 비중으로 병행하는 `ensemble_a_static_equal`이다. OOS 2025-01~2026-02 결과는 수익 약 2,608,362원, MDD 약 493,590/493,591원, calmar 약 5.28이었다. 근거: `docs/research/condition_research/research_runs/alpha_lab_v4_20260707/v4_final_verdict.md`, `docs/update_log/2026-07-07_alpha_lab_v4_supervised_deployment_protocol.md`.

중요한 제한은 다음과 같다.

- 적응형 합산, 단일 적응형, 레짐 로테이션은 OOS에서 개선 실패했다.
- 성공 원인은 타이밍 예측이 아니라 손익 비동조에 따른 정적 다각화다.
- 동일비중 1/4 고정, 비중 최적화 금지, 소액 감독형 운용, 약 740k 킬스위치, 미래 데이터 재검증이 필수 제약이다.
- 2025-01~2026-02는 현재 문서 작성 시점에 이미 알려진 감사 증거이므로 향후 fresh blind OOS로 재사용할 수 없다.

### 2.6 v4.1: 견고성 보강

v4.1은 v4 정적 등가중의 견고성을 보강했다. 마스터 핸드오프는 4창 walk-forward와 몬테카를로 결과를 통해 다각화 MDD 감소가 4/4창 견고하고 OOS 위험조정 우위 확률이 75%라고 기록한다. 근거: `docs/research/condition_research/plans/2026-07-07_alpha_lab_master_handoff_ideas_to_deployment.md`.

이 보강은 v4를 “완전 자동 배포”가 아니라 “감독형 후보”로 올리는 수준이다. 미래 데이터 검증 의무는 사라지지 않는다.

### 2.7 v5: 비상관 확장 시도는 재료 부족으로 중단

v5는 비상관 전략 추가로 앙상블 상관을 낮추려 했으나, 후보들이 구식 엔진 API 문제로 실행 불가해 kill됐다. 근거: `docs/research/condition_research/plans/2026-07-07_alpha_lab_master_handoff_ideas_to_deployment.md`, `docs/update_log/2026-07-07_alpha_lab_v4_supervised_deployment_protocol.md`.

결론은 현재 실행 가능한 재료의 천장이 rr8 계보와 GPTAUTH_G8 조합이며, 추가 확장은 현행 API로 실행 가능한 비상관 신규 전략이 필요하다는 것이다.

### 2.8 Idea5 foundation: replay는 triage, engine은 final judge

Idea5의 리플레이는 강한 후보 선별기로 유용했지만, 전역 청산 교체의 최종 판정은 엔진에서 기각됐다. `hard_stop -5 + time_stop 300`은 full window에서 방향성은 양(+)이었으나 95% CI가 0을 포함했고, 2024/2025에서 역전됐으며, MDD가 5개 창 중 4개에서 악화됐다. 근거: `docs/research/condition_research/research_runs/alpha_lab_20260705/p5_engine_confirmation.md`.

따라서 미래 Idea5는 리플레이를 최종 증명으로 쓰면 안 된다. 리플레이는 후보를 줄이는 triage이며, 별도 승인 후 엔진 확인이 최종 심판이다.

---

## 3. Final verdict table by idea

| 아이디어 | 최종 판정 | 살릴 것 | 버릴 것/금지 | 주요 근거 |
|---|---|---|---|---|
| Idea1 규칙 채굴 | 실패했지만 부정 지도와 번역 인프라 재사용 | ranking/lift 진단, STOM 문법 번역기, 피처 패리티 검증, 실패 규칙 원장 | lift 높은 규칙을 곧바로 단독 매수식으로 주장 | `docs/update_log/2026-07-07_alpha_lab_three_cycle_synthesis_and_decision.md` |
| Idea2 이벤트 스터디 | 현재 사건 카탈로그로는 생존 이벤트 0 | 사전등록·FDR 절차, 사건 측정 프레임, 기저율 표 | FDR 0인 사건을 조건식 시드로 포장 | `docs/research/condition_research/plans/2026-07-07_alpha_lab_master_handoff_ideas_to_deployment.md` |
| Idea3 미시구조 레이어 | 표본 부족으로 inconclusive | 챔피언 위에만 얹는 조건부 레이어 원칙, 표본 하한 2,000 | 표본 346개 결과를 성공/실패로 과잉 판정 | `docs/research/condition_research/plans/2026-07-07_alpha_lab_master_handoff_ideas_to_deployment.md` |
| Idea4 레짐 게이트 | 원형 레짐 타이밍은 실패, 포트폴리오 사고 일부만 생존 | 포트폴리오 수준 위험 배정 문제의식, 상관·다각화 관찰 | adaptive timing, regime rotation 성공 주장 | `docs/research/condition_research/research_runs/alpha_lab_v4_20260707/v4_final_verdict.md` |
| Idea5 챔피언 청산/증류 | 리플레이 triage는 유용, 전역 청산 교체는 기각 | 챔피언 원장, 반사실 재생, 엔진 확인 절차, 정적 앙상블 재료 | hard_stop -5 + time_stop 300 채택 주장, 리플레이만으로 최종 확정 | `docs/research/condition_research/research_runs/alpha_lab_20260705/p5_engine_confirmation.md` |

---

## 4. Common root causes

### 4.1 통계적 신호와 거래 가능 EV의 간극

v1/v2/v3는 ranking, lift, 교차창 재현 같은 통계 신호가 있어도 비용과 손실 발화를 이기는 거래 EV로 번역되지 않을 수 있음을 보였다. `docs/update_log/2026-07-07_alpha_lab_three_cycle_synthesis_and_decision.md`는 lift가 높은 규칙도 모든 참 시점에 거래하면 다수 손실 발화가 소수 승리를 압도한다고 해석한다.

### 4.2 단독 조건식 문법의 표현 한계

챔피언의 엣지는 단일 상태 임계값이 아니라 손튜닝된 조합, 진입·청산·보유·베팅 상호작용에 있었다. 얕은 트리와 축-정렬 규칙은 이 상호작용을 포착하기 어렵다. 따라서 “규칙 하나를 캐면 된다”는 가정이 약했다.

### 4.3 표본과 레짐의 부족

Idea3는 재조인 표본 346개로 봉인 하한 2,000개에 미달했다. Idea4 원형은 레짐 사건 수가 작고, v4에서도 adaptive timing과 regime rotation이 OOS에서 실패했다. 작은 표본의 레짐 설명은 향후에도 가설 생성까지만 허용해야 한다.

### 4.4 오프라인 후보와 엔진 현실의 차이

P5는 리플레이에서 강했지만 엔진에서 최근 연도 역전, CI 0 포함, MDD 악화가 드러났다. 체결 컨벤션, 슬롯 점유, 재진입, 현행 매도식의 미세 절 등 엔진 현실을 오프라인 모델이 모두 대체하지 못했다. 근거: `docs/research/condition_research/research_runs/alpha_lab_20260705/p5_engine_confirmation.md`.

### 4.5 복잡한 적응보다 단순한 다각화가 강했다

v4의 승자는 discovery 창 순위 8위였던 정적 등가중이었다. 반대로 적응형 단일, 적응형 합산, 레짐 로테이션은 실패했다. 이는 과적합 위험이 큰 동적 타이밍보다 무파라미터 1/N 다각화가 현재 증거에서 더 견고하다는 뜻이다. 근거: `docs/research/condition_research/research_runs/alpha_lab_v4_20260707/v4_final_verdict.md`.

---

## 5. Reuse asset map

| 자산 | 출처 아이디어/사이클 | 재사용 방식 | 사용 전 조건 |
|---|---|---|---|
| 사전등록·봉인·n_trials 원장 | 전 사이클 | 후속 연구의 스누핑 방어 템플릿 | 새 가설마다 새 봉인과 별도 승인 필요 |
| 피처 패리티와 번역 경로 | Idea1/v1~v3 | STOM 문법 변환 가능성 점검, 실패 규칙 재현 | 번역 성공을 수익성으로 오인 금지 |
| 실패 규칙·EV 0 원장 | Idea1/v3 | 재탐색 금지 구역, 후보 중복 제거 | 유사 피처/라벨이면 먼저 원장 대조 |
| 이벤트 측정 프레임 | Idea2/v1 | 새 사건 카탈로그 검증, 기저율 측정 | FDR 생존 전에는 시드화 금지 |
| MCL 표본 하한 규율 | Idea3/v1 | 챔피언 필터 연구의 표본성 검문 | 최소 2,000개 또는 별도 승인된 새 설계 필요 |
| P5 반사실 리플레이 | Idea5/v1 | 청산 후보 triage, 후보 수 축소 | 리플레이 통과 후에도 엔진 확인 필수 |
| P5 엔진 기각 기록 | Idea5/v1 | hard_stop/time_stop 계열 재제안 방지 | 새 레짐 조건부 청산은 새 봉인과 새 n_trials 필요 |
| v4 4챔피언 원문 | Idea5+Idea4/v4 | 감독형 등가중 후보, 비교 기준선 | 1/4 고정, 원문 조건식 불변, 소액 감독 |
| v4 실패한 adaptive/regime 결과 | Idea4/v4 | 타이밍 오버레이 재사용 방지 | 미래 fresh data와 별도 승인 없이는 성공 주장 금지 |
| v5 실행 불가 후보 기록 | v5 | 비상관 확장 후보 필터 | 현행 API 실행 가능성 선검증 |

---

## 6. What “profitable STOM condition expression” can mean after current evidence

현재 증거 이후 “수익형 STOM 조건식”이라는 표현은 엄격하게 분리해야 한다.

### 6.1 허용 의미 A — 검증된 원문 조건식의 포트폴리오형 운용

v4 정적 등가중은 새로운 단일 조건식이 아니라 네 개의 기존 조건식을 원문 그대로 병행하는 운용 규칙이다. 이 경우 수익형이라는 말은 “각 조건식의 원문을 보존하고 1/4 고정 비중으로 합산했을 때 알려진 감사창에서 위험조정이 개선됐다”는 뜻이다. 근거: `docs/research/condition_research/research_runs/alpha_lab_v4_20260707/v4_final_verdict.md`, `docs/update_log/2026-07-07_alpha_lab_v4_supervised_deployment_protocol.md`.

### 6.2 허용 의미 B — 후속 개발의 후보 시드

Idea1/2/3의 산출물 중 일부는 직접 수익 조건식이 아니라 후보 시드, 금지 구역, 측정 프레임으로 유용하다. “수익형으로 가는 조건식 연구 자산”이라고 부를 수는 있지만, deployable condition이라고 부르면 안 된다.

### 6.3 허용 의미 C — 미래 fresh data로 재검증된 신규 조건식

향후 2026-03 이후 등 현재 문서에 알려지지 않은 데이터에서 별도 봉인, 별도 승인, 별도 엔진 확인을 통과하면 신규 수익 조건식으로 인정할 수 있다. 단, 2025-01~2026-02를 다시 fresh blind OOS로 쓰는 것은 불가하다.

### 6.4 금지 의미 — 실패 후보의 포장

다음은 수익형 조건식으로 표현하면 안 된다.

- v1/v2/v3 채굴 규칙 자체.
- FDR 생존 0인 이벤트 셀.
- 표본 346개에 그친 MCL 결론.
- P5 `hard_stop -5 + time_stop 300` 전역 청산 교체.
- v4 adaptive timing, single adaptive variants, regime rotation.

---

## 7. Future roadmap with approval gates

### Gate 0 — 문서 증거 동결

- 이 문서와 per-idea 문서를 먼저 읽고, C-001~C-015 claim ledger를 기준으로 새 주장을 대조한다.
- 기존 실패를 성공처럼 재명명하지 않는다.
- 산출물: 새 연구 질문 1개와 참조 claim 목록.

### Gate 1 — 새 가설 승인

- 가설은 기존 실패 공간과 어떻게 다른지 명시해야 한다.
- 새 데이터, 새 표본, 새 조건부 레짐, 새 엔진 확인 예산 중 무엇이 필요한지 분리한다.
- 승인 전에는 DB 쓰기, 전략 등록, 엔진 실행, 백테스트 실행을 하지 않는다.

### Gate 2 — 사전등록·봉인

- 측정 전 success/fail/partial 기준, 표본 하한, n_trials 예산, 금지된 사후 선택을 봉인한다.
- 2025-01~2026-02는 known/audit evidence로 표기하고 fresh blind로 쓰지 않는다.

### Gate 3 — 오프라인 triage

- Idea1/2/3/5 인프라를 이용해 후보 수를 줄인다.
- triage 통과는 최종 증명이 아니다.
- 중복 후보는 실패 원장과 먼저 대조한다.

### Gate 4 — 엔진 확인 승인

- 오프라인 후보가 통과하면 별도 승인으로 엔진 확인 범위와 예산을 연다.
- P5 사례처럼 CI, 연도별 역전, MDD 악화, 거래수 변화, 체결 컨벤션 차이를 모두 기록한다.

### Gate 5 — 감독형 배포 후보 판정

- v4 기준선과 비교한다.
- 단일 수익 최대화가 아니라 수익/MDD, calmar, 창별 안정성, 킬스위치 가능성을 본다.
- 감독형 소액 운용 전에는 동일비중·무최적화·kill-switch·미래 재검증 조건을 문서화한다.

### Gate 6 — 미래 데이터 재검증

- 2026-03 이후 등 현재 문서에 알려지지 않은 데이터를 별도 future OOS로 사용한다.
- 통과 전까지 “실전 보장”, “자동 배포 가능”, “fresh OOS 재확인 완료”라고 쓰지 않는다.

---

## 8. Non-negotiable constraints and invalid claims

### 8.1 비협상 제약

1. 문서 패키지는 소스 코드 변경, DB 쓰기, 엔진 실행, 백테스트 실행, 전략 등록을 승인하지 않는다.
2. v4 후보는 4개 원문 조건식의 동일비중 1/4 고정 운용으로만 설명한다. 비중 최적화, 파라미터 조정, 타이밍 오버레이는 다른 가설이다.
3. P5 리플레이는 triage이며 엔진 확인이 최종 심판이다.
4. 2025-01~2026-02는 향후 연구에서 known/audit evidence다.
5. 실패한 채굴 결과는 재사용 가능 자산이지만 deployable alpha가 아니다.

### 8.2 무효 주장 목록

| 무효 주장 | 왜 무효인가 | 반박 근거 |
|---|---|---|
| “Idea1 규칙 채굴은 수익 매수식을 만들었다.” | ranking/lift는 있었지만 단독 매수식은 unprofitable이었다. | `docs/update_log/2026-07-07_alpha_lab_three_cycle_synthesis_and_decision.md` |
| “Idea2 사건은 조건식으로 바로 쓰면 된다.” | 42,363 이벤트·138 셀에서 FDR survivor 0이었다. | `docs/research/condition_research/plans/2026-07-07_alpha_lab_master_handoff_ideas_to_deployment.md` |
| “Idea3 MCL은 실패 또는 성공이 확정됐다.” | 표본 346<2,000이라 inconclusive다. | `docs/research/condition_research/plans/2026-07-07_alpha_lab_master_handoff_ideas_to_deployment.md` |
| “P5 hard_stop -5 + time_stop 300을 채택해야 한다.” | CI 0 포함, 2024/2025 역전, MDD 4/5창 악화로 기각됐다. | `docs/research/condition_research/research_runs/alpha_lab_20260705/p5_engine_confirmation.md` |
| “v4는 adaptive timing 또는 regime rotation 성공이다.” | OOS에서 adaptive와 rotation은 실패했고 static equal만 성공했다. | `docs/research/condition_research/research_runs/alpha_lab_v4_20260707/v4_final_verdict.md` |
| “v4 결과는 앞으로도 fresh blind OOS로 쓸 수 있다.” | 현재 이미 알려진 감사 증거이므로 future blind가 아니다. | `docs/update_log/2026-07-07_alpha_lab_v4_supervised_deployment_protocol.md` |
| “이 문서만으로 배포·등록·엔진 실행이 승인됐다.” | 본 문서는 docs-only 합성 로드맵이다. | 본 문서 범위와 C-015 |

---

## 9. Cross-link index to the five per-idea docs

아래 문서들은 이 종합본의 세부 분해 문서다. 각 문서는 해당 아이디어의 실패 원인, 개선 가능성, 재사용 자산을 별도로 다룬다.

| 아이디어 | 세부 문서 |
|---|---|
| Idea1 규칙 채굴 | `docs/research/condition_research/plans/2026-07-07_alpha_lab_idea1_rule_mining_failure_improvement_reuse.md` |
| Idea2 이벤트 스터디 | `docs/research/condition_research/plans/2026-07-07_alpha_lab_idea2_event_study_failure_improvement_reuse.md` |
| Idea3 미시구조 레이어 | `docs/research/condition_research/plans/2026-07-07_alpha_lab_idea3_microstructure_layer_failure_improvement_reuse.md` |
| Idea4 레짐 게이트 | `docs/research/condition_research/plans/2026-07-07_alpha_lab_idea4_regime_gate_failure_improvement_reuse.md` |
| Idea5 챔피언 청산/증류 | `docs/research/condition_research/plans/2026-07-07_alpha_lab_idea5_champion_exit_failure_improvement_reuse.md` |

---

## Appendix A — Canonical Claim Ledger

| Claim ID | Canonical claim | Status in this roadmap |
|---|---|---|
| C-001 | 초기 5개 아이디어와 점수: rule mining 83, event study 82, microstructure 77, regime gate 71, champion exit 75. | 원안 기준으로 채택. |
| C-002 | 공통 원리: offline discovery, backtest/engine as final judge. | 모든 후속 gate의 기본 원칙. |
| C-003 | cycle 1은 인프라를 구축했고 deployable alpha는 없었지만 durable negative assets를 만들었다. | v1 결론으로 보존. |
| C-004 | Idea1/P1은 ranking/lift signal을 찾았지만 translated standalone buy rules는 unprofitable이었다. | Idea1 판정의 핵심. |
| C-005 | v3 EV mining은 positive-EV adopted rules/leaves 0개였고, data-first mining은 v1/v2/v3에서 실패했다. | 데이터-우선 채굴 종결 근거. |
| C-006 | Idea2/P2는 42,363 events와 138 cells를 측정했고 FDR survivors는 0이었다. | 이벤트 시드화 금지 근거. |
| C-007 | Idea3/P3는 346 champion samples를 재조인해 sealed minimum 2,000에 미달했고 inconclusive/sample-limited다. | 과잉 판정 금지. |
| C-008 | P5 replay gate는 강했지만 global exit candidate hard_stop -5 + time_stop 300은 engine confirmation에서 rejected됐다. | P5 최종 판정. |
| C-009 | P5 rejection reasons: CI crosses zero, 2024/2025 reversal, MDD worsened in 4/5 windows; incumbent sell remains baseline. | 현행 매도식 유지 근거. |
| C-010 | v4 equal-weight 4-champion ensemble은 2025-01~2026-02에서 profit 약 2,608,362, MDD 약 493,590/493,591, calmar 약 5.28로 성공했다. | 감독형 후보의 수치 기준. |
| C-011 | v4 success는 static equal-weight diversification이며 adaptive timing, single adaptive variants, regime rotation은 OOS에서 실패했다. | 타이밍 성공 주장 금지. |
| C-012 | v4 supervised protocol은 fixed equal 1/4 weights, no optimization, small supervised deployment, kill-switch around 740k, future-data revalidation을 요구한다. | 배포 후보 제약. |
| C-013 | 2025-01~2026-02는 future work를 위한 known/audit evidence이지 fresh blind OOS가 아니다. | 후속 연구의 OOS 표기 규율. |
| C-014 | Future Idea5는 replay를 triage로 취급해야 하며, 별도 승인 후 engine confirmation이 final judge다. | 청산 연구 gate 원칙. |
| C-015 | 이 documentation package는 source-code changes, DB writes, engine runs, strategy registrations를 승인하지 않는다. | 범위 제한. |
