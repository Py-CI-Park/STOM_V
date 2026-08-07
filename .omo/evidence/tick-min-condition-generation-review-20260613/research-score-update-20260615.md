# Tick/Min Condition Research Score Update (2026-06-15)

## 결론

| 구분 | 현재 점수 | 부족분 | 판단 |
|---|---:|---:|---|
| 기존 검증 챔피언 포함 연구 완성도 | 84% | 16% | THETA/T2C3와 V6 포트폴리오는 paper 운용 준비 단계까지 왔다. live 완료는 아니다. |
| 새 tick/min 조건식 자동발견 기능 | 49% | 51% | 생성기·게이트·기록은 개선됐지만, 새 OOS 생존 알파는 아직 0이다. |
| 실제 신규 알파 발견 성과 | 18% | 82% | 14~28, multiband 40회, A/B n=8 모두 신규 OOS promising 0이다. |
| 연구 관리·기록·관측성 | 88% | 12% | ledger, 증거, 보고서, 관측성은 좋다. 일부 path drift와 stateful 표시 부족이 남았다. |
| 전체 통합 완성도 | 67% | 33% | 6/13의 strict 52%보다 개선됐지만, 핵심 병목은 여전히 신규 알파 OOS 생존이다. |

핵심은 두 가지를 분리해서 보는 것이다. **운용 가능한 기존 후보를 관리하는 능력은 높아졌고, 새 조건식을 계속 만들어 추가 알파를 찾는 능력은 아직 절반 수준**이다. seed가 중요하다는 사용자의 판단은 맞지만, 현재 병목은 seed 하나가 아니라 `넓은 seed -> 게이트 -> 피드백 -> grid/mutator -> OOS/WF`가 이어지는 전체 학습 루프다.

## 최신 반영 내용

| 영역 | 반영된 내용 | 근거 | 점수 영향 |
|---|---|---|---|
| 다밴드 seed 생성 | `p5_template_hypothesis.md`가 시간대 x 시가총액 이산 분기, T2C3 few-shot, build_v5 점수합산 실패, 넓은 slot 후보값을 명시한다. | `git diff -- ai_strategy_loop/brain/prompts/p5_template_hypothesis.md` | seed 폭 점수 상승 |
| 검증기 어휘 보강 | 검증된 seed가 쓰는 `초당거래대금N`, `매수총잔량N`, `매도총잔량N`이 whitelist에 추가됐다. | `git diff -- ai_strategy_loop/scripts/gen_template_hypothesis.py` | 검증 시드 재현성 상승 |
| stateful feedback 입력 | `gen_template_hypothesis.py --feedback-file`과 `build_prompt(..., feedback_text=...)`가 추가됐다. | `git diff -- ai_strategy_loop/scripts/gen_template_hypothesis.py` | 학습 루프 기반 상승 |
| 다밴드 테스트 | proven multiband seed 3종 검증, shifted accessor whitelist, prompt 문구 테스트가 추가됐다. | `git diff -- tests/unit/test_template_hypothesis.py` | 회귀 방지 상승 |
| refine gate | P0b에서 known-good THETA는 PASS, no-go 후보는 REFUSE로 기록됐다. | `.omo/evidence/tmap-walkforward/gate/p0b_verify.py` | false-positive 차단 상승 |
| A/B pilot | random 0/8 smoke-pass, stateful 3/8 smoke-pass이나 OOS promising은 둘 다 0이다. | `.omo/evidence/tmap-walkforward/ab_result_n8.json` | process edge는 약간 상승, 성과 점수는 유지 |
| multiband overnight | 40회 중 PROMISING 0, iter7은 smoke-pass였지만 3년 train -2,030,044로 기각됐다. | `docs/update_log/2026-06-15_multiband_overnight_results.md` | 신규 알파 성과 점수 하락 또는 보수 유지 |
| 기록 관리 | record/dashboard audit가 기록 9.0/10, 관측성 8.5/10, 코드 정합 9.5/10으로 평가했다. | `docs/update_log/2026-06-15_record_and_dashboard_observability_audit.md` | 연구 관리 점수 상승 |

## 부족분 상세

| 부족분 | 부족률 | 왜 부족한가 | 개선 방법 | 합격 기준 |
|---|---:|---|---|---|
| 신규 OOS 알파 생존 | 82% | 최신 생성 후보가 OOS/WF를 통과하지 못했다. stateful도 OOS 0이다. | random 장기 반복을 멈추고 P1 A/B full 또는 명확한 stop rule로 process edge부터 검증한다. | 신규 후보 1개 이상이 full train + OOS + WF를 통과 |
| min full-session 조건 생성 | 78% | 09:00~15:00 template/data path는 있으나 min_new 후보와 min rotation이 음수다. 데이터도 약 11개월로 짧다. | min primitive map을 먼저 만들고 시간대별 robust corner가 없으면 LLM 생성을 보류한다. | min time-band corner가 split validation에서 반복 흑자 |
| stateful 학습 루프 | 44% | feedback이 smoke-pass/train-fail을 선호 신호로 오해할 수 있다. `_discovery_feedback.txt` 요약도 약하다. | smoke-pass 후 full-train 실패는 avoid로 기록하고, OOS survivor만 prefer로 올린다. | stateful arm이 random 대비 OOS promising 또는 사전등록 rate 기준 우위 |
| seed coverage | 28% | prompt는 넓어졌지만 실제 coverage ledger가 없어 어떤 시간대 x 시총 x 신호 셀이 비었는지 모른다. | `coverage_ledger.json`을 만들고 미탐색 셀에서 seed를 뽑는다. | 각 run이 새 coverage cell을 명시하고 중복률을 낮춤 |
| grid/mutator | 42% | 현재는 LLM이 전체 genome을 다시 뽑는 비중이 크고, 2D/3D 상호작용 grid가 자동 루프에 약하다. | anchor branch 고정 후 cap/take/trail, time/cap/signal 2D grid를 coarse-to-fine으로 붙인다. | 1D plateau 상위 후보에서 2D mesa corner 1개 이상 확인 |
| gate reason 학습 | 22% | gate는 false positive를 막지만, 왜 탈락했는지를 다음 생성에 충분히 구조화하지 않는다. | `gate_distance`, `reject_reason`, `train_fail_after_smoke`를 summary와 feedback에 넣는다. | 다음 생성 prompt에 structured avoid/prefer가 들어감 |
| 연구 산출물 정리 | 45% | untracked scripts/templates/evidence가 많아 durable artifact와 scratch 구분이 약하다. | commit/ignore/archive 표를 만들어 산출물 수명을 분류한다. | `git status`가 의도된 문서·코드·증거 단위로 정리됨 |

## Seed에 대한 판단

| 질문 | 답 |
|---|---|
| seed가 중요한가 | 중요하다. 초기에 넓고 깨끗한 seed가 없으면 후속 sweep과 feedback이 볼 수 있는 공간이 좁아진다. |
| 현재 넓은 seed 생성 과정이 있는가 | 일부 있다. p5 prompt가 tick 09:00~09:30, min 09:00~15:00을 시간대별로 나누고, 2~3밴드와 넓은 slot 후보값을 요구한다. |
| 아직 부족한가 | 부족하다. "넓게 만들라"는 prompt 지시는 생겼지만, coverage ledger와 데이터 기반 seed context가 없어 실제 탐색 범위가 정량 관리되지 않는다. |
| seed만 잘 만들면 되는가 | 아니다. seed는 시작점이고, 현재 가장 큰 병목은 OOS 생존 후보 0이다. gate, feedback, grid/mutator, data expansion까지 이어져야 한다. |

## 다음 개발 순서

| 순서 | 작업 | 이유 | 산출물 |
|---:|---|---|---|
| 1 | P0 gate 유지 및 reason 구조화 | in-sample feedback이 먼저 켜지면 선택편향이 커진다. | `refine_gate` summary fields |
| 2 | P1 A/B full 또는 명확한 stop rule 완료 | stateful이 random보다 나은지 확인해야 다음 구현이 의미 있다. | `ab_result_n40.json` 또는 C3 stop report |
| 3 | feedback 의미 수정 | smoke-pass/train-fail을 prefer가 아니라 avoid로 바꿔야 한다. | `_discovery_feedback.txt` structured format |
| 4 | coverage ledger 추가 | seed가 넓은지 숫자로 봐야 한다. | `coverage_ledger.json` |
| 5 | data-driven seed context 주입 | LLM이 이름 요약이 아니라 실제 유효/무효 셀을 보게 해야 한다. | `mine_generation_context.py` or equivalent |
| 6 | grid/coarse-to-fine 연결 | THETA류 고차원 상호작용을 1D sweep만으로 못 잡는다. | grid escalation summary |
| 7 | min primitive map 재실행 | min full-session은 아직 alpha evidence가 약하다. | min split validation report |
| 8 | THETA/T2C3 paper 운용 병행 | 신규 발굴이 OOS 0인 동안 실전 검증 가능한 가치는 기존 champion에 있다. | 30-40 trade paper report |

## 관리 상태

| 항목 | 판단 |
|---|---|
| 연구 기록 | 잘되고 있다. 문서, evidence, ledger, A/B, gate 자료가 남는다. |
| 연구 판단 | 예전보다 보수적으로 좋아졌다. smoke-pass와 OOS survivor를 구분한다. |
| 가장 큰 관리 리스크 | 산출물이 너무 많고 untracked가 많아, 어느 것이 durable인지 분류가 필요하다. |
| 다음 관리 개선 | commit/ignore/archive decision table과 summary schema 통일이 필요하다. |

## 근거 파일

| 파일 | 사용한 이유 |
|---|---|
| `docs/update_log/2026-06-15_multiband_overnight_results.md` | 40회 multiband 결과와 PROMISING 0 확인 |
| `.omo/evidence/tmap-walkforward/ab_result_n8.json` | random/stateful pilot 정량 비교 |
| `docs/update_log/2026-06-15_record_and_dashboard_observability_audit.md` | 기록 관리·관측성 평가 |
| `docs/update_log/2026-06-15_condition_discovery_process_research_report.md` | 6단계 process 점수와 병목 |
| `docs/update_log/2026-06-15_session_handoff_pipeline_execution.md` | P0a/P0b/P2/P1 진행 상태 |
| `git diff -- ai_strategy_loop/...` | prompt, feedback, whitelist, test 반영 확인 |

