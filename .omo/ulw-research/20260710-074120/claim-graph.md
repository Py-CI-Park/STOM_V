# Claim Graph

## Verified claims

로컬 원자료·코드·DB·커밋·과거 세션을 교차검증한 현재 판정이다.

| claim_id | statement | claim type | risk tier | scope | intent ids | supporting observations | contradicting observations | independent observation groups | convergence | counter-search | primary source | dependencies | status | synthesis location |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C-01 | 최신 v2 실패는 실제 손익/MDD 실패이며 게이트·보고서 오류만으로 설명되지 않는다 | empirical | high | v2 8-body replay | I-1,I-4 | O-001,O-002,O-006 | none for 7 measured rows | raw JSON + 7 CSVs + corrected audit | converged | gate/outlier/frequency alternatives rejected | local machine artifacts | none | verified | root cause |
| C-02 | 최신 v2는 자율 controller 학습 run이 아니라 정적 artifact + batch evaluation 경로다 | architecture/provenance | high | latest experiment | I-2,I-3 | O-003,O-007,O-008 | run config retains provider=gpt_auth template | commit + current_state + DB names | converged | searched for reusable generator/caller | local code/git/DB | none | verified | process map |
| C-03 | v2 본문은 데이터 계보가 있으나 숫자 임계값은 통계적으로 산출됐다는 영수증이 없고 구조 다양성도 낮다 | provenance/quality | high | v2 body generation | I-2,I-4 | O-003,O-009,O-010 | category-level failure-map rationale exists | exact bodies + axis spec + git -G | converged | searched threshold history and generator source | local artifacts/git | C-02 | verified with bounded wording | creativity audit |
| C-04 | 구현된 학습 기능 다수는 기본 OFF이거나 별도 경로이며 일부는 주 loop 미배선이다 | architecture | high | current source | I-3,I-4 | O-011,O-012,O-013 | CLI research has a real context-pack consumer | config + controller + CLI code | converged | broad no-caller claim corrected | local source | none | verified | wiring audit |
| C-05 | 현재 Hall-of-Fame는 인간과 AI를 공정하게 비교하는 표준 벤치마크가 아니다 | benchmark | high | dashboard | I-5 | O-004,O-005,O-014 | reliable AILOOP rows still materially trail human display | backend + JSON + report | converged | quality-gap counterevidence retained | local code/data | none | verified | HOF audit |
| C-06 | promotion-review의 zero-generation 표시는 실제 controller generation을 막지 않는다 | runtime safety | high | controller governance | I-3 | O-015,O-016 | no contrary enforcement found | source + read-only DB | converged | searched controller consumers | local source/DB | C-04 | verified | runtime contradiction |
| C-07 | 저장소 전체 timestamp 최신 handoff는 현재 checkout의 564879fe가 아니라 divergent sibling 585051e이며, 두 연구선은 함께 보존해야 한다 | provenance/history | high | all refs | I-1,I-2 | O-019 | neither commit is ancestor of the other | git log --all + merge-base + both handoffs | converged | current-branch-only interpretation retained as scoped claim | git objects/docs | none | verified | handoff reconciliation |
| C-08 | v2 원자료는 결합된 entry×exit의 음수 실현 기대값을 증명하지만 entry와 exit 각각의 인과 기여는 분리하지 못한다 | causal boundary | high | v2 replay | I-4 | O-002,O-006,O-018 | adverse MFE/MAE suggests entry weakness; shared exits suggest exit weakness | raw trades + structure receipt + no factorial ablation | converged | entry-only and exit-only explanations both counter-searched | local artifacts | C-01,C-03 | verified bounded claim | causal verdict |
