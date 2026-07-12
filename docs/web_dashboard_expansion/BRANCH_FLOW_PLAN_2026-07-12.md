# 브랜치 승격 플로우 계획 (V4 대시보드 → loop → 2U_C-ai-strategy-loop)

작성: 2026-07-12 · 작성 위치: `STOM_V.wt-dashboard-remodel` → 이 문서는 loop 병합으로 함께 이동한다.
이어서 작업할 워크트리: `C:/System_Trading/STOM/STOM_V.wt-dev` (branch `loop/process-research-pipeline`).

## 목표 모델 (3계층 승격)

```
 feature/dashboard-v4-20260704 (V4 완성)          research/alpha-lab-idea5-foundation-20260707
        │  P1~P2 (완료)                                      │  P4 (남음, 충돌 0)
        ▼                                                    ▼
 loop/process-research-pipeline  ←── P3: 여기서 연구·개발 계속 (wt-dev)
        │  P5: 마일스톤마다 PR merge 승격 (clean FF)
        ▼
 STOM_Version_2U_C-ai-strategy-loop  (안정 승격 레인)
```

## 진행 상태

| 페이지 | 내용 | 상태 |
|---|---|---|
| P0 | 현황·사전 점검 | ✅ 완료 |
| P1 | loop → feature 반영·충돌 해결 (`controller/loop.py` union: W1-C last_completed_gen + CL-R04 evidence ledger) | ✅ 완료 |
| P2 | 전수 검증 → PR → loop 머지 | ✅ 완료 (이 문서가 loop에 있으면 머지된 것) |
| P3 | **loop(wt-dev)에서 연구·개발 지속** | ⏳ **현재 단계** |
| P4 | `research/alpha-lab-idea5-foundation-20260707` → loop 반영 | 🔜 남음 |
| P5 | loop → `STOM_Version_2U_C-ai-strategy-loop` PR merge 승격 | 🔜 남음 |
| P6 | 가드레일·롤백 (상시) | ♻ 상시 |

## P3 · loop(wt-dev)에서 개발 지속 — 안내

| 항목 | 내용 |
|---|---|
| 기준 | `loop/process-research-pipeline` (V4 대시보드 + CL-R07 연구 통합 완료 상태) |
| 시작 | wt-dev에서 `git pull` (origin/loop이 병합 결과로 갱신됨 → FF) |
| 대시보드 실행 | `python -m uvicorn ai_strategy_loop.dashboard.app:app --host 127.0.0.1 --port 8770` → `http://127.0.0.1:8770/ui/v4/` |
| 회귀 방지 | dashboard 관련 변경 시 `pytest tests/unit/dashboard/ -q` (기준 689+/0) |
| 실행 UAT | 큰 변경 후 `python scripts/v4_uat.py --execute --out <fresh-dir>` (13/13 기준) |
| 프론트 변경 시 | `webui-build`에서 `npm run typecheck && npm run build` (번들 커밋 동반) |
| 커밋 규칙 | 명시적 스테이징(`git add -A` 금지) · 한글 메시지 · 작은 단위 |

## P4 · alpha-lab → loop 반영 (남은 작업)

| # | 작업 | 명령 | 비고 |
|---|---|---|---|
| 1 | alpha push | `git push origin research/alpha-lab-idea5-foundation-20260707` | 로컬 전용 브랜치 → 원격 등록 |
| 2 | 충돌 재확인 | `git merge-tree --write-tree research/alpha-lab-idea5-... loop/...` | 2026-07-12 실측 **충돌 0** |
| 3 | PR 생성·머지 | `gh pr create --base loop/process-research-pipeline --head research/alpha-lab-idea5-...` | 검증 통과 후 머지 |

## P5 · loop → 2U_C-ai-strategy-loop 승격 (남은 작업)

| # | 작업 | 명령 | 비고 |
|---|---|---|---|
| 1 | FF 확인 | `git merge-base --is-ancestor STOM_Version_2U_C-ai-strategy-loop loop/...` | 참이면 clean FF |
| 2 | 전수 검증 | dashboard·top-level·UAT·npm·verify_nonrelease_sync | 전부 통과 시에만 |
| 3 | PR 생성·머지 | `gh pr create --base STOM_Version_2U_C-ai-strategy-loop --head loop/...` | 안정 레인 승격 |

## P6 · 가드레일 (상시)

- V3K 게이트 **3/6 유지**, 전 activation 플래그 **default-OFF** (`STOM_DASHBOARD_ALLOW_*` 포함).
- 보호 경로 무기록: `_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`, `backtest/graph/`, `.omx/reports/`, `v3k_settings*.json`, `_v3k_sidecar/`.
- `.omo/start-work/ledger.jsonl` append-only(기존 줄 수정 금지).
- 머지 전 롤백 = 통합 브랜치 삭제 / 머지 후 롤백 = `git revert -m 1 <merge>`.

## 참고 (이번 P1~P2에서 결정된 것)

- `controller/loop.py` 충돌은 W1-C(`last_completed_gen`)와 CL-R04(evidence ledger, DEFAULT-OFF) **양쪽 보존(union)** 으로 해결.
- `.omo/boulder.json`은 loop의 최신 운영 스키마 유지 + V4 works 기록 union, `ledger.jsonl`은 base+loop+V4 append union(700줄).
- PR #104(feature→2U_C-aisl 직접)는 이 모델에서 우회 대상이라 닫음.
