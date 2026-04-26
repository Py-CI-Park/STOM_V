# Wide v1 release checklist

## MVP readiness

- [x] v5 actual row-set 대표 후보 10개 확보
- [x] 대표 후보 cand017 선택
- [x] 최종 전략명 `WideV1Final_B_20260425` 고정
- [x] 최종 전략 스냅샷 `utility/ai_agent/WideV1Final_B_20260425.py` 커밋
- [x] runtime-preflight 통과
- [x] WFO dry-run window count 8 확인
- [x] WFO full validation 통과
- [x] balanced preset 통과
- [x] conservative preset 통과
- [x] WFO CLI dict config bugfix 테스트 포함

## Not yet release-safe for live trading

- [ ] 소액 실거래 파일럿 기간 정의
- [ ] 슬리피지와 호가 체결 차이 측정
- [ ] 장중 네트워크/API 장애 대응 확인
- [ ] 주문 수량, 예수금, 종목당 배팅금액 live guard 확인
- [ ] 실거래 중지 조건과 rollback 절차 정의
- [ ] 장 종료 후 거래 로그와 백테스트 예측 비교 템플릿 작성

## Frozen artifacts

| Artifact | Path |
| --- | --- |
| Final strategy snapshot | `utility/ai_agent/WideV1Final_B_20260425.py` |
| Promote manifest | `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_manifest.json` |
| WFO report | `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_wfo_report.json` |
| WFO decision | `docs/research/condition_research/pilot_logs/2026-04-25_wide_v1_v5_promote_wfo_decision.md` |
| MVP freeze report | `docs/research/condition_research/mvp/2026-04-26_wide_v1_mvp_freeze.md` |
| Operational reproduction | `docs/research/condition_research/mvp/2026-04-26_wide_v1_operational_reproduction.md` |

## Next branch after PR merge

- branch=feature/wide-v1-post-mvp-risk-backlog
- command=$writing-plans Wide v1 post-MVP risk backlog 및 운영 파일럿 체크리스트 작성

## Stop conditions

- 신규 조건식 탐색은 MVP freeze PR merge 이후 별도 post-MVP backlog에서만 재개한다.
- WFO 결과를 덮어쓰는 full rerun은 별도 브랜치와 별도 PR로만 수행한다.
- `STOM_Version_2U_C`에 직접 커밋하지 않는다.
- 이후 통합은 GitHub PR 생성과 PR merge 기록을 남긴다.
