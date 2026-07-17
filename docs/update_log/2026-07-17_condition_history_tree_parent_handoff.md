# 부모 브랜치 핸드오프 — 조건식 History 트리·와이드 시드 연구 라인

- 날짜: 2026-07-17
- 소스 브랜치: `research/condition-history-tree-seeds-20260715` (워크트리 `STOM_V.wt-condition-tree`)
- 기준 커밋: `d5dece4f43d80358f7303cb3fdaf4ab820e7e072` / 2U_C 계열 merge-base: `8006cd93`
- 대상: 부모 연구 라인(예: `research/v4-condition-process-audit-20260714` 또는 후속 통합 라인). **cherry-pick만 사용, overlay merge 금지** (브랜치 규약)
- 정본 계획: ralplan `stage-09-final.md` (SHA-256 `a41097790e2e469c41b94ce515e7d026be03ddca2377ef732a06a824aae5c8cd`, 세션 `.gjc/_session-019f660b-1c18-7000-98db-61af7bc0d0aa/plans/ralplan/019f660b-1c18-7000-98db-61af7bc0d0aa/`)
- 울트라골 감사: `.gjc/_session-019f6602-b0e6-7000-bd71-18662f76db88/ultragoal/` (goals.json 5/5 complete, ledger.jsonl 영수증 전체)

## 1. 이 브랜치가 만든 것 (커밋 10개)

| 커밋 | 성격 | 내용 |
|---|---|---|
| `f254b9dd` | 기록 | 합의 계획 한글 기록 + 검토 HTML(조건식 전문) |
| `ac3bfffd` | **인프라** | `cli/condition_history_schema.py`(동결 축/청산 영수증, condition_history_v1 노드·flat_rows·검증), `cli/research_history_projection.py`(단일 원자 발행기), `ai_strategy_loop/dashboard/history_adapters.py`(Campaign/LoopRun 읽기 전용 어댑터) + 테스트 54 |
| `019fde99` | **인프라** | `ai_strategy_loop/dashboard/history_api.py`(/history/index·detail, cursor/400/409/422), `frontend/history-condition-tree.jsx`(v4.1 트리·테이블 패널), research_api.py +2줄, app.jsx +3줄 + 테스트 17 |
| `229be537` | 빌드 | webui-build 표준 빌드로 bundle/app.js·HTML ?v= 재생성 |
| `2633358f` | 수정 | 패널 badge를 서버 label 계약(code_lookup_status·hypotheses_present)에 고정, 번들 재생성 |
| `f055b64a` | **인프라** | `cli/wide_seed_v1.py`(승인 계획 byte-일치 통합 조건식 4종·격리 DB 전용 등록기·`_database` 경로 거부), `cli/wide_seed_trial_planner.py`(TrialSpecV1·예산 2/4·append-only 원장), `cli/stage0_inventory.py` + 테스트 51 + `utility/ai_agent/strategy/` 시드 텍스트 4종 |
| `4fac0f89` | 수정 | Stage-0 영수증 생성기 단독 재현성(min_coverage/notes 명시 입력) |
| `6febb8af` | **인프라+기록** | `cli/stage1_run.py`(sealed env cold/warm 2모드 공식 실행), `cli/stage1_cell_decomposition.py`(매수시간×시가총액 12셀 분해·12자리 min 타임스탬프·unassigned 사유·파리티 보증·History 변환/발행), companion 소비 통합, Stage-1 결과 한글 기록 |
| `ff0a774b` | 수정 | 형태 불량 companion typed 흡수(API 500 방지) |
| (본 커밋) | 기록 | 부모 핸드오프 문서 |

## 2. 부모 브랜치 반영 절차 (cherry-pick)

권장 순서(의존성 순): `ac3bfffd → 019fde99 → 2633358f → f055b64a → 4fac0f89 → 6febb8af → ff0a774b` (+ 기록 커밋 `f254b9dd`·본 커밋은 선택)

1. **번들 커밋 `229be537`은 cherry-pick하지 말 것** — 부모의 frontend 상태와 해시가 다르므로 소스 반영 후 부모에서 `cd ai_strategy_loop/dashboard/webui-build && npm ci && npm run build`로 재생성한다(2633358f의 번들 hunk 충돌 시 소스 파일만 받고 번들은 재빌드).
2. **예상 충돌 지점**: `frontend/app.jsx`(+3줄 배선), `dashboard/research_api.py`(+2줄 router 등록) — 부모에서 해당 파일이 진화했으면 같은 자리(Track-Z import 블록, history_router include)에 수동 재배선.
3. **반영 후 검증(필수)**:
   - `PYTHONUTF8=1 python -m pytest tests/unit/test_condition_history_schema.py tests/unit/test_research_history_projection.py tests/unit/test_history_adapters.py tests/unit/test_history_api.py tests/unit/test_wide_seed_v1.py tests/unit/test_wide_seed_trial_planner.py tests/unit/test_stage0_inventory.py tests/unit/test_stage1_run.py tests/unit/test_stage1_cell_decomposition.py -q` (이 브랜치 기준 총 149개)
   - `python -m pytest tests/unit/test_dashboard* -q` (회귀 391개, 이 브랜치에서 무손상 확인됨)
   - `pytest tests/unit/ -q` + nonrelease 경로 접촉 시 `python scripts/verify_nonrelease_sync.py` (루트 규약)
   - 번들 재빌드 후 대시보드 기동 → 히스토리 탭에서 "조건식 History (v4.1)" 패널 육안 확인
4. **커밋하지 않는 것들**(런타임/산출물 — 부모에서 재생성): `ai_strategy_loop/state/loop_strategies.db`의 WSEED_V1_* 등록 4건, `backtest/csv/stock_bt_WSEED_V1_*.csv`, `.omo/evidence/tmap-walkforward/wide_seed_v1_stage1_{tick,min}_condition_history_v1.json`, `artifacts/ultragoal-condtree/*`. 재현 방법은 §4.

## 3. 부모가 검토해야 할 사항 (설계 결정·경계)

- **동결 축 정본**: `cli/condition_history_schema.py`의 frozen 상수 — tick 창 90000/90500/91000/92000, min 창 90000/93000/100000/140000, 시총 4군 3000/6000/10000억, 갭 ±15% 5구간, 등락률 -15~29, 워밍업/신호 20. 변경은 새 boundary receipt 발행으로만.
- **Min 12~13시 포함은 opt-in 권위** — 기존 `MIN_BANDS`(lattice) 기본값은 불변. 이 프로필에서만 override.
- **매도 프로필은 미검증 비교용**(tick -3/+5/300초, min -4/+6/60분) — 후속 ②(청산 A/B) 전까지 성과 주장 금지.
- **companion이 캠페인 정본**: `<campaign>_condition_history_v1.json`이 있으면 어댑터가 이를 소비(재합성 없음), 손상/형태 불량은 typed `companion_invalid`. 발행은 `cli.research_history_projection.publish_condition_history` 단일 경로만.
- **결과 역할 경계**: `wide_seed_v1_stage1_*`는 `exploratory_full_history` — OOS·승격·export/live 근거 아님. 레인 간 기간 불일치(`non_common_history`, tick 2022~ vs min 2025~).
- **알려진 함정**: ① min per-trade CSV `매수시간`은 12자리(YYYYMMDDHHMM) — 분해기는 대응 완료, 다른 소비자 주의. ② cold-subprocess(4엔진) full-universe는 `engine_data_response_timeout` 병목 — 공식 실행은 warm-session 32엔진(`run_trial_warm`) 사용. ③ `데이터길이<20` 워밍업이 각 레인 첫 시간창 유효 구간을 축소(코드 유지, 해석 시 명시).
- **보안/격리**: 운영 `_database/` 등록·기록 경로는 코드 레벨 거부(ValueError). 시세 DB는 env(`STOM_CLI_DATABASE_DIR`/`STOM_CLI_DB_*`) 읽기 전용 참조.

## 4. 재현 시퀀스 (부모에서 Stage-1 재실행 시)

```text
1) 시드 등록:   python -c "from cli.wide_seed_v1 import register_seeds; register_seeds('ai_strategy_loop/state/loop_strategies.db')"
2) 계획/원장:   cli.wide_seed_trial_planner.build_default_plan(boundary_sha, exit_sha) → append_ledger_entry(planned)
3) Stage-0:     cli.stage0_inventory.build_stage0_receipt(데이터루트, stock_min_back.db, ..., min_coverage=선언) → write_receipt
4) 실행(min):   cli.stage1_run.run_trial_warm(...)  # warm-session 32엔진, 전체기간 103초 실측
   실행(tick):  tick 전용 wrapper(artifacts/ultragoal-condtree/g005_run_tick_warm_wrapper.py 패턴), 952일 ≈ 20분
5) 분해/발행:   cli.stage1_cell_decomposition.decompose_cells → cells_to_history_evaluations → publish (research_id/stage.research_id 일관 유지)
6) 확인:        대시보드 히스토리 탭 → 조건식 History (v4.1) → campaign:wide_seed_v1_stage1_*
```

## 5. Stage-1 결과 요약과 후속 연구 로드맵 (부모에서 재고려용)

결과 상세: `docs/update_log/2026-07-17_wide_seed_v1_stage1_exploratory_results.md` (같은 브랜치, cherry-pick 대상 포함)

- Tick 178,247건/2,314종목: 전 셀 순손실(합계 약 -40.8억), 승률 29~34%, 늦은 창일수록 하락, 소형주 손실 집중 최대
- Min 26,198건/1,067종목: 합계 약 -7.6억, **장초 30분 × 중대형(≥6000억) 승률 41%로 상대 우위**

| 순위 | 후속 단계 | 목적 | 부하/예상 시간 | 예상 성과 |
|---:|---|---|---|---|
| ① | 유망 셀 세분화 시드(라운드 2): min 09:00~10:00 × 중대형을 **시가갭 5구간 × 등락률 6구간** 중첩 elif로 세분화(leaf별 전체 조건 반복 — 갭은 CSV 사후분해 불가라 조건식 내 분기 필수) | 승률 41%→50%+ 임계값의 데이터 근거 | 백테스트 5분 미만(min), 총 2~3시간 | 첫 수익성 후보 구간 확정 또는 제외 구간 확정 |
| ② | 매도 프로필 민감도 A/B(2~3 변형: 손절 -2/-5, 보유 절반/2배) | 손실이 진입 문제인지 청산 문제인지 분리 | min 5분·tick ≈1시간, 총 2~3시간 | 청산 기본값 동결 근거(손익비/승률 곡선) |
| ③ | 셀별 자본곡선/MDD 분리 — stage-08-final(SHA `cfcbfb592291b6a44d5f8bd2f77725c3d756229324123616b26ac09adaba4d85`)의 24개 분리 전략(예산 26/33) | 셀별 낙폭·동시보유 상호작용 | tick 12×20분 ≈ 4.5시간 | ①·②로 후보가 좁혀진 뒤에만 실행 권장 |
| ④ | Frozen OOS/WF 승격 게이트 — 새 ralplan으로 disjoint calibration/selection/frozen 기간·스냅샷 해시 동결 후 별도 승인 | 선택 편향 제거된 승격 판정 | 계획 1시간 + 실행 3~5시간 | 승격 가/부 — 통과 시에만 final approval/export 자격 |
| ⑤ | 부모 브랜치 cherry-pick(본 문서 §2) | 인프라 공용화 | 30~60분 + 회귀 | 모든 캠페인이 이력 트리·셀 분해 도구 공용 |

권장 순서: **⑤(인프라 흡수) → ①+②(병렬 가능, 반나절) → ④ → ③(필요 시)**. ①~③은 연구 전용이며, 수익 전략 확정 관문은 ④가 유일하다.

## 6. 미결/주의 사항

- G004Seeds 워커의 pytest 자체 실행 일탈 1건 — 리더 독립 재검증으로 무해 확인(기록 목적 명기).
- `.gjc/` 세션 산출물(계획/원장)은 세션 정리 시 소실될 수 있음 — 본 문서와 두 update_log가 내구 기록이며, 필요 시 stage-09-final 전문은 검토 HTML(`docs/research/condition_research/condition_seed_review_20260716.html`)에 조건식 원문이 보존되어 있다.
- 이 브랜치의 번들(`229be537`·`2633358f`)은 이 브랜치 소스 기준 — 부모 반영 시 반드시 재빌드.
