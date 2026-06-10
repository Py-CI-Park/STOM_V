# LazyCodex Master Roadmap Command

이 명령은 `condition-research-end-to-end-master-roadmap-20260606` 마스터 플랜을 기준으로
조건식 발굴 전체 페이지를 순차 수행시키기 위한 복사용 명령이다.

주의: 이 명령은 마스터 플랜 전체 완료를 목표로 계속 진행하도록 지시하지만, 실제 실행 중
타임아웃, 검증 실패, 보호 경로 제약, OOS 불합격 같은 블로커가 나오면 그 지점에서 증거와
다음 조치를 보고해야 한다. OOS 전에는 인간 수준/초월 성과를 주장하지 않는다.

## Copy Command

```text
$ulw-loop 조건식 발굴 end-to-end master roadmap의 모든 페이지를 순차 수행해줘.
정본은 docs/AGENT_HANDOFF.md, docs/update_log/2026-06-05_direction_review_through_84acb6cb.md, .omo/plans/condition-research-end-to-end-master-roadmap-20260606.md, .omo/plans/tick-human-like-research-criteria-dashboard-20260605.md로 삼아라.

이번 명령은 마스터 플랜에 "AI Prompt Context Pack 강화" 단계를 추가 반영하는 승인이다.
단, 공식 엔진/하드게이트/backtest_graph/보호 경로/production export/final_approval/live/V3K는 수정하지 말고, 신규 기능은 기본 OFF 또는 연구 config 전용으로 유지해라.

목표:
1. utility/ai_agent/strategy.txt, utility/ai_agent/rules.txt, utility/ai_agent/system_prompt/v1/*를 읽고 조건식 가이드 요약 Context Pack을 만든다.
2. 현재/이전 매수·매도 조건식 원문, 이전 대비 diff, 조건식 구성 패턴, 금지 문법, 좋은 예시 few-shot을 AI 생성 프롬프트에 선택적으로 주입한다.
3. 백테스트 결과에서 profit, return, MDD, trade_count, payoff, avg_hold, daily stats, 세대 이력, 실패 사유를 요약해 프롬프트에 넣는다.
4. 시간대별, 시가총액별, 변수별 상관도/히스토그램/범위/세그먼트 분석을 생성하고 DB 또는 연구 스냅샷에 저장한다.
5. 이 분석 결과를 "다음 세대에서 개선할 점"으로 압축해 프롬프트에 넣되, 원문 과다 주입으로 토큰 폭증이나 조건식 복잡도 폭증이 생기지 않도록 상한을 둔다.
6. 대시보드에서 사용 중 조건식, 이전 조건식 diff, AI 요청 프롬프트, 사용된 Context Pack, 분석 요약, 백테스트 기간/연도/시간대/시총 구간을 볼 수 있게 한다.
7. 이후 마스터 플랜 순서대로 09:00~09:30 generated 전략 타임아웃 완화, 2024~2026 최근 구간 검토, 후보 고정, OOS 검증, PBO/DSR/slippage/promotion-card/wiki 문서화를 진행한다.
8. 각 페이지 완료 시 전체 마스터 플랜 진행률 테이블, 현재 페이지 진행률, 성과, 남은 리스크, 다음 추천 명령어를 보고해라.

검증:
- 프롬프트 로그에서 has_base_code, has_few_shot, guide_context, diff_context, analysis_context, correlation_context가 실제 주입됐는지 확인한다.
- 대시보드에서 프롬프트/조건식/diff/분석 요약이 실제 보이는지 브라우저 증거를 남긴다.
- 단위 테스트, git diff --check, python scripts/verify_nonrelease_sync.py, 보호 경로 status를 통과시킨다.
- 인간 수준/초월 성과는 OOS 전에는 주장하지 말고, 연구 후보와 증명 후보를 구분해라.
```

## Expected Flow

```text
AI Prompt Context Pack 강화
→ 조건식 생성 입력 품질 개선
→ generated 전략 복잡도/타임아웃 감소
→ 09:00~09:30 연구 확장
→ 2024~2026 최근 구간 검토
→ 후보 고정
→ OOS 검증
→ PBO/DSR/slippage/promotion-card/wiki/대시보드 정리
```

## Status Reporting Requirement

실행 에이전트는 각 페이지 또는 주요 체크포인트마다 아래 형식으로 보고해야 한다.

| 구분 | 보고 내용 |
|---|---|
| 마스터 플랜 진행률 | 전체 페이지 중 완료/진행/대기/차단 상태 |
| 현재 페이지 진행률 | 현재 작업 페이지의 체크포인트별 상태 |
| 성과 | 수익, 수익률, MDD, 거래 수, payoff, 기간, 시간대, 시총 구간 |
| 증거 | 테스트, 브라우저 스크린샷, 프롬프트 로그, 분석 스냅샷 |
| 리스크 | 과적합, 거래 수 부족, 타임아웃, 토큰 폭증, 조건식 복잡도 |
| 다음 추천 명령 | 다음 `$start-work` 또는 `$ulw-plan` 명령과 이유 |
