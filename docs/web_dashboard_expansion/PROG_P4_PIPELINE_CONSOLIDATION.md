# P4 — PIPELINE 통합(canonical `window.STOM_PIPELINE` in format.ts)

> 2026-06-14. 대시보드 스타일·구조 개선 프로그램 Phase 4. 유일하게 안전 병합 가능한 쌍.

## 한 줄 요약
중복된 진화 7단계 정의(`_RL_PIPELINE`@research-lab vs `RP_PIPELINE`@research-pro)를 **format.ts 의 정본 `window.STOM_PIPELINE` 단일 출처**로 통합. 두 소비처는 정본 참조, 로컬 사본 삭제. C2 규칙(공유 데이터는 pre-app format.ts) 준수.

## field-diff (병합 전 — 버리는 사본이 고유 내용 없음 증명)
두 사본은 **같은 7단계·같은 아이콘·같은 단계 제목**. 차이는 (a) `desc`/`terms` 문구 상세도, (b) `RP_PIPELINE`만 `key` 필드 보유. **RP 가 RL 의 슈퍼셋**(RP 문구가 RL 의 모든 의미를 포함·확장):

| 단계 | RL desc(터서) | RP desc(상세·정본 채택) | 판정 |
|------|--------------|------------------------|------|
| 시드 선택 | "…이후 진화의 기준점입니다." | "…이후 **모든** 진화의 기준점이 됩니다." + 용어에 "(예: Tick_902)" | RP ⊇ RL |
| 후보 생성 | "직전 부검…" | "**LLM이** 직전 세대의 부검…" + 용어 확장 | RP ⊇ RL |
| 격자 탐색 | "…단일 피크가 아닌 '고원'…" | "…격자(grid)…견고한지 지형…단일 피크가 아닌 '고원'…" + 용어 2개 확장 | RP ⊇ RL |
| 백테스트 평가 | "…시뮬레이션합니다." | "…시뮬레이션해 **성과를 측정**합니다." | RP ⊇ RL |
| 적합도/품질 게이트 | "…통과합니다." | "…통과합니다. **품질은 결과의 견고함을 봅니다.**" + 용어 "(fitness)" | RP ⊇ RL |
| OOS 검증 | "…유지되는지 확인합니다." | "…확인합니다. **과최적화를 거르는 핵심 관문.**" | RP ⊇ RL |
| 명예의 전당/동결 | "…운영 후보로 보관합니다." | "…**더 이상 바뀌지 않도록** 동결(freeze)…보관합니다." | RP ⊇ RL |

→ RP 판본 + `key` 필드를 **정본**으로 채택. RL 사본은 의미 손실 없이 삭제 가능. (RL 오버레이의 표시 문구는 터서→상세로 바뀜 = 이 PR 의 유일한 픽셀/콘텐츠 변화, research-lab 한 면.)

## 변경
- **webui-build/src/format.ts**: `interface PipelineStage` + `export const STOM_PIPELINE: PipelineStage[]`(RP 7단계 정본) + `window` 노출(C2: pre-app 전역, no-TDZ, .jsx collision 면제).
- **research-lab.jsx**: `const _RL_PIPELINE = [...]` 삭제 → `_RlProcessFlowOverlay` 내 `const PIPELINE = window.STOM_PIPELINE || []` + 사용처 3곳 `PIPELINE`.
- **research-pro.jsx**: `const RP_PIPELINE = [...]` 삭제 → `_RpProcessFlowOverlay` 내 동일 alias + 사용처 3곳.
- **test_p3_consolidation.py**: `test_pipeline_consts_still_separate`(이전 이연 가드) → `test_pipeline_consolidated_to_format_ts`(정본 통합 단언)로 갱신.
- **test_research_pro.py**: 7단계 문구 단언을 research-pro.jsx → format.ts 로 리타겟 + `window.STOM_PIPELINE` 소비 단언.
- 빌드 산출물: **stom-ui.js(v=f41f5701, format.ts 변경) + app.js(v=f1f2f4e9) + manifest** 재생성·커밋(M2).

## 가드/검증
- `const _RL_PIPELINE = [`·`const RP_PIPELINE = [` 0(로컬 사본 제거). no_duplicate_globals green(정본은 format.ts → .jsx 검사 면제; 로컬 alias `PIPELINE` 은 함수 내부라 비-최상위).
- test_p3_consolidation·test_research_pro·test_p11_process_flow(라이브 ProcessFlowPanel — 무영향)·p14·index_cache green.
- 전체 pytest 7 failed(핀 베이스라인 동일) + 3229 passed — 신규 0. verify_nonrelease exit0.
- 8771 런타임: `window.STOM_PIPELINE` = 7원소(keys seed→freeze, firstTitle "시드 선택"); 6탭 0 pageerror.

## 다음
**[P6 전 정지 — 사용자 지시]** P6(디자인시스템 랜딩)은 선행조건(OQ#2 밀집표 폰트 예외목록) + 사람의 시각 재베이스라인 승인 필요. P7도 픽셀 변경. 사용자 입력 대기.
