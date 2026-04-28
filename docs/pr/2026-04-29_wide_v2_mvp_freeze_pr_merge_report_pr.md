# Wide v2 MVP freeze 및 PR 병합 보고서

## 목적

Wide v2 v5 direct_v4 shortfall recovery와 WFO/OOS 검증을 통과한 `WideV2Final_B_20260428`를 MVP freeze 후보로 고정하고, 기준 브랜치 `STOM_Version_2U_C`로 병합할 PR 증거를 정리한다.

## 전체 방향

```text
Wide v2 candidate_count=10 full validation
-> direct_v4 shortfall recovery
-> candidate pool 28
-> executed candidates 20
-> actual row-set representatives 10
-> cand007 final best
-> WideV2Final_B_20260428 permanent strategy
-> runtime-preflight
-> WFO/OOS 8 windows
-> balanced/conservative pass
-> MVP freeze
-> PR merge point
-> post-MVP risk backlog
```

## 변경 사항

- Wide v2 MVP freeze 보고서 추가
- Wide v2 운영 재현 명령어 문서 추가
- Wide v2 release checklist 추가
- Wide v2 PR merge report 본문 추가
- WFO/OOS 검증 결과를 freeze 판단 기준으로 연결

## 핵심 근거

- final_buy_strategy=`WideV2Final_B_20260428`
- base_buy_strategy=`WideV1Final_B_20260425`
- source_candidate=`WideV2V5DirectV4ShortfallRecovery_20260428__round001__cand007`
- source_expression=`66.999 <= 시가총액 < 2_580 and 등락율 > 3.535`
- final_candidate_pool_count=`28`
- execution_count=`20`
- actual_selected_count=`10`
- row_set_identity_status=`all_distinct`
- WFO/OOS `round_count=8`
- WFO/OOS `success_rate=1.0`
- WFO/OOS `mean_oos_metric=0.5725`
- WFO/OOS `mean_trade_count=2045.125`
- WFO/OOS `zero_trade_rounds=0`
- balanced preset 통과
- conservative preset 통과

## 검증 계획

- `python .\stom_backtest.py runtime-preflight --buy WideV2Final_B_20260428 ...`
- `python .\stom_backtest.py wfo --dry-run ...`
- `python -m pytest tests/unit/test_wfo.py tests/unit/test_wfo_cli.py tests/unit/test_ai_controller.py tests/unit/test_strategy_generator.py tests/unit/test_strategy_loader.py -q`
- `python -m pytest tests/unit/test_research_optimizer.py tests/unit/test_research_optimizer_report.py tests/unit/test_research_loop.py tests/unit/test_subcommands.py -q`
- `python scripts/verify_nonrelease_sync.py`
- `git diff --check --ignore-cr-at-eol HEAD`
- `gh pr create --base STOM_Version_2U_C --head feature/wide-v2-mvp-freeze-pr-report --title "Wide v2 MVP freeze 및 PR 병합 보고서" --body-file docs/pr/2026-04-29_wide_v2_mvp_freeze_pr_merge_report_pr.md`

## 병합 원칙

- 기준 브랜치에 직접 커밋하지 않는다.
- `feature/wide-v2-mvp-freeze-pr-report`에서 GitHub PR을 생성한다.
- PR merge 후 local `STOM_Version_2U_C`는 `git pull --ff-only origin STOM_Version_2U_C`로 동기화한다.
- raw runtime 산출물인 `backtest/temp`, `backtest/csv`, `backtest/graph`는 커밋하지 않는다.
- `utility/strategy.db`는 런타임 DB이므로 커밋하지 않는다.

## 남은 위험

- MVP freeze는 실거래 수익 보장이 아니다.
- 실거래 전에는 소액 파일럿, 슬리피지, 호가 체결, 주문 실패 대응을 별도 확인해야 한다.
- 신규 후보 탐색은 post-MVP backlog에서 별도 브랜치와 PR로 재개한다.

## 다음 단계

- PR merge 후 `feature/wide-v2-post-mvp-risk-backlog` 브랜치를 생성한다.
- 다음 명령어: `$writing-plans Wide v2 post-MVP risk backlog 및 운영 파일럿 체크리스트 작성`
