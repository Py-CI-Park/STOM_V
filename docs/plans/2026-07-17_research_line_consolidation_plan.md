# 연구 라인 통합 계획 — loop/process-research-pipeline 단일화 (2026-07-17)

## 0. 의도와 배경 (사장님 결정)

- 두 워크트리 연구(`research/v4-condition-process-audit-20260714`,
  `research/condition-history-tree-seeds-20260715`)는 **같은 목표**
  — "좋은 조건식을 만드는 시스템" — 를 속도를 위해 병렬 분산한 것이다.
- 이제 `loop/process-research-pipeline`을 **유일한 연구 본선**으로 재통합하고,
  이후 모든 신규 연구는 이 라인에서 진행한다.
- 워크트리는 앞으로도 단기 포크로 쓸 수 있으나, 종료 시 핸드오프 문서와
  체리픽 반영을 의무로 한다(이번 condtree 핸드오프가 모범 사례).

현재 상태 실측: 본선=`57d5c062`(v4 감사 라인 21커밋 흡수·origin 반영 완료),
condtree=`aaa05b41`(10커밋 + 핸드오프 문서). 두 라인 변경 파일 겹침 0.

## Phase 1 — condtree 인프라 흡수 (30~60분)

핸드오프 문서(`2026-07-17_condition_history_tree_parent_handoff.md`) §2 그대로:

1. 본선에 체리픽(의존 순): `ac3bfffd → 019fde99 → 2633358f → f055b64a →
   4fac0f89 → 6febb8af → ff0a774b` + 기록 `f254b9dd`, `aaa05b41`
2. **번들 커밋 `229be537` 제외** — 소스 반영 후 본선에서 재빌드
3. 예상 충돌 2곳 수동 배선: `frontend/app.jsx`(+3줄), `dashboard/research_api.py`(+2줄)
4. 커밋하지 않는 것: 그쪽 런타임 산출물(WSEED 등록·CSV·evidence JSON)

롤백 지점: 체리픽 전 본선 SHA 기록, 실패 시 `git reset --hard`로 원복.

## Phase 2 — 대시보드 v4.x 정합 (30~60분)

1. `ai_strategy_loop/dashboard/webui-build`에서 `npm ci && npm run build`로
   번들·HTML `?v=` 재생성 (v4.1 History 트리 패널 포함)
2. 검증 게이트:
   - 핸드오프 지정 집중 테스트 149개 (history/wide_seed/stage 계열)
   - 대시보드 회귀 391개 (`pytest tests/unit/test_dashboard* -q`)
   - 대시보드 실기동 → 히스토리 탭 "조건식 History (v4.1)" 육안 확인
   - 시작 설정 폼에 "홀드아웃 졸업검사" 필드 노출 확인(우리 라인 기여분)
3. v4.2 백로그(이번 범위 아님, 기록만): typed 피드백 인가 현황 배지,
   A/B 실험 러닝 상태 패널 — 후속 연구에서 필요해질 때만 착수.

## Phase 3 — 실험 교훈의 기본값 반영 (15분)

연구 프리셋(`research_presets.py`)에 실측 교훈 2건 반영:
- `analysis_card_v3_enabled: True` (카드 채널 원천 토글 누락 재발 방지)
- `bt_timeout: 2400` (틱 3년 warm 로딩 실측 15~20분 > 기존 900초)
테스트(`test_feedback_toggles_on.py` 계열) 동기 갱신.

## Phase 4 — 본선 확정과 워크트리 정리 (15분)

1. 전체 단위 테스트 + `verify_nonrelease_sync.py` + `git diff --check`
2. `loop/process-research-pipeline` fast-forward + origin push
3. wt-dev 체크아웃을 `loop/process-research-pipeline`으로 전환
   (연구 브랜치 이름이 아니라 본선에서 직접 작업 — 사장님 운영 원칙 반영)
4. 두 연구 브랜치는 병합 완료 표식으로 보존(삭제하지 않음), condtree
   워크트리는 그쪽 담당자가 본선 rebase 후 재사용 또는 휴면.

## Phase 5 — 통합 라인에서 새 연구 착수 (반나절~)

condtree Stage-1 실측이 준 리드를 그대로 잇는다 (핸드오프 §5 로드맵):

| 순서 | 연구 | 근거 | 예상 |
|---|---|---|---|
| ①+② 병렬 | min 장초 30분 × 중대형(승률 41% 셀)을 시가갭 5구간 × 등락률 6구간으로 세분화 + 매도 프로필 민감도 A/B | 첫 수익성 후보 구간 확정/제외의 데이터 근거 | 반나절 |
| ④ | Frozen OOS/WF 승격 게이트 (새 ralplan + 별도 승인) | 선택 편향 제거 — **수익 전략 확정의 유일한 관문** | 계획 1h + 실행 3~5h |
| ③ | 셀별 자본곡선/MDD 분리 (①·② 결과로 후보가 좁혀진 뒤에만) | 낙폭·동시보유 상호작용 | ~4.5h |
| (보류) | typed 피드백 승격 재도전 | ①~④로 게이트 통과가 실재하는 환경이 생긴 뒤 | ~6h |

## 안전 경계 (전 Phase 공통)

- cherry-pick만 사용, overlay merge 금지 (브랜치 규약)
- 운영 `_database/` 등록·기록 금지 (condtree 코드도 경로 거부 내장)
- Stage-1 결과는 `exploratory_full_history` — OOS·승격·export/live 근거 아님
- `performance_proved=false` 유지, 성과 주장은 Phase 5-④ 통과 후에만
