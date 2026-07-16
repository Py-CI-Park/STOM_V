# V4 감사 브랜치 본선 반영과 파생 워크트리 동기화 안내 (2026-07-16)

## 1. 본선 반영

- `research/v4-condition-process-audit-20260714`를 `loop/process-research-pipeline`에
  fast-forward로 반영했다. 부모가 분기점(`bb41ae4e`)에서 이동하지 않아 체리픽과
  결과가 동일하며, 검증된 커밋 해시가 그대로 보존된다.
- 반영 커밋(분기점 이후 순서):
  1. `3f7cb1d6` 문서: V4 조건식 개선 프로세스 심층 감사
  2. `920736fe` 문서: 백테스트 기반 AI 조건식 재생성 집중 감사
  3. `004dd622` 개선: V4 조건식 P0 계약 폐쇄
  4. `d5dece4f` 개선: V4 조건식 피드백 계약 폐쇄
  5. `8cee4679` 정리: 미사용 2x2 영수증 계층 제거
  6. `3d6e8675` 수정: 백테스트 큐 계약과 단위 기준선 복구
  7. `f3ddbd14` 수정: V4 병합 차단 계약과 증거 경계 보강
  8. `a3022b82` 정리: 검증 도구 위생 보수 (이후 커밋 포함)

## 2. 파생 워크트리 `STOM_V.wt-condition-tree` 동기화 안내

`research/condition-history-tree-seeds-20260715`는 `d5dece4f`에서 파생되어
위 5~8번 커밋이 빠져 있다. 특히 `3d6e8675` 없이는 다음이 그 워크트리에 남는다.

- BackTest가 구식 확장 생성자 계약으로 동작 (당시 시점 안에서는 일관되므로 즉시 깨지지는 않음)
- warm session BackTest spawn 결함 (실 warm 실행 실패)
- 단위 기준선 실패 7건

### 동기화 절차 (그쪽 연구가 다음 커밋 지점에 도달했을 때 수행)

```powershell
# 진행 중 미추적 연구 산출물 위에 얹지 말 것 — 반드시 커밋 경계에서 수행
cd C:/System_Trading/STOM/STOM_V.wt-condition-tree
git status --short --untracked-files=no   # 추적 변경이 없는지 확인
git cherry-pick 8cee4679 3d6e8675 a3754e9b f3ddbd14 a3022b82
pytest tests/unit/ -q
python scripts/verify_nonrelease_sync.py
```

### 충돌 예상 파일

`cli/runner.py`, `cli/warm_session.py`, `backtest/backtest.py`,
`scripts/verify_nonrelease_sync.py` — 그쪽에서 이 파일을 수정했다면
**소형 12인자 생성자 + 13필드 backQ 선전달** 계약을 기준으로 해소한다.

## 3. 자원 조율

- 본선에서 실 연구 A/B(`ab20260716_*`)가 순차 실행 중인 동안
  condition-tree 워크트리의 대규모 warm 백테스트 실행은 시간대를 분리한다.
  (같은 머신에서 warm 32엔진 × 2 세션 동시 실행 시 타임아웃 오판 위험)
