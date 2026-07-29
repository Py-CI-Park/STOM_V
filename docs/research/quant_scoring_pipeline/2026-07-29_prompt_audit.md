# P0-b — 조건식 생성 프롬프트 전수 감사 (2026-07-29)

> 대상: `utility/ai_agent/system_prompt/v1/` 8파일(1,321줄) + 생성 스택(`brain/`).
> 목적: "분석 결과를 받아 조건식을 **확실하게** 잘 생성·검토"하도록 부족분을 식별하고 증보한다.

## 1. 생성 스택 실물 (감사로 확인)

```
build_messages(brain/prompt.py)          ← 프롬프트 조립(시스템+과제+피드백)
  └ provider.chat → extract_code
      → validate_strategy(compile)       ← PRE-SAVE 게이트 ①
      → check_tokens(금지 토큰)           ← ②
      → variable_scope(매수식의 매도전용 변수) ← ③
      → dedup(정규화 해시)                ← ④
      → liquidity_gate / principle_gate(CSC 기계판정 일부) ← ⑤
      → save_strategy_to_db
```

- 참조 문서: system_prompt·variables_reference(어휘 SSOT)·forbidden·examples·
  composite_examples + **차트술사 구조론**(principles 139줄·constraints CSC-01~14·idiom).
- 피드백 주입: history_summary + sell_feedback(청산 부검) + segment 부검 + meta_seed.

## 2. 강점 (유지)

| 항목 | 평가 |
|---|---|
| 어휘 SSOT 단일화(variables_reference → 로더 공유) | 우수 — v5.13.3 범위 전개로 보강됨 |
| 금지 규칙의 기계 판정화(forbidden + token_check) | 우수 |
| 구조론 제약의 기계 판정화(CSC-01~14 → principle_gate 일부 구현) | 우수(부분 배선) |
| 실패 재시도에 prior_error 환류 | 우수 |

## 3. 간극 (증보 대상 — 초안 4종 작성)

| # | 간극 | 증거 | 증보 초안 |
|---|---|---|---|
| G1 | **분석→수정 방법론 부재**: 세그먼트 잔차표를 받았을 때 "어느 리프의 어느 경계를 어떤 근거로" 고치는지 절차가 없음 — 피드백을 텍스트로 던질 뿐 | prompt.py 에 feedback 원문 주입만 존재 | `prompt_v2_drafts/analysis_to_revision.md` |
| G2 | **의도-일치 자가검토 부재**: "요청된 수정만 반영됐는가"를 생성자가 스스로 diff 로 검증하는 체크리스트 없음 (elelif 사고·과잉 수정 재발 여지) | system_prompt §작성절차 4단계에 없음 | `prompt_v2_drafts/self_review_checklist.md` |
| G3 | **다후보 규약 부재**: 후보 N개를 서로 다른 가설(수정 축)로 만들라는 지시 없음 → 동일 방향 미세 변형만 나올 위험 | dedup 게이트가 사후 차단만 담당 | `prompt_v2_drafts/multi_candidate_protocol.md` |
| G4 | **계층 조건식 보존 규칙 부재**: 밴드×시총 골격(QSP1 HIER)의 "리프만 수정, 골격 불변" 규칙 없음 → 수정 시 구조 붕괴 위험 | composite_examples 에 계층형 예제 없음 | `prompt_v2_drafts/hierarchy_preservation.md` |

## 4. 긴장 발견 (한계 원장 등재)

- **CSC-03(구조 없는 모멘텀 매수 금지) vs Wide-net 시드**: QSP1 HIER 시드는 의도적으로
  구조 참조 없이 넓게 진입한다(데이터 수집용). CSC 를 전 단계에 일괄 적용하면 wide-net
  자체가 위반이 된다. → **적용 시점 규정 필요**: CSC 는 "최종 답 후보" 게이트에는 강제,
  "데이터 수집 그물"에는 면제(면제 사실을 원장·MD에 명시). 이 구분이 없던 것이 v1 의 한계.
- principles 의 수치 임계는 문서 스스로 "무근거 가설"로 선언 — 데이터 보정 전제가 이미
  있으므로 G1(분석→수정)이 그 보정 경로의 실체가 된다.

## 5. 버전링 계획

- v1 은 불변(기존 run 재현성). 증보 4종은 초안 검증(P2 의 의도-일치 게이트와 함께 배선) 후
  `system_prompt/v2/` 로 승격 — build_messages 의 로더에 v2 우선 스위치(기본 v1, 토글).
- 승격 게이트: 동일 과제 생성 v1 vs v2 비교(구조 보존·의도 반영·preflight 통과율).
