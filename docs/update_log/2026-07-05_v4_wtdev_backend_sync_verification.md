# 2026-07-05 V4 ← wt-dev 백엔드 동기화 격리 검증 (채택 대기)

## 결론
`loop/process-research-pipeline`(wt-dev 백엔드 연구 파이프라인, merge-base 이후 37커밋)을
`feature/dashboard-v4-20260704` 위에 머지한 격리 브랜치
**`integration/v4-wtdev-backend-sync-20260705`** 의 전 게이트가 green 이다.
채택(머지) 시 V4 브랜치 자체 백엔드가 research_observability page_data 를 emit 하고,
백테 리포트에 측정계 라벨이 표기된다. **채택 여부는 베이스라인 결정 사안 — 사용자 승인 대기.**

## 머지 내용
- 소스 충돌 **0** — 충돌 11건은 전부 빌드 산출물(html ?v=/manifest)·OMC 상태(.omo)·
  브라우저 증거 아티팩트(add/add)로, ours 채택 후 번들 재빌드로 정본화.
- 유입: autopsy/(ablation·analysis_card·trade_ledger), brain/(pack_producer·principle_gate·
  principles·sulsa 데이터), controller/(axis_ledger·context_pack_builder·replay_profile·
  condition_discovery/loop 갱신), fitness/(measurement_frame·slippage_profiles·
  positive_control), portfolio/(assembler·promotion_preconditions), provider/failover,
  dashboard/backtest_report(측정계 라벨: line 573 `측정계: {label} [{frame}]` — UI 추가 없이
  BacktestTab 리포트에 자동 표기), tests 39파일.

## 게이트 결과 (격리 워크트리)
| 게이트 | 결과 |
|---|---|
| 번들 재빌드 | 0에러 |
| jsdom 하네스 V1~V7 | allPass (V4 프론트 8뷰 무손상) |
| `verify_nonrelease_sync.py` | 통과(exit 0) |
| `app.py` compile | OK |
| pytest (머지 테스트 델타 39파일 + CORS env + route parity) | **722 passed** |

## 채택 절차(승인 시)
```
cd STOM_V.wt-dashboard-remodel
git merge integration/v4-wtdev-backend-sync-20260705   # fast-forward 아님(머지커밋 유지)
# 재빌드 + 하네스 + verify_nonrelease 재확인 후 커밋 정리
```
미채택 시: 격리 브랜치/워크트리는 그대로 보존(증거) 또는 폐기 가능.
