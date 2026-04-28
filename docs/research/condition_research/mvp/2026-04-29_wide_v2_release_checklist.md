# Wide v2 release checklist

## MVP readiness

- [x] Wide v2 direct_v4 shortfall recovery 구현
- [x] direct_v4 shortfall recovery loop integration 검증
- [x] candidate_count=10 full validation에서 후보 풀 28개 확보
- [x] planned_execution_count=20 실행
- [x] actual row-set 대표 후보 10개 확보
- [x] row_set_identity_status=all_distinct 확인
- [x] final candidate `cand007` 선택
- [x] 최종 전략명 `WideV2Final_B_20260428` 고정
- [x] 최종 전략 스냅샷 `utility/ai_agent/WideV2Final_B_20260428.py` 커밋
- [x] runtime-preflight 통과
- [x] WFO dry-run window count 8 확인
- [x] WFO/OOS full validation 통과
- [x] balanced preset 통과
- [x] conservative preset 통과
- [x] Korean PR-ready validation report 작성

## Not yet release-safe for live trading

- [ ] 소액 실거래 파일럿 기간 정의
- [ ] 슬리피지와 호가 체결 차이 측정
- [ ] 장중 네트워크/API 장애 대응 확인
- [ ] 주문 수량, 예수금, 종목당 배팅금액 live guard 확인
- [ ] 실거래 중지 조건과 rollback 절차 정의
- [ ] 장 종료 후 거래 로그와 백테스트 예측 비교 템플릿 작성
- [ ] WFO/OOS 결과를 실거래 주문 로직과 연결하기 전 risk owner 확인

## Frozen artifacts

| Artifact | Path |
| --- | --- |
| Final strategy snapshot | `utility/ai_agent/WideV2Final_B_20260428.py` |
| WFO/OOS manifest | `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_manifest.json` |
| WFO/OOS windows | `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_windows.json` |
| WFO/OOS report | `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_report.json` |
| WFO/OOS decision | `docs/research/condition_research/pilot_logs/2026-04-28_wide_v2_wfo_oos_decision.md` |
| MVP freeze report | `docs/research/condition_research/mvp/2026-04-29_wide_v2_mvp_freeze.md` |
| Operational reproduction | `docs/research/condition_research/mvp/2026-04-29_wide_v2_operational_reproduction.md` |

## Next branch after PR merge

- branch=feature/wide-v2-post-mvp-risk-backlog
- command=$writing-plans Wide v2 post-MVP risk backlog 및 운영 파일럿 체크리스트 작성

## Stop conditions

- 신규 조건식 탐색은 MVP freeze PR merge 이후 별도 post-MVP backlog에서만 재개한다.
- WFO/OOS 결과를 덮어쓰는 full rerun은 별도 브랜치와 별도 PR로만 수행한다.
- STOM_Version_2U_C에 직접 커밋하지 않는다.
- 이후 통합은 GitHub PR 생성과 PR merge 기록을 남긴다.
