# system_prompt v2 (QSP1 P2, 2026-07-30)

v2 = **v1 전체(../v1/ 8파일 그대로 유효)** + 아래 증보 4종.
v1 은 불변(기존 run 재현성). 소비 주체:
  - AI 에이전트 생성 경로: 즉시 적용(agent_intervention_guidelines 의무)
  - 결정적 제안 경로(revision/proposer + intent_gate): analysis_to_revision 계약의 코드 구현
  - LLM 루프(brain/prompt.py) 배선: LLM 복귀 스모크와 함께(한계 원장 등재 — 대기)

| 파일 | 채우는 간극 |
|---|---|
| analysis_to_revision.md | G1 분석→수정 방법론(수정 명세 계약) |
| self_review_checklist.md | G2 의도-일치 자가검토 |
| multi_candidate_protocol.md | G3 다후보 가설 축 규약 |
| hierarchy_preservation.md | G4 계층 골격 보존 |
