## 목적

`STOM_Version_2U_C-ai-strategy-loop` 이후 누적된 조건식 연구, 대시보드 감사, evidence lineage, 공식 OOS 재시작 기준을 한 번에 검토 가능한 패키지로 정리합니다.

이 PR은 실제 연구 재개 전 준비 단계입니다. 현재 브랜치의 기존 연구 커밋 흐름을 protected anchor 브랜치로 PR merge하기 위한 기준 문서와 검증 증거를 제공합니다.

## 포함

- 브랜치/PR 재시작 지도와 dirty worktree 분류
- 조건식 연구 registry, naming taxonomy, evidence lineage
- 공식 OOS 큐와 승격/보류 상태 경계
- 대시보드 IA, 중복 기능, 시각/오류/비효율 감사
- 전체 QA 매트릭스, 자동 검증, 실제 브라우저/HTML/PNG QA 증거
- `wt-dev` 연구 흐름과 `wt-webbt` 대시보드 구현 PR 분리 전략

## 제외

- 실제 official OOS 실행 없음
- live/strategy DB 승격 없음
- V3K gate 변경 없음
- KHOPENAPI/login/live order 작업 없음
- `backtest.py` 변경 없음
- `git add -A` 사용 없음

## 검증

- `python -m json.tool .omo/evidence/stom-reorg-20260618/research-registry.json`
- `git diff --check`
- protected path status 재검사
- `python scripts/verify_nonrelease_sync.py`
- `node build-app.mjs`
- `node track-z-harness.mjs`
- `node check-missing-imports.mjs`
- dashboard focused pytest: 10 passed + 4 passed
- 임시 uvicorn + curl smoke: `/ui/`, `/research_records`, `/evolution_gui_parity?run_id=&gen_no=-1`, `/research_docs`
- Chrome headless 7탭 HTML/PNG 캡처

## 다음 단계

1. PR 검토 후 merge commit으로 `STOM_Version_2U_C-ai-strategy-loop`를 갱신합니다.
2. 갱신된 anchor에서 다음 연구 브랜치를 생성합니다.
3. 실제 연구는 `official-oos-queue.md` 기준으로 `저시총 제외 방어 조합` 공식 OOS부터 시작합니다.
4. 대시보드 구현은 `wt-webbt`에서 file-disjoint PR로 별도 진행합니다.
