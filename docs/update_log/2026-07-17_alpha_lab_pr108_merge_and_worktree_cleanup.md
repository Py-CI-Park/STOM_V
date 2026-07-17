# 2026-07-17 알파 연구 랩 PR #108 통합 병합 + 알파 워크트리 정리

## 0. 요약
PR #108(`연구 랩 통합 → loop 복귀`)을 **라인 연결형 merge commit**(`4b6cc9a7`)으로 본선
`loop/process-research-pipeline`에 병합. 두 알파 워크트리(`wt-alpha`, `wt-alpha-audit`)를
정리. 순수 additive(코어 app.py 2줄만), 안정화 통과, `performance_proved` 판단은 알파 랩
자체 영수증에 위임(본선은 자산·이력 편입만).

## 1. 병합 방식 결정 (사장님: "깃 라인이 이어져야 관리 쉽다")
- squash(라인 끊김)·cherry-pick(라인 끊김) 대신 **일반 merge commit** 채택 → 218커밋 이력이
  본선에 연결·보존. `git log --first-parent`로 병합노드만 보면 깔끔.
- 병합노드 `4b6cc9a7` 부모 2개: `0a0ecca5`(loop) + `03c73513`(alpha idea5).

## 2. 병합 범위 (662파일)
- 신규 657 / 기존 수정 5(app.py·.gitattributes·README·스크립트1+테스트1) / 삭제 0 / 프런트·번들 무접촉.
- `alpha_lab/*` 신규 패키지(채굴·번역·이벤트스터디·규율·리포팅·runlab·btrack·o3/o4lab 등, 새 네임스페이스).
- `ai_strategy_loop/dashboard/alpha_api.py`(신규) + app.py `alpha_router` 등록.
- `docs/research/*` 영수증·리포트 418, `tests/unit` 50개 알파 테스트.
- `.gitattributes`: `alpha_lab` 러너-소스 LF 고정(신뢰-해시 게이트 결정성 — **기존 파일 무영향**).

### 유일 충돌 = app.py 1파일(import 블록)
양측 additive(보안 import vs alpha_api import) → **둘 다 유지**로 해소. include_router는 무충돌 병합.

## 3. 안정화 검증
| 항목 | 결과 |
|---|---|
| 병합 완전성 | `03c73513 ∈ origin/loop` = YES, 잔여 고유커밋 0 |
| `create_app()` + `/api/alpha` 5종 라우트 | 등록 확인(status/dataset/events/rules/funnel), 보안 게이트 403(정상) |
| 대시보드+history 회귀(app.py 표면) | **1,295 passed** |
| 알파 임계 테스트(api·reporting·shell가드·캐시·라우트·baseline) | 49/50 passed |
| `verify_nonrelease_sync.py` | exit 0 |
| `git diff --check` / 보호경로 스테이징 | clean / 없음 |

### 유일 실패 1건 = 환경 의존(회귀 아님)
`tests/unit/test_reporting.py::test_build_conditions_sha_and_escape` — `render_conditions()`가
**보호 런타임 경로 `_database/strategy.db`**(stockbuy/stocksell)를 read-only로 읽어 매수조건
SHA `348c5181`을 검증한다. wt-alpha에는 해당 챔피언 조건이 등록돼 통과, wt-dev에는 미등록이라
graceful degradation → SHA 부재. **바이트 동일 코드가 wt-alpha에서 통과함을 교차검증**으로 확인
(merge 회귀 아님, PR 핸드오프가 예고한 seed-DB 환경 부류). 알파 무거운 테스트 다수가 동일하게
로컬 DB/서브프로세스에 의존한다.

## 4. 워크트리 정리
| 워크트리 | 커밋 보존 | 정리 결과 |
|---|---|---|
| `wt-alpha` (idea5 @ 03c73513) | origin 푸시 + 본선 병합 완료 | git 등록 해제·브랜치 ref 보존. 물리 폴더는 파일 잠금(resource busy)으로 잔존 → **점유 창/프로세스 닫고 폴더 수동 삭제 필요** |
| `wt-alpha-audit` (audit @ e808015c, ⊆ idea5) | idea5에 완전 포함(origin 보존) | 완전 제거 ✓ |
- 브랜치 ref 2개 보존(마커): 필요 시 재-워크트리 가능. audit는 origin 미푸시지만 idea5⊇audit라 무손실.
- 미추적 증거 1건(9B) `artifacts/wt-alpha-preserved/_discovery_feedback.txt`로 보존.

## 5. 후속 (별도)
1. `wt-alpha` 물리 폴더 잔여 삭제(잠금 해제 후).
2. (선택) **V4 대시보드에 알파 탭 반영** — `alpha_api`(백엔드)는 들어왔으나 V4 셸(`v4-*.jsx`)
   미배선. 신규 패널 V4 배선 규칙(AGENTS.md)대로 별도 진행.
3. C단계(41% 셀 세분화 + 청산 A/B) 착수 — 알파 v4 앙상블 자산 본선 확보로 교차참조 용이.
