# 조건식 연구 점수 재점검 및 개선 계획 (2026-06-15)

## 요약

| 평가축 | 완성도 | 부족분 | 결론 |
|---|---:|---:|---|
| 기존 champion/portfolio 연구 | 84% | 16% | THETA/T2C3는 paper 운용 준비권이다. live 완료는 아니다. |
| 새 tick/min 조건식 자동발견 | 49% | 51% | 생성·검증 인프라는 개선됐지만 OOS 생존 신규 알파는 아직 없다. |
| 실제 신규 알파 성과 | 18% | 82% | multiband 40회와 A/B n=8 모두 OOS promising 0이다. |
| 연구 관리·기록·관측성 | 88% | 12% | 기록 관리는 좋아졌다. 산출물 정리와 stateful 표시가 남았다. |
| 전체 통합 상태 | 67% | 33% | 6/13 strict 52%보다 개선됐지만, 핵심 병목은 신규 알파 생존이다. |

## 최신 반영 판단

| 항목 | 반영 내용 | 판단 |
|---|---|---|
| 넓은 seed 생성 | p5 prompt가 tick/min 전체 시간대를 나누고 2~3개 시간대 x 시총 밴드와 넓은 slot 후보값을 요구한다. | seed 폭은 개선됐다. |
| T2C3 교훈 | T2C3가 시간대 x 시총 다밴드의 유효성을 보여준다. | seed 설계의 기준점으로 유지한다. |
| 검증기 | 검증된 seed 어휘 whitelist와 다밴드 테스트가 추가됐다. | 재현성은 개선됐다. |
| feedback | `--feedback-file` 기반 stateful 생성 경로가 생겼다. | 학습 루프의 시작점은 생겼다. |
| A/B 결과 | stateful은 smoke-pass 3/8, random은 0/8이지만 OOS promising은 둘 다 0이다. | process edge는 약하지만 alpha 성과는 아직 0이다. |
| multiband 40회 | PROMISING 0. iter7은 smoke-pass였지만 full train에서 탈락했다. | 전체기간 gate가 false positive를 잘 막았다. |

## 부족분과 개선책

| 우선순위 | 부족분 | 개선책 | 합격 기준 |
|---:|---|---|---|
| 1 | OOS survivor 0 | P1 A/B full 또는 C3 stop rule로 stateful이 random보다 나은지 먼저 검증 | OOS promising 1개 이상 또는 process edge 없음 판정 |
| 2 | feedback 의미 불명확 | smoke-pass/full-train-fail은 prefer가 아니라 avoid로 기록 | feedback summary에 reject reason 반영 |
| 3 | seed coverage 미정량 | 시간대 x 시총 x 신호 coverage ledger 추가 | 신규 run마다 미탐색 cell 명시 |
| 4 | grid/mutator 약함 | anchor branch 고정 후 2D/3D grid와 coarse-to-fine 적용 | mesa/plateau corner 확인 |
| 5 | min full-session 약함 | LLM보다 min primitive map과 split 검증 우선 | min time-band robust corner 1개 이상 |
| 6 | 산출물 정리 부족 | commit/ignore/archive decision table 작성 | `git status`가 의도 단위로 정리 |

## Seed 관련 결론

seed는 중요하다. 특히 초기에 넓고 깨끗한 seed가 있어야 sweep, gate, feedback이 볼 수 있는 탐색 공간이 넓어진다. 다만 seed가 전부는 아니다. 현재는 seed 폭보다 **OOS 생존 후보를 끝까지 살려내는 학습 루프**가 더 큰 병목이다.

따라서 다음 개발은 `넓은 seed 생성`만 반복하지 말고, `coverage ledger -> data-driven context -> P0 gate -> P1 A/B -> feedback 수정 -> grid/mutator` 순서로 진행해야 한다.

상세 점수표와 근거는 `.omo/evidence/tick-min-condition-generation-review-20260613/research-score-update-20260615.md` 및 `.json`에 기록했다.

