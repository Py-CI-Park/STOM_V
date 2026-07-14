# AI 조건식 루프 정본 재구축 마스터 계획 (2026-07-11)

> 이 문서는 `.omo/plans/ai-condition-loop-canonical-rebuild-20260711.md` 실행계획의 사람이 읽는 governance 미러다. 세부 실행 계약은 그 `.omo` 계획과 정본 설계 spec `docs/research/condition_research/generated_conditions/lattice_v3_design_20260709/lattice_v3_design_spec_20260709.md`가 보유한다.

## TL;DR
모든 후보·데이터·실패 진단·다음 변경·평가·최종 판정이 추적되는 하나의 조건식 개선 시스템을 만든다. 기존 generator·공식 백테스트·분석·대시보드는 유지하고, 누락된 증거 연결과 단일 소유권을 그 주위에 추가한다. 소형 학습 증명을 성능 검증보다 먼저 하고, 미관측 데이터·인간 비교는 앞선 증거가 통과할 때까지 잠근다. 규모 XL, 위험 High.

## 권한 위계
1. 이 마스터 계획 = 유일한 최상위 실행 로드맵.
2. `lattice_v3_design_spec_20260709.md` = 유일 정본 설계 계약.
3. `docs/update_log/2026-07-11_ai_condition_loop_goal_process_reset_audit.md` = 현재 목표/상태 권한.
4. `docs/research/condition_research/plans/lattice_condition_generation_v3_design_only_20260709.md` = 하위 CL-D 실행계약.
5. receipt·failure matrix·protocol·handoff = 지원 증거(계약 재정의 불가).

## 단계 개요 (canonical IDs)

### 설계 단계 CL-D0..CL-D4 (이번 실행 범위)
| ID | legacy | 산출물 | 커밋 |
|---|---|---|---|
| CL-D0 | P1/T0 | source read receipt + scope lock | 누적 |
| CL-D1 | P2/T1 | failure lesson matrix | 누적 |
| CL-D2 | P3/T2 | canonical design specification | 누적 |
| CL-D3 | P4/T3 | evaluation protocol + next command | 누적 |
| CL-D4 | P5/T4 | master plan + handoff + pointer 교정 + verification | 한국어 문서 커밋 후 HARD STOP |

### 런타임/증거 단계 CL-R01..CL-R10 (이번 실행에서 잠금; 각 정확 승인 문구 필요)
| ID | legacy | 내용 | 승인 문구 |
|---|---|---|---|
| CL-R01..R06 | P6(P7/P8 흡수) | phase 계약·증거 계약·EvidenceStore·provenance/wiring·피드백·다양성/2x2 | `I approve CL-R01-R06 code integration only` |
| CL-R07 | P9 | 3라운드 제한 폐루프(프로세스 증명, 최대 9 공식평가/3 provider/120분) | `I approve CL-R07 bounded mini-loop only` |
| CL-R08 | P10 | 60일 train40/validation20 제한 성능(최대 11 공식평가/4시간) | `I approve CL-R08 bounded min performance only` |
| CL-R09 | P10 | 2026-07-11 이후 20일 4-fold 봉인 OOS/WF | `I approve CL-R09 sealed OOS/WF only` |
| CL-R10 | P11 | 동일 cohort 인간 비교·승격 검토(분석) | `I approve CL-R10 benchmark promotion review only` |

## 실행 순서 요약
- 이번 ultragoal 실행 = CL-D0..CL-D4 (설계/문서 전용) → 한국어 커밋 → HARD STOP.
- CL-R01 이후는 위 정확 승인 문구가 기록된 뒤 별도로 진행. 성능 통과도 export/live를 자동 승인하지 않는다.

## 가드레일
- 조건식 본문 생성·provider import·런타임 DB open·backtest/replay/OOS/Plan D/portfolio/export/live 금지(설계 단계).
- 증거 테이블 append-only INSERT-only(UPDATE/DELETE 금지). 런타임 DB/CSV/log는 Git 커밋 금지.
- 보호 경로 불가침(`_database/`, `_database_v3k_shadow/`, `_log/`, `backup/`, `*.db`, `backtest/graph/`, `.omx/reports/`, `v3k_settings*.json`, `ai_strategy_loop/state`).
- `git add -A` 금지, 명시 allowlist만 스테이징, 커밋 한국어.
- run_loop이 최종 계보의 유일 소유자. batch/research는 근거/제안 어댑터일 뿐 자율 학습을 주장할 수 없다.

## 성공 기준 (분리 보고)
`system_built`, `learning_proved`, `performance_proved`, `human_comparison_proved`, `live_authorized`(이 범위에서 항상 false)를 각각 정직하게 보고한다. 인프라/문서 완성만으로 자율 개선 목표 달성을 선언하지 않는다.
## DR-00 post-completion governance overlay pointer (2026-07-13)

Post-completion governance amendment: `docs/research/condition_research/plans/2026-07-13_ai_condition_loop_dr00_post_completion_governance_amendment.md`. This master plan retains its historical authority; the amendment has overlay-only precedence for explicit post-completion DR interpretation. Evidence != authority, no existing CL phrase/receipt carries DR authority, and there is no automatic CL-R08 transition.
